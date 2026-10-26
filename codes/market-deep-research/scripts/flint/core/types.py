"""Port of the constants from src/lib/agents-chart/core/types.ts.

Only the runtime constants `channels` and `channelGroups` are needed at
runtime; all TS interfaces are erased.
"""

from __future__ import annotations


channels: list[str] = [
    "x", "y", "x2", "y2", "id", "color", "opacity", "size", "shape", "strokeDash",
    "column", "row", "latitude", "longitude", "radius", "detail", "group",
    "open", "high", "low", "close", "angle",
    "metric", "value", "goal",
]


channelGroups: dict[str, list[str]] = {
    "": ["x", "x2", "y", "y2", "latitude", "longitude", "id", "radius", "detail"],
    "legends": ["color", "group", "size", "shape", "text", "opacity", "strokeDash"],
    "price": ["open", "high", "low", "close"],
    "facets": ["column", "row"],
    "kpi": ["metric", "value", "goal"],
}
