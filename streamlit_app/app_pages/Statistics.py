"""Statistics — deep statistical summary for the most recent extraction.

Reuses the extraction made on Single Simulation (session_state["last_extracted"])
so you don't have to re-select file/object/variable; falls back to its own
mini filter panel if nothing has been extracted yet this session.
"""
import streamlit as st

from components.cards import metric_card, section_header
from components.charts import histogram_figure, render_plotly_chart
from components.filters import file_selector, object_selector, variable_selector
from components.tables import download_button_for_df, styled_dataframe
from utils.loaders import (
    ORCAFLEX_AVAILABLE,
    show_orcaflex_unavailable_banner,
    calculate_statistics_summary,
    compute_extended_statistics_summary,
    ensure_session_state,
    extract_time_history_multi_objects,
    get_variable_units,
)

ensure_session_state()

section_header("Statistics", "Descriptive and distribution-shape statistics for the active dataset.", icon="📋")

if not ORCAFLEX_AVAILABLE:
    show_orcaflex_unavailable_banner()
    st.stop()

state = st.session_state.get("last_extracted", {})
df, active_variable = state.get("df"), state.get("variable")

if df is None or df.empty:
    st.info("No extraction yet this session — pick a file/object/variable below, or run one from **Single Simulation**.")
    with st.expander("Quick extraction", expanded=True):
        _, file_path = file_selector(container=st, key_prefix="stats_")
        if file_path:
            object_type, object_names = object_selector(file_path, container=st, key_prefix="stats_")
            variable_name = variable_selector(object_type, container=st, key_prefix="stats_")
            if st.button("Extract", disabled=not (object_names and variable_name)):
                with st.spinner("Extracting..."):
                    df = extract_time_history_multi_objects(file_path, object_names, variable_name)
                active_variable = variable_name
                st.session_state["last_extracted"] = {"df": df, "variable": variable_name, "object_type": object_type}
                st.rerun()
    st.stop()

units = get_variable_units(active_variable) or ""
object_columns = [c for c in df.columns if c != "Time"]

st.caption(f"Showing statistics for **{active_variable}** across {len(object_columns)} object(s).")

basic = calculate_statistics_summary(df, active_variable)
extended = compute_extended_statistics_summary(df, active_variable)
merged = basic.merge(extended, on="Object", how="left")

st.markdown("#### Summary table")
styled_dataframe(merged)
download_button_for_df(merged, f"statistics_{active_variable}.csv".replace(" ", "_"))

st.markdown("#### Per-object detail")
selected_object = st.selectbox("Object", object_columns)
if selected_object:
    row = merged[merged["Object"] == selected_object]
    if not row.empty:
        r = row.iloc[0]
        cols = st.columns(4)
        skew_val = r.get(f"Skewness ({active_variable})")
        kurt_val = r.get(f"Kurtosis ({active_variable})")
        with cols[0]:
            metric_card("Mean", f"{r.get(f'Mean ({active_variable})', 0):.2f}", icon="μ", accent="accent_blue", suffix=f" {units}")
        with cols[1]:
            metric_card("Std deviation", f"{r.get(f'Std Deviation ({active_variable})', 0):.2f}", icon="σ", accent="accent_green", suffix=f" {units}")
        with cols[2]:
            skew_label = "symmetric" if skew_val is not None and abs(skew_val) < 0.5 else ("right-skewed" if (skew_val or 0) > 0 else "left-skewed")
            metric_card("Skewness", f"{skew_val:.3f}" if skew_val is not None else "—", icon="↔", accent="accent_amber", help_text=skew_label)
        with cols[3]:
            kurt_label = "near-normal tails" if kurt_val is not None and abs(kurt_val) < 0.5 else ("heavy-tailed" if (kurt_val or 0) > 0 else "light-tailed")
            metric_card("Excess kurtosis", f"{kurt_val:.3f}" if kurt_val is not None else "—", icon="⛰", accent="accent_red", help_text=kurt_label)

    bins = st.slider("Histogram bins", min_value=10, max_value=150, value=50, step=5)
    render_plotly_chart(histogram_figure(df, [selected_object], active_variable, units, bins))
