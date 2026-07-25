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
