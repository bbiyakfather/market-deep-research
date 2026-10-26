"""Bump Chart template."""
from __future__ import annotations

from .utils import default_build_encodings


RANK_SEMANTIC_TYPES = {"Rank", "Score", "Level"}


def _is_discrete(t):
    return t == "nominal" or t == "ordinal"


def _bump_declare(cs, table, chart_properties):
    return {
        "paramOverrides": {
            "continuousMarkCrossSection": {"x": 80, "y": 20, "seriesCountAxis": "auto"},
            "facetAspectRatioResistance": 0.4,
        },
    }


def _bump_instantiate(spec, ctx):
    default_build_encodings(spec, ctx["resolvedEncodings"])
    encoding = spec.get("encoding") or {}
    x_enc = encoding.get("x")
    y_enc = encoding.get("y")
    if not x_enc or not y_enc:
        return

    semantic_types = ctx.get("semanticTypes") or {}

    x_sem = semantic_types.get(x_enc.get("field")) if x_enc.get("field") else None
    y_sem = semantic_types.get(y_enc.get("field")) if y_enc.get("field") else None
    x_is_rank = x_sem in RANK_SEMANTIC_TYPES
    y_is_rank = y_sem in RANK_SEMANTIC_TYPES

    if y_is_rank and not x_is_rank:
        rank_axis = "y"
    elif x_is_rank and not y_is_rank:
        rank_axis = "x"
    elif _is_discrete(x_enc.get("type")) and not _is_discrete(y_enc.get("type")):
        rank_axis = "y"
    elif _is_discrete(y_enc.get("type")) and not _is_discrete(x_enc.get("type")):
        rank_axis = "x"
    else:
        rank_axis = "y"

    if rank_axis == "y":
        existing_scale = y_enc.get("scale") or {}
        y_enc["scale"] = {**existing_scale, "reverse": True}

    if rank_axis == "x" and y_enc.get("field"):
        spec["encoding"]["order"] = {
            "field": y_enc["field"],
            "type": y_enc.get("type") or "quantitative",
        }


bump_chart_def = {
    "chart": "Bump Chart",
    "template": {
        "mark": {"type": "line", "point": True, "interpolate": "monotone", "strokeWidth": 2},
        "encoding": {},
    },
    "channels": ["x", "y", "color", "detail", "column", "row"],
    "markCognitiveChannel": "position",
    "declareLayoutMode": _bump_declare,
    "instantiate": _bump_instantiate,
}
