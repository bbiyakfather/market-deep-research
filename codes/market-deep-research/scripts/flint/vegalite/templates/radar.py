"""Radar / Spider Chart template."""
from __future__ import annotations

import math
import re
from typing import Any, Optional
from ...core import js_round


def _nice_max(v: float) -> float:
    if v <= 0:
        return 1
    pw = math.pow(10, math.floor(math.log10(v)))
    mantissa = v / pw
    if mantissa <= 1:
        nice = 1
    elif mantissa <= 2:
        nice = 2
    elif mantissa <= 2.5:
        nice = 2.5
    elif mantissa <= 5:
        nice = 5
    else:
        nice = 10
    return nice * pw


def _build_radar_layers(rows, axis_field, value_field, group_field, opts):
    axes: list = []
    axis_set: set = set()
    for row in rows:
        a = str(row.get(axis_field))
        if a not in axis_set:
            axis_set.add(a)
            axes.append(a)
    if len(axes) < 2:
        return []

    groups: list = []
    if group_field:
        group_set: set = set()
        for row in rows:
            g = str(row.get(group_field))
            if g not in group_set:
                group_set.add(g)
                groups.append(g)
    else:
        groups.append("_all")

    axis_max: dict = {}
    for axis in axes:
        vals = []
        for r in rows:
            if str(r.get(axis_field)) == axis:
                try:
                    v = float(r.get(value_field))
                    if math.isfinite(v):
                        vals.append(v)
                except (TypeError, ValueError):
                    pass
        mx = max(vals) if vals else 1
        axis_max[axis] = _nice_max(mx)

    key_map: dict = {}
    for row in rows:
        grp = str(row.get(group_field)) if group_field else "_all"
        axis = str(row.get(axis_field))
        try:
            raw = float(row.get(value_field) or 0)
        except (TypeError, ValueError):
            raw = 0.0
        mx = axis_max.get(axis, 0)
        norm = raw / mx if mx > 0 else 0
        k = f"{grp}|||{axis}"
        if k not in key_map:
            key_map[k] = {"sum": 0.0, "rawSum": 0.0, "count": 0}
        e = key_map[k]
        e["sum"] += norm
        e["rawSum"] += raw
        e["count"] += 1

    angle_step = 360 / len(axes)
    final_data: list = []
    for k, v in key_map.items():
        grp, axis = k.split("|||")
        axis_index = axes.index(axis)
        angle = axis_index * angle_step
        norm_val = v["sum"] / v["count"]
        raw_val = js_round((v["rawSum"] / v["count"]) * 100) / 100
        rad = angle * math.pi / 180
        final_data.append({
            "__group": grp,
            "__axis": axis,
            "__value": norm_val,
            "__raw": raw_val,
            "__angle": angle,
            "__x": norm_val * math.sin(rad),
            "__y": -norm_val * math.cos(rad),
        })

    grid_data: list = []
    for idx in range(len(axes)):
        ang = idx * angle_step * math.pi / 180
        grid_data.append({
            "__type": "spoke",
            "__x": 0, "__y": 0,
            "__x2": math.sin(ang),
            "__y2": -math.cos(ang),
        })
    for level in (0.25, 0.5, 0.75, 1.0):
        points: list = []
        for i in range(len(axes) + 1):
            ang = (i % len(axes)) * angle_step * math.pi / 180
            points.append({"__x": level * math.sin(ang), "__y": -level * math.cos(ang)})
        for i in range(len(points) - 1):
            grid_data.append({
                "__type": "ring", "__level": level,
                "__x": points[i]["__x"], "__y": points[i]["__y"],
                "__x2": points[i + 1]["__x"], "__y2": points[i + 1]["__y"],
            })

    label_data: list = []
    for i, axis in enumerate(axes):
        ang_deg = i * angle_step
        ang = ang_deg * math.pi / 180
        r = 1.15
        mx = axis_max[axis]
        # JS: mx % 1 === 0 ? String(mx) : mx.toFixed(1)
        if mx == int(mx):
            max_str = _js_number_to_string(mx)
        else:
            max_str = f"{mx:.1f}"

        sin_a = math.sin(ang)
        cos_a = -math.cos(ang)
        align = ""
        baseline = ""
        dx = 0
        dy = 0

        if abs(sin_a) < 0.15:
            align = "center"
            baseline = "bottom" if cos_a < 0 else "top"
            dy = -4 if cos_a < 0 else 4
        elif sin_a > 0:
            align = "left"
            baseline = "middle" if abs(cos_a) < 0.3 else ("bottom" if cos_a < 0 else "top")
            dx = 4
        else:
            align = "right"
            baseline = "middle" if abs(cos_a) < 0.3 else ("bottom" if cos_a < 0 else "top")
            dx = -4

        label_data.append({
            "__label": [axis, f"({max_str})"],
            "__x": r * math.sin(ang), "__y": -r * math.cos(ang),
            "__align": align, "__baseline": baseline, "__dx": dx, "__dy": dy,
        })

    filled = opts["filled"]
    fill_opacity = opts["fillOpacity"]
    stroke_width = opts["strokeWidth"]
    domain_pad = opts["domainPad"]
    layers: list = []

    # Spokes
    layers.append({
        "data": {"values": [d for d in grid_data if d["__type"] == "spoke"]},
        "mark": {"type": "rule", "stroke": "#ddd", "strokeWidth": 0.8},
        "encoding": {
            "x": {"field": "__x", "type": "quantitative", "scale": {"domain": [-domain_pad, domain_pad]}, "axis": None},
            "y": {"field": "__y", "type": "quantitative", "scale": {"domain": [-domain_pad, domain_pad]}, "axis": None},
            "x2": {"field": "__x2"}, "y2": {"field": "__y2"},
        },
    })

    # Rings
    layers.append({
        "data": {"values": [d for d in grid_data if d["__type"] == "ring"]},
        "mark": {"type": "rule", "stroke": "#e0e0e0", "strokeWidth": 0.6},
        "encoding": {
            "x": {"field": "__x", "type": "quantitative", "axis": None},
            "y": {"field": "__y", "type": "quantitative", "axis": None},
            "x2": {"field": "__x2"}, "y2": {"field": "__y2"},
        },
    })

    # Labels
    for lbl in label_data:
        lines = lbl["__label"]
        layers.append({
            "data": {"values": [lbl]},
            "mark": {
                "type": "text", "fontSize": 10, "fill": "#555",
                "align": lbl["__align"], "baseline": lbl["__baseline"],
                "dx": lbl["__dx"], "dy": lbl["__dy"],
                "limit": 120, "lineHeight": 13,
            },
            "encoding": {
                "x": {"field": "__x", "type": "quantitative", "axis": None},
                "y": {"field": "__y", "type": "quantitative", "axis": None},
                "text": {"value": lines},
            },
        })

    # Data polygon
    line_layer: dict = {
        "data": {"values": final_data},
        "mark": {
            "type": "line", "interpolate": "linear-closed", "strokeWidth": stroke_width, "point": False,
        },
        "encoding": {
            "x": {"field": "__x", "type": "quantitative", "axis": None},
            "y": {"field": "__y", "type": "quantitative", "axis": None},
            "order": {"field": "__angle", "type": "quantitative"},
            "tooltip": [
                {"field": "__axis", "type": "nominal", "title": axis_field},
                {"field": "__raw", "type": "quantitative", "title": value_field},
            ],
        },
    }
    if filled:
        line_layer["mark"]["fillOpacity"] = fill_opacity
    if len(groups) > 1 and group_field:
        line_layer["encoding"]["stroke"] = {"field": "__group", "type": "nominal", "title": group_field}
        if filled:
            line_layer["encoding"]["fill"] = {"field": "__group", "type": "nominal", "title": group_field, "legend": None}
    elif filled:
        line_layer["mark"]["fill"] = "#4c78a8"
    layers.append(line_layer)

    # Data points
    point_layer: dict = {
        "data": {"values": final_data},
        "mark": {"type": "point", "filled": True, "size": 25},
        "encoding": {
            "x": {"field": "__x", "type": "quantitative", "axis": None},
            "y": {"field": "__y", "type": "quantitative", "axis": None},
            "tooltip": (
                ([{"field": "__group", "type": "nominal", "title": group_field}] if group_field else []) +
                [
                    {"field": "__axis", "type": "nominal", "title": axis_field},
                    {"field": "__raw", "type": "quantitative", "title": value_field},
                ]
            ),
        },
    }
    if len(groups) > 1 and group_field:
        point_layer["encoding"]["color"] = {"field": "__group", "type": "nominal", "title": group_field, "legend": None}
    layers.append(point_layer)

    return layers


def _js_number_to_string(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return repr(v)


def _radar_instantiate(spec, ctx):
    axis_field = (ctx["resolvedEncodings"].get("x") or {}).get("field")
    value_field = (ctx["resolvedEncodings"].get("y") or {}).get("field")
    group_field = (ctx["resolvedEncodings"].get("color") or {}).get("field")
    column_field = (ctx["resolvedEncodings"].get("column") or {}).get("field")
    row_field = (ctx["resolvedEncodings"].get("row") or {}).get("field")

    table = ctx["table"]
    canvas_size = ctx.get("canvasSize") or {}
    config = ctx.get("chartProperties")

    filled = (config or {}).get("filled", True) if config else True
    fill_opacity = (config or {}).get("fillOpacity", 0.15) if config else 0.15
    stroke_width = (config or {}).get("strokeWidth", 1.5) if config else 1.5

    if not table or len(table) == 0 or not axis_field or not value_field:
        spec["mark"] = "point"
        return

    size = min(canvas_size.get("width") or 400, canvas_size.get("height") or 400)
    layer_opts = {
        "filled": filled, "fillOpacity": fill_opacity,
        "strokeWidth": stroke_width, "domainPad": 1.18,
    }

    if not column_field and not row_field:
        layers = _build_radar_layers(table, axis_field, value_field, group_field, layer_opts)
        if len(layers) == 0:
            spec["mark"] = "point"
            return

        final_spec = {
            "width": size, "height": size, "layer": layers,
            "config": {"view": {"stroke": None}},
        }
        keys = list(spec.keys())
        for k in keys:
            del spec[k]
        spec.update(final_spec)
        return

    col_groups: list = []
    if column_field:
        seen = set()
        for r in table:
            v = str(r.get(column_field))
            if v not in seen:
                seen.add(v)
                col_groups.append(v)
    else:
        col_groups = ["_all"]
    row_groups: list = []
    if row_field:
        seen = set()
        for r in table:
            v = str(r.get(row_field))
            if v not in seen:
                seen.add(v)
                row_groups.append(v)
    else:
        row_groups = ["_all"]

    min_subplot = 200
    subplot_size = max(min_subplot, size)

    def build_subplot(rows, title=None):
        layers = _build_radar_layers(rows, axis_field, value_field, group_field, layer_opts)
        if len(layers) == 0:
            return None
        out = {
            "width": subplot_size, "height": subplot_size,
            "layer": layers,
        }
        if title:
            out["title"] = title
        return out

    final_spec: dict = {}
    concat_spacing = 5

    if row_field and column_field:
        vconcat: list = []
        for rg in row_groups:
            hconcat: list = []
            for cg in col_groups:
                subset = [r for r in table if str(r.get(row_field)) == rg and str(r.get(column_field)) == cg]
                s = build_subplot(subset, f"{cg}")
                if s:
                    hconcat.append(s)
            if len(hconcat) > 0:
                vconcat.append({"hconcat": hconcat, "spacing": concat_spacing, "title": rg})
        final_spec = {"vconcat": vconcat, "spacing": concat_spacing, "config": {"view": {"stroke": None}}}
    elif column_field:
        hconcat: list = []
        for cg in col_groups:
            subset = [r for r in table if str(r.get(column_field)) == cg]
            s = build_subplot(subset, cg)
            if s:
                hconcat.append(s)
        final_spec = {"hconcat": hconcat, "spacing": concat_spacing, "config": {"view": {"stroke": None}}}
    else:
        vconcat: list = []
        for rg in row_groups:
            subset = [r for r in table if str(r.get(row_field)) == rg]
            s = build_subplot(subset, rg)
            if s:
                vconcat.append(s)
        final_spec = {"vconcat": vconcat, "spacing": concat_spacing, "config": {"view": {"stroke": None}}}

    keys = list(spec.keys())
    for k in keys:
        del spec[k]
    spec.update(final_spec)


radar_chart_def = {
    "chart": "Radar Chart",
    "template": {
        "description": "Radar / Spider chart",
        "mark": "point",
        "encoding": {},
    },
    "channels": ["x", "y", "color", "column", "row"],
    "markCognitiveChannel": "position",
    "instantiate": _radar_instantiate,
    "properties": [
        {"key": "filled", "label": "Filled", "type": "binary", "defaultValue": True},
        {"key": "fillOpacity", "label": "Fill Opacity", "type": "continuous",
         "min": 0, "max": 0.5, "step": 0.05, "defaultValue": 0.15},
        {"key": "strokeWidth", "label": "Line Width", "type": "continuous",
         "min": 0.5, "max": 4, "step": 0.5, "defaultValue": 1.5},
    ],
}
