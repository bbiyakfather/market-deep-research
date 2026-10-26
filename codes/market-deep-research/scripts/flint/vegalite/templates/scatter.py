"""Scatter Plot, Regression, Ranged Dot Plot, and Boxplot templates."""
from __future__ import annotations

import copy

from .utils import (
    default_build_encodings,
    apply_point_size_scaling,
    set_mark_prop,
    detect_banded_axis_force_discrete,
)


def _scatter_instantiate(spec, ctx):
    default_build_encodings(spec, ctx["resolvedEncodings"])
    # A `shape` encoding only renders distinct glyphs on the `point` mark;
    # `circle` ignores it. Promote the mark when shape is in play.
    if (spec.get("encoding") or {}).get("shape", {}).get("field"):
        spec["mark"] = set_mark_prop(spec.get("mark"), "type", "point")
    canvas = ctx.get("canvasSize") or {}
    apply_point_size_scaling(spec, ctx["table"], canvas.get("width"), canvas.get("height"))
    config = ctx.get("chartProperties")
    if config and config.get("opacity") is not None and config["opacity"] < 1:
        spec["mark"] = set_mark_prop(spec.get("mark"), "opacity", config["opacity"])


scatter_plot_def = {
    "chart": "Scatter Plot",
    "template": {"mark": "circle", "encoding": {}},
    "channels": ["x", "y", "color", "size", "shape", "opacity", "column", "row"],
    "markCognitiveChannel": "position",
    "instantiate": _scatter_instantiate,
    "properties": [
        {"key": "opacity", "label": "Opacity", "type": "continuous",
         "min": 0.1, "max": 1, "step": 0.05, "defaultValue": 1},
    ],
}


# ─── Regression ─────────────────────────────────────────────────────────────

def _regression_instantiate(spec, ctx):
    encs = ctx["resolvedEncodings"]
    x = encs.get("x")
    y = encs.get("y")
    color = encs.get("color")
    size = encs.get("size")
    column = encs.get("column")
    row = encs.get("row")
    config = ctx.get("chartProperties")

    layer0 = spec["layer"][0]
    layer1 = spec["layer"][1]

    if x:
        layer0["encoding"]["x"] = {**layer0["encoding"].get("x", {}), **x}
        layer1["encoding"]["x"] = {**layer1["encoding"].get("x", {}), **x}
        if x.get("field"):
            layer1["transform"][0]["on"] = x["field"]
    if y:
        layer0["encoding"]["y"] = {**layer0["encoding"].get("y", {}), **y}
        layer1["encoding"]["y"] = {**layer1["encoding"].get("y", {}), **y}
        if y.get("field"):
            layer1["transform"][0]["regression"] = y["field"]

    method = (config or {}).get("regressionMethod")
    if method and method != "linear":
        layer1["transform"][0]["method"] = method
        if method == "poly":
            order = (config or {}).get("polyOrder", 3)
            layer1["transform"][0]["order"] = order

    if color:
        layer0["encoding"]["color"] = {**layer0["encoding"].get("color", {}), **color}
        if color.get("field"):
            layer1["transform"][0]["groupby"] = [color["field"]]
            layer1["encoding"]["color"] = {**color}
            layer1["mark"] = {"type": "line"}

    if size:
        layer0["encoding"]["size"] = {**layer0["encoding"].get("size", {}), **size}

    if "encoding" not in spec:
        spec["encoding"] = {}
    if column:
        spec["encoding"]["column"] = column
    if row:
        spec["encoding"]["row"] = row


regression_def = {
    "chart": "Regression",
    "template": {
        "layer": [
            {
                "mark": "circle",
                "encoding": {"x": {}, "y": {}, "color": {}, "size": {}},
            },
            {
                "mark": {"type": "line", "color": "red"},
                "transform": [{"regression": "field1", "on": "field2"}],
                "encoding": {"x": {}, "y": {}},
            },
        ],
    },
    "channels": ["x", "y", "size", "color", "column", "row"],
    "markCognitiveChannel": "position",
    "instantiate": _regression_instantiate,
    "properties": [
        {"key": "regressionMethod", "label": "Method", "type": "discrete",
         "options": [
             {"value": "linear", "label": "Linear"},
             {"value": "log", "label": "Logarithmic"},
             {"value": "exp", "label": "Exponential"},
             {"value": "pow", "label": "Power"},
             {"value": "quad", "label": "Quadratic"},
             {"value": "poly", "label": "Polynomial"},
         ],
         "defaultValue": "linear"},
        {"key": "polyOrder", "label": "Poly Order", "type": "continuous",
         "min": 2, "max": 10, "step": 1, "defaultValue": 3},
    ],
}


# ─── Ranged Dot Plot ────────────────────────────────────────────────────────

def _ranged_dot_instantiate(spec, ctx):
    encs = ctx["resolvedEncodings"]
    color = encs.get("color")
    rest = {ch: enc for ch, enc in encs.items() if ch != "color"}
    if "encoding" not in spec:
        spec["encoding"] = {}
    for ch, enc in rest.items():
        spec["encoding"][ch] = {**(spec["encoding"].get(ch) or {}), **enc}
    if color:
        layer1_enc = spec["layer"][1]["encoding"]
        layer1_enc["color"] = {**(layer1_enc.get("color") or {}), **color}

    encoding = spec.get("encoding") or {}
    y_enc = encoding.get("y")
    x_enc = encoding.get("x")
    if y_enc and y_enc.get("type") == "nominal":
        spec["layer"][0]["encoding"]["detail"] = copy.deepcopy(y_enc)
    elif x_enc and x_enc.get("type") == "nominal":
        spec["layer"][0]["encoding"]["detail"] = copy.deepcopy(x_enc)


ranged_dot_plot_def = {
    "chart": "Ranged Dot Plot",
    "template": {
        "encoding": {},
        "layer": [
            {"mark": "line", "encoding": {"detail": {}}},
            {"mark": {"type": "point", "filled": True}, "encoding": {"color": {}}},
        ],
    },
    "channels": ["x", "y", "color"],
    "markCognitiveChannel": "position",
    "instantiate": _ranged_dot_instantiate,
}


# ─── Boxplot ────────────────────────────────────────────────────────────────

def _boxplot_declare(cs, table, chart_properties):
    if not (cs.get("x") or {}).get("field") or not (cs.get("y") or {}).get("field"):
        return {}
    result = detect_banded_axis_force_discrete(cs, table, {"preferAxis": "x"})
    if not result:
        return {}
    return {
        "axisFlags": {result["axis"]: {"banded": True}},
        "resolvedTypes": result.get("resolvedTypes"),
        "paramOverrides": {"defaultBandSize": 28},
    }


def _boxplot_instantiate(spec, ctx):
    default_build_encodings(spec, ctx["resolvedEncodings"])
    layout = ctx.get("layout") or {}
    x_count = layout.get("xNominalCount", 0) or 0
    y_count = layout.get("yNominalCount", 0) or 0
    if x_count > 0 or y_count > 0:
        box_step = layout.get("xStep") if x_count > 0 else layout.get("yStep")
        if box_step is not None:
            from ...core import js_round
            box_size = max(4, js_round(box_step * 0.7))
            spec["mark"] = set_mark_prop(spec.get("mark"), "size", box_size)


boxplot_def = {
    "chart": "Boxplot",
    "template": {"mark": "boxplot", "encoding": {}},
    "channels": ["x", "y", "color", "opacity", "column", "row"],
    "markCognitiveChannel": "position",
    "declareLayoutMode": _boxplot_declare,
    "instantiate": _boxplot_instantiate,
}
