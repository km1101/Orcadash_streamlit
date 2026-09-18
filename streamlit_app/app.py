"""
App shell: page config, ops theme injection, and left-sidebar navigation.

Individual pages live under ``app_pages/`` and are wired up here via
``st.Page``/``st.navigation`` so the sidebar can carry the wireframe labels
(Dashboard, Results, Comparisons, Reports, Settings, Help, About).
"""
import streamlit as st

from components.sidebar import (
    inject_sidebar_collapse_css,
    is_sidebar_collapsed,
    render_sidebar_branding,
    render_sidebar_footer,
)
from components.themes import inject_theme
from utils.config import APP_DIR, APP_ICON, APP_NAME, NAV_STRUCTURE
from utils.loaders import ensure_session_state

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_session_state()
inject_theme()
inject_sidebar_collapse_css()
render_sidebar_branding()

# When the rail is collapsed, keep icons and shorten titles so the narrow
# sidebar still matches the wireframe icon-only look.
collapsed = is_sidebar_collapsed()

sections = {}
for section in NAV_STRUCTURE:
    # Hide Tools section in the collapsed rail (still available when expanded)
    if collapsed and section["section"] == "Tools":
        continue
    sections[section["section"]] = [
        st.Page(
            str(APP_DIR / p["file"]),
            # Keep a non-empty title for Streamlit; CSS clips labels in the rail
            title=p["title"],
            icon=p["icon"],
            default=p.get("default", False),
        )
        for p in section["pages"]
    ]

pg = st.navigation(sections)
render_sidebar_footer()
pg.run()
