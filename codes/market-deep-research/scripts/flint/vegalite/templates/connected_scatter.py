"""Connected Scatter Plot template.

Points are plotted in 2-D (x, y both quantitative) and connected by a straight
line in a defined order (usually time / sequence), tracing a trajectory through
the space. Port of vegalite/templates/connected-scatter.ts.
"""
from __future__ import annotations

from .utils import default_build_encodings


def _resolve_order_type(cs_type, field, table):
    """Pick a sortable VL type for the order encoding (mirrors JS)."""
    values = [r.get(field) for r in table if r.get(field) not in (None, "")]

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

    all_numeric = len(values) > 0 and all(_is_num(v) for v in values)
    # Numeric sequence fields (years, step indices, …) sort numerically — even
    # when the resolver classified them as temporal/ordinal.
    if all_numeric:
        return "quantitative"
    if cs_type == "temporal":
        return "temporal"
    return cs_type if cs_type in ("ordinal", "nominal") else "nominal"


def _connected_scatter_instantiate(spec, ctx):
    default_build_encodings(spec, ctx["resolvedEncodings"])

    encoding = spec.get("encoding") or {}
    x_enc = encoding.get("x")
    y_enc = encoding.get("y")
    if not x_enc or not y_enc:
        return

    # The connecting line must follow the sequence field, NOT the x value.
    order_cs = (ctx.get("channelSemantics") or {}).get("order") or {}
    if order_cs.get("field"):
        spec["encoding"]["order"] = {
            "field": order_cs["field"],
            "type": _resolve_order_type(order_cs.get("type"), order_cs["field"], ctx["table"]),
        }
    else:
        spec["encoding"].pop("order", None)

    # Both position axes fit the data; a few px of padding keeps extreme points
    # (and markers) clear of the plot edges.
    x_enc["scale"] = {**(x_enc.get("scale") or {}), "nice": True, "padding": 10}
    y_enc["scale"] = {**(y_enc.get("scale") or {}), "nice": True, "padding": 10}


connected_scatter_def = {
    "chart": "Connected Scatter Plot",
    "template": {
        "mark": {"type": "line", "point": True, "interpolate": "linear", "strokeWidth": 2},
        "encoding": {},
    },
    "channels": ["x", "y", "order", "color", "detail", "column", "row"],
    "markCognitiveChannel": "position",
    "instantiate": _connected_scatter_instantiate,
}
