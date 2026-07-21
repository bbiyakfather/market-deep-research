"""preview_pdf.py — report.pdf → 페이지별 PNG (팀리드 육안검증용).

fitz(PyMuPDF)로 지정 페이지를 래스터화해 _preview/ 에 PNG로 떨군다.
Read 도구로 팀리드가 렌더 결과를 눈으로 확인하는 용도.

CLI:
    python preview_pdf.py --pdf report.pdf [--pages 1-3,5] [--dpi 110] [--out _preview/]
    python preview_pdf.py --selfcheck
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_paths  # noqa: E402,F401  (import 시 UTF-8 콘솔 부트스트랩 1회)


def parse_pages(spec, n_pages: int) -> list[int]:
    """'1-3,5' → [1,2,3,5] (1-based). 빈 spec은 전체. 범위 밖 페이지는 버린다."""
    if not spec:
        return list(range(1, n_pages + 1))
    out: list[int] = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted({p for p in out if 1 <= p <= n_pages})


def render_previews(pdf_path, pages=None, dpi: int = 110, out_dir=None) -> list[Path]:
    """PDF 페이지 → PNG 목록. 반환: 생성된 PNG 경로들(정렬)."""
    import fitz  # PyMuPDF

    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"입력 PDF 없음: {pdf_path}")
    out_dir = Path(out_dir).resolve() if out_dir else pdf_path.parent / "_preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)  # 72dpi 기준 확대율
    doc = fitz.open(str(pdf_path))
    try:
        written: list[Path] = []
        for pno in parse_pages(pages, doc.page_count):
            pix = doc.load_page(pno - 1).get_pixmap(matrix=mat)
            out = out_dir / f"{pdf_path.stem}_p{pno:03d}.png"
            pix.save(str(out))
            written.append(out)
        return written
    finally:
        doc.close()


def _selfcheck() -> int:
    # parse_pages: 범위·중복·경계 클램프·전체 기본
    assert parse_pages("1-3,5", 10) == [1, 2, 3, 5], parse_pages("1-3,5", 10)
    assert parse_pages("", 3) == [1, 2, 3], parse_pages("", 3)
    assert parse_pages(None, 2) == [1, 2], parse_pages(None, 2)
    assert parse_pages("2-2,2", 5) == [2], parse_pages("2-2,2", 5)   # 중복 제거
    assert parse_pages("4-99", 5) == [4, 5], parse_pages("4-99", 5)  # 상한 클램프
    assert parse_pages("0,3", 5) == [3], parse_pages("0,3", 5)       # 하한 클램프
    print("SELFCHECK OK")
    return 0


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="preview_pdf", description="PDF → 페이지별 PNG")
    p.add_argument("--pdf", help="입력 PDF")
    p.add_argument("--pages", help="페이지 범위 '1-3,5' (기본: 전체)")
    p.add_argument("--dpi", type=int, default=110, help="래스터 해상도 (기본 110)")
    p.add_argument("--out", help="출력 폴더 (기본: <pdf>와 같은 폴더의 _preview/)")
    p.add_argument("--selfcheck", action="store_true", help="내부 자기검증")
    args = p.parse_args(argv)

    if args.selfcheck:
        return _selfcheck()
    if not args.pdf:
        p.error("--pdf 필요")
    try:
        pngs = render_previews(args.pdf, pages=args.pages, dpi=args.dpi, out_dir=args.out)
    except FileNotFoundError as e:
        print(f"프리뷰 실패: {e}", file=sys.stderr)
        return 2
    print(f"PNG {len(pngs)}개 생성:")
    for p_ in pngs:
        print(f"  {p_}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
