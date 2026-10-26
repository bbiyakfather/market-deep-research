"""Density Plot template."""
from __future__ import annotations

import math


def _estimate_bandwidth(values):
    """Silverman/Scott rule-of-thumb bandwidth (mirrors density.ts /
    vega-statistics): 1.06 * v * n^-0.2 with v = min(std, IQR/1.34)."""
    n = len(values)
    if n < 2:
        return 1
    s = sorted(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    d = math.sqrt(variance)  # standard deviation
    q1 = s[math.floor((n - 1) * 0.25)]
    q3 = s[math.floor((n - 1) * 0.75)]
    iqr = q3 - q1
    h = iqr / 1.34
    inner = h if h else d
    m = min(d, inner)
    return 1.06 * (m or d or 1) * (n ** -0.2)


def _max_group_bandwidth(table, field, groupby):
    """Widest per-group Silverman bandwidth across the groups Vega's density
    transform forms (one KDE per `groupby` combination). Mirrors density.ts."""
    groups: dict[str, list] = {}
    for row in table:
        v = row.get(field)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            continue
        key = "\u0000".join(str(row.get(f)) for f in groupby) if groupby else ""
        groups.setdefault(key, []).append(v)
    mx = 0
    for arr in groups.values():
        bw = _estimate_bandwidth(arr)
        if bw > mx:
            mx = bw
    return mx


def _density_instantiate(spec, ctx):
    encs = ctx["resolvedEncodings"]
    x = encs.get("x")
    color = encs.get("color")
    column = encs.get("column")
    row = encs.get("row")
    if x and x.get("field"):
        spec["transform"][0]["density"] = x["field"]
        spec["encoding"]["x"]["title"] = x["field"]
    if color and color.get("field"):
        spec["transform"][0]["groupby"] = [color["field"]]
        existing_color = (spec.get("encoding") or {}).get("color") or {}
        spec["encoding"]["color"] = {**existing_color, **color}
    if column:
        spec["encoding"]["column"] = column
    if row:
        spec["encoding"]["row"] = row
    config = ctx.get("chartProperties")
    # `bandwidth` is a *relative* smoothing multiplier (1 ≈ the data-derived
    # default per group), not an absolute width — see _estimate_bandwidth. We
    # scale the widest per-group Silverman base by it so the slider reads
    # consistently across fields of any scale and matches the JS reference. 0 /
    # unset leaves Vega to pick its own (auto) bandwidth per group.
    if config and config.get("bandwidth") and config["bandwidth"] > 0 and x and x.get("field"):
        groupby = [
            f.get("field")
            for f in (color, column, row)
            if f and f.get("field")
        ]
        base = _max_group_bandwidth(ctx["table"], x["field"], groupby)
        if base > 0:
            spec["transform"][0]["bandwidth"] = base * config["bandwidth"]



density_plot_def = {
    "chart": "Density Plot",
    "template": {
        "mark": "area",
        "transform": [{"density": "__field__"}],
        "encoding": {
            "x": {"field": "value", "type": "quantitative"},
            "y": {"field": "density", "type": "quantitative"},
        },
    },
    "channels": ["x", "color", "column", "row"],
    "markCognitiveChannel": "area",
    "instantiate": _density_instantiate,
    "properties": [
        {"key": "bandwidth", "label": "Bandwidth", "type": "continuous",
         "min": 0.05, "max": 2, "step": 0.05, "defaultValue": 0},
    ],
}
