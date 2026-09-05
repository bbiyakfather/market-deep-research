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


_SUBSTR_CHARS = set(".,0123456789")   # 인접 시 부분문자열 오귀속으로 보고 버릴 문자('45%'·'2024-45'는 살림)


def _standalone_rects(page, rects: list, matched: str) -> list:
    """부분문자열 오귀속 차단(V15): rect 좌우 바로 옆 글자가 숫자/콤마/소수점이면
    '2045' 안의 '45' 처럼 더 큰 숫자의 일부이므로 버린다."""
    out = []
    for r in rects:
        cw = r.width / max(len(matched), 1)           # 문자 1개 평균 폭 추정 → 인접칸 폭
        margin = cw * 1.2
        before = page.get_textbox(fitz.Rect(r.x0 - margin, r.y0, r.x0, r.y1)).strip()
        after = page.get_textbox(fitz.Rect(r.x1, r.y0, r.x1 + margin, r.y1)).strip()
        if before[-1:] not in _SUBSTR_CHARS and after[:1] not in _SUBSTR_CHARS:
            out.append(r)
    return out


def capture_number(pdf_path: Path | str, number: str, out_png: Path | str,
                   page_hint: int | None = None, zoom: float = 2.0, pad: int = 40) -> dict:
    out_png = Path(out_png)
    if out_png.resolve() == Path(pdf_path).resolve():
        raise ValueError("캡처 출력 경로는 원본 PDF와 달라야 합니다")
    # 재시도 시작 시 이전 성공본을 무효화한다. 원본 열기/렌더 예외도 옛 PNG를 남기면 안 된다.
    out_png.unlink(missing_ok=True)
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
                raw = page.search_for(v)
                if not raw:
                    continue
                filtered = _standalone_rects(page, raw, v)
                if filtered:
                    matched, rects = v, filtered
                    break
            if not rects:
                continue
            r = rects[0]
            for rr in rects:                              # 하이라이트(필터 후 목록만 — 오귀속 방지)
                page.add_highlight_annot(rr)
            clip = fitz.Rect(max(0, r.x0 - pad), max(0, r.y0 - pad),
                             min(page.rect.width, r.x1 + pad * 4),
                             min(page.rect.height, r.y1 + pad))
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
            out_png.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(out_png))
            return {"ok": True, "type": "source_capture", "page": pno + 1,
                    "matched": matched, "rect": [r.x0, r.y0, r.x1, r.y1],
                    "path": str(out_png), "captured_at": _now()}
        # 실패(미발견 또는 부분문자열만 발견돼 강등): out_png 와 분리된 .FAILED 사이드카에
        # 첫 페이지(또는 힌트) 전체 렌더 + 상태 fail(육안 fallback). out_png 자체는 생성하지
        # 않아 대장이 이 경로를 가리켜도 증빙게이트가 파일부재로 [증빙유실] FAIL 을 낸다(V04).
        failed_png = out_png.with_name(out_png.stem + ".FAILED" + out_png.suffix)
        pno = (page_hint - 1) if page_hint else 0
        page = doc.load_page(max(0, min(pno, doc.page_count - 1)))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        failed_png.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(failed_png))
        has_text = bool(page.get_text().strip())
        return {"ok": False, "type": "source_capture",
                "reason": "숫자 미발견(표기변형/스캔PDF 의심)" if has_text else "텍스트레이어 없음(스캔PDF)",
                "page": page.number + 1, "path": str(failed_png), "captured_at": _now()}
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
        # 미발견 → ok False + .FAILED 사이드카에만 저장(out_png 자체는 생성되지 않음, V04)
        e3 = Path(td) / "e3.png"
        r3 = capture_number(pdf, "999999", e3)
        assert not r3["ok"] and ".FAILED" in r3["path"] and Path(r3["path"]).exists() and not e3.exists(), r3

        # V15: 부분문자열 오귀속 차단 — '2045' 안의 '45' 는 버리고 독립된 '45' 만 채택
        pdf2 = Path(td) / "s2.pdf"
        doc2 = fitz.open()
        p2 = doc2.new_page()
        p2.insert_text((72, 100), "Year 2045 projection")
        p2.insert_text((72, 140), "target value 45 units")
        doc2.save(str(pdf2)); doc2.close()
        r4 = capture_number(pdf2, "45", Path(td) / "e4.png")
        assert r4["ok"] and r4["rect"][1] > 120, r4    # 오귀속 되살아나면 y≈88 의 2045 rect 가 잡힘

        # V15: 유효 rect 가 0개(전부 부분문자열)면 실패 경로로 강등
        pdf3 = Path(td) / "s3.pdf"
        doc3 = fitz.open()
        doc3.new_page().insert_text((72, 100), "Market 2,450 MW")
        doc3.save(str(pdf3)); doc3.close()
        r5 = capture_number(pdf3, "45", Path(td) / "e5.png")
        assert not r5["ok"] and ".FAILED" in r5["path"], r5
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
        result = capture_number(args[0], args[1], args[2], pg)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if result["ok"] else 1)
    else:
        print(__doc__); sys.exit(2)
