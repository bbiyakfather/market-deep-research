"""fetch.py — 자체 fetch/extract 스택 (plan-v2 핵심설계3 + v3-C).

보안경계(선제) → [도메인 라우팅] → curl_cffi TLS 그리드 → 모바일(iOS 지문+UA) → 브라우저
→ Jina Reader → Googlebot UA → RSS → Wayback → OGP 메타. 우회 전략을 **내장**한다(외부 스킬 위임 없음).
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
import http.client
import ipaddress
import re
import json
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

MAX_BYTES = 8 * 1024 * 1024          # HTML·일반 응답
DOC_MAX_BYTES = 40 * 1024 * 1024    # PDF·문서 파일만. HTML 은 MAX_BYTES
MAX_IMG_BYTES = 15 * 1024 * 1024
MAX_REDIRECTS = 5
CHUNK_BYTES = 65536
TIMEOUT = 25
# chrome/safari 는 설치본 최신 별칭. firefox 는 다른 엔진 계열 최신(0.16.2 → firefox147).
IMPERSONATE_GRID = ["chrome", "safari", "firefox"]
# 문서 MIME. octet-stream 은 URL 확장자로 다시 본다(_office_kind).
_DOC_MIME = {
    "application/x-hwp": "hwp",
    "application/haansofthwp": "hwp",
    "application/vnd.hancom.hwp": "hwp",
    "application/hwp+zip": "hwpx",
    "application/vnd.hancom.hwpx": "hwpx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/csv": "csv",
    "application/csv": "csv",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
}
_DOC_EXT = {"hwp", "hwpx", "xlsx", "xls", "docx", "pptx", "csv", "zip", "pdf"}
ALLOWED_MIME = ("text/html", "text/plain", "application/json", "application/xml", "text/xml",
                "application/xhtml", "application/pdf", "application/rss",
                "application/rss+xml", "application/atom+xml", *tuple(_DOC_MIME))
CHALLENGE_MARKERS = ("just a moment", "access denied", "cf-challenge", "datadome",
                     "sec-if-cpt-container", "enable javascript and cookies",
                     "verifying you are human", "captcha-delivery")
# 차단 페이지에만 나오는 구절. 동의·쿠키·404·로그인·삭제된·consent 같은 한 단어는
# 기사 제목·본문에 흔해서 쓰지 않는다. 제목·본문 모두 정제 본문 1000자 미만일 때만(V27).
_BODY_SUSPECT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("not_found", ("page not found", "페이지를 찾을 수 없", "요청하신 페이지")),
    ("login", ("로그인이 필요", "로그인 후 이용", "sign in to continue")),
    ("access_denied", ("access denied", "접근이 거부")),
    ("consent", ("쿠키 사용에 동의", "accept all cookies")),
)
# 제목은 '포함'이 아니라 그 문구로 시작하거나, 구분자(- | · :) 앞 첫 토막·제목 전체가 그 문구일 때.
_TITLE_SUSPECT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("not_found", ("404", "not found", "page not found", "페이지를 찾을 수 없습니다")),
    ("login", ("로그인", "sign in", "log in")),
    ("access_denied", ("access denied", "접근이 거부")),
)
_TITLE_SPLIT_RE = r"\s*[-|·:]\s*"
_SEP = r"[\s:\-|·–—]*"
_DEAD_TITLE_RE = re.compile(
    rf"(?:(?:error|http){_SEP}404(?!\d)"                                  # Error: 404 … / HTTP 404 …
    rf"|404(?!\d){_SEP}(?:error|(?:page\s+)?not\s+found)(?![a-z])"       # 404 - Page Not Found
    rf"|(?:page\s+)?not\s+found(?![a-z])"                                # Page not found | …
    rf"|페이지를 찾을 수 없습니다)", re.I)

# --- 내장 우회 계층 상수 (구 insane-search 위임분 흡수) -----------------------
# User-Agent 는 빼 둔다. safari_ios 가 프로필 UA 를 넣게 해 TLS 지문과 버전을 맞춘다.
MOBILE_HEADERS = {"Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                  "Referer": "https://m.naver.com/"}
GOOGLEBOT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; "
                                   "+http://www.google.com/bot.html)"}
# iOS 최신 별칭(0.16.2 → safari260_ios). 미지원이면 reason 이 error: 로 시작해 safari 로 degrade.
MOBILE_IMPERSONATE = "safari_ios"

DEFAULT_ORDER = ["direct", "mobile", "browser", "jina", "googlebot", "rss", "wayback"]

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


def _audit_fetch_attempt(url: str, tier: str, result: dict | None = None,
                         failure_reason: str | None = None) -> str:
    """Append one machine-readable fetch receipt without affecting the ladder."""
    receipt_id = uuid.uuid4().hex
    try:
        result = result or {}
        text = result.get("text") or ""
        body = extract_text(text)
        body_bytes = body.encode("utf-8")
        snapshot_path: str | None = None
        audit = Path("audit")
        snapshots = audit / "_fetch_snapshots"
        snapshots.mkdir(parents=True, exist_ok=True)
        if result.get("ok"):
            snapshot = snapshots / f"{receipt_id}.txt"
            snapshot.write_bytes(body_bytes)
            snapshot_path = str(snapshot).replace("\\", "/")
        row = {
            "kind": "attempt",
            "id": receipt_id,
            "url": url,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "tier": tier,
            "status": result.get("acquisition_status", "fail"),
            "http_status": result.get("status"),
            "failure_reason": failure_reason or (result.get("reason")
                               if result.get("acquisition_status") == "fail" or not result.get("ok") else None),
            "body_sha256": hashlib.sha256(body_bytes).hexdigest() if body_bytes else None,
            "snapshot_path": snapshot_path,
        }
        with (audit / "fetch-log.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception:
        # Audit is observational; a logging filesystem error must not alter fetch/SSRF behavior.
        pass
    return receipt_id


# --- 보안경계 (SSRF) ---------------------------------------------------------
class SsrfBlocked(ValueError):
    pass


def _ip_is_unsafe(ip: str) -> bool:
    a = ipaddress.ip_address(ip)
    return (a.is_private or a.is_loopback or a.is_link_local or a.is_reserved
            or a.is_multicast or a.is_unspecified)


def _resolve_safe(url: str) -> tuple[str, list[str]]:
    """검사한 주소를 연결에도 사용하여 DNS 재해석 사이의 경계 이탈을 막는다."""
    if "\\" in url or any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise SsrfBlocked("URL 제어문자·공백·역슬래시 금지")
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise SsrfBlocked(f"허용 안 되는 스킴: {p.scheme!r}")
    host = p.hostname
    if not host:
        raise SsrfBlocked("호스트 없음")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise SsrfBlocked("잘못된 국제화 호스트") from exc
    if p.username is not None or p.password is not None:
        raise SsrfBlocked("URL 사용자 정보 금지")
    try:
        p.port
    except ValueError as exc:
        raise SsrfBlocked(f"잘못된 포트: {exc}") from exc
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise SsrfBlocked(f"DNS 해석 실패: {host} ({e})")
    addresses = []
    for info in infos:
        ip = info[4][0]
        if _ip_is_unsafe(ip):
            raise SsrfBlocked(f"차단 IP({ip}) → {host}")
        if ip not in addresses:
            addresses.append(ip)
    if not addresses:
        raise SsrfBlocked(f"DNS 주소 없음: {host}")
    return host, addresses


def check_url_safe(url: str) -> str:
    """공통 스킴·호스트·주소 가드. 안전하면 host 반환."""
    return _resolve_safe(url)[0]


def check_response_ip(r) -> None:
    """고정 연결의 추가 사후 검사. 이 검사 자체는 이미 송신한 요청을 되돌리지 못한다.

    프록시 환경변수와 무관하게 검사한다. 공통 transport는 목적지 고정을 보장하려고
    환경 프록시를 사용하지 않는다(프록시 내부의 DNS/연결은 이 프로세스가 검증 불가).
    """
    ip = getattr(r, "primary_ip", None)
    if ip and _ip_is_unsafe(ip):
        raise SsrfBlocked(f"실접속 차단 IP({ip})")


# --- 4계층 성공검증 (R2) -----------------------------------------------------
def _phrase_in(text: str, phrases: tuple[str, ...]) -> bool:
    low = text.casefold()
    return any(phrase.casefold() in low for phrase in phrases)


def _body_suspect(text: str) -> str | None:
    raw = text or ""
    if not raw.strip():
        return None
    for kind, phrases in _BODY_SUSPECT:
        if _phrase_in(raw, phrases):
            return kind
    return None


def _title_starts(low: str, phrase: str) -> bool:
    """문구로 시작하고 바로 뒤가 글자·숫자가 아니면 참."""
    if not low.startswith(phrase):
        return False
    rest = low[len(phrase):]
    return not (rest and rest[0].isalnum())             # 404억·not founders·sign industry 는 시작이 아니다


def _title_suspect(title: str) -> str | None:
    import re
    raw = (title or "").strip()
    if not raw:
        return None
    low = raw.casefold()
    first = re.split(_TITLE_SPLIT_RE, raw, maxsplit=1)[0].strip().casefold()
    for kind, phrases in _TITLE_SUSPECT:
        for phrase in phrases:
            folded = phrase.casefold()
            if low == folded or first == folded or _title_starts(low, folded):
                return kind
    return None


def _url_ext(url: str) -> str:
    return Path(urlparse(url).path).suffix.lower().lstrip(".")


def _mime_base(mime: str) -> str:
    return (mime or "").split(";", 1)[0].strip().lower()


def _office_kind(mime: str, url: str) -> str | None:
    """PDF 가 아닌 문서. octet-stream 은 URL 확장자로만 종류를 정한다."""
    base = _mime_base(mime)
    if base in _DOC_MIME:
        return _DOC_MIME[base]
    if base == "application/octet-stream":
        ext = _url_ext(url)
        if ext in _DOC_EXT and ext != "pdf":
            return ext
    return None


def _doc_byte_cap(mime: str, url: str) -> bool:
    """PDF·문서(또는 octet-stream+문서 확장자)면 40MB. HTML 은 호출자 상한 그대로."""
    base = _mime_base(mime)
    if base == "application/pdf" or base in _DOC_MIME:
        return True
    return base == "application/octet-stream" and _url_ext(url) in _DOC_EXT


def validate_body(text: str, status: int, success_selectors: list[str] | None = None) -> dict:
    """{verdict: ok|partial|challenge|empty, reason}. HTTP200 ≠ 성공."""
    if not isinstance(status, int) or not 200 <= status < 300:
        return {"verdict": "empty", "reason": f"http {status}"}
    low = (text or "").lower()
    n = len(text or "")
    if success_selectors and any(s.lower() in low for s in success_selectors):
        return {"verdict": "ok", "reason": "success selector matched"}  # ① 성공 셀렉터 최우선
    body = extract_text(text)
    # 길이 판정 앞. 1000자 이상은 확정 성공으로 넘어가고, 그 미만만 차단 구절을 본다.
    title = _html_title(text) or ""
    # 없는 페이지 안내는 메뉴·푸터 때문에 본문이 길다. 제목이 그 문구로 시작하면 길이와 무관하게 건다.
    suspect = "not_found" if _DEAD_TITLE_RE.match(title.strip()) else None
    if not suspect and len(body) < 1000:
        suspect = _title_suspect(title) or _body_suspect(body)
    if suspect:
        return {"verdict": "partial", "reason": f"suspect:{suspect}"}
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
    # 폴백: script/style 을 먼저 지운 뒤 태그 제거(빈 SPA 셸이 길이로 ok 가 되지 않게).
    import re
    cleaned = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", html or "")
    return re.sub(r"<[^>]+>", " ", cleaned)


# --- 공통 transport: 수동 리다이렉트·고정 IP·스트리밍 크기캡 -----------------
class DownloadLimitError(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _urllib_open(url: str, host: str, addresses: list[str], headers: dict, timeout: float):
    def connection_factory(cls):
        def factory(*args, **kwargs):
            conn = cls(*args, **kwargs)

            def connect(address, timeout=timeout, source_address=None):
                # numeric IP만 connect에 전달한다. TLS의 SNI/인증서 검증은 원 host 유지.
                last_error = None
                for ip in addresses:
                    try:
                        sock = socket.create_connection((ip, address[1]), timeout, source_address)
                        if _ip_is_unsafe(sock.getpeername()[0]):
                            sock.close()
                            raise SsrfBlocked("실접속 차단 IP")
                        return sock
                    except OSError as exc:
                        last_error = exc
                raise last_error or OSError(f"연결 실패: {host}")

            conn._create_connection = connect
            return conn
        return factory

    class HTTPHandler(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(connection_factory(http.client.HTTPConnection), req)

    class HTTPSHandler(urllib.request.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(connection_factory(http.client.HTTPSConnection), req,
                                context=self._context)

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(),
                                        HTTPHandler(), HTTPSHandler())
    try:
        return opener.open(urllib.request.Request(url, headers=headers), timeout=timeout)
    except urllib.error.HTTPError as exc:
        return exc  # HTTPError도 스트림. redirect/오류 상태 처리는 공통 루프에서 한다.


_DEFAULT_CLIENT = object()


def request_bytes(url: str, *, impersonate: str = "chrome", headers: dict | None = None,
                  timeout: int = TIMEOUT, max_bytes: int = MAX_BYTES,
                  max_redirects: int = MAX_REDIRECTS, client=_DEFAULT_CLIENT,
                  doc_cap: bool = False) -> dict:
    """fetch·검색·이미지 수집이 공유하는 유일한 HTTP 경계.

    doc_cap 은 열람(_fetch_once)만 켠다. 검색·이미지 JSON 호출이 서버가 붙인 Content-Type 만으로 40MB 를 받지 않게 한다.
    """
    client = creq if client is _DEFAULT_CLIENT else client
    cur = url
    deadline = time.monotonic() + timeout
    for hop in range(min(max_redirects, MAX_REDIRECTS) + 1):
        host, addresses = _resolve_safe(cur)
        p = urlparse(cur)
        authority = f"[{host}]" if ":" in host else host
        if p.port is not None:
            authority += f":{p.port}"
        cur = p._replace(netloc=authority, fragment="").geturl()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("다운로드 시간 초과")
        if client is not None:
            from curl_cffi.const import CurlOpt
            port = p.port or (443 if p.scheme == "https" else 80)
            pinned = ",".join(f"[{ip}]" if ":" in ip else ip for ip in addresses)
            r = client.get(cur, impersonate=impersonate, timeout=remaining,
                           allow_redirects=False, stream=True, headers=headers or {},
                           verify=_CA_BUNDLE or True,
                           curl_options={CurlOpt.RESOLVE: [f"{host}:{port}:{pinned}"],
                                         CurlOpt.PROXY: ""})
        else:
            r = _urllib_open(cur, host, addresses, headers or {}, remaining)
        try:
            check_response_ip(r)
            status = r.status_code if client is not None else r.code
            response_headers = {k.lower(): v for k, v in r.headers.items()}
            cap = max_bytes
            if doc_cap and max_bytes == MAX_BYTES and _doc_byte_cap(response_headers.get("content-type", ""), cur):
                cap = DOC_MAX_BYTES
            if status in (301, 302, 303, 307, 308):
                loc = response_headers.get("location")
                if not loc:
                    raise ValueError("redirect without Location")
                if hop == min(max_redirects, MAX_REDIRECTS):
                    raise ValueError("too many redirects")
                cur = urljoin(cur, loc)
                continue
            length = response_headers.get("content-length", "")
            if length.isdigit() and int(length) > cap:
                raise DownloadLimitError("oversize")
            chunks = r.iter_content(chunk_size=CHUNK_BYTES) if client is not None else iter(
                lambda: r.read(CHUNK_BYTES), b"")
            buf = bytearray()
            for chunk in chunks:
                if time.monotonic() > deadline:
                    raise TimeoutError("다운로드 시간 초과")
                if len(buf) + len(chunk) > cap:
                    raise DownloadLimitError("oversize")
                buf.extend(chunk)
            return {"status": status, "headers": response_headers, "raw": bytes(buf),
                    "final_url": cur}
        finally:
            r.close()
    raise ValueError("too many redirects")


def _header_charset(ctype: str) -> str | None:
    for part in (ctype or "").split(";")[1:]:
        if part.strip().lower().startswith("charset="):
            charset = part.split("=", 1)[1].strip().strip('"').strip("'")
            return charset or None
    return None


def _meta_charset(raw: bytes) -> str | None:
    """헤더에 charset 이 없을 때만. 앞 2048바이트의 meta charset / http-equiv Content-Type."""
    import re
    if not raw:
        return None
    for tag in re.findall(br"<meta\b[^>]*>", raw[:2048], re.I):
        low = tag.lower()
        found = re.search(br"""charset\s*=\s*["']?\s*([A-Za-z0-9._-]+)""", tag, re.I)
        if not found:
            continue
        if b"http-equiv" in low and b"content-type" not in low:
            continue
        return found.group(1).decode("ascii")
    return None


def response_text(response: dict) -> str:
    ctype = response.get("headers", {}).get("content-type", "")
    charset = _header_charset(ctype) or _meta_charset(response.get("raw") or b"") or "utf-8"
    try:
        return response["raw"].decode(charset)
    except (LookupError, UnicodeDecodeError):
        return response["raw"].decode("utf-8", errors="replace")


def _fetch_once(url: str, impersonate: str, max_redirects: int = MAX_REDIRECTS,
                headers: dict | None = None) -> dict:
    try:
        response = request_bytes(url, impersonate=impersonate, headers=headers,
                                 max_redirects=max_redirects, doc_cap=True)
    except SsrfBlocked:
        raise
    except (DownloadLimitError, ValueError, OSError) as exc:
        reason = str(exc)
        # ImpersonateError 는 OSError 라 여기서 삼켜진다. mobile degrade 는 error: 접두를 본다.
        if exc.__class__.__name__ == "ImpersonateError":
            reason = f"error:{reason}"
        return {"ok": False, "reason": reason, "status": None, "text": "", "final_url": url}
    buf, status = response["raw"], response["status"]
    mime = response["headers"].get("content-type", "").split(";", 1)[0].strip().lower()
    text = response_text(response)
    base = {"status": status, "text": text, "final_url": response["final_url"], "mime": mime}
    # PDF 판정 전에 상태를 거부한다. 진단 본문은 유지하되 확보 성공으로 쓰지 않는다.
    if not 200 <= status < 300:
        return {**base, "ok": False, "reason": f"http {status}", "is_pdf": False}
    is_pdf = buf[:5] == b"%PDF-"
    doc_kind = None if is_pdf else _office_kind(mime, response["final_url"])
    if not is_pdf and not doc_kind and mime and mime not in ALLOWED_MIME:
        return {**base, "ok": False, "reason": f"mime:{mime}"}
    binary = is_pdf or bool(doc_kind)
    out = {**base, "ok": True, "text": "" if binary else text, "raw": buf, "is_pdf": is_pdf}
    if doc_kind:
        out["doc_kind"] = doc_kind
    return out


# --- 폴백 계층 ---------------------------------------------------------------
def _via_jina(url: str) -> dict:
    j = "https://r.jina.ai/" + url
    res = _fetch_once(j, "chrome")
    if res.get("ok"):
        import re
        # Jina 는 죽은 페이지·차단 페이지도 200 과 긴 본문으로 감싼다. 머리말이 알려 주는 원 응답 코드를 믿는다.
        head = res.get("text", "").split("Markdown Content:", 1)[0][:8000]
        origin = re.search(r"^Warning: Target URL returned error (\d{3})", head, re.M)
        if origin:
            return {**res, "ok": False, "status": int(origin.group(1)), "reason": f"http {origin.group(1)}"}
        title = re.search(r"^Title:[ \t]*(.*)$", head, re.M)   # Jina 본문에는 <title> 이 없어 validate_body 가 못 본다
        if title and _DEAD_TITLE_RE.match(title.group(1).strip()):
            return {**res, "ok": False, "reason": "suspect:not_found"}
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


def _rss_entry(res: dict, requested_url: str, expected_title: str | None = None) -> dict:
    """RSS/Atom에서 대응하는 단일 항목만 추출한다. 무관 피드는 탐색 자료로 보존."""
    import re
    from html import unescape

    def normalized_url(value):
        p = urlparse(unescape(value).strip())
        return p._replace(scheme=p.scheme.lower(), netloc=p.netloc.lower(), fragment="").geturl()

    def title_key(value):
        return re.sub(r"\s+", " ", unescape(value or "")).strip().casefold()

    partial = {**res, "acquisition_status": "partial", "rss_match": False, "_note": "rss",
               "reason": "요청 기사와 일치하는 RSS entry 없음"}
    try:
        root = ET.fromstring(res.get("text", ""))
    except ET.ParseError:
        return {**res, "ok": False, "reason": "RSS XML 파싱 실패"}
    if root.tag.rsplit("}", 1)[-1] not in ("rss", "feed", "RDF"):
        return {**res, "ok": False, "reason": "RSS/Atom 피드 아님"}
    matches, title_matches = [], []
    for entry in root.iter():
        if entry.tag.rsplit("}", 1)[-1] not in ("item", "entry"):
            continue
        fields: dict[str, list[str]] = {}
        for child in entry:
            tag = child.tag.rsplit("}", 1)[-1]
            value = "".join(child.itertext()).strip()
            if tag == "link":
                if child.get("rel", "alternate") != "alternate":
                    continue
                value = child.get("href") or value
            fields.setdefault(tag, []).append(value)
        identifiers = fields.get("link", []) + fields.get("guid", []) + fields.get("id", [])
        if any(normalized_url(urljoin(res.get("final_url") or requested_url, value)) ==
               normalized_url(requested_url) for value in identifiers):
            matches.append((entry, fields))
        elif expected_title and title_key(" ".join(fields.get("title", []))) == title_key(expected_title):
            title_matches.append((entry, fields))
    matches = matches or title_matches
    if len(matches) != 1:  # 중복 제목/모호한 항목은 원문이라고 단정하지 않는다.
        return partial
    entry, fields = matches[0]
    body = next((fields[key][0] for key in ("encoded", "content", "description", "summary")
                 if fields.get(key) and fields[key][0]), "")
    # Atom XHTML은 itertext로 텍스트를 추출한다. RSS CDATA HTML은 그대로 본문 검증에 넘긴다.
    text = "\n".join([" ".join(fields.get("title", [])), body]).strip()
    # raw는 수신한 피드 바이트 그대로 보존한다. 검증·clean 대상만 대응 entry로 좁힌다.
    return {**res, "text": text, "rss_match": True, "_note": "rss"}


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


def _mobile_dns_missing(url: str) -> bool:
    """합성한 m. 호스트가 풀리지 않으면 True. 요청·시도 로그 없이 그 후보만 건너뛴다."""
    host = (urlparse(url).hostname or "").lower()
    if not host.startswith("m."):
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True
    return not infos


def _third_party_blocked(explicit: bool | None = None) -> bool:
    """jina·wayback 은 대상 URL 을 외부 서비스로 보낸다. 대외비 조사에서 끈다."""
    if explicit is not None:
        return explicit
    return os.environ.get("MDR_NO_THIRD_PARTY") == "1"


# --- 브라우저 계층 (선택 의존성. 없어도 나머지 사다리는 동작한다) ------------
_BROWSER_IDLE_MS = 20_000
_BROWSER_SCROLLS = 5
_BROWSER_ABORT_TYPES = frozenset({"image", "font", "media"})


def _browser_skip(url: str) -> dict:
    return {"ok": False, "status": None, "text": "", "final_url": url, "mime": "",
            "reason": "skip:browser 미설치"}


def _browser_fail(url: str, exc: BaseException) -> dict:
    return {"ok": False, "status": None, "text": "", "final_url": url, "mime": "",
            "reason": f"error:{exc}"}


def _load_sync_playwright(package: str):
    try:
        if package == "patchright":
            from patchright.sync_api import sync_playwright
        elif package == "playwright":
            from playwright.sync_api import sync_playwright
        else:
            return None
        return sync_playwright
    except Exception:
        return None


def _browser_engines() -> list[tuple]:
    """import 되는 엔진을 patchright, playwright 순으로 낸다."""
    found = []
    for name in ("patchright", "playwright"):
        fn = _load_sync_playwright(name)
        if fn is not None:
            found.append((fn, name))
    return found


def _is_missing_browser(exc: BaseException) -> bool:
    text = str(exc).casefold()
    return ("executable doesn't exist" in text
            or "executable does not exist" in text
            or "please run the following command to download" in text)


def _is_main_document(request) -> bool:
    if getattr(request, "resource_type", "") != "document":
        return False
    frame = getattr(request, "frame", None)
    if frame is None:
        return True
    return getattr(frame, "parent_frame", None) is None


def _browser_route_action(url: str, resource_type: str) -> str:
    """abort 또는 continue. 이미지·폰트·미디어와 사설·비 http(s) 는 받지 않는다."""
    if resource_type in _BROWSER_ABORT_TYPES:
        return "abort"
    try:
        check_url_safe(url)
    except SsrfBlocked:
        return "abort"
    return "continue"


def _guard_browser_route(route, blocked: list | None = None) -> None:
    request = route.request
    action = _browser_route_action(request.url, getattr(request, "resource_type", "") or "")
    if action == "abort":
        route.abort()
        if blocked is not None and _is_main_document(request):
            blocked.append(request.url)
        return
    route.continue_()


def _read_rendered_page(page) -> str:
    """네트워크가 잠잠해질 때까지(상한 20초) 기다린 뒤, 높이가 늘지 않으면 멈추는 스크롤 최대 5회."""
    try:
        page.wait_for_load_state("networkidle", timeout=_BROWSER_IDLE_MS)
    except Exception:
        pass
    height_js = ("() => { const el = document.scrollingElement || document.body;"
                 " return el ? el.scrollHeight : 0; }")
    scroll_js = ("() => { const el = document.scrollingElement || document.body;"
                 " if (el) window.scrollTo(0, el.scrollHeight); }")
    for _ in range(_BROWSER_SCROLLS):
        height = page.evaluate(height_js)
        page.evaluate(scroll_js)
        page.wait_for_timeout(200)
        if page.evaluate(height_js) <= height:
            break
    return page.content()


def _launch_chromium(playwright):
    """헤드리스 Chromium. 번들 실행이 죽거나 없으면 설치된 Chrome 을 헤드리스로 한 번 더 연다.

    지문·UA 는 넣지 않는다. 이 환경의 번들 headless shell 은 ICU 데이터 오류로 바로 죽는다.
    """
    if os.environ.get("MDR_BROWSER_HEADED") == "1":      # 창이 뜬다. JS 챌린지는 헤드리스에서 안 풀린다
        return playwright.chromium.launch(headless=False, channel="chrome")
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as bundled:
        try:
            return playwright.chromium.launch(headless=True, channel="chrome")
        except Exception:
            raise bundled


def _render_url(sync_playwright, url: str) -> dict:
    blocked: list[str] = []
    status = {"code": None}
    with sync_playwright() as pw:
        browser = _launch_chromium(pw)
        context = None
        try:
            # 호출마다 새 컨텍스트. 닫으면 쿠키·저장소가 남지 않는다. 다운로드·권한은 거부.
            # 서비스 워커는 route 검사를 우회하므로 막는다.
            context = browser.new_context(accept_downloads=False, service_workers="block")
            page = context.new_page()
            page.on("dialog", lambda dialog: dialog.dismiss())

            def on_response(response):
                if _is_main_document(response.request):
                    status["code"] = response.status
                # route 는 처음 주소만 본다. 리다이렉트·DNS 재해석으로 내부망에 닿은 응답은 여기서 잡는다.
                # shortcut: 요청은 이미 한 번 나간 뒤다(내용만 버린다), 송신까지 막으려면 필터링 프록시를 둔다.
                try:
                    ip = (response.server_addr() or {}).get("ipAddress")
                    if ip and _ip_is_unsafe(ip):
                        blocked.append(response.url)
                except Exception:
                    pass

            page.on("response", on_response)
            page.route("**/*", lambda route: _guard_browser_route(route, blocked))
            # WebSocket 은 위 route 를 타지 않는다. 열람에는 필요 없으므로 전부 닫는다(내부망 ws:// 우회 차단).
            page.route_web_socket("**", lambda ws: ws.close())
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=_BROWSER_IDLE_MS)
            except Exception as exc:
                if blocked:
                    raise SsrfBlocked(f"브라우저 주 문서 차단: {blocked[0]}") from exc
                raise
            if blocked:
                raise SsrfBlocked(f"브라우저 주 문서 차단: {blocked[0]}")
            if status["code"] in (403, 503):             # 챌린지가 스스로 풀리고 다시 싣는 시간을 준다
                try:
                    page.wait_for_event("response", predicate=lambda r: _is_main_document(r.request)
                                        and 200 <= r.status < 300, timeout=10_000)
                except Exception:
                    pass
            text = _read_rendered_page(page)
            final_url = page.url
            if blocked:                                  # 내부망 응답이 섞인 페이지는 통째로 버린다
                raise SsrfBlocked(f"브라우저 내부망 응답 차단: {blocked[0]}")
            check_url_safe(final_url)
        finally:
            if context is not None:
                context.close()
            browser.close()
    code = status["code"]
    base = {"status": code, "text": text, "final_url": final_url, "mime": "text/html"}
    if not isinstance(code, int) or not 200 <= code < 300:
        return {**base, "ok": False, "reason": f"http {code}"}
    return {**base, "ok": True}


def _via_browser(url: str) -> dict:
    """헤드리스 Chromium. 엔진·실행 파일이 없으면 skip 하고 사다리가 다음으로 간다.

    patchright 가 import 되면 그것을 쓴다. 그 실행 파일만 없으면 playwright 로 한 번 더 연다.
    주 문서가 사설·루프백·링크로컬·비 http(s) 로 막히면 SsrfBlocked 를 전파한다.
    """
    check_url_safe(url)
    engines = _browser_engines()
    if not engines:
        return _browser_skip(url)
    for sync_playwright, _name in engines:
        try:
            return _render_url(sync_playwright, url)
        except SsrfBlocked:
            raise
        except Exception as exc:
            if _is_missing_browser(exc):
                continue
            return _browser_fail(url, exc)
    return _browser_skip(url)


def _exhausted_hint() -> str:
    if os.environ.get("MDR_BROWSER") == "0":
        return ("자체 사다리 전 계층 소진 — 브라우저 계층은 꺼져 있었다(MDR_BROWSER=0). "
                "JS 렌더가 필요하면 스위치를 켜고, 아니면 대체출처를 찾을 것")
    return ("자체 사다리 전 계층 소진 — 브라우저 계층(patchright 또는 playwright)까지 실패했다. "
            "대체출처를 찾을 것")


def _candidates(tier: str, url: str):
    """계층 이름 → (라벨, _fetch_once 형태 응답) 후보들을 순서대로 내놓는다."""
    if tier == "direct":
        for imp in IMPERSONATE_GRID:
            res = _fetch_once(url, imp)                          # SSRF 는 전파(보안 사건)
            yield f"curl_cffi:{imp}", res
            if res.get("status") == 429:                        # 같은 계층의 남은 프로필은 치지 않는다
                break
    elif tier == "mobile":
        for u in _mobile_urls(url):
            if _mobile_dns_missing(u):
                continue
            res = _try_derived(u, MOBILE_IMPERSONATE, headers=MOBILE_HEADERS)
            if not res.get("ok") and str(res.get("reason", "")).startswith("error:"):
                res = _try_derived(u, "safari", headers=MOBILE_HEADERS)  # iOS 지문 미지원 빌드
            yield "mobile", res
    elif tier == "browser":
        yield "browser", _via_browser(url)
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


def _fetch_ladder(url: str, success_selectors: list[str] | None = None,
                  expected_title: str | None = None, *, no_third_party: bool | None = None) -> dict:
    """자체 사다리 전체(도메인 라우팅 + 내장 우회). 반환 status ∈ {ok, partial, fail}.

    구 버전의 `delegate`(insane-search 스킬 위임)는 사다리에 흡수돼 사라졌다.
    """
    trace: list[dict] = []
    fetch_refs: list[str] = []
    partial_res: dict | None = None
    last_html: str = ""
    blocked = _third_party_blocked(no_third_party)
    direct_dead = False
    check_url_safe(url)                                 # 진입 전 1차 검증

    for tier in _tier_order(url):
        if blocked and tier in ("jina", "wayback"):
            trace.append({"tier": tier, "skip": "no-third-party"})
            continue
        # direct 가 전부 404/410 이면 죽은 페이지. 아카이브(wayback)만 남긴다.
        if direct_dead and tier != "wayback":
            trace.append({"tier": tier, "skip": "direct-404"})
            continue
        if tier == "browser" and os.environ.get("MDR_BROWSER") == "0":
            trace.append({"tier": tier, "skip": "MDR_BROWSER=0"})
            continue
        direct_statuses: list = []
        tier_done = False
        try:
            for label, res in _candidates(tier, url):
                res = dict(res or {})
                if tier == "direct":
                    direct_statuses.append(res.get("status"))
                status = res.get("status")
                if res.get("ok") and (not isinstance(status, int) or not 200 <= status < 300):
                    res.update(ok=False, reason=f"http {status}")
                if res.get("ok") and tier == "rss":
                    res = _rss_entry(res, url, expected_title)
                if not res.get("ok"):
                    v = {"verdict": "fail", "reason": res.get("reason")}
                elif res.get("rss_match") is False:
                    v = {"verdict": "partial", "reason": res["reason"]}
                elif res.get("is_pdf"):
                    v = {"verdict": "ok", "reason": "pdf"}
                elif res.get("doc_kind"):
                    v = {"verdict": "ok", "reason": res["doc_kind"]}
                else:
                    v = validate_body(res.get("text", ""), status, success_selectors)
                res["acquisition_status"] = v["verdict"] if v["verdict"] in ("ok", "partial") else "fail"
                if res["acquisition_status"] == "fail":
                    res["reason"] = v["reason"]
                if tier == "direct" and res.get("ok") and v["verdict"] == "partial" and not expected_title:
                    expected_title = _html_title(res.get("text", ""))
                ref = _audit_fetch_attempt(url, label, res)
                fetch_refs.append(ref)
                if not res or not res.get("ok"):
                    trace.append({"tier": label, "fail": (res or {}).get("reason"), "fetch_ref": ref})
                    continue
                res["_fetch_ref"] = ref
                if res.get("is_pdf") and v["verdict"] == "ok":
                    return _result("ok", res, trace, note="pdf", fetch_refs=fetch_refs)
                if res.get("doc_kind") and v["verdict"] == "ok":
                    return _result("ok", res, trace, note=res["doc_kind"], fetch_refs=fetch_refs)
                trace.append({"tier": label, "verdict": v["verdict"], "reason": v["reason"],
                              "fetch_ref": ref})
                if v["verdict"] == "ok":
                    return _result("ok", res, trace, note=tier, fetch_refs=fetch_refs)
                if v["verdict"] == "partial" and partial_res is None:
                    partial_res = res
                if res.get("text"):
                    last_html = res["text"]
            tier_done = True
        except SsrfBlocked:
            raise
        except Exception as e:
            ref = _audit_fetch_attempt(url, tier, failure_reason=str(e))
            fetch_refs.append(ref)
            trace.append({"tier": tier, "error": str(e)})
        if (tier_done and tier == "direct" and direct_statuses
                and all(code in (404, 410) for code in direct_statuses)):
            direct_dead = True

    if partial_res is not None:
        return _result("partial", partial_res, trace, fetch_refs=fetch_refs)
    # OGP 메타만이라도 — 제목+요약 확보 시 partial 인정
    if last_html:
        og = _ogp_partial(last_html)
        if len(og) >= 40:
            trace.append({"tier": "ogp", "verdict": "partial"})
            return _result("partial", {"final_url": url, "text": og, "mime": "text/html"},
                           trace, note="ogp", fetch_refs=fetch_refs)
    return {"status": "fail", "final_url": url, "trace": trace, "fetch_refs": fetch_refs,
            "hint": _exhausted_hint()}


def fetch(url: str, success_selectors: list[str] | None = None,
          expected_title: str | None = None, *, no_third_party: bool | None = None) -> dict:
    """한 호출의 최종 확보 상태를 시도 로그와 구분해 기록한다."""
    result = {"status": "fail"}
    try:
        result = _fetch_ladder(url, success_selectors, expected_title, no_third_party=no_third_party)
        return result
    finally:
        try:
            audit = Path("audit")
            audit.mkdir(parents=True, exist_ok=True)
            row = {"kind": "final", "url": url, "ts": _now(), "status": result["status"],
                   "fetch_ref": result.get("fetch_ref"), "final_url": result.get("final_url")}
            with (audit / "fetch-log.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError:
            pass


def _result(status: str, res: dict, trace: list, note: str = "", fetch_refs: list[str] | None = None) -> dict:
    out = {"status": status, "final_url": res.get("final_url"), "http_status": res.get("status"),
           "archived_url": res.get("archived_url"), "mime": res.get("mime"),
           "text": res.get("text", ""), "raw": res.get("raw"), "is_pdf": res.get("is_pdf", False),
           "trace": trace, "note": note or res.get("_note", ""), "fetch_ref": res.get("_fetch_ref"),
           "fetch_refs": fetch_refs or []}
    if res.get("doc_kind"):
        out["doc_kind"] = res["doc_kind"]
    return out


def _html_title(html: str) -> str | None:
    """HTML <title> 우선, 없으면 og:title. PDF/없음은 None."""
    if not html:
        return None
    import html as _html
    import re
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1)))
        t = _html.unescape(t).strip()
        if t:
            return t
    og = _ogp_partial(html)
    if og and re.search(r"og:title", html, re.I):
        first = _html.unescape(og.split("\n", 1)[0]).strip()
        return first or None
    return None


# --- 저장(원본 + 정제본 + 해시 + 메타 사이드카) -----------------------------
def save(result: dict, out_dir: Path | str, url: str | None = None) -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    raw = result.get("raw")
    if raw is None and result.get("text"):
        raw = result["text"].encode("utf-8")
    if raw is None:
        return result
    sha = hashlib.sha256(raw).hexdigest()
    sha12 = sha[:12]
    binary = bool(result.get("is_pdf") or result.get("doc_kind"))
    if result.get("is_pdf"):
        ext = "pdf"
    elif result.get("doc_kind"):
        ext = result["doc_kind"]
    else:
        ext = "html" if "<" in result.get("text", "")[:200] else "txt"
    raw_name = f"{sha12}_raw.{ext}"
    (out / raw_name).write_bytes(raw)
    clean_name = None
    if not binary:
        clean = extract_text(result.get("text", ""))
        clean_name = f"{sha12}_clean.txt"
        (out / clean_name).write_text(clean, encoding="utf-8")
    accessed = _now()
    title = None if binary else _html_title(result.get("text") or "")
    status = result.get("status")
    if status not in ("ok", "partial"):
        status = "ok"
    meta = {
        "url": url if url is not None else result.get("url"),
        "final_url": result.get("final_url"),
        "http_status": result.get("http_status"),
        "mime": result.get("mime"),
        "is_pdf": bool(result.get("is_pdf")),
        "sha256": sha,
        "accessed_at": accessed,
        "title": title,
        "raw": raw_name,
        "clean": clean_name,
        "status": status,
        "fetch_ref": result.get("fetch_ref"),
    }
    meta_path = out / f"{sha12}.meta.json"
    if meta_path.exists():
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
        # 읽을 수 없는 이력은 덮어쓰지 않는다. legacy 최상위 필드는 최초 조회 그대로 유지한다.
        if not isinstance(previous, dict) or not isinstance(previous.get("urls", []), list):
            raise ValueError(f"출처 메타 형식 오류: {meta_path}")
        history = previous.get("urls") or [dict(previous)]
        previous["urls"] = [*history, meta]
        meta = previous
    else:
        meta = {**meta, "urls": [dict(meta)]}
    # blob은 공유하되 URL·최종 URL·상태·접근시각·fetch_ref 조회 이력은 누적한다.
    from facts_db import _write_bytes_atomic
    _write_bytes_atomic(meta_path, (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    result.update({"sha256": sha, "local": str(out / raw_name),
                   "clean": str(out / clean_name) if clean_name else None, "accessed_at": accessed})
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
    # 숫자 공인 IP는 DNS/외부 통신 없이 긍정형 경계를 검사한다.
    assert check_url_safe("https://93.184.216.34/") == "93.184.216.34"

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
    assert _html_title("<html><head><title>  Example Title </title></head></html>") == "Example Title"
    assert _html_title('<meta property="og:title" content="OG Title">') == "OG Title"
    assert _html_title("<html><body>없음</body></html>") is None

    # 메타 사이드카: 가짜 result 로 save → <sha12>.meta.json 필드 존재(오프라인)
    import tempfile
    html = ('<html><head><title>Example Title</title>'
            '<meta property="og:title" content="OG Title"></head>'
            '<body><p>hello sidecar</p></body></html>')
    fake = {"status": "ok", "final_url": "https://example.com/a", "http_status": 200,
            "mime": "text/html", "is_pdf": False, "text": html, "raw": None,
            "fetch_ref": "ref-demo"}
    with tempfile.TemporaryDirectory() as td:
        saved = save(fake, td, url="https://example.com/a")
        sha12 = saved["sha256"][:12]
        meta_path = Path(td) / f"{sha12}.meta.json"
        assert meta_path.is_file(), meta_path
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for k in ("url", "final_url", "http_status", "mime", "is_pdf", "sha256",
                  "accessed_at", "title", "raw", "clean", "status", "fetch_ref"):
            assert k in meta, k
        assert meta["url"] == "https://example.com/a"
        assert meta["final_url"] == "https://example.com/a"
        assert meta["http_status"] == 200
        assert meta["title"] == "Example Title"
        assert meta["raw"] == f"{sha12}_raw.html"
        assert meta["clean"] == f"{sha12}_clean.txt"
        assert meta["status"] == "ok"
        assert meta["fetch_ref"] == "ref-demo"
        assert (Path(td) / meta["raw"]).is_file()
        assert (Path(td) / meta["clean"]).is_file()
        # 기존 호출자 호환: url 생략해도 save 는 동작, meta.url 은 null
        fake2 = dict(fake, text="<html><body>x</body></html>", raw=None)
        saved2 = save(fake2, td)
        meta2 = json.loads((Path(td) / f"{saved2['sha256'][:12]}.meta.json").read_text(encoding="utf-8"))
        assert meta2["url"] is None
        # PDF: title/clean 은 null
        pdf_fake = {"status": "partial", "final_url": "https://example.com/a.pdf",
                    "http_status": 200, "mime": "application/pdf", "is_pdf": True,
                    "text": "", "raw": b"%PDF-1.4 demo", "fetch_ref": None}
        saved3 = save(pdf_fake, td, url="https://example.com/a.pdf")
        meta3 = json.loads((Path(td) / f"{saved3['sha256'][:12]}.meta.json").read_text(encoding="utf-8"))
        assert meta3["title"] is None and meta3["clean"] is None and meta3["is_pdf"] is True
        assert meta3["status"] == "partial"
        assert meta3["raw"].endswith(".pdf")

    print(f"[{_now()}] fetch demo OK (curl_cffi={'Y' if creq else 'N'}, "
          f"trafilatura={'Y' if trafilatura else 'N'}, CA={'ascii' if _CA_BUNDLE else 'default'})")


def _print_cli_result(result: dict) -> None:
    """stdout JSON을 자르지 않는다. 긴 trace는 감사 파일로 이동한다."""
    summary = {k: v for k, v in result.items() if k not in ("text", "raw")}
    summary.setdefault("sha256", None)
    summary.setdefault("local", None)
    trace = summary.get("trace", [])
    if len(json.dumps(trace, ensure_ascii=False)) > 1000:
        audit = Path("audit")
        audit.mkdir(parents=True, exist_ok=True)
        path = audit / f"fetch-trace-{uuid.uuid4().hex}.json"
        path.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary.pop("trace", None)
        summary.update(trace_path=path.as_posix(), trace_count=len(trace))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _cli_target(args: list[str]) -> tuple[str | None, str, bool]:
    """(url, out, no_third_party). `--no-third-party` 와 `--out` 은 위치와 무관하게 읽는다."""
    no_tp = "--no-third-party" in args or os.environ.get("MDR_NO_THIRD_PARTY") == "1"
    out = "_sources"
    url = None
    i = 1
    while i < len(args):
        item = args[i]
        if item == "--no-third-party":
            i += 1
            continue
        if item == "--out":
            out = args[i + 1]
            i += 2
            continue
        if url is None:
            url = item
        i += 1
    return url, out, no_tp


def main(args: list[str] | None = None) -> None:
    args = sys.argv[1:] if args is None else args
    if not args or args[0] == "demo":
        demo()
    elif args[0] in ("smoke", "get"):
        url, out, no_tp = _cli_target(args)
        if not url:
            print(__doc__)
            sys.exit(2)
        # 플래그가 꺼져 있으면 기존 호출 형태(fetch(url))를 유지한다.
        r = fetch(url, no_third_party=True) if no_tp else fetch(url)
        if args[0] == "get" and r["status"] in ("ok", "partial"):
            r = save(r, out, url=url)
        _print_cli_result(r)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):          # cp949 콘솔/파이프 UnicodeEncodeError 방지
        _reconf = getattr(_stream, "reconfigure", None)
        if _reconf:
            _reconf(encoding="utf-8", errors="replace")
    main()
