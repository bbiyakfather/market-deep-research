"""test_adversarial.py — 적대적 fixture 전건 실패 검출 (plan-v2 검증 완료기준).

게이트/검증기가 조작·오류를 '정확히 실패로' 잡는지 확인한다. 각 케이스는 통과가 아니라
'검출(실패 판정)'이 성공이다. chk-scope: 빈결과·삼킨 예외를 성공으로 신뢰하지 않는다.
"""
import hashlib
import ipaddress
import json
import socket
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fitz                                                 # noqa: E402
from skill_paths import REFERENCES, resolve_work_dir, WorkPaths   # noqa: E402
from facts_db import (FactsDB, ValidationError, _write_jsonl_atomic,      # noqa: E402
                       check_capture_path, load_schema, validate_fact)
import capture_pdf                                          # noqa: E402
import fetch                                               # noqa: E402
import manifest                                            # noqa: E402
import render_pdf                                            # noqa: E402
import search                                                # noqa: E402
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


class _FakeResp:
    """curl_cffi Response 최소 흉내 — fetch._fetch_once/search._get 가 쓰는 속성만."""
    def __init__(self, status_code=200, headers=None, body=b"", primary_ip=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.primary_ip = primary_ip

    @property
    def text(self):
        return self._body.decode("utf-8", errors="replace")

    def iter_content(self, chunk_size=65536):
        yield self._body

    def close(self):
        pass


class _FakeCreq:
    """스크립트한 응답을 순서대로(소진되면 마지막 것 반복) 반환하는 오프라인 creq 대체."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(url)
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


def _fake_getaddrinfo(public_ip="93.184.216.34"):
    """상징적 호스트명은 공인 IP 로 위장(오프라인). 리터럴 IP 는 실제 해석에 맡긴다(로컬 판정이라
    네트워크 불필요) — 그래야 사설IP 리다이렉트 차단 서브케이스를 같은 스푸핑으로 무력화하지 않는다."""
    real = socket.getaddrinfo

    def _fn(host, *a, **kw):
        try:
            ipaddress.ip_address(host)
            return real(host, *a, **kw)
        except ValueError:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (public_ip, 0))]
    return _fn


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
                             "source_url": "https://x", "sha256": _H})
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
                         "source_url": "https://dart", "sha256": _H})
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
                         "source_url": "https://dart", "sha256": _H})   # capture 없음
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


# --- G5 재작성 회귀(V04) -------------------------------------------------------
@case
def failed_capture_claimed_as_evidence():
    """capture_pdf 가 대상 숫자를 못 찾아 .FAILED 사이드카만 남겼는데, 대장에는 마치 성공한
    것처럼 원본 out_png 경로(_captures/E001.png)를 evidence.capture 로 기입한 적대적 시나리오.
    V04(capture_pdf.py 의 성공/실패 저장 경로 분리) 가 없으면 out_png 에 실패 렌더가 그대로
    저장돼 파일이 '존재'하므로 게이트가 PASS 로 뚫린다 — 그 구멍을 겨냥한다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)

        # 실제로 실패 캡처를 만들어 .FAILED 산출물만 디스크에 존재하게 한다(대상 숫자가 PDF에 없음)
        pdf = Path(td) / "s.pdf"
        doc = fitz.open(); doc.new_page().insert_text((72, 100), "no relevant number here")
        doc.save(str(pdf)); doc.close()
        cap = capture_pdf.capture_number(pdf, "300.9", wp.captures / "E001.png")
        assert not cap["ok"] and ".FAILED" in cap["path"], cap
        assert not (wp.captures / "E001.png").exists(), "out_png 가 생성되면 안 됨(V04)"

        # 대장에는 실패 산출물이 아니라 성공 경로(E001.png)를 증거로 기입(조작)
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart", "sha256": _H,
                         "capture": "_captures/E001.png", "source_role": "원출처"})
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")

        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![](_captures/E001.png)\n",
                                      encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("증빙유실" in f for f in rep["failures"]), rep


# --- G7 재작성 회귀(V17·V18·V19·V26) -------------------------------------------
@case
def http_error_body_not_trusted():
    """V17: 404 본문이 길어도 신뢰하지 않음(긍정형 짝: 같은 본문도 200이면 ok)."""
    body_2000 = ("가나다 " * 400).encode("utf-8")
    resp = _FakeResp(404, {"content-type": "text/html"}, body_2000)
    orig_creq, orig_gai = fetch.creq, socket.getaddrinfo
    fetch.creq, socket.getaddrinfo = _FakeCreq([resp]), _fake_getaddrinfo()
    try:
        r = fetch._fetch_once("https://origin.example/x", "chrome")
        v = fetch.validate_body(r["text"], r["status"])
        assert v["verdict"] != "ok", v
        v2 = fetch.validate_body(r["text"], 200)          # 긍정형 짝
        assert v2["verdict"] == "ok", v2
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai


@case
def fake_pdf_not_trusted():
    """V18a: .pdf URL + application/pdf 헤더인데 매직바이트가 HTML(챌린지) → is_pdf False + 검증 태움.
    긍정형 짝: 진짜 %PDF- 바이트는 is_pdf True."""
    orig_creq, orig_gai = fetch.creq, socket.getaddrinfo
    fetch.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(200, {"content-type": "application/pdf"}, b"<html>Just a moment... cf-challenge</html>")]
    ), _fake_getaddrinfo()
    try:
        r = fetch._fetch_once("https://origin.example/x.pdf", "chrome")
        assert not r["is_pdf"], r
        assert fetch.validate_body(r["text"], r["status"])["verdict"] == "challenge", r
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai
    fetch.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(200, {"content-type": "application/pdf"}, b"%PDF-1.4\n...")]
    ), _fake_getaddrinfo()
    try:
        r2 = fetch._fetch_once("https://origin.example/x.pdf", "chrome")
        assert r2["ok"] and r2["is_pdf"], r2
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai


@case
def disallowed_mime_rejected():
    """V18b: 허용목록 밖 MIME 거부. 긍정형 짝: octet-stream 인데 진짜 PDF 는 통과(회귀 방지)."""
    orig_creq, orig_gai = fetch.creq, socket.getaddrinfo
    fetch.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(200, {"content-type": "video/mp4"}, b"binary junk not pdf")]
    ), _fake_getaddrinfo()
    try:
        r = fetch._fetch_once("https://origin.example/v", "chrome")
        assert not r["ok"] and r["reason"].startswith("mime:"), r
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai
    fetch.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(200, {"content-type": "application/octet-stream"}, b"%PDF-1.4\n...")]
    ), _fake_getaddrinfo()
    try:
        r2 = fetch._fetch_once("https://origin.example/report", "chrome")
        assert r2["ok"] and r2["is_pdf"], r2
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai


@case
def euckr_decoded_without_replacement():
    """charset 선언(euc-kr)을 무시하고 utf-8 로 디코드하면 U+FFFD 로 깨지던 것 수정 확인."""
    korean = "삼성전자 반도체 매출 전망 시장조사 " * 160
    assert len(korean) >= 3000
    body = korean.encode("euc-kr")
    orig_creq, orig_gai = fetch.creq, socket.getaddrinfo
    fetch.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(200, {"content-type": "text/html; charset=euc-kr"}, body)]
    ), _fake_getaddrinfo()
    try:
        r = fetch._fetch_once("https://origin.example/kr", "chrome")
        assert r["ok"] and r["text"].count("�") == 0 and korean in r["text"], r["text"][:50]
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai


@case
def redirect_join_and_hop_ssrf():
    """V19: urljoin 기준 5개 형태(프로토콜상대·상대경로·포트보존·쿼리전용·httpX 오판정) 전부 일치.
    (b) 리다이렉트가 사설IP 로 향하면 다음 홉의 check_url_safe 사전검증이 여전히 잡는지(회귀 없음)."""
    cases = [
        ("https://origin.example/start", "//cdn.example.net/a", "https://cdn.example.net/a"),
        ("https://origin.example/dir/start.html", "page2.html", "https://origin.example/dir/page2.html"),
        ("https://origin.example:8443/dir/start", "/newpath", "https://origin.example:8443/newpath"),
        ("https://origin.example/x", "?q=1", "https://origin.example/x?q=1"),
        ("https://origin.example/x", "httpsomething.html", "https://origin.example/httpsomething.html"),
    ]
    orig_creq, orig_gai = fetch.creq, socket.getaddrinfo
    for base, loc, expect in cases:
        fake = _FakeCreq([_FakeResp(302, {"location": loc}),
                          _FakeResp(200, {"content-type": "text/html"}, b"<html>" + b"ok body " * 30 + b"</html>")])
        fetch.creq, socket.getaddrinfo = fake, _fake_getaddrinfo()
        try:
            fetch._fetch_once(base, "chrome")
        finally:
            fetch.creq, socket.getaddrinfo = orig_creq, orig_gai
        assert fake.calls[1] == expect, (base, loc, fake.calls)

    fetch.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(302, {"location": "http://127.0.0.1/x"})]
    ), _fake_getaddrinfo()
    try:
        try:
            fetch._fetch_once("https://origin.example/start", "chrome")
            assert False, "사설IP 리다이렉트가 차단되지 않음"
        except fetch.SsrfBlocked:
            pass
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai


@case
def dns_rebinding_post_connect():
    """V26: DNS 사전검증은 공인 IP 로 통과하지만 실접속 primary_ip 가 사설이면 차단(TOCTOU).
    fetch·search 양쪽 다 확인. 긍정형 짝: primary_ip 가 공인이면 정상 통과."""
    orig_creq, orig_gai = fetch.creq, socket.getaddrinfo
    fetch.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(200, {"content-type": "text/html"}, b"body", primary_ip="127.0.0.1")]
    ), _fake_getaddrinfo()
    try:
        try:
            fetch._fetch_once("https://origin.example/x", "chrome")
            assert False, "fetch TOCTOU 차단 안 됨"
        except fetch.SsrfBlocked:
            pass
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai

    fetch.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(200, {"content-type": "text/html"}, b"<html>" + b"ok " * 400 + b"</html>", primary_ip="93.184.216.34")]
    ), _fake_getaddrinfo()
    try:
        r = fetch._fetch_once("https://origin.example/x", "chrome")
        assert r["ok"], r                              # 긍정형 짝
    finally:
        fetch.creq, socket.getaddrinfo = orig_creq, orig_gai

    orig_screq, orig_gai2 = search.creq, socket.getaddrinfo
    search.creq, socket.getaddrinfo = _FakeCreq(
        [_FakeResp(200, {}, b"{}", primary_ip="127.0.0.1")]
    ), _fake_getaddrinfo()
    try:
        try:
            search._get("https://origin.example/x")
            assert False, "search._get TOCTOU 차단 안 됨"
        except fetch.SsrfBlocked:
            pass
    finally:
        search.creq, socket.getaddrinfo = orig_screq, orig_gai2


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
def ghost_figure_path():
    """V09-9: 이미지 문법은 있으나 참조 경로가 실재하지 않으면(유령 도판) [도판경로] 로 검출."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        md = "매출 300.9조원(F001).\n\n![c](_captures/DOES_NOT_EXIST.png)\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("도판경로" in f for f in rep["failures"]), rep


# --- G6a 재작성 회귀(pandoc 리소스 경고 승격 · manifest assets 추적) -----------
@case
def render_missing_resource():
    """pandoc 이 리소스(이미지)를 못 찾으면 --fail-if-warnings 로 rc≠0 → RuntimeError.
    증빙 이미지가 통째로 빠진 PDF 가 조용히 ok=True 로 반환되던 사각지대를 막는다.
    긍정형 짝: 실재하는 리소스만 참조하는 정상 markdown 은 여전히 ok."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("렌더누락", base=td)
        wp = WorkPaths(wd)
        bad = wp.root / "bad.md"
        bad.write_text("# t\n\n![유령](_captures/GHOST.png)\n", encoding="utf-8")
        try:
            render_pdf.render(bad, wp.root / "bad.pdf", resource_dir=wp.root)
            raise AssertionError("리소스 누락인데 render 가 성공함")
        except RuntimeError as e:
            assert "pandoc" in str(e), e

        good = wp.root / "good.md"
        good.write_text("# t\n\n정상 서술 300.9조원(F001).\n", encoding="utf-8")
        r = render_pdf.render(good, wp.root / "good.pdf", resource_dir=wp.root)
        assert r["ok"] and Path(r["pdf"]).stat().st_size > 1000, r          # 긍정형 짝


@case
def manifest_asset_swap():
    """생성 차트(assets/**)가 report.pdf 에 --embed-resources 로 내장되는데 TRACKED 밖이면
    변조를 못 잡던 사각지대. 긍정형 짝: 변조 안 하면 여전히 ok."""
    assert any(pattern.startswith("assets/") for _, pattern in manifest.TRACKED)
    assert not any(pattern.startswith("audit") for _, pattern in manifest.TRACKED)
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("차트변조", base=td)
        wp = WorkPaths(wd)
        (wp.gen_assets / "chart.png").write_bytes(b"\x89PNG-orig")
        manifest.build(wp)
        assert manifest.verify(wp)["ok"]                                    # 긍정형 짝(변조 전)
        (wp.gen_assets / "chart.png").write_bytes(b"\x89PNG-tampered")      # 차트 변조
        v = manifest.verify(wp)
        assert not v["ok"] and "assets/chart.png" in v["changed"], v


# --- G4 재작성 회귀(대장 무검증 신뢰 제거 + 증빙 경로 봉쇄) --------------------
@case
def unvalidated_ledger_row():
    """verify() 가 db.facts() 를 dict 화만 하고 재검증을 안 하면, 대장 파일에 직접 append 된
    미검증 confirmed 행(evidence_ids=[] 인데 confirmed)이 조용히 통과한다. check_ledger_integrity
    가 전 행을 validate_fact 로 재검증해야 [대장무결성] 으로 잡는다."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("미검증행", base=td)
        wp = WorkPaths(wd)
        rows = [{"kind": "fact", "claim_key": "x|y|z|2024|_|_", "id": "F001",
                 "claim": "위조 사실",
                 "context": {"metric": "x", "entity": "y", "geography": "z", "period": "2024"},
                 "value": {"raw": "1", "unit": "x"},
                 "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"},
                 "risk": "normal", "status": "confirmed", "evidence_ids": [], "verify_events": []}]
        _write_jsonl_atomic(wp.facts, rows)
        (wp.root / "r.md").write_text("본문에 태그 없음.\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("대장무결성" in f for f in rep["failures"]), rep

        # 긍정형 짝: 정상 add_fact/add_evidence 경로로 등재된 행은 [대장무결성] 없이 통과
        wd2, db2 = _base_db(td)
        wp2 = WorkPaths(wd2)
        _confirm(db2, wp2, "F001")
        (wp2.root / "ok.md").write_text(
            "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        rep2 = verify_facts.verify(wp2.root / "ok.md", wd2)
        assert not any("대장무결성" in f for f in rep2["failures"]), rep2


@case
def duplicate_fact_id():
    """같은 F-ID 로 중복 행을 심으면 dict화 시 마지막 행이 조용히 채택돼 값대조를 무력화한다
    (진짜 F001=300.9 옆에 조작 F001=999 를 추가하면 본문 '999(F001)' 이 값불일치 없이 통과).
    [중복ID] 로 잡아야 한다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)          # 진짜 F001 raw=300.9 unit=KRW_T
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        (wp.root / "ok.md").write_text(
            "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        rep_before = verify_facts.verify(wp.root / "ok.md", wd)
        assert not any("중복ID" in f for f in rep_before["failures"]), rep_before   # 긍정형 짝

        rows = db.facts()
        forged = dict(rows[0]); forged["value"] = {"raw": "999", "unit": "KRW_T"}
        rows.append(forged)             # 같은 id="F001" 중복 행(조작값)
        _write_jsonl_atomic(wp.facts, rows)
        (wp.root / "bad.md").write_text(
            "매출은 999조원(F001).\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "bad.md", wd)
        assert not rep["ok"] and any("중복ID" in f for f in rep["failures"]), rep


@case
def fake_evidence_hash():
    """sha256 형식이 64자리 16진수가 아니거나, local 스냅샷이 실재해도 재계산한 해시가
    선언값과 다르면 [해시형식]/[해시불일치] 로 잡아야 한다(형식/필드 존재만 보던 구멍).
    긍정형 짝: local 실재 + 해시 일치하면 통과."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart", "sha256": "not-a-real-hash"})
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")
        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![c](x.png)\n", encoding="utf-8")
        (wp.root / "x.png").write_bytes(b"\x89PNG")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("해시형식" in f for f in rep["failures"]), rep

    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        snap = wp.sources / "snap.txt"
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text("실제 내용", encoding="utf-8")
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart", "sha256": _H,   # 실제 파일 해시와 다름
                         "local": "_sources/snap.txt"})
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")
        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![c](x.png)\n", encoding="utf-8")
        (wp.root / "x.png").write_bytes(b"\x89PNG")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("해시불일치" in f for f in rep["failures"]), rep

    with tempfile.TemporaryDirectory() as td:                          # 긍정형 짝
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        snap = wp.sources / "snap.txt"
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text("정확한 내용", encoding="utf-8")
        real_hash = manifest.sha256_file(snap)
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart", "sha256": real_hash,
                         "local": "_sources/snap.txt"})
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")
        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![c](x.png)\n", encoding="utf-8")
        (wp.root / "x.png").write_bytes(b"\x89PNG")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not any(("해시형식" in f or "해시불일치" in f) for f in rep["failures"]), rep


@case
def capture_outside_workdir():
    """capture 가 작업폴더의 _captures/ 밖(../ 탈출)이거나 _reconstructed/ 재구성 발췌면
    증빙으로 인정하면 안 된다 — add_evidence 시점(정상 API)과, 대장을 직접 조작해 이미
    evidence.jsonl 에 박힌 경우(check_evidence_chain 시점) 둘 다 확인한다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        try:
            db.add_evidence({"fact_id": "F001", "type": "table_cell",
                             "source_url": "https://x", "sha256": _H,
                             "capture": "../../outside.png"})
            assert False, "작업폴더 밖 capture 가 add_evidence 를 통과함"
        except ValidationError:
            pass
        try:
            db.add_evidence({"fact_id": "F001", "type": "table_cell",
                             "source_url": "https://x", "sha256": _H,
                             "capture": "_reconstructed/x.png"})
            assert False, "_reconstructed/ capture 가 add_evidence 를 통과함"
        except ValidationError:
            pass

    with tempfile.TemporaryDirectory() as td:      # 대장 직접조작(정상 API 우회) 시나리오
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        db.add_verify_event("F001", "lead", "reread")
        ev_rows = [{"id": "E001", "fact_id": "F001", "type": "table_cell",
                    "source_url": "https://x", "sha256": _H, "accessed_at": "2026-01-01",
                    "capture": "../../outside.png"}]
        _write_jsonl_atomic(wp.evidence, ev_rows)
        facts = db.facts(); facts[0]["evidence_ids"] = ["E001"]
        _write_jsonl_atomic(wp.facts, facts)
        db.set_status("F001", "confirmed")
        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![c](x.png)\n", encoding="utf-8")
        (wp.root / "x.png").write_bytes(b"\x89PNG")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("증빙경계" in f for f in rep["failures"]), rep

    with tempfile.TemporaryDirectory() as td:      # 긍정형 짝: 정상 _captures/ 하위 상대경로
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        (wp.root / "ok.md").write_text(
            "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        rep2 = verify_facts.verify(wp.root / "ok.md", wd)
        assert not any("증빙경계" in f for f in rep2["failures"]), rep2


@case
def status_regrade_blocked():
    """반박이 기록되거나 폐기 사유가 남은 채, 또는 강등 이후 새 lead 재검증 없이 confirmed
    재승급이 되면 안 된다 — 파이프라인이 실제로 이 경로를 압박한다(disputed 인용은 [미확정]
    FAIL, 태그를 빼면 [무태그] FAIL 이라 재승급이 유일한 탈출구가 됨). 새 lead 재검증 추가
    후엔 성공(긍정형 짝)."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        db.set_status("F001", "disputed")
        facts = db.facts()
        facts[0]["counter_search"] = {"query": "정정", "result": "발견",
                                      "found_stronger_refutation": True}
        _write_jsonl_atomic(wp.facts, facts)
        try:
            db.set_status("F001", "confirmed")
            assert False, "반박 기록된 채 재승급이 통과됨"
        except ValidationError:
            pass

        facts = db.facts()
        facts[0]["counter_search"]["found_stronger_refutation"] = False
        _write_jsonl_atomic(wp.facts, facts)
        time.sleep(1.1)     # demoted_at 과 같은 초 충돌 방지(_now() 는 초 단위)
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")            # 긍정형 짝: 새 검증 있으면 재승급 성공
        assert db.facts()[0]["status"] == "confirmed"

        # 폐기 사유가 남은 채로 억지로 confirmed 로 되돌린 원시 행은 validate_fact 자체가 거부
        facts = db.facts()
        facts[0]["status"], facts[0]["discard_reason"] = "confirmed", "무출처(테스트)"
        try:
            validate_fact(facts[0], load_schema())
            assert False, "폐기 사유 남은 채 confirmed 검증이 통과됨"
        except ValidationError:
            pass


@case
def orphan_evidence_rejected():
    """add_evidence 가 존재하지 않는 fact_id 에 조용히 성공하던 구멍(G1 에서 이관) — evidence
    기록 전에 fact 존재를 선검사해 거부. 긍정형 짝: 존재하는 fact_id 는 정상 등재."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        try:
            db.add_evidence({"fact_id": "F999", "type": "table_cell",
                             "source_url": "https://x", "sha256": _H})
            assert False, "orphan evidence 가 통과됨"
        except ValidationError:
            pass
        assert db.evidence() == [], "orphan evidence 가 파일에 남으면 안 됨"

        ev = db.add_evidence({"fact_id": "F001", "type": "table_cell",
                              "source_url": "https://x", "sha256": _H})   # 긍정형 짝
        assert ev["fact_id"] == "F001" and len(db.evidence()) == 1


# --- G6b 재작성 회귀(봉인 순서 정합) -------------------------------------------
@case
def pdf_tamper_detected():
    """재봉인 후 report.pdf 를 1바이트 변조하면 ok=False 이고 changed 에 report.pdf 포함.
    (수정 전에는 report.pdf 가 애초에 매니페스트에 없어 변조해도 절대 검출 안 됐다.)"""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("pdf변조", base=td)
        wp = WorkPaths(wd)
        wp.report_pdf.write_bytes(b"%PDF-1.4 original content")
        manifest.build(wp)                                    # 봉인(report.pdf 포함)
        assert manifest.verify(wp)["ok"]
        data = bytearray(wp.report_pdf.read_bytes())
        data[10] ^= 0xFF                                       # 1바이트 변조
        wp.report_pdf.write_bytes(bytes(data))
        v = manifest.verify(wp)
        assert not v["ok"] and "report.pdf" in v["changed"], v


@case
def unsealed_new_file_fails():
    """봉인 후 추적 대상 디렉터리(_captures/)에 임의 파일을 추가하면 ok=False.
    (수정 전에는 new 항목이 ok 판정에 안 들어가 조용히 통과했다 — render 로 생긴 report.pdf
    가 영구히 미봉인 상태로 남던 것과 같은 뿌리의 구멍.)"""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("미봉인신규", base=td)
        wp = WorkPaths(wd)
        (wp.sources / "a.txt").write_text("x", encoding="utf-8")
        manifest.build(wp)
        assert manifest.verify(wp)["ok"]
        (wp.captures / "sneaky.png").write_bytes(b"\x89PNG")   # 봉인 후 임의 파일 추가
        v = manifest.verify(wp)
        assert not v["ok"] and "_captures/sneaky.png" in v["new"], v


# --- G9 재작성 회귀(목차 기계검사) --------------------------------------------
def _toc_plan(wp: WorkPaths, plan_text: str) -> None:
    wp.audit.mkdir(parents=True, exist_ok=True)
    (wp.audit / "research-plan.md").write_text(plan_text, encoding="utf-8")


@case
def toc_part_missing():
    """승인 목차의 부가 본문에서 통째로 빠지면 [목차이탈] FAIL. 긍정형 짝: 부가 전부 있으면
    PASS([도판경로] 오염 방지를 위해 실제 캡처 이미지를 참조한다)."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        _toc_plan(wp, "# 부 0. 개요\n# 부 1. 검증 요약\n# 부 3. 테마별 본론\n## 축: 매출\n")

        bad = ("## 0. 개요\n매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n\n"
              "## 3. 테마별 본론\n### 매출\n서술.\n")          # '부 1. 검증 요약' 통째로 빠짐
        (wp.root / "bad.md").write_text(bad, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "bad.md", wd)
        assert not rep["ok"] and any("목차이탈" in f for f in rep["failures"]), rep

        good = ("## 0. 개요\n매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n\n"
               "## 1. 검증 요약\n검증 내용.\n\n## 3. 테마별 본론\n### 매출\n서술.\n")
        (wp.root / "good.md").write_text(good, encoding="utf-8")
        rep2 = verify_facts.verify(wp.root / "good.md", wd)
        assert not any("목차이탈" in f for f in rep2["failures"]), rep2


@case
def toc_empty_section():
    """헤딩은 있는데 다음 헤딩까지 본문이 비어 있으면 [빈챕터] FAIL. 긍정형 짝: 내용 있으면 PASS."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        _toc_plan(wp, "# 부 0. 개요\n# 부 3. 테마별 본론\n## 축: 매출\n")

        bad = ("## 0. 개요\n\n## 3. 테마별 본론\n### 매출\n매출은 300.9조원(F001).\n\n"
              "![c](_captures/F001.png)\n")                     # '0. 개요' 헤딩만 있고 본문 없음
        (wp.root / "bad.md").write_text(bad, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "bad.md", wd)
        assert not rep["ok"] and any("빈챕터" in f for f in rep["failures"]), rep

        good = ("## 0. 개요\n개요 서술.\n\n## 3. 테마별 본론\n### 매출\n"
               "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n")
        (wp.root / "good.md").write_text(good, encoding="utf-8")
        rep2 = verify_facts.verify(wp.root / "good.md", wd)
        assert not any("빈챕터" in f for f in rep2["failures"]), rep2

        # 조건부 부는 '해당 없음' 한 줄이면 충족(빈챕터로 안 잡힘)
        _toc_plan(wp, "# 부 3. 테마별 본론\n## 축: 매출\n# 부 5. 결론(해당 시)\n")
        cond = ("## 3. 테마별 본론\n### 매출\n매출은 300.9조원(F001).\n\n"
               "![c](_captures/F001.png)\n\n## 5. 결론\n해당 없음\n")
        (wp.root / "cond.md").write_text(cond, encoding="utf-8")
        rep3 = verify_facts.verify(wp.root / "cond.md", wd)
        assert not any("빈챕터" in f for f in rep3["failures"]), rep3


@case
def toc_axis_chapter_missing():
    """3부 승인 축 챕터가 본문에 없으면 [축누락] FAIL. 긍정형 짝: 축 챕터가 다 있으면 PASS."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        _toc_plan(wp, "# 부 3. 테마별 본론\n## 축: 매출\n## 축: 시장규모\n")

        bad = ("## 3. 테마별 본론\n### 매출\n매출은 300.9조원(F001).\n\n"
              "![c](_captures/F001.png)\n")                     # '시장규모' 축 챕터 없음
        (wp.root / "bad.md").write_text(bad, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "bad.md", wd)
        assert not rep["ok"] and any("축누락" in f for f in rep["failures"]), rep

        good = ("## 3. 테마별 본론\n### 매출\n매출은 300.9조원(F001).\n\n"
               "![c](_captures/F001.png)\n\n### 시장규모\n서술.\n")
        (wp.root / "good.md").write_text(good, encoding="utf-8")
        rep2 = verify_facts.verify(wp.root / "good.md", wd)
        assert not any("축누락" in f for f in rep2["failures"]), rep2


@case
def plan_format_contract():
    """research-plan.md 의 '승인 목차 예시' 블록을 그대로 읽어 파서에 먹인다 — G2 가 서식을
    바꾸는 순간 자동탐지가 게이트 강화가 아니라 전건 오탐 폭탄이 되므로, 실제 파일을 직접
    검증해 문서-파서 계약을 고정한다. 긍정형 짝: --plan 미지정(기본값)이면 목차 관련
    failure 가 0(계획 파일 없는 기존 조사와 호환)."""
    plan_path = REFERENCES / "research-plan.md"
    parts, axes = verify_facts.parse_plan_toc(plan_path.read_text(encoding="utf-8"))
    assert len(parts) >= 3, parts
    assert len(axes) >= 1, axes
    assert any(title == "부록" for _, title in parts), parts

    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        (wp.root / "r.md").write_text(
            "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)      # plan 미지정 → 자동탐지도 실패(없음)
        assert not any(x.startswith(("[목차이탈]", "[빈챕터]", "[축누락]"))
                      for x in rep["failures"]), rep


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
