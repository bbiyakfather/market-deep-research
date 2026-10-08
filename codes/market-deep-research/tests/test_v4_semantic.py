"""v4 의미 검증 회귀: 실제 조사물을 읽지 않고 임시 합성 대장만 사용한다."""
from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import facts_db
from skill_paths import SCRIPTS, WorkPaths, resolve_work_dir
from facts_db import (FactsDB, ValidationError, _write_jsonl_atomic, _write_text_atomic,
                      make_claim_key, needs_search_scope, validate_fact, validate_evidence)
import verify_calculations as calculations
import verify_claims as claims


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fact_fixture(**changes):
    row = {"id": "F001", "claim": "KC인증·노선 적용",
           "context": {"metric": "deployment", "entity": "합성기업", "geography": "KR", "period": "2025"},
           "value": {"raw": "KC인증·노선 적용", "unit": "건"},
           "grade": {"authority": "A", "independence": "B", "directness": "A", "recency": "A"},
           "risk": "normal", "status": "pending", "evidence_ids": [], "verify_events": []}
    row["claim_key"] = make_claim_key(row["context"])
    row.update(changes)
    return row


def evidence_fixture(**changes):
    row = {"id": "E001", "fact_id": "F001", "type": "text_quote",
           "source_url": "https://example.invalid/source", "verbatim": "KC인증·노선 적용",
           "sha256": digest("합성 원문"), "accessed_at": "2026-09-05T18:00:00"}
    row.update(changes)
    return row


def scope_fixture():
    return {"queries": ["합성 기술 최초"], "sources": ["합성 특허 DB"],
            "searched_at": "2026-09-05", "geo_scope": "KR+US+EP", "period_scope": "2015-2026",
            "results_reviewed": 12, "known_gaps": "공식 등록원장 미조회"}


def numeric_fixture(**changes):
    row = {"base_value": "4.5", "forecast_value": "12.8", "base_year": 2025,
           "forecast_year": 2035, "reported_cagr": "17.8", "cagr_start_year": 2025,
           "cagr_end_year": 2035, "precision_digits": 1, "currency": "USD", "scale": "billion"}
    row.update(changes)
    return row


class V4SemanticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.wp = WorkPaths(resolve_work_dir("합성 v4 회귀", base=self.temp.name))
        self.db = FactsDB(self.wp)

    def confirmed(self):
        self.db.add_fact(fact_fixture())
        self.db.add_evidence(evidence_fixture())
        self.db.add_verify_event("F001", "lead", "reread", reread_sha256=digest("합성 원문"))
        return self.db.set_status("F001", "confirmed")

    def review(self, body, support="supported", qualification="", **changes):
        _write_text_atomic(self.wp.report_md, "# 부 3. 사업화\n" + body)
        sentence = claims.extract_claim_sentences(self.wp.report_md.read_text(encoding="utf-8"))[0]
        row = {**sentence, "claim_type": "observed", "reviewed_text_sha256": digest(sentence["text"]),
               "evidence_ids": ["E001"], "support": support, "unsupported_terms": [],
               "required_qualification": qualification, "reviewer": "lead", "reviewed_at": "2026-09-05T18:00:00",
               # 결박은 대장 파일 전체가 아니라 **문장이 인용한 사실**에만 건다
               # (전체 해시로 묶으면 무관한 사실 한 건 정정에 전 문장 검토가 무효가 된다).
               "evidence_revision": claims.cited_revision(
                   {r["id"]: r for r in facts_db._read_jsonl(self.wp.facts)}, sentence["fact_ids"])}
        row.update(changes)
        _write_jsonl_atomic(self.wp.audit / "claim-review.jsonl", [row])
        return row

    def cli(self, name, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                              text=True, encoding="utf-8", capture_output=True, check=False)

    def test_T01_semantic_expansion_rejected(self):
        self.confirmed()
        self.review("배터리 없는 센서를 상용 노선에 올렸다(F001).", "unsupported", "EH 적용은 원문에서 확인되지 않음",
                    unsupported_terms=["배터리 없는"])
        result = claims.run(self.wp)
        self.assertTrue(any("미지원" in f for f in result["failures"]))
        proc = self.cli("verify_claims.py", "run", self.wp.root, "--dry-run")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_T02_partial_with_qualification(self):
        self.confirmed()
        qualification = "무전원·에너지하베스팅 적용 여부는 확인되지 않는다"
        for body in (f"KC인증 제품을 노선에 적용했다(F001); {qualification}.",
                     f"KC인증 제품을 노선에 적용했다(F001). {qualification}."):
            with self.subTest(body=body):
                self.review(body, "partial", qualification)
                self.assertEqual(claims.run(self.wp, dry_run=True)["failures"], [])
        self.assertEqual(self.cli("verify_claims.py", "run", self.wp.root, "--dry-run").returncode, 0)

    def test_T03_changed_text_requires_review(self):
        self.confirmed()
        self.review("제품을 노선에 적용했다(F001).")
        _write_text_atomic(self.wp.report_md, "# 부 3. 사업화\n제품을 전국 노선에 적용했다(F001).")
        self.assertTrue(any("문장변경" in f for f in claims.run(self.wp)["failures"]))

    def test_T04_coverage_including_untagged_superlative(self):
        self.confirmed()
        _write_text_atomic(self.wp.report_md, "# 부 3. 적용\n노선에 적용했다(F001). 세계 유일 기술이다.")
        result = claims.run(self.wp, dry_run=True)
        self.assertEqual(result["stats"]["unreviewed"], 2)
        self.assertEqual(len(result["failures"]), 2)

    def test_T05_cagr_conflict_and_cli_exit(self):
        row = fact_fixture(id="F091", numeric=numeric_fixture())
        before = copy.deepcopy(row)
        result = calculations.check_fact(row)
        self.assertEqual(result["computed"], "11.02")
        self.assertEqual(result["result"], "MISMATCH")
        self.assertEqual(result["severity"], "실제 충돌")
        self.assertEqual(row, before)
        _write_jsonl_atomic(self.wp.facts, [row])
        original = self.wp.facts.read_bytes()
        proc = self.cli("verify_calculations.py", "run", self.wp.root)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("11.02", proc.stdout)
        self.assertEqual(original, self.wp.facts.read_bytes())

    def test_T06_rounding_and_periods(self):
        numeric = numeric_fixture()
        lower, upper = calculations.rounding_band(numeric)
        self.assertLess(lower, Decimal("11.0"))
        self.assertGreater(upper, Decimal("11.0"))
        self.assertLess(upper, Decimal("17.8"))
        self.assertEqual(calculations.check_fact({"numeric": numeric_fixture(reported_cagr="11.0")})["result"], "MATCH")
        result = calculations.check_fact({"numeric": numeric_fixture(cagr_start_year=2028)})
        self.assertEqual(result["result"], "NOT_CHECKABLE")
        self.assertIn("CAGR 산정기간이 값 기간과 다름", result["note"])
        inferred = numeric_fixture()
        del inferred["precision_digits"]
        self.assertEqual(calculations.rounding_band(inferred), (lower, upper))
        for invalid in (numeric_fixture(forecast_year=2025, cagr_end_year=2025),
                        numeric_fixture(base_value="0"), numeric_fixture(reported_cagr="NaN")):
            self.assertEqual(calculations.check_fact({"numeric": invalid})["result"], "NOT_CHECKABLE")

    def test_T07_search_scope_and_hedges(self):
        with self.assertRaises(ValidationError):
            self.db.add_fact(fact_fixture(claim="세계 유일 기술"))
        self.db.add_fact(fact_fixture(claim="세계 유일 기술", search_scope=scope_fixture()))
        self.assertFalse(needs_search_scope({"claim": "조사한 범위에서 확인하지 못했다"}))
        self.assertTrue(needs_search_scope({"claim": "조사한 범위에서 유일하며 추가 사례 없음"}))
        for text in ("조사한 범위에서 국내 최초", "미확인이나 세계 3번째", "확인되지 않으나 0건"):
            self.assertTrue(needs_search_scope({"claim": text}), text)
        self.assertFalse(needs_search_scope({"claim": "제품 10건을 확인했다"}))
        self.assertFalse(needs_search_scope({"claim": "readonly 인터페이스"}))
        self.assertTrue(needs_search_scope({"claim": "조사한 범위", "value": {"raw": "유일"}}))
        for text in ("only supplier", "no commercial product", "first in market", "사례 전무"):
            self.assertTrue(needs_search_scope({"claim": text}))

    def test_T08_hypothesis_cannot_confirm(self):
        self.db.add_fact(fact_fixture(claim_type="hypothesis"))
        self.db.add_evidence(evidence_fixture())
        self.db.add_verify_event("F001", "lead", "reread", reread_sha256=digest("원문"))
        with self.assertRaises(ValidationError):
            self.db.set_status("F001", "confirmed")
        self.assertEqual(self.db.facts()[0]["status"], "pending")

    def test_T09_incomplete_numeric(self):
        for numeric in ({"base_value": "4.5"}, {"reported_cagr": "17.8"}, numeric_fixture(base_value="NaN")):
            with self.subTest(numeric=numeric), self.assertRaises(ValidationError):
                validate_fact(fact_fixture(numeric=numeric))
        self.assertIsNotNone(validate_fact(fact_fixture(numeric={})))

    def capture(self, **changes):
        capture_file = self.wp.captures / "E001.png"
        capture_file.write_bytes(b"synthetic capture bytes")
        review = {"image_sha256": hashlib.sha256(capture_file.read_bytes()).hexdigest(),
                  "reviewed_by": "lead", "reviewed_at": "2026-09-05T18:00:00",
                  "page_state": "content", "claim_visible": True, "context_visible": True,
                  "verdict": "valid", "note": "합성 캡처"}
        review.update(changes)
        return evidence_fixture(capture="_captures/E001.png", capture_review=review)

    def test_T_CAP_1_capture_review_required(self):
        self.assertIsNotNone(validate_evidence(evidence_fixture(capture="_captures/E001.png")))

    def test_T_CAP_2_blocked_not_valid(self):
        row = self.capture(page_state="blocked")
        with self.assertRaises(ValidationError):
            validate_evidence(row, work=self.wp)
        row["capture_review"]["verdict"] = "invalid"
        self.assertEqual(validate_evidence(row, work=self.wp), row)
        with self.assertRaises(ValidationError):
            validate_evidence(self.capture(claim_visible=False), work=self.wp)

    def test_T_CAP_3_capture_hash(self):
        row = self.capture(image_sha256="0" * 64)
        with self.assertRaisesRegex(ValidationError, "재검토 필요"):
            validate_evidence(row, work=self.wp)
        self.assertEqual(validate_evidence(row), row)
        self.assertIsNotNone(validate_evidence(self.capture(), work=self.wp))

    def test_T_NEG_1_scope_before_evidence_write(self):
        self.db.add_fact(fact_fixture())
        before = self.wp.facts.read_bytes()
        with self.assertRaises(ValidationError):
            self.db.add_evidence(evidence_fixture(type="negative_search"))
        self.assertFalse(self.wp.evidence.exists())
        self.assertEqual(before, self.wp.facts.read_bytes())
        rows = self.db.facts()
        rows[0]["search_scope"] = scope_fixture()
        _write_jsonl_atomic(self.wp.facts, rows)
        self.assertEqual(self.db.add_evidence(evidence_fixture(type="negative_search"))["id"], "E001")

    def test_T_REC_1_recommendation_block(self):
        with self.assertRaises(ValidationError):
            validate_fact(fact_fixture(claim_type="recommendation"))
        block = {"supported_facts": [], "assumptions": [], "unresolved_conditions": [], "next_validation": []}
        validate_fact(fact_fixture(claim_type="recommendation", recommendation=block))
        del block["assumptions"]
        with self.assertRaises(ValidationError):
            validate_fact(fact_fixture(claim_type="recommendation", recommendation=block))

    def test_T_COMPAT_v3_rows_unchanged(self):
        fact, evidence = fact_fixture(), evidence_fixture()
        before = copy.deepcopy((fact, evidence))
        validate_fact(fact)
        validate_evidence(evidence)
        self.assertEqual((fact, evidence), before)
        self.confirmed()

    def test_raw_composite_dry_run_and_strict(self):
        rows = [fact_fixture(id="F091", value={"raw": "4.5(2025)->12.8(2035), CAGR 17.8%", "unit": "USD"}),
                fact_fixture(id="F092", value={"raw": "85.68 million(2025) -> 493.35 million(2034)", "unit": "USD"})]
        _write_jsonl_atomic(self.wp.facts, rows)
        before = {p.relative_to(self.wp.root): p.read_bytes() for p in self.wp.root.rglob("*") if p.is_file()}
        result = calculations.run(self.wp, dry_run=True)
        self.assertEqual(result["not_checkable"], 2)
        self.assertEqual(result["rows"][0]["missing_fields"], ["numeric"])
        after = {p.relative_to(self.wp.root): p.read_bytes() for p in self.wp.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(self.cli("verify_calculations.py", "run", self.wp.root, "--dry-run").returncode, 1)
        self.assertEqual(self.cli("verify_calculations.py", "run", self.wp.root, "--dry-run", "--strict").returncode, 1)

    def test_extraction_skips_markup_and_keeps_table_rows(self):
        body = '''# 부 3. 기술
제품은 4.5 USD다(F001). 적용했다(F002)!
```python
최초(F099)
```
<style>
없음(F099)
</style>
![최초(F099)](image.png)
<img src="x" alt="없음(F099)">
<figure>
최초(F099)
</figure>
그림 1. 최초(F099)
|대상|사실|
|---|---|
|제품|사실(F003). 두 표현(F004).|
# 부 4. 권고
권고한다(F005).
<!-- FACTSHEET:APPENDIX -->
최초(F099)
'''
        rows = claims.extract_claim_sentences(body)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["sentence_id"], "P03-S001")
        self.assertEqual(rows[-1]["sentence_id"], "P04-S001")
        self.assertEqual(rows[3]["fact_ids"], ["F003", "F004"])
        self.assertNotIn("F099", str(rows))

    def test_hash_fallback_when_sentence_id_shifts(self):
        self.confirmed()
        self.review("노선에 적용했다(F001).")
        _write_text_atomic(self.wp.report_md, "# 부 3. 사업화\n설명 문장이다. 노선에 적용했다(F001).")
        result = claims.run(self.wp, dry_run=True)
        self.assertEqual(result["failures"], [])

    def test_missing_qualification_and_disputed_fact(self):
        self.confirmed()
        self.review("노선에 적용했다(F001).", "partial", "무전원·에너지하베스팅 적용 여부는 확인되지 않는다")
        self.assertTrue(any("검사 조각" in f for f in claims.run(self.wp)["failures"]))
        self.db.set_status("F001", "disputed")
        self.review("노선에 적용했다(F001).")
        self.assertTrue(any("disputed F001" in f for f in claims.run(self.wp)["failures"]))
        qualification = "무전원·에너지하베스팅 적용 여부는 확인되지 않는다"
        self.review(f"노선에 적용했다(F001). {qualification}.", "partial", qualification)
        self.assertTrue(claims.run(self.wp)["ok"])

    def test_recommendation_review_requires_basis(self):
        self.confirmed()
        self.review("실증부터 추진할 것을 권고한다(F001).", claim_type="recommendation")
        self.assertTrue(any("권고근거없음" in f for f in claims.run(self.wp)["failures"]))
        self.review("실증부터 추진할 것을 권고한다(F001).", claim_type="recommendation",
                    assumptions=[], unresolved_conditions=[])
        self.assertTrue(claims.run(self.wp)["ok"])

    def test_scaffold_never_overwrites_reviews(self):
        self.confirmed()
        self.review("노선에 적용했다(F001).")
        original = (self.wp.audit / "claim-review.jsonl").read_bytes()
        _write_text_atomic(self.wp.report_md, "# 부 3. 사업화\n노선에 적용했다(F001). 세계 최초 기술이다.")
        result = claims.scaffold(self.wp)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["rows"][0]["support"], "unresolved")
        self.assertEqual(original, (self.wp.audit / "claim-review.jsonl").read_bytes())
        before = {p: p.read_bytes() for p in self.wp.audit.iterdir()}
        claims.run(self.wp, dry_run=True)
        claims.scaffold(self.wp, dry_run=True)
        self.assertEqual(before, {p: p.read_bytes() for p in self.wp.audit.iterdir()})

    def test_revision_and_evidence_links(self):
        self.confirmed()
        self.review("노선에 적용했다(F001).", evidence_ids=["E999"])
        self.assertTrue(any("증거연결" in f for f in claims.run(self.wp)["failures"]))
        self.review("노선에 적용했다(F001).", evidence_revision="0" * 12)
        self.assertTrue(any("근거변경" in f for f in claims.run(self.wp)["failures"]))

    def test_derived_requires_explicit_inputs(self):
        with self.assertRaises(ValidationError):
            validate_fact(fact_fixture(claim_type="derived"))
        validate_fact(fact_fixture(claim_type="derived", numeric=numeric_fixture()))
        validate_fact(fact_fixture(claim_type="derived", input_fact_ids=["F002"]))

    def test_record_gate_dry_run_never_writes(self):
        self.confirmed()
        self.review("노선에 적용했다(F001).")
        for name in ("verify_claims.py", "verify_calculations.py"):
            proc = self.cli(name, "run", self.wp.root, "--dry-run", "--record-gate")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse((self.wp.audit / "gates.jsonl").exists())

    def test_rounding_interval_overlap_positive(self):
        with patch.object(calculations, "rounding_band", return_value=(Decimal("21.33"), Decimal("21.34"))), \
                patch.object(calculations, "cagr", return_value=Decimal("21.33")):
            row = calculations.check_fact({"numeric": numeric_fixture(reported_cagr="21.3")})
        self.assertEqual(row["result"], "MATCH")
        self.assertEqual(row["severity"], "없음")
        for numeric in (numeric_fixture(base_value="802.4", forecast_value="2248.7", reported_cagr="10.85"),
                        numeric_fixture(base_value="85.68", forecast_value="493.35", reported_cagr="21.5",
                                        forecast_year=2034, cagr_end_year=2034, precision_digits=2)):
            self.assertEqual(calculations.check_fact({"numeric": numeric})["result"], "MATCH")

    def test_unatomized_requires_complete_exemption(self):
        row = fact_fixture(value={"raw": "4.5(2025)->12.8(2035), CAGR 17.8%", "unit": "USD"})
        _write_jsonl_atomic(self.wp.facts, [row])
        self.assertEqual(self.cli("verify_calculations.py", "run", self.wp.root).returncode, 1)
        self.assertEqual(calculations.run(self.wp, dry_run=True)["not_checkable_blocking"], 1)
        row["calc_exempt"] = {"reason": "원출처 시계열 기준 불일치", "approved_by": "lead", "approved_at": "2026-09-05"}
        validate_fact(row)
        _write_jsonl_atomic(self.wp.facts, [row])
        self.assertEqual(self.cli("verify_calculations.py", "run", self.wp.root).returncode, 0)
        self.assertIn("원출처 시계열", calculations.run(self.wp, dry_run=True)["rows"][0]["note"])
        for key in tuple(row["calc_exempt"]):
            bad = copy.deepcopy(row)
            del bad["calc_exempt"][key]
            with self.assertRaises(ValidationError):
                validate_fact(bad)
        _write_jsonl_atomic(self.wp.facts, [fact_fixture(numeric=numeric_fixture(cagr_start_year=2028))])
        self.assertEqual(calculations.run(self.wp, dry_run=True)["not_checkable_blocking"], 0)

    def test_search_scope_property_counterexamples(self):
        for text, expected in (("제품에는 배터리가 없다", False), ("해당 없음", False),
                               ("적용 사례가 없다", True), ("검색 범위에서 확인하지 못했다", False),
                               ("국내 최초", True), ("조사한 범위에서 유일", True)):
            self.assertEqual(needs_search_scope({"claim": text}), expected, text)

    def test_qualification_preserves_polarity_and_short_phrases(self):
        required = "무전원 에너지하베스팅 적용 여부는 원문에서 확인되지 않는다"
        ok, reason = claims._qualification(required, "무전원 에너지하베스팅 적용 기술이다", "")
        self.assertFalse(ok)
        self.assertIn("부정/조건 표지 불일치", reason)
        for required in ("조건부", "확인하지 못했다"):
            self.assertTrue(claims._qualification(required, required, "")[0])
            self.assertTrue(claims._qualification(required, "대상 기술이다", required)[0])

    def test_html_block_boundaries_and_inline_text(self):
        for boundary in ("</p><p>", "<br/>", "<br>", "</div><div>", "</li><li>"):
            rows = claims.extract_claim_sentences("<p>첫 <b>주장</b>(F001)." + boundary + "둘째 주장(F002).</p>")
            self.assertEqual([r["fact_ids"] for r in rows], [["F001"], ["F002"]])
            self.assertEqual(rows[0]["text"], "첫 주장(F001).")

    def test_strict_capture_context_only_for_numeric(self):
        row = self.capture(context_visible=False)
        facts_db.validate_capture_review(row["capture_review"], "E001")
        with self.assertRaisesRegex(ValidationError, "context_visible"):
            facts_db.validate_capture_review(row["capture_review"], "E001", strict_context=True)


if __name__ == "__main__":
    unittest.main()
