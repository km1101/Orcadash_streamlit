"""
Export helpers: DataFrame -> CSV bytes, and a lightweight self-contained
HTML report combining tables and interactive Plotly charts.
"""
from datetime import datetime

import pandas as pd

from utils.cache import record_export
from utils.config import EXPORT_DIR


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def save_and_record_csv(df: pd.DataFrame, filename: str) -> bytes:
    """Return CSV bytes for a download button, and log the export for Home/Reports."""
    data = dataframe_to_csv_bytes(df)
    dest = EXPORT_DIR / filename
    with open(dest, "wb") as f:
        f.write(data)
    record_export(dest, kind="CSV")
    return data


_REPORT_CSS = """
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
       background: #0F172A; color: #E2E8F0; padding: 32px; }
h1 { color: #3B82F6; }
h2 { border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 40px; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; }
th, td { border: 1px solid #334155; padding: 6px 10px; text-align: left; font-size: 13px; }
th { background: #1E293B; }
.meta { color: #94A3B8; font-size: 13px; }
.section { background: #1E293B; border-radius: 12px; padding: 20px; margin-bottom: 24px; }
"""


def build_html_report(title: str, sections: list) -> str:
    """Build a standalone HTML report.

    Args:
        title: Report title.
        sections: list of dicts, each with:
            - 'heading': str
            - 'text': optional str (free text / caption)
            - 'table': optional DataFrame
            - 'figure': optional plotly Figure (embedded as interactive HTML)

    Returns:
        Full HTML document as a string.
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        f"<html><head><meta charset='utf-8'><title>{title}</title>",
        f"<style>{_REPORT_CSS}</style></head><body>",
        f"<h1>{title}</h1><p class='meta'>Generated {generated_at}</p>",
    ]

    for section in sections:
        parts.append("<div class='section'>")
        parts.append(f"<h2>{section.get('heading', '')}</h2>")
        if section.get("text"):
            parts.append(f"<p>{section['text']}</p>")
        if section.get("table") is not None:
            parts.append(section["table"].to_html(index=False, border=0))
        if section.get("figure") is not None:
            parts.append(section["figure"].to_html(full_html=False, include_plotlyjs="cdn"))
        parts.append("</div>")

    parts.append("</body></html>")
    return "\n".join(parts)


def save_and_record_report(html: str, filename: str) -> str:
    dest = EXPORT_DIR / filename
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html)
    record_export(dest, kind="Report")
    return str(dest)
