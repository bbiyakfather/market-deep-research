"""verify_claims.py — 문장별 의미 검토 대장의 누락·변경·미지원 판정 차단.

CLI: python scripts/verify_claims.py <report.md> <work_dir>
     python scripts/verify_claims.py --demo
의미 판단은 검토자가 기록한다. 이 검사는 그 판단의 진실성을 자동 보증하지 않는다.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import gates
from facts_db import (FactsDB, ValidationError, _read_jsonl, confirmed_digest, is_v4_work,
                      load_schema, schema_version)
from skill_paths import WorkPaths
from verify_facts import TAG, split_body_appendix, split_segments

FIELDS = {"sentence_id", "claim_type", "fact_ids", "evidence_ids", "support", "unsupported_terms",
          "required_qualification", "sentence_text", "reviewed_text_sha256", "evidence_revision"}


def tagged_sentences(body: str) -> list[str]:
    """수치 없는 문장도 포함한다. 표는 근거 태그가 다른 셀에 있어 행 전체를 검토한다."""
    return [s.strip() for s in split_segments(body, preserve_text=True) if TAG.search(s)]


def validate_review(row: dict) -> None:
    if not isinstance(row, dict) or set(row) != FIELDS:
        raise ValidationError(f"claim-review 필드 누락/미지원: {sorted(FIELDS - set(row)) if isinstance(row, dict) else '객체 아님'}")
    for name in FIELDS - {"fact_ids", "evidence_ids", "unsupported_terms"}:
        if not isinstance(row[name], str):
            raise ValidationError(f"claim-review.{name}: 문자열 필요")
        if name != "required_qualification" and not row[name].strip():
            raise ValidationError(f"claim-review.{name}: 빈 문자열 불가")
    for name in ("fact_ids", "evidence_ids", "unsupported_terms"):
        value = row[name]
        if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
            raise ValidationError(f"claim-review.{name}: 문자열 배열 필요")
        if len(set(value)) != len(value):
            raise ValidationError(f"claim-review.{name}: 중복 값")
    enums = load_schema()["enums"]
    for name in ("claim_type", "support"):
        if row[name] not in enums[name]:
            raise ValidationError(f"claim-review.{name}: 허용값 {enums[name]} 아님")


def verify(report_md: Path | str, work: WorkPaths | Path | str, *, check_only: bool = False) -> dict:
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    db = FactsDB(wp)
    facts, evidence = db.facts(), db.evidence()
    strict = is_v4_work(facts, evidence)
    body, _ = split_body_appendix(Path(report_md).read_text(encoding="utf-8"))
    sentences = tagged_sentences(body)
    revision = confirmed_digest(facts)
    path = wp.audit / "claim-review.jsonl"
    issues, reviewed, ids = [], [], set()
    version_errors = []
    for row in [*facts, *evidence]:
        try:
            schema_version(row)
        except ValidationError as exc:
            version_errors.append(str(exc))
    fact_map = {f["id"]: f for f in facts}
    evidence_map = {e["id"]: e for e in evidence}
    if not path.is_file():
        issues.append("claim-review.jsonl 없음 — 문장별 의미 검토 필요")
        rows = []
    else:
        try:
            rows = _read_jsonl(path)
        except (OSError, ValueError) as exc:
            rows = []
            issues.append(f"claim-review 읽기 실패: {exc}")
    for index, row in enumerate(rows, 1):
        try:
            validate_review(row)
        except ValidationError as exc:
            issues.append(f"행 {index}: {exc}")
            continue
        sid, sentence = row["sentence_id"], row["sentence_text"]
        if sid in ids:
            issues.append(f"{sid}: sentence_id 중복")
        ids.add(sid)
        if sentence not in body:
            issues.append(f"{sid}: 현재 본문에 sentence_text 없음 — 문장 변경 후 재검토 필요")
        elif TAG.search(sentence) and sentence not in sentences:
            issues.append(f"{sid}: 문장 일부만 검토됨 — 표행/문장 전체 검토 필요")
        else:
            reviewed.append(sentence)
        if row["reviewed_text_sha256"] != gates.sha256_text(sentence):
            issues.append(f"{sid}: reviewed_text_sha256 불일치 — 문장 재검토 필요")
        if row["evidence_revision"] != revision:
            issues.append(f"{sid}: evidence_revision 불일치 — 근거 변경 후 재검토 필요")
        tagged = {m.group(0).strip("()[]") for m in TAG.finditer(sentence)}
        if not tagged.issubset(set(row["fact_ids"])):
            issues.append(f"{sid}: 본문 태그의 fact_ids 누락")
        if not row["fact_ids"] or not row["evidence_ids"]:
            issues.append(f"{sid}: fact_ids/evidence_ids 근거 누락")
        for fid in row["fact_ids"]:
            if fid not in fact_map:
                issues.append(f"{sid}: 알 수 없는 fact_id {fid}")
            elif not set(fact_map[fid].get("evidence_ids", [])).intersection(row["evidence_ids"]):
                issues.append(f"{sid}: {fid}의 evidence_ids 미결박")
        for eid in row["evidence_ids"]:
            if eid not in evidence_map or evidence_map[eid].get("fact_id") not in row["fact_ids"]:
                issues.append(f"{sid}: 근거 fact와 연결되지 않은 evidence_id {eid}")
        support, kind = row["support"], row["claim_type"]
        if (kind in ("observed", "derived") and support != "supported") or support == "unsupported":
            issues.append(f"{sid}: {kind}/{support} — 미지원 주장 축소·한계 명기 후 재검토 필요")
        if support == "supported" and row["unsupported_terms"]:
            issues.append(f"{sid}: supported인데 unsupported_terms가 남음")
    review_counts = Counter(reviewed)
    for sentence, count in Counter(sentences).items():
        if review_counts[sentence] < count:
            issues.append(f"검토 누락({count - review_counts[sentence]}건): {sentence}")
    messages = [f"[주장검토] {issue}" for issue in issues]
    report = {"ok": not (version_errors or (strict and issues)), "mode": "v4" if strict else "v3 legacy",
              "failures": version_errors + (messages if strict else []), "warnings": [] if strict else messages,
              "sentences": len(sentences), "reviewed": len(reviewed), "evidence_revision": revision}
    if not check_only:
        wp.audit.mkdir(parents=True, exist_ok=True)
        (wp.audit / "claim-check.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def demo() -> None:
    import tempfile
    from facts_db import _write_jsonl_atomic
    with tempfile.TemporaryDirectory() as td:
        wp = WorkPaths(td)
        facts = [{"id": "F001", "schema_version": 4, "status": "confirmed",
                  "evidence_ids": ["E001"], "value": {"raw": "인증", "unit": "text"}}]
        _write_jsonl_atomic(wp.facts, facts)
        _write_jsonl_atomic(wp.evidence, [{"id": "E001", "fact_id": "F001"}])
        sentence = "센서의 인증 경험만 확인된다. [F001]"
        wp.report_md.write_text(sentence, encoding="utf-8")
        assert not verify(wp.report_md, wp)["ok"]
        row = {"sentence_id": "S001", "claim_type": "observed", "fact_ids": ["F001"],
               "evidence_ids": ["E001"], "support": "supported", "unsupported_terms": [],
               "required_qualification": "", "sentence_text": sentence,
               "reviewed_text_sha256": gates.sha256_text(sentence), "evidence_revision": confirmed_digest(facts)}
        _write_jsonl_atomic(wp.audit / "claim-review.jsonl", [row])
        assert verify(wp.report_md, wp)["ok"]
        row["support"] = "partial"
        _write_jsonl_atomic(wp.audit / "claim-review.jsonl", [row])
        assert not verify(wp.report_md, wp)["ok"]
    print("claim-review demo PASS: 검토 누락/partial 차단, 제한 표현 supported 통과")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--demo"]:
        demo()
        return 0
    if len(args) != 2:
        print(__doc__)
        return 2
    try:
        report = verify(args[0], args[1])
    except (OSError, ValueError) as exc:
        print(f"주장 검사 FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
