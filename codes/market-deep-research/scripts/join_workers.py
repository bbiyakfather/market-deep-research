"""워커 raw 마커·JSONL 검증과 중앙 등재용 재매핑 계획. 대장에는 쓰지 않는다.

python scripts/join_workers.py <raw.md> [<raw.md> ...] --out audit/join-results.json
python scripts/join_workers.py --demo
python scripts/join_workers.py coverage <work_dir>

central_id=null은 팀리드의 add_fact/add_evidence 반환 ID로 채울 대기 칸이다.
지문은 중복 후보 신호이며, 리드 동등성·기존 웨이브 대비 신규 여부는 팀리드가 판단한다.
coverage 하위 명령은 보고용이다. 공백이 있어도 종료 코드는 0이다.
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
                      check_ledger_references, evidence_ids, _read_jsonl)
from skill_paths import WorkPaths

SECTIONS = ("EVIDENCE", "CLAIMS", "EXPAND", "FIGURES", "인사이트", "요약")
HEADING = re.compile(
    r"^##\s+(EVIDENCE(?:\s*\(JSONL\))?|CLAIMS|EXPAND|FIGURES|인사이트|요약|COVERAGE)\s*$")
FACT_ID = re.compile(r"(?<![A-Za-z0-9_])F\d{3,}(?![A-Za-z0-9_])")
URL = re.compile(r"https?://[^\s<>\"`]+")
_BACKEND = r"ddg|searx|WebSearch|MCP:[^\s—]+"
QUERY_RE = re.compile(
    rf"^-\s*QUERY:\s*(.+?)\s*—\s*BACKEND:\s*({_BACKEND})\s*—\s*RESULT:\s*(\d+|BLOCKED|ERROR)\s*$")
GAP_RE = re.compile(
    r"^-\s*GAP:\s*(.+?)\s*—\s*STATE:\s*(NOT_FOUND|UNREACHABLE|NOT_ATTEMPTED)"
    r"\s*—\s*TRIED:\s*(\d+)\s*—\s*WHY:\s*(\S.*?)\s*$")
GAP_STATES = ("NOT_FOUND", "UNREACHABLE", "NOT_ATTEMPTED")
# fetch 로그 대조에서 빼는 증거. 웹 페이지를 다시 받을 대상이 아니다.
LOG_EXEMPT_EVIDENCE = {"api_response", "negative_search", "calculation"}


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().replace("**", "").split())


def _fingerprint(axis: str, lead: str) -> str:
    payload = json.dumps([_normalize(axis), _normalize(lead)], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_coverage(lines: list[tuple[int, str]], errors: list[dict]) -> tuple[list[dict], list[dict]]:
    """COVERAGE 줄 파싱. 형식 오류는 EXPAND 와 같이 errors 에 넣고 해당 줄만 건너뛴다."""
    queries, gaps = [], []
    if not any(line.strip() for _, line in lines):
        errors.append({"section": "COVERAGE", "message": "빈 섹션: 결과가 없으면 없음 표기 필요"})
        return queries, gaps
    for number, line in lines:
        stripped = line.strip()
        if not stripped or stripped == "없음":
            continue
        query = QUERY_RE.fullmatch(stripped)
        if query:
            queries.append({"line": number, "query": query.group(1).strip(),
                            "backend": query.group(2), "result": query.group(3)})
            continue
        gap = GAP_RE.fullmatch(stripped)
        if gap:
            gaps.append({"line": number, "target": gap.group(1).strip(), "state": gap.group(2),
                         "tried": int(gap.group(3)), "why": gap.group(4).strip()})
            continue
        errors.append({"section": "COVERAGE", "line": number, "message": "QUERY/GAP 마커 필요"})
    return queries, gaps


def _aggregate_coverage(results: list[dict]) -> dict:
    """파일별 질의 수·GAP·상태 집계. 섹션이 없는 파일은 missing 에만 넣고 invalid 로 만들지 않는다."""
    by_file, gaps, missing = [], [], []
    by_state = {state: 0 for state in GAP_STATES}
    for result in results:
        parsed = result.get("coverage") or {"present": False, "queries": [], "gaps": []}
        if not parsed.get("present"):
            missing.append(result["file"])
        states = {state: 0 for state in GAP_STATES}
        for gap in parsed.get("gaps") or []:
            state = gap.get("state")
            if state in states:
                states[state] += 1
                by_state[state] += 1
            gaps.append({**gap, "file": result["file"]})
        by_file.append({"file": result["file"], "queries": len(parsed.get("queries") or []),
                        "gaps": list(parsed.get("gaps") or []), "by_state": states})
    return {"by_file": by_file, "gaps": gaps, "by_state": by_state, "missing": missing}


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
    if "COVERAGE" in sections:
        queries, gaps = _parse_coverage(sections["COVERAGE"], errors)
        parsed_coverage = {"present": True, "queries": queries, "gaps": gaps}
    else:
        parsed_coverage = {"present": False, "queries": [], "gaps": []}
    verdict = "invalid" if errors else "blocked" if blocked else "ok"
    return {"file": source, "verdict": verdict, "blocked_reason": reason,
            "sections": list(sections), "errors": errors, "warnings": notices,
            "records": records, "id_remapping": list(remapping.values()),
            "expand": leads, "dead_ends": dead_ends, "coverage": parsed_coverage}


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
    coverage = _aggregate_coverage(results)
    return {"ok": all(r["verdict"] != "invalid" for r in results), "files": results,
            "registration": "팀리드가 잠정 id와 evidence_ids를 제거하고 add_fact/add_evidence로 등재; "
                            "반환 ID로 central_id와 인사이트 등 references를 치환한다. 기존 claim_key는 명시적으로 병합한다.",
            "duplicate_leads": [{"kind": key, "fingerprint": digest, "occurrences": occurrences}
                                for (key, digest), occurrences in groups.items() if len(occurrences) > 1],
            "coverage": coverage,
            "convergence": {"eligible_workers": [r["file"] for r in eligible],
                "excluded_workers": [r["file"] for r in results if r["verdict"] != "ok"],
                "lead_count": sum(len(r["expand"]) for r in eligible),
                "empty_expand_wave": len(eligible) == len(results) and all(not r["expand"] for r in eligible),
                "open_gaps": coverage["by_state"]["UNREACHABLE"] + coverage["by_state"]["NOT_ATTEMPTED"],
                "coverage_missing": len(coverage["missing"])}}


def _norm_label(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _split_labels(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,，、;/]", text) if part.strip()]


def _parse_universe(text: str) -> list[dict]:
    """audit/universe.md 표에서 데이터 행만 뽑는다. 포함/제외 필터는 호출자가 한다."""
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0] == "대상" or all(set(cell) <= set("-: ") and cell for cell in cells):
            continue
        rows.append({"name": cells[0], "aliases": _split_labels(cells[1]),
                     "sources": cells[2], "include": cells[3], "reason": cells[4]})
    return rows


def _fact_matches(fact: dict, target: dict) -> bool:
    """context.entity(쉼표 등으로 나뉜 조각 포함)가 대상명 또는 별칭과 같으면 그 대상의 사실로 센다."""
    if not isinstance(fact, dict):
        return False
    context = fact.get("context")
    entity = context.get("entity") if isinstance(context, dict) else None
    if not isinstance(entity, str) or not entity.strip():
        return False
    names = {_norm_label(target["name"])}
    names.update(_norm_label(alias) for alias in target["aliases"])
    names.discard("")
    pieces = [entity, *_split_labels(entity)]
    return any(_norm_label(piece) in names for piece in pieces if piece.strip())


def _norm_url(url: str) -> str:
    return url.strip().rstrip("/")


def _fetch_log_urls(path: Path) -> set[str]:
    found = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and isinstance(row.get("url"), str):
            found.add(_norm_url(row["url"]))
    return found


def _read_ledger(path: Path, notices: list[str], label: str) -> list[dict] | None:
    try:
        return _read_jsonl(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        notices.append(f"{label} 파싱 실패 — 해당 검사를 건너뜀: {exc}")
        return None


def coverage_report(work_dir: Path | str) -> dict:
    """포함 대상의 사실 0건·1건과 fetch-log 밖 증거 비율. 없는 파일은 그 검사만 건너뛴다."""
    root = Path(work_dir)
    wp = WorkPaths(root)
    notices: list[str] = []
    report = {"command": "coverage", "ok": True, "work_dir": str(root), "notices": notices,
              "included": [], "zero_facts": [], "single_fact": [], "counts": [], "fetch_log": None}
    if not root.is_dir():
        notices.append(f"작업폴더 없음: {root} — 검사를 건너뜀")
        return report

    universe = wp.audit / "universe.md"
    targets = None
    if not universe.is_file():
        notices.append("audit/universe.md 없음 — 대상 대조를 건너뜀")
    else:
        try:
            rows = _parse_universe(universe.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError) as exc:
            notices.append(f"audit/universe.md 읽기 실패 — 대상 대조를 건너뜀: {exc}")
            rows = None
        if rows is not None:
            if not rows:
                notices.append("audit/universe.md 에 표 행이 없음 — 대상 대조를 건너뜀")
            else:
                targets = [row for row in rows if row["include"] == "포함" and row["name"]]

    facts = None
    if not wp.facts.is_file():
        notices.append("facts.jsonl 없음 — 사실 건수 대조를 건너뜀")
    else:
        facts = _read_ledger(wp.facts, notices, "facts.jsonl")

    if targets is not None and facts is not None:
        for target in targets:
            count = sum(1 for fact in facts if _fact_matches(fact, target))
            report["included"].append(target["name"])
            report["counts"].append({"target": target["name"], "facts": count})
            if count == 0:
                report["zero_facts"].append(target["name"])
            elif count == 1:
                report["single_fact"].append(target["name"])

    if not wp.evidence.is_file():
        notices.append("evidence.jsonl 없음 — fetch-log 밖 증거 비율을 건너뜀")
        return report
    evidence = _read_ledger(wp.evidence, notices, "evidence.jsonl")
    if evidence is None:
        return report
    fetch_log = wp.audit / "fetch-log.jsonl"
    if not fetch_log.is_file():
        notices.append("audit/fetch-log.jsonl 없음 — fetch-log 밖 증거 비율을 건너뜀")
        return report
    try:
        logged = _fetch_log_urls(fetch_log)
    except (OSError, UnicodeError) as exc:
        notices.append(f"audit/fetch-log.jsonl 읽기 실패 — fetch-log 밖 증거 비율을 건너뜀: {exc}")
        return report
    checked = []
    for item in evidence:
        if not isinstance(item, dict) or item.get("type") in LOG_EXEMPT_EVIDENCE:
            continue
        url = item.get("source_url")
        if isinstance(url, str) and url.strip():
            checked.append(url.strip())
    missing = [url for url in checked if _norm_url(url) not in logged]
    ratio = round(len(missing) / len(checked), 4) if checked else None
    warning = None
    if missing:
        warning = (f"증거 URL {len(missing)}/{len(checked)} ({ratio:.0%}) 가 "
                   "audit/fetch-log.jsonl 에 없음")
        notices.append(warning)
    elif not checked:
        notices.append("fetch-log 대조 대상 증거 URL 이 없음(api_response·negative_search·calculation 제외)")
    report["fetch_log"] = {"evidence_urls": len(checked), "missing_urls": len(missing),
                           "missing_ratio": ratio, "warning": warning}
    return report


def _print_coverage(args: list[str]) -> int:
    if len(args) != 1:
        result = {"command": "coverage", "ok": True, "notices": [
            "사용법: python scripts/join_workers.py coverage <work_dir>"],
            "included": [], "zero_facts": [], "single_fact": [], "counts": [], "fetch_log": None}
    else:
        result = coverage_report(args[0])
    print(json.dumps(result, ensure_ascii=False, indent=2) + "\n", end="")
    return 0


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
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "coverage":
        return _print_coverage(argv[1:])
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
