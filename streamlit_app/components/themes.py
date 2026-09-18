"""
Load and inject the ORCAFLEX Ops Console CSS into Streamlit.

Call ``inject_theme()`` once from ``app.py`` (and optionally from pages when
run in isolation) so the navy/ocean/sea-green design system is applied.
"""
from typing import Dict, List, Optional

import streamlit as st

from utils.config import APP_NAME, APP_TAGLINE, ASSETS_DIR

CSS_PATH = ASSETS_DIR / "css" / "orcaflex_ops.css"


def load_ops_css() -> str:
    if CSS_PATH.exists():
        return CSS_PATH.read_text(encoding="utf-8")
    return "/* orcaflex_ops.css missing */"


def inject_theme():
    """Inject ops CSS once per session rerun (cheap; Streamlit re-renders HTML)."""
    css = load_ops_css()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_ops_header(
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    meta: Optional[Dict] = None,
    status_text: str = "LOCAL",
    status_kind: str = "ok",
):
    """Render the navy ops header bar used at the top of workspace pages."""
    title = title or APP_NAME
    subtitle = subtitle or APP_TAGLINE
    meta = meta or {}

    meta_html = ""
    for label, value in meta.items():
        meta_html += (
            f'<div class="meta-item">'
            f'<span class="meta-label">{label}</span>'
            f'<span class="meta-value">{value}</span>'
            f"</div>"
        )

    st.markdown(
        f"""
        <div class="ops-header">
          <div class="ops-brand">
            <div class="ops-logo">OF</div>
            <div>
              <div class="ops-title">{title}</div>
              <div class="ops-subtitle">{subtitle}</div>
            </div>
          </div>
          <div class="ops-meta">
            {meta_html}
            <span class="status {status_kind}">{status_text}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_timeline(stages: List[dict], progress: Optional[float] = None):
    """
    Render a vertical processing status timeline.

    Each stage: ``{"label": str, "state": "done"|"active"|"pending", "sub": str?}``
    """
    items = []
    for stage in stages:
        state = stage.get("state", "pending")
        sub = stage.get("sub", "")
        sub_html = f'<div class="tl-sub">{sub}</div>' if sub else ""
        items.append(
            f'<div class="tl-item {state}">'
            f'<div class="tl-dot"></div>'
            f'<div><div class="tl-label">{stage["label"]}</div>{sub_html}</div>'
            f"</div>"
        )
    bar = ""
    if progress is not None:
        pct = max(0, min(100, int(progress * 100)))
        bar = (
            f'<div class="progress-track"><div class="progress-fill" '
            f'style="width:{pct}%"></div></div>'
            f'<div class="tl-sub" style="margin-top:0.25rem">{pct}%</div>'
        )
    st.markdown(
        f'<div class="timeline">{"".join(items)}{bar}</div>',
        unsafe_allow_html=True,
    )


def viz_placeholder(message: str = "Your results will appear here"):
    st.markdown(
        f"""
        <div class="viz-placeholder">
          <div>
            <div class="icon">📈</div>
            <div style="font-weight:700;color:var(--navy);margin-bottom:0.35rem;">{message}</div>
            <div class="faint">Configure selections above, then click <strong>Generate Results</strong>.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
