"""Line Chart template."""
from __future__ import annotations

from .utils import default_build_encodings, set_mark_prop


def _apply_interpolate(vg_spec, config):
    if not config or not config.get("interpolate"):
        return
    vg_spec["mark"] = set_mark_prop(vg_spec.get("mark"), "interpolate", config["interpolate"])


def _apply_interpolate_to_mark(mark, config):
    """Return a mark with interpolate applied (mirrors JS applyInterpolate)."""
    if not config or not config.get("interpolate"):
        return mark
    return set_mark_prop(mark, "interpolate", config["interpolate"])


def _apply_show_points(vg_spec, config):
    if not config or not config.get("showPoints"):
        return
    vg_spec["mark"] = set_mark_prop(vg_spec.get("mark"), "point", True)


def _is_continuous_color(ctx) -> bool:
    color = (ctx.get("resolvedEncodings") or {}).get("color")
    if not color or not color.get("field"):
        return False
    color_type = color.get("type") or (ctx.get("channelSemantics") or {}).get("color", {}).get("type")
    return color_type in ("quantitative", "temporal")


def _build_continuous_color_layers(spec, resolved_encodings, chart_properties):
    """Vega-Lite splits a line into one segment per datum when color is
    quantitative, so nothing visible connects. Mirror ECharts: a neutral line
    plus colored points.
    """
    color = resolved_encodings.get("color")
    column = resolved_encodings.get("column")
    row = resolved_encodings.get("row")
    x = resolved_encodings.get("x")
    y = resolved_encodings.get("y")
    detail = resolved_encodings.get("detail")
    opacity = resolved_encodings.get("opacity")

    # The line keeps every channel except color/column/row.
    consumed = {"color", "column", "row"}
    line_encoding: dict = {}
    for ch, enc in resolved_encodings.items():
        if ch in consumed:
            continue
        if isinstance(enc, dict) and len(enc) > 0:
            line_encoding[ch] = enc

    point_encoding: dict = {}
    if x:
        point_encoding["x"] = x
    if y:
        point_encoding["y"] = y
    if color:
        point_encoding["color"] = color
    if detail:
        point_encoding["detail"] = detail
    if opacity:
        point_encoding["opacity"] = opacity

    spec["layer"] = [
        {
            "mark": _apply_interpolate_to_mark({"type": "line", "color": "#cccccc"}, chart_properties),
            "encoding": line_encoding,
        },
        {
            "mark": {"type": "point", "filled": True, "size": 80},
            "encoding": point_encoding,
        },
    ]
    spec.pop("mark", None)

    if column or row:
        if not spec.get("encoding"):
            spec["encoding"] = {}
        if column:
            spec["encoding"]["column"] = column
        if row:
            spec["encoding"]["row"] = row
    else:
        spec.pop("encoding", None)


def _line_declare_layout(cs, table, chart_properties):
    return {
        "paramOverrides": {
            "continuousMarkCrossSection": {"x": 100, "y": 20, "seriesCountAxis": "auto"},
            "facetAspectRatioResistance": 0.5,
        },
    }


def _line_instantiate(spec, ctx):
    if _is_continuous_color(ctx):
        _build_continuous_color_layers(spec, ctx["resolvedEncodings"], ctx.get("chartProperties"))
        return
    default_build_encodings(spec, ctx["resolvedEncodings"])
    _apply_interpolate(spec, ctx.get("chartProperties"))
    _apply_show_points(spec, ctx.get("chartProperties"))


line_chart_def = {
    "chart": "Line Chart",
    "template": {"mark": "line", "encoding": {}},
    "channels": ["x", "y", "color", "strokeDash", "detail", "opacity", "column", "row"],
    "markCognitiveChannel": "position",
    "declareLayoutMode": _line_declare_layout,
    "instantiate": _line_instantiate,
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
                {"value": "cardinal", "label": "Cardinal"},
                {"value": "catmull-rom", "label": "Catmull-Rom"},
            ],
        },
        {"key": "showPoints", "label": "Show points", "type": "binary", "defaultValue": False},
    ],
}
