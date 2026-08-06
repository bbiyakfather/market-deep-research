"""harvest_images.py — 대표 이미지(도판) 수확: 소스 PDF 크롭 → 웹페이지 → 이미지 검색.

증빙캡처(capture_pdf: 숫자 하이라이트)와 목적이 다르다. 세부주제(단락) 이해를 돕는 도판
(지도·인포그래픽·개념도·위성사진)을 ① 이미 확보한 소스 PDF 에서 우선 수확하고(출처 자동
일치), ② 확보한 웹페이지의 이미지, ③ 부족분만 이미지 검색으로 보충한다. 후보는 팀리드가
육안 선별(Read)한 뒤 `[그림]` 캡션+출처로 본문 결박. 규율은 references/image-research.md.

CLI:
  python harvest_images.py pdf <file.pdf> [--out _images/harvest] [--min-pt 120]
  python harvest_images.py page <url>                      # og:image·본문 <img> 후보
  python harvest_images.py search "<query>" [--n 8]        # openverse+commons(+searx)
  python harvest_images.py get <image_url> --out _images/web [--name slug]
  python harvest_images.py demo                            # 오프라인 self-check
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

from fetch import check_url_safe, creq, TIMEOUT, _CA_BUNDLE
from skill_paths import ASSETS

MAX_IMG_BYTES = 15 * 1024 * 1024
MIN_IMG_BYTES = 8 * 1024                       # 아이콘·트래킹픽셀 컷
# 매직바이트 → 확장자 (svg 등 텍스트 포맷은 검증면이 넓어져 제외 — 래스터만)
MAGIC = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png", b"GIF8": ".gif", b"RIFF": ".webp"}
CAPTION_RE = re.compile(r"^\s*[\[\(【]?\s*(그림|Figure|Fig\.|자료|Exhibit|도표)", re.I)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) market-deep-research/1.0"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(s: str, n: int = 40) -> str:
    return re.sub(r"[^\w가-힣-]+", "_", s).strip("_")[:n] or "img"


# --- ① 소스 PDF 도판 수확 -----------------------------------------------------

def _merge_rects(rects: list[fitz.Rect], gap: float = 8.0) -> list[fitz.Rect]:
    """겹치거나 gap 이내로 인접한 rect 를 union (래스터+벡터 혼합 도판 병합)."""
    rects = [fitz.Rect(r) for r in rects]
    merged = True
    while merged:
        merged = False
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a = fitz.Rect(rects[i]); a.x0 -= gap; a.y0 -= gap; a.x1 += gap; a.y1 += gap
                if a.intersects(rects[j]):
                    rects[i] |= rects[j]; del rects[j]; merged = True; break
            if merged:
                break
    return rects


def _caption_below(page: fitz.Page, rect: fitz.Rect) -> str:
    """도판 바로 아래(60pt)에서 x-겹침 있는 텍스트 블록의 첫 줄 → 캡션 추정."""
    best = ""
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_rest, btype = b
        if btype != 0 or not text.strip():
            continue
        if rect.y1 - 5 <= y0 <= rect.y1 + 60 and min(x1, rect.x1) - max(x0, rect.x0) > rect.width * 0.3:
            line = text.strip().splitlines()[0][:120]
            if CAPTION_RE.search(line):
                return line                     # 명시적 캡션이 최우선
            best = best or line
    return best


def pdf_figures(pdf_path: Path | str, out_dir: Path | str = "_images/harvest",
                zoom: float = 2.0, min_pt: float = 120.0, max_per_page: int = 4) -> dict:
    """소스 PDF 전수 스캔 → 도판 후보 크롭 + 캡션 추정 + index.json.

    래스터(get_image_info) + 벡터(cluster_drawings) 후보를 병합 크롭. 반복 로고(3+페이지
    동일 xref)·아이콘(min_pt 미만)·전면 텍스트영역은 제외. 선별은 팀리드 육안(Read)."""
    pdf_path = Path(pdf_path)
    out = Path(out_dir) / _slug(pdf_path.stem)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))

    # 반복 배치 xref(페이지 장식·로고) 사전 집계
    xref_pages: dict[int, set] = {}
    for pno in range(doc.page_count):
        for info in doc[pno].get_image_info(xrefs=True):
            xref_pages.setdefault(info.get("xref", 0), set()).add(pno)
    deco = {x for x, ps in xref_pages.items() if len(ps) >= 3}

    results, seen = [], set()
    for pno in range(doc.page_count):
        page = doc[pno]
        cand: list[fitz.Rect] = []
        for info in page.get_image_info(xrefs=True):
            if info.get("xref", 0) in deco:
                continue
            r = fitz.Rect(info["bbox"])
            if min(r.width, r.height) >= min_pt:
                cand.append(r)
        for r in page.cluster_drawings():
            if min(r.width, r.height) >= min_pt:
                # 텍스트 밀도 높은 클러스터(표·박스글)는 도판 아님
                if len(page.get_text("text", clip=r)) <= 400:
                    cand.append(fitz.Rect(r))
        rects = _merge_rects(cand)
        # 전면 배경(페이지의 85%+ 이면서 장문 포함) 제외, 큰 것부터 페이지당 상한
        pa = abs(page.rect)
        rects = [r for r in rects
                 if not (abs(r) > pa * 0.85 and len(page.get_text("text", clip=r)) > 800)]
        rects.sort(key=lambda r: -abs(r))
        for k, r in enumerate(rects[:max_per_page]):
            clip = fitz.Rect(max(0, r.x0 - 6), max(0, r.y0 - 6),
                             min(page.rect.x1, r.x1 + 6), min(page.rect.y1, r.y1 + 6))
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
            digest = hashlib.sha1(pix.samples).hexdigest()[:16]
            if digest in seen:                  # 문서 내 동일 도판 중복 제거
                continue
            seen.add(digest)
            fname = f"{_slug(pdf_path.stem)}_p{pno + 1:02d}_{k}.png"
            pix.save(str(out / fname))
            results.append({"file": str(out / fname), "page": pno + 1,
                            "bbox": [round(v, 1) for v in r], "caption": _caption_below(page, r),
                            "source": str(pdf_path), "sha1": digest})
    doc.close()
    (out / "index.json").write_text(json.dumps(
        {"source": str(pdf_path), "at": _now(), "figures": results},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "count": len(results), "out": str(out), "figures": results}


# --- ② 확보한 웹페이지 이미지 후보 --------------------------------------------

def page_images(url: str) -> dict:
    """fetch 사다리로 페이지 HTML 확보 → og:image·본문 <img> 후보(절대 URL)."""
    from fetch import fetch as _fetch
    r = _fetch(url)
    html = r.get("text") or ""
    if not html:                                 # 정제본이 비면 원본 bytes 를 디코드해 쓴다
        raw = r.get("raw")
        html = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else (raw or "")
    if not html:
        return {"ok": False, "url": url, "note": r.get("note", "fetch 실패"), "candidates": []}
    cands, seen = [], set()
    for m in re.finditer(r'property=["\'](?:og:image|twitter:image)["\']\s+content=["\']([^"\']+)', html):
        cands.append({"url": m.group(1), "kind": "og:image"})
    for m in re.finditer(r'<img\b[^>]*?src=["\']([^"\']+)["\']', html, re.I):
        src = m.group(1)
        if src.startswith("data:") or re.search(r"(logo|icon|sprite|pixel|avatar)", src, re.I):
            continue
        cands.append({"url": src, "kind": "img"})
    out = []
    for c in cands:
        absu = urllib.parse.urljoin(r.get("final_url", url), c["url"])
        if absu not in seen:
            seen.add(absu); out.append({**c, "url": absu})
    return {"ok": True, "url": url, "candidates": out[:30]}


# --- ③ 이미지 검색 (무료: openverse·commons·searx) -----------------------------

def _json_get(url: str, timeout: int = 12) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _openverse(query: str, n: int) -> list[dict]:
    q = urllib.parse.quote(query)
    d = _json_get(f"https://api.openverse.org/v1/images/?q={q}&page_size={n}")
    return [{"url": r.get("url"), "title": r.get("title", ""), "license": r.get("license", ""),
             "page": r.get("foreign_landing_url", ""), "source": "openverse"}
            for r in d.get("results", []) if r.get("url")]


def _commons(query: str, n: int) -> list[dict]:
    q = urllib.parse.quote(query)
    d = _json_get("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                  f"&generator=search&gsrsearch={q}&gsrnamespace=6&gsrlimit={n}"
                  "&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=1400")
    out = []
    for p in (d.get("query", {}).get("pages", {}) or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        lic = (ii.get("extmetadata", {}).get("LicenseShortName", {}) or {}).get("value", "")
        if ii.get("thumburl") or ii.get("url"):
            out.append({"url": ii.get("thumburl") or ii.get("url"), "title": p.get("title", ""),
                        "license": lic, "page": ii.get("descriptionurl", ""), "source": "commons"})
    return out


def _searx_images(query: str, n: int) -> list[dict]:
    insts = json.loads((ASSETS / "searx-instances.json").read_text(encoding="utf-8"))["instances"]
    q = urllib.parse.quote(query)
    for inst in insts:
        try:
            d = _json_get(f"{inst.rstrip('/')}/search?q={q}&categories=images&format=json", timeout=10)
            rs = [{"url": r.get("img_src"), "title": r.get("title", ""), "license": "",
                   "page": r.get("url", ""), "source": f"searx"}
                  for r in d.get("results", [])[:n] if r.get("img_src")]
            if rs:
                return rs
        except Exception:
            continue                            # 인스턴스 불가 → 다음 (degrade)
    return []


def search_images(query: str, n: int = 8) -> list[dict]:
    """무료 소스 병합 검색. 라이선스 표기 있는 소스(openverse·commons) 우선."""
    out, seen = [], set()
    for fn in (_openverse, _commons, _searx_images):
        try:
            for r in fn(query, n):
                if r["url"] not in seen:
                    seen.add(r["url"]); out.append(r)
        except Exception:
            continue
    return out[: n * 2]


# --- ④ 검증 다운로드 -----------------------------------------------------------

def download(url: str, out_dir: Path | str = "_images/web", name: str | None = None) -> dict:
    """SSRF 경계 + 매직바이트·크기 검증 통과분만 저장. 실패는 ok:false 로 정직 반환."""
    check_url_safe(url)
    if creq is not None:
        r = creq.get(url, impersonate="chrome", timeout=TIMEOUT, verify=_CA_BUNDLE or True,
                     headers={"User-Agent": UA})
        status, body = r.status_code, r.content
    else:                                        # curl_cffi 미설치 degrade
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status, body = resp.status, resp.read(MAX_IMG_BYTES + 1)
    if status != 200:                            # 429/403 에러페이지를 이미지 실패로 오보하지 않기
        return {"ok": False, "url": url, "note": f"HTTP {status}"}
    if len(body) > MAX_IMG_BYTES:
        return {"ok": False, "url": url, "note": f"크기 초과 {len(body)}B"}
    if len(body) < MIN_IMG_BYTES:
        return {"ok": False, "url": url, "note": f"너무 작음 {len(body)}B(아이콘 의심)"}
    ext = next((e for m, e in MAGIC.items() if body[:12].startswith(m) or m in body[:12]), None)
    if not ext:
        return {"ok": False, "url": url, "note": "이미지 매직바이트 아님(html/svg 등)"}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    stem = _slug(name or Path(urllib.parse.urlparse(url).path).stem)
    path = out / f"{stem}{ext}"
    i = 1
    while path.exists():
        path = out / f"{stem}_{i}{ext}"; i += 1
    path.write_bytes(body)
    return {"ok": True, "file": str(path), "url": url, "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(), "accessed_at": _now()}


# --- demo (오프라인 self-check) -------------------------------------------------

def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # 합성 PDF: 큰 도판 1 + 캡션 + 아이콘(제외돼야) + 본문
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 60)); pix.clear_with(90)
        big = fitz.Rect(80, 120, 480, 420)
        page.insert_image(big, pixmap=pix)
        # 데모는 helv 폰트라 ASCII 캡션 사용(한글은 실제 PDF 의 내장폰트에서 정상 추출됨)
        page.insert_text((180, 445), "[Figure] test hydrogen concept", fontsize=10)
        page.insert_image(fitz.Rect(20, 20, 50, 50), pixmap=pix)          # 아이콘(min_pt 컷)
        page.insert_text((80, 500), "body text " * 30, fontsize=9)
        p = Path(td) / "t.pdf"; doc.save(str(p)); doc.close()

        r = pdf_figures(p, Path(td) / "harvest", min_pt=120)
        assert r["ok"] and r["count"] == 1, r
        assert "Figure" in r["figures"][0]["caption"], r["figures"][0]
        assert Path(r["figures"][0]["file"]).stat().st_size > 500, "크롭 파일 비정상"

        # 매직바이트 검증: png OK / html 거부 (download 의 판정부만 로컬 검증)
        assert next((e for m, e in MAGIC.items() if b"\x89PNG_test"[:12].startswith(m)), None) == ".png"
        assert next((e for m, e in MAGIC.items() if b"<html><body>"[:12].startswith(m)), None) is None
        # SSRF 경계가 물려 있는지 (내부 IP 거부)
        try:
            check_url_safe("http://127.0.0.1/x.png"); raise AssertionError("SSRF 미차단")
        except ValueError:
            pass

        # page_images: fetch 는 raw 를 bytes 로 준다(fetch.py `_result`) — str 정규식이 죽지 않아야 한다
        import types
        _real = sys.modules.get("fetch")
        _stub = types.ModuleType("fetch")
        for _n in ("check_url_safe", "creq", "TIMEOUT", "_CA_BUNDLE"):
            setattr(_stub, _n, globals()[_n])
        _stub.fetch = lambda u, **kw: {
            "final_url": u, "text": "",
            "raw": b'<html><meta property="og:image" content="https://e.test/f.png">'
                   b'<img src="/in/body.jpg"><img src="/logo.png"></html>'}
        sys.modules["fetch"] = _stub
        try:
            pi = page_images("https://e.test/a")
        finally:
            sys.modules["fetch"] = _real if _real else sys.modules.pop("fetch", None)
        kinds = {c["kind"] for c in pi["candidates"]}
        assert pi["ok"] and {"og:image", "img"} <= kinds, pi
        assert all(c["url"].startswith("http") for c in pi["candidates"]), pi   # 절대 URL 화
        assert not any("logo" in c["url"] for c in pi["candidates"]), "로고 제외 실패"

        # _searx_images: 인스턴스 목록은 dict 의 "instances" 키 — 키 문자열을 URL 로 조립하면 안 된다
        _insts = json.loads((ASSETS / "searx-instances.json").read_text(encoding="utf-8"))["instances"]
        assert _insts and all(u.startswith("https://") for u in _insts), _insts
    print(f"[{_now()}] harvest_images demo OK")


if __name__ == "__main__":
    import io
    # 한글 Windows 콘솔(cp949)이 PDF 특수문자(❍ 등)에서 죽는 것 방지
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif args[0] == "pdf" and len(args) >= 2:
        out = args[args.index("--out") + 1] if "--out" in args else "_images/harvest"
        mp = float(args[args.index("--min-pt") + 1]) if "--min-pt" in args else 120.0
        r = pdf_figures(args[1], out, min_pt=mp)
        print(json.dumps({k: v for k, v in r.items() if k != "figures"}, ensure_ascii=False))
        for f in r["figures"]:
            print(f"  p{f['page']:>3} {Path(f['file']).name}  {f['caption'][:60]}")
    elif args[0] == "page" and len(args) >= 2:
        print(json.dumps(page_images(args[1]), ensure_ascii=False, indent=1))
    elif args[0] == "search" and len(args) >= 2:
        n = int(args[args.index("--n") + 1]) if "--n" in args else 8
        print(json.dumps(search_images(args[1], n), ensure_ascii=False, indent=1))
    elif args[0] == "get" and len(args) >= 2:
        out = args[args.index("--out") + 1] if "--out" in args else "_images/web"
        name = args[args.index("--name") + 1] if "--name" in args else None
        print(json.dumps(download(args[1], out, name), ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
