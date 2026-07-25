"""test_adversarial.py — 적대적 fixture 전건 실패 검출 (plan-v2 검증 완료기준).

게이트/검증기가 조작·오류를 '정확히 실패로' 잡는지 확인한다. 각 케이스는 통과가 아니라
'검출(실패 판정)'이 성공이다. chk-scope: 빈결과·삼킨 예외를 성공으로 신뢰하지 않는다.
"""
import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from skill_paths import resolve_work_dir, WorkPaths        # noqa: E402
from facts_db import FactsDB, ValidationError              # noqa: E402
import fetch                                               # noqa: E402
import manifest                                            # noqa: E402
import verify_facts                                        # noqa: E402

CASES = []

# 유효한 64자리 sha256 fixture 상수 — 후속 케이스가 "h" 같은 placeholder 를 재도입하지 못하게.
_H = hashlib.sha256(b"fixture").hexdigest()


def case(fn):
    CASES.append(fn)
    return fn


def _base_db(td):
    wd = resolve_work_dir("적대", base=td)
    db = FactsDB(wd)
    db.add_fact({"claim": "매출 300.9조", "risk": "high", "status": "pending",
                 "context": {"metric": "revenue", "entity": "삼성", "geography": "KR", "period": "2024"},
                 "value": {"raw": "300.9", "unit": "KRW_T"},
                 "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
    return wd, db


@case
def ssrf_private_and_scheme():
    for bad in ["http://127.0.0.1/", "http://10.0.0.1/", "http://169.254.169.254/",
                "file:///etc/passwd", "ftp://x/"]:
        try:
            fetch.check_url_safe(bad); raise AssertionError(f"SSRF 미차단: {bad}")
        except fetch.SsrfBlocked:
            pass


@case
def html_injection_challenge():
    v = fetch.validate_body("Please enable JavaScript and cookies to continue", 200)
    assert v["verdict"] == "challenge", v


@case
def dup_fact_and_claimkey():
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        try:
            db.add_fact({"claim": "중복", "risk": "normal", "status": "pending",
                         "context": {"metric": "revenue", "entity": "삼성", "geography": "KR", "period": "2024"},
                         "value": {"raw": "301", "unit": "KRW_T"},
                         "grade": {"authority": "B", "independence": "B", "directness": "B", "recency": "B"}})
            raise AssertionError("동일 claim_key 미차단")
        except ValidationError:
            pass


@case
def no_source_confirm():
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        try:
            db.set_status("F001", "confirmed"); raise AssertionError("무출처 confirm 통과")
        except ValidationError:
            pass


@case
def text_quote_without_verbatim():
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        try:
            db.add_evidence({"fact_id": "F001", "type": "text_quote",
                             "source_url": "https://x", "sha256": "h"})
            raise AssertionError("verbatim 누락 통과")
        except ValidationError:
            pass


@case
def untagged_number_in_body():
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        (wp.root / "r.md").write_text("시장 규모는 45조원으로 성장.\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("무태그" in f for f in rep["failures"]), rep


@case
def mistagged_value():
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart", "sha256": "h"})
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")
        wp = WorkPaths(wd)
        (wp.root / "r.md").write_text("매출은 999조원(F001).\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("값불일치" in f for f in rep["failures"]), rep


@case
def appendix_bypass_blocked():
    """부록에만 태그를 몰아넣어 본문 무태그를 숨기려는 우회 → 여전히 본문에서 검출."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        md = "시장은 45조원 규모다.\n<!-- FACTSHEET:APPENDIX -->\n## 부록\n45조원(F001)\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("무태그" in f for f in rep["failures"]), rep


@case
def high_risk_without_capture():
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart", "sha256": "h"})   # capture 없음
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")
        wp = WorkPaths(wd)
        (wp.root / "r.md").write_text("매출 300.9조원(F001).\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("증빙" in f for f in rep["failures"]), rep


@case
def manifest_capture_swap():
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("스왑", base=td)
        wp = WorkPaths(wd)
        (wp.captures / "E001.png").write_bytes(b"\x89PNG-orig")
        manifest.build(wp)
        (wp.captures / "E001.png").write_bytes(b"\x89PNG-swapped")     # 캡처 교체
        v = manifest.verify(wp)
        assert not v["ok"] and v["changed"], v


# --- G3 재작성 회귀(V02·V13·V10·V09) ------------------------------------------
def _confirm(db, wp, fid, with_capture=True):
    """fact 를 confirmed 로 만든다(증거+팀리드 재열람). with_capture 면 실파일까지 결박해
    check_evidence_chain 의 [증빙] 실패가 값대조 assert 를 오염시키지 않게 한다."""
    ev = {"fact_id": fid, "type": "table_cell", "source_url": "https://x", "sha256": _H}
    if with_capture:
        cap = f"_captures/{fid}.png"
        (wp.captures).mkdir(parents=True, exist_ok=True)
        (wp.root / cap).write_bytes(b"\x89PNG")
        ev["capture"] = cap
    db.add_evidence(ev)
    db.add_verify_event(fid, "lead", "reread")
    db.set_status(fid, "confirmed")


@case
def segment_binding():
    """V02-1·V02-2: 세그먼트 안 1:1 최근접 결박 — 문장 내 두 번째(무태그) 수치가 첫 태그로
    면제되지 않고, 태그가 수치보다 앞에 와도(선행 태그) 값대조가 걸린다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)          # F001 raw=300.9 unit=KRW_T
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")

        (wp.root / "r1.md").write_text(
            "매출은 300.9조원(F001) 이며 2030년에는 999조원까지 성장한다.\n", encoding="utf-8")
        r1 = verify_facts.verify(wp.root / "r1.md", wd)
        assert not r1["ok"] and any("무태그" in f for f in r1["failures"]), r1
        assert not any("값불일치" in f for f in r1["failures"]), r1  # F001 자체는 값일치라 오염 없어야

        (wp.root / "r2.md").write_text("(F001) 매출은 999조원.\n", encoding="utf-8")
        r2 = verify_facts.verify(wp.root / "r2.md", wd)
        assert not r2["ok"] and any("값불일치" in f for f in r2["failures"]), r2


@case
def scale_unit_bypass():
    """V02-3·V02-4: 콤마 10배 오기·단위 축척 오기가 값대조를 통과하지 못하는지.
    긍정형 짝: 같은 대장에 정상 표기 '300.9조원(F001)' 은 ok=True 여야 한다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)          # F001 raw=300.9 unit=KRW_T
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")

        (wp.root / "ok.md").write_text(
            "매출은 300.9조원(F001).\n\n![증빙](_captures/F001.png)\n", encoding="utf-8")
        rok = verify_facts.verify(wp.root / "ok.md", wd)
        assert rok["ok"], rok

        (wp.root / "comma.md").write_text("매출은 3,009조원(F001).\n", encoding="utf-8")
        rc = verify_facts.verify(wp.root / "comma.md", wd)
        assert not rc["ok"] and any("값불일치" in f for f in rc["failures"]), rc

        (wp.root / "scale.md").write_text("매출은 300.9억원(F001).\n", encoding="utf-8")
        rs = verify_facts.verify(wp.root / "scale.md", wd)
        assert not rs["ok"] and any(("값불일치" in f or "단위불일치" in f) for f in rs["failures"]), rs


@case
def range_value_ok():
    """V02-5: 대장이 범위값(45~50%)일 때 동일 범위 표기는 통과, 범위가 어긋나면 실패."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("범위", base=td)
        db = FactsDB(wd)
        db.add_fact({"claim": "점유율 45~50%", "risk": "normal", "status": "pending",
                     "context": {"metric": "share", "entity": "글로벌", "geography": "GL", "period": "2030"},
                     "value": {"raw": "45~50", "unit": "%"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")

        (wp.root / "ok.md").write_text(
            "점유율은 45~50%(F001).\n\n![증빙](_captures/F001.png)\n", encoding="utf-8")
        rok = verify_facts.verify(wp.root / "ok.md", wd)
        assert rok["ok"], rok
        assert not any("값불일치" in f for f in rok["failures"]), rok

        (wp.root / "bad.md").write_text("점유율은 45~60%(F001).\n", encoding="utf-8")
        rbad = verify_facts.verify(wp.root / "bad.md", wd)
        assert not rbad["ok"] and any("값불일치" in f for f in rbad["failures"]), rbad


@case
def evidence_table_row_forgery():
    """V02-6: 근거표 행(사실(F001) | 위조수치 | …)이 표 셀 경계에 가려 전건 면제되지 않는지."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)          # F001 raw=300.9 unit=KRW_T
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        md = "| 사실 | 수치 |\n|---|---|\n| 매출(F001) | 999조원 |\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any(("무태그" in f or "값불일치" in f) for f in rep["failures"]), rep


@case
def numeral_and_energy_units_untagged():
    """V13-7: 한국식 수사 삽입형(1천억)·TWh 무태그 사실주장 검출. '12건'·'3개사' 같은 구조
    카운트(계수 단위)는 오탐하지 않아야 한다(긍정형 짝)."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        for text in ("투자액은 1천억원 규모다.\n", "발전량은 연 10 TWh.\n", "생산량은 10만톤이다.\n"):
            (wp.root / "x.md").write_text(text, encoding="utf-8")
            rep = verify_facts.verify(wp.root / "x.md", wd)
            assert not rep["ok"] and any("무태그" in f for f in rep["failures"]), (text, rep)

        (wp.root / "cnt.md").write_text("총 12건의 프로젝트를 3개사가 진행한다.\n", encoding="utf-8")
        rcnt = verify_facts.verify(wp.root / "cnt.md", wd)
        assert not any("무태그" in f for f in rcnt["failures"]), rcnt


@case
def appendix_forward_bypass():
    """V10-8: 본문 중간의 '## 부록' 소제목 하나로 뒤 진짜 본문이 부록 취급돼 빠지지 않는지
    (경계는 주석 최우선, 없으면 최후 헤딩). 긍정형 짝: 정식 주석 마커 뒤 부록은 여전히 면제."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        md = ("본론\n## 부록: 용어 정리\n시장은 999조원 규모다.\n"
              "<!-- FACTSHEET:APPENDIX -->\n## 부록\n999조원(F001)\n")
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("무태그" in f for f in rep["failures"]), rep

        _confirm(db, wp, "F001")
        good = ("본론 정상 서술.\n\n![증빙](_captures/F001.png)\n"
                "<!-- FACTSHEET:APPENDIX -->\n## 부록\n- 소스: 사내(F001)\n")
        (wp.root / "g.md").write_text(good, encoding="utf-8")
        rgood = verify_facts.verify(wp.root / "g.md", wd)
        assert rgood["ok"], rgood


@case
def missing_image_path():
    """V09-9: 이미지 문법은 있으나 참조 경로가 실재하지 않으면 [도판경로] 로 검출."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        md = "매출 300.9조원(F001).\n\n![c](_captures/DOES_NOT_EXIST.png)\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("도판경로" in f for f in rep["failures"]), rep


def main():
    import traceback
    ok = 0
    for fn in CASES:
        try:
            fn(); print(f"  [검출OK] {fn.__name__}"); ok += 1
        except Exception as e:                     # assert 외 예외로 스위트 전체가 죽지 않게
            print(f"  [실패!!] {fn.__name__}: {e}"); traceback.print_exc()
    print(f"\n적대적 fixture: {ok}/{len(CASES)} 검출 성공")
    sys.exit(0 if ok == len(CASES) else 1)


if __name__ == "__main__":
    main()
