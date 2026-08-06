"""test_adversarial.py — 적대적 fixture 전건 실패 검출 (plan-v2 검증 완료기준).

게이트/검증기가 조작·오류를 '정확히 실패로' 잡는지 확인한다. 각 케이스는 통과가 아니라
'검출(실패 판정)'이 성공이다. chk-scope: 빈결과·삼킨 예외를 성공으로 신뢰하지 않는다.
"""
import hashlib
import ipaddress
import json
import re
import socket
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
def merge_evidence_join_and_conflict():
    """v5: 같은 claim_key 재수집의 정규 출구(add_fact 가 안내하던 함수가 실재하지 않았다).
    값 일치면 evidence 합류, 값 불일치면 병합 거부 — 자동 채택 금지."""
    import search as _search                                  # 차단/무결과 분리도 같은 배치
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart.fss.or.kr/x", "sha256": _H})
        same = {"claim": "동일 관찰", "risk": "normal", "status": "pending",
                "context": {"metric": "revenue", "entity": "삼성", "geography": "KR",
                            "period": "2024"},
                "value": {"raw": "300.9", "unit": "KRW_T"},
                "grade": {"authority": "B", "independence": "B", "directness": "B",
                          "recency": "B"},
                "evidence_ids": ["E001"]}
        r = db.merge_evidence(same)
        assert r["merged"] and r["fact_id"] == "F001", r
        assert len(db.facts()) == 1, "병합인데 행이 늘었다"
        assert r["observer_groups"] == ["dart.fss.or.kr"], r    # 같은 출처는 그룹 1개

        diff = dict(same, value={"raw": "412.0", "unit": "KRW_T"})
        r2 = db.merge_evidence(diff)
        assert not r2["merged"] and r2["conflict"], r2
        assert len(db.facts()) == 1 and db.facts()[0]["value"]["raw"] == "300.9", db.facts()

    # 검색: 200 차단 페이지는 '결과 없음'이 아니라 차단으로 분리돼야 한다
    assert _search.is_blocked_page("<html>...unusual traffic detected...</html>")
    assert not _search.is_blocked_page("<html><a class='result__a' href='x'>정상</a></html>")
    blocked = []
    orig_get = _search._get
    _search._get = lambda u, timeout=12: (200, "<html>anomaly detection triggered</html>")
    try:
        res = _search._ddg("수소 시장", 5, blocked)
    finally:
        _search._get = orig_get
    assert res == [] and blocked == ["ddg:blocked"], (res, blocked)


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
def feed_mime_allowed_and_item_matched():
    """v5: application/rss+xml 류가 정확일치 규칙에 막혀 전량 차단되던 것 해소(긍정형).
    반대편: 사이트 공용 피드에 대상 URL 이 없으면 '남의 기사'를 원문으로 인정하지 않는다."""
    for mime in ("application/rss+xml", "application/atom+xml", "application/rdf+xml"):
        assert fetch.mime_allowed(mime), mime
    assert not fetch.mime_allowed("video/mp4"), "허용 범위가 과도하게 열림"

    feed = ("<rss><channel>" + "".join(
        f"<item><title>기사{i}</title><link>https://news.example/other{i}</link>"
        f"<description>{'본문 내용 ' * 60}</description></item>" for i in range(5))
        + "</channel></rss>")
    res = {"text": feed, "final_url": "https://news.example/target", "status": 200}
    v = fetch._feed_item_verdict(res, "https://news.example/target",
                                 {"verdict": "ok", "reason": "body"})
    assert v["verdict"] == "partial" and "feed item mismatch" in v["reason"], v

    hit = feed.replace("https://news.example/other2", "https://www.news.example/target/")
    res2 = dict(res, text=hit)
    v2 = fetch._feed_item_verdict(res2, "https://news.example/target",
                                  {"verdict": "ok", "reason": "body"})
    assert v2["verdict"] == "ok", v2                  # 일치 item 이 있으면 그대로 인정


@case
def mojibake_body_not_counted_as_success():
    """v5: 인코딩 판독 실패로 U+FFFD 범벅이 된 본문이 '수집 성공'으로 저장되면 안 된다.
    긍정형 짝: meta charset 만 선언한 EUC-KR 문서는 사다리 폴백으로 깨끗이 디코드된다."""
    korean = "수소 산업 시장 전망 보고서 " * 200
    html = ('<html><head><meta charset="euc-kr"></head><body>' + korean + "</body></html>")
    decoded = fetch._decode_body(html.encode("euc-kr"), None)   # 헤더 charset 미선언
    assert decoded.count("�") == 0 and korean[:20] in decoded, decoded[:60]

    broken = ("가나다 " * 500).encode("euc-kr")                  # 선언과 실체 불일치 + 폴백 불가
    text = broken.decode("utf-8", errors="replace")
    assert fetch._mojibake_ratio(text) > fetch.MOJIBAKE_MAX
    v = fetch.validate_body(text, 200, mojibake=fetch._mojibake_ratio(text))
    assert v["verdict"] == "partial" and "mojibake" in v["reason"], v


@case
def wayback_snapshot_date_and_https():
    """v5: 아카이브 조회는 https + 스냅샷 시점 병기 + 배너 없는 id_ 본문."""
    calls = []

    def _fake_once(u, imp, **kw):
        calls.append(u)
        if "archive.org/wayback/available" in u:
            return {"ok": True, "status": 200, "text": json.dumps({"archived_snapshots": {
                "closest": {"available": True, "timestamp": "20210317120000",
                            "url": "https://web.archive.org/web/20210317120000/https://x.test/ir"}}}),
                "final_url": u}
        return {"ok": True, "status": 200, "text": "본문 " * 500, "raw": b"x", "final_url": u}

    orig = fetch._fetch_once
    fetch._fetch_once = _fake_once
    try:
        r = fetch._via_wayback("https://x.test/ir")
    finally:
        fetch._fetch_once = orig
    assert calls[0].startswith("https://"), calls[0]
    assert r.get("snapshot_date") == "2021-03-17", r.get("snapshot_date")
    assert "id_/" in r["archived_url"], r["archived_url"]


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
def _real_png(path: Path, text: str = "매출 300.9조원") -> bytes:
    """진짜 PNG 캡처(fitz 렌더). 4바이트 스텁은 픽셀 검사·해시 결박을 원리적으로 못 받는다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=420, height=200)
    page.draw_rect(fitz.Rect(10, 10, 410, 190), color=(0.1, 0.2, 0.6), width=2)
    page.insert_text((28, 70), text, fontsize=13)
    page.insert_text((28, 110), "source: https://dart.example/doc", fontsize=9)
    page.get_pixmap(dpi=110).save(str(path))
    doc.close()
    return path.read_bytes()


def _snapshot(wp, fid: str, body: str = "매출 300.9조원(원문 스냅샷)") -> tuple[str, str]:
    """_sources 에 원문 스냅샷 실파일을 쓰고 (상대경로, 실해시)를 돌려준다.
    evidence.sha256 이 '아무 64자 hex'가 아니라 실제 바이트의 해시여야 결박이 성립한다."""
    wp.sources.mkdir(parents=True, exist_ok=True)
    rel = f"_sources/{fid}_clean.txt"
    p = wp.root / rel
    p.write_text(body, encoding="utf-8")
    return rel, hashlib.sha256(p.read_bytes()).hexdigest()


def _confirm(db, wp, fid, with_capture=True, claim_graph=True):
    """fact 를 confirmed 로 만든다(원문 스냅샷 + 캡처 + 팀리드 재열람 + claim-graph 요건).

    스냅샷·캡처는 **실파일**이고 sha256 은 그 실해시다 — 픽스처가 위조본이면 결박 검사를
    도입할 때마다 '그린 유지'가 아니라 '그린 재획득'이 된다(v5 감사에서 실제로 막혔던 부채).
    claim_graph=True 면 [Bx] 긍정 요건까지 채운다(v8 에서 FAIL 로 승격됐고, 고위험 사실의
    '정당하게 확정된 상태'란 이 요건을 만족한 상태라는 뜻이다). 요건 미달을 시험하는
    케이스는 claim_graph=False 로 부른다.
    """
    local, sha = _snapshot(wp, fid)
    ev = {"fact_id": fid, "type": "table_cell", "source_url": "https://dart.example/doc",
          "sha256": sha, "local": local, "http_status": 200, "source_role": "원출처",
          "observer_group": "dart"}
    if with_capture:
        cap = f"_captures/{fid}.png"
        raw = _real_png(wp.root / cap)
        ev["capture"] = cap
        ev["capture_sha256"] = hashlib.sha256(raw).hexdigest()
    ev_rec = db.add_evidence(ev)
    if claim_graph:
        rows = db.facts()
        fr = next(r for r in rows if r["id"] == fid)
        fr.update({"independent_groups": ["dart", "irstatement"],
                   "counter_search": {"query": f"{fid} 정정 공시", "result": "없음",
                                      "found_stronger_refutation": False},
                   "primary_source_ref": ev_rec["id"],
                   "observed_at": "2026-08-06", "valid_at": "2025-03"})
        _write_jsonl_atomic(wp.facts, rows)
    db.add_verify_event(fid, "lead", "reread", evidence_id=ev_rec["id"])
    db.set_status(fid, "confirmed")
    return ev_rec


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
def blank_capture_rejected_at_generation():
    """v6/SC-4: 백지·단색 렌더는 생성 시점에 .FAILED 로 돌린다 — 종전에는 팀리드 육안만이
    유일한 검출 장치라, 비용 압박으로 표본만 보면 방어가 통째로 사라졌다."""
    with tempfile.TemporaryDirectory() as td:
        blank = Path(td) / "blank.pdf"
        doc = fitz.open(); doc.new_page(); doc.save(str(blank)); doc.close()   # 완전 백지
        out = Path(td) / "cap.png"
        r = capture_pdf.capture_page(blank, 1, out)
        assert not r["ok"] and "백지" in r["reason"], r
        assert not out.exists(), "백지인데 정상 캡처 경로에 저장됨"
        assert out.with_name("cap.FAILED.png").exists(), "실패 사이드카가 없다"

        # 긍정형 짝: 잉크가 옅은 페이지도 통과해야 한다 — 과잉 차단이 백지 통과보다 나쁘다.
        # (실측 기준: 정상 최저는 표 형태 unique=3·잉크율 0.0097, 임계는 unique<=2 & 0.0005)
        for name, build in [
            ("표 형태", lambda p: ([p.draw_line(fitz.Point(50, 80 + i * 25),
                                             fitz.Point(500, 80 + i * 25)) for i in range(8)],
                                 [p.insert_text((60, 95 + i * 25), f"항목{i}  300.9  45.2")
                                  for i in range(7)])),
            ("텍스트 1줄", lambda p: p.insert_text((72, 100), "Revenue 2024: 300.9 KRW trillion")),
        ]:
            good = Path(td) / f"{name}.pdf"
            doc = fitz.open(); pg = doc.new_page(); build(pg)
            doc.save(str(good)); doc.close()
            out2 = Path(td) / f"{name}.png"
            r2 = capture_pdf.capture_page(good, 1, out2)
            assert r2["ok"] and out2.exists(), (name, r2)


_LIVE_PAGE = """<html><head><meta charset="utf-8"><style>{style}</style></head><body>
<h1>Global Market Report 2024</h1><nav>Home About</nav><div class="main">
<table border=1><tr><th>Year</th><th>USD mn</th></tr><tr><td>2024</td><td>820.5</td></tr></table>
<p>The market was valued at USD 820.5 million in 2024, up from 2045 units.</p></div></body></html>"""


def _live_url(td: Path, name: str, style: str = "") -> str:
    p = td / name
    p.write_text(_LIVE_PAGE.format(style=style), encoding="utf-8")
    return p.resolve().as_uri()


@case
def live_capture_does_not_degrade_silently():
    """v9: 실화면 캡처를 코어에 내장하면서 생긴 새 우회로를 막는다 — print 렌더에서 수치를
    못 찾았을 때 **무조건** 화면 캡처로 내려가면 '그 수치가 없는 이미지'가 source_capture 로
    등재된다(백지 캡처·캡처 돌려막기와 같은 계열). 화면 폴백은 텍스트 오라클 자체가 죽었을
    때만 정당하고, 오라클이 살아 있는데 수치가 없으면 fail-closed 여야 한다."""
    import capture_web
    with tempfile.TemporaryDirectory() as _td:
        td = Path(_td)
        cap = td / "_captures"

        # ★ 오라클 생존 + 수치 부재 → 화면 캡처로 강등되지 않는다(out_png 미생성, V04)
        bad = cap / "E900.png"
        r = capture_web.capture_live(_live_url(td, "a.html"), "999999", bad)
        assert not r["ok"], f"수치가 없는데 캡처가 성립했다: {r}"
        assert r.get("capture_mode") != "screen", f"조용한 강등: {r}"
        assert not bad.exists(), "실패인데 정상 캡처 경로에 파일이 생겼다"
        assert not bad.with_name("E900.FAILED.png").exists(), \
            "성공 캡처 옆에 남을 실패 사이드카가 정리되지 않았다"

        # 긍정형 짝 ① 수치가 있으면 print 경로로 통과 + verbatim 이 기계로 확인된다
        ok1 = cap / "E901.png"
        r1 = capture_web.capture_live(_live_url(td, "b.html"), "820.5", ok1)
        assert r1["ok"] and r1["capture_mode"] == "print", r1
        assert r1["capture_verbatim"] == "820.5" and ok1.stat().st_size > 0, r1

        # 긍정형 짝 ② 오라클이 죽은 페이지(print CSS 가 본문 전체를 지움)는 화면 폴백이 정당
        r2 = capture_web.capture_live(
            _live_url(td, "c.html", "@media print{body{display:none}}"), "820.5", cap / "E902.png")
        assert r2["ok"] and r2["capture_mode"] == "screen", r2
        assert r2["capture_verbatim"] is None, "화면 캡처가 기계확인된 것처럼 보고됐다"

        # 부분문자열 오귀속 차단(V15)이 웹 경로에서도 그대로 물린다 — '45'는 2045/820.5 안에만 있다
        e45 = cap / "E903.png"
        assert not capture_web.capture_live(_live_url(td, "d.html"), "45", e45)["ok"]
        assert not e45.exists()

        # 신뢰경계: 실화면↔재구성 발췌는 서로의 출력 경로를 거부한다(양방향)
        for fn, path in ((lambda p: capture_web.capture_live("https://x.invalid", "1", p),
                          td / "_reconstructed" / "x.png"),
                         (lambda p: capture_web.reconstruct_excerpt("t", "https://x.invalid", p),
                          cap / "y.png")):
            try:
                fn(path); assert False, f"신뢰경계 위반 경로가 통과됨: {path}"
            except ValueError:
                pass


@case
def capture_mode_weak_path_surfaced():
    """v9: print 모드(텍스트레이어로 verbatim 기계확인)와 screen 모드(육안뿐)는 증거 강도가
    다르다. 차이를 기록만 하고 검사에 반영하지 않으면 조용한 강등이므로 WARN 으로 표면화하고,
    print 을 '주장'만 하는 것으로 경고를 지울 수 없어야 한다(포징 유인 차단)."""
    w = verify_facts._capture_mode_warnings
    assert w({"id": "E1", "capture_mode": "screen"}), "화면 캡처가 무경고로 통과"
    assert "육안" in w({"id": "E1", "capture_mode": "screen"})[0]
    assert w({"id": "E2", "capture_mode": "print"}), "verbatim 없는 print 주장이 무경고로 통과"
    # 긍정형 짝: 기계확인 산출물이 실제로 있으면 경고 없음 / 모드 미기재도 경고 없음(소급 차단 안 함)
    assert not w({"id": "E3", "capture_mode": "print", "capture_verbatim": "820.5"})
    assert not w({"id": "E4"})

    # 배선 확인 — 헬퍼만 있고 검사 경로에 안 붙어 있으면 방어가 0
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        rows = db.evidence()
        rows[0]["capture_mode"] = "screen"
        _write_jsonl_atomic(wp.evidence, rows)
        ev = {e["id"]: e for e in db.evidence()}
        assert any("[캡처약결박]" in x for x in verify_facts.check_capture_structure(ev, wp)), \
            "check_capture_structure 에 배선되지 않음"


@case
def evidence_hash_unbound_without_snapshot():
    """v6/EV-1: local 스냅샷이 없으면 sha256 은 대조 대상이 없어 아무 64자 hex 나 통과한다.
    원문을 열지 않고 만든 evidence 가 A등급 1차출처로 인쇄되던 경로를 검증 쪽에서 닫는다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _real_png(wp.captures / "F001.png")
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart.example/없는문서",   # 열어본 적 없는 URL
                         "sha256": hashlib.sha256("지어낸 값".encode()).hexdigest(),
                         "capture": "_captures/F001.png"})
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")
        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n",
                                      encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"], rep
        assert any("해시미결박" in f for f in rep["failures"]), rep["failures"]
        assert any("재검증미결박" in f for f in rep["failures"]), rep["failures"]

    # 긍정형 짝: 실파일 스냅샷 + evidence_id 결박이면 통과(정상 경로를 막지 않는다)
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n",
                                      encoding="utf-8")
        assert verify_facts.verify(wp.root / "r.md", wd)["ok"], "정상 결박이 막힘"


@case
def capture_reuse_and_swap_blocked():
    """v6/EV-2·EV-3: 캡처 1장을 여러 fact 의 증빙으로 돌려막기 + 등재 후 이미지 교체 검출."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        db.add_fact({"claim": "시장 45조", "risk": "normal", "status": "pending",
                     "context": {"metric": "market_size", "entity": "수소", "geography": "KR",
                                 "period": "2030"},
                     "value": {"raw": "45", "unit": "KRW_T"},
                     "grade": {"authority": "B", "independence": "B", "directness": "B",
                               "recency": "B"}})
        _confirm(db, wp, "F001")
        # F002 가 F001 의 캡처를 그대로 재사용(복제) — 실제 수치가 찍힌 캡처는 1장뿐
        raw = (wp.captures / "F001.png").read_bytes()
        (wp.captures / "F002.png").write_bytes(raw)
        local, sha = _snapshot(wp, "F002")
        ev2 = db.add_evidence({"fact_id": "F002", "type": "table_cell",
                               "source_url": "https://other.example/x", "sha256": sha,
                               "local": local, "capture": "_captures/F002.png",
                               "capture_sha256": hashlib.sha256(raw).hexdigest()})
        db.add_verify_event("F002", "lead", "reread", evidence_id=ev2["id"])
        db.set_status("F002", "confirmed")
        (wp.root / "r.md").write_text(
            "매출은 300.9조원(F001), 시장은 45조원(F002).\n\n![c](_captures/F001.png)\n",
            encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("캡처재사용" in f for f in rep["failures"]), rep["failures"]

    # 등재 후 캡처 교체(파일만 바꿔치기) → capture_sha256 불일치로 검출
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        _real_png(wp.captures / "F001.png", text="전혀 다른 화면")     # 사후 교체
        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n",
                                      encoding="utf-8")
        rep2 = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep2["ok"] and any("캡처해시" in f for f in rep2["failures"]), rep2["failures"]


@case
def verify_event_time_order_enforced():
    """v6/EV-5: '재검증'이 증거 확보보다 먼저 기록된 대장은 재열람이 성립하지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        rows = db.facts()
        rows[0]["verify_events"][0]["at"] = "2000-01-01T00:00:00"      # 증거보다 과거로 조작
        _write_jsonl_atomic(wp.facts, rows)
        (wp.root / "r.md").write_text("매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n",
                                      encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("재검증시각" in f for f in rep["failures"]), rep["failures"]

    # 남의 fact 증거를 재검증 대상으로 지목하는 것은 등재 시점에 거부된다
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        ev = _confirm(db, wp, "F001")
        db.add_fact({"claim": "시장 45조", "risk": "normal", "status": "pending",
                     "context": {"metric": "market_size", "entity": "수소", "geography": "KR",
                                 "period": "2030"},
                     "value": {"raw": "45", "unit": "KRW_T"},
                     "grade": {"authority": "B", "independence": "B", "directness": "B",
                               "recency": "B"}})
        try:
            db.add_verify_event("F002", "lead", "reread", evidence_id=ev["id"])
            raise AssertionError("남의 증거를 가리키는 재검증이 통과됨")
        except ValidationError:
            pass


@case
def appendix_marker_at_top_blocked():
    """v5: 문서 맨 앞 마커 한 줄로 본문 전체를 검사 면제시키는 우회 → 최후 출현 규칙으로 차단.
    긍정형 짝: 마커가 실제 부록 앞(정상 위치)이면 종전대로 통과."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        md = ("<!-- FACTSHEET:APPENDIX -->\n본론\n시장은 45조원 규모다.\n"
              "매출은 300.9조원이다.\n")
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("부록경계" in f for f in rep["failures"]), rep

        # 서론만 남기고 마커를 앞당겨 표준 챕터를 통째로 부록에 넣는 형태도 구조로 검출
        mid = ("# 부 0. 서론\n요약 문장.\n<!-- FACTSHEET:APPENDIX -->\n"
               "# 부 3. 조사 결과\n시장은 45조원 규모다.\n")
        (wp.root / "m.md").write_text(mid, encoding="utf-8")
        rep_mid = verify_facts.verify(wp.root / "m.md", wd)
        assert not rep_mid["ok"] and any("부록경계" in f for f in rep_mid["failures"]), rep_mid

        _confirm(db, wp, "F001")
        good = ("본론 정상 서술.\n\n![증빙](_captures/F001.png)\n"
                "<!-- FACTSHEET:APPENDIX -->\n## 부록\n- 소스: 사내(F001)\n")
        (wp.root / "g.md").write_text(good, encoding="utf-8")
        assert verify_facts.verify(wp.root / "g.md", wd)["ok"], "정상 부록 마커가 막힘"


@case
def appendix_marker_multiplied_or_leaky():
    """v5: 마커 2개로 중간 구간을 은닉하는 우회 + 부록에 남은 플레이스홀더·비밀 잔존 검출."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        two = ("본론.\n\n![증빙](_captures/F001.png)\n<!-- FACTSHEET:APPENDIX -->\n"
               "숨긴 구간: 시장은 45조원 규모다.\n<!-- FACTSHEET:APPENDIX -->\n## 부록\n- 소스(F001)\n")
        (wp.root / "two.md").write_text(two, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "two.md", wd)
        assert not rep["ok"] and any("부록경계" in f for f in rep["failures"]), rep

        leak = ("본론.\n\n![증빙](_captures/F001.png)\n<!-- FACTSHEET:APPENDIX -->\n"
                "## 부록\n- 소스(F001)\n- 확인필요: " + "TO" + "DO 수치 보강\n")
        (wp.root / "leak.md").write_text(leak, encoding="utf-8")
        rep2 = verify_facts.verify(wp.root / "leak.md", wd)
        assert not rep2["ok"] and any("플레이스홀더" in f for f in rep2["failures"]), rep2


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


@case
def claim_graph_requirements_enforced():
    """v8: risk=high confirmed fact 가 **본문에 인용되면** claim-graph 긍정 요건(독립그룹≥2·
    반박검색·기본소스·시간증거) 미달은 FAIL. 종전에는 warning 이라 고위험 수치가 요건을 한
    번도 안 거치고 인쇄될 수 있었다(승격을 막던 '실전 대장이 통째로 막힌다'는 사유는 그
    대장이 테스트 샘플임이 확인돼 소멸). 긍정형 짝: 요건을 채우면 통과."""
    md = "매출은 300.9조원(F001).\n\n![c](_captures/F001.png)\n"
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)          # F001 risk=high
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001", claim_graph=False)               # 요건 미충족 상태로 확정
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"] and any("반박게이트" in f for f in rep["failures"]), rep

        # 요건별로 하나씩 빠져도 각각 잡히는지(한 요건이 다른 요건을 가리지 않게)
        base = {"independent_groups": ["dart", "irstatement"],
                "counter_search": {"query": "q", "result": "없음",
                                   "found_stronger_refutation": False},
                "primary_source_ref": "E001", "observed_at": "2026-07-22"}
        for drop, token in [("counter_search", "반박검색"), ("primary_source_ref", "기본소스"),
                            ("observed_at", "시간증거")]:
            rows = db.facts()
            fr = next(r for r in rows if r["id"] == "F001")
            fr.update({**base, drop: None})
            _write_jsonl_atomic(wp.facts, rows)
            r = verify_facts.verify(wp.root / "r.md", wd)
            assert not r["ok"] and any(token in f for f in r["failures"]), (drop, r["failures"])

    # 긍정형 짝 ①: 네 요건을 다 채우면 통과
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001")
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        assert verify_facts.verify(wp.root / "r.md", wd)["ok"], "정당한 확정이 막힘"

    # 긍정형 짝 ②: 독립 관찰이 1개뿐이어도 1차출처를 직접 인용하면 대체 충족(WARN 으로만)
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        ev = _confirm(db, wp, "F001")
        rows = db.facts()
        fr = next(r for r in rows if r["id"] == "F001")
        fr["independent_groups"] = ["dart"]                       # 관찰그룹 1개
        fr["primary_source_ref"] = ev["id"]                       # source_role=원출처
        _write_jsonl_atomic(wp.facts, rows)
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert rep["ok"], rep["failures"]
        assert any("대체 충족" in w for w in rep["warnings"]), rep["warnings"]

    # 본문에 안 쓰인 fact 는 FAIL 이 아니라 WARN(게이트가 지키는 것은 인쇄되는 수치다)
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        _confirm(db, wp, "F001", claim_graph=False)
        (wp.root / "r.md").write_text("서술만 있고 태그 없음.\n\n![c](_captures/F001.png)\n",
                                      encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not any("반박게이트" in f for f in rep["failures"]), rep["failures"]
        assert any("반박게이트" in w and "미사용" in w for w in rep["warnings"]), rep["warnings"]


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


# --- v4 흡수(gajae-absorption) 케이스 -----------------------------------------
@case
def v4_schema_fields_enforced():
    """[v4] additive 필드(dispute_kind·derivation·superseded_by·evidence.verdict) 위반 검출."""
    from facts_db import validate_evidence
    s = load_schema()
    base = {"claim_key": "k", "id": "F001", "claim": "c",
            "context": {"metric": "m", "entity": "e", "geography": "g", "period": "p"},
            "value": {"raw": "1", "unit": "u"},
            "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"},
            "risk": "high", "status": "pending"}
    validate_fact(dict(base, dispute_kind="refuted", derivation="computed", superseded_by="F002"), s)
    for bad in ({"dispute_kind": "bogus"}, {"derivation": "magic"}, {"superseded_by": "X01"}):
        try:
            validate_fact(dict(base, **bad), s); raise AssertionError(f"v4 필드 위반 통과: {bad}")
        except ValidationError:
            pass
    ev = {"id": "E001", "fact_id": "F001", "type": "text_quote", "source_url": "https://x",
          "sha256": _H, "accessed_at": "2026", "verbatim": "q"}
    validate_evidence(dict(ev, verdict="contradict"), s)
    try:
        validate_evidence(dict(ev, verdict="maybe"), s); raise AssertionError("evidence.verdict 위반 통과")
    except ValidationError:
        pass


@case
def placeholder_and_secret_in_body_fail():
    """[v4-Q] 플레이스홀더·비밀/내부경로가 본문에 잔존하면 FAIL."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        md = ("보고서 " + "TO" + "DO" + " 정리 필요.\n"
              "로그: C:\\Users\\someone\\work\\a.log 참조.\n")
        (wp.root / "r.md").write_text(md, encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert not rep["ok"], rep
        assert any("플레이스홀더" in f for f in rep["failures"]), rep["failures"]
        assert any("비밀유출" in f for f in rep["failures"]), rep["failures"]


@case
def hedge_without_tag_warns():
    """[v4-Q] F태그 없는 추정 서술은 WARN, 태그 동반이면 비대상."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        (wp.root / "r.md").write_text("시장은 확대될 것으로 보인다.\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert any("무근거헤지" in w for w in rep["warnings"]), rep["warnings"]
        (wp.root / "r2.md").write_text("성장세로 추정된다(F001).\n", encoding="utf-8")
        rep2 = verify_facts.verify(wp.root / "r2.md", wd)
        assert not any("무근거헤지" in w for w in rep2["warnings"]), rep2["warnings"]


@case
def capture_structure_tiny_warns():
    """[v4-Q] 존재하지만 바이트 하한 미달인 캡처는 [캡처구조] WARN(존재 검사와 분리)."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        db.add_evidence({"fact_id": "F001", "type": "table_cell", "source_url": "https://dart",
                         "sha256": _H, "capture": "_captures/E001.png"})
        wp = WorkPaths(wd)
        (wp.root / "_captures").mkdir(parents=True, exist_ok=True)
        (wp.root / "_captures" / "E001.png").write_bytes(b"\x89PNG\r\n")   # 6B — 하한 미달
        (wp.root / "r.md").write_text("본문 없음.\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd)
        assert any("캡처구조" in w for w in rep["warnings"]), rep["warnings"]


@case
def min_confirmed_floor_message():
    """[v4-Q] --min-confirmed 정량 하한 — 미달 시 요구/실측 카운트를 담은 실패."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        (wp.root / "r.md").write_text("본문 없음.\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd, min_confirmed=5)
        assert any("requires at least 5" in f and "current: 0" in f
                   for f in rep["failures"]), rep["failures"]


@case
def cited_domains_missing_warns():
    """[v4-S] 대상 스펙의 기대 1차출처 도메인이 대장에 전무하면 [기대출처] WARN."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        spec = wp.root / "audit" / "target-spec.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"targets": [{"name": "삼성", "cited_domains": ["dart.fss.or.kr"]}]},
                                   ensure_ascii=False), encoding="utf-8")
        (wp.root / "r.md").write_text("본문 없음.\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd, target_spec=spec)
        assert any("기대출처" in w and "dart.fss.or.kr" in w for w in rep["warnings"]), rep["warnings"]


@case
def out_of_scope_term_warns():
    """[v4-Q] 확정 범위 밖(out_of_scope) 용어가 F태그 사실주장 세그먼트에 등장하면 [축외침범] WARN."""
    with tempfile.TemporaryDirectory() as td:
        wd, db = _base_db(td)
        wp = WorkPaths(wd)
        spec = wp.root / "audit" / "target-spec.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"out_of_scope": ["수소차"]}, ensure_ascii=False), encoding="utf-8")
        (wp.root / "r.md").write_text("수소차 매출 300.9조원(F001) 이다.\n", encoding="utf-8")
        rep = verify_facts.verify(wp.root / "r.md", wd, target_spec=spec)
        assert any("축외침범" in w for w in rep["warnings"]), rep["warnings"]


@case
def audit_artifact_roster_parity():
    """[v4-L/R] audit 산출물 로스터(고정 표면) — run_ledger 상수와 report-format.md 문서 정합."""
    import run_ledger
    doc = (REFERENCES / "report-format.md").read_text(encoding="utf-8")
    for name in run_ledger.ROSTER_REQUIRED + run_ledger.ROSTER_OPTIONAL:
        assert name in doc, f"report-format.md audit 로스터에 {name} 누락"
    assert "이벤트성 대장 신설 금지" in doc, "로스터 고정 표면 선언 누락"
    for legacy in run_ledger.ROSTER_LEGACY:
        assert legacy not in doc.replace("run-ledger.jsonl", ""), \
            f"금지된 이벤트성 대장 {legacy} 가 문서에 재등장"


@case
def gates_enum_parity():
    """[v4-L] assets/gates.json 11종이 SKILL.md·verification-gates.md 와 정합."""
    gates = json.loads((SKILL_ROOT / "assets" / "gates.json").read_text(encoding="utf-8"))["gates"]
    ids = [g["id"] for g in gates]
    assert ids == ["G0", "PLAN", "G1", "LV", "BX", "G2", "G3", "G5C", "RENDER", "G4", "G5"], ids
    assert [g["order"] for g in gates] == list(range(11)), "order 불연속"
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    vg = (REFERENCES / "verification-gates.md").read_text(encoding="utf-8")
    for gid in ids:
        assert gid in skill, f"SKILL.md 에 게이트 {gid} 언급 없음"
        assert gid in vg, f"verification-gates.md 에 게이트 {gid} 언급 없음"


@case
def completion_rule_parity():
    """[v4-L] 완료 선언 규칙 문구가 SKILL.md·verification-gates.md 양쪽에 존재."""
    rule = "진행기억·산문선언은증거가아니다"      # 공백·개행 제거 후 대조(줄바꿈 무관)
    skill = re.sub(r"\s+", "", (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8"))
    vg = re.sub(r"\s+", "", (REFERENCES / "verification-gates.md").read_text(encoding="utf-8"))
    assert rule in skill and "run_ledger.py" in skill, "SKILL.md 완료 선언 규칙 누락"
    assert rule in vg, "verification-gates.md 완료 선언 규칙 누락"


@case
def lane_contract_parity():
    """[v4-W/C] 레인 계약·리뷰어 verdict·restate 앵커가 문서 간 정합."""
    briefs = (REFERENCES / "agent-briefs.md").read_text(encoding="utf-8")
    plan = (REFERENCES / "research-plan.md").read_text(encoding="utf-8")
    for anchor in ("### Lane", "## RECEIPT", "## BLOCKERS", "# Research brief (authoritative)",
                   "human_blocked", "VERDICT:"):
        assert anchor in briefs, f"agent-briefs.md 에 {anchor!r} 누락"
    for anchor in ("PLANNING-STUCK", "restated_goal", "반례 쿼리", "consent"):
        assert anchor in plan, f"research-plan.md 에 {anchor!r} 누락"


@case
def v5_doc_code_parity():
    """v5: 새로 만든 방어가 문서(정본)와 코드 양쪽에 같이 존재하는지 — 한쪽만 바뀌면 거짓 안내."""
    import run_ledger as _rl
    import search as _search
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    vg = (REFERENCES / "verification-gates.md").read_text(encoding="utf-8")
    rf = (REFERENCES / "report-format.md").read_text(encoding="utf-8")
    sl = (REFERENCES / "source-ladder.md").read_text(encoding="utf-8")

    # ① 산출물 부재 = 미완료
    assert "missing_watch" in skill and "missing_watch" in vg, "완료 fail-closed 규칙 문서 누락"
    assert _rl.MISSING and _rl._completion_possible({}, ["bx-report.md"]) is False, \
        "로스터 누락인데 완료 가능으로 판정"    # 동작 검증(상태머신 상세는 test_run_ledger)
    # ② 동의 기록의 한계 명문화 — 반쯤 구현하고 '막았다'고 쓰면 그게 순증 위험이다
    assert "인증이 아니다" in vg, "동의 기록 한계 명문화 누락"
    # ③ 부록 경계 건전성
    assert "[부록경계]" in rf, "report-format.md 부록 경계 규칙 누락"
    assert hasattr(verify_facts, "check_appendix_boundary")
    # ④ 수집 스택 v5 보강
    for anchor in ("feed item mismatch", "MOJIBAKE_MAX", "snapshot_date", "blocked_engines"):
        assert anchor in sl, f"source-ladder.md 에 {anchor!r} 누락"
    assert hasattr(fetch, "mime_allowed") and hasattr(fetch, "_feed_item_verdict")
    assert hasattr(_search, "search_with_diagnostics")
    assert _search._BLOCK_MARKERS, "차단 마커가 assets 에서 로드되지 않음"
    # ⑤ 중복 수집의 정규 출구가 실재해야 한다(안내만 하고 함수가 없던 것이 v5 이전 상태)
    assert "merge_evidence" in vg, "verification-gates.md 병합 경로 안내 누락"
    from facts_db import FactsDB as _FDB
    assert callable(getattr(_FDB, "merge_evidence", None)), "merge_evidence 미구현"

    # ⑥ v6 증거 결박 — 문서의 실패 태그가 실제로 코드에서 나는 것과 같아야 한다
    ec = (REFERENCES / "evidence-capture.md").read_text(encoding="utf-8")
    for tag in ("[해시미결박]", "[캡처해시]", "[캡처재사용]", "[재검증미결박]", "[재검증시각]"):
        assert tag in ec, f"evidence-capture.md 에 {tag} 규칙 누락"
    assert hasattr(verify_facts, "check_capture_binding")
    assert "capture_sha256" in json.loads(
        (SKILL_ROOT / "assets" / "facts-schema.json").read_text(encoding="utf-8")
    )["evidence"]["properties"], "스키마에 capture_sha256 없음"
    # 임계는 실측 근거와 함께 코드에 있어야 한다(추정 임계 재도입 방지)
    assert capture_pdf.BLANK_MAX_COLORS == 2 and capture_pdf.BLANK_MAX_INK == 0.0005

    # ⑦ v7 — 레거시 완화가 문서·코드 어디에도 되살아나 있지 않아야 한다
    rl_src = (SKILL_ROOT / "scripts" / "run_ledger.py").read_text(encoding="utf-8")
    assert "폐지" in vg and "floor(d)" in vg, "verification-gates.md 에 floor 규칙 갱신 누락"
    assert "migration_required:" not in rl_src, "레거시 완화 코드가 되살아남"
    assert "폐지" in skill, "SKILL.md 에 완화 폐지 사실 누락"
    assert hasattr(_rl, "_stale_reverify_scan") and hasattr(_rl, "_ledger_lock")

    # ⑧ v8 — [Bx] 승격이 문서·코드 양쪽에 있고, 대체 충족 예외가 규칙으로 적혀 있어야 한다
    for doc, name in ((skill, "SKILL.md"), (vg, "verification-gates.md")):
        assert "원출처" in doc and "FAIL" in doc, f"{name} 에 [Bx] 승격/예외 규칙 누락"
    assert hasattr(verify_facts, "_cites_primary"), "1차출처 대체 충족 판정 함수 없음"

    # ⑨ v9 — 실화면 캡처가 코어에 내장됐고(MCP 미연결에도 증빙 가능), 등급 차이가 기록된다
    import capture_web as _cw
    assert hasattr(_cw, "capture_live") and hasattr(_cw, "_host_rules")
    assert hasattr(verify_facts, "_capture_mode_warnings")
    props = json.loads((SKILL_ROOT / "assets" / "facts-schema.json")
                       .read_text(encoding="utf-8"))["evidence"]["properties"]
    for f in ("capture_mode", "capture_verbatim"):
        assert f in props, f"스키마에 {f} 없음"
    for doc, name in ((skill, "SKILL.md"), (ec, "evidence-capture.md")):
        assert "capture_live" in doc, f"{name} 에 실화면 캡처 내장 규칙 누락"
    assert "[캡처약결박]" in ec, "evidence-capture.md 에 경로 강도 WARN 태그 누락"
    # 임계는 실측 근거와 함께 코드에 있어야 한다(v6 백지 임계와 같은 규율)
    assert _cw.TEXT_ORACLE_MIN == 1, "텍스트 오라클 임계가 실측 근거 없이 바뀜"


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
