"""test_run_ledger.py — run_ledger 게이트 영수증 상태머신 【v4-L】 동작 검증.

test_adversarial.py 와 같은 러너 패턴(pytest 아님, python 직접 실행). 각 케이스는
'게이트가 조작·위반을 정확히 잡는지'와 '정상 경로가 막히지 않는지'의 짝을 확인한다.
"""
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from skill_paths import resolve_work_dir, WorkPaths            # noqa: E402
from facts_db import FactsDB, _read_jsonl, _write_jsonl_atomic  # noqa: E402
import run_ledger                                               # noqa: E402
from run_ledger import LedgerError                              # noqa: E402

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def _fact(entity="삼성", metric="revenue", raw="300.9"):
    return {"claim": f"{entity} {metric} {raw}", "risk": "high", "status": "pending",
            "context": {"metric": metric, "entity": entity, "geography": "KR",
                        "period": "2024"},
            "value": {"raw": raw, "unit": "KRW_T"},
            "grade": {"authority": "A", "independence": "A", "directness": "A",
                      "recency": "A"}}


def _work(td):
    """유효 fact 1건 + 빈 evidence.jsonl(레거시 완화 배제) 있는 작업폴더."""
    wd = resolve_work_dir("run_ledger_테스트", base=td)
    db = FactsDB(wd)
    db.add_fact(_fact())
    wp = WorkPaths(wd)
    wp.evidence.write_text("", encoding="utf-8")
    return wd, wp, db


def _ledger(wp):
    return _read_jsonl(wp.journal("run-ledger.jsonl"))


@case
def gates_json_authoritative():
    """gates.json 로드: 11개 · order 0..10 연속 · watches 어휘 고정, 미정의 게이트 id 거부."""
    gates = run_ledger.load_gates()
    assert len(gates) == 11, f"게이트 {len(gates)}개 — 11개 아님"
    assert [g["id"] for g in gates] == ["G0", "PLAN", "G1", "LV", "BX", "G2", "G3",
                                        "G5C", "RENDER", "G4", "G5"]
    assert [g["order"] for g in gates] == list(range(11)), "order 불연속"
    for g in gates:
        assert set(g["watches"]) <= {"facts", "report_md", "report_pdf"}, g
    with tempfile.TemporaryDirectory() as td:
        wd, wp, _ = _work(td)
        try:
            run_ledger.checkpoint(wd, "G9", "PASS", "없는 게이트")
            assert False, "미정의 게이트 id 가 통과됨"
        except LedgerError:
            pass
        assert not wp.journal("run-ledger.jsonl").exists(), "거부됐는데 레코드가 기록됨"


@case
def checkpoint_receipt_and_hashes():
    """checkpoint 영수증 기록 + 파일 sha256·fact 단위 content-hash 실재 + 메타데이터 갱신."""
    with tempfile.TemporaryDirectory() as td:
        wd, wp, db = _work(td)
        run_ledger.checkpoint(wd, "G1", "PASS", "join 완료", phase="complete",
                              lane_verdicts=[{"lane": "coverage", "token": "CLEAR"}])
        rows = _ledger(wp)
        assert len(rows) == 1 and rows[0]["kind"] == "checkpoint" and rows[0]["gate"] == "G1"
        want = hashlib.sha256(wp.facts.read_bytes()).hexdigest()
        assert rows[0]["target_hashes"]["facts"] == want, "facts 파일 해시 불일치"
        ck = db.facts()[0]["claim_key"]
        fh = rows[0]["fact_hashes"]
        assert ck in fh and re.fullmatch(r"[0-9a-f]{64}", fh[ck]), "fact content-hash 형식 오류"
        assert rows[0]["generation"] == 1
        assert rows[0]["lane_verdicts"] == [{"lane": "coverage", "token": "CLEAR"}]
        meta = json.loads(wp.journal("run-metadata.json").read_text(encoding="utf-8"))
        assert meta["fact_count"] == 1 and meta["last_fresh_gate"] == "G1"


@case
def floor_b_forces_block():
    """floor(b): confirmed 무증거 → 팀리드 PASS 요청을 무시하고 BLOCK 강제."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("floor_b", base=td)
        wp = WorkPaths(wd)
        bad = {**_fact(), "id": "F001", "claim_key": "revenue|삼성|KR|2024|na|na",
               "status": "confirmed", "evidence_ids": [],
               "verify_events": [{"by": "lead", "at": "2026-01-01T00:00:00",
                                  "action": "reread", "note": ""}]}
        _write_jsonl_atomic(wp.facts, [bad])
        wp.evidence.write_text("", encoding="utf-8")     # 레거시 완화 배제
        rec = run_ledger.checkpoint(wd, "G1", "PASS", "팀리드 PASS 요청", phase="complete")
        assert rec["verdict"] == "BLOCK", f"BLOCK 강제 실패: {rec['verdict']}"
        assert any("floor(b)" in b for b in rec["blockers"]), rec["blockers"]


@case
def legacy_single_ledger_demotes_to_watch():
    """레거시 단일 대장(evidence.jsonl 부재): 스키마 위반(c)은 WATCH + migration_required 로 강등."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("legacy", base=td)
        wp = WorkPaths(wd)
        bad = {**_fact(), "id": "F001", "claim_key": "k|삼성|KR|2024|na|na"}
        del bad["grade"]                                  # 스키마 위반, confirmed 아님(b 미발동)
        _write_jsonl_atomic(wp.facts, [bad])
        assert not wp.evidence.exists()
        rec = run_ledger.checkpoint(wd, "G1", "PASS", "레거시 조사 재개", phase="complete")
        assert rec["verdict"] == "WATCH", f"레거시 완화 실패: {rec['verdict']}"
        assert any("migration_required" in b for b in rec["blockers"]), rec["blockers"]


@case
def fact_level_freshness():
    """fact 1건 수정 → 해당 claim_key 만 partial_stale(무관 fact 실효 없음)."""
    with tempfile.TemporaryDirectory() as td:
        wd, wp, db = _work(td)
        f2 = db.add_fact(_fact(entity="LG", raw="80.0"))
        run_ledger.checkpoint(wd, "G1", "PASS", "join", phase="complete")
        assert run_ledger.status(wd)["gates"]["G1"]["state"] == "fresh"
        facts = db.facts()
        target = next(f for f in facts if f["context"]["entity"] == "삼성")
        target["value"]["raw"] = "999.9"
        _write_jsonl_atomic(wp.facts, facts)
        g1 = run_ledger.status(wd)["gates"]["G1"]
        assert g1["state"] == "partial_stale", g1
        assert target["claim_key"] in g1["changed_claim_keys"]
        assert f2["claim_key"] not in g1["changed_claim_keys"], "무관 fact 가 실효됨"


@case
def report_md_change_stales_g3_whole():
    """report_md 변경 → G3 는 파일 해시 전체 실효(stale)."""
    with tempfile.TemporaryDirectory() as td:
        wd, wp, _ = _work(td)
        wp.report_md.write_text("# 초안", encoding="utf-8")
        run_ledger.checkpoint(wd, "G3", "PASS", "verify_facts 통과")
        assert run_ledger.status(wd)["gates"]["G3"]["state"] == "fresh"
        wp.report_md.write_text("# 초안 v2 — 무단 수정", encoding="utf-8")
        g3 = run_ledger.status(wd)["gates"]["G3"]
        assert g3["state"] == "stale" and "report_md" in g3["stale_watches"], g3


@case
def g1_phase_gating():
    """G1 phase 필수 / failed 후 후속 게이트 거부 / awaiting_verification 은 허용."""
    with tempfile.TemporaryDirectory() as td:
        wd, wp, _ = _work(td)
        try:
            run_ledger.checkpoint(wd, "G1", "PASS", "phase 누락")
            assert False, "G1 phase 누락이 통과됨"
        except LedgerError:
            pass
        run_ledger.checkpoint(wd, "G1", "BLOCK", "레인 실패", phase="failed")
        try:
            run_ledger.checkpoint(wd, "LV", "PASS", "재검증 시도")
            assert False, "G1 failed 후 후속 게이트 checkpoint 가 통과됨"
        except LedgerError:
            pass
        run_ledger.checkpoint(wd, "G1", "PASS", "join 재수행", phase="awaiting_verification")
        rec = run_ledger.checkpoint(wd, "LV", "PASS", "재검증 완료")
        assert rec["gate"] == "LV", "awaiting_verification 정상 경로가 막힘"


@case
def validate_readonly_full_diagnostics():
    """validate: 상태 무변경(파일 미생성) + floor·로스터 전 진단 일괄 반환."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("validate_ro", base=td)
        wp = WorkPaths(wd)
        bad = {**_fact(), "id": "F001", "claim_key": "k|삼성|KR|2024|na|na",
               "status": "confirmed", "evidence_ids": []}
        _write_jsonl_atomic(wp.facts, [bad])
        wp.evidence.write_text("", encoding="utf-8")
        (wp.audit / "임시메모.txt").write_text("x", encoding="utf-8")
        r = run_ledger.validate(wd)
        assert not wp.journal("run-ledger.jsonl").exists(), "validate 가 상태를 변경함"
        assert not wp.journal("run-metadata.json").exists(), "validate 가 메타데이터를 씀"
        # 첫 위반에서 멈추지 않고 floor 와 로스터 진단이 모두 채워져야 한다
        assert r["floor"]["b"], "floor(b) 위반 미검출"
        assert r["roster"]["missing"] and r["roster"]["unexpected"], r["roster"]
        assert r["block_level"]


@case
def roster_three_way_classification():
    """audit 로스터(A3): missing / unexpected / legacy 3분류 + verify-<slug>.md 허용."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("roster", base=td)
        wp = WorkPaths(wd)
        (wp.audit / "bx-report.md").write_text("# Bx", encoding="utf-8")
        (wp.audit / "asks.jsonl").write_text("{}", encoding="utf-8")       # 금지된 이벤트성 대장
        (wp.audit / "verify-cagr.md").write_text("# 검산", encoding="utf-8")
        (wp.audit / "낙서.txt").write_text("x", encoding="utf-8")
        roster = run_ledger.validate(wd)["roster"]
        assert "run-receipt.md" in roster["missing"], roster["missing"]
        assert "bx-report.md" not in roster["missing"]
        assert roster["legacy"] == ["asks.jsonl"], roster["legacy"]
        assert roster["unexpected"] == ["낙서.txt"], roster["unexpected"]  # verify-*.md 는 허용


@case
def single_active_ask_and_idempotent_answer():
    """ask 활성 1개 강제(큐잉 안내) + answer 멱등(같은 답 no-op·다른 답 conflict, 원답 보존)."""
    with tempfile.TemporaryDirectory() as td:
        wd, wp, _ = _work(td)
        run_ledger.record(wd, "ask", ask_id="A1", gate_id="PLAN",
                          question="목차 승인?", options=["안1", "안2"])
        try:
            run_ledger.record(wd, "ask", ask_id="A2", gate_id="G2",
                              question="추가 조사?", options=["y", "n"])
            assert False, "활성 ask 존재 중 새 ask 가 통과됨"
        except LedgerError as e:
            assert "큐잉" in str(e), f"큐잉 안내 없음: {e}"
        run_ledger.record(wd, "answer", ask_id="A1", answer="안1", resolved_by="user")
        n = len(_ledger(wp))
        r = run_ledger.record(wd, "answer", ask_id="A1", answer="안1", resolved_by="user")
        assert r is None and len(_ledger(wp)) == n, "같은 답 재적용이 no-op 아님"
        r2 = run_ledger.record(wd, "answer", ask_id="A1", answer="안2", resolved_by="user")
        rows = _ledger(wp)
        assert r2["kind"] == "conflict" and rows[-1]["kind"] == "conflict"
        answers = [x for x in rows if x.get("kind") == "answer" and x["ask_id"] == "A1"]
        assert len(answers) == 1 and answers[0]["answer"] == "안1", "사용자 원답이 보존 안 됨"
        rec = run_ledger.record(wd, "ask", ask_id="A2", gate_id="G2",
                                question="추가 조사?", options=["y", "n"])
        assert rec["kind"] == "ask", "활성 ask 해소 후 새 ask 가 막힘"


@case
def record_kind_field_validation():
    """steering op·disposition 값 enum 검증, 유효 conflict/disposition 은 append."""
    with tempfile.TemporaryDirectory() as td:
        wd, wp, _ = _work(td)
        try:
            run_ledger.record(wd, "steering", op="delete_item", evidence="e", rationale="r")
            assert False, "미정의 steering.op 가 통과됨"
        except LedgerError:
            pass
        try:
            run_ledger.record(wd, "disposition", ref_id="C001", disposition="ignore")
            assert False, "미정의 disposition 값이 통과됨"
        except LedgerError:
            pass
        run_ledger.record(wd, "conflict", conflict_id="C001",
                          fact_ids=["F001"], sources=["a.com", "b.com"])
        run_ledger.record(wd, "disposition", ref_id="C001",
                          disposition="synthesize_range", rationale="범위 병기",
                          decided_by="lead")
        kinds = [r["kind"] for r in _ledger(wp)]
        assert kinds == ["conflict", "disposition"], kinds


@case
def completion_declaration_rules():
    """완료 선언: 11게이트 전건 신선 PASS/WATCH 면 가능, BLOCK 1개면 불가."""
    with tempfile.TemporaryDirectory() as td:
        wd, wp, _ = _work(td)
        wp.report_md.write_text("# 보고서", encoding="utf-8")
        wp.report_pdf.write_bytes(b"%PDF-1.4 fake")
        for g in run_ledger.load_gates():
            kw = {"phase": "complete"} if g["id"] == "G1" else {}
            run_ledger.checkpoint(wd, g["id"], "PASS", f"{g['id']} 통과", **kw)
        st = run_ledger.status(wd)
        assert st["completion_possible"], {k: v["state"] for k, v in st["gates"].items()}
        meta = json.loads(wp.journal("run-metadata.json").read_text(encoding="utf-8"))
        assert meta["completedAt"], "완료 시점이 메타데이터에 없음"
        run_ledger.checkpoint(wd, "G2", "BLOCK", "미처분 충돌 잔존")
        st2 = run_ledger.status(wd)
        assert not st2["completion_possible"], "BLOCK 잔존인데 완료 선언 가능"
        meta2 = json.loads(wp.journal("run-metadata.json").read_text(encoding="utf-8"))
        assert meta2["completedAt"] is None


@case
def generation_increments_on_facts_change():
    """generation: facts 해시가 직전 checkpoint 와 달라질 때만 +1(재동결 세대, AP6 연동)."""
    with tempfile.TemporaryDirectory() as td:
        wd, wp, db = _work(td)
        r1 = run_ledger.checkpoint(wd, "G1", "PASS", "join", phase="complete")
        r2 = run_ledger.checkpoint(wd, "LV", "PASS", "재검증")
        assert r1["generation"] == 1 and r2["generation"] == 1
        db.add_fact(_fact(entity="SK", raw="50.0"))       # 대장 변경 → 재동결
        r3 = run_ledger.checkpoint(wd, "G1", "PASS", "일괄 보수 후 재동결",
                                   phase="complete")
        assert r3["generation"] == 2, r3["generation"]


def main():
    import traceback
    ok = 0
    for fn in CASES:
        try:
            fn(); print(f"  [검출OK] {fn.__name__}"); ok += 1
        except Exception as e:                     # assert 외 예외로 스위트 전체가 죽지 않게
            print(f"  [실패!!] {fn.__name__}: {e}"); traceback.print_exc()
    print(f"\nrun_ledger fixture: {ok}/{len(CASES)} 검출 성공")
    sys.exit(0 if ok == len(CASES) else 1)


if __name__ == "__main__":
    main()
