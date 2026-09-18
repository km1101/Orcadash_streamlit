"""
App-wide constants: branding, paths, and navigation structure.

Centralizing these here means the sidebar and every page reference the same
single source of truth instead of duplicating labels.
"""
from pathlib import Path

APP_NAME = "ORCAFLEX Post Result Simulation"
APP_TAGLINE = "Engineering results console"
APP_ICON = "🌊"
BRAND_SHORT = "ORCAFLEX"

# --- Paths -------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent.parent           # streamlit_app/
BACKEND_DIR = APP_DIR.parent / "backend"                    # backend/
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"

# Local, gitignored state directory (uploads, caches, recent files, exports)
STATE_DIR = APP_DIR / ".local_state"
UPLOAD_DIR = STATE_DIR / "uploads"
EXPORT_DIR = STATE_DIR / "exports"
for _dir in (STATE_DIR, UPLOAD_DIR, EXPORT_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --- Navigation (wireframe labels) ---------------------------------------
# Page scripts live under ``app_pages/`` (not ``pages/``) so Streamlit does not
# also register legacy auto-discovered multipage routes beside ``st.navigation``.
NAV_STRUCTURE = [
    {
        "section": "Workspace",
        "pages": [
            {"file": "app_pages/Home.py", "title": "Dashboard", "icon": "🏠", "default": True},
            {"file": "app_pages/Statistics.py", "title": "Statistics", "icon": "📋"},
            {"file": "app_pages/Single_Simulation.py", "title": "Results", "icon": "📈"},
            {"file": "app_pages/Batch_Analysis.py", "title": "Comparisons", "icon": "📊"},
            {"file": "app_pages/Reports.py", "title": "Reports", "icon": "📄"},
        ],
    },
    {
        "section": "System",
        "pages": [
            {"file": "app_pages/Settings.py", "title": "Settings", "icon": "⚙️"},
            {"file": "app_pages/Help.py", "title": "Help", "icon": "❓"},
            {"file": "app_pages/About.py", "title": "About", "icon": "ℹ️"},
        ],
    },
    {
        "section": "Tools",
        "pages": [
            {"file": "app_pages/Load_Files.py", "title": "File Manager", "icon": "📂"},
        ],
    },
]

OBJECT_TYPE_ICONS = {
    "Line": "⚓",
    "Vessel": "🚢",
    "6DBuoy": "🔵",
    "3DBuoy": "🔵",
    "Winch": "🎣",
    "Link": "🧵",
    "Environment": "🌊",
    "All": "📦",
}

# Display labels for the Dashboard object catalog (valid OrcaFlex types only)
OBJECT_CATALOG_ORDER = [
    ("Vessel", "Vessels"),
    ("Line", "Lines"),
    ("Winch", "Winches"),
    ("Link", "Links"),
    ("6DBuoy", "6D Buoys"),
    ("3DBuoy", "3D Buoys"),
    ("Environment", "Environment"),
]

# OrcaFlex desktop Period list order; default selection is Whole Simulation.
PERIOD_OPTIONS = [
    "Specified Period",
    "Latest Wave",
    "Whole Simulation",
    "Build-up",
    "Stage 1",
]
DEFAULT_PERIOD = "Whole Simulation"

# Ops console palette (for Plotly / programmatic use — mirrors CSS variables)
OPS_COLORS = {
    "navy": "#102a43",
    "ocean": "#1f4e79",
    "slate": "#52606d",
    "sea_green": "#2d6a6a",
    "brass": "#2d8a6d",
    "brass_dark": "#246f58",
    "accent_green_light": "#5fc2a3",
    "page_bg": "#e8ecf0",
    "panel": "#ffffff",
    "panel_alt": "#f4f7f9",
    "panel_border": "#d3dae2",
    "text": "#102a43",
    "text_muted": "#52606d",
    "series": ["#1f4e79", "#2d8a6d", "#c79a3a", "#d3792f", "#2d6a6a", "#52606d", "#5fc2a3"],
}
