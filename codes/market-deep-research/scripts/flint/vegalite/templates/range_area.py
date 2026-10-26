"""Range Area Chart (band / high-low / area-range) template.

A filled band over a continuum showing a low-high range at each x. Port of
vegalite/templates/range-area.ts.
"""
from __future__ import annotations

from .utils import default_build_encodings, set_mark_prop


def _range_area_declare_layout(cs, table, chart_properties):
    return {
        "paramOverrides": {
            "continuousMarkCrossSection": {"x": 100, "y": 20, "seriesCountAxis": "auto"},
            "facetAspectRatioResistance": 0.5,
        },
    }


def _range_area_instantiate(spec, ctx):
    default_build_encodings(spec, ctx["resolvedEncodings"])

    encoding = spec.get("encoding") or {}
    y_enc = encoding.get("y")
    y2_enc = encoding.get("y2")
    if not y_enc or not (y2_enc and y2_enc.get("field")):
        return

    # y2 (upper bound) shares y's scale — only the field reference is needed.
    spec["encoding"]["y2"] = {"field": y2_enc["field"]}

    # The band spans y..y2; it is NOT measured from a zero baseline.
    y_enc["scale"] = {**(y_enc.get("scale") or {}), "zero": False, "nice": True}

    # Multiple bands (a color series) must OVERLAP, never stack.
    if spec["encoding"].get("color"):
        y_enc["stack"] = None

    config = ctx.get("chartProperties")
    if config and config.get("interpolate"):
        spec["mark"] = set_mark_prop(spec.get("mark"), "interpolate", config["interpolate"])
    if config and config.get("opacity") is not None and config["opacity"] < 1:
        spec["mark"] = set_mark_prop(spec.get("mark"), "opacity", config["opacity"])


range_area_chart_def = {
    "chart": "Range Area Chart",
    "template": {"mark": {"type": "area", "opacity": 0.5, "line": {"strokeWidth": 1}}, "encoding": {}},
    "channels": ["x", "y", "y2", "color", "column", "row"],
    "markCognitiveChannel": "area",
    "declareLayoutMode": _range_area_declare_layout,
    "instantiate": _range_area_instantiate,
    "properties": [
        {
            "key": "interpolate", "label": "Curve", "type": "discrete",
            "options": [
                {"value": None, "label": "Default (linear)"},
                {"value": "linear", "label": "Linear"},
                {"value": "monotone", "label": "Monotone (smooth)"},
                {"value": "step", "label": "Step"},
                {"value": "step-before", "label": "Step Before"},
                {"value": "step-after", "label": "Step After"},
                {"value": "basis", "label": "Basis (smooth)"},
            ],
        },
        {"key": "opacity", "label": "Opacity", "type": "continuous",
         "min": 0.1, "max": 1, "step": 0.05, "defaultValue": 0.5},
    ],
}
