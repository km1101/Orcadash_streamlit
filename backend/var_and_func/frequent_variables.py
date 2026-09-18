"""Persist usage counts for OrcaFlex variables selected in the dashboard."""
import json
import os

_USAGE_FILE = os.path.join(os.path.dirname(__file__), "frequent_variables_usage.json")


def _load_usage():
    if os.path.exists(_USAGE_FILE):
        try:
            with open(_USAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read frequent-variable usage file: {e}")
    return {}


def _save_usage(usage):
    try:
        with open(_USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(usage, f, indent=2)
    except OSError as e:
        print(f"Warning: could not persist frequent-variable usage: {e}")


def record_variable_usage(variable_name):
    """Increment the usage count for a variable."""
    if not variable_name:
        return
    usage = _load_usage()
    usage[variable_name] = usage.get(variable_name, 0) + 1
    _save_usage(usage)
