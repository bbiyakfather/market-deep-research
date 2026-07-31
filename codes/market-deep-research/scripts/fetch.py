"""fetch.py — 자체 fetch/extract 스택 (plan-v2 핵심설계3 + v3-C).

보안경계(선제) → [도메인 라우팅] → curl_cffi TLS 그리드 → 모바일(iOS 지문+UA) → Jina Reader
→ Googlebot UA → RSS → Wayback → OGP 메타. 우회 전략을 **내장**한다(외부 스킬 위임 없음).
원본(raw) + 정제본(trafilatura) 둘 다 저장 + SHA-256. archived_url(Jina/Wayback)은 원 URL과 구분.

철칙(정책·완화 불가):
  - HTTP(S)만. private/loopback/link-local/reserved IP 및 그 대상으로의 리다이렉트 차단(SSRF).
  - 크기·시간·MIME 제한. 원문 = 신뢰하지 않는 데이터(프롬프트 인젝션 주의 — 여기선 추출만).
  - 로그인/CAPTCHA/paywall 우회 금지. 인가된 대상만.

CLI:
  python fetch.py demo                      # 오프라인 self-check(SSRF·검증 로직)
  python fetch.py smoke <url>               # 실제 네트워크 1건(라이브 스모크용)
  python fetch.py get <url> --out _sources  # 저장까지
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import shutil
import socket
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

MAX_BYTES = 8 * 1024 * 1024
TIMEOUT = 25
IMPERSONATE_GRID = ["chrome", "safari", "chrome110"]
ALLOWED_MIME = ("text/html", "text/plain", "application/json", "application/xml", "text/xml",
                "application/xhtml", "application/pdf", "application/rss")
CHALLENGE_MARKERS = ("just a moment", "access denied", "cf-challenge", "datadome",
                     "sec-if-cpt-container", "enable javascript and cookies",
                     "verifying you are human", "captcha-delivery")

# --- 내장 우회 계층 상수 (구 insane-search 위임분 흡수) -----------------------
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
MOBILE_HEADERS = {"User-Agent": MOBILE_UA,
                  "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                  "Referer": "https://m.naver.com/"}
GOOGLEBOT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; "
                                   "+http://www.google.com/bot.html)"}
# iOS TLS 지문 우선, 없으면 데스크톱 safari로 degrade
MOBILE_IMPERSONATE = "safari180_ios"

DEFAULT_ORDER = ["direct", "mobile", "jina", "googlebot", "rss", "wayback"]

# 도메인 라우팅 — 매칭되면 그 계층을 앞에 세운다(insane-search 사이트 인덱스 흡수).
# (호스트 정규식, 우선 계층). 나머지 계층은 DEFAULT_ORDER 순서로 뒤따른다.
ROUTES: list[tuple[str, list[str]]] = [
    (r"(^|\.)blog\.naver\.com$",                      ["mobile", "rss"]),
    (r"(^|\.)(news|finance|tv)\.naver\.com$",         ["jina"]),
    (r"(^|\.)(dcinside\.com|fmkorea\.com)$",          ["mobile"]),
    (r"(^|\.)yozm\.wishket\.com$",                    ["mobile"]),          # Jina 차단
    (r"(^|\.)tistory\.com$",                          ["rss"]),
    (r"(^|\.)(medium\.com|substack\.com)$",           ["jina", "rss"]),
    (r"(^|\.)(brunch\.co\.kr|clien\.net|ruliweb\.com|ppomppu\.co\.kr)$", ["jina", "rss"]),
    (r"(^|\.)(news\.hada\.io|44bits\.io|careerly\.co\.kr)$", ["jina"]),
    (r"(^|\.)(hankyung\.com|news\.daum\.net)$",       ["jina", "rss"]),
]

try:
    from curl_cffi import requests as creq          # TLS 위장
except Exception:                                    # 미설치 → degrade
    creq = None
try:
    import trafilatura
except Exception:
    trafilatura = None


def _ascii_ca() -> str | None:
    """libcurl(C)은 non-ASCII 경로의 CA 파일을 못 연다(Windows 한글 계정 이슈).
    certifi 번들 경로가 non-ASCII면 ASCII 경로로 1회 복사해 그 경로를 쓴다. verify는 항상 ON.
    V24: 매 실행 무조건 덮어써 위조 번들 선점을 막는다(크기만 비교하면 동일크기 위조를 못 잡음).
    후보 경로는 사용자 전용 → 세계쓰기 순. 이 분기가 도는 조건이 '홈 경로가 non-ASCII' 라
    사용자 전용 경로가 항상 쓸 수 있는 게 아니고, ASCII 가 아니면 libcurl 이 못 여니
    ProgramData 폴백이 필요하다. 기존 ProgramData 잔존본은 다른 프로세스가 쓸 수 있어
    지우지 않고 덮어쓰기만 한다."""
    try:
        import certifi
    except Exception:
        return None
    ca = certifi.where()
    try:
        ca.encode("ascii"); return ca                # 이미 ASCII면 그대로
    except UnicodeEncodeError:
        pass
    for base in (Path.home() / ".claude",             # 사용자 전용(홈이 ASCII 일 때만 성립)
                 Path(os.environ.get("ProgramData", r"C:\ProgramData")),
                 Path(os.environ.get("SystemDrive", "C:") + "\\")):
        try:
            dst = base / "market-deep-research" / "cacert.pem"
            s = str(dst); s.encode("ascii")           # 복사 전에 ASCII 판정(무의미한 쓰기 방지)
            dst.parent.mkdir(parents=True, exist_ok=True)
            # ponytail: 무조건 덮어쓰기. 덮어쓰기~libcurl 읽기 사이 TOCTOU 창은 남는다.
            #           완전 차단은 디렉터리 ACL 제한이 필요하고 그건 이 스킬 범위 밖.
            shutil.copyfile(ca, dst)
            return s
        except Exception:
            continue
    return ca


_CA_BUNDLE = _ascii_ca()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# --- 보안경계 (SSRF) ---------------------------------------------------------
class SsrfBlocked(ValueError):
    pass


def _ip_is_unsafe(ip: str) -> bool:
    a = ipaddress.ip_address(ip)
    return (a.is_private or a.is_loopback or a.is_link_local or a.is_reserved
            or a.is_multicast or a.is_unspecified)


def check_url_safe(url: str) -> str:
    """스킴·호스트·해석IP 검증. 안전하면 host 반환, 아니면 SsrfBlocked."""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise SsrfBlocked(f"허용 안 되는 스킴: {p.scheme!r}")
    host = p.hostname
    if not host:
        raise SsrfBlocked("호스트 없음")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise SsrfBlocked(f"DNS 해석 실패: {host} ({e})")
    for info in infos:
        ip = info[4][0]
        if _ip_is_unsafe(ip):
            raise SsrfBlocked(f"차단 IP({ip}) → {host}")
    return host


def check_response_ip(r) -> None:
    """실접속 IP 사후 재검증(V26 — TOCTOU 방지). check_url_safe 가 검증한 DNS 해석과 실제
    connect() 대상이 다를 수 있다(DNS 리바인딩). curl_cffi 응답의 primary_ip 를 재검사한다.
    프록시(HTTP_PROXY/HTTPS_PROXY) 사용 시 primary_ip 는 프록시 주소이므로 검사를 건너뛴다."""
    if os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY") \
            or os.environ.get("http_proxy") or os.environ.get("https_proxy"):
        return
    ip = getattr(r, "primary_ip", None)
    if ip and _ip_is_unsafe(ip):
        raise SsrfBlocked(f"실접속 차단 IP({ip})")


# --- 4계층 성공검증 (R2) -----------------------------------------------------
def validate_body(text: str, status: int, success_selectors: list[str] | None = None) -> dict:
    """{verdict: ok|partial|challenge|empty, reason}. HTTP200 ≠ 성공."""
    if status and status >= 400:                       # ⓪ 상태코드 우선(V17) — 4xx/5xx 본문은 안 믿음
        return {"verdict": "empty", "reason": f"http {status}"}
    low = (text or "").lower()
    n = len(text or "")
    if success_selectors and any(s.lower() in low for s in success_selectors):
        return {"verdict": "ok", "reason": "success selector matched"}  # ① 성공 셀렉터 최우선
    body = extract_text(text)
    if len(body) >= 1000:                              # ② 본문이 충분히 길면 확정 성공(V27 —
        return {"verdict": "ok", "reason": f"body {len(body)} chars"}  #   긴 기사 안의 챌린지 문구 인용은 오탐 아님)
    for m in CHALLENGE_MARKERS:                        # ③ 챌린지 마커(짧은 인터스티셜만 여기 도달)
        if m in low:
            return {"verdict": "challenge", "reason": f"challenge marker: {m}"}
    if n < 200:                                         # ④ 비정상 크기(빈 SPA/차단)
        return {"verdict": "empty", "reason": f"too small ({n}B)"}
    if n >= 200:
        return {"verdict": "partial", "reason": f"thin body ({len(body)} chars)"}
    return {"verdict": "empty", "reason": "no usable body"}


def extract_text(html: str) -> str:
    if trafilatura:
        out = trafilatura.extract(html, include_comments=False, include_tables=True)
        if out:
            return out
    # 폴백: 태그 제거(정제 라이브러리 없을 때)
    import re
    return re.sub(r"<[^>]+>", " ", html or "")


# --- 단일 fetch (수동 리다이렉트 검증 + 크기캡) -----------------------------
def _fetch_once(url: str, impersonate: str, max_redirects: int = 5,
                headers: dict | None = None) -> dict:
    if creq is None:
        return {"ok": False, "reason": "curl_cffi 미설치", "status": None, "text": "", "final_url": url}
    cur = url
    for _ in range(max_redirects + 1):
        check_url_safe(cur)                             # 각 홉 SSRF 사전검증(DNS 기준)
        _kw = {"verify": _CA_BUNDLE} if _CA_BUNDLE else {}
        if headers:
            _kw["headers"] = headers                    # UA 위장(모바일·봇) — TLS 지문과 별개 축
        r = creq.get(cur, impersonate=impersonate, timeout=TIMEOUT,
                     allow_redirects=False, stream=True, **_kw)
        check_response_ip(r)                            # 실접속 IP 사후 재검증(V26 — TOCTOU)
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("location") or r.headers.get("Location")
            r.close()
            if not loc:
                return {"ok": False, "reason": "redirect without Location", "status": r.status_code,
                        "text": "", "final_url": cur}
            cur = urljoin(cur, loc)                     # V19 — 수제 조립 대신 표준 결합(프로토콜상대·상대경로·포트 보존)
            continue
        ctype = r.headers.get("content-type") or ""
        mime = ctype.split(";")[0].strip().lower()
        charset = next((p.split("=", 1)[1].strip().strip('"') for p in ctype.split(";")[1:]
                        if p.strip().lower().startswith("charset=")), None)
        buf = b""
        for chunk in r.iter_content(chunk_size=65536):
            buf += chunk
            if len(buf) > MAX_BYTES:
                r.close()
                return {"ok": False, "reason": "oversize", "status": r.status_code,
                        "text": "", "final_url": cur, "mime": mime}
        r.close()
        is_pdf = buf[:5] == b"%PDF-"                    # V18a — 매직바이트만 신뢰(확장자/헤더는 위조 가능)
        if not is_pdf and mime and mime not in ALLOWED_MIME:   # V18b — PDF 판정 뒤에 게이트(옥텟스트림 PDF 보존)
            return {"ok": False, "reason": f"mime:{mime}", "status": r.status_code,
                    "text": "", "final_url": cur, "mime": mime}
        if is_pdf:
            text = ""
        else:
            try:
                text = buf.decode(charset or "utf-8")   # 선언된 charset 우선(EUC-KR 등 무시 방지)
            except (LookupError, UnicodeDecodeError):
                text = buf.decode("utf-8", errors="replace")
        return {"ok": True, "status": r.status_code, "text": text, "raw": buf,
                "final_url": cur, "mime": mime, "is_pdf": is_pdf}
    return {"ok": False, "reason": "too many redirects", "status": None, "text": "", "final_url": cur}


# --- 폴백 계층 ---------------------------------------------------------------
def _via_jina(url: str) -> dict:
    j = "https://r.jina.ai/" + url
    res = _fetch_once(j, "chrome")
    if res.get("ok"):
        res["archived_url"] = j
    return res


def _via_wayback(url: str) -> dict:
    api = "http://archive.org/wayback/available?url=" + quote(url, safe="")
    meta = _fetch_once(api, "chrome")
    if meta.get("ok"):
        try:
            snap = json.loads(meta["text"]).get("archived_snapshots", {}).get("closest", {})
            if snap.get("available") and snap.get("url"):
                res = _fetch_once(snap["url"], "chrome")
                if res.get("ok"):
                    res["archived_url"] = snap["url"]
                return res
        except Exception as e:
            return {"ok": False, "reason": f"wayback parse: {e}", "status": None, "text": "", "final_url": url}
    return {"ok": False, "reason": "no wayback snapshot", "status": None, "text": "", "final_url": url}


def _mobile_urls(url: str) -> list[str]:
    """모바일 대체 URL 후보. 네이버 블로그는 PostView 변환이 유일하게 본문을 준다."""
    p = urlparse(url)
    host = (p.hostname or "").lower()
    out: list[str] = []
    if host.endswith("blog.naver.com") and not host.startswith("m."):
        seg = [s for s in p.path.split("/") if s]
        if len(seg) >= 2 and seg[1].isdigit():
            out.append(f"https://m.blog.naver.com/PostView.naver?blogId={seg[0]}&logNo={seg[1]}")
        out.append(url.replace("://blog.naver.com", "://m.blog.naver.com", 1))
    elif host and not host.startswith("m.") and host.count(".") >= 1:
        out.append(p._replace(netloc="m." + p.netloc).geturl())
    out.append(url)                                     # 원 URL + 모바일 UA 조합도 시도
    return list(dict.fromkeys(out))


def _rss_urls(url: str) -> list[str]:
    p = urlparse(url)
    host = (p.hostname or "").lower()
    base = f"{p.scheme}://{p.netloc}"
    out: list[str] = []
    if host.endswith("blog.naver.com"):
        seg = [s for s in p.path.split("/") if s]
        if seg:
            out.append(f"https://rss.blog.naver.com/{seg[0]}.xml")
    if host.endswith("substack.com"):
        out.append(base + "/feed")
    out += [base + "/rss", base + "/feed", base + "/rss.xml"]
    return list(dict.fromkeys(out))


def _ogp_partial(html: str) -> str:
    """본문 확보 실패 시 OGP/description 메타만이라도 건진다(fallback.md 2번)."""
    import re
    got: dict[str, str] = {}
    pat = (r'<meta[^>]+?(?:property|name)\s*=\s*["\'](og:title|og:description|description)["\']'
           r'[^>]*?content\s*=\s*["\']([^"\']+)',
           r'<meta[^>]+?content\s*=\s*["\']([^"\']+)["\']'
           r'[^>]*?(?:property|name)\s*=\s*["\'](og:title|og:description|description)["\']')
    for m in re.finditer(pat[0], html, re.I | re.S):
        got.setdefault(m.group(1).lower(), m.group(2))
    for m in re.finditer(pat[1], html, re.I | re.S):
        got.setdefault(m.group(2).lower(), m.group(1))
    parts = [got.get("og:title", ""), got.get("og:description") or got.get("description", "")]
    return "\n".join(p for p in parts if p).strip()


def _try_derived(url: str, impersonate: str, headers: dict | None = None) -> dict:
    """**파생** URL(모바일·RSS 등 우리가 합성한 주소) 전용 fetch.

    SSRF 차단·미해석 호스트는 그 후보만 건너뛴다 — 차단 자체는 그대로 유효하고(요청 안 나감),
    다만 사다리를 죽이지 않는다. 원 URL 의 SSRF 는 진입부 check_url_safe 가 이미 막았고
    `direct` 계층에서는 계속 전파시킨다(리다이렉트 내부망 이탈은 보안 사건).
    """
    try:
        return _fetch_once(url, impersonate, headers=headers)
    except SsrfBlocked as e:
        return {"ok": False, "reason": f"skip:{e}", "status": None, "text": "", "final_url": url}
    except Exception as e:
        return {"ok": False, "reason": f"error:{e}", "status": None, "text": "", "final_url": url}


def _candidates(tier: str, url: str):
    """계층 이름 → (라벨, _fetch_once 형태 응답) 후보들을 순서대로 내놓는다."""
    if tier == "direct":
        for imp in IMPERSONATE_GRID:
            yield f"curl_cffi:{imp}", _fetch_once(url, imp)      # SSRF 는 전파(보안 사건)
    elif tier == "mobile":
        for u in _mobile_urls(url):
            res = _try_derived(u, MOBILE_IMPERSONATE, headers=MOBILE_HEADERS)
            if not res.get("ok") and str(res.get("reason", "")).startswith("error:"):
                res = _try_derived(u, "safari", headers=MOBILE_HEADERS)  # iOS 지문 미지원 빌드
            yield "mobile", res
    elif tier == "jina":
        yield "jina", _via_jina(url)
    elif tier == "googlebot":
        yield "googlebot", _try_derived(url, "chrome", headers=GOOGLEBOT_HEADERS)
    elif tier == "rss":
        for u in _rss_urls(url):
            res = _try_derived(u, "chrome")
            if res.get("ok"):
                res["archived_url"] = u                  # 원 URL과 구분(대체 표현물)
            yield "rss", res
    elif tier == "wayback":
        yield "wayback", _via_wayback(url)


def _tier_order(url: str) -> list[str]:
    """`direct`(원 URL·원본 충실도 최고)를 항상 먼저 타고, 도메인 라우팅은 **폴백 순서만** 바꾼다.

    insane-search 라우팅표는 WebFetch 기준이라 "이 사이트는 jina로" 식이지만,
    이 스택의 1계층 curl_cffi(TLS 위장)는 WebFetch보다 강해 대개 direct로 뚫린다.
    라우팅을 앞세우면 헛요청이 늘고, 더 나쁘게는 RSS 요약본이 본문보다 먼저 partial 로
    잡혀 원문 대신 반환될 수 있다(한경 실측).
    """
    import re
    host = (urlparse(url).hostname or "").lower()
    head: list[str] = []
    for pat, tiers in ROUTES:
        if re.search(pat, host):
            head = [t for t in tiers if t != "direct"]
            break
    return ["direct"] + head + [t for t in DEFAULT_ORDER if t not in head and t != "direct"]


def fetch(url: str, success_selectors: list[str] | None = None) -> dict:
    """자체 사다리 전체(도메인 라우팅 + 내장 우회). 반환 status ∈ {ok, partial, fail}.

    구 버전의 `delegate`(insane-search 스킬 위임)는 사다리에 흡수돼 사라졌다.
    """
    trace: list[dict] = []
    partial_res: dict | None = None
    last_html: str = ""
    check_url_safe(url)                                 # 진입 전 1차 검증

    for tier in _tier_order(url):
        try:
            for label, res in _candidates(tier, url):
                if not res or not res.get("ok"):
                    trace.append({"tier": label, "fail": (res or {}).get("reason")})
                    continue
                if res.get("is_pdf"):
                    return _result("ok", res, trace, note="pdf")
                v = validate_body(res["text"], res.get("status", 0), success_selectors)
                trace.append({"tier": label, "verdict": v["verdict"], "reason": v["reason"]})
                if v["verdict"] == "ok":
                    return _result("ok", res, trace, note=tier)
                if v["verdict"] == "partial" and partial_res is None:
                    partial_res = res
                if res.get("text"):
                    last_html = res["text"]
        except SsrfBlocked:
            raise
        except Exception as e:
            trace.append({"tier": tier, "error": str(e)})

    if partial_res is not None:
        return _result("partial", partial_res, trace)
    # OGP 메타만이라도 — 제목+요약 확보 시 partial 인정
    if last_html:
        og = _ogp_partial(last_html)
        if len(og) >= 40:
            trace.append({"tier": "ogp", "verdict": "partial"})
            return _result("partial", {"final_url": url, "text": og, "mime": "text/html"},
                           trace, note="ogp")
    return {"status": "fail", "final_url": url, "trace": trace,
            "hint": "자체 사다리 전 계층 소진 — playwright MCP(JS 렌더링) 또는 대체출처를 찾을 것"}


def _result(status: str, res: dict, trace: list, note: str = "") -> dict:
    return {"status": status, "final_url": res.get("final_url"), "http_status": res.get("status"),
            "archived_url": res.get("archived_url"), "mime": res.get("mime"),
            "text": res.get("text", ""), "raw": res.get("raw"), "is_pdf": res.get("is_pdf", False),
            "trace": trace, "note": note}


# --- 저장(원본 + 정제본 + 해시) ---------------------------------------------
def save(result: dict, out_dir: Path | str) -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    raw = result.get("raw")
    if raw is None and result.get("text"):
        raw = result["text"].encode("utf-8")
    if raw is None:
        return result
    sha = hashlib.sha256(raw).hexdigest()
    ext = "pdf" if result.get("is_pdf") else ("html" if "<" in result.get("text", "")[:200] else "txt")
    (out / f"{sha[:12]}_raw.{ext}").write_bytes(raw)
    clean_path = None
    if not result.get("is_pdf"):
        clean = extract_text(result.get("text", ""))
        clean_path = out / f"{sha[:12]}_clean.txt"
        clean_path.write_text(clean, encoding="utf-8")
    result.update({"sha256": sha, "local": str(out / f'{sha[:12]}_raw.{ext}'),
                   "clean": str(clean_path) if clean_path else None, "accessed_at": _now()})
    return result


# --- self-check --------------------------------------------------------------
def demo() -> None:
    # SSRF 차단: 사설/루프백/링크로컬/스킴
    for bad in ["http://127.0.0.1/x", "http://169.254.169.254/latest/meta-data",
                "http://10.0.0.5/", "file:///etc/passwd", "http://localhost:8080/"]:
        try:
            check_url_safe(bad); assert False, f"차단 실패: {bad}"
        except SsrfBlocked:
            pass
    # 공인 도메인은 통과(DNS 필요 — 실패 시 환경 문제로 스킵)
    try:
        assert check_url_safe("https://example.com/") == "example.com"
    except SsrfBlocked as e:
        print(f"  (경고) 공인 도메인 해석 스킵: {e}")

    # 4계층 검증
    assert validate_body("Just a moment... cf-challenge", 200)["verdict"] == "challenge"
    assert validate_body("", 200)["verdict"] == "empty"
    assert validate_body("<html><body>" + ("가나다 " * 400) + "</body></html>", 200)["verdict"] == "ok"
    thin = ("<html><head>" + '<meta name="x" content="y">' * 20
            + "<title>t</title></head><body><div id='app'></div><p>로딩중</p></body></html>")
    assert len(thin) >= 200
    assert validate_body(thin, 200)["verdict"] == "partial"
    # V17: 상태코드 우선 — 4xx/5xx 본문은 아무리 길어도 안 믿음(200 이면 같은 본문도 ok, 긍정형 짝)
    long_body = "가나다 " * 500
    assert validate_body(long_body, 404)["verdict"] == "empty"
    assert validate_body(long_body, 503)["verdict"] == "empty"
    assert validate_body(long_body, 200)["verdict"] == "ok"
    # V27: 긴 기사 안에 챌린지 문구가 인용문으로만 등장 → ok(짧은 진짜 챌린지 페이지는 여전히 challenge)
    article = ("<html><body><article><p>" + "전문가는 Just a moment 라는 문구를 인용했다. " * 80
               + "</p></article></body></html>")
    assert validate_body(article, 200)["verdict"] == "ok"

    # --- 내장 우회 계층(구 insane-search 위임분) ---------------------------
    # 도메인 라우팅: direct 가 **항상 먼저**, 라우팅은 폴백 순서만 조정(중복 없음)
    assert _tier_order("https://blog.naver.com/abc/223")[:3] == ["direct", "mobile", "rss"]
    assert _tier_order("https://news.naver.com/x")[:2] == ["direct", "jina"]
    assert _tier_order("https://yozm.wishket.com/magazine/detail/1/")[:2] == ["direct", "mobile"]
    plain = _tier_order("https://example.com/a")
    assert plain == DEFAULT_ORDER, plain
    for u in ("https://blog.naver.com/a/1", "https://news.naver.com/x", "https://x.substack.com/p/a"):
        assert _tier_order(u)[0] == "direct", u   # 원본 충실도 최우선 — RSS 요약본 선점 방지
    for u in ("https://blog.naver.com/a/1", "https://example.com/a"):
        order = _tier_order(u)
        assert len(order) == len(set(order)) == len(DEFAULT_ORDER), order

    # 네이버 블로그: 숫자 logNo 일 때만 PostView 변환(오변환 방지)
    mu = _mobile_urls("https://blog.naver.com/navion/223456789")
    assert mu[0] == "https://m.blog.naver.com/PostView.naver?blogId=navion&logNo=223456789", mu
    assert _mobile_urls("https://blog.naver.com/navion/tag")[0].startswith(
        "https://m.blog.naver.com/navion/tag"), "숫자 아닌 경로는 PostView 변환 금지"
    assert _mobile_urls("https://example.com/a")[0] == "https://m.example.com/a"
    assert "https://example.com/a" in _mobile_urls("https://example.com/a")  # 원 URL 폴백 보존

    assert "https://rss.blog.naver.com/navion.xml" in _rss_urls("https://blog.naver.com/navion/1")
    assert "https://x.substack.com/feed" in _rss_urls("https://x.substack.com/p/a")

    # 파생 URL 이 SSRF·미해석이어도 그 후보만 건너뛴다(사다리 전체가 죽으면 안 됨).
    # 차단 자체는 유효 — 요청은 나가지 않고 reason 에 skip 으로 남는다.
    _d = _try_derived("http://127.0.0.1/x", "chrome")
    assert _d["ok"] is False and _d["reason"].startswith("skip:"), _d

    # OGP: 속성 순서 뒤바뀐 경우도 잡아야 한다
    assert "제목" in _ogp_partial('<meta property="og:title" content="제목">')
    assert "요약" in _ogp_partial('<meta content="요약" name="og:description">')
    assert _ogp_partial("<html><body>없음</body></html>") == ""

    print(f"[{_now()}] fetch demo OK (curl_cffi={'Y' if creq else 'N'}, "
          f"trafilatura={'Y' if trafilatura else 'N'}, CA={'ascii' if _CA_BUNDLE else 'default'})")


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):          # cp949 콘솔/파이프 UnicodeEncodeError 방지
        _reconf = getattr(_stream, "reconfigure", None)
        if _reconf:
            _reconf(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif args[0] == "smoke" and len(args) >= 2:
        r = fetch(args[1])
        print(json.dumps({k: v for k, v in r.items() if k not in ("text", "raw")},
                         ensure_ascii=False, indent=2)[:1500])
    elif args[0] == "get" and len(args) >= 2:
        r = fetch(args[1])
        out = args[args.index("--out") + 1] if "--out" in args else "_sources"
        if r["status"] in ("ok", "partial"):
            r = save(r, out)
        print(json.dumps({k: v for k, v in r.items() if k not in ("text", "raw")},
                         ensure_ascii=False, indent=2)[:1500])
    else:
        print(__doc__); sys.exit(2)
