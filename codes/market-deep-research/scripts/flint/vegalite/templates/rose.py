"""Rose Chart (Nightingale / Coxcomb) template."""
from __future__ import annotations

import math
import re

from .utils import set_mark_prop


def _rose_declare_layout(cs, table, chart_properties):
    return {}


_XY_SORT_RE = re.compile(r"^-?[xy]$")


def _rose_instantiate(spec, ctx):
    if "encoding" not in spec:
        spec["encoding"] = {}

    re_encodings = ctx["resolvedEncodings"]
    x = re_encodings.get("x")
    y = re_encodings.get("y")
    color = re_encodings.get("color")
    column = re_encodings.get("column")
    row = re_encodings.get("row")
    rest = {k: v for k, v in re_encodings.items() if k not in ("x", "y", "color", "column", "row")}
    is_faceted = bool(column or row)

    # ── theta encoding (shared) ──
    if x:
        theta_enc = {**x}
        if theta_enc.get("type") in ("quantitative", "temporal"):
            theta_enc["type"] = "nominal"
        s = theta_enc.get("sort")
        if isinstance(s, str) and _XY_SORT_RE.match(s):
            del theta_enc["sort"]
        if "scale" in theta_enc:
            del theta_enc["scale"]
        theta_enc["stack"] = True

        cats = set()
        for r in ctx["table"]:
            cats.add(r.get(x["field"]))
        n = len(cats)
        if n > 0:
            alignment = (ctx.get("chartProperties") or {}).get("alignment", "left")
            if alignment == "center":
                half_slice = math.pi / n
                theta_enc["scale"] = {"range": [-half_slice, 2 * math.pi - half_slice]}

        spec["encoding"]["theta"] = theta_enc

    radius_enc = None
    radius_field = None
    if y:
        radius_enc = {**y}
        s = radius_enc.get("sort")
        if isinstance(s, str) and _XY_SORT_RE.match(s):
            del radius_enc["sort"]
        radius_enc["scale"] = {"type": "sqrt"}
        if color:
            radius_enc["stack"] = True
        radius_field = radius_enc.get("field")

    color_enc = None
    if color:
        color_enc = color
    elif x:
        color_enc = {"field": x["field"], "type": x.get("type") or "nominal"}
        if isinstance(x.get("sort"), list):
            color_enc["sort"] = x["sort"]

    if is_faceted:
        if radius_enc:
            spec["encoding"]["radius"] = radius_enc
        if color_enc:
            spec["encoding"]["color"] = color_enc

        if column and not row:
            facet_enc = {**column}
            cats = set()
            for r in ctx["table"]:
                cats.add(r.get(column["field"]))
            facet_count = len(cats)
            facet_enc["columns"] = facet_count if facet_count <= 6 else math.ceil(math.sqrt(facet_count))
            spec["encoding"]["facet"] = facet_enc
        elif row and not column:
            spec["encoding"]["row"] = row
        else:
            spec["encoding"]["column"] = column
            spec["encoding"]["row"] = row
    else:
        arc_mark = spec.get("mark")
        spec["layer"] = [
            {"mark": arc_mark, "encoding": {}},
            {
                "mark": {"type": "text", "radiusOffset": 15, "fontSize": 11},
                "encoding": {},
            },
        ]
        if "mark" in spec:
            del spec["mark"]

        if radius_enc:
            spec["layer"][0]["encoding"]["radius"] = radius_enc
        if color_enc:
            spec["layer"][0]["encoding"]["color"] = color_enc

        if x and spec["layer"][1]:
            text_layer = spec["layer"][1]
            text_layer["encoding"]["text"] = {"field": x["field"], "type": x.get("type") or "nominal"}
            if radius_field:
                text_layer["transform"] = [
                    {
                        "aggregate": [{"op": "sum", "field": radius_field, "as": radius_field}],
                        "groupby": [x["field"]],
                    },
                ]
                text_layer["encoding"]["radius"] = {
                    "field": radius_field,
                    "type": "quantitative",
                    "scale": {"type": "sqrt"},
                }

    has_radius = (
        spec.get("encoding", {}).get("radius")
        or (spec.get("layer") and spec["layer"][0].get("encoding", {}).get("radius"))
    )
    if not has_radius:
        fallback = {"aggregate": "count", "type": "quantitative", "scale": {"type": "sqrt"}}
        if spec.get("layer"):
            spec["layer"][0]["encoding"]["radius"] = fallback
        else:
            spec["encoding"]["radius"] = fallback
    if not spec["encoding"].get("theta"):
        spec["encoding"]["theta"] = {"aggregate": "count", "type": "quantitative"}

    mapped_channels = {"x", "y", "color", "column", "row", "radius", "size", "theta", "facet"}
    for ch, enc in rest.items():
        if ch in mapped_channels:
            continue
        if not enc.get("field") and not enc.get("aggregate"):
            continue
        spec["encoding"][ch] = enc

    layout = ctx["layout"]
    canvas = ctx.get("canvasSize") or {}
    sub_w = layout.get("subplotWidth") if layout.get("subplotWidth") is not None else canvas.get("width")
    sub_h = layout.get("subplotHeight") if layout.get("subplotHeight") is not None else canvas.get("height")
    size = min(sub_w, sub_h)
    spec["width"] = size
    spec["height"] = size

    config = ctx.get("chartProperties")
    if config:
        mark_target = spec["layer"][0] if spec.get("layer") else spec
        if config.get("innerRadius", 0) > 0:
            mark_target["mark"] = set_mark_prop(mark_target.get("mark"), "innerRadius", config["innerRadius"])
        if config.get("padAngle", 0) > 0:
            mark_target["mark"] = set_mark_prop(mark_target.get("mark"), "padAngle", config["padAngle"])


rose_chart_def = {
    "chart": "Rose Chart",
    "template": {
        "mark": {
            "type": "arc",
            "stroke": "white",
            "padAngle": 0.02,
        },
        "encoding": {},
    },
    "channels": ["x", "y", "color", "column", "row"],
    "markCognitiveChannel": "area",
    "declareLayoutMode": _rose_declare_layout,
    "instantiate": _rose_instantiate,
    "properties": [
        {"key": "innerRadius", "label": "Inner Radius", "type": "continuous",
         "min": 0, "max": 100, "step": 5, "defaultValue": 0},
        {"key": "padAngle", "label": "Gap", "type": "continuous",
         "min": 0, "max": 0.1, "step": 0.005, "defaultValue": 0},
        {
            "key": "alignment", "label": "Alignment", "type": "discrete", "options": [
                {"value": "left", "label": "Left (default)"},
                {"value": "center", "label": "Center"},
            ],
        },
    ],
}
