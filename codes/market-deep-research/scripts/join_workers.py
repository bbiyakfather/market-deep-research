"""워커 raw 마커·JSONL 검증과 중앙 등재용 재매핑 계획. 대장에는 쓰지 않는다.

python scripts/join_workers.py <raw.md> [<raw.md> ...] --out audit/join-results.json
python scripts/join_workers.py --demo

central_id=null은 팀리드의 add_fact/add_evidence 반환 ID로 채울 대기 칸이다.
지문은 중복 후보 신호이며, 리드 동등성·기존 웨이브 대비 신규 여부는 팀리드가 판단한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from facts_db import (ValidationError, load_schema, validate_fact, validate_evidence,
                      check_ledger_references, evidence_ids)

SECTIONS = ("EVIDENCE", "CLAIMS", "EXPAND", "FIGURES", "인사이트", "요약")
HEADING = re.compile(r"^##\s+(EVIDENCE(?:\s*\(JSONL\))?|CLAIMS|EXPAND|FIGURES|인사이트|요약)\s*$")
FACT_ID = re.compile(r"(?<![A-Za-z0-9_])F\d{3,}(?![A-Za-z0-9_])")
URL = re.compile(r"https?://[^\s<>\"`]+")


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().replace("**", "").split())


def _fingerprint(axis: str, lead: str) -> str:
    payload = json.dumps([_normalize(axis), _normalize(lead)], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sections(text: str, errors: list[dict]) -> dict[str, list[tuple[int, str]]]:
    result = {}
    current = None
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})", stripped)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        match = HEADING.fullmatch(stripped) if fence is None else None
        if match:
            current = match.group(1).split(" (")[0]
            if current.startswith("EVIDENCE"):
                current = "EVIDENCE"
            if current in result:
                errors.append({"line": number, "section": current, "message": "중복 섹션"})
            result.setdefault(current, [])
        elif current:
            result[current].append((number, line))
    if fence:
        errors.append({"section": current, "message": "닫히지 않은 코드 펜스"})
    return result


def validate_worker(text: str, source: str = "worker") -> dict:
    """파일 하나의 완전성·행별 스키마·잠정 참조를 검사한다. BLOCKED도 잘못된 행은 invalid."""
    text = text.lstrip("\ufeff")
    errors, notices = [], []
    lines = text.splitlines()
    blocked = bool(lines and lines[0].startswith("BLOCKED:"))
    reason = lines[0].partition(":")[2].strip() if blocked else None
    if blocked and not reason:
        errors.append({"line": 1, "message": "BLOCKED 사유 누락"})
    sections = _sections(text, errors)
    for name in SECTIONS:
        if name not in sections:
            if not blocked:
                errors.append({"section": name, "message": "필수 섹션 누락"})
        elif not any(line.strip() for _, line in sections[name]):
            errors.append({"section": name, "message": "빈 섹션: 결과가 없으면 없음 표기 필요"})

    schema = load_schema()
    records, facts, evidence = [], [], []
    remapping = {}

    def reference(rid, location, *, definition=False):
        if not isinstance(rid, str):
            return
        entry = remapping.setdefault(rid, {"temporary_id": rid, "scoped_id": f"{source}::{rid}",
            "central_id": None, "kind": "fact" if rid.startswith("F") else "evidence",
            "defined": False, "references": []})
        if definition and entry["defined"]:
            errors.append({"section": "EVIDENCE", "message": f"잠정 ID 중복: {rid}", **location})
        entry["defined"] |= definition
        entry["references"].append(location)

    for number, line in sections.get("EVIDENCE", []):
        if not line.strip() or line.strip() == "없음":
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("fact"), dict) or not isinstance(row.get("evidence"), list):
                raise ValidationError('행은 {"fact": {...}, "evidence": [...]} 형태여야 함')
            fact = row["fact"]
            validate_fact(fact, schema, warnings=notices)
            if fact["status"] != "pending":
                raise ValidationError("워커 fact는 status=pending으로 반환해야 함")
            for ev in row["evidence"]:
                if not isinstance(ev, dict):
                    raise ValidationError("evidence item: 타입 오류(object)")
                validate_evidence(ev, schema, warnings=notices)
                if ev["fact_id"] != fact["id"]:
                    raise ValidationError(f"{ev['id']}: 같은 행의 fact.id와 fact_id 불일치")
            records.append({**row, "line": number})
            facts.append(fact)
            evidence.extend(row["evidence"])
            reference(fact["id"], {"line": number, "field": "fact.id"}, definition=True)
            if isinstance(fact.get("primary_source_ref"), str) and re.fullmatch(r"E\d{3,}", fact["primary_source_ref"]):
                reference(fact["primary_source_ref"], {"line": number, "field": "fact.primary_source_ref"})
            for eid in fact.get("evidence_ids", []) if isinstance(fact.get("evidence_ids"), list) else []:
                reference(eid, {"line": number, "field": "fact.evidence_ids"})
            for ev in row["evidence"]:
                reference(ev["id"], {"line": number, "field": "evidence.id"}, definition=True)
                reference(ev["fact_id"], {"line": number, "field": "evidence.fact_id"})
        except (ValueError, TypeError, KeyError) as exc:
            errors.append({"section": "EVIDENCE", "line": number, "message": str(exc)})
    # pending 워커 fact의 역방향 목록은 중앙 add_evidence가 채운다. 명시된 잘못된 참조는 검출한다.
    forward_facts = [{**fact, "evidence_ids": list(dict.fromkeys([
        *evidence_ids(fact),
        *(ev["id"] for ev in evidence if ev["fact_id"] == fact["id"])]))} for fact in facts]
    ref_errors, ref_notices = check_ledger_references(forward_facts, evidence)
    errors.extend({"section": "EVIDENCE", "message": message} for message in ref_errors)
    notices.extend(ref_notices)
    for number, line in sections.get("인사이트", []):
        for fid in FACT_ID.findall(line):
            reference(fid, {"line": number, "field": "인사이트"})
    for entry in remapping.values():
        if not entry["defined"]:
            issue = {"message": f"정의 없는 잠정 ID 참조: {entry['temporary_id']}",
                     "references": entry["references"]}
            # BLOCKED 부분 결과의 미정의 참조는 보존하되, 완전 결과에서는 등재 전에 해소한다.
            # 대장 참조의 v3 WARN/v4 FAIL은 위 공통 검사에 맡긴다.
            blocking = not blocked and any(ref["field"] == "인사이트" for ref in entry["references"])
            (errors if blocking else notices).append(issue)

    leads, dead_ends = [], []
    for number, line in sections.get("EXPAND", []):
        stripped = line.strip()
        if not stripped or stripped == "없음":
            continue
        match = re.fullmatch(r"-\s*(LEAD|DEAD END):\s*(.+?)\s*—\s*AXIS:\s*([^—]+)(.*)", stripped)
        if not match or not match.group(2).strip() or not match.group(3).strip():
            errors.append({"section": "EXPAND", "line": number, "message": "LEAD/DEAD END와 AXIS 마커 필요"})
            continue
        kind, lead, axis, rest = match.groups()
        item = {"line": number, "lead": lead.strip(), "axis": axis.strip()}
        if kind == "DEAD END":
            dead_ends.append(item)
            continue
        item["fingerprint"] = _fingerprint(axis, lead)
        urls = sorted(set(url.rstrip(".,;)") for url in URL.findall(lead + " " + rest)))
        item["url_fingerprint"] = _fingerprint(axis, " ".join(urls)) if urls else None
        leads.append(item)
    verdict = "invalid" if errors else "blocked" if blocked else "ok"
    return {"file": source, "verdict": verdict, "blocked_reason": reason,
            "sections": list(sections), "errors": errors, "warnings": notices,
            "records": records, "id_remapping": list(remapping.values()),
            "expand": leads, "dead_ends": dead_ends}


def join_workers(paths: list[Path | str]) -> dict:
    """파일별 verdict와 파일 네임스페이스를 보존한다. 검증 실패 파일도 JSON 결과에 포함한다."""
    if not paths:
        raise ValueError("워커 raw 파일이 필요합니다")
    results = []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        try:
            result = validate_worker(path.read_text(encoding="utf-8-sig"), str(path))
        except (OSError, UnicodeError) as exc:
            result = {"file": str(path), "verdict": "invalid", "errors": [{"message": str(exc)}],
                      "warnings": [], "id_remapping": [], "expand": []}
        results.append(result)
    eligible = [result for result in results if result["verdict"] == "ok"]
    groups = {}
    for result in eligible:
        for lead in result["expand"]:
            for key in ("fingerprint", "url_fingerprint"):
                if lead.get(key):
                    groups.setdefault((key, lead[key]), []).append(
                        {"file": result["file"], "line": lead["line"], "lead": lead["lead"]})
    return {"ok": all(r["verdict"] != "invalid" for r in results), "files": results,
            "registration": "팀리드가 잠정 id와 evidence_ids를 제거하고 add_fact/add_evidence로 등재; "
                            "반환 ID로 central_id와 인사이트 등 references를 치환한다. 기존 claim_key는 명시적으로 병합한다.",
            "duplicate_leads": [{"kind": key, "fingerprint": digest, "occurrences": occurrences}
                                for (key, digest), occurrences in groups.items() if len(occurrences) > 1],
            "convergence": {"eligible_workers": [r["file"] for r in eligible],
                "excluded_workers": [r["file"] for r in results if r["verdict"] != "ok"],
                "lead_count": sum(len(r["expand"]) for r in eligible),
                "empty_expand_wave": len(eligible) == len(results) and all(not r["expand"] for r in eligible)}}


def demo() -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        paths = [Path(td) / name for name in ("ok.md", "blocked.md", "invalid.md")]
        paths[0].write_text("\n".join(f"## {section}\n없음" for section in SECTIONS), encoding="utf-8")
        paths[1].write_text("BLOCKED: timeout\n", encoding="utf-8")
        paths[2].write_text("## EVIDENCE\n없음\n", encoding="utf-8")
        result = join_workers(paths)
        assert [r["verdict"] for r in result["files"]] == ["ok", "blocked", "invalid"]
        assert not result["convergence"]["empty_expand_wave"]
        assert join_workers(paths[:1])["convergence"]["empty_expand_wave"]
    return {"demo": "join_workers", "ok": True, "verdicts": ["ok", "blocked", "invalid"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    if not args.demo and not args.files:
        parser.error("워커 raw 파일이 필요합니다")
    result = demo() if args.demo else join_workers(args.files)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
