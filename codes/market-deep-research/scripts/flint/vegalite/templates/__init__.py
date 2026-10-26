"""Template registry — only includes templates needed for gallery fixtures."""
from __future__ import annotations

from .bar import (
    bar_chart_def, grouped_bar_chart_def, stacked_bar_chart_def,
    histogram_def, pyramid_chart_def, heatmap_def,
)
from .line import line_chart_def
from .area import area_chart_def, streamgraph_def
from .scatter import scatter_plot_def, regression_def, ranged_dot_plot_def, boxplot_def
from .connected_scatter import connected_scatter_def
from .gantt import gantt_chart_def
from .bullet import bullet_chart_def
from .ecdf import ecdf_plot_def
from .violin import violin_plot_def
from .slope import slope_chart_def
from .range_area import range_area_chart_def
from .map import map_def, choropleth_def
from .pie import pie_chart_def
from .radar import radar_chart_def
from .rose import rose_chart_def
from .kpi_card import kpi_card_def
from .bump import bump_chart_def
from .lollipop import lollipop_chart_def
from .density import density_plot_def
from .jitter import strip_plot_def
from .candlestick import candlestick_chart_def
from .waterfall import waterfall_chart_def
from .bar_table import bar_table_def


# ─── Cross-cutting injected properties ──────────────────────────────────────
# Mirror of src/lib/agents-chart/vegalite/templates/index.ts (`withInjectedProperties`).
#
# These property definitions are *not* declared per template; the registry
# attaches them based on a template's channels and `markCognitiveChannel`.
# Their `check(ctx)` callbacks run at assembly time to decide applicability
# and a recommendedValue.

def _facet_independent_y_check(ctx: dict) -> dict:
    encs = ctx.get("encodings") or {}
    cs = (ctx.get("channelSemantics") or {}).get("y") or {}
    applicable = (
        (bool((encs.get("column") or {}).get("field")) or bool((encs.get("row") or {}).get("field")))
        and cs.get("type") == "quantitative"
    )
    return {"applicable": applicable}


FACET_AXIS_PROPERTIES = [
    {
        "key": "independentYAxis", "label": "Independent Y", "type": "binary",
        "check": _facet_independent_y_check,
    },
]


def _make_log_scale_check(axis: str):
    def check(ctx: dict) -> dict:
        cs = (ctx.get("channelSemantics") or {}).get(axis) or {}
        if not cs.get("field") or cs.get("type") != "quantitative":
            return {"applicable": False}
        pos_min = float("inf")
        pos_max = float("-inf")
        pos_count = 0
        has_negative = False
        field = cs["field"]
        for row in (ctx.get("data") or []):
            v = row.get(field)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if v != v or v in (float("inf"), float("-inf")):
                continue
            if v < 0:
                has_negative = True
            elif v > 0:
                pos_count += 1
                if v < pos_min:
                    pos_min = v
                if v > pos_max:
                    pos_max = v
        # Offer only on non-negative data with enough positive spread (>= 3
        # orders of magnitude); log is undefined for negatives.
        offer_eligible = (
            not has_negative
            and pos_count >= 5
            and pos_min > 0
            and (pos_max / pos_min) >= 1000
        )
        choice = (ctx.get("chartProperties") or {}).get(f"logScale_{axis}")
        recommends_log = cs.get("scaleType") in ("log", "symlog")
        return {
            "applicable": offer_eligible or choice is True or choice is False,
            "recommendedValue": recommends_log,
        }
    return check


LOG_SCALE_PROPERTIES = [
    {
        "key": "logScale_x", "label": "Log X", "type": "binary", "defaultValue": False,
        "check": _make_log_scale_check("x"),
    },
    {
        "key": "logScale_y", "label": "Log Y", "type": "binary", "defaultValue": False,
        "check": _make_log_scale_check("y"),
    },
]


def _make_zero_baseline_check(axis: str):
    def check(ctx: dict) -> dict:
        cs = (ctx.get("channelSemantics") or {}).get(axis) or {}
        if not cs.get("field") or cs.get("type") != "quantitative":
            return {"applicable": False}
        decision = cs.get("zero")
        if not decision:
            return {"applicable": False}
        choice = (ctx.get("chartProperties") or {}).get(f"includeZero_{axis}")
        return {
            "applicable": bool(decision.get("uncertain")) or choice is True or choice is False,
            "recommendedValue": decision.get("zero"),
        }
    return check


ZERO_BASELINE_PROPERTIES = [
    {
        "key": "includeZero_x", "label": "Zero X", "type": "binary",
        "check": _make_zero_baseline_check("x"),
    },
    {
        "key": "includeZero_y", "label": "Zero Y", "type": "binary",
        "check": _make_zero_baseline_check("y"),
    },
]


AXIS_DTYPE_CHARTS = {"Bar Chart", "Line Chart", "Area Chart", "Lollipop Chart"}
AXIS_DTYPE_MAX_CATEGORIES = 50


def _make_axis_dtype_check(axis: str):
    def check(ctx: dict) -> dict:
        cs = (ctx.get("channelSemantics") or {}).get(axis) or {}
        if not cs.get("field"):
            return {"applicable": False}
        choice = (ctx.get("chartProperties") or {}).get(f"{axis}AxisType")
        if choice is not None:
            return {"applicable": True, "recommendedValue": "temporal"}
        if cs.get("type") != "temporal":
            return {"applicable": False}
        field = cs["field"]
        distinct = set()
        for r in (ctx.get("data") or []):
            v = r.get(field)
            if v is None or v == "":
                continue
            distinct.add(v)
            if len(distinct) > AXIS_DTYPE_MAX_CATEGORIES:
                break
        dual = 2 <= len(distinct) <= AXIS_DTYPE_MAX_CATEGORIES
        return {"applicable": dual, "recommendedValue": "temporal"}
    return check


AXIS_DTYPE_PROPERTIES = [
    {
        "key": "xAxisType", "label": "X as", "type": "discrete",
        "options": [
            {"value": "temporal", "label": "Temporal"},
            {"value": "nominal", "label": "Discrete"},
        ],
        "check": _make_axis_dtype_check("x"),
    },
    {
        "key": "yAxisType", "label": "Y as", "type": "discrete",
        "options": [
            {"value": "temporal", "label": "Temporal"},
            {"value": "nominal", "label": "Discrete"},
        ],
        "check": _make_axis_dtype_check("y"),
    },
]


def with_injected_properties(def_: dict) -> dict:
    """Attach cross-cutting injected properties to a template. Mirror of
    `withInjectedProperties` in index.ts. Idempotent w.r.t. ``key``: any
    property the template already declares with the same key wins."""
    channels = def_.get("channels") or []
    has_facet_channels = any(ch in ("column", "row") for ch in channels)
    is_position = def_.get("markCognitiveChannel") == "position"
    wants_axis_dtype = def_.get("chart") in AXIS_DTYPE_CHARTS

    extra = []
    if has_facet_channels:
        extra.extend(FACET_AXIS_PROPERTIES)
    if is_position:
        extra.extend(LOG_SCALE_PROPERTIES)
        extra.extend(ZERO_BASELINE_PROPERTIES)
    if wants_axis_dtype:
        extra.extend(AXIS_DTYPE_PROPERTIES)
    if not extra:
        return def_
    own_keys = {p.get("key") for p in (def_.get("properties") or [])}
    merged = list(def_.get("properties") or []) + [p for p in extra if p.get("key") not in own_keys]
    return {**def_, "properties": merged}


vl_template_defs = {
    "Points": [scatter_plot_def, regression_def, connected_scatter_def, ranged_dot_plot_def, strip_plot_def],
    "Bars": [bar_chart_def, grouped_bar_chart_def, stacked_bar_chart_def, lollipop_chart_def,
             waterfall_chart_def, gantt_chart_def, bullet_chart_def],
    "Distributions": [histogram_def, density_plot_def, ecdf_plot_def, violin_plot_def,
                      boxplot_def, pyramid_chart_def, candlestick_chart_def],
    "Lines & Areas": [line_chart_def, bump_chart_def, slope_chart_def, area_chart_def,
                      streamgraph_def, range_area_chart_def],
    "Circular": [pie_chart_def, rose_chart_def, radar_chart_def],
    "Tables & Maps": [heatmap_def, bar_table_def, kpi_card_def, map_def, choropleth_def],
}

# Apply withInjectedProperties to every template once at module import so the
# `properties` key on every emitted ChartTemplateDef carries the cross-cutting
# axis controls (matching the JS catalog).
vl_template_defs = {
    category: [with_injected_properties(d) for d in defs]
    for category, defs in vl_template_defs.items()
}


vl_all_template_defs = []
for _group in vl_template_defs.values():
    vl_all_template_defs.extend(_group)


def vl_get_template_def(chart_type: str):
    for t in vl_all_template_defs:
        if t["chart"] == chart_type:
            return t
    return None


def vl_get_template_channels(chart_type: str):
    t = vl_get_template_def(chart_type)
    return t["channels"] if t else []
