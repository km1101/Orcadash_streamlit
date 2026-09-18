"""Reports — build a self-contained HTML report from the current session's analysis."""
from datetime import datetime

import pandas as pd
import streamlit as st

from components.cards import section_header
from components.charts import SERIES_SELECTOR_CAPTION, histogram_figure, psd_figure, series_multiselect, time_history_figure
from components.tables import styled_dataframe
from utils.cache import get_recent_exports
from utils.exporters import build_html_report, save_and_record_report
from utils.loaders import calculate_statistics_summary, compute_extended_statistics_summary, ensure_session_state, get_variable_units

ensure_session_state()

section_header("Reports", "Generate a shareable HTML report from your current analysis.", icon="📄")

state = st.session_state.get("last_extracted", {})
df, active_variable = state.get("df"), state.get("variable")

if df is None or df.empty:
    st.info("Run an extraction on **Single Simulation** first, then come back here to build a report.")
else:
    units = get_variable_units(active_variable) or ""

    # Explicit series selection — filters the DataFrame *before* any report
    # figure is built, so excluded series are never added as traces. This is
    # what keeps the report in sync with what the user actually wants shown:
    # Plotly's legend-click state lives only in the browser and never reaches
    # this session, so rebuilding figures from the full extraction here would
    # otherwise always include every series regardless of what was toggled
    # off in an earlier interactive chart.
    report_df, selected_objects, _ = series_multiselect(
        df, {"Time"}, key="report_series_select",
        label="Series to include in report",
        help="Only the selected series become chart traces / table rows in the generated report.",
    )
    st.caption(SERIES_SELECTOR_CAPTION)
    object_columns = selected_objects

    st.markdown(f"Building a report for **{active_variable}** across {len(object_columns)} object(s).")
    report_title = st.text_input("Report title", value=f"OrcaFlex Analysis — {active_variable}")

    include_time_history = st.checkbox("Include time history chart", value=True)
    include_statistics = st.checkbox("Include statistics table", value=True)
    include_histogram = st.checkbox("Include frequency distribution chart", value=True)
    include_psd = st.checkbox("Include frequency-domain (PSD) chart", value=False)
    notes = st.text_area("Additional notes (optional)", placeholder="Context, assumptions, conclusions...")

    if st.button("📄 Generate report", type="primary"):
        sections = []
        if notes:
            sections.append({"heading": "Notes", "text": notes.replace("\n", "<br>")})
        if include_time_history:
            sections.append({
                "heading": "Time History",
                "figure": time_history_figure(report_df, active_variable, units),
            })
        if include_statistics:
            basic = calculate_statistics_summary(report_df, active_variable)
            extended = compute_extended_statistics_summary(report_df, active_variable)
            merged = basic.merge(extended, on="Object", how="left")
            sections.append({"heading": "Statistics Summary", "table": merged})
        if include_histogram:
            sections.append({
                "heading": "Frequency Distribution",
                "figure": histogram_figure(report_df, object_columns, active_variable, units),
            })
        if include_psd:
            fig, summary_rows = psd_figure(report_df, object_columns, active_variable or "")
            sections.append({"heading": "Frequency Domain (Spectral)", "figure": fig})
            if summary_rows:
                sections.append({"heading": "Spectral Peaks", "table": pd.DataFrame(summary_rows)})

        html = build_html_report(report_title, sections)
        filename = f"report_{active_variable.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        save_and_record_report(html, filename)

        st.success("Report generated.")
        st.download_button("⬇ Download report", data=html, file_name=filename, mime="text/html")

st.write("")
section_header("Recent exports", icon="🕒")
exports = get_recent_exports(limit=10)
if not exports:
    st.caption("Nothing exported yet.")
else:
    styled_dataframe(pd.DataFrame(exports)[["name", "kind", "exported_at"]])
