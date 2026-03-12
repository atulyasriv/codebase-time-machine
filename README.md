# Codebase Time Machine — GitHub Evolution Visualizer

A fancy dark-themed Streamlit app that visualizes **how a GitHub repo evolved over time**:

- Commit heatmaps (when the repo changes)
- Commit + churn timelines (adds/deletes, files changed)
- Interactive **force-directed “dependency” graph** via file co-changes (files that change together cluster)
- “Dead code” hints (stale files)
- Most complex Python modules (cyclomatic complexity via `radon`)

## Quickstart (Windows)

```powershell
cd "C:\Users\ATULYA SRIVASTAVA\Desktop\time machine"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## How the graph works

The main graph is a **co-change network**:

- **Nodes**: files
- **Edges**: two files modified in the same commit
- **Edge weight**: number of co-changes

This usually reveals natural module clusters even across multiple languages.

## Notes

- Repos are cloned to `.cache/repos/` and cached for speed.
- Private repos aren’t supported yet (no auth flow in this MVP).


