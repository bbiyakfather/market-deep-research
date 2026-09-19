"""harvest_images.py — 대표 이미지(도판) 수확: 소스 PDF 크롭 → 웹페이지 → 이미지 검색.

증빙캡처(capture_pdf: 숫자 하이라이트)와 목적이 다르다. 세부주제(단락) 이해를 돕는 도판
(지도·인포그래픽·개념도·위성사진)을 ① 이미 확보한 소스 PDF 에서 우선 수확하고(출처 자동
일치), ② 확보한 웹페이지의 이미지, ③ 부족분만 이미지 검색으로 보충한다. 후보는 팀리드가
육안 선별(Read)한 뒤 `[그림]` 캡션+출처로 본문 결박. 규율은 references/image-research.md.

CLI:
  python harvest_images.py pdf <file.pdf> [--out _images/harvest] [--min-pt 120] [--min-score -20]
  python harvest_images.py page <url>                      # og:image·본문 <img> 후보
  python harvest_images.py search "<query>" [--n 8] [--sites iea.org,irena.org]
  python harvest_images.py get <image_url> --out _images/web [--name slug]
  python harvest_images.py index <work_dir>                # _images/IMAGES.md 생성
  python harvest_images.py demo                            # 오프라인 self-check
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import fitz  # PyMuPDF

from fetch import (check_url_safe, creq, request_bytes, response_text,
                   DownloadLimitError, MAX_IMG_BYTES)
from skill_paths import ASSETS

MIN_IMG_BYTES = 8 * 1024                       # 아이콘·트래킹픽셀 컷
# 매직바이트 → 확장자 (svg 등 텍스트 포맷은 검증면이 넓어져 제외 — 래스터만)
MAGIC = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png", b"GIF8": ".gif", b"RIFF": ".webp"}
CAPTION_RE = re.compile(r"^\s*[\[\(【]?\s*(그림|Figure|Fig\.|자료|Exhibit|도표)", re.I)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) market-deep-research/1.0"
PDF_HINT = "PDF 후보: 다운로드한 뒤 `pdf` 서브커맨드로 도판을 크롭하세요."
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


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


def _caption_near(page: fitz.Page, rect: fitz.Rect) -> tuple[str, bool]:
    """도판 위·아래 60pt의 캡션 후보와 명시적 캡션 여부를 반환한다."""
    nearby: list[tuple[float, str, bool]] = []
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_rest, btype = b
        if btype != 0 or not text.strip():
            continue
        overlap = min(x1, rect.x1) - max(x0, rect.x0)
        if overlap <= rect.width * 0.3:
            continue
        below = rect.y1 - 5 <= y0 <= rect.y1 + 60
        above = rect.y0 - 60 <= y1 <= rect.y0 + 5
        if not (above or below):
            continue
        line = text.strip().splitlines()[0][:120]
        distance = max(0.0, y0 - rect.y1) if below else max(0.0, rect.y0 - y1)
        nearby.append((distance, line, bool(CAPTION_RE.search(line))))
    if not nearby:
        return "", False
    # 저자가 Figure/그림 등으로 명시한 캡션이 단순 인접 문장보다 항상 우선이다.
    nearby.sort(key=lambda item: (not item[2], item[0]))
    _distance, line, explicit = nearby[0]
    return line, explicit


def _caption_below(page: fitz.Page, rect: fitz.Rect) -> str:
    """기존 내부 호출과의 호환을 위한 캡션 문자열 래퍼."""
    return _caption_near(page, rect)[0]


def _rect_signature(rect: fitz.Rect, page_rect: fitz.Rect) -> tuple[int, int, int, int]:
    """페이지 크기가 달라도 반복 배치를 찾도록 좌표를 2% 격자로 정규화한다."""
    vals = (rect.x0 / page_rect.width, rect.y0 / page_rect.height,
            rect.x1 / page_rect.width, rect.y1 / page_rect.height)
    return tuple(round(value / 0.02) for value in vals)


def _infographic_score(page: fitz.Page, rect: fitz.Rect, caption: str, explicit_caption: bool,
                       vector_elements: int, repeat_pages: int) -> tuple[float, dict]:
    """로고·장식보다 설명력 있는 도판을 위로 올리는 휴리스틱 점수.

    가중치 근거: 명시적 캡션(+45)은 저자의 도판 선언이므로 가장 강하고,
    면적(+35)은 작은 로고를 얇게 걸러낸다. 벡터 밀도(+20)는 단일 래스터
    사진보다 정보 도해일 가능성을 높인다. 반복 배치(-22/-60)와 극단적
    종횡비(-10/-22), 초소형 정사각형(-14)은 머리말·배너·아이콘을 강하게 내린다.
    """
    page_area = max(abs(page.rect), 1.0)
    area_ratio = max(0.0, min(abs(rect) / page_area, 1.0))
    area_points = 35.0 * min(area_ratio / 0.35, 1.0)

    short_side = max(min(rect.width, rect.height), 0.1)
    aspect_ratio = max(rect.width, rect.height) / short_side
    aspect_penalty = -22.0 if aspect_ratio >= 7.0 else (-10.0 if aspect_ratio >= 4.0 else 0.0)
    small_square_penalty = -14.0 if aspect_ratio <= 1.25 and area_ratio < 0.04 else 0.0

    caption_points = 45.0 if explicit_caption else (6.0 if caption else 0.0)
    # 10,000pt² 당 벡터 path 수를 밀도로 보며, 3개 이상이면 가산점을 포화한다.
    vector_density = vector_elements / max(abs(rect) / 10000.0, 1.0)
    vector_points = 20.0 * min(vector_density / 3.0, 1.0)
    repeat_penalty = -60.0 if repeat_pages >= 3 else (-22.0 if repeat_pages == 2 else 0.0)

    score = area_points + caption_points + vector_points + aspect_penalty + small_square_penalty + repeat_penalty
    signals = {
        "area_ratio": round(area_ratio, 4),
        "aspect_ratio": round(aspect_ratio, 2),
        "explicit_caption": explicit_caption,
        "vector_elements": vector_elements,
        "vector_density": round(vector_density, 2),
        "repeat_pages": repeat_pages,
    }
    return round(score, 2), signals


def pdf_figures(pdf_path: Path | str, out_dir: Path | str = "_images/harvest",
                zoom: float = 2.0, min_pt: float = 120.0, max_per_page: int = 4,
                min_score: float = -20.0) -> dict:
    """소스 PDF 전수 스캔 → 도판 후보 크롭 + 캡션 추정 + index.json.

    래스터(get_image_info) + 벡터(cluster_drawings) 후보를 병합 크롭. 반복 로고(3+페이지
    동일 xref)·아이콘(min_pt 미만)·전면 텍스트영역은 제외. 선별은 팀리드 육안(Read)."""
    pdf_path = Path(pdf_path)
    out = Path(out_dir) / _slug(pdf_path.stem)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))

    # 반복 xref(페이지 장식·로고)는 기존처럼 제외한다. xref=0은 서로
    # 다른 inline image일 수 있어 반복 판정에 쓰지 않는다.
    xref_pages: dict[int, set] = {}
    for pno in range(doc.page_count):
        for info in doc[pno].get_image_info(xrefs=True):
            xref = info.get("xref", 0)
            if xref:
                xref_pages.setdefault(xref, set()).add(pno)
    deco = {x for x, ps in xref_pages.items() if len(ps) >= 3}

    staged: list[dict] = []
    for pno in range(doc.page_count):
        page = doc[pno]
        cand: list[fitz.Rect] = []
        for info in page.get_image_info(xrefs=True):
            if info.get("xref", 0) in deco:
                continue
            r = fitz.Rect(info["bbox"])
            if min(r.width, r.height) >= min_pt:
                cand.append(r)
        drawings = page.get_drawings()
        drawing_rects = [fitz.Rect(item["rect"]) for item in drawings]
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
        for r in rects:
            vector_elements = sum(1 for drawing_rect in drawing_rects if drawing_rect.intersects(r))
            caption, explicit = _caption_near(page, r)
            staged.append({"page_no": pno, "rect": r, "caption": caption,
                           "explicit_caption": explicit, "vector_elements": vector_elements,
                           "signature": _rect_signature(r, page.rect)})

    signature_pages: dict[tuple[int, int, int, int], set[int]] = {}
    for item in staged:
        signature_pages.setdefault(item["signature"], set()).add(item["page_no"])
    for item in staged:
        page = doc[item["page_no"]]
        repeat_pages = len(signature_pages[item["signature"]])
        item["score"], item["score_signals"] = _infographic_score(
            page, item["rect"], item["caption"], item["explicit_caption"],
            item["vector_elements"], repeat_pages)

    # 페이지당 상한을 점수로 적용한 뒤, 전체 문서 순서도 점수 내림차순으로 보장한다.
    selected: list[dict] = []
    for pno in range(doc.page_count):
        page_items = [item for item in staged
                      if item["page_no"] == pno and item["score"] >= min_score]
        page_items.sort(key=lambda item: (-item["score"], -abs(item["rect"])))
        for local_rank, item in enumerate(page_items[:max_per_page]):
            item["local_rank"] = local_rank
            selected.append(item)
    selected.sort(key=lambda item: (-item["score"], item["page_no"], item["local_rank"]))

    results, seen = [], set()
    for item in selected:
        pno, r = item["page_no"], item["rect"]
        page = doc[pno]
        clip = fitz.Rect(max(0, r.x0 - 6), max(0, r.y0 - 6),
                         min(page.rect.x1, r.x1 + 6), min(page.rect.y1, r.y1 + 6))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
        digest = hashlib.sha1(pix.samples).hexdigest()[:16]
        if digest in seen:                      # 문서 내 동일 도판 중복 제거
            continue
        seen.add(digest)
        fname = f"{_slug(pdf_path.stem)}_p{pno + 1:02d}_{item['local_rank']}.png"
        pix.save(str(out / fname))
        results.append({"file": str(out / fname), "page": pno + 1,
                        "bbox": [round(v, 1) for v in r], "caption": item["caption"],
                        "score": item["score"], "score_signals": item["score_signals"],
                        "source": str(pdf_path), "license": "unknown", "sha1": digest})
    for rank, result in enumerate(results, 1):
        result["rank"] = rank
    doc.close()
    (out / "index.json").write_text(json.dumps(
        {"source": str(pdf_path), "at": _now(), "figures": results},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "count": len(results), "out": str(out), "figures": results}


# --- ② 확보한 웹페이지 이미지 후보 --------------------------------------------


class _PageImageParser(HTMLParser):
    """`figure` 구조와 일반 `img` 인접 텍스트를 보존하는 경량 파서."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.candidates: list[dict] = []
        self.figures: list[dict] = []
        self._figure_stack: list[dict] = []
        self._figcaption_depth = 0
        self._last_text = ""
        self._pending_image: dict | None = None

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.lower(): value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = self._attrs(attrs)
        if tag == "meta":
            prop = (values.get("property") or values.get("name") or "").lower()
            if prop in {"og:image", "twitter:image"} and values.get("content"):
                self.candidates.append({"url": values["content"], "kind": "og:image",
                                        "caption": "", "alt": "", "adjacent_text": ""})
            return
        if tag == "figure":
            self._figure_stack.append({"images": [], "caption_parts": []})
            return
        if tag == "figcaption" and self._figure_stack:
            self._figcaption_depth += 1
            return
        if tag != "img":
            return
        src = values.get("src") or values.get("data-src") or values.get("data-original")
        if not src:
            return
        alt = re.sub(r"\s+", " ", values.get("alt", "")).strip()[:240]
        image = {"url": src, "kind": "img", "caption": alt, "alt": alt,
                 "adjacent_text": self._last_text[-240:]}
        if self._figure_stack:
            self._figure_stack[-1]["images"].append(image)
        else:
            self.candidates.append(image)
        self._pending_image = image

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "figcaption" and self._figcaption_depth:
            self._figcaption_depth -= 1
        elif tag == "figure" and self._figure_stack:
            figure = self._figure_stack.pop()
            caption = re.sub(r"\s+", " ", " ".join(figure["caption_parts"])).strip()[:500]
            for image in figure["images"]:
                image["kind"] = "figure"
                image["figcaption"] = caption
                image["caption"] = caption or image["alt"] or image["adjacent_text"]
                self.figures.append(image)
            self._pending_image = None

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._figure_stack and self._figcaption_depth:
            self._figure_stack[-1]["caption_parts"].append(text)
        elif self._pending_image is not None:
            # alt가 없을 때 이미지 뒤의 첫 텍스트를 보조 캡션으로 사용한다.
            adjacent = text[:240]
            before = self._pending_image.get("adjacent_text", "")
            self._pending_image["adjacent_text"] = " ".join(part for part in (before, adjacent) if part)
            if not self._pending_image.get("caption"):
                self._pending_image["caption"] = adjacent
            self._pending_image = None
        self._last_text = text


def _parse_page_images(html: str, base_url: str) -> list[dict]:
    """HTML 조각을 네트워크 없이 파싱하여 절대 URL 후보를 만든다."""
    parser = _PageImageParser()
    parser.feed(html)
    parser.close()
    # figure를 먼저 두어 동일 URL의 og:image보다 풍부한 figcaption을 보존한다.
    candidates = parser.figures + parser.candidates
    out_by_url: dict[str, dict] = {}
    for candidate in candidates:
        src = candidate["url"]
        if src.startswith("data:") or re.search(r"(logo|icon|sprite|pixel|avatar)", src, re.I):
            continue
        absolute = urllib.parse.urljoin(base_url, src)
        existing = out_by_url.get(absolute)
        normalized = {**candidate, "url": absolute}
        if existing is None:
            out_by_url[absolute] = normalized
        elif normalized.get("caption") and not existing.get("caption"):
            existing.update(normalized)
    return list(out_by_url.values())[:30]


def page_images(url: str) -> dict:
    """fetch 사다리로 HTML 확보 → figure/figcaption·og:image·img 후보."""
    from fetch import fetch as _fetch
    r = _fetch(url)
    raw = r.get("raw")
    html = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else (raw or r.get("text") or "")
    if not html:
        return {"ok": False, "url": url,
                "note": r.get("note") or r.get("reason") or "fetch 실패", "candidates": []}
    return {"ok": True, "url": url,
            "candidates": _parse_page_images(html, r.get("final_url", url))}


# --- ③ 이미지 검색 (무료: openverse·commons·searx) -----------------------------

def _json_get(url: str, timeout: int = 12) -> dict | list:
    response = request_bytes(url, timeout=timeout, headers={"User-Agent": UA}, client=creq)
    if not 200 <= response["status"] < 300:
        raise urllib.error.HTTPError(url, response["status"], "검색 요청 실패", None, None)
    return json.loads(response_text(response))


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


def _searx_instances() -> list[str]:
    data = json.loads((ASSETS / "searx-instances.json").read_text(encoding="utf-8"))
    values = data.get("instances", []) if isinstance(data, dict) else data
    return [str(value) for value in values if isinstance(value, str) and value.startswith("https://")]


def _searx_images(query: str, n: int) -> list[dict]:
    insts = _searx_instances()
    q = urllib.parse.quote(query)
    errors: list[dict] = []
    for inst in insts:
        try:
            d = _json_get(f"{inst.rstrip('/')}/search?q={q}&categories=images&format=json", timeout=10)
            rs = [{"url": r.get("img_src"), "title": r.get("title", ""), "license": "",
                   "page": r.get("url", ""), "source": f"searx"}
                  for r in d.get("results", [])[:n] if r.get("img_src")]
            if rs:
                return rs + errors
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code in {403, 429}:
                errors.append({"url": "", "title": "", "license": "", "page": "",
                               "source": "searx", "kind": "error", "note": f"HTTP {code}"})
            continue                            # 인스턴스 불가 → 다음 (degrade)
    return errors


def _curated_domains() -> list[str]:
    """assets/curated-sources.json의 기존 도메인을 읽어 코드 상수 중복을 피한다."""
    try:
        data = json.loads((ASSETS / "curated-sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    raw = data.get("curated_domains", {})
    values = raw.values() if isinstance(raw, dict) else []
    out: list[str] = []
    for group in values:
        if not isinstance(group, list):
            continue
        for domain in group:
            normalized = str(domain).strip().lower().lstrip("*.")
            if re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", normalized) and normalized not in out:
                out.append(normalized)
    return out


def _normalize_sites(sites: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if sites is None:
        return []
    values = sites.split(",") if isinstance(sites, str) else sites
    out: list[str] = []
    for value in values:
        domain = str(value).strip().lower()
        if "://" in domain:
            domain = urllib.parse.urlparse(domain).hostname or ""
        domain = domain.lstrip("*.").strip("./")
        if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", domain):
            raise ValueError(f"잘못된 --sites 도메인: {value}")
        if domain not in out:
            out.append(domain)
    return out


def _host_allowed(url: str, sites: list[str]) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return any(host == site or host.endswith("." + site) for site in sites)


def _is_pdf_url(url: str) -> bool:
    return bool(re.search(r"\.pdf(?:$|[?#])", url, re.I))


def _annotate_search_candidate(candidate: dict) -> dict:
    """PDF 링크를 이미지처럼 버리지 않고 크롭 작업으로 연결한다."""
    target = candidate.get("page") or candidate.get("url") or ""
    if _is_pdf_url(target) or _is_pdf_url(candidate.get("url") or ""):
        candidate = {**candidate, "kind": "pdf", "hint": PDF_HINT}
    return candidate


def _searx_sites(query: str, n: int, sites: list[str]) -> list[dict]:
    """기관 도메인으로 제한한 일반 검색. PDF·보도자료 페이지를 그대로 보존한다."""
    if not sites:
        return []
    insts = _searx_instances()
    restriction = " OR ".join(f"site:{site}" for site in sites)
    q = urllib.parse.quote(f"{query} ({restriction})")
    errors: list[dict] = []
    for inst in insts:
        endpoint = f"{inst.rstrip('/')}/search?q={q}&categories=general&format=json"
        try:
            data = _json_get(endpoint, timeout=10)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code in {403, 429}:
                # 같은 요청을 재시도하지 않고 사유를 결과에 남긴 뒤 다음 인스턴스로 넘어간다.
                errors.append({"url": endpoint, "title": "", "license": "", "page": "",
                               "source": "searx-site", "kind": "error", "note": f"HTTP {code}"})
            continue
        results: list[dict] = []
        for result in data.get("results", [])[: n * 3]:
            landing = result.get("url") or ""
            if not landing or not _host_allowed(landing, sites):
                continue
            is_pdf = _is_pdf_url(landing)
            image_url = result.get("img_src") or result.get("thumbnail") or ""
            candidate_url = landing if is_pdf or not image_url else image_url
            candidate = {
                "url": candidate_url,
                "title": result.get("title", ""),
                "license": result.get("license", ""),
                "page": landing,
                "source": "searx-site",
                "site": urllib.parse.urlparse(landing).hostname or "",
                "kind": "pdf" if is_pdf else ("image" if image_url else "page"),
            }
            results.append(_annotate_search_candidate(candidate))
            if len(results) >= n:
                break
        if results:
            return results + errors
    return errors


def search_images(query: str, n: int = 8,
                  sites: str | list[str] | tuple[str, ...] | None = None) -> list[dict]:
    """무료 소스와 curated 기관 직격 검색을 병합한다.

    `sites`가 주어지면 요청한 도메인 결과만 반환한다. 생략 시에는
    curated-sources.json의 기존 도메인을 먼저 조회하고 openverse·commons로 보충한다.
    """
    requested_sites = _normalize_sites(sites)
    direct_sites = requested_sites or _curated_domains()
    out, seen = [], set()

    def add(results: list[dict]) -> None:
        for result in results:
            result = _annotate_search_candidate(result)
            key = result.get("url") or f"{result.get('source')}:{result.get('note')}"
            if key not in seen:
                seen.add(key)
                out.append(result)

    try:
        add(_searx_sites(query, n, direct_sites))
    except Exception as exc:
        code = getattr(exc, "code", None)
        if code in {403, 429}:
            add([{"url": "", "title": "", "license": "", "page": "",
                  "source": "searx-site", "kind": "error", "note": f"HTTP {code}"}])

    if requested_sites:
        # `--sites`는 하드 경계다. 일반 이미지 엔진 결과를 섞어 도메인을 우회하지 않는다.
        return out[: n * 2]

    for source, fn in (("openverse", _openverse), ("commons", _commons), ("searx", _searx_images)):
        try:
            add(fn(query, n))
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code in {403, 429}:
                add([{"url": "", "title": "", "license": "", "page": "", "source": source,
                      "kind": "error", "note": f"HTTP {code}"}])
    return out[: n * 2]


# --- ④ 검증 다운로드 -----------------------------------------------------------

def download(url: str, out_dir: Path | str = "_images/web", name: str | None = None) -> dict:
    """SSRF 경계 + 매직바이트·크기 검증 통과분만 저장. 실패는 ok:false 로 정직 반환."""
    try:
        response = request_bytes(url, headers={"User-Agent": UA},
                                 max_bytes=MAX_IMG_BYTES, client=creq)
    except DownloadLimitError:
        return {"ok": False, "url": url, "note": "크기 초과"}
    status, body = response["status"], response["raw"]
    if not 200 <= status < 300:
        return {"ok": False, "url": url, "note": f"HTTP {status}"}
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
    result = {"ok": True, "file": str(path), "url": url, "source": url,
              "license": "unknown", "bytes": len(body),
              "sha256": hashlib.sha256(body).hexdigest(), "accessed_at": _now()}
    _record_download_index(out, result)
    return result


def _record_download_index(out_dir: Path, result: dict) -> None:
    """`get`으로 받은 파일의 출처 메타를 동일 디렉터리 index.json에 누적한다."""
    index_path = out_dir / "index.json"
    data: dict = {"source": "web", "at": _now(), "images": []}
    if index_path.exists():
        try:
            loaded = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError, TypeError):
            pass
    images = data.setdefault("images", [])
    if not isinstance(images, list):
        images = data["images"] = []
    images.append(result)
    data["at"] = result["accessed_at"]
    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


# --- ⑤ _images 출처 인덱스 --------------------------------------------------

def _metadata_file_candidates(raw_file: str, work_dir: Path, index_path: Path) -> list[Path]:
    path = Path(raw_file)
    if path.is_absolute():
        return [path.resolve()]
    return [(work_dir / path).resolve(), (index_path.parent / path).resolve(),
            (index_path.parent / path.name).resolve()]


def _load_image_metadata(images_dir: Path, work_dir: Path) -> dict[Path, dict]:
    metadata: dict[Path, dict] = {}
    for index_path in images_dir.rglob("index.json"):
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        records: list[dict] = []
        for key in ("figures", "images", "files", "candidates"):
            value = data.get(key)
            if isinstance(value, list):
                records.extend(item for item in value if isinstance(item, dict))
        for record in records:
            raw_file = str(record.get("file") or "").strip()
            if not raw_file:
                continue
            source = str(record.get("source") or record.get("url") or data.get("source") or "unknown")
            page = record.get("page")
            if page not in (None, "") and source != "unknown":
                source = f"{source} · p.{page}"
            item = {
                "source": source or "unknown",
                "license": str(record.get("license") or data.get("license") or "unknown"),
                "accessed_at": str(record.get("accessed_at") or record.get("at")
                                   or data.get("accessed_at") or data.get("at") or "unknown"),
            }
            for candidate in _metadata_file_candidates(raw_file, work_dir, index_path):
                if candidate.exists():
                    metadata[candidate] = item
                    break
    return metadata


def _md_cell(value: object) -> str:
    text = str(value or "unknown").strip() or "unknown"
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def write_image_index(work_dir: Path | str) -> dict:
    """`_images/**` 실제 파일과 수확 index.json을 대조해 IMAGES.md를 생성한다."""
    work = Path(work_dir).resolve()
    images_dir = work if work.name == "_images" else work / "_images"
    images_dir.mkdir(parents=True, exist_ok=True)
    metadata = _load_image_metadata(images_dir, work if work.name != "_images" else work.parent)
    image_files = sorted((path for path in images_dir.rglob("*")
                          if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES),
                         key=lambda path: path.relative_to(images_dir).as_posix().lower())
    lines = ["# IMAGES", "",
             "| 파일 | 출처(문서·p / URL) | 라이선스 판단 | accessed_at |",
             "|---|---|---|---|"]
    for path in image_files:
        item = metadata.get(path.resolve(), {})
        rel = path.relative_to(images_dir).as_posix()
        lines.append(f"| {_md_cell(rel)} | {_md_cell(item.get('source'))} | "
                     f"{_md_cell(item.get('license'))} | {_md_cell(item.get('accessed_at'))} |")
    output = images_dir / "IMAGES.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "count": len(image_files), "file": str(output)}


# --- demo (오프라인 self-check) -------------------------------------------------

def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "work"
        # 합성 PDF: 캡션+벡터 요소가 있는 큰 도판과 2페이지 반복 로고.
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 60)); pix.clear_with(90)
        big = fitz.Rect(80, 120, 480, 420)
        page.insert_image(big, pixmap=pix)
        for i in range(8):
            x0 = 105 + (i % 4) * 85
            y0 = 155 + (i // 4) * 120
            page.draw_rect(fitz.Rect(x0, y0, x0 + 55, y0 + 55), color=(1, 1, 1), width=2)
        # 데모는 helv 폰트라 ASCII 캡션 사용(한글은 실제 PDF 의 내장폰트에서 정상 추출됨)
        page.insert_text((180, 445), "[Figure] test hydrogen concept", fontsize=10)
        page.insert_image(fitz.Rect(20, 20, 50, 50), pixmap=pix)
        page.insert_text((80, 500), "body text " * 30, fontsize=9)
        page2 = doc.new_page(width=595, height=842)
        page2.insert_image(fitz.Rect(20, 20, 50, 50), pixmap=pix)
        page2.insert_text((80, 500), "second page body", fontsize=9)
        p = Path(td) / "t.pdf"; doc.save(str(p)); doc.close()

        r = pdf_figures(p, work / "_images" / "harvest", min_pt=20, min_score=-100)
        assert r["ok"] and r["count"] >= 2, r
        figure = next(item for item in r["figures"] if "Figure" in item["caption"])
        logo = min(r["figures"], key=lambda item: item["score"])
        assert r["figures"][0] is figure and figure["score"] > logo["score"], r["figures"]
        assert figure["score_signals"]["explicit_caption"], figure
        assert Path(figure["file"]).stat().st_size > 500, "크롭 파일 비정상"

        # figure/figcaption을 한 후보로 묶고, 일반 img의 alt/인접 텍스트도 보존한다.
        html = """<p>Market overview</p><figure><img src='/diagram.png' alt='hydrogen map'>
        <figcaption>Figure 2. Hydrogen value chain</figcaption></figure>
        <img src='plant.jpg' alt='Electrolyser facility'>"""
        parsed = _parse_page_images(html, "https://agency.example/release/")
        paired = next(item for item in parsed if item["kind"] == "figure")
        assert paired["url"] == "https://agency.example/diagram.png", paired
        assert paired["caption"] == "Figure 2. Hydrogen value chain", paired
        assert any(item["alt"] == "Electrolyser facility" for item in parsed), parsed
        import fetch as fetch_module
        original_fetch = fetch_module.fetch
        try:
            fetch_module.fetch = lambda _url: {
                "raw": html.encode("utf-8"), "text": "", "final_url": "https://agency.example/release/"}
            fetched = page_images("https://agency.example/release/")
        finally:
            fetch_module.fetch = original_fetch
        assert fetched["ok"] and any(item["kind"] == "figure" for item in fetched["candidates"]), fetched
        assert _normalize_sites("iea.org, energy.gov") == ["iea.org", "energy.gov"]
        assert _searx_instances() and all(url.startswith("https://") for url in _searx_instances())
        pdf_candidate = _annotate_search_candidate(
            {"url": "https://iea.org/report.pdf", "page": "", "license": "CC BY 4.0"})
        assert pdf_candidate["kind"] == "pdf" and "pdf" in pdf_candidate["hint"].lower(), pdf_candidate

        # 메타가 없는 파일은 빈칸 대신 unknown으로 명시되어야 한다.
        orphan = work / "_images" / "orphan.png"
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_bytes(Path(figure["file"]).read_bytes())
        index_result = write_image_index(work)
        index_text = Path(index_result["file"]).read_text(encoding="utf-8")
        orphan_row = next(line for line in index_text.splitlines() if "orphan.png" in line)
        assert orphan_row.count("unknown") == 3, orphan_row
        assert f"p.{figure['page']}" in index_text, index_text

        # 매직바이트 검증: png OK / html 거부 (download 의 판정부만 로컬 검증)
        assert next((e for m, e in MAGIC.items() if b"\x89PNG_test"[:12].startswith(m)), None) == ".png"
        assert next((e for m, e in MAGIC.items() if b"<html><body>"[:12].startswith(m)), None) is None
        # SSRF 경계가 물려 있는지 (내부 IP 거부)
        try:
            check_url_safe("http://127.0.0.1/x.png"); raise AssertionError("SSRF 미차단")
        except ValueError:
            pass
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
        min_score = float(args[args.index("--min-score") + 1]) if "--min-score" in args else -20.0
        r = pdf_figures(args[1], out, min_pt=mp, min_score=min_score)
        print(json.dumps({k: v for k, v in r.items() if k != "figures"}, ensure_ascii=False))
        for f in r["figures"]:
            print(f"  #{f['rank']:>2} score={f['score']:>6.2f} p{f['page']:>3} "
                  f"{Path(f['file']).name}  {f['caption'][:60]}")
    elif args[0] == "page" and len(args) >= 2:
        print(json.dumps(page_images(args[1]), ensure_ascii=False, indent=1))
    elif args[0] == "search" and len(args) >= 2:
        n = int(args[args.index("--n") + 1]) if "--n" in args else 8
        sites = args[args.index("--sites") + 1] if "--sites" in args else None
        print(json.dumps(search_images(args[1], n, sites=sites), ensure_ascii=False, indent=1))
    elif args[0] == "get" and len(args) >= 2:
        out = args[args.index("--out") + 1] if "--out" in args else "_images/web"
        name = args[args.index("--name") + 1] if "--name" in args else None
        print(json.dumps(download(args[1], out, name), ensure_ascii=False))
    elif args[0] == "index" and len(args) >= 2:
        print(json.dumps(write_image_index(args[1]), ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
