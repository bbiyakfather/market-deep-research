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

import hashlib
import json
import os
import re
import sys
import tempfile
import warnings
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from skill_paths import ASSETS, WorkPaths

_SCHEMA_PATH = ASSETS / "facts-schema.json"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.I)


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


def _lead_reread_events(fact: dict) -> list[dict]:
    events = fact.get("verify_events")
    return [e for e in events if isinstance(e, dict)
            and e.get("by") == "lead" and e.get("action") == "reread"] if isinstance(events, list) else []


def schema_version(record: dict) -> int:
    """버전 생략은 v3. 알 수 없는 버전을 검증된 v3/v4로 취급하지 않는다."""
    version = record.get("schema_version", 3)
    if type(version) is not int or version not in (3, 4):
        raise ValidationError(f"schema_version: 지원하지 않는 버전 {version!r}")
    return version


def is_v4_work(facts: list[dict], evidence: list[dict] = ()) -> bool:
    """혼합 이행 폴더는 문장 검토를 v4로 강제하고 행별 기존 검사는 해당 버전을 따른다."""
    return any(r.get("schema_version") == 4 for r in [*facts, *evidence])


def valid_iso_time(value, *, timestamp: bool = False) -> bool:
    """시점은 YYYY / YYYY-MM / YYYY-MM-DD / ISO datetime, 이벤트는 datetime만 허용."""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return False
    try:
        if not timestamp:
            if re.fullmatch(r"\d{4}", value):
                date(int(value), 1, 1)
                return True
            if re.fullmatch(r"\d{4}-\d{2}", value):
                date.fromisoformat(value + "-01")
                return True
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                date.fromisoformat(value)
                return True
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", value):
            return False
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _check_properties(obj, spec: dict, enums: dict, where: str) -> None:
    """객체·배열 item에 같은 스키마 검증을 재귀 적용한다. bool은 number가 아니다."""
    kinds = {"string": lambda v: isinstance(v, str), "integer": lambda v: type(v) is int,
             "number": lambda v: type(v) in (int, float), "boolean": lambda v: type(v) is bool,
             "object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
             "null": lambda v: v is None}
    types = spec.get("type", "object" if "properties" in spec else [])
    types = [types] if isinstance(types, str) else types
    if types and not any(kinds[t](obj) for t in types):
        raise ValidationError(f"{where}: 타입 오류({types})")
    if "enum_ref" in spec:
        _check_enum(obj, spec["enum_ref"], enums, where)
    if "enum" in spec and obj not in spec["enum"]:
        raise ValidationError(f"{where}: 허용값 {spec['enum']} 아님")
    if obj is None:
        return
    if isinstance(obj, str):
        if (not obj.strip() and not spec.get("allowEmpty")) or len(obj) < spec.get("minLength", 0):
            raise ValidationError(f"{where}: 공백/빈 문자열 불가")
    if spec.get("pattern") and not re.fullmatch(spec["pattern"], str(obj)):
        raise ValidationError(f"{where}: 형식 오류")
    fmt = spec.get("format")
    if fmt in ("iso-time", "date-time") and not valid_iso_time(obj, timestamp=fmt == "date-time"):
        raise ValidationError(f"{where}: ISO 날짜/시각 형식 오류")
    if fmt == "decimal" or type(obj) in (int, float):
        try:
            if not Decimal(str(obj)).is_finite():
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            raise ValidationError(f"{where}: 유한 Decimal 값이 아님") from None
    if isinstance(obj, list):
        if len(obj) < spec.get("minItems", 0):
            raise ValidationError(f"{where}: 빈 배열 불가")
        for index, item in enumerate(obj):
            _check_properties(item, spec.get("items", {}), enums, f"{where}[{index}]")
    if isinstance(obj, dict):
        for key in spec.get("required", []):
            if key not in obj or obj[key] is None:
                raise ValidationError(f"{where}: 필수 필드 '{key}' 누락")
        for key, val in obj.items():
            rule = spec.get("properties", {}).get(key)
            if rule is None:
                if spec.get("additionalProperties") is False:
                    raise ValidationError(f"{where}: 알 수 없는 필드 '{key}'")
                continue
            _check_properties(val, rule, enums, f"{where}.{key}")


def _check_record(record: dict, spec: dict, enums: dict, where: str,
                  warnings: list[str] | None) -> None:
    try:
        _check_properties(record, spec, enums, where)
    except ValidationError as exc:
        if schema_version(record) == 4:
            raise
        if warnings is not None:
            warnings.append(f"[legacy스키마] {record.get('id')}: {exc}")


def validate_capture_review(review: dict, schema: dict | None = None) -> None:
    schema = schema or load_schema()
    spec = schema["evidence"]["properties"]["capture_review"]
    _check_properties(review, spec, schema["enums"], "capture_review")
    if review["verdict"] == "accept" and (review["page_state"] != "content"
            or not review["claim_visible"] or not review["context_visible"]):
        raise ValidationError("capture_review: accept는 content + 주장·문맥 확인이 필요")


def validate_fact(fact: dict, schema: dict | None = None, *, warnings: list[str] | None = None) -> dict:
    schema = schema or load_schema()
    enums = schema["enums"]
    spec = schema["fact"]
    _check_record(fact, spec, enums, "fact", warnings)
    if schema_version(fact) == 4:
        _check_required(fact, ["claim_type"], "fact v4")
        if fact.get("claim_key") != make_claim_key(fact["context"]):
            raise ValidationError("fact.claim_key: context 재계산 불일치")
        if fact.get("risk") == "high":
            from verify_calculations import is_calculation_candidate, ATOMIC_INPUTS
            if is_calculation_candidate(fact) and not any(
                    k in (fact.get("value") or {}) for k in ATOMIC_INPUTS):
                raise ValidationError(f"{fact.get('id')}: 고위험 시장 전망 원자화 미기록")
        if fact.get("status") == "confirmed":
            from verify_calculations import check_calculation, is_calculation_candidate
            if is_calculation_candidate(fact) and check_calculation(fact)["status"] == "CONFLICT":
                raise ValidationError(f"{fact.get('id')}: CAGR 계산 충돌이 남은 채 confirmed 불가")
    _check_required(fact, spec["required"], "fact")

    fid = fact["id"]
    if not (isinstance(fid, str) and fid.startswith("F") and fid[1:].isdigit() and len(fid) >= 4):
        raise ValidationError(f"fact.id 형식 오류: {fid!r} (F### 이상)")

    # v3 타입 경고가 다른 필드의 기존 필수 조건(특히 confirmed)을 면제하지 않도록 계속 검사한다.
    for key in ("context", "value", "grade"):
        if isinstance(fact[key], dict):
            _check_required(fact[key], spec["properties"][key]["required"], f"fact.{key}")

    if isinstance(fact["grade"], dict):
        for dim in ("authority", "independence", "directness", "recency"):
            _check_enum(fact["grade"][dim], "grade", enums, f"fact.grade.{dim}")
    _check_enum(fact["risk"], "risk", enums, "fact.risk")
    _check_enum(fact["status"], "status", enums, "fact.status")
    b = fact["context"].get("basis") if isinstance(fact["context"], dict) else None
    if b:
        _check_enum(b, "basis", enums, "fact.context.basis")

    # lead 재열람 이벤트는 재열람 산출물 해시(reread_sha256)가 있어야 한다 — by="lead" 는 누구나 쓸 수 있는
    # 관례라(M2·MEDIUM-2) 원문 미열람 자가신고를 구조적으로 막는다. 상태와 무관하게 형식은 항상 검사.
    for e in _lead_reread_events(fact):
        if not _SHA256_RE.match(str(e.get("reread_sha256") or "")):
            raise ValidationError(f"{fid}: lead reread 이벤트에 reread_sha256(64hex) 없음/형식오류")
    # confirmed 는 최소 1 evidence + 팀리드 reread verify_event 필요(무출처 confirm 금지)
    if fact["status"] == "confirmed":
        if not fact.get("evidence_ids"):
            raise ValidationError(f"{fid}: confirmed 인데 evidence_ids 비어있음")
        lead_events = _lead_reread_events(fact)
        if not lead_events:
            raise ValidationError(f"{fid}: confirmed 인데 팀리드(lead) reread verify_event 없음")
        # G4: status 전이 무제약 차단 — 반박이 기록됐거나 폐기 사유가 남은 채로,
        # 또는 강등 이후 새 lead 재검증 없이 confirmed 로 (재)승급하는 것을 막는다.
        cs = fact.get("counter_search") if isinstance(fact.get("counter_search"), dict) else {}
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


def validate_evidence(ev: dict, schema: dict | None = None, work: WorkPaths | None = None, *,
                      warnings: list[str] | None = None) -> dict:
    schema = schema or load_schema()
    enums = schema["enums"]
    spec = schema["evidence"]
    _check_record(ev, spec, enums, "evidence", warnings)
    if schema_version(ev) == 4:
        if ev.get("capture") and "capture_review" not in ev:
            raise ValidationError(f"{ev.get('id')}: v4 capture는 capture_review 필수")
        if "capture_review" in ev:
            validate_capture_review(ev["capture_review"], schema)
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
    if ev["type"] == "text_quote" and not ev.get("verbatim"):
        raise ValidationError(f"{eid}: text_quote 는 verbatim 필수")
    if ev.get("capture"):
        violation = check_capture_path(ev["capture"], work)
        if violation:
            raise ValidationError(f"{eid}: capture 신뢰경계 위반 — {violation}")
    return ev


# --- claim_key ---------------------------------------------------------------
def make_claim_key(context: dict) -> str:
    """v4 키: 식별자·정의를 포함한 무손실 JSON의 SHA-256. null과 문자열도 구분한다."""
    fields = ("metric", "entity", "entity_id", "geography", "period", "basis", "scenario", "definition")
    payload = json.dumps([context.get(k) for k in fields], ensure_ascii=False, separators=(",", ":"))
    return "v4:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _legacy_claim_key(context: dict) -> str:
    """기존 v3 생성 산식은 이행 중 그대로 유지한다."""
    def norm(v):
        return str(v).strip().replace("|", "/") if v not in (None, "") else "na"
    parts = [context.get("metric"), context.get("entity"), context.get("geography"),
             context.get("period"), context.get("basis"), context.get("scenario")]
    return "|".join(norm(p) for p in parts)


# --- JSONL 원자적 저장 -------------------------------------------------------
def evidence_ids(fact: dict) -> list[str]:
    value = fact.get("evidence_ids")
    return [eid for eid in value if isinstance(eid, str)] if isinstance(value, list) else []


def check_ledger_references(facts_raw: list[dict], evidence_raw: list[dict]) -> tuple[list[str], list[str]]:
    """N10 양방향 참조 검사. 로드 fsck와 G3가 같은 규칙(v4 FAIL/v3 WARN)을 쓴다."""
    failures, notices = [], []
    facts = {f["id"]: f for f in facts_raw if isinstance(f, dict) and isinstance(f.get("id"), str)}
    evidence = {e["id"]: e for e in evidence_raw if isinstance(e, dict) and isinstance(e.get("id"), str)}
    for fact in facts_raw:
        if not isinstance(fact, dict):
            continue
        for eid in evidence_ids(fact):
            ev = evidence.get(eid)
            strict = fact.get("schema_version") == 4 or (ev or {}).get("schema_version") == 4
            issues = failures if strict else notices
            if ev is None:
                issues.append(f"[증거유실] {fact.get('id')} → {eid} 없음")
            elif ev.get("fact_id") != fact.get("id"):
                issues.append(f"[증거역참조] {fact.get('id')} → {eid}의 fact_id={ev.get('fact_id')}")
    for ev in evidence_raw:
        if not isinstance(ev, dict):
            continue
        fact = facts.get(ev.get("fact_id")) if isinstance(ev.get("fact_id"), str) else None
        strict = ev.get("schema_version") == 4 or (fact or {}).get("schema_version") == 4
        if fact is None or ev.get("id") not in evidence_ids(fact):
            (failures if strict else notices).append(
                f"[증거역참조] {ev.get('id')} → {ev.get('fact_id')} 없거나 fact.evidence_ids에서 누락")
    return failures, notices


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            out.append(json.loads(ln))
    return out


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)                      # 같은 볼륨 원자적 교체
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    _write_bytes_atomic(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8"))


class FactsDB:
    def __init__(self, work: WorkPaths | Path | str):
        self.wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
        self.schema = load_schema()
        self.integrity = self.fsck()
        if self.integrity["failures"]:
            raise ValidationError("[대장fsck] FAIL: " + "; ".join(self.integrity["failures"]))
        for notice in self.integrity["warnings"]:
            warnings.warn("[대장fsck] WARN: " + notice, UserWarning, stacklevel=2)

    def fsck(self) -> dict:
        """원문·캡처 I/O 없는 경량 참조 검사. 전체 스키마 검사는 G3에서 수행한다."""
        failures, notices = check_ledger_references(self.facts(), self.evidence())
        return {"ok": not failures, "failures": failures, "warnings": notices}

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
        if not isinstance(fact.get("context", {}), dict):
            raise ValidationError("fact.context: 타입 오류(object)")
        key = (make_claim_key if schema_version(fact) == 4 else _legacy_claim_key)(fact.get("context", {}))
        if schema_version(fact) == 4 and "claim_key" in fact and fact["claim_key"] != key:
            raise ValidationError("fact.claim_key: context 재계산 불일치")
        fact.setdefault("claim_key", key)
        fact.setdefault("id", self._next_id(rows, "F"))
        fact.setdefault("status", "pending")
        fact.setdefault("evidence_ids", [])
        fact.setdefault("verify_events", [])
        validate_fact(fact, self.schema)
        if any(r["id"] == fact["id"] for r in rows):
            raise ValidationError(f"중복 fact.id: {fact['id']}")
        if any(r.get("claim_key") == fact["claim_key"] for r in rows):
            raise ValidationError(
                f"동일 claim_key 존재: {fact['claim_key']} → 기존 fact에 add_evidence로 증거 추가")
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
        target.setdefault("evidence_ids", [])
        if ev["id"] not in target["evidence_ids"]:
            target["evidence_ids"].append(ev["id"])
        # 단일 writer: 두 번째 쓰기 실패 시 선기록을 바이트 그대로 복원한다.
        # 프로세스 강제 종료/전원 장애 복구용 journal은 아니며, 재시작 fsck가 불일치를 드러낸다.
        preimage = self.wp.evidence.read_bytes() if self.wp.evidence.exists() else None
        _write_jsonl_atomic(self.wp.evidence, rows)
        try:
            _write_jsonl_atomic(self.wp.facts, facts)
        except BaseException as exc:
            try:
                if preimage is None:
                    self.wp.evidence.unlink(missing_ok=True)
                else:
                    _write_bytes_atomic(self.wp.evidence, preimage)
            except OSError as rollback_error:
                raise OSError(f"facts 저장 실패({exc}); evidence 롤백 실패 — 대장 복구 필요") from rollback_error
            raise
        return ev

    def add_verify_event(self, fact_id: str, by: str, action: str, note: str = "", *,
                         reread_sha256: str | None = None) -> None:
        if by == "lead" and action == "reread" and not _SHA256_RE.match(str(reread_sha256 or "")):
            raise ValidationError(f"{fact_id}: lead reread 이벤트는 reread_sha256(재열람 원문 해시 64hex) 필수 — "
                                  "fetch.py get 의 sha256 / 로컬 PDF 해시 / WebFetch verbatim 의 sha256_text")
        facts = self.facts()
        for fr in facts:
            if fr["id"] == fact_id:
                ev = {"by": by, "at": _now(), "action": action, "note": note}
                if reread_sha256:
                    ev["reread_sha256"] = reread_sha256.lower()
                fr.setdefault("verify_events", []).append(ev)
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


def confirmed_digest(rows: list[dict]) -> str:
    """v3 기존 confirmed 투영을 보존하고 v4의 confirmed/disputed 주장·맥락·원자값을 결박한다.
    evidence_ids·claim-graph 필드는 [2] 이후 G2·[Bx] 가 정상적으로 바꾸므로 제외(D4)."""
    proj = []
    for r in sorted((r for r in rows if r.get("status") == "confirmed" or
                     (r.get("schema_version") == 4 and r.get("status") == "disputed")),
                    key=lambda r: r.get("id", "")):
        v = r.get("value") if isinstance(r.get("value"), dict) else {}
        ev = sorted((e.get("at") or "", str(e.get("reread_sha256") or "").lower())
                    for e in _lead_reread_events(r))
        row = [r.get("id"), v.get("raw"), v.get("unit"), ev]
        if r.get("schema_version") == 4:
            # 원자화 값·조건·문장 유형 변경도 재검토 대상. v3의 기존 투영은 그대로 보존한다.
            row.append({"schema_version": 4, "value": v, "claim": r.get("claim"),
                        "context": r.get("context"), "claim_type": r.get("claim_type")})
            if r.get("status") == "disputed":
                row[-1]["status"] = "disputed"  # 기존 v4 confirmed 다이제스트는 유지한다.
        proj.append(row)
    return hashlib.sha256(json.dumps(proj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


# --- 재조사 diff (claim_key 기준) --------------------------------------------
def diff_facts(old_path: Path | str, new_path: Path | str) -> dict:
    """이전/현재 facts.jsonl 을 claim_key 로 정렬해 '수치 변동/정의 변동/신규/제거' 검출."""
    def index(path):
        rows = {}
        for fact in _read_jsonl(Path(path)):
            key = fact.get("claim_key", fact["id"])
            if key in rows:
                raise ValidationError(f"{path}: 중복 claim_key {key!r} — diff 입력 대장 정리 필요")
            rows[key] = fact
        return rows
    old, new = index(old_path), index(new_path)
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
        try:
            db.add_verify_event("F001", "lead", "reread"); assert False, "reread_sha256 없는 lead 이벤트가 통과됨"
        except ValidationError:
            pass
        db.add_verify_event("F001", by="lead", action="reread", note="DART 원문 표셀 재열람 일치",
                            reread_sha256=_h("F001-E001"))
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
        db.add_verify_event("F001", by="lead", action="reread", note="재조사 후 재열람",
                            reread_sha256=_h("F001-E001"))
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
