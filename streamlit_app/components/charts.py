"""
Chart helpers for the ORCAFLEX ops console.

All interactive result charts (Time History, Range Graph, X-Y, histogram,
PSD, KPI gauges) are built as Plotly ``go.Figure`` objects so pages get full
modebar interactivity — autoscale, zoom, pan, and PNG download — which the
native ``st.line_chart``/``st.scatter_chart`` widgets don't provide. Render
figures with :func:`render_plotly_chart` (or ``st.plotly_chart`` +
``PLOTLY_CONFIG`` directly) to keep the toolbar enabled everywhere.
"""
import os
import re

import plotly.graph_objects as go
import streamlit as st

from utils.config import OPS_COLORS
from utils.loaders import compute_histogram, compute_power_spectral_density

_SERIES = OPS_COLORS["series"]
_LEGEND_NAME_MAX = 64
_CHART_HEIGHT = 540
# Multi-file merge columns use ``file::object`` (legacy ``file=object`` tolerated).
_SERIES_SEP_RE = re.compile(r"^(?P<file>.+?)(?:::|=)(?P<object>.+)$")
_VAR_TAG_RE = re.compile(r"^(?P<head>.*)(?P<tag>\s\[[^\]]+\])$")

# Full modebar so on-screen charts always expose autoscale/zoom/pan/download —
# native st.line_chart/st.scatter_chart lack these, which is why Plotly is used
# for every interactive result chart in this app.
PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToAdd": ["v1hovermode", "toggleSpikelines"],
    "toImageButtonOptions": {"format": "png", "filename": "orcaflex_chart"},
}


def render_plotly_chart(fig, **kwargs):
    """``st.plotly_chart`` with the ops-console modebar always enabled.

    Centralizing this call keeps zoom/pan/autoscale/download consistent
    across pages instead of each call site repeating (or forgetting) the
    ``config`` dict.
    """
    kwargs.setdefault("width", "stretch")
    kwargs.setdefault("config", PLOTLY_CONFIG)
    st.plotly_chart(fig, **kwargs)


# Plotly's legend-click only toggles a trace's ``visible`` state inside the
# browser's copy of the figure — that state is never sent back to the
# Streamlit/Python session (no websocket message exists for it). Anything
# rendered server-side afterwards — the modebar's "Download as PNG" (which
# Plotly.js renders from the *same* in-browser figure, legend included) and
# any Report export (which reconstructs a fresh ``go.Figure`` from the
# session's DataFrame) has no way to know which traces the user hid. Fixing
# this without a client-event bridge (e.g. ``streamlit-plotly-events``) means
# doing the filtering *before* the figure is built: a normal Streamlit
# multiselect below decides which columns become traces at all, so an
# excluded series is simply never drawn — not hidden — and every consumer of
# that figure (on-screen chart, PNG download, Report HTML) agrees by
# construction.
SERIES_SELECTOR_CAPTION = (
    "Legend-click above hides a trace only in your browser session — it does not change PNG "
    "downloads or Report exports. Use **Series to display** to control exactly what those show."
)


def series_multiselect(df, id_cols, key, label="Series to display", help=None, container=None):
    """Column-level "series to display" multiselect for Time-History-shaped frames.

    Defaults to every non-id column selected; a prior pick that survives a
    rerun (same columns still present) is kept so switching view modes or
    display options doesn't reset the user's choice. Returns
    ``(filtered_df, selected_columns, all_options)`` — pass ``filtered_df``
    into the figure builder instead of ``df`` so unselected series are never
    added as traces.
    """
    target = container or st
    if df is None or getattr(df, "empty", True):
        return df, [], []
    options = [c for c in df.columns if c not in id_cols]
    if not options:
        return df, [], []

    prev = st.session_state.get(key)
    pruned = [c for c in prev if c in options] if isinstance(prev, list) else None
    if not pruned:
        st.session_state[key] = list(options)
    elif pruned != prev:
        st.session_state[key] = pruned

    selected = target.multiselect(
        label, options, format_func=_format_series_label, key=key, help=help,
    )
    keep = [c for c in df.columns if c in id_cols or c in selected]
    return df[keep], selected, options


def object_multiselect(names, key, label="Series to display", help=None, container=None):
    """Object-name-level selector for Range Graph / X-Y charts.

    Each "series" there spans several columns (``_min``/``_max``/``_mean`` or
    ``_x``/``_y``), so filtering has to happen on the object name rather than
    a single column. Returns the selected names (a subset of ``names``).
    """
    target = container or st
    names = list(names or [])
    if not names:
        return []

    prev = st.session_state.get(key)
    pruned = [n for n in prev if n in names] if isinstance(prev, list) else None
    if not pruned:
        st.session_state[key] = list(names)
    elif pruned != prev:
        st.session_state[key] = pruned

    return target.multiselect(
        label, names, format_func=_format_series_label, key=key, help=help,
    )


def filter_columns_for_objects(df, id_cols, selected_names, suffixes):
    """Keep ``id_cols`` plus, for each selected object name, the columns
    named ``f"{name}{suffix}"`` for every ``suffix`` in ``suffixes``
    (e.g. ``("_min", "_max", "_mean")`` for Range Graph or ``("_x", "_y")``
    for X-Y). Used alongside :func:`object_multiselect`.
    """
    if df is None or getattr(df, "empty", True):
        return df
    keep = set(id_cols)
    for name in selected_names:
        for suf in suffixes:
            keep.add(f"{name}{suf}")
    cols = [c for c in df.columns if c in keep]
    return df[cols]


def _legend_name(name, max_len=_LEGEND_NAME_MAX):
    """Keep full object names when possible; truncate gently for very long labels."""
    text = str(name)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _format_series_label(name):
    """Readable legend label from ``file::object`` column keys.

    Data columns keep ``::`` for uniqueness; display prefers
    ``{object} ({file_stem})`` so ``.sim::`` never reads like ``.sim=``.
    """
    text = str(name).strip()
    var_tag = ""
    tagged = _VAR_TAG_RE.match(text)
    if tagged:
        text, var_tag = tagged.group("head"), tagged.group("tag")

    # XY / range helpers may pass ``file::object_x`` — strip trailing _x/_y for match only.
    xy_suffix = ""
    if text.endswith("_x") or text.endswith("_y"):
        xy_suffix = text[-2:]
        text = text[:-2]

    matched = _SERIES_SEP_RE.match(text)
    if matched:
        file_part = matched.group("file")
        obj_part = matched.group("object")
        stem = os.path.splitext(os.path.basename(file_part))[0] or file_part
        label = f"{obj_part} ({stem})"
    else:
        label = text

    if xy_suffix:
        label = f"{label}{xy_suffix}"
    if var_tag:
        label = f"{label}{var_tag}"
    return _legend_name(label)


def _clean_xy_series(df, x_col, y_col):
    """Per-series (x, y) with NaNs dropped and x sorted ascending.

    Outer-merges on Time/z leave NaNs in other columns; plotting the shared
    axis with those gaps lets Plotly draw straight chords across non-adjacent
    samples. Dropping NaNs per series and sorting x avoids that.
    """
    if df is None or getattr(df, "empty", True):
        return None
    if x_col not in df.columns or y_col not in df.columns:
        return None
    sub = df[[x_col, y_col]].dropna()
    if sub.empty:
        return None
    return sub.sort_values(x_col, kind="mergesort")


def _variable_label(variable_name, units=""):
    """``Effective Tension`` or ``Effective Tension (KN)`` when units are set."""
    label = variable_name or "Variable"
    units = (units or "").strip()
    return f"{label} ({units})" if units else label


def _normalize_title_text(text):
    """ASCII spaced hyphen separator — avoids em-dash mangling to ``---`` in PNG exports."""
    s = str(text)
    for token in ("\u2014", "\u2013", "---", "--"):
        s = s.replace(token, " - ")
    s = re.sub(r"\s*-\s*", " - ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def _chart_title(text):
    """Centered layout title so Plotly camera/PNG export includes it clearly."""
    if not text:
        return None
    return dict(
        text=_normalize_title_text(text),
        x=0.5,
        xanchor="center",
        y=0.98,
        yanchor="top",
        font=dict(size=18, color=OPS_COLORS["navy"], family="Inter, Segoe UI, sans-serif"),
    )


def _ops_layout(fig, show_legend=True, show_grid=True, is_3d=False, **overrides):
    # Legend inside the plot area so downloads/exports keep object names visible.
    legend = dict(
        orientation="v",
        x=1,
        y=1,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255,255,255,0.75)",
        bordercolor=OPS_COLORS["panel_border"],
        borderwidth=1,
        font=dict(size=11),
        traceorder="normal",
        title=dict(text=""),
    )
    has_title = bool(overrides.get("title"))
    margin = dict(l=56, r=28, t=80 if has_title else 40, b=56)
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=OPS_COLORS["panel_alt"],
        font=dict(family="Inter, Segoe UI, sans-serif", color=OPS_COLORS["text"], size=12),
        legend=legend,
        margin=margin,
        showlegend=show_legend,
        height=_CHART_HEIGHT,
        # "x unified" hover has no meaning for a 3D scene (there's no shared
        # x-axis across traces) — Plotly silently ignores it there, but
        # "closest" is the correct 3D-native behavior, so pick per chart kind.
        hovermode="closest" if is_3d else "x unified",
    )
    layout.update(overrides)
    # Never keep a noisy "Object" legend title from callers.
    layout.pop("legend_title_text", None)
    fig.update_layout(**layout)
    if is_3d:
        # 3D figures carry their axis config under layout.scene (passed via
        # overrides), not layout.xaxis/yaxis — update_xaxes/update_yaxes below
        # only affect the (unused) 2D axes and would be a no-op at best, so
        # skip them entirely for 3D charts.
        return fig
    grid = "rgba(16, 42, 67, 0.12)" if show_grid else "rgba(0,0,0,0)"
    # Explicit autorange + "normal" rangemode (not "tozero") so the plot always
    # fits the actual data min/max with Plotly's own padding — any stale fixed
    # `range=[...]` from a caller is what caused the chart to "float" without
    # respecting upper/lower bounds. Axes below always win over layout overrides
    # applied above since update_xaxes/update_yaxes run last.
    fig.update_xaxes(
        showgrid=show_grid, gridcolor=grid, zeroline=False, linecolor=OPS_COLORS["panel_border"],
        autorange=True, rangemode="normal",
    )
    fig.update_yaxes(
        showgrid=show_grid, gridcolor=grid, zeroline=False, linecolor=OPS_COLORS["panel_border"],
        autorange=True, rangemode="normal",
    )
    return fig


def time_history_figure(df, variable_name, units="", show_legend=True, show_grid=True):
    fig = go.Figure()
    if df is not None and not df.empty and "Time" in df.columns:
        i = 0
        for col in df.columns:
            if col == "Time":
                continue
            series = _clean_xy_series(df, "Time", col)
            if series is None:
                continue
            fig.add_trace(go.Scatter(
                x=series["Time"], y=series[col], mode="lines",
                name=_format_series_label(col),
                line=dict(color=_SERIES[i % len(_SERIES)], width=1.8),
                connectgaps=False,
                visible=True,
            ))
            i += 1
    axis_label = _variable_label(variable_name, units)
    return _ops_layout(
        fig,
        show_legend=show_legend,
        show_grid=show_grid,
        title=_chart_title(f"{axis_label} - Time History"),
        xaxis_title="Time (s)",
        yaxis_title=axis_label,
    )


def histogram_figure(df, columns, variable_name, units="", bins=50, show_legend=True, show_grid=True):
    fig = go.Figure()
    for i, col in enumerate(columns):
        if df is None or col not in df.columns:
            continue
        hist = compute_histogram(df[col], bins=bins)
        if not hist["bin_centers"]:
            continue
        fig.add_trace(go.Bar(
            x=hist["bin_centers"], y=hist["density"], name=_format_series_label(col),
            opacity=0.65,
            marker_color=_SERIES[i % len(_SERIES)],
        ))
    axis_label = _variable_label(variable_name, units)
    return _ops_layout(
        fig,
        show_legend=show_legend,
        show_grid=show_grid,
        title=_chart_title(f"{axis_label} - Frequency Distribution"),
        barmode="overlay",
        xaxis_title=axis_label,
        yaxis_title="Probability density",
    )


def psd_figure(df, columns, variable_name="", show_legend=True, show_grid=True):
    """Returns (figure, summary_rows) where summary_rows is a list of dicts
    with per-object peak frequency/period, suitable for a summary table."""
    fig = go.Figure()
    summary_rows = []
    for i, col in enumerate(columns):
        if df is None or col not in df.columns or "Time" not in df.columns:
            continue
        series = _clean_xy_series(df, "Time", col)
        if series is None:
            continue
        psd_result = compute_power_spectral_density(series["Time"], series[col])
        if not psd_result["frequency"]:
            continue
        fig.add_trace(go.Scatter(
            x=psd_result["frequency"], y=psd_result["psd"], mode="lines",
            name=_format_series_label(col),
            line=dict(color=_SERIES[i % len(_SERIES)], width=1.8),
        ))
        summary_rows.append({
            "Object": col,
            "Peak frequency (Hz)": round(psd_result["peak_frequency"], 4) if psd_result["peak_frequency"] else None,
            "Peak period (s)": round(psd_result["peak_period"], 3) if psd_result["peak_period"] else None,
        })
    label = variable_name or "Signal"
    fig = _ops_layout(
        fig, show_legend=show_legend, show_grid=show_grid,
        title=_chart_title(f"{label} - Power Spectral Density"),
        xaxis_title="Frequency (Hz)", yaxis_title="Power spectral density", height=500,
    )
    return fig, summary_rows


def range_graph_figure(
    merged_df,
    object_names,
    variable_name,
    show_legend=True,
    show_grid=True,
    statistics=("min", "max", "mean"),
):
    """Plot Range Graph envelope traces along arc length.

    ``statistics`` selects which of min / max / mean to draw (columns named
    ``{object}_{stat}``). Defaults to all three.
    """
    fig = go.Figure()
    stat_styles = (("min", "dot"), ("max", "dot"), ("mean", "solid"))
    selected = {s.lower() for s in (statistics or ())}
    if merged_df is not None and not merged_df.empty and "z" in merged_df.columns:
        i = 0
        for line_name in object_names:
            for stat, dash in stat_styles:
                if selected and stat not in selected:
                    continue
                col = f"{line_name}_{stat}"
                series = _clean_xy_series(merged_df, "z", col)
                if series is None:
                    continue
                short = _format_series_label(line_name)
                fig.add_trace(go.Scatter(
                    x=series["z"], y=series[col], mode="lines",
                    name=f"{short} ({stat})",
                    line=dict(dash=dash, color=_SERIES[i % len(_SERIES)], width=1.6),
                    connectgaps=False,
                    visible=True,
                ))
                i += 1
    label = variable_name or "Variable"
    return _ops_layout(
        fig, show_legend=show_legend, show_grid=show_grid,
        title=_chart_title(f"{label} - Range Graph"),
        xaxis_title="Arc length (m)", yaxis_title=label,
    )


def line_shape_3d_figure(df, object_names, statistic="mean", show_legend=True, show_grid=True):
    """3D line-shape plot — X/Y/Z path along arc length — for Line objects.

    Expects ``{name}_X`` / ``{name}_Y`` / ``{name}_Z`` columns per name in
    ``object_names`` (the single-statistic column convention produced by
    :func:`backend.var_and_func.range_graph.extract_3D_position_data`).
    One ``Scatter3d`` trace per line, colored from the same accent cycle
    used by every other chart in this module.
    """
    fig = go.Figure()
    if df is not None and not df.empty:
        for i, name in enumerate(object_names or []):
            cx, cy, cz = f"{name}_X", f"{name}_Y", f"{name}_Z"
            if not all(c in df.columns for c in (cx, cy, cz)):
                continue
            sub = df[[cx, cy, cz]].dropna()
            if sub.empty:
                continue
            color = _SERIES[i % len(_SERIES)]
            fig.add_trace(go.Scatter3d(
                x=sub[cx], y=sub[cy], z=sub[cz],
                mode="lines+markers",
                name=_format_series_label(name),
                line=dict(color=color, width=5),
                marker=dict(size=2.5, color=color),
                hovertemplate="X: %{x:.2f} m<br>Y: %{y:.2f} m<br>Z: %{z:.2f} m<extra>%{fullData.name}</extra>",
            ))
    stat_label = (statistic or "mean").strip().capitalize()
    grid_color = "rgba(16, 42, 67, 0.12)" if show_grid else "rgba(0,0,0,0)"
    scene_axis = dict(
        showgrid=show_grid, gridcolor=grid_color, zeroline=False,
        backgroundcolor=OPS_COLORS["panel_alt"], showbackground=True,
    )
    return _ops_layout(
        fig,
        show_legend=show_legend,
        is_3d=True,
        title=_chart_title(f"3D Line Shape ({stat_label})"),
        scene=dict(
            xaxis=dict(title="X (m)", **scene_axis),
            yaxis=dict(title="Y (m)", **scene_axis),
            zaxis=dict(title="Z (m)", **scene_axis),
            # "data" keeps the true aspect ratio between axes so the plotted
            # shape isn't visually stretched/squashed — critical for a real
            # line-path plot vs. an abstract scatter where distortion is fine.
            aspectmode="data",
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.1)),
        ),
        height=620,
    )


def xy_figure(df, variable_x, variable_y, units_x="", units_y="", object_names=None,
              show_legend=True, show_grid=True):
    """Parametric X-Y plot: each object as ``{name}_x`` vs ``{name}_y`` (time order)."""
    fig = go.Figure()
    if df is not None and not df.empty:
        names = object_names or []
        if not names:
            # Infer object names from ``*_x`` columns
            names = sorted({c[:-2] for c in df.columns if c.endswith("_x")})
        for i, name in enumerate(names):
            cx, cy = f"{name}_x", f"{name}_y"
            if cx not in df.columns or cy not in df.columns:
                continue
            # Preserve chronological order: drop NaN pairs, then sort by Time if present.
            cols = [cx, cy] + (["Time"] if "Time" in df.columns else [])
            sub = df[cols].dropna(subset=[cx, cy])
            if sub.empty:
                continue
            if "Time" in sub.columns:
                sub = sub.sort_values("Time", kind="mergesort")
            fig.add_trace(go.Scatter(
                x=sub[cx], y=sub[cy], mode="lines", name=_format_series_label(name),
                line=dict(color=_SERIES[i % len(_SERIES)], width=1.8),
                connectgaps=False,
                visible=True,
            ))
    x_label = variable_x or "X"
    y_label = variable_y or "Y"
    x_title = _variable_label(x_label, units_x)
    y_title = _variable_label(y_label, units_y)
    return _ops_layout(
        fig,
        show_legend=show_legend,
        show_grid=show_grid,
        title=_chart_title(f"{y_title} vs {x_title}"),
        xaxis_title=x_title,
        yaxis_title=y_title,
    )


def kpi_gauge_figure(value, title, vmin=None, vmax=None):
    """Simple KPI gauge for Dashboard view-mode switcher."""
    import math
    if value is None or (isinstance(value, float) and math.isnan(value)):
        value = 0
    vmin = vmin if vmin is not None else min(0, float(value) * 1.2 if value else 0)
    vmax = vmax if vmax is not None else max(abs(float(value)) * 1.4, 1.0)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(value),
        title={"text": title, "font": {"size": 14, "color": OPS_COLORS["navy"]}},
        number={"font": {"family": "SFMono-Regular, Consolas, monospace", "color": OPS_COLORS["navy"]}},
        gauge={
            "axis": {"range": [vmin, vmax], "tickcolor": OPS_COLORS["slate"]},
            "bar": {"color": OPS_COLORS["brass"]},
            "bgcolor": OPS_COLORS["panel_alt"],
            "bordercolor": OPS_COLORS["panel_border"],
            "steps": [
                {"range": [vmin, vmax * 0.5], "color": "rgba(62, 142, 90, 0.15)"},
                {"range": [vmax * 0.5, vmax * 0.8], "color": "rgba(199, 154, 58, 0.18)"},
                {"range": [vmax * 0.8, vmax], "color": "rgba(178, 59, 46, 0.15)"},
            ],
        },
    ))
    fig.update_layout(
        height=280, margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, Segoe UI, sans-serif"),
    )
    return fig
