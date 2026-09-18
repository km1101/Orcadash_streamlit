"""
Small persisted-state store (recent files, favorites, recent exports)
plus the Streamlit caching wrapper for model summaries.

State persists to plain JSON files under ``.local_state/`` so it survives
across app restarts without needing a database for what is, functionally,
a handful of small lists.
"""
import json
from datetime import datetime

import streamlit as st

from utils.config import STATE_DIR

_RECENT_FILES = STATE_DIR / "recent_files.json"
_FAVORITES = STATE_DIR / "favorites.json"
_EXPORTS = STATE_DIR / "recent_exports.json"

_MAX_RECENT = 15
_MAX_EXPORTS = 15


def _read_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default


def _write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        st.warning(f"Could not persist app state to {path.name}: {e}")


# --- Recent files ---------------------------------------------------------

def add_recent_file(file_path, display_name):
    entries = _read_json(_RECENT_FILES, [])
    entries = [e for e in entries if e.get("path") != str(file_path)]
    entries.insert(0, {
        "path": str(file_path),
        "name": display_name,
        "opened_at": datetime.now().isoformat(timespec="seconds"),
    })
    _write_json(_RECENT_FILES, entries[:_MAX_RECENT])


def get_recent_files(limit=10):
    return _read_json(_RECENT_FILES, [])[:limit]


# --- Favorites -------------------------------------------------------------

def toggle_favorite(file_path, display_name):
    favorites = _read_json(_FAVORITES, [])
    file_path = str(file_path)
    if any(f.get("path") == file_path for f in favorites):
        favorites = [f for f in favorites if f.get("path") != file_path]
    else:
        favorites.append({"path": file_path, "name": display_name})
    _write_json(_FAVORITES, favorites)
    return is_favorite(file_path)


def is_favorite(file_path):
    favorites = _read_json(_FAVORITES, [])
    return any(f.get("path") == str(file_path) for f in favorites)


def get_favorites():
    return _read_json(_FAVORITES, [])


# --- Recent exports ----------------------------------------------------------

def record_export(file_path, kind):
    entries = _read_json(_EXPORTS, [])
    entries.insert(0, {
        "path": str(file_path),
        "name": file_path.name if hasattr(file_path, "name") else str(file_path),
        "kind": kind,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
    })
    _write_json(_EXPORTS, entries[:_MAX_EXPORTS])


def get_recent_exports(limit=10):
    return _read_json(_EXPORTS, [])[:limit]


# --- Cached model summaries --------------------------------------------------

@st.cache_data(show_spinner=False)
def cached_model_summary(file_path, _mtime):
    """Cache key includes file mtime so a re-uploaded/changed file busts the cache."""
    from utils.loaders import get_model_summary
    return get_model_summary(file_path)


def get_cached_model_summary(file_path):
    import os
    mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
    return cached_model_summary(file_path, mtime)
