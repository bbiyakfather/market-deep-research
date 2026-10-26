"""학술 어댑터 파서·폴스루 테스트 (네트워크 없음, 고정 JSON/XML)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import search as S

OPENALEX = {"meta": {"count": 5}, "results": [{
    "id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/abc", "title": "Solid <i>state</i> battery",
    "publication_year": 2024, "authorships": [{"author": {"display_name": "Kim A"}}],
    "abstract_inverted_index": {"world": [1], "Hello": [0]}}]}
CROSSREF = {"status": "ok", "message": {"total-results": 9, "items": [{
    "DOI": "10.2/x", "title": ["T"], "URL": "http://dx.doi.org/10.2/x", "issued": {"date-parts": [[2021, 3]]},
    "author": [{"given": "A", "family": "Lee"}], "abstract": "<jats:p>abs</jats:p>"}]}}
EPMC = {"hitCount": 2, "resultList": {"result": [{
    "id": "123", "source": "MED", "title": "P", "pubYear": "2020", "doi": "10.3/y",
    "authorString": "Park J, Choi K.", "abstractText": "a"}]}}
S2 = {"total": 1, "data": [{"title": "S", "year": 2022, "url": "https://s2/1", "abstract": None,
                            "externalIds": {"DOI": "10.4/z"}, "authors": [{"name": "Z"}]}]}


def test_parsers_normal():
    o = S._parse_openalex(OPENALEX, 3)[0]
    assert (o["source"], o["year"], o["doi"], o["url"]) == ("openalex", "2024", "10.1/abc", "https://doi.org/10.1/abc")
    assert o["abstract"] == "Hello world" and o["title"] == "Solid state battery" and o["authors"] == ["Kim A"]
    c = S._parse_crossref(CROSSREF, 3)[0]
    assert (c["year"], c["doi"], c["abstract"], c["authors"]) == ("2021", "10.2/x", "abs", ["A Lee"])
    e = S._parse_europepmc(EPMC, 3)[0]
    assert (e["year"], e["authors"], e["url"]) == ("2020", ["Park J", "Choi K"], "https://doi.org/10.3/y")
    s = S._parse_s2(S2, 3)[0]
    assert (s["source"], s["doi"], s["abstract"]) == ("semanticscholar", "10.4/z", "")


@pytest.mark.parametrize("fn,data", [
    (S._parse_openalex, {"meta": {"count": 7}, "results": []}),                 # 총건수>0 인데 0건
    (S._parse_openalex, {"meta": {"count": 0}, "results": OPENALEX["results"]}),  # 총건수 0 인데 반환 있음
    (S._parse_openalex, {"error": "Invalid query"}),
    (S._parse_crossref, {"status": "ok", "message": {"total-results": 4, "items": []}}),
    (S._parse_crossref, {"status": "failed", "message": {}}),
    (S._parse_europepmc, {"version": "6", "errCode": 400, "errMsg": "pageSize too big"}),
    (S._parse_europepmc, {"hitCount": 3, "resultList": {"result": []}}),
    (S._parse_s2, {"message": "Too Many Requests"}),
])
def test_http200_failures_raise(fn, data):
    with pytest.raises(S._BackendError):
        fn(data, 3)


def test_zero_hits_is_empty_not_failure():
    assert S._parse_openalex({"meta": {"count": 0}, "results": []}, 3) == []
    assert S._parse_europepmc({"hitCount": 0, "resultList": {"result": []}}, 3) == []


def test_arxiv_error_entry_is_failure(monkeypatch):
    feed = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Error</title>'
            '<summary>start must be an integer</summary><id>http://arxiv.org/api/errors</id></entry></feed>')
    monkeypatch.setattr(S, "_get", lambda url, timeout=12: (200, feed))
    assert S._arxiv("x", 3) == []


def test_arxiv_academic_path_records_error(monkeypatch, tmp_path):
    feed = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Error</title>'
            '<summary>bad</summary></entry></feed>')
    for resp in ((200, feed), (429, "Rate exceeded."), (200, "Rate exceeded.")):
        monkeypatch.setattr(S, "_get", lambda url, timeout=12, headers=None, r=resp: r)
        with pytest.raises(S._BackendError):
            S._arxiv("x", 3, strict=True)
    monkeypatch.setattr(S, "_ACADEMIC", [("arxiv", lambda q, n: S._arxiv(q, n, strict=True))])
    assert S.search("x", 3, "academic", work_dir=tmp_path) == []
    row = json.loads((tmp_path / "audit" / "search-log.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["backend"] == "academic:arxiv" and row["error"]


def test_arxiv_normal_entry(monkeypatch):
    feed = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Attn</title><summary>s</summary>'
            '<id>http://arxiv.org/abs/1</id><published>2017-06-12T00:00:00Z</published>'
            '<author><name>V</name></author></entry></feed>')
    monkeypatch.setattr(S, "_get", lambda url, timeout=12: (200, feed))
    r = S._arxiv("x", 3)[0]
    assert (r["year"], r["authors"], r["source"]) == ("2017", ["V"], "arxiv")


def test_fallthrough_on_429_and_failure_logs_each_backend(monkeypatch, tmp_path):
    def boom(q, n):
        raise S._BackendError("HTTP 429")
    ok = [{"title": "t", "url": "https://x/1", "source": "europepmc"}]
    monkeypatch.setattr(S, "_ACADEMIC", [("openalex", boom), ("crossref", lambda q, n: []),
                                         ("europepmc", lambda q, n: ok), ("arxiv", boom)])
    assert S.search("q", 3, "academic", axis="기술요소", work_dir=tmp_path) == ok
    rows = [json.loads(l) for l in (tmp_path / "audit" / "search-log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["backend"] for r in rows] == ["academic:openalex", "academic:crossref", "academic:europepmc"]
    assert rows[0]["error"] == "HTTP 429" and rows[1]["n_returned"] == 0 and rows[2]["tier"] == "europepmc"


def test_s2_retries_once_on_429_then_gives_up(monkeypatch):
    calls = []
    monkeypatch.setattr(S.time, "sleep", lambda s: None)
    monkeypatch.setattr(S, "_get", lambda url, timeout=12, headers=None: calls.append(url) or (429, ""))
    with pytest.raises(S._BackendError):
        S._s2("x", 3)
    assert len(calls) == 2


def test_api_polite_headers_and_mailto(monkeypatch):
    seen = {}
    monkeypatch.setenv("MDR_CONTACT_EMAIL", "me@corp.com")
    monkeypatch.setattr(S, "_get", lambda url, timeout=12, headers=None: seen.update(u=url, h=headers) or (200, "{}"))
    S._api("https://api.crossref.org/works?x=1" + S._mailto())
    assert "mailto=me%40corp.com" in seen["u"] and "market-deep-research" in seen["h"]["User-Agent"]
    monkeypatch.delenv("MDR_CONTACT_EMAIL")
    assert S._mailto() == ""
