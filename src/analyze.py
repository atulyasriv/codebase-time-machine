from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import git
import networkx as nx
import pandas as pd


@dataclass(frozen=True)
class CommitRow:
    sha: str
    authored_dt: datetime
    author: str
    message: str
    files_changed: int
    insertions: int
    deletions: int


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iter_commits(repo: git.Repo, *, max_count: int | None = None) -> Iterable[git.objects.Commit]:
    kwargs = {}
    if max_count:
        kwargs["max_count"] = int(max_count)
    # default: walk HEAD
    return repo.iter_commits(**kwargs)


def commit_table(repo: git.Repo, *, max_count: int = 2500) -> pd.DataFrame:
    rows: list[CommitRow] = []
    for c in iter_commits(repo, max_count=max_count):
        stats = c.stats.total
        authored = _to_utc(c.authored_datetime)
        rows.append(
            CommitRow(
                sha=c.hexsha,
                authored_dt=authored,
                author=getattr(c.author, "name", "unknown") or "unknown",
                message=(c.message or "").splitlines()[0][:120],
                files_changed=int(stats.get("files", 0)),
                insertions=int(stats.get("insertions", 0)),
                deletions=int(stats.get("deletions", 0)),
            )
        )
    df = pd.DataFrame([r.__dict__ for r in rows])
    if df.empty:
        return df
    df = df.sort_values("authored_dt").reset_index(drop=True)
    df["date"] = df["authored_dt"].dt.date
    df["dow"] = df["authored_dt"].dt.dayofweek  # 0=Mon
    df["hour"] = df["authored_dt"].dt.hour
    return df


def file_churn_table(repo: git.Repo, *, max_count: int = 2500) -> pd.DataFrame:
    """
    Per-file aggregated churn across commits.
    """
    agg: dict[str, dict[str, int]] = {}
    last_touch: dict[str, datetime] = {}
    for c in iter_commits(repo, max_count=max_count):
        dt = _to_utc(c.authored_datetime)
        for path, st in c.stats.files.items():
            if path not in agg:
                agg[path] = {"insertions": 0, "deletions": 0, "lines": 0, "commits": 0}
            agg[path]["insertions"] += int(st.get("insertions", 0))
            agg[path]["deletions"] += int(st.get("deletions", 0))
            agg[path]["lines"] += int(st.get("lines", 0))
            agg[path]["commits"] += 1
            if path not in last_touch or dt > last_touch[path]:
                last_touch[path] = dt

    if not agg:
        return pd.DataFrame()

    df = pd.DataFrame(
        [
            {
                "path": p,
                **v,
                "last_touched": last_touch.get(p),
                "churn": v["insertions"] + v["deletions"],
            }
            for p, v in agg.items()
        ]
    )
    df = df.sort_values(["churn", "commits"], ascending=[False, False]).reset_index(drop=True)
    return df


def cochange_graph(repo: git.Repo, *, max_count: int = 1500, min_edge_weight: int = 2) -> nx.Graph:
    """
    Build a file co-change graph: if two files are modified in the same commit, connect them.
    """
    g = nx.Graph()

    for c in iter_commits(repo, max_count=max_count):
        files = sorted({p for p in c.stats.files.keys() if p and not p.endswith("/")})
        if len(files) < 2:
            for f in files:
                if not g.has_node(f):
                    g.add_node(f)
            continue

        # add nodes
        for f in files:
            if not g.has_node(f):
                g.add_node(f)

        # add weighted edges
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                a, b = files[i], files[j]
                if g.has_edge(a, b):
                    g[a][b]["weight"] += 1
                else:
                    g.add_edge(a, b, weight=1)

    # prune weak edges
    to_remove = [(u, v) for (u, v, d) in g.edges(data=True) if int(d.get("weight", 1)) < min_edge_weight]
    g.remove_edges_from(to_remove)

    # prune isolated nodes
    isolates = [n for n in g.nodes() if g.degree(n) == 0]
    g.remove_nodes_from(isolates)
    return g


def dead_code_candidates(
    file_df: pd.DataFrame, *, now_utc: datetime | None = None, stale_days: int = 180, min_churn: int = 10
) -> pd.DataFrame:
    """
    Heuristic: "dead-ish" files are stale (not touched recently) and low churn.
    """
    if file_df is None or file_df.empty:
        return pd.DataFrame()

    now_utc = now_utc or datetime.now(tz=timezone.utc)
    df = file_df.copy()
    df["age_days"] = df["last_touched"].apply(lambda d: math.inf if pd.isna(d) else (now_utc - d).days)
    return df[(df["age_days"] >= stale_days) & (df["churn"] <= min_churn)].sort_values(
        ["age_days", "commits"], ascending=[False, True]
    )


def repo_file_extensions(repo_path: Path) -> pd.DataFrame:
    """
    Basic extension counts for the visual "legend" feel.
    """
    exts: dict[str, int] = {}
    for p in repo_path.rglob("*"):
        if not p.is_file():
            continue
        if ".git" in p.parts:
            continue
        ext = p.suffix.lower().lstrip(".") or "(no ext)"
        exts[ext] = exts.get(ext, 0) + 1
    df = pd.DataFrame([{"ext": k, "count": v} for k, v in exts.items()])
    if df.empty:
        return df
    return df.sort_values("count", ascending=False).reset_index(drop=True)


