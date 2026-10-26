"""RF2 브라우저 계층. 네트워크·외부 사이트 없이 사다리와 요청 검사만 본다."""
import ipaddress
import socket
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch

PUBLIC_IP = "93.184.216.34"
SCRIPTED = (
    "<html><body><div id='app'></div><script>"
    "document.getElementById('app').textContent='스크립트가 그린 본문';"
    "</script></body></html>"
)


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = socket.getaddrinfo

    def resolve(host, *args, **kwargs):
        text = str(host).strip("[]")
        if text in ("localhost", "127.0.0.1", "::1"):
            return original(host, *args, **kwargs)
        try:
            ipaddress.ip_address(text)
        except ValueError:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 0))]
        return original(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(fetch, "trafilatura", None)


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


class FakeRoute:
    def __init__(self, url, resource_type="document"):
        self.request = SimpleNamespace(url=url, resource_type=resource_type, frame=None)
        self.action = None

    def abort(self):
        self.action = "abort"

    def continue_(self):
        self.action = "continue"


def _client(status=403, body=b"no"):
    urls = []

    def get(url, **kwargs):
        urls.append(url)
        return Response(status, body, {"content-type": "text/html"})

    return urls, SimpleNamespace(get=get)


def _long_html() -> str:
    return ("<html><head><title>본문</title></head><body><article><p>"
            + ("가나다 " * 300) + "</p></article></body></html>")


def test_browser_runs_after_direct_and_mobile_and_stops(monkeypatch):
    urls, client = _client()
    monkeypatch.setattr(fetch, "creq", client)
    seen = []

    def via(url):
        seen.append(url)
        return {"ok": True, "status": 200, "text": _long_html(), "final_url": url,
                "mime": "text/html"}

    monkeypatch.setattr(fetch, "_via_browser", via)
    result = fetch.fetch("https://origin.test/app")
    assert seen == ["https://origin.test/app"]
    assert result["status"] == "ok" and result["note"] == "browser", result
    labels = [item.get("tier") for item in result["trace"]]
    assert any(str(label).startswith("curl_cffi:") for label in labels)
    assert "mobile" in labels and labels[-1] == "browser"
    assert not any("r.jina.ai" in url for url in urls)


def test_browser_env_off_does_not_call(monkeypatch):
    urls, client = _client()
    monkeypatch.setattr(fetch, "creq", client)
    monkeypatch.setenv("MDR_BROWSER", "0")
    seen = []
    monkeypatch.setattr(fetch, "_via_browser", lambda url: seen.append(url))
    result = fetch.fetch("https://origin.test/app")
    assert seen == []
    assert any(item.get("tier") == "browser" and item.get("skip") == "MDR_BROWSER=0"
               for item in result["trace"])
    assert any("r.jina.ai" in url for url in urls)
    assert "MDR_BROWSER=0" in result["hint"]


def test_missing_engine_skips_to_next_tier(monkeypatch):
    urls, client = _client()
    monkeypatch.setattr(fetch, "creq", client)
    monkeypatch.setattr(fetch, "_browser_engines", lambda: [])
    result = fetch.fetch("https://origin.test/app")
    browser = [item for item in result["trace"] if item.get("tier") == "browser"]
    assert browser and str(browser[0].get("fail", "")).startswith("skip:"), browser
    assert any("r.jina.ai" in url for url in urls)
    assert "브라우저 계층" in result["hint"]
    assert "MDR_BROWSER=0" not in result["hint"]


def test_direct_404_does_not_call_browser(monkeypatch):
    urls, client = _client(status=404, body=b"gone")
    monkeypatch.setattr(fetch, "creq", client)
    seen = []
    monkeypatch.setattr(fetch, "_via_browser", lambda url: seen.append(url))
    result = fetch.fetch("https://origin.test/gone")
    assert seen == []
    assert any(item.get("tier") == "browser" and item.get("skip") == "direct-404"
               for item in result["trace"])
    assert not any("r.jina.ai" in url for url in urls)


def test_route_aborts_private_and_continues_public():
    blocked = [
        "http://127.0.0.1/",
        "http://169.254.169.254/",
        "file:///etc/passwd",
    ]
    for url in blocked:
        route = FakeRoute(url)
        fetch._guard_browser_route(route)
        assert route.action == "abort", url
    public = FakeRoute("https://93.184.216.34/a")
    fetch._guard_browser_route(public)
    assert public.action == "continue"
    for kind in ("image", "font", "media"):
        route = FakeRoute("https://93.184.216.34/x", kind)
        fetch._guard_browser_route(route)
        assert route.action == "abort", kind


def test_scripted_body_is_in_rendered_html():
    engines = fetch._browser_engines()
    if not engines:
        pytest.skip("browser 엔진 없음")
    last = None
    for sync_playwright, _name in engines:
        try:
            with sync_playwright() as pw:
                browser = fetch._launch_chromium(pw)
                context = browser.new_context(accept_downloads=False)
                page = context.new_page()
                page.set_content(SCRIPTED, wait_until="domcontentloaded")
                text = fetch._read_rendered_page(page)
                context.close()
                browser.close()
        except Exception as exc:
            if fetch._is_missing_browser(exc):
                last = exc
                continue
            raise
        assert "스크립트가 그린 본문" in text
        return
    pytest.skip(f"browser 실행 파일 없음: {last}")
