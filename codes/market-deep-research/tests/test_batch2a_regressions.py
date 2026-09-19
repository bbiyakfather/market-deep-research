"""배치 2A: 리뷰 재현의 부정 회귀와 정상 모바일/RSS/렌더 대조군. 외부 통신 없음."""
import json
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import capture_web
import fetch
import harvest_images
import render_pdf
import search
import source_index
import verify_facts
from skill_paths import WorkPaths

PUBLIC_IP = "93.184.216.34"
ARTICLE = "실제 원문의 시장 분석과 기술 설명입니다. " * 150


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = socket.getaddrinfo

    def resolve(host, *args, **kwargs):
        if host == "localhost" or host in ("127.0.0.1", "::1", PUBLIC_IP):
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
        self.reads = 0

    @property
    def content(self):
        raise AssertionError("전량 content 접근 금지")

    def iter_content(self, chunk_size):
        for start in range(0, len(self.body), chunk_size):
            self.reads += 1
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


@pytest.mark.parametrize("url", ["http://127.0.0.1/private", "file:///secret", "http://localhost/x"])
@pytest.mark.parametrize("caller", ["search", "image", "image_search"])
def test_n03_initial_guard_without_curl(url, caller, monkeypatch, tmp_path):
    monkeypatch.setattr(search, "creq", None)
    monkeypatch.setattr(harvest_images, "creq", None)
    with pytest.raises(fetch.SsrfBlocked):
        if caller == "search":
            search._get(url)
        elif caller == "image":
            harvest_images.download(url, tmp_path / "images")
        else:
            harvest_images._json_get(url)
    assert not (tmp_path / "images").exists()


@pytest.fixture
def local_server():
    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            if self.path == "/start":
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/private")
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"\x89PNG" + b"x" * 19000)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, hits
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize("transport", ["curl", "urllib"])
@pytest.mark.parametrize("caller", ["search", "image", "image_search"])
def test_n03_real_redirect_never_requests_private(local_server, monkeypatch, tmp_path, transport, caller):
    port, hits = local_server
    url = f"http://origin.test:{port}/start"
    if transport == "curl":
        real_client = pytest.importorskip("curl_cffi.requests")
        from curl_cffi.const import CurlOpt

        def get(url, **kwargs):
            # 테스트에서만 공인 origin의 실제 연결을 직접 만든 서버로 향하게 한다.
            kwargs["curl_options"][CurlOpt.RESOLVE] = [f"origin.test:{port}:127.0.0.1"]
            response = real_client.get(url, **kwargs)
            response.primary_ip = PUBLIC_IP
            return response

        client = SimpleNamespace(get=get)
    else:
        client = None
        real_connect = socket.create_connection

        class PublicPeer:
            def __init__(self, sock):
                self.sock = sock

            def getpeername(self):
                return PUBLIC_IP, port

            def __getattr__(self, key):
                return getattr(self.sock, key)

        def connect(address, *args, **kwargs):
            assert address == (PUBLIC_IP, port)
            return PublicPeer(real_connect(("127.0.0.1", port), *args, **kwargs))

        monkeypatch.setattr(socket, "create_connection", connect)
    monkeypatch.setattr(search, "creq", client)
    monkeypatch.setattr(harvest_images, "creq", client)
    with pytest.raises(fetch.SsrfBlocked):
        if caller == "search":
            search._get(url)
        elif caller == "image":
            harvest_images.download(url, tmp_path / "images")
        else:
            harvest_images._json_get(url)
    assert hits == ["/start"]
    assert not (tmp_path / "images").exists()


def test_n03_curl_pins_dns_disables_proxy_and_checks_peer(monkeypatch):
    from curl_cffi.const import CurlOpt
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9999")
    response = Response(ip="127.0.0.1")
    client = Client([response])
    with pytest.raises(fetch.SsrfBlocked):
        fetch.request_bytes("https://origin.test/x", client=client)
    options = client.calls[0][1]
    assert options["allow_redirects"] is False and options["stream"] is True
    assert options["curl_options"][CurlOpt.RESOLVE] == [f"origin.test:443:{PUBLIC_IP}"]
    assert options["curl_options"][CurlOpt.PROXY] == ""
    assert response.closed and response.reads == 0


def test_n03_redirect_hop_limit_and_public_success():
    client = Client([Response(302, headers={"location": "/next"}) for _ in range(6)])
    with pytest.raises(ValueError, match="too many redirects"):
        fetch.request_bytes("https://origin.test/start", client=client, max_redirects=99)
    assert len(client.calls) == 6
    client = Client([Response(302, headers={"location": "//cdn.test/image"}), Response(body=b"ok")])
    result = fetch.request_bytes("https://origin.test/start", client=client)
    assert result["raw"] == b"ok" and result["final_url"] == "https://cdn.test/image"


@pytest.mark.parametrize("transport", ["curl", "urllib"])
def test_n03_stream_limit_stops_before_entire_body(monkeypatch, transport):
    response = Response(body=b"x" * (fetch.CHUNK_BYTES * 4))
    if transport == "curl":
        client = Client([response])
    else:
        client = None
        response.code = 200

        def read(size):
            response.reads += 1
            return response.body[:size]

        response.read = read
        monkeypatch.setattr(fetch, "_urllib_open", lambda *a: response)
    with pytest.raises(fetch.DownloadLimitError):
        fetch.request_bytes("https://origin.test/x", client=client, max_bytes=fetch.CHUNK_BYTES)
    assert response.reads == 2 and response.closed


@pytest.mark.parametrize("status", [199, 302, 404, 503])
def test_n15_pdf_error_not_success(monkeypatch, status):
    response = {"ok": True, "status": status, "is_pdf": True, "raw": b"%PDF-1.4 error",
                "text": "", "final_url": "https://origin.test/report.pdf"}
    monkeypatch.setattr(fetch, "_tier_order", lambda url: ["direct"])
    monkeypatch.setattr(fetch, "_candidates", lambda *a: iter([("direct", response)]))
    result = fetch.fetch(response["final_url"])
    assert result["status"] == "fail"
    rows = [json.loads(line) for line in Path("audit/fetch-log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["failure_reason"] == f"http {status}"
    assert rows[-1]["kind"] == "final" and rows[-1]["status"] == "fail"


def test_n15_transport_rejects_pdf_503_but_accepts_200(monkeypatch):
    monkeypatch.setattr(fetch, "creq", Client([Response(503, b"%PDF-1.4 error"), Response(200, b"%PDF-1.4 content")]))
    assert fetch._fetch_once("https://origin.test/a", "chrome")["ok"] is False
    assert fetch._fetch_once("https://origin.test/a", "chrome")["is_pdf"] is True


def feed_response(xml):
    return {"ok": True, "status": 200, "text": xml, "raw": xml.encode(), "is_pdf": False,
            "mime": "application/rss+xml", "final_url": "https://origin.test/feed"}


def test_n16_unrelated_feed_partial_and_ladder_continues(monkeypatch):
    xml = f"<rss><channel><item><link>https://origin.test/other</link><description>{ARTICLE}</description></item></channel></rss>"
    visited = []

    def candidates(tier, url):
        visited.append(tier)
        yield tier, feed_response(xml) if tier == "rss" else {"ok": False, "reason": "missing"}

    monkeypatch.setattr(fetch, "_tier_order", lambda url: ["rss", "wayback"])
    monkeypatch.setattr(fetch, "_candidates", candidates)
    result = fetch.fetch("https://origin.test/missing", success_selectors=["시장"])
    assert result["status"] == "partial" and result["note"] == "rss"
    assert visited == ["rss", "wayback"]
    assert source_index._fetch_counts(Path.cwd()) == {"attempt_failures": 1, "final_failures": 0}


@pytest.mark.parametrize("identity", ["link", "guid", "title", "atom"])
def test_n16_matching_entry_preserves_real_article(monkeypatch, identity):
    target = "https://origin.test/article"
    if identity == "atom":
        xml = (f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><link href="{target}"/>'
               f'<title>대상 제목</title><content type="html">{ARTICLE}</content></entry></feed>')
    else:
        marker = "대상 제목" if identity == "title" else target
        xml = (f"<rss><channel><item><{identity}>{marker}</{identity}><description>{ARTICLE}</description>"
               "</item><item><link>https://origin.test/unrelated</link><description>UNRELATED_ENTRY</description>"
               "</item></channel></rss>")
    monkeypatch.setattr(fetch, "_tier_order", lambda url: ["rss"])
    monkeypatch.setattr(fetch, "_candidates", lambda *a: iter([("rss", feed_response(xml))]))
    result = fetch.fetch(target, expected_title="대상 제목" if identity == "title" else None)
    assert result["status"] == "ok" and result["note"] == "rss"
    assert ARTICLE.strip() in result["text"] and "UNRELATED_ENTRY" not in result["text"]
    assert result["raw"] == xml.encode()  # raw 원본은 재직렬화하거나 잘라내지 않는다.


@pytest.mark.parametrize("mime", ["application/rss+xml", "application/atom+xml"])
def test_n16_real_candidate_mime_and_rss_body(monkeypatch, mime):
    xml = f"<rss><channel><item><link>https://origin.test/article</link><description>{ARTICLE}</description></item></channel></rss>"
    monkeypatch.setattr(fetch, "creq", Client([Response(200, xml.encode(), {"content-type": mime})]))
    monkeypatch.setattr(fetch, "_tier_order", lambda url: ["rss"])
    result = fetch.fetch("https://origin.test/article")
    assert result["status"] == "ok" and result["archived_url"] == "https://origin.test/rss"


def test_n16_nonfeed_pdf_cannot_take_success_fast_path(monkeypatch):
    monkeypatch.setattr(fetch, "_tier_order", lambda url: ["rss"])
    monkeypatch.setattr(fetch, "_candidates", lambda *a: iter([("rss", {
        "ok": True, "status": 200, "is_pdf": True, "text": "", "raw": b"%PDF-1.4 error"})]))
    assert fetch.fetch("https://origin.test/article")["status"] == "fail"


def test_n03_normal_mobile_fingerprint_fallback(monkeypatch):
    calls = []

    def request(url, **kwargs):
        calls.append((url, kwargs))
        mobile = kwargs["impersonate"] == fetch.MOBILE_IMPERSONATE
        return Response(200 if mobile else 403, ARTICLE.encode() if mobile else b"denied")

    monkeypatch.setattr(fetch, "creq", SimpleNamespace(get=request))
    result = fetch.fetch("https://origin.test/article")
    assert result["status"] == "ok" and result["note"] == "mobile"
    assert [kwargs["impersonate"] for _, kwargs in calls[:3]] == fetch.IMPERSONATE_GRID
    assert calls[-1][1]["headers"] == fetch.MOBILE_HEADERS


@pytest.mark.parametrize("target", ["http://127.0.0.1/render-image", "https://origin.test/x", "//origin.test/x",
                                    "data:image/png;base64,eA==", "../outside.png"])
def test_n02_g3_rejects_external_data_and_escape(tmp_path, target):
    failures, _ = verify_facts.check_figures(f"![그림]({target})\n[그림] 출처: 예시\n", {}, WorkPaths(tmp_path))
    assert any("도판경로" in failure for failure in failures)


@pytest.mark.parametrize("body", [
    '<img src=http://127.0.0.1/x>',
    '![image][source]\n\n[source]: https://origin.test/x',
    '![source][]\n\n[source]: data:image/png;base64,eA==',
])
def test_n02_g3_alternate_image_syntax_rejected(tmp_path, body):
    failures, _ = verify_facts.check_figures(body, {}, WorkPaths(tmp_path))
    assert any("도판경로" in failure for failure in failures)


def test_g3_windows_absolute_path_matches_renderer_policy(tmp_path):
    # 같은 내부 PNG 를 상대경로/드라이브 절대경로로 참조하면 G3 판정이 같아야 한다
    # (렌더러는 드라이브 경로를 허용하므로 — 리뷰 2A 발견 1). 루트 밖 절대경로는 계속 거부.
    png = tmp_path / "_captures" / "image.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    for target in ("_captures/image.png", str(png).replace("\\", "/")):
        failures, _ = verify_facts.check_figures(
            f"![그림]({target})\n[그림] 출처: 예시\n", {}, WorkPaths(tmp_path))
        assert not any("도판경로" in f for f in failures), target
    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(b"\x89PNG\r\n\x1a\n")
    failures, _ = verify_facts.check_figures(
        f"![그림]({str(outside).replace(chr(92), '/')})\n[그림] 출처: 예시\n", {}, WorkPaths(tmp_path))
    assert any("도판경로" in f for f in failures)


@pytest.mark.parametrize("syntax", ["inline", "reference", "html"])
def test_n02_external_render_rejected_before_request(local_server, tmp_path, syntax):
    port, hits = local_server
    url = f"http://127.0.0.1:{port}/render-image"
    content = {"inline": f"![그림]({url})", "reference": f"![그림][image]\n\n[image]: {url}",
               "html": f'<img src="{url}">'}[syntax]
    md = tmp_path / "report.md"
    md.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="외부 이미지"):
        render_pdf.render(md)
    assert hits == [] and not md.with_suffix(".pdf").exists()


def test_n02_active_html_not_executed_and_local_image_renders(tmp_path):
    image_path = tmp_path / "그림.png"
    with fitz.open() as doc:
        page = doc.new_page(width=100, height=100)
        page.draw_rect(page.rect, fill=(1, 0, 0))
        page.get_pixmap().save(image_path)
    md = tmp_path / "report.md"
    md.write_text('# 제목\n\n![그림](그림.png)\n\n<script>document.body.append("UNREVIEWED_" + "SCRIPT_OUTPUT");</script>',
                  encoding="utf-8")
    render_pdf._pandoc_html(md, tmp_path / "out.html", tmp_path)
    html = (tmp_path / "out.html").read_text(encoding="utf-8")
    assert "<script>" not in html and "script-src 'none'" in html and "data:image/png;base64," in html
    result = render_pdf.render(md)
    with fitz.open(result["pdf"]) as doc:
        assert "UNREVIEWED_SCRIPT_OUTPUT" not in "".join(page.get_text() for page in doc)
        assert any(page.get_images() for page in doc)


def test_n02_timeouts_and_sandbox_default(monkeypatch, tmp_path):
    md = tmp_path / "report.md"
    md.write_text("# 제목", encoding="utf-8")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["timeout"] == 180
        raise subprocess.TimeoutExpired(command, 180)

    monkeypatch.setattr(render_pdf.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="시간 초과"):
        render_pdf._pandoc_html(md, tmp_path / "out.html", tmp_path)
    monkeypatch.setattr(render_pdf, "_find_chrome", lambda: "chrome")
    with pytest.raises(RuntimeError, match="시간 초과"):
        render_pdf._chrome_pdf(tmp_path / "out.html", tmp_path / "out.pdf")
    assert "--no-sandbox" not in calls[-1]
    assert "--disable-background-networking" in calls[-1]
    assert "--host-resolver-rules=MAP * ~NOTFOUND" in calls[-1]


def test_n02_html_writer_also_has_timeout(monkeypatch, tmp_path):
    md = tmp_path / "report.md"
    md.write_text("# 제목", encoding="utf-8")

    def run(command, **kwargs):
        assert kwargs["timeout"] == 180
        if command[command.index("-t") + 1] == "json":
            return SimpleNamespace(returncode=0, stdout='{"blocks": [], "meta": {}}')
        raise subprocess.TimeoutExpired(command, 180)

    monkeypatch.setattr(render_pdf.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="HTML 변환 시간 초과"):
        render_pdf._pandoc_html(md, tmp_path / "out.html", tmp_path)


@pytest.mark.parametrize("allow", [False, True])
def test_n02_sandbox_fallback_requires_explicit_flag(monkeypatch, tmp_path, allow):
    calls = []
    pdf = tmp_path / "out.pdf"

    def run(command, **kwargs):
        calls.append(command)
        if "--no-sandbox" in command:
            pdf.write_bytes(b"%PDF-test")
            return SimpleNamespace(returncode=0, stderr="")
        return SimpleNamespace(returncode=1, stderr="No usable sandbox")

    monkeypatch.setattr(render_pdf, "_find_chrome", lambda: "chrome")
    monkeypatch.setattr(render_pdf.subprocess, "run", run)
    if allow:
        render_pdf._chrome_pdf(tmp_path / "in.html", pdf, allow_no_sandbox=True)
        assert len(calls) == 2
    else:
        with pytest.raises(RuntimeError, match="Chrome PDF 실패"):
            render_pdf._chrome_pdf(tmp_path / "in.html", pdf)
        assert len(calls) == 1
    assert "--no-sandbox" not in calls[0]


@pytest.mark.parametrize("suffix", ["../forged.png", "../../forged.png"])
def test_n14_reconstruction_cannot_escape(tmp_path, suffix):
    with pytest.raises(ValueError, match="경로 이탈"):
        capture_web.reconstruct_excerpt("위조", "https://origin.test", tmp_path / "_captures" / "_reconstructed" / suffix)
    assert not list(tmp_path.rglob("*.png"))


def test_n14_normal_reconstruction(tmp_path):
    path = tmp_path / "_captures" / "_reconstructed" / "nested" / "image.png"
    result = capture_web.reconstruct_excerpt("정상 발췌", "https://origin.test", path)
    assert result["ok"] and result["evidence"] is False and path.stat().st_size > 0


def test_n22_actual_log_final_status_and_custom_output(tmp_path):
    audit = tmp_path / "audit"
    audit.mkdir()
    rows = [
        {"url": "https://origin.test/a", "failure_reason": "403"},
        {"url": "https://origin.test/a", "kind": "final", "status": "ok"},
        {"url": "https://origin.test/b", "failure_reason": "503"},
        {"url": "https://origin.test/b", "failure_reason": "503"},
        {"url": "https://origin.test/b", "kind": "final", "status": "fail"},
        {"url": "https://origin.test/c", "kind": "final", "status": "partial"},
    ]
    (audit / "fetch-log.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    assert source_index._fetch_counts(tmp_path) == {"attempt_failures": 3, "final_failures": 1}
    out = source_index.write_markdown([{"n": 1, "status": "partial"}, {"n": 2, "status": "ok"}],
                                      tmp_path / "nested" / "sources.md", work_dir=tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "최종 실패 URL 1건" in text and "시도 실패 3회" in text
    assert "| 상태 |" in text and "| partial |" in text and "| ok |" in text


@pytest.mark.parametrize("mode", ["get", "smoke"])
def test_k07_cli_json_keeps_hash_path_and_full_trace(monkeypatch, tmp_path, capsys, mode):
    trace = [{"tier": "mobile", "error": "오류" * 2000} for _ in range(30)]
    result = {"status": "ok", "text": ARTICLE, "raw": ARTICLE.encode(), "trace": trace,
              "final_url": "https://origin.test/a"}
    monkeypatch.setattr(fetch, "fetch", lambda url: dict(result))
    fetch.main([mode, result["final_url"], "--out", str(tmp_path / "_sources")])
    output = json.loads(capsys.readouterr().out)
    assert "sha256" in output and "local" in output
    assert output["trace_count"] == 30
    assert json.loads(Path(output["trace_path"]).read_text(encoding="utf-8")) == trace
    if mode == "get":
        assert len(output["sha256"]) == 64 and Path(output["local"]).is_file()
