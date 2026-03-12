from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import git


_GITHUB_RE = re.compile(
    r"^(?:https?://)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)(?:\.git)?/?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RepoRef:
    owner: str
    repo: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}.git"


def parse_github_repo(url_or_slug: str) -> RepoRef:
    s = (url_or_slug or "").strip()
    if "/" in s and not s.lower().startswith("http"):
        owner, repo = s.split("/", 1)
        repo = repo.removesuffix(".git")
        return RepoRef(owner=owner.strip(), repo=repo.strip())

    m = _GITHUB_RE.match(s)
    if not m:
        raise ValueError("Please enter a GitHub URL or `owner/repo` (e.g. `pallets/flask`).")
    return RepoRef(owner=m.group("owner"), repo=m.group("repo"))


def get_cache_dir(project_root: Path) -> Path:
    d = project_root / ".cache" / "repos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def local_repo_path(project_root: Path, ref: RepoRef) -> Path:
    safe = f"{ref.owner}__{ref.repo}"
    return get_cache_dir(project_root) / safe


def ensure_local_repo(project_root: Path, ref: RepoRef, *, refresh: bool = False) -> Path:
    """
    Clone (or fetch) a repo into the local cache and return its path.
    """
    dest = local_repo_path(project_root, ref)
    if refresh and dest.exists():
        shutil.rmtree(dest, ignore_errors=True)

    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        git.Repo.clone_from(ref.url, str(dest), depth=0)
        return dest

    # fetch latest
    repo = git.Repo(str(dest))
    try:
        repo.remote().fetch(prune=True)
    except Exception:
        # network/offline etc — keep cached clone
        pass
    return dest


def open_repo(path: Path) -> git.Repo:
    return git.Repo(str(path))


def current_branch(repo: git.Repo) -> str:
    try:
        return repo.active_branch.name
    except Exception:
        return "HEAD"


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists() and os.path.isdir(path / ".git")


