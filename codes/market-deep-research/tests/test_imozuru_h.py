"""imozuru 강화안 H1~H11 회귀: 문장 인용 강제·뒷받침 제안·빌드 중단·증빙판 HTML·본문 하한·축별 근거."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_evidence_html as bev
import fetch
import gates
import render_pdf
import verify_facts as vf
from facts_db import FactsDB, _read_jsonl, _write_jsonl_atomic
from skill_paths import WorkPaths, resolve_work_dir
from test_p0_regressions import cli, start_chain, work  # noqa: F401 — pytest fixture


def _f(fid="F001", **kw):
    base = {"id": fid, "status": "confirmed", "claim_type": "observed", "evidence_ids": ["E001"],
            "value": {"raw": "300.9조원", "unit": "KRW"},
            "context": {"entity": "삼성전자", "period": "2024"}}
    return {**base, **kw}


def _e(eid="E001", **kw):
    return {**{"id": eid, "type": "text_quote", "verbatim": "삼성전자 2024년 매출 300.9조원"}, **kw}


SENT = "삼성전자 2024년 매출은 300.9조원이다(F001).\n"


# --- H1 ----------------------------------------------------------------------
def test_h1_sentence_without_passed_quote_fails_in_v4_and_warns_in_v3():
    facts, ev = {"F001": _f()}, {"E001": _e()}
    fail, warn = vf.check_sentence_quotes(SENT, facts, ev, passed=set(), strict=True)   # 바꿔 쓴 인용 = 대조 탈락
    assert fail and "[문장인용없음] F001" in fail[0] and not warn
    fail, warn = vf.check_sentence_quotes(SENT, facts, ev, passed=set(), strict=False)
    assert not fail and "[문장인용없음]" in warn[0]
    assert vf.check_sentence_quotes(SENT, facts, ev, passed={"E001"}, strict=True) == ([], [])


def test_h1_non_quote_evidence_and_exemptions():
    ev = {"E001": _e(type="table_cell")}
    assert vf.check_sentence_quotes(SENT, {"F001": _f()}, ev, {"E001"}, True)[0]          # text_quote 가 아니면 불인정
    soft = _f(capture_only_reason="로그인 벽 뒤 캡처만 가능")
    fail, _ = vf.check_sentence_quotes(SENT, {"F001": soft}, ev, set(), True)
    assert fail                                                                            # 사유만 적은 우회는 불인정
    accepted = {"E001": _e(type="table_cell", capture_review={"verdict": "accept"})}
    fail, warn = vf.check_sentence_quotes(SENT, {"F001": soft}, accepted, set(), True)
    assert not fail and warn                                                               # accept 캡처 + 사유 → WARN
    fail, warn = vf.check_sentence_quotes(SENT, {"F001": _f()}, {"E001": _e()}, set(), True, no_clean={"E001"})
    assert not fail and "clean 원문 없음" in warn[0]                                        # 대조 불가(clean 부재) → WARN
    assert vf.check_sentence_quotes(SENT, {"F001": _f(claim_type="derived")}, ev, set(), True) == ([], [])


def test_h1_integrated_paraphrased_quote_blocks_g3(work):
    assert vf.verify(work.report_md, work)["ok"]
    rows = _read_jsonl(work.evidence)
    rows[0]["verbatim"] = "Certification and deployment happened. Energy unknown."      # 원문과 다르게 바꿔 씀
    _write_jsonl_atomic(work.evidence, rows)
    rep = vf.verify(work.report_md, work)
    assert not rep["ok"] and any("[문장인용없음] F001" in x for x in rep["failures"])


# --- H2 ----------------------------------------------------------------------
def test_h2_support_levels_and_partial_mark():
    facts = {"F001": _f()}
    full = vf.suggest_support(facts, {"E001": _e()}, {"E001"})
    assert full["F001"]["support"] == "supported"
    part = vf.suggest_support(facts, {"E001": _e(verbatim="매출 300.9조원")}, {"E001"})   # 주체·기간 누락
    assert part["F001"]["support"] == "partial" and part["F001"]["missing"] == ["entity", "period"]
    noval = vf.suggest_support(facts, {"E001": _e(verbatim="삼성전자 2024년 매출 12조원")}, {"E001"})
    assert noval["F001"]["support"] == "partial" and noval["F001"]["missing"] == ["value"]   # value.raw 없음 → partial
    assert vf.suggest_support(facts, {"E001": _e(verbatim="매출 300.9조원")}, set()) == {}    # 대조 미통과 → 제안 없음
    boundary = vf.suggest_support({"F001": _f(value={"raw": "3조원", "unit": "KRW"})},
                                  {"E001": _e(verbatim="삼성전자 2024년 매출 13조원")}, {"E001"})
    assert boundary["F001"]["missing"] == ["value"]                                          # "3조원" ⊄ "13조원"
    # claim-review 가 partial 로 판정한 문장만 FAIL, 판정이 다르거나 없으면 WARN
    review = [{"sentence_text": SENT.strip(), "support": "partial", "claim_type": "observed", "fact_ids": ["F001"]}]
    fail, _ = vf.check_support_marks(SENT, part, True, review)
    assert fail and "[부분근거미표기] F001" in fail[0]
    fail, warn = vf.check_support_marks(SENT, part, True, [])
    assert not fail and "[부분근거불일치] F001" in warn[0]
    ok = SENT.replace("이다", "이다 (일부 근거)")
    assert vf.check_support_marks(ok, part, True, review) == ([], [])
    assert vf.check_support_marks(SENT, part, False, review)[0] == []


def test_h2_verify_writes_support_auto_but_check_only_does_not(work):
    vf.verify(work.report_md, work, check_only=True)
    assert not (work.audit / "support-auto.jsonl").exists()
    vf.verify(work.report_md, work)
    assert (work.audit / "support-auto.jsonl").exists()


# --- H3 ----------------------------------------------------------------------
def test_h3_render_writes_via_temp_and_keeps_old_pdf_on_failure(tmp_path, monkeypatch):
    md, pdf = tmp_path / "report.md", tmp_path / "report.pdf"
    md.write_text("# t\n", encoding="utf-8")
    pdf.write_bytes(b"OLD")
    monkeypatch.setattr(render_pdf, "_pandoc_html", lambda *a, **k: None)

    def boom(html, out, **k):
        out.write_bytes(b"PARTIAL")
        raise RuntimeError("chrome 실패")
    monkeypatch.setattr(render_pdf, "_chrome_pdf", boom)
    with pytest.raises(RuntimeError):
        render_pdf.render(md, pdf)
    assert pdf.read_bytes() == b"OLD" and not list(tmp_path.glob(".*.tmp"))
    monkeypatch.setattr(render_pdf, "_chrome_pdf", lambda html, out, **k: out.write_bytes(b"NEW"))
    assert render_pdf.render(md, pdf)["ok"] and pdf.read_bytes() == b"NEW"


def test_h3_verify_fail_stops_build_and_keeps_report_pdf(work, monkeypatch):
    start_chain(work)
    assert cli("verify_facts.py", work.report_md, work.root).returncode == 0
    pdf = work.root / "report.pdf"
    pdf.write_bytes(b"OLD-PDF")
    called = []
    monkeypatch.setattr(render_pdf, "render", lambda *a, **k: called.append(1))
    # 영수증이 유효해도(대장 변조는 영수증이 따로 막는다) 렌더 직전 재검증이 FAIL 이면 PDF 를 쓰지 않는다
    monkeypatch.setattr(vf, "verify", lambda *a, **k: {"ok": False, "failures": ["[문장인용없음] F001"], "warnings": []})
    with pytest.raises(gates.GateError, match="PDF 미생성"):
        render_pdf.render_and_record(work)
    assert not called and pdf.read_bytes() == b"OLD-PDF"


# --- H4·H5·H7·H8·H10 ---------------------------------------------------------
def _enrich(work, **ev_changes):
    rows = _read_jsonl(work.evidence)
    rows[0].update(ev_changes)
    _write_jsonl_atomic(work.evidence, rows)


def test_h4_evidence_html_internal_and_customer(work):
    _enrich(work, source_tier="공식통계", raw_quality="ocr")
    (work.audit / "search-log.jsonl").write_text(
        json.dumps({"ts": "2026-10-26T10:00:00", "query": "고체전지 <b>x</b>", "n_returned": 3}) + "\n", encoding="utf-8")
    page = bev.build(work.report_md, work).read_text(encoding="utf-8")
    assert "Certification and deployment." in page and "원문 대조 통과" in page
    assert "출처유형: 공식통계" in page and "원문품질: ocr" in page            # H10·H7 표지
    assert "앞뒤 맥락" in page and "_clean.txt" in page and 'src="data:image/png;base64,' in page
    assert "검색 기록" in page and "&lt;b&gt;x&lt;/b&gt;" in page               # H5, 이스케이프
    cust = bev.build(work.report_md, work, customer=True)
    text = cust.read_text(encoding="utf-8")
    assert cust.name == "evidence-customer.html"
    assert "Certification and deployment." in text and "data:image/png;base64," in text
    assert "앞뒤 맥락" not in text and "_clean.txt" not in text and "검색 기록" not in text


def test_h4_url_file_count_mismatch_drops_links(work):
    facts = _read_jsonl(work.facts)
    facts[0]["evidence_ids"].append("E002")
    _write_jsonl_atomic(work.facts, facts)
    rows = _read_jsonl(work.evidence)
    rows.append({**rows[0], "id": "E002", "source_url": "https://example.test/other"})   # URL 2개 ↔ 원문 파일 1개
    _write_jsonl_atomic(work.evidence, rows)
    page = bev.build(work.report_md, work).read_text(encoding="utf-8")
    assert "링크 미부착" in page and "_clean.txt" not in page and "<a href=" not in page


def test_h8_time_locator_link(tmp_path):
    wp = WorkPaths(resolve_work_dir("영상", base=tmp_path))
    _write_jsonl_atomic(wp.facts, [_f()])
    _write_jsonl_atomic(wp.evidence, [_e(source_url="https://youtu.be/abc", span={"clean": "a" * 12, "t": "1:30"},
                                         sha256="b" * 64, accessed_at="2026-10-26")])
    passed = set()
    assert vf.check_spans({"F001": _f()}, {"E001": _e(span={"clean": "a" * 12, "t": "1:30"})}, wp, passed) == ([], [])
    assert passed == {"E001"}
    wp.report_md.write_text(SENT, encoding="utf-8")
    assert "t=90" in bev.build(wp.report_md, wp).read_text(encoding="utf-8")


# --- H6 ----------------------------------------------------------------------
def test_h6_pdf_body_floor():
    assert fetch.validate_pdf_text(None)["verdict"] == "ok"                      # 텍스트를 못 얻으면 기존 동작
    assert fetch.validate_pdf_text("a " * 1000)["verdict"] == "partial"          # 영문 2,000자 < 3,000
    assert fetch.validate_pdf_text("a" * 3000)["verdict"] == "ok"
    assert fetch.validate_pdf_text("가" * 1400)["verdict"] == "partial"          # 한글 1,500 미만
    assert fetch.validate_pdf_text("가" * 1500)["verdict"] == "ok"
    assert fetch.pdf_text(b"%PDF-1.4 not really") is None
    assert fetch.validate_body("<html><body>" + "짧음 " * 50 + "</body></html>", 200)["verdict"] != "ok"  # HTML 1,000자 미만


# --- H9 ----------------------------------------------------------------------
def test_h9_axis_without_passed_fact_warns(tmp_path):
    wp = WorkPaths(resolve_work_dir("축", base=tmp_path))
    (wp.audit / "research-plan.md").write_text("# 부 3. 본론\n## 축: 기술요소\n## 축: 시장\n", encoding="utf-8")
    facts = {"F001": _f(context={"axis": "기술요소"}), "F002": _f("F002", context={"axis": "시장"}, evidence_ids=["E002"])}
    warn = vf.check_axis_evidence(wp, facts, {"E001"})
    assert len(warn) == 1 and "[축근거부족] 시장" in warn[0]
    assert vf.check_axis_evidence(wp, facts, {"E001", "E002"}) == []
    plain = {"F001": _f()}                                                       # 축 필드를 안 쓰면 생략
    assert vf.check_axis_evidence(wp, plain, set()) == []


# --- 리뷰 반영: span 우회·PDF clean·렌더 방어·증빙판 보강 ------------------------
@pytest.mark.parametrize("span", [{}, {"clean": "a" * 12}, {"clean": "a" * 12, "t": "abc"}])
def test_review_span_without_line_needs_valid_t(tmp_path, span):
    wp = WorkPaths(resolve_work_dir("span", base=tmp_path))
    passed = set()
    fail, _ = vf.check_spans({"F001": _f()}, {"E001": _e(span=span)}, wp, passed)
    assert fail and "[span형식]" in fail[0] and not passed


def test_review_missing_clean_is_warn_present_is_fail(work):
    rows = _read_jsonl(work.evidence)
    rows[0]["verbatim"] = "Certification and deployment happened. Energy unknown."
    _write_jsonl_atomic(work.evidence, rows)
    assert any("[문장인용없음]" in x for x in vf.verify(work.report_md, work)["failures"])   # clean 있음 → FAIL
    for p in (work.root / "_sources").glob("*_clean.txt"):
        p.rename(p.with_suffix(".gone"))
    rep = vf.verify(work.report_md, work)                                                    # clean 없음 → WARN
    assert not any("[문장인용없음]" in x for x in rep["failures"])
    assert any("[문장인용없음]" in x for x in rep["warnings"])


def test_review_pdf_save_writes_clean_and_stops_early(tmp_path, monkeypatch):
    import fitz
    doc = fitz.open()
    for i in range(5):
        doc.new_page().insert_text((50, 80), f"PAGE{i} " + "word " * 40)
    raw = doc.tobytes()
    assert "PAGE4" in fetch.pdf_text(raw) and "PAGE4" not in fetch.pdf_text(raw, stop_at=20)   # 상한 도달 시 추출 중단
    meta = fetch.save({"status": "ok", "is_pdf": True, "raw": raw, "text": ""}, tmp_path, url="https://e.test/a.pdf")
    assert meta["clean"] and (tmp_path / meta["clean"]).read_text(encoding="utf-8").count("PAGE") == 5


def test_review_render_cleans_stale_tmp_and_converts_verify_exceptions(work, tmp_path, monkeypatch):
    md, pdf = tmp_path / "r.md", tmp_path / "r.pdf"
    md.write_text("# t\n", encoding="utf-8")
    (tmp_path / ".r.pdf.tmp").write_bytes(b"STALE")
    monkeypatch.setattr(render_pdf, "_pandoc_html", lambda *a, **k: None)
    monkeypatch.setattr(render_pdf, "_chrome_pdf", lambda html, out, **k: out.write_bytes(b"NEW"))
    render_pdf.render(md, pdf)
    assert pdf.read_bytes() == b"NEW" and not (tmp_path / ".r.pdf.tmp").exists()
    start_chain(work)
    assert cli("verify_facts.py", work.report_md, work.root).returncode == 0
    monkeypatch.setattr(vf, "verify", lambda *a, **k: (_ for _ in ()).throw(KeyError("boom")))
    with pytest.raises(gates.GateError, match="재검증 예외"):
        render_pdf.render_and_record(work)


def test_review_customer_html_is_clean_and_embeds_thumbnail(work):
    facts = _read_jsonl(work.facts)
    facts[0]["evidence_ids"].append("E002")
    _write_jsonl_atomic(work.facts, facts)
    rows = _read_jsonl(work.evidence)
    rows.append({**rows[0], "id": "E002", "source_url": "https://example.test/other", "verbatim": "엉뚱한 인용"})
    _write_jsonl_atomic(work.evidence, rows)
    text = bev.build(work.report_md, work, customer=True).read_text(encoding="utf-8")
    assert "대조 미확인" not in text and "링크 미부착" not in text and "엉뚱한 인용" not in text   # 대표 1건만, 메모 없음
    assert 'src="data:image/png;base64,' in text and "../_captures" not in text               # 단일 파일


def test_review_html_tolerates_bad_span(work):
    for span in ("문자열", {"clean": "x", "t": "zz"}, {"clean": "x", "line": "a"}):
        _enrich(work, span=span, source_url="https://youtu.be/abc")
        page = bev.build(work.report_md, work).read_text(encoding="utf-8")
        assert "증빙판" in page


def test_review_axis_uses_given_plan(tmp_path):
    wp = WorkPaths(resolve_work_dir("plan", base=tmp_path))
    other = tmp_path / "other-plan.md"
    other.write_text("# 부 3. 본론\n## 축: 정책\n", encoding="utf-8")
    facts = {"F001": _f(context={"axis": "기술요소"})}
    warn = vf.check_axis_evidence(wp, facts, {"E001"}, plan=other)
    assert len(warn) == 1 and "[축근거부족] 정책" in warn[0]
