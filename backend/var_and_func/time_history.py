"""Time-history helpers used by the Streamlit dashboard.

Keep this module import-light: extraction pages need period/position resolution,
X-Y pairing, and the basic statistics table. Multi-object TimeHistory itself
lives in ``extract_multi_objects``.
"""
import OrcFxAPI
import pandas as pd


def resolve_line_object_extra(position_spec):
    """Resolve a user-provided position specification to an OrcaFlex ObjectExtra.

    Accepted forms:
    - None -> End A
    - 'A', 'EndA', 'End A' -> End A
    - 'B', 'EndB', 'End B' -> End B
    - float/int -> arclength in model units (m), uses oeArcLength
    - dict like {"mode": "ArcLength", "value": 12.3} -> arclength
    - prebuilt ObjectExtra from OrcFxAPI (e.g., OrcFxAPI.oeEndA) -> returned as is
    """
    try:
        if position_spec is None:
            return OrcFxAPI.oeEndA

        if not isinstance(position_spec, (str, int, float, dict)):
            return position_spec

        if isinstance(position_spec, str):
            key = position_spec.strip().lower().replace(" ", "")
            if key in ("a", "enda"):
                return OrcFxAPI.oeEndA
            if key in ("b", "endb"):
                return OrcFxAPI.oeEndB
            try:
                arc = float(position_spec)
                return OrcFxAPI.oeArcLength(float(arc))
            except ValueError:
                pass

        if isinstance(position_spec, (int, float)):
            return OrcFxAPI.oeArcLength(float(position_spec))

        if isinstance(position_spec, dict):
            mode = str(position_spec.get("mode", "")).strip().lower()
            if mode in ("arclength", "arc_length", "arc") and "value" in position_spec:
                return OrcFxAPI.oeArcLength(float(position_spec["value"]))
            if mode in ("enda", "a"):
                return OrcFxAPI.oeEndA
            if mode in ("endb", "b"):
                return OrcFxAPI.oeEndB

        return OrcFxAPI.oeEndA
    except Exception:
        return OrcFxAPI.oeEndA


def resolve_period(period_name, period_from=None, period_to=None):
    """Convert GUI period selection to OrcFxAPI period format.

    Args:
        period_name: String period name matching OrcaFlex desktop Period list:
            "Specified Period", "Latest Wave", "Whole Simulation", "Build-up", "Stage 1"
        period_from: Start time in seconds (required for "Specified Period")
        period_to: End time in seconds (required for "Specified Period")

    Returns:
        OrcFxAPI period object/PeriodNum/stage int, or None for whole simulation
    """
    if period_name is None or period_name == "Whole Simulation":
        return None
    elif period_name == "Latest Wave":
        return OrcFxAPI.PeriodNum.LatestWave
    elif period_name == "Build-up":
        return 0
    elif period_name == "Stage 1":
        return 1
    elif period_name == "Specified Period":
        if period_from is not None and period_to is not None:
            return OrcFxAPI.SpecifiedPeriod(float(period_from), float(period_to))
        raise ValueError("period_from and period_to must be provided for Specified Period")
    return None


def extract_xy_time_history_data(
    file_path, object_names, variable_x, variable_y, position_spec=None, period_spec=None
):
    """Pair two time-history variables at identical time steps for X-Y graph extraction.

    Delegates per-variable extraction to :func:`extract_time_history_multi_objects` (lazy import
    to avoid circular imports with ``extract_multi_objects``).
    """
    from .extract_multi_objects import extract_time_history_multi_objects

    df_x = extract_time_history_multi_objects(
        file_path, object_names, variable_x, position_spec, period_spec
    )
    df_y = extract_time_history_multi_objects(
        file_path, object_names, variable_y, position_spec, period_spec
    )

    if df_x.empty or "Time" not in df_x.columns or df_y.empty or "Time" not in df_y.columns:
        raise ValueError(
            "No data extracted for X-Y pairing. "
            f"x columns: {list(df_x.columns)}, y columns: {list(df_y.columns)}"
        )

    rename_x = {"Time": "Time"}
    rename_y = {"Time": "Time"}
    for name in object_names:
        if name in df_x.columns:
            rename_x[name] = f"{name}_x"
        if name in df_y.columns:
            rename_y[name] = f"{name}_y"

    df_x = df_x.rename(columns=rename_x)
    df_y = df_y.rename(columns=rename_y)
    merged = pd.merge(df_x, df_y, on="Time", how="inner")
    if merged.empty:
        raise ValueError("No overlapping time steps between the two variables.")

    data_list = []
    for _, row in merged.iterrows():
        point = {"time": f'{row["Time"]:.3f}'}
        for name in object_names:
            cx = f"{name}_x"
            cy = f"{name}_y"
            if cx in merged.columns and cy in merged.columns:
                point[cx] = f"{float(row[cx]):.6f}"
                point[cy] = f"{float(row[cy]):.6f}"
        data_list.append(point)

    return data_list


def calculate_statistics_summary(data_df, variable_name=""):
    """Calculate max/min/mean/std for each object column in a time-history DataFrame."""
    if variable_name:
        max_col = f"Max ({variable_name})"
        min_col = f"Min ({variable_name})"
        mean_col = f"Mean ({variable_name})"
        std_col = f"Std Deviation ({variable_name})"
    else:
        max_col = "Max"
        min_col = "Min"
        mean_col = "Mean"
        std_col = "Std Deviation"

    default_columns = ["Object", max_col, min_col, mean_col, std_col]

    if data_df is None or data_df.empty:
        return pd.DataFrame(columns=default_columns)

    object_columns = [col for col in data_df.columns if col != "Time"]
    if not object_columns:
        return pd.DataFrame(columns=default_columns)

    stats_list = []
    for obj_col in object_columns:
        values = pd.to_numeric(data_df[obj_col], errors="coerce")
        values_clean = values.dropna()
        if len(values_clean) > 0:
            stats_list.append({
                "Object": obj_col,
                max_col: round(values_clean.max(), 2),
                min_col: round(values_clean.min(), 2),
                mean_col: round(values_clean.mean(), 2),
                std_col: round(values_clean.std(), 2) if len(values_clean) > 1 else 0.0,
            })
        else:
            stats_list.append({
                "Object": obj_col,
                max_col: None,
                min_col: None,
                mean_col: None,
                std_col: None,
            })

    return pd.DataFrame(stats_list)
