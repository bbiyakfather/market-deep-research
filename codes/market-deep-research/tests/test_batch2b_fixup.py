"""배치 2B 재리뷰 R1·R2·R3: 실제 검증 경로의 실패와 정상 대조."""
import copy
from decimal import Decimal

import pytest

from test_p0_regressions import work, review, LIMITED
from test_batch2b_regressions import fact_record
import verify_claims as claims
import verify_facts as verifier
from facts_db import FactsDB, _write_jsonl_atomic, make_claim_key


@pytest.mark.parametrize("spacing", ["", " "])
@pytest.mark.parametrize("status,marker,ok", [
    ("confirmed", "", True), ("disputed", "", False), ("disputed", "[상충] ", True)])
@pytest.mark.parametrize("claim", ["Certification is verified", "Source claims 45 USD"])
def test_r1_link_adjacent_tag_status(work, spacing, status, marker, ok, claim):
    facts = FactsDB(work).facts()
    facts[0].update(status=status, value={"raw": "45", "unit": "USD"})
    _write_jsonl_atomic(work.facts, facts)
    sentence = marker + claim + f" [source](https://example.test/999mw){spacing}(F001)."
    work.report_md.write_text(sentence + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
    review(work, sentence)
    checked = verifier.verify(work.report_md, work, check_only=True)
    assert checked["ok"] == ok, checked
    if not ok:
        assert any("[미확정]" in item for item in checked["failures"]), checked
    assert not any("999" in item for item in checked["failures"] + checked["warnings"]), checked


def test_r1_unknown_tag_after_link():
    failures, _ = verifier.check_bound_numbers("Claim [source](https://example.test/999mw)(F999).", {})
    assert any("[오태그]" in item for item in failures)


def test_r4_parenthesized_url_numbers_not_body_claims(work):
    # R4: URL 경로의 균형 괄호 안 숫자(999MW)가 본문 수치로 오검출되면 안 된다.
    # 동시에 URL 이 뒤따르는 F태그 괄호를 삼켜 R1 차단이 풀려도 안 된다.
    sentence = "Source claims 45 USD(F001) [source](https://example.test/source_(999MW))."
    work.report_md.write_text(sentence + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
    review(work, sentence)
    checked = verifier.verify(work.report_md, work, check_only=True)
    assert checked["ok"], checked
    assert not any("999" in item for item in checked["failures"] + checked["warnings"]), checked
    # URL 정규식 단위 대조: 태그 모양 괄호는 URL 에 흡수되지 않는다
    assert "(F001)" in verifier._URL.sub(" ", "See https://example.test/source(F001).")


def appendix_setup(work, sentence):
    facts, evidence = FactsDB(work).facts(), FactsDB(work).evidence()
    fact = fact_record()
    fact.update(id="F002", status="disputed", evidence_ids=["E002"])
    ev = copy.deepcopy(evidence[0])
    ev.update(id="E002", fact_id="F002")
    _write_jsonl_atomic(work.facts, facts + [fact])
    _write_jsonl_atomic(work.evidence, evidence + [ev])
    (work.audit / "research-plan.md").write_text("# 부 1. 본론\n# 부 11. 부록\n", encoding="utf-8")
    work.report_md.write_text("# 본론\n\n" + LIMITED + "\n\n![증빙](_captures/E001.png)\n"
                             "\n<!-- FACTSHEET:APPENDIX -->\n# 부 11. 부록\n\n" + sentence + "\n",
                             encoding="utf-8")
    return review(work)


@pytest.mark.parametrize("sentence", ["[상충] Source claims 45 USD(F002).",
    "[상충] Certification remains disputed [source](https://example.test/source)(F002).",
    "| [상충] | Source claims 45 USD | (F002) |"])
def test_r2_appendix_review_required_and_bound(work, sentence):
    body_row = appendix_setup(work, sentence)
    checked = verifier.verify(work.report_md, work, check_only=True)
    assert not checked["ok"] and any("검토 누락" in item for item in checked["failures"]), checked
    appendix_row = review(work, sentence)
    appendix_row.update(sentence_id="S002", fact_ids=["F002"], evidence_ids=["E002"])
    rows = [body_row, appendix_row]
    _write_jsonl_atomic(work.audit / "claim-review.jsonl", rows)
    assert verifier.verify(work.report_md, work, check_only=True)["ok"]
    text = work.report_md.read_text(encoding="utf-8")
    work.report_md.write_text(text.replace(sentence, sentence.replace("claims", "asserts")
                                          .replace("remains", "is")), encoding="utf-8")
    checked = claims.verify(work.report_md, work, check_only=True)
    assert not checked["ok"] and any("검토 누락" in item for item in checked["failures"]), checked
    work.report_md.write_text(text, encoding="utf-8")
    for field in ("reviewed_text_sha256", "evidence_revision"):
        bad_rows = copy.deepcopy(rows)
        bad_rows[1][field] = "0" * 64
        _write_jsonl_atomic(work.audit / "claim-review.jsonl", bad_rows)
        checked = claims.verify(work.report_md, work, check_only=True)
        assert not checked["ok"] and any(field + " 불일치" in item for item in checked["failures"]), checked
    _write_jsonl_atomic(work.audit / "claim-review.jsonl", rows)
    facts = FactsDB(work).facts()
    facts[1]["context"]["entity"] = "Different entity"
    facts[1]["claim_key"] = make_claim_key(facts[1]["context"])
    _write_jsonl_atomic(work.facts, facts)
    checked = claims.verify(work.report_md, work, check_only=True)
    assert not checked["ok"] and any("evidence_revision 불일치" in item for item in checked["failures"])


def test_r2_appendix_partial_sentence_rejected(work):
    sentence = "[상충] Source claims 45 USD(F002)."
    body_row = appendix_setup(work, sentence)
    appendix_row = review(work, "45 USD(F002).")
    appendix_row.update(sentence_id="S002", fact_ids=["F002"], evidence_ids=["E002"])
    _write_jsonl_atomic(work.audit / "claim-review.jsonl", [body_row, appendix_row])
    assert not claims.verify(work.report_md, work, check_only=True)["ok"]


RANGES = [
    (".5~.6", "0.5~0.6", "-.5~-.6", ["0.5", "0.6"]),
    ("1e3~2e3", "1000~2000", "-1e3~-2e3", ["1000", "2000"]),
    ("1e-3~2e-3", "0.001~0.002", "-1e-3~-2e-3", ["0.001", "0.002"]),
    ("+1E+3~+2E+3", "1000~2000", "-1E+3~-2E+3", ["1000", "2000"]),
    ("40-45", "40~45", "-40~-45", ["40", "45"]),
    ("-45~-40", "-45--40", "45~40", ["-45", "-40"]),
    ("-.6~-.5", "-0.6~-0.5", ".6~.5", ["-0.6", "-0.5"]),
    ("-2e-3~-1e-3", "-0.002~-0.001", "2e-3~1e-3", ["-0.002", "-0.001"]),
]


@pytest.mark.parametrize("raw,equivalent,wrong_sign,expected", RANGES)
def test_r3_decimal_range_comparison_and_core_capture(work, raw, equivalent, wrong_sign, expected):
    assert verifier._vals(raw) == list(map(Decimal, expected))
    facts, evidence = FactsDB(work).facts(), FactsDB(work).evidence()
    facts[0]["value"] = {"raw": raw, "unit": "USD"}
    _write_jsonl_atomic(work.facts, facts)
    for value, ok in ((raw, True), (equivalent, True), ("9~10", False), (wrong_sign, False)):
        sentence = f"Range {value} USD(F001)."
        work.report_md.write_text(sentence + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
        review(work, sentence)
        checked = verifier.verify(work.report_md, work, check_only=True)
        assert checked["ok"] == ok, checked
        if not ok:
            assert any("[값불일치]" in item for item in checked["failures"]), checked
        assert not any("[값미대조]" in item for item in checked["warnings"]), checked
        failures, warnings = verifier.check_bound_numbers(f"USD {value}(F001)", {"F001": facts[0]})
        assert bool(failures) != ok and not warnings, (failures, warnings)
    evidence[0].pop("capture")
    failures, _ = verifier.check_evidence_chain({"F001": facts[0]}, {"E001": evidence[0]}, work, {"F001"})
    assert any("핵심수치 F001 source_capture 없음" in item for item in failures), failures
