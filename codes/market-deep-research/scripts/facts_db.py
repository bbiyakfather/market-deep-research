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

    # confirmed 는 최소 1 evidence + 팀리드 verify_event 필요(무출처 confirm 금지)
    if fact["status"] == "confirmed":
        if not fact.get("evidence_ids"):
            raise ValidationError(f"{fid}: confirmed 인데 evidence_ids 비어있음")
        events = fact.get("verify_events") or []
        if not any((e.get("by") == "lead") for e in events):
            raise ValidationError(f"{fid}: confirmed 인데 팀리드(lead) verify_event 없음")
    return fact


def validate_evidence(ev: dict, schema: dict | None = None) -> dict:
    schema = schema or load_schema()
    enums = schema["enums"]
    spec = schema["evidence"]
    _check_required(ev, spec["required"], "evidence")

    eid = ev["id"]
    if not (isinstance(eid, str) and eid.startswith("E") and eid[1:].isdigit() and len(eid) >= 4):
        raise ValidationError(f"evidence.id 형식 오류: {eid!r} (E### 이상)")
    _check_enum(ev["type"], "evidence_type", enums, "evidence.type")
    if ev.get("source_role"):
        _check_enum(ev["source_role"], "source_role", enums, "evidence.source_role")
    if ev["type"] == "text_quote" and not ev.get("verbatim"):
        raise ValidationError(f"{eid}: text_quote 는 verbatim 필수")
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
        """검증 후 등재 + 연결된 fact 의 evidence_ids 갱신."""
        rows = self.evidence()
        ev.setdefault("id", self._next_id(rows, "E"))
        ev.setdefault("accessed_at", _now())
        validate_evidence(ev, self.schema)
        if any(r["id"] == ev["id"] for r in rows):
            raise ValidationError(f"중복 evidence.id: {ev['id']}")
        rows.append(ev)
        _write_jsonl_atomic(self.wp.evidence, rows)
        # fact 연결
        facts = self.facts()
        for fr in facts:
            if fr["id"] == ev["fact_id"]:
                fr.setdefault("evidence_ids", [])
                if ev["id"] not in fr["evidence_ids"]:
                    fr["evidence_ids"].append(ev["id"])
                _write_jsonl_atomic(self.wp.facts, facts)
                break
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
                fr["status"] = status
                if status == "discarded" and reason:
                    fr["discard_reason"] = reason
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
    import tempfile as _tf
    from skill_paths import resolve_work_dir
    with _tf.TemporaryDirectory() as td:
        wd = resolve_work_dir("데모 주제", base=td)
        db = FactsDB(wd)

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

        db.add_evidence({
            "fact_id": "F001", "type": "table_cell",
            "source_url": "https://dart.fss.or.kr/x", "sha256": "abc",
            "locator": {"page": 12, "row": 3, "col": 2}, "source_role": "원출처",
        })
        db.add_verify_event("F001", by="lead", action="reread", note="DART 원문 표셀 재열람 일치")
        db.set_status("F001", "confirmed")
        assert db.facts()[0]["status"] == "confirmed"

        # text_quote 는 verbatim 필수
        try:
            db.add_evidence({"fact_id": "F001", "type": "text_quote",
                             "source_url": "https://x", "sha256": "z"})
            assert False, "verbatim 누락이 통과됨"
        except ValidationError:
            pass

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
