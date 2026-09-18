"""
Small layout helpers — KPI metrics and section headers for the ops console.
"""
import streamlit as st

_BADGE_COLORS = {
    "accent_blue": "blue",
    "accent_green": "green",
    "accent_amber": "orange",
    "accent_red": "red",
}


def metric_card(label, value, icon="", accent=None, suffix="", help_text=None):
    """Thin wrapper around ``st.metric`` (styled by ops CSS)."""
    st.metric(f"{icon} {label}".strip(), f"{value}{suffix}", help=help_text)


def info_card(title, body_markdown, icon=""):
    with st.container(border=True):
        st.markdown(f"**{icon} {title}**")
        st.markdown(body_markdown)


def section_header(title, subtitle=None, icon=""):
    st.markdown(f"## {icon} {title}" if icon else f"## {title}")
    if subtitle:
        st.caption(subtitle)


def pill(text, accent="accent_blue"):
    """Return a Markdown color-badge directive for inline use in ``st.markdown``."""
    color = _BADGE_COLORS.get(accent, "blue")
    return f":{color}-badge[{text}]"
