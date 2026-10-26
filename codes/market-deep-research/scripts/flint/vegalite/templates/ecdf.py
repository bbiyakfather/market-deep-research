"""ECDF Plot (Empirical Cumulative Distribution Function) template.

Plots each distinct value `x` of a quantitative measure against the proportion
of observations <= x. Port of vegalite/templates/ecdf.ts.
"""
from __future__ import annotations

from .utils import set_mark_prop


def _unique_name(base, taken):
    name = base
    while name in taken:
        name = "_" + name
    return name


def _ecdf_declare_layout(cs, table, chart_properties):
    return {
        "paramOverrides": {
            "continuousMarkCrossSection": {"x": 100, "y": 20, "seriesCountAxis": "auto"},
            "facetAspectRatioResistance": 0.5,
        },
    }


def _ecdf_instantiate(spec, ctx):
    encs = ctx["resolvedEncodings"]
    x = encs.get("x")
    color = encs.get("color")
    detail = encs.get("detail")
    column = encs.get("column")
    row = encs.get("row")
    measure = x.get("field") if x else None
    if not measure:
        return

    # Internal column names that must not clash with real data columns.
    taken = set()
    for r in (ctx.get("table") or []):
        for k in r.keys():
            taken.add(k)
    cnt_name = _unique_name("__ecdf_count", taken)
    total_name = _unique_name("__ecdf_total", taken)
    ecdf_name = _unique_name("__ecdf", taken)

    # Group running count + total by every grouping/facet field.
    groupby = []

    def push_group(f):
        if f and f != measure and f not in groupby:
            groupby.append(f)

    push_group(color.get("field") if color else None)
    push_group(detail.get("field") if detail else None)
    push_group(column.get("field") if column else None)
    push_group(row.get("field") if row else None)

    window_step = {
        "window": [{"op": "count", "field": measure, "as": cnt_name}],
        "sort": [{"field": measure, "order": "ascending"}],
        "frame": [None, 0],
    }
    join_step = {"joinaggregate": [{"op": "count", "field": measure, "as": total_name}]}
    if groupby:
        window_step["groupby"] = groupby
        join_step["groupby"] = groupby
    spec["transform"] = [
        window_step,
        join_step,
        {"calculate": "datum['{}'] / datum['{}']".format(cnt_name, total_name), "as": ecdf_name},
    ]

    # The measure on x, suppressing the engine's zero-baseline.
    spec["encoding"]["x"] = {
        **x,
        "type": "quantitative",
        "title": measure,
        "scale": {**((x.get("scale") if x else None) or {}), "zero": False},
    }
    # The cumulative proportion on y, pinned to [0, 1].
    spec["encoding"]["y"] = {
        "field": ecdf_name,
        "type": "quantitative",
        "scale": {"domain": [0, 1]},
        "title": "Cumulative proportion",
    }

    if color and color.get("field"):
        spec["encoding"]["color"] = {**color}
    if detail and detail.get("field"):
        spec["encoding"]["detail"] = {**detail}
    if column:
        spec["encoding"]["column"] = column
    if row:
        spec["encoding"]["row"] = row

    if (ctx.get("chartProperties") or {}).get("showPoints"):
        spec["mark"] = set_mark_prop(spec.get("mark"), "point", True)


ecdf_plot_def = {
    "chart": "ECDF Plot",
    "template": {
        "mark": {"type": "line", "interpolate": "step-after"},
        "transform": [],
        "encoding": {},
    },
    "channels": ["x", "color", "detail", "column", "row"],
    "markCognitiveChannel": "position",
    "declareLayoutMode": _ecdf_declare_layout,
    "instantiate": _ecdf_instantiate,
    "properties": [
        {"key": "showPoints", "label": "Show points", "type": "binary", "defaultValue": False},
    ],
}
