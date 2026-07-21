"""facts_db.py — facts.jsonl 원자적 read/append/validate + claim_key + evidence 병합.

facts.jsonl은 **단일 파일**. 각 라인 첫 필드 `kind`가 "fact"|"evidence"로 혼재한다.
검증 기준은 assets/facts-schema.json (draft 2020-12) — 이 스키마가 **단일 진실원천**이다.
jsonschema에 의존하지 않고(스킬 설치 환경에 없을 수 있음) 스키마 파일을 직접 해석하는
소형 재귀 검증기를 둔다.

주요 책임:
  - claim_key 생성(context → 안정적 diff 키)
  - G1 등재: run 단위 전역 순번 단일 채번(F%03d/E%03d) + 임시 ID 재매핑
  - status 전이 강제(pending 진입만 / confirmed는 evidence+lead reread 이벤트 필요)
  - 원자적 쓰기(임시파일+os.replace 전체 재작성, 중복 id 거부)
  - claim_key diff(값 변동 / 정의 변동 구분)

CLI:
    python facts_db.py --selfcheck
    python facts_db.py ingest <work_dir> <input.jsonl>
    python facts_db.py add-event <work_dir> <fact_id> --by lead --action reread --result match [...]
    python facts_db.py set-status <work_dir> <fact_id> <status> [--note ...] [--discard-reason ...]
    python facts_db.py diff <old_facts.jsonl> <new_facts.jsonl>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_paths  # noqa: E402  (import 시 UTF-8 콘솔 부트스트랩 1회)

import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import unicodedata  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from functools import lru_cache  # noqa: E402


class FactError(Exception):
    """스키마 위반·전이 거부·중복 id 등 등재 규칙 위반."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# --- 스키마 로드 ----------------------------------------------------------
@lru_cache(maxsize=1)
def load_schema() -> dict:
    p = skill_paths.skill_root() / "assets" / "facts-schema.json"
    return json.loads(p.read_text(encoding="utf-8"))


# --- 소형 JSON Schema 재귀 검증기 (facts-schema.json이 쓰는 부분집합만 해석) ---
# 지원 키워드: $ref(로컬), const, enum, type, pattern, minLength,
#              required, properties, items, allOf, anyOf, oneOf, if/then/else
def _resolve_ref(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise FactError(f"지원하지 않는 $ref: {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _type_ok(value, t) -> bool:
    if isinstance(t, list):
        return any(_type_ok(value, x) for x in t)
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    return True


def _validate(value, schema: dict, root: dict, path: str = "") -> list[str]:
    """스키마 위반 문자열 리스트 반환(빈 리스트=통과)."""
    if "$ref" in schema:
        return _validate(value, _resolve_ref(schema["$ref"], root), root, path)

    errs: list[str] = []
    if "const" in schema and value != schema["const"]:
        errs.append(f"{path or '.'}: const 불일치(기대 {schema['const']!r})")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path or '.'}: enum 위반({value!r} not in {schema['enum']})")
    if "type" in schema and not _type_ok(value, schema["type"]):
        errs.append(f"{path or '.'}: type 위반(기대 {schema['type']}, got {type(value).__name__})")
        return errs  # 타입 불일치면 하위 검사 무의미
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        errs.append(f"{path or '.'}: pattern 위반({value!r} !~ {schema['pattern']})")
    if "minLength" in schema and isinstance(value, str) and len(value) < schema["minLength"]:
        errs.append(f"{path or '.'}: minLength 위반(<{schema['minLength']})")

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path or '.'}: 필수필드 누락 '{req}'")
        for k, subs in schema.get("properties", {}).items():
            if k in value:
                errs += _validate(value[k], subs, root, f"{path}.{k}")
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errs += _validate(item, schema["items"], root, f"{path}[{i}]")

    for sub in schema.get("allOf", []):
        errs += _validate(value, sub, root, path)
    if "anyOf" in schema and not any(not _validate(value, s, root, path) for s in schema["anyOf"]):
        errs.append(f"{path or '.'}: anyOf 위반(매칭 branch 없음)")
    if "oneOf" in schema:
        matched = sum(1 for s in schema["oneOf"] if not _validate(value, s, root, path))
        if matched != 1:
            errs.append(f"{path or '.'}: oneOf 위반({matched}개 매칭)")
    if "if" in schema:
        if not _validate(value, schema["if"], root, path):
            if "then" in schema:
                errs += _validate(value, schema["then"], root, path)
        elif "else" in schema:
            errs += _validate(value, schema["else"], root, path)
    return errs


def validate_record(rec: dict, schema: dict | None = None) -> list[str]:
    """kind로 fact/evidence 하위 스키마를 골라 검증(정확한 오류 메시지)."""
    schema = schema or load_schema()
    kind = rec.get("kind")
    if kind not in ("fact", "evidence"):
        return [f"kind가 'fact'|'evidence' 아님: {kind!r}"]
    return _validate(rec, schema["$defs"][kind], schema)


# --- claim_key 생성 -------------------------------------------------------
# 순서 고정: metric|entity|geography|period|basis|scenario
_CK_FIELDS = ["metric", "entity", "geography", "period", "basis", "scenario"]
_CK_LOWER = {"metric", "basis", "geography"}


def _norm_field(name: str, raw) -> str:
    s = "" if raw is None else str(raw)
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s.strip())  # trim + 내부공백 단일화
    if name in _CK_LOWER:
        s = s.lower()
    s = s.replace("|", "／")  # 값 내 파이프는 전각 ／로 이스케이프(필드 경계 보호)
    return s or "_"


def make_claim_key(context: dict) -> str:
    context = context or {}
    return "|".join(_norm_field(f, context.get(f)) for f in _CK_FIELDS)


# --- 파일 I/O (원자적) ----------------------------------------------------
def facts_path(work) -> Path:
    return Path(work) / "facts.jsonl"


def load(path) -> list[dict]:
    recs = []
    # utf-8-sig: 다른 도구가 Windows에서 쓴 파일의 BOM을 관용(없으면 utf-8과 동일)
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def save_atomic(path, records: list[dict]) -> None:
    """임시파일+os.replace 전체 재작성. 중복 id는 거부(부분쓰기 방지)."""
    ids = [r.get("id") for r in records]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        raise FactError(f"중복 id append 거부: {dups}")
    path = Path(path)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def append_records(path, new_records: list[dict]) -> None:
    existing = load(path) if Path(path).exists() else []
    save_atomic(path, existing + new_records)  # dup 검사는 save_atomic 내부


# --- ID 채번/재매핑 -------------------------------------------------------
def _id_num(s: str) -> int:
    return int(s[1:]) if s and s[:1] in "FE" and s[1:].isdigit() else 0


def _max_ids(records: list[dict]) -> tuple[int, int]:
    fmax = emax = 0
    for r in records:
        i = r.get("id", "")
        if i.startswith("F"):
            fmax = max(fmax, _id_num(i))
        elif i.startswith("E"):
            emax = max(emax, _id_num(i))
    return fmax, emax


def ingest(work, input_records: list[dict]) -> dict:
    """G1 등재: 조사원 temp 스키마(agent-briefs.md §2)를 정식 스키마로 치환.

    temp-fact  {tid, evidence_tids, proposed_grade, ...} → {id, evidence_ids, grade, ...}
    temp-evid  {tid, fact_tid, proposed_grade, ...}       → {id, fact_id, grade, ...}

    run 단위 전역 순번 단일 채번(tid→F%03d/E%03d, 참조 재매핑) + proposed_grade→grade 승격
    + claim_key 생성 + status=pending → 정식 스키마 검증 → 원자적 append."""
    fpath = facts_path(work)
    existing = load(fpath) if fpath.exists() else []
    fmax, emax = _max_ids(existing)
    schema = load_schema()

    # 1차: temp id(tid) 채번(fact→F, evidence→E). 참조는 2차에서 이 표로 재매핑.
    remap: dict[tuple[str, str], str] = {}
    for rec in input_records:
        kind, tid = rec.get("kind"), rec.get("tid")
        if kind not in ("fact", "evidence"):
            raise FactError(f"kind가 'fact'|'evidence' 아님: {kind!r}")
        if not tid:
            raise FactError(f"temp 라인에 tid(임시 ID) 없음: {rec}")
        if kind == "fact":
            fmax += 1
            remap[("fact", tid)] = f"F{fmax:03d}"
        else:
            emax += 1
            remap[("evidence", tid)] = f"E{emax:03d}"

    # 2차: temp→정식 변환 후 정식 스키마로 검증(입력 원본 불변 — 깊은 복사)
    out = []
    for rec in input_records:
        r = json.loads(json.dumps(rec, ensure_ascii=False))
        if r["kind"] == "fact":
            rr = {
                "kind": "fact",
                "claim_key": make_claim_key(r.get("context", {})),
                "id": remap[("fact", r["tid"])],
                "claim": r.get("claim", ""),
                "context": r.get("context", {}),
                "value": r.get("value", {}),
                "grade": r.get("proposed_grade", {}),  # 조사원 제안을 초기 대표등급으로(팀리드가 G2 확정)
                "status": "pending",
                "verified_by": None,
                "verify_events": [],
                "evidence_ids": [remap.get(("evidence", et), et) for et in (r.get("evidence_tids") or [])],
                "discard_reason": None,
            }
        else:  # evidence: temp 필드 제거 + 정식 필드 승격
            rr = {k: v for k, v in r.items() if k not in ("tid", "fact_tid", "proposed_grade")}
            rr["kind"] = "evidence"
            rr["id"] = remap[("evidence", r["tid"])]
            rr["fact_id"] = remap.get(("fact", r.get("fact_tid")), r.get("fact_tid"))
            rr["grade"] = r.get("proposed_grade", {})  # 출처별 등급(필수) — 팀리드가 G2 확정
        errs = validate_record(rr, schema)
        if errs:
            raise FactError(f"스키마 위반({r['kind']} {r.get('tid')}): {'; '.join(errs)}")
        out.append(rr)

    save_atomic(fpath, existing + out)
    return {
        "added": len(out),
        "facts": sum(1 for r in out if r["kind"] == "fact"),
        "evidence": sum(1 for r in out if r["kind"] == "evidence"),
        "total": len(existing) + len(out),
    }


# --- status 전이 강제 -----------------------------------------------------
STATUSES = ["pending", "confirmed", "disputed", "superseded", "discarded"]


def _has_lead_reread_match(fact: dict) -> bool:
    return any(
        e.get("action") == "reread" and e.get("result") == "match" and e.get("by") == "lead"
        for e in fact.get("verify_events", [])
    )


def transition(fact: dict, new_status: str, *, by: str = "lead",
               note: str | None = None, discard_reason: str | None = None,
               at: str | None = None) -> dict:
    """status 전이 게이트. 위반 시 FactError."""
    if new_status not in STATUSES:
        raise FactError(f"알 수 없는 status: {new_status}")
    if new_status == "confirmed":
        if len(fact.get("evidence_ids") or []) < 1:
            raise FactError("confirmed 거부: evidence_ids 최소 1개 필요")
        if not _has_lead_reread_match(fact):
            raise FactError("confirmed 거부: lead의 {action:reread,result:match} verify_event 필요")
    if new_status in ("disputed", "superseded") and not (note and note.strip()):
        raise FactError(f"{new_status} 거부: note(사유) 필수")
    if new_status == "discarded" and not (discard_reason and discard_reason.strip()):
        raise FactError("discarded 거부: discard_reason 필수")

    fact["status"] = new_status
    if new_status == "confirmed":
        fact["verified_by"] = by
    if new_status == "discarded":
        fact["discard_reason"] = discard_reason
    # 전이 자체를 누적 이벤트로 기록(감사 추적)
    fact.setdefault("verify_events", []).append({
        "at": at or _now_iso(), "by": by, "action": f"status:{new_status}",
        "evidence_id": None, "source_url": None, "result": None,
        "note": note or discard_reason,
    })
    return fact


def _find_fact(records: list[dict], fact_id: str) -> dict:
    for r in records:
        if r.get("kind") == "fact" and r.get("id") == fact_id:
            return r
    raise FactError(f"fact 없음: {fact_id}")


def add_event(work, fact_id: str, event: dict) -> dict:
    fpath = facts_path(work)
    recs = load(fpath)
    fact = _find_fact(recs, fact_id)
    fact.setdefault("verify_events", []).append(event)
    save_atomic(fpath, recs)
    return fact


def set_status(work, fact_id: str, new_status: str, **kw) -> dict:
    fpath = facts_path(work)
    recs = load(fpath)
    fact = _find_fact(recs, fact_id)
    transition(fact, new_status, **kw)
    save_atomic(fpath, recs)
    return fact


def set_capture(work, evidence_id: str, capture_path: str) -> dict:
    """G2: capture_pdf가 만든 캡처 경로를 evidence.capture에 결박.
    파일 실재 확인 + _reconstructed(재구성 발췌=증빙 불인정) 경로 거부 + 스키마 재검증."""
    work = Path(work)
    fpath = facts_path(work)
    recs = load(fpath)
    ev = next((r for r in recs if r.get("kind") == "evidence" and r.get("id") == evidence_id), None)
    if ev is None:
        raise FactError(f"evidence 없음: {evidence_id}")
    cap = Path(capture_path)
    fs = cap if cap.is_absolute() else work / cap
    if "_reconstructed" in fs.parts:  # 재구성 발췌는 증빙 불인정
        raise FactError(f"_reconstructed 경로는 증빙 불인정(source_capture만 인정): {capture_path}")
    if not fs.is_file():
        raise FactError(f"capture 파일 부재: {capture_path}")
    # 작업폴더 내부면 상대 posix로 저장(local/manifest 규약과 일치)
    try:
        ev["capture"] = fs.resolve().relative_to(work.resolve()).as_posix()
    except ValueError:
        ev["capture"] = cap.as_posix()
    errs = validate_record(ev, load_schema())
    if errs:
        raise FactError(f"스키마 위반({evidence_id}): {'; '.join(errs)}")
    save_atomic(fpath, recs)
    return ev


# --- claim_key diff (값 변동 / 정의 변동) ---------------------------------
def _facts_by_key(records: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in records:
        if r.get("kind") == "fact":
            out.setdefault(r.get("claim_key", ""), r)  # 첫 등장 대표(중복 시 무시)
    return out


def diff(old_records: list[dict], new_records: list[dict]) -> dict:
    """이전/현재 facts를 claim_key 기준 대조.
    같은 claim_key에서 value.decimal 다르면 '값 변동',
    context.definition/basis 다르면 '정의 변동'으로 구분."""
    old = _facts_by_key(old_records)
    new = _facts_by_key(new_records)
    report = {"value_change": [], "definition_change": [], "added": [], "removed": []}
    for key in sorted(set(old) & set(new)):
        of, nf = old[key], new[key]
        o_dec = (of.get("value") or {}).get("decimal")
        n_dec = (nf.get("value") or {}).get("decimal")
        o_ctx, n_ctx = of.get("context") or {}, nf.get("context") or {}
        if o_dec != n_dec:
            report["value_change"].append({
                "claim_key": key, "old": o_dec, "new": n_dec,
                "old_id": of.get("id"), "new_id": nf.get("id"),
            })
        if (o_ctx.get("definition") != n_ctx.get("definition")
                or o_ctx.get("basis") != n_ctx.get("basis")):
            report["definition_change"].append({
                "claim_key": key,
                "old": {"definition": o_ctx.get("definition"), "basis": o_ctx.get("basis")},
                "new": {"definition": n_ctx.get("definition"), "basis": n_ctx.get("basis")},
            })
    report["added"] = sorted(set(new) - set(old))
    report["removed"] = sorted(set(old) - set(new))
    return report


# --- selfcheck ------------------------------------------------------------
def _selfcheck() -> int:
    import tempfile

    schema = load_schema()

    def valid_fact(fid="F001", **over):
        f = {
            "kind": "fact", "claim_key": "x", "id": fid, "claim": "요지",
            "context": {"metric": "revenue", "entity": "삼성전자", "geography": "KR",
                        "period": "2024", "basis": "annual"},
            "value": {"raw": "300.9", "unit": "KRW_T", "decimal": "300900000000000"},
            "grade": {"authority": "A", "independence": "B", "directness": "A", "recency": "A"},
            "status": "pending", "verified_by": None, "verify_events": [],
            "evidence_ids": [], "discard_reason": None,
        }
        f.update(over)
        return f

    sha = "a" * 64  # 유효한 SHA-256 형식(^[0-9a-f]{64}$)

    def valid_ev(eid="E001", **over):
        e = {
            "kind": "evidence", "id": eid, "fact_id": "F001", "type": "table_cell",
            "source_url": "https://example.com/x.pdf", "archived_url": None,
            "local": "_sources/x.pdf", "sha256": sha, "accessed_at": "2025-01-01T00:00:00+09:00",
            "http_status": 200, "locator": {"page": 12, "row": 3, "col": 2},
            "verbatim": None, "source_role": "원출처",
            "grade": {"authority": "A", "independence": "C", "directness": "A", "recency": "A"},
            "capture": None,
        }
        e.update(over)
        return e

    # ① 스키마 위반 append 거부
    assert validate_record(valid_fact(), schema) == [], validate_record(valid_fact(), schema)
    assert validate_record(valid_ev(), schema) == [], validate_record(valid_ev(), schema)
    # 필수필드 누락
    bad = valid_fact()
    del bad["value"]
    assert any("필수필드 누락 'value'" in e for e in validate_record(bad, schema))
    # 잘못된 enum
    bad = valid_fact()
    bad["grade"]["authority"] = "Z"
    assert any("enum 위반" in e for e in validate_record(bad, schema))
    bad = valid_fact(status="unknown")
    assert any("enum 위반" in e for e in validate_record(bad, schema))
    # text_quote인데 verbatim 없음
    bad = valid_ev(type="text_quote", locator={"page": 1}, verbatim=None)
    assert any("verbatim" in e for e in validate_record(bad, schema)), validate_record(bad, schema)
    # text_quote + verbatim 있으면 통과
    ok = valid_ev(type="text_quote", locator={"page": 1}, verbatim="원문 그대로")
    assert validate_record(ok, schema) == [], validate_record(ok, schema)
    # table_cell locator 필수키 누락(page/row/col)
    bad = valid_ev(type="table_cell", locator={"page": 1})
    assert any("필수필드 누락" in e for e in validate_record(bad, schema)), validate_record(bad, schema)
    # evidence.grade 필수(팀리드 결정: 출처별 4차원 등급)
    bad = valid_ev()
    del bad["grade"]
    assert any("필수필드 누락 'grade'" in e for e in validate_record(bad, schema)), validate_record(bad, schema)
    bad = valid_ev(grade={"authority": "A", "independence": "C", "directness": "A"})  # recency 누락
    assert any("필수필드 누락 'recency'" in e for e in validate_record(bad, schema)), validate_record(bad, schema)
    # sha256 조건부 필수: 외부 원문 참조 type은 저장 원본 해시 필수(null도 거부)
    for t, loc in (("table_cell", {"page": 1, "row": 1, "col": 1}),
                   ("text_quote", {"page": 1}),
                   ("chart", {"page": 1, "series": "s", "point": 1}),
                   ("api_response", {"endpoint": "/x", "params": {}, "json_path": "$.a", "response_sha256": "h"})):
        bad = valid_ev(type=t, locator=loc, verbatim="원문", sha256=None)
        assert any("sha256" in e for e in validate_record(bad, schema)), (t, validate_record(bad, schema))
    # sha256 형식 위반(64-hex 아님)도 거부
    bad = valid_ev(type="table_cell", sha256="notahash")
    assert any("pattern 위반" in e for e in validate_record(bad, schema)), validate_record(bad, schema)
    # negative_search/calculation은 sha256 선택(해시 대상 파일이 없음)
    ok = valid_ev(type="negative_search", locator={"query": "q", "scope": "s", "as_of": "2025"}, sha256=None)
    assert validate_record(ok, schema) == [], validate_record(ok, schema)
    ok = valid_ev(type="calculation", locator={"formula": "a+b", "inputs": ["F001", "F002"]}, sha256=None)
    assert validate_record(ok, schema) == [], validate_record(ok, schema)

    # ② 동일 id 재append 거부
    try:
        save_atomic(Path(tempfile.gettempdir()) / "nope.jsonl",
                    [valid_fact("F001"), valid_fact("F001")])
        raise AssertionError("중복 id인데 save_atomic이 통과함")
    except FactError as e:
        assert "중복 id" in str(e), e

    # ③ pending→confirmed: verify_event 없으면 거부, 있으면 허용
    f = valid_fact(evidence_ids=["E001"])
    try:
        transition(f, "confirmed")
        raise AssertionError("reread 이벤트 없는데 confirmed 통과")
    except FactError as e:
        assert "verify_event" in str(e), e
    f["verify_events"].append({"at": "t", "by": "lead", "action": "reread",
                               "evidence_id": "E001", "source_url": "u",
                               "result": "match", "note": None})
    transition(f, "confirmed")
    assert f["status"] == "confirmed" and f["verified_by"] == "lead", f
    # evidence 없으면 이벤트 있어도 거부
    f2 = valid_fact(evidence_ids=[])
    f2["verify_events"].append({"at": "t", "by": "lead", "action": "reread",
                                "result": "match"})
    try:
        transition(f2, "confirmed")
        raise AssertionError("evidence 0인데 confirmed 통과")
    except FactError as e:
        assert "evidence" in str(e), e
    # disputed는 note 필수, discarded는 discard_reason 필수
    try:
        transition(valid_fact(), "disputed")
        raise AssertionError("note 없는 disputed 통과")
    except FactError:
        pass
    try:
        transition(valid_fact(), "discarded")
        raise AssertionError("discard_reason 없는 discarded 통과")
    except FactError:
        pass
    d = valid_fact()
    transition(d, "discarded", discard_reason="원문 미확인")
    assert d["status"] == "discarded" and d["discard_reason"] == "원문 미확인"

    # ④ claim_key 생성 규칙(한글 entity·빈값 _·공백 정규화·소문자·이스케이프)
    ck = make_claim_key({"metric": "Revenue", "entity": " 삼성  전자 ", "geography": "KR",
                         "period": "2024", "basis": "Annual", "scenario": None})
    assert ck == "revenue|삼성 전자|kr|2024|annual|_", ck
    assert make_claim_key({}) == "_|_|_|_|_|_", make_claim_key({})
    assert make_claim_key({"metric": "a|b"}) == "a／b|_|_|_|_|_", make_claim_key({"metric": "a|b"})

    # ⑤ 동일 claim_key 값 변동 / 정의 변동 diff 구분
    old = [valid_fact("F001", claim_key="K1", value={"raw": "1", "decimal": "100"}),
           valid_fact("F002", claim_key="K2",
                      context={"metric": "m", "entity": "e", "geography": "g",
                               "period": "p", "basis": "annual", "definition": "별도"},
                      value={"raw": "5", "decimal": "500"})]
    new = [valid_fact("F010", claim_key="K1", value={"raw": "2", "decimal": "200"}),
           valid_fact("F011", claim_key="K2",
                      context={"metric": "m", "entity": "e", "geography": "g",
                               "period": "p", "basis": "annual", "definition": "연결"},
                      value={"raw": "5", "decimal": "500"})]
    dr = diff(old, new)
    assert [c["claim_key"] for c in dr["value_change"]] == ["K1"], dr["value_change"]
    assert [c["claim_key"] for c in dr["definition_change"]] == ["K2"], dr["definition_change"]

    # ⑥ 원자적 재작성 후 라인 수·순서 보존
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "facts.jsonl"
        recs = [valid_fact(f"F{i:03d}", claim_key=f"K{i}") for i in range(1, 6)]
        recs += [valid_ev(f"E{i:03d}") for i in range(1, 3)]
        save_atomic(fp, recs)
        got = load(fp)
        assert len(got) == len(recs), (len(got), len(recs))
        assert [r["id"] for r in got] == [r["id"] for r in recs], [r["id"] for r in got]

        # ingest: 조사원 temp 스키마(tid/fact_tid/evidence_tids/proposed_grade) → 정식 치환
        wd = Path(td) / "run"
        wd.mkdir()
        pg = {"authority": "A", "independence": "C", "directness": "A", "recency": "A"}
        inp = [
            {"kind": "fact", "tid": "TF001", "claim": "삼성 매출",
             "context": {"metric": "revenue", "entity": "삼성전자", "geography": "KR",
                         "period": "2024", "basis": "annual"},
             "value": {"raw": "300.9", "unit": "KRW_T", "decimal": "300900000000000"},
             "evidence_tids": ["TE001"], "proposed_grade": pg, "note": "IR 확인"},
            {"kind": "evidence", "tid": "TE001", "fact_tid": "TF001", "type": "text_quote",
             "source_url": "https://x", "accessed_at": "t", "locator": {"page": 1},
             "verbatim": "원문", "sha256": sha, "source_role": "원출처", "proposed_grade": pg},
        ]
        r1 = ingest(wd, inp)
        assert r1 == {"added": 2, "facts": 1, "evidence": 1, "total": 2}, r1
        recs2 = load(facts_path(wd))
        f_rec = next(r for r in recs2 if r["kind"] == "fact")
        e_rec = next(r for r in recs2 if r["kind"] == "evidence")
        # tid→정식 ID 채번, 참조(evidence_ids/fact_id) 재매핑
        assert f_rec["id"] == "F001" and e_rec["id"] == "E001", recs2
        assert f_rec["evidence_ids"] == ["E001"] and e_rec["fact_id"] == "F001", recs2
        # proposed_grade→grade 승격, temp 필드 제거, status pending, claim_key 생성
        assert f_rec["grade"] == pg and e_rec["grade"] == pg, recs2
        assert "tid" not in e_rec and "proposed_grade" not in e_rec and "fact_tid" not in e_rec, e_rec
        assert f_rec["status"] == "pending", f_rec["status"]
        assert f_rec["claim_key"] == make_claim_key(f_rec["context"]), f_rec["claim_key"]
        # 등재 결과가 정식 스키마를 만족(라운드트립)
        assert validate_record(f_rec, schema) == [] and validate_record(e_rec, schema) == []
        # 2차 ingest는 순번 이어받아 재매핑(TF001→F002)
        ingest(wd, [{"kind": "fact", "tid": "TF001", "claim": "c",
                     "context": {"metric": "m", "entity": "e", "geography": "g",
                                 "period": "p", "basis": "annual"},
                     "value": {"raw": "1"}, "evidence_tids": [], "proposed_grade": pg}])
        assert load(facts_path(wd))[-1]["id"] == "F002", load(facts_path(wd))[-1]["id"]
        # temp 라인에 tid 없으면 거부
        try:
            ingest(wd, [{"kind": "fact", "claim": "no tid"}])
            raise AssertionError("tid 없는 temp-fact ingest 통과")
        except FactError as e:
            assert "tid" in str(e), e
        # proposed_grade 없으면 정식 grade 누락 → 검증 거부
        try:
            ingest(wd, [{"kind": "fact", "tid": "TFX", "claim": "c",
                         "context": {"metric": "m", "entity": "e", "geography": "g",
                                     "period": "p", "basis": "annual"},
                         "value": {"raw": "1"}, "evidence_tids": []}])
            raise AssertionError("grade 없는 temp-fact ingest 통과")
        except FactError as e:
            assert "grade" in str(e), e

    # set_capture: 정상 결박 / 없는 evidence / _reconstructed 거부 / 파일 부재
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td)
        (wd / "_captures").mkdir()
        (wd / "_reconstructed").mkdir()
        (wd / "_captures" / "E001.png").write_bytes(b"png")
        (wd / "_reconstructed" / "E001.png").write_bytes(b"png")
        save_atomic(facts_path(wd), [valid_fact("F001", evidence_ids=["E001"]), valid_ev("E001")])
        # ① 정상 결박(작업폴더 상대 posix 저장)
        ev = set_capture(wd, "E001", "_captures/E001.png")
        assert ev["capture"] == "_captures/E001.png", ev["capture"]
        assert load(facts_path(wd))[1]["capture"] == "_captures/E001.png"
        # ② 없는 evidence 거부
        try:
            set_capture(wd, "E999", "_captures/E001.png")
            raise AssertionError("없는 evidence 통과")
        except FactError as e:
            assert "evidence 없음" in str(e), e
        # ③ _reconstructed 경로 거부(증빙 불인정)
        try:
            set_capture(wd, "E001", "_reconstructed/E001.png")
            raise AssertionError("_reconstructed 경로 통과")
        except FactError as e:
            assert "_reconstructed" in str(e), e
        # 파일 부재 거부
        try:
            set_capture(wd, "E001", "_captures/none.png")
            raise AssertionError("파일 부재 통과")
        except FactError as e:
            assert "부재" in str(e), e

    print("SELFCHECK OK")
    return 0


# --- CLI ------------------------------------------------------------------
def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="facts_db", description="facts.jsonl 데이터 모델")
    p.add_argument("--selfcheck", action="store_true", help="내부 자기검증")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("ingest", help="G1 등재(스키마검증·채번·재매핑)")
    sp.add_argument("work_dir")
    sp.add_argument("input_jsonl")

    sp = sub.add_parser("add-event", help="fact에 verify_event 추가")
    sp.add_argument("work_dir")
    sp.add_argument("fact_id")
    sp.add_argument("--by", default="lead")
    sp.add_argument("--action", required=True)
    sp.add_argument("--evidence-id", default=None)
    sp.add_argument("--source-url", default=None)
    sp.add_argument("--result", default=None)
    sp.add_argument("--note", default=None)
    sp.add_argument("--at", default=None)

    sp = sub.add_parser("set-status", help="status 전이(게이트 강제)")
    sp.add_argument("work_dir")
    sp.add_argument("fact_id")
    sp.add_argument("status", choices=STATUSES)
    sp.add_argument("--by", default="lead")
    sp.add_argument("--note", default=None)
    sp.add_argument("--discard-reason", default=None)

    sp = sub.add_parser("set-capture", help="evidence.capture 결박(파일 실재·_reconstructed 거부)")
    sp.add_argument("work_dir")
    sp.add_argument("evidence_id")
    sp.add_argument("capture_path")

    sp = sub.add_parser("diff", help="claim_key 기준 값/정의 변동 대조")
    sp.add_argument("old_jsonl")
    sp.add_argument("new_jsonl")

    args = p.parse_args(argv)
    if args.selfcheck:
        return _selfcheck()

    try:
        if args.cmd == "ingest":
            res = ingest(args.work_dir, load(args.input_jsonl))
            print(json.dumps(res, ensure_ascii=False, indent=2))
        elif args.cmd == "add-event":
            ev = {"at": args.at or _now_iso(), "by": args.by, "action": args.action,
                  "evidence_id": args.evidence_id, "source_url": args.source_url,
                  "result": args.result, "note": args.note}
            f = add_event(args.work_dir, args.fact_id, ev)
            print(f"이벤트 추가: {f['id']} (총 {len(f['verify_events'])}개)")
        elif args.cmd == "set-status":
            f = set_status(args.work_dir, args.fact_id, args.status, by=args.by,
                           note=args.note, discard_reason=args.discard_reason)
            print(f"{f['id']} → {f['status']}")
        elif args.cmd == "set-capture":
            ev = set_capture(args.work_dir, args.evidence_id, args.capture_path)
            print(f"{ev['id']} capture ← {ev['capture']}")
        elif args.cmd == "diff":
            rep = diff(load(args.old_jsonl), load(args.new_jsonl))
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            p.print_help()
    except FactError as e:
        print(f"FACT ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
