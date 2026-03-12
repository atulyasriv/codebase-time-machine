from __future__ import annotations

import streamlit as st


def inject_global_css() -> None:
    st.markdown(
        """
<style>
/* ---------- App background + typography ---------- */
html, body, [class*="css"]  {
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Inter, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif;
}

.stApp {
  background:
    radial-gradient(1200px 800px at 20% 10%, rgba(124,58,237,0.20), rgba(0,0,0,0) 55%),
    radial-gradient(1000px 650px at 80% 20%, rgba(6,182,212,0.14), rgba(0,0,0,0) 60%),
    radial-gradient(900px 700px at 50% 100%, rgba(236,72,153,0.10), rgba(0,0,0,0) 60%),
    linear-gradient(180deg, #050711 0%, #070A12 60%, #060714 100%);
}

/* ---------- Top padding + overall spacing ---------- */
.block-container {
  padding-top: 2.25rem;
  padding-bottom: 2.25rem;
  max-width: 1200px;
}

/* ---------- Glass cards ---------- */
.tm-card {
  background: rgba(11, 18, 32, 0.66);
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 16px 40px rgba(0,0,0,0.45);
  border-radius: 18px;
  padding: 18px 18px;
  backdrop-filter: blur(10px);
}

.tm-metric {
  display: grid;
  gap: 2px;
}
.tm-metric .k { color: rgba(230,234,242,0.72); font-size: 12px; text-transform: uppercase; letter-spacing: .06em;}
.tm-metric .v { font-size: 20px; font-weight: 650; }
.tm-metric .s { color: rgba(230,234,242,0.62); font-size: 12px; }

/* ---------- Buttons ---------- */
div.stButton > button {
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.14);
  background: linear-gradient(135deg, rgba(124,58,237,0.95), rgba(6,182,212,0.65));
  color: #0B1020;
  font-weight: 700;
  padding: 0.6rem 0.95rem;
  box-shadow: 0 10px 26px rgba(124,58,237,0.22);
}
div.stButton > button:hover {
  filter: brightness(1.05);
  transform: translateY(-1px);
}

/* ---------- Inputs ---------- */
div[data-baseweb="input"] > div {
  border-radius: 12px !important;
  background: rgba(9, 14, 26, 0.75) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
}

/* ---------- Tabs ---------- */
button[role="tab"] {
  border-radius: 999px !important;
  padding: 8px 14px !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  background: rgba(11,18,32,0.45) !important;
}
button[role="tab"][aria-selected="true"] {
  background: rgba(124,58,237,0.22) !important;
  border: 1px solid rgba(124,58,237,0.30) !important;
}

/* ---------- Hide Streamlit default stuff a bit ---------- */
header { visibility: hidden; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

</style>
        """,
        unsafe_allow_html=True,
    )


def page_header() -> None:
    st.markdown(
        """
<div class="tm-card">
  <div style="display:flex; align-items:center; justify-content:space-between; gap:16px;">
    <div>
      <div style="font-size:28px; font-weight:800; letter-spacing:-0.02em;">
        Codebase Time Machine
      </div>
      <div style="color:rgba(230,234,242,0.70); margin-top:2px;">
        Visualize how a GitHub repo evolves — commits, churn, clusters, complexity.
      </div>
    </div>
    <div style="padding:10px 12px; border-radius:14px; border:1px solid rgba(255,255,255,0.10);
                background:rgba(0,0,0,0.20);">
      <div style="font-size:12px; color:rgba(230,234,242,0.72); text-transform:uppercase; letter-spacing:.08em;">
        Mode
      </div>
      <div style="font-weight:800;">Dark / Neon</div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, sub: str | None = None) -> None:
    st.markdown(
        f"""
<div class="tm-card">
  <div class="tm-metric">
    <div class="k">{label}</div>
    <div class="v">{value}</div>
    <div class="s">{sub or ""}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


