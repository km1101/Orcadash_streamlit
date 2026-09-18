"""
Bridge to the shared OrcaFlex extraction modules in ``backend/var_and_func``,
plus local file/model helper functions used across pages.

This is the single place that adds ``backend/`` to ``sys.path`` and imports
the extraction package, so every page and component gets the same modules
(and the same availability flag) without repeating the import dance.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.config import BACKEND_DIR, UPLOAD_DIR

sys.path.insert(0, str(BACKEND_DIR))

ORCAFXAPI_AVAILABLE = False
ORCAFLEX_AVAILABLE = False
IMPORT_ERROR = None
PYTHON_EXECUTABLE = sys.executable


def _orcfxapi_setup_hint() -> str:
    return (
        f"Python running this app: {PYTHON_EXECUTABLE}. "
        "OrcFxAPI ships with OrcaFlex (not PyPI). Use the project virtualenv "
        "(run `run_app.bat` from the repo root) or install OrcFxAPI into this "
        "interpreter from your OrcaFlex program folder (OrcFxAPI.py + OrcFxAPIConfig.py)."
    )


def _backend_deps_hint(missing: str) -> str:
    return (
        f"Missing dependency `{missing}` for {PYTHON_EXECUTABLE}. "
        f"Install with: `{PYTHON_EXECUTABLE} -m pip install -r requirements.txt` "
        "or start the app via `run_app.bat` / `.venv\\Scripts\\streamlit.exe`."
    )


try:
    import OrcFxAPI

    ORCAFXAPI_AVAILABLE = True
except ImportError as e:
    IMPORT_ERROR = f"{e}. {_orcfxapi_setup_hint()}"
except Exception as e:
    IMPORT_ERROR = f"OrcFxAPI failed to load: {e}. {_orcfxapi_setup_hint()}"

if ORCAFXAPI_AVAILABLE:
    try:
        from var_and_func.variables import variables_dict, Range_Graph_variable_dict
        from var_and_func.variables import (
            END_LOAD_CATEGORIES,
            is_end_load_category,
            is_end_load_variable,
            get_variable_units,
        )
        from var_and_func.variable_mapping import get_variables_for_object_types
        from var_and_func.extract_multi_objects import extract_time_history_multi_objects
        from var_and_func.time_history import (
            calculate_statistics_summary,
            extract_xy_time_history_data,
            resolve_period,
        )
        from var_and_func.statistics_utils import (
            compute_histogram,
            compute_extended_statistics_summary,
            compute_power_spectral_density,
        )
        from var_and_func.frequent_variables import record_variable_usage

        # Reload range_graph so Streamlit hot-reloads pick up signature changes
        # under backend/ (outside the watched streamlit_app tree).
        import importlib
        import var_and_func.range_graph as _range_graph_mod

        _range_graph_mod = importlib.reload(_range_graph_mod)
        extract_range_graph_data = _range_graph_mod.extract_range_graph_data
        extract_3D_position_data = _range_graph_mod.extract_3D_position_data

        ORCAFLEX_AVAILABLE = True
        IMPORT_ERROR = None
    except ImportError as e:
        name = getattr(e, "name", None) or str(e)
        IMPORT_ERROR = _backend_deps_hint(name)
    except Exception as e:
        IMPORT_ERROR = f"OrcaFlex backend failed to initialize: {e}"

if not ORCAFLEX_AVAILABLE:
    variables_dict, Range_Graph_variable_dict = {}, {}
    END_LOAD_CATEGORIES = ()

    def is_end_load_category(*_a, **_k):
        return False

    def is_end_load_variable(*_a, **_k):
        return False

    def get_variables_for_object_types(*_a, **_k):
        return []

    def get_variable_units(*_a, **_k):
        return ""

    def extract_time_history_multi_objects(*_a, **_k):
        return pd.DataFrame()

    def extract_range_graph_data(*_a, **_k):
        return pd.DataFrame()

    def extract_3D_position_data(*_a, **_k):
        return pd.DataFrame(columns=["arc_length"])

    def extract_xy_time_history_data(*_a, **_k):
        return []

    def calculate_statistics_summary(*_a, **_k):
        return pd.DataFrame()

    def resolve_period(*_a, **_k):
        return None

    def compute_histogram(*_a, **_k):
        return {"bin_centers": [], "density": []}

    def compute_extended_statistics_summary(*_a, **_k):
        return pd.DataFrame()

    def compute_power_spectral_density(*_a, **_k):
        return {"frequency": [], "psd": [], "peak_frequency": None, "peak_period": None}

    def record_variable_usage(*_a, **_k):
        return None


# --- Session state -----------------------------------------------------------

def ensure_session_state():
    """Initialize the small pieces of shared state used across pages.

    Call at the top of every page (idempotent via ``setdefault``) so pages
    can be visited in any order.
    """
    st.session_state.setdefault("loaded_files", {})     # display_name -> path str
    st.session_state.setdefault("active_file", None)    # display_name of the current focus file
    st.session_state.setdefault("extraction_count", 0)  # incremented on every successful extraction
    st.session_state.setdefault("last_extracted", {})   # page-scoped cache of the most recent extraction
    # Dashboard (wireframe 1–7) workflow state
    st.session_state.setdefault("dash_selected_keys", [])   # list of "file||type||name"
    st.session_state.setdefault("dash_catalog_filter", "All")
    st.session_state.setdefault("dash_process_stage", 0)    # 0 idle … 4 ready
    st.session_state.setdefault("dash_process_progress", 0.0)
    st.session_state.setdefault("dash_result", {})          # last Generate Results payload
    st.session_state.setdefault("dash_view_mode", "Line Chart")
    st.session_state.setdefault("dash_result_type", "Time History")
    st.session_state.setdefault("sidebar_collapsed", False)


def register_loaded_file(display_name, file_path):
    """Add a file to session state + persisted recent-files list."""
    from utils.cache import add_recent_file
    st.session_state["loaded_files"][display_name] = str(file_path)
    st.session_state["active_file"] = display_name
    add_recent_file(file_path, display_name)


# --- File handling ---------------------------------------------------------

def save_uploaded_file(uploaded_file):
    """Persist a Streamlit UploadedFile to the local upload directory."""
    dest = UPLOAD_DIR / uploaded_file.name
    if not dest.exists():
        with open(dest, "wb") as f:
            f.write(uploaded_file.getbuffer())
    return dest


def scan_folder_for_sim_files(folder_path):
    """Recursively find .sim files under a local folder path."""
    root = Path(folder_path)
    if not folder_path or not root.exists() or not root.is_dir():
        return []
    return sorted(root.rglob("*.sim"))


# --- Model summary -----------------------------------------------------------

def get_model_summary(file_path):
    """Load a .sim model once and summarize object counts + simulated duration.

    Used by the Home dashboard's stat cards and the Load Files preview panel.
    Callers should go through ``utils.cache.get_cached_model_summary`` rather
    than calling this directly, so repeat visits don't reload the model.
    """
    summary = {
        "file_path": str(file_path),
        "file_name": os.path.basename(file_path),
        "file_size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2) if os.path.exists(file_path) else 0.0,
        "objects": {"Line": [], "6DBuoy": [], "3DBuoy": [], "Vessel": [], "Winch": [], "Link": []},
        "duration_s": None,
        "error": None,
    }
    if not ORCAFLEX_AVAILABLE:
        summary["error"] = IMPORT_ERROR
        return summary

    try:
        model = OrcFxAPI.Model(str(file_path))
        objects = {"Line": [], "6DBuoy": [], "3DBuoy": [], "Vessel": [], "Winch": [], "Link": []}
        for obj in model.objects:
            if obj.type == OrcFxAPI.otLine:
                objects["Line"].append(obj.Name)
            elif obj.type == OrcFxAPI.ot6DBuoy:
                objects["6DBuoy"].append(obj.Name)
            elif obj.type == OrcFxAPI.ot3DBuoy:
                objects["3DBuoy"].append(obj.Name)
            elif obj.type == OrcFxAPI.otVessel:
                objects["Vessel"].append(obj.Name)
            elif obj.type == OrcFxAPI.otWinch:
                objects["Winch"].append(obj.Name)
            elif obj.type == OrcFxAPI.otLink:
                objects["Link"].append(obj.Name)
        summary["objects"] = objects

        time = model.general.TimeHistory("Time")
        if time is not None and len(time) > 0:
            summary["duration_s"] = float(time[-1] - time[0])
    except Exception as e:
        summary["error"] = str(e)

    return summary


# --- Period resolution --------------------------------------------------------

def period_from_spec(period_spec):
    """Resolve a UI period selection (string or dict) to an OrcFxAPI period."""
    if not ORCAFLEX_AVAILABLE:
        return None
    if period_spec is None:
        return None
    if isinstance(period_spec, str):
        return resolve_period(period_spec)
    if isinstance(period_spec, dict):
        period_name = period_spec.get("period", "Whole Simulation")
        if period_name == "Specified Period":
            return resolve_period(period_name, period_spec.get("period_from"), period_spec.get("period_to"))
        return resolve_period(period_name)
    return period_spec


# --- Environment extraction ----------------------------------------------------
# Environment is a singleton per model (OrcFxAPI.otEnvironment), not iterated
# via model.objects the way Line/Vessel/Buoy are, so it needs its own helper.

def extract_environment_time_history(file_path, variable_name, period_spec=None):
    if not ORCAFLEX_AVAILABLE:
        return pd.DataFrame()
    try:
        model = OrcFxAPI.Model(str(file_path))
        period = period_from_spec(period_spec)
        if period is None:
            time = model.general.TimeHistory("Time")
            values = model.environment.TimeHistory(variable_name)
        else:
            time = model.general.TimeHistory("Time", period)
            values = model.environment.TimeHistory(variable_name, period)
        return pd.DataFrame({"Time": time, "Environment": values})
    except Exception as e:
        print(f"Error extracting environment variable '{variable_name}' from {file_path}: {e}")
        return pd.DataFrame()


def xy_data_to_dataframe(data_list):
    """Convert ``extract_xy_time_history_data`` list[dict] rows into a float DataFrame.

    Backend rows use string keys ``time``, ``{name}_x``, ``{name}_y``. Returns a
    DataFrame with ``Time`` plus numeric ``*_x`` / ``*_y`` columns, or empty on failure.
    """
    if not data_list:
        return pd.DataFrame()
    try:
        df = pd.DataFrame(data_list)
        if "time" in df.columns:
            df = df.rename(columns={"time": "Time"})
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        print(f"Error converting X-Y data to DataFrame: {e}")
        return pd.DataFrame()


def extract_xy_dataframe(file_path, object_names, variable_x, variable_y, position_spec=None, period_spec=None):
    """X-Y graph extraction returning a numeric DataFrame (empty if unavailable)."""
    if not ORCAFLEX_AVAILABLE:
        return pd.DataFrame()
    try:
        data_list = extract_xy_time_history_data(
            file_path, object_names, variable_x, variable_y, position_spec, period_spec
        )
        return xy_data_to_dataframe(data_list)
    except Exception as e:
        print(f"Error extracting X-Y data from {file_path}: {e}")
        return pd.DataFrame()
