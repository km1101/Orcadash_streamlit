import OrcFxAPI
import pandas as pd

from var_and_func.time_history import resolve_period


def _period_from_spec(period_spec):
    """Resolve UI period selection to an OrcFxAPI period for RangeGraph.

    TimeHistory treats Whole Simulation as ``None`` (omit the argument).
    RangeGraph requires an explicit period; map Whole Simulation to
    ``PeriodNum.WholeSimulation``. Other options reuse :func:`resolve_period`.
    """
    if period_spec is None or period_spec == "Whole Simulation":
        return OrcFxAPI.PeriodNum.WholeSimulation
    if isinstance(period_spec, dict):
        period_name = period_spec.get("period", "Whole Simulation")
        if period_name == "Whole Simulation" or period_name is None:
            return OrcFxAPI.PeriodNum.WholeSimulation
        if period_name == "Specified Period":
            return resolve_period(
                period_name,
                period_spec.get("period_from"),
                period_spec.get("period_to"),
            )
        resolved = resolve_period(period_name)
        return OrcFxAPI.PeriodNum.WholeSimulation if resolved is None else resolved
    if isinstance(period_spec, str):
        resolved = resolve_period(period_spec)
        return OrcFxAPI.PeriodNum.WholeSimulation if resolved is None else resolved
    return period_spec


def extract_range_graph_data(file_path, selected_line, selected_variable, period_spec=None):
    """Extract range graph data for a specific line and variable.

    ``period_spec`` matches Time History: ``None`` / ``\"Whole Simulation\"``,
    stage labels (``\"Stage 1\"``, ``\"Build-up\"``, …), or a Specified Period dict.
    """
    try:
        import os
        # Validate file path exists
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
            
        print(f"Extracting data from: {file_path}")
        
        # Load OrcaFlex model
        model = OrcFxAPI.Model(file_path)
        line = model[selected_line]
        
        period = _period_from_spec(period_spec)
        rg = line.RangeGraph(selected_variable, period)
        
        df = pd.DataFrame({
            'z': rg.X,
            'min': rg.Min,
            'max': rg.Max,
            'mean': rg.Mean
        })
        
        print(f"Extracted {len(df)} data points for line '{selected_line}', variable '{selected_variable}'")
        return df
    except Exception as e:
        print(f"Error extracting range graph data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(columns=['z', 'min', 'max', 'mean'])


#############################
# 3D Position Graph
#############################
_3D_VALID_STATISTICS = ("mean", "min", "max")
_3D_AXES = ("X", "Y", "Z")


def extract_3D_position_data(file_path, selected_lines, selected_statistics=None):
    """Extract a 3D (X, Y, Z) line-shape path along arc length for one or more Lines.

    For each line in ``selected_lines``, pulls the Position category's ``X``,
    ``Y`` and ``Z`` RangeGraph variables (via :func:`extract_range_graph_data`)
    and merges them on arc length, giving a single ``(x, y, z)`` point per
    arc-length station suitable for ``go.Scatter3d(x=..., y=..., z=...)``.

    A single, consistent statistic is used across X/Y/Z for a given line —
    combining e.g. Min(X)/Max(Y)/Mean(Z) into one 3D path would not describe
    a physically coherent line shape, since each axis' min/max can occur at a
    different time step. ``mean`` is the default because it is the
    statistically representative choice for a static geometric shape; callers
    wanting an "extreme" shape can still pass ``selected_statistics=["min"]``
    or ``["max"]`` explicitly.

    Column naming convention
    -------------------------
    - ``arc_length`` — arc length along the line (m); the merge key (this is
      the ``z`` column from :func:`extract_range_graph_data`, renamed here
      for clarity — it is unrelated to the ``Z`` position axis).
    - One statistic requested (the default, ``["mean"]``): ``{line}_X``,
      ``{line}_Y``, ``{line}_Z`` for each line in ``selected_lines``.
    - Multiple statistics requested (e.g. ``["mean", "min"]``):
      ``{line}_X_{stat}``, ``{line}_Y_{stat}``, ``{line}_Z_{stat}`` for each
      requested ``stat``.

    Parameters
    ----------
    file_path : str
        Path to the OrcaFlex ``.sim`` file.
    selected_lines : list[str]
        Line object names to extract.
    selected_statistics : list[str] | None
        Subset of ``{"mean", "min", "max"}`` to keep from each RangeGraph
        result. Defaults to ``["mean"]`` when not provided (or when none of
        the requested values are recognized).

    Returns
    -------
    pandas.DataFrame
        ``arc_length`` plus the per-line/axis(/stat) columns described
        above. Returns a DataFrame with only the ``arc_length`` column (no
        data columns) when no data could be extracted for any requested
        line — callers should treat that as "no data" rather than an error.
        Unexpected failures (bad arguments, merge errors) are logged with a
        traceback and re-raised rather than swallowed, so callers can tell a
        real bug apart from "no data".
    """
    stats = [s for s in (selected_statistics or ["mean"]) if s in _3D_VALID_STATISTICS]
    if not stats:
        print(
            f"No valid statistics in {selected_statistics!r} "
            f"(expected a subset of {_3D_VALID_STATISTICS}) — defaulting to ['mean']."
        )
        stats = ["mean"]
    multi_stat = len(stats) > 1

    try:
        combined_df = pd.DataFrame()
        lines_with_data = []

        for line in selected_lines or []:
            axis_frames = []
            for axis in _3D_AXES:
                axis_df = extract_range_graph_data(file_path, line, axis)
                if axis_df is None or axis_df.empty:
                    print(f"No RangeGraph '{axis}' data for line '{line}' — skipping this line.")
                    axis_frames = []
                    break

                rename = {
                    stat: (f"{line}_{axis}" if not multi_stat else f"{line}_{axis}_{stat}")
                    for stat in stats
                    if stat in axis_df.columns
                }
                if not rename:
                    print(
                        f"None of the requested statistics {stats} are present in RangeGraph "
                        f"output for line '{line}', axis '{axis}' — skipping this line."
                    )
                    axis_frames = []
                    break
                axis_frames.append(axis_df[['z'] + list(rename.keys())].rename(columns=rename))

            if not axis_frames:
                continue

            line_df = axis_frames[0]
            for extra in axis_frames[1:]:
                line_df = pd.merge(line_df, extra, on='z', how='outer')

            combined_df = line_df if combined_df.empty else pd.merge(combined_df, line_df, on='z', how='outer')
            lines_with_data.append(line)

        if combined_df.empty:
            print(f"No 3D position data extracted for lines {list(selected_lines or [])}.")
            return pd.DataFrame(columns=['arc_length'])

        combined_df = (
            combined_df.rename(columns={'z': 'arc_length'})
            .sort_values('arc_length', kind='mergesort')
            .reset_index(drop=True)
        )
        print(
            f"Extracted 3D position data for {len(lines_with_data)}/{len(selected_lines or [])} "
            f"line(s) with statistic(s) {stats}."
        )
        return combined_df
    except Exception as e:
        print(f"Error extracting 3D position data for lines {selected_lines}: {e}")
        import traceback
        traceback.print_exc()
        raise
    