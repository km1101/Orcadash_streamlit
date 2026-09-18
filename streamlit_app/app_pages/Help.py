"""Help — quick reference for the Dashboard 1–7 workflow."""
import streamlit as st

from components.themes import render_ops_header
from utils.loaders import ensure_session_state

ensure_session_state()

render_ops_header(
    title="Help",
    subtitle="Workflow reference",
    meta={"Topic": "Dashboard"},
    status_text="GUIDE",
    status_kind="ok",
)

st.markdown(
    """
<div class="panel">
  <h2>Dashboard workflow (steps 1–7)</h2>
  <ol>
    <li><strong>Select .sim File(s)</strong> — drag/drop uploads or scan a folder. Status timeline warms the object catalogue.</li>
    <li><strong>Objects in Selected File(s)</strong> — filter by type (Vessel, Line, Winch, Link, 6D Buoy, 3D Buoy, Environment), search, and tick rows in the object table (selection lives here).</li>
    <li><strong>Result Type</strong> — Time History, Range Graph, X-Y Graph, or 3D Line Shape. Range Graph and
      3D Line Shape are both <strong>Line-only</strong> (arc-length envelope); Winch/Link/Vessel/Buoy selections
      are skipped with a message if chosen for either.</li>
    <li><strong>Variable Category</strong> / <strong>Variable(s)</strong> — for Time History and Range Graph, pick one
      Category from the OrcaFlex variable dictionary, then multi-select one or more Variables from it. For
      <strong>X-Y Graph</strong>, this becomes a <em>Select axis variables</em> panel with two independent controls:
      an <strong>X axis</strong> Category + Variable and a <strong>Y axis</strong> Category + Variable — so X and Y
      can come from entirely different categories (e.g. X = Position/Z, Y = Forces/Effective Tension). Environment
      and Winch each get their own dedicated category (<code>Environment *</code> / <code>Winch</code>) instead of
      being scattered across the shared Position/Motions/Forces categories — selecting only that object type narrows
      the Category dropdown to just its dedicated category(ies). For <strong>3D Line Shape</strong>, there is no
      Category/Variable picker — axes are always the Position category's X, Y, Z; instead pick a single
      <strong>Statistic</strong> (Mean / Min / Max, default Mean) applied consistently across all three axes so the
      3D path describes one physically coherent line shape.</li>
    <li><strong>Period</strong> — OrcaFlex period (Specified Period / Latest Wave / Whole Simulation / Build-up / Stage 1); line Position when applicable; then <em>Generate Results</em>. Range Graph uses the same period options as Time History; 3D Line Shape still uses Whole Simulation.</li>
    <li><strong>Results &amp; Visualization</strong> — switch Line Chart / Range Graph / X-Y Chart / <strong>3D Line Shape</strong> / Data Table / Gauge views (per result type) and export CSV. 3D Line Shape renders an interactive Plotly 3D curve (zoom/pan/rotate) — one trace per selected line.</li>
  </ol>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="panel">
  <h2>Other pages</h2>
  <ul>
    <li><strong>Results</strong> — deeper single-file workspace (statistics, histogram, PSD, range graph).</li>
    <li><strong>Comparisons</strong> — compare one variable across multiple loaded simulations.</li>
    <li><strong>Reports</strong> — build a shareable HTML report from extracted data.</li>
    <li><strong>Statistics</strong> — deep statistical summary of the most recent extraction.</li>
    <li><strong>File Manager</strong> — power-user file tool under the Tools nav section.</li>
  </ul>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="panel">
  <h2>Requirements</h2>
  <p class="muted">Extraction requires a local OrcaFlex install with a valid <code>OrcFxAPI</code> license.
  Without it the UI still loads; Generate Results stays disabled. Check <strong>Settings</strong> for environment status.</p>
</div>
""",
    unsafe_allow_html=True,
)
