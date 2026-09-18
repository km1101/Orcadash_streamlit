"""
Consistent styled-dataframe rendering and CSV download button wiring, shared
across pages so tables look and behave the same everywhere.
"""
import streamlit as st

from utils.exporters import save_and_record_csv


def styled_dataframe(df, height=None, use_container_width=True):
    if df is None or df.empty:
        st.info("No data to display yet.")
        return
    st.dataframe(df, height=height or "content", width="stretch" if use_container_width else "content", hide_index=True)


def download_button_for_df(df, filename, label="⬇ Download CSV", key=None):
    if df is None or df.empty:
        return
    data = save_and_record_csv(df, filename)
    st.download_button(label, data=data, file_name=filename, mime="text/csv", key=key)
