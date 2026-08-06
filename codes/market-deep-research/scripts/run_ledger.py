"""run_ledger.py — 게이트 영수증 상태머신 【v4-L】 (AP1: run-ledger.jsonl append-only 대장).

목적: "보고서 완성" 선언을 진행 기억·산문이 아니라 기계 검증 가능한 영수증으로 강제한다.
11개 게이트(assets/gates.json 정본)마다 checkpoint 영수증을 남기고, watches 대상의
파일 sha256 + fact 단위 content-hash(claim_key→sha) 를 함께 봉인해 신선도
(fresh / partial_stale / stale / missing)를 사후 판정한다.
완료 선언 = 11개 게이트 전부 신선 PASS/WATCH(BLOCK 0). 산문은 상태를 변이하지 않는다.

레코드 스키마 정본(A4 — references 문서는 이 docstring 을 참조한다):
  checkpoint  {kind, gate, verdict, lane_verdicts[], evidence, blockers[], phase?,
               target_hashes{facts?, evidence?, report_md?, report_pdf?},
               fact_hashes{claim_key: content_sha}?, generation, at}
  steering    {kind, op: add_item|split_item|reorder|revise_wording|supersede_item|annotate,
               evidence, rationale, at}
  ask         {kind, ask_id, gate_id, question, options[], recommended?, supersedes?, at}
  answer      {kind, ask_id, answer, resolved_by: user|timeout, at}
  conflict    {kind, conflict_id, fact_ids[], sources[], at}
  disposition {kind, ref_id(conflict_id|finding_id), disposition, rationale, decided_by, at}
    - conflict 처분값: accept_a|accept_b|synthesize_range|defer_to_report_caveat|reject_both
    - 검증 발견 처분값: accept|rebut

기계 하한(floor) — checkpoint 시 스크립트가 대장을 직접 스캔, 요청 verdict 를 강제 하향:
  (b) confirmed 인데 evidence_ids 빈 배열 → BLOCK
  (c) 대장 스키마 위반 행 존재 → BLOCK. 단 evidence.jsonl 부재(=배치1 이전 레거시 단일
      대장)면 (c)는 WATCH + migration_required 사유로 강등(기존 조사 재개를 막지 않는다).

join 4상+1: G1 checkpoint 는 --phase 필수
  complete | awaiting_verification | failed | cancelled | blocked_partial
직전 G1 phase 가 failed|cancelled 면 후속(order 가 G1 초과) 게이트 checkpoint 거부.
generation 은 facts 파일 해시가 직전 기록과 달라질 때 +1 (동결 세대 카운터, AP6 연동).

출력 규약: 실패를 만나도 전 게이트/전 진단 검사 후 일괄 보고(통과 항목도
"위반: <none>" 형태로 출력) 후 exit code. 쓰기는 전부 append-only + 원자적
(facts_db 의 temp+os.replace 패턴 재사용). checkpoint/record 마다
audit/run-metadata.json 갱신(mode·completedAt·마지막 신선 게이트·fact 카운트) — 재개 진입점.

CLI:
  python run_ledger.py --work <dir> checkpoint <gate> --verdict PASS|WATCH|BLOCK \
      --evidence "..." [--phase ...] [--lane-verdict lane=token ...] [--blocker ...]
  python run_ledger.py --work <dir> status
  python run_ledger.py --work <dir> validate      # 읽기전용 사전검증 + audit 로스터(A3) 검사
  python run_ledger.py --work <dir> record <kind> [필드 옵션 ...]

exit code: 0=정상(PASS/WATCH 기록·no-op 포함) · 1=BLOCK 기록 또는 validate 위반 또는
answer 충돌 기록 · 2=거부(미기록: 미정의 게이트·phase 위반·활성 ask 중복 등)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from skill_paths import ASSETS, WorkPaths
from facts_db import (_read_jsonl, _write_jsonl_atomic, load_schema,
                      make_claim_key, validate_evidence, validate_fact)
from manifest import sha256_file

GATES_PATH = ASSETS / "gates.json"
LEDGER_NAME = "run-ledger.jsonl"
META_NAME = "run-metadata.json"

_SEV = {"PASS": 0, "WATCH": 1, "BLOCK": 2}
G1_PHASES = ("complete", "awaiting_verification", "failed", "cancelled", "blocked_partial")
_HALT_PHASES = ("failed", "cancelled")

STEERING_OPS = ("add_item", "split_item", "reorder", "revise_wording",
                "supersede_item", "annotate")
DISPOSITIONS = ("accept_a", "accept_b", "synthesize_range", "defer_to_report_caveat",
                "reject_both",           # conflict 처분
                "accept", "rebut")       # 검증 발견 처분

# audit 산출물 로스터(A3 고정 표면) — validate 가 missing/unexpected/legacy 3분류 검사.
ROSTER_REQUIRED = (
    "run-ledger.jsonl", "run-metadata.json", "quality-metrics.json",   # 스크립트 관리
    "bx-report.md", "g4-visual-check.md", "run-receipt.md",            # 사람용 보고
    "research-plan.md", "intent-diff.md", "expansion-log.md",          # 기존 유지
    "verification-economics.md", "cause-disappearance.md",
)
ROSTER_OPTIONAL = ("handoff.md",)          # draft-factsheet.md 는 작업폴더 루트(스캔 밖)
# 이벤트성 대장 신설 금지(A3) — 별도 파일로 남아 있으면 legacy 로 분류(레코드 kind 로 이관 대상)
ROSTER_LEGACY = ("asks.jsonl", "steering.jsonl", "conflicts.jsonl", "dispositions.jsonl")


class LedgerError(ValueError):
    pass


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _wp(work) -> WorkPaths:
    return work if isinstance(work, WorkPaths) else WorkPaths(work)


def _ledger_path(wp: WorkPaths) -> Path:
    return wp.journal(LEDGER_NAME)


def _meta_path(wp: WorkPaths) -> Path:
    return wp.journal(META_NAME)


def load_gates() -> list[dict]:
    return json.loads(GATES_PATH.read_text(encoding="utf-8"))["gates"]


def _read_ledger(wp: WorkPaths) -> list[dict]:
    return _read_jsonl(_ledger_path(wp))


def _write_json_atomic(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# --- 해시 ---------------------------------------------------------------------
def _canon_sha(obj: dict) -> str:
    import hashlib
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _fact_hashes(wp: WorkPaths) -> dict[str, str]:
    """fact 단위 content-hash 맵 — 신선도를 fact 단위로 판정하는 근거(claim_key→sha)."""
    out: dict[str, str] = {}
    for f in _read_jsonl(wp.facts):
        key = f.get("claim_key") or make_claim_key(f.get("context") or {})
        out[key] = _canon_sha(f)
    return out


def _watch_file(wp: WorkPaths, watch: str) -> Path:
    return {"facts": wp.facts, "report_md": wp.report_md, "report_pdf": wp.report_pdf}[watch]


def _target_hashes(wp: WorkPaths, watches: list[str]) -> dict[str, str]:
    th: dict[str, str] = {}
    for w in watches:
        p = _watch_file(wp, w)
        if p.exists():
            th[w] = sha256_file(p)
        if w == "facts" and wp.evidence.exists():
            th["evidence"] = sha256_file(wp.evidence)
    return th


# --- 기계 하한(floor) ---------------------------------------------------------
def _floor_scan(wp: WorkPaths) -> dict:
    """(b) confirmed 무증거 / (c) 스키마 위반 / legacy(evidence.jsonl 부재) 스캔."""
    schema = load_schema()
    b, c = [], []
    legacy = not wp.evidence.exists()
    for f in _read_jsonl(wp.facts):
        fid = f.get("id") or f.get("claim_key") or "?"
        if f.get("status") == "confirmed" and not f.get("evidence_ids"):
            b.append(str(fid))
        try:
            validate_fact(f, schema)
        except Exception as e:                    # 형식 파손 행도 위반으로 집계(전 진단 계속)
            c.append(f"{fid}: {e}")
    if not legacy:
        for ev in _read_jsonl(wp.evidence):
            try:
                validate_evidence(ev, schema, wp)
            except Exception as e:
                c.append(f"{ev.get('id', '?')}: {e}")
    return {"b": b, "c": c, "legacy": legacy}


def _print_floor(fl: dict) -> None:
    print(f"[floor(b)] confirmed 무증거 위반: {', '.join(fl['b']) or '<none>'}")
    tag = " (레거시 단일 대장 — migration_required 완화)" if fl["legacy"] and fl["c"] else ""
    print(f"[floor(c)] 대장 스키마 위반: {'; '.join(fl['c']) or '<none>'}{tag}")


def _clamp(requested: str, fl: dict, blockers: list[str]) -> str:
    """floor 위반을 blockers 에 적재하고 최종 verdict 를 하향 강제(상향은 없음)."""
    final = requested
    if fl["b"]:
        final = "BLOCK"
        blockers += [f"floor(b): {i} confirmed 인데 evidence_ids 빈 배열" for i in fl["b"]]
    if fl["c"]:
        if fl["legacy"]:
            if _SEV[final] < _SEV["WATCH"]:
                final = "WATCH"
            blockers.append(
                f"migration_required: 레거시 단일 대장(evidence.jsonl 부재) — 스키마 위반 {len(fl['c'])}행")
        else:
            final = "BLOCK"
            blockers += [f"floor(c): {i}" for i in fl["c"]]
    return final


# --- checkpoint ---------------------------------------------------------------
def checkpoint(work, gate_id: str, verdict: str, evidence: str, phase: str | None = None,
               lane_verdicts: list[dict] | None = None, blockers: list[str] | None = None,
               mode: str | None = None) -> dict:
    wp = _wp(work)
    gates = load_gates()
    gmap = {g["id"]: g for g in gates}
    ledger = _read_ledger(wp)
    fl = _floor_scan(wp)

    # 거부 사유는 모으되, 전 진단을 먼저 일괄 출력한다(첫 실패에서 멈추지 않는다).
    refusals: list[str] = []
    if verdict not in _SEV:
        refusals.append(f"verdict '{verdict}' 는 PASS|WATCH|BLOCK 아님")
    if gate_id not in gmap:
        refusals.append(f"미정의 게이트 id: {gate_id} (정본: assets/gates.json)")
    if gate_id == "G1" and phase not in G1_PHASES:
        refusals.append(f"G1 checkpoint 는 --phase 필수({'|'.join(G1_PHASES)}) — 현재: {phase}")
    g1_last = next((r for r in reversed(ledger)
                    if r.get("kind") == "checkpoint" and r.get("gate") == "G1"), None)
    if (gate_id in gmap and gmap[gate_id]["order"] > gmap["G1"]["order"]
            and g1_last and g1_last.get("phase") in _HALT_PHASES):
        refusals.append(
            f"직전 G1 phase={g1_last['phase']} — 후속 게이트 checkpoint 거부(G1 재수행 필요)")

    _print_floor(fl)
    print(f"[checkpoint 사전검사] 거부 사유: {'; '.join(refusals) or '<none>'}")
    if refusals:
        raise LedgerError("; ".join(refusals))

    blk = list(blockers or [])
    final = _clamp(verdict, fl, blk)

    gate = gmap[gate_id]
    th = _target_hashes(wp, gate["watches"])
    if gate_id == "G5":                     # run-receipt.md 무결성: G5 영수증 자기참조(AP1)
        receipt = wp.journal("run-receipt.md")
        if receipt.exists():
            th["run_receipt"] = sha256_file(receipt)

    # generation: facts 파일 해시가 직전 기록과 달라질 때 +1
    ckpts = [r for r in ledger if r.get("kind") == "checkpoint"]
    prev_gen = ckpts[-1].get("generation", 1) if ckpts else 1
    last_facts_sha = next((r["target_hashes"]["facts"] for r in reversed(ckpts)
                           if "facts" in (r.get("target_hashes") or {})), None)
    cur_facts_sha = sha256_file(wp.facts) if wp.facts.exists() else None
    gen = prev_gen + 1 if (last_facts_sha and cur_facts_sha
                           and cur_facts_sha != last_facts_sha) else prev_gen

    rec = {"kind": "checkpoint", "gate": gate_id, "verdict": final,
           "lane_verdicts": lane_verdicts or [], "evidence": evidence,
           "blockers": blk, "target_hashes": th, "generation": gen, "at": _now()}
    if phase is not None:
        rec["phase"] = phase
    if "facts" in gate["watches"]:
        rec["fact_hashes"] = _fact_hashes(wp)

    _append(wp, ledger, rec, mode=mode)
    print(f"[checkpoint] {gate_id} verdict={final} (요청 {verdict}) generation={gen} "
          f"blockers={len(blk)}건")
    return rec


# --- status -------------------------------------------------------------------
def _gate_states(wp: WorkPaths, ledger: list[dict], gates: list[dict]) -> dict[str, dict]:
    cur_fh = _fact_hashes(wp)
    out: dict[str, dict] = {}
    for g in gates:
        last = next((r for r in reversed(ledger)
                     if r.get("kind") == "checkpoint" and r.get("gate") == g["id"]), None)
        if last is None:
            out[g["id"]] = {"state": "missing", "verdict": None,
                            "changed_claim_keys": [], "stale_watches": []}
            continue
        changed: list[str] = []
        stale: list[str] = []
        for w in g["watches"]:
            if w == "facts":
                rec_fh = last.get("fact_hashes") or {}
                changed = sorted({k for k in cur_fh if rec_fh.get(k) != cur_fh[k]}
                                 | {k for k in rec_fh if k not in cur_fh})
            else:
                p = _watch_file(wp, w)
                cur = sha256_file(p) if p.exists() else None
                if (last.get("target_hashes") or {}).get(w) != cur:
                    stale.append(w)
        state = "stale" if stale else ("partial_stale" if changed else "fresh")
        out[g["id"]] = {"state": state, "verdict": last.get("verdict"),
                        "generation": last.get("generation"),
                        "changed_claim_keys": changed, "stale_watches": stale}
    return out


def _completion_possible(states: dict[str, dict]) -> bool:
    return all(s["state"] == "fresh" and s["verdict"] in ("PASS", "WATCH")
               for s in states.values())


def status(work) -> dict:
    wp = _wp(work)
    gates = load_gates()
    states = _gate_states(wp, _read_ledger(wp), gates)
    for g in gates:
        s = states[g["id"]]
        print(f"{g['id']:<7} {s['state']:<14} verdict={s['verdict'] or '<none>'}"
              f"  실효 watches: {', '.join(s['stale_watches']) or '<none>'}"
              f"  변경 claim_key: {', '.join(s['changed_claim_keys']) or '<none>'}")
        if s["changed_claim_keys"]:
            print(f"        └ 재검증 대상(fact 단위 — 전건 재검증 아님): {len(s['changed_claim_keys'])}건")
    done = _completion_possible(states)
    print(f"완료 선언 가능(11게이트 신선 PASS/WATCH, BLOCK 0): {'가능' if done else '불가'}")
    return {"gates": states, "completion_possible": done}


# --- validate (읽기전용) ------------------------------------------------------
def _roster_check(wp: WorkPaths) -> dict:
    present = ({p.name for p in wp.audit.iterdir() if p.is_file()}
               if wp.audit.exists() else set())
    allowed = set(ROSTER_REQUIRED) | set(ROSTER_OPTIONAL)
    missing = [n for n in ROSTER_REQUIRED if n not in present]
    legacy = sorted(n for n in present if n in ROSTER_LEGACY)
    unexpected = sorted(n for n in present
                        if n not in allowed and n not in ROSTER_LEGACY
                        and not (n.startswith("verify-") and n.endswith(".md")))
    return {"missing": missing, "unexpected": unexpected, "legacy": legacy}


def validate(work) -> dict:
    """checkpoint 와 동일 규칙 사전검증 + audit 로스터(A3) 검사. 상태 무변경, 전 진단 일괄 출력."""
    wp = _wp(work)
    ledger = _read_ledger(wp)
    fl = _floor_scan(wp)
    roster = _roster_check(wp)
    g1_last = next((r for r in reversed(ledger)
                    if r.get("kind") == "checkpoint" and r.get("gate") == "G1"), None)
    g1_halted = bool(g1_last and g1_last.get("phase") in _HALT_PHASES)

    _print_floor(fl)
    print(f"[로스터] missing: {', '.join(roster['missing']) or '<none>'}")
    print(f"[로스터] unexpected: {', '.join(roster['unexpected']) or '<none>'}")
    print(f"[로스터] legacy(이벤트성 대장 — run-ledger kind 로 이관 대상): "
          f"{', '.join(roster['legacy']) or '<none>'}")
    print(f"[G1] 후속 게이트 진행 차단 상태(failed|cancelled): {'예' if g1_halted else '<none>'}")

    block_level = bool(fl["b"] or (fl["c"] and not fl["legacy"]))
    print(f"[판정] checkpoint 시 BLOCK 강제될 위반: {'있음' if block_level else '<none>'}")
    return {"floor": fl, "roster": roster, "g1_halted": g1_halted, "block_level": block_level}


# --- record -------------------------------------------------------------------
def _active_ask(ledger: list[dict]) -> dict | None:
    answered = {r.get("ask_id") for r in ledger if r.get("kind") == "answer"}
    superseded = {r.get("supersedes") for r in ledger
                  if r.get("kind") == "ask" and r.get("supersedes")}
    for r in reversed(ledger):
        if (r.get("kind") == "ask" and r["ask_id"] not in answered
                and r["ask_id"] not in superseded):
            return r
    return None


def record(work, kind: str, **kw) -> dict | None:
    """steering/ask/answer/conflict/disposition 레코드 append(스키마는 모듈 docstring 정본).
    ask 는 활성 1개 강제, answer 는 멱등(같은 답 no-op → None 반환, 다른 답 conflict 기록)."""
    wp = _wp(work)
    ledger = _read_ledger(wp)
    now = _now()

    if kind == "steering":
        if kw.get("op") not in STEERING_OPS:
            raise LedgerError(f"steering.op '{kw.get('op')}' 는 {'|'.join(STEERING_OPS)} 아님")
        rec = {"kind": kind, "op": kw["op"], "evidence": kw.get("evidence", ""),
               "rationale": kw.get("rationale", ""), "at": now}

    elif kind == "ask":
        for req in ("ask_id", "gate_id", "question"):
            if not kw.get(req):
                raise LedgerError(f"ask 필수 필드 누락: {req}")
        active = _active_ask(ledger)
        if active and active["ask_id"] != kw["ask_id"] and kw.get("supersedes") != active["ask_id"]:
            raise LedgerError(
                f"활성 ask 존재: {active['ask_id']} — 새 ask 는 큐잉하라"
                f"(활성 ask 의 answer 기록 또는 supersedes 지정 후 재시도)")
        rec = {"kind": kind, "ask_id": kw["ask_id"], "gate_id": kw["gate_id"],
               "question": kw["question"], "options": kw.get("options") or [], "at": now}
        for opt in ("recommended", "supersedes"):
            if kw.get(opt):
                rec[opt] = kw[opt]

    elif kind == "answer":
        ask_id = kw.get("ask_id")
        if not any(r.get("kind") == "ask" and r.get("ask_id") == ask_id for r in ledger):
            raise LedgerError(f"answer 대상 ask 없음: {ask_id}")
        if kw.get("resolved_by") not in ("user", "timeout"):
            raise LedgerError(f"answer.resolved_by 는 user|timeout — 현재: {kw.get('resolved_by')}")
        prev = [r for r in ledger if r.get("kind") == "answer" and r.get("ask_id") == ask_id]
        if prev:
            if prev[-1]["answer"] == kw.get("answer"):
                print(f"[record] answer 멱등 no-op: {ask_id} 같은 답 재적용")
                return None
            rec = {"kind": "conflict", "conflict_id": f"answer-conflict-{ask_id}",
                   "fact_ids": [], "sources": [prev[-1]["answer"], kw.get("answer")], "at": now}
            _append(wp, ledger, rec)
            print(f"[record] answer 충돌 기록: {ask_id} 기존 답 보존 — conflict 레코드 append")
            return rec
        rec = {"kind": kind, "ask_id": ask_id, "answer": kw.get("answer"),
               "resolved_by": kw["resolved_by"], "at": now}

    elif kind == "conflict":
        if not kw.get("conflict_id"):
            raise LedgerError("conflict 필수 필드 누락: conflict_id")
        rec = {"kind": kind, "conflict_id": kw["conflict_id"],
               "fact_ids": kw.get("fact_ids") or [], "sources": kw.get("sources") or [],
               "at": now}

    elif kind == "disposition":
        if kw.get("disposition") not in DISPOSITIONS:
            raise LedgerError(
                f"disposition '{kw.get('disposition')}' 는 {'|'.join(DISPOSITIONS)} 아님")
        if not kw.get("ref_id"):
            raise LedgerError("disposition 필수 필드 누락: ref_id(conflict_id|finding_id)")
        rec = {"kind": kind, "ref_id": kw["ref_id"], "disposition": kw["disposition"],
               "rationale": kw.get("rationale", ""), "decided_by": kw.get("decided_by", "lead"),
               "at": now}

    else:
        raise LedgerError(f"미정의 record kind: {kind}")

    _append(wp, ledger, rec)
    print(f"[record] {kind} append: {json.dumps(rec, ensure_ascii=False)}")
    return rec


# --- append + metadata (crash-safe 재개 진입점) --------------------------------
def _append(wp: WorkPaths, ledger: list[dict], rec: dict, mode: str | None = None) -> None:
    ledger.append(rec)
    _write_jsonl_atomic(_ledger_path(wp), ledger)
    _update_metadata(wp, ledger, mode=mode)


def _update_metadata(wp: WorkPaths, ledger: list[dict], mode: str | None = None) -> None:
    gates = load_gates()
    states = _gate_states(wp, ledger, gates)
    fresh = [g for g in gates
             if states[g["id"]]["state"] == "fresh"
             and states[g["id"]]["verdict"] in ("PASS", "WATCH")]
    old = {}
    if _meta_path(wp).exists():
        try:
            old = json.loads(_meta_path(wp).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            old = {}                       # 손상 감지 시 현재 run 스코프만 재시드
    meta = {
        "mode": mode or old.get("mode") or "research",
        "completedAt": _now() if _completion_possible(states) else None,
        "last_fresh_gate": max(fresh, key=lambda g: g["order"])["id"] if fresh else None,
        "fact_count": len(_read_jsonl(wp.facts)),
        "updated_at": _now(),
    }
    _write_json_atomic(_meta_path(wp), meta)


# --- CLI ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description="run-ledger 게이트 영수증 상태머신 【v4-L】")
    ap.add_argument("--work", default=".", help="조사 작업폴더(기본: 현재 디렉터리)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("checkpoint")
    c.add_argument("gate")
    c.add_argument("--verdict", required=True, choices=["PASS", "WATCH", "BLOCK"])
    c.add_argument("--evidence", required=True)
    c.add_argument("--phase", default=None)
    c.add_argument("--lane-verdict", action="append", default=[], metavar="lane=token")
    c.add_argument("--blocker", action="append", default=[])
    c.add_argument("--mode", default=None)

    sub.add_parser("status")
    sub.add_parser("validate")

    r = sub.add_parser("record")
    r.add_argument("kind", choices=["steering", "ask", "answer", "conflict", "disposition"])
    r.add_argument("--op")
    r.add_argument("--evidence", default="")
    r.add_argument("--rationale", default="")
    r.add_argument("--ask-id", dest="ask_id")
    r.add_argument("--gate-id", dest="gate_id")
    r.add_argument("--question")
    r.add_argument("--option", action="append", default=[], dest="options")
    r.add_argument("--recommended")
    r.add_argument("--supersedes")
    r.add_argument("--answer")
    r.add_argument("--resolved-by", dest="resolved_by", default="user",
                   choices=["user", "timeout"])
    r.add_argument("--conflict-id", dest="conflict_id")
    r.add_argument("--fact-id", action="append", default=[], dest="fact_ids")
    r.add_argument("--source", action="append", default=[], dest="sources")
    r.add_argument("--ref-id", dest="ref_id")
    r.add_argument("--disposition")
    r.add_argument("--decided-by", dest="decided_by", default="lead")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "checkpoint":
            lanes = []
            for s in args.lane_verdict:
                if "=" not in s:
                    raise LedgerError(f"--lane-verdict 형식은 lane=token — 현재: {s}")
                lane, token = s.split("=", 1)
                lanes.append({"lane": lane, "token": token})
            rec = checkpoint(args.work, args.gate, args.verdict, args.evidence,
                             phase=args.phase, lane_verdicts=lanes,
                             blockers=args.blocker, mode=args.mode)
            sys.exit(1 if rec["verdict"] == "BLOCK" else 0)
        elif args.cmd == "status":
            status(args.work)
            sys.exit(0)
        elif args.cmd == "validate":
            sys.exit(1 if validate(args.work)["block_level"] else 0)
        elif args.cmd == "record":
            kw = {k: getattr(args, k) for k in
                  ("op", "evidence", "rationale", "ask_id", "gate_id", "question",
                   "options", "recommended", "supersedes", "answer", "resolved_by",
                   "conflict_id", "fact_ids", "sources", "ref_id", "disposition",
                   "decided_by")}
            rec = record(args.work, args.kind, **kw)
            sys.exit(1 if rec and rec.get("kind") == "conflict"
                     and args.kind == "answer" else 0)
    except LedgerError as e:
        print(f"[거부] {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
