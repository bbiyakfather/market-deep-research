"""KPI Card template — "big number" dashboard tile."""
from __future__ import annotations

import math
from typing import Any, Optional
from ...core import js_round


PROGRESS_TRACK = "#e6e9ef"
PROGRESS_ON_TRACK = "#5b8def"
PROGRESS_EXCEEDED = "#22a06b"
PROGRESS_BEHIND = "#e07a3c"

CARD_FILL = "#ffffff"
CARD_STROKE = "#e6e9ef"
CARD_RADIUS = 8


def _to_locale_int(v: int) -> str:
    return "{:,}".format(v)


def _to_locale_float_2dp(v: float) -> str:
    """Emulate JS Number.toLocaleString(undefined, {maximumFractionDigits: 2}).
    JS strips trailing zeros after the decimal."""
    s = "{:,.2f}".format(v)
    # strip trailing zeros and lone dot
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _render_scalar(v: Any) -> str:
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)) and math.isfinite(v):
        x = v
        if abs(x) < 1e-9:
            x = 0
        # Number.isInteger
        if isinstance(x, int) or (isinstance(x, float) and x.is_integer()):
            return _to_locale_int(int(x))
        return _to_locale_float_2dp(float(x))
    if v is None:
        return "null"
    return str(v)


def _clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def _kpi_instantiate(spec, ctx):
    re_enc = ctx["resolvedEncodings"]
    metric = re_enc.get("metric")
    value = re_enc.get("value")
    goal = re_enc.get("goal")
    config = ctx.get("chartProperties") or {}

    metric_field = metric.get("field") if metric else None
    value_field = value.get("field") if value else None
    goal_field = goal.get("field") if goal else None

    # behind threshold
    try:
        raw_behind = float(config.get("behindThreshold"))
        if math.isfinite(raw_behind):
            behind_threshold = min(1, max(0, raw_behind))
        else:
            behind_threshold = 0.5
    except (TypeError, ValueError):
        behind_threshold = 0.5

    source_table = ctx.get("fullTable") or ctx.get("table") or []

    # ── Collect tiles ──
    tiles: list = []
    if value_field:
        for row in source_table:
            if not row:
                continue
            raw_value = row.get(value_field)
            if raw_value is None:
                continue
            if metric_field:
                mv = row.get(metric_field)
                caption = str(mv) if mv is not None else ""
            else:
                caption = value_field
            raw_goal = row.get(goal_field) if goal_field else None
            value_text = _render_scalar(raw_value)
            goal_text = _render_scalar(raw_goal) if raw_goal is not None else None
            progress = None
            if (
                isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool) and math.isfinite(float(raw_value))
                and isinstance(raw_goal, (int, float)) and not isinstance(raw_goal, bool) and math.isfinite(float(raw_goal))
                and raw_goal != 0
            ):
                progress = {
                    "fraction": float(raw_value) / float(raw_goal),
                    "valueNum": float(raw_value),
                    "goalNum": float(raw_goal),
                }
            tile = {"caption": caption, "valueText": value_text, "goalText": goal_text, "progress": progress}
            tiles.append(tile)

    if len(tiles) == 0:
        tiles.append({"caption": "Value", "valueText": "—", "goalText": None, "progress": None})

    # ── Layout ──
    base_w = ctx["canvasSize"]["width"]
    n = len(tiles)
    requested_layout = config.get("layout") or "auto"
    layout = requested_layout if requested_layout in ("horizontal", "vertical", "grid") else "grid"

    if layout == "horizontal":
        cols, rows = n, 1
    elif layout == "vertical":
        cols, rows = 1, n
    else:
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)

    spacing = 4
    MAX_STRETCH = 1.6
    TARGET_ASPECT = 1.4
    TARGET_TILE_W = 220
    MIN_TILE_W = 130
    MIN_TILE_H = js_round(MIN_TILE_W / TARGET_ASPECT)  # 93

    wish_w = cols * TARGET_TILE_W + (cols - 1) * spacing
    budget_w = base_w * MAX_STRETCH
    min_required_w = cols * MIN_TILE_W + (cols - 1) * spacing

    W = max(min_required_w, min(budget_w, max(base_w, wish_w)))

    tile_w = max(MIN_TILE_W, math.floor((W - spacing * (cols - 1)) / cols))
    tile_h = max(MIN_TILE_H, js_round(tile_w / TARGET_ASPECT))
    H = rows * tile_h + (rows - 1) * spacing

    card_left_inset = max(0.5, math.floor(tile_w * 0.04))
    card_inner_pad_x = max(8, math.floor(tile_w * 0.06))
    card_inner_w = max(20, tile_w - 2 * card_left_inset - 2 * card_inner_pad_x)

    CHAR_W_BOLD = 0.66
    CHAR_W_REGULAR = 0.58

    max_value_chars = max((len(t["valueText"]) for t in tiles), default=1) or 1
    max_caption_chars = max((len(t["caption"]) for t in tiles), default=1) or 1

    def _sub_chars(t):
        if t.get("progress"):
            pct = js_round(t["progress"]["fraction"] * 100)
            text = f"{pct}% of {t.get('goalText') or ''}"
            return len(text)
        if t.get("goalText") is not None:
            return len(f"Goal: {t['goalText']}")
        return 1

    max_sub_chars = max((_sub_chars(t) for t in tiles), default=1) or 1

    def font_fits_width(chars: int, char_w: float) -> int:
        return math.floor(card_inner_w / max(1, chars * char_w))

    value_font_by_width = font_fits_width(max_value_chars, CHAR_W_BOLD)
    caption_font_by_width = font_fits_width(max_caption_chars, CHAR_W_REGULAR)
    sub_font_by_width = font_fits_width(max_sub_chars, CHAR_W_REGULAR)

    has_sub_line = any(t.get("progress") or t.get("goalText") is not None for t in tiles)
    has_progress = any(t.get("progress") for t in tiles)

    value_h_cap = tile_h / 2.6 if has_sub_line else tile_h / 2.1
    value_font = min(80, max(10, math.floor(min(tile_w / 5.0, value_h_cap, value_font_by_width))))
    caption_font = max(11, min(22, math.floor(min(value_font / 3.0, caption_font_by_width))))
    sub_font = max(10, min(18, math.floor(min(caption_font, sub_font_by_width))))

    pad_top = max(4, math.floor(caption_font * 0.55))
    pad_bot = max(4, math.floor(sub_font * 0.6))
    gap_cv = max(6, math.floor(caption_font * 0.55))
    gap_vs = max(8, math.floor(sub_font * 1.0))
    gap_sb = max(4, math.floor(sub_font * 0.55))
    bar_height = max(2, math.floor(sub_font * 0.4))

    caption_top = pad_top
    caption_bot = caption_top + caption_font
    value_top = caption_bot + gap_cv
    value_mid = value_top + math.floor(value_font / 2)
    value_bot = value_top + value_font
    sub_top = value_bot + gap_vs
    sub_bot = sub_top + sub_font
    bar_top = sub_bot + gap_sb
    bar_bot = bar_top + bar_height

    content_bot = bar_bot if has_progress else (sub_bot if has_sub_line else value_bot)
    slack = max(0, tile_h - (content_bot + pad_bot))
    y_offset = math.floor(slack / 2)

    caption_y = caption_top + y_offset
    value_y = value_mid + y_offset
    sub_y = sub_top + y_offset
    bar_y = bar_top + y_offset

    bar_pad = max(4, math.floor(tile_w * 0.1))
    bar_left = bar_pad
    bar_right = tile_w - bar_pad
    bar_width = max(12, bar_right - bar_left)

    card_outer_pad_y = max(4, math.floor(tile_h * 0.06))
    card_left = card_left_inset
    card_right = tile_w - card_left_inset
    card_top = max(0.5, card_outer_pad_y)
    card_bot = min(tile_h - 0.5, tile_h - card_outer_pad_y)

    show_card_frame = config.get("style") is not False

    def build_tile(t):
        layers: list = []
        if show_card_frame:
            layers.append({
                "data": {"values": [{}]},
                "mark": {
                    "type": "rect",
                    "fill": CARD_FILL,
                    "stroke": CARD_STROKE,
                    "strokeWidth": 1,
                    "cornerRadius": CARD_RADIUS,
                    "tooltip": None,
                },
                "encoding": {
                    "x": {"value": card_left},
                    "x2": {"value": card_right},
                    "y": {"value": card_top},
                    "y2": {"value": card_bot},
                },
            })

        layers.append({
            "data": {"values": [{}]},
            "mark": {
                "type": "text",
                "fontSize": caption_font,
                "fontWeight": 500,
                "fill": "#4a4a4a",
                "align": "center",
                "baseline": "top",
                "text": t["caption"],
                "tooltip": None,
            },
            "encoding": {
                "x": {"value": tile_w / 2},
                "y": {"value": caption_y},
            },
        })

        layers.append({
            "data": {"values": [{}]},
            "mark": {
                "type": "text",
                "fontSize": value_font,
                "fontWeight": "bold",
                "fill": "#1a1a1a",
                "align": "center",
                "baseline": "middle",
                "text": t["valueText"],
                "tooltip": None,
            },
            "encoding": {
                "x": {"value": tile_w / 2},
                "y": {"value": value_y},
            },
        })

        if t.get("progress"):
            pct = _clamp(t["progress"]["fraction"], 0, 1.5)
            pct_text = f"{js_round(t['progress']['fraction'] * 100)}% of {t.get('goalText')}"
            is_exceeded = t["progress"]["fraction"] >= 1
            is_behind = t["progress"]["fraction"] < behind_threshold
            fill_color = PROGRESS_EXCEEDED if is_exceeded else (PROGRESS_BEHIND if is_behind else PROGRESS_ON_TRACK)

            layers.append({
                "data": {"values": [{}]},
                "mark": {
                    "type": "text",
                    "fontSize": sub_font,
                    "fontWeight": 600 if is_exceeded else 400,
                    "fill": PROGRESS_EXCEEDED if is_exceeded else "#666",
                    "align": "center",
                    "baseline": "top",
                    "text": pct_text,
                    "tooltip": None,
                },
                "encoding": {
                    "x": {"value": tile_w / 2},
                    "y": {"value": sub_y},
                },
            })

            layers.append({
                "data": {"values": [{}]},
                "mark": {
                    "type": "rect",
                    "fill": PROGRESS_TRACK,
                    "cornerRadius": bar_height / 2,
                    "tooltip": None,
                },
                "encoding": {
                    "x": {"value": bar_left},
                    "x2": {"value": bar_right},
                    "y": {"value": bar_y},
                    "y2": {"value": bar_y + bar_height},
                },
            })
            fill_end = bar_left + min(1, pct) * bar_width
            layers.append({
                "data": {"values": [{}]},
                "mark": {
                    "type": "rect",
                    "fill": fill_color,
                    "cornerRadius": bar_height / 2,
                    "tooltip": None,
                },
                "encoding": {
                    "x": {"value": bar_left},
                    "x2": {"value": fill_end},
                    "y": {"value": bar_y},
                    "y2": {"value": bar_y + bar_height},
                },
            })
        elif t.get("goalText") is not None:
            layers.append({
                "data": {"values": [{}]},
                "mark": {
                    "type": "text",
                    "fontSize": sub_font,
                    "fill": "#666",
                    "align": "center",
                    "baseline": "top",
                    "text": f"Goal: {t['goalText']}",
                    "tooltip": None,
                },
                "encoding": {
                    "x": {"value": tile_w / 2},
                    "y": {"value": sub_y},
                },
            })

        return {
            "width": tile_w,
            "height": tile_h,
            "layer": layers,
            "resolve": {"scale": {"x": "independent", "y": "independent"}},
        }

    tile_specs = [build_tile(t) for t in tiles]

    if len(tile_specs) == 1:
        tile = tile_specs[0]
        spec["width"] = tile["width"]
        spec["height"] = tile["height"]
        spec["layer"] = tile["layer"]
        spec["resolve"] = tile["resolve"]
        return

    if "layer" in spec:
        del spec["layer"]
    if "encoding" in spec:
        del spec["encoding"]
    if layout == "horizontal":
        spec["hconcat"] = tile_specs
        spec["spacing"] = spacing
    elif layout == "vertical":
        spec["vconcat"] = tile_specs
        spec["spacing"] = spacing
    else:
        grid: list = []
        for r in range(rows):
            row_tiles = tile_specs[r * cols:(r + 1) * cols]
            if len(row_tiles) == 0:
                continue
            grid.append({"hconcat": row_tiles, "spacing": spacing})
        spec["vconcat"] = grid
        spec["spacing"] = spacing


kpi_card_def = {
    "chart": "KPI Card",
    "template": {"layer": []},
    "channels": ["metric", "value", "goal"],
    "markCognitiveChannel": "position",
    "instantiate": _kpi_instantiate,
    "properties": [
        {
            "key": "layout",
            "label": "Layout",
            "type": "discrete",
            "options": [
                {"value": "horizontal", "label": "Horizontal"},
                {"value": "vertical", "label": "Vertical"},
                {"value": "grid", "label": "Grid"},
            ],
            "defaultValue": "grid",
        },
        {
            "key": "style",
            "label": "Card style",
            "type": "binary",
            "defaultValue": True,
        },
        {
            "key": "behindThreshold",
            "label": "Behind threshold",
            "type": "continuous",
            "min": 0,
            "max": 1,
            "step": 0.05,
            "defaultValue": 0.5,
            "check": lambda ctx: {
                "applicable": bool(((ctx.get("encodings") or {}).get("goal") or {}).get("field")),
            },
        },
    ],
}
