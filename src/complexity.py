from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from radon.complexity import cc_visit


@dataclass(frozen=True)
class ComplexityRow:
    path: str
    avg_cc: float
    max_cc: float
    blocks: int


def python_complexity(repo_path: Path, *, top_n: int = 30) -> pd.DataFrame:
    """
    Cyclomatic complexity for Python files (radon CC).
    """
    rows: list[ComplexityRow] = []
    for p in repo_path.rglob("*.py"):
        if ".git" in p.parts:
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        try:
            blocks = cc_visit(src)
        except Exception:
            continue
        if not blocks:
            continue
        ccs = [float(b.complexity) for b in blocks if getattr(b, "complexity", None) is not None]
        if not ccs:
            continue
        rows.append(
            ComplexityRow(
                path=str(p.relative_to(repo_path)).replace("\\", "/"),
                avg_cc=sum(ccs) / len(ccs),
                max_cc=max(ccs),
                blocks=len(ccs),
            )
        )

    df = pd.DataFrame([r.__dict__ for r in rows])
    if df.empty:
        return df
    return df.sort_values(["max_cc", "avg_cc", "blocks"], ascending=[False, False, False]).head(top_n).reset_index(
        drop=True
    )


