"""search.py — market-research-assistant 자체 검색 (유료 API 무의존).

핵심 설계 3(plan-v2) ①: 무료 백엔드 계층 폴백으로 1차출처 후보 URL을 찾는다.

    python search.py "쿼리" [--n 10] [--type web|news|academic|filing] [--json]
    python search.py --selfcheck            # 오프라인 자기검증(네트워크 미사용)

계층 폴백(--type의 백엔드를 curated-sources.json 순서대로, 첫 성공에서 종료):
  ① DuckDuckGo HTML (html.duckduckgo.com/html/ POST)
  ② SearXNG 공개 인스턴스 로테이션 (assets/searx-instances.json; 헬스체크=검색요청,
     실패 시 지수 백오프 기록 후 다음 인스턴스; 인스턴스당 1회)
  ③ 전문 무료 API: --type academic=arXiv, --type filing=SEC EDGAR full-text,
     web 최후단 보조=Wikipedia OpenSearch.

--type 규칙:
  curated-sources.json의 types에 **있는 값만** 허용. 미지원 --type(예: patent)은
  조용히 web으로 떨어지지 않고 **명시적 실패(exit 2)** + 사유 출력.

정책:
  - firecrawl/tavily 등 유료 API 경로 코드 없음(범위 제외).
  - HTTP 요청은 fetch.py의 보안경계/HTTP 계층을 import 재사용(SSRF 차단·리다이렉트
    홉 재검증·크기/MIME 상한). 검색 백엔드도 임의 URL과 동일하게 검증된다.
  - 요청 예산(인스턴스당 1회·전체 상한)과 단순 파일 캐시(OS 임시폴더).

★ 검색 완전성 미보장 ★
  어떤 계층도 "웹 전체"를 검색하지 않는다. 무료 백엔드 로테이션의 부분 결과다.
  조사원은 내장 WebSearch와 병행하고, "못 찾음"을 "존재하지 않음"으로 해석하지 말 것.
"""
from __future__ import annotations

import skill_paths  # noqa: F401  ── import 시 UTF-8 콘솔 부트스트랩(반드시 최상단)
import fetch         # ── 보안경계/HTTP 계층 재사용(_validate_url·_follow·_guarded_get 등)

import argparse
import html
import json
import re
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

INCOMPLETE_NOTICE = (
    "검색 완전성 미보장: 무료 백엔드 로테이션의 부분 결과다. 내장 WebSearch와 병행하고, "
    "'못 찾음'을 '존재하지 않음'으로 해석하지 말 것."
)

# 요청 예산(전체 상한) — 한 번의 검색에서 나가는 총 HTTP 요청 수 상한.
MAX_TOTAL_REQUESTS = 8
# SearXNG 로테이션에서 한 번에 시도할 최대 인스턴스 수(인스턴스당 1회).
MAX_SEARX_TRIES = 3
SEARCH_TIMEOUT_S = 20
CACHE_TTL_S = 3600
# SEC 공정접근 정책: 연락처가 포함된 User-Agent 요구.
SEC_UA = "market-research-assistant/1.0 (research contact: research@example.com)"

_CACHE_DIR = Path(tempfile.gettempdir()) / "mra-search-cache"
_BACKOFF_FILE = _CACHE_DIR / "searx-backoff.json"
_BACKOFF_BASE_S = 300      # 첫 실패 후 5분 제외
_BACKOFF_CAP_S = 6 * 3600  # 상한 6시간


class _Budget:
    """전체 요청 예산 카운터. 초과 시 이후 백엔드는 요청 없이 건너뛴다."""
    def __init__(self, cap: int = MAX_TOTAL_REQUESTS):
        self.cap = cap
        self.used = 0

    def spend(self) -> bool:
        if self.used >= self.cap:
            return False
        self.used += 1
        return True


# ── 자산 로드/검증 ────────────────────────────────────────────────────────
def _assets_dir() -> Path:
    return skill_paths.skill_root() / "assets"


def load_curated(path: Path | None = None) -> dict:
    """curated-sources.json 로드 + 형식 검증. types/domains 필수, 백엔드 이름은 알려진 것만."""
    path = path or (_assets_dir() / "curated-sources.json")
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if "types" not in cfg or "domains" not in cfg:
        raise ValueError("curated-sources.json: 'types'/'domains' 키 필수")
    known = set(_BACKENDS)
    for t, spec in cfg["types"].items():
        backs = spec.get("backends")
        if not isinstance(backs, list) or not backs:
            raise ValueError(f"curated-sources.json: type {t!r} backends 목록 필요")
        for b in backs:
            if b not in known:
                raise ValueError(f"curated-sources.json: type {t!r} 미지원 백엔드 {b!r}")
    return cfg


def load_searx(path: Path | None = None) -> list[dict]:
    """searx-instances.json 로드 + 형식 검증. {instances:[{url, note}]}."""
    path = path or (_assets_dir() / "searx-instances.json")
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    inst = cfg.get("instances")
    if not isinstance(inst, list) or not inst:
        raise ValueError("searx-instances.json: 'instances' 목록 필요")
    for it in inst:
        if not isinstance(it, dict) or not it.get("url", "").startswith("http"):
            raise ValueError(f"searx-instances.json: 잘못된 인스턴스 {it!r}")
    return inst


def backends_for_type(rtype: str, cfg: dict) -> list[str]:
    """--type → 백엔드 순서 목록. 미지원 type은 KeyError(상위에서 exit 2)."""
    return list(cfg["types"][rtype]["backends"])


# ── 백오프 저장(헬스체크: 최근 실패 인스턴스는 잠시 제외) ─────────────────
def _load_backoff() -> dict:
    try:
        return json.loads(_BACKOFF_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_backoff(data: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _BACKOFF_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass  # 캐시는 best-effort — 쓰기 실패해도 검색 자체는 진행


def _backoff_active(url: str, store: dict, now: float | None = None) -> bool:
    now = now if now is not None else time.time()
    rec = store.get(url)
    if not rec:
        return False
    wait = min(_BACKOFF_BASE_S * (2 ** max(0, rec.get("count", 1) - 1)), _BACKOFF_CAP_S)
    return now < rec.get("fail_at", 0) + wait


def _record_fail(url: str, store: dict, now: float | None = None) -> None:
    now = now if now is not None else time.time()
    rec = store.get(url, {"count": 0})
    store[url] = {"fail_at": now, "count": rec.get("count", 0) + 1}


def _record_ok(url: str, store: dict) -> None:
    store.pop(url, None)  # 성공하면 백오프 해제


# ── 단순 파일 캐시(동일 쿼리 반복 시 rate-limit 유발 방지) ────────────────
def _cache_key(query: str, rtype: str, n: int) -> str:
    import hashlib
    raw = f"{rtype}|{n}|{query}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _cache_get(key: str):
    f = _CACHE_DIR / f"q_{key}.json"
    try:
        blob = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    if time.time() - blob.get("at", 0) > CACHE_TTL_S:
        return None
    return blob.get("payload")


def _cache_put(key: str, payload: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"q_{key}.json").write_text(
            json.dumps({"at": time.time(), "payload": payload}), encoding="utf-8")
    except Exception:
        pass


# ── HTTP: GET은 fetch._guarded_get 직접, POST만 얇은 재사용 래퍼 ──────────
def _guarded_post(url: str, data: dict, headers: dict | None = None,
                  timeout: int = SEARCH_TIMEOUT_S) -> dict:
    """fetch.py의 보안경계(_validate_url·_follow·_read_capped·_mime_category) 재사용 POST.

    GET용 fetch._guarded_get과 동일한 SSRF/리다이렉트/크기/MIME 검증을 거친다.
    """
    if fetch._creq is None:
        raise fetch.FetchError(fetch.TIMEOUT, "curl_cffi 미설치")
    sess = fetch._creq.Session()
    hdrs = dict(fetch._BASE_HEADERS)
    hdrs.update(headers or {})

    def _req(u):
        return sess.post(u, data=data, headers=hdrs, timeout=timeout,
                         impersonate="chrome", allow_redirects=False, stream=True)

    resp, chain = fetch._follow(url, _req)  # 홉마다 _validate_url 재검증(SSRF 차단)
    try:
        status = resp.status_code
        ctype = resp.headers.get("content-type") or resp.headers.get("Content-Type") or ""
        cat = fetch._mime_category(ctype)
        if cat is None:
            raise fetch.FetchError(fetch.BAD_MIME, ctype or "(none)")
        raw = fetch._read_capped(resp.iter_content(chunk_size=fetch.CHUNK))
    finally:
        resp.close()
    return {"raw": raw, "final_url": str(getattr(resp, "url", url)) or url,
            "http_status": status, "content_type": ctype, "mime_cat": cat}


def _text(raw: bytes, ctype: str) -> str:
    return fetch._decode(raw, ctype)


# ── 백엔드별 파서(순수 함수 — 셀프체크에서 fixture로 단위검증) ─────────────
_DDG_ANCHOR = re.compile(
    r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
_DDG_SNIPPET = re.compile(
    r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return html.unescape(_TAG.sub("", s or "")).strip()


def _ddg_real_url(href: str) -> str:
    """DDG 결과 href는 //duckduckgo.com/l/?uddg=<인코딩된URL> 리다이렉트일 수 있다."""
    if href.startswith("//"):
        href = "https:" + href
    p = urlparse(href)
    if "duckduckgo.com" in (p.netloc or "") and p.path.startswith("/l/"):
        q = parse_qs(p.query)
        if "uddg" in q and q["uddg"]:
            return q["uddg"][0]
    return href


def parse_ddg(html_text: str, n: int) -> list[dict]:
    anchors = _DDG_ANCHOR.findall(html_text)
    snippets = _DDG_SNIPPET.findall(html_text)
    out = []
    for i, (href, title) in enumerate(anchors):
        url = _ddg_real_url(href)
        if not url.startswith("http"):
            continue
        snip = _strip_html(snippets[i]) if i < len(snippets) else ""
        out.append({"title": _strip_html(title), "url": url,
                    "snippet": snip, "backend": "ddg"})
        if len(out) >= n:
            break
    return out


def parse_searxng(body: str, n: int) -> list[dict]:
    data = json.loads(body)
    out = []
    for r in data.get("results", []):
        url = r.get("url", "")
        if not url.startswith("http"):
            continue
        out.append({"title": (r.get("title") or "").strip(), "url": url,
                    "snippet": (r.get("content") or "").strip(), "backend": "searxng"})
        if len(out) >= n:
            break
    return out


_ATOM = "{http://www.w3.org/2005/Atom}"


def parse_arxiv(xml_text: str, n: int) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall(f"{_ATOM}entry"):
        title = (e.findtext(f"{_ATOM}title") or "").strip()
        url = (e.findtext(f"{_ATOM}id") or "").strip()
        summary = " ".join((e.findtext(f"{_ATOM}summary") or "").split())
        if not url.startswith("http"):
            continue
        out.append({"title": title, "url": url,
                    "snippet": summary[:300], "backend": "arxiv"})
        if len(out) >= n:
            break
    return out


def parse_wikipedia(body: str, n: int) -> list[dict]:
    # OpenSearch 응답: [query, [titles], [descriptions], [urls]]
    data = json.loads(body)
    if not (isinstance(data, list) and len(data) >= 4):
        return []
    titles, descs, urls = data[1], data[2], data[3]
    out = []
    for i, url in enumerate(urls):
        if not str(url).startswith("http"):
            continue
        out.append({"title": titles[i] if i < len(titles) else "", "url": url,
                    "snippet": descs[i] if i < len(descs) else "", "backend": "wikipedia"})
        if len(out) >= n:
            break
    return out


def parse_sec_edgar(body: str, n: int) -> list[dict]:
    data = json.loads(body)
    hits = data.get("hits", {}).get("hits", [])
    out = []
    for h in hits:
        src = h.get("_source", {})
        _id = h.get("_id", "")  # "<accession-with-dashes>:<primary_doc>"
        names = src.get("display_names") or []
        form = src.get("file_type") or (src.get("root_forms") or [""])[0]
        date = src.get("file_date", "")
        url = _sec_url(_id, src)
        title = f"{', '.join(names)} — {form} ({date})".strip(" —")
        out.append({"title": title or _id, "url": url,
                    "snippet": f"form={form} date={date}", "backend": "sec_edgar"})
        if len(out) >= n:
            break
    return out


def _sec_url(_id: str, src: dict) -> str:
    """EDGAR FTS _id로부터 문서 URL을 best-effort 구성. 실패 시 FTS UI 링크."""
    try:
        accession, doc = _id.split(":", 1)
        acc_nodash = accession.replace("-", "")
        cik = src.get("cik")
        if isinstance(cik, list):
            cik = cik[0] if cik else None
        if cik:
            cik_num = str(int(str(cik)))  # 선행 0 제거
            return f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_nodash}/{doc}"
    except Exception:
        pass
    return "https://efts.sec.gov/LATEST/search-index?q=" + quote_plus(_id)


# ── 백엔드 실행기(네트워크) ───────────────────────────────────────────────
def _run_ddg(query: str, n: int, budget: _Budget, log: list) -> list[dict]:
    if not budget.spend():
        return []
    try:
        r = _guarded_post("https://html.duckduckgo.com/html/", data={"q": query})
        results = parse_ddg(_text(r["raw"], r["content_type"]), n)
        log.append(f"ddg: http {r['http_status']}, {len(results)}건")
        return results
    except fetch.FetchError as e:
        log.append(f"ddg: 실패({e.code}: {e.detail})")
        return []
    except Exception as e:
        log.append(f"ddg: 실패({type(e).__name__}: {e})")
        return []


def _run_searxng(query: str, n: int, budget: _Budget, log: list) -> list[dict]:
    instances = load_searx()
    store = _load_backoff()
    tries = 0
    try:
        for it in instances:
            base = it["url"].rstrip("/")
            if tries >= MAX_SEARX_TRIES:
                break
            if _backoff_active(base, store):
                log.append(f"searxng[{base}]: 백오프 중 건너뜀")
                continue
            if not budget.spend():
                log.append("searxng: 요청 예산 소진, 중단")
                break
            tries += 1
            url = (base + "/search?q=" + quote_plus(query) +
                   "&format=json&safesearch=0&language=en")
            try:
                r = fetch._guarded_get(url, {"Accept": "application/json"},
                                       timeout=SEARCH_TIMEOUT_S)
                if r["mime_cat"] != "json":
                    raise fetch.FetchError(fetch.BAD_MIME, r["content_type"])
                results = parse_searxng(_text(r["raw"], r["content_type"]), n)
                if results:
                    _record_ok(base, store)
                    log.append(f"searxng[{base}]: http {r['http_status']}, {len(results)}건")
                    return results
                _record_fail(base, store)
                log.append(f"searxng[{base}]: 0건 → 백오프 기록, 다음 인스턴스")
            except fetch.FetchError as e:
                _record_fail(base, store)
                log.append(f"searxng[{base}]: 실패({e.code}) → 백오프 기록, 다음 인스턴스")
            except Exception as e:
                _record_fail(base, store)
                log.append(f"searxng[{base}]: 실패({type(e).__name__}) → 백오프 기록, 다음 인스턴스")
        return []
    finally:
        _save_backoff(store)


def _run_wikipedia(query: str, n: int, budget: _Budget, log: list) -> list[dict]:
    if not budget.spend():
        return []
    url = ("https://en.wikipedia.org/w/api.php?action=opensearch&search=" +
           quote_plus(query) + f"&limit={n}&namespace=0&format=json")
    try:
        r = fetch._guarded_get(url, {"Accept": "application/json"}, timeout=SEARCH_TIMEOUT_S)
        results = parse_wikipedia(_text(r["raw"], r["content_type"]), n)
        log.append(f"wikipedia: http {r['http_status']}, {len(results)}건")
        return results
    except Exception as e:
        log.append(f"wikipedia: 실패({type(e).__name__}: {e})")
        return []


def _run_arxiv(query: str, n: int, budget: _Budget, log: list) -> list[dict]:
    if not budget.spend():
        return []
    url = ("https://export.arxiv.org/api/query?search_query=all:" +
           quote_plus(query) + f"&start=0&max_results={n}")
    try:
        r = fetch._guarded_get(url, {"Accept": "application/atom+xml"}, timeout=SEARCH_TIMEOUT_S)
        results = parse_arxiv(_text(r["raw"], r["content_type"]), n)
        log.append(f"arxiv: http {r['http_status']}, {len(results)}건")
        return results
    except Exception as e:
        log.append(f"arxiv: 실패({type(e).__name__}: {e})")
        return []


def _run_sec_edgar(query: str, n: int, budget: _Budget, log: list) -> list[dict]:
    if not budget.spend():
        return []
    url = "https://efts.sec.gov/LATEST/search-index?q=" + quote_plus(query)
    try:
        r = fetch._guarded_get(url, {"Accept": "application/json", "User-Agent": SEC_UA},
                               timeout=SEARCH_TIMEOUT_S)
        results = parse_sec_edgar(_text(r["raw"], r["content_type"]), n)
        log.append(f"sec_edgar: http {r['http_status']}, {len(results)}건")
        return results
    except Exception as e:
        log.append(f"sec_edgar: 실패({type(e).__name__}: {e})")
        return []


_BACKENDS = {
    "ddg": _run_ddg,
    "searxng": _run_searxng,
    "wikipedia": _run_wikipedia,
    "arxiv": _run_arxiv,
    "sec_edgar": _run_sec_edgar,
}


# ── 오케스트레이션 ───────────────────────────────────────────────────────
def search(query: str, rtype: str = "web", n: int = 10, cfg: dict | None = None,
           use_cache: bool = True) -> dict:
    """백엔드를 curated 순서대로 시도, 첫 성공에서 종료. 반환 메타 dict."""
    cfg = cfg or load_curated()
    backends = backends_for_type(rtype, cfg)  # 미지원 type이면 KeyError

    key = _cache_key(query, rtype, n)
    if use_cache:
        cached = _cache_get(key)
        if cached is not None:
            cached["from_cache"] = True
            return cached

    budget = _Budget()
    log: list[str] = []
    results: list[dict] = []
    responded = None
    for name in backends:
        runner = _BACKENDS[name]
        results = runner(query, n, budget, log)
        if results:
            responded = name
            break

    payload = {
        "query": query, "type": rtype, "backends_order": backends,
        "responded_backend": responded, "count": len(results),
        "results": results, "log": log, "budget_used": budget.used,
        "notice": INCOMPLETE_NOTICE, "from_cache": False,
    }
    if use_cache and results:
        _cache_put(key, payload)
    return payload


# ── 오프라인 셀프체크(네트워크 미사용) ───────────────────────────────────
def _selfcheck() -> int:
    # (1) JSON 2종 로드·형식 검증
    cfg = load_curated()
    inst = load_searx()
    assert cfg["types"] and cfg["domains"], "curated 구조"
    assert len(inst) >= 5, f"searx 인스턴스 부족: {len(inst)}"

    # (2) 백엔드 라우팅
    assert backends_for_type("web", cfg) == ["ddg", "searxng", "wikipedia"]
    assert backends_for_type("news", cfg) == ["ddg", "searxng"]
    assert backends_for_type("academic", cfg) == ["arxiv"]
    assert backends_for_type("filing", cfg) == ["sec_edgar"]

    # (3) 미지원 --type → CLI exit 2
    rc = main(["dummy query", "--type", "patent"])
    assert rc == 2, f"미지원 type exit 2 기대, got {rc}"

    # (4) 파서 단위검증(fixture — 네트워크 없음)
    ddg_html = (
        '<a rel="nofollow" class="result__a" '
        'href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&rut=x">'
        'Title <b>One</b></a>'
        '<a class="result__snippet" href="#">Snippet <b>one</b> here</a>'
        '<a rel="nofollow" class="result__a" href="https://example.org/b">T2</a>'
        '<a class="result__snippet" href="#">Snip two</a>')
    d = parse_ddg(ddg_html, 10)
    assert len(d) == 2, d
    assert d[0]["url"] == "https://example.com/a", d[0]
    assert d[0]["title"] == "Title One" and d[0]["snippet"] == "Snippet one here", d[0]
    assert d[1]["url"] == "https://example.org/b", d[1]

    sx = parse_searxng(json.dumps({"results": [
        {"title": "A", "url": "https://a.com", "content": "sa"},
        {"title": "B", "url": "ftp://skip", "content": "x"},
        {"title": "C", "url": "https://c.com", "content": "sc"}]}), 10)
    assert [r["url"] for r in sx] == ["https://a.com", "https://c.com"], sx
    assert sx[0]["backend"] == "searxng"

    ax = parse_arxiv(
        f'<feed xmlns="http://www.w3.org/2005/Atom">'
        f'<entry><title>Quantum</title><id>http://arxiv.org/abs/1234.5678</id>'
        f'<summary>A  paper\non  quantum</summary></entry></feed>', 10)
    assert ax[0]["url"] == "http://arxiv.org/abs/1234.5678", ax
    assert ax[0]["snippet"] == "A paper on quantum", ax[0]

    wk = parse_wikipedia(json.dumps(
        ["q", ["Apple", "Apple Inc"], ["d1", "d2"],
         ["https://en.wikipedia.org/wiki/Apple", "https://en.wikipedia.org/wiki/Apple_Inc"]]), 10)
    assert len(wk) == 2 and wk[0]["backend"] == "wikipedia", wk

    sec = parse_sec_edgar(json.dumps({"hits": {"hits": [
        {"_id": "0000320193-23-000106:aapl-20230930.htm",
         "_source": {"display_names": ["Apple Inc. (AAPL)"], "file_type": "10-K",
                     "file_date": "2023-11-03", "cik": ["0000320193"]}}]}}), 10)
    assert sec[0]["url"] == \
        "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm", sec
    assert "Apple" in sec[0]["title"] and sec[0]["backend"] == "sec_edgar"
    # cik 없으면 FTS UI 폴백
    sec2 = parse_sec_edgar(json.dumps({"hits": {"hits": [
        {"_id": "acc:doc.htm", "_source": {"display_names": ["X"], "file_type": "8-K"}}]}}), 10)
    assert sec2[0]["url"].startswith("https://efts.sec.gov/LATEST/search-index?q="), sec2

    # (5) 백오프 상태기계(시간 주입 — 네트워크 없음)
    store: dict = {}
    assert not _backoff_active("https://x", store, now=1000.0)
    _record_fail("https://x", store, now=1000.0)
    assert _backoff_active("https://x", store, now=1000.0 + 10)          # 5분 내 = 제외
    assert not _backoff_active("https://x", store, now=1000.0 + 301)     # 5분 후 = 해제
    _record_ok("https://x", store)
    assert "https://x" not in store

    # (6) 예산 카운터
    b = _Budget(cap=2)
    assert b.spend() and b.spend() and not b.spend()

    print("SELFCHECK OK")
    return 0


# ── 출력 + CLI ───────────────────────────────────────────────────────────
def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for r in payload["results"]:
        print(json.dumps(r, ensure_ascii=False))  # JSONL
    who = payload["responded_backend"] or "(없음)"
    print(f"\n[backend={who}] {payload['count']}건 · 요청 {payload['budget_used']}회"
          + (" · cache" if payload.get("from_cache") else ""), file=sys.stderr)
    for line in payload["log"]:
        print("  - " + line, file=sys.stderr)
    print(INCOMPLETE_NOTICE, file=sys.stderr)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="search", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("query", nargs="?", help="검색 쿼리")
    p.add_argument("--n", type=int, default=10, help="원하는 결과 수(기본 10)")
    p.add_argument("--type", default="web", help="web|news|academic|filing (curated-sources.json 매핑)")
    p.add_argument("--no-cache", action="store_true", help="파일 캐시 무시")
    p.add_argument("--json", action="store_true", help="메타 포함 JSON 객체로 출력")
    p.add_argument("--selfcheck", action="store_true", help="오프라인 자기검증")
    args = p.parse_args(argv)

    if args.selfcheck:
        return _selfcheck()
    if not args.query:
        p.error("검색 쿼리가 필요합니다 (또는 --selfcheck)")

    try:
        cfg = load_curated()
    except Exception as e:
        print(f"curated-sources.json 로드 실패: {e}", file=sys.stderr)
        return 2

    if args.type not in cfg["types"]:
        supported = ", ".join(sorted(cfg["types"]))
        print(f"미지원 --type {args.type!r}. 지원: {supported}. "
              f"(유료/미배선 백엔드는 조용히 web으로 떨어지지 않고 명시적으로 실패한다)",
              file=sys.stderr)
        return 2

    payload = search(args.query, rtype=args.type, n=args.n, cfg=cfg,
                     use_cache=not args.no_cache)
    _emit(payload, args.json)
    return 0 if payload["results"] else 1


if __name__ == "__main__":
    sys.exit(main())
