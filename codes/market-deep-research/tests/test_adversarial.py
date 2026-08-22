"""test_adversarial.py — 적대적 fixture 전건 실패 검출 (plan-v2 검증 완료기준).

게이트/검증기가 조작·오류를 '정확히 실패로' 잡는지 확인한다. 각 케이스는 통과가 아니라
'검출(실패 판정)'이 성공이다. chk-scope: 빈결과·삼킨 예외를 성공으로 신뢰하지 않는다.
"""
import hashlib
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fitz                                                 # noqa: E402
from skill_paths import REFERENCES, SKILL_ROOT, resolve_work_dir, WorkPaths   # noqa: E402
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
_CLI_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def _run_script(*args):
    """scripts/<name> CLI 를 utf-8 로 실행(Windows cp949 콘솔 대비)."""
    return subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / args[0]), *args[1:]],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_CLI_ENV,
    )


def _ledger(wp):
    import gates
    path = gates.ledger_path(wp)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _chain_to_g3(td, topic="봉인"):
    """G0·G1·[2] API 영수증 + report.md + G3 기준선(build + extra 결박). verify_facts 소유자 흉내."""
    import gates
    wd = resolve_work_dir(topic, base=td)
    wp = WorkPaths(wd)
    (wp.audit / "research-plan.md").write_text("# plan\n", encoding="utf-8")
    wp.facts.write_text("", encoding="utf-8")
    wp.report_md.write_text("# r\n", encoding="utf-8")
    gates.record_manual(wp, "G0", "approved")
    gates.record_script_result(wp, "G1", 0, "join PASS")
    gates.record_manual(wp, "[2]", "lead reread")
    sealed = manifest.build(wp)
    gates.record_script_result(
        wp, "G3", 0, "verify PASS",
        extra={"manifest_sha256": manifest.sha256_file(wp.manifest),
               "manifest_entries": len(sealed["entries"])},
    )
    return wd, wp


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
        db.add_verify_event("F001", "lead", "reread", reread_sha256=_H)
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
def duplicate_appendix_marker_blocked():
    """본문 앞쪽에 APPENDIX 마커를 하나 더 심으면 첫 마커 기준 절단이라 그 뒤 본문 전체가
    부록 취급(무태그 검출 침묵) → 마커 중복 자체를 FAIL 로 차단."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        md = ("<!-- FACTSHEET:APPENDIX -->\n시장은 45조원 규모다.\n"
              "<!-- FACTSHEET:APPENDIX -->\n## 부록\n")
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("부록마커중복" in f for f in rep["failures"]), rep


@case
def empty_body_blocked():
    """마커가 1개뿐이어도 문서 최상단이면 body='' — 무태그 등 본문 검사 전체가 대상 없음으로
    침묵([도판]만 떠 원인 오도) → 본문 공백 자체를 FAIL 로 차단."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        md = "<!-- FACTSHEET:APPENDIX -->\n시장은 45조원 규모다.\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("본문공백" in f for f in rep["failures"]), rep


@case
def high_risk_without_capture():
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart", "sha256": _H})   # capture 없음
        db.add_verify_event("F001", "lead", "reread", reread_sha256=_H)
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
        db.add_verify_event("F001", "lead", "reread", reread_sha256=_H)
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
    db.add_verify_event(fid, "lead", "reread", reread_sha256=_H)
    rows = db.facts(); fr = next(r for r in rows if r["id"] == fid)
    if fr.get("risk") == "high":      # (d) 이후 high-risk 본문 사용은 ①② 필수 — 긍정형 짝 픽스처 기본값
        fr.setdefault("independent_groups", ["dart", "irstatement"])
        fr.setdefault("counter_search", {"query": "정정 검색", "result": "없음", "found_stronger_refutation": False})
        _write_jsonl_atomic(wp.facts, rows)
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
    """V13-7: 한국식 수사 삽입형(1천억)·TWh 무태그 사실주장 검출."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        for text in ("투자액은 1천억원 규모다.\n", "발전량은 연 10 TWh.\n", "생산량은 10만톤이다.\n"):
            (wp.root / "x.md").write_text(text, encoding="utf-8")
            rep = verify_facts.verify(wp.root / "x.md", wd)
            assert not rep["ok"] and any("무태그" in f for f in rep["failures"]), (text, rep)


@case
def currency_prefix_untagged_and_mistagged():
    """H2 ①: 접두 통화 표기는 무태그도 오값도 통과하던 사각지대(probe B/C 실측). 긍정형 짝: 값 일치는 통과,
    대장 'USD_million' ↔ 본문 bare 'million' 호환도 유지."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        db.add_fact({"claim": "딜 120M", "risk": "normal", "status": "pending",
                     "context": {"metric": "deal", "entity": "x", "geography": "US", "period": "2025"},
                     "value": {"raw": "120", "unit": "USD_million"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
        _confirm(db, wp, "F002")
        for text in ("시장 규모는 $4.5B 에 달한다.\n", "US$4.5 billion 규모다.\n", "€120M 를 투자했다.\n",
                     "₩300조 시장이다.\n", "USD 45 billion 이다.\n"):
            (wp.root / "u.md").write_text(text, encoding="utf-8")
            rep = verify_facts.verify(wp.root / "u.md", wd)
            assert sum("무태그" in f for f in rep["failures"]) == 1, (text, rep)      # 중복 매치 없이 정확히 1건
        (wp.root / "v.md").write_text("딜 규모는 $999M(F002) 이다.\n", encoding="utf-8")
        rv = verify_facts.verify(wp.root / "v.md", wd)
        assert not rv["ok"] and any("값불일치" in f for f in rv["failures"]), rv
        (wp.root / "s.md").write_text("딜 규모는 $120B(F002) 이다.\n", encoding="utf-8")
        rs = verify_facts.verify(wp.root / "s.md", wd)
        assert not rs["ok"] and any("값불일치" in f for f in rs["failures"]), rs
        for ok_text in ("딜 규모는 $120M(F002) 이다.\n\n![c](_captures/F002.png)\n",
                        "딜 규모는 US$120 million(F002) 이다.\n\n![c](_captures/F002.png)\n",
                        "딜 규모는 120 million(F002) 이다.\n\n![c](_captures/F002.png)\n"):
            (wp.root / "ok.md").write_text(ok_text, encoding="utf-8")
            rok = verify_facts.verify(wp.root / "ok.md", wd)
            assert rok["ok"], (ok_text, rok)


@case
def count_units_are_claims():
    """H2 ②: 건·명·개사·기·위·배·대·kt·Mt·㎡·ha·배럴·EUR 무태그 사실주장 검출. 긍정형 짝: 연도·각주·페이지·
    표 행번호·F태그·연령대·'3대 과제'·'3기 신도시'·'6개월'·'4개 축'·'KT'·'has' 는 오탐하지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        claims = ("직원은 4,500명이다.", "특허 1,234건을 보유한다.", "업계 2위로 부상했다.", "매출이 3.2배 늘었다.",
                  "120기를 설치했다.", "100만대를 판매했다.", "1,200대를 보급했다.", "3개사가 참여한다.",
                  "연 30 kt 생산한다.", "배출량 5 Mt 이다.", "부지 3,000㎡ 규모다.", "3,000만 배럴을 수입했다.",
                  "EUR 120 million 을 조달했다.")
        for text in claims:
            (wp.root / "c.md").write_text(text + "\n", encoding="utf-8")
            rep = verify_facts.verify(wp.root / "c.md", wd)
            assert any("무태그" in f for f in rep["failures"]), (text, rep)
        clean = ("2024년 기준 3부 테마별 본론을 본다. 표 3 과 각주[12], p.45 참조. (F001) 태그. 2026-08-21 접근.\n"
                 "| 3 | 건수 | 12월 건설 |\n\n"
                 "20~30대 소비자와 50대 여성, 3대 핵심 과제, 3기 신도시, 6개월 연장, 4개 축으로 구성.\n"
                 "2023 KT 매출 보고서(EUROPE 2024)는 2024 has grown 이라 썼다. 제25조 규정.\n")
        (wp.root / "ok.md").write_text(clean, encoding="utf-8")
        rok = verify_facts.verify(wp.root / "ok.md", wd)
        assert not any("무태그" in f for f in rok["failures"]), rok


@case
def korean_numeral_warned():
    """H2 ③: 한글 수사('삼백조원')는 값 파싱을 못 하므로 FAIL 대신 [한글수사] WARN 으로 표면화한다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        (wp.root / "k.md").write_text("매출은 삼백조원 규모이며 300.9조원(F001) 이다.\n\n![c](_captures/F001.png)\n",
                                      encoding="utf-8")
        rep = verify_facts.verify(wp.root / "k.md", wd)
        assert rep["ok"] and any("한글수사" in w for w in rep["warnings"]), rep
        (wp.root / "n.md").write_text("삼성전자와 일부 원인을 본다.\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        assert not any("한글수사" in w for w in verify_facts.verify(wp.root / "n.md", wd)["warnings"])


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
def appendix_value_mismatch_fails():
    """H1: 부록은 무태그만 면제다 — 오태그·미확정·값불일치는 부록에서도 FAIL(본문에서 값불일치 맞은
    수치를 부록 '환산근거'로 옮겨 G3 를 통과하던 우회 차단). 긍정형 짝: 값 일치 + 무태그 수치는 WARN."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        good = "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n<!-- FACTSHEET:APPENDIX -->\n## 부록\n"
        for bad, tag in (("- 환산근거: 매출 999조원(F001)\n", "값불일치"),
                         ("- 환산근거: 매출 300.9조원(F009)\n", "오태그")):
            (wp.root / "r.md").write_text(good + bad, encoding="utf-8")
            rep = verify_facts.verify(wp.root / "r.md", wd)
            assert not rep["ok"] and any(tag in f and "부록" in f for f in rep["failures"]), (bad, rep)
        db.add_fact({"claim": "시장 45조", "risk": "normal", "status": "pending",
                     "context": {"metric": "market_size", "entity": "x", "geography": "KR", "period": "2030"},
                     "value": {"raw": "45", "unit": "KRW_T"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
        (wp.root / "r.md").write_text(good + "- 미확정 병기: 45조원(F002)\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("미확정" in f and "부록" in f for f in rep["failures"]), rep
        (wp.root / "ok.md").write_text(good + "- 환율 1,350원/달러 기준 · 매출 300.9조원(F001)\n", encoding="utf-8")
        rok = verify_facts.verify(wp.root / "ok.md", wd)
        assert rok["ok"] and any("부록무태그" in w for w in rok["warnings"]), rok


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


@case
def manifest_image_swap():
    """_images/ 도판은 report.pdf 에 내장되는데 TRACKED 밖이면 G3 뒤 교체를 G5 가 못 잡는다(M3 실측).
    긍정형 짝: 변조 안 하면 ok. IMAGES.md 도 봉인 대상."""
    assert any(pattern.startswith("_images/") for _, pattern in manifest.TRACKED)
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("도판변조", base=td)
        wp = WorkPaths(wd)
        (wp.root / "_images").mkdir()
        (wp.root / "_images" / "fig.png").write_bytes(b"\x89PNG-orig")
        manifest.build(wp)
        assert manifest.verify(wp)["ok"]
        (wp.root / "_images" / "fig.png").write_bytes(b"\x89PNG-swapped")
        v = manifest.verify(wp)
        assert not v["ok"] and "_images/fig.png" in v["changed"], v
        manifest.build(wp)
        (wp.root / "_images" / "IMAGES.md").write_text("| f |\n", encoding="utf-8")   # 봉인 후 인덱스 추가
        v2 = manifest.verify(wp)
        assert not v2["ok"] and "_images/IMAGES.md" in v2["new"], v2


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
        db.add_verify_event("F001", "lead", "reread", reread_sha256=_H)
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
        db.add_verify_event("F001", "lead", "reread", reread_sha256=_H)
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
        db.add_verify_event("F001", "lead", "reread", reread_sha256=_H)
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
        db.add_verify_event("F001", "lead", "reread", reread_sha256=_H)
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
        db.add_verify_event("F001", "lead", "reread", reread_sha256=_H)
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
def lead_event_requires_reread_sha256():
    """M2·MEDIUM-2: by="lead" action="reread" 이벤트는 재열람 산출물 해시가 없으면 add 시점·validate 시점
    모두 거부. 워커 이벤트·lead 의 비-reread 이벤트는 해시 없이 허용(긍정형 짝)."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        db.add_evidence({"fact_id": "F001", "type": "table_cell", "source_url": "https://x", "sha256": _H})
        for bad in (None, "abc", "X" * 64):
            try:
                db.add_verify_event("F001", "lead", "reread", reread_sha256=bad)
                assert False, f"reread_sha256={bad!r} 가 통과됨"
            except ValidationError:
                pass
        db.add_verify_event("F001", "worker-1", "reread")                        # 워커는 해시 없어도 됨
        db.add_verify_event("F001", "lead", "demote", "정의차")                  # lead 비-reread 도 허용
        try:
            db.set_status("F001", "confirmed"); assert False, "lead reread 없이 confirmed 통과"
        except ValidationError:
            pass
        rows = db.facts()
        rows[0]["verify_events"].append({"by": "lead", "at": "2026-08-21T00:00:00", "action": "reread"})  # 손기록
        rows[0]["status"] = "confirmed"
        _write_jsonl_atomic(wp.facts, rows)
        (wp.root / "r.md").write_text("매출 300.9조원(F001).\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("대장무결성" in f and "reread_sha256" in f for f in rep["failures"]), rep


@case
def reread_sha_unbound_warned():
    """D5: reread_sha256 이 그 fact 의 evidence sha256/local/verbatim 어느 해시와도 안 맞으면 [재열람미결박] WARN
    (FAIL 아님 — WebFetch 재열람 경로). 긍정형 짝: evidence sha 와 같으면 WARN 없음."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")                                                 # reread_sha256=_H == evidence sha
        md = "매출 300.9조원(F001).\n\n![c](_captures/F001.png)\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert rep["ok"] and not any("재열람미결박" in w for w in rep["warnings"]), rep
        other = hashlib.sha256(b"elsewhere").hexdigest()
        db.add_verify_event("F001", "lead", "reread", reread_sha256=other)
        rows = db.facts(); rows[0]["verify_events"] = [e for e in rows[0]["verify_events"] if e.get("reread_sha256") != _H]
        _write_jsonl_atomic(wp.facts, rows)
        rep2 = verify_facts.verify(wp.root / "r.md", wd)
        assert rep2["ok"] and any("재열람미결박" in w for w in rep2["warnings"]), rep2


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


@case
def claim_graph_high_risk_used_fails():
    """H4·HIGH-G: risk=high confirmed fact 가 본문에 쓰였는데 ①독립그룹≥2 ②반박검색이 없으면 [반박게이트] FAIL.
    ③기본소스 ④시간증거는 WARN. 본문 미사용 high-risk 는 WARN 만. 중복 라벨(['dart','dart'])은 1그룹.
    긍정형 짝: ①② 채우면 ok(③④ WARN 잔존), 네 필드 다 채우면 WARN 도 사라짐."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)          # F001 risk=high
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")       # _confirm 이 ①② 기본값을 채우므로 여기서 비워 결핍 상태로 시작
        rows = db.facts(); fr = rows[0]
        fr.update({"independent_groups": [], "counter_search": None}); _write_jsonl_atomic(wp.facts, rows)
        md = "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n"
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("[반박게이트]" in f and "독립" in f and "반박검색" in f for f in rep["failures"]), rep

        fr.update({"independent_groups": ["dart", "dart"],
                   "counter_search": {"query": "q", "result": "없음", "found_stronger_refutation": False}})
        _write_jsonl_atomic(wp.facts, rows)
        rep_dup = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep_dup["ok"] and any("독립" in f for f in rep_dup["failures"]), rep_dup

        fr["independent_groups"] = ["dart", "irstatement"]; _write_jsonl_atomic(wp.facts, rows)
        rep2 = verify_facts.verify(wp.root / "r.md", wd)
        assert rep2["ok"] and any("반박게이트" in w and "기본소스" in w for w in rep2["warnings"]), rep2

        fr.update({"primary_source_ref": "E001", "observed_at": "2026-07-22", "valid_at": "2025-03"})
        _write_jsonl_atomic(wp.facts, rows)
        rep3 = verify_facts.verify(wp.root / "r.md", wd)
        assert rep3["ok"] and not any("반박게이트" in w for w in rep3["warnings"]), rep3

        # 본문 미사용 high-risk: WARN 만
        (wp.root / "u.md").write_text("본문에 F001 없음.\n\n![c](_captures/F001.png)\n", encoding="utf-8")
        fr.update({"independent_groups": [], "counter_search": None}); _write_jsonl_atomic(wp.facts, rows)
        ru = verify_facts.verify(wp.root / "u.md", wd)
        assert ru["ok"] and any("본문 미사용" in w for w in ru["warnings"]), ru


# --- G2/G8 재작성 회귀(문서정합 — 축 프리셋·종료기준·조사유형 4종·intent-diff) --------------
def _read(rel):
    return (SKILL_ROOT / rel).read_text(encoding="utf-8")


@case
def axis_preset_parity():
    rfmt = (SKILL_ROOT / "references" / "report-format.md").read_text(encoding="utf-8")
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    def rf_axes(label):
        m = re.search(rf"\*\*{label}\*\*.*?3부\s*축=([^\n]+?)\s·\s\d+부=", rfmt, re.S)
        assert m, f"report-format.md 에 {label} 3부 축 목록 없음"
        toks = [re.sub(r"\([^)]*\)", "", t).strip() for t in m.group(1).split("/")]
        return {t for t in toks if t}

    assert re.search(r"^## 조사유형별", rfmt, re.M), "절 제목 접두 유지 안 됨"
    assert "축 프리셋" in rfmt
    assert "성숙도" not in rfmt, "폐기 축 문자열이 report-format.md 에 남아있음"

    m_block = re.search(r"- 조사 분할:.*?(?=\n- )", skill, re.S)
    assert m_block, "SKILL.md 의 '조사 분할:' 불릿을 못 찾음(문서 구조 변경됨?)"
    clauses = {lbl: val for lbl, val in
              re.findall(r"\*\*([^*]+)\*\*=(.+?)(?=\s*·\s*\*\*|\.\s*$)", m_block.group(0) + " ", re.S)}
    assert clauses, "SKILL.md 조사 분할에서 절을 하나도 못 찾음"

    for label in ("기술동향", "산업동향"):
        assert label in clauses, f"SKILL.md 조사 분할에 {label} 없음"
        m1 = re.search(r"축분할\s*\(([^)]+)\)", clauses[label])
        if m1:
            skill_set = {t for t in re.split("·", m1.group(1).split("+")[0].strip()) if t}
        else:
            skill_set = set()
            for part in clauses[label].split("+"):
                part = re.sub(r"\([^)]*\)", "", part).strip()
                if part:
                    skill_set.add(part)
        assert rf_axes(label) == skill_set, (label, rf_axes(label), skill_set)

    rf_biz = rf_axes("기술사업화 실사")
    assert rf_biz
    if "기술사업화 실사" in clauses:
        m2 = re.search(r"축분할\s*\(([^)]+)\)", clauses["기술사업화 실사"])
        assert m2, clauses["기술사업화 실사"]
        skill_biz = {t for t in re.split("·", m2.group(1).split(",")[0].strip()) if t}
        assert rf_biz == skill_biz, (rf_biz, skill_biz)

    assert rf_axes("기관·기업 실사")   # SKILL.md 비교대상 없음(대상기반 분할) — 존재만


@case
def termination_terms_unified():
    """SKILL.md·agent-briefs.md·report-format.md·verification-gates.md 4파일에서
    '조사종료기준'/'종료기준'(공백 정규화 후) 이 사라지고 '축별 충분조건'·'루프 수렴조건'이
    존재하는지."""
    files = {"SKILL.md": _read("SKILL.md"),
             "agent-briefs.md": _read("references/agent-briefs.md"),
             "report-format.md": _read("references/report-format.md"),
             "verification-gates.md": _read("references/verification-gates.md")}
    norm = lambda s: re.sub(r"\s+", "", s)
    for name, t in files.items():
        n = norm(t)
        assert "조사종료기준" not in n and "종료기준" not in n, f"{name} 에 종료기준 잔존"
    assert "유일종료조건" not in norm(files["SKILL.md"]), "SKILL.md 에 구 문구 잔존"
    assert "축별충분조건" in norm(files["SKILL.md"])
    assert "루프수렴조건" in norm(files["SKILL.md"])
    for name in ("agent-briefs.md", "report-format.md", "verification-gates.md"):
        assert "축별충분조건" in norm(files[name]), f"{name} 에 축별 충분조건 없음"


@case
def depth_cap_default_present():
    """깊이캡 숫자 기본값이 SKILL.md·research-plan.md 최소 2곳에 정규식으로 잡히고 서로
    일치하는지(한쪽만 고치고 다른 쪽을 잊는 사고 방지)."""
    skill = _read("SKILL.md")
    plan = _read("references/research-plan.md")
    m1 = re.search(r"깊이캡.{0,20}?(\d+)\s*회.{0,10}?(\d+)\s*명", skill)
    assert m1, "SKILL.md 에 깊이캡 숫자 기본값 없음"
    m2 = re.search(r"깊이캡 기본값.*?(\d+)\s*회.*?(\d+)\s*명", plan)
    assert m2, "research-plan.md 에 깊이캡 숫자 기본값 없음"
    assert (m1.group(1), m1.group(2)) == (m2.group(1), m2.group(2)), \
        f"깊이캡 값 불일치: SKILL.md={m1.groups()} research-plan.md={m2.groups()}"


@case
def axis_scoped_convergence():
    """확장수렴 절에 '축별'·'잔여'가 함께 있는지 — 리드가 안 나오는 축이 조용히 '수렴 성공'
    으로 처리되는 구멍을 막는 문구가 실제로 있는지 확인."""
    m = re.search(r"\*\*확장수렴 루프\*\*.*?(?=\n\n|\n###)", _read("SKILL.md"), re.S)
    assert m, "확장수렴 루프 절을 못 찾음"
    block = m.group(0)
    assert "축별" in block and "잔여" in block, block


@case
def expand_marker_has_axis():
    """agent-briefs.md EXPAND 블록의 LEAD·DEAD END 줄에 AXIS 필드가 (LEAD 는 같은 줄에) 있는지."""
    m = re.search(r"## EXPAND\n(.*?)\n\n", _read("references/agent-briefs.md"), re.S)
    assert m, "EXPAND 블록을 못 찾음"
    block = m.group(1)
    lead_line = next((ln for ln in block.splitlines() if ln.startswith("- LEAD:")), None)
    assert lead_line and "AXIS:" in lead_line, f"LEAD 줄에 AXIS 없음: {lead_line!r}"
    assert "AXIS:" in block, "EXPAND 블록에 AXIS 없음"


@case
def survey_type_parity():
    """report-format.md 조사유형별 절의 유형 수(4)와 SKILL.md 조사 분할의 유형 수(4)가 같고,
    양쪽 다 '기술사업화 실사' 를 포함하는지."""
    rfmt = _read("references/report-format.md")
    skill = _read("SKILL.md")
    m_sec = re.search(r"## 조사유형별.*?(?=\n##|\Z)", rfmt, re.S)
    assert m_sec, "조사유형별 절을 못 찾음"
    types = ["기술동향", "산업동향", "기관·기업", "기술사업화 실사"]
    for t in types:
        assert t in m_sec.group(0), f"report-format.md 조사유형별 절에 {t} 없음"
    m_block = re.search(r"- 조사 분할:.*?(?=\n- )", skill, re.S)
    assert m_block, "SKILL.md 조사 분할 불릿을 못 찾음"
    for t in types:
        short = t.replace(" 실사", "")
        assert short in m_block.group(0) or t in m_block.group(0), f"SKILL.md 조사 분할에 {t} 없음"
    assert "기술사업화 실사" in rfmt and "기술사업화 실사" in skill


@case
def ip_landscape_in_tech_variant():
    """기술동향 변형 4부가 IP 랜드스케이프(출원추이·CPC 등)로 승격됐고, source-ladder.md 가
    특허 1차소스 도구를 실제로 가리키는지."""
    rfmt = _read("references/report-format.md")
    ladder = _read("references/source-ladder.md")
    assert "랜드스케이프" in rfmt and "CPC" in rfmt, "기술동향 4부에 IP 랜드스케이프 요소 없음"
    assert ("korean-patent-search" in ladder or "Patent_Landscape" in ladder
            or "Patent Landscape" in ladder), "source-ladder.md 에 특허 1차소스 도구 명시 없음"


@case
def intent_diff_closed_at_g4():
    """SKILL.md 가 'G4 에서 발견과 대조해 gap 종결'이라 약속한 것을 verification-gates.md
    G4 절이 실제로 이행하는지(축별 대조 단계 + gap 발견 시 복귀처 명시)."""
    gates = _read("references/verification-gates.md")
    skill = _read("SKILL.md")
    m = re.search(r"## G4 preview.*?(?=\n##|\Z)", gates, re.S)
    assert m, "verification-gates.md G4 절을 못 찾음"
    block = m.group(0)
    assert "intent-diff" in block, "G4 절에 intent-diff 대조 단계 없음"
    assert "축별" in block, "G4 절에 '축별' 대조 언급 없음"
    assert "복귀" in block, "G4 절에 복귀 규칙 없음"
    assert skill.count("intent-diff") >= 2, "SKILL.md 의 intent-diff 언급이 너무 적음(약속만 하고 안 지킴 재발 방지)"
    assert "verification-gates.md" in re.search(r"\[4\] render_pdf.*?(?=\n---|\Z)", skill, re.S).group(0), \
        "SKILL.md G4 절이 verification-gates.md 를 참조하지 않음"


@case
def skill_frontmatter_intact():
    """front-matter YAML 이 여전히 파싱되고, description 이 1024자 이하이며, 4번째 조사유형
    '기술사업화 실사' 가 포함되는지."""
    text = _read("SKILL.md")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "front-matter 파싱 실패(--- 블록 없음)"
    data = yaml.safe_load(m.group(1))
    desc = data["description"]
    assert len(desc) <= 1024, f"description {len(desc)}자 — 1024자 초과"
    assert "기술사업화 실사" in desc, "description 에 기술사업화 실사 없음"


# --- 게이트 원장 소유권(영수증 위조·G5 자기기록 회귀) --------------------------

@case
def owned_gate_cli_forgery_blocked():
    """소유 스크립트 게이트(G3/[4b]/G5)를 gates.py CLI 손기록으로 위조하면 거부되는지 —
    소유자를 우회한 손기록은 스크립트를 돌리지 않은 영수증과 구분되지 않는다.
    긍정형 짝: 무소유 게이트(G1)는 CLI 기록이 여전히 된다."""
    import gates
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("원장위조", base=td)
        wp = WorkPaths(wd)
        for g in ("G3", "[4b]", "G5"):
            rc = gates.main(["record_script_result", g, "0", str(wd)])
            assert rc == 1, f"{g} CLI 손기록이 통과됨"
        assert not gates.ledger_path(wp).exists(), "거부됐는데 원장에 기록이 남음"
        assert gates.main(["record_script_result", "G1", "0", str(wd), "--summary", "join"]) == 0
        assert gates.successful_receipt(wp, "G1"), "무소유 게이트(G1) CLI 기록 실패"


@case
def g5_receipt_owned_by_manifest_verify():
    """manifest.py verify CLI 가 G4 영수증 없이는 거부하고, 정상 체인에선 결과를 G5 로
    자기기록하며, 변조 후 FAIL 도 원장에 남는지(실패 이력 소실 방지)."""
    import subprocess
    import gates
    cli = [sys.executable, str(SKILL_ROOT / "scripts" / "manifest.py"), "verify"]

    def run_cli(wd):
        return subprocess.run(cli + [str(wd)], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")

    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("지5소유", base=td)
        wp = WorkPaths(wd)
        (wp.audit / "research-plan.md").write_text("# plan\n", encoding="utf-8")
        wp.facts.write_text("", encoding="utf-8")
        (wp.root / "report.md").write_text("# r\n", encoding="utf-8")
        gates.record_manual(wp, "G0", "approved")
        gates.record_script_result(wp, "G1", 0, "join PASS")
        gates.record_manual(wp, "[2]", "lead reread")
        gates.record_script_result(wp, "G3", 0, "verify PASS")
        manifest.build(wp)
        gates.record_script_result(wp, "[4b]", 0, "reseal PASS",
                                   extra={"manifest_sha256": manifest.sha256_file(wp.manifest)})

        r1 = run_cli(wd)
        assert r1.returncode == 1 and "G4" in r1.stderr, f"G4 없이 verify 통과: {r1.stderr!r}"

        gates.record_manual(wp, "G4", "preview OK")
        r2 = run_cli(wd)
        assert r2.returncode == 0, f"정상 체인인데 verify 실패: {r2.stderr!r}"
        assert gates.successful_receipt(wp, "G5"), "G5 영수증 미기록"

        (wp.root / "report.md").write_text("# tampered\n", encoding="utf-8")
        r3 = run_cli(wd)
        tail = json.loads(gates.ledger_path(wp).read_text(encoding="utf-8").splitlines()[-1])
        assert r3.returncode == 1 and tail["gate"] == "G5" and tail["exit"] == 1, (r3.returncode, tail)


@case
def receipt2_requires_lead_reread_and_binds_digest():
    """M1·HIGH-H: record [2] 는 confirmed 전건 lead reread 검사 후에만 기록되고, 이후 confirmed 집합이
    바뀌면 영수증이 무효(G3 선행 실패) → 재기록해야 한다. G2 의 evidence 추가는 무효화하지 않는다(긍정형 짝)."""
    import gates
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        (wp.audit).mkdir(parents=True, exist_ok=True)
        (wp.audit / "research-plan.md").write_text("# plan\n", encoding="utf-8")
        gates.record_manual(wp, "G0", "approved")
        gates.record_script_result(wp, "G1", 0, "join")
        rows = db.facts(); rows[0].update({"status": "confirmed", "evidence_ids": ["E001"]})   # lead 이벤트 없는 손기록
        _write_jsonl_atomic(wp.facts, rows)
        try:
            gates.record_manual(wp, "[2]", "hand"); assert False, "lead 이벤트 없는 confirmed 가 [2] 를 통과"
        except gates.GateError:
            pass
        rows[0].update({"status": "pending", "evidence_ids": []}); _write_jsonl_atomic(wp.facts, rows)
        _confirm(db, wp, "F001")
        rec = gates.record_manual(wp, "[2]", "lead reread")
        assert rec["confirmed_count"] == 1 and rec["confirmed_digest_sha256"] and rec["facts_db_sha256"]
        assert gates.check_gate(wp, "G3")["ok"], gates.check_gate(wp, "G3")
        db.add_evidence({"fact_id": "F001", "type": "text_quote", "verbatim": "추가 증거",
                         "source_url": "https://y", "sha256": _H})                      # G2 경로: 무효화 안 됨
        assert gates.check_gate(wp, "G3")["ok"]
        db.add_fact({"claim": "x", "risk": "normal", "status": "pending",
                     "context": {"metric": "m", "entity": "e", "geography": "KR", "period": "2025"},
                     "value": {"raw": "1", "unit": "건"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
        _confirm(db, wp, "F002")                                                          # confirmed 집합 변경
        chk = gates.check_gate(wp, "G3")
        assert not chk["ok"] and any("[2]" in i and "재기록" in i for i in chk["issues"]), chk
        gates.record_manual(wp, "[2]", "lead reread again")
        assert gates.check_gate(wp, "G3")["ok"]
        # 원장 없는 작업폴더에서 [2] 는 fail-closed
        wd2 = resolve_work_dir("대장없음", base=td); wp2 = WorkPaths(wd2)
        (wp2.audit).mkdir(parents=True, exist_ok=True); (wp2.audit / "research-plan.md").write_text("# p\n", encoding="utf-8")
        gates.record_manual(wp2, "G0", "ok"); gates.record_script_result(wp2, "G1", 0, "join")
        try:
            gates.record_manual(wp2, "[2]", "hand"); assert False, "facts.jsonl 없이 [2] 기록됨"
        except gates.GateError:
            pass


@case
def figure_caption_without_source_fails():
    """도판 바로 뒤에 [그림] 캡션이 있어도 출처가 없으면 [도판출처] FAIL 이어야 한다."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("도판출처누락", base=td)
        wp = WorkPaths(wd)
        wp.report_md.write_text(
            "본문.\n\n![외부 도판](https://example.com/chart.png)\n[그림] 시장 구조\n",
            encoding="utf-8",
        )
        rep = verify_facts.verify(wp.report_md, wd)
        assert not rep["ok"] and any("[도판출처]" in f for f in rep["failures"]), rep


@case
def generated_chart_without_fact_binding_fails():
    """assets/ 생성 차트의 캡션에 출처가 있어도 F태그가 없으면 [도판무결박] FAIL 이어야 한다."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("도판무결박", base=td)
        wp = WorkPaths(wd)
        (wp.gen_assets / "market.png").write_bytes(b"\x89PNG")
        wp.report_md.write_text(
            "본문.\n\n![시장 차트](assets/market.png)\n[그림] 시장 추이 · 출처: 자체 계산\n",
            encoding="utf-8",
        )
        rep = verify_facts.verify(wp.report_md, wd)
        assert not rep["ok"] and any("[도판무결박]" in f for f in rep["failures"]), rep


@case
def sourced_and_fact_bound_chart_passes():
    """캡션·출처·F태그를 모두 갖춘 assets/ 도판은 새 강제 검사에서 통과해야 한다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        (wp.gen_assets / "market.png").write_bytes(b"\x89PNG")
        wp.report_md.write_text(
            "본문.\n\n![시장 차트](assets/market.png)\n"
            "[그림] 매출 추이 (F001) · 출처: 자체 계산\n",
            encoding="utf-8",
        )
        rep = verify_facts.verify(wp.report_md, wd)
        assert rep["ok"], rep


@case
def axis_figure_coverage_is_warning_only():
    """3부 축 이름은 헤딩에서 동적으로 읽고, 도판 없는 축은 FAIL 아닌 경고로만 표면화한다."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("도판커버리지", base=td)
        wp = WorkPaths(wd)
        wp.report_md.write_text(
            "# 부 3. 테마별 본론\n"
            "## 축: 시장\n![시장](https://example.com/market.png)\n"
            "[그림] 시장 구조 · 출처: 공식 통계\n"
            "## 축: 정책\n정책 환경 서술.\n",
            encoding="utf-8",
        )
        rep = verify_facts.verify(wp.report_md, wd)
        coverage = [w for w in rep["warnings"] if "[도판커버리지]" in w]
        assert rep["ok"] and len(coverage) == 1 and "축: 정책" in coverage[0], rep


@case
def empty_source_label_fails():
    """`출처:` 라벨만 있고 값이 비면 [도판출처] FAIL 이어야 한다 — 서식만 갖춘 무출처 차단."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("빈출처", base=td)
        wp = WorkPaths(wd)
        (wp.root / "_images").mkdir(exist_ok=True)
        (wp.root / "_images" / "a.png").write_bytes(b"\x89PNG")
        wp.report_md.write_text(
            "본문.\n\n![](_images/a.png)\n[그림] 제목 — 출처:\n", encoding="utf-8")
        rep = verify_facts.verify(wp.report_md, wd)
        assert not rep["ok"] and any("[도판출처]" in f for f in rep["failures"]), rep


@case
def every_missing_figure_path_is_reported():
    """참조 경로는 건별 판정한다 — 한 장만 실재하면 나머지 깨진 경로가 묻히면 안 된다."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("경로건별", base=td)
        wp = WorkPaths(wd)
        (wp.root / "_images").mkdir(exist_ok=True)
        (wp.root / "_images" / "real.png").write_bytes(b"\x89PNG")
        body = "".join(f"![](_images/miss{i}.png)\n[그림] 제목{i} — 출처: 기관\n" for i in range(3))
        wp.report_md.write_text(
            body + "![](_images/real.png)\n[그림] 진짜 — 출처: 기관\n", encoding="utf-8")
        rep = verify_facts.verify(wp.report_md, wd)
        missing = [f for f in rep["failures"] if "[도판경로]" in f]
        assert not rep["ok"] and len(missing) == 3, rep


@case
def dotdot_path_cannot_borrow_captures_exemption():
    """`_captures/../assets/...` 는 실제로 assets 차트다 — 증빙캡처 면제를 빌려쓰지 못한다."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("경로우회", base=td)
        wp = WorkPaths(wd)
        (wp.gen_assets / "chart.svg").write_text("<svg/>", encoding="utf-8")
        wp.report_md.write_text(
            "본문.\n\n![](_captures/../assets/chart.svg)\n캡션 없음\n", encoding="utf-8")
        rep = verify_facts.verify(wp.report_md, wd)
        assert not rep["ok"] and any("[도판출처]" in f for f in rep["failures"]) \
            and any("[도판무결박]" in f for f in rep["failures"]), rep


@case
def figure_tag_without_image_is_not_a_figure():
    """`<figure>` 만 있고 이미지 참조가 없으면 0장이다 — 결박검사 대상 밖으로 새지 않게."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("빈figure", base=td)
        wp = WorkPaths(wd)
        wp.report_md.write_text("본문.\n\n<figure>도표 자리</figure>\n", encoding="utf-8")
        rep = verify_facts.verify(wp.report_md, wd)
        assert not rep["ok"] and any("[도판]" in f for f in rep["failures"]), rep


# --- C1·C2 봉인 회귀(G3 이후 변조 세탁 차단 · TRACKED 밖 산출물 추적) ----------
@case
def reseal_rejects_post_g3_tamper():
    """G3 이후 facts.jsonl 을 변조한 채 render_pdf.py CLI 를 돌리면 재봉인이 거부된다.
    세탁이 성공하면 변조가 새 기준선이 되어 G5 가 PASS 한다(C1). 긍정형 짝: 변조 없으면
    exit 0, [4b] 에 manifest_sha256·artifacts(report.pdf) 가 있고 기존 항목 해시는 그대로."""
    import gates
    with tempfile.TemporaryDirectory() as td:
        wd, wp = _chain_to_g3(td, "렌더변조")
        baseline = manifest.sha256_file(wp.manifest)
        wp.facts.write_text('{"id":"F001","tampered":1}\n', encoding="utf-8")
        r = _run_script("render_pdf.py", str(wp.report_md))
        assert r.returncode == 1, f"변조 후 render CLI 가 통과함: {r.stderr!r} {r.stdout!r}"
        assert not any(rec.get("gate") == "[4b]" for rec in _ledger(wp)), _ledger(wp)
        assert manifest.sha256_file(wp.manifest) == baseline, "실패했는데 manifest.json 이 바뀜"

    with tempfile.TemporaryDirectory() as td:                          # 긍정형 짝
        wd, wp = _chain_to_g3(td, "렌더정상")
        before = json.loads(wp.manifest.read_text(encoding="utf-8"))["entries"]
        r = _run_script("render_pdf.py", str(wp.report_md))
        assert r.returncode == 0, f"정상 체인인데 render CLI 실패: {r.stderr!r}"
        rec = gates.successful_receipt(wp, "[4b]")
        assert rec and rec.get("manifest_sha256"), rec
        arts = rec.get("artifacts") or []
        assert any((a.get("path") if isinstance(a, dict) else a) == "report.pdf" for a in arts), rec
        after = json.loads(wp.manifest.read_text(encoding="utf-8"))["entries"]
        assert "report.pdf" in after, after
        for rel, meta in before.items():
            assert after[rel]["sha256"] == meta["sha256"], (rel, meta, after[rel])


@case
def g5_rejects_rebuilt_manifest():
    """정상 체인([4b] 까지) 뒤 manifest.build 로 기준선을 세탁하고 G4 후 verify CLI 를
    돌리면 [4b]↔manifest 결박 불일치로 거부돼야 한다. 전제조건 단계에서 죽으므로 G5 PASS
    영수증은 남지 않는다."""
    import gates
    with tempfile.TemporaryDirectory() as td:
        wd, wp = _chain_to_g3(td, "기준선세탁")
        wp.report_pdf.write_bytes(b"%PDF-1.4 fake")
        g3 = gates.successful_receipt(wp, "G3")
        manifest.extend(wp, [wp.report_pdf], expected_sha256=g3["manifest_sha256"])
        gates.record_script_result(
            wp, "[4b]", 0, "reseal PASS",
            extra={"manifest_sha256": manifest.sha256_file(wp.manifest),
                   "artifacts": [{"path": "report.pdf",
                                  "sha256": manifest.sha256_file(wp.report_pdf)}]},
        )
        manifest.build(wp)                                            # 세탁 시도
        gates.record_manual(wp, "G4", "preview OK")
        r = _run_script("manifest.py", "verify", str(wd))
        assert r.returncode == 1, f"세탁된 manifest 가 G5 를 통과함: {r.stderr!r}"
        assert "[4b]" in r.stderr, r.stderr
        tail = _ledger(wp)[-1]
        assert tail["gate"] != "G5" or tail.get("exit") != 0, tail
        assert not gates.successful_receipt(wp, "G5")


@case
def manifest_extend_tracks_custom_artifact():
    """extend 로 TRACKED 글롭 밖 이름(custom.pdf)을 봉인하면 변조는 changed, 삭제는
    missing 으로 잡힌다. 작업폴더 밖 경로는 ValueError."""
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("커스텀산출물", base=td)
        wp = WorkPaths(wd)
        wp.facts.write_text("{}\n", encoding="utf-8")
        manifest.build(wp)
        outside = Path(td) / "outside.pdf"
        outside.write_bytes(b"%PDF outside")
        try:
            manifest.extend(wp, [outside])
            raise AssertionError("작업폴더 밖 경로가 extend 를 통과함")
        except ValueError:
            pass

        custom = wp.root / "custom.pdf"
        custom.write_bytes(b"%PDF custom")
        manifest.extend(wp, [custom], label="render")
        assert manifest.verify(wp)["ok"]
        custom.write_bytes(b"%PDF tampered")
        v = manifest.verify(wp)
        assert not v["ok"] and "custom.pdf" in v["changed"], v
        custom.unlink()
        v2 = manifest.verify(wp)
        assert not v2["ok"] and "custom.pdf" in v2["missing"], v2


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
