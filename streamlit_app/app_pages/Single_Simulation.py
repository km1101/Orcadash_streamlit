"""Single Simulation — deep-dive workspace for one loaded .sim file.

Covers time history, range graph, and object-type views (Line / Vessel /
6DBuoy / 3DBuoy / Environment). "Moorings" are Line objects in OrcaFlex, so
they're reached via the Line object type rather than a separate category.
"""
import pandas as pd
import streamlit as st

from components.cards import section_header
from components.charts import (
    SERIES_SELECTOR_CAPTION,
    filter_columns_for_objects,
    histogram_figure,
    object_multiselect,
    psd_figure,
    range_graph_figure,
    render_plotly_chart,
    series_multiselect,
    time_history_figure,
)
from components.filters import file_selector, object_selector, period_selector, position_selector, variable_selector
from components.tables import download_button_for_df, styled_dataframe
from utils.loaders import (
    ORCAFLEX_AVAILABLE,
    show_orcaflex_unavailable_banner,
    calculate_statistics_summary,
    compute_extended_statistics_summary,
    ensure_session_state,
    extract_environment_time_history,
    extract_range_graph_data,
    extract_time_history_multi_objects,
    get_variable_units,
    is_end_load_variable,
    record_variable_usage,
)
from utils.loaders import Range_Graph_variable_dict

ensure_session_state()

section_header("Single Simulation", "Time history, statistics, and spectral analysis for one model.", icon="📈")

if not ORCAFLEX_AVAILABLE:
    show_orcaflex_unavailable_banner()
    st.stop()

st.sidebar.markdown("### Filters")
_, file_path = file_selector()
if not file_path:
    st.stop()

object_type, object_names = object_selector(file_path)
variable_name = variable_selector(object_type)
position_spec = position_selector(object_type, ends_only=is_end_load_variable(variable_name))
period_spec = period_selector()

extract_clicked = st.sidebar.button(
    "🔎 Extract data", type="primary",
    disabled=not (object_names and variable_name),
)

if extract_clicked:
    with st.spinner(f"Extracting '{variable_name}' for {len(object_names)} object(s)..."):
        if object_type == "Environment":
            df = extract_environment_time_history(file_path, variable_name, period_spec)
        else:
            df = extract_time_history_multi_objects(file_path, object_names, variable_name, position_spec, period_spec)
    st.session_state["last_extracted"] = {"df": df, "variable": variable_name, "object_type": object_type}
    st.session_state["extraction_count"] = st.session_state.get("extraction_count", 0) + 1
    record_variable_usage(variable_name)

state = st.session_state.get("last_extracted", {})
df, active_variable = state.get("df"), state.get("variable")
units = get_variable_units(active_variable) or "" if active_variable else ""

tabs = st.tabs(["📉 Time History", "📋 Statistics", "📊 Frequency Distribution", "🌊 Frequency Domain", "📌 Range Graph"])

with tabs[0]:
    if df is None or df.empty:
        st.info("Choose a file, object(s), and variable in the sidebar, then click **Extract data**.")
    else:
        chart_df, _, _ = series_multiselect(
            df, {"Time"}, key="single_series_th",
            help="Choose which objects appear in the chart, PNG download, and Report exports.",
        )
        st.caption(SERIES_SELECTOR_CAPTION)
        render_plotly_chart(time_history_figure(chart_df, active_variable, units))
        download_button_for_df(df, f"time_history_{active_variable}.csv".replace(" ", "_"))
        # Keep Reports.py in sync — it reads last_extracted rather than
        # rebuilding the chart from the full unfiltered extraction.
        st.session_state["last_extracted"] = {
            "df": chart_df, "variable": active_variable, "object_type": state.get("object_type"),
        }

with tabs[1]:
    if df is None or df.empty:
        st.info("Run an extraction to see statistics.")
    else:
        basic = calculate_statistics_summary(df, active_variable)
        extended = compute_extended_statistics_summary(df, active_variable)
        merged = basic.merge(extended, on="Object", how="left")
        styled_dataframe(merged)
        st.caption(
            "RMS and Significant Value (H₁/₃-style, average of the highest 1/3 of peaks) and "
            "Skewness/Kurtosis describe distribution shape beyond mean/std."
        )
        download_button_for_df(merged, f"statistics_{active_variable}.csv".replace(" ", "_"))

with tabs[2]:
    if df is None or df.empty:
        st.info("Run an extraction to see the frequency distribution.")
    else:
        object_columns = [c for c in df.columns if c != "Time"]
        selected = st.multiselect("Objects to include", object_columns, default=object_columns, key="hist_objects")
        bins = st.slider("Number of bins", min_value=10, max_value=150, value=50, step=5)
        render_plotly_chart(histogram_figure(df, selected, active_variable, units, bins))

with tabs[3]:
    if df is None or df.empty:
        st.info("Run an extraction to see the frequency-domain (spectral) view.")
    else:
        object_columns = [c for c in df.columns if c != "Time"]
        selected = st.multiselect("Objects to include", object_columns, default=object_columns[:1], key="psd_objects")
        fig, summary_rows = psd_figure(df, selected, active_variable or "")
        render_plotly_chart(fig)
        if summary_rows:
            styled_dataframe(pd.DataFrame(summary_rows))
        st.caption(
            "Welch's method PSD estimate of the extracted time-domain signal — distinct from "
            "OrcFxAPI's native frequency-domain analysis type, which requires the model itself "
            "to have been solved in the frequency domain."
        )

with tabs[4]:
    if object_type != "Line" or not object_names:
        st.info("Select one or more **Line** objects in the sidebar to use the range graph.")
    else:
        rg_categories = list(Range_Graph_variable_dict.keys())
        rg_category = st.selectbox("Category", rg_categories, key="rg_category")
        rg_variable = st.selectbox("Variable", Range_Graph_variable_dict[rg_category], key="rg_variable")

        st.caption("Statistics — choose which envelope values to extract.")
        s1, s2, s3 = st.columns(3)
        with s1:
            rg_want_min = st.checkbox("Min", value=True, key="single_rg_stat_min")
        with s2:
            rg_want_max = st.checkbox("Max", value=True, key="single_rg_stat_max")
        with s3:
            rg_want_mean = st.checkbox("Mean", value=True, key="single_rg_stat_mean")
        rg_statistics = [
            s for s, on in (
                ("min", rg_want_min),
                ("max", rg_want_max),
                ("mean", rg_want_mean),
            )
            if on
        ]
        if not rg_statistics:
            st.warning("Select at least one statistic (Min, Max, or Mean).")

        if st.button("Extract range graph", disabled=not rg_statistics):
            progress = st.progress(0.0, text="Extracting range graph...")
            frames = []
            for i, line_name in enumerate(object_names):
                rg_df = extract_range_graph_data(file_path, line_name, rg_variable, period_spec)
                if not rg_df.empty:
                    keep_cols = ["z"] + [s for s in rg_statistics if s in rg_df.columns]
                    rg_df = rg_df[keep_cols].rename(
                        columns={c: f"{line_name}_{c}" for c in keep_cols if c != "z"}
                    )
                    frames.append(rg_df)
                progress.progress((i + 1) / len(object_names), text=f"Extracted {line_name}")
            progress.empty()

            if not frames:
                st.warning("No range graph data extracted.")
            else:
                merged_rg = frames[0]
                for extra_df in frames[1:]:
                    merged_rg = pd.merge(merged_rg, extra_df, on="z", how="outer")
                if "z" in merged_rg.columns:
                    merged_rg = merged_rg.sort_values("z", kind="mergesort").reset_index(drop=True)
                st.session_state["last_range_graph"] = {
                    "df": merged_rg,
                    "objects": object_names,
                    "variable": rg_variable,
                    "statistics": list(rg_statistics),
                }

        rg_state = st.session_state.get("last_range_graph")
        if rg_state:
            rg_selected = object_multiselect(
                rg_state["objects"], key="single_series_rg",
                help="Choose which line objects appear in the chart, PNG download, and Report exports.",
            )
            extracted_stats = [
                s for s in ("min", "max", "mean")
                if s in (rg_state.get("statistics") or ("min", "max", "mean"))
            ]
            if not extracted_stats:
                extracted_stats = [
                    s for s in ("min", "max", "mean")
                    if any(str(c).endswith(f"_{s}") for c in rg_state["df"].columns)
                ] or ["min", "max", "mean"]
            st.caption("Statistics to display on the chart")
            viz_cols = st.columns(len(extracted_stats))
            viz_statistics = []
            for col, stat in zip(viz_cols, extracted_stats):
                with col:
                    if st.checkbox(
                        stat.capitalize(),
                        value=True,
                        key=f"single_rg_viz_{stat}",
                        help="Show or hide this envelope statistic for all selected lines.",
                    ):
                        viz_statistics.append(stat)
            st.caption(SERIES_SELECTOR_CAPTION)
            suffixes = tuple(f"_{s}" for s in viz_statistics) if viz_statistics else ("__none__",)
            rg_chart_df = filter_columns_for_objects(
                rg_state["df"], {"z"}, rg_selected, suffixes
            )
            render_plotly_chart(
                range_graph_figure(
                    rg_chart_df,
                    rg_selected,
                    rg_state["variable"],
                    statistics=viz_statistics or extracted_stats,
                )
            )
            styled_dataframe(rg_state["df"])
            download_button_for_df(rg_state["df"], f"range_graph_{rg_state['variable']}.csv".replace(" ", "_"))
