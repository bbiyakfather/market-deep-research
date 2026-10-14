"""Batch RD: COVERAGE 파싱, 열린 공백 집계, universe 대조, 문서 표지."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import join_workers
from facts_db import ValidationError, make_claim_key, validate_fact

ROOT = Path(__file__).resolve().parents[1]
DASH = "—"


def _worker(extra=""):
    chunks = [f"## {name}{' (JSONL)' if name == 'EVIDENCE' else ''}\n없음"
              for name in join_workers.SECTIONS]
    text = "\n\n".join(chunks)
    if extra:
        text += "\n\n" + extra
    return text + "\n"


COVERAGE = f"""## COVERAGE
- QUERY: 알파 매출 {DASH} BACKEND: ddg {DASH} RESULT: 2
- QUERY: 알파 filetype:pdf {DASH} BACKEND: MCP:opendart {DASH} RESULT: BLOCKED
- GAP: 알파 특허 {DASH} STATE: NOT_FOUND {DASH} TRIED: 3 {DASH} WHY: 정상 응답이나 없음
- GAP: 베타 재무 {DASH} STATE: UNREACHABLE {DASH} TRIED: 1 {DASH} WHY: 종료 코드 2
- GAP: 감마 고객 {DASH} STATE: NOT_ATTEMPTED {DASH} TRIED: 0 {DASH} WHY: 범위 밖
"""


def _pending_fact():
    fact = {"id": "F001", "schema_version": 4, "claim_type": "observed", "claim": "원문 값",
            "context": {"metric": "revenue", "entity": "Acme", "geography": "GL", "period": "2026",
                        "entity_id": "acme", "definition": "연결 매출"},
            "value": {"raw": "45", "unit": "USD"}, "risk": "normal", "status": "pending",
            "grade": {key: "A" for key in ("authority", "independence", "directness", "recency")},
            "evidence_ids": [], "verify_events": []}
    fact["claim_key"] = make_claim_key(fact["context"])
    return fact


def test_coverage_parses_queries_and_open_gaps(tmp_path):
    good = tmp_path / "good.md"
    good.write_text(_worker(COVERAGE), encoding="utf-8")
    alone = join_workers.validate_worker(good.read_text(encoding="utf-8"), str(good))
    assert alone["verdict"] == "ok"
    assert alone["coverage"]["present"] is True
    assert len(alone["coverage"]["queries"]) == 2
    assert [gap["state"] for gap in alone["coverage"]["gaps"]] == [
        "NOT_FOUND", "UNREACHABLE", "NOT_ATTEMPTED"]

    bare = tmp_path / "bare.md"
    bare.write_text(_worker(), encoding="utf-8")
    joined = join_workers.join_workers([good, bare])
    assert joined["ok"]
    assert [row["verdict"] for row in joined["files"]] == ["ok", "ok"]
    assert joined["convergence"]["open_gaps"] == 2
    assert joined["convergence"]["coverage_missing"] == 1
    assert joined["coverage"]["missing"] == [str(bare.resolve())]
    assert joined["coverage"]["by_state"]["NOT_FOUND"] == 1
    assert joined["coverage"]["by_file"][0]["queries"] == 2
    # 옛 무신규 신호는 EXPAND 만 본다. 열린 공백이 있어도 empty_expand_wave 는 그대로다.
    assert joined["convergence"]["empty_expand_wave"] is True


def test_coverage_format_error_is_invalid_and_absent_section_stays_ok(tmp_path):
    broken = join_workers.validate_worker(_worker("## COVERAGE\n- QUERY: 깨진 줄"))
    assert broken["verdict"] == "invalid"
    assert any(err.get("section") == "COVERAGE" for err in broken["errors"])
    assert broken["coverage"]["gaps"] == []

    empty = join_workers.validate_worker(_worker("## COVERAGE"))
    assert empty["verdict"] == "invalid"
    assert any("빈 섹션" in err.get("message", "") for err in empty["errors"])

    none = join_workers.validate_worker(_worker("## COVERAGE\n없음"))
    assert none["verdict"] == "ok"
    assert none["coverage"]["present"] is True
    assert none["coverage"]["queries"] == []

    legacy = tmp_path / "legacy.md"
    legacy.write_text(_worker(), encoding="utf-8")
    result = join_workers.join_workers([legacy])
    assert result["files"][0]["verdict"] == "ok"
    assert result["convergence"]["empty_expand_wave"] is True
    assert result["convergence"]["coverage_missing"] == 1
    assert result["convergence"]["open_gaps"] == 0


def test_discovery_is_optional_and_closed():
    fact = _pending_fact()
    assert validate_fact(fact)["id"] == "F001"
    fact["discovery"] = None
    assert validate_fact(fact)["discovery"] is None
    fact["discovery"] = {"query": "알파 매출", "wave": "0", "axis": "재무", "worker": "w1"}
    assert validate_fact(fact)["discovery"]["axis"] == "재무"
    fact["discovery"] = {"query": "알파", "extra": "x"}
    with pytest.raises(ValidationError, match="알 수 없는 필드"):
        validate_fact(fact)
    fact["discovery"] = {"wave": 1}
    with pytest.raises(ValidationError, match="타입 오류"):
        validate_fact(fact)


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def test_coverage_command_reports_thin_targets_and_off_log_urls(tmp_path):
    audit = tmp_path / "audit"
    audit.mkdir()
    (audit / "universe.md").write_text("""
| 대상 | 별칭 | 목록 출처 | 포함/제외 | 사유 |
|---|---|---|---|---|
| 알파 | Alpha | 협회 명부, 공시 DB | 포함 | 핵심 |
| 베타 |  | 업계 지도 | 포함 |  |
| 감마 |  | 특허 순위 | 제외 | 범위 밖 |
| 델타 | 디, Delta | 협회 명부 | 포함 | 후보 |
""".strip() + "\n", encoding="utf-8")
    _write_jsonl(tmp_path / "facts.jsonl", [
        {"id": "F001", "context": {"entity": "alpha"}},
        {"id": "F002", "context": {"entity": "베타"}},
        {"id": "F003", "context": {"entity": "베타"}},
        {"id": "F004", "context": {"entity": "알파 주식회사"}},
        {"id": "F005", "context": {"entity": "감마"}},
    ])
    _write_jsonl(tmp_path / "evidence.jsonl", [
        {"id": "E001", "type": "text_quote", "source_url": "https://example.test/a"},
        {"id": "E002", "type": "text_quote", "source_url": "https://example.test/b/"},
        {"id": "E003", "type": "text_quote", "source_url": "https://example.test/c"},
        {"id": "E004", "type": "api_response", "source_url": "https://example.test/api"},
        {"id": "E005", "type": "negative_search", "source_url": "https://example.test/none"},
        {"id": "E006", "type": "calculation", "source_url": "https://example.test/calc"},
    ])
    _write_jsonl(audit / "fetch-log.jsonl", [
        {"url": "https://example.test/a"},
        {"url": "https://example.test/b"},
    ])

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "join_workers.py"), "coverage", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", check=False)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["zero_facts"] == ["델타"]
    assert report["single_fact"] == ["알파"]
    assert report["included"] == ["알파", "베타", "델타"]
    assert report["fetch_log"]["evidence_urls"] == 3
    assert report["fetch_log"]["missing_urls"] == 1
    assert report["fetch_log"]["warning"]
    assert any("fetch-log" in note for note in report["notices"])

    skipped = tmp_path / "no-universe"
    skipped.mkdir()
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "join_workers.py"), "coverage", str(skipped)],
        capture_output=True, text=True, encoding="utf-8", check=False)
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["zero_facts"] == []
    assert any("universe.md" in note for note in report["notices"])
    assert any("facts.jsonl" in note for note in report["notices"])
    assert any("evidence.jsonl" in note for note in report["notices"])


def test_design_markers_exist_in_docs():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    briefs = (ROOT / "references" / "agent-briefs.md").read_text(encoding="utf-8")
    plan = (ROOT / "references" / "research-plan.md").read_text(encoding="utf-8")
    gates = (ROOT / "references" / "verification-gates.md").read_text(encoding="utf-8")
    assert "## COVERAGE" in briefs
    assert "audit/universe.md" in skill and "audit/universe.md" in plan
    assert "audit/gap-log.md" in skill and "audit/gap-log.md" in gates
