"""render_pdf.py — 고객용 report.md → report.pdf (오프라인 2단계 렌더).

1단계 pandoc: md(gfm+fenced_divs+bracketed_spans) → self-contained HTML.
  style.html을 -H(include-in-header)로 주입하고, 캡처 PNG는 --embed-resources로
  data URI 인라인 → 외부 참조 없는 자기완결 HTML.
2단계 HeadlessChrome: file:// URI(한글경로 퍼센트인코딩)를 --print-to-pdf로
  A4 PDF 출력. HTML이 self-contained라 네트워크 접근 없는 오프라인 렌더.

style.html의 factsheet 클래스는 fenced_divs(`::: {.caution}`)와
bracketed_spans(`[300조 원]{.ftag}`) 문법으로 부착되므로 두 확장이 필수다.

CLI:
    python render_pdf.py --md report.md [--style assets/style.html] [--out report.pdf]
    python render_pdf.py --selfcheck
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_paths  # noqa: E402  (import 시 UTF-8 콘솔 부트스트랩 1회)

import os  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402


# --- pandoc 탐색 (skill_paths._find_chrome 와 동일 패턴) -------------------
def _find_pandoc():
    """pandoc 실행파일: PATH → Windows 표준/ winget 설치경로 후보.

    winget 설치 직후 세션은 PATH 미반영이라 which가 실패한다 → 표준 경로 보강.
    """
    p = shutil.which("pandoc")
    if p:
        return p
    localapp = os.environ.get("LOCALAPPDATA", "")
    progfiles = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = [
        Path(progfiles) / "Pandoc" / "pandoc.exe",
        Path(localapp) / "Pandoc" / "pandoc.exe",
        Path(localapp) / "Microsoft" / "WinGet" / "Links" / "pandoc.exe",
    ]
    if localapp:  # winget Packages(버전 폴더) — 최신 우선
        pkgs = Path(localapp) / "Microsoft" / "WinGet" / "Packages"
        candidates += sorted(pkgs.glob("JohnMacFarlane.Pandoc_*/pandoc-*/pandoc.exe"),
                             reverse=True)
    for c in candidates:
        if c and Path(c).is_file():
            return str(c)
    return None


# --- 렌더 ----------------------------------------------------------------
def _default_style() -> Path:
    return skill_paths.skill_root() / "assets" / "style.html"


def render(md_path, style_path=None, out_path=None, timeout: int = 120) -> Path:
    """report.md → report.pdf. 실패 시 RuntimeError(명확한 사유)."""
    md_path = Path(md_path).resolve()
    if not md_path.is_file():
        raise FileNotFoundError(f"입력 md 없음: {md_path}")
    style_path = Path(style_path).resolve() if style_path else _default_style()
    if not style_path.is_file():
        raise FileNotFoundError(f"style.html 없음: {style_path}")
    out_path = Path(out_path).resolve() if out_path else md_path.with_suffix(".pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pandoc = _find_pandoc()
    if not pandoc:
        raise RuntimeError("pandoc 미설치: winget install JohnMacFarlane.Pandoc 후 재시도")
    chrome = skill_paths._find_chrome()
    if not chrome:
        raise RuntimeError("chrome 미설치: Google Chrome 설치 후 재시도")

    # 1단계: pandoc → self-contained HTML(임시). --resource-path 로 md 폴더의
    # 상대 이미지(_captures/*.png)를 어디서 실행하든 인라인 임베드.
    fd, tmp_html = tempfile.mkstemp(suffix=".html", prefix="render_")
    os.close(fd)
    tmp_html = Path(tmp_html)
    try:
        r = skill_paths.run(
            [pandoc, str(md_path),
             "-f", "gfm+fenced_divs+bracketed_spans",
             "-t", "html5", "--standalone", "--embed-resources",
             "--resource-path", str(md_path.parent),
             "-H", str(style_path),
             "-o", str(tmp_html)],
            capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"pandoc 실패(exit {r.returncode}):\n{r.stderr}")

        # 2단계: HeadlessChrome → PDF. 임시 user-data-dir 로 기존 Chrome 인스턴스와
        # 격리(안 그러면 print-to-pdf 가 기존 창으로 위임돼 PDF 미생성).
        with tempfile.TemporaryDirectory(prefix="chrome_profile_") as profile:
            r = skill_paths.run(
                [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                 f"--user-data-dir={profile}",
                 f"--print-to-pdf={out_path}",
                 tmp_html.as_uri()],
                capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"chrome 실패(exit {r.returncode}):\n{r.stderr}")
        if not out_path.is_file() or out_path.stat().st_size == 0:
            raise RuntimeError(f"PDF 미생성(빈 파일): {out_path}")
        return out_path
    finally:
        tmp_html.unlink(missing_ok=True)


# --- selfcheck ------------------------------------------------------------
_MINI_MD = """# 반도체 시장 팩트시트

## 시장 규모

세계 반도체 시장은 **300조 원**[300조 원]{.ftag} 규모로 성장했다 (F001).

| 사실 | 수치 | 출처 | 등급 | 증빙 |
|---|---|---|---|---|
| 시장 규모 | 300조 원 | example.com | A/B/A/A | E001.png |
| 성장률 | 12.5% | example.com | B/B/A/B | E001.png |

::: {.caution}
정의 차이: "메모리 반도체"와 "전체 반도체"의 기준이 출처마다 다르다.
:::

::: {.evidence-box}
![사업보고서 p.112 매출 행](E001.png)

캡션: 300조 원 수치의 원문 위치(손익계산서 매출 행).
:::
"""


def _selfcheck() -> int:
    import fitz  # PyMuPDF (필수 의존성)

    # 생성물은 팀리드 육안검증용 — 삭제 금지(임시 잡 폴더)
    base = os.environ.get("CLAUDE_JOB_DIR") or tempfile.gettempdir()
    sample = Path(base) / "tmp" / "n9_sample"
    sample.mkdir(parents=True, exist_ok=True)

    # (a) 증빙용 미니 PNG(fitz) — evidence-box <img> 대상
    img = sample / "E001.png"
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 240, 80), False)
    pix.set_rect(pix.irect, (220, 232, 244))
    pix.save(str(img))

    # (b) 미니 md(한글+표+숫자+ftag+caution+evidence-box). 이미지는 E001.png 고정
    md = sample / "sample.md"
    md.write_text(_MINI_MD, encoding="utf-8")

    # (c) render → PDF (파일 존재·크기>10KB)
    pdf = render(md, out_path=sample / "sample.pdf")
    size = pdf.stat().st_size
    assert pdf.is_file() and size > 10_000, f"PDF 크기 미달: {size} bytes"

    # (d) preview → PNG (페이지 수만큼)
    import preview_pdf
    doc = fitz.open(str(pdf))
    n_pages = doc.page_count
    text = "".join(doc.load_page(i).get_text() for i in range(n_pages))
    doc.close()
    pngs = preview_pdf.render_previews(pdf, out_dir=sample / "_preview")
    assert len(pngs) == n_pages, f"PNG 수 불일치: {len(pngs)} != {n_pages}쪽"
    assert all(p.is_file() and p.stat().st_size > 0 for p in pngs), "빈 PNG 존재"

    # (e) PDF 텍스트에 한글 실재(폰트 임베드·인코딩 검증):
    #     제목/본문 · 표&본문 수치 · caution 박스 내부 · evidence-box 캡션
    for needle in ("반도체 시장", "300조 원", "정의 차이", "손익계산서"):
        assert needle in text, f"PDF 텍스트에 '{needle}' 없음(폰트/인코딩 문제)"

    print(f"  PDF : {pdf} ({size:,} bytes, {n_pages}쪽)")
    print(f"  PNG : {len(pngs)}개 → {sample / '_preview'}")
    print("SELFCHECK OK")
    return 0


# --- CLI ------------------------------------------------------------------
def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="render_pdf",
                                description="report.md → report.pdf (pandoc + HeadlessChrome)")
    p.add_argument("--md", help="입력 마크다운")
    p.add_argument("--style", help="style.html (기본: assets/style.html)")
    p.add_argument("--out", help="출력 PDF (기본: <md>.pdf)")
    p.add_argument("--selfcheck", action="store_true", help="내부 자기검증")
    args = p.parse_args(argv)

    if args.selfcheck:
        return _selfcheck()
    if not args.md:
        p.error("--md 필요")
    try:
        out = render(args.md, style_path=args.style, out_path=args.out)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"렌더 실패: {e}", file=sys.stderr)
        return 2
    print(f"PDF 생성: {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
