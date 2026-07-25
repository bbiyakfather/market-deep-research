"""capture_pdf.py — PDF 정확숫자 하이라이트+크롭 → source_capture (plan-v2 핵심설계4).

로컬/다운로드 PDF 에서 대상 숫자를 검색해 하이라이트하고 주변을 크롭한 PNG 를 만든다.
파일명 = evidence ID. 정확 숫자 검색(부분문자열 금지 지향) — 표기변형(쉼표·공백)은 변형 재시도.
스캔PDF(텍스트레이어 없음)·표기변형 실패 시 페이지 전체 렌더 + 실패상태(육안 fallback).

CLI: python capture_pdf.py demo
     python capture_pdf.py <pdf> <number> <out.png> [--page N]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _variants(number: str) -> list[str]:
    n = number.strip()
    out = [n]
    if "," in n:
        out.append(n.replace(",", ""))
    else:  # 천단위 콤마 삽입 변형(정수부)
        try:
            if n.replace(".", "").isdigit() and "." not in n and len(n) > 3:
                out.append(f"{int(n):,}")
        except ValueError:
            pass
    out.append(n.replace(" ", ""))
    seen, uniq = set(), []
    for v in out:
        if v not in seen:
            seen.add(v); uniq.append(v)
    return uniq


def capture_number(pdf_path: Path | str, number: str, out_png: Path | str,
                   page_hint: int | None = None, zoom: float = 2.0, pad: int = 40) -> dict:
    doc = fitz.open(str(pdf_path))
    try:
        pages = [page_hint - 1] if page_hint else range(doc.page_count)
        for pno in pages:
            if pno < 0 or pno >= doc.page_count:
                continue
            page = doc.load_page(pno)
            rects = []
            matched = None
            for v in _variants(number):
                rects = page.search_for(v)
                if rects:
                    matched = v; break
            if not rects:
                continue
            r = rects[0]
            for rr in rects:                              # 하이라이트(여러 등장 표시)
                page.add_highlight_annot(rr)
            clip = fitz.Rect(max(0, r.x0 - pad), max(0, r.y0 - pad),
                             min(page.rect.width, r.x1 + pad * 4),
                             min(page.rect.height, r.y1 + pad))
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
            Path(out_png).parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(out_png))
            return {"ok": True, "type": "source_capture", "page": pno + 1,
                    "matched": matched, "rect": [r.x0, r.y0, r.x1, r.y1],
                    "path": str(out_png), "captured_at": _now()}
        # 실패: 첫 페이지(또는 힌트) 전체 렌더 + 상태 fail(육안 fallback)
        pno = (page_hint - 1) if page_hint else 0
        page = doc.load_page(max(0, min(pno, doc.page_count - 1)))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        Path(out_png).parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_png))
        has_text = bool(page.get_text().strip())
        return {"ok": False, "type": "source_capture",
                "reason": "숫자 미발견(표기변형/스캔PDF 의심)" if has_text else "텍스트레이어 없음(스캔PDF)",
                "page": page.number + 1, "path": str(out_png), "captured_at": _now()}
    finally:
        doc.close()


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "s.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), "Revenue 2024: 300.9  (KRW trillion)")
        page.insert_text((72, 140), "Market size 1,234 USD_M")
        doc.save(str(pdf)); doc.close()

        r = capture_number(pdf, "300.9", Path(td) / "e1.png")
        assert r["ok"] and r["page"] == 1 and Path(r["path"]).stat().st_size > 0, r
        # 콤마 변형: "1234" → "1,234" 로 발견
        r2 = capture_number(pdf, "1234", Path(td) / "e2.png")
        assert r2["ok"] and r2["matched"] == "1,234", r2
        # 미발견 → ok False + 페이지 렌더
        r3 = capture_number(pdf, "999999", Path(td) / "e3.png")
        assert not r3["ok"] and Path(r3["path"]).exists(), r3
    print(f"[{_now()}] capture_pdf demo OK")


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):          # cp949 콘솔/파이프 UnicodeEncodeError 방지
        _reconf = getattr(_stream, "reconfigure", None)
        if _reconf:
            _reconf(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif len(args) >= 3:
        pg = int(args[args.index("--page") + 1]) if "--page" in args else None
        import json
        print(json.dumps(capture_number(args[0], args[1], args[2], pg), ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
