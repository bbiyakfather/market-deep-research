"""HWPX 에서 뽑아 낸 PDF 를 PyMuPDF 로 네 지표 채점한다.

정적 XML 검사는 크롭·세로쏟아짐·쪽 밀림을 못 잡는다. 한글로 출력한 PDF 에서
그림 종횡비, 낱말 잘림, 표 쪽걸침, 여백 낭비를 센다. 의심 쪽만 90dpi PNG 로 남긴다.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

import fitz
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# HWPUNIT → pt (1pt = 100 HWPUNIT). 3.5cm ≈ 99.21pt.
HWP_TO_PT = 100.0
GAP_LIMIT_PT = 3.5 * 72 / 2.54  # 3.5cm
LINE_DY = 1.5
DEFAULT_PROFILE = {
    "page": {"body_w": 48188, "body_h": 70012, "tbl_w": 48178},
    "table": {"in_margin": 1020, "col_unit": 500},
}
# 내비온 양식 실측 — 프로필에 여백이 없을 때 본문 하단 y 계산용
_MARGIN_BOTTOM = 4252
_FOOTER = 2835

_IMG_MD_RE = re.compile(r"!\[.*?\]\((.+?)\)")


def _build_hwpx():
    """build_hwpx 는 다른 워커가 만든다. 없으면 낱말 잘림만 건너뛴다."""
    scripts = str(Path(__file__).resolve().parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        import build_hwpx as bh  # type: ignore
        return bh
    except Exception:
        return None


def load_profile(name_or_path: str = "navion-2026") -> dict:
    """프로필 JSON. build_hwpx.load_profile 이 있으면 그걸 쓰고, 없으면 옆 폴더 파일을 연다."""
    bh = _build_hwpx()
    if bh is not None and hasattr(bh, "load_profile"):
        try:
            return bh.load_profile(name_or_path)
        except Exception:
            pass
    p = Path(name_or_path)
    if not p.exists():
        p = Path(__file__).resolve().parent.parent / "profiles" / f"{name_or_path}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return DEFAULT_PROFILE


def _body_metrics(profile: dict, page: fitz.Page) -> tuple[float, float]:
    """본문 폭(pt), 본문 하단 y(pt, PyMuPDF 는 아래로 증가)."""
    page_info = profile.get("page") or {}
    body_w = float(page_info.get("body_w") or DEFAULT_PROFILE["page"]["body_w"]) / HWP_TO_PT
    body_bottom = page.rect.height - (_FOOTER + _MARGIN_BOTTOM) / HWP_TO_PT
    return body_w, body_bottom


def _md_images(md_path: Path) -> list[Path]:
    text = md_path.read_text(encoding="utf-8")
    out: list[Path] = []
    for rel in _IMG_MD_RE.findall(text):
        out.append((md_path.parent / rel).resolve())
    return out


def _pdf_images(doc: fitz.Document) -> list[tuple[int, int, int]]:
    """문서 순서대로 (xref, w, h).

    page.get_images() 는 PNG 알파의 SMask 를 별도 항목으로 돌려준다
    (예: xref 37 smask 0 + xref 38 smask 37). 다른 항목의 smask 로 쓰이는
    xref 는 같은 그림이므로 세지 않는다.
    """
    raw: list[tuple[int, int, int, int]] = []
    smask_xrefs: set[int] = set()
    for page in doc:
        for img in page.get_images():
            xref, smask, w, h = img[0], img[1], img[2], img[3]
            raw.append((int(xref), int(smask), int(w), int(h)))
            if smask:
                smask_xrefs.add(int(smask))
    return [(xref, w, h) for xref, smask, w, h in raw if xref not in smask_xrefs]


def _aspect_defects(doc: fitz.Document, md_path: Path | None) -> tuple[list[dict], int]:
    pdf_imgs = _pdf_images(doc)
    n_pdf = len(pdf_imgs)
    if md_path is None:
        return [], n_pdf
    md_imgs = _md_images(md_path)
    defects: list[dict] = []
    if len(md_imgs) != n_pdf:
        defects.append({
            "kind": "count_mismatch",
            "md": len(md_imgs),
            "pdf": n_pdf,
        })
    n = min(len(md_imgs), n_pdf)
    for i in range(n):
        path = md_imgs[i]
        _xref, pw, ph = pdf_imgs[i]
        if not path.exists() or ph == 0:
            defects.append({"kind": "missing_or_zero", "i": i, "path": str(path),
                            "pdf": [pw, ph]})
            continue
        with Image.open(path) as im:
            ow, oh = im.size
        if oh == 0 or ph == 0:
            continue
        orig = ow / oh
        got = pw / ph
        err = abs(got - orig) / orig if orig else 1.0
        if err > 0.02:
            defects.append({
                "kind": "aspect",
                "i": i,
                "path": str(path),
                "orig": [ow, oh],
                "pdf": [pw, ph],
                "err": round(err, 4),
            })
    return defects, n_pdf


def _word_cut_defects(md_path: Path | None, profile: dict) -> tuple[list[dict] | str, int]:
    """표 셀에서 최장 낱말이 열폭−안여백을 넘으면 결함. build_hwpx 없으면 skipped."""
    if md_path is None:
        return [], 0
    bh = _build_hwpx()
    if bh is None or not hasattr(bh, "col_widths") or not hasattr(bh, "_disp_len"):
        return "skipped", 0
    if hasattr(bh, "load_profile"):
        try:
            bh.load_profile(profile.get("name") or "navion-2026")
        except Exception:
            pass
    table_cfg = profile.get("table") or {}
    in_margin = int(table_cfg.get("in_margin") or 1020)
    col_unit = int(table_cfg.get("col_unit") or 500)
    text = md_path.read_text(encoding="utf-8")
    if hasattr(bh, "parse_md"):
        blocks = bh.parse_md(text)
        tables = [b for b in blocks if b.get("t") == "table"]
    else:
        return "skipped", 0
    defects: list[dict] = []
    for ti, b in enumerate(tables):
        rows = b.get("rows") or []
        if not rows:
            continue
        ncol = max(len(r) for r in rows)
        rows = [r + [""] * (ncol - len(r)) for r in rows]
        widths = bh.col_widths(rows, ncol)
        for ri, row in enumerate(rows):
            for ci, txt in enumerate(row):
                words = txt.split() or [txt]
                longest = max(bh._disp_len(w) for w in words)
                need = longest * col_unit
                avail = widths[ci] - in_margin
                if need > avail:
                    defects.append({
                        "table": ti,
                        "row": ri,
                        "col": ci,
                        "word": max(words, key=bh._disp_len),
                        "need": need,
                        "avail": avail,
                    })
    return defects, len(defects)


def _long_h_lines(page: fitz.Page, min_width: float) -> int:
    n = 0
    for d in page.get_drawings():
        for it in d.get("items") or []:
            op = it[0]
            if op == "l" and len(it) >= 3:
                p1, p2 = it[1], it[2]
                dx, dy = abs(p2.x - p1.x), abs(p2.y - p1.y)
                if dy <= LINE_DY and dx >= min_width:
                    n += 1
            elif op == "re" and len(it) >= 2:
                r = it[1]
                if r.width >= min_width and r.height <= 3:
                    n += 1
    return n


def _last_content_bottom(page: fitz.Page) -> float:
    blocks = page.get_text("dict").get("blocks") or []
    bottoms = [b["bbox"][3] for b in blocks if b.get("bbox")]
    return max(bottoms) if bottoms else 0.0


def _spill_and_gap(doc: fitz.Document, profile: dict) -> tuple[list[dict], list[dict]]:
    spills: list[dict] = []
    gaps: list[dict] = []
    n_pages = doc.page_count
    for i, page in enumerate(doc):
        body_w, body_bottom = _body_metrics(profile, page)
        min_w = body_w * 0.80
        n_lines = _long_h_lines(page, min_w)
        text = page.get_text()
        has_caption = "<표>" in text
        if (not has_caption) and n_lines >= 3:
            spills.append({
                "page": i + 1,
                "lines": n_lines,
                "note": "표가 앞 쪽에서 넘어옴",
            })
        if i == n_pages - 1:
            continue
        last = _last_content_bottom(page)
        gap = body_bottom - last
        if gap > GAP_LIMIT_PT:
            gaps.append({
                "page": i + 1,
                "gap_pt": round(gap, 1),
                "last": round(last, 1),
                "body_bottom": round(body_bottom, 1),
            })
    return spills, gaps


def _summary(pages: int, images: int, defects: dict, suspect: list[int]) -> dict:
    return {
        "pages": pages,
        "images": images,
        "defects": defects,
        "suspect_pages": suspect,
    }


def grade(pdf, md=None, profile: str = "navion-2026") -> dict:
    """PDF 를 네 지표로 채점한다. md 가 없으면 종횡비·낱말 잘림은 건너뛴다."""
    pdf_path = Path(pdf).resolve()
    md_path = Path(md).resolve() if md else None
    prof = load_profile(profile)
    doc = fitz.open(pdf_path)
    try:
        aspect, n_images = _aspect_defects(doc, md_path)
        word_cut, n_cut = _word_cut_defects(md_path, prof)
        spills, gaps = _spill_and_gap(doc, prof)
        n_pages = doc.page_count
        if word_cut == "skipped":
            n_cut = 0
        defects = {
            "aspect": len(aspect),
            "word_cut": n_cut,
            "table_spill": len(spills),
            "gap": len(gaps),
        }
        suspect = sorted({
            *[d.get("page") for d in spills if d.get("page")],
            *[d.get("page") for d in gaps if d.get("page")],
        })
        # 그림 결함은 쪽 번호가 없을 수 있어, 이미지가 있는 쪽을 의심 쪽에 넣지 않는다
        # (종횡비는 원본 대조이지 쪽 레이아웃 결함이 아님). 캡션 없는 쪽걸침·여백만.
        result = _summary(n_pages, n_images, defects, suspect)
        result["details"] = {
            "aspect": aspect,
            "word_cut": word_cut,
            "table_spill": spills,
            "gap": gaps,
        }
        result["pdf"] = str(pdf_path)
        if md_path:
            result["md"] = str(md_path)
        return result
    finally:
        doc.close()


def _render_suspects(pdf, suspect: list[int], render_dir: Path) -> list[str]:
    render_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    written: list[str] = []
    try:
        for n in suspect:
            if n < 1 or n > doc.page_count:
                continue
            pix = doc[n - 1].get_pixmap(dpi=90)
            dest = render_dir / f"page-{n:03d}.png"
            pix.save(str(dest))
            written.append(str(dest))
    finally:
        doc.close()
    return written


def demo() -> None:
    """2쪽짜리 PDF 로 gap/spill 을 보고, RGBA PNG 1장은 SMask 를 빼면 images==1 인지 본다."""
    import io

    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((72, 80), "demo page 1 no caption")
    sh = p1.new_shape()
    for y in (200, 220, 240):
        sh.draw_line(fitz.Point(50, y), fitz.Point(480, y))
    sh.finish(color=(0, 0, 0), width=0.6)
    sh.commit()
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((72, 80), "demo page 2 last")
    p2.insert_text((72, 700), "near bottom")
    buf = io.BytesIO()
    Image.new("RGBA", (40, 30), (10, 200, 50, 180)).save(buf, format="PNG")
    p2.insert_image(fitz.Rect(72, 400, 172, 475), stream=buf.getvalue())
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp = Path(f.name)
    doc.save(str(tmp))
    doc.close()
    try:
        r = grade(tmp, md=None)
        assert r["pages"] == 2, r
        assert r["defects"]["table_spill"] >= 1, r
        assert r["defects"]["gap"] >= 1, r
        assert 1 in r["suspect_pages"], r
        assert 2 not in r["suspect_pages"], r  # 마지막 쪽은 여백 낭비 제외, 선도 없음
        assert r["images"] == 1, r  # SMask xref 는 같은 RGBA 그림이라 세지 않는다
        raw_n = 0
        d2 = fitz.open(tmp)
        try:
            for page in d2:
                raw_n += len(page.get_images())
        finally:
            d2.close()
        assert raw_n >= 1
    finally:
        tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--demo" in args:
        demo()
        print("demo ok")
        return 0
    if not args:
        print("usage: grade_pdf.py <pdf> [--md <원고.md>] [--profile navion-2026] "
              "[--out grade.json] [--render <dir>]", file=sys.stderr)
        return 1
    pdf = args[0]
    md = None
    profile = "navion-2026"
    out = None
    render = None
    i = 1
    while i < len(args):
        if args[i] == "--md" and i + 1 < len(args):
            md = args[i + 1]
            i += 2
        elif args[i] == "--profile" and i + 1 < len(args):
            profile = args[i + 1]
            i += 2
        elif args[i] == "--out" and i + 1 < len(args):
            out = args[i + 1]
            i += 2
        elif args[i] == "--render" and i + 1 < len(args):
            render = args[i + 1]
            i += 2
        else:
            print(f"unknown arg: {args[i]}", file=sys.stderr)
            return 1
    try:
        result = grade(pdf, md=md, profile=profile)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1
    rendered: list[str] = []
    if render:
        rendered = _render_suspects(pdf, result["suspect_pages"], Path(render))
        result["render"] = rendered
    summary = _summary(
        result["pages"], result["images"], result["defects"], result["suspect_pages"],
    )
    if out:
        Path(out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
