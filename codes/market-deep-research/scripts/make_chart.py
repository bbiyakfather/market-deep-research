"""facts.jsonl의 confirmed 사실만 사용해 단순 SVG 차트를 생성한다.

CLI:
  python make_chart.py bar  <work_dir> --facts F001,F002 --title "제목" [--out assets/<slug>.svg]
  python make_chart.py line <work_dir> --facts F010,F011,F012 --title "제목" [--out assets/<slug>.svg]
  python make_chart.py demo
  python make_chart.py <type> <work_dir> --facts ... --title "제목" [--engine flint|native] [--top N]
    type = CHART_MAP 의 키(hbar·bar·line·grouped·stacked100·scatter·pie·heatmap·lollipop·slope·bump·dot·area·radar·rose·pyramid).
    기본 engine=flint: scripts/flint(내장, 수정 금지) → assets/<slug>.vl.json 사이드카 + (vl-convert 있으면) .svg.
    native 는 bar·line 두 종만 있는 자체 SVG 폴백.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path

from facts_db import FactsDB, _write_jsonl_atomic
from skill_paths import WorkPaths, slugify


class ChartError(ValueError):
    """차트 입력 사실이나 출력 경로가 안전하지 않을 때 발생한다."""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_fact_ids(raw: str) -> list[str]:
    fact_ids = [item.strip() for item in raw.split(",") if item.strip()]
    if not fact_ids:
        raise ChartError("--facts에 F-ID를 하나 이상 지정해야 합니다")
    if len(set(fact_ids)) != len(fact_ids):
        raise ChartError("--facts에 중복 F-ID가 있습니다")
    return fact_ids


def _load_confirmed_facts(wp: WorkPaths, fact_ids: list[str]) -> list[dict]:
    """FactsDB의 공용 로더로 사실을 읽고 요청 순서대로 반환한다."""
    by_id = {fact.get("id"): fact for fact in FactsDB(wp).facts()}
    rejected = []
    for fact_id in fact_ids:
        status = by_id.get(fact_id, {}).get("status", "missing")
        if status != "confirmed":
            rejected.append(f"{fact_id}={status}")
    if rejected:
        raise ChartError("confirmed가 아닌 사실: " + ", ".join(rejected))
    return [by_id[fact_id] for fact_id in fact_ids]


def _numeric_values(facts: list[dict]) -> tuple[list[Decimal], list[str], str]:
    values: list[Decimal] = []
    raw_labels: list[str] = []
    units: list[str] = []
    for fact in facts:
        fact_id = fact["id"]
        value = fact.get("value") or {}
        raw = str(value.get("raw", "")).strip()
        unit = str(value.get("unit", "")).strip()
        try:
            number = Decimal(raw.replace(",", ""))
        except InvalidOperation as exc:
            raise ChartError(f"{fact_id}: value.raw가 숫자가 아닙니다: {raw!r}") from exc
        if not number.is_finite():
            raise ChartError(f"{fact_id}: 유한한 숫자만 차트로 만들 수 있습니다: {raw!r}")
        if not unit:
            raise ChartError(f"{fact_id}: value.unit이 비어 있습니다")
        values.append(number)
        raw_labels.append(raw)
        units.append(unit)
    if len(set(units)) != 1:
        details = ", ".join(f"{fact['id']}={unit}" for fact, unit in zip(facts, units))
        raise ChartError(f"서로 다른 단위는 한 차트에서 비교할 수 없습니다: {details}")
    return values, raw_labels, units[0]


def _axis_labels(facts: list[dict]) -> list[str]:
    contexts = [fact.get("context") or {} for fact in facts]
    periods = [str(context.get("period", "")).strip() for context in contexts]
    entities = [str(context.get("entity", "")).strip() for context in contexts]
    if all(periods) and len(set(periods)) == len(periods):
        return periods
    if all(entities) and len(set(entities)) == len(entities):
        return entities
    labels = []
    for fact, entity, period in zip(facts, entities, periods):
        label = " · ".join(part for part in (entity, period) if part)
        labels.append(label or fact["id"])
    if len(set(labels)) != len(labels):
        labels = [f"{label} ({fact['id']})" for fact, label in zip(facts, labels)]
    return labels


def _format_tick(value: Decimal) -> str:
    text = format(value, ".4f").rstrip("0").rstrip(".")
    if text in ("", "-0"):
        return "0"
    integer, dot, fraction = text.partition(".")
    return f"{int(integer):,}" + (dot + fraction if dot else "")


def _svg(chart_type: str, facts: list[dict], title: str) -> str:
    fact_ids = [fact["id"] for fact in facts]
    values, raw_labels, unit = _numeric_values(facts)
    labels = _axis_labels(facts)

    width, height = 960, 540
    left, right, top, bottom = 95, 35, 80, 400
    plot_width, plot_height = width - left - right, bottom - top

    data_min, data_max = min(values), max(values)
    y_min, y_max = min(data_min, Decimal(0)), max(data_max, Decimal(0))
    if y_min == y_max:
        y_max = Decimal(1)
    span = y_max - y_min
    pad = span * Decimal("0.10")
    if y_min < 0:
        y_min -= pad
    if y_max > 0:
        y_max += pad
    span = y_max - y_min

    def x_pos(index: int) -> float:
        return left + plot_width * (index + 0.5) / len(values)

    def y_pos(value: Decimal) -> float:
        return top + float((y_max - value) / span) * plot_height

    metrics = {str((fact.get("context") or {}).get("metric", "")).strip() for fact in facts}
    metrics.discard("")
    x_axis = next(iter(metrics)) if len(metrics) == 1 else "fact"

    lines = [
        f"<!-- FACTS: {','.join(fact_ids)} -->",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"  <title>{escape(title)}</title>",
        f"  <desc>{escape(', '.join(fact_ids))}의 confirmed 사실로 생성한 {chart_type} 차트</desc>",
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
        f'  <text x="{width / 2:.1f}" y="38" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#172033">{escape(title)}</text>',
    ]

    for index in range(6):
        tick = y_min + span * Decimal(index) / Decimal(5)
        y = y_pos(tick)
        lines.extend([
            f'  <line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#d9dee8" stroke-width="1"/>',
            f'  <text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#4b5565">{escape(_format_tick(tick))}</text>',
        ])

    zero_y = y_pos(Decimal(0))
    lines.extend([
        f'  <line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#586174" stroke-width="1.5"/>',
        f'  <line x1="{left}" y1="{zero_y:.2f}" x2="{width - right}" y2="{zero_y:.2f}" stroke="#586174" stroke-width="1.5"/>',
        f'  <text x="24" y="{(top + bottom) / 2:.1f}" transform="rotate(-90 24 {(top + bottom) / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#384152">{escape(unit)}</text>',
    ])

    if chart_type == "bar":
        slot = plot_width / len(values)
        bar_width = slot * 0.58
        for index, (value, raw_label) in enumerate(zip(values, raw_labels)):
            x = x_pos(index) - bar_width / 2
            value_y = y_pos(value)
            rect_y = min(value_y, zero_y)
            rect_height = max(abs(zero_y - value_y), 1.0)
            text_y = value_y - 8 if value >= 0 else value_y + 18
            lines.extend([
                f'  <rect x="{x:.2f}" y="{rect_y:.2f}" width="{bar_width:.2f}" height="{rect_height:.2f}" fill="#2f6fed"/>',
                f'  <text x="{x_pos(index):.2f}" y="{text_y:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="600" fill="#172033">{escape(raw_label)}</text>',
            ])
    else:
        points = " ".join(f"{x_pos(i):.2f},{y_pos(value):.2f}" for i, value in enumerate(values))
        lines.append(f'  <polyline points="{points}" fill="none" stroke="#0f766e" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
        for index, (value, raw_label) in enumerate(zip(values, raw_labels)):
            x, y = x_pos(index), y_pos(value)
            text_y = y - 11 if value >= 0 else y + 21
            lines.extend([
                f'  <circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#0f766e"/>',
                f'  <text x="{x:.2f}" y="{text_y:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="600" fill="#172033">{escape(raw_label)}</text>',
            ])

    for index, label in enumerate(labels):
        lines.append(
            f'  <text x="{x_pos(index):.2f}" y="{bottom + 24}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#384152">{escape(label)}</text>'
        )
    lines.extend([
        f'  <text x="{left + plot_width / 2:.2f}" y="{bottom + 52}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#384152">{escape(x_axis)}</text>',
        f'  <text x="{width / 2:.1f}" y="510" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#586174">출처 사실: ({escape(", ".join(fact_ids))}) · 단위: {escape(unit)}</text>',
        "</svg>",
    ])
    return "\n".join(lines) + "\n"


def make_chart(chart_type: str, work_dir: Path | str, fact_ids: list[str], title: str,
               out: Path | str | None = None) -> Path:
    if chart_type not in ("bar", "line"):
        raise ChartError(f"지원하지 않는 차트 종류: {chart_type}")
    wp = WorkPaths(work_dir)
    facts = _load_confirmed_facts(wp, fact_ids)

    if out is None:
        target = wp.gen_assets / f"{slugify(title)}.svg"
    else:
        out_path = Path(out)
        target = out_path if out_path.is_absolute() else wp.root / out_path
    assets_root = wp.gen_assets.resolve()
    target = target.resolve()
    try:
        target.relative_to(assets_root)
    except ValueError as exc:
        raise ChartError(f"--out은 작업 폴더의 assets/ 아래여야 합니다: {target}") from exc
    if target.suffix.lower() != ".svg":
        raise ChartError(f"--out 확장자는 .svg여야 합니다: {target.name}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_svg(chart_type, facts, title), encoding="utf-8", newline="\n")
    return target


# ---------------------------------------------------------------------------
# flint 엔진 — scripts/flint(내장, 수정 금지)로 Vega-Lite 스펙을 만들고 사이드카로 남긴다.
# ---------------------------------------------------------------------------
# mdr 유형명 -> (flint chartType, {채널: 행 필드}, 시리즈 필수 여부, chartProperties)
# 행 필드: label(축·범주) / series(fact.context.series, 없으면 label 만) / value.
# 가정: 범주는 context.axis → period → entity 순, 시리즈는 context.series. scatter 는 series 가 "x"/"y" 인 fact 쌍.
CHART_MAP: dict[str, tuple[str, dict, bool, dict]] = {
    "hbar": ("Bar Chart", {"y": "label", "x": "value"}, False, {"includeZero_x": True}),
    "bar": ("Bar Chart", {"x": "label", "y": "value"}, False, {"includeZero_y": True}),
    "line": ("Line Chart", {"x": "label", "y": "value", "color": "series"}, False, {}),
    "grouped": ("Grouped Bar Chart", {"x": "label", "y": "value", "group": "series"}, True, {"includeZero_y": True}),
    "stacked100": ("Stacked Bar Chart", {"x": "label", "y": "value", "color": "series"}, True, {"stackMode": "normalize"}),
    "scatter": ("Scatter Plot", {"x": "x", "y": "y"}, True, {}),
    "pie": ("Pie Chart", {"size": "value", "color": "label"}, False, {}),
    "heatmap": ("Heatmap", {"x": "label", "y": "series", "color": "value"}, True, {}),
    "lollipop": ("Lollipop Chart", {"y": "label", "x": "value"}, False, {}),
    "slope": ("Slope Chart", {"x": "series", "y": "value", "color": "label"}, True, {}),
    "bump": ("Bump Chart", {"x": "series", "y": "value", "color": "label"}, True, {}),
    "dot": ("Ranged Dot Plot", {"x": "value", "y": "label", "color": "series"}, True, {}),
    "area": ("Area Chart", {"x": "label", "y": "value", "color": "series"}, False, {}),
    "radar": ("Radar Chart", {"x": "label", "y": "value", "color": "series"}, False, {}),
    "rose": ("Rose Chart", {"x": "label", "y": "value"}, False, {}),
    "pyramid": ("Pyramid Chart", {"y": "label", "x": "value", "color": "series"}, True, {}),
}
MAX_CATEGORY, MAX_SERIES, MAX_HEATMAP_AXIS, MAX_PIE = 20, 12, 25, 5
LABEL_WIDTH_CAP = 14  # 한글=1.6 단위. flint 폭 추정(라틴 0.62)이 한글을 과소평가하므로 래퍼에서 라벨 길이를 제한한다.
FONT_STACK = "Malgun Gothic, Noto Sans KR, sans-serif"


def _wide(text: str) -> float:
    return sum(1.6 if unicodedata.east_asian_width(c) in "WF" else 1.0 for c in text)


def _cap_label(text: str) -> str:
    if _wide(text) <= LABEL_WIDTH_CAP:
        return text
    out = ""
    for ch in text:
        if _wide(out + ch) > LABEL_WIDTH_CAP - 1:
            break
        out += ch
    return out + "…"


def _flint_rows(chart_type: str, facts: list[dict]) -> list[dict]:
    """fact -> 행. 값은 float, 원문은 value_raw 문자열로 따로 둔다."""
    groups = [facts]
    if chart_type == "scatter":
        groups = [[f for f in facts if (f.get("context") or {}).get("series") == ax] for ax in ("x", "y")]
        if sum(map(len, groups)) != len(facts) or not all(groups):
            raise ChartError("scatter: 모든 fact 의 context.series 가 'x' 또는 'y' 여야 합니다")
    rows: list[dict] = []
    for group in groups:
        values, raws, unit = _numeric_values(group)
        for f, v, raw in zip(group, values, raws):
            c = f.get("context") or {}
            rows.append({"fact_id": f["id"], "value": float(v), "value_raw": raw, "unit": unit,
                         "series": str(c.get("series", "")).strip(),
                         "_axis": str(c.get("axis") or c.get("period") or c.get("entity") or "").strip()})
    by_id = {r["fact_id"]: r for r in rows}
    rows = [by_id[f["id"]] for f in facts]
    if not any(r["series"] for r in rows):
        for r, label in zip(rows, _axis_labels(facts)):
            r["label"] = label
    else:
        for r, f in zip(rows, facts):
            r["label"] = r["_axis"] or f["id"]
        if len({(r["label"], r["series"]) for r in rows}) != len(rows):
            raise ChartError("(범주, 시리즈) 조합이 중복됩니다 — context.axis/series 를 확인하세요")
    for r in rows:
        r.pop("_axis")
    return rows


def _check_limits(chart_type: str, rows: list[dict], top: int | None) -> tuple[list[dict], list[str]]:
    """한도 초과는 FAIL(조용한 절단 금지). --top 으로 명시 선택한 경우만 상위 N 을 남기고 나머지 F-ID 를 기록한다."""
    cats = {r["label"] for r in rows}
    sers = {r["series"] for r in rows if r["series"]}
    limit = MAX_PIE if chart_type == "pie" else MAX_HEATMAP_AXIS if chart_type == "heatmap" else MAX_CATEGORY
    if chart_type == "pie" and len(cats) != len(rows):
        raise ChartError("pie: 범주당 1행이어야 합니다")
    if len(sers) > (MAX_HEATMAP_AXIS if chart_type == "heatmap" else MAX_SERIES):
        raise ChartError(f"시리즈 {len(sers)}개가 한도를 넘습니다(시리즈 {MAX_SERIES}·히트맵 축 {MAX_HEATMAP_AXIS})")
    if len(cats) <= limit:
        return rows, []
    if top is None:
        raise ChartError(f"범주 {len(cats)}개 > 한도 {limit} — 조용한 절단은 하지 않습니다(--top N 으로 명시 선택)")
    if sers:
        raise ChartError("--top 은 시리즈 없는 차트에만 쓸 수 있습니다")
    keep = {r["fact_id"] for r in sorted(rows, key=lambda r: -r["value"])[:top]}
    return [r for r in rows if r["fact_id"] in keep], [r["fact_id"] for r in rows if r["fact_id"] not in keep]


def _semantic(unit: str) -> str:
    if "%" in unit or unit.upper() in ("PCT", "PERCENT"):
        return "Percentage"
    return "Count" if unit.lower() in ("count", "건", "개", "명") else "Quantity"


def _pivot_scatter(rows: list[dict]) -> list[dict]:
    pts: dict[str, dict] = {}
    for r in rows:
        pt = pts.setdefault(r["label"], {"label": r["label"]})
        pt[r["series"]], pt["fact_id_" + r["series"]] = r["value"], r["fact_id"]
    if not all("x" in p and "y" in p for p in pts.values()):
        raise ChartError("scatter: 각 범주에 x·y fact 가 한 쌍씩 필요합니다")
    return list(pts.values())


def _resolve_target(wp: WorkPaths, title: str, out: Path | str | None) -> Path:
    if out is None:
        target = wp.gen_assets / f"{slugify(title)}.svg"
    else:
        out_path = Path(out)
        target = out_path if out_path.is_absolute() else wp.root / out_path
    target = target.resolve()
    try:
        target.relative_to(wp.gen_assets.resolve())
    except ValueError as exc:
        raise ChartError(f"--out은 작업 폴더의 assets/ 아래여야 합니다: {target}") from exc
    if target.suffix.lower() != ".svg":
        raise ChartError(f"--out 확장자는 .svg여야 합니다: {target.name}")
    return target


def make_chart_flint(chart_type: str, work_dir: Path | str, fact_ids: list[str], title: str,
                     out: Path | str | None = None, top: int | None = None,
                     native_fallback: bool = False) -> tuple[Path, Path | None]:
    """(사이드카 경로, svg 경로|None) 반환. svg 는 vl_convert 가 없으면 None."""
    if chart_type not in CHART_MAP:
        raise ChartError(f"지원하지 않는 차트 종류: {chart_type} (지원: {', '.join(CHART_MAP)})")
    from flint.vegalite import assemble_vegalite  # 임포트 지연: native 경로는 내장 패키지에 의존하지 않는다

    flint_type, channels, need_series, props = CHART_MAP[chart_type]
    wp = WorkPaths(work_dir)
    facts = _load_confirmed_facts(wp, fact_ids)
    target = _resolve_target(wp, title, out)
    rows = _flint_rows(chart_type, facts)
    if need_series and not any(r["series"] for r in rows):
        raise ChartError(f"{chart_type}: fact.context.series 가 필요합니다")
    rows, dropped = _check_limits(chart_type, rows, top)
    shown = {r["label"]: _cap_label(r["label"]) for r in rows}
    if len(set(shown.values())) != len(shown):
        raise ChartError("라벨을 줄이면 중복됩니다 — 라벨을 짧게 고치세요")
    values = [{**r, "label": shown[r["label"]]} for r in rows]
    if chart_type == "scatter":
        values = _pivot_scatter(values)
    if chart_type == "hbar":
        values.sort(key=lambda r: -r["value"])
    types = {"x": "Quantity", "y": "Quantity"} if chart_type == "scatter" else {
        "label": "Category", "series": "Category", "value": _semantic(rows[0]["unit"])}
    spec = assemble_vegalite({
        "data": {"values": values},
        "semantic_types": types,
        "chart_spec": {"chartType": flint_type, "encodings": {ch: {"field": f} for ch, f in channels.items()},
                       **({"chartProperties": props} if props else {})},
    })

    warnings = [str(w) for w in spec.get("_warnings", [])]
    for k in [k for k in spec if k.startswith("_")]:
        del spec[k]  # flint 내부 메타 — Vega-Lite 에 넘기지 않는다
    returned = {v.get("fact_id") for v in (spec.get("data") or {}).get("values", []) if isinstance(v, dict)}
    if chart_type != "scatter" and not returned >= {r["fact_id"] for r in rows}:
        raise ChartError("flint 가 행을 조용히 절단했습니다(overflow) — 행 수를 줄이거나 --top N 을 쓰세요")
    notes = []
    if chart_type in ("line", "area") and (((spec.get("encoding") or {}).get("y") or {}).get("scale") or {}).get("zero") is False:
        notes.append("축 절단")
    if chart_type in ("hbar", "bar") and isinstance(spec.get("mark"), str):  # 값 라벨은 value_raw 원문 그대로
        pos = {"hbar": {"align": "left", "baseline": "middle", "dx": 4}, "bar": {"baseline": "bottom", "dy": -3}}[chart_type]
        enc = spec.pop("encoding")
        spec["layer"] = [{"mark": spec.pop("mark"), "encoding": enc},
                         {"mark": {"type": "text", "fontSize": 10, **pos},
                          "encoding": {**{k: v for k, v in enc.items() if k in ("x", "y")},
                                       "text": {"field": "value_raw", "type": "nominal"}}}]
    for enc in [spec.get("encoding") or {}] + [lay.get("encoding") or {} for lay in spec.get("layer", [])]:
        for e in enc.values():  # 내부 필드명(label/value) 대신 축 제목: 값=단위, 범주=없음
            if isinstance(e, dict) and e.get("field") in ("value", "label"):
                e["title"] = rows[0]["unit"] if e["field"] == "value" else None
    spec["title"] = title
    spec["description"] = f"{', '.join(fact_ids)}의 confirmed 사실로 생성한 {flint_type}"
    spec.setdefault("config", {})["font"] = FONT_STACK
    spec["mdr"] = {
        "fact_ids": [r["fact_id"] for r in rows], "chart_type": chart_type, "flint_chart_type": flint_type, "title": title,
        "values": [{"fact_id": r["fact_id"], "label": r["label"], "series": r["series"],
                    "value_raw": r["value_raw"], "unit": r["unit"]} for r in rows],
        "dropped": dropped, "note": "; ".join(notes), "warnings": warnings,
        "label_truncated": [k for k, v in shown.items() if k != v],
    }
    side = target.with_suffix(".vl.json")
    side.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)  # 렌더 실패 시 낡은 SVG 가 새 사이드카로 통과하지 않게
    side.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    try:
        import vl_convert as vlc
    except ImportError:
        if chart_type in ("bar", "line") and native_fallback:
            print("[make_chart] vl_convert 없음 — native SVG 로 폴백(사이드카 제거)", file=sys.stderr)
            side.unlink()
            return side, make_chart(chart_type, work_dir, fact_ids, title, out)
        return side, None
    try:
        vlc.register_font_directory("C:/Windows/Fonts")
    except Exception:  # 폰트 디렉터리가 없어도 렌더는 진행
        pass
    svg = vlc.vegalite_to_svg({k: v for k, v in spec.items() if k != "mdr"})  # 모르는 최상위 키는 Vega-Lite 가 경고한다
    target.write_text(f"<!-- FACTS: {','.join(r['fact_id'] for r in rows)} -->\n" + svg, encoding="utf-8", newline="\n")
    return side, target


def demo() -> None:
    with tempfile.TemporaryDirectory() as td:
        wp = WorkPaths(Path(td) / "research_demo")

        def fact(fact_id: str, raw: str, period: str, status: str) -> dict:
            return {
                "claim_key": f"market_size|demo|KR|{period}|annual|na",
                "id": fact_id,
                "claim": f"{period} 시장규모는 {raw}조원",
                "context": {"metric": "market_size", "entity": "demo", "geography": "KR", "period": period},
                "value": {"raw": raw, "unit": "KRW_T"},
                "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"},
                "risk": "normal",
                "status": status,
                "evidence_ids": [f"E{fact_id[1:]}"] if status == "confirmed" else [],
                "verify_events": ([{"by": "lead", "at": _now(), "action": "reread", "note": "demo",
                                    "reread_sha256": "0" * 64}]
                                  if status == "confirmed" else []),
            }

        _write_jsonl_atomic(wp.facts, [
            fact("F001", "10", "2025", "confirmed"),
            fact("F002", "15.5", "2026", "confirmed"),
            fact("F003", "20", "2027", "pending"),
        ])
        out = make_chart("bar", wp.root, ["F001", "F002"], "데모 시장규모")
        svg = out.read_text(encoding="utf-8")
        assert svg.splitlines()[0] == "<!-- FACTS: F001,F002 -->", svg.splitlines()[0]
        assert "(F001, F002)" in svg, "가시 사실 캡션 누락"
        try:
            make_chart("bar", wp.root, ["F001", "F003"], "거부되어야 할 차트")
            assert False, "pending 사실이 차트에 포함됨"
        except ChartError as exc:
            assert "F003=pending" in str(exc), exc
    print(f"[{_now()}] make_chart demo OK")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for chart_type in CHART_MAP:
        chart_parser = subparsers.add_parser(chart_type)
        chart_parser.add_argument("work_dir")
        chart_parser.add_argument("--facts", required=True)
        chart_parser.add_argument("--title", required=True)
        chart_parser.add_argument("--out")
        chart_parser.add_argument("--engine", choices=("flint", "native"), default="flint")
        chart_parser.add_argument("--top", type=int)
    subparsers.add_parser("demo")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "demo":
        demo()
        return 0
    try:
        fact_ids = _parse_fact_ids(args.facts)
        if args.engine == "native":
            print(make_chart(args.command, args.work_dir, fact_ids, args.title, args.out))
            return 0
        side, svg = make_chart_flint(args.command, args.work_dir, fact_ids, args.title, args.out, args.top,
                                     native_fallback=True)
    except (ChartError, OSError) as exc:
        print(f"[make_chart] 실패: {exc}", file=sys.stderr)
        return 1
    print(side)
    if svg is None:
        print("[make_chart] SVG 미생성 — pip install vl-convert-python", file=sys.stderr)
        return 2
    print(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
