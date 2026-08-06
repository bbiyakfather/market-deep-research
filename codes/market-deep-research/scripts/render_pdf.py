"""render_pdf.py — report.md → report.pdf (pandoc → HeadlessChrome, 오프라인·한글경로).

파이프라인: pandoc(gfm → 독립형 html, --embed-resources 로 캡처 이미지 data URI 내장,
style.html 을 헤더 주입) → Chrome --headless --print-to-pdf(절대경로·file:// 퍼센트인코딩).
네트워크 접근 없이 렌더(증빙 이미지는 로컬 파일).

CLI: python render_pdf.py <report.md> [out.pdf]
     python render_pdf.py demo
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from skill_paths import ASSETS
from preflight import _find_chrome

STYLE = ASSETS / "style.html"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _pandoc_html(md_path: Path, html_out: Path, resource_dir: Path) -> None:
    # title 은 문서 자체 H1 을 쓰도록 비워 둔다(하드코딩 제목이 표지에 찍히는 것 방지).
    # pandoc 은 빈 title 에 경고만 내고 정상 산출한다.
    # --fail-if-warnings: 리소스(이미지 등) 미발견 경고가 exit 0 으로 조용히 넘어가던 것을
    # 승격 — 증빙 이미지가 통째로 빠진 PDF 가 ok=True 로 반환되는 사각지대를 막는다(G6a).
    cmd = ["pandoc", str(md_path), "-f", "gfm", "-t", "html5", "--standalone",
           "--embed-resources", f"--resource-path={resource_dir}",
           f"--include-in-header={STYLE}", "--metadata", "title=",
           "--fail-if-warnings", "-o", str(html_out)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"pandoc 실패: {r.stderr.strip()}")


def _chrome_pdf(html_path: Path, pdf_out: Path) -> None:
    chrome = _find_chrome()
    if not chrome:
        raise RuntimeError("Chrome 미발견 — G0 preflight 확인")
    # 임시파일에 렌더 후 원자 교체. 예전엔 pdf_out 을 먼저 unlink 했는데, 뷰어가 연 파일은
    # Windows 에서 **삭제만 되고**(delete-pending) 같은 이름의 새 파일 생성이 거부돼 옛 PDF
    # 까지 유실됐다(2026-08-03 실측). 렌더가 실패해도 기존 산출물은 남아야 한다.
    # Chrome 은 --print-to-pdf 의 **상대경로를 자기 cwd 기준**으로 해석해 "액세스 거부"로
    # 죽는다(2026-08-03 실측). 항상 절대경로로 넘긴다.
    pdf_out = pdf_out.resolve()
    tmp_pdf = pdf_out.with_name(pdf_out.stem + ".rendering" + pdf_out.suffix)
    tmp_pdf.unlink(missing_ok=True)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", f"--print-to-pdf={tmp_pdf}",
           html_path.resolve().as_uri()]                  # file:// 퍼센트인코딩(한글경로)
    # encoding 명시: 한글 Windows(cp949) 기본 디코딩이 Chrome stderr 바이트에서 죽어
    # 에러 메시지를 못 읽던 문제 차단(errors=replace 로 렌더 실패 원인은 항상 노출).
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not tmp_pdf.exists() or tmp_pdf.stat().st_size == 0:
        raise RuntimeError(f"Chrome PDF 실패(생성 안 됨): {r.stderr[-400:]}")
    try:
        tmp_pdf.replace(pdf_out)                          # 옛 PDF 는 성공했을 때만 사라진다
    except PermissionError as e:
        raise RuntimeError(f"기존 PDF 잠김 — 뷰어 닫고 재시도: {pdf_out} "
                           f"(새 PDF 는 {tmp_pdf} 에 보존) ({e})")


def render(md_path: Path | str, pdf_out: Path | str | None = None,
           resource_dir: Path | str | None = None) -> dict:
    md_path = Path(md_path)
    pdf_out = Path(pdf_out) if pdf_out else md_path.with_suffix(".pdf")
    resource_dir = Path(resource_dir) if resource_dir else md_path.parent
    with tempfile.TemporaryDirectory() as td:
        html_out = Path(td) / "render.html"
        _pandoc_html(md_path, html_out, resource_dir)
        _chrome_pdf(html_out, pdf_out)
    return {"ok": True, "pdf": str(pdf_out), "size": pdf_out.stat().st_size, "at": _now()}


def demo() -> None:
    with tempfile.TemporaryDirectory() as td:
        md = Path(td) / "r.md"
        md.write_text("# 시장조사 보고서\n\n## Executive Summary\n\n삼성전자 2024년 매출은 "
                      "**300.9조원(F001)** 입니다.\n\n| 사실 | 수치 | 등급 |\n|---|---|---|\n"
                      "| 매출 | 300.9조원 | A |\n\n> ⚠ 주의: 예시 데이터.\n", encoding="utf-8")
        r = render(md, Path(td) / "out.pdf")
        assert r["ok"] and r["size"] > 1000, r
        # 덮어쓰기(unlink 후 재생성) 경로도 정상 — 잠기지 않은 파일은 그대로 갱신
        r_again = render(md, Path(td) / "out.pdf")
        assert r_again["ok"] and r_again["size"] > 1000, r_again
        # 한글 파일명 경로도 렌더되는지
        kd = Path(td) / "한글폴더"; kd.mkdir()
        md2 = kd / "보고서.md"; md2.write_text("# 한글\n\n내용 300조원(F001).\n", encoding="utf-8")
        r2 = render(md2)
        assert r2["ok"] and Path(r2["pdf"]).stat().st_size > 1000, r2
    print(f"[{_now()}] render_pdf demo OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif len(args) >= 1:
        out = args[1] if len(args) >= 2 else None
        import json
        print(json.dumps(render(args[0], out), ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
