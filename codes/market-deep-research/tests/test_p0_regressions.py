"""P0 회귀: 합성 근거의 의미 확장·캡처 검토·CAGR·영수증 재발급과 최종 출고.

기존 테스트는 standalone main/@case 방식이라 pytest가 수집하지 않는다.
기존 함수들을 그대로 호출해 필수 pytest 명령이 기존+신규 전체를 실제로 실행하게 한다.
"""
import copy
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gates
import manifest
import render_pdf
import verify_calculations as calculations
import verify_claims as claims
import verify_facts
from facts_db import (FactsDB, ValidationError, _write_jsonl_atomic, confirmed_digest,
                      validate_evidence, validate_fact)
from skill_paths import WorkPaths, resolve_work_dir
import test_adversarial
import test_e2e

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
LIMITED = "센서의 인증과 노선 적용은 확인되며, 무전원 적용 여부는 미확인이다(F001)."
EXPANDED = "배터리 없는 센서가 상용 노선에 적용되었다[F001]."


def cli(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def capture(path, text="Certification and deployment. Energy source unknown."):
    with fitz.open() as doc:
        page = doc.new_page(width=480, height=180)
        page.insert_text((24, 55), text, fontsize=12)
        page.draw_rect(fitz.Rect(20, 25, 460, 140), color=(0.1, 0.3, 0.6))
        page.get_pixmap().save(path)


def capture_review(path, state="content"):
    return {"image_sha256": gates.sha256_file(path), "reviewed_by": "lead",
            "reviewed_at": "2026-01-01T12:00:00", "page_state": state,
            "claim_visible": state == "content", "context_visible": state == "content",
            "verdict": "accept" if state == "content" else "reject"}


def review(wp, sentence=LIMITED, support="supported", kind="observed"):
    row = {"sentence_id": "S001", "claim_type": kind, "fact_ids": ["F001"],
           "evidence_ids": ["E001"], "support": support,
           "unsupported_terms": [] if support == "supported" else ["배터리 없는"],
           "required_qualification": "무전원 여부 미확인", "sentence_text": sentence,
           "reviewed_text_sha256": gates.sha256_text(sentence),
           "evidence_revision": confirmed_digest(FactsDB(wp).facts())}
    _write_jsonl_atomic(wp.audit / "claim-review.jsonl", [row])
    return row


@pytest.fixture
def work(tmp_path):
    wp = WorkPaths(resolve_work_dir("합성 센서", base=tmp_path))
    db = FactsDB(wp)
    cap = wp.captures / "E001.png"
    capture(cap)
    fact = db.add_fact({"schema_version": 4, "claim_type": "observed",
        "claim": "인증 및 노선 적용, 에너지원 미확인", "risk": "normal", "status": "pending",
        "context": {"metric": "certification", "entity": "가상 센서사", "geography": "TEST",
                    "period": "2026"}, "value": {"raw": "인증", "unit": "text"},
        "grade": {k: "A" for k in ("authority", "independence", "directness", "recency")}})
    quote = "Certification and deployment. Energy source unknown."
    db.add_evidence({"schema_version": 4, "fact_id": fact["id"], "type": "text_quote",
        "source_url": "https://example.test/source", "sha256": gates.sha256_text(quote),
        "verbatim": quote, "capture": "_captures/E001.png", "capture_review": capture_review(cap)})
    db.add_verify_event("F001", "lead", "reread", reread_sha256=gates.sha256_text(quote))
    db.set_status("F001", "confirmed")
    wp.report_md.write_text(LIMITED + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
    (wp.audit / "research-plan.md").write_text("# 조사 승인\n", encoding="utf-8")
    review(wp)
    return wp


def start_chain(wp):
    gates.record_manual(wp, "G0", "계획 확인")
    gates.record_script_result(wp, "G1", 0, "join")
    return gates.record_manual(wp, "[2]", "전건 재열람", refs=["facts.jsonl"])


def to_final(wp):
    checked = cli("verify_facts.py", wp.report_md, wp.root)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    rendered = cli("render_pdf.py", wp.report_md)
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    gates.record_manual(wp, "G4", "합성 보고서 preview 확인", refs=["report.pdf"])
    checked = cli("manifest.py", "verify", wp.root)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    receipts = [gates.require_receipt(wp, gate) for gate in ("G3", "[4b]", "G4", "G5")]
    assert len({r["revision_id"] for r in receipts}) == 1
    return receipts


def test_t01_meaning_expansion_blocks_g3(work):
    work.report_md.write_text(EXPANDED + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
    review(work, EXPANDED, "partial")
    checked = verify_facts.verify(work.report_md, work)
    assert not checked["ok"] and any("partial" in f for f in checked["failures"])
    start_chain(work)
    assert cli("verify_facts.py", work.report_md, work.root).returncode == 1
    assert not gates.successful_receipt(work, "G3")


def test_t02_limited_sentence_passes(work):
    assert claims.verify(work.report_md, work)["ok"]
    assert verify_facts.verify(work.report_md, work)["ok"]


@pytest.mark.parametrize("state", ["blocked", "login", "blank", "unknown"])
def test_t03_ineligible_capture_is_not_refutation(work, state):
    cap = work.captures / "E001.png"
    capture(cap, "Security check. Please sign in." if state != "blank" else "")
    db = FactsDB(work)
    evidence = db.evidence()
    evidence[0]["capture_review"] = capture_review(cap, state)
    _write_jsonl_atomic(work.evidence, evidence)
    assert not verify_facts.inspect_capture(evidence[0], work)["valid"]
    checked = verify_facts.verify(work.report_md, work)
    assert not checked["ok"] and any("유효 source_capture 0건" in x for x in checked["failures"])
    assert db.facts()[0]["status"] == "confirmed"  # 원본 상태/수치를 자동 변경하지 않는다.


def test_t04_capture_replacement_requires_review(work):
    capture(work.captures / "E001.png", "A different source image.")
    checked = verify_facts.verify(work.report_md, work)
    assert not checked["ok"] and any("image_sha256 불일치" in x for x in checked["failures"])


def market_fact():
    return {"id": "F001", "schema_version": 4, "risk": "high", "status": "confirmed",
            "value": {"raw": "4.5 -> 12.8 / 17.8%", "unit": "USD_B", "base_value": "4.5",
                      "forecast_value": "12.8", "base_year": 2025, "forecast_year": 2035,
                      "reported_cagr": "17.8", "cagr_start_year": 2025, "cagr_end_year": 2035}}


def test_t05_cagr_conflict_is_read_only_and_blocks_confirmation(work):
    db = FactsDB(work)
    facts = db.facts()
    facts[0].update(value=market_fact()["value"])
    _write_jsonl_atomic(work.facts, facts)
    before = work.facts.read_bytes()
    checked = calculations.verify(work)
    assert not checked["ok"] and checked["results"][0]["status"] == "CONFLICT"
    assert Decimal("11.01") < Decimal(checked["results"][0]["calculated_cagr"]) < Decimal("11.03")
    assert cli("verify_calculations.py", work.root).returncode == 1
    assert work.facts.read_bytes() == before
    with pytest.raises(ValidationError, match="CAGR"):
        db.set_status("F001", "confirmed")
    assert not verify_facts.verify(work.report_md, work)["ok"]
    facts[0]["status"] = "disputed"
    _write_jsonl_atomic(work.facts, facts)
    checked = calculations.verify(work)
    assert checked["ok"] and checked["results"][0]["status"] == "CONFLICT"


def test_t06_precision_and_period_are_not_fixed_tolerance():
    fact = market_fact()
    fact["value"]["reported_cagr"] = "11.1"
    assert calculations.check_calculation(fact)["status"] == "MATCH"
    fact["value"].update(base_value="4.500", forecast_value="12.800")
    assert calculations.check_calculation(fact)["status"] == "CONFLICT"
    fact["value"]["cagr_start_year"] = 2026
    result = calculations.check_calculation(fact)
    assert result["status"] == "NOT_CHECKABLE" and result["missing_fields"]
    del fact["value"]["forecast_value"]
    assert "forecast_value" in calculations.check_calculation(fact)["missing_fields"]


def test_t10_reissue_preserves_history_and_completes_new_revision(work):
    old = start_chain(work)
    to_final(work)
    history = gates.ledger_path(work).read_bytes()
    facts = FactsDB(work).facts()
    facts[0]["value"]["raw"] = "인증 및 노선 적용"
    _write_jsonl_atomic(work.facts, facts)
    assert set(("[2]", "G3", "[4b]", "G4", "G5")) <= set(gates.status(work)["rerun_required"])
    assert gates.check_prerequisites(work, "[2]")["ok"]
    assert not gates.check_current_receipt(work, "[2]")["ok"]
    new = gates.record_manual(work, "[2]", "변경 후 재열람", refs=["facts.jsonl"])
    assert new["supersedes_receipt"] == old["receipt_id"]
    assert new["revision_id"] != old["revision_id"]
    assert new["input_digest"] != old["input_digest"]
    assert gates.ledger_path(work).read_bytes().startswith(history)
    assert not claims.verify(work.report_md, work)["ok"]
    review(work)
    to_final(work)  # 기존 PDF가 남은 상태에서 G3 기준선 재작성→재렌더→G5 완주


def test_t10_same_revision_receipt_replacement_invalidates_descendants(work):
    start_chain(work)
    checked = cli("verify_facts.py", work.report_md, work.root)
    assert checked.returncode == 0, checked.stdout
    gates.record_manual(work, "[2]", "동일 근거 재열람", refs=["facts.jsonl"])
    assert not gates.successful_receipt(work, "G3")
    assert cli("verify_facts.py", work.report_md, work.root).returncode == 0


def test_changed_plan_invalidates_final_receipt_without_explicit_refs(work):
    start_chain(work)
    to_final(work)
    (work.audit / "research-plan.md").write_text("# 계획 변경\n", encoding="utf-8")
    assert not gates.successful_receipt(work, "G5")
    assert not manifest.finalize_report(work)["ok"]


def test_t11_direct_render_is_draft_only(work):
    rendered = render_pdf.render(work.report_md)
    assert rendered["ok"] and rendered["publication_state"] == "초안"
    assert work.report_pdf.is_file()
    manifest.build(work)
    assert manifest.verify(work)["ok"]  # 기존 API는 파일 해시 대조만 담당한다.
    assert not manifest.finalize_report(work)["ok"]
    assert cli("manifest.py", "verify", work.root).returncode == 1
    assert not gates.successful_receipt(work, "G5")


def test_t12_code_identifier_and_supersedes(work, monkeypatch):
    first = start_chain(work)
    assert len(first["code_sha256"]) == 64 and first["run_id"]
    monkeypatch.setattr(gates, "_code_digest", lambda: "f" * 64)
    second = gates.record_manual(work, "[2]", "변경 코드에서 재검증", refs=["facts.jsonl"])
    assert first["code_sha256"] != second["code_sha256"]
    assert second["supersedes_receipt"] == first["receipt_id"]


@pytest.mark.parametrize("mutation", ["missing", "hash", "text", "partial", "revision", "ids", "enum", "substring"])
def test_claim_review_cannot_go_stale_or_omit_records(work, mutation):
    row = review(work)
    if mutation == "missing":
        (work.audit / "claim-review.jsonl").unlink()
    else:
        if mutation == "hash": row["reviewed_text_sha256"] = "0" * 64
        if mutation == "text": work.report_md.write_text(EXPANDED, encoding="utf-8")
        if mutation == "partial": row["support"] = "partial"
        if mutation == "revision": row["evidence_revision"] = "0" * 64
        if mutation == "ids": row["fact_ids"] = []
        if mutation == "enum": row["support"] = "looks-good"
        if mutation == "substring":
            row["sentence_text"] = "미확인이다(F001)."
            row["reviewed_text_sha256"] = gates.sha256_text(row["sentence_text"])
        _write_jsonl_atomic(work.audit / "claim-review.jsonl", [row])
    assert not claims.verify(work.report_md, work)["ok"]


@pytest.mark.parametrize("kind", ["hypothesis", "recommendation"])
def test_conditional_claim_types_follow_support_contract(work, kind):
    for support in ("supported", "partial", "contradicted", "unresolved"):
        review(work, support=support, kind=kind)
        assert claims.verify(work.report_md, work)["ok"]
    review(work, support="unsupported", kind=kind)
    assert not claims.verify(work.report_md, work)["ok"]


def test_claim_softwrap_and_square_tags_preserve_verbatim(work):
    sentence = "센서 인증은\n확인된다. [F001]"
    work.report_md.write_text(sentence, encoding="utf-8")
    review(work, sentence=sentence)
    assert claims.verify(work.report_md, work)["ok"]
    work.report_md.write_text(sentence.replace("\n", " "), encoding="utf-8")
    assert not claims.verify(work.report_md, work)["ok"]


def test_repeated_sentences_need_records_for_each_occurrence(work):
    work.report_md.write_text(LIMITED + "\n\n" + LIMITED, encoding="utf-8")
    first = review(work)
    assert not claims.verify(work.report_md, work)["ok"]
    second = {**first, "sentence_id": "S002"}
    _write_jsonl_atomic(work.audit / "claim-review.jsonl", [first, second])
    assert claims.verify(work.report_md, work)["ok"]


def test_capture_automatic_checks_never_grant_accept(work):
    evidence = FactsDB(work).evidence()[0]
    cap = work.captures / "E001.png"
    with fitz.open() as doc:
        doc.new_page(width=480, height=180).get_pixmap().save(cap)
    evidence.pop("capture_review")
    result = verify_facts.inspect_capture(evidence, work)
    assert not result["valid"] and any("백지 의심" in x for x in result["warnings"])
    cap.write_bytes(b"not an image")
    evidence["capture_review"] = capture_review(cap)
    result = verify_facts.inspect_capture(evidence, work)
    assert not result["valid"] and any("디코딩 실패" in x for x in result["issues"])


def test_legacy_new_checks_warn_without_silently_validating(work):
    db = FactsDB(work)
    facts, evidence = db.facts(), db.evidence()
    for row in [*facts, *evidence]: row.pop("schema_version")
    evidence[0].pop("capture_review")
    _write_jsonl_atomic(work.facts, facts)
    _write_jsonl_atomic(work.evidence, evidence)
    (work.audit / "claim-review.jsonl").unlink()
    checked = verify_facts.verify(work.report_md, work)
    assert checked["ok"] and any("capture_review" in x for x in checked["warnings"])
    assert any("claim-review.jsonl" in x for x in checked["warnings"])
    facts[0]["value"] = market_fact()["value"]
    _write_jsonl_atomic(work.facts, facts)
    checked = calculations.verify(work)
    assert checked["ok"] and checked["results"][0]["status"] == "CONFLICT"


@pytest.mark.parametrize("key,value", [("page_state", "success"), ("claim_visible", "true"),
                                     ("reviewed_by", ""), ("image_sha256", "invalid"),
                                     ("verdict", "PASS")])
def test_v4_nested_capture_fields_are_validated(work, key, value):
    evidence = FactsDB(work).evidence()[0]
    evidence["capture_review"][key] = value
    with pytest.raises(ValidationError): validate_evidence(evidence, work=work)


def test_v4_atomic_fields_and_conditional_requirements(work):
    fact = FactsDB(work).facts()[0]
    unknown = copy.deepcopy(fact)
    unknown["value"]["base_val"] = "4.5"
    with pytest.raises(ValidationError, match="알 수 없는 필드"):
        validate_fact(unknown)
    for bad in (None, 5, True, "4"):
        modified = copy.deepcopy(fact)
        modified["schema_version"] = bad
        with pytest.raises(ValidationError): validate_fact(modified)
    fact["value"]["base_value"] = "NaN"
    with pytest.raises(ValidationError): validate_fact(fact)
    fact["value"].pop("base_value")
    fact.update(risk="high", claim="시장 CAGR 전망")
    with pytest.raises(ValidationError, match="원자화"): validate_fact(fact)
    fact["value"]["reported_cagr"] = "12.3"
    validate_fact(fact)  # 부분 입력은 NOT_CHECKABLE이며 계산 오류로 단정하지 않는다.
    _write_jsonl_atomic(work.facts, [fact])
    checked = calculations.verify(work)
    assert checked["ok"] and checked["results"][0]["status"] == "NOT_CHECKABLE"


@pytest.mark.parametrize("legacy_case", test_adversarial.CASES, ids=lambda fn: fn.__name__)
def test_existing_adversarial(legacy_case):
    legacy_case()


def test_existing_e2e():
    test_e2e.main()


@pytest.mark.parametrize("gate", ["G3", "[4b]", "G5"])
def test_owned_success_cannot_be_forged_via_public_api(work, gate):
    start_chain(work)
    manifest.build(work, for_g3=True)
    with pytest.raises(gates.GateError, match="소유 스크립트"):
        gates.record_script_result(work, gate, 0, "검증·렌더 생략",
            extra={"manifest_sha256": gates.sha256_file(work.manifest)})
    assert not manifest.finalize_report(work)["ok"]
    assert not gates.successful_receipt(work, "G5")
    failure = gates.record_script_result(work, gate, 1, "실패 이력")
    assert failure["exit"] == 1 and failure["gate"] == gate
    assert gates.main(["record_script_result", gate, "1", str(work.root)]) == 0


def test_receipt_only_pipeline_cannot_finalize(work):
    start_chain(work)
    manifest.build(work, for_g3=True)
    baseline = gates.sha256_file(work.manifest)
    with pytest.raises(gates.GateError, match="소유 스크립트"):
        gates.record_script_result(work, "G3", 0, extra={"manifest_sha256": baseline})
    work.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
    manifest.extend(work, [work.report_pdf], expected_sha256=baseline)
    with pytest.raises(gates.GateError, match="소유 스크립트"):
        gates.record_script_result(work, "[4b]", 0,
            extra={"manifest_sha256": gates.sha256_file(work.manifest)})
    with pytest.raises(gates.GateError):
        gates.record_manual(work, "G4", "가짜 preview")
    assert manifest.verify(work)["ok"]  # 파일 해시만으로 소유 단계 실행을 증명할 수 없다.
    result = manifest.finalize_report(work)
    assert not result["ok"] and result["publication_state"] == "재검토 필요"


def test_real_g3_cannot_be_followed_by_forged_render_receipt(work):
    start_chain(work)
    checked = cli("verify_facts.py", work.report_md, work.root)
    assert checked.returncode == 0, checked.stderr
    g3 = gates.require_receipt(work, "G3")
    work.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
    manifest.extend(work, [work.report_pdf], expected_sha256=g3["manifest_sha256"])
    with pytest.raises(gates.GateError, match="소유 스크립트"):
        gates.record_script_result(work, "[4b]", 0,
            extra={"manifest_sha256": gates.sha256_file(work.manifest)})
    assert not manifest.finalize_report(work)["ok"]


def test_g3_rejects_clean_alternate_manuscript(work):
    start_chain(work)
    clean = work.root / "clean.md"
    clean.write_bytes(work.report_md.read_bytes())
    work.report_md.write_text(EXPANDED + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
    # clean.md 자체는 검토 대장과 일치해도 실제 report.md와 다르면 함수·CLI 모두 거부한다.
    assert claims.verify(clean, work)["ok"]
    result = verify_facts.verify(clean, work)
    assert not result["ok"] and any("원고경로" in issue for issue in result["failures"])
    checked = cli("verify_facts.py", clean, work.root)
    assert checked.returncode == 1 and "검증 원고 경로 불일치" in checked.stderr
    assert not work.manifest.exists()
    assert not gates.successful_receipt(work, "G3")
    assert not manifest.finalize_report(work)["ok"]


def test_render_cli_rejects_alternate_manuscript_after_real_g3(work):
    start_chain(work)
    checked = cli("verify_facts.py", work.report_md, work.root)
    assert checked.returncode == 0, checked.stderr
    alternate = work.root / "alternate.md"
    alternate.write_text(EXPANDED, encoding="utf-8")
    checked = cli("render_pdf.py", alternate)
    assert checked.returncode == 1 and "렌더 원고 경로 불일치" in checked.stderr
    assert not alternate.with_suffix(".pdf").exists()
    assert not gates.successful_receipt(work, "[4b]")
    assert not manifest.finalize_report(work)["ok"]


def legacy_chain(wp, *, v4=False):
    """변경 전 원장 형식을 합성한다. 새 API로 구형 영수증을 발급하지 않는다."""
    facts, evidence = FactsDB(wp).facts(), FactsDB(wp).evidence()
    if not v4:
        for row in [*facts, *evidence]:
            row.pop("schema_version")
        _write_jsonl_atomic(wp.facts, facts)
        _write_jsonl_atomic(wp.evidence, evidence)
    render_pdf.render(wp.report_md)  # 구형 영수증 호환도 현재 원고·PDF 실검증은 통과해야 한다.
    sealed = manifest.build(wp)
    sealed.pop("revision_id")
    manifest._write(wp, sealed)
    refs = [{"path": rel, "sha256": gates.sha256_file(wp.root / rel)}
            for rel in ("report.md", "facts.jsonl", "evidence.jsonl")]
    rows = []
    for gate in ("G0", "G1", "[2]", "G2", "G3", "G5c", "[4]", "[4b]", "G4", "G5"):
        row = {"gate": gate, "exit": 0, "kind": "manual" if gate in gates.MANUAL_GATES else "script",
               "ts": "2026-01-01T00:00:00", "refs": copy.deepcopy(refs)}
        if gate == "G0":
            row.update(research_plan="audit/research-plan.md",
                       research_plan_sha256=gates.sha256_file(wp.audit / "research-plan.md"))
        if gate == "[2]":
            row["confirmed_digest_sha256"] = confirmed_digest(facts)
        if gate in ("G3", "[4b]"):
            row["manifest_sha256"] = gates.sha256_file(wp.manifest)
        rows.append(row)
    _write_jsonl_atomic(gates.ledger_path(wp), rows)
    return rows


def test_old_v3_receipts_finalize_with_revision_warnings(work):
    rows = legacy_chain(work)
    history = gates.ledger_path(work).read_bytes()
    with pytest.warns(UserWarning, match="v3 구형 revision_id"):
        for row in rows:
            assert gates.require_receipt(work, row["gate"])["exit"] == 0
        assert manifest.finalize_report(work)["ok"]
        current = gates.require_receipt(work, "G5")
    assert current["revision_id"] == confirmed_digest(FactsDB(work).facts())
    assert gates.ledger_path(work).read_bytes().startswith(history)


def test_old_receipts_are_rejected_in_v4_work(work):
    rows = legacy_chain(work, v4=True)
    for row in rows:
        if row["gate"] in gates.REVISION_GATES:
            with pytest.raises(gates.GateError, match="revision_id"):
                gates.require_receipt(work, row["gate"])
    assert not manifest.finalize_report(work)["ok"]


@pytest.mark.parametrize("mutation", ["refs", "confirmed", "manifest", "plan"])
def test_legacy_exception_preserves_existing_bindings(work, mutation):
    rows = legacy_chain(work)
    if mutation == "refs":
        work.report_md.write_text("# 변조", encoding="utf-8")
    elif mutation == "confirmed":
        rows[2]["confirmed_digest_sha256"] = "0" * 64
        _write_jsonl_atomic(gates.ledger_path(work), rows)
        with pytest.warns(UserWarning):
            with pytest.raises(gates.GateError, match="confirmed"):
                gates.require_receipt(work, "[2]")
        return
    elif mutation == "manifest":
        work.manifest.write_text(work.manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    else:
        (work.audit / "research-plan.md").write_text("# 변조", encoding="utf-8")
        with pytest.raises(gates.GateError, match="계획 해시"):
            gates.require_receipt(work, "G0")
        return
    with pytest.warns(UserWarning):
        assert not manifest.finalize_report(work)["ok"]


def test_new_v3_receipt_cannot_lose_revision_id(work):
    legacy_chain(work)
    with pytest.warns(UserWarning):
        assert manifest.finalize_report(work)["ok"]
    rows = gates._read_records(work)
    rows[-1].pop("revision_id")
    _write_jsonl_atomic(gates.ledger_path(work), rows)
    with pytest.warns(UserWarning):
        with pytest.raises(gates.GateError, match="revision_id"):
            gates.require_receipt(work, "G5")


def test_owned_bindings_are_recomputed_and_checked(work):
    start_chain(work)
    checked = verify_facts.verify_and_record(work)
    assert checked["verification"]["ok"]
    g3 = gates.require_receipt(work, "G3")
    assert g3["manifest_sha256"] == gates.sha256_file(work.manifest)
    # 소유 내부 경로도 extra로 결박값을 주입받지 않는다.
    with pytest.raises(TypeError):
        gates._record_owned_result(work, "[4b]", extra={"manifest_sha256": "0" * 64})
    with pytest.raises(gates.GateError, match="소유 작업 실행 필요"):
        gates._record_owned_result(work, "[4b]")
    rendered = render_pdf.render_and_record(work)
    receipt = rendered["receipt"]
    assert receipt["manifest_sha256"] == gates.sha256_file(work.manifest)
    assert receipt["g3_receipt_id"] == g3["receipt_id"]
    assert receipt["artifacts"] == [{"path": "report.pdf",
                                      "sha256": gates.sha256_file(work.report_pdf)}]
    work.report_md.write_text("# 변조", encoding="utf-8")
    with pytest.raises(gates.GateError, match="소유 작업 실행 필요"):
        gates._record_owned_result(work, "G3")
    assert not verify_facts.verify_and_record(work)["verification"]["ok"]
    assert not gates.successful_receipt(work, "G3")


def test_review_a_failed_g3_cannot_finalize_via_owned_record_path(work):
    """리뷰 A: 실패 원고를 수동 봉인해도 소유 성공 영수증으로 세탁할 수 없다."""
    start_chain(work)
    work.report_md.write_text(EXPANDED + "\n\n![증빙](_captures/E001.png)\n", encoding="utf-8")
    assert not verify_facts.verify(work.report_md, work)["ok"]
    manifest.build(work, for_g3=True)
    baseline = gates.sha256_file(work.manifest)
    with pytest.raises(gates.GateError, match="소유 작업 실행 필요"):
        gates._record_owned_result(work, "G3", "owner record without PASS")
    result = verify_facts.verify_and_record(work)
    assert not result["verification"]["ok"] and result["receipt"]["exit"] == 1
    assert gates.sha256_file(work.manifest) == baseline  # FAIL은 기준선을 재봉인하지 않는다.
    work.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
    manifest.extend(work, [work.report_pdf], expected_sha256=baseline)
    with pytest.raises(gates.GateError, match="소유 작업 실행 필요"):
        gates._record_owned_result(work, "[4b]", "owner record without render")
    with pytest.raises(gates.GateError):
        gates.record_manual(work, "G4", "review declaration", refs=["report.pdf"])
    final = manifest.finalize_report(work)
    assert not final["ok"]
    assert all(not gates.successful_receipt(work, gate) for gate in ("G3", "[4b]", "G5"))
    print(json.dumps({"scenario": "failed_g3", "actual_g3_ok": False,
                      "g3_current": False, "render_current": False, "final_ok": final["ok"],
                      "g5_current": False}, ensure_ascii=False))


def test_review_b_skipped_render_cannot_finalize_via_owned_record_path(work):
    """리뷰 B: 실제 G3 PASS 뒤 가짜 PDF+extend도 [4b] 실행을 대신하지 못한다."""
    start_chain(work)
    checked = cli("verify_facts.py", work.report_md, work.root)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    g3 = gates.require_receipt(work, "G3")
    work.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
    manifest.extend(work, [work.report_pdf], expected_sha256=g3["manifest_sha256"])
    assert manifest.verify(work)["ok"]
    with pytest.raises(gates.GateError, match="소유 작업 실행 필요"):
        gates._record_owned_result(work, "[4b]", "owner record without render")
    with pytest.raises(gates.GateError, match="기준선과 다름"):
        render_pdf.render_and_record(work)
    assert work.report_pdf.read_bytes() == b"%PDF-1.4 fabricated"
    assert gates._read_records(work)[-1]["exit"] == 1  # 실행 실패도 append-only로 보존한다.
    with pytest.raises(gates.GateError):
        gates.record_manual(work, "G4", "review declaration", refs=["report.pdf"])
    final = manifest.finalize_report(work)
    assert not final["ok"]
    assert gates.successful_receipt(work, "G3")
    assert not gates.successful_receipt(work, "[4b]")
    assert not gates.successful_receipt(work, "G5")
    print(json.dumps({"scenario": "skipped_render", "actual_g3_ok": True,
                      "render_current": False, "final_ok": final["ok"],
                      "g5_current": False}, ensure_ascii=False))


def forged_render_chain(wp, g3):
    """재리뷰와 동일한 하위 기록 API로 디스크 해시가 맞는 [4b]·G4를 만든다."""
    sealed = manifest.extend(wp, [wp.report_pdf], expected_sha256=g3["manifest_sha256"])
    gates._record_script_result(wp, "[4b]", 0, "without render", extra={
        "manifest_sha256": gates.sha256_file(wp.manifest),
        "g3_receipt_id": gates._receipt_id(g3),
        "g3_result_summary_sha256": g3["result_summary_sha256"],
        "artifacts": [{"path": rel, "sha256": gates.sha256_file(wp.root / rel)}
                      for rel in sealed["extended"][-1]["added"]]})
    gates.record_manual(wp, "G4", "review declaration", refs=["report.pdf"])


@pytest.mark.parametrize("scenario,real_pdf", [
    ("failed_g3", False), ("skipped_render", False), ("failed_g3", True)])
def test_rereview_private_receipt_forgery_cannot_finalize(work, scenario, real_pdf):
    """원본 재현 A·B와, A에서 진짜 PDF를 써 원고 재검증을 독립 검증하는 짝."""
    start_chain(work)
    if scenario == "failed_g3":
        work.report_md.write_text(EXPANDED + "\n\n![](_captures/E001.png)\n", encoding="utf-8")
        checked = verify_facts.verify_and_record(work)
        assert not checked["verification"]["ok"] and checked["receipt"]["exit"] == 1
        sealed = manifest.build(work, for_g3=True)
        g3 = gates._record_script_result(work, "G3", 0, "without PASS", extra={
            "manifest_sha256": gates.sha256_file(work.manifest),
            "manifest_entries": len(sealed["entries"])})
    else:
        checked = verify_facts.verify_and_record(work)
        assert checked["verification"]["ok"]
        g3 = checked["receipt"]
    if real_pdf:
        render_pdf.render(work.report_md)
    else:
        work.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
    forged_render_chain(work, g3)
    assert manifest.verify(work)["ok"]
    assert all(gates.successful_receipt(work, gate) for gate in ("G3", "[4b]", "G4"))
    history = gates.ledger_path(work).read_bytes()
    final = manifest.finalize_report(work)
    assert not final["ok"] and final["publication_state"] != "최종"
    assert final["facts"]["ok"] == (scenario == "skipped_render")
    assert final["pdf"]["ok"] == real_pdf
    assert not gates.successful_receipt(work, "G5")
    assert gates.ledger_path(work).read_bytes().startswith(history)
    status = gates.status(work)
    assert status["publication_state"] == "재검토 필요" and "G5" not in status["completed"]
    print(json.dumps({"scenario": scenario, "real_pdf": real_pdf,
                      "final_ok": final["ok"], "publication_state": final["publication_state"]},
                     ensure_ascii=False))


@pytest.mark.parametrize("invalid", [False, True])
def test_check_only_verification_does_not_write_files(work, invalid):
    if invalid:
        work.report_md.write_text(EXPANDED, encoding="utf-8")
    for name in ("claim-check.json", "calc-check.json"):
        (work.audit / name).write_text("기존 감사 출력", encoding="utf-8")
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in work.root.rglob("*") if p.is_file()}
    result = verify_facts.verify(work.report_md, work, check_only=True)
    assert result["ok"] != invalid
    after = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in work.root.rglob("*") if p.is_file()}
    assert before == after


@pytest.mark.parametrize("omitted", [None, "tags", "links", "captures"])
def test_final_rechecks_pdf_content_with_valid_seal(work, omitted):
    # 참조형 링크도 렌더와 같은 파서로 추적해야 한다.
    with work.report_md.open("a", encoding="utf-8") as stream:
        stream.write("\n[Source][source]\n\n[source]: https://example.test/source\n")
    start_chain(work)
    checked = verify_facts.verify_and_record(work)
    assert checked["verification"]["ok"]
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((30, 40), "Evidence" if omitted == "tags" else "Evidence (F001)")
        if omitted != "links":
            page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(30, 50, 120, 65),
                              "uri": "https://example.test/source"})
        if omitted != "captures":
            page.insert_image(fitz.Rect(30, 80, 510, 260), filename=str(work.captures / "E001.png"))
        doc.save(work.report_pdf)
    forged_render_chain(work, checked["receipt"])
    final = manifest.finalize_report(work)
    assert final["facts"]["ok"] and final["ok"] == (omitted is None)
    if omitted:
        marker = {"tags": "PDF F태그", "links": "PDF 링크", "captures": "PDF 캡처"}[omitted]
        assert marker in final["reason"]


def test_finalize_runs_read_only_verification_once_and_status_only_checks_bindings(work, monkeypatch):
    start_chain(work)
    assert verify_facts.verify_and_record(work)["verification"]["ok"]
    render_pdf.render_and_record(work)
    gates.record_manual(work, "G4", "preview", refs=["report.pdf"])
    before = {p: p.read_bytes() for p in work.root.rglob("*") if p.is_file()}
    calls = []
    actual_verify = verify_facts.verify

    def observed_verify(*args, **kwargs):
        calls.append(kwargs)
        return actual_verify(*args, **kwargs)

    monkeypatch.setattr(verify_facts, "verify", observed_verify)
    assert manifest.finalize_report(work)["ok"]
    assert calls == [{"check_only": True}]
    assert all(p.read_bytes() == data for p, data in before.items() if p != gates.ledger_path(work))
    status = gates.status(work)
    assert status["publication_state"] == "최종(판정시점)"
    assert status["finalization"]["bindings_match"] is True
    assert len(calls) == 1  # status는 원고·PDF를 다시 검사하지 않는다.
    # 일반 감사 출력은 판정 입력이 아니다.
    (work.audit / "calc-check.json").write_text("새 감사 출력", encoding="utf-8")
    assert gates.status(work)["finalization"]["bindings_match"] is True
    # manifest 자체는 그대로 두고 파일만 바꿔도 status가 드리프트를 검출한다.
    with work.report_pdf.open("ab") as stream:
        stream.write(b"\n% changed")
    assert gates.status(work)["publication_state"] == "재검토 필요"
    assert gates.status(work)["finalization"]["bindings_match"] is False
    assert len(calls) == 1


def test_g5_success_receipt_without_actual_verification_is_not_final(work):
    start_chain(work)
    assert verify_facts.verify_and_record(work)["verification"]["ok"]
    work.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
    forged_render_chain(work, gates.require_receipt(work, "G3"))
    gates._record_script_result(work, "G5", 0, "without final checks", extra={
        "manifest_sha256": gates.sha256_file(work.manifest), "refs": manifest._final_refs(work)})
    assert gates.successful_receipt(work, "G5")  # 기록 유효성과 출고 승인을 구분한다.
    assert manifest.publication_state(work)["publication_state"] == "재검토 필요"
    assert gates.status(work)["publication_state"] == "재검토 필요"
    assert "G5" not in gates.status(work)["completed"]
    assert not manifest.finalize_report(work)["ok"]


def test_custom_rendered_pdf_is_rechecked_and_can_finalize(work):
    start_chain(work)
    assert verify_facts.verify_and_record(work)["verification"]["ok"]
    output = work.root / "custom.pdf"
    render_pdf.render_and_record(work, output)
    gates.record_manual(work, "G4", "custom preview", refs=["custom.pdf"])
    final = manifest.finalize_report(work)
    assert final["ok"] and final["pdf"]["artifacts"]["custom.pdf"]["ok"]
    assert not work.report_pdf.exists()
    assert gates.status(work)["finalization"]["bindings_match"] is True
    output.write_bytes(b"%PDF-1.4 fabricated")
    assert gates.status(work)["publication_state"] == "재검토 필요"
    assert not manifest.finalize_report(work)["ok"]


@pytest.mark.parametrize("field", ["final_verification", "final_verification_sha256",
                                  "result_summary_sha256", "snapshot_hashes", "snapshot_sha256"])
def test_forged_status_extra_is_rejected(work, field):
    start_chain(work)
    assert verify_facts.verify_and_record(work)["verification"]["ok"]
    work.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
    forged_render_chain(work, gates.require_receipt(work, "G3"))
    fake = {"ok": True, "facts": {"ok": True}, "pdf": {"ok": True}}
    payload = {"final_verification": fake,
               "final_verification_sha256": gates.sha256_text(json.dumps(fake)),
               "result_summary_sha256": gates.sha256_text(json.dumps(fake)),
               "snapshot_hashes": manifest._final_snapshot(work), "snapshot_sha256": "a" * 64}
    before = gates.ledger_path(work).read_bytes()
    with pytest.raises(gates.GateError, match="예약 필드"):
        gates._record_script_result(work, "G5", 0,
            json.dumps(fake, ensure_ascii=False, sort_keys=True), extra={
                "manifest_sha256": gates.sha256_file(work.manifest),
                "refs": manifest._final_refs(work), field: payload[field]})
    assert gates.ledger_path(work).read_bytes() == before
    assert gates.status(work)["publication_state"] != "최종(판정시점)"
    assert not manifest.finalize_report(work)["ok"]
    print(f"forged_status: {field} 주입 거부, 최종 표시 없음, 실검증 FAIL")


def test_plan_option_diagnostic_cannot_issue_g3_or_finalize(work):
    plan = work.audit / "research-plan.md"
    plan.write_text("# 부 1. 반드시 포함할 승인 장\n", encoding="utf-8")
    alternate = work.root / "alternate-plan.md"
    alternate.write_text("# 진단용 별도 계획\n", encoding="utf-8")
    start_chain(work)
    before = gates.ledger_path(work).read_bytes()
    diagnostic = cli("verify_facts.py", work.report_md, work.root,
                     "--check-only", "--plan", alternate)
    assert diagnostic.returncode == 0, diagnostic.stdout + diagnostic.stderr
    assert gates.ledger_path(work).read_bytes() == before
    assert not work.manifest.exists()
    with pytest.raises(ValueError, match="계획경로"):
        verify_facts.verify(work.report_md, work, plan=alternate)
    with pytest.raises(ValueError, match="계획경로"):
        verify_facts.verify_and_record(work, plan=alternate)
    recorded = cli("verify_facts.py", work.report_md, work.root, "--plan", alternate)
    assert recorded.returncode == 1 and "계획경로" in recorded.stderr
    regular = verify_facts.verify_and_record(work)
    assert not regular["verification"]["ok"]
    assert any("목차이탈" in issue for issue in regular["verification"]["failures"])
    assert not gates.successful_receipt(work, "G3")
    assert not manifest.finalize_report(work)["ok"]
    print("plan_option: 별도 계획 진단 PASS, API/CLI 기록 거부, 정규 계획 목차이탈 FAIL, 최종 출고 차단")


def test_g3_binds_canonical_plan_even_when_g0_uses_alternate(work):
    alternate = work.root / "g0-plan.md"
    alternate.write_text("# G0 별도 승인\n", encoding="utf-8")
    gates.record_manual(work, "G0", "계획 확인", plan=alternate)
    gates.record_script_result(work, "G1", 0, "join")
    gates.record_manual(work, "[2]", "전건 재열람", refs=["facts.jsonl"])
    receipt = verify_facts.verify_and_record(work, plan=work.audit / "research-plan.md")["receipt"]
    assert {"path": "audit/research-plan.md", "sha256": gates.sha256_file(
        work.audit / "research-plan.md")} in receipt["refs"]
    (work.audit / "research-plan.md").write_text("# 계획 변경\n", encoding="utf-8")
    assert gates.successful_receipt(work, "G0")
    assert not gates.successful_receipt(work, "G3")


@pytest.mark.parametrize("rel", ["_sources/input.txt", "_captures/E001.png", "facts.jsonl",
                                "evidence.jsonl", "report.md", "report.pdf", "custom.pdf",
                                "audit/claim-review.jsonl", "audit/research-plan.md",
                                "manifest.json", "_sources/new.txt"])
def test_finalize_rehashes_all_inputs_after_validation(work, monkeypatch, rel):
    (work.sources / "input.txt").write_text("근거", encoding="utf-8")
    start_chain(work)
    assert verify_facts.verify_and_record(work)["verification"]["ok"]
    render_pdf.render_and_record(work, work.root / "custom.pdf")
    gates.record_manual(work, "G4", "preview", refs=["custom.pdf"])
    original = manifest._check_final_report

    def mutate_after_checks(wp):
        result = original(wp)
        assert result["ok"], result
        with (wp.root / rel).open("ab") as stream:
            stream.write(b"\n ")  # JSONL도 유효한 채로 바꿔 기록 시 파싱 오류와 구분한다.
        return result

    monkeypatch.setattr(manifest, "_check_final_report", mutate_after_checks)
    result = manifest.finalize_report(work)
    assert not result["ok"] and "검증 중 입력 변경" in result["reason"]
    receipt = gates._latest(gates._read_records(work), "G5")
    assert receipt["exit"] == 1
    assert manifest.publication_state(work)["publication_state"] == "재검토 필요"


def test_final_snapshot_covers_seal_and_missing_canonical_pdf(work):
    start_chain(work)
    verify_facts.verify_and_record(work)
    render_pdf.render_and_record(work, work.root / "custom.pdf")
    gates.record_manual(work, "G4", "preview", refs=["custom.pdf"])
    assert manifest.finalize_report(work)["ok"]
    receipt = gates.require_receipt(work, "G5")
    snapshot = receipt["snapshot_hashes"]
    assert set(manifest._load(work)["entries"]) <= set(snapshot)
    assert {"report.md", "report.pdf", "audit/claim-review.jsonl", "audit/research-plan.md"} <= set(snapshot)
    assert snapshot["report.pdf"] == "missing"
    assert snapshot == manifest._final_snapshot(work)
    state = gates.status(work)
    assert state["publication_state"] == "최종(판정시점)"
    assert "원장 기반" in state["finalization"]["basis"]
    assert "manifest.py verify" in state["finalization"]["basis"]
    # 구형 위조 조합은 요약 해시가 맞아도 스냅샷이 없으면 최종 표시를 얻지 못한다.
    forged = copy.deepcopy(receipt)
    forged.pop("snapshot_hashes")
    forged.pop("snapshot_sha256")
    assert manifest.publication_state(work, forged)["publication_state"] == "재검토 필요"
