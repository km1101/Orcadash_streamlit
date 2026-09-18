# ORCAFLEX Post Result Simulation (Streamlit)

A local engineering **ops console** for exploring OrcaFlex `.sim` results —
time histories, statistics, frequency distribution, spectral (PSD) analysis,
range graphs, and multi-file comparison. The **Dashboard** follows a numbered
1–7 workflow matching the product wireframe. Extraction reuses
`backend/var_and_func`.

## Running it

```bash
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```

On Windows with the Python launcher:

```bash
py -m pip install -r streamlit_app/requirements.txt
py -m streamlit run streamlit_app/app.py
```

Requires a machine with OrcaFlex installed and licensed (`OrcFxAPI`) for live
extraction. Without it, every page still loads — Generate Results is disabled
and **Settings** shows environment status.

## Dashboard workflow (1–7)

| Step | Purpose |
|---|---|
| 1 Select .sim File(s) | Drag/drop upload or folder scan; processing timeline warms model summaries |
| 2 Objects in Selected File(s) | Type catalog (Vessel / Line / Winch / Link / 6D Buoy / 3D Buoy / Environment), searchable table, selection summary (selection lives here) |
| 3 Result Type | Time History / Range Graph / X-Y Graph / 3D Line Shape |
| 4–5 Variable Category / Variable(s) | Time History / Range Graph: one Category + multi-select Variable(s). X-Y Graph: independent **X axis** and **Y axis** panels, each with its own Category + Variable selectbox (X and Y can come from different categories). 3D Line Shape: a single **Statistic** picker (Mean / Min / Max, default Mean) — axes are fixed to the Position category's X, Y, Z |
| 6 Period | OrcaFlex period list + From/To for Specified Period; line Position when applicable; **Generate Results** (Range Graph uses the same period options; 3D Line Shape forces Whole Simulation) |
| 7 Results & Visualization | Line Chart / 3D stub / Range Graph / X-Y Chart / **3D Line Shape** / Data Table / Gauge-KPI + CSV export |

## Architecture

```
streamlit_app/
  app.py                  # shell: theme inject, st.navigation
  app_pages/
    Home.py               # Dashboard — wireframe 1–7 workflow
    Single_Simulation.py  # Results — deep single-file workspace
    Batch_Analysis.py     # Comparisons
    Reports.py            # HTML report builder
    Settings.py           # cache / session / diagnostics
    Help.py / About.py    # wireframe nav pages
    Statistics.py         # Workspace → Statistics
    Load_Files.py         # Tools → File Manager
  components/
    themes.py             # CSS inject + ops header / timeline helpers
    charts.py             # Plotly figures (ops palette)
    filters.py / tables.py / cards.py / sidebar.py
  utils/
    config.py             # branding, nav, OPS_COLORS
    cache.py / loaders.py / exporters.py
  assets/css/orcaflex_ops.css   # navy/ocean/sea-green design system
```

### Theme

The app injects `assets/css/orcaflex_ops.css` — a light ops-console palette
(navy `#102a43`, ocean `#1f4e79`, sea-green / brass accents) with panel cards,
sidebar chrome, and Streamlit widget restyles. This replaces the previous
default Streamlit look (and must not be swapped back to dark glassmorphism).

### Navigation

Sidebar labels match the wireframe: **Dashboard**, **Statistics**, **Results**,
**Comparisons**, **Reports**, **Settings**, **Help**, **About**. File Manager
remains under **Tools**. Collapse the sidebar with Streamlit’s native chevron.

### Intentional deviations from the wireframe

- **3D View** (a Time-History-result view-mode option) is a clear stub —
  full spatial/model replay belongs in OrcaFlex; the console focuses on
  charts/tables/KPIs. This is distinct from the **3D Line Shape** *result
  type*, which is fully implemented — it plots a Line's X/Y/Z position path
  along arc length as a real interactive 3D Plotly curve (zoom/pan/rotate),
  not a stub.
- Risers are modeled as **Line** objects in OrcaFlex (often named with “riser”);
  the catalog does not invent a separate Riser type.
- Object selection is only in step 2 (no duplicate “Select Objects” step).
- Multi-page deep analysis (PSD, range graph, batch compare) lives on
  Results / Comparisons rather than crowding step 7.

### Supported object types

Line, Vessel, 6D Buoy, 3D Buoy, Winch, Link, and Environment are all
fully supported for **Time History** and **X-Y Graph** extraction (Winch and
Link behave like Vessel/Buoy — no line-position control, since they aren't
arc-length objects). **Range Graph** and **3D Line Shape** remain **Line-only**:
OrcFxAPI does not expose a `RangeGraph()` method on Winch or Link objects (it's
an along-arc-length envelope concept), so non-Line selections are skipped with
a clear message rather than raising an error. 3D Line Shape additionally
requires a *single* statistic (Mean by default) applied consistently across
X, Y, and Z — mixing independently-extremized Min/Max per axis would not
describe a physically coherent 3D path.

### Variable categories

Most Variable Categories (Position, Motions, Forces, …) are shared across
Line/Vessel/Buoy/Link. Two object types get their own **dedicated** category
instead of being scattered across the shared ones — **Environment** has
`Environment Position` / `Environment Motions` / `Environment Current` /
`Environment Wind` / `Environment Properties`, and **Winch** has a single
`Winch` category (X, Y, Z, Tension, Length, Stretched Length, Velocity,
Azimuth, Declination, Connection Force, Connection GX/GY/GZ-Force). Selecting
only Winch objects narrows the Category dropdown to just `Winch`; selecting
Winch alongside other (non-Environment) types keeps `Winch` available next to
the shared categories.
