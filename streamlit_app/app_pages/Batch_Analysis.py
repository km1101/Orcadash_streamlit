"""Multiple Simulations — compare the same variable across several loaded .sim files."""
import pandas as pd
import streamlit as st

from components.cards import section_header
from components.charts import SERIES_SELECTOR_CAPTION, render_plotly_chart, series_multiselect, time_history_figure
from components.tables import download_button_for_df, styled_dataframe
from utils.cache import get_cached_model_summary
from utils.loaders import (
    ORCAFLEX_AVAILABLE,
    IMPORT_ERROR,
    calculate_statistics_summary,
    ensure_session_state,
    extract_time_history_multi_objects,
    get_variable_units,
    get_variables_for_object_types,
    record_variable_usage,
    variables_dict,
)

ensure_session_state()

section_header("Multiple Simulations", "Compare one variable side-by-side across several loaded files.", icon="📊")

if not ORCAFLEX_AVAILABLE:
    st.error(f"OrcFxAPI is not available in this environment ({IMPORT_ERROR}).")
    st.stop()

loaded = st.session_state.get("loaded_files", {})
if len(loaded) < 2:
    st.info("Load at least two files in **📂 Load Files** to compare simulations.")
    st.stop()

file_names = st.multiselect("Files to compare", list(loaded.keys()), default=list(loaded.keys())[:3])
if len(file_names) < 2:
    st.warning("Select at least two files.")
    st.stop()

object_type = st.selectbox("Object type", ["Line", "Vessel", "6DBuoy", "3DBuoy", "Winch", "Link"])

try:
    valid_variables = get_variables_for_object_types([object_type])
except Exception:
    valid_variables = None
if object_type == "Winch":
    # Dedicated category, same pattern as Environment* categories — a
    # Winch-only selection is scoped to just the "Winch" category.
    categories = [c for c in variables_dict.keys() if c == "Winch"]
else:
    categories = [c for c in variables_dict.keys() if not c.startswith("Environment") and c != "Winch"]
category = st.selectbox("Category", categories)
category_variables = list(variables_dict.get(category, {}).keys())
variable_options = (
    [v for v in category_variables if v in valid_variables] or category_variables
    if valid_variables else category_variables
)
variable_name = st.selectbox("Variable", variable_options) if variable_options else None

# --- Per-file object selection -----------------------------------------------
st.markdown("#### Object per file")
st.caption("Pick which object to extract from each file (names commonly differ across models).")
per_file_object = {}
cols = st.columns(len(file_names))
for col, fname in zip(cols, file_names):
    summary = get_cached_model_summary(loaded[fname])
    options = summary.get("objects", {}).get(object_type, [])
    with col:
        st.markdown(f"**{fname}**")
        per_file_object[fname] = st.selectbox(
            "Object", options or ["(none available)"], key=f"batch_obj_{fname}", label_visibility="collapsed"
        )

extract_clicked = st.button(
    "🔎 Extract & compare", type="primary",
    disabled=not variable_name or any(v == "(none available)" for v in per_file_object.values()),
)

if extract_clicked:
    progress = st.progress(0.0, text="Extracting from each file...")
    frames = {}
    for i, fname in enumerate(file_names):
        obj_name = per_file_object[fname]
        df = extract_time_history_multi_objects(loaded[fname], [obj_name], variable_name)
        if not df.empty:
            frames[f"{fname}::{obj_name}"] = df.rename(columns={obj_name: f"{fname}::{obj_name}"})
        progress.progress((i + 1) / len(file_names), text=f"Extracted {fname}")
    progress.empty()

    if not frames:
        st.warning("No data extracted.")
    else:
        merged = None
        for label, df in frames.items():
            merged = df if merged is None else pd.merge(merged, df, on="Time", how="outer")
        st.session_state["batch_result"] = {"df": merged.sort_values("Time"), "variable": variable_name}
        st.session_state["extraction_count"] = st.session_state.get("extraction_count", 0) + 1
        record_variable_usage(variable_name)

result = st.session_state.get("batch_result")
if result:
    df, active_variable = result["df"], result["variable"]
    units = get_variable_units(active_variable) or ""

    chart_df, _, _ = series_multiselect(
        df, {"Time"}, key="batch_series_th",
        help="Choose which files/objects appear in the chart, PNG download, and Report exports.",
    )
    st.caption(SERIES_SELECTOR_CAPTION)
    render_plotly_chart(time_history_figure(chart_df, active_variable, units))

    st.markdown("#### Comparison statistics")
    stats = calculate_statistics_summary(df, active_variable)
    styled_dataframe(stats)
    download_button_for_df(df, f"comparison_{active_variable}.csv".replace(" ", "_"))
