"""facts.jsonl의 confirmed 사실만 사용해 단순 SVG 차트를 생성한다.

CLI:
  python make_chart.py bar  <work_dir> --facts F001,F002 --title "제목" [--out assets/<slug>.svg]
  python make_chart.py line <work_dir> --facts F010,F011,F012 --title "제목" [--out assets/<slug>.svg]
  python make_chart.py demo
"""
from __future__ import annotations

import argparse
import sys
import tempfile
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
                "verify_events": ([{"by": "lead", "at": _now(), "action": "reread", "note": "demo"}]
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
    for chart_type in ("bar", "line"):
        chart_parser = subparsers.add_parser(chart_type)
        chart_parser.add_argument("work_dir")
        chart_parser.add_argument("--facts", required=True)
        chart_parser.add_argument("--title", required=True)
        chart_parser.add_argument("--out")
    subparsers.add_parser("demo")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "demo":
        demo()
        return 0
    try:
        fact_ids = _parse_fact_ids(args.facts)
        out = make_chart(args.command, args.work_dir, fact_ids, args.title, args.out)
    except (ChartError, OSError) as exc:
        print(f"[make_chart] 실패: {exc}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
