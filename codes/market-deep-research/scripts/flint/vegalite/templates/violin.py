"""Violin Plot template.

Shows the full smoothed distribution shape of a quantitative measure, one
mirrored kernel-density curve per category. Port of vegalite/templates/violin.ts.
"""
from __future__ import annotations

import math

from ...core import js_round
from .utils import detect_banded_axis_force_discrete


def _is_discrete(t):
    return t == "nominal" or t == "ordinal"


def _distinct_values(table, field):
    """Distinct non-null values of a field, in data-encounter order."""
    seen = set()
    out = []
    for row in table:
        v = row.get(field)
        if v is None:
            continue
        key = str(v)
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def _numeric_extent(table, field):
    """[min, max] of a numeric field across the table (ignoring non-numbers)."""
    mn = math.inf
    mx = -math.inf
    for row in table:
        v = row.get(field)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            continue
        if v < mn:
            mn = v
        if v > mx:
            mx = v
    if mn == math.inf or mx == -math.inf:
        return None
    if mn == mx:
        mn -= 0.5
        mx += 0.5
    return [mn, mx]


def _quantile_sorted(sorted_vals, p):
    """Linear-interpolated quantile of an already-sorted ascending array."""
    n = len(sorted_vals)
    if n == 0:
        return float("nan")
    idx = (n - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def _stdev(values):
    """Sample standard deviation (n-1) of a numeric array."""
    n = len(values)
    if n < 2:
        return 0
    mean = sum(values) / n
    v = sum((x - mean) * (x - mean) for x in values) / (n - 1)
    return math.sqrt(v)


def _bandwidth_nrd(values):
    """Normal-reference (Scott/Silverman) KDE bandwidth."""
    n = len(values)
    if n < 2:
        return 0
    s = sorted(values)
    lo = _quantile_sorted(s, 0.25)
    hi = _quantile_sorted(s, 0.75)
    sd = _stdev(s)
    h = min(sd, (hi - lo) / 1.34)
    if not (h > 0):
        h = sd or abs(lo) or 1
    return 1.06 * h * (n ** -0.2)


def _max_group_bandwidth(table, measure, groupby):
    """Largest per-group KDE bandwidth across the groups Vega will form."""
    groups = {}
    for row in table:
        v = row.get(measure)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            continue
        key = "\u0000".join(str(row.get(f)) for f in groupby)
        groups.setdefault(key, []).append(v)
    mx = 0
    for arr in groups.values():
        bw = _bandwidth_nrd(arr)
        if bw > mx:
            mx = bw
    return mx


def _violin_declare_layout(cs, table, chart_properties):
    if not (cs.get("x") or {}).get("field") or not (cs.get("y") or {}).get("field"):
        return {}
    result = detect_banded_axis_force_discrete(cs, table, {"preferAxis": "x"})
    if not result:
        return {}
    return {"resolvedTypes": result.get("resolvedTypes")}


def _violin_instantiate(spec, ctx):
    encs = ctx["resolvedEncodings"]
    x = encs.get("x")
    y = encs.get("y")
    color = encs.get("color")
    row = encs.get("row")
    cat_field = x.get("field") if x else None
    measure_field = y.get("field") if y else None
    if not cat_field or not measure_field:
        return

    # --- Density transform (per category, retaining every facet field) ---
    color_field = color.get("field") if color else None
    row_field = row.get("field") if row else None
    groupby = [cat_field]
    if row_field and row_field != cat_field:
        groupby.append(row_field)
    if color_field and color_field != cat_field and color_field != row_field:
        groupby.append(color_field)
    spec["transform"][0]["density"] = measure_field
    spec["transform"][0]["groupby"] = groupby

    # --- Bandwidth (mirrors density.ts) ---
    config = ctx.get("chartProperties") or {}
    user_bandwidth = config["bandwidth"] if config.get("bandwidth") and config["bandwidth"] > 0 else 0
    if user_bandwidth > 0:
        spec["transform"][0]["bandwidth"] = user_bandwidth

    extent = _numeric_extent(ctx["table"], measure_field)
    if extent:
        rng = extent[1] - extent[0]
        effective_bw = user_bandwidth if user_bandwidth > 0 else _max_group_bandwidth(ctx["table"], measure_field, groupby)
        pad = max(rng * 0.05, 1.5 * effective_bw, 1e-6)
        spec["transform"][0]["extent"] = [extent[0] - pad, extent[1] + pad]

    # --- Value axis (the measure) ---
    spec["encoding"]["y"]["title"] = measure_field

    # --- Color: default to the category so each violin has its own hue ---
    cat_type = x.get("type") if (x and _is_discrete(x.get("type"))) else "nominal"
    if color_field:
        spec["encoding"]["color"] = {**color}
    else:
        spec["encoding"]["color"] = {"field": cat_field, "type": cat_type}
    if not color_field or color_field == cat_field:
        spec["encoding"]["color"]["legend"] = None

    # --- Per-category panels: the category occupies the column/wrap facet ---
    cats = _distinct_values(ctx["table"], cat_field)
    cat_count = max(1, len(cats))

    canvas_w = (ctx.get("canvasSize") or {}).get("width") or 560
    canvas_h = (ctx.get("canvasSize") or {}).get("height") or 360
    spacing = 0
    reserved_w = 60
    reserved_h = 70
    min_panel_w = 44
    max_per_row = max(1, math.floor((canvas_w - reserved_w) / (min_panel_w + spacing)))
    columns = min(cat_count, max_per_row)
    rows_count = math.ceil(cat_count / columns)
    panel_w = js_round((canvas_w - reserved_w - (columns - 1) * spacing) / columns)
    panel_w = max(min_panel_w, min(panel_w, 220))
    panel_h = max(120, js_round((canvas_h - reserved_h) / rows_count) - (24 if rows_count > 1 else 0))

    facet_def = {
        "field": cat_field,
        "type": cat_type,
        "spacing": spacing,
        "header": {"titleOrient": "bottom", "labelOrient": "bottom", "labelPadding": 2},
    }
    if x and "sort" in x:
        facet_def["sort"] = x["sort"]

    if row:
        spec["encoding"]["column"] = facet_def
        spec["encoding"]["row"] = row
    else:
        spec["encoding"]["facet"] = {**facet_def, "columns": columns}

    spec["width"] = panel_w
    spec["height"] = panel_h


violin_plot_def = {
    "chart": "Violin Plot",
    "template": {
        "mark": {"type": "area", "orient": "horizontal"},
        "transform": [{"density": "__measure__", "groupby": [], "as": ["value", "density"]}],
        "encoding": {
            "y": {"field": "value", "type": "quantitative"},
            "x": {
                "field": "density", "type": "quantitative", "stack": "center",
                "impute": None, "title": None,
                "axis": {"labels": False, "ticks": False, "grid": False},
            },
        },
    },
    "channels": ["x", "y", "color", "row"],
    "markCognitiveChannel": "area",
    "declareLayoutMode": _violin_declare_layout,
    "instantiate": _violin_instantiate,
    "properties": [
        {"key": "bandwidth", "label": "Bandwidth", "type": "continuous",
         "min": 0.05, "max": 2, "step": 0.05, "defaultValue": 0},
    ],
}
