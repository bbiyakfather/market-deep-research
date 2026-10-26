"""search.py — 자체 검색 (유료 API 무의존). plan-v2 핵심설계3.

계층: ddgs 다중 백엔드(web=text, news=news) → DuckDuckGo HTML → SearXNG(자체 호스트 등록 시만)
      → 전문 무료 API(academic=OpenAlex→Crossref→Europe PMC→Semantic Scholar→arXiv, SEC EDGAR full-text=filing). --type 은 curated-sources.json
      의 type_backends 에 있는 것만. 미지원 유형은 명시적 실패. 0건 계층은 stderr 경고 후 건너뜀.

주의: "검색 완전성 미보장". 에이전트는 내장 WebSearch 와 병행한다.

CLI:
  python search.py demo
  python search.py "쿼리" --n 8 --type web|news|academic|filing [--axis 축이름] [--work <작업폴더>]

검색 호출마다 <작업폴더>/audit/search-log.jsonl(기본 MDR_WORK_DIR, 없으면 현재 폴더) 에 1줄 기록(빈 결과·실패 포함) — 커버리지 선언의 집계 근거.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from skill_paths import ASSETS

from fetch import creq, request_bytes, response_text

_CURATED = json.loads((ASSETS / "curated-sources.json").read_text(encoding="utf-8"))
_SEARX = json.loads((ASSETS / "searx-instances.json").read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


_SECRET = re.compile(r"((?:api[_-]?)?key|secret|password|auth|token|mailto|email)=[^&\s]+|Bearer\s+\S+|[\w.+-]+@[\w-]+\.[\w.]+", re.I)


def _mask(text: str) -> str:
    """로그에 키·이메일이 새지 않게 가린다."""
    return _SECRET.sub(lambda m: (m.group(1) + "=***") if m.group(1) else "***", text)


def log_search(query: str, type: str, n: int, results: list[dict] | None, axis: str | None = None,
               error: str | None = None, audit: Path | None = None) -> None:
    """audit/search-log.jsonl 에 검색 1회를 1줄 append. 기록 실패가 검색을 막지 않는다."""
    audit = audit or Path("audit")
    n_ret = len(results or [])
    row = {"ts": _now(), "axis": axis, "tier": (results[0]["source"] if n_ret else None), "backend": type,
           "query": _mask(query), "filters": {"type": type}, "n_requested": n, "n_returned": n_ret,
           "n_kept": len({r["url"] for r in results or []})}
    if error:
        row["error"] = _mask(error)
    try:
        audit.mkdir(parents=True, exist_ok=True)
        with (audit / "search-log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"  ⚠ search-log 기록 실패: {e}", file=sys.stderr)


def _get(url: str, timeout: int = 12, headers: dict | None = None) -> tuple[int, str]:
    response = request_bytes(url, timeout=timeout, client=creq,
                             headers=headers or {"User-Agent": "Mozilla/5.0"})
    return response["status"], response_text(response)


# --- 백엔드들 ----------------------------------------------------------------
def _ddg(query: str, n: int) -> list[dict]:
    """DuckDuckGo HTML. 결과 링크는 //duckduckgo.com/l/?uddg=<encoded> 리다이렉트 → 디코드."""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + quote(query)
        _, html = _get(url)
    except Exception as e:                     # 1차 백엔드도 다른 백엔드처럼 실패는 건너뜀(V28)
        print(f"  ⚠ ddg 실패(건너뜀): {e}", file=sys.stderr)
        return []
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        real = _decode_ddg(href)
        if real:
            out.append({"title": title, "url": real, "snippet": "", "source": "ddg"})
        if len(out) >= n:
            break
    if not out:
        print("  ⚠ ddg 0건(건너뜀)", file=sys.stderr)
    return out


def _ddgs(query: str, n: int, kind: str = "web") -> list[dict]:
    """ddgs(구 duckduckgo_search) 다중 백엔드 메타검색. 미설치·예외·0건이면 경고 후 []."""
    try:
        from ddgs import DDGS
        region = "kr-kr" if re.search("[가-힣]", query) else "us-en"
        raw = (DDGS().news(query, region=region, max_results=n) if kind == "news"
               else DDGS().text(query, region=region, max_results=n))
    except Exception as e:
        print(f"  ⚠ ddgs 실패(건너뜀): {e}", file=sys.stderr)
        return []
    out = [{"title": r.get("title", ""), "url": r.get("href") or r.get("url", ""),
            "snippet": r.get("body", ""), "source": "ddgs"} for r in raw]
    out = [r for r in out if r["url"].startswith(("http://", "https://"))]   # 상대 URL 광고 링크 제거
    if not out:
        print("  ⚠ ddgs 0건(건너뜀)", file=sys.stderr)
    return out


def _decode_ddg(href: str) -> str | None:
    if href.startswith("//"):
        href = "https:" + href
    q = parse_qs(urlparse(href).query)
    if "uddg" in q:
        return unquote(q["uddg"][0])
    return href if href.startswith("http") else None


def _searx(query: str, n: int) -> list[dict]:
    """공개 SearXNG 로테이션 + 백오프. JSON 미지원/죽은 인스턴스는 다음으로."""
    if not _SEARX["instances"]:                          # 자체 호스트 미등록 → 네트워크 없이 즉시 종료
        return []
    for inst in _SEARX["instances"]:
        for delay in [0] + _SEARX["backoff_sec"]:
            if delay:
                time.sleep(delay)
            try:
                st, txt = _get(f"{inst}/search?q={quote(query)}&format=json", timeout=_SEARX["timeout_sec"])
                if st == 200 and txt.lstrip().startswith("{"):
                    data = json.loads(txt)
                    res = [{"title": r.get("title", ""), "url": r.get("url", ""),
                            "snippet": r.get("content", ""), "source": f"searx:{urlparse(inst).hostname}"}
                           for r in data.get("results", [])[:n]]
                    if res:
                        return res
            except Exception:
                continue
            break                                        # 이 인스턴스 1회만(백오프는 429 등서만 의미)
    print("  ⚠ searx 0건(건너뜀)", file=sys.stderr)
    return []


def _arxiv(query: str, n: int, strict: bool = False) -> list[dict]:
    """strict=True(academic 경로)면 HTTP 오류·Error 항목·파싱 실패를 삼키지 않고 _BackendError 로 올려 로그에 error 가 남게 한다."""
    q = query.strip()
    if " " in q and not q.startswith('"'):   # 무인용 all: 은 단어별 OR 라 무관 논문이 섞임 → 구문 먼저, 0건이면 AND
        res = _arxiv(f'"{q}"', n, strict)
        if res:
            return res
        q = " AND ".join(f"all:{w}" for w in q.split())
    else:
        q = f"all:{q}"
    url = f"https://export.arxiv.org/api/query?search_query={quote(q, safe=":")}&max_results={n}"
    try:
        st, xml = _get(url, timeout=25)                  # arXiv API 는 느릴 수 있음
        if st != 200:                                    # 429 는 XML 이 아니라 "Rate exceeded." 평문
            raise _BackendError(f"HTTP {st}")
        ns = {"a": "http://www.w3.org/2005/Atom"}
        out = []
        entries = ET.fromstring(xml).findall("a:entry", ns)
        if any((e.findtext("a:title", "", ns) or "").strip() == "Error" for e in entries):
            raise _BackendError("arXiv 가 오류를 <title>Error</title> 항목으로 반환")   # HTTP 200 이어도 논문이 아님
        for e in entries:
            summary = (e.findtext("a:summary", "", ns) or "").strip()
            out.append({"title": (e.findtext("a:title", "", ns) or "").strip(),
                        "url": (e.findtext("a:id", "", ns) or "").strip(), "source": "arxiv",
                        "year": (e.findtext("a:published", "", ns) or "")[:4], "doi": None,
                        "authors": [x.findtext("a:name", "", ns) for x in e.findall("a:author", ns)],
                        "abstract": summary, "snippet": summary[:300]})
        if not out:
            print("  ⚠ arxiv 0건(건너뜀)", file=sys.stderr)
        return out
    except Exception as e:
        if strict:
            raise _BackendError(str(e)) from e
        print(f"  ⚠ arxiv 실패(건너뜀): {e}", file=sys.stderr)
        return []


# --- 학술 어댑터 (--type academic) --------------------------------------------
# 순서: OpenAlex → Crossref → Europe PMC → Semantic Scholar → arXiv. 첫 비어있지 않은 백엔드 결과를 쓴다.
# 공통 반환: {title, url, source, year, doi, authors, abstract, snippet}. 각 백엔드는 audit 로그 1줄.
class _BackendError(Exception):
    """HTTP 200 이어도 실패(총건수 불일치·오류 본문)와 비200 을 한데 묶는 신호."""


def _api(url: str, headers: dict | None = None) -> dict:
    """학술 API GET → JSON. 비200(429 포함)·JSON 아님이면 _BackendError."""
    mail = os.environ.get("MDR_CONTACT_EMAIL", "").strip()
    ua = "market-deep-research/1.0" + (f" (mailto:{mail})" if mail else "")
    st, txt = _get(url, 15, {"User-Agent": ua, **(headers or {})})
    if st != 200:
        raise _BackendError(f"HTTP {st}")
    try:
        return json.loads(txt)
    except ValueError:
        raise _BackendError("JSON 아님")


def _mailto() -> str:
    mail = os.environ.get("MDR_CONTACT_EMAIL", "").strip()
    return f"&mailto={quote(mail)}" if mail else ""


def _check_total(total, items: list, name: str) -> None:
    """총건수와 반환 건수가 (0 여부 기준으로) 어긋나면 200 응답이어도 실패."""
    if not isinstance(total, int) or (total > 0) != bool(items):
        raise _BackendError(f"{name} 총건수 {total} ≠ 반환 {len(items)}건")


def _rec(source: str, title, url: str, year, doi, authors: list, abstract) -> dict:
    abstract = re.sub(r"<[^>]+>", "", abstract or "").strip()
    doi = (doi or "").removeprefix("https://doi.org/") or None
    return {"title": re.sub(r"<[^>]+>", "", title or "").strip(), "url": f"https://doi.org/{doi}" if doi else url,
            "source": source, "year": str(year) if year else None, "doi": doi,
            "authors": [a for a in authors if a], "abstract": abstract, "snippet": abstract[:300]}


def _parse_openalex(data: dict, n: int) -> list[dict]:
    if "error" in data or "results" not in data:
        raise _BackendError(str(data.get("error") or "results 없음")[:100])
    _check_total((data.get("meta") or {}).get("count"), data["results"], "openalex")
    out = []
    for w in data["results"][:n]:
        words = sorted((p, t) for t, ps in (w.get("abstract_inverted_index") or {}).items() for p in ps)
        out.append(_rec("openalex", w.get("title"), w.get("id", ""), w.get("publication_year"), w.get("doi"),
                        [(a.get("author") or {}).get("display_name") for a in w.get("authorships") or []],
                        " ".join(t for _, t in words)))
    return out


def _parse_crossref(data: dict, n: int) -> list[dict]:
    msg = data.get("message")
    if data.get("status") != "ok" or not isinstance(msg, dict) or "items" not in msg:
        raise _BackendError("status≠ok 또는 items 없음")
    _check_total(msg.get("total-results"), msg["items"], "crossref")
    out = []
    for w in msg["items"][:n]:
        year = ((w.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        out.append(_rec("crossref", (w.get("title") or [""])[0], w.get("URL", ""), year, w.get("DOI"),
                        [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in w.get("author") or []],
                        w.get("abstract")))
    return out


def _parse_europepmc(data: dict, n: int) -> list[dict]:
    if data.get("errCode") or "resultList" not in data:        # 오류는 HTTP 200 + resultList 없음으로 온다
        raise _BackendError(f"errCode={data.get('errCode')} {data.get('errMsg', '')}"[:100])
    items = data["resultList"].get("result", [])
    _check_total(data.get("hitCount"), items, "europepmc")
    return [_rec("europepmc", w.get("title"), f"https://europepmc.org/article/{w.get('source')}/{w.get('id')}",
                 w.get("pubYear") or (w.get("firstPublicationDate") or "")[:4], w.get("doi"),
                 [a.strip() for a in (w.get("authorString") or "").rstrip(".").split(",")], w.get("abstractText"))
            for w in items[:n]]


def _parse_s2(data: dict, n: int) -> list[dict]:
    if "message" in data or "error" in data or "total" not in data:
        raise _BackendError(str(data.get("message") or data.get("error") or "total 없음")[:100])
    items = data.get("data") or []
    _check_total(data["total"], items, "semanticscholar")
    return [_rec("semanticscholar", w.get("title"), w.get("url", ""), w.get("year"),
                 (w.get("externalIds") or {}).get("DOI"), [(a or {}).get("name") for a in w.get("authors") or []],
                 w.get("abstract")) for w in items[:n]]


def _openalex(query: str, n: int) -> list[dict]:
    sel = "id,doi,title,publication_year,authorships,abstract_inverted_index"
    return _parse_openalex(_api(f"https://api.openalex.org/works?search={quote(query)}&per_page={n}&select={sel}{_mailto()}"), n)


def _crossref(query: str, n: int) -> list[dict]:
    sel = "DOI,title,URL,issued,author,abstract"
    return _parse_crossref(_api(f"https://api.crossref.org/works?query={quote(query)}&rows={n}&select={sel}{_mailto()}"), n)


def _europepmc(query: str, n: int) -> list[dict]:
    return _parse_europepmc(_api("https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=core"
                                 f"&pageSize={n}&query={quote(query)}"), n)


def _s2(query: str, n: int) -> list[dict]:
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?fields=title,year,abstract,authors,externalIds,url"
           f"&limit={n}&query={quote(query)}")
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    hdr = {"x-api-key": key} if key else None
    try:
        data = _api(url, hdr)
    except _BackendError as e:
        if "429" not in str(e):
            raise
        time.sleep(3)                                    # 키 없는 공유 풀은 429 가 잦다 — 1회 재시도 후 포기
        data = _api(url, hdr)
    return _parse_s2(data, n)


_ACADEMIC = [("openalex", _openalex), ("crossref", _crossref), ("europepmc", _europepmc),
             ("semanticscholar", _s2), ("arxiv", lambda q, n: _arxiv(q, n, strict=True))]


def _academic(query: str, n: int, axis: str | None, audit: Path) -> list[dict]:
    """백엔드를 순서대로 시도, 백엔드마다 로그 1줄. 실패·0건이면 다음으로."""
    for name, run in _ACADEMIC:
        res, err = [], None
        try:
            res = run(query, n)
        except Exception as e:
            err = str(e)
            print(f"  ⚠ {name} 실패(건너뜀): {e}", file=sys.stderr)
        log_search(query, f"academic:{name}", n, res, axis, error=err, audit=audit)
        if res:
            return res
    return []


def _sec_edgar(query: str, n: int) -> list[dict]:
    url = 'https://efts.sec.gov/LATEST/search-index?q="' + quote(query) + '"'
    try:
        _, txt = _get(url)
        hits = json.loads(txt).get("hits", {}).get("hits", [])[:n]
    except Exception as e:
        print(f"  ⚠ sec_edgar 실패(건너뜀): {e}", file=sys.stderr)
        return []
    if not hits:
        print("  ⚠ sec_edgar 0건(건너뜀)", file=sys.stderr)
    out = []
    for h in hits:
        src = h.get("_source", {})
        ciks = src.get("ciks") or []                    # V22 — 실응답 필드는 복수형 'ciks' 뿐(단수 'cik' 없음)
        cik = ciks[0] if ciks else ""
        acc, _, fname = (h.get("_id") or "").partition(":")   # accession:filename → 공시 문서 직행 URL
        if cik and acc and fname:
            url = (f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0') or '0'}/"
                   f"{acc.replace('-', '')}/{fname}")
        else:
            url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
        out.append({"title": src.get("display_names", [""])[0] if src.get("display_names") else h.get("_id", ""),
                    "url": url, "snippet": src.get("form", ""), "source": "sec_edgar"})
    return out


# --- 디스패치 ----------------------------------------------------------------
def search(query: str, n: int = 10, type: str = "web", axis: str | None = None,
           work_dir: str | Path | None = None) -> list[dict]:
    """검색 + <work_dir>/audit/search-log.jsonl 기록. work_dir 기본값은 MDR_WORK_DIR, 없으면 현재 폴더."""
    audit = Path(work_dir or os.environ.get("MDR_WORK_DIR") or ".") / "audit"
    if type == "academic":                               # 백엔드별 로그를 _academic 이 직접 남긴다
        return _academic(query, n, axis, audit)
    try:
        res = _search(query, n, type)
    except Exception as e:
        log_search(query, type, n, None, axis, error=str(e), audit=audit)
        raise
    log_search(query, type, n, res, axis, audit=audit)
    return res


def _search(query: str, n: int, type: str) -> list[dict]:
    backends = _CURATED["type_backends"]
    if type not in backends:
        raise ValueError(f"미지원 --type: {type!r} (지원: {list(backends)})")
    backend = backends[type]["backend"]
    if backend in ("ddg+searx",):
        res = _ddgs(query, n, "news" if type == "news" else "web")
        for layer in (_ddg, _searx):                     # 부족하면 ddg → searx 순으로 보강
            if len(res) >= max(3, n // 2):
                break
            res += [r for r in layer(query, n) if r["url"] not in {x["url"] for x in res}]
        return res[:n]
    if backend == "arxiv":
        return _arxiv(query, n)
    if backend == "sec_edgar":
        return _sec_edgar(query, n)
    raise ValueError(f"백엔드 미구현: {backend}")


def demo() -> None:
    # 미지원 type 은 명시적 실패
    try:
        search("x", type="patent"); assert False
    except ValueError:
        pass
    # uddg 디코드
    assert _decode_ddg("//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&rut=1") == "https://example.com/a"
    assert "ddg+searx" == _CURATED["type_backends"]["web"]["backend"]   # 라벨은 분기 키 — ddgs 는 이 분기 안에서 얹음
    assert (_SEARX["instances"] or _searx("x", 3) == [])                # 빈 목록이면 네트워크 없이 []

    # V22: EDGAR 고정 픽스처 — 실응답 필드는 'ciks'(복수형)뿐. CIK 가 비어 있지 않아야 함(긍정형)
    _get_orig = globals()["_get"]
    fixture = json.dumps({"hits": {"hits": [{"_id": "0001193125-10-068933:d8k.htm",
                          "_source": {"ciks": ["0001318605"], "display_names": ["Tesla, Inc."], "form": "8-K"}}]}})
    globals()["_get"] = lambda url, timeout=12: (200, fixture)
    try:
        r = _sec_edgar("Tesla", 3)
        assert "1318605" in r[0]["url"], r
        assert not r[0]["url"].rstrip().endswith("CIK="), r    # 옛 cik 단수필드 버그면 빈 CIK= 로 끝남
    finally:
        globals()["_get"] = _get_orig

    # V28: 1차 백엔드(ddg) 밑단(_get)이 타임아웃해도 예외가 전파되지 않고 빈 리스트로 강등되는지
    # (_searx 의 인스턴스×백오프 재시도는 느려서 demo 에선 건드리지 않음 — 별도 적대적 케이스에서 검증)
    globals()["_get"] = lambda url, timeout=12: (_ for _ in ()).throw(TimeoutError("stub timeout"))
    try:
        assert _ddg("x", 5) == []
    finally:
        globals()["_get"] = _get_orig

    print(f"[{_now()}] search demo OK (curl_cffi={'Y' if creq else 'N'})")


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
    elif not args or args[0] == "demo":
        demo()
    else:
        q = args[0]
        n = int(args[args.index("--n") + 1]) if "--n" in args else 10
        t = args[args.index("--type") + 1] if "--type" in args else "web"
        axis = args[args.index("--axis") + 1] if "--axis" in args else None
        work = args[args.index("--work") + 1] if "--work" in args else None
        found = search(q, n, t, axis, work)
        for i, r in enumerate(found, 1):
            print(f"{i:2}. [{r['source']}] {r['title'][:70]}\n    {r['url']}")
