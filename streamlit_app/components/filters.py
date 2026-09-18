"""
Reusable selection widgets: file, object, variable, position, and period.

Each function accepts a ``key_prefix`` so the same filter can be reused more
than once on one page (e.g. two file pickers side-by-side in Batch Analysis)
without Streamlit widget-key collisions, and a ``container`` (``st`` or
``st.sidebar``) so pages decide whether filters live in the main panel or
the left rail.
"""
import streamlit as st

from utils.config import DEFAULT_PERIOD, OBJECT_TYPE_ICONS, PERIOD_OPTIONS
from utils.loaders import ORCAFLEX_AVAILABLE, get_variables_for_object_types, variables_dict, END_LOAD_CATEGORIES, is_end_load_variable
from utils.cache import get_cached_model_summary


def file_selector(container=st.sidebar, key_prefix=""):
    loaded = st.session_state.get("loaded_files", {})
    if not loaded:
        container.info("No files loaded yet. Visit **📂 Load Files** to add one.")
        return None, None
    display_name = container.selectbox("File", list(loaded.keys()), key=f"{key_prefix}file")
    return display_name, loaded[display_name]


def object_selector(file_path, container=st.sidebar, key_prefix=""):
    if not file_path:
        return None, []
    summary = get_cached_model_summary(file_path)
    objects = summary.get("objects", {})

    available_types = [t for t, names in objects.items() if names]
    available_types.append("Environment")  # always present, model-wide

    labels = {t: f"{OBJECT_TYPE_ICONS.get(t, '')} {t}" for t in available_types}
    object_type = container.selectbox(
        "Object type", available_types, format_func=lambda t: labels.get(t, t), key=f"{key_prefix}object_type"
    )

    if object_type == "Environment":
        container.caption("Environment is a single, model-wide object (current / wind / wave).")
        return object_type, ["Environment"]

    names = objects.get(object_type, [])
    object_names = container.multiselect("Objects", names, default=names[:1], key=f"{key_prefix}object_names")
    return object_type, object_names


def variable_selector(object_type, container=st.sidebar, key_prefix=""):
    if not ORCAFLEX_AVAILABLE or not object_type:
        return None

    try:
        valid_variables = get_variables_for_object_types([object_type])
    except Exception:
        valid_variables = None

    if object_type == "Environment":
        categories = [c for c in variables_dict.keys() if c.startswith("Environment")]
    elif object_type == "Winch":
        # Dedicated category, same pattern as Environment* categories above —
        # a Winch-only selection is scoped to just the "Winch" category.
        categories = [c for c in variables_dict.keys() if c == "Winch"]
    else:
        categories = [c for c in variables_dict.keys() if not c.startswith("Environment") and c != "Winch"]
        # End Loads* are Line + Time History at End A/B only
        if object_type != "Line":
            categories = [c for c in categories if c not in END_LOAD_CATEGORIES]

    category = container.selectbox("Category", categories, key=f"{key_prefix}category")
    category_variables = list(variables_dict.get(category, {}).keys())

    if valid_variables:
        variable_options = [v for v in category_variables if v in valid_variables] or category_variables
    else:
        variable_options = category_variables

    if not variable_options:
        container.warning("No variables available for this category/object type.")
        return None

    variable = container.selectbox("Variable", variable_options, key=f"{key_prefix}variable")
    if is_end_load_variable(variable):
        container.caption("End Loads apply at **End A** / **End B** only.")
    return variable


def position_selector(object_type, container=st.sidebar, key_prefix="", ends_only=False):
    if object_type != "Line":
        return None
    options = ["End A", "End B"] if ends_only else ["End A", "End B", "Custom arc length"]
    # Separate widget keys so switching End-Loads ↔ normal does not leave an
    # invalid "Custom arc length" value in session state.
    choice_key = f"{key_prefix}position_choice_ends" if ends_only else f"{key_prefix}position_choice"
    choice = container.radio(
        "Position", options, horizontal=True, key=choice_key
    )
    if choice == "Custom arc length":
        return container.number_input("Arc length (m)", min_value=0.0, value=0.0, step=1.0, key=f"{key_prefix}arc")
    return choice


def period_selector(container=st.sidebar, key_prefix=""):
    """Period control matching OrcaFlex desktop (Specified Period shows From/To)."""
    default_idx = PERIOD_OPTIONS.index(DEFAULT_PERIOD) if DEFAULT_PERIOD in PERIOD_OPTIONS else 0
    choice = container.selectbox(
        "Period",
        PERIOD_OPTIONS,
        index=default_idx,
        key=f"{key_prefix}period_choice",
    )
    if choice == "Specified Period":
        col1, col2 = container.columns(2)
        period_from = col1.number_input("From (s)", value=0.0, step=1.0, key=f"{key_prefix}period_from")
        period_to = col2.number_input("To (s)", value=100.0, step=1.0, key=f"{key_prefix}period_to")
        return {"period": choice, "period_from": period_from, "period_to": period_to}
    return choice
