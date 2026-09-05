"""verify_calculations.py — 원문 표시 정밀도를 보존하는 Decimal CAGR 전수 검산.

CLI: python scripts/verify_calculations.py <work_dir>
     python scripts/verify_calculations.py --demo
원본 대장은 읽기만 하고 결과를 audit/calc-check.json에 쓴다. v3 신규 결함은 WARN.
"""
from __future__ import annotations

import json
import re
import sys
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

from facts_db import FactsDB, ValidationError, schema_version
from skill_paths import WorkPaths

ATOMIC_INPUTS = ("base_value", "base_year", "forecast_value", "forecast_year",
                 "reported_cagr", "cagr_start_year", "cagr_end_year")
_FORECAST = re.compile(r"(?:19|20)\d{2}.*?(?:→|->|~|–|-|부터|to).*?(?:19|20)\d{2}", re.I)


def is_calculation_candidate(fact: dict) -> bool:
    value = fact.get("value") or {}
    context = fact.get("context") or {}
    text = " ".join(str(x) for x in (fact.get("claim", ""), value.get("raw", ""),
                                    context.get("metric", ""), context.get("period", "")))
    return (any(k in value for k in ATOMIC_INPUTS)
            or bool(re.search(r"CAGR|연평균.*성장", text, re.I))
            or bool(_FORECAST.search(text))
            or (context.get("basis") == "forecast"
                and any(term in str(context.get("metric", "")).lower() for term in ("market", "시장"))))


def _decimal(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("숫자 또는 Decimal 문자열 필요")
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("유한 Decimal 값 필요")
    return number


def check_calculation(fact: dict) -> dict:
    """끝값 각각 ±반 최소표시단위. 다른 CAGR 기간은 억지로 같은 끝값에 적용하지 않는다."""
    value = fact.get("value") or {}
    result = {"fact_id": fact.get("id"), "status": "NOT_CHECKABLE",
              "raw": value.get("raw"), "missing_fields": [
                  k for k in ATOMIC_INPUTS if value.get(k) in (None, "")]}
    if result["missing_fields"]:
        return result
    try:
        with localcontext() as ctx:
            ctx.prec = 50
            base, forecast, reported = (_decimal(value[k]) for k in
                                        ("base_value", "forecast_value", "reported_cagr"))
            years = {k: _decimal(value[k]) for k in
                     ("base_year", "forecast_year", "cagr_start_year", "cagr_end_year")}
            if any(y != y.to_integral_value() for y in years.values()):
                raise ValueError("연도는 정수여야 함")
            start, end = years["cagr_start_year"], years["cagr_end_year"]
            if end <= start or years["forecast_year"] <= years["base_year"]:
                raise ValueError("전망기간은 양수여야 함")
            if start != years["base_year"] or end != years["forecast_year"]:
                result.update(reason="CAGR 기간과 끝값 기준연도 불일치 — 해당 기간 끝값 재확인 필요",
                              missing_fields=["base_value_at_cagr_start_year",
                                              "forecast_value_at_cagr_end_year"])
                return result
            # 문자열의 소수 자릿수/지수는 표시 정밀도다. 4.50을 4.5로 정규화하면 안 된다.
            base_half = Decimal(1).scaleb(base.as_tuple().exponent) / 2
            forecast_half = Decimal(1).scaleb(forecast.as_tuple().exponent) / 2
            if base - base_half <= 0 or forecast - forecast_half <= 0:
                raise ValueError("반올림 구간의 양 끝값은 양수여야 함")
            exponent = Decimal(1) / (end - start)
            growth = lambda ratio: (ratio ** exponent - 1) * 100
            calculated = growth(forecast / base)
            lower = growth((forecast - forecast_half) / (base + base_half))
            upper = growth((forecast + forecast_half) / (base - base_half))
            result.update(status="MATCH" if lower <= reported <= upper else "CONFLICT",
                          calculated_cagr=str(calculated), reported_cagr=str(reported),
                          cagr_interval={"lower": str(lower), "upper": str(upper)},
                          years=str(end - start))
    except (InvalidOperation, ValueError, ArithmeticError) as exc:
        result.update(status="INVALID_INPUT", reason=str(exc))
    return result


def verify(work: WorkPaths | Path | str, *, check_only: bool = False) -> dict:
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    failures, warnings, results = [], [], []
    for fact in FactsDB(wp).facts():
        try:
            strict = schema_version(fact) == 4
        except ValidationError as exc:
            failures.append(str(exc))
            continue
        if not is_calculation_candidate(fact):
            continue
        result = check_calculation(fact)
        results.append(result)
        issues = []
        if fact.get("risk") == "high" and not any(k in (fact.get("value") or {}) for k in ATOMIC_INPUTS):
            issues.append("고위험 시장 전망 원자화 미기록")
        if result["status"] == "INVALID_INPUT":
            issues.append(result["reason"])
        if result["status"] == "CONFLICT":
            message = (f"[계산충돌] {fact.get('id')}: reported={result['reported_cagr']}%, "
                       f"calculated={result['calculated_cagr']}%, 구간={result['cagr_interval']}")
            (failures if strict and fact.get("status") == "confirmed" else warnings).append(message)
        for issue in issues:
            (failures if strict else warnings).append(f"[계산] {fact.get('id')}: {issue}")
        if result["status"] == "NOT_CHECKABLE":
            warnings.append(f"[NOT_CHECKABLE] {fact.get('id')}: 누락={result['missing_fields']}"
                            + (f"; {result['reason']}" if result.get("reason") else ""))
    report = {"ok": not failures, "failures": failures, "warnings": warnings, "results": results}
    if not check_only:
        wp.audit.mkdir(parents=True, exist_ok=True)
        (wp.audit / "calc-check.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def demo() -> None:
    sample = {"id": "F001", "value": {"raw": "4.5 -> 12.8", "base_value": "4.5",
              "base_year": 2025, "forecast_value": "12.8", "forecast_year": 2035,
              "reported_cagr": "17.8", "cagr_start_year": 2025, "cagr_end_year": 2035}}
    result = check_calculation(sample)
    assert result["status"] == "CONFLICT", result
    sample["value"]["reported_cagr"] = "11.0"
    assert check_calculation(sample)["status"] == "MATCH"
    sample["value"]["cagr_start_year"] = 2026
    assert check_calculation(sample)["status"] == "NOT_CHECKABLE"
    print(json.dumps({"demo": "PASS", "conflict": result}, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--demo"]:
        demo()
        return 0
    if len(args) != 1:
        print(__doc__)
        return 2
    try:
        report = verify(args[0])
    except (OSError, ValueError) as exc:
        print(f"계산 검사 FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
