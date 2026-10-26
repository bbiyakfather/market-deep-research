"""Port of src/lib/agents-chart/core/encoding-actions.ts.

Reusable factories for Category-B encoding actions: declarative transforms
applied to the user's encoding map at the top of assembly, so the whole
pipeline (semantic resolution -> overflow -> layout -> instantiate) sees the
transformed encodings. See :mod:`flint.core.encoding_overrides` for the
composer.
"""
from __future__ import annotations

from typing import Any, Optional


# Sort choices the Sort control exposes.
SortChoice = str  # 'value-asc' | 'value-desc'


def _is_measure_enc(e: Optional[dict[str, Any]]) -> bool:
    """A measure is a quantitative channel or any aggregated channel."""
    if not e or not e.get("field"):
        return False
    return bool(e.get("aggregate")) or e.get("type") == "quantitative"


def _is_discrete_category_enc(e: Optional[dict[str, Any]]) -> bool:
    """A sortable category axis is discrete (nominal/ordinal). Temporal axes
    are deliberately excluded: reordering a time axis by value scrambles the
    chronology, so Sort should not apply to them."""
    if not e or not e.get("field"):
        return False
    return (
        not e.get("aggregate")
        and e.get("type") != "quantitative"
        and e.get("type") != "temporal"
    )


def _resolve_sort_channels(
    encodings: dict[str, dict[str, Any]],
    candidates: tuple[str, str],
) -> Optional[dict[str, str]]:
    """Identify the discrete category axis and the measure axis among a pair
    of position channels, so Sort works under either orientation (vertical or
    horizontal) and only when a discrete axis actually exists.

    Returns ``None`` when there is no discrete-category + measure pair to sort
    (e.g. a temporal-x time series, or two quantitative axes).
    """
    category = next((c for c in candidates if _is_discrete_category_enc(encodings.get(c))), None)
    measure = next((c for c in candidates if _is_measure_enc(encodings.get(c))), None)
    if not category or not measure or category == measure:
        return None
    return {"category": category, "measure": measure}


def make_sort_action(
    key: str = "sort",
    label: str = "Sort",
    channels: tuple[str, str] = ("x", "y"),
) -> dict[str, Any]:
    """Sort the category axis of a bar-like chart by the measure value.

    Encoding model: a value sort writes ``sortBy = <measure channel>`` (one of
    'x' | 'y', which the assembler understands) on the category channel.
    "Default" clears the sort so the field's canonical ordering wins.
    """
    candidates = channels

    def is_applicable(ctx: dict[str, Any]) -> bool:
        return _resolve_sort_channels(ctx.get("encodings") or {}, candidates) is not None

    def get_value(encodings: dict[str, dict[str, Any]]) -> Optional[str]:
        resolved = _resolve_sort_channels(encodings, candidates)
        if not resolved:
            return None
        enc = encodings[resolved["category"]]
        if enc.get("sortBy") == resolved["measure"]:
            return "value-desc" if enc.get("sortOrder") == "descending" else "value-asc"
        # Any other sort (label order, custom value order, sort-by-color)
        # is not representable by this control -> show as Default.
        return None

    def set_value(
        encodings: dict[str, dict[str, Any]],
        value: Optional[str],
    ) -> dict[str, dict[str, Any]]:
        resolved = _resolve_sort_channels(encodings, candidates)
        if not resolved:
            return encodings
        category = resolved["category"]
        measure = resolved["measure"]
        base = encodings[category]
        if value == "value-asc":
            nxt = {**base, "sortBy": measure, "sortOrder": "ascending"}
        elif value == "value-desc":
            nxt = {**base, "sortBy": measure, "sortOrder": "descending"}
        else:
            nxt = {**base, "sortBy": None, "sortOrder": None}
        return {**encodings, category: nxt}

    return {
        "key": key,
        "label": label,
        "dependencies": list(candidates),
        "isApplicable": is_applicable,
        "control": {
            "type": "discrete",
            "options": [
                {"value": None, "label": "Default"},
                {"value": "value-desc", "label": "Value \u2193"},
                {"value": "value-asc", "label": "Value \u2191"},
            ],
        },
        "get": get_value,
        "set": set_value,
    }
