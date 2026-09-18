"""
Sidebar chrome: branding, collapsible rail, and session-status footer.

Uses Streamlit's native ``st.navigation`` for page links, plus a session_state
collapse toggle and CSS width tricks so the left rail matches the wireframe
(expanded labels vs. icon-only narrow rail).
"""
import streamlit as st

from utils.config import APP_NAME, APP_TAGLINE, BRAND_SHORT, LOGO_PATH
from utils.loaders import ORCAFLEX_AVAILABLE, is_streamlit_community_cloud

_COLLAPSE_KEY = "sidebar_collapsed"


def _ensure_collapse_state():
    st.session_state.setdefault(_COLLAPSE_KEY, False)


def is_sidebar_collapsed() -> bool:
    _ensure_collapse_state()
    return bool(st.session_state.get(_COLLAPSE_KEY, False))


def inject_sidebar_collapse_css():
    """Apply body class so CSS can shrink the sidebar to an icon rail."""
    _ensure_collapse_state()
    collapsed = is_sidebar_collapsed()
    # Toggle a body class without fighting Streamlit's own sidebar collapse.
    flag = "true" if collapsed else "false"
    st.markdown(
        f"""
        <script>
        (function () {{
          const root = window.parent.document;
          if (!root || !root.body) return;
          if ({flag}) {{
            root.body.classList.add("ops-sidebar-collapsed");
          }} else {{
            root.body.classList.remove("ops-sidebar-collapsed");
          }}
        }})();
        </script>
        <style>
        /* Fallback width rules keyed off a marker element Streamlit keeps in-page */
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Also inject a durable CSS block that does not rely solely on JS class timing
    if collapsed:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {
              min-width: 4.75rem !important;
              max-width: 4.75rem !important;
              width: 4.75rem !important;
            }
            [data-testid="stSidebar"] > div:first-child {
              width: 4.75rem !important;
            }
            .ops-sidebar-brand { justify-content: center !important; padding: 0.55rem 0.35rem 0.7rem !important; }
            .ops-sidebar-brand-text,
            .ops-sidebar-status { display: none !important; }
            [data-testid="stSidebarNav"] a {
              margin: 0.2rem 0.35rem !important;
              justify-content: center !important;
              padding-left: 0.35rem !important;
              padding-right: 0.35rem !important;
              border-left-width: 0 !important;
              overflow: hidden !important;
              white-space: nowrap !important;
              font-size: 1.15rem !important;
            }
            [data-testid="stSidebarNav"] span[data-testid="stIconMaterial"],
            [data-testid="stSidebarNav"] a > span:first-child {
              display: inline-flex !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar_branding():
    _ensure_collapse_state()
    collapsed = is_sidebar_collapsed()
    with st.sidebar:
        if LOGO_PATH.exists() and not collapsed:
            st.logo(str(LOGO_PATH), icon_image=str(LOGO_PATH))
        elif LOGO_PATH.exists() and collapsed:
            # Compact mark only — logo still helps brand recognition in the rail
            st.logo(str(LOGO_PATH), icon_image=str(LOGO_PATH))

        brand_text_display = "none" if collapsed else "block"
        st.markdown(
            f"""
            <div class="ops-sidebar-brand">
              <div class="ops-sidebar-mark">OF</div>
              <div class="ops-sidebar-brand-text" style="display:{brand_text_display};">
                <div class="brand">{BRAND_SHORT}</div>
                <div class="name">{APP_NAME}</div>
                <div class="tag">{APP_TAGLINE}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar_footer():
    """Session status + wireframe Collapse / Expand control."""
    _ensure_collapse_state()
    collapsed = is_sidebar_collapsed()
    loaded = st.session_state.get("loaded_files", {})
    selected = st.session_state.get("dash_selected_keys", [])
    if ORCAFLEX_AVAILABLE:
        api_label = "OrcFxAPI ready"
    elif is_streamlit_community_cloud():
        api_label = "Public demo"
    else:
        api_label = "OrcFxAPI offline"

    with st.sidebar:
        st.markdown("---")
        if not collapsed:
            st.markdown(
                f'<div class="ops-sidebar-status">'
                f"📁 {len(loaded)} file(s) · ✅ {len(selected)} object(s)<br/>{api_label}"
                f"</div>",
                unsafe_allow_html=True,
            )

        label = ">> Expand" if collapsed else "<< Collapse"
        help_txt = "Expand navigation labels" if collapsed else "Collapse to icon-only rail"
        st.markdown('<div class="ops-collapse-wrap">', unsafe_allow_html=True)
        if st.button(label, key="ops_sidebar_collapse", help=help_txt, width="stretch"):
            st.session_state[_COLLAPSE_KEY] = not collapsed
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
