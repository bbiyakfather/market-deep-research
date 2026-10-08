"""v4 영수증·출고·캡처 회귀: 임시 합성 자료만 사용한다."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import facts_db
import finalize_report
import gates
import manifest
import verify_facts
import verify_claims
from skill_paths import SCRIPTS, WorkPaths, resolve_work_dir


class GatesV4Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.wp = WorkPaths(resolve_work_dir("v4 합성", base=self.temp.name))
        self.wp.facts.write_text("", encoding="utf-8")
        self.wp.evidence.write_text("", encoding="utf-8")
        (self.wp.audit / "research-plan.md").write_text("# 합성 승인 계획\n", encoding="utf-8")

    def first_gates(self):
        quality = self.wp.audit / "quality-checklist.json"
        gates.record_manual(self.wp, "G0", "합성 승인", revision="r1",
                            refs=["audit/quality-checklist.json"] if quality.is_file() else [])
        gates.record_script_result(self.wp, "G1", 0, "합성 join", revision="r1")
        return gates.record_manual(self.wp, "2", "합성 재검증", refs=["facts.jsonl"], revision="r1")

    def complete_gates(self, capture_exempt=False):
        if capture_exempt:
            self.exempt_capture_fact()
        else:
            self.capture_fact()
        facts = facts_db._read_jsonl(self.wp.facts)
        facts[0]["numeric"] = {"base_value": "300.9", "forecast_value": "601.8", "base_year": 2024,
                                "forecast_year": 2034, "cagr_start_year": 2024, "cagr_end_year": 2034,
                                "reported_cagr": "7.2", "precision_digits": 1}
        facts_db._write_jsonl_atomic(self.wp.facts, facts)
        self.first_gates()
        review = verify_claims.scaffold(self.wp, dry_run=True)["rows"][0]
        review.update(support="supported", reviewer="lead", reviewed_at="2026-09-05T18:00:00")
        facts_db._write_jsonl_atomic(self.wp.audit / "claim-review.jsonl", [review])
        self.cli("verify_calculations.py", "run", self.wp.root, "--record-gate")
        self.cli("verify_claims.py", "run", self.wp.root, "--record-gate")
        self.cli("verify_facts.py", self.wp.report_md, self.wp.root)
        # 실제 render_pdf CLI를 별도 프로세스로 실행하되 외부 렌더 엔진만 더미로 치환한다.
        # 선행검사·manifest.extend·[4b] 기록은 제품 코드 그대로 실행한다.
        helper = '''import runpy, sys, subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import preflight
def engine(cmd, **kwargs):
    if cmd[0] == "pandoc":
        Path(cmd[cmd.index("-o") + 1]).write_text("<p>synthetic</p>", encoding="utf-8")
    else:
        target = next(v.split("=", 1)[1] for v in cmd if v.startswith("--print-to-pdf="))
        Path(target).write_bytes(b"%PDF-1.4 synthetic")
    return subprocess.CompletedProcess(cmd, 0, "", "")
script = str(Path(sys.argv[1]) / "render_pdf.py")
sys.argv = [script, sys.argv[2]]
with patch("subprocess.run", side_effect=engine), patch.object(preflight, "_find_chrome", return_value="synthetic-chrome"):
    runpy.run_path(script, run_name="__main__")
'''
        process = subprocess.run([sys.executable, "-c", helper, str(SCRIPTS), str(self.wp.report_md)],
                                 capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.trace.append("render_pdf.py (더미 엔진)\n" + process.stdout)
        self.cli("gates.py", "record", "G4", self.wp.root, "--evidence", "합성 preview", "--revision", "r1")
        self.cli("manifest.py", "verify", self.wp.root)

    def cli(self, script, *args, expected=0):
        process = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                                 capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
        if not hasattr(self, "trace"):
            self.trace = []
        self.trace.append(" ".join([script, *map(str, args)]) + "\n" + process.stdout + process.stderr)
        return process

    def capture_fact(self, state="content", verdict="valid"):
        cap = self.wp.captures / "E001.png"
        cap.write_bytes(b"synthetic image bytes")
        db = facts_db.FactsDB(self.wp.root)
        db.add_fact({"claim": "매출 300.9조", "context": {"metric": "revenue", "entity": "합성 기업",
                     "geography": "KR", "period": "2024"}, "value": {"raw": "300.9", "unit": "KRW_T"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"},
                     "risk": "normal", "status": "pending"})
        digest = gates.sha256_text("합성 원문")
        db.add_evidence({"fact_id": "F001", "type": "table_cell", "source_url": "https://example.org/source",
                         "sha256": digest, "capture": "_captures/E001.png",
                         "capture_review": {"image_sha256": gates.sha256_file(cap), "reviewed_by": "lead",
                                            "reviewed_at": "2026-09-05T18:00:00", "page_state": state,
                                            "claim_visible": state == "content", "context_visible": True,
                                            "verdict": verdict, "note": "합성 fixture"}})
        db.add_verify_event("F001", "lead", "reread", reread_sha256=digest)
        db.set_status("F001", "confirmed")
        self.wp.report_md.write_text("매출은 300.9조원(F001) 입니다.\n\n![](_captures/E001.png)\n", encoding="utf-8")
        return db, cap

    def exempt_capture_fact(self, state="blocked"):
        db, cap = self.capture_fact(state, "invalid")
        evidence = db.evidence()
        evidence[0]["verbatim"] = "합성 원문"
        facts_db._write_jsonl_atomic(self.wp.evidence, evidence)
        facts = db.facts()
        facts[0]["capture_exempt"] = {
            "reason": "자동조회 봇 확인 화면으로 원문 캡처가 불가능하여 대체 결박을 기록함",
            "approved_by": "lead", "approved_at": "2026-09-05T19:30:00",
            "alternative_evidence_id": "E001", "blocker": "bot_challenge"}
        facts_db._write_jsonl_atomic(self.wp.facts, facts)
        return db, cap

    def assert_capture_exemption_rejected(self):
        result = verify_facts.verify(self.wp.report_md, self.wp.root)
        self.assertFalse(result["ok"], result)
        self.assertTrue(any("[유효증빙없음]" in f for f in result["failures"]), result)
        self.assertFalse(any("[증빙면제]" in w for w in result["warnings"]), result)
        self.assertEqual(result["capture_stats"]["exempted"], 0)

    def test_T_EX_1_blocked_capture_exemption_warns(self):
        db, _ = self.exempt_capture_fact()
        before = (self.wp.facts.read_bytes(), self.wp.evidence.read_bytes())
        facts_db.validate_fact(db.facts()[0])
        result = verify_facts.verify(self.wp.report_md, self.wp.root)
        self.assertTrue(result["ok"], result)
        self.assertIn("[증빙면제] F001: bot_challenge — 대체 결박 E001(verbatim+lead 재열람)",
                      result["warnings"])
        self.assertEqual(result["capture_stats"]["exempted"], 1)
        self.assertEqual(result["capture_stats"]["valid_evidence"], 0)
        self.assertEqual(result["capture_stats"]["excluded_page_states"]["blocked"], 1)
        self.assertEqual(before, (self.wp.facts.read_bytes(), self.wp.evidence.read_bytes()))

    def test_T_EX_2_missing_alternative_rejected(self):
        db, _ = self.exempt_capture_fact()
        fact = db.facts()[0]
        del fact["capture_exempt"]["alternative_evidence_id"]
        with self.assertRaises(facts_db.ValidationError):
            facts_db.validate_fact(fact)

    def test_T_EX_3_other_fact_evidence_rejected(self):
        db, _ = self.exempt_capture_fact()
        other = {key: value for key, value in db.facts()[0].items()
                 if key in ("claim", "context", "value", "grade", "risk")}
        other["claim"] = "다른 사실"
        other["context"] = {**other["context"], "entity": "다른 기업"}
        db.add_fact(other)
        db.add_evidence({"fact_id": "F002", "type": "text_quote", "verbatim": "다른 원문",
                         "source_url": "https://example.org/other", "sha256": gates.sha256_text("다른 원문")})
        facts = db.facts()
        facts[0]["capture_exempt"]["alternative_evidence_id"] = "E002"
        facts_db._write_jsonl_atomic(self.wp.facts, facts)
        self.assert_capture_exemption_rejected()
        # evidence_ids만 위조해도 evidence.fact_id의 역방향 연결이 막는다.
        facts[0]["evidence_ids"].append("E002")
        facts_db._write_jsonl_atomic(self.wp.facts, facts)
        self.assert_capture_exemption_rejected()

    def test_T_EX_4_missing_verbatim_rejected(self):
        db, _ = self.exempt_capture_fact()
        for value in (None, "", "   ", 123):
            with self.subTest(verbatim=value):
                evidence = db.evidence()
                evidence[0]["verbatim"] = value
                facts_db._write_jsonl_atomic(self.wp.evidence, evidence)
                self.assert_capture_exemption_rejected()

    def test_T_EX_5_missing_lead_reread_rejected(self):
        db, _ = self.exempt_capture_fact()
        facts = db.facts()
        facts[0]["verify_events"] = []
        facts_db._write_jsonl_atomic(self.wp.facts, facts)
        self.assert_capture_exemption_rejected()

    def test_T_EX_6_content_cannot_claim_bot_block(self):
        self.exempt_capture_fact("content")
        self.assert_capture_exemption_rejected()

    def test_T_EX_7_worker_approval_rejected(self):
        db, _ = self.exempt_capture_fact()
        fact = db.facts()[0]
        fact["capture_exempt"]["approved_by"] = "worker"
        with self.assertRaises(facts_db.ValidationError):
            facts_db.validate_fact(fact)

    def test_capture_exempt_without_capture_warns_once(self):
        db, _ = self.exempt_capture_fact()
        evidence = db.evidence()
        del evidence[0]["capture"]
        del evidence[0]["capture_review"]
        facts_db._write_jsonl_atomic(self.wp.evidence, evidence)
        for blocker in ("bot_challenge", "paywall", "login_required", "http_error", "offline_source"):
            with self.subTest(blocker=blocker):
                facts = db.facts()
                facts[0]["capture_exempt"]["blocker"] = blocker
                facts_db._write_jsonl_atomic(self.wp.facts, facts)
                result = verify_facts.verify(self.wp.report_md, self.wp.root)
                self.assertTrue(result["ok"], result)
                self.assertEqual(sum("[증빙면제]" in w for w in result["warnings"]), 1)
                self.assertEqual(result["capture_stats"]["exempted"], 1)

    def test_capture_exempt_invalid_metadata_keeps_failure(self):
        db, _ = self.exempt_capture_fact()
        original = db.facts()[0]
        invalid = [None, {}, *[{k: v for k, v in original["capture_exempt"].items() if k != missing}
                              for missing in original["capture_exempt"]]]
        invalid += [{**original["capture_exempt"], key: value} for key, value in
                    (("reason", "짧음"), ("reason", " " * 30), ("reason", 123),
                     ("approved_at", " "), ("alternative_evidence_id", "F001"), ("blocker", "unknown"))]
        for exempt in invalid:
            with self.subTest(exempt=exempt):
                fact = {**original, "capture_exempt": exempt}
                with self.assertRaises(facts_db.ValidationError):
                    facts_db.validate_fact(fact)
                facts_db._write_jsonl_atomic(self.wp.facts, [fact])
                self.assert_capture_exemption_rejected()

    def test_capture_exempt_invalid_reread_keeps_failure(self):
        db, _ = self.exempt_capture_fact()
        facts = db.facts()
        for event in ({"by": "worker", "action": "reread", "reread_sha256": "a" * 64},
                      {"by": "lead", "action": "review", "reread_sha256": "a" * 64},
                      *[{"by": "lead", "action": "reread", "reread_sha256": digest}
                        for digest in ("", "a" * 63, "g" * 64, "a" * 64 + "\n")]):
            with self.subTest(event=event):
                facts[0]["verify_events"] = [event]
                facts_db._write_jsonl_atomic(self.wp.facts, facts)
                self.assert_capture_exemption_rejected()

    def test_capture_exempt_does_not_hide_capture_tamper(self):
        _, cap = self.exempt_capture_fact()
        cap.write_bytes(b"replacement")
        result = verify_facts.verify(self.wp.report_md, self.wp.root)
        self.assertFalse(result["ok"], result)
        self.assertTrue(any("[캡처변경]" in f for f in result["failures"]), result)

    def test_capture_exempt_release_is_conditional(self):
        self.complete_gates(capture_exempt=True)
        result = finalize_report.finalize(self.wp)
        self.assertEqual(result["blocking"], [], result)
        self.assertEqual(result["release_status"], "조건부 초안")
        self.assertTrue(any("[증빙면제]" in w for w in result["warnings"]), result)
        self.assertEqual(result["capture_stats"]["exempted"], 1)

    def test_T03_blocked_capture_does_not_change_fact_status(self):
        db, cap = self.capture_fact("blocked", "invalid")
        before = self.wp.facts.read_bytes()
        result = verify_facts.verify(self.wp.report_md, self.wp.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("[유효증빙없음]" in x for x in result["failures"]))
        self.assertEqual(result["capture_stats"]["valid_evidence"], 0)
        self.assertEqual(result["capture_stats"]["excluded_page_states"]["blocked"], 1)
        self.assertEqual(db.facts()[0]["status"], "confirmed")
        self.assertEqual(before, self.wp.facts.read_bytes())

    def test_T04_changed_capture_invalidates_review(self):
        _, cap = self.capture_fact()
        self.assertTrue(verify_facts.verify(self.wp.report_md, self.wp.root)["ok"])
        cap.write_bytes(b"replacement")
        result = verify_facts.verify(self.wp.report_md, self.wp.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("[캡처변경]" in x for x in result["failures"]))

    def test_T10_receipt_reissue_is_append_only(self):
        old = self.first_gates()
        ledger_before = gates.ledger_path(self.wp).read_bytes()
        facts_db.FactsDB(self.wp.root).add_fact({"claim": "새 사실", "context": {"metric": "count",
            "entity": "합성", "geography": "KR", "period": "2026"},
            "value": {"raw": "1", "unit": "개"}, "status": "pending", "risk": "normal",
            "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
        self.assertFalse(gates.check_current_receipt(self.wp, "2")["ok"])
        self.assertTrue(gates.check_prerequisites(self.wp, "2")["ok"])
        new = gates.record_manual(self.wp, "2", "새 사실 확인", refs=["facts.jsonl"])
        self.assertEqual(new["supersedes_receipt"]["ts"], old["ts"])
        self.assertTrue(gates.ledger_path(self.wp).read_bytes().startswith(ledger_before))
        self.assertEqual(len(gates.receipt_history(self.wp, "2")), 2)
        self.assertTrue(gates.check_prerequisites(self.wp, "C")["ok"])

    def test_T11_direct_render_cannot_release(self):
        # 렌더 의존성 없이 함수 직접 호출로 만든 PDF 상태를 재현한다.
        self.wp.report_md.write_text("# 초안\n", encoding="utf-8")
        self.wp.report_pdf.write_bytes(b"%PDF-1.4 draft")
        result = finalize_report.finalize(self.wp)
        self.assertEqual((result["release_status"], result["exit"]), ("재검토 필요", 1))
        self.assertEqual(gates.receipt_history(self.wp, "G6")[-1]["exit"], 1)

    def test_T12_revision_mismatch_blocks_release(self):
        self.complete_gates()
        gates.record_manual(self.wp, "2", "r2 재검증", revision="r2")
        self.assertIn("[2]", gates.release_check(self.wp)["revision_mismatch"])
        self.assertEqual(finalize_report.finalize(self.wp)["release_status"], "재검토 필요")

    def test_T_REL_1_complete_same_revision_releases(self):
        self.complete_gates()
        result = json.loads(self.cli("finalize_report.py", self.wp.root).stdout)
        self.assertEqual(result["blocking"], [])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["release_status"], "최종")
        self.assertEqual(gates.receipt_history(self.wp, "G6")[-1]["exit"], 0)
        print("\nCLI C→R→G3→[4b]→G4→G5→G6 실제 출력:\n" + "\n".join(self.trace))

    def test_T_ALIAS_legacy_G5c(self):
        gates._append(self.wp, {"gate": "G5c", "exit": 0, "ts": "legacy"})
        self.assertEqual(gates.receipt_history(self.wp, "[C]")[-1]["gate"], "G5c")
        with self.assertRaises(gates.GateError):
            gates.require_bound_receipt(self.wp, "[C]")

    def test_unbound_disclosed_conflict_blocks(self):
        self.complete_gates()
        (self.wp.audit / "calculation-checks.jsonl").write_text(
            json.dumps({"result": "MISMATCH", "fact_id": "F001", "disclosed": True}) + "\n", encoding="utf-8")
        result = finalize_report.finalize(self.wp)
        self.assertEqual((result["release_status"], result["exit"]), ("재검토 필요", 1))
        result = finalize_report.finalize(self.wp, allow_conditional=True)
        self.assertEqual(result["exit"], 1)

    def test_legacy_revision_is_warning(self):
        self.complete_gates()
        legacy = {k: v for k, v in gates.receipt_history(self.wp, "G1")[-1].items()
                  if k not in ("revision_id", "run_id")}
        gates._append(self.wp, legacy)
        result = gates.release_check(self.wp)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["warnings"])
        self.assertEqual(result["gates"]["G1"]["revision_id"], "(미기록)")

    def test_plan_drift_still_blocks_G4(self):
        self.complete_gates()
        (self.wp.audit / "research-plan.md").write_text("변경된 계획", encoding="utf-8")
        with self.assertRaises(gates.GateError):
            gates.record_manual(self.wp, "G4", "다시 검사")

    def test_explicit_release_revision_must_match(self):
        self.complete_gates()
        result = finalize_report.finalize(self.wp, revision="r2")
        self.assertEqual(result["release_status"], "재검토 필요")
        self.assertFalse(manifest.verify(self.wp, revision="r2")["ok"])

    def test_search_scope_uses_shared_hedge_rules(self):
        facts = {"F001": {"value": {"raw": "문자"}}}
        failed, _ = verify_facts.check_v4_audits("세계 최초 제품(F001).", facts, self.wp, {"F001"})
        self.assertTrue(any("검색범위없음" in x for x in failed))
        failed, _ = verify_facts.check_v4_audits("조사한 범위에서 유일한 제품(F001).", facts, self.wp, {"F001"})
        self.assertTrue(any("검색범위없음" in x for x in failed))

    def test_G3_regression_flag_never_writes_receipt(self):
        self.capture_fact()
        self.first_gates()
        before = gates.ledger_path(self.wp).read_bytes()
        command = [sys.executable, str(Path(verify_facts.__file__)), str(self.wp.report_md), str(self.wp.root)]
        strict = subprocess.run(command, capture_output=True)
        self.assertEqual(strict.returncode, 1)
        regression = subprocess.run(command + ["--allow-missing-cr"], capture_output=True)
        self.assertEqual(regression.returncode, 0, regression.stderr)
        self.assertEqual(before, gates.ledger_path(self.wp).read_bytes())
        self.assertFalse(self.wp.manifest.exists())

    def test_quality_denominator_preserves_predeclared_exclusion(self):
        (self.wp.audit / "quality-checklist.json").write_text(json.dumps({
            "수치·계산 일관성": [{"name": "구조화", "applicable": True},
                                {"name": "환산", "applicable": False, "reason": "G0 환산 OFF"}]
        }, ensure_ascii=False), encoding="utf-8")
        self.complete_gates()
        result = finalize_report.finalize(self.wp)
        self.assertEqual(result["release_status"], "최종")
        report = (self.wp.audit / "release-status.md").read_text(encoding="utf-8")
        self.assertIn("| 수치·계산 일관성 | 20 | 1/2 |", report)
        self.assertIn("비적용: G0 환산 OFF", report)

    def test_forged_R_with_unsupported_review_cannot_release(self):
        self.complete_gates()
        review_path = self.wp.audit / "claim-review.jsonl"
        reviews = facts_db._read_jsonl(review_path)
        reviews[0].update(support="unsupported", required_qualification="확인하지 못했다")
        facts_db._write_jsonl_atomic(review_path, reviews)
        forged = dict(gates.receipt_history(self.wp, "[R]")[-1])
        forged.update(claim_review_sha256=gates.sha256_file(review_path), failure_count=0)
        gates._append(self.wp, forged)
        result = finalize_report.finalize(self.wp)
        self.assertEqual(result["release_status"], "재검토 필요")
        self.assertTrue(any("미지원" in issue for issue in result["blocking"]))
        self.assertFalse(gates.check_current_receipt(self.wp, "[R]")["ok"])

    def test_owned_receipt_missing_binding_rejected(self):
        self.first_gates()
        before = gates.ledger_path(self.wp).read_bytes()
        for gate in ("C", "R", "G3", "[4b]", "G5"):
            with self.assertRaisesRegex(gates.GateError, "필수 extra"):
                gates.record_script_result(self.wp, gate, 0)
        self.assertEqual(before, gates.ledger_path(self.wp).read_bytes())

    def test_missing_prerequisites_do_not_write_audits_or_receipts(self):
        self.capture_fact()
        for script in ("verify_calculations.py", "verify_claims.py"):
            self.cli(script, "run", self.wp.root, "--record-gate", expected=1)
        self.assertFalse(gates.ledger_path(self.wp).exists())
        self.assertFalse((self.wp.audit / "calculation-checks.jsonl").exists())

    def test_receipt_only_missing_and_prerequisite_default(self):
        self.assertFalse(gates.check_gate(self.wp, "G3", mode="receipt-only")["ok"])
        self.cli("gates.py", "check", "G3", self.wp.root, "--receipt-only", expected=1)
        self.complete_gates()
        gates.record_script_result(self.wp, "G5", 1, "무결성 실패", extra={
            "manifest_sha256": gates.sha256_file(self.wp.manifest)})
        self.assertTrue(gates.check_gate(self.wp, "G5")["ok"])
        self.assertFalse(gates.check_gate(self.wp, "G5", include_current=True)["ok"])
        self.cli("manifest.py", "verify", self.wp.root)
        self.assertTrue(gates.check_current_receipt(self.wp, "G5")["ok"])

    def test_script_reissue_links_previous_success_and_preserves_bytes(self):
        self.complete_gates()
        old = gates.receipt_history(self.wp, "C")[-1]
        before = gates.ledger_path(self.wp).read_bytes()
        self.cli("verify_calculations.py", "run", self.wp.root, "--record-gate")
        new = gates.receipt_history(self.wp, "C")[-1]
        self.assertEqual(new["supersedes_receipt"]["ts"], old["ts"])
        self.assertTrue(gates.ledger_path(self.wp).read_bytes().startswith(before))

    def test_calc_audit_tamper_blocks_release(self):
        self.complete_gates()
        audit = self.wp.audit / "calculation-checks.jsonl"
        audit.write_text("", encoding="utf-8")
        self.assertFalse(gates.check_prerequisites(self.wp, "R")["ok"])
        self.assertEqual(finalize_report.finalize(self.wp)["release_status"], "재검토 필요")

    def test_disclosure_binding_requires_current_sentence_fact_and_hash(self):
        self.complete_gates()
        reviews = facts_db._read_jsonl(self.wp.audit / "claim-review.jsonl")
        disclosure = {"sentence_id": reviews[0]["sentence_id"], "fact_id": "F001",
                      "report_md_sha256": gates.sha256_file(self.wp.report_md)}
        row = {"fact_id": "F001", "result": "MISMATCH", "disclosed": disclosure}
        self.assertTrue(finalize_report._disclosure_bound(row, reviews, self.wp))
        for bad in (True, {**disclosure, "sentence_id": "missing"},
                    {**disclosure, "fact_id": "F999"}, {**disclosure, "report_md_sha256": "0" * 64}):
            self.assertFalse(finalize_report._disclosure_bound({**row, "disclosed": bad}, reviews, self.wp))

    def test_capture_review_warn_vs_fail_and_context(self):
        db, _ = self.capture_fact()
        evs = db.evidence()
        del evs[0]["capture_review"]
        facts_db._write_jsonl_atomic(self.wp.evidence, evs)
        facts_db.validate_evidence(evs[0], work=self.wp)
        result = verify_facts.verify(self.wp.report_md, self.wp.root)
        self.assertTrue(any("캡처미검토" in v for v in result["failures"]))
        facts = {row["id"]: row for row in db.facts()}
        facts["F001"]["value"]["raw"] = "제품 속성"
        result = verify_facts.check_capture_reviews(facts, {"E001": evs[0]}, self.wp, {"F001"})
        self.assertEqual(result["failures"], [])
        self.assertTrue(any("캡처미검토" in v for v in result["warnings"]))
        facts["F001"]["risk"] = "high"
        result = verify_facts.check_capture_reviews(facts, {"E001": evs[0]}, self.wp, set())
        self.assertTrue(result["failures"])

    def test_numeric_capture_missing_context_fails_G3(self):
        db, _ = self.capture_fact()
        evs = db.evidence()
        evs[0]["capture_review"]["context_visible"] = False
        facts_db._write_jsonl_atomic(self.wp.evidence, evs)
        result = verify_facts.verify(self.wp.report_md, self.wp.root)
        self.assertTrue(any("context_visible" in v for v in result["failures"]))

    def test_unatomized_fact_blocks_finalize(self):
        self.complete_gates()
        facts = facts_db._read_jsonl(self.wp.facts)
        del facts[0]["numeric"]
        facts[0]["value"]["raw"] = "300.9(2024)->601.8(2034), CAGR 7.2%"
        facts_db._write_jsonl_atomic(self.wp.facts, facts)
        result = finalize_report.finalize(self.wp)
        self.assertEqual(result["release_status"], "재검토 필요")
        self.assertTrue(any("검산 불가 차단" in v for v in result["blocking"]))


if __name__ == "__main__":
    unittest.main()
