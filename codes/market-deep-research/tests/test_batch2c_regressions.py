"""배치 2C: 파일 저장 실패, 워커 부분결과, URL 이력의 실제 입출력 회귀."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import facts_db
import fetch
import join_workers
import source_index
from facts_db import FactsDB, ValidationError, _write_jsonl_atomic
from test_batch2b_regressions import fact_record, evidence_record


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure_point", ["write", "replace"])
def test_n12_second_write_failure_restores_exact_preimage(tmp_path, monkeypatch, existing, failure_point):
    db = FactsDB(tmp_path)
    db.add_fact(fact_record())
    if existing:
        db.add_evidence(evidence_record())
        # JSON 재직렬화가 아니라 공백·CRLF까지 복원되는지 확인한다.
        db.wp.evidence.write_bytes(db.wp.evidence.read_bytes().replace(b"\n", b" \r\n"))
    before_facts = db.wp.facts.read_bytes()
    before_evidence = db.wp.evidence.read_bytes() if existing else None
    original = facts_db._write_jsonl_atomic if failure_point == "write" else os.replace

    def fail_second(first, second):
        target = first if failure_point == "write" else second
        if Path(target) == db.wp.facts:
            raise OSError("injected facts write failure")
        return original(first, second)

    if failure_point == "write":
        monkeypatch.setattr(facts_db, "_write_jsonl_atomic", fail_second)
    else:
        monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError, match="injected"):
        db.add_evidence(evidence_record("E002"))
    assert db.wp.facts.read_bytes() == before_facts
    assert (db.wp.evidence.read_bytes() if db.wp.evidence.exists() else None) == before_evidence
    assert FactsDB(tmp_path).fsck() == {"ok": True, "failures": [], "warnings": []}
    assert not list(tmp_path.rglob("*.tmp"))


def test_n12_success_keeps_both_ledgers_linked(tmp_path):
    db = FactsDB(tmp_path)
    db.add_fact(fact_record())
    db.add_evidence(evidence_record())
    db.add_evidence(evidence_record("E002"))
    loaded = FactsDB(tmp_path)
    assert loaded.facts()[0]["evidence_ids"] == ["E001", "E002"]
    assert len(loaded.evidence()) == 2 and loaded.integrity["ok"]


@pytest.mark.parametrize("version", [3, 4])
@pytest.mark.parametrize("damage", ["orphan", "reverse_missing", "foreign", "missing_evidence"])
def test_n12_load_fsck_reuses_g3_references(tmp_path, version, damage):
    fact, ev = fact_record(version), evidence_record(version=version)
    fact["evidence_ids"] = ["E001"]
    facts, evidence = [fact], [ev]
    if damage == "orphan":
        facts = []
    elif damage == "reverse_missing":
        fact["evidence_ids"] = []
    elif damage == "foreign":
        ev["fact_id"] = "F002"
    else:
        evidence = []
    _write_jsonl_atomic(tmp_path / "facts.jsonl", facts)
    _write_jsonl_atomic(tmp_path / "evidence.jsonl", evidence)
    failures, notices = facts_db.check_ledger_references(facts, evidence)
    if version == 4:
        assert failures and not notices
        with pytest.raises(ValidationError, match="대장fsck.*FAIL"):
            FactsDB(tmp_path)
    else:
        assert notices and not failures
        with pytest.warns(UserWarning, match="대장fsck.*WARN"):
            db = FactsDB(tmp_path)
        assert db.integrity["warnings"] == notices


def worker_text(*, rows=None, expand="없음", insight="없음", omit=None):
    evidence = "없음" if rows is None else "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    sections = {name: "없음" for name in join_workers.SECTIONS}
    sections.update(EVIDENCE=evidence, EXPAND=expand, 인사이트=insight)
    return "\n\n".join(f"## {name}{' (JSONL)' if name == 'EVIDENCE' else ''}\n{body}"
                         for name, body in sections.items() if name != omit) + "\n"


def worker_row(version=4):
    return {"fact": fact_record(version), "evidence": [evidence_record(version=version)]}


@pytest.mark.parametrize("missing", join_workers.SECTIONS)
def test_n17_missing_section_is_invalid(missing):
    result = join_workers.validate_worker(worker_text(omit=missing))
    assert result["verdict"] == "invalid"
    assert any(e.get("section") == missing and "누락" in e["message"] for e in result["errors"])


def test_n17_explicit_empty_and_blocked_are_distinct(tmp_path):
    assert join_workers.validate_worker(worker_text())["verdict"] == "ok"
    assert join_workers.validate_worker("BLOCKED: timeout\n")["verdict"] == "blocked"
    invalid = join_workers.validate_worker("BLOCKED: timeout\n## EVIDENCE\n{bad}\n")
    assert invalid["verdict"] == "invalid" and invalid["errors"][0]["line"] == 3
    assert join_workers.validate_worker(worker_text().replace("## EXPAND\n없음", "## EXPAND\n"))["verdict"] == "invalid"
    for bad in ("BLOCKED:\n", worker_text() + "\n## EXPAND\n없음", worker_text() + "\n```json\n"):
        assert join_workers.validate_worker(bad)["verdict"] == "invalid"


def test_n17_all_invalid_jsonl_rows_report_line_numbers():
    raw = worker_text().replace("## EVIDENCE (JSONL)\n없음", "## EVIDENCE (JSONL)\n{bad}\n[]\n{}")
    result = join_workers.validate_worker(raw)
    assert result["verdict"] == "invalid"
    assert [error["line"] for error in result["errors"]] == [2, 3, 4]


@pytest.mark.parametrize("kind", ["fact", "evidence"])
def test_n17_reuses_schema_v4_fail_v3_warn(kind):
    for version in (3, 4):
        row = worker_row(version)
        if kind == "fact":
            row["fact"]["value"]["base_value"] = True
        else:
            row["evidence"][0]["http_status"] = "200"
        result = join_workers.validate_worker(worker_text(rows=[row]))
        assert result["verdict"] == ("invalid" if version == 4 else "ok"), result
        assert result["errors"] if version == 4 else result["warnings"]


def test_n17_scoped_ids_and_insight_reference_plan(tmp_path):
    paths = [tmp_path / name for name in ("worker-a.md", "worker-b.md")]
    for path in paths:
        path.write_text(worker_text(rows=[worker_row()], insight="근거 F001에서 추론."), encoding="utf-8")
    result = join_workers.join_workers(paths)
    assert [r["verdict"] for r in result["files"]] == ["ok", "ok"]
    mappings = [r["id_remapping"] for r in result["files"]]
    assert mappings[0][0]["scoped_id"] != mappings[1][0]["scoped_id"]
    for mapping in mappings:
        assert {entry["temporary_id"] for entry in mapping} == {"F001", "E001"}
        assert all(entry["central_id"] is None for entry in mapping)
        assert any(ref["field"] == "인사이트" for ref in mapping[0]["references"])
    # 중앙 등재 시 기존 ID 뒤에 중앙이 배정하고, 결과로 재매핑 표를 채울 수 있다.
    db = FactsDB(tmp_path / "central")
    existing = fact_record()
    existing.pop("id")
    existing.pop("claim_key")
    existing["context"]["entity"] = "Other"
    db.add_fact(existing)
    record = copy.deepcopy(result["files"][0]["records"][0])
    fact = record["fact"]
    fact.pop("id")
    fact.pop("evidence_ids")
    registered = db.add_fact(fact)
    assert registered["id"] == "F002"
    ev = record["evidence"][0]
    ev.pop("id")
    ev["fact_id"] = registered["id"]
    assert db.add_evidence(ev)["fact_id"] == "F002"
    assert FactsDB(db.wp).integrity["ok"]


def test_n17_bad_id_links_and_duplicates_are_invalid():
    row = worker_row()
    row["evidence"][0]["fact_id"] = "F999"
    assert join_workers.validate_worker(worker_text(rows=[row]))["verdict"] == "invalid"
    assert join_workers.validate_worker(worker_text(rows=[worker_row(), worker_row()]))["verdict"] == "invalid"
    assert join_workers.validate_worker(worker_text(insight="근거 F999"))["verdict"] == "invalid"
    fenced = worker_text(rows=[worker_row()]).replace('## EVIDENCE (JSONL)\n', '## EVIDENCE (JSONL)\n```json\n')
    fenced = fenced.replace("\n\n## CLAIMS", "\n```\n\n## CLAIMS")
    assert join_workers.validate_worker(fenced)["verdict"] == "ok"


@pytest.mark.parametrize("version", [3, 4])
def test_n17_reference_severity_preserved_and_worker_status_pending(version):
    row = worker_row(version)
    row["fact"]["evidence_ids"] = ["E999"]
    result = join_workers.validate_worker(worker_text(rows=[row]))
    assert result["verdict"] == ("invalid" if version == 4 else "ok")
    assert result["errors"] if version == 4 else result["warnings"]
    row = worker_row(version)
    row["fact"]["status"] = "disputed"
    assert join_workers.validate_worker(worker_text(rows=[row]))["verdict"] == "invalid"


def test_n17_dedup_and_success_only_convergence(tmp_path):
    paths = []
    for index, (axis, lead) in enumerate((("시장", "Alpha   report"), ("시장", "alpha report"),
                                         ("시장", "renamed report"), ("기술", "alpha report"))):
        path = tmp_path / f"{index}.md"
        path.write_text(worker_text(expand=f"- LEAD: {lead} — AXIS: {axis} — WHY: 검토 — ANGLE: https://example.test/a"), encoding="utf-8")
        paths.append(path)
    result = join_workers.join_workers(paths)
    groups = {group["kind"]: group for group in result["duplicate_leads"]}
    assert len(groups["fingerprint"]["occurrences"]) == 2
    assert len(groups["url_fingerprint"]["occurrences"]) == 3
    assert result["convergence"]["lead_count"] == 4
    assert not result["convergence"]["empty_expand_wave"]
    paths[0].write_text(worker_text(), encoding="utf-8")
    paths[1].write_text("BLOCKED: timeout\n", encoding="utf-8")
    result = join_workers.join_workers(paths[:2])
    assert len(result["convergence"]["eligible_workers"]) == 1
    assert not result["convergence"]["empty_expand_wave"]
    assert join_workers.join_workers(paths[:1])["convergence"]["empty_expand_wave"]


def test_n17_cli_json_and_exit_status(tmp_path):
    raw, output = tmp_path / "워커.md", tmp_path / "join.json"
    for body, expected in ((worker_text(), 0), ("BLOCKED: timeout\n", 0), ("## EVIDENCE\n없음\n", 1)):
        raw.write_text(body, encoding="utf-8")
        run = subprocess.run([sys.executable, str(SCRIPTS / "join_workers.py"), str(raw), "--out", str(output)],
                             capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert run.returncode == expected, run.stderr
        assert json.loads(run.stdout) == json.loads(output.read_text(encoding="utf-8"))
    result = join_workers.join_workers([tmp_path / "missing.md"])
    assert not result["ok"] and result["files"][0]["errors"]


def fetch_record(url, status="ok", ref="first"):
    return {"url": url, "final_url": url + "/final", "status": status, "fetch_ref": ref,
            "text": "<html><head><title>동일 본문</title></head><body>공통 본문</body></html>",
            "raw": None, "mime": "text/html", "http_status": 200, "is_pdf": False}


@pytest.mark.parametrize("legacy", [False, True])
def test_n20_shared_blob_retains_url_history_and_status(tmp_path, legacy):
    source = tmp_path / "_sources"
    first = fetch.save(fetch_record("https://a.test"), source)
    path = source / f"{first['sha256'][:12]}.meta.json"
    if legacy:
        meta = json.loads(path.read_text(encoding="utf-8"))
        meta.pop("urls")
        path.write_text(json.dumps(meta), encoding="utf-8")
    fetch.save(fetch_record("https://b.test", "partial", "second"), source)
    fetch.save(fetch_record("https://b.test", "ok", "third"), source)
    meta = json.loads(path.read_text(encoding="utf-8"))
    assert meta["url"] == "https://a.test" and meta["fetch_ref"] == "first"
    assert [r["url"] for r in meta["urls"]] == ["https://a.test", "https://b.test", "https://b.test"]
    assert [r["status"] for r in meta["urls"]] == ["ok", "partial", "ok"]
    assert [r["fetch_ref"] for r in meta["urls"]] == ["first", "second", "third"]
    assert len(list(source.glob("*_raw.*"))) == 1
    rows = source_index.build_index(tmp_path)
    assert len(rows) == 2 and {r["url"] for r in rows} == {"https://a.test", "https://b.test"}
    assert all(r["status"] == "ok" and len(r["shared_urls"]) == 2 for r in rows)
    fetch.save(fetch_record("https://b.test", "partial"), source)
    rows = source_index.build_index(tmp_path)
    markdown = source_index.write_markdown(rows, tmp_path / "sources.md").read_text(encoding="utf-8")
    assert "https://a.test" in markdown and "https://b.test" in markdown
    assert "| 상태 |" in markdown and "| partial |" in markdown and "동일 본문 URL 집합" in markdown


def test_n20_malformed_history_is_not_overwritten(tmp_path):
    saved = fetch.save(fetch_record("https://a.test"), tmp_path)
    path = tmp_path / f"{saved['sha256'][:12]}.meta.json"
    broken = b'{"urls": "broken history"}'
    path.write_bytes(broken)
    with pytest.raises(ValueError, match="메타 형식"):
        fetch.save(fetch_record("https://b.test"), tmp_path)
    assert path.read_bytes() == broken
