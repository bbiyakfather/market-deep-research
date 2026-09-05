"""Gate receipt journal for the market-deep-research pipeline.

The journal is deliberately append-only.  A receipt is evidence that a gate
was recorded (and, for script gates, that the script returned the recorded
exit code); it is not a replacement for the underlying artefacts.

CLI::

    python gates.py record G0 <work_dir> --evidence "..." --refs audit/research-plan.md
    python gates.py check G4 <work_dir>
    python gates.py status <work_dir>

The public ``record_script_result`` API refuses successful script-owned
receipts (G3/[4b]/G5). G3/[4b] owners execute their work before recording;
failed results and ownerless script gates remain publicly recordable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import uuid
import warnings
from datetime import datetime
from pathlib import Path
from typing import Iterable

from facts_db import ValidationError, _read_jsonl, confirmed_digest, is_v4_work, load_schema, validate_fact
from skill_paths import WorkPaths, resolve_work_dir


MANUAL_GATES = frozenset({"G0", "[2]", "G4"})

# 소유 스크립트가 자기기록하는 게이트 — 공개 API·CLI 성공 기록 불가(실패는 허용).
# (G3=verify_facts.py · [4b]=render_pdf.py · G5=manifest.py verify)
# 소유자가 있는 게이트의 손기록을 허용하면 스크립트를 돌리지 않은 영수증과
# 구분할 수 없다 — 위조 가능한 영수증은 영수증이 아니다.
SCRIPT_OWNED = frozenset({"G3", "[4b]", "G5"})
REVISION_GATES = frozenset({"[2]", "G2", "G3", "G5c", "[4]", "[4b]", "G4", "G5"})

# The order follows SKILL.md.  G4 also has a separate N8 plan-hash check
# against G0; keeping that check independent makes drift explicit in errors.
PREREQUISITES: dict[str, tuple[str, ...]] = {
    "G0": (),
    "G1": ("G0",),
    "[2]": ("G0", "G1"),
    "G2": ("[2]",),
    "G3": ("G1", "[2]"),
    "G5c": ("G3",),
    "[4]": ("G3",),
    "[4b]": ("G3",),
    "G4": ("[4b]",),
    "G5": ("G4",),
}


class GateError(RuntimeError):
    """A fail-closed journal or gate validation error."""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sha256_file(path: Path | str) -> str:
    """Return the SHA-256 digest of a file without loading it all at once."""
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(value: str | bytes) -> str:
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _work_paths(work: WorkPaths | Path | str) -> WorkPaths:
    return work if isinstance(work, WorkPaths) else WorkPaths(work)


def ledger_path(work: WorkPaths | Path | str) -> Path:
    """Return the canonical append-only ledger path for a work directory."""
    return _work_paths(work).audit / "gates.jsonl"


def normalize_gate(gate: str) -> str:
    value = str(gate).strip()
    if value == "2":
        value = "[2]"
    if not value or any(char in value for char in "\\/\r\n"):
        raise GateError(f"잘못된 gate 이름: {gate!r}")
    return value


def _read_records(work: WorkPaths | Path | str) -> list[dict]:
    path = ledger_path(work)
    if not path.exists():
        return []
    records: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GateError(f"원장 읽기 실패: {path} ({exc})") from exc
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GateError(f"원장 JSON 오류: {path}:{line_no}") from exc
        if not isinstance(record, dict) or not record.get("gate"):
            raise GateError(f"원장 레코드 형식 오류: {path}:{line_no}")
        if "exit" not in record or not isinstance(record["exit"], int):
            raise GateError(f"원장 exit 필드 오류: {path}:{line_no}")
        records.append(record)
    return records


def _append(work: WorkPaths | Path | str, record: dict) -> dict:
    wp = _work_paths(work)
    previous = _latest(_read_records(wp), record["gate"])
    record.update({"receipt_id": uuid.uuid4().hex, "run_id": uuid.uuid4().hex,
                   "revision_id": confirmed_digest(_read_jsonl(wp.facts)),
                   "input_digest": _input_digest(record.get("refs", [])),
                   "supersedes_receipt": _receipt_id(previous) if previous else None,
                   "code_sha256": _code_digest()})
    record["prerequisite_receipts"] = {
        gate: _receipt_id(prereq) for gate in PREREQUISITES.get(record["gate"], ())
        if (prereq := _latest(_read_records(wp), gate)) is not None}
    path = ledger_path(work)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        raise GateError(f"원장 append 실패: {path} ({exc})") from exc
    return record


def _receipt_id(record: dict) -> str:
    """ID 없는 과거 행도 원본을 바꾸지 않고 정규 JSON 해시로 참조한다."""
    return record.get("receipt_id") or sha256_text(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _input_digest(refs: list[dict]) -> str:
    return sha256_text(json.dumps(sorted(refs, key=lambda r: r["path"]),
                                  ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _code_digest() -> str:
    """미커밋 코드 변경도 구분하도록 실행 스크립트·스키마의 해시 묶음을 기록한다."""
    scripts = Path(__file__).resolve().parent
    paths = [*sorted(scripts.glob("*.py")), scripts.parent / "assets" / "facts-schema.json"]
    return sha256_text(json.dumps([(p.name, sha256_file(p)) for p in paths], separators=(",", ":")))


def _latest(records: Iterable[dict], gate: str) -> dict | None:
    found = [record for record in records if normalize_gate(record.get("gate", "")) == gate]
    return found[-1] if found else None


def _successful(record: dict | None) -> bool:
    return bool(record and record.get("exit") == 0)


def _resolve_ref(value: str | Path, wp: WorkPaths) -> tuple[Path, str]:
    raw = Path(value)
    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        # Work-directory-relative refs are the stable convention.  The cwd
        # fallback keeps the CLI usable when a caller passes a repo-relative
        # path while still preferring the actual investigation directory.
        candidate = (wp.root / raw).resolve()
        resolved = candidate if candidate.exists() else raw.resolve()
    try:
        stored = resolved.relative_to(wp.root.resolve()).as_posix()
    except ValueError:
        stored = str(resolved)
    return resolved, stored


def _refs_from_record(record: dict, wp: WorkPaths) -> list[str]:
    refs = record.get("refs") or []
    if not isinstance(refs, list):
        return ["refs 필드가 배열이 아님"]
    issues: list[str] = []
    for ref in refs:
        if not isinstance(ref, dict) or not ref.get("path") or not ref.get("sha256"):
            issues.append("refs 레코드 형식 오류")
            continue
        resolved, _ = _resolve_ref(ref["path"], wp)
        if ref["sha256"] == "missing":
            if resolved.exists():
                issues.append(f"refs 신규 입력 발생: {ref['path']}")
            continue
        if not resolved.is_file():
            issues.append(f"refs 경로 없음: {ref['path']}")
            continue
        try:
            actual = sha256_file(resolved)
        except OSError as exc:
            issues.append(f"refs 읽기 실패: {ref['path']} ({exc})")
            continue
        if actual.lower() != str(ref["sha256"]).lower():
            issues.append(f"refs 해시 불일치: {ref['path']}")
    return issues


def _plan_path(wp: WorkPaths, plan: Path | str | None = None) -> Path:
    if not plan:
        return wp.audit / "research-plan.md"
    raw = Path(plan)
    if raw.is_absolute():
        return raw
    candidate = wp.root / raw
    return candidate if candidate.exists() else raw


def _plan_digest(wp: WorkPaths, plan: Path | str | None = None) -> tuple[Path, str]:
    path = _plan_path(wp, plan)
    if not path.is_file():
        raise GateError(f"research-plan.md 없음: {path}")
    try:
        return path, sha256_file(path)
    except OSError as exc:
        raise GateError(f"research-plan.md 읽기 실패: {path} ({exc})") from exc


def _check_reverification(wp: WorkPaths) -> dict:
    """[2] 영수증은 기록이 아니라 계산이다(M1·HIGH-H): facts.jsonl 의 confirmed 전건에 lead reread 이벤트
    (+reread_sha256)가 있는지 validate_fact 로 검사하고, 결박용 다이제스트를 돌려준다."""
    if not wp.facts.is_file():
        raise GateError("[2] 재검증 선언인데 facts.jsonl 이 없음")
    rows = _read_jsonl(wp.facts)
    schema = load_schema()
    confirmed = [r for r in rows if r.get("status") == "confirmed"]
    for r in confirmed:
        try:
            validate_fact(r, schema)
        except ValidationError as exc:
            raise GateError(f"[2] 재검증 미완: {exc}") from exc
    return {"facts_db_sha256": sha256_file(wp.facts),
            "confirmed_digest_sha256": confirmed_digest(rows),
            "confirmed_count": len(confirmed)}


def _legacy_revision(record: dict, wp: WorkPaths) -> bool:
    """버전 없는 v3 대장과 구형 행만 예외. 새 형식 행의 revision 삭제는 허용하지 않는다."""
    return ("revision_id" not in record
            and not any(key in record for key in
                        ("receipt_id", "run_id", "input_digest", "supersedes_receipt",
                         "code_sha256", "prerequisite_receipts"))
            and all("schema_version" not in row
                    for row in [*_read_jsonl(wp.facts), *_read_jsonl(wp.evidence)]))


def _check_revision(record: dict, wp: WorkPaths, label: str) -> list[str]:
    if _legacy_revision(record, wp):
        warnings.warn(f"{label}: v3 구형 revision_id 없음 — 기존 결박 검사만 적용",
                      UserWarning, stacklevel=2)
        return []
    if record.get("revision_id") != confirmed_digest(_read_jsonl(wp.facts)):
        return [f"{label} revision_id 불일치/누락 — 재실행 필요"]
    return []


def _receipt_issues(record: dict, wp: WorkPaths) -> list[str]:
    """refs 재해시 + [2] 결박 다이제스트 대조. successful_receipt/require_receipt/check_gate 가 공유."""
    issues = _refs_from_record(record, wp)
    gate = normalize_gate(record.get("gate", ""))
    if gate == "G0":
        try:
            _, plan_sha = _plan_digest(wp, record.get("research_plan"))
            if plan_sha != record.get("research_plan_sha256"):
                issues.append("G0 계획 해시 드리프트 — 재실행 필요")
        except GateError as exc:
            issues.append(str(exc))
    if record.get("input_digest") and record["input_digest"] != _input_digest(record.get("refs", [])):
        issues.append("input_digest와 refs 해시 묶음 불일치")
    if gate in REVISION_GATES:
        issues.extend(_check_revision(record, wp, gate))
    records = _read_records(wp)
    for prerequisite, receipt_id in record.get("prerequisite_receipts", {}).items():
        # 원장 필드는 코드에 정의된 DAG의 간선만 허용해 순환 참조를 피한다.
        if prerequisite not in PREREQUISITES.get(gate, ()):
            issues.append(f"알 수 없는 선행 게이트 결박: {prerequisite}")
            continue
        current = _latest(records, prerequisite)
        if not current or _receipt_id(current) != receipt_id:
            issues.append(f"선행 {prerequisite} 영수증 교체 — {gate} 재실행 필요")
        elif not _successful(current) or _receipt_issues(current, wp):
            issues.append(f"선행 {prerequisite} 영수증 무효 — {gate} 재실행 필요")
    if normalize_gate(record.get("gate", "")) == "[2]":
        stored = record.get("confirmed_digest_sha256")
        if not stored:
            issues.append("[2] 영수증에 confirmed_digest 없음(구버전) — record [2] 재기록 필요")
        elif wp.facts.is_file() and confirmed_digest(_read_jsonl(wp.facts)).lower() != str(stored).lower():
            issues.append("[2] 영수증이 대장 confirmed 집합/값/재열람 이벤트와 불일치 — 재검증 후 record [2] 재기록")
    return issues


def successful_receipt(work: WorkPaths | Path | str, gate: str) -> dict | None:
    """Return the latest successful receipt for ``gate`` or ``None``.

    Referenced files are rehashed before a receipt is accepted.  This keeps a
    stale receipt from satisfying a later script gate.
    """
    wp = _work_paths(work)
    canonical = normalize_gate(gate)
    records = _read_records(wp)
    record = _latest(records, canonical)
    if not _successful(record):
        return None
    if _receipt_issues(record, wp):
        return None
    return record


def require_receipt(work: WorkPaths | Path | str, gate: str) -> dict:
    """Require a current, successful, untampered receipt for ``gate``."""
    wp = _work_paths(work)
    canonical = normalize_gate(gate)
    records = _read_records(wp)
    record = _latest(records, canonical)
    if not record:
        raise GateError(f"선행 게이트 영수증 없음: {canonical}")
    if not _successful(record):
        raise GateError(f"게이트 영수증이 PASS가 아님: {canonical} (exit={record.get('exit')})")
    issues = _receipt_issues(record, wp)
    if issues:
        raise GateError(f"게이트 영수증 무효: {canonical}; " + "; ".join(issues))
    return record


def check_prerequisites(work: WorkPaths | Path | str, gate: str) -> dict:
    """Check prerequisite receipts for a gate and N8 drift for G4.

    The gate being checked need not already have a receipt: this is the
    precondition check used immediately before recording/running that gate.
    """
    wp = _work_paths(work)
    canonical = normalize_gate(gate)
    records = _read_records(wp)
    issues: list[str] = []
    missing: list[str] = []
    for prerequisite in PREREQUISITES.get(canonical, ()):
        try:
            require_receipt(wp, prerequisite)
        except GateError as exc:
            missing.append(prerequisite)
            issues.append(str(exc))

    if canonical == "G4":
        g0 = _latest(records, "G0")
        if not _successful(g0):
            if "G0" not in missing:
                missing.append("G0")
                issues.append("선행 게이트 영수증 없음: G0")
        else:
            try:
                _, current_sha = _plan_digest(wp)
            except GateError as exc:
                issues.append(str(exc))
            else:
                recorded_sha = g0.get("research_plan_sha256")
                if not recorded_sha:
                    issues.append("G0 영수증에 research-plan.md 해시가 없음")
                elif current_sha.lower() != str(recorded_sha).lower():
                    issues.append(
                        "N8 계획 해시 드리프트: "
                        f"G0={recorded_sha} 현재={current_sha}"
                    )

    return {
        "ok": not issues,
        "gate": canonical,
        "missing": list(dict.fromkeys(missing)),
        "issues": list(dict.fromkeys(issues)),
        "prerequisites": list(PREREQUISITES.get(canonical, ())),
    }


def check_current_receipt(work: WorkPaths | Path | str, gate: str) -> dict:
    """기존 영수증의 현행성 검사. 실패는 재실행 신호이며 새 기록의 선행조건이 아니다."""
    wp = _work_paths(work)
    canonical = normalize_gate(gate)
    current = _latest(_read_records(wp), canonical)
    if not current:
        issues = [f"영수증 없음: {canonical}"]
    else:
        issues = _receipt_issues(current, wp)
        if not _successful(current):
            issues.append(f"{canonical} PASS 아님(exit={current.get('exit')})")
    return {"ok": not issues, "gate": canonical, "issues": issues,
            "state": "유효" if not issues else "재실행 필요", "receipt": current}


def check_gate(work: WorkPaths | Path | str, gate: str) -> dict:
    """CLI 진단은 선행조건과 기존 영수증을 모두 표시한다. 실행/재발급은 prerequisites만 쓴다."""
    checked = check_prerequisites(work, gate)
    current = check_current_receipt(work, gate)
    if current["receipt"]:
        checked["issues"].extend(current["issues"])
    checked["issues"] = list(dict.fromkeys(checked["issues"]))
    checked["ok"] = not checked["issues"]
    checked["state"] = "실행 가능" if checked["ok"] else "재실행 필요"
    return checked


def _flatten_refs(refs: Iterable[str] | None) -> list[str]:
    flattened: list[str] = []
    for value in refs or ():
        flattened.extend(part for part in str(value).split(",") if part.strip())
    return flattened


def record_manual(work: WorkPaths | Path | str, gate: str, evidence: str,
                  refs: Iterable[str] | None = None,
                  plan: Path | str | None = None) -> dict:
    """Append a manual G0/[2]/G4 receipt after fail-closed validation."""
    wp = _work_paths(work)
    canonical = normalize_gate(gate)
    if canonical not in MANUAL_GATES:
        raise GateError(f"수동 record 대상이 아님: {canonical} (G0/[2]/G4만 허용)")
    if not str(evidence).strip():
        raise GateError("evidence가 비어 있음")

    if canonical != "G0":
        checked = check_prerequisites(wp, canonical)
        if not checked["ok"]:
            raise GateError(f"{canonical} 선행조건 미충족: " + "; ".join(checked["issues"]))

    ref_rows: list[dict] = []
    for value in _flatten_refs(refs):
        resolved, stored = _resolve_ref(value, wp)
        if not resolved.is_file():
            raise GateError(f"refs 경로 없음: {value}")
        try:
            digest = sha256_file(resolved)
        except OSError as exc:
            raise GateError(f"refs 읽기 실패: {value} ({exc})") from exc
        ref_rows.append({"path": stored, "sha256": digest})

    record: dict = {
        "gate": canonical,
        "kind": "manual",
        "ts": _now(),
        "exit": 0,
        "evidence": str(evidence).strip(),
        "refs": ref_rows,
    }
    if canonical == "G0":
        plan_path, plan_sha = _plan_digest(wp, plan)
        try:
            plan_stored = plan_path.resolve().relative_to(wp.root.resolve()).as_posix()
        except ValueError:
            plan_stored = str(plan_path.resolve())
        record.update({"research_plan": plan_stored, "research_plan_sha256": plan_sha})
    if canonical == "[2]":
        record.update(_check_reverification(wp))
    return _append(wp, record)


def record_script_result(work: WorkPaths | Path | str, gate: str, exit_code: int,
                         result_summary: str | bytes = "",
                         facts_db: Path | str | None = None, *,
                         result_summary_sha256: str | None = None,
                         facts_db_sha256: str | None = None,
                         extra: dict | None = None) -> dict:
    """범용 기록 API: 소유 게이트의 성공은 소유 스크립트에서만 발급한다. 실패는 보존한다."""
    canonical = normalize_gate(gate)
    try:
        exit_value = int(exit_code)
    except (TypeError, ValueError) as exc:
        raise GateError(f"exit가 정수가 아님: {exit_code!r}") from exc
    if canonical in SCRIPT_OWNED and exit_value == 0:
        raise GateError(f"{canonical} 성공은 소유 스크립트만 기록 가능")
    return _record_script_result(
        work, canonical, exit_value, result_summary, facts_db,
        result_summary_sha256=result_summary_sha256,
        facts_db_sha256=facts_db_sha256, extra=extra)


def _record_owned_result(work: WorkPaths | Path | str, gate: str,
                         result_summary: str | bytes = "") -> dict:
    """G5 최종 검사·기록 경로. G3/[4b]는 소유 작업과 기록을 분리할 수 없다."""
    import manifest

    wp = _work_paths(work)
    canonical = normalize_gate(gate)
    if canonical not in SCRIPT_OWNED:
        raise GateError(f"소유 게이트가 아님: {canonical}")
    if canonical in {"G3", "[4b]"}:
        raise GateError(f"{canonical} 소유 작업 실행 필요 — "
                        "verify_facts.verify_and_record / render_pdf.render_and_record 사용")
    # 호환 진입점도 단일 출고 경로를 쓴다. 호출자의 성공 요약은 판정 근거가 아니다.
    result = manifest.finalize_report(wp)
    if not result["ok"]:
        raise GateError(f"G5 최종 검증 실패: {result}")
    return require_receipt(wp, "G5")


def _record_script_result(work: WorkPaths | Path | str, gate: str, exit_code: int,
                          result_summary: str | bytes = "",
                          facts_db: Path | str | None = None, *,
                          result_summary_sha256: str | None = None,
                          facts_db_sha256: str | None = None,
                          extra: dict | None = None,
                          _final_verification: dict | None = None,
                          _snapshot_hashes: dict | None = None) -> dict:
    """Append a script gate result.

    ``result_summary`` is normally the script's deterministic summary/output;
    callers may provide its already-computed digest through
    ``result_summary_sha256``.  ``facts_db`` defaults to the work directory's
    ``facts.jsonl`` and is recorded only when that file exists.
    ``extra`` holds binding fields an owning script wants later gates to
    re-check (e.g. ``manifest_sha256`` so [4b] can prove it extended the very
    baseline G3 sealed, not a rebuilt one).  Reserved record keys cannot be
    overridden.
    """
    wp = _work_paths(work)
    canonical = normalize_gate(gate)
    reserved = {"final_verification", "final_verification_sha256", "snapshot_hashes",
                "snapshot_sha256", "result_summary_sha256"}
    if reserved.intersection(extra or {}):
        raise GateError(f"extra 가 예약 필드를 덮어씀: {sorted(reserved.intersection(extra))}")
    # finalize 전용 입력이다. 같은 프로세스의 내부 API 호출은 보안 경계가 아니다.
    if _final_verification is not None:
        if canonical != "G5" or _snapshot_hashes is None or result_summary_sha256 is not None:
            raise GateError("최종 검증 결과는 G5 finalize 전용 입력이어야 함")
        result_summary = json.dumps(_final_verification, ensure_ascii=False, sort_keys=True)
    elif _snapshot_hashes is not None:
        raise GateError("스냅샷에는 최종 검증 결과가 필요함")
    try:
        exit_value = int(exit_code)
    except (TypeError, ValueError) as exc:
        raise GateError(f"exit가 정수가 아님: {exit_code!r}") from exc
    checked = check_prerequisites(wp, canonical)
    # v3의 독립 G1 join 기록 API는 보존한다. 후속 [2]는 여전히 G0·G1 모두 필요하다.
    legacy_join = (canonical == "G1" and not _latest(_read_records(wp), "G0")
                   and not is_v4_work(_read_jsonl(wp.facts), _read_jsonl(wp.evidence)))
    if exit_value == 0 and not checked["ok"] and not legacy_join:
        raise GateError(f"{canonical} 선행조건 미충족: " + "; ".join(checked["issues"]))
    if result_summary_sha256:
        summary_sha = str(result_summary_sha256)
    else:
        summary_sha = sha256_text(result_summary)

    if facts_db:
        raw_facts_path = Path(facts_db)
        facts_path = raw_facts_path if raw_facts_path.is_absolute() else wp.root / raw_facts_path
    else:
        facts_path = wp.facts
    if facts_db_sha256:
        facts_sha = str(facts_db_sha256)
    elif facts_path.is_file():
        facts_sha = sha256_file(facts_path)
    else:
        facts_sha = None

    record = {
        "gate": canonical,
        "kind": "script",
        "ts": _now(),
        "exit": exit_value,
        "result_summary_sha256": summary_sha,
        "facts_db_sha256": facts_sha,
    }
    if canonical == "G3":
        # 결과 파일이 아니라 검증 입력을 결박한다. 누락된 v3 검토 파일의 나중 추가도 드리프트다.
        record["refs"] = [{"path": rel, "sha256": sha256_file(wp.root / rel)
                           if (wp.root / rel).is_file() else "missing"}
                          for rel in ("facts.jsonl", "evidence.jsonl", "report.md", "audit/claim-review.jsonl",
                                      "audit/research-plan.md")]
    if _final_verification is not None:
        record.update(final_verification=_final_verification, snapshot_hashes=_snapshot_hashes,
                      snapshot_sha256=sha256_text(json.dumps(
                          _snapshot_hashes, ensure_ascii=False, sort_keys=True)))
    for key, value in (extra or {}).items():
        if key in record or key in {"receipt_id", "revision_id", "input_digest", "supersedes_receipt",
                                    "run_id", "code_sha256", "prerequisite_receipts"}:
            raise GateError(f"extra 가 예약 필드를 덮어씀: {key}")
        record[key] = value
    return _append(wp, record)


def status(work: WorkPaths | Path | str) -> dict:
    """영수증 진단과 판정시점 출고 상태를 표시한다. 실검증은 finalize에서만 수행한다."""
    import manifest

    wp = _work_paths(work)
    records = _read_records(wp)
    latest_by_gate: dict[str, dict] = {}
    completion_order: list[str] = []
    for record in records:
        canonical = normalize_gate(record["gate"])
        latest_by_gate[canonical] = record
        if record.get("exit") == 0:
            if canonical in completion_order:
                completion_order.remove(canonical)
            completion_order.append(canonical)
        elif canonical in completion_order:
            completion_order.remove(canonical)
    tail = records[-1] if records else None
    states = {gate: check_current_receipt(wp, gate) for gate in latest_by_gate}
    stale = [gate for gate in completion_order if not states[gate]["ok"]]
    completion_order = [gate for gate in completion_order if states[gate]["ok"]]
    finalization = manifest.publication_state(wp, latest_by_gate.get("G5"))
    if "G5" in completion_order and finalization["publication_state"] != "최종(판정시점)":
        completion_order.remove("G5")
        stale.append("G5")
        states["G5"].update(state="재실행 필요", issues=finalization["issues"])
    return {
        "ledger": str(ledger_path(wp)),
        "current_gate": tail.get("gate") if tail else None,
        "completed_gates": completion_order,
        "completed": completion_order,
        "facts_db": str(wp.facts),
        "tail": tail,
        "receipts": len(records),
        "rerun_required": stale,
        "publication_state": finalization["publication_state"],
        "finalization": finalization,
        "states": {gate: {"state": state["state"], "issues": state["issues"]}
                   for gate, state in states.items()},
    }


def _work_arg(parser: argparse.ArgumentParser, positional: str | None,
              option: str | None) -> Path:
    if positional and option and Path(positional).resolve() != Path(option).resolve():
        parser.error("work_dir와 --work-dir를 동시에 다르게 지정할 수 없음")
    return Path(option or positional or Path.cwd())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    rec = sub.add_parser("record", help="수동 G0/[2]/G4 영수증 append")
    rec.add_argument("gate")
    rec.add_argument("work_dir", nargs="?")
    rec.add_argument("--work-dir", dest="work_dir_opt")
    rec.add_argument("--evidence", required=True)
    rec.add_argument("--refs", nargs="+", action="append", default=[])
    rec.add_argument("--plan")

    chk = sub.add_parser("check", help="게이트 선행 영수증/N8 검사")
    chk.add_argument("gate")
    chk.add_argument("work_dir", nargs="?")
    chk.add_argument("--work-dir", dest="work_dir_opt")

    stat = sub.add_parser("status", help="원장 꼬리에서 상태 파생")
    stat.add_argument("work_dir", nargs="?")
    stat.add_argument("--work-dir", dest="work_dir_opt")

    script = sub.add_parser("record_script_result", help="스크립트 게이트 결과 append")
    script.add_argument("gate")
    script.add_argument("exit_code", type=int)
    script.add_argument("work_dir", nargs="?")
    script.add_argument("--work-dir", dest="work_dir_opt")
    script.add_argument("--summary", default="")
    script.add_argument("--facts-db")
    script.add_argument("--result-summary-sha256")
    script.add_argument("--facts-db-sha256")

    demo = sub.add_parser("demo", help="임시 폴더 자체 데모")
    demo.add_argument("--work-dir")
    return parser


def demo(base: Path | str | None = None) -> dict:
    """Exercise record/check/status, refs tamper detection, and N8 drift."""
    with tempfile.TemporaryDirectory(dir=str(base) if base else None) as td:
        wd = resolve_work_dir("gates-demo", base=td)
        wp = WorkPaths(wd)
        plan = wp.audit / "research-plan.md"
        ref = wp.audit / "evidence.txt"
        plan.write_text("# approved plan\n", encoding="utf-8")
        ref.write_text("evidence\n", encoding="utf-8")
        record_manual(wp, "G0", "approved", ["audit/evidence.txt"])
        assert check_gate(wp, "G0")["ok"]
        snapshot = status(wp)
        assert snapshot["current_gate"] == "G0"
        ref.write_text("tampered\n", encoding="utf-8")
        assert not check_gate(wp, "G0")["ok"], "refs 변조 미검출"
        ref.write_text("evidence\n", encoding="utf-8")
        wp.facts.write_text("", encoding="utf-8")
        record_script_result(wp, "G1", 0, "join PASS")
        record_manual(wp, "[2]", "lead reread")
        for gate in SCRIPT_OWNED:
            try:
                record_script_result(wp, gate, 0, "위조 시도")
            except GateError:
                pass
            else:
                raise AssertionError(f"{gate} 공개 API 성공 위조 미차단")
        plan.write_text("# drifted plan\n", encoding="utf-8")
        drift = check_gate(wp, "G4")
        assert not drift["ok"] and any("드리프트" in issue for issue in drift["issues"]), drift
        # 공개 API와 CLI 모두 성공 손기록을 차단한다.
        assert main(["record_script_result", "G3", "0", str(wd)]) == 1, "G3 CLI 손기록 미차단"
        assert main(["record_script_result", "G1", "1", str(wd), "--summary", "rejoin"]) == 0, \
            "무소유 게이트(G1) CLI 기록이 막힘"
        result = {"status": snapshot, "refs_tamper_detected": True,
                  "plan_drift_detected": True, "owned_gate_cli_blocked": True,
                  "owned_gate_api_blocked": True}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "record":
            work = _work_arg(parser, args.work_dir, args.work_dir_opt)
            result = record_manual(work, args.gate, args.evidence,
                                   [item for group in args.refs for item in group], args.plan)
        elif args.command == "check":
            work = _work_arg(parser, args.work_dir, args.work_dir_opt)
            result = check_gate(work, args.gate)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 1
        elif args.command == "status":
            work = _work_arg(parser, args.work_dir, args.work_dir_opt)
            result = status(work)
        elif args.command == "record_script_result":
            work = _work_arg(parser, args.work_dir, args.work_dir_opt)
            canonical = normalize_gate(args.gate)
            if canonical in SCRIPT_OWNED and args.exit_code == 0:
                raise GateError(
                    f"{canonical} 는 소유 스크립트만 기록 가능(CLI 손기록 금지): "
                    "G3=verify_facts.py · [4b]=render_pdf.py · G5=manifest.py verify")
            result = record_script_result(
                work, args.gate, args.exit_code, args.summary, args.facts_db,
                result_summary_sha256=args.result_summary_sha256,
                facts_db_sha256=args.facts_db_sha256,
            )
        elif args.command == "demo":
            result = demo(args.work_dir)
            return 0
        else:
            parser.print_help()
            return 2
    except (GateError, OSError, ValueError) as exc:
        print(f"GATE FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
