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
