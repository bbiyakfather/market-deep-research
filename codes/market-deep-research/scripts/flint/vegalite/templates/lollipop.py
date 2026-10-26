"""Lollipop Chart template."""
from __future__ import annotations

from ...core import js_round
from ...core.encoding_actions import make_sort_action
from .utils import detect_banded_axis_from_semantics, set_mark_prop


def _lollipop_declare(cs, table, chart_properties):
    result = detect_banded_axis_from_semantics(cs, table, {"preferAxis": "x"})
    axis_flags = {result["axis"]: {"banded": True}} if result else {"x": {"banded": True}}
    return {
        "axisFlags": axis_flags,
        "resolvedTypes": result.get("resolvedTypes") if result else None,
        "paramOverrides": {
            "defaultBandSize": 20, "minStep": 4, "maxStretch": 3, "targetBandAR": 240,
        },
    }


def _is_measure(t):
    return t is not None and t != "nominal" and t != "ordinal"


def _lollipop_instantiate(spec, ctx):
    encs = ctx["resolvedEncodings"]
    color = encs.get("color")
    column = encs.get("column")
    row = encs.get("row")
    positional = {ch: enc for ch, enc in encs.items() if ch not in ("color", "column", "row")}

    for ch, enc in positional.items():
        for layer in spec["layer"]:
            layer["encoding"][ch] = {**(layer["encoding"].get(ch) or {}), **enc}

    if color:
        spec["layer"][1]["encoding"]["color"] = {
            **(spec["layer"][1]["encoding"].get("color") or {}), **color
        }

    if "encoding" not in spec:
        spec["encoding"] = {}
    if column:
        spec["encoding"]["column"] = column
    if row:
        spec["encoding"]["row"] = row

    table = ctx.get("table") or []
    config = ctx.get("chartProperties") or {}
    layout = ctx.get("layout") or {}

    x_enc = (spec["layer"][0].get("encoding") or {}).get("x") or {}
    y_enc = (spec["layer"][0].get("encoding") or {}).get("y") or {}
    x_type = x_enc.get("type")
    y_type = y_enc.get("type")

    if _is_measure(y_type):
        spec["layer"][0]["encoding"]["y2"] = {"datum": 0}
    elif _is_measure(x_type):
        spec["layer"][0]["encoding"]["x2"] = {"datum": 0}

    n = len(table)
    canvas = ctx.get("canvasSize") or {}
    plot_width = layout.get("subplotWidth") or canvas.get("width") or 400
    plot_height = layout.get("subplotHeight") or canvas.get("height") or 300

    default_dot_size = config.get("dotSize", 80) if config.get("dotSize") is not None else 80
    plot_area = plot_width * plot_height
    target_coverage = 0.15
    current_coverage = (n * default_dot_size) / plot_area if plot_area > 0 else 0
    dot_size = default_dot_size
    if n > 0 and current_coverage > target_coverage:
        dot_size = js_round(max(4, (target_coverage * plot_area) / n))

    mark1 = spec["layer"][1]["mark"]
    if isinstance(mark1, str):
        mark1 = {"type": mark1}
    spec["layer"][1]["mark"] = {**mark1, "size": dot_size}

    base_stroke = 1.5
    mark0 = spec["layer"][0]["mark"]
    if isinstance(mark0, str):
        mark0 = {"type": mark0}
    if dot_size < default_dot_size:
        ratio = dot_size / default_dot_size
        stroke = max(0.15, base_stroke * ratio)
        mark0 = {**mark0, "strokeWidth": stroke}
        spec["layer"][0]["mark"] = mark0

    discrete_axis = "x" if not _is_measure(x_type) else "y" if not _is_measure(y_type) else None
    discrete_field = (
        x_enc.get("field") if discrete_axis == "x"
        else y_enc.get("field") if discrete_axis == "y"
        else None
    )
    if discrete_field and table:
        counts = {}
        for r in table:
            key = str(r.get(discrete_field) if r.get(discrete_field) is not None else "")
            counts[key] = counts.get(key, 0) + 1
        max_overlap = max(counts.values()) if counts else 0
        if max_overlap > 1:
            mark0 = spec["layer"][0]["mark"]
            if isinstance(mark0, str):
                mark0 = {"type": mark0}
            current_stroke = mark0.get("strokeWidth", base_stroke)
            stroke = max(0.15, current_stroke / max_overlap)
            mark0 = {**mark0, "strokeWidth": stroke}
            spec["layer"][0]["mark"] = mark0

    for axis in ("x", "y"):
        count = (
            layout.get("xContinuousAsDiscrete") if axis == "x" else layout.get("yContinuousAsDiscrete")
        ) or 0
        if count <= 0:
            continue
        eff_step = layout.get("xStep") if axis == "x" else layout.get("yStep")
        if eff_step is None:
            continue
        max_rule_width = max(0.15, min(eff_step * 0.4, 2))
        max_dot_size = max(4, js_round(eff_step * eff_step * 0.6))
        mark0 = spec["layer"][0]["mark"]
        if isinstance(mark0, str):
            mark0 = {"type": mark0}
        current_stroke = mark0.get("strokeWidth", base_stroke)
        spec["layer"][0]["mark"] = set_mark_prop(
            spec["layer"][0]["mark"], "strokeWidth", min(current_stroke, max_rule_width)
        )
        mark1_curr = spec["layer"][1]["mark"]
        if isinstance(mark1_curr, str):
            mark1_curr = {"type": mark1_curr}
        current_dot_size = mark1_curr.get("size", dot_size)
        spec["layer"][1]["mark"] = set_mark_prop(
            spec["layer"][1]["mark"], "size", min(current_dot_size, max_dot_size)
        )

    if config.get("dotSize"):
        mark1_curr = spec["layer"][1]["mark"]
        if isinstance(mark1_curr, str):
            mark1_curr = {"type": mark1_curr}
        spec["layer"][1]["mark"] = {**mark1_curr, "size": config["dotSize"]}


lollipop_chart_def = {
    "chart": "Lollipop Chart",
    "template": {
        "encoding": {},
        "layer": [
            {"mark": {"type": "rule", "strokeWidth": 1.5}, "encoding": {}},
            {"mark": {"type": "circle", "size": 80, "opacity": 1}, "encoding": {}},
        ],
    },
    "channels": ["x", "y", "color", "column", "row"],
    "markCognitiveChannel": "length",
    "declareLayoutMode": _lollipop_declare,
    "instantiate": _lollipop_instantiate,
    "properties": [
        {"key": "dotSize", "label": "Dot Size", "type": "continuous",
         "min": 20, "max": 300, "step": 10, "defaultValue": 80},
    ],
    "encodingActions": [make_sort_action()],
}
