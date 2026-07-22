"""fetch.py — 자체 fetch/extract 스택 (plan-v2 핵심설계3 + v3-C).

보안경계(선제) → curl_cffi TLS 그리드 → Jina Reader → Wayback → (실패 시) insane-search 위임 신호.
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
from urllib.parse import quote, urlparse

MAX_BYTES = 8 * 1024 * 1024
TIMEOUT = 25
IMPERSONATE_GRID = ["chrome", "safari", "chrome110"]
ALLOWED_MIME = ("text/html", "text/plain", "application/json", "application/xml",
                "application/xhtml", "application/pdf", "application/rss")
CHALLENGE_MARKERS = ("just a moment", "access denied", "cf-challenge", "datadome",
                     "sec-if-cpt-container", "enable javascript and cookies",
                     "verifying you are human", "captcha-delivery")

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
    certifi 번들 경로가 non-ASCII면 ASCII 경로로 1회 복사해 그 경로를 쓴다. verify는 항상 ON."""
    try:
        import certifi
    except Exception:
        return None
    ca = certifi.where()
    try:
        ca.encode("ascii"); return ca                # 이미 ASCII면 그대로
    except UnicodeEncodeError:
        pass
    for base in (os.environ.get("ProgramData", r"C:\ProgramData"),
                 (os.environ.get("SystemDrive", "C:") + "\\")):
        try:
            dst = Path(base) / "factsheet-research" / "cacert.pem"
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or dst.stat().st_size != Path(ca).stat().st_size:
                shutil.copyfile(ca, dst)
            s = str(dst); s.encode("ascii"); return s
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


# --- 4계층 성공검증 (R2) -----------------------------------------------------
def validate_body(text: str, status: int, success_selectors: list[str] | None = None) -> dict:
    """{verdict: ok|partial|challenge|empty, reason}. HTTP200 ≠ 성공."""
    low = (text or "").lower()
    for m in CHALLENGE_MARKERS:                       # ① 챌린지 마커
        if m in low:
            return {"verdict": "challenge", "reason": f"challenge marker: {m}"}
    n = len(text or "")
    if n < 200:                                        # ② 비정상 크기(빈 SPA/차단)
        return {"verdict": "empty", "reason": f"too small ({n}B)"}
    if success_selectors and any(s.lower() in low for s in success_selectors):
        return {"verdict": "ok", "reason": "success selector matched"}  # ④ 성공 셀렉터
    body = extract_text(text)
    if len(body) >= 1000:
        return {"verdict": "ok", "reason": f"body {len(body)} chars"}
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
def _fetch_once(url: str, impersonate: str, max_redirects: int = 5) -> dict:
    if creq is None:
        return {"ok": False, "reason": "curl_cffi 미설치", "status": None, "text": "", "final_url": url}
    cur = url
    for _ in range(max_redirects + 1):
        check_url_safe(cur)                             # 각 홉 SSRF 검증
        _kw = {"verify": _CA_BUNDLE} if _CA_BUNDLE else {}
        r = creq.get(cur, impersonate=impersonate, timeout=TIMEOUT,
                     allow_redirects=False, stream=True, **_kw)
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("location") or r.headers.get("Location")
            r.close()
            if not loc:
                return {"ok": False, "reason": "redirect without Location", "status": r.status_code,
                        "text": "", "final_url": cur}
            cur = loc if loc.startswith("http") else f"{urlparse(cur).scheme}://{urlparse(cur).hostname}{loc}"
            continue
        mime = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
        buf = b""
        for chunk in r.iter_content(chunk_size=65536):
            buf += chunk
            if len(buf) > MAX_BYTES:
                r.close()
                return {"ok": False, "reason": "oversize", "status": r.status_code,
                        "text": "", "final_url": cur, "mime": mime}
        r.close()
        is_pdf = mime == "application/pdf" or cur.lower().endswith(".pdf")
        text = "" if is_pdf else buf.decode("utf-8", errors="replace")
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


def fetch(url: str, success_selectors: list[str] | None = None) -> dict:
    """자체 사다리 전체. 반환 status ∈ {ok, partial, fail, delegate}.
    delegate = 자체 스택 소진 → 오케스트레이터가 insane-search 스킬로 위임."""
    trace: list[dict] = []
    partial_res: dict | None = None
    check_url_safe(url)                                 # 진입 전 1차 검증

    # 1) curl_cffi TLS 그리드(전수)
    for imp in IMPERSONATE_GRID:
        try:
            res = _fetch_once(url, imp)
        except SsrfBlocked:
            raise
        except Exception as e:
            trace.append({"tier": f"curl_cffi:{imp}", "error": str(e)}); continue
        if not res.get("ok"):
            trace.append({"tier": f"curl_cffi:{imp}", "fail": res.get("reason")}); continue
        if res.get("is_pdf"):
            return _result("ok", res, trace, note="pdf")
        v = validate_body(res["text"], res.get("status", 0), success_selectors)
        trace.append({"tier": f"curl_cffi:{imp}", "verdict": v["verdict"], "reason": v["reason"]})
        if v["verdict"] == "ok":
            return _result("ok", res, trace)
        if v["verdict"] == "partial":
            partial_res = res
    # 2) Jina Reader
    try:
        jr = _via_jina(url)
        if jr.get("ok"):
            v = validate_body(jr["text"], jr.get("status", 0), success_selectors)
            trace.append({"tier": "jina", "verdict": v["verdict"]})
            if v["verdict"] in ("ok", "partial"):
                return _result(v["verdict"], jr, trace)
    except SsrfBlocked:
        raise
    except Exception as e:
        trace.append({"tier": "jina", "error": str(e)})
    # 3) Wayback
    try:
        wb = _via_wayback(url)
        if wb.get("ok"):
            v = validate_body(wb["text"], wb.get("status", 0), success_selectors)
            trace.append({"tier": "wayback", "verdict": v["verdict"]})
            if v["verdict"] in ("ok", "partial"):
                return _result(v["verdict"], wb, trace)
    except Exception as e:
        trace.append({"tier": "wayback", "error": str(e)})

    if partial_res is not None:
        return _result("partial", partial_res, trace)
    # 4) 소진 → 위임 신호
    return {"status": "delegate", "final_url": url, "trace": trace,
            "hint": "insane-search 스킬로 위임(강방어 사이트)"}


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
    print(f"[{_now()}] fetch demo OK (curl_cffi={'Y' if creq else 'N'}, "
          f"trafilatura={'Y' if trafilatura else 'N'}, CA={'ascii' if _CA_BUNDLE else 'default'})")


if __name__ == "__main__":
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
