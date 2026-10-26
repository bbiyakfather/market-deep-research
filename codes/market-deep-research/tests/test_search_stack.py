"""검색 스택: 네트워크 없이 폴백·빈 인스턴스·arXiv 구문 검색 확인."""
import builtins
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import search


def test_ddgs_import_failure_falls_back_to_ddg(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "ddgs":
            raise ImportError("no ddgs")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    called = []
    monkeypatch.setattr(search, "_ddg", lambda q, n: called.append(q) or [
        {"title": "t", "url": f"https://e.com/{i}", "snippet": "", "source": "ddg"} for i in range(5)])
    res = search.search("x", 5, "web")
    assert called == ["x"] and res[0]["source"] == "ddg"


def test_searx_empty_instances_makes_no_request(monkeypatch):
    monkeypatch.setitem(search._SEARX, "instances", [])
    monkeypatch.setattr(search, "_get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    assert search._searx("x", 5) == []


def test_arxiv_quotes_phrase_then_retries_and(monkeypatch):
    urls = []
    empty = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    monkeypatch.setattr(search, "_get", lambda url, timeout=12: urls.append(url) or (200, empty))
    assert search._arxiv("advanced packaging", 3) == []
    assert "all:%22advanced%20packaging%22" in urls[0] and "all:advanced%20AND%20all:packaging" in urls[1]


def test_ddgs_drops_relative_urls(monkeypatch):
    import types
    class FakeDDGS:
        def text(self, *a, **k):
            return [{"title": "ad", "href": "/clev?event=1", "body": ""},
                    {"title": "ok", "href": "https://e.com/a", "body": ""}]
    monkeypatch.setitem(sys.modules, "ddgs", types.SimpleNamespace(DDGS=FakeDDGS))
    assert [r["url"] for r in search._ddgs("x", 5)] == ["https://e.com/a"]
