"""Bullet Chart template — a compact KPI panel.

One row per label, each showing a measure bar compared against its own target,
set against muted gray range bands. Port of vegalite/templates/bullet.ts.
"""
from __future__ import annotations

import json

from ...core import js_round

# Muted grays for the qualitative zones, darkest nearest zero (poorest range).
ZONE_GRAYS = ["#e2e2e2", "#ececec", "#f5f5f5"]
# Goal-attainment colors: muted red for under target, muted green for met target.
STATUS_COLORS = {"below": "#c44e52", "met": "#2f855a"}
STATUS_BELOW = "Below target"
STATUS_MET = "Meets target"


def _is_finite_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))


def _bullet_declare_layout(cs, table, chart_properties):
    return {"axisFlags": {"y": {"banded": True}}}


def _bullet_instantiate(spec, ctx):
    encs = ctx["resolvedEncodings"]
    x = encs.get("x")
    y = encs.get("y")
    goal = encs.get("goal")
    color = encs.get("color")
    column = encs.get("column")
    row = encs.get("row")

    value_title = (x.get("title") if x.get("title") is not None else x.get("field")) if x else None
    x_axis = {"title": value_title} if value_title is not None else {}

    # Shared category axis at the top level so every layer aligns by row.
    spec["encoding"] = {}
    if y:
        spec["encoding"]["y"] = {**y, "axis": {**(y.get("axis") or {}), "title": None}}
    if column:
        spec["encoding"]["column"] = column
    if row:
        spec["encoding"]["row"] = row

    table = ctx.get("table") or []
    layers = []

    # --- Per-row gray qualitative bands (drawn first, behind everything) ---
    if x and x.get("field") and y and y.get("field") and goal and goal.get("field") and len(table) > 0:
        y_field = y["field"]
        goal_field = goal["field"]
        zone_data = [[], [], []]
        for r in table:
            cat = r.get(y_field)
            g = r.get(goal_field)
            try:
                g = float(g)
            except (TypeError, ValueError):
                continue
            if cat is None or not _is_finite_number(g) or g <= 0:
                continue
            zone_data[0].append({y_field: cat, "__lo": 0, "__hi": 0.25 * g})
            zone_data[1].append({y_field: cat, "__lo": 0.25 * g, "__hi": 0.5 * g})
            zone_data[2].append({y_field: cat, "__lo": 0.5 * g, "__hi": 0.75 * g})
        for i, rows in enumerate(zone_data):
            if len(rows) == 0:
                continue
            layers.append({
                "data": {"values": rows},
                "mark": {"type": "rect", "color": ZONE_GRAYS[i], "opacity": 1},
                "encoding": {
                    "x": {"field": "__lo", "type": "quantitative", "axis": x_axis},
                    "x2": {"field": "__hi"},
                },
            })

    # --- Value bar — length from zero, colored by goal attainment ---
    bar_layer = {"mark": {"type": "bar", "height": {"band": 0.5}}, "encoding": {}}
    if x:
        bar_layer["encoding"]["x"] = {
            **x,
            "scale": {**(x.get("scale") or {}), "zero": True},
            "axis": {**(x.get("axis") or {}), "title": value_title},
        }
    if color:
        # Explicit grouping wins over goal-attainment coloring.
        bar_layer["encoding"]["color"] = color
    elif x and x.get("field") and goal and goal.get("field"):
        bar_layer["transform"] = [{
            "calculate": "datum[{}] >= datum[{}] ? '{}' : '{}'".format(
                json.dumps(x["field"]), json.dumps(goal["field"]), STATUS_MET, STATUS_BELOW),
            "as": "__status",
        }]
        bar_layer["encoding"]["color"] = {
            "field": "__status",
            "type": "nominal",
            "scale": {
                "domain": [STATUS_BELOW, STATUS_MET],
                "range": [STATUS_COLORS["below"], STATUS_COLORS["met"]],
            },
            "legend": {"title": None},
            "title": None,
        }
    layers.append(bar_layer)

    # --- Target marker — a dark tick at the goal, sized to the row band ---
    if goal:
        band = (ctx.get("layout") or {}).get("yStep")
        if band and band > 0:
            tick_size = min(band, max(8, js_round(band * 0.72)))
        else:
            tick_size = 22
        layers.append({
            "mark": {"type": "tick", "color": "#1a1a1a", "thickness": 3, "opacity": 1, "size": tick_size},
            "encoding": {
                "x": {"field": goal["field"], "type": "quantitative", "axis": x_axis},
            },
        })

    spec["layer"] = layers


bullet_chart_def = {
    "chart": "Bullet Chart",
    "template": {"encoding": {}, "layer": []},
    "channels": ["y", "x", "goal", "color", "column", "row"],
    "markCognitiveChannel": "length",
    "declareLayoutMode": _bullet_declare_layout,
    "instantiate": _bullet_instantiate,
}
