"""search.py — 자체 검색 (유료 API 무의존). plan-v2 핵심설계3.

계층: ddgs 다중 백엔드(web=text, news=news) → DuckDuckGo HTML → SearXNG(자체 호스트 등록 시만)
      → 전문 무료 API(arXiv=academic, SEC EDGAR full-text=filing). --type 은 curated-sources.json
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


def _get(url: str, timeout: int = 12) -> tuple[int, str]:
    response = request_bytes(url, timeout=timeout, client=creq,
                             headers={"User-Agent": "Mozilla/5.0"})
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


def _arxiv(query: str, n: int) -> list[dict]:
    q = query.strip()
    if " " in q and not q.startswith('"'):   # 무인용 all: 은 단어별 OR 라 무관 논문이 섞임 → 구문 먼저, 0건이면 AND
        res = _arxiv(f'"{q}"', n)
        if res:
            return res
        q = " AND ".join(f"all:{w}" for w in q.split())
    else:
        q = f"all:{q}"
    url = f"https://export.arxiv.org/api/query?search_query={quote(q, safe=":")}&max_results={n}"
    try:
        _, xml = _get(url, timeout=25)                   # arXiv API 는 느릴 수 있음
        ns = {"a": "http://www.w3.org/2005/Atom"}
        out = []
        for e in ET.fromstring(xml).findall("a:entry", ns):
            out.append({"title": (e.findtext("a:title", "", ns) or "").strip(),
                        "url": (e.findtext("a:id", "", ns) or "").strip(),
                        "snippet": (e.findtext("a:summary", "", ns) or "").strip()[:300],
                        "source": "arxiv"})
        if not out:
            print("  ⚠ arxiv 0건(건너뜀)", file=sys.stderr)
        return out
    except Exception as e:
        print(f"  ⚠ arxiv 실패(건너뜀): {e}", file=sys.stderr)
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
    if not args or args[0] == "demo":
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
