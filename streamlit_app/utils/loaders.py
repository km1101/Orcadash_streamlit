"""
Bridge to the shared OrcaFlex extraction modules in ``backend/var_and_func``,
plus local file/model helper functions used across pages.

This is the single place that adds ``backend/`` to ``sys.path`` and imports
the extraction package, so every page and component gets the same modules
(and the same availability flag) without repeating the import dance.
"""
import ctypes
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
ORCAFLEX_DLL_VERSION = None
ORCAFLEX_DLL_PATH = None
ORCAFLEX_INSTALLS = []
PYTHON_EXECUTABLE = sys.executable

_WIN_PLATFORM = "Win64" if ctypes.sizeof(ctypes.c_void_p) == 8 else "Win32"
_SEARCH_ROOTS = (
    r"C:\Program Files (x86)\Orcina\OrcaFlex",
    r"C:\Program Files\Orcina\OrcaFlex",
)


def _is_streamlit_community_cloud() -> bool:
    return "/home/adminuser/venv/" in Path(PYTHON_EXECUTABLE).as_posix()


def _version_sort_key(install: dict) -> tuple:
    """Newest full install first; Demo and unnumbered installs last."""
    parts = [
        int(chunk) for chunk in str(install["version"]).split(".") if chunk.isdigit()
    ]
    return (
        0 if install["edition"] == "Normal" else 1,
        0 if parts else 1,
        [-p for p in parts],
    )


def _add_install(installs: dict, version: str, edition: str, install_dir: str) -> None:
    if not install_dir:
        return
    install_dir = os.path.normpath(install_dir)
    dll_path = os.path.join(install_dir, "OrcFxAPI", _WIN_PLATFORM, "OrcFxAPI.dll")
    if not os.path.isfile(dll_path) or dll_path.lower() in installs:
        return
    installs[dll_path.lower()] = {
        "version": version,
        "edition": edition,
        "install_dir": install_dir,
        "dll_path": dll_path,
    }


def _registry_installs(installs: dict) -> None:
    try:
        import winreg
    except ImportError:
        return

    views = (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY)
    for view in views:
        try:
            root = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"Software\Orcina\OrcaFlex",
                0,
                winreg.KEY_READ | view,
            )
        except OSError:
            continue

        with root:
            # Versioned keys first so installs keep their real version label; the
            # unversioned key is the same install under a generic name.
            subkeys = []
            index = 0
            while True:
                try:
                    name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                if name != "Installation Directory":
                    subkeys.append(f"{name}\\Installation Directory")
            subkeys.append("Installation Directory")

            for subkey in subkeys:
                version = subkey.split("\\")[0]
                if version == "Installation Directory":
                    version = "unknown"
                try:
                    key = winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | view)
                except OSError:
                    continue
                with key:
                    for edition in ("Normal", "Demo"):
                        try:
                            path = winreg.QueryValueEx(key, edition)[0]
                        except OSError:
                            continue
                        _add_install(installs, version, edition, path)


def _filesystem_installs(installs: dict) -> None:
    for root in _SEARCH_ROOTS:
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            path = os.path.join(root, entry)
            if os.path.isdir(path):
                edition = "Demo" if entry.lower() == "demo" else "Normal"
                _add_install(installs, entry, edition, path)


def discover_orcaflex_installs() -> list:
    """All OrcaFlex installs on this machine, newest licensed version first."""
    if sys.platform != "win32":
        return []
    installs: dict = {}
    _registry_installs(installs)
    _filesystem_installs(installs)
    return sorted(installs.values(), key=_version_sort_key)


def _register_dll_dir(dll_path: str) -> None:
    dll_dir = os.path.dirname(dll_path)
    if hasattr(os, "add_dll_directory") and os.path.isdir(dll_dir):
        try:
            os.add_dll_directory(dll_dir)
        except OSError:
            pass
    os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")


# Creates and destroys a bare model through the raw C API, which is the cheapest
# way to find out whether a given install can actually claim a licence.
_LICENCE_PROBE = r"""
import ctypes, sys

class Params(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("Size", ctypes.c_int), ("ThreadCount", ctypes.c_int)]

lib = ctypes.WinDLL(sys.argv[1])
handle = ctypes.c_void_p()
status = ctypes.c_int(0)
params = Params()
params.Size = ctypes.sizeof(params)
params.ThreadCount = 1
if hasattr(lib, "C_CreateModel2"):
    lib.C_CreateModel2(ctypes.byref(handle), ctypes.byref(params), ctypes.byref(status))
else:
    lib.C_CreateModel(ctypes.byref(handle), ctypes.byref(status))
if status.value == 0:
    lib.C_DestroyModel(handle, ctypes.byref(status))
sys.exit(0 if status.value == 0 else 1)
"""


def _licence_available(dll_path: str) -> bool:
    """Probe a licence in a throwaway process.

    Loading several OrcaFlex versions into one process is unsupported, and an
    unlicensed version prints its own dialogs/errors, so the probe is isolated.
    """
    import subprocess

    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            [sys.executable, "-c", _LICENCE_PROBE, dll_path],
            capture_output=True,
            timeout=60,
            creationflags=creationflags,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _activate_orcaflex_install() -> None:
    """Pick a licensed OrcFxAPI.dll before OrcFxAPI is imported.

    OrcFxAPI binds its DLL at import time, so the choice has to be made here:
    walk the installed versions newest-first and keep the first one whose
    licence actually grants a model, falling back to the newest that loads.
    """
    global ORCAFLEX_INSTALLS, ORCAFLEX_DLL_PATH
    if sys.platform != "win32":
        return

    ORCAFLEX_INSTALLS = discover_orcaflex_installs()

    override = os.environ.get("ORCAFLEX_DLL_PATH") or os.environ.get("_OrcFxAPIlib")
    candidates = list(ORCAFLEX_INSTALLS)
    if override and os.path.isfile(override):
        candidates.insert(
            0,
            {
                "version": "override",
                "edition": "Normal",
                "install_dir": os.path.dirname(override),
                "dll_path": override,
            },
        )

    chosen = None
    for install in candidates:
        install["licensed"] = _licence_available(install["dll_path"])
        if install["licensed"] and chosen is None:
            chosen = install

    if chosen is None and candidates:
        chosen = candidates[0]
    if chosen is None:
        return

    _register_dll_dir(chosen["dll_path"])
    try:
        import OrcFxAPIConfig

        OrcFxAPIConfig.setLibPath(chosen["dll_path"], childProcessInherit=True)
    except ImportError:
        os.environ["_OrcFxAPIlib"] = chosen["dll_path"]
    ORCAFLEX_DLL_PATH = chosen["dll_path"]


_activate_orcaflex_install()


def _orcfxapi_setup_hint() -> str:
    if sys.platform != "win32":
        return (
            "OrcaFlex and OrcFxAPI require Windows, so extractions cannot run on this "
            f"host ({PYTHON_EXECUTABLE}). Run the app on the Windows PC where OrcaFlex "
            "is installed."
        )
    return (
        "Install OrcaFlex on this computer with a valid license, then "
        f"`{PYTHON_EXECUTABLE} -m pip install -r requirements.txt` so OrcFxAPI is "
        "available to the interpreter running this app. Prefer starting the app with "
        "`run_app.bat` from the repo root."
    )


def _backend_deps_hint(missing: str) -> str:
    return (
        f"Missing Python package `{missing}` for {PYTHON_EXECUTABLE}. "
        f"Run `{PYTHON_EXECUTABLE} -m pip install -r requirements.txt` "
        "or start via `run_app.bat` / `.venv\\Scripts\\streamlit.exe` (Windows)."
    )


def header_status_for_api() -> tuple[str, str]:
    if ORCAFLEX_AVAILABLE:
        return "OrcFxAPI OK", "ok"
    return "API OFFLINE", "warn"


def show_orcaflex_unavailable_banner() -> None:
    if ORCAFLEX_AVAILABLE:
        return

    if sys.platform != "win32":
        where = (
            "**Streamlit Community Cloud**"
            if _is_streamlit_community_cloud()
            else "a **Linux/macOS host**"
        )
        st.warning(
            f"This copy of the app is hosted on {where}, where **OrcaFlex** cannot run — "
            "it is Windows-only and needs a local license, so a remote server cannot reach "
            "the OrcaFlex install on your own PC. Uploads and the UI work here, but "
            "**Generate Results** and extractions are disabled."
        )
        st.caption(
            "To run extractions, start the app on your Windows PC with `run_app.bat` "
            "(or `.venv\\Scripts\\streamlit.exe run streamlit_app\\app.py`) and open "
            "http://localhost:8501."
        )
        st.caption(f"Host Python: `{PYTHON_EXECUTABLE}`")
        return

    st.warning(
        "OrcFxAPI is not available. Install **OrcaFlex** on this machine with a valid "
        "**license** and ensure **OrcFxAPI** is installed for the Python running this app. "
        "You can still upload files and browse the UI; **Generate Results** and extractions "
        "stay disabled until OrcaFlex and OrcFxAPI are set up."
    )
    st.caption(f"Python running this app: `{PYTHON_EXECUTABLE}`")
    st.caption(
        "Start the app with **`run_app.bat`** from the repo root so Streamlit uses the "
        "same Python as your OrcaFlex/OrcFxAPI install."
    )
    if IMPORT_ERROR:
        st.caption(IMPORT_ERROR)


def verify_orcaflex_runtime() -> tuple[bool, str]:
    """Check the DLL loads *and* the license grants a working model."""
    if not ORCAFLEX_AVAILABLE:
        return False, IMPORT_ERROR or "Backend not initialized."
    try:
        version = OrcFxAPI.DLLVersion()
        OrcFxAPI.Model()
        return True, f"OrcaFlex {version} licensed and ready — {ORCAFLEX_DLL_PATH}"
    except Exception as e:
        return False, f"OrcaFlex {ORCAFLEX_DLL_PATH} failed the license check: {e}"


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

        try:
            ORCAFLEX_DLL_VERSION = OrcFxAPI.DLLVersion()
        except Exception as e:
            raise RuntimeError(
                f"OrcFxAPI imported but OrcaFlex DLL/license check failed: {e}"
            ) from e

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
