"""RF1 fetch 열람 판정. 네트워크 없음."""
import json
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch

PUBLIC_IP = "93.184.216.34"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = socket.getaddrinfo

    def resolve(host, *args, **kwargs):
        if host in ("localhost", "127.0.0.1", "::1", PUBLIC_IP):
            return original(host, *args, **kwargs)
        if str(host).endswith(".test"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 0))]
        raise AssertionError(f"테스트 외부 DNS 금지: {host}")

    monkeypatch.setattr(socket, "getaddrinfo", resolve)


class Response:
    def __init__(self, status=200, body=b"", headers=None, ip=PUBLIC_IP):
        self.status_code = status
        self.headers = headers or {"content-type": "text/html"}
        self.primary_ip = ip
        self.body = body
        self.closed = False

    def iter_content(self, chunk_size):
        for start in range(0, len(self.body), chunk_size):
            yield self.body[start:start + chunk_size]

    def close(self):
        self.closed = True


class Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


def _article(body: str, title: str = "국내 시장 동향") -> str:
    return (f"<html><head><title>{title}</title></head>"
            f"<body><article><p>{body}</p></article></body></html>")


def _pad(phrase: str, n: int) -> str:
    filler = "시장 문장입니다. "
    text = phrase
    while len(text) < n:
        text += filler
    return text


def test_suspect_titles_are_partial(monkeypatch):
    """제목이 차단 문구 자체이거나 본문이 차단 구절일 때만. 본문은 1000자 미만."""
    monkeypatch.setattr(fetch, "trafilatura", None)
    short = "안내 " * 30
    pages = {
        "not_found": ("페이지를 찾을 수 없습니다", short),
        "login": ("로그인", short),
        "access_denied": ("Access Denied", short),
        "consent": ("안내", "쿠키 사용에 동의해야 계속할 수 있습니다. " + short),
    }
    for kind, (title, body) in pages.items():
        html = _article(body, title)
        assert len(fetch.extract_text(html)) < 1000
        verdict = fetch.validate_body(html, 200)
        assert verdict["verdict"] == "partial", verdict
        assert verdict["reason"] == f"suspect:{kind}", verdict


def test_common_words_in_articles_stay_ok(monkeypatch):
    """한 단어(동의·404·쿠키·로그인·삭제된)가 기사에 있어도 차단 구절이 아니면 ok."""
    monkeypatch.setattr(fetch, "trafilatura", None)
    cases = [
        (_pad("합병안에 동의했다. ", 1300), "국내 시장 동향"),
        (_pad("매출은 1,404억 원. ", 1300), "국내 시장 동향"),
        (_pad("서드파티 쿠키 폐지. ", 1300), "국내 시장 동향"),
        (_pad("시장 문장입니다. ", 4200), "쿠키 없는 광고 시장 전망"),
        (_pad("시장 문장입니다. ", 4200), "국회, 합병 동의안 통과"),
        (_pad("시장 문장입니다. ", 4200), "간편 로그인 시장 점유율"),
        (_pad("시장 문장입니다. ", 1300), "삭제된 영상 논란"),
    ]
    for body, title in cases:
        html = _article(body, title)
        assert len(fetch.extract_text(html)) >= 1000
        verdict = fetch.validate_body(html, 200)
        assert verdict["verdict"] == "ok", (title, verdict)


def test_block_page_phrases_are_partial(monkeypatch):
    monkeypatch.setattr(fetch, "trafilatura", None)
    login_body = "로그인이 필요한 서비스입니다. " + ("안내 " * 25)
    assert 80 <= len(login_body) <= 160
    cases = [
        (_article(login_body, "로그인 - 사이트"), "login"),
        (_article("없는 주소입니다.", "404 Not Found"), "not_found"),
        (_article("없는 주소입니다.", "Sign in · Example"), "login"),
        (_article("요청하신 페이지를 찾을 수 없습니다.", "안내"), "not_found"),
    ]
    for html, kind in cases:
        assert len(fetch.extract_text(html)) < 1000
        verdict = fetch.validate_body(html, 200)
        assert verdict["verdict"] == "partial", verdict
        assert verdict["reason"] == f"suspect:{kind}", verdict


def test_title_contains_word_but_short_body_is_not_suspect(monkeypatch):
    """제목 한가운데의 로그인·쿠키·삭제된 만으로는 걸지 않는다. 짧으면 thin partial 일 수 있다."""
    monkeypatch.setattr(fetch, "trafilatura", None)
    body = "시장 문장입니다. " * 12
    for title in ("간편 로그인 시장 점유율", "쿠키 없는 광고 시장 전망",
                  "삭제된 영상 논란", "회원 로그인", "국회, 합병 동의안 통과"):
        html = _article(body, title)
        assert len(fetch.extract_text(html)) < 1000
        verdict = fetch.validate_body(html, 200)
        assert not str(verdict["reason"]).startswith("suspect:"), (title, verdict)


def test_login_quote_inside_long_article_stays_ok(monkeypatch):
    monkeypatch.setattr(fetch, "trafilatura", None)
    sentence = "시장 조사 본문은 로그인 화면을 인용해도 기사 자체다. "
    assert len(sentence) * 120 >= 3000
    html = ("<html><head><title>국내 시장 동향</title></head><body><article><p>"
            + sentence * 120 + "</p></article></body></html>")
    verdict = fetch.validate_body(html, 200)
    assert verdict["verdict"] == "ok", verdict


def test_script_style_shell_is_not_ok(monkeypatch):
    monkeypatch.setattr(fetch, "trafilatura", None)
    script = "var token = 'abcdefghij';" * 80
    style = "body{display:none}" * 80
    assert len(script) + len(style) > 1000
    html = (f"<html><head><style>{style}</style><script>{script}</script></head>"
            "<body><div id='app'></div></body></html>")
    verdict = fetch.validate_body(html, 200)
    assert verdict["verdict"] != "ok", verdict


def test_meta_charset_decodes_euc_kr_when_header_has_none():
    korean = "삼성전자 시장"
    page = ("<html><head><meta charset=\"euc-kr\"></head><body>"
            + korean + "</body></html>").encode("euc-kr")
    text = fetch.response_text({"headers": {"content-type": "text/html"}, "raw": page})
    assert korean in text and "\ufffd" not in text

    equiv = ('<html><head><meta http-equiv="Content-Type" '
             'content="text/html; charset=euc-kr"></head><body>'
             + korean + "</body></html>").encode("euc-kr")
    text = fetch.response_text({"headers": {"content-type": "text/html"}, "raw": equiv})
    assert korean in text and "\ufffd" not in text

    # 헤더 charset 이 있으면 meta 보다 우선한다.
    utf8 = "<html><head><meta charset=\"euc-kr\"></head><body>안녕</body></html>".encode("utf-8")
    text = fetch.response_text({"headers": {"content-type": "text/html; charset=utf-8"}, "raw": utf8})
    assert "안녕" in text


def test_direct_404_skips_to_wayback(monkeypatch):
    calls = []

    def get(url, **kwargs):
        calls.append(kwargs.get("impersonate"))
        return Response(404, b"gone", {"content-type": "text/html"})

    monkeypatch.setattr(fetch, "creq", SimpleNamespace(get=get))
    seen = []
    real = fetch._candidates

    def wrapped(tier, url):
        seen.append(tier)
        if tier == "wayback":
            yield "wayback", {"ok": False, "status": None, "reason": "no wayback snapshot",
                              "text": "", "final_url": url}
            return
        yield from real(tier, url)

    monkeypatch.setattr(fetch, "_candidates", wrapped)
    result = fetch.fetch("https://origin.test/gone")
    assert seen == ["direct", "wayback"], seen
    assert calls == fetch.IMPERSONATE_GRID
    assert any(item.get("tier") == "mobile" and item.get("skip") == "direct-404"
               for item in result["trace"])
    assert result["status"] == "fail"


def test_unresolved_mobile_host_is_not_logged(monkeypatch):
    def resolve(host, *args, **kwargs):
        if str(host).startswith("m."):
            raise socket.gaierror(8, "not found")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return Response(403, b"no", {"content-type": "text/html"})

    monkeypatch.setattr(fetch, "creq", SimpleNamespace(get=get))
    monkeypatch.setattr(fetch, "_tier_order", lambda url: ["mobile"])
    fetch.fetch("https://origin.test/a")
    assert calls and all("m.origin.test" not in url for url in calls)
    assert any(urlparse(url).hostname == "origin.test" for url in calls)
    log = Path("audit/fetch-log.jsonl").read_text(encoding="utf-8")
    assert "m.origin.test" not in log
    assert "DNS" not in log


def test_hwp_and_xlsx_saved_with_extension(tmp_path, monkeypatch):
    payloads = {
        "/a.hwp": (b"HWP Document File", "application/octet-stream"),
        "/b.xlsx": (b"PK\x03\x04xlsx", XLSX_MIME),
    }

    def get(url, **kwargs):
        path = urlparse(url).path
        body, mime = payloads[path]
        return Response(200, body, {"content-type": mime})

    monkeypatch.setattr(fetch, "creq", SimpleNamespace(get=get))
    expected = {"https://origin.test/a.hwp": "hwp", "https://origin.test/b.xlsx": "xlsx"}
    for url, ext in expected.items():
        result = fetch.fetch(url)
        assert result["status"] == "ok" and result["note"] == ext, result
        assert result["is_pdf"] is False
        saved = fetch.save(result, tmp_path, url=url)
        assert saved["local"].endswith(f"_raw.{ext}")
        meta_path = tmp_path / f"{saved['sha256'][:12]}.meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["raw"].endswith(f".{ext}") and meta["clean"] is None
        assert meta["is_pdf"] is False
        assert (tmp_path / meta["raw"]).read_bytes() == payloads[urlparse(url).path][0]


def test_document_size_cap_is_not_applied_to_html():
    nine = 9 * 1024 * 1024
    over = 41 * 1024 * 1024

    def once(mime, url, length):
        client = Client([Response(200, b"x", {"content-type": mime, "content-length": str(length)})])
        return fetch.request_bytes(url, client=client, doc_cap=True)

    with pytest.raises(fetch.DownloadLimitError):
        once("text/html", "https://origin.test/page.html", nine)
    with pytest.raises(fetch.DownloadLimitError):       # 검색·이미지 호출은 doc_cap 을 켜지 않으므로 8MB 그대로
        fetch.request_bytes("https://origin.test/sheet.xlsx", client=Client(
            [Response(200, b"x", {"content-type": XLSX_MIME, "content-length": str(nine)})]))
    got = once(XLSX_MIME, "https://origin.test/sheet.xlsx", nine)
    assert got["status"] == 200 and got["raw"] == b"x"
    with pytest.raises(fetch.DownloadLimitError):
        once("application/pdf", "https://origin.test/big.pdf", over)
    got = once("application/octet-stream", "https://origin.test/note.hwp", nine)
    assert got["status"] == 200


def test_no_third_party_skips_jina_and_wayback(monkeypatch):
    monkeypatch.setenv("MDR_NO_THIRD_PARTY", "1")
    seen = []

    def candidates(tier, url):
        seen.append(tier)
        yield tier, {"ok": False, "status": 403, "reason": "http 403", "text": "",
                     "final_url": url, "is_pdf": False}

    monkeypatch.setattr(fetch, "_candidates", candidates)
    result = fetch.fetch("https://origin.test/secret")
    assert "jina" not in seen and "wayback" not in seen
    assert "mobile" in seen and "direct" in seen
    skipped = {item["tier"] for item in result["trace"] if item.get("skip") == "no-third-party"}
    assert skipped == {"jina", "wayback"}


def test_direct_429_stops_remaining_profiles(monkeypatch):
    calls = []

    def get(url, **kwargs):
        calls.append(kwargs.get("impersonate"))
        return Response(429, b"slow down", {"content-type": "text/html"})

    monkeypatch.setattr(fetch, "creq", SimpleNamespace(get=get))
    monkeypatch.setattr(fetch, "_tier_order", lambda url: ["direct"])
    fetch.fetch("https://origin.test/limited")
    assert calls == [fetch.IMPERSONATE_GRID[0]]


def test_unsupported_mobile_alias_degrades_to_safari(monkeypatch):
    monkeypatch.setattr(fetch, "MOBILE_IMPERSONATE", "not-a-real-browser")
    calls = []

    class ImpersonateError(OSError):
        pass

    def get(url, **kwargs):
        calls.append(kwargs.get("impersonate"))
        if kwargs.get("impersonate") == "not-a-real-browser":
            raise ImpersonateError("Impersonating not-a-real-browser is not supported")
        body = ("본문입니다. " * 200).encode("utf-8")
        return Response(200, body, {"content-type": "text/html; charset=utf-8"})

    monkeypatch.setattr(fetch, "creq", SimpleNamespace(get=get))
    monkeypatch.setattr(fetch, "_tier_order", lambda url: ["mobile"])
    result = fetch.fetch("https://origin.test/a")
    assert "not-a-real-browser" in calls and "safari" in calls
    assert result["status"] == "ok"


def test_jina_origin_error_is_failure(monkeypatch):
    """Jina 가 죽은 페이지를 200 으로 감싸도 머리말의 원 응답 코드로 실패 처리한다."""
    wrapped = ("Title: Error 404: Oops\n\nURL Source: https://example.com/x.pdf\n\n"
               "Warning: Target URL returned error 404: Not Found\n\nMarkdown Content:\n" + "메뉴 " * 2000)
    monkeypatch.setattr(fetch, "_fetch_once", lambda url, imp, **kw: {
        "ok": True, "status": 200, "text": wrapped, "final_url": url, "mime": "text/plain"})
    res = fetch._via_jina("https://example.com/x.pdf")
    assert res["ok"] is False and res["status"] == 404 and res["reason"] == "http 404"
    live = "Title: 기사\n\nURL Source: https://example.com/a\n\nMarkdown Content:\n" + "본문 " * 2000
    monkeypatch.setattr(fetch, "_fetch_once", lambda url, imp, **kw: {
        "ok": True, "status": 200, "text": live, "final_url": url, "mime": "text/plain"})
    assert fetch._via_jina("https://example.com/a")["ok"] is True


def test_dead_page_title_overrides_long_body():
    """없는 페이지 안내는 메뉴 때문에 길다. 제목이 그 문구로 시작하면 길이와 무관하게 partial."""
    para = "<p>회사 소개와 제품 안내, 고객 지원 메뉴가 이어지는 긴 탐색 영역 문단이다. 분기 실적과 채용 공고도 있다.</p>"
    def page(title):
        return f"<html><head><title>{title}</title></head><body><article>{para * 60}</article></body></html>"
    for title in ("Page not found | Air Liquide", "404 Error | Analog Devices", "HTTP 404: Page Not Found",
                  "페이지를 찾을 수 없습니다 - 국토교통부"):
        verdict = fetch.validate_body(page(title), 200)
        assert verdict == {"verdict": "partial", "reason": "suspect:not_found"}, (title, verdict)
    for title in ("404 Media, 독립 언론의 수익 모델", "Lost and Found 서비스 시장 전망", "간편 로그인 시장 점유율"):
        assert fetch.validate_body(page(title), 200)["verdict"] == "ok", title


def test_dead_title_separators_and_lookalikes():
    """리뷰 지적: 구분자 낀 404 제목은 걸리고, 접두만 같은 정상 제목은 걸리지 않는다."""
    para = "<p>회사 소개와 제품 안내, 고객 지원 메뉴가 이어지는 긴 탐색 영역 문단이다. 분기 실적과 채용 공고도 있다.</p>"

    def verdict(title):
        html = f"<html><head><title>{title}</title></head><body><article>{para * 60}</article></body></html>"
        return fetch.validate_body(html, 200)["verdict"]

    for title in ("404 - Page Not Found", "404 | Not Found", "404: Not Found", "Error: 404 Not Found", "Error - 404"):
        assert verdict(title) == "partial", title
    for title in ("Page Not Founders Summit", "404 Not Founders Club", "페이지를 찾을 수 없는 공공데이터",
                  "Error 4040년 시장", "HTTP 4040 센서", "404억 원 매출 달성"):
        assert verdict(title) == "ok", title


def test_jina_dead_title_and_late_warning(monkeypatch):
    """Jina 각색본은 <title> 이 없다. Title: 줄과, 머리말 뒤쪽에 있는 원 응답 경고를 모두 본다."""
    def wrapped(head):
        return {"ok": True, "status": 200, "text": head + "\n\nMarkdown Content:\n" + "메뉴 " * 2000,
                "final_url": "https://r.jina.ai/x", "mime": "text/plain"}

    cases = {
        "Title: Page not found | Air Liquide\n\nURL Source: https://origin.test/x": False,
        "Title: " + "가" * 1100 + "\n\nWarning: Target URL returned error 404: Not Found": False,
        "Title: 수전해 시장 전망\n\nURL Source: https://origin.test/a": True,
    }
    for head, expected in cases.items():
        monkeypatch.setattr(fetch, "_fetch_once", lambda url, imp, _h=head, **kw: wrapped(_h))
        assert fetch._via_jina("https://origin.test/x")["ok"] is expected, head[:40]
