"""배치 2B: 리뷰 공격 재현과 정상 대조군. 외부 통신 없이 실제 대장·CLI를 검사한다."""
import copy
import sys
from decimal import Decimal
from pathlib import Path

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import capture_pdf
import gates
import manifest
import verify_facts as verifier
from facts_db import (FactsDB, ValidationError, _write_jsonl_atomic, confirmed_digest,
                      diff_facts, make_claim_key, validate_evidence, validate_fact)
from test_p0_regressions import work, cli, review, start_chain, to_final


def fact_record(version=4):
    fact = {"id": "F001", "schema_version": version, "claim_type": "observed",
            "claim": "원문 값", "context": {"metric": "revenue", "entity": "Acme",
            "geography": "GL", "period": "2026", "entity_id": "acme", "definition": "연결 매출"},
            "value": {"raw": "45", "unit": "USD"}, "risk": "normal", "status": "pending",
            "grade": {key: "A" for key in ("authority", "independence", "directness", "recency")},
            "evidence_ids": [], "verify_events": []}
    fact["claim_key"] = make_claim_key(fact["context"])
    return fact


def evidence_record(eid="E001", group="A", role="원출처", version=4):
    return {"id": eid, "schema_version": version, "fact_id": "F001", "type": "text_quote",
            "source_url": f"https://example.test/{eid}", "sha256": gates.sha256_text(eid),
            "accessed_at": "2026-09-05T10:00:00+09:00", "verbatim": f"45 USD {eid}",
            "source_role": role, "observer_group": group}


def ledger_check(work, fact, evidence=(), used=None):
    return verifier.check_ledger_integrity({fact["id"]: fact}, {fact["id"]} if used is None else used,
                                            [fact], list(evidence), work)


@pytest.mark.parametrize("raw,expected", [("-45", ["-45"]), ("-45~-40", ["-45", "-40"]),
    ("45", ["45"]), ("40-45", ["40", "45"]), ("-45--40", ["-45", "-40"]),
    ("−45–−40", ["-45", "-40"]), ("-45±2", ["-47", "-43"]),
    ("+1,200.5", ["1200.5"]), ("-45~40", ["-45", "40"])])
def test_n07_signed_scalar_range_and_uncertainty(raw, expected):
    assert verifier._vals(raw) == list(map(Decimal, expected))
    fact = {"status": "confirmed", "value": {"raw": raw, "unit": "USD"}}
    assert verifier.check_bound_numbers(f"損益 {raw} USD(F001).", {"F001": fact}) == ([], [])


@pytest.mark.parametrize("raw,body", [("-45", "45 USD"), ("45", "-45 USD"),
    ("-45~-40", "45~40 USD"), ("45", "$-45"), ("45", "-$45"), ("-45", "USD 45")])
def test_n07_sign_mismatch_fails(raw, body):
    fact = {"status": "confirmed", "value": {"raw": raw, "unit": "USD"}}
    failures, _ = verifier.check_bound_numbers(body + "(F001).", {"F001": fact})
    assert any("값불일치" in issue for issue in failures)


@pytest.mark.parametrize("unit,power", [("µW", -6), ("uW", -6), ("μW", -6), ("mW", -3),
    ("W", 0), ("kW", 3), ("MW", 6), ("GW", 9), ("TWh", 12), ("µWh", -6),
    ("uWh", -6), ("mWh", -3), ("Wh", 0), ("kWh", 3), ("MWh", 6), ("GWh", 9)])
def test_n08_si_prefixes_detect_values_and_keep_scale(unit, power):
    assert verifier._resolve_unit(unit) == ("WH" if unit.endswith("Wh") else "W", Decimal(10) ** power)
    fact = {"status": "confirmed", "value": {"raw": "45", "unit": unit}}
    assert verifier.check_bound_numbers(f"45 {unit}(F001).", {"F001": fact}) == ([], [])
    failures, _ = verifier.check_bound_numbers(f"999 {unit}(F001).", {"F001": fact})
    assert any("값불일치" in issue for issue in failures)


@pytest.mark.parametrize("left,right", [("mW", "MW"), ("mWh", "MWh"), ("µW", "mW"), ("W", "Wh")])
def test_n08_unit_mismatch_fails(left, right):
    fact = {"status": "confirmed", "value": {"raw": "45", "unit": left}}
    assert verifier.check_bound_numbers(f"45 {right}(F001)", {"F001": fact})[0]


@pytest.mark.parametrize("raw,unit,body", [("45", "usd", "45 UsD"),
    ("4.5", "USD billion", "us$4.5B"), ("40-45", "EUR", "EUR 40~45"),
    ("300.9", "KRW_T", "300.9조원"), ("45", "MW (PEM portion)", "45 MW"),
    ("1000", "uW", "1 mW"), ("45", "건", "45건"), ("45", "Mt", "45 Mt"),
    ("-45", "USD", "-$45"), ("-45", "USD", "$-45"), ("-45", "USD", "−USD 45"),
    (".5", "USD", "0.5 USD"), ("4.5E+9", "USD", "USD 4.5 billion")])
def test_n07_n08_currency_existing_units_and_equivalence(raw, unit, body):
    fact = {"status": "confirmed", "value": {"raw": raw, "unit": unit}}
    assert verifier.check_bound_numbers(body + "(F001)", {"F001": fact}) == ([], [])


@pytest.mark.parametrize("path,value", [("claim", 42), ("claim", "  "), ("context", []),
    ("context.entity", 123), ("context.period", False), ("context.definition", "  "),
    ("value.base_value", True), ("value.base_value", float("nan")), ("value.raw", ""),
    ("independent_groups", "AB"), ("independent_groups", ["A", 2]),
    ("independent_groups", ["A", " "]), ("evidence_ids", [1]), ("evidence_ids", "E001"),
    ("verify_events", ["lead"]), ("verify_events", [{"by": "lead", "action": "read"}]),
    ("verify_events", [{"by": "lead", "action": "read", "at": "not-a-date"}]),
    ("verify_events", [{"by": " ", "action": "read", "at": "2026-09-05T10:00:00"}]),
    ("counter_search", {"query": " ", "result": "없음", "found_stronger_refutation": False}),
    ("counter_search", {"query": "q", "result": "없음", "found_stronger_refutation": "false"}),
    ("valid_at", "2026-02-30"), ("observed_at", "not-a-date")])
def test_n09_v4_types_items_events_and_empty_values(path, value):
    fact = fact_record()
    keys = path.split(".")
    target = fact if len(keys) == 1 else fact[keys[0]]
    target[keys[-1]] = value
    if isinstance(fact["context"], dict):
        fact["claim_key"] = make_claim_key(fact["context"])
    with pytest.raises(ValidationError):
        validate_fact(fact)


@pytest.mark.parametrize("field,value", [("http_status", True), ("locator", []),
    ("source_url", " "), ("accessed_at", "2026-13-01"), ("observer_group", 3)])
def test_n09_v4_evidence_types(field, value):
    ev = evidence_record()
    ev[field] = value
    with pytest.raises(ValidationError):
        validate_evidence(ev)


@pytest.mark.parametrize("time", ["2026", "2026-09", "2026-09-05", "2026-09-05T12:00:00Z",
                                  "2026-09-05T12:00:00.123+09:00"])
def test_n09_valid_dates_and_nullable_fields(time):
    fact = fact_record()
    fact.update(valid_at=time, observed_at=None, independent_groups=[],
                counter_search=None, verify_events=[{"by": "lead", "action": "read",
                                    "at": "2026-09-05T12:00:00Z", "note": ""}])
    validate_fact(fact)
    validate_evidence(evidence_record())


@pytest.mark.parametrize("field,value", [("claim", 42), ("independent_groups", "AB"),
    ("verify_events", [{"by": "lead", "action": "read", "at": "bad"}]), ("valid_at", "bad")])
def test_n09_v3_new_schema_violations_warn(work, field, value):
    fact = fact_record(3)
    fact[field] = value
    failures, warnings = ledger_check(work, fact)
    assert not failures and any("legacy스키마" in issue for issue in warnings)


@pytest.mark.parametrize("kind,field,value", [("fact", "claim_key", []), ("fact", "id", []),
    ("fact", "context", [1]), ("fact", "value", [1]), ("fact", "evidence_ids", [1]),
    ("fact", "verify_events", [1]), ("evidence", "fact_id", []), ("evidence", "id", [])])
def test_n09_g3_returns_failure_for_wrong_types_instead_of_crashing(work, kind, field, value):
    path = work.facts if kind == "fact" else work.evidence
    rows = FactsDB(work).facts() if kind == "fact" else FactsDB(work).evidence()
    rows[0][field] = value
    _write_jsonl_atomic(path, rows)
    checked = verifier.verify(work.report_md, work)
    assert not checked["ok"] and any("타입 오류" in issue for issue in checked["failures"])


@pytest.mark.parametrize("field", ["context", "value", "grade"])
def test_n09_v3_nested_type_warn_does_not_skip_confirmation_rules(work, field):
    facts, evidence = FactsDB(work).facts(), FactsDB(work).evidence()
    facts[0]["schema_version"] = evidence[0]["schema_version"] = 3
    facts[0][field] = ["legacy 잘못된 타입"]
    _write_jsonl_atomic(work.facts, facts)
    _write_jsonl_atomic(work.evidence, evidence)
    checked = verifier.verify(work.report_md, work)
    assert checked["ok"] and any("legacy스키마" in issue for issue in checked["warnings"]), checked
    facts[0]["evidence_ids"] = []
    with pytest.raises(ValidationError, match="evidence_ids"):
        validate_fact(facts[0])


@pytest.mark.parametrize("version", [3, 4])
@pytest.mark.parametrize("mode", ["foreign", "orphan", "reverse_missing", "missing_evidence"])
def test_n10_bidirectional_links_for_pending_records(work, version, mode):
    fact, ev = fact_record(version), evidence_record(version=version)
    fact["evidence_ids"] = ["E001"]
    evidence = [ev]
    if mode in ("foreign", "orphan"):
        ev["fact_id"] = "F999"
    if mode in ("orphan", "reverse_missing"):
        fact["evidence_ids"] = []
    if mode == "missing_evidence":
        evidence = []
    failures, warnings = ledger_check(work, fact, evidence)
    assert bool(failures) == (version == 4)
    assert any("증거역참조" in issue or "증거유실" in issue
               for issue in (failures if version == 4 else warnings))
    ev["fact_id"] = "F001"
    fact["evidence_ids"] = ["E001"]
    assert not ledger_check(work, fact, [ev])[0]


@pytest.mark.parametrize("field,left,right", [("entity", "A|B", "A/B"),
    ("entity_id", "corp-a", "corp-b"), ("definition", "연결", "별도"),
    ("scenario", None, "na"), ("entity", "A", " A")])
def test_n11_lossless_identity_key(field, left, right):
    context = fact_record()["context"]
    assert make_claim_key({**context, field: left}) != make_claim_key({**context, field: right})
    assert make_claim_key(context) == make_claim_key(dict(reversed(list(context.items()))))


def test_n11_add_recomputes_key_and_keeps_v3_history(work):
    db = FactsDB(work)
    fact = fact_record()
    fact["id"] = "F002"
    fact["claim_key"] = "forged"
    before = work.facts.read_bytes()
    with pytest.raises(ValidationError, match="재계산"):
        db.add_fact(fact)
    assert work.facts.read_bytes() == before
    fact["claim_key"] = make_claim_key(fact["context"])
    db.add_fact(fact)
    duplicate = copy.deepcopy(fact)
    duplicate["id"] = "F003"
    with pytest.raises(ValidationError, match="add_evidence") as error:
        db.add_fact(duplicate)
    assert "merge_evidence" not in str(error.value)
    legacy = fact_record(3)
    legacy.update(id="F003", claim_key="old|opaque|key")
    assert db.add_fact(legacy)["claim_key"] == "old|opaque|key"


@pytest.mark.parametrize("side", ["old", "new"])
def test_n11_diff_rejects_duplicate_keys_and_reports_changes(tmp_path, side):
    old, new = tmp_path / "old.jsonl", tmp_path / "new.jsonl"
    fact = fact_record()
    changed = copy.deepcopy(fact)
    changed["value"]["raw"] = "46"
    _write_jsonl_atomic(old, [fact])
    _write_jsonl_atomic(new, [changed])
    assert len(diff_facts(old, new)["value_changed"]) == 1
    _write_jsonl_atomic(old if side == "old" else new, [fact, {**fact, "id": "F002"}])
    with pytest.raises(ValidationError, match="중복 claim_key"):
        diff_facts(old, new)


def high_risk(version=4):
    fact = fact_record(version)
    evidence = [evidence_record(version=version), evidence_record("E002", "B", version=version)]
    fact.update(status="confirmed", risk="high", evidence_ids=["E001", "E002"],
                verify_events=[{"by": "lead", "action": "reread", "at": "2026-09-05T10:00:00",
                                "reread_sha256": evidence[0]["sha256"]}], independent_groups=["A", "B"],
                counter_search={"query": "Acme 매출 정정", "result": "없음", "found_stronger_refutation": False},
                primary_source_ref="E001", valid_at="2026-09")
    return fact, evidence


@pytest.mark.parametrize("mode", ["one_source", "reprint", "same_group", "same_url", "same_hash",
    "blank_query", "blank_result", "missing_result", "no_refutation_record", "missing_primary",
    "foreign_primary", "missing_time", "bad_time", "one_bad_time"])
def test_k06_v4_required_conditions_and_independence_join(work, mode):
    fact, evidence = high_risk()
    assert not ledger_check(work, fact, evidence)[0]
    if mode == "one_source":
        fact["evidence_ids"] = ["E001"]
        evidence = evidence[:1]
    if mode == "reprint": evidence[1]["source_role"] = "재인용"
    if mode == "same_group": evidence[1]["observer_group"] = "A"
    if mode == "same_url": evidence[1]["source_url"] = evidence[0]["source_url"] + "#fragment"
    if mode == "same_hash": evidence[1]["sha256"] = evidence[0]["sha256"]
    if mode == "blank_query": fact["counter_search"]["query"] = "  "
    if mode == "blank_result": fact["counter_search"]["result"] = "  "
    if mode == "missing_result": del fact["counter_search"]["result"]
    if mode == "no_refutation_record": del fact["counter_search"]["found_stronger_refutation"]
    if mode == "missing_primary": fact["primary_source_ref"] = "E999"
    if mode == "foreign_primary": evidence[0]["fact_id"] = "F999"
    if mode == "missing_time": del fact["valid_at"]
    if mode == "bad_time": fact["valid_at"] = "not-a-date"
    if mode == "one_bad_time": fact.update(observed_at="2026-09-05", valid_at="bad")
    assert ledger_check(work, fact, evidence)[0]


def test_k06_v3_existing_strength_and_v4_unused_warn(work):
    fact, evidence = high_risk(3)
    fact.update(primary_source_ref="E999", valid_at="bad")
    failures, warnings = ledger_check(work, fact, evidence[:1])
    assert not failures and any("기본소스" in issue for issue in warnings)
    fact["independent_groups"] = "AB"
    fact["counter_search"]["query"] = " "
    failures, _ = ledger_check(work, fact, evidence)
    assert any("독립 관찰그룹" in issue and "반박검색" in issue for issue in failures)
    fact, evidence = high_risk()
    fact.update(primary_source_ref=None, valid_at=None)
    failures, warnings = ledger_check(work, fact, evidence, used=set())
    assert not failures and any("반박게이트" in issue for issue in warnings)


@pytest.mark.parametrize("metric", ["market_size", "market size", "CAGR", "growth_rate",
    "deal_size", "rank", "시장규모", "시장 규모", "성장률", "딜규모", "순위"])
def test_k06_untagged_risk_surfaces_without_promotion(work, metric):
    fact = fact_record()
    fact["context"]["metric"] = metric
    fact["claim_key"] = make_claim_key(fact["context"])
    failures, warnings = ledger_check(work, fact)
    assert not failures and any("risk태깅" in issue for issue in warnings)
    assert fact["risk"] == "normal"


@pytest.mark.parametrize("heading", ["Executive conclusions", "결론", "요약", "승인 본문 장", "새로운 장"])
def test_n18_early_appendix_marker_blocks_body_and_unknown_chapters(work, heading):
    plan = "# 부 1. 승인 본문 장\n# 부 11. 부록\n## 환산근거\n"
    (work.audit / "research-plan.md").write_text(plan, encoding="utf-8")
    before = work.report_md.read_text(encoding="utf-8")
    text = before + f"\n<!-- FACTSHEET:APPENDIX -->\n## 부록\n# {heading}\nMarket 999 USD.\n"
    work.report_md.write_text(text, encoding="utf-8")
    assert any("부록경계" in issue for issue in verifier.verify(work.report_md, work)["failures"])


def test_n18_valid_appendix_keeps_untagged_warning(work):
    (work.audit / "research-plan.md").write_text("# 부 1. 본론\n# 부 11. 부록\n## 환산근거\n", encoding="utf-8")
    text = "# 본론\n\n" + work.report_md.read_text(encoding="utf-8")
    text += "\n<!-- FACTSHEET:APPENDIX -->\n# 부 11. 부록\n\n## 환산근거\n환율 1,350원/달러.\n"
    work.report_md.write_text(text, encoding="utf-8")
    checked = verifier.verify(work.report_md, work)
    assert checked["ok"], checked
    assert any("부록무태그" in issue for issue in checked["warnings"])
    text = text.replace("<!-- FACTSHEET:APPENDIX -->\n", "<!-- FACTSHEET:APPENDIX -->\nMarket 999 USD.\n")
    assert verifier.check_appendix_boundary(text, work)[0]


def test_n18_no_plan_still_blocks_review_reproduction(work):
    text = "# Title\n\n![capture](_captures/E001.png)\n<!-- FACTSHEET:APPENDIX -->\n# Executive conclusions\nMarket 999 USD."
    work.report_md.write_text(text, encoding="utf-8")
    assert any("부록경계" in issue for issue in verifier.verify(work.report_md, work)["failures"])


@pytest.mark.parametrize("marker", ["[상충] ", "| [상충] | ", "- [상충] "])
def test_n19_disputed_explicit_context_only(marker):
    fact = {"status": "disputed", "value": {"raw": "45", "unit": "USD"}}
    facts = {"F001": fact}
    assert verifier.check_bound_numbers(marker + "45 USD(F001)", facts) == ([], [])
    assert verifier.check_bound_numbers("45 USD(F001)", facts)[0]
    assert verifier.check_bound_numbers(marker + "999 USD(F001)", facts)[0]
    assert verifier.check_bound_numbers(marker + "45 MW(F001)", facts)[0]
    assert verifier.check_bound_numbers("# [상충]\n45 USD(F001)", facts)[0]
    assert verifier.check_bound_numbers("[상충] 별도 주장. 45 USD(F001)", facts)[0]
    assert verifier.check_bound_numbers("- [상충] 45 USD(F001)\n- 일반 주장 45 USD(F001)", facts)[0]
    assert verifier.check_bound_numbers(marker + "45 USD(F999)", facts)[0]


@pytest.mark.parametrize("mode", ["valid", "missing_evidence", "foreign_evidence", "source_missing",
                                   "bad_hash", "capture_replaced", "no_marker"])
def test_n19_disputed_provenance_still_required(work, mode):
    facts, evidence = FactsDB(work).facts(), FactsDB(work).evidence()
    facts[0].update(status="disputed", value={"raw": "45", "unit": "USD"})
    if mode == "missing_evidence": facts[0]["evidence_ids"] = []
    if mode == "foreign_evidence": evidence[0]["fact_id"] = "F999"
    if mode == "source_missing": evidence[0]["source_url"] = " "
    if mode == "bad_hash": evidence[0]["sha256"] = "bad"
    if mode == "capture_replaced": (work.captures / "E001.png").write_bytes(b"bad")
    _write_jsonl_atomic(work.facts, facts)
    _write_jsonl_atomic(work.evidence, evidence)
    sentence = ("" if mode == "no_marker" else "[상충] ") + "자료가 제시한 값은 45 USD(F001)."
    work.report_md.write_text(sentence + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
    review(work, sentence)
    checked = verifier.verify(work.report_md, work)
    assert checked["ok"] == (mode == "valid"), checked


def test_n19_disputed_context_change_requires_fresh_review(work):
    facts = FactsDB(work).facts()
    facts[0]["status"] = "disputed"
    _write_jsonl_atomic(work.facts, facts)
    sentence = "[상충] 자료에 인증 및 노선 적용이 기재되었으나 적용 범위는 상충한다(F001)."
    work.report_md.write_text(sentence + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
    review(work, sentence)
    assert verifier.verify(work.report_md, work)["ok"]
    facts[0]["context"]["entity"] = "다른 기업"
    facts[0]["claim_key"] = make_claim_key(facts[0]["context"])
    _write_jsonl_atomic(work.facts, facts)
    checked = verifier.verify(work.report_md, work)
    assert any("evidence_revision 불일치" in issue for issue in checked["failures"])
    review(work, sentence)
    assert verifier.verify(work.report_md, work)["ok"]


def test_n19_appendix_disputed_citation_requires_evidence(work):
    fact = fact_record()
    fact.update(id="F002", status="disputed", evidence_ids=[])
    facts = FactsDB(work).facts() + [fact]
    _write_jsonl_atomic(work.facts, facts)
    with work.report_md.open("a", encoding="utf-8") as report:
        report.write("\n<!-- FACTSHEET:APPENDIX -->\n## 부록\n\n[상충] 45 USD(F002).\n")
    review(work)
    checked = verifier.verify(work.report_md, work)
    assert any("상충 인용 F002 evidence_ids 없음" in issue for issue in checked["failures"])


def test_n04_failed_ancestor_and_changed_plan_cannot_repass_g5(work):
    start_chain(work)
    to_final(work)
    gates.record_script_result(work, "G1", 1, "수집 재시도 실패")
    assert not gates.check_current_receipt(work, "G5")["ok"]
    (work.audit / "research-plan.md").write_text("# 승인 계획 변경\n", encoding="utf-8")
    assert not manifest.finalize_report(work)["ok"]
    assert cli("manifest.py", "verify", work.root).returncode == 1
    assert not gates.successful_receipt(work, "G5")


@pytest.mark.parametrize("field", ["claim", "entity", "entity_id", "period", "definition"])
def test_n05_reviewed_claim_or_context_change_invalidates_receipt(work, field):
    start_chain(work)
    facts = FactsDB(work).facts()
    before = confirmed_digest(facts)
    (facts[0] if field == "claim" else facts[0]["context"])[field] = "Beta 2035 전망"
    facts[0]["claim_key"] = make_claim_key(facts[0]["context"])
    _write_jsonl_atomic(work.facts, facts)
    assert confirmed_digest(facts) != before
    assert not gates.check_current_receipt(work, "[2]")["ok"]
    assert cli("verify_facts.py", work.report_md, work.root).returncode == 1
    assert not gates.successful_receipt(work, "G3")


def test_n13_failed_capture_retry_invalidates_old_png_and_cli(work):
    pdf = work.sources / "input.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 100), "Revenue 45 USD.")
        doc.save(pdf)
    target = work.captures / "E001.png"
    assert capture_pdf.capture_number(pdf, "45", target)["ok"]
    assert target.is_file()
    result = cli("capture_pdf.py", pdf, "999", target)
    assert result.returncode == 1, result.stdout
    assert not target.exists()
    assert target.with_name("E001.FAILED.png").is_file()
    facts = FactsDB(work).facts()
    facts[0]["value"] = {"raw": "45", "unit": "USD"}
    failures, _ = verifier.check_evidence_chain({"F001": facts[0]},
                                              {"E001": FactsDB(work).evidence()[0]}, work, {"F001"})
    assert any("증빙유실" in issue for issue in failures)
    assert capture_pdf.capture_number(pdf, "45", target)["ok"] and target.is_file()
