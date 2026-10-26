"""Gantt Chart template — one horizontal bar per task, spanning [start, end].

Port of vegalite/templates/gantt.ts.
"""
from __future__ import annotations


def _gantt_declare_layout(cs, table, chart_properties):
    return {"axisFlags": {"y": {"banded": True}}}


def _gantt_instantiate(spec, ctx):
    encs = ctx["resolvedEncodings"]
    x = encs.get("x")
    x2 = encs.get("x2")
    y = encs.get("y")
    color = encs.get("color")
    detail = encs.get("detail")
    column = encs.get("column")
    row = encs.get("row")

    if "encoding" not in spec:
        spec["encoding"] = {}

    if y:
        spec["encoding"]["y"] = {**y}
        spec["encoding"]["y"]["axis"] = {**(spec["encoding"]["y"].get("axis") or {}), "title": None}
        # Order tasks by when they start so the timeline reads chronologically.
        if x and x.get("field"):
            spec["encoding"]["y"]["sort"] = {"field": x["field"], "op": "min", "order": "ascending"}

    if x:
        spec["encoding"]["x"] = {**x}
        spec["encoding"]["x"]["axis"] = {**(spec["encoding"]["x"].get("axis") or {}), "title": None}
        # A non-zero baseline only matters for a quantitative interval; on a time
        # scale Vega-Lite ignores (and warns about) scale.zero.
        if x.get("type") == "quantitative":
            spec["encoding"]["x"]["scale"] = {**(spec["encoding"]["x"].get("scale") or {}), "zero": False}

    # x2 shares x's scale; it only needs the field reference.
    if x2:
        spec["encoding"]["x2"] = {"field": x2["field"]} if x2.get("field") is not None else {}

    if color:
        spec["encoding"]["color"] = color
    if detail:
        spec["encoding"]["detail"] = detail
    if column:
        spec["encoding"]["column"] = column
    if row:
        spec["encoding"]["row"] = row


gantt_chart_def = {
    "chart": "Gantt Chart",
    "template": {
        "mark": {"type": "bar", "cornerRadius": 2, "height": {"band": 0.7}},
        "encoding": {},
    },
    "channels": ["y", "x", "x2", "color", "detail", "column", "row"],
    "markCognitiveChannel": "position",
    "declareLayoutMode": _gantt_declare_layout,
    "instantiate": _gantt_instantiate,
}
