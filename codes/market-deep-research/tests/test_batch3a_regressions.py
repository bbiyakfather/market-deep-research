"""배치 3A: 근거 내용 결박·조건 명시·버전 이행·부록 인용의 회귀 검사."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gates
import manifest
import render_pdf
import verify_claims as claims
import verify_facts
from facts_db import (FactsDB, ValidationError, _read_jsonl, _write_jsonl_atomic,
                      confirmed_digest, evidence_content_digest, schema_version)
from test_p0_regressions import work, cli, review, start_chain, LIMITED


def write_review(work, row):
    _write_jsonl_atomic(work.audit / "claim-review.jsonl", [row])


@pytest.mark.parametrize("field,value", [
    ("verbatim", "인증과 적용은 완료되지 않았다."), ("sha256", "a" * 64),
    ("source_url", "https://example.test/replaced"), ("local", "_sources/replaced.txt"),
    ("capture", "_captures/replaced.png"), ("type", "table_cell"),
    ("capture_review", {"reviewed_by": "다른 검토자"}),
])
def test_r01_same_evidence_content_change_requires_review(work, field, value):
    assert verify_facts.verify(work.report_md, work)["ok"]
    revision = confirmed_digest(_read_jsonl(work.facts))
    evidence = _read_jsonl(work.evidence)
    evidence[0][field] = value
    _write_jsonl_atomic(work.evidence, evidence)
    result = claims.verify(work.report_md, work)
    assert not result["ok"]
    assert any("[근거변경]" in item for item in result["failures"])
    assert confirmed_digest(_read_jsonl(work.facts)) == revision
    assert not verify_facts.verify(work.report_md, work)["ok"]


def test_r01_new_evidence_does_not_invalidate_review(work):
    row = _read_jsonl(work.audit / "claim-review.jsonl")[0]
    db = FactsDB(work)
    evidence = copy.deepcopy(db.evidence()[0])
    evidence["id"] = "E002"
    db.add_evidence(evidence)
    assert row["evidence_revision"] == confirmed_digest(db.facts())
    assert row["evidence_content_sha256"] == evidence_content_digest(db.evidence(), ["E001"])
    assert verify_facts.verify(work.report_md, work)["ok"]


def test_r01_digest_is_canonical_and_missing_id_rejected(work):
    rows = _read_jsonl(work.evidence)
    rows.append({**rows[0], "id": "E002", "verbatim": "추가 원문"})
    projected = [{key: value for key, value in row.items() if key not in ("accessed_at", "note")}
                 for row in sorted(rows, key=lambda item: item["id"])]
    expected = gates.sha256_text(json.dumps(projected, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    assert evidence_content_digest(list(reversed(rows)), ["E002", "E001"]) == expected
    with pytest.raises(ValidationError, match="E999"):
        evidence_content_digest(rows, ["E999"])


@pytest.mark.parametrize("field,value", [
    ("locator", {"page": 12, "row": 20, "col": 9}),
    ("source_role", "재인용"),
    ("observer_group", "다른그룹"),
    ("observed_at", "2026-06-01"),
])
def test_r01_context_field_change_invalidates_review(work, field, value):
    assert verify_facts.verify(work.report_md, work)["ok"]
    revision = confirmed_digest(_read_jsonl(work.facts))
    evidence = _read_jsonl(work.evidence)
    evidence[0][field] = value
    _write_jsonl_atomic(work.evidence, evidence)
    result = claims.verify(work.report_md, work)
    assert not result["ok"]
    assert any("[근거변경]" in item for item in result["failures"])
    assert confirmed_digest(_read_jsonl(work.facts)) == revision
    assert not verify_facts.verify(work.report_md, work)["ok"]


@pytest.mark.parametrize("field,value", [
    ("accessed_at", "2099-01-01T00:00:00"),
    ("note", "운영 메모"),
])
def test_r01_operational_field_change_keeps_review(work, field, value):
    assert verify_facts.verify(work.report_md, work)["ok"]
    evidence = _read_jsonl(work.evidence)
    evidence[0][field] = value
    _write_jsonl_atomic(work.evidence, evidence)
    result = claims.verify(work.report_md, work)
    assert result["ok"], result
    assert verify_facts.verify(work.report_md, work)["ok"]


@pytest.mark.parametrize("version", [3, 4])
@pytest.mark.parametrize("binding", [None, "0" * 64])
def test_r01_missing_or_stale_binding_fails_v4_warns_v3(work, version, binding):
    for path in (work.facts, work.evidence):
        rows = _read_jsonl(path)
        rows[0]["schema_version"] = version
        _write_jsonl_atomic(path, rows)
    row = review(work)
    if binding is None:
        row.pop("evidence_content_sha256")
    else:
        row["evidence_content_sha256"] = binding
    write_review(work, row)
    result = verify_facts.verify(work.report_md, work)
    assert result["ok"] == (version == 3)
    messages = result["warnings"] if version == 3 else result["failures"]
    assert any(("[근거결박누락]" if binding is None else "[근거변경]") in item for item in messages)


@pytest.mark.parametrize("kind", ["hypothesis", "recommendation"])
@pytest.mark.parametrize("support", ["partial", "contradicted", "unresolved"])
@pytest.mark.parametrize("qualification,code", [(" \n\t", "[조건미명시]"),
    ("검증되지 않은 조건", "[조건본문누락]"), ("무전원  적용\n여부는 미확인", None)])
def test_r03_conditional_claim_requires_visible_qualification(work, kind, support, qualification, code):
    row = review(work, kind=kind, support=support)
    row["required_qualification"] = qualification
    write_review(work, row)
    result = verify_facts.verify(work.report_md, work)
    assert result["ok"] == (code is None), result
    if code:
        assert any(code in item for item in result["failures"])


@pytest.mark.parametrize("key", ["schema_verison", "Schema_Version", "schema-version", "schemaVersion"])
@pytest.mark.parametrize("kind", ["fact", "evidence", "review"])
def test_r04_schema_version_typo_rejected_in_every_ledger(work, key, kind):
    with pytest.raises(ValidationError, match="schema_version 오타 의심"):
        schema_version({key: 4})
    # 모든 행이 legacy로 보이는 폴더에서도 오타는 경고로 낮추지 않는다.
    for path in (work.facts, work.evidence):
        rows = _read_jsonl(path)
        rows[0]["schema_version"] = 3
        _write_jsonl_atomic(path, rows)
    row = review(work)
    path = {"fact": work.facts, "evidence": work.evidence,
            "review": work.audit / "claim-review.jsonl"}[kind]
    rows = _read_jsonl(path)
    rows[0].pop("schema_version", None)
    rows[0][key] = 4
    _write_jsonl_atomic(path, rows)
    result = verify_facts.verify(work.report_md, work)
    assert not result["ok"]
    assert any("schema_version 오타 의심" in item for item in result["failures"])


@pytest.mark.parametrize("legacy", ["fact", "evidence", "both"])
@pytest.mark.parametrize("appendix", [False, True])
def test_r04_mixed_version_citation_fails(work, legacy, appendix):
    facts, evidence = _read_jsonl(work.facts), _read_jsonl(work.evidence)
    if legacy in ("fact", "both"):
        facts[0]["schema_version"] = 3
    if legacy in ("evidence", "both"):
        evidence[0]["schema_version"] = 3
    if legacy == "both":
        pending = copy.deepcopy(facts[0])
        pending.update(id="F002", schema_version=4, status="pending", evidence_ids=[], claim_key="unused")
        pending["context"]["entity"] = "미인용 회사"
        from facts_db import make_claim_key
        pending["claim_key"] = make_claim_key(pending["context"])
        facts.append(pending)
    _write_jsonl_atomic(work.facts, facts)
    _write_jsonl_atomic(work.evidence, evidence)
    if appendix:
        work.report_md.write_text("# 본문\n\n![증빙](_captures/E001.png)\n\n"
            "<!-- FACTSHEET:APPENDIX -->\n## 부록\n\n" + LIMITED, encoding="utf-8")
    review(work)
    result = verify_facts.verify(work.report_md, work)
    assert not result["ok"]
    assert any("[버전혼합]" in item for item in result["failures"])


def test_r04_legacy_finalize_requires_explicit_flag_and_records_mode(work):
    for path in (work.facts, work.evidence):
        rows = _read_jsonl(path)
        rows[0].pop("schema_version")
        _write_jsonl_atomic(path, rows)
    review(work)
    start_chain(work)
    assert verify_facts.verify(work.report_md, work, check_only=True)["ok"]
    assert verify_facts.verify_and_record(work)["verification"]["ok"]
    render_pdf.render_and_record(work)
    gates.record_manual(work, "G4", "호환 출고 검토", refs=["report.pdf"])
    blocked = manifest.finalize_report(work)
    assert not blocked["ok"] and "[legacy출고]" in blocked["reason"]
    assert cli("manifest.py", "verify", work.root).returncode == 1
    allowed = manifest.finalize_report(work, allow_legacy_v3=True)
    assert allowed["ok"] and allowed["legacy_v3"] is True
    result = cli("manifest.py", "verify", work.root, "--allow-legacy-v3")
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = gates.require_receipt(work, "G5")
    assert receipt["legacy_v3"] is True
    assert receipt["final_verification"]["legacy_v3"] is True
    assert "legacy(v3) 출고" in json.dumps(gates.status(work), ensure_ascii=False)
    status = cli("gates.py", "status", work.root)
    assert status.returncode == 0 and "legacy(v3) 출고" in status.stdout


def test_r05_appendix_high_risk_citation_requires_evidence(work):
    facts, evidence = _read_jsonl(work.facts), _read_jsonl(work.evidence)
    facts[0]["risk"] = "high"
    evidence[0].pop("capture")
    evidence[0].pop("capture_review")
    _write_jsonl_atomic(work.facts, facts)
    _write_jsonl_atomic(work.evidence, evidence)
    work.report_md.write_text("# 본문\n\n![도판](_captures/E001.png)\n\n"
        "<!-- FACTSHEET:APPENDIX -->\n## 부록\n\n" + LIMITED, encoding="utf-8")
    review(work)
    result = verify_facts.verify(work.report_md, work)
    assert not result["ok"]
    high_risk = next(item for item in result["failures"] if "[반박게이트]" in item)
    for expected in ("독립 관찰그룹", "반박검색", "기본소스", "시간증거"):
        assert expected in high_risk
    assert any("[증빙]" in item for item in result["failures"])
    assert not any("미사용" in item for item in result["warnings"])


@pytest.mark.parametrize("segment", [LIMITED, "- " + LIMITED, "1. " + LIMITED])
def test_r05_appendix_prose_and_list_require_review(work, segment):
    work.report_md.write_text("# 본문\n\n![증빙](_captures/E001.png)\n\n"
        "<!-- FACTSHEET:APPENDIX -->\n## 부록\n\n" + segment, encoding="utf-8")
    _write_jsonl_atomic(work.audit / "claim-review.jsonl", [])
    result = verify_facts.verify(work.report_md, work)
    assert not result["ok"] and any("검토 누락" in item for item in result["failures"])
    review(work, claims.tagged_sentences(segment)[0])
    assert verify_facts.verify(work.report_md, work)["ok"]


def test_r05_appendix_table_review_and_untagged_number_exemptions_remain(work):
    with work.report_md.open("a", encoding="utf-8") as report:
        report.write("\n<!-- FACTSHEET:APPENDIX -->\n## 부록\n\n"
                     "| 사실 | 근거 |\n|---|---|\n| 인증 | [F001] |\n\n수집 수치 123 USD\n")
    result = verify_facts.verify(work.report_md, work)
    assert result["ok"], result
    assert any("[부록무태그]" in item for item in result["warnings"])
    assert claims.verify(work.report_md, work)["sentences"] == 1
