"""
Dashboard — numbered 1–7 workflow for loading .sim files, choosing result type,
selecting objects/variables, generating results, and visualizing them.
"""
import os
import time

import pandas as pd
import streamlit as st

from components.charts import (
    SERIES_SELECTOR_CAPTION,
    filter_columns_for_objects,
    kpi_gauge_figure,
    line_shape_3d_figure,
    object_multiselect,
    range_graph_figure,
    render_plotly_chart,
    series_multiselect,
    time_history_figure,
    xy_figure,
)
from components.filters import position_selector
from components.tables import download_button_for_df, styled_dataframe
from components.themes import render_ops_header, render_timeline, viz_placeholder
from utils.cache import get_cached_model_summary
from utils.config import DEFAULT_PERIOD, OBJECT_CATALOG_ORDER, OBJECT_TYPE_ICONS, PERIOD_OPTIONS
from utils.loaders import (
    IMPORT_ERROR,
    ORCAFLEX_AVAILABLE,
    END_LOAD_CATEGORIES,
    Range_Graph_variable_dict,
    ensure_session_state,
    extract_3D_position_data,
    extract_environment_time_history,
    extract_range_graph_data,
    extract_time_history_multi_objects,
    extract_xy_dataframe,
    get_variable_units,
    get_variables_for_object_types,
    is_end_load_category,
    is_end_load_variable,
    record_variable_usage,
    register_loaded_file,
    save_uploaded_file,
    variables_dict,
)

RESULT_TYPES = ("Time History", "Range Graph", "X-Y Graph", "3D Line Shape")
RESULT_TYPE_HELP = {
    "Time History": "Results vs time — time-series values for selected objects and variables.",
    "Range Graph": "Results vs range — arc-length profiles (min / max / mean) for Line objects.",
    "X-Y Graph": "Results vs X-Y — parametric plot of one variable against another at matching time steps.",
    "3D Line Shape": "3D path — X/Y/Z position along arc length for Line objects, as a 3D curve.",
}
# Result types that use OrcaFlex's along-arc-length RangeGraph() rather than a
# time-history extraction — both are Line-only. Range Graph accepts the same
# Period options as Time History; 3D Line Shape still uses Whole Simulation.
RANGE_GRAPH_LIKE_RESULT_TYPES = ("Range Graph", "3D Line Shape")
PERIOD_LOCKED_RESULT_TYPES = ("3D Line Shape",)
RANGE_GRAPH_STATISTICS = ("min", "max", "mean")

ensure_session_state()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _object_key(file_name, obj_type, obj_name):
    return f"{file_name}||{obj_type}||{obj_name}"


def _parse_key(key):
    parts = key.split("||", 2)
    if len(parts) != 3:
        return None
    return {"file": parts[0], "type": parts[1], "name": parts[2]}


def _build_object_catalog(loaded_files):
    """Flatten model summaries into catalog rows + type counts."""
    rows = []
    counts = {k: 0 for k, _ in OBJECT_CATALOG_ORDER}
    for file_name, path in loaded_files.items():
        summary = get_cached_model_summary(path)
        objects = summary.get("objects", {})
        for obj_type, names in objects.items():
            for name in names:
                counts[obj_type] = counts.get(obj_type, 0) + 1
                rows.append({
                    "key": _object_key(file_name, obj_type, name),
                    "name": name,
                    "type": obj_type,
                    "description": f"{obj_type} in {file_name}",
                    "file": file_name,
                    "path": path,
                })
        # Environment is always available per file when API is present
        if ORCAFLEX_AVAILABLE and not summary.get("error"):
            counts["Environment"] = counts.get("Environment", 0) + 1
            rows.append({
                "key": _object_key(file_name, "Environment", "Environment"),
                "name": "Environment",
                "type": "Environment",
                "description": f"Model environment — {file_name}",
                "file": file_name,
                "path": path,
            })
    return rows, counts


def _file_size_label(path):
    try:
        size = os.path.getsize(path)
    except OSError:
        return "—"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / 1024:.0f} KB"


def _warmup_files(paths_and_names):
    """Warm model-summary cache with visible progress; update process stage."""
    n = len(paths_and_names)
    if n == 0:
        st.session_state["dash_process_stage"] = 0
        st.session_state["dash_process_progress"] = 0.0
        return

    st.session_state["dash_process_stage"] = 1
    st.session_state["dash_process_progress"] = 0.15
    progress = st.progress(0.15, text="Files uploaded — generating objects…")

    for i, (name, path) in enumerate(paths_and_names):
        st.session_state["dash_process_stage"] = 2
        st.session_state["dash_process_progress"] = 0.15 + 0.7 * ((i + 0.5) / n)
        progress.progress(
            st.session_state["dash_process_progress"],
            text=f"Generating objects — {name}",
        )
        get_cached_model_summary(path)
        time.sleep(0.04)

    st.session_state["dash_process_stage"] = 4
    st.session_state["dash_process_progress"] = 1.0
    progress.progress(1.0, text="Objects ready — ready for selection")
    time.sleep(0.15)
    progress.empty()


def _timeline_from_stage(stage, progress):
    labels = [
        ("Files uploaded", "done" if stage >= 1 else ("active" if stage == 0 and progress > 0 else "pending")),
        ("Generating objects…", "done" if stage >= 3 else ("active" if stage == 2 else ("pending" if stage < 2 else "done"))),
        ("Objects ready", "done" if stage >= 3 else ("active" if stage == 3 else "pending")),
        ("Ready for selection", "done" if stage >= 4 else ("active" if stage == 4 else "pending")),
    ]
    # Simplify mapping for clearer UX
    states = ["pending", "pending", "pending", "pending"]
    if stage <= 0 and progress <= 0:
        pass
    elif stage == 1:
        states = ["done", "active", "pending", "pending"]
    elif stage == 2:
        states = ["done", "active", "pending", "pending"]
    elif stage == 3:
        states = ["done", "done", "active", "pending"]
    elif stage >= 4:
        states = ["done", "done", "done", "done"]

    stages = []
    for (label, _), state in zip(labels, states):
        entry = {"label": label, "state": state}
        if state == "active" and stage == 2:
            entry["sub"] = "Reading model object catalogue"
        stages.append(entry)
    return stages


def _variable_categories(var_source, raw_types, allow_environment=True, allow_end_loads=True):
    """Category keys from ``var_source``, filtered for the selected object types.

    ``allow_environment=False`` always excludes ``Environment*`` categories —
    used by X-Y Graph, whose extraction path (paired object time histories)
    has no Environment support, regardless of what is selected in Step 2.
    Winch is unaffected by this flag — Winch is fully supported for X-Y Graph
    (see README "Supported object types"), so its dedicated "Winch" category
    stays available there.

    The "Winch" category is scoped the same way "Environment*" categories
    are: selecting only Winch objects narrows the list to just "Winch";
    mixing Winch with other (non-Environment) types keeps "Winch" alongside
    the shared categories; selecting no Winch objects hides "Winch" entirely.

    End Loads* categories are Line + Time History only (``allow_end_loads``).
    """
    if not var_source:
        return []
    types_set = set(raw_types)
    end_load_cats = set(END_LOAD_CATEGORIES)

    def _without_end_loads(cats):
        if allow_end_loads and "Line" in types_set:
            return cats
        return [c for c in cats if c not in end_load_cats]

    if not allow_environment:
        cats = [c for c in var_source.keys() if not c.startswith("Environment")]
        if "Winch" not in types_set:
            cats = [c for c in cats if c != "Winch"]
        return _without_end_loads(cats)
    if types_set == {"Environment"}:
        return [c for c in var_source.keys() if c.startswith("Environment")]
    if types_set == {"Winch"}:
        return [c for c in var_source.keys() if c == "Winch"]
    if any(t == "Environment" for t in raw_types):
        return _without_end_loads(list(var_source.keys()))
    categories = [c for c in var_source.keys() if not c.startswith("Environment")]
    if "Winch" not in types_set:
        categories = [c for c in categories if c != "Winch"]
    return _without_end_loads(categories)


def _variable_options(var_source, category, raw_types):
    """Variable names in ``category``, narrowed to ones valid for ``raw_types``."""
    if not category or not var_source:
        return []
    category_variables = list(var_source.get(category, {}).keys())
    try:
        valid = get_variables_for_object_types(
            [t for t in raw_types if t != "Environment"] or raw_types
        )
    except Exception:
        valid = None
    if valid and "Environment" not in raw_types:
        return [v for v in category_variables if v in valid] or category_variables
    return category_variables


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

loaded = st.session_state.get("loaded_files", {})
selected_keys = list(st.session_state.get("dash_selected_keys", []))
api_ok = ORCAFLEX_AVAILABLE

render_ops_header(
    meta={
        "Files": str(len(loaded)),
        "Selected": str(len(selected_keys)),
        "Extractions": str(st.session_state.get("extraction_count", 0)),
    },
    status_text="OrcFxAPI OK" if api_ok else "API OFFLINE",
    status_kind="ok" if api_ok else "warn",
)

if not api_ok:
    st.warning(
        f"OrcFxAPI is not available ({IMPORT_ERROR}). You can still upload files and browse the UI; "
        "result generation stays disabled until OrcaFlex is installed and licensed."
    )

# ===========================================================================
# STEP 1 — Select .sim File(s)
# ===========================================================================
st.markdown(
    '<div class="panel"><div class="panel-head"><h2>'
    '<span class="step-badge">1</span>Select .sim File(s)</h2></div></div>',
    unsafe_allow_html=True,
)

col_upload, col_files, col_status = st.columns([1.15, 1.1, 1.0], gap="medium")

with col_upload:
    st.caption("Drag & drop or browse for OrcaFlex simulation files")
    uploads = st.file_uploader(
        "Upload .sim files",
        type=["sim"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="dash_uploader",
    )
    folder_path = st.text_input(
        "Or load from folder path",
        placeholder=r"C:\Projects\OrcaFlex\Models",
        key="dash_folder",
    )
    scan_clicked = st.button("Scan folder", key="dash_scan", width="stretch")
with col_files:
    st.caption("Selected files")
    if not loaded:
        st.info("No files loaded yet.")
    else:
        for name, path in list(loaded.items()):
            c1, c2 = st.columns([4, 1])
            c1.markdown(
                f'<div class="file-chip"><div><strong>{name}</strong>'
                f'<div class="size">{_file_size_label(path)}</div></div></div>',
                unsafe_allow_html=True,
            )
            if c2.button("✕", key=f"rm_{name}", help=f"Remove {name}"):
                del st.session_state["loaded_files"][name]
                st.session_state["dash_selected_keys"] = [
                    k for k in st.session_state.get("dash_selected_keys", [])
                    if not k.startswith(f"{name}||")
                ]
                if st.session_state.get("active_file") == name:
                    st.session_state["active_file"] = None
                st.rerun()
        if st.button("Clear all", key="dash_clear_all"):
            st.session_state["loaded_files"] = {}
            st.session_state["dash_selected_keys"] = []
            st.session_state["active_file"] = None
            st.session_state["dash_process_stage"] = 0
            st.session_state["dash_process_progress"] = 0.0
            st.rerun()

with col_status:
    st.caption("Processing status")
    stage = st.session_state.get("dash_process_stage", 0)
    prog = st.session_state.get("dash_process_progress", 0.0)
    if loaded and stage < 4:
        # Files present from a prior session — mark ready
        st.session_state["dash_process_stage"] = 4
        st.session_state["dash_process_progress"] = 1.0
        stage, prog = 4, 1.0
    render_timeline(_timeline_from_stage(stage, prog), progress=prog if stage in (1, 2) else (1.0 if stage >= 4 else None))

# Handle uploads / folder scan (only new files — uploader re-emits on every rerun)
if uploads:
    batch = []
    for uploaded in uploads:
        if uploaded.name in st.session_state.get("loaded_files", {}):
            continue
        dest = save_uploaded_file(uploaded)
        register_loaded_file(uploaded.name, dest)
        batch.append((uploaded.name, str(dest)))
    if batch:
        _warmup_files(batch)
        st.rerun()

if scan_clicked and folder_path:
    from utils.loaders import scan_folder_for_sim_files
    found = scan_folder_for_sim_files(folder_path)
    if not found:
        st.warning("No `.sim` files found under that path.")
    else:
        batch = []
        for path in found:
            if path.name in st.session_state.get("loaded_files", {}):
                continue
            register_loaded_file(path.name, str(path))
            batch.append((path.name, str(path)))
        if batch:
            _warmup_files(batch)
            st.success(f"Loaded {len(batch)} new file(s) from folder.")
            st.rerun()
        else:
            st.info("All scanned files are already loaded.")

# ===========================================================================
# STEP 2 — Objects in Selected File(s)
# ===========================================================================
st.markdown(
    '<div class="panel"><div class="panel-head"><h2>'
    '<span class="step-badge">2</span>Objects in Selected File(s)</h2></div></div>',
    unsafe_allow_html=True,
)

catalog_rows, type_counts = _build_object_catalog(loaded)

col_tree, col_table, col_summary = st.columns([1.0, 2.2, 0.85], gap="medium")

with col_tree:
    st.caption("Object catalog")
    filter_choice = st.session_state.get("dash_catalog_filter", "All")
    valid_filters = {"All"} | {k for k, _ in OBJECT_CATALOG_ORDER}
    if filter_choice not in valid_filters:
        st.session_state["dash_catalog_filter"] = "All"
        filter_choice = "All"

    # Single uniform list (All + each type) so every catalog button is built
    # from the same loop — keeps width/height/spacing identical across rows.
    catalog_buttons = [("All", "All objects", OBJECT_TYPE_ICONS.get("All", "📦"), len(catalog_rows))]
    catalog_buttons += [
        (type_key, label, OBJECT_TYPE_ICONS.get(type_key, "•"), type_counts.get(type_key, 0))
        for type_key, label in OBJECT_CATALOG_ORDER
    ]
    for type_key, label, icon, count in catalog_buttons:
        is_active = filter_choice == type_key
        if st.button(
            f"{icon} {label} ({count})",
            key=f"cat_{type_key}",
            width="stretch",
            type="primary" if is_active else "secondary",
            disabled=count == 0 and type_key not in ("Environment", "All"),
        ):
            st.session_state["dash_catalog_filter"] = type_key
            st.rerun()

with col_table:
    st.caption("Searchable object table")

    # Search + file filter share one row so their top edge matches the
    # catalog buttons' top edge in col_tree and the summary card in
    # col_summary (both start immediately after their own caption).
    file_names = list(loaded.keys())
    search_col, file_col = st.columns([2.3, 1.4], gap="small")
    with search_col:
        search = st.text_input(
            "Search objects",
            placeholder="Filter by name, type, or file…",
            key="dash_obj_search",
            label_visibility="collapsed",
        )
    with file_col:
        file_filter = st.multiselect(
            "Filter by file",
            file_names,
            key="dash_file_filter",
            placeholder="All files",
            label_visibility="collapsed",
            disabled=not file_names,
            help="Narrow the table to one or more loaded .sim files (matches the File Source column exactly).",
        )

    filter_choice = st.session_state.get("dash_catalog_filter", "All")
    filtered = catalog_rows
    if filter_choice != "All":
        filtered = [r for r in filtered if r["type"] == filter_choice]
    if file_filter:
        file_filter_set = set(file_filter)
        filtered = [r for r in filtered if r["file"] in file_filter_set]
    if search:
        q = search.lower()
        filtered = [
            r for r in filtered
            if q in r["name"].lower() or q in r["type"].lower() or q in r["file"].lower()
        ]
    filtered_keys = [r["key"] for r in filtered]

    # Reset the "select all" toggle whenever the visible set changes (new
    # search/type/file filter) so it never silently re-applies to a
    # different set of rows than the one the user actually checked. Also
    # honor a deferred reset request from the Selection Summary buttons
    # (col_summary renders *after* this checkbox, so it can't touch this
    # widget's session_state directly — it sets the pending flag instead,
    # and we apply it here, before the checkbox is instantiated).
    filter_signature = (filter_choice, search, tuple(sorted(file_filter)))
    reset_requested = st.session_state.pop("dash_select_all_reset_pending", False)
    if reset_requested or st.session_state.get("dash_filter_signature") != filter_signature:
        st.session_state["dash_filter_signature"] = filter_signature
        st.session_state["dash_select_all_cb"] = False
        st.session_state["dash_select_all_prev"] = False

    select_all_value = st.checkbox(
        f"Select all ({len(filtered)} filtered)" if filtered else "Select all (0 filtered)",
        key="dash_select_all_cb",
        disabled=not filtered,
        help="Select or clear every object currently shown below (respects search + file filter).",
    )
    prev_select_all = st.session_state.get("dash_select_all_prev", False)
    selected_set = set(st.session_state.get("dash_selected_keys", []))
    if select_all_value and not prev_select_all:
        selected_set |= set(filtered_keys)
        st.session_state["dash_selected_keys"] = list(selected_set)
    elif not select_all_value and prev_select_all:
        selected_set -= set(filtered_keys)
        st.session_state["dash_selected_keys"] = list(selected_set)
    st.session_state["dash_select_all_prev"] = select_all_value
    selected_set = set(st.session_state.get("dash_selected_keys", []))

    if not filtered:
        st.info("Load a `.sim` file to populate the object catalogue.")
        editor_df = pd.DataFrame(columns=["Select", "Object Name", "Type", "Description", "File Source", "_key"])
    else:
        editor_df = pd.DataFrame([
            {
                "Select": r["key"] in selected_set,
                "Object Name": r["name"],
                "Type": r["type"],
                "Description": r["description"],
                "File Source": r["file"],
                "_key": r["key"],
            }
            for r in filtered
        ])

    edited = st.data_editor(
        editor_df,
        column_config={
            "Select": st.column_config.CheckboxColumn("✓", default=False),
            "Object Name": st.column_config.TextColumn("Object Name"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Description": st.column_config.TextColumn("Description"),
            "File Source": st.column_config.TextColumn("File Source"),
            "_key": None,
        },
        hide_index=True,
        width="stretch",
        height=280,
        key="dash_object_editor",
        disabled=["Object Name", "Type", "Description", "File Source"],
    )

    # Merge editor selections back into session (respect filter view)
    if not edited.empty and "_key" in edited.columns:
        visible_keys = set(edited["_key"].tolist())
        kept = [k for k in st.session_state.get("dash_selected_keys", []) if k not in visible_keys]
        newly = edited.loc[edited["Select"] == True, "_key"].tolist()  # noqa: E712
        st.session_state["dash_selected_keys"] = kept + newly
        selected_keys = st.session_state["dash_selected_keys"]

with col_summary:
    st.caption("Selection summary")
    n_sel = len(st.session_state.get("dash_selected_keys", []))
    st.markdown(
        f"""
        <div class="summary-box">
          <div class="count">{n_sel}</div>
          <div class="muted">object(s) selected</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    sel_col, clr_col = st.columns(2, gap="small")
    with sel_col:
        if st.button(
            "Select all",
            key="dash_select_all_global",
            width="stretch",
            disabled=not catalog_rows,
            help="Select every object across all loaded files (ignores the current search/type/file filter).",
        ):
            st.session_state["dash_selected_keys"] = [r["key"] for r in catalog_rows]
            st.session_state["dash_select_all_reset_pending"] = True
            st.rerun()
    with clr_col:
        if st.button("Clear selection", key="dash_clear_sel", width="stretch"):
            st.session_state["dash_selected_keys"] = []
            st.session_state["dash_select_all_reset_pending"] = True
            st.rerun()

# ===========================================================================
# STEP 3 — Result Type (critical)
# ===========================================================================
st.markdown(
    '<div class="panel"><div class="panel-head"><h2>'
    '<span class="step-badge">3</span>Result Type</h2></div></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="result-type-hint">Choose the result output type.</p>',
    unsafe_allow_html=True,
)

rt_default = st.session_state.get("dash_result_type", "Time History")
if rt_default not in RESULT_TYPES:
    rt_default = "Time History"
result_type = st.radio(
    "Result Type",
    RESULT_TYPES,
    index=RESULT_TYPES.index(rt_default),
    key="dash_result_type",
    horizontal=True,
    label_visibility="collapsed",
    captions=["Results vs time", "Results vs range", "Results vs X-Y", "3D path along arc length"],
)

# Reset category / variable widgets when Result Type changes (stable keys)
if st.session_state.get("_dash_last_result_type") != result_type:
    for _k in (
        "dash_category", "dash_variables",
        "dash_xy_x_category", "dash_xy_x_variable",
        "dash_xy_y_category", "dash_xy_y_variable",
        "dash_3d_statistic",
    ):
        st.session_state.pop(_k, None)
    st.session_state["_dash_last_result_type"] = result_type
    # Prefer a chart mode that matches the new result type
    if result_type == "Range Graph":
        st.session_state["dash_view_mode"] = "Range Graph"
    elif result_type == "X-Y Graph":
        st.session_state["dash_view_mode"] = "X-Y Chart"
    elif result_type == "3D Line Shape":
        st.session_state["dash_view_mode"] = "3D Line Shape"
    else:
        st.session_state["dash_view_mode"] = "Line Chart"

# Card-style summaries under the radio (wireframe affordance)
rt_cols = st.columns(len(RESULT_TYPES), gap="small")
for col, rtype in zip(rt_cols, RESULT_TYPES):
    active = "border-color:var(--ocean);background:rgba(31,78,121,0.06);" if rtype == result_type else ""
    with col:
        st.markdown(
            f'<div class="result-type-card" style="{active}">'
            f"<strong>{rtype}</strong>"
            f'<div class="desc">{RESULT_TYPE_HELP[rtype].split(" — ", 1)[-1]}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

with st.expander("Learn more about result types", expanded=False):
    st.markdown(
        """
        - **Time History** — extract results versus simulation time for any supported object type
          (Lines, Vessels, Buoys, Environment).
        - **Range Graph** — extract min / max / mean along a Line’s arc length. Only **Line**
          objects are supported; other types are skipped with a clear message.
        - **X-Y Graph** — parametric plot of two time-history variables at identical time steps.
          Choose an **X-axis** and **Y-axis** variable below.
        - **3D Line Shape** — plot the X/Y/Z position path along a Line’s arc length as a 3D
          curve, using one consistent statistic (Mean by default) across all three axes. Only
          **Line** objects are supported; other types are skipped with a clear message.
        """
    )

selected_parsed = [_parse_key(k) for k in st.session_state.get("dash_selected_keys", [])]
selected_parsed = [p for p in selected_parsed if p]
selected_types = sorted({p["type"] for p in selected_parsed})
raw_types_for_vars = sorted({p["type"] for p in selected_parsed}) or ["Line"]
line_like = [p for p in selected_parsed if p["type"] == "Line"]
non_line = [p for p in selected_parsed if p["type"] != "Line"]

if result_type in RANGE_GRAPH_LIKE_RESULT_TYPES and non_line and not line_like:
    st.warning(
        f"{result_type} requires **Line** objects. "
        f"Current selection has no lines ({', '.join(selected_types) or 'none'})."
    )
elif result_type in RANGE_GRAPH_LIKE_RESULT_TYPES and non_line:
    st.info(
        f"{result_type} will use {len(line_like)} Line object(s). "
        f"{len(non_line)} non-Line selection(s) will be skipped."
    )

# ===========================================================================
# STEPS 4–6 — Variables / options + Generate
# ===========================================================================
st.markdown(
    '<div class="panel"><div class="panel-head"><h2>'
    '<span class="step-badge">4</span>–'
    '<span class="step-badge">6</span>Configure extraction</h2></div></div>',
    unsafe_allow_html=True,
)

# Balanced row: Category | Variable(s) | Period | Generate
# Position (when needed) sits on its own row below as a sibling control.
# vertical_alignment="top" is Streamlit's default, but set explicitly since
# top-alignment across these columns depends on every column's header being
# the *same* DOM/CSS construct — a "**bold markdown**" <p><strong> heading
# followed by a selectbox with label_visibility="collapsed" — used
# identically for every header in this row ("X axis — Category",
# "Y axis — Category", "6. Period", "4. Variable Category",
# "5. Variable(s)"). Mixing that with a native (visible) selectbox label,
# which has a different font-size/weight/line-height/margin, is what broke
# alignment before — matching line *count* alone doesn't pixel-align two
# different element types.
c4, c5, c6, c_gen = st.columns([1.2, 1.35, 1.35, 1.0], gap="small", vertical_alignment="top")

# ---- Variable category / variables depend on result type ----
use_rg_vars = result_type == "Range Graph"
var_source = Range_Graph_variable_dict if use_rg_vars else variables_dict

variables = []
variable_x = None
variable_y = None
category = None

if result_type == "X-Y Graph":
    # X-Y needs two fully independent axis pickers — a shared Category +
    # Variable(s) control (as used by Time History / Range Graph) can't
    # express "Position/Z on X vs Forces/Effective Tension on Y". Each axis
    # gets its own Category selectbox (scoped to it) followed by a Variable
    # selectbox scoped to that category, per the "Select axis variables"
    # reference layout. Environment is excluded from both — the X-Y
    # extraction path pairs object time histories and has no Environment
    # support (see the skip/warning in the Generate branch below).
    #st.markdown("**4–5. Select axis variables**")
    xy_categories = _variable_categories(
        var_source, raw_types_for_vars, allow_environment=False, allow_end_loads=False
    )

    with c4:
        # Header uses the exact same "**bold markdown**" construct as
        # "6. Period" (and "4. Variable Category" / "5. Variable(s)" in the
        # non-XY branch below) — same <p><strong> DOM node, same default
        # Streamlit font-size/weight/line-height/margin. The selectbox's own
        # native label is hidden via label_visibility="collapsed" so it never
        # renders a second, differently-styled label underneath. Identical
        # markdown construct + identical widget structure is what actually
        # pixel-aligns the dropdowns across columns — matching line count
        # alone (the previous fix) isn't sufficient when the two headers are
        # different DOM/CSS constructs.
        st.markdown("**X axis — Category**")
        if ORCAFLEX_AVAILABLE and xy_categories:
            x_category = st.selectbox(
                "X axis — Category", xy_categories, key="dash_xy_x_category",
                label_visibility="collapsed",
            )
            x_variable_options = _variable_options(var_source, x_category, raw_types_for_vars)
            st.markdown("**X axis — Variable**")
            variable_x = st.selectbox(
                "X axis — Variable",
                x_variable_options or ["— no variables —"],
                key="dash_xy_x_variable",
                disabled=not x_variable_options,
                label_visibility="collapsed",
            )
            if not x_variable_options:
                variable_x = None
        else:
            st.selectbox(
                "X axis — Category", ["— OrcFxAPI required —"], disabled=True,
                label_visibility="collapsed",
            )
            st.markdown("**X axis — Variable**")
            st.selectbox(
                "X axis — Variable", ["— OrcFxAPI required —"], disabled=True,
                label_visibility="collapsed",
            )

    with c5:
        # See c4 above — identical bold-markdown heading + collapsed native
        # label pattern, so "Y axis — Category" pixel-matches "X axis —
        # Category" and "6. Period".
        st.markdown("**Y axis — Category**")
        if ORCAFLEX_AVAILABLE and xy_categories:
            y_default = 1 if len(xy_categories) > 1 else 0
            y_category = st.selectbox(
                "Y axis — Category", xy_categories, index=y_default, key="dash_xy_y_category",
                label_visibility="collapsed",
            )
            y_variable_options = _variable_options(var_source, y_category, raw_types_for_vars)
            st.markdown("**Y axis — Variable**")
            variable_y = st.selectbox(
                "Y axis — Variable",
                y_variable_options or ["— no variables —"],
                key="dash_xy_y_variable",
                disabled=not y_variable_options,
                label_visibility="collapsed",
            )
            if not y_variable_options:
                variable_y = None
        else:
            st.selectbox(
                "Y axis — Category", ["— OrcFxAPI required —"], disabled=True,
                label_visibility="collapsed",
            )
            st.markdown("**Y axis — Variable**")
            st.selectbox(
                "Y axis — Variable", ["— OrcFxAPI required —"], disabled=True,
                label_visibility="collapsed",
            )

    if variable_x:
        variables = [variable_x]
    if variable_y and variable_y not in variables:
        variables.append(variable_y)
    if variable_x and variable_y and variable_x == variable_y:
        st.caption("Tip: pick different X and Y variables for a meaningful parametric plot.")
elif result_type == "3D Line Shape":
    # No Category/Variable(s) picker here — the shape is always the Position
    # category's X, Y, Z RangeGraph variables; the only real choice is which
    # single statistic is applied consistently across all three axes.
    with c4:
        st.markdown("**4. Statistic**")
        if ORCAFLEX_AVAILABLE:
            statistic_3d = st.selectbox(
                "Statistic",
                ["Mean", "Min", "Max"],
                key="dash_3d_statistic",
                label_visibility="collapsed",
                help=(
                    "Applied consistently across X, Y, and Z for one physically coherent 3D "
                    "path. Mean is the default — per-axis Min/Max can occur at different time "
                    "steps and don't combine into a real static line shape."
                ),
            )
        else:
            statistic_3d = "Mean"
            st.selectbox(
                "Statistic", ["— OrcFxAPI required —"], disabled=True, label_visibility="collapsed"
            )

    with c5:
        st.markdown("**5. Axes**")
        st.selectbox(
            "Axes", ["X, Y, Z (Position)"], disabled=True, label_visibility="collapsed",
            help="3D Line Shape always plots the Position category's X, Y, Z RangeGraph variables.",
        )
    variables = ["Position"]
else:
    with c4:
        st.markdown("**4. Variable Category**")
        if ORCAFLEX_AVAILABLE and var_source:
            if use_rg_vars:
                categories = list(var_source.keys())
            else:
                categories = _variable_categories(
                    var_source,
                    raw_types_for_vars,
                    allow_end_loads=(result_type == "Time History"),
                )
            if not categories:
                categories = list(var_source.keys())
            category = st.selectbox(
                "Category", categories, key="dash_category", label_visibility="collapsed"
            )
        else:
            category = None
            st.selectbox("Category", ["— OrcFxAPI required —"], disabled=True, label_visibility="collapsed")

    with c5:
        st.markdown("**5. Variable(s)**")
        variable_options = []
        if ORCAFLEX_AVAILABLE and category and var_source:
            if use_rg_vars:
                # Range_Graph_variable_dict values are lists of variable names
                raw_vars = var_source.get(category, [])
                variable_options = list(raw_vars) if isinstance(raw_vars, (list, tuple)) else list(raw_vars.keys())
            else:
                variable_options = _variable_options(var_source, category, raw_types_for_vars)

        prev = st.session_state.get("dash_variables")
        if isinstance(prev, list) and variable_options:
            pruned = [v for v in prev if v in variable_options]
            if pruned != prev:
                st.session_state["dash_variables"] = pruned or variable_options[:1]
        elif variable_options and not prev:
            st.session_state["dash_variables"] = variable_options[:1]
        variables = st.multiselect(
            "Variables",
            variable_options,
            key="dash_variables",
            label_visibility="collapsed",
            disabled=not variable_options,
        )

with c6:
    st.markdown("**6. Period**")
    # Keep Period mounted for all types (disabled only where period is locked)
    # so session state / AppTest stay stable when Result Type switches.
    _period_default_idx = PERIOD_OPTIONS.index(DEFAULT_PERIOD) if DEFAULT_PERIOD in PERIOD_OPTIONS else 0
    period_choice = st.selectbox(
        "Period",
        PERIOD_OPTIONS,
        index=_period_default_idx,
        key="dash_period",
        disabled=(result_type in PERIOD_LOCKED_RESULT_TYPES),
        label_visibility="collapsed",
        help=(
            "3D Line Shape uses the whole-simulation envelope along arc length. "
            "Range Graph uses the same period options as Time History."
        ),
    )
    period_spec = "Whole Simulation" if result_type in PERIOD_LOCKED_RESULT_TYPES else period_choice
    if result_type not in PERIOD_LOCKED_RESULT_TYPES and period_choice == "Specified Period":
        pf, pt = st.columns(2)
        period_from = pf.number_input("From (s)", value=0.0, key="dash_p_from")
        period_to = pt.number_input("To (s)", value=100.0, key="dash_p_to")
        period_spec = {"period": period_choice, "period_from": period_from, "period_to": period_to}
    elif result_type in PERIOD_LOCKED_RESULT_TYPES:
        st.caption("Uses whole-simulation envelope along arc length.")

with c_gen:
    # Single spacer element matching the "6. Period" label height/line-count
    # above the selectbox — keeps the button's top aligned with the other
    # columns' widgets regardless of any caption text below the selectbox
    # (captions render *after* the widget, so they don't affect its top offset).
    st.markdown("**&nbsp;**", unsafe_allow_html=True)
    # Peek session state so Generate can validate before the checkbox widgets
    # below are drawn (defaults match the checkbox value=True).
    if result_type == "Range Graph":
        rg_statistics = [
            s
            for s, key in (
                ("min", "dash_rg_stat_min"),
                ("max", "dash_rg_stat_max"),
                ("mean", "dash_rg_stat_mean"),
            )
            if st.session_state.get(key, True)
        ]
    else:
        rg_statistics = list(RANGE_GRAPH_STATISTICS)
    if result_type == "X-Y Graph":
        can_generate = bool(
            ORCAFLEX_AVAILABLE and selected_parsed and variable_x and variable_y and loaded
        )
    elif result_type == "Range Graph":
        can_generate = bool(
            ORCAFLEX_AVAILABLE and line_like and variables and loaded and rg_statistics
        )
    elif result_type == "3D Line Shape":
        can_generate = bool(ORCAFLEX_AVAILABLE and line_like and loaded)
    else:
        can_generate = bool(ORCAFLEX_AVAILABLE and selected_parsed and variables and loaded)
    generate = st.button(
        "📈 Generate Results",
        type="primary",
        width="stretch",
        disabled=not can_generate,
        key="dash_generate",
    )

# Line position for Time History / X-Y only (Range Graph is arc-length envelope — no position_spec)
# Own row so the configure columns above stay height-balanced.
position_spec = None
needs_line_position = result_type in ("Time History", "X-Y Graph") and bool(line_like)
end_loads_selected = result_type == "Time History" and (
    is_end_load_category(category)
    or any(is_end_load_variable(v) for v in (variables or []))
)
if needs_line_position:
    if end_loads_selected:
        st.caption("End Loads — available only at **End A** / **End B** (not arc length).")
    else:
        st.caption("Line position — End A / End B / arc length (ignored for Vessel / Buoy / Environment).")
    position_spec = position_selector(
        "Line", container=st, key_prefix="dash_", ends_only=end_loads_selected
    )
elif result_type in ("Time History", "X-Y Graph") and selected_parsed:
    st.caption("Position applies only when Line objects are selected.")

# Range Graph statistics — which envelope traces to extract (default: all three)
if result_type == "Range Graph":
    st.caption("Statistics — choose which envelope values to extract along the line.")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        rg_want_min = st.checkbox("Min", value=True, key="dash_rg_stat_min")
    with sc2:
        rg_want_max = st.checkbox("Max", value=True, key="dash_rg_stat_max")
    with sc3:
        rg_want_mean = st.checkbox("Mean", value=True, key="dash_rg_stat_mean")
    rg_statistics = [
        s for s, on in (
            ("min", rg_want_min),
            ("max", rg_want_max),
            ("mean", rg_want_mean),
        )
        if on
    ]
    if not rg_statistics:
        st.warning("Select at least one statistic (Min, Max, or Mean) to generate a Range Graph.")

# ---------------------------------------------------------------------------
# Generate Results — branch by Result Type
# ---------------------------------------------------------------------------
if generate:
    frames = []
    merge_on = "Time"
    primary_variable = (variables[0] if variables else None) or variable_x
    object_names_for_rg = []
    xy_object_names = []
    object_names_for_3d = []
    errors = []

    if result_type == "3D Line Shape":
        primary_variable = f"Position ({statistic_3d})"

    spinner_label = {
        "Time History": "Extracting time history…",
        "Range Graph": "Extracting range graph…",
        "X-Y Graph": "Extracting X-Y graph…",
        "3D Line Shape": "Extracting 3D line shape…",
    }.get(result_type, "Extracting…")

    with st.spinner(spinner_label):
        by_file = {}
        for p in selected_parsed:
            by_file.setdefault(p["file"], []).append(p)

        if result_type == "Time History":
            for variable_name in variables:
                multi = len(variables) > 1
                for file_name, objs in by_file.items():
                    path = loaded.get(file_name)
                    if not path:
                        continue
                    env_objs = [o for o in objs if o["type"] == "Environment"]
                    other_objs = [o for o in objs if o["type"] != "Environment"]

                    if env_objs:
                        df_env = extract_environment_time_history(path, variable_name, period_spec)
                        if not df_env.empty:
                            label = f"{file_name}::Environment"
                            if multi:
                                label = f"{label} [{variable_name}]"
                            frames.append(df_env.rename(columns={"Environment": label}))

                    if other_objs:
                        names = [o["name"] for o in other_objs]
                        pos = position_spec if any(o["type"] == "Line" for o in other_objs) else None
                        df_obj = extract_time_history_multi_objects(
                            path, names, variable_name, pos, period_spec
                        )
                        if df_obj is not None and not df_obj.empty:
                            rename = {}
                            for c in df_obj.columns:
                                if c == "Time":
                                    continue
                                label = f"{file_name}::{c}"
                                if multi:
                                    label = f"{label} [{variable_name}]"
                                rename[c] = label
                            frames.append(df_obj.rename(columns=rename))

                try:
                    record_variable_usage(variable_name)
                except Exception:
                    pass

        elif result_type == "Range Graph":
            merge_on = "z"
            variable_name = variables[0]
            for file_name, objs in by_file.items():
                path = loaded.get(file_name)
                if not path:
                    continue
                for o in objs:
                    if o["type"] != "Line":
                        errors.append(f"Skipped {o['name']} ({o['type']}) — Range Graph is Line-only.")
                        continue
                    rg_df = extract_range_graph_data(path, o["name"], variable_name, period_spec)
                    if rg_df is None or rg_df.empty:
                        errors.append(f"No range data for {file_name}::{o['name']}.")
                        continue
                    keep_cols = ["z"] + [s for s in rg_statistics if s in rg_df.columns]
                    rg_df = rg_df[keep_cols]
                    label = f"{file_name}::{o['name']}"
                    object_names_for_rg.append(label)
                    renamed = rg_df.rename(
                        columns={c: f"{label}_{c}" for c in rg_df.columns if c != "z"}
                    )
                    frames.append(renamed)
            try:
                record_variable_usage(variable_name)
            except Exception:
                pass

        elif result_type == "3D Line Shape":
            merge_on = "arc_length"
            stat_key = statistic_3d.lower()
            for file_name, objs in by_file.items():
                path = loaded.get(file_name)
                if not path:
                    continue
                for o in objs:
                    if o["type"] != "Line":
                        errors.append(f"Skipped {o['name']} ({o['type']}) — 3D Line Shape is Line-only.")
                file_lines = [o for o in objs if o["type"] == "Line"]
                if not file_lines:
                    continue
                line_names = [o["name"] for o in file_lines]
                pos_df = extract_3D_position_data(path, line_names, selected_statistics=[stat_key])
                if pos_df is None or pos_df.empty or len(pos_df.columns) <= 1:
                    errors.append(f"No 3D position data for {file_name}.")
                    continue
                # Prefix columns with file for multi-file clarity, matching the Range Graph pattern.
                rename = {}
                for line_name in line_names:
                    label = f"{file_name}::{line_name}"
                    has_any_axis = False
                    for axis in ("X", "Y", "Z"):
                        col = f"{line_name}_{axis}"
                        if col in pos_df.columns:
                            rename[col] = f"{label}_{axis}"
                            has_any_axis = True
                    if has_any_axis and label not in object_names_for_3d:
                        object_names_for_3d.append(label)
                frames.append(pos_df.rename(columns=rename))
            try:
                record_variable_usage("Position")
            except Exception:
                pass

        else:  # X-Y Graph
            for file_name, objs in by_file.items():
                path = loaded.get(file_name)
                if not path:
                    continue
                # Environment not supported by extract_xy_time_history_data
                other_objs = [o for o in objs if o["type"] != "Environment"]
                env_objs = [o for o in objs if o["type"] == "Environment"]
                if env_objs:
                    errors.append(
                        f"Skipped Environment in {file_name} — X-Y Graph uses object time histories."
                    )
                if not other_objs:
                    continue
                names = [o["name"] for o in other_objs]
                pos = position_spec if any(o["type"] == "Line" for o in other_objs) else None
                df_xy = extract_xy_dataframe(
                    path, names, variable_x, variable_y, pos, period_spec
                )
                if df_xy is None or df_xy.empty:
                    errors.append(f"No X-Y data for {file_name}.")
                    continue
                # Prefix columns with file for multi-file clarity
                rename = {}
                for c in df_xy.columns:
                    if c == "Time":
                        continue
                    # c is like Name_x / Name_y
                    base = c.rsplit("_", 1)
                    if len(base) == 2 and base[1] in ("x", "y"):
                        new_name = f"{file_name}::{base[0]}"
                        rename[c] = f"{new_name}_{base[1]}"
                        if new_name not in xy_object_names:
                            xy_object_names.append(new_name)
                    else:
                        rename[c] = f"{file_name}::{c}"
                frames.append(df_xy.rename(columns=rename))
            for v in (variable_x, variable_y):
                if v:
                    try:
                        record_variable_usage(v)
                    except Exception:
                        pass

        if frames:
            merged = frames[0]
            for extra in frames[1:]:
                if merge_on in merged.columns and merge_on in extra.columns:
                    merged = pd.merge(merged, extra, on=merge_on, how="outer")
                else:
                    merged = pd.concat([merged, extra], axis=1)
            # Outer merges scramble row order; sort so Time/z plots stay chronological.
            if merge_on in merged.columns:
                merged = merged.sort_values(merge_on, kind="mergesort").reset_index(drop=True)
            st.session_state["dash_result"] = {
                "df": merged,
                "result_type": result_type,
                "variable": primary_variable,
                "variable_x": variable_x,
                "variable_y": variable_y,
                "variables": variables,
                "objects": selected_parsed,
                "object_names_rg": object_names_for_rg,
                "object_names_xy": xy_object_names,
                "object_names_3d": object_names_for_3d,
                "statistic": stat_key if result_type == "3D Line Shape" else None,
                "statistics": list(rg_statistics) if result_type == "Range Graph" else None,
                "period": period_spec,
                "position": position_spec,
            }
            st.session_state["last_extracted"] = {
                "df": merged,
                "variable": primary_variable,
                "object_type": raw_types_for_vars[0] if raw_types_for_vars else None,
                "result_type": result_type,
            }
            st.session_state["extraction_count"] = st.session_state.get("extraction_count", 0) + 1

    for msg in errors:
        st.warning(msg)

    result_df = st.session_state.get("dash_result", {}).get("df")
    if result_df is None or result_df.empty:
        st.error("No data extracted. Verify selections and that the model contains results.")
    else:
        if result_type == "X-Y Graph":
            st.success(f"Generated X-Y results for **{variable_x}** vs **{variable_y}**.")
        elif result_type == "3D Line Shape":
            st.success(
                f"Generated 3D Line Shape results for **{len(object_names_for_3d)} line(s)** "
                f"(statistic: **{statistic_3d}**)."
            )
        else:
            st.success(f"Generated {result_type} results for **{', '.join(variables)}**.")

# ===========================================================================
# STEP 7 — Results & Visualization
# Vertical stack: compact controls → full-width chart → full-width data
# ===========================================================================
st.markdown(
    '<div class="panel"><div class="panel-head"><h2>'
    '<span class="step-badge">7</span>Results &amp; Visualization</h2></div></div>',
    unsafe_allow_html=True,
)

result = st.session_state.get("dash_result", {})
df = result.get("df")
stored_type = result.get("result_type", result_type)
active_variable = result.get("variable")
units = (get_variable_units(active_variable) or "") if (active_variable and ORCAFLEX_AVAILABLE) else ""
units_x = (get_variable_units(result.get("variable_x")) or "") if (result.get("variable_x") and ORCAFLEX_AVAILABLE) else ""
units_y = (get_variable_units(result.get("variable_y")) or "") if (result.get("variable_y") and ORCAFLEX_AVAILABLE) else ""

# View modes depend on result type
if stored_type == "Range Graph":
    view_modes = ["Range Graph", "Data Table"]
elif stored_type == "X-Y Graph":
    view_modes = ["X-Y Chart", "Data Table", "Gauge / KPI"]
elif stored_type == "3D Line Shape":
    view_modes = ["3D Line Shape", "Data Table"]
else:
    view_modes = ["Line Chart", "3D View", "Data Table", "Gauge / KPI"]

current_mode = st.session_state.get("dash_view_mode", view_modes[0])
if current_mode not in view_modes:
    current_mode = view_modes[0]
    st.session_state["dash_view_mode"] = current_mode

# --- Top row: compact visualization controls + display options ---
st.markdown('<div class="viz-toolbar-mark"></div>', unsafe_allow_html=True)
ctrl_type, ctrl_opts = st.columns([2.4, 1.6], gap="medium")
with ctrl_type:
    st.markdown('<p class="viz-section-label">Visualization type</p>', unsafe_allow_html=True)
    view_mode = st.radio(
        "View mode",
        view_modes,
        index=view_modes.index(current_mode),
        key="dash_view_mode",
        horizontal=True,
        label_visibility="collapsed",
    )
with ctrl_opts:
    st.markdown('<p class="viz-section-label">Display options</p>', unsafe_allow_html=True)
    opt_l, opt_g, opt_a = st.columns(3)
    with opt_l:
        show_legend = st.checkbox("Legend", value=True, key="dash_legend",
                                   help="Show/hide the in-plot series legend.")
    with opt_g:
        show_grid = st.checkbox("Grid", value=True, key="dash_grid",
                                 help="Show/hide the chart gridlines.")
    with opt_a:
        st.checkbox(
            "Animate",
            value=False,
            key="dash_animate",
            disabled=True,
            help="Frame-by-frame animation is not implemented for this chart yet.",
        )

meta_bits = [f"Result type: <strong>{stored_type}</strong>"]
if result.get("position") is not None:
    meta_bits.append(f"Line position: <strong>{result.get('position')}</strong>")
meta_bits.append("Interactive Plotly charts — zoom, pan, autoscale, and download from the toolbar.")
st.markdown(
    f'<p class="viz-meta">{" · ".join(meta_bits)}</p>',
    unsafe_allow_html=True,
)

# --- Series to display — filters which traces exist *before* the figure is
# built, so the on-screen chart, PNG download, and any Report export all agree
# on what's included (Plotly's legend-click state never leaves the browser). ---
has_result = df is not None and not (hasattr(df, "empty") and df.empty)
chart_df = df
chart_object_names_rg = result.get("object_names_rg") or []
chart_object_names_xy = result.get("object_names_xy") or []
chart_object_names_3d = result.get("object_names_3d") or []
if has_result:
    st.markdown('<p class="viz-section-label">Series to display</p>', unsafe_allow_html=True)
    if stored_type == "Range Graph":
        chart_object_names_rg = object_multiselect(
            chart_object_names_rg,
            key="dash_series_rg",
            help="Choose which line objects appear in the chart, PNG download, and Report exports.",
        )
        extracted_stats = [
            s for s in RANGE_GRAPH_STATISTICS
            if s in (result.get("statistics") or list(RANGE_GRAPH_STATISTICS))
        ]
        # Infer from columns if an older result payload lacks "statistics"
        if not extracted_stats and df is not None:
            extracted_stats = [
                s for s in RANGE_GRAPH_STATISTICS
                if any(str(c).endswith(f"_{s}") for c in df.columns)
            ] or list(RANGE_GRAPH_STATISTICS)
        st.markdown('<p class="viz-section-label">Statistics to display</p>', unsafe_allow_html=True)
        viz_cols = st.columns(len(extracted_stats) or 1)
        viz_statistics = []
        for col, stat in zip(viz_cols, extracted_stats):
            with col:
                if st.checkbox(
                    stat.capitalize(),
                    value=True,
                    key=f"dash_rg_viz_{stat}",
                    help="Show or hide this envelope statistic on the chart for all selected lines.",
                ):
                    viz_statistics.append(stat)
        if extracted_stats and not viz_statistics:
            st.caption("Select at least one statistic to display on the chart.")
        suffixes = tuple(f"_{s}" for s in viz_statistics) if viz_statistics else ("__none__",)
        chart_df = filter_columns_for_objects(df, {"z"}, chart_object_names_rg, suffixes)
        # Stash for the figure call below
        st.session_state["_dash_rg_viz_statistics"] = viz_statistics
    elif stored_type == "X-Y Graph":
        if not chart_object_names_xy:
            chart_object_names_xy = sorted({c[:-2] for c in df.columns if c.endswith("_x")})
        chart_object_names_xy = object_multiselect(
            chart_object_names_xy,
            key="dash_series_xy",
            help="Choose which objects appear in the chart, PNG download, and Report exports.",
        )
        chart_df = filter_columns_for_objects(df, {"Time"}, chart_object_names_xy, ("_x", "_y"))
    elif stored_type == "3D Line Shape":
        chart_object_names_3d = object_multiselect(
            chart_object_names_3d,
            key="dash_series_3d",
            help="Choose which line objects appear in the 3D shape plot, PNG download, and Report exports.",
        )
        chart_df = filter_columns_for_objects(df, {"arc_length"}, chart_object_names_3d, ("_X", "_Y", "_Z"))
    else:
        chart_df, _, _ = series_multiselect(
            df, {"Time"},
            key="dash_series_th",
            help="Choose which series appear in the chart, PNG download, and Report exports.",
        )
        # Keep Reports.py in sync with the same explicit selection — it reads
        # last_extracted rather than rebuilding from the full unfiltered df.
        _last = dict(st.session_state.get("last_extracted") or {})
        if _last:
            _last["df"] = chart_df
            st.session_state["last_extracted"] = _last
    st.caption(SERIES_SELECTOR_CAPTION)

# --- Full-width main view ---
st.markdown('<p class="viz-section-label">Main view</p>', unsafe_allow_html=True)
if df is None or (hasattr(df, "empty") and df.empty):
    viz_placeholder("Your results will appear here")
elif stored_type == "Range Graph" and view_mode == "Range Graph":
    fig = range_graph_figure(
        chart_df,
        chart_object_names_rg,
        active_variable or "Variable",
        show_legend=show_legend,
        show_grid=show_grid,
        statistics=st.session_state.get("_dash_rg_viz_statistics")
        or result.get("statistics")
        or RANGE_GRAPH_STATISTICS,
    )
    render_plotly_chart(fig)
elif stored_type == "X-Y Graph" and view_mode == "X-Y Chart":
    fig = xy_figure(
        chart_df,
        result.get("variable_x") or "X",
        result.get("variable_y") or "Y",
        units_x=units_x,
        units_y=units_y,
        object_names=chart_object_names_xy or None,
        show_legend=show_legend,
        show_grid=show_grid,
    )
    render_plotly_chart(fig)
elif stored_type == "3D Line Shape" and view_mode == "3D Line Shape":
    fig = line_shape_3d_figure(
        chart_df,
        chart_object_names_3d,
        statistic=result.get("statistic") or "mean",
        show_legend=show_legend,
        show_grid=show_grid,
    )
    render_plotly_chart(fig)
elif view_mode == "Line Chart":
    fig = time_history_figure(
        chart_df, active_variable or "Variable", units,
        show_legend=show_legend, show_grid=show_grid,
    )
    render_plotly_chart(fig)
elif view_mode == "3D View":
    st.markdown(
        """
        <div class="viz-placeholder">
          <div>
            <div class="icon">🧊</div>
            <div style="font-weight:700;color:var(--navy);">3D View</div>
            <div class="faint" style="margin-top:0.4rem;">
              Spatial / 3D model visualization is not available in this Streamlit console.<br/>
              Use <span class="mode-hint">Line Chart</span> or open the model in OrcaFlex for 3D replay.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
elif view_mode == "Data Table":
    styled_dataframe(chart_df, height=480)
else:  # Gauge / KPI
    skip = {"Time", "z"}
    value_cols = [c for c in chart_df.columns if c not in skip]
    if not value_cols:
        viz_placeholder("No numeric series for gauges")
    else:
        gcols = st.columns(min(3, len(value_cols)))
        for i, col in enumerate(value_cols[:6]):
            series = chart_df[col].dropna()
            if series.empty:
                continue
            with gcols[i % len(gcols)]:
                render_plotly_chart(
                    kpi_gauge_figure(
                        float(series.iloc[-1]), col,
                        vmin=float(series.min()), vmax=float(series.max()),
                    ),
                )

# --- Full-width data table + export (below chart) ---
data_expanded = view_mode != "Data Table"
with st.expander("Data", expanded=data_expanded):
    if df is None or (hasattr(df, "empty") and df.empty):
        st.caption("Export becomes available after Generate Results.")
        st.dataframe(
            pd.DataFrame(columns=["Time", "Value"]),
            height=280,
            width="stretch",
            hide_index=True,
        )
    else:
        st.dataframe(df, height=320, width="stretch", hide_index=True)
        stem = (active_variable or result.get("variable_x") or "data").replace(" ", "_")
        fname = f"{stored_type.lower().replace(' ', '_').replace('-', '')}_{stem}.csv"
        download_button_for_df(df, fname, label="⬇ Export CSV", key="dash_export")

st.markdown(
    '<div class="ops-footer">ORCAFLEX Post Result Simulation · '
    '<strong>Ops Console</strong> · Local engineering workspace</div>',
    unsafe_allow_html=True,
)