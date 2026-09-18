"""About — product identity for the ORCAFLEX ops console."""
import streamlit as st

from components.themes import render_ops_header
from utils.config import APP_NAME, APP_TAGLINE
from utils.loaders import ORCAFLEX_AVAILABLE, ensure_session_state

ensure_session_state()

render_ops_header(
    title="About",
    subtitle=APP_TAGLINE,
    meta={"Product": "Ops Console"},
    status_text="INFO",
    status_kind="ok",
)

st.markdown(
    f"""
<div class="panel">
  <h2>{APP_NAME}</h2>
  <p class="muted">
    A local engineering dashboard for post-processing OrcaFlex <code>.sim</code> results.
    The Dashboard follows a numbered 1–7 workflow from file load through object selection,
    variable configuration, and interactive visualization — styled as a light ops console
    (navy / ocean / sea-green) rather than a generic Streamlit demo.
  </p>
  <p class="muted">
    Extraction logic lives in <code>backend/var_and_func</code>, so time
    history, statistics, histogram, PSD, and range-graph helpers stay
    consistent across pages.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

api_state = "Available" if ORCAFLEX_AVAILABLE else "Not detected on this machine"
st.markdown(
    f"""
<div class="panel">
  <h2>Environment</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="label">OrcFxAPI</div><div class="value" style="font-size:1rem;">{api_state}</div></div>
    <div class="kpi"><div class="label">UI shell</div><div class="value" style="font-size:1rem;">Streamlit</div></div>
    <div class="kpi"><div class="label">Charts</div><div class="value" style="font-size:1rem;">Plotly</div></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="ops-footer">Built for offshore / marine engineers working with OrcaFlex simulation results.</div>
""",
    unsafe_allow_html=True,
)
