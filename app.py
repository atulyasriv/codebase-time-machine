from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.analyze import (
    cochange_graph,
    commit_table,
    dead_code_candidates,
    file_churn_table,
    repo_file_extensions,
)
from src.complexity import python_complexity
from src.git_repo import ensure_local_repo, open_repo, parse_github_repo
from src.ui import inject_global_css, metric_card, page_header
from src.viz import (
    plot_commit_heatmap,
    plot_commit_timeline,
    plot_daily_commits,
    plot_extension_bar,
    pyvis_force_graph_html,
)


PROJECT_ROOT = Path(__file__).resolve().parent


st.set_page_config(
    page_title="Codebase Time Machine",
    page_icon="🕰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
page_header()


@st.cache_resource(show_spinner=False)
def _get_repo_path(repo_input: str, refresh: bool) -> Path:
    ref = parse_github_repo(repo_input)
    return ensure_local_repo(PROJECT_ROOT, ref, refresh=refresh)


@st.cache_data(show_spinner=False)
def _analyze(repo_path_str: str, max_commits: int, min_edge_weight: int):
    repo_path = Path(repo_path_str)
    repo = open_repo(repo_path)
    commits_df = commit_table(repo, max_count=max_commits)
    churn_df = file_churn_table(repo, max_count=max_commits)
    g = cochange_graph(repo, max_count=max_commits, min_edge_weight=min_edge_weight)
    ext_df = repo_file_extensions(repo_path)
    dead_df = dead_code_candidates(churn_df, now_utc=datetime.now(tz=timezone.utc))
    cx_df = python_complexity(repo_path)
    return commits_df, churn_df, g, ext_df, dead_df, cx_df


with st.sidebar:
    st.markdown("### Controls")
    repo_input = st.text_input("GitHub repo URL or `owner/repo`", value="pallets/flask")
    colA, colB = st.columns(2)
    with colA:
        max_commits = st.slider("Commits", 200, 5000, 1500, step=100)
    with colB:
        min_edge_weight = st.slider("Graph min co-change", 1, 12, 2, step=1)

    refresh = st.checkbox("Refresh clone (re-download)", value=False)
    run = st.button("Analyze repo", use_container_width=True)

    st.markdown(
        """
<div style="margin-top:10px; color:rgba(230,234,242,0.68); font-size:12px;">
Tip: start with ~1500 commits for big repos. Raise "min co-change" to declutter the graph.
</div>
        """,
        unsafe_allow_html=True,
    )


if not run:
    st.markdown(
        """
<div style="margin-top:16px;" class="tm-card">
  <div style="font-weight:750; font-size:16px;">Drop in a repo and hit <span style="color:#A78BFA;">Analyze</span>.</div>
  <div style="color:rgba(230,234,242,0.70); margin-top:6px;">
    You’ll get a commit heatmap, churn timeline, a clustered force graph, plus dead-code & complexity hints.
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


try:
    repo_path = _get_repo_path(repo_input, refresh)
except Exception as e:
    st.error(str(e))
    st.stop()


with st.spinner("Crunching history… (commits, churn, graph, complexity)"):
    commits_df, churn_df, g, ext_df, dead_df, cx_df = _analyze(str(repo_path), max_commits, min_edge_weight)


top = st.columns([1, 1, 1, 1])
with top[0]:
    metric_card("Repo path (cached)", f"{repo_path.name}", repo_path.as_posix())
with top[1]:
    metric_card("Commits analyzed", f"{len(commits_df):,}", f"max={max_commits:,}")
with top[2]:
    metric_card("Files seen", f"{len(churn_df):,}" if churn_df is not None else "0", "across analyzed commits")
with top[3]:
    metric_card("Graph nodes / edges", f"{g.number_of_nodes():,} / {g.number_of_edges():,}", f"min co-change={min_edge_weight}")


tab1, tab2, tab3, tab4 = st.tabs(["Evolution", "Force Graph", "Files", "Quality signals"])

with tab1:
    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        st.markdown("#### Commit churn over time")
        st.plotly_chart(plot_commit_timeline(commits_df), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        st.markdown("#### Commit activity heatmap")
        st.plotly_chart(plot_commit_heatmap(commits_df), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="tm-card" style="margin-top:14px;">', unsafe_allow_html=True)
    st.markdown("#### Daily commits + additions/deletions")
    st.plotly_chart(plot_daily_commits(commits_df), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown(
        """
<div class="tm-card">
  <div style="display:flex; align-items:flex-end; justify-content:space-between; gap:10px;">
    <div>
      <div style="font-size:18px; font-weight:800;">Co-change Force Graph</div>
      <div style="color:rgba(230,234,242,0.70); margin-top:4px;">
        Files that change together cluster. Drag nodes, scroll to zoom, hover for full paths.
      </div>
    </div>
    <div style="color:rgba(230,234,242,0.60); font-size:12px;">
      Tip: increase <b>min co-change</b> to reduce edges.
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    if g.number_of_nodes() == 0:
        st.info("Graph is empty at current thresholds. Try lowering **min co-change** or increasing **commits**.")
    else:
        html = pyvis_force_graph_html(g, height_px=620)
        components.html(html, height=640, scrolling=False)

with tab3:
    left, right = st.columns([0.9, 1.1])
    with left:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        st.markdown("#### File types (top)")
        st.plotly_chart(plot_extension_bar(ext_df), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        st.markdown("#### Top churn files")
        show_cols = ["path", "commits", "insertions", "deletions", "churn", "last_touched"]
        st.dataframe(churn_df[show_cols].head(40), use_container_width=True, height=360)
        st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    q1, q2 = st.columns(2)
    with q1:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        st.markdown("#### Dead code candidates (heuristic)")
        st.caption("Stale + low churn. Not a proof — just a shortlist.")
        if dead_df is None or dead_df.empty:
            st.write("Nothing flagged with current thresholds.")
        else:
            st.dataframe(dead_df[["path", "age_days", "commits", "churn", "last_touched"]].head(40), use_container_width=True, height=360)
        st.markdown("</div>", unsafe_allow_html=True)

    with q2:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        st.markdown("#### Most complex Python files (radon CC)")
        st.caption("Only Python files are scored in this MVP.")
        if cx_df is None or cx_df.empty:
            st.write("No Python complexity data found.")
        else:
            st.dataframe(cx_df, use_container_width=True, height=360)
        st.markdown("</div>", unsafe_allow_html=True)


