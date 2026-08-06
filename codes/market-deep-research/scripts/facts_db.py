"""facts_db.py — 사실/증거 대장의 원자적 read/append/validate + claim_key + diff.

설계(plan-v2 핵심설계1 + v3-B/E):
  - fact + evidence[] 증거모델. facts.jsonl / evidence.jsonl 분리 저장.
  - 스키마 검증은 assets/facts-schema.json 을 읽어 경량 수행(외부 jsonschema 의존 없음).
  - claim_key = 안정적 diff 키(순번 아님) → "조사마다 다른 수치"를 데이터로 검출.
  - 쓰기는 temp+os.replace 로 원자적(부분쓰기·중복ID 방지). 중앙 대장은 팀리드(단일 writer)가 G1 join 에서 기록.

CLI:
  python facts_db.py demo                 # self-check
  python facts_db.py validate <f.jsonl> <kind: fact|evidence>
  python facts_db.py diff <old.jsonl> <new.jsonl>
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from skill_paths import ASSETS, WorkPaths

_SCHEMA_PATH = ASSETS / "facts-schema.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


# --- 경량 검증 ---------------------------------------------------------------
class ValidationError(ValueError):
    pass


def _check_enum(val, enum_ref: str, enums: dict, field: str):
    allowed = enums.get(enum_ref, [])
    if val is not None and val not in allowed:
        raise ValidationError(f"{field}='{val}' 은 허용값 {allowed} 아님")


def _check_required(obj: dict, required: list[str], where: str):
    for k in required:
        if k not in obj or obj[k] in (None, "", []):
            raise ValidationError(f"{where}: 필수 필드 '{k}' 누락")


def validate_fact(fact: dict, schema: dict | None = None) -> dict:
    schema = schema or load_schema()
    enums = schema["enums"]
    spec = schema["fact"]
    _check_required(fact, spec["required"], "fact")

    fid = fact["id"]
    if not (isinstance(fid, str) and fid.startswith("F") and fid[1:].isdigit() and len(fid) >= 4):
        raise ValidationError(f"fact.id 형식 오류: {fid!r} (F### 이상)")

    _check_required(fact["context"], spec["properties"]["context"]["required"], "fact.context")
    _check_required(fact["value"], spec["properties"]["value"]["required"], "fact.value")
    _check_required(fact["grade"], spec["properties"]["grade"]["required"], "fact.grade")

    for dim in ("authority", "independence", "directness", "recency"):
        _check_enum(fact["grade"][dim], "grade", enums, f"fact.grade.{dim}")
    _check_enum(fact["risk"], "risk", enums, "fact.risk")
    _check_enum(fact["status"], "status", enums, "fact.status")
    b = fact["context"].get("basis")
    if b:
        _check_enum(b, "basis", enums, "fact.context.basis")
    # [v4] additive optional 필드 — 있으면 enum/형식 검증(없으면 통과, 레거시 대장 호환)
    if fact.get("dispute_kind"):
        _check_enum(fact["dispute_kind"], "dispute_kind", enums, "fact.dispute_kind")
    if fact.get("derivation"):
        _check_enum(fact["derivation"], "derivation", enums, "fact.derivation")
    sb = fact.get("superseded_by")
    if sb and not (isinstance(sb, str) and sb.startswith("F") and sb[1:].isdigit() and len(sb) >= 4):
        raise ValidationError(f"{fid}: superseded_by 형식 오류: {sb!r} (F### 이상)")

    # confirmed 는 최소 1 evidence + 팀리드 verify_event 필요(무출처 confirm 금지)
    if fact["status"] == "confirmed":
        if not fact.get("evidence_ids"):
            raise ValidationError(f"{fid}: confirmed 인데 evidence_ids 비어있음")
        events = fact.get("verify_events") or []
        lead_events = [e for e in events if e.get("by") == "lead"]
        if not lead_events:
            raise ValidationError(f"{fid}: confirmed 인데 팀리드(lead) verify_event 없음")
        # G4: status 전이 무제약 차단 — 반박이 기록됐거나 폐기 사유가 남은 채로,
        # 또는 강등 이후 새 lead 재검증 없이 confirmed 로 (재)승급하는 것을 막는다.
        cs = fact.get("counter_search") or {}
        if cs.get("found_stronger_refutation"):
            raise ValidationError(f"{fid}: 더 강한 반박(counter_search)이 기록된 채 confirmed 불가")
        if fact.get("discard_reason"):
            raise ValidationError(f"{fid}: 폐기 사유가 남은 채 confirmed 불가(discard_reason 미해제)")
        demoted_at = fact.get("demoted_at")
        if demoted_at and max((e.get("at") or "" for e in lead_events)) <= demoted_at:
            raise ValidationError(
                f"{fid}: 강등({demoted_at}) 이후 새 lead verify_event 없이 confirmed 재승급 불가")
    return fact


def check_capture_path(capture: str, work: WorkPaths | None = None) -> str | None:
    """capture 경로 신뢰경계 판정 — 위반 있으면 사유 문자열, 없으면 None.
    재구성 발췌(_reconstructed/)는 SKILL.md·evidence-capture.md·verification-gates.md 세 곳이
    '증빙 불인정'으로 규정하므로 경로 어디에 있든 즉시 거부. work 가 있으면 정규화 경로가
    작업폴더의 캡처 디렉터리(_captures/) 하위가 아닌 것도 거부(절대경로·../ 탈출 포함) —
    resolve()+relative_to 는 manifest.py·install.py 가 이미 쓰는 관행이라 그대로 따른다."""
    if not capture:
        return None
    if "_reconstructed" in Path(capture).as_posix().split("/"):
        return "재구성 발췌(_reconstructed/)는 증빙 불인정"
    if work is None:
        return None
    p = Path(capture)
    target = p.resolve() if p.is_absolute() else (work.root / p).resolve()
    try:
        target.relative_to(work.captures.resolve())
    except ValueError:
        return f"작업폴더 캡처 디렉터리(_captures/) 밖: {capture}"
    return None


def validate_evidence(ev: dict, schema: dict | None = None, work: WorkPaths | None = None) -> dict:
    schema = schema or load_schema()
    enums = schema["enums"]
    spec = schema["evidence"]
    _check_required(ev, spec["required"], "evidence")

    eid = ev["id"]
    if not (isinstance(eid, str) and eid.startswith("E") and eid[1:].isdigit() and len(eid) >= 4):
        raise ValidationError(f"evidence.id 형식 오류: {eid!r} (E### 이상)")
    fid = ev.get("fact_id")
    if not (isinstance(fid, str) and fid.startswith("F") and fid[1:].isdigit() and len(fid) >= 4):
        raise ValidationError(f"{eid}: evidence.fact_id 형식 오류: {fid!r} (F### 이상)")
    _check_enum(ev["type"], "evidence_type", enums, "evidence.type")
    if ev.get("source_role"):
        _check_enum(ev["source_role"], "source_role", enums, "evidence.source_role")
    if ev.get("verdict"):
        _check_enum(ev["verdict"], "evidence_verdict", enums, "evidence.verdict")
    if ev["type"] == "text_quote" and not ev.get("verbatim"):
        raise ValidationError(f"{eid}: text_quote 는 verbatim 필수")
    if ev.get("capture"):
        violation = check_capture_path(ev["capture"], work)
        if violation:
            raise ValidationError(f"{eid}: capture 신뢰경계 위반 — {violation}")
    return ev


# --- claim_key ---------------------------------------------------------------
def make_claim_key(context: dict) -> str:
    def norm(v):
        return str(v).strip().replace("|", "/") if v not in (None, "") else "na"
    parts = [context.get("metric"), context.get("entity"), context.get("geography"),
             context.get("period"), context.get("basis"), context.get("scenario")]
    return "|".join(norm(p) for p in parts)


# --- JSONL 원자적 저장 -------------------------------------------------------
def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            out.append(json.loads(ln))
    return out


def _write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)                      # 같은 볼륨 원자적 교체
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


class FactsDB:
    def __init__(self, work: WorkPaths | Path | str):
        self.wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
        self.schema = load_schema()

    def facts(self) -> list[dict]:
        return _read_jsonl(self.wp.facts)

    def evidence(self) -> list[dict]:
        return _read_jsonl(self.wp.evidence)

    def _next_id(self, rows: list[dict], prefix: str) -> str:
        n = 0
        for r in rows:
            rid = r.get("id", "")
            if rid.startswith(prefix) and rid[1:].isdigit():
                n = max(n, int(rid[1:]))
        return f"{prefix}{n + 1:03d}"

    def add_fact(self, fact: dict) -> dict:
        """검증 후 원자적 등재. id 없으면 부여. 같은 claim_key 있으면 예외(merge 는 명시적으로)."""
        rows = self.facts()
        fact.setdefault("claim_key", make_claim_key(fact.get("context", {})))
        fact.setdefault("id", self._next_id(rows, "F"))
        fact.setdefault("status", "pending")
        fact.setdefault("evidence_ids", [])
        fact.setdefault("verify_events", [])
        validate_fact(fact, self.schema)
        if any(r["id"] == fact["id"] for r in rows):
            raise ValidationError(f"중복 fact.id: {fact['id']}")
        if any(r.get("claim_key") == fact["claim_key"] for r in rows):
            raise ValidationError(
                f"동일 claim_key 존재: {fact['claim_key']} → merge_evidence/set_status 사용")
        rows.append(fact)
        _write_jsonl_atomic(self.wp.facts, rows)
        return fact

    def add_evidence(self, ev: dict) -> dict:
        """검증 후 등재 + 연결된 fact 의 evidence_ids 갱신. fact_id 가 대장에 없으면 거부
        (G4: orphan evidence 가 evidence.jsonl 에만 조용히 쌓이던 구멍 차단) — 쓰기 전에 확인."""
        rows = self.evidence()
        ev.setdefault("id", self._next_id(rows, "E"))
        ev.setdefault("accessed_at", _now())
        validate_evidence(ev, self.schema, self.wp)
        if any(r["id"] == ev["id"] for r in rows):
            raise ValidationError(f"중복 evidence.id: {ev['id']}")
        facts = self.facts()
        target = next((fr for fr in facts if fr["id"] == ev["fact_id"]), None)
        if target is None:
            raise ValidationError(f"{ev['fact_id']}: 존재하지 않는 fact_id — orphan evidence 거부")
        rows.append(ev)
        _write_jsonl_atomic(self.wp.evidence, rows)
        target.setdefault("evidence_ids", [])
        if ev["id"] not in target["evidence_ids"]:
            target["evidence_ids"].append(ev["id"])
        _write_jsonl_atomic(self.wp.facts, facts)
        return ev

    def add_verify_event(self, fact_id: str, by: str, action: str, note: str = "") -> None:
        facts = self.facts()
        for fr in facts:
            if fr["id"] == fact_id:
                fr.setdefault("verify_events", []).append(
                    {"by": by, "at": _now(), "action": action, "note": note})
                _write_jsonl_atomic(self.wp.facts, facts)
                return
        raise ValidationError(f"fact 없음: {fact_id}")

    def set_status(self, fact_id: str, status: str, reason: str | None = None) -> dict:
        facts = self.facts()
        for fr in facts:
            if fr["id"] == fact_id:
                if fr.get("status") == "confirmed" and status != "confirmed":
                    fr["demoted_at"] = _now()      # G4: 강등 시각 기록 → 재승급엔 그 이후 lead 재검증 요구
                if status == "discarded":
                    if reason:
                        fr["discard_reason"] = reason
                else:
                    fr["discard_reason"] = None    # discarded 아닌 상태로 옮기면 폐기 사유 해제
                fr["status"] = status
                validate_fact(fr, self.schema)
                _write_jsonl_atomic(self.wp.facts, facts)
                return fr
        raise ValidationError(f"fact 없음: {fact_id}")


# --- 재조사 diff (claim_key 기준) --------------------------------------------
def diff_facts(old_path: Path | str, new_path: Path | str) -> dict:
    """이전/현재 facts.jsonl 을 claim_key 로 정렬해 '수치 변동/정의 변동/신규/제거' 검출."""
    old = {f.get("claim_key", f["id"]): f for f in _read_jsonl(Path(old_path))}
    new = {f.get("claim_key", f["id"]): f for f in _read_jsonl(Path(new_path))}
    report = {"value_changed": [], "definition_changed": [], "added": [], "removed": []}
    for k, nf in new.items():
        if k not in old:
            report["added"].append(k); continue
        of = old[k]
        if (of.get("value") or {}).get("raw") != (nf.get("value") or {}).get("raw"):
            report["value_changed"].append(
                {"claim_key": k, "old": of.get("value"), "new": nf.get("value")})
        if (of.get("context") or {}).get("definition") != (nf.get("context") or {}).get("definition"):
            report["definition_changed"].append(k)
    for k in old:
        if k not in new:
            report["removed"].append(k)
    return report


# --- CLI / self-check --------------------------------------------------------
def demo() -> None:
    import hashlib
    import tempfile as _tf
    from skill_paths import resolve_work_dir
    _h = lambda tag: hashlib.sha256(tag.encode()).hexdigest()  # 유효한 sha256 fixture 생성
    with _tf.TemporaryDirectory() as td:
        wd = resolve_work_dir("데모 주제", base=td)
        db = FactsDB(wd)
        wp = WorkPaths(wd)

        f = db.add_fact({
            "claim": "삼성전자 2024 연결기준 매출은 300.9조원",
            "context": {"metric": "revenue", "entity": "삼성전자", "geography": "KR",
                        "period": "2024", "as_of": "2025-03", "basis": "annual",
                        "definition": "연결기준 매출"},
            "value": {"raw": "300.9", "unit": "KRW_T", "decimal": "300900000000000"},
            "grade": {"authority": "A", "independence": "B", "directness": "A", "recency": "A"},
            "risk": "high",
        })
        assert f["id"] == "F001" and f["claim_key"].startswith("revenue|삼성전자|KR|2024")

        # 무출처 confirm 차단
        try:
            db.set_status("F001", "confirmed"); assert False, "무출처 confirm 이 통과됨"
        except ValidationError:
            pass

        # orphan evidence(존재하지 않는 fact_id) 거부 — G4
        try:
            db.add_evidence({"fact_id": "F999", "type": "table_cell",
                             "source_url": "https://x", "sha256": _h("orphan")})
            assert False, "orphan evidence 가 통과됨"
        except ValidationError:
            pass
        assert db.evidence() == [], "orphan evidence 가 파일에 남으면 안 됨"

        # capture 가 _captures/ 밖(작업폴더 탈출)이면 거부 — G4
        try:
            db.add_evidence({"fact_id": "F001", "type": "table_cell",
                             "source_url": "https://x", "sha256": _h("escape"),
                             "capture": "../../etc/passwd"})
            assert False, "작업폴더 밖 capture 경로가 통과됨"
        except ValidationError:
            pass

        db.add_evidence({
            "fact_id": "F001", "type": "table_cell",
            "source_url": "https://dart.fss.or.kr/x", "sha256": _h("F001-E001"),
            "locator": {"page": 12, "row": 3, "col": 2}, "source_role": "원출처",
        })
        db.add_verify_event("F001", by="lead", action="reread", note="DART 원문 표셀 재열람 일치")
        db.set_status("F001", "confirmed")
        assert db.facts()[0]["status"] == "confirmed"

        # text_quote 는 verbatim 필수
        try:
            db.add_evidence({"fact_id": "F001", "type": "text_quote",
                             "source_url": "https://x", "sha256": _h("noverbatim")})
            assert False, "verbatim 누락이 통과됨"
        except ValidationError:
            pass

        # G4: 반박이 기록된 채 confirmed 재승급 차단, 폐기 사유 남은 채 confirmed 차단,
        # 강등 이후 새 lead 재검증 없으면 재승급 차단 — 새 lead 재검증 추가 후엔 성공(긍정형 짝)
        db.set_status("F001", "disputed")
        facts = db.facts()
        fr = next(r for r in facts if r["id"] == "F001")
        fr["counter_search"] = {"query": "정정 검색", "result": "더 강한 반박 발견",
                                 "found_stronger_refutation": True}
        _write_jsonl_atomic(wp.facts, facts)
        try:
            db.set_status("F001", "confirmed")
            assert False, "반박 기록된 채 confirmed 재승급이 통과됨"
        except ValidationError:
            pass
        # 반박 해제 + 폐기 사유 없이 새 lead 재검증 추가 → 재승급 성공
        facts = db.facts()
        fr = next(r for r in facts if r["id"] == "F001")
        fr["counter_search"]["found_stronger_refutation"] = False
        _write_jsonl_atomic(wp.facts, facts)
        # _now() 가 초 단위라 demoted_at 과 같은 초에 재검증하면 '이후'인지 판정이 흔들린다 —
        # 자동화 테스트에서 확실히 다음 초가 되게 잠깐 대기(운영 흐름에선 재조사 자체가 걸림).
        import time as _time; _time.sleep(1.1)
        db.add_verify_event("F001", by="lead", action="reread", note="재조사 후 재열람")
        db.set_status("F001", "confirmed")           # 긍정형 짝: 새 검증 있으면 재승급 성공
        assert db.facts()[0]["status"] == "confirmed"

        # diff: 같은 claim_key, 값만 변동
        old = Path(td) / "old.jsonl"; new = Path(td) / "new.jsonl"
        old.write_text(json.dumps({**f, "value": {"raw": "302.0", "unit": "KRW_T"}},
                                  ensure_ascii=False) + "\n", encoding="utf-8")
        new.write_text(json.dumps(f, ensure_ascii=False) + "\n", encoding="utf-8")
        d = diff_facts(old, new)
        assert d["value_changed"] and not d["added"], d
    print(f"[{_now()}] facts_db demo OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif args[0] == "validate" and len(args) == 3:
        rows = _read_jsonl(Path(args[1]))
        vf = validate_fact if args[2] == "fact" else validate_evidence
        for i, r in enumerate(rows):
            vf(r)
        print(f"OK: {len(rows)} {args[2]} rows valid")
    elif args[0] == "diff" and len(args) == 3:
        print(json.dumps(diff_facts(args[1], args[2]), ensure_ascii=False, indent=2))
    else:
        print(__doc__); sys.exit(2)
