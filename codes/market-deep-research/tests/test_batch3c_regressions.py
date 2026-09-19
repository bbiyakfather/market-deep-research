"""배치 3C: R06~R09 수치·단위 파서 회귀.

해석하지 못한 표기를 검증 성공으로 처리하지 않는지, 기존 양성 대조가 깨지지 않는지를 고정한다.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_facts as verifier


def fact(raw, unit, status="confirmed"):
    return {"status": status, "value": {"raw": raw, "unit": unit}}


def check(body, raw, unit):
    return verifier.check_bound_numbers(body, {"F001": fact(raw, unit)})


def test_r06_usd_b_matches_billions_prefix():
    failures, warnings = check("$4.5B(F001)", "4.5", "USD_B")
    assert failures == [] and warnings == []


def test_r06_usd_b_rejects_unscaled_dollars():
    failures, warnings = check("$4.5(F001)", "4.5", "USD_B")
    assert any("값불일치" in item for item in failures)
    assert warnings == []


def test_r06_uninterpreted_currency_suffix_is_unsupported():
    failures, _ = check("$4.5(F001)", "4.5", "USD_FOO")
    assert any("단위미지원" in item for item in failures)


@pytest.mark.parametrize("unit,body", [("USD_MN", "$4.5M(F001)"), ("USD_BN", "$4.5B(F001)"),
                                       ("EUR_M", "€4.5M(F001)"), ("KRW_T", "₩4.5조(F001)")])
def test_r06_currency_multiplier_aliases(unit, body):
    failures, warnings = check(body, "4.5", unit)
    assert failures == [] and warnings == []


def test_r07_lowercase_mw_is_unrecognized():
    failures, warnings = check("999 mw(F001)", "45", "mW")
    assert any("수치미인식" in item or "값불일치" in item for item in failures)
    assert any("999 mw" in item for item in failures)
    assert warnings == []


def test_r07_canadian_dollar_is_not_usd():
    failures, warnings = check("C$999(F001)", "45", "USD")
    assert any("단위불일치" in item for item in failures)
    assert warnings == []


def test_r07_si_case_controls_unchanged():
    ok, warn = check("45 mW(F001)", "45", "mW")
    assert ok == [] and warn == []
    bad, _ = check("45 MW(F001)", "45", "mW")
    assert bad


def test_r08_b2b_is_not_a_billion_suffix():
    body = "매출은 $45 B2B 부문에서 발생했다(F001)."
    failures, warnings = check(body, "45", "USD")
    assert failures == [] and warnings == []


@pytest.mark.parametrize("body", [
    "매출은 $45 M2M 부문에서 발생했다(F001).",
    "매출은 $45 T1 라인에서 발생했다(F001).",
])
def test_r08_alphanumeric_after_scale_is_not_consumed(body):
    failures, warnings = check(body, "45", "USD")
    assert failures == [] and warnings == []


def test_r09_parenthetical_period_does_not_split_tag():
    body = "매출은 45 USD(주1. 연결 기준)(F001)이다."
    failures, warnings = check(body, "45", "USD")
    assert failures == [] and warnings == []


def test_r09_unclosed_paren_falls_back_to_old_split():
    body = "매출은 45 USD(주1. 연결 기준(F001)이다."
    failures, _ = check(body, "45", "USD")
    assert any("무태그" in item for item in failures)


@pytest.mark.parametrize("raw,unit,body", [
    ("175", "USD_M", "US$175M(F001)"),
    ("120", "EUR_M", "€120M(F001)"),
    ("300", "KRW_T", "₩300조(F001)"),
    ("-3.2", "%", "-3.2%(F001)"),
    ("1.2~1.5", "GW", "1.2~1.5 GW(F001)"),
    ("3", "개사", "3개사(F001)"),
])
def test_positive_controls_keep_passing(raw, unit, body):
    failures, warnings = check(body, raw, unit)
    assert failures == [] and warnings == [], (body, failures, warnings)


@pytest.mark.parametrize("unit,body", [
    ("USD_million_extra", "$4.5M(F001)"),
    ("USD_billionTypo", "$4.5B(F001)"),
    ("USD_B_extra", "$4.5B(F001)"),
    ("USD_million2", "$4.5M(F001)"),
])
def test_b3_03_currency_unit_rejects_remaining_suffix(unit, body):
    failures, warnings = check(body, "4.5", unit)
    assert any("[단위미지원]" in item for item in failures)
    assert warnings == []


@pytest.mark.parametrize("unit,body", [
    ("USD_B", "$4.5B(F001)"), ("USD_MN", "$4.5M(F001)"),
    ("USD_BN", "$4.5B(F001)"), ("USD_million", "$4.5M(F001)"),
    ("USD_billion", "$4.5B(F001)"), ("USD_thousand", "$4.5K(F001)"),
    ("USD_trillion", "$4.5T(F001)"), ("usd_mIlLiOn", "$4.5M(F001)"),
    ("USD billion", "$4.5B(F001)"),
])
def test_b3_03_complete_currency_aliases_still_match(unit, body):
    assert check(body, "4.5", unit) == ([], [])


@pytest.mark.parametrize("body", [
    "출력은 999 밀리와트(F001)이다.", "출력은 999 메가와트(F001)이다.",
    "출력은 999밀리와트이다(F001).", "출력은 999 mw(F001)이다.",
    "출력은 999 Mw(F001)이다.", "전력량은 999 gwh(F001)이다.",
])
def test_b3_04_unbound_unit_candidates_fail(body):
    failures, warnings = check(body, "45", "mW")
    assert any("[수치미인식]" in item for item in failures)
    assert warnings == []


@pytest.mark.parametrize("unit", [
    "와트", "킬로와트", "메가와트", "기가와트", "테라와트", "밀리와트", "마이크로와트",
    "와트시", "킬로와트시", "메가와트시", "기가와트시", "유로", "엔", "위안", "프로",
    "킬로그램", "그램", "미터", "킬로미터", "헤르츠", "킬로헤르츠", "메가헤르츠",
    "기가헤르츠", "볼트", "암페어", "리터",
])
def test_b3_04_korean_unit_names_are_not_silently_ignored(unit):
    failures, warnings = check(f"수량은 999 {unit}(F001)이다.", "45", "mW")
    assert any("[수치미인식]" in item for item in failures)
    assert warnings == []


def test_b3_04_recognized_dollar_still_compares_value():
    failures, warnings = check("매출은 999 달러(F001)이다.", "45", "USD")
    assert any("[수치미인식]" in item or "[값불일치]" in item for item in failures)
    assert warnings == []


@pytest.mark.parametrize("identifier", ["B2B", "M2M", "T1"])
def test_b3_05_table_fallback_with_identifier_is_bound(identifier):
    assert check(f"| 매출 | $45 {identifier} | (F001) |", "45", "USD") == ([], [])


def test_b3_05_table_fallback_prevents_second_unrecognized_verdict():
    assert check("| 매출 | $45 | 999 mw | (F001) |", "45", "USD") == ([], [])


@pytest.mark.parametrize("identifier", ["B2B", "M2M", "H2", "CO2", "T1", "X45MW"])
def test_b3_05_number_does_not_start_inside_identifier(identifier):
    assert check(f"{identifier} 시장 전망이다(F001).", "45", "mW") == ([], [])


@pytest.mark.parametrize("body", [
    "5G 시장 전망이다(F001).", "4K 시장 전망이다(F001).", "3D 시장 전망이다(F001).",
    "2024 OECD 전망이다(F001).", "2024년 기준이다(F001).", "3분기 전망이다(F001).",
    "제25조 규정이다(F001).", "2030년 목표이다(F001).", "9월 전망이다(F001).",
    "19일 발표이다(F001).", "2차 전망이다(F001).", "3세대 기술이다(F001).",
    "제3항 규정이다(F001).", "제4호 규정이다(F001).",
])
def test_b3_06_non_quantity_citations_remain_clean(body):
    assert check(body, "45", "mW") == ([], [])


def test_b3_06_unknown_korean_quantity_is_warning_only():
    failures, warnings = check("진출 범위는 45 개국(F001)이다.", "45", "mW")
    assert failures == []
    assert len(warnings) == 1 and "[수치미인식?]" in warnings[0]


@pytest.mark.parametrize("body,raw", [
    ("출력은 999 밀리와트(F001)이다.", "정성 전망"),
    ("출력은 45 mW(F001)이며 999 밀리와트도 언급했다.", "45"),
])
def test_b3_06_unrecognized_check_requires_unbound_numeric_fact(body, raw):
    assert check(body, raw, "mW") == ([], [])
