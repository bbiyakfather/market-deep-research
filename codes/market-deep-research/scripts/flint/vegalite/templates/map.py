"""Map (bubble) and Choropleth templates.

Port of vegalite/templates/map.ts. Both templates choose their geography (US vs
World base TopoJSON, projection, frame size) from the ``region`` property,
defaulting to auto-inference from the data. TopoJSON is referenced by URL.
"""
from __future__ import annotations

import math

from ...core.field_semantics import to_type_string
from .geo_lookup import resolve_country, resolve_us_state

_MAP_PROJECTIONS = [
    {"value": "mercator", "label": "Mercator"},
    {"value": "equalEarth", "label": "Equal Earth"},
    {"value": "orthographic", "label": "Orthographic (Globe)"},
    {"value": "stereographic", "label": "Stereographic"},
    {"value": "conicEqualArea", "label": "Conic Equal Area"},
    {"value": "conicEquidistant", "label": "Conic Equidistant"},
    {"value": "azimuthalEquidistant", "label": "Azimuthal Equidistant"},
    {"value": "mollweide", "label": "Mollweide"},
]

_PROJECTION_CENTER_PRESETS = [
    {"label": "World (Atlantic)", "center": [0, 0]},
    {"label": "World (Pacific)", "center": [150, 0]},
    {"label": "China", "center": [105, 35]},
    {"label": "USA", "center": [-98, 39]},
    {"label": "Europe", "center": [10, 50]},
    {"label": "Japan", "center": [138, 36]},
    {"label": "India", "center": [78, 22]},
    {"label": "Brazil", "center": [-52, -14]},
    {"label": "Australia", "center": [134, -25]},
    {"label": "Russia", "center": [100, 60]},
    {"label": "Africa", "center": [20, 0]},
    {"label": "Middle East", "center": [45, 28]},
    {"label": "Southeast Asia", "center": [115, 5]},
    {"label": "South America", "center": [-60, -15]},
    {"label": "North America", "center": [-100, 45]},
    {"label": "UK", "center": [-2, 54]},
    {"label": "Germany", "center": [10, 51]},
    {"label": "France", "center": [2, 47]},
    {"label": "Korea", "center": [128, 36]},
]

_SCOPE_GEO = {
    "us": {
        "url": "https://vega.github.io/vega-lite/data/us-10m.json",
        "feature": "states",
        "projection": "albersUsa",
        "width": 500,
        "height": 300,
        "strokeWidth": 0.5,
    },
    "world": {
        "url": "https://vega.github.io/vega-lite/data/world-110m.json",
        "feature": "countries",
        "projection": "equalEarth",
        "width": 600,
        "height": 350,
        "strokeWidth": 0.4,
    },
}

_US_LON = (-170, -66)
_US_LAT = (18, 72)


def _to_number(v):
    if isinstance(v, bool):
        return float("nan")
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return float("nan")


def _in_us_box(lon, lat):
    return _US_LON[0] <= lon <= _US_LON[1] and _US_LAT[0] <= lat <= _US_LAT[1]


def _infer_bubble_scope(rows, lon_field, lat_field):
    if not lon_field or not lat_field:
        return "us"
    for r in rows:
        lon = _to_number(r.get(lon_field))
        lat = _to_number(r.get(lat_field))
        if not math.isfinite(lon) or not math.isfinite(lat):
            continue
        if not _in_us_box(lon, lat):
            return "world"
    return "us"


def _infer_choropleth_scope(rows, id_field):
    if not id_field:
        return "us"
    for r in rows:
        v = r.get(id_field)
        if v is None or v == "":
            continue
        if resolve_us_state(v) is None:
            return "world"
    return "us"


_SEMANTIC_SCOPE = {"State": "us", "Country": "world"}


def _semantic_scope(sem_type):
    if not sem_type:
        return None
    return _SEMANTIC_SCOPE.get(sem_type) if sem_type in _SEMANTIC_SCOPE else None


def _pick_scope(chart_properties, sem_scope, infer):
    choice = (chart_properties or {}).get("region")
    if choice in ("us", "world"):
        return choice
    if sem_scope:
        return sem_scope
    return infer()


def _would_be_world(ctx):
    choice = (ctx.get("chartProperties") or {}).get("region")
    if choice == "us":
        return False
    if choice == "world":
        return True
    rows = ctx.get("data") or []
    encs = ctx.get("encodings") or {}
    lon_field = (encs.get("longitude") or {}).get("field")
    lat_field = (encs.get("latitude") or {}).get("field")
    return _infer_bubble_scope(rows, lon_field, lat_field) == "world"


_REGION_PROPERTY = {
    "key": "region",
    "label": "Region",
    "type": "discrete",
    "options": [
        {"value": "auto", "label": "Auto-detect"},
        {"value": "us", "label": "United States"},
        {"value": "world", "label": "World"},
    ],
    "defaultValue": "auto",
}


def _apply_point_encodings(layer, resolved):
    if not layer.get("encoding"):
        layer["encoding"] = {}
    for ch, enc in resolved.items():
        layer["encoding"][ch] = {**(layer["encoding"].get(ch) or {}), **enc}
    for ch in list(layer["encoding"].keys()):
        enc = layer["encoding"][ch]
        if isinstance(enc, dict) and len(enc.keys()) == 0:
            del layer["encoding"][ch]


def _configure_bubble(spec, scope):
    g = _SCOPE_GEO[scope]
    spec["width"] = g["width"]
    spec["height"] = g["height"]
    spec["layer"][0]["data"] = {"url": g["url"], "format": {"type": "topojson", "feature": g["feature"]}}
    spec["layer"][0]["projection"] = {"type": g["projection"]}
    spec["layer"][1]["projection"] = {"type": g["projection"]}


def _configure_choropleth(spec, scope):
    g = _SCOPE_GEO[scope]
    spec["width"] = g["width"]
    spec["height"] = g["height"]
    spec["data"] = {"url": g["url"], "format": {"type": "topojson", "feature": g["feature"]}}
    spec["projection"] = {"type": g["projection"]}
    if isinstance(spec.get("mark"), dict):
        spec["mark"]["strokeWidth"] = g["strokeWidth"]


def _map_instantiate(spec, ctx):
    rows = ctx.get("fullTable") or ctx.get("table") or []
    lon_field = (ctx["resolvedEncodings"].get("longitude") or {}).get("field")
    lat_field = (ctx["resolvedEncodings"].get("latitude") or {}).get("field")
    scope = _pick_scope(ctx.get("chartProperties"), None,
                        lambda: _infer_bubble_scope(rows, lon_field, lat_field))

    _configure_bubble(spec, scope)
    _apply_point_encodings(spec["layer"][1], ctx["resolvedEncodings"])

    # Projection controls only apply to the world map; the US map is fixed to
    # albersUsa (which insets Alaska + Hawaii).
    if scope == "world":
        config = ctx.get("chartProperties")
        if config:
            projection = config.get("projection")
            projection_center = config.get("projectionCenter")

            def apply_projection(obj):
                if obj.get("projection"):
                    if projection and projection != "default":
                        obj["projection"]["type"] = projection
                    if projection_center and obj["projection"].get("type") != "albersUsa":
                        obj["projection"]["rotate"] = [-projection_center[0], -projection_center[1], 0]

            for layer in spec["layer"]:
                apply_projection(layer)


map_def = {
    "chart": "Map",
    "template": {
        "layer": [
            {"mark": {"type": "geoshape", "fill": "lightgray", "stroke": "white"}},
            {
                "mark": "circle",
                "encoding": {"longitude": {}, "latitude": {}, "size": {}, "color": {}, "opacity": {}},
            },
        ],
    },
    "channels": ["longitude", "latitude", "color", "size", "opacity"],
    "markCognitiveChannel": "position",
    "instantiate": _map_instantiate,
    "properties": [
        _REGION_PROPERTY,
        {
            "key": "projection",
            "label": "Projection",
            "type": "discrete",
            "options": [{"value": "default", "label": "Default"}]
            + [{"value": p["value"], "label": p["label"]} for p in _MAP_PROJECTIONS],
            "defaultValue": "default",
            "check": lambda ctx: {"applicable": _would_be_world(ctx)},
        },
        {
            "key": "projectionCenter",
            "label": "Center",
            "type": "discrete",
            "options": [{"value": None, "label": "Default"}]
            + [{"value": p["center"], "label": "{} [{}, {}]".format(p["label"], p["center"][0], p["center"][1])}
               for p in _PROJECTION_CENTER_PRESETS],
            "defaultValue": None,
            "check": lambda ctx: {"applicable": _would_be_world(ctx)},
        },
    ],
}


def _build_choropleth_join(spec, ctx, resolver):
    id_field = (ctx["resolvedEncodings"].get("id") or {}).get("field")
    color_enc = ctx["resolvedEncodings"].get("color")
    value_field = color_enc.get("field") if color_enc else None
    detail_enc = ctx["resolvedEncodings"].get("detail")
    label_field = (detail_enc.get("field") if detail_enc else None) or id_field

    rows = ctx.get("fullTable") or ctx.get("table") or []

    if id_field:
        joined = []
        for r in rows:
            geo = resolver(r.get(id_field))
            row = {**r, "__geo_id": geo}
            if geo is None:
                # JS sets `__geo_id: undefined`, which JSON.stringify drops.
                del row["__geo_id"]
            joined.append(row)
        lookup_fields = [f for f in (value_field, label_field) if f]
        spec["transform"] = [
            {"lookup": "id", "from": {"data": {"values": joined}, "key": "__geo_id", "fields": lookup_fields}},
        ]

    spec["encoding"] = {}
    if color_enc:
        spec["encoding"]["color"] = {**color_enc}

    tooltip = []
    if label_field:
        tooltip.append({"field": label_field, "type": "nominal"})
    if value_field:
        tooltip.append({"field": value_field, "type": (color_enc.get("type") if color_enc else None) or "quantitative"})
    if tooltip:
        spec["encoding"]["tooltip"] = tooltip


def _choropleth_instantiate(spec, ctx):
    rows = ctx.get("fullTable") or ctx.get("table") or []
    id_field = (ctx["resolvedEncodings"].get("id") or {}).get("field")
    sem_type = to_type_string((ctx.get("semanticTypes") or {}).get(id_field)) if id_field else ""
    sem_scope = _semantic_scope(sem_type)
    scope = _pick_scope(ctx.get("chartProperties"), sem_scope,
                        lambda: _infer_choropleth_scope(rows, id_field))

    _configure_choropleth(spec, scope)
    resolver = resolve_us_state if scope == "us" else resolve_country
    _build_choropleth_join(spec, ctx, resolver)


choropleth_def = {
    "chart": "Choropleth",
    "template": {
        "mark": {"type": "geoshape", "stroke": "white", "strokeWidth": 0.5},
        "encoding": {},
    },
    "channels": ["id", "color", "detail"],
    "markCognitiveChannel": "color",
    "instantiate": _choropleth_instantiate,
    "properties": [_REGION_PROPERTY],
}
