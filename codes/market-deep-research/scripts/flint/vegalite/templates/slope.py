"""Slope Chart (slopegraph) template.

One straight line per category connecting that category's value at exactly two
periods, with a point marker at each end. Port of vegalite/templates/slope.ts.
"""
from __future__ import annotations

from ...core.js_date import js_date_parse_ms
from .utils import default_build_encodings, resolve_discrete_type


def _is_discrete(type_):
    return type_ == "nominal" or type_ == "ordinal"


def _ordered_distinct(table, field):
    """Distinct values of `field` ordered naturally (numeric, then date, else
    data-encounter order)."""
    seen = {}
    for row in table:
        v = row.get(field)
        if v is None:
            continue
        key = str(v)
        if key not in seen:
            seen[key] = v
    values = list(seen.values())
    if len(values) <= 1:
        return values

    def _is_num(v):
        if isinstance(v, bool):
            return False
        if isinstance(v, (int, float)):
            return True
        if isinstance(v, str) and v.strip() != "":
            try:
                float(v)
                return True
            except ValueError:
                return False
        return False

    if all(_is_num(v) for v in values):
        return sorted(values, key=lambda v: float(v))
    if all(js_date_parse_ms(str(v)) is not None for v in values):
        return sorted(values, key=lambda v: js_date_parse_ms(str(v)))
    return values


def _slope_declare_layout(cs, table, chart_properties):
    resolved_types = {}
    xcs = cs.get("x") or {}
    if xcs.get("field") and not _is_discrete(xcs.get("type")):
        resolved_types["x"] = resolve_discrete_type(xcs.get("type"), xcs["field"], table)
    result = {
        "axisFlags": {"x": {"banded": True}},
        "paramOverrides": {
            "defaultBandSize": 120,
            "continuousMarkCrossSection": {"x": 0, "y": 0, "seriesCountAxis": "auto"},
            "facetAspectRatioResistance": 0.4,
        },
    }
    if resolved_types:
        result["resolvedTypes"] = resolved_types
    return result


def _slope_instantiate(spec, ctx):
    default_build_encodings(spec, ctx["resolvedEncodings"])

    encoding = spec.get("encoding") or {}
    x_enc = encoding.get("x")
    y_enc = encoding.get("y")
    if not x_enc or not y_enc:
        return

    # Defensive: the period axis must be discrete.
    if not _is_discrete(x_enc.get("type")):
        x_enc["type"] = resolve_discrete_type(x_enc.get("type"), x_enc.get("field"), ctx["table"])

    # Order the two period bands with an explicit natural order.
    if x_enc.get("type") in ("ordinal", "nominal") and x_enc.get("sort") is None and x_enc.get("field"):
        order = _ordered_distinct(ctx["table"], x_enc["field"])
        if len(order) > 1:
            x_enc["sort"] = order

    # Inset the two period bands from the plot edges.
    x_enc["scale"] = {**(x_enc.get("scale") or {}), "padding": 0.4}

    # The value axis fits the data (read the slope, not the absolute level).
    y_enc["scale"] = {**(y_enc.get("scale") or {}), "zero": False, "nice": True, "padding": 12}


slope_chart_def = {
    "chart": "Slope Chart",
    "template": {
        "mark": {"type": "line", "point": True, "interpolate": "linear", "strokeWidth": 2},
        "encoding": {},
    },
    "channels": ["x", "y", "color", "detail", "column", "row"],
    "markCognitiveChannel": "position",
    "declareLayoutMode": _slope_declare_layout,
    "instantiate": _slope_instantiate,
}
