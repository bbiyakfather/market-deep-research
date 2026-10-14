"""search.py — 자체 검색 (유료 API 무의존). plan-v2 핵심설계3.

계층: DuckDuckGo HTML → SearXNG(환경변수 MDR_SEARX_URL 이 있으면 그 주소부터,
      없으면 공개인스턴스 로테이션) → 전문 무료 API
      (arXiv=academic, SEC EDGAR full-text=filing, Wikipedia). --type 은 curated-sources.json
      의 type_backends 에 있는 것만. 미지원 유형은 명시적 실패.

백엔드가 막히거나 죽으면 빈 목록만 주지 않는다. search_report() 가 결과와 함께
백엔드별 status(ok|empty|blocked|error) 를 돌려준다. search() 는 그 결과 목록만 받는 래퍼다.

주의: "검색 완전성 미보장". 에이전트는 내장 WebSearch 와 병행한다.

CLI:
  python search.py demo
  python search.py health
  python search.py "쿼리" --n 8 --type web|news|academic|filing [--json]
  결과 0건이고 시도한 백엔드가 전부 blocked|error 이면 종료 코드 2.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import parse_qs, parse_qsl, quote, unquote, urlencode, urlparse, urlunparse

from skill_paths import ASSETS

from fetch import creq, request_bytes, response_text

_CURATED = json.loads((ASSETS / "curated-sources.json").read_text(encoding="utf-8"))
_SEARX = json.loads((ASSETS / "searx-instances.json").read_text(encoding="utf-8"))

# 한 번의 _searx 호출이 죽은 인스턴스 백오프에 묶여 몇 분을 쓰지 않게 하는 상한.
_SEARX_DEADLINE_SEC = 30
_DROP_QUERY = {"fbclid", "gclid"}
# 본문이 캡차·anomaly·챌린지 페이지인지 보는 표지. 맨 단어 "challenge" 는 정상 문서에도 나온다.
_BLOCK_BODY = re.compile(
    r"captcha|anomaly|cf-challenge|g-recaptcha|hcaptcha|challenge-form",
    re.IGNORECASE,
)
_DDG_LINK = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.S,
)
_DDG_CLASS = re.compile(r'class="result__a"')


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _get(url: str, timeout: int = 12) -> tuple[int, str]:
    response = request_bytes(url, timeout=timeout, client=creq,
                             headers={"User-Agent": "Mozilla/5.0"})
    return response["status"], response_text(response)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None                                      # urllib 가 3xx 를 HTTPError 로 올린다


_NO_REDIRECT = urllib.request.build_opener(_NoRedirect)
_TRUSTED_MAX_BYTES = 8 * 1024 * 1024


def _get_trusted(url: str, timeout: int = 12) -> tuple[int, str]:
    """MDR_SEARX_URL 전용. 운영자가 지정한 주소만 표준 라이브러리로 직접 연다.

    fetch.request_bytes 는 사설 IP·localhost 를 막는다. 그 방어는 건드리지 않고,
    이 함수로 들어온 URL 만 우회한다.
    """
    if urlparse(url).scheme not in ("http", "https"):   # urllib 는 file:// 도 연다
        raise ValueError(f"MDR_SEARX_URL 은 http(s) 만 허용: {url[:60]}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        # 운영자가 믿는다고 한 것은 이 주소 하나다. Location 으로 다른 호스트·내부망에 가지 않는다.
        with _NO_REDIRECT.open(req, timeout=timeout) as resp:
            raw = resp.read(_TRUSTED_MAX_BYTES)
            code = getattr(resp, "status", None) or resp.getcode()
            return int(code), raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read(_TRUSTED_MAX_BYTES) if exc.fp is not None else b""
        return int(exc.code), raw.decode("utf-8", errors="replace")


def _detail_exc(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".replace("\n", " ").strip()
    return text[:200]


def _backend(name: str, status: str, count: int, detail: str) -> dict:
    return {"name": name, "status": status, "count": count, "detail": detail}


def _body_blocked(body: str) -> bool:
    return bool(body and _BLOCK_BODY.search(body))


def _is_retryable(status: int) -> bool:
    """429·5xx 만 같은 인스턴스에서 다시 시도한다. 예외·403 은 해당하지 않는다."""
    return status == 429 or 500 <= status <= 599


def _normalize_url(url: str) -> str:
    """중복 판정용 키. 저장된 url 필드는 바꾸지 않는다.

    호스트 소문자, fragment 제거, utm_*·fbclid·gclid 제거, 끝 슬래시 정리.
    남은 쿼리 순서가 달라도 같게 보도록 키만 정렬한다.
    """
    raw = (url or "").strip()
    parts = urlparse(raw)
    if not parts.netloc:
        return raw
    kept = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        low = key.lower()
        if low.startswith("utm_") or low in _DROP_QUERY:
            continue
        kept.append((key, value))
    kept.sort()
    return urlunparse((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        "",
        urlencode(kept),
        "",
    ))


def _merge_results(primary: list[dict], extra: list[dict], n: int) -> list[dict]:
    out = list(primary)
    seen = {_normalize_url(r["url"]) for r in out if r.get("url")}
    for item in extra:
        key = _normalize_url(item["url"]) if item.get("url") else ""
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(item)
        if len(out) >= n:
            break
    return out[:n]


# --- 백엔드들 ----------------------------------------------------------------
def _parse_ddg(html: str, n: int) -> tuple[list[dict], int]:
    """결과 링크는 //duckduckgo.com/l/?uddg=<encoded> 리다이렉트 → 디코드."""
    html = html or ""
    raw_hits = len(_DDG_CLASS.findall(html))
    out = []
    for match in _DDG_LINK.finditer(html):
        href, title = match.group(1), re.sub(r"<[^>]+>", "", match.group(2)).strip()
        real = _decode_ddg(href)
        if real:
            out.append({"title": title, "url": real, "snippet": "", "source": "ddg"})
        if len(out) >= n:
            break
    return out, raw_hits


def _classify_ddg(status: int, html: str, n: int) -> tuple[list[dict], dict]:
    results, raw_hits = _parse_ddg(html, n)
    if status in (403, 429):
        return [], _backend("ddg", "blocked", 0, f"http {status}")
    if 500 <= status <= 599:
        return [], _backend("ddg", "error", 0, f"http {status}")
    if results and status == 200:
        return results, _backend("ddg", "ok", len(results), f"http {status}")
    # 200 인데 result__a 가 없으면 캡차/anomaly 페이지와 진짜 0건을 가른다.
    if raw_hits == 0 and _body_blocked(html):
        return [], _backend("ddg", "blocked", 0, f"http {status} captcha")
    if status == 200 and raw_hits == 0:
        return [], _backend("ddg", "empty", 0, "http 200")
    if raw_hits and not results:
        return [], _backend("ddg", "error", 0, "parse")
    if _body_blocked(html):
        return [], _backend("ddg", "blocked", 0, f"http {status} captcha")
    if results:
        return results, _backend("ddg", "ok", len(results), f"http {status}")
    return [], _backend("ddg", "error", 0, f"http {status}")


def _ddg_report(query: str, n: int) -> tuple[list[dict], dict]:
    try:
        url = "https://html.duckduckgo.com/html/?q=" + quote(query)
        status, html = _get(url)
    except Exception as exc:               # 1차 백엔드도 다른 백엔드처럼 실패는 건너뜀(V28)
        print(f"  ⚠ ddg 실패(건너뜀): {exc}", file=sys.stderr)
        return [], _backend("ddg", "error", 0, _detail_exc(exc))
    return _classify_ddg(status, html, n)


def _ddg(query: str, n: int) -> list[dict]:
    results, _be = _ddg_report(query, n)
    return results


def _decode_ddg(href: str) -> str | None:
    if href.startswith("//"):
        href = "https:" + href
    parsed = parse_qs(urlparse(href).query)
    if "uddg" in parsed:
        return unquote(parsed["uddg"][0])
    return href if href.startswith("http") else None


def _searx_targets() -> list[tuple[str, bool]]:
    """(base_url, trusted). trusted 면 urllib 직통, 아니면 fetch 경계."""
    raw = os.environ.get("MDR_SEARX_URL", "")
    trusted = [(part.strip().rstrip("/"), True) for part in raw.split(",") if part.strip()]
    public = [(item.rstrip("/"), False) for item in _SEARX.get("instances", [])]
    return trusted + public


def _judge_searx(status: int, txt: str, n: int, host: str) -> tuple[str, str, list[dict]]:
    if status in (403, 429):
        return "blocked", f"http {status}", []
    if 500 <= status <= 599:
        return "error", f"http {status}", []
    body = txt or ""
    if status == 200 and body.lstrip().startswith("{"):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return "error", "parse", []
        rows = data.get("results", []) if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return "error", "parse", []
        results = []
        for row in rows[:n]:
            if not isinstance(row, dict):
                continue
            results.append({
                "title": row.get("title", "") or "",
                "url": row.get("url", "") or "",
                "snippet": row.get("content", "") or "",
                "source": f"searx:{host}",
            })
        if results:
            return "ok", f"http {status}", results
        if _body_blocked(body):
            return "blocked", f"http {status} captcha", []
        return "empty", f"http {status}", []
    if _body_blocked(body):
        return "blocked", f"http {status} captcha", []
    if status == 200:
        return "error", "parse", []
    return "error", f"http {status}", []


def _aggregate_searx(attempts: list[dict], results: list[dict]) -> dict:
    if not attempts:
        return _backend("searx", "error", 0, "시도 없음")
    detail = "; ".join(f"{item['host']}: {item['detail']}" for item in attempts)
    if results:
        return _backend("searx", "ok", len(results), detail)
    if any(item["status"] == "empty" for item in attempts):
        return _backend("searx", "empty", 0, detail)
    if any(item["status"] == "blocked" for item in attempts):
        return _backend("searx", "blocked", 0, detail)
    return _backend("searx", "error", 0, detail)


def _searx_report(query: str, n: int) -> tuple[list[dict], dict]:
    """공개·자체 SearXNG. 429·5xx 만 백오프 재시도. 예외는 즉시 다음 인스턴스.

    호출 전체는 _SEARX_DEADLINE_SEC 를 넘기지 않는다.
    """
    deadline = time.monotonic() + _SEARX_DEADLINE_SEC
    attempts: list[dict] = []
    found: list[dict] = []
    backoff = [int(item) for item in _SEARX.get("backoff_sec", [1, 2, 4])]
    timeout = int(_SEARX.get("timeout_sec", 10))
    for base, trusted in _searx_targets():
        if time.monotonic() >= deadline:
            break
        host = urlparse(base).hostname or base
        getter = _get_trusted if trusted else _get
        last: tuple[str, str, list[dict]] | None = None
        stop_all = False
        for idx, delay in enumerate([0, *backoff]):
            now = time.monotonic()
            if now >= deadline or (delay and now + delay > deadline):
                stop_all = True
                break
            if delay:
                time.sleep(delay)
            url = f"{base}/search?q={quote(query)}&format=json"
            try:
                status, txt = getter(url, timeout=timeout)
            except Exception as exc:
                last = ("error", _detail_exc(exc), [])
                break
            label, detail, parsed = _judge_searx(status, txt, n, host)
            last = (label, detail, parsed)
            if parsed or not _is_retryable(status) or idx == len(backoff):
                break
        if last is not None:
            label, detail, parsed = last
            attempts.append({
                "host": host, "status": label, "detail": detail, "count": len(parsed),
            })
            if parsed:
                found = parsed
                break
        if stop_all:
            break
    trimmed = found[:n]
    return trimmed, _aggregate_searx(attempts, trimmed)


def _searx(query: str, n: int) -> list[dict]:
    results, _be = _searx_report(query, n)
    return results


def _arxiv_report(query: str, n: int) -> tuple[list[dict], dict]:
    url = f"https://export.arxiv.org/api/query?search_query=all:{quote(query)}&max_results={n}"
    try:
        status, xml = _get(url, timeout=25)             # arXiv API 는 느릴 수 있음
    except Exception as exc:
        print(f"  ⚠ arxiv 실패(건너뜀): {exc}", file=sys.stderr)
        return [], _backend("arxiv", "error", 0, _detail_exc(exc))
    if status in (403, 429):
        return [], _backend("arxiv", "blocked", 0, f"http {status}")
    if 500 <= status <= 599:
        return [], _backend("arxiv", "error", 0, f"http {status}")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        if _body_blocked(xml):
            return [], _backend("arxiv", "blocked", 0, f"http {status} captcha")
        return [], _backend("arxiv", "error", 0, "parse")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for entry in root.findall("a:entry", ns):
        out.append({
            "title": (entry.findtext("a:title", "", ns) or "").strip(),
            "url": (entry.findtext("a:id", "", ns) or "").strip(),
            "snippet": (entry.findtext("a:summary", "", ns) or "").strip()[:300],
            "source": "arxiv",
        })
        if len(out) >= n:
            break
    if out:
        return out, _backend("arxiv", "ok", len(out), f"http {status}")
    if _body_blocked(xml):
        return [], _backend("arxiv", "blocked", 0, f"http {status} captcha")
    if status == 200:
        return [], _backend("arxiv", "empty", 0, f"http {status}")
    return [], _backend("arxiv", "error", 0, f"http {status}")


def _arxiv(query: str, n: int) -> list[dict]:
    results, _be = _arxiv_report(query, n)
    return results


def _sec_edgar_report(query: str, n: int) -> tuple[list[dict], dict]:
    url = 'https://efts.sec.gov/LATEST/search-index?q="' + quote(query) + '"'
    try:
        status, txt = _get(url)
    except Exception as exc:
        print(f"  ⚠ sec_edgar 실패(건너뜀): {exc}", file=sys.stderr)
        return [], _backend("sec_edgar", "error", 0, _detail_exc(exc))
    if status in (403, 429):
        return [], _backend("sec_edgar", "blocked", 0, f"http {status}")
    if 500 <= status <= 599:
        return [], _backend("sec_edgar", "error", 0, f"http {status}")
    try:
        data = json.loads(txt)
        hits = data.get("hits", {}).get("hits", [])
    except (json.JSONDecodeError, AttributeError):
        if _body_blocked(txt):
            return [], _backend("sec_edgar", "blocked", 0, f"http {status} captcha")
        return [], _backend("sec_edgar", "error", 0, "parse")
    if not isinstance(hits, list):
        return [], _backend("sec_edgar", "error", 0, "parse")
    out = []
    for hit in hits[:n]:
        if not isinstance(hit, dict):
            continue
        src = hit.get("_source", {}) or {}
        ciks = src.get("ciks") or []                    # V22 — 실응답 필드는 복수형 'ciks' 뿐(단수 'cik' 없음)
        cik = ciks[0] if ciks else ""
        acc, _, fname = (hit.get("_id") or "").partition(":")   # accession:filename → 공시 문서 직행 URL
        if cik and acc and fname:
            doc_url = (f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0') or '0'}/"
                       f"{acc.replace('-', '')}/{fname}")
        else:
            doc_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
        names = src.get("display_names")
        title = names[0] if names else hit.get("_id", "")
        out.append({"title": title, "url": doc_url, "snippet": src.get("form", ""), "source": "sec_edgar"})
    if out:
        return out, _backend("sec_edgar", "ok", len(out), f"http {status}")
    if _body_blocked(txt):
        return [], _backend("sec_edgar", "blocked", 0, f"http {status} captcha")
    if status == 200:
        return [], _backend("sec_edgar", "empty", 0, f"http {status}")
    return [], _backend("sec_edgar", "error", 0, f"http {status}")


def _sec_edgar(query: str, n: int) -> list[dict]:
    results, _be = _sec_edgar_report(query, n)
    return results


def _wikipedia_report(query: str, n: int, lang: str = "en") -> tuple[list[dict], dict]:
    url = (f"https://{lang}.wikipedia.org/w/api.php?action=opensearch"
           f"&search={quote(query)}&limit={n}&format=json")
    try:
        status, txt = _get(url, timeout=20)
    except Exception as exc:
        print(f"  ⚠ wikipedia 실패(건너뜀): {exc}", file=sys.stderr)
        return [], _backend("wikipedia", "error", 0, _detail_exc(exc))
    if status in (403, 429):
        return [], _backend("wikipedia", "blocked", 0, f"http {status}")
    if 500 <= status <= 599:
        return [], _backend("wikipedia", "error", 0, f"http {status}")
    try:
        data = json.loads(txt)
    except json.JSONDecodeError:
        if _body_blocked(txt):
            return [], _backend("wikipedia", "blocked", 0, f"http {status} captcha")
        return [], _backend("wikipedia", "error", 0, "parse")
    if not isinstance(data, list) or len(data) < 4:
        return [], _backend("wikipedia", "error", 0, "parse")
    out = [{"title": title, "url": link, "snippet": desc, "source": "wikipedia"}
           for title, desc, link in zip(data[1], data[2], data[3])]
    out = out[:n]
    if out:
        return out, _backend("wikipedia", "ok", len(out), f"http {status}")
    if _body_blocked(txt):
        return [], _backend("wikipedia", "blocked", 0, f"http {status} captcha")
    if status == 200:
        return [], _backend("wikipedia", "empty", 0, f"http {status}")
    return [], _backend("wikipedia", "error", 0, f"http {status}")


def _wikipedia(query: str, n: int, lang: str = "en") -> list[dict]:
    results, _be = _wikipedia_report(query, n, lang)
    return results


# --- 디스패치 ----------------------------------------------------------------
def search_report(query: str, n: int = 10, type: str = "web") -> dict:
    """결과와 시도한 백엔드 상태를 함께 돌려준다.

    status: ok=1건 이상, empty=정상 응답 0건, blocked=403/429/캡차,
    error=예외·5xx·파싱 불가.
    """
    backends = _CURATED["type_backends"]
    if type not in backends:
        raise ValueError(f"미지원 --type: {type!r} (지원: {list(backends)})")
    backend = backends[type]["backend"]
    if backend == "ddg+searx":
        ddg_results, ddg_state = _ddg_report(query, n)
        states = [ddg_state]
        merged = list(ddg_results)
        if len(merged) < max(3, n // 2):                # 부족하면 SearXNG 보강
            searx_results, searx_state = _searx_report(query, n)
            states.append(searx_state)
            merged = _merge_results(ddg_results, searx_results, n)
        return {"results": merged[:n], "backends": states}
    if backend == "arxiv":
        results, state = _arxiv_report(query, n)
        return {"results": results, "backends": [state]}
    if backend == "sec_edgar":
        results, state = _sec_edgar_report(query, n)
        return {"results": results, "backends": [state]}
    raise ValueError(f"백엔드 미구현: {backend}")


def search(query: str, n: int = 10, type: str = "web") -> list[dict]:
    return search_report(query, n, type)["results"]


def wikipedia(query: str, n: int = 5, lang: str = "en") -> list[dict]:
    return _wikipedia(query, n, lang)


def _print_backend_lines(states: list[dict]) -> None:
    for state in states:
        print(f"backend {state['name']}: {state['status']} ({state['detail']})", file=sys.stderr)


def _exit_code(report: dict) -> int:
    """0건인데 시도한 백엔드가 전부 차단·오류면 2. 하나라도 empty 면 0."""
    states = report.get("backends") or []
    if report.get("results"):
        return 0
    if states and all(state["status"] in ("blocked", "error") for state in states):
        return 2
    return 0


def health() -> int:
    """인스턴스 health_path 와 ddg 를 각 1회만 찌른다. 재시도 없음."""
    timeout = int(_SEARX.get("timeout_sec", 10))
    rows: list[tuple[str, str, str]] = []
    try:
        status, html = _get("https://html.duckduckgo.com/html/?q=test", timeout=timeout)
        _results, state = _classify_ddg(status, html, 10)
        rows.append(("ddg", state["status"], state["detail"]))
    except Exception as exc:
        rows.append(("ddg", "error", _detail_exc(exc)))
    path = _SEARX.get("health_path", "/search?q=test&format=json")
    for inst in _SEARX.get("instances", []):
        host = urlparse(inst).hostname or inst
        url = inst.rstrip("/") + path
        try:
            status, txt = _get(url, timeout=timeout)
        except Exception as exc:
            rows.append((host, "error", _detail_exc(exc)))
            continue
        label, detail, _parsed = _judge_searx(status, txt, 10, host)
        rows.append((host, label, detail))
    print(f"{'백엔드':<28}{'상태':<10}상세")
    for name, label, detail in rows:
        print(f"{name:<28}{label:<10}{detail}")
    return 0


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
        found = _sec_edgar("Tesla", 3)
        assert "1318605" in found[0]["url"], found
        assert not found[0]["url"].rstrip().endswith("CIK="), found    # 옛 cik 단수필드 버그면 빈 CIK= 로 끝남
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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] == "demo":
        demo()
        return 0
    if args[0] == "health":
        return health()
    query = args[0]
    n = int(args[args.index("--n") + 1]) if "--n" in args else 10
    kind = args[args.index("--type") + 1] if "--type" in args else "web"
    report = search_report(query, n, kind)
    if "--json" in args:
        json.dump(report, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for index, item in enumerate(report["results"], 1):
            print(f"{index:2}. [{item['source']}] {item['title'][:70]}\n    {item['url']}")
    _print_backend_lines(report["backends"])
    return _exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
