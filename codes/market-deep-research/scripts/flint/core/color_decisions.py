"""Port of src/lib/agents-chart/core/color-decisions.ts."""

from __future__ import annotations

from typing import Any, Optional


def _infer_color_channel_primary(channel: str, chart_type: str) -> bool:
    if channel in ("color", "group"):
        return True
    return False


def _decide_scheme_type_from_channel(
    channel: str,
    cs: Optional[dict[str, Any]],
) -> dict[str, Any]:
    hint = (cs or {}).get("colorScheme")
    if hint:
        if hint.get("type") == "diverging":
            return {"schemeType": "diverging", "divergingMidpoint": hint.get("domainMid")}
        if hint.get("type") == "sequential":
            return {"schemeType": "sequential"}
        if hint.get("type") == "categorical":
            sem_type = (cs or {}).get("semanticAnnotation", {}).get("semanticType")
            is_rank_like = sem_type == "Rank"
            if is_rank_like:
                return {"schemeType": "sequential"}
            if (cs or {}).get("type") == "temporal" and channel == "color":
                return {"schemeType": "sequential"}
            return {"schemeType": "categorical"}

    enc_type = (cs or {}).get("type")
    sem_type = (cs or {}).get("semanticAnnotation", {}).get("semanticType")
    if sem_type == "Correlation":
        return {"schemeType": "diverging", "divergingMidpoint": 0}
    if enc_type in ("quantitative", "temporal"):
        return {"schemeType": "sequential"}
    return {"schemeType": "categorical"}


def _count_distinct_values(table: list, field: Optional[str]) -> Optional[int]:
    if not field:
        return None
    s = set()
    for row in table:
        if row is None:
            continue
        s.add(row.get(field))
    return len(s)


def _decide_color_for_channel(channel: str, ctx: dict[str, Any]) -> Optional[dict[str, Any]]:
    encoding = ctx["encodings"].get(channel)
    cs = ctx["channelSemantics"].get(channel)
    if not encoding or not cs or not cs.get("field"):
        return None

    data_driven = True
    primary = _infer_color_channel_primary(channel, ctx["chartType"])

    if encoding.get("scheme") and encoding.get("scheme") != "default":
        distinct = _count_distinct_values(ctx["table"], cs.get("field"))
        scheme_info = _decide_scheme_type_from_channel(channel, cs)
        return {
            "channel": channel,
            "schemeType": scheme_info["schemeType"],
            "schemeId": encoding["scheme"],
            "categoryCount": distinct,
            "primary": primary,
            "dataDriven": data_driven,
        }

    scheme_info = _decide_scheme_type_from_channel(channel, cs)
    distinct = _count_distinct_values(ctx["table"], cs.get("field"))

    out: dict[str, Any] = {
        "channel": channel,
        "schemeType": scheme_info["schemeType"],
        "categoryCount": distinct,
        "primary": primary,
        "dataDriven": data_driven,
    }
    if scheme_info.get("divergingMidpoint") is not None:
        out["divergingMidpoint"] = scheme_info["divergingMidpoint"]
    return out


def decide_color_maps(ctx: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"color": None, "group": None, "fill": None, "stroke": None}
    for ch in ("color", "group"):
        decision = _decide_color_for_channel(ch, ctx)
        if decision:
            result[ch] = decision
    return result
