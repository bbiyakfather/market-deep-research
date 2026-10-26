"""Strip Plot template (jitter)."""
from __future__ import annotations

from ...core import js_round
from .utils import default_build_encodings


def _strip_declare(cs, table, chart_properties):
    return {"paramOverrides": {"defaultBandSize": 50, "minStep": 16}}


def _strip_instantiate(spec, ctx):
    default_build_encodings(spec, ctx["resolvedEncodings"])

    table = ctx.get("table") or []
    canvas = ctx.get("canvasSize") or {}
    config = ctx.get("chartProperties") or {}

    step_width = config.get("stepWidth")
    if step_width is None:
        step_width = 20
    point_size = config.get("pointSize") if config.get("pointSize") is not None else 0
    opacity = config.get("opacity") if config.get("opacity") is not None else 0

    encoding = spec.get("encoding") or {}
    x_type = (encoding.get("x") or {}).get("type")
    y_type = (encoding.get("y") or {}).get("type")

    cat_axis = (
        "x" if x_type in ("nominal", "ordinal")
        else "y" if y_type in ("nominal", "ordinal")
        else None
    )

    max_group_count = len(table)
    if cat_axis and (encoding.get(cat_axis) or {}).get("field") and table:
        cat_field = encoding[cat_axis]["field"]
        group_counts = {}
        for r in table:
            key = str(r.get(cat_field) if r.get(cat_field) is not None else "")
            group_counts[key] = group_counts.get(key, 0) + 1
        max_group_count = max(1, *group_counts.values()) if group_counts else 1

    cont_len = (canvas.get("height") or 400) if cat_axis == "x" else (canvas.get("width") or 400)
    area_budget = step_width * cont_len
    target_coverage = 0.35

    if point_size == 0:
        ideal_size = (target_coverage * area_budget) / max_group_count if max_group_count else 0
        point_size = max(5, min(100, js_round(ideal_size)))

    if opacity == 0:
        density = (max_group_count * point_size) / area_budget if area_budget else 0
        if density < 0.2:
            opacity = 0.8
        elif density < 0.5:
            opacity = 0.6
        elif density < 1:
            opacity = 0.4
        else:
            opacity = max(0.1, 0.3 / density) if density else 0.1
        opacity = js_round(opacity * 20) / 20

    mark = spec.get("mark")
    if isinstance(mark, str):
        mark = {"type": mark}
    mark["size"] = point_size
    mark["opacity"] = opacity
    spec["mark"] = mark

    jitter_width = step_width * 0.6
    if cat_axis == "x":
        spec["width"] = {"step": step_width}
    elif cat_axis == "y":
        spec["height"] = {"step": step_width}

    if jitter_width > 0:
        if not spec.get("transform"):
            spec["transform"] = []
        # Render integer-valued floats without a trailing `.0` to match JS.
        def _fmt(v):
            return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)
        neg_half = -jitter_width / 2
        spec["transform"].append({
            "calculate": f"{_fmt(neg_half)} + random() * {_fmt(jitter_width)}",
            "as": "__jitter",
        })
        offset_enc = {
            "field": "__jitter",
            "type": "quantitative",
            "axis": None,
            "scale": {"domain": [-step_width / 2, step_width / 2]},
        }
        if cat_axis == "x":
            spec["encoding"]["xOffset"] = offset_enc
        elif cat_axis == "y":
            spec["encoding"]["yOffset"] = offset_enc
        else:
            spec["encoding"]["xOffset"] = offset_enc


strip_plot_def = {
    "chart": "Strip Plot",
    "template": {
        "mark": {"type": "circle", "opacity": 0.7},
        "encoding": {},
    },
    "channels": ["x", "y", "color", "size", "column", "row"],
    "markCognitiveChannel": "position",
    "declareLayoutMode": _strip_declare,
    "instantiate": _strip_instantiate,
    "properties": [
        {"key": "stepWidth", "label": "Jitter", "type": "continuous",
         "min": 10, "max": 100, "step": 5, "defaultValue": 20},
        {"key": "pointSize", "label": "Size", "type": "continuous",
         "min": 0, "max": 150, "step": 5, "defaultValue": 0},
        {"key": "opacity", "label": "Opacity", "type": "continuous",
         "min": 0, "max": 1, "step": 0.05, "defaultValue": 0},
    ],
}
