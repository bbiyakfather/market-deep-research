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
    from fetch import _CA_BUNDLE, check_url_safe
except Exception:
    creq = None
    _CA_BUNDLE = None
    def check_url_safe(u): return urlparse(u).hostname

_CURATED = json.loads((ASSETS / "curated-sources.json").read_text(encoding="utf-8"))
_SEARX = json.loads((ASSETS / "searx-instances.json").read_text(encoding="utf-8"))


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
    return r.status_code, r.text


# --- 백엔드들 ----------------------------------------------------------------
def _ddg(query: str, n: int) -> list[dict]:
    """DuckDuckGo HTML. 결과 링크는 //duckduckgo.com/l/?uddg=<encoded> 리다이렉트 → 디코드."""
    url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    _, html = _get(url)
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


def _searx(query: str, n: int) -> list[dict]:
    """공개 SearXNG 로테이션 + 백오프. JSON 미지원/죽은 인스턴스는 다음으로."""
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
        cik = (src.get("cik") or [""])[0] if isinstance(src.get("cik"), list) else src.get("cik", "")
        out.append({"title": src.get("display_names", [""])[0] if src.get("display_names") else h.get("_id", ""),
                    "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
                    "snippet": src.get("form", ""), "source": "sec_edgar"})
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
def search(query: str, n: int = 10, type: str = "web") -> list[dict]:
    backends = _CURATED["type_backends"]
    if type not in backends:
        raise ValueError(f"미지원 --type: {type!r} (지원: {list(backends)})")
    backend = backends[type]["backend"]
    if backend in ("ddg+searx",):
        res = _ddg(query, n)
        if len(res) < max(3, n // 2):                    # 부족하면 SearXNG 보강
            res += [r for r in _searx(query, n) if r["url"] not in {x["url"] for x in res}]
        return res[:n]
    if backend == "arxiv":
        return _arxiv(query, n)
    if backend == "sec_edgar":
        return _sec_edgar(query, n)
    raise ValueError(f"백엔드 미구현: {backend}")


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
