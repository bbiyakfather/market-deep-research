"""RS: 검색 백엔드 상태, SearXNG 재시도, 자체 호스트, URL 중복 제거. 네트워크 없음."""
import json
import socket
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import search


class _Body:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self, size=-1):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    @property
    def status(self):
        return 200


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.delenv("MDR_SEARX_URL", raising=False)
    monkeypatch.setattr(search.time, "sleep", lambda _delay: None)


def _html_link(url: str, title: str = "제목") -> str:
    from urllib.parse import quote
    href = "//duckduckgo.com/l/?uddg=" + quote(url, safe="") + "&rut=1"
    return f'<a class="result__a" href="{href}">{title}</a>'


def _json_results(*urls: str) -> str:
    return json.dumps({
        "results": [{"title": "t", "url": url, "content": "s"} for url in urls],
    })


def test_ddg_429_is_blocked_and_exit_2(monkeypatch, capsys):
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (429, "no"))
    report = search.search_report("q", n=2)
    assert report["results"] == []
    assert report["backends"][0] == {
        "name": "ddg", "status": "blocked", "count": 0, "detail": "http 429",
    }
    assert all(item["status"] in ("blocked", "error") for item in report["backends"])
    assert search.main(["q", "--n", "2"]) == 2
    assert "backend ddg: blocked (http 429)" in capsys.readouterr().err


def test_ddg_200_captcha_is_blocked(monkeypatch):
    page = "<html><body>anomaly detected. solve the captcha</body></html>"
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (200, page))
    report = search.search_report("q", n=2)
    assert report["backends"][0]["status"] == "blocked"
    assert report["backends"][0]["count"] == 0
    assert report["results"] == []


def test_ddg_200_clean_zero_is_empty_exit_0(monkeypatch, capsys):
    page = "<html><body><p>no matches</p></body></html>"
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (200, page))
    report = search.search_report("q", n=2)
    assert report["backends"][0] == {
        "name": "ddg", "status": "empty", "count": 0, "detail": "http 200",
    }
    assert search.main(["q", "--n", "2"]) == 0
    err = capsys.readouterr().err
    assert "backend ddg: empty (http 200)" in err


def test_ddg_exception_is_error(monkeypatch):
    def boom(url, timeout=12):
        raise TimeoutError("stub timeout")

    monkeypatch.setattr(search, "_get", boom)
    report = search.search_report("q", n=2)
    assert report["results"] == []
    assert report["backends"][0]["status"] == "error"
    assert report["backends"][0]["name"] == "ddg"
    assert "TimeoutError" in report["backends"][0]["detail"]
    assert isinstance(search.search("q", n=2), list)


def test_search_return_type_stays_list(monkeypatch):
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (200, "<html></html>"))
    assert isinstance(search.search("q", n=2), list)
    assert search.search("q", n=2) == search.search_report("q", n=2)["results"]


def test_demo_assertions_still_pass(capsys):
    search.demo()
    assert "search demo OK" in capsys.readouterr().out


def test_searx_429_backoff_and_dns_skips(monkeypatch):
    calls = []
    sleeps = []

    def fake_get(url, timeout=12):
        calls.append(url)
        if "inst-a.example" in url:
            return 429, "rate"
        if "inst-b.example" in url:
            raise socket.gaierror("dns")
        if "inst-c.example" in url:
            return 200, _json_results("https://found.example/a")
        raise AssertionError(url)

    monkeypatch.setattr(search, "_get", fake_get)
    monkeypatch.setattr(search.time, "sleep", lambda delay: sleeps.append(delay))
    monkeypatch.setitem(search._SEARX, "instances", [
        "https://inst-a.example",
        "https://inst-b.example",
        "https://inst-c.example",
    ])
    monkeypatch.setitem(search._SEARX, "backoff_sec", [1, 2, 4])
    results = search._searx("q", 5)
    assert sleeps == [1, 2, 4]
    assert sum("inst-a.example" in url for url in calls) == 4
    assert sum("inst-b.example" in url for url in calls) == 1
    assert sum("inst-c.example" in url for url in calls) == 1
    assert results[0]["url"] == "https://found.example/a"


def test_searx_5xx_retries_and_403_does_not(monkeypatch):
    calls = []
    sleeps = []
    answers = [(503, "down"), (200, _json_results("https://after-retry.example/a"))]

    def fake_get(url, timeout=12):
        calls.append(url)
        return answers.pop(0)

    monkeypatch.setattr(search, "_get", fake_get)
    monkeypatch.setattr(search.time, "sleep", lambda delay: sleeps.append(delay))
    monkeypatch.setitem(search._SEARX, "instances", ["https://only.example"])
    results, state = search._searx_report("q", 3)
    assert sleeps == [1]
    assert len(calls) == 2
    assert results[0]["url"] == "https://after-retry.example/a"
    assert state["status"] == "ok"

    calls.clear()
    sleeps.clear()

    def forbidden(url, timeout=12):
        calls.append(url)
        if "blocked.example" in url:
            return 403, "no"
        return 200, _json_results("https://next.example/b")

    monkeypatch.setattr(search, "_get", forbidden)
    monkeypatch.setitem(search._SEARX, "instances", [
        "https://blocked.example",
        "https://next.example",
    ])
    results = search._searx("q", 3)
    assert sleeps == []
    assert sum("blocked.example" in url for url in calls) == 1
    assert results[0]["url"] == "https://next.example/b"


def test_searx_deadline_stops_further_instances(monkeypatch):
    clock = {"now": 0.0}
    calls = []

    def mono():
        return clock["now"]

    def sleep(delay):
        clock["now"] += delay

    def fake_get(url, timeout=12):
        calls.append(url)
        clock["now"] += 10
        return 429, "rate"

    monkeypatch.setattr(search.time, "monotonic", mono)
    monkeypatch.setattr(search.time, "sleep", sleep)
    monkeypatch.setattr(search, "_get", fake_get)
    monkeypatch.setitem(search._SEARX, "instances", [
        "https://a.example",
        "https://b.example",
        "https://c.example",
    ])
    monkeypatch.setitem(search._SEARX, "backoff_sec", [1, 2, 4])
    _results, state = search._searx_report("q", 3)
    assert calls
    assert all("a.example" in url for url in calls)
    assert state["status"] == "blocked"


def test_mdr_searx_url_uses_urllib_before_public(monkeypatch):
    opened = []
    public = []

    def urlopen(req, timeout=12):
        opened.append(req.full_url)
        if "127.0.0.1" in req.full_url:
            raise urllib.error.URLError("dns")
        return _Body(_json_results("https://ok.example/a").encode("utf-8"))

    def public_get(url, timeout=12):
        public.append(url)
        raise AssertionError("public instance called before trusted URL succeeded")

    monkeypatch.setenv("MDR_SEARX_URL", "http://127.0.0.1:8888, http://10.0.0.2:8888")
    monkeypatch.setattr(search._NO_REDIRECT, "open", urlopen)
    monkeypatch.setattr(search, "_get", public_get)
    results = search._searx("q", 3)
    assert opened[0].startswith("http://127.0.0.1:8888/search?")
    assert opened[1].startswith("http://10.0.0.2:8888/search?")
    assert public == []
    assert results[0]["url"] == "https://ok.example/a"
    assert results[0]["source"].startswith("searx:")


def test_normalize_url_and_merge_keeps_original(monkeypatch):
    left = search._normalize_url("https://Example.COM/a/?utm_source=x&fbclid=1&keep=1#frag")
    right = search._normalize_url("https://example.com/a?gclid=zzz&keep=1")
    assert left == right
    assert search._normalize_url("https://example.com/a/") == search._normalize_url("https://example.com/a")

    ddg_url = "https://Example.COM/a/?utm_source=nl&fbclid=f&keep=1"
    page = _html_link(ddg_url, "원문")

    def fake_get(url, timeout=12):
        if "duckduckgo" in url:
            return 200, page
        return 200, _json_results(
            "https://example.com/a?keep=1&gclid=zzz",
            "https://other.example/b",
        )

    monkeypatch.setattr(search, "_get", fake_get)
    results = search.search("q", n=4)
    assert len(results) == 2
    assert results[0]["url"] == ddg_url
    assert results[0]["source"] == "ddg"
    assert results[1]["url"] == "https://other.example/b"


def test_json_stdout_is_full_report(monkeypatch, capsys):
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (200, "<html></html>"))
    assert search.main(["q", "--json", "--n", "2"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["results"] == []
    assert payload["backends"][0]["status"] == "empty"
    assert "backend ddg:" in captured.err


def test_health_pokes_once_each_without_retry(monkeypatch, capsys):
    calls = []
    sleeps = []

    def fake_get(url, timeout=12):
        calls.append(url)
        if "duckduckgo" in url:
            return 429, ""
        return 200, _json_results()

    monkeypatch.setattr(search, "_get", fake_get)
    monkeypatch.setattr(search.time, "sleep", lambda delay: sleeps.append(delay))
    assert search.health() == 0
    assert sleeps == []
    assert len(calls) == 1 + len(search._SEARX["instances"])
    out = capsys.readouterr().out
    assert "ddg" in out and "blocked" in out


def test_arxiv_sec_wikipedia_status_rules(monkeypatch, capsys):
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (500, "no"))
    report = search.search_report("q", n=2, type="academic")
    assert report["results"] == []
    assert report["backends"][0]["name"] == "arxiv"
    assert report["backends"][0]["status"] == "error"
    assert report["backends"][0]["detail"] == "http 500"

    def boom(url, timeout=12):
        raise OSError("down")

    monkeypatch.setattr(search, "_get", boom)
    report = search.search_report("Tesla", n=2, type="filing")
    assert report["results"] == []
    assert report["backends"][0]["status"] == "error"
    assert "sec_edgar" in capsys.readouterr().err

    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (200, '["q",[],[],[]]'))
    results, state = search._wikipedia_report("q", 3)
    assert results == [] and state["status"] == "empty"
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (403, "no"))
    results, state = search._wikipedia_report("q", 3)
    assert results == [] and state["status"] == "blocked" and state["detail"] == "http 403"


def test_arxiv_empty_feed_is_empty(monkeypatch):
    feed = ('<?xml version="1.0"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom"></feed>')
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: (200, feed))
    report = search.search_report("q", n=2, type="academic")
    assert report["results"] == []
    assert report["backends"][0]["status"] == "empty"


def test_trusted_searx_does_not_follow_redirect():
    """지정 주소가 다른 호스트로 넘기면 따라가지 않고 3xx 를 그대로 돌려준다(내부망 응답이 검색 결과가 되지 않게)."""
    import http.server
    import socketserver
    import threading

    hits = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            if self.path.startswith("/go"):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{port}/meta")
                self.end_headers()
                return
            body = b'{"results":[{"title":"secret","url":"http://10.0.0.9/x","content":"cred"}]}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        status, text = search._get_trusted(f"http://127.0.0.1:{port}/go")
    finally:
        server.shutdown()
        server.server_close()
    assert status == 302 and "secret" not in text
    assert hits == ["/go"]
