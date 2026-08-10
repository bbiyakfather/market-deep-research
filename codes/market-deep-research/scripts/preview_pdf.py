"""preview_pdf.py — PDF 페이지 이미지화 (G4 팀리드 육안검증용).

fitz 로 각 페이지를 PNG 로 렌더한다. 팀리드가 Read 로 이미지를 열어 F태그·표·캡처·한글이
정상인지 육안 확인한다. (정적 통과가 아니라 실제 렌더 화면 대조 — chk-scope)

CLI: python preview_pdf.py <pdf> [out_dir] [--dpi 120]
     python preview_pdf.py demo
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import fitz


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def preview(pdf_path: Path | str, out_dir: Path | str | None = None, dpi: int = 120) -> list[str]:
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir) if out_dir else pdf_path.parent / "_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72.0
    doc = fitz.open(str(pdf_path))
    paths = []
    try:
        for i in range(doc.page_count):
            pix = doc.load_page(i).get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            p = out_dir / f"{pdf_path.stem}_p{i + 1:03d}.png"
            pix.save(str(p)); paths.append(str(p))
    finally:
        doc.close()
    return paths


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "d.pdf"
        doc = fitz.open(); p = doc.new_page(); p.insert_text((72, 100), "page one 300.9")
        doc.new_page().insert_text((72, 100), "page two")
        doc.save(str(pdf)); doc.close()
        imgs = preview(pdf, Path(td) / "_preview")
        assert len(imgs) == 2 and all(Path(x).stat().st_size > 0 for x in imgs), imgs
    print(f"[{_now()}] preview_pdf demo OK")


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):          # cp949 콘솔/파이프 UnicodeEncodeError 방지
        _reconf = getattr(_stream, "reconfigure", None)
        if _reconf:
            _reconf(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif len(args) >= 1:
        dpi = int(args[args.index("--dpi") + 1]) if "--dpi" in args else 120
        out = args[1] if len(args) >= 2 and not args[1].startswith("--") else None
        for p in preview(args[0], out, dpi):
            print(p)
    else:
        print(__doc__); sys.exit(2)
