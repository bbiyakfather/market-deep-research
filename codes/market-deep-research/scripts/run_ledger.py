"""run_ledger.py — 게이트 영수증 상태머신 【v4-L】 (AP1: run-ledger.jsonl append-only 대장).

목적: "보고서 완성" 선언을 진행 기억·산문이 아니라 기계 검증 가능한 영수증으로 강제한다.
11개 게이트(assets/gates.json 정본)마다 checkpoint 영수증을 남기고, watches 대상의
파일 sha256 + fact 단위 content-hash(claim_key→sha) 를 함께 봉인해 신선도
(fresh / partial_stale / stale / missing)를 사후 판정한다.
완료 선언 = 11개 게이트 전부 신선 PASS/WATCH(BLOCK 0). 산문은 상태를 변이하지 않는다.

레코드 스키마 정본(A4 — references 문서는 이 docstring 을 참조한다):
  checkpoint  {kind, gate, verdict, lane_verdicts[], evidence, blockers[], phase?,
               target_hashes{facts?, evidence?, report_md?, report_pdf?, run_receipt?},
               fact_hashes{claim_key: content_sha}?, generation, at, prev_hash}
  steering    {kind, op: add_item|split_item|reorder|revise_wording|supersede_item|annotate,
               evidence, rationale, at, prev_hash}
  ask         {kind, ask_id, gate_id, question, options[], recommended?, supersedes?, at, prev_hash}
  answer      {kind, ask_id, answer, resolved_by: user|timeout, at, prev_hash}
  conflict    {kind, conflict_id, fact_ids[], sources[], at, prev_hash}
  disposition {kind, ref_id(conflict_id|finding_id), disposition, rationale, decided_by, at, prev_hash}
    - conflict 처분값: accept_a|accept_b|synthesize_range|defer_to_report_caveat|reject_both
    - 검증 발견 처분값: accept|rebut
  【v10-I4】 prev_hash: append 시 자동 부여(직전 레코드의 _canon_sha, 최초는 'GENESIS') —
    append-only 를 이름만이 아니라 실제로 강제한다. 레코드를 직접 열어 지우거나 위조해도
    체인이 끊겨 validate/status 가 잡는다. prev_hash 필드가 없는 레거시 레코드는 체인
    검사에서 건너뛴다(소급 차단 금지).

기계 하한(floor) — checkpoint 시 스크립트가 대장을 직접 스캔, 요청 verdict 를 강제 하향:
  (b) confirmed 인데 evidence_ids 가 비었거나 참조 대상이 실재하지 않음(댕글링) → BLOCK
  (c) 대장 스키마 위반 행 존재 → BLOCK  【v7】 evidence.jsonl 부재를 사유로 한 WATCH 완화는
      폐지했다 — 완화 조건이 '증거 대장이 없음'이라 "안 만들면 통과"라는 우회로였다.
  (d) LV 한정: 직전 LV 영수증 이후 내용이 바뀐 confirmed fact 에 lead 재검증이 늘지 않음 → BLOCK
      (수정 후 재열람 없이 checkpoint 만 다시 찍어 신선도를 되살리는 경로 차단. 기준선은
       영수증에 실린 claim_key 별 lead 재검증 횟수 — 타임스탬프가 초 단위라 시각 비교는 못 쓴다)
  (e) 【v10-C4】 G2 이상 게이트(order 기준): 대응 disposition(ref_id=conflict_id) 없는
      kind:conflict 가 대장에 남아 있으면 → BLOCK(SKILL.md:167-168 "미처분 충돌 잔존 시
      G2 진입 불가"의 기계화)
  (f) 【v10-C10】 G5C 한정: derivation=computed fact 또는 evidence.type=calculation 대상이
      있는데 audit/verify-*.md 산출물이 하나도 없으면 → BLOCK(verification-gates.md:138-141
      약속의 기계화. slug 1:1 대조 규칙 정본이 없어 '대상 존재 시 최소 1개 실재'로 최소
      요건만 강제한다 — 근거는 _g5c_target_scan() 주석)

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

import contextlib
import json
import os
import sys
import tempfile
import threading
import time
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
    """fact 단위 content-hash 맵 — 신선도를 fact 단위로 판정하는 근거(claim_key→sha).

    같은 claim_key 가 여러 행이면 덮어쓰지 않고 정렬 후 결합한다. 덮어쓰면 뒤 행만 봉인돼
    앞 행(예: 원본) 변경이 신선도에서 마스킹된다(v5 실측). 정렬이라 행 순서에는 불변.
    """
    import hashlib
    groups: dict[str, list[str]] = {}
    for f in _read_jsonl(wp.facts):
        key = f.get("claim_key") or make_claim_key(f.get("context") or {})
        groups.setdefault(key, []).append(_canon_sha(f))
    return {k: (v[0] if len(v) == 1
                else hashlib.sha256("".join(sorted(v)).encode("utf-8")).hexdigest())
            for k, v in groups.items()}


def _watch_file(wp: WorkPaths, watch: str) -> Path:
    # 【v10-C5/C12】 evidence·run_receipt 을 정식 watch 어휘로 추가 — gates.json 에서
    # 이 이름을 쓰는 게이트만 실제로 대조된다(_gate_states 루프가 g["watches"] 를 순회).
    return {"facts": wp.facts, "evidence": wp.evidence,
            "report_md": wp.report_md, "report_pdf": wp.report_pdf,
            "run_receipt": wp.journal("run-receipt.md")}[watch]


MISSING = "<missing>"          # 부재를 '없는 값'이 아니라 명시 상태로(fail-closed 센티널)


def _target_hashes(wp: WorkPaths, watches: list[str]) -> dict[str, str]:
    """감시 대상 파일 해시. 부재는 생략하지 않고 MISSING 으로 기록한다 — 생략하면
    기록 None == 현재 None 이라 '산출물을 만든 적 없는' 게이트가 fresh 로 보인다(v5 실측)."""
    th: dict[str, str] = {}
    for w in watches:
        p = _watch_file(wp, w)
        th[w] = sha256_file(p) if p.exists() else MISSING
    return th


# --- 기계 하한(floor) ---------------------------------------------------------
def _floor_scan(wp: WorkPaths) -> dict:
    """(b) confirmed 무증거·댕글링 참조 / (c) 스키마 위반 스캔.

    【v7】 evidence.jsonl 부재를 사유로 (c)를 WATCH 로 낮추던 '레거시 완화'는 폐지했다.
    완화가 보호하던 대상(구 스키마 조사 폴더)이 실은 테스트 샘플이라 지킬 실데이터가 없었고,
    남은 효과는 '증거 대장을 만들지 않으면(또는 지우면) 위반이 WATCH 로 강등된다'는 공식
    우회로뿐이었다 — 완화 조건이 '증거가 없음'인 것 자체가 설계 오류였다.
    """
    schema = load_schema()
    b, c = [], []
    ev_rows = _read_jsonl(wp.evidence) if wp.evidence.exists() else []
    known_ev = {e.get("id") for e in ev_rows}
    for f in _read_jsonl(wp.facts):
        fid = f.get("id") or f.get("claim_key") or "?"
        if f.get("status") == "confirmed":
            ids = f.get("evidence_ids") or []
            if not ids:
                b.append(str(fid))
            else:
                dangling = [e for e in ids if e not in known_ev]
                if dangling:      # 참조는 있는데 대상이 없다 = 증거 없는 confirmed 와 같다
                    b.append(f"{fid}(댕글링 {', '.join(dangling)})")
        try:
            validate_fact(f, schema)
        except Exception as e:                    # 형식 파손 행도 위반으로 집계(전 진단 계속)
            c.append(f"{fid}: {e}")
    for ev in ev_rows:
        try:
            validate_evidence(ev, schema, wp)
        except Exception as e:
            c.append(f"{ev.get('id', '?')}: {e}")
    return {"b": b, "c": c}


def _print_floor(fl: dict) -> None:
    print(f"[floor(b)] confirmed 무증거·댕글링 위반: {', '.join(fl['b']) or '<none>'}")
    print(f"[floor(c)] 대장 스키마 위반: {'; '.join(fl['c']) or '<none>'}")
    if fl.get("d"):
        print(f"[floor(d)] 변경 후 재검증 없음: {', '.join(fl['d'])}")
    if fl.get("e"):
        print(f"[floor(e)] 미처분 충돌 잔존(G2+): {', '.join(fl['e'])}")
    if fl.get("f"):
        print(f"[floor(f)] G5C 대상 존재하는데 verify-*.md 부재: {', '.join(fl['f'])}")


def _clamp(requested: str, fl: dict, blockers: list[str]) -> str:
    """floor 위반을 blockers 에 적재하고 최종 verdict 를 하향 강제(상향은 없음)."""
    final = requested
    if fl["b"]:
        final = "BLOCK"
        blockers += [f"floor(b): {i} confirmed 인데 유효한 evidence 참조 없음" for i in fl["b"]]
    if fl["c"]:
        final = "BLOCK"
        blockers += [f"floor(c): {i}" for i in fl["c"]]
    if fl.get("d"):
        final = "BLOCK"
        blockers += [f"floor(d): {i}" for i in fl["d"]]
    if fl.get("e"):
        final = "BLOCK"
        blockers += [f"floor(e): 미처분 충돌 {i} 잔존 — G2 이상 게이트 진입 불가" for i in fl["e"]]
    if fl.get("f"):
        final = "BLOCK"
        blockers += [f"floor(f): G5C 대상 {i} 인데 verify-*.md 산출물 부재" for i in fl["f"]]
    return final


def _stale_reverify_scan(wp: WorkPaths, ledger: list[dict], gate_id: str) -> list[str]:
    """floor(d) 【v7】 — LV(팀리드 전건 재검증) 한정: 직전 LV checkpoint 이후 **내용이 바뀐**
    confirmed fact 는, 그 변경 이후에 기록된 lead 재검증 이벤트가 있어야 다시 PASS 가 된다.

    이게 없으면 '수치를 고치고 → 재열람 없이 checkpoint 만 다시 찍어 → 신선도 복귀'가 성립해
    fact 단위 신선도 모델 자체가 무의미해진다(v5 감사 GS-4). 대상을 LV 로 좁힌 이유는 LV 만이
    '전 fact 를 팀리드가 원문 재열람'을 의미하는 게이트이기 때문이다 — BX·G2 는 요구 증적이
    달라 같은 규칙을 그대로 씌우면 과잉 차단이 된다.
    """
    if gate_id != "LV":
        return []
    last = next((r for r in reversed(ledger)
                 if r.get("kind") == "checkpoint" and r.get("gate") == "LV"), None)
    if not last:
        return []                                  # 최초 LV 는 대조할 직전 상태가 없다
    prev_counts = last.get("lead_verify_counts")
    if prev_counts is None:
        return []                                  # v7 이전 영수증은 기준선이 없다(소급 차단 안 함)
    prev_fh = last.get("fact_hashes") or {}
    cur = _fact_hashes(wp)
    changed = {k for k in cur if prev_fh.get(k) != cur[k]}
    if not changed:
        return []
    cur_counts = _lead_verify_counts(wp)
    out: list[str] = []
    for f in _read_jsonl(wp.facts):
        key = f.get("claim_key") or make_claim_key(f.get("context") or {})
        if key not in changed or f.get("status") != "confirmed":
            continue
        # 시각 비교는 못 쓴다 — 타임스탬프가 초 단위라 같은 초에 벌어진 수정과 재검증이
        # 구분되지 않는다. 대신 '직전 영수증 이후 lead 재검증이 새로 늘었는가'를 본다.
        if cur_counts.get(key, 0) <= prev_counts.get(key, 0):
            out.append(f"{f.get('id') or key} 변경됐는데 직전 LV 영수증 이후 lead 재검증이 늘지 않음")
    return out


def _lead_verify_counts(wp: WorkPaths) -> dict[str, int]:
    """claim_key → 팀리드 재검증 이벤트 수. floor(d) 의 기준선(시계 비의존)."""
    out: dict[str, int] = {}
    for f in _read_jsonl(wp.facts):
        key = f.get("claim_key") or make_claim_key(f.get("context") or {})
        n = sum(1 for v in (f.get("verify_events") or []) if v.get("by") == "lead")
        out[key] = out.get(key, 0) + n
    return out


def _unresolved_conflict_scan(ledger: list[dict], gate_id: str, gmap: dict) -> list[str]:
    """floor(e) 【v10-C4】 — G2 이상 게이트(order 기준)는 미처분 kind:conflict 가 있으면 BLOCK.

    SKILL.md:167-168 이 문서로만 약속하던 "미처분 충돌 잔존 시 G2 진입 불가"를 기계화한다.
    disposition 이 conflict 를 가리키는 필드는 record() 의 기존 관례를 그대로 쓴다 — ref_id
    가 conflict_id 를 가리킨다(tests/test_run_ledger.py 의 conflict→disposition 사용례 정본,
    다른 이름의 참조 필드는 대장 어디에도 없다).
    """
    if gate_id not in gmap or gmap[gate_id]["order"] < gmap["G2"]["order"]:
        return []
    disposed = {r.get("ref_id") for r in ledger if r.get("kind") == "disposition"}
    return sorted({r.get("conflict_id") or "?" for r in ledger
                   if r.get("kind") == "conflict" and r.get("conflict_id") not in disposed})


def _g5c_target_scan(wp: WorkPaths, gate_id: str) -> list[str]:
    """floor(f) 【v10-C10】 — G5C 대상(derivation=computed 인 fact 또는 evidence.type=calculation
    이 딸린 fact)이 있는데 audit/verify-*.md 산출물이 하나도 없으면 BLOCK
    (verification-gates.md:138-141, SKILL.md:224-227 약속의 기계화).

    slug 규칙 정본 없음(문서·기존 코드 어디에도 fact_id→slug 변환 규칙이 없다): fact 별 1:1
    파일명 매칭을 새로 발명하면 그 자체가 새 규약을 창설하는 것이라, 대신 '대상이 있으면
    verify-*.md 가 최소 1개는 실재해야 한다'는 최소 요건만 기계화한다. 이 결정은 이 주석이
    정본이다 — 더 엄격한 1:1 대조가 필요해지면 slug 규칙부터 문서에 먼저 정의할 것.
    """
    if gate_id != "G5C":
        return []
    ev = _read_jsonl(wp.evidence) if wp.evidence.exists() else []
    calc_fact_ids = {e.get("fact_id") for e in ev if e.get("type") == "calculation"}
    targets = sorted({f.get("id") for f in _read_jsonl(wp.facts)
                      if f.get("derivation") == "computed" or f.get("id") in calc_fact_ids})
    if not targets:
        return []
    has_verify_md = (wp.audit.exists()
                     and any(p.name.startswith("verify-") and p.name.endswith(".md")
                             for p in wp.audit.iterdir() if p.is_file()))
    return [] if has_verify_md else targets


def _chain_scan(ledger: list[dict]) -> list[str]:
    """prev_hash 해시체인 검증 【v10-I4】 — append-only 를 이름만이 아니라 실제로 강제한다.

    레거시 레코드(prev_hash 필드 없음)는 검사 대상에서 제외한다 — floor(d) 의 prev_counts
    부재 처리(위 _stale_reverify_scan) 선례와 동일하게, 기준선이 없으면 소급 차단하지 않는다
    (안 그러면 이 기능을 넣기 전에 완료된 기존 조사폴더가 다음 status 호출에서 전부 오탐
    BLOCK 된다). 체인이 한 번이라도 시작된 뒤에는 그 앞의 레거시 레코드 내용이 다음 체인
    레코드의 prev_hash 앵커로 쓰이므로, 이후 그 레거시 레코드를 변조해도 잡힌다(의도적 부수
    효과 — 탐지 능력을 일부러 줄이지 않는다).
    """
    out: list[str] = []
    for i, r in enumerate(ledger):
        if "prev_hash" not in r:
            continue
        expected = _canon_sha(ledger[i - 1]) if i > 0 else "GENESIS"
        if r["prev_hash"] != expected:
            out.append(f"#{i}({r.get('kind')}/{r.get('gate') or r.get('ask_id') or ''})")
    return out


# --- checkpoint ---------------------------------------------------------------
def checkpoint(work, gate_id: str, verdict: str, evidence: str, phase: str | None = None,
               lane_verdicts: list[dict] | None = None, blockers: list[str] | None = None,
               mode: str | None = None) -> dict:
    wp = _wp(work)
    # 【v10-C13】 게이트 id 대소문자 무시 — SKILL.md 는 "G5c" 소문자로 표기하는데 enum 은
    # 대문자다. 문서 5곳을 고치는 대신 여기서 정규화(향후 표기 흔들림도 함께 흡수).
    gate_id = (gate_id or "").upper()
    gates = load_gates()
    gmap = {g["id"]: g for g in gates}
    ledger = _read_ledger(wp)
    fl = _floor_scan(wp)
    fl["d"] = _stale_reverify_scan(wp, ledger, gate_id)
    fl["e"] = _unresolved_conflict_scan(ledger, gate_id, gmap)
    fl["f"] = _g5c_target_scan(wp, gate_id)

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
    # 【v10-C12】 run-receipt.md 무결성(AP1, G5 영수증 자기참조)은 이제 gates.json 의 G5
    # watches 에 "run_receipt" 이 있어 _target_hashes 가 일반 경로로 기록·대조한다(write-only
    # 였던 특례 분기 제거 — G5 PASS 후 run-receipt.md 를 고쳐도 잡히지 않던 결함의 실제 수정).
    th = _target_hashes(wp, gate["watches"])

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
    if gate_id == "LV":                     # floor(d) 기준선 — 다음 LV 가 이 수치와 대조한다
        rec["lead_verify_counts"] = _lead_verify_counts(wp)

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
                            "changed_claim_keys": [], "stale_watches": [],
                            "missing_watches": []}
            continue
        changed: list[str] = []
        stale: list[str] = []
        missing: list[str] = []
        for w in g["watches"]:
            p = _watch_file(wp, w)
            if not p.exists():                  # 산출물 자체가 없다 — 신선도 이전의 문제
                missing.append(w)
                continue
            if w == "facts":
                rec_fh = last.get("fact_hashes") or {}
                changed = sorted({k for k in cur_fh if rec_fh.get(k) != cur_fh[k]}
                                 | {k for k in rec_fh if k not in cur_fh})
            else:
                cur = sha256_file(p)
                if (last.get("target_hashes") or {}).get(w) != cur:
                    stale.append(w)
        state = ("missing_watch" if missing else
                 "stale" if stale else ("partial_stale" if changed else "fresh"))
        out[g["id"]] = {"state": state, "verdict": last.get("verdict"),
                        "generation": last.get("generation"),
                        "changed_claim_keys": changed, "stale_watches": stale,
                        "missing_watches": missing}
    return out


def _completion_possible(states: dict[str, dict], roster_missing: list[str] | None = None,
                         chain_breaks: list[str] | None = None) -> bool:
    """완료 = 11게이트 신선 PASS/WATCH + 필수 audit 산출물 실재 + 대장 해시체인 무결.
    missing_watch(산출물 부재)는 fresh 가 아니므로 여기서 자동 배제된다.
    chain_breaks(【v10-I4】)는 대장 자체가 변조됐다는 신호라 완료 선언을 무조건 막는다."""
    if roster_missing or chain_breaks:
        return False
    return all(s["state"] == "fresh" and s["verdict"] in ("PASS", "WATCH")
               for s in states.values())


def status(work) -> dict:
    wp = _wp(work)
    gates = load_gates()
    ledger = _read_ledger(wp)
    states = _gate_states(wp, ledger, gates)
    roster_missing = _roster_check(wp)["missing"]
    chain_breaks = _chain_scan(ledger)
    for g in gates:
        s = states[g["id"]]
        print(f"{g['id']:<7} {s['state']:<14} verdict={s['verdict'] or '<none>'}"
              f"  실효 watches: {', '.join(s['stale_watches']) or '<none>'}"
              f"  변경 claim_key: {', '.join(s['changed_claim_keys']) or '<none>'}")
        if s["missing_watches"]:
            print(f"        └ 산출물 부재(선언만 있고 물건이 없음): {', '.join(s['missing_watches'])}")
        if s["changed_claim_keys"]:
            print(f"        └ 재검증 대상(fact 단위 — 전건 재검증 아님): {len(s['changed_claim_keys'])}건")
    ask = _active_ask(ledger)
    if ask:
        print(f"[미답 ask] {ask['ask_id']}({ask.get('gate_id') or '-'}): {ask.get('question') or ''}")
    if roster_missing:
        print(f"[로스터] 필수 audit 산출물 부재: {', '.join(roster_missing)}")
    if chain_breaks:
        print(f"[체인] prev_hash 무결성 위반(변조 의심): {', '.join(chain_breaks)}")
    done = _completion_possible(states, roster_missing, chain_breaks)
    print(f"완료 선언 가능(11게이트 신선 PASS/WATCH, BLOCK 0, 필수 산출물 실재, 해시체인 무결): "
          f"{'가능' if done else '불가'}")
    return {"gates": states, "completion_possible": done,
            "roster_missing": roster_missing, "active_ask": ask, "chain_breaks": chain_breaks}


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
    chain_breaks = _chain_scan(ledger)      # 【v10-I4】 대장 해시체인 무결성(변조 탐지)
    g1_last = next((r for r in reversed(ledger)
                    if r.get("kind") == "checkpoint" and r.get("gate") == "G1"), None)
    g1_halted = bool(g1_last and g1_last.get("phase") in _HALT_PHASES)

    _print_floor(fl)
    print(f"[로스터] missing: {', '.join(roster['missing']) or '<none>'}")
    print(f"[로스터] unexpected: {', '.join(roster['unexpected']) or '<none>'}")
    print(f"[로스터] legacy(이벤트성 대장 — run-ledger kind 로 이관 대상): "
          f"{', '.join(roster['legacy']) or '<none>'}")
    print(f"[G1] 후속 게이트 진행 차단 상태(failed|cancelled): {'예' if g1_halted else '<none>'}")
    print(f"[체인] prev_hash 무결성 위반(변조 의심): {', '.join(chain_breaks) or '<none>'}")

    # 【v10】 종전 `fl["c"] and not fl["legacy"]` 는 _floor_scan 이 반환하지 않는 키를 읽어
    # (b)가 비고 (c)만 찬 조합에서 KeyError 로 죽었다(v7 에서 레거시 완화를 폐지할 때 남은 잔재).
    # 완화는 폐지됐고 checkpoint 의 _clamp 는 이미 (c)를 무조건 BLOCK 시킨다 — 두 경로를 정렬한다.
    block_level = bool(fl["b"] or fl["c"] or chain_breaks)
    print(f"[판정] checkpoint 시 BLOCK 강제될 위반: {'있음' if block_level else '<none>'}")
    return {"floor": fl, "roster": roster, "g1_halted": g1_halted,
            "chain_breaks": chain_breaks, "block_level": block_level}


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

    elif kind in ("wave", "respawn", "engine_suspend", "engine_resume"):
        # 런타임 상한(깊이캡·재스폰·엔진 격리) 카운터의 영속 근거. 세션 기억에만 두면
        # 중단·재개마다 리셋되어 상한이 없는 것과 같다 — 별도 파일 신설 없이 같은 대장에.
        rec = {"kind": kind, "at": now}
        if kind == "wave":
            rec["index"] = int(kw.get("index") or 0) or None
        if kind == "respawn":
            if not kw.get("lane"):
                raise LedgerError("respawn 필수 필드 누락: lane")
            rec["lane"] = kw["lane"]
        if kind in ("engine_suspend", "engine_resume"):
            if not kw.get("engine"):
                raise LedgerError(f"{kind} 필수 필드 누락: engine")
            rec["engine"] = kw["engine"]
        rec["rationale"] = kw.get("rationale", "")

    else:
        raise LedgerError(f"미정의 record kind: {kind}")

    _append(wp, ledger, rec)
    print(f"[record] {kind} append: {json.dumps(rec, ensure_ascii=False)}")
    return rec


# --- append + metadata (crash-safe 재개 진입점) --------------------------------
_THREAD_LOCK = threading.Lock()      # 같은 프로세스 안의 직렬화(파일락만으로는 부족 — 아래)
_LOCK_RETRY_SEC = (0.01, 0.03, 0.08, 0.2, 0.5)


@contextlib.contextmanager
def _ledger_lock(path: Path):
    """대장 쓰기 직렬화 — 프로세스 내부는 스레드 락, 프로세스 간은 사이드카 .lock 파일.

    Windows 의 open(path,'a') 는 seek 후 write 라 원자적이지 않다(레코드가 1KB 를 넘으면 실측
    손상 보고가 있다). 그래서 락이 필요한데, `msvcrt.locking(LK_LOCK)` 은 경합 시 곧바로
    OSError(EDEADLOCK, '[Errno 36] Resource deadlock avoided')를 던진다 — 20스레드 실측에서
    절반이 즉시 실패했다. 예외를 삼키면 방어가 0 이 되므로 (a) 스레드 락으로 프로세스 내부를
    먼저 직렬화하고, (b) 파일락은 짧은 백오프로 재시도한다. 끝내 못 잡아도 쓰기는 진행하되
    그 사실을 stderr 로 알린다(조용한 무방비 금지).
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with _THREAD_LOCK:
        fh, held = None, False
        try:
            fh = open(lock_path, "a+b")
            for i, wait in enumerate((0.0,) + _LOCK_RETRY_SEC):
                if wait:
                    time.sleep(wait)
                try:
                    if os.name == "nt":
                        import msvcrt
                        fh.seek(0)
                        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                    held = True
                    break
                except OSError:
                    continue                    # 다른 프로세스가 점유 중 — 백오프 후 재시도
                except Exception:               # noqa: BLE001 — 락 미지원 플랫폼은 degrade
                    break
            if not held:
                print(f"  (경고) 대장 파일락 미획득 — 다른 프로세스와 동시 쓰기 시 경합 가능: "
                      f"{lock_path.name}", file=sys.stderr)
            yield
        finally:
            if fh is not None:
                if held:
                    try:
                        if os.name == "nt":
                            import msvcrt
                            fh.seek(0)
                            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                    except Exception:           # noqa: BLE001
                        pass
                fh.close()


def _append(wp: WorkPaths, ledger: list[dict], rec: dict, mode: str | None = None) -> None:
    """append-only 대장에 **한 줄만** 덧붙인다.

    종전에는 전체를 읽어 전체를 다시 썼다 — (a) 동시 쓰기에서 나중 쓰기가 앞선 레코드를 통째로
    덮어(lost update) ask·checkpoint 가 소실되고, (b) 레코드 N 건이면 I/O 가 O(N²)로 팽창했다.
    호출자가 넘긴 `ledger` 는 읽은 시점의 스냅샷이므로, 실제 상태는 락 안에서 디스크를 다시
    읽어 판단한다(다른 프로세스가 그 사이 남긴 레코드까지 반영).

    【v10-I4】 prev_hash: 락 안에서 읽은 디스크 최신 마지막 레코드를 앵커로 건다(호출자의
    `ledger` 스냅샷을 쓰면 안 된다 — 동시 쓰기에서 다른 프로세스가 먼저 끼워넣은 레코드를
    놓쳐 체인이 끊긴다). 최초 레코드는 'GENESIS'.
    """
    path = _ledger_path(wp)
    with _ledger_lock(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        disk_ledger = _read_jsonl(path) if path.exists() else []
        rec["prev_hash"] = _canon_sha(disk_ledger[-1]) if disk_ledger else "GENESIS"
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        fresh = disk_ledger + [rec]              # 파생 상태는 대장 재생이 정본
        # 메타데이터 쓰기도 락 안에서 — 밖에서 하면 20스레드가 같은 run-metadata.json 에
        # 동시에 os.replace 해 Windows 에서 WinError 5(액세스 거부)로 죽는다(실측). prev_hash
        # 계산으로 락 내부 구간이 짧아지며 원래도 있던 이 경합이 실제로 드러났다.
        _update_metadata(wp, fresh, mode=mode)
    ledger.append(rec)                          # 호출자 스냅샷도 최신화(반환값 일관성)


def _counters(ledger: list[dict]) -> dict:
    """런타임 상한 카운터를 대장 재생으로 산출(파생 상태를 직접 쓰지 않는다 — 재생이 정본).
    세션 기억에만 있던 값들이라 중단·재개 때 리셋되어 상한이 실질 무력화됐다."""
    c = {"wave": 0, "respawn_by_lane": {}, "interview_round": 0,
         "autoconfirm_streak": 0, "suspended_engines": []}
    for r in ledger:
        k = r.get("kind")
        if k == "wave":
            c["wave"] = max(c["wave"], int(r.get("index") or c["wave"] + 1))
        elif k == "respawn":
            lane = r.get("lane") or "?"
            c["respawn_by_lane"][lane] = c["respawn_by_lane"].get(lane, 0) + 1
        elif k == "ask":
            c["interview_round"] += 1
        elif k == "engine_suspend":
            eng = r.get("engine")
            if eng and eng not in c["suspended_engines"]:
                c["suspended_engines"].append(eng)
        elif k == "engine_resume":
            c["suspended_engines"] = [e for e in c["suspended_engines"] if e != r.get("engine")]
    return c


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
    ask = _active_ask(ledger)
    # 【v10-I4】 해시체인이 끊겼으면(대장 변조 의심) completedAt 도 완료로 봉인하지 않는다 —
    # status() 가 보고하는 완료 가능 여부와 메타데이터가 서로 다른 말을 하면 안 된다.
    chain_breaks = _chain_scan(ledger)
    meta = {
        "mode": mode or old.get("mode") or "research",
        "completedAt": (_now() if _completion_possible(
            states, _roster_check(wp)["missing"], chain_breaks) else None),
        "last_fresh_gate": max(fresh, key=lambda g: g["order"])["id"] if fresh else None,
        "fact_count": len(_read_jsonl(wp.facts)),
        # 재개 진입점에 미답 ask 를 노출한다 — 없으면 재개 세션이 교착의 원인을 못 본다.
        "active_ask": ({"ask_id": ask["ask_id"], "gate_id": ask.get("gate_id"),
                        "question": ask.get("question"), "asked_at": ask.get("at")}
                       if ask else None),
        "counters": _counters(ledger),
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
    r.add_argument("kind", choices=["steering", "ask", "answer", "conflict", "disposition",
                                    "wave", "respawn", "engine_suspend", "engine_resume"])
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
    # 기본값 없음(필수 지정) — 기본 'user' 는 플래그를 생략한 자가 답변을 사용자 동의로
    # 봉인해버린다. 지정을 강제해도 '에이전트가 쓴 user 답'은 기계로 못 가르는 한계는 남는다.
    r.add_argument("--resolved-by", dest="resolved_by", choices=["user", "timeout"])
    r.add_argument("--lane")
    r.add_argument("--engine")
    r.add_argument("--index", type=int)
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
            if args.kind == "answer" and not args.resolved_by:
                raise LedgerError("answer 는 --resolved-by user|timeout 명시 필수 "
                                  "(기본값 없음 — 자가 답변이 동의로 봉인되는 것을 막는다)")
            kw = {k: getattr(args, k) for k in
                  ("op", "evidence", "rationale", "ask_id", "gate_id", "question",
                   "options", "recommended", "supersedes", "answer", "resolved_by",
                   "conflict_id", "fact_ids", "sources", "ref_id", "disposition",
                   "decided_by", "lane", "engine", "index")}
            rec = record(args.work, args.kind, **kw)
            sys.exit(1 if rec and rec.get("kind") == "conflict"
                     and args.kind == "answer" else 0)
    except LedgerError as e:
        print(f"[거부] {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
