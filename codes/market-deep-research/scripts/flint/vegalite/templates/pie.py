"""Pie Chart template."""
from __future__ import annotations

from ...core.decisions import compute_circumference_pressure, compute_effective_bar_count
from .utils import set_mark_prop


def _pie_instantiate(spec, ctx):
    if "encoding" not in spec:
        spec["encoding"] = {}
    for ch, enc in ctx["resolvedEncodings"].items():
        if ch == "size":
            theta_enc = {k: v for k, v in enc.items() if k != "scale"}
            spec["encoding"]["theta"] = theta_enc
        else:
            spec["encoding"][ch] = enc

    if not spec["encoding"].get("theta"):
        spec["encoding"]["theta"] = {"aggregate": "count", "type": "quantitative"}

    config = ctx.get("chartProperties")
    if config and config.get("innerRadius", 0) > 0:
        spec["mark"] = set_mark_prop(spec.get("mark"), "innerRadius", config["innerRadius"])

    theta_field = spec["encoding"].get("theta", {}).get("field")
    color_field = spec["encoding"].get("color", {}).get("field") if spec["encoding"].get("color") else None

    table = ctx["table"]
    if theta_field and color_field:
        agg: dict = {}
        for row in table:
            cat = str(row.get(color_field) if row.get(color_field) is not None else "")
            try:
                val = float(row.get(theta_field) or 0)
            except (TypeError, ValueError):
                val = 0.0
            agg[cat] = agg.get(cat, 0) + val
        effective_count = compute_effective_bar_count(list(agg.values()))
    elif color_field:
        cats = set()
        for r in table:
            cats.add(str(r.get(color_field) if r.get(color_field) is not None else ""))
        effective_count = len(cats)
    else:
        effective_count = len(table)

    assemble_options = ctx.get("assembleOptions") or {}
    pressure_params = {
        "minArcPx": 45,
        "minRadius": 60,
        "margin": 50,
    }
    if assemble_options.get("maxStretch") is not None:
        pressure_params["maxStretch"] = assemble_options["maxStretch"]
    if assemble_options.get("maxStretchX") is not None:
        pressure_params["maxStretchX"] = assemble_options["maxStretchX"]
    if assemble_options.get("maxStretchY") is not None:
        pressure_params["maxStretchY"] = assemble_options["maxStretchY"]
    pressure = compute_circumference_pressure(
        effective_count,
        ctx["canvasSize"],
        pressure_params,
    )

    spec["width"] = pressure["canvasW"]
    spec["height"] = pressure["canvasH"]


pie_chart_def = {
    "chart": "Pie Chart",
    "template": {"mark": "arc", "encoding": {}},
    "channels": ["size", "color", "column", "row"],
    "markCognitiveChannel": "area",
    "instantiate": _pie_instantiate,
    "properties": [
        {"key": "innerRadius", "label": "Donut", "type": "continuous",
         "min": 0, "max": 100, "step": 5, "defaultValue": 0},
    ],
}
