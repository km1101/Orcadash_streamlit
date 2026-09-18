"""Settings — cache management, session reset, and environment diagnostics."""
import shutil

import streamlit as st

from components.cards import info_card, section_header
from components.themes import render_ops_header
from utils.config import EXPORT_DIR, STATE_DIR, UPLOAD_DIR
from utils.loaders import ORCAFLEX_AVAILABLE, IMPORT_ERROR, ensure_session_state

ensure_session_state()

render_ops_header(
    title="Settings",
    subtitle="Cache, session, and environment",
    meta={"Workspace": "Local"},
    status_text="CONFIG",
    status_kind="ok",
)

section_header("Settings", "Cache, session state, and environment diagnostics.", icon="⚙️")

# --- Environment status -----------------------------------------------------
st.markdown("#### Environment")
if ORCAFLEX_AVAILABLE:
    st.success("OrcFxAPI detected — extractions will run against your local OrcaFlex license.")
else:
    st.error(f"OrcFxAPI is not available: {IMPORT_ERROR}")
    st.caption("This page (and every analysis page) still loads, but extraction is disabled without a licensed OrcaFlex install.")

st.write("")

# --- Cache management ----------------------------------------------------------
st.markdown("#### Cache & session")
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🧹 Clear computation cache"):
        st.cache_data.clear()
        st.success("Cleared cached model summaries and computed results.")
with c2:
    if st.button("🔁 Reset session (loaded files)"):
        st.session_state["loaded_files"] = {}
        st.session_state["active_file"] = None
        st.session_state["last_extracted"] = {}
        st.session_state["dash_selected_keys"] = []
        st.session_state["dash_result"] = {}
        st.session_state["dash_process_stage"] = 0
        st.session_state["dash_process_progress"] = 0.0
        st.session_state.pop("batch_result", None)
        st.session_state.pop("last_range_graph", None)
        st.success("Session state reset. Persisted history (recent files, favorites, notes) is untouched.")
with c3:
    if st.button("🗑️ Delete uploaded file copies"):
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        st.success("Removed locally-cached copies of uploaded files.")

st.write("")
info_card(
    "About persisted state",
    f"Recent files, favorites, notes, and export history are stored as small JSON files under "
    f"`{STATE_DIR}`. Deleting that folder resets the app to a clean slate. Exported "
    f"reports/CSVs are saved under `{EXPORT_DIR}`.",
    icon="💾",
)

st.write("")
info_card(
    "Appearance",
    "This app injects the **ORCAFLEX Ops Console** light theme (navy / ocean / sea-green). "
    "Streamlit's own theme picker can still override some chrome; prefer keeping the "
    "browser/app theme on Light for the intended engineering-console look.",
    icon="🎨",
)
