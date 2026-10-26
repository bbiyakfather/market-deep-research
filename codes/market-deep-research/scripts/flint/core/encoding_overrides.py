"""Port of src/lib/agents-chart/core/encoding-overrides.ts.

Composes Category-B encoding-action overrides (stored by the host as
configuration overrides in ``chartProperties``, keyed by the action's ``key``)
onto the base encoding map before any pipeline phase runs.
"""
from __future__ import annotations

from typing import Any, Optional


def apply_encoding_overrides(
    template: dict[str, Any],
    encodings: dict[str, dict[str, Any]],
    chart_properties: Optional[dict[str, Any]] = None,
) -> dict[str, dict[str, Any]]:
    """For each ``encodingAction`` whose override is present in
    ``chartProperties``, apply the action's ``set(encodings, value)`` to
    produce the transformed encodings. Absent (``None``/missing) overrides
    are skipped so the base encoding value stands.
    """
    actions = template.get("encodingActions")
    if not actions or not chart_properties:
        return encodings

    result = encodings
    for action in actions:
        key = action.get("key")
        if key is None:
            continue
        # JS: `if (override !== undefined)`. In Python `chart_properties.get(key)
        # returns None both when the key is absent and when explicitly set to
        # None — for our extracted fixtures the host never sends explicit None,
        # so "not None" is the right semantic equivalent.
        override = chart_properties.get(key)
        if override is not None:
            result = action["set"](result, override)
    return result
