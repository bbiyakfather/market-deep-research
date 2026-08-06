"""search.py — 자체 검색 (유료 API 무의존). plan-v2 핵심설계3.

계층: DuckDuckGo HTML → SearXNG 공개인스턴스 로테이션(헬스체크·백오프) → 전문 무료 API
      (arXiv=academic, SEC EDGAR full-text=filing, Wikipedia). --type 은 curated-sources.json
      의 type_backends 에 있는 것만. 미지원 유형은 명시적 실패.

주의: "검색 완전성 미보장". 에이전트는 내장 WebSearch 와 병행한다.

CLI:
  python search.py demo
  python search.py "쿼리" --n 8 --type web|news|academic|filing
"""
from __future__ import annotations

import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from skill_paths import ASSETS

try:
    from curl_cffi import requests as creq
    from fetch import _CA_BUNDLE, check_url_safe, check_response_ip
except Exception:
    creq = None
    _CA_BUNDLE = None
    def check_url_safe(u): return urlparse(u).hostname
    def check_response_ip(r): pass   # ponytail: urllib 폴백엔 primary_ip 가 없음 — TOCTOU 방어는 curl_cffi 전제

_CURATED = json.loads((ASSETS / "curated-sources.json").read_text(encoding="utf-8"))
_SEARX = json.loads((ASSETS / "searx-instances.json").read_text(encoding="utf-8"))
_BLOCK_MARKERS = tuple(m.lower() for m in _SEARX.get("block_markers", []))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _get(url: str, timeout: int = 12) -> tuple[int, str]:
    check_url_safe(url)
    if creq is None:
        from urllib.request import Request, urlopen
        with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    kw = {"verify": _CA_BUNDLE} if _CA_BUNDLE else {}
    r = creq.get(url, impersonate="chrome", timeout=timeout, **kw)
    check_response_ip(r)                                # V26 — 실접속 IP 사후 재검증(TOCTOU)
    return r.status_code, r.text


# --- 백엔드들 ----------------------------------------------------------------
def is_blocked_page(text: str) -> bool:
    """봇 차단 페이지는 200 으로 온다 — 파싱 0매치를 '결과 없음'과 구분하기 위한 마커 판정.
    판독 실패는 '차단 아님'으로 안전측 처리(cloudscraper 규약)."""
    low = (text or "").lower()
    return any(m in low for m in _BLOCK_MARKERS)


def _ddg(query: str, n: int, blocked: list[str] | None = None) -> list[dict]:
    """DuckDuckGo HTML. 결과 링크는 //duckduckgo.com/l/?uddg=<encoded> 리다이렉트 → 디코드."""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + quote(query)
        _, html = _get(url)
    except Exception as e:                     # 1차 백엔드도 다른 백엔드처럼 실패는 건너뜀(V28)
        print(f"  ⚠ ddg 실패(건너뜀): {e}", file=sys.stderr)
        if blocked is not None:
            blocked.append("ddg:error")
        return []
    if is_blocked_page(html):
        print("  ⚠ ddg 차단 페이지(200) — '결과 없음'이 아니라 차단됨", file=sys.stderr)
        if blocked is not None:
            blocked.append("ddg:blocked")
        return []
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        real = _decode_ddg(href)
        if real:
            out.append({"title": title, "url": real, "snippet": "", "source": "ddg"})
        if len(out) >= n:
            break
    return out


def _decode_ddg(href: str) -> str | None:
    if href.startswith("//"):
        href = "https:" + href
    q = parse_qs(urlparse(href).query)
    if "uddg" in q:
        return unquote(q["uddg"][0])
    return href if href.startswith("http") else None


def _searx(query: str, n: int, blocked: list[str] | None = None) -> list[dict]:
    """공개 SearXNG 로테이션 + 백오프. JSON 미지원/죽은 인스턴스는 다음으로."""
    for inst in _SEARX["instances"]:
        host = urlparse(inst).hostname
        for delay in [0] + _SEARX["backoff_sec"]:
            if delay:
                time.sleep(delay)
            try:
                st, txt = _get(f"{inst}/search?q={quote(query)}&format=json", timeout=_SEARX["timeout_sec"])
            except Exception:
                break                                    # 접속 자체 실패 → 다음 인스턴스
            if st in (429, 503):
                # 레이트리밋은 재시도가 의미 있는 유일한 경우다. 종전에는 여기서도 즉시
                # break 해 backoff_sec 리스트가 한 번도 소비되지 않는 데드코드였다.
                if blocked is not None and f"searx:{host}" not in blocked:
                    blocked.append(f"searx:{host}")
                continue
            if st == 200 and txt.lstrip().startswith("{"):
                try:
                    data = json.loads(txt)
                except json.JSONDecodeError:
                    break
                res = [{"title": r.get("title", ""), "url": r.get("url", ""),
                        "snippet": r.get("content", ""), "source": f"searx:{host}"}
                       for r in data.get("results", [])[:n]]
                if res:
                    return res
            break                                        # 그 밖의 응답은 이 인스턴스 포기
    return []


def _arxiv(query: str, n: int) -> list[dict]:
    url = f"https://export.arxiv.org/api/query?search_query=all:{quote(query)}&max_results={n}"
    try:
        _, xml = _get(url, timeout=25)                   # arXiv API 는 느릴 수 있음
        ns = {"a": "http://www.w3.org/2005/Atom"}
        out = []
        for e in ET.fromstring(xml).findall("a:entry", ns):
            out.append({"title": (e.findtext("a:title", "", ns) or "").strip(),
                        "url": (e.findtext("a:id", "", ns) or "").strip(),
                        "snippet": (e.findtext("a:summary", "", ns) or "").strip()[:300],
                        "source": "arxiv"})
        return out
    except Exception as e:
        print(f"  ⚠ arxiv 실패(건너뜀): {e}", file=sys.stderr)
        return []


def _sec_edgar(query: str, n: int) -> list[dict]:
    url = 'https://efts.sec.gov/LATEST/search-index?q="' + quote(query) + '"'
    try:
        _, txt = _get(url)
        hits = json.loads(txt).get("hits", {}).get("hits", [])[:n]
    except Exception:
        return []
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


def _wikipedia(query: str, n: int, lang: str = "en") -> list[dict]:
    url = f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={quote(query)}&limit={n}&format=json"
    try:
        _, txt = _get(url, timeout=20)
        data = json.loads(txt)
        return [{"title": t, "url": u, "snippet": d, "source": "wikipedia"}
                for t, d, u in zip(data[1], data[2], data[3])]
    except Exception as e:
        print(f"  ⚠ wikipedia 실패(건너뜀): {e}", file=sys.stderr)
        return []


# --- 디스패치 ----------------------------------------------------------------
def search_with_diagnostics(query: str, n: int = 10, type: str = "web") -> dict:
    """{results, blocked_engines}. 빈 결과가 '이 주제에 출처가 없다'인지 '차단당했다'인지
    구분해야 커버리지 공백이 보고서 서술로 굳는 것을 막는다."""
    backends = _CURATED["type_backends"]
    if type not in backends:
        raise ValueError(f"미지원 --type: {type!r} (지원: {list(backends)})")
    backend = backends[type]["backend"]
    blocked: list[str] = []
    if backend in ("ddg+searx",):
        res = _ddg(query, n, blocked)
        if len(res) < max(3, n // 2):                    # 부족하면 SearXNG 보강
            res += [r for r in _searx(query, n, blocked) if r["url"] not in {x["url"] for x in res}]
        res = res[:n]
    elif backend == "arxiv":
        res = _arxiv(query, n)
    elif backend == "sec_edgar":
        res = _sec_edgar(query, n)
    else:
        raise ValueError(f"백엔드 미구현: {backend}")
    if not res and blocked:
        print(f"  ⚠ 결과 0건이지만 차단된 엔진이 있다: {', '.join(blocked)} "
              f"— '출처 없음'으로 결론내지 말 것", file=sys.stderr)
    return {"results": res, "blocked_engines": blocked}


def search(query: str, n: int = 10, type: str = "web") -> list[dict]:
    """호환 유지용 얇은 래퍼 — 진단이 필요하면 search_with_diagnostics 를 쓴다."""
    return search_with_diagnostics(query, n, type)["results"]


def wikipedia(query: str, n: int = 5, lang: str = "en") -> list[dict]:
    return _wikipedia(query, n, lang)


def demo() -> None:
    # 미지원 type 은 명시적 실패
    try:
        search("x", type="patent"); assert False
    except ValueError:
        pass
    # uddg 디코드
    assert _decode_ddg("//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&rut=1") == "https://example.com/a"
    assert "ddg+searx" == _CURATED["type_backends"]["web"]["backend"]

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
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    else:
        q = args[0]
        n = int(args[args.index("--n") + 1]) if "--n" in args else 10
        t = args[args.index("--type") + 1] if "--type" in args else "web"
        for i, r in enumerate(search(q, n, t), 1):
            print(f"{i:2}. [{r['source']}] {r['title'][:70]}\n    {r['url']}")
