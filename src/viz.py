from __future__ import annotations

import math
from datetime import date

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pyvis.network import Network


def plot_commit_timeline(commit_df: pd.DataFrame) -> go.Figure:
    df = commit_df.copy()
    df["net"] = df["insertions"] - df["deletions"]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["authored_dt"],
            y=df["insertions"],
            name="Additions",
            marker_color="rgba(34,197,94,0.70)",
        )
    )
    fig.add_trace(
        go.Bar(
            x=df["authored_dt"],
            y=[-v for v in df["deletions"]],
            name="Deletions",
            marker_color="rgba(239,68,68,0.65)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["authored_dt"],
            y=df["files_changed"],
            mode="lines",
            name="Files changed",
            line=dict(color="rgba(124,58,237,0.9)", width=2),
            yaxis="y2",
        )
    )
    fig.update_layout(
        barmode="relative",
        template="plotly_dark",
        height=360,
        margin=dict(l=10, r=10, t=25, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(title="Churn (lines)"),
        yaxis2=dict(title="Files", overlaying="y", side="right", showgrid=False),
    )
    return fig


def plot_commit_heatmap(commit_df: pd.DataFrame) -> go.Figure:
    """
    Day-of-week vs hour-of-day heatmap.
    """
    df = commit_df.copy()
    if df.empty:
        return go.Figure()
    pivot = df.pivot_table(index="dow", columns="hour", values="sha", aggfunc="count", fill_value=0)
    pivot = pivot.reindex([0, 1, 2, 3, 4, 5, 6])
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    z = pivot.values
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=list(range(24)),
            y=[dow_names[i] for i in range(7)],
            colorscale=[
                [0.0, "rgba(8,10,18,1)"],
                [0.2, "rgba(124,58,237,0.35)"],
                [0.55, "rgba(6,182,212,0.50)"],
                [1.0, "rgba(236,72,153,0.85)"],
            ],
            hovertemplate="Day=%{y}<br>Hour=%{x}:00<br>Commits=%{z}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Hour of day", tickmode="linear", dtick=2),
        yaxis=dict(title="Day of week"),
    )
    return fig


def plot_extension_bar(ext_df: pd.DataFrame, *, top_n: int = 12) -> go.Figure:
    if ext_df is None or ext_df.empty:
        return go.Figure()
    df = ext_df.head(top_n).copy()
    fig = px.bar(df, x="count", y="ext", orientation="h", template="plotly_dark")
    fig.update_traces(marker_color="rgba(148,163,184,0.7)")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="", xaxis_title="Files")
    return fig


def _size_from_degree(deg: int) -> int:
    return int(max(10, min(46, 10 + 6 * math.log2(deg + 1))))


def pyvis_force_graph_html(g: nx.Graph, *, height_px: int = 560) -> str:
    """
    Render a force graph (dark) to HTML using pyvis.
    """
    net = Network(height=f"{height_px}px", width="100%", bgcolor="#050711", font_color="#E6EAF2", directed=False)
    net.barnes_hut(gravity=-12000, central_gravity=0.18, spring_length=140, spring_strength=0.03, damping=0.15)

    degrees = dict(g.degree())
    max_w = max((int(d.get("weight", 1)) for _, _, d in g.edges(data=True)), default=1)

    def edge_color(w: int) -> str:
        t = min(1.0, max(0.0, w / max_w))
        # purple -> cyan -> pink
        if t < 0.5:
            return "rgba(124,58,237,0.55)"
        if t < 0.85:
            return "rgba(6,182,212,0.55)"
        return "rgba(236,72,153,0.60)"

    for n in g.nodes():
        deg = int(degrees.get(n, 0))
        net.add_node(
            n,
            label=n.split("/")[-1],
            title=n,
            size=_size_from_degree(deg),
            color="rgba(148,163,184,0.85)",
        )

    for u, v, d in g.edges(data=True):
        w = int(d.get("weight", 1))
        net.add_edge(
            u,
            v,
            value=w,
            title=f"Co-changes: {w}",
            color=edge_color(w),
            width=1 + min(8, w),
        )

    # Tune visuals and interactions
    net.set_options(
        """
var options = {
  "nodes": {
    "borderWidth": 0,
    "font": {"size": 14, "face": "Inter, Segoe UI, Arial"},
    "shadow": {"enabled": true, "color": "rgba(0,0,0,0.45)", "size": 14, "x": 0, "y": 4}
  },
  "edges": {
    "smooth": {"enabled": true, "type": "dynamic"},
    "shadow": {"enabled": false},
    "selectionWidth": 2
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 120,
    "hideEdgesOnDrag": true
  },
  "physics": {
    "enabled": true,
    "stabilization": {"enabled": true, "iterations": 250}
  }
}
        """
    )
    return net.generate_html()


def plot_daily_commits(commit_df: pd.DataFrame) -> go.Figure:
    if commit_df is None or commit_df.empty:
        return go.Figure()
    df = commit_df.groupby("date", as_index=False).agg(commits=("sha", "count"), insertions=("insertions", "sum"), deletions=("deletions", "sum"))
    df["date"] = df["date"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["commits"], mode="lines", name="Commits", line=dict(color="rgba(250,204,21,0.9)", width=2)))
    fig.add_trace(go.Bar(x=df["date"], y=df["insertions"], name="Additions", marker_color="rgba(34,197,94,0.55)"))
    fig.add_trace(go.Bar(x=df["date"], y=df["deletions"], name="Deletions", marker_color="rgba(239,68,68,0.50)"))
    fig.update_layout(
        barmode="overlay",
        template="plotly_dark",
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(title="Day", type="category", showgrid=False),
    )
    return fig


