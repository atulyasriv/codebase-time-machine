"""
Codebase TimeMachine — FastAPI Backend
Proxies real GitHub API data to the frontend.

Run:
    pip install fastapi uvicorn httpx python-dotenv
    python server.py

Optional: set GITHUB_TOKEN in .env for higher rate limits (5000 req/hr vs 60)
"""

import os
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Codebase TimeMachine API")

# Allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
BASE = "https://api.github.com"

def gh_headers():
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h

async def gh_get(client: httpx.AsyncClient, path: str, params: dict = None):
    """GET a GitHub API endpoint, return JSON or raise HTTPException."""
    r = await client.get(f"{BASE}{path}", headers=gh_headers(), params=params or {}, timeout=15)
    if r.status_code == 404:
        raise HTTPException(404, f"GitHub returned 404 for {path}")
    if r.status_code == 403:
        raise HTTPException(403, "GitHub rate limit hit. Set GITHUB_TOKEN in .env for 5000 req/hr.")
    if r.status_code == 202:
        # GitHub is computing stats — return empty, frontend will retry
        return None
    r.raise_for_status()
    return r.json()


@app.get("/api/repo/{owner}/{repo}")
async def get_repo_data(owner: str, repo: str):
    """
    Fetch ALL data for one repo in parallel:
      - repo metadata (stars, forks, description, language, created_at)
      - commit activity (52-week heatmap)
      - contributors (top 10)
      - languages breakdown
      - recent commits (last 10)
      - weekly addition/deletion stats
    """
    async with httpx.AsyncClient() as client:
        # Fire all requests in parallel
        results = await asyncio.gather(
            gh_get(client, f"/repos/{owner}/{repo}"),
            gh_get(client, f"/repos/{owner}/{repo}/stats/commit_activity"),
            gh_get(client, f"/repos/{owner}/{repo}/contributors", {"per_page": "10", "anon": "false"}),
            gh_get(client, f"/repos/{owner}/{repo}/languages"),
            gh_get(client, f"/repos/{owner}/{repo}/commits", {"per_page": "10"}),
            gh_get(client, f"/repos/{owner}/{repo}/stats/code_frequency"),
            return_exceptions=True,
        )

    meta, commit_activity, contributors, languages, recent_commits, code_freq = results

    # Handle any individual failures gracefully
    def safe(val, default):
        return default if (val is None or isinstance(val, Exception)) else val

    meta = safe(meta, {})
    commit_activity = safe(commit_activity, [])
    contributors = safe(contributors, [])
    languages = safe(languages, {})
    recent_commits = safe(recent_commits, [])
    code_freq = safe(code_freq, [])

    if not meta:
        raise HTTPException(404, f"Repository {owner}/{repo} not found.")

    # ---- Process commit heatmap (52 weeks × 7 days) ----
    heatmap = []
    for week in (commit_activity or []):
        heatmap.append({
            "week": week.get("week", 0),
            "days": week.get("days", [0]*7),
            "total": week.get("total", 0),
        })

    # ---- Process contributors ----
    top_contributors = []
    total_contribs = sum(c.get("contributions", 0) for c in (contributors or []) if isinstance(c, dict))
    for c in (contributors or []):
        if not isinstance(c, dict): continue
        top_contributors.append({
            "login": c.get("login", "unknown"),
            "avatar": c.get("avatar_url", ""),
            "contributions": c.get("contributions", 0),
            "pct": round(c["contributions"] / total_contribs * 100, 1) if total_contribs else 0,
            "url": c.get("html_url", ""),
        })

    # ---- Process languages ----
    lang_total = sum(languages.values()) if languages else 1
    lang_list = [
        {"name": lang, "bytes": bytes_, "pct": round(bytes_ / lang_total * 100, 1)}
        for lang, bytes_ in sorted(languages.items(), key=lambda x: -x[1])
    ] if languages else []

    # Language colors (common ones)
    LANG_COLORS = {
        "JavaScript": "#f7df1e", "TypeScript": "#3178c6", "Python": "#3572A5",
        "Go": "#00ADD8", "Rust": "#dea584", "C": "#555599", "C++": "#f34b7d",
        "Java": "#b07219", "Kotlin": "#A97BFF", "Ruby": "#701516",
        "PHP": "#4F5D95", "Swift": "#F05138", "Scala": "#c22d40",
        "Shell": "#89e051", "HTML": "#e34c26", "CSS": "#563d7c",
        "Makefile": "#427819", "Dockerfile": "#384d54", "Vue": "#41b883",
        "Svelte": "#ff3e00", "Dart": "#00B4AB", "Elixir": "#6e4a7e",
        "Haskell": "#5e5086", "Lua": "#000080", "R": "#198CE7",
        "MATLAB": "#e16737", "Jupyter Notebook": "#DA5B0B",
    }
    for lang in lang_list:
        lang["color"] = LANG_COLORS.get(lang["name"], "#888888")

    # ---- Process recent commits ----
    commits_out = []
    COMMIT_EMOJIS = {"feat": "✨", "fix": "🐛", "refactor": "♻️", "docs": "📝",
                     "perf": "⚡", "test": "🧪", "chore": "🔧", "style": "🎨",
                     "ci": "⚙️", "build": "🏗️", "revert": "⏪", "security": "🔒"}
    for c in (recent_commits or []):
        if not isinstance(c, dict): continue
        msg = (c.get("commit", {}).get("message", "") or "").split("\n")[0]
        prefix = msg.split(":")[0].lower().strip() if ":" in msg else ""
        emoji = COMMIT_EMOJIS.get(prefix, "📝")
        author = (c.get("author") or {}).get("login") or \
                 (c.get("commit", {}).get("author") or {}).get("name", "unknown")
        date_str = (c.get("commit", {}).get("author") or {}).get("date", "")
        commits_out.append({
            "hash": (c.get("sha") or "")[:7],
            "msg": msg[:80],
            "author": author,
            "date": date_str,
            "emoji": emoji,
            "url": c.get("html_url", ""),
        })

    # ---- Process code frequency (monthly additions/deletions) ----
    monthly = {}
    for entry in (code_freq or []):
        if not isinstance(entry, (list, tuple)) or len(entry) < 3: continue
        import datetime
        try:
            dt = datetime.datetime.utcfromtimestamp(entry[0])
            key = f"{dt.year}-{dt.month:02d}"
            if key not in monthly:
                monthly[key] = {"adds": 0, "dels": 0}
            monthly[key]["adds"] += entry[1]
            monthly[key]["dels"] += abs(entry[2])
        except Exception:
            continue
    # Last 12 months
    import datetime
    now = datetime.datetime.utcnow()
    month_labels, month_adds, month_dels = [], [], []
    for i in range(11, -1, -1):
        dt = now.replace(day=1) - datetime.timedelta(days=i*28)
        key = f"{dt.year}-{dt.month:02d}"
        label = dt.strftime("%b")
        month_labels.append(label)
        month_adds.append(monthly.get(key, {}).get("adds", 0))
        month_dels.append(-monthly.get(key, {}).get("dels", 0))

    # ---- Total commits (from repo stats) ----
    total_commits_approx = sum(
        sum(w.get("days", [])) for w in (commit_activity or []) if isinstance(w, dict)
    )
    # GitHub only returns 52 weeks in commit_activity; for full count use contributor sum
    contrib_total = sum(c.get("contributions", 0) for c in (contributors or []) if isinstance(c, dict))

    return {
        "meta": {
            "full_name": meta.get("full_name", f"{owner}/{repo}"),
            "description": meta.get("description") or "No description",
            "stars": meta.get("stargazers_count", 0),
            "forks": meta.get("forks_count", 0),
            "open_issues": meta.get("open_issues_count", 0),
            "language": meta.get("language") or "Unknown",
            "created_at": meta.get("created_at", ""),
            "updated_at": meta.get("updated_at", ""),
            "default_branch": meta.get("default_branch", "main"),
            "size_kb": meta.get("size", 0),
            "topics": meta.get("topics", []),
            "url": meta.get("html_url", ""),
            "owner_avatar": (meta.get("owner") or {}).get("avatar_url", ""),
        },
        "stats": {
            "commits_last_year": total_commits_approx,
            "contributors_shown": len(top_contributors),
            "total_contributor_commits": contrib_total,
            "languages_count": len(lang_list),
            "size_kb": meta.get("size", 0),
        },
        "heatmap": heatmap,
        "contributors": top_contributors,
        "languages": lang_list,
        "recent_commits": commits_out,
        "activity": {
            "labels": month_labels,
            "additions": month_adds,
            "deletions": month_dels,
        },
    }


@app.get("/api/health")
async def health():
    token_set = bool(GITHUB_TOKEN)
    return {"status": "ok", "github_token": token_set,
            "rate_limit": "5000/hr" if token_set else "60/hr (set GITHUB_TOKEN for more)"}


# Serve the frontend HTML at root
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Codebase TimeMachine server starting...")
    print("📡 API:      http://localhost:8000/api/repo/{owner}/{repo}")
    print("🌐 Frontend: http://localhost:8000")
    print("💡 Tip: Add GITHUB_TOKEN=your_token to .env for 5000 req/hr\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
