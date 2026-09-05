"""render_pdf.py — report.md → report.pdf (pandoc → HeadlessChrome, 오프라인·한글경로).

파이프라인: pandoc(gfm → AST, raw HTML 이스케이프·로컬 이미지 data URI 내장 → 독립형 HTML,
style.html·CSP 헤더 주입) → Chrome --headless --print-to-pdf(절대경로·file:// 퍼센트인코딩).
네트워크 접근 없이 렌더(증빙 이미지는 로컬 파일).

CLI: python render_pdf.py <report.md> [out.pdf]
     --allow-no-sandbox: sandbox 오류일 때에만 명시적 폴백 허용(기본 비활성)
     python render_pdf.py demo
"""
from __future__ import annotations

import base64
import json
import mimetypes
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from skill_paths import ASSETS
import gates
import manifest
from skill_paths import WorkPaths
from preflight import _find_chrome

STYLE = ASSETS / "style.html"
RENDER_TIMEOUT = 180
OFFLINE_CSP = ("default-src 'none'; img-src data:; style-src 'unsafe-inline'; "
               "font-src data:; script-src 'none'; connect-src 'none'; frame-src 'none'; "
               "object-src 'none'; base-uri 'none'; form-action 'none'")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _pandoc_html(md_path: Path, html_out: Path, resource_dir: Path) -> None:
    def local_image(target: str) -> str:
        p = urlsplit(target)
        if p.scheme == "data":
            if not target.lower().startswith("data:image/"):
                raise ValueError(f"이미지 data URI만 허용: {target[:80]}")
            return target
        # UNC/프로토콜 상대 경로도 원격 리소스다. 드라이브 문자는 로컬 절대경로로 허용.
        drive_path = len(p.scheme) == 1 and len(target) > 2 and target[1] == ":"
        if p.netloc or target.startswith(("//", "\\\\")) or (p.scheme and not drive_path and p.scheme != "file"):
            raise ValueError(f"오프라인 렌더: 외부 이미지 금지: {target}")
        raw_path = unquote(p.path) if not drive_path else unquote(target)
        if p.scheme == "file" and len(raw_path) > 2 and raw_path[0] == "/" and raw_path[2] == ":":
            raw_path = raw_path[1:]
        if raw_path.startswith(("//", "\\\\")):
            raise ValueError(f"오프라인 렌더: 외부 이미지 금지: {target}")
        root = resource_dir.resolve()
        path = (root / raw_path).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"작업폴더 내부 이미지 파일 필요: {target}")
        if not path.is_file():
            raise RuntimeError(f"pandoc 리소스 사전검사: 이미지 파일 없음: {target}")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")

    class ImageCheck(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag.lower() == "img":
                for key, value in attrs:
                    if key == "src" and value:
                        local_image(value)

    # raw HTML은 제거/이스케이프되지만 이미지의 외부 참조는 명확한 오류로 알린다.
    ImageCheck().feed(md_path.read_text(encoding="utf-8"))
    try:
        parsed = subprocess.run(["pandoc", str(md_path), "-f", "gfm-raw_html", "-t", "json", "--sandbox"],
                                capture_output=True, text=True, encoding="utf-8", timeout=RENDER_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("pandoc 원고 파싱 시간 초과") from exc
    if parsed.returncode:
        raise RuntimeError(f"pandoc 파싱 실패: {parsed.stderr.strip()}")
    ast = json.loads(parsed.stdout)

    def embed(node):
        if isinstance(node, dict):
            # 일부 pandoc GFM 빌드는 -raw_html에도 RawBlock을 남긴다. AST에서 재차
            # 텍스트 노드로 바꿔 writer가 반드시 이스케이프하게 한다.
            if node.get("t") in ("RawBlock", "RawInline"):
                raw = node["c"][1]
                replacement = {"t": "Str", "c": raw}
                if node["t"] == "RawBlock":
                    replacement = {"t": "Para", "c": [replacement]}
                node.clear()
                node.update(replacement)
            if node.get("t") == "Image":
                node["c"][2][0] = local_image(node["c"][2][0])
            for value in node.values():
                embed(value)
        elif isinstance(node, list):
            for value in node:
                embed(value)

    embed(ast)  # pandoc AST이므로 참조형 이미지·괄호/공백 경로도 같은 검사를 받는다.
    header = html_out.with_suffix(".header.html")
    header.write_text(f'<meta http-equiv="Content-Security-Policy" content="{OFFLINE_CSP}">\n' +
                      STYLE.read_text(encoding="utf-8"), encoding="utf-8")
    # title 은 문서 자체 H1 을 쓰도록 비워 둔다(하드코딩 제목이 표지에 찍히는 것 방지).
    # pandoc 은 빈 title 에 경고만 내고 정상 산출한다.
    # --fail-if-warnings: 리소스(이미지 등) 미발견 경고가 exit 0 으로 조용히 넘어가던 것을
    # 승격 — 증빙 이미지가 통째로 빠진 PDF 가 ok=True 로 반환되는 사각지대를 막는다(G6a).
    # 이미지를 직접 data URI로 바꿔 pandoc의 네트워크 리소스 로더를 호출하지 않는다.
    cmd = ["pandoc", "-f", "json", "-t", "html5", "--standalone",
           f"--include-in-header={header}", "--metadata", "title=",
           "--fail-if-warnings", "-o", str(html_out)]
    try:
        r = subprocess.run(cmd, input=json.dumps(ast, ensure_ascii=False), capture_output=True,
                           text=True, encoding="utf-8", timeout=RENDER_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("pandoc HTML 변환 시간 초과") from exc
    if r.returncode != 0:
        raise RuntimeError(f"pandoc 실패: {r.stderr.strip()}")


def _chrome_pdf(html_path: Path, pdf_out: Path, *, allow_no_sandbox: bool = False) -> None:
    chrome = _find_chrome()
    if not chrome:
        raise RuntimeError("Chrome 미발견 — G0 preflight 확인")
    # 렌더 전 기존 PDF 삭제: 잠긴(뷰어가 연) 파일에 Chrome 이 덮어쓰기 실패해도 옛 파일이
    # size≠0 로 남아 '성공'으로 오검증되던 false positive 차단. 잠김이면 명시적 에러로 노출.
    try:
        pdf_out.unlink()
    except FileNotFoundError:
        pass
    except PermissionError as e:
        raise RuntimeError(f"기존 PDF 잠김 — 뷰어 닫고 재시도: {pdf_out} ({e})")
    cmd = [chrome, "--headless=new", "--disable-gpu",
           "--disable-background-networking", "--disable-component-update", "--disable-sync",
           "--no-first-run", "--no-default-browser-check", "--no-proxy-server",
           "--host-resolver-rules=MAP * ~NOTFOUND",
           "--no-pdf-header-footer", f"--print-to-pdf={pdf_out}",
           html_path.resolve().as_uri()]                  # file:// 퍼센트인코딩(한글경로)
    # encoding 명시: 한글 Windows(cp949) 기본 디코딩이 Chrome stderr 바이트에서 죽어
    # 에러 메시지를 못 읽던 문제 차단(errors=replace 로 렌더 실패 원인은 항상 노출).
    with tempfile.TemporaryDirectory(prefix="mdr-chrome-") as profile:
        cmd.insert(1, f"--user-data-dir={profile}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=RENDER_TIMEOUT)
            if r.returncode != 0 and allow_no_sandbox and "sandbox" in r.stderr.lower():
                # 정상 기본값은 sandbox ON. 실패 사유가 sandbox이고 호출자가 명시할 때만 폴백.
                pdf_out.unlink(missing_ok=True)
                r = subprocess.run([*cmd[:-1], "--no-sandbox", cmd[-1]], capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=RENDER_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            pdf_out.unlink(missing_ok=True)
            raise RuntimeError("Chrome PDF 시간 초과") from exc
    if r.returncode != 0 or not pdf_out.exists() or pdf_out.stat().st_size == 0:
        raise RuntimeError(f"Chrome PDF 실패(생성 안 됨): {r.stderr[-400:]}")


def render(md_path: Path | str, pdf_out: Path | str | None = None,
           resource_dir: Path | str | None = None, *, allow_no_sandbox: bool = False) -> dict:
    md_path = Path(md_path).resolve()
    pdf_out = Path(pdf_out).resolve() if pdf_out else md_path.with_suffix(".pdf")
    resource_dir = Path(resource_dir) if resource_dir else md_path.parent
    with tempfile.TemporaryDirectory() as td:
        html_out = Path(td) / "render.html"
        _pandoc_html(md_path, html_out, resource_dir)
        if allow_no_sandbox:
            _chrome_pdf(html_out, pdf_out, allow_no_sandbox=True)
        else:
            _chrome_pdf(html_out, pdf_out)
    # artifacts: 봉인([4b] extend) 대상 목록 — 양식 모듈 공통 반환 계약(hwpx 등도 같은 키로 돌려준다)
    return {"ok": True, "pdf": str(pdf_out), "size": pdf_out.stat().st_size, "at": _now(),
            "artifacts": [str(pdf_out)], "publication_state": "초안"}


def render_and_record(work: WorkPaths | Path | str,
                      pdf_out: Path | str | None = None, *, allow_no_sandbox: bool = False) -> dict:
    """G3 정규 원고를 실제 렌더하고 그 반환 산출물만 확장·[4b] 기록한다."""
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    # 선행 G3 거부는 렌더 실행 전이므로 기존처럼 [4b] 실행 이력을 만들지 않는다.
    g3 = gates.require_receipt(wp, "G3")
    baseline = g3.get("manifest_sha256")
    if not baseline:
        raise gates.GateError("G3 기준선 manifest_sha256 없음 — verify_facts.py 재실행")
    try:
        if gates.sha256_file(wp.manifest) != baseline:
            raise gates.GateError("manifest.json 이 G3 영수증의 기준선과 다름 — G3 복귀")
        rendered = (render(wp.report_md, pdf_out, allow_no_sandbox=True) if allow_no_sandbox
                    else render(wp.report_md, pdf_out))
        if not rendered["ok"] or not rendered.get("artifacts"):
            raise gates.GateError("렌더 성공 산출물 없음")
        sealed = manifest.extend(wp, rendered["artifacts"], expected_sha256=baseline)
        diff = manifest._diff(wp, sealed["entries"])
        if diff["changed"] or diff["missing"] or diff["new"]:
            raise gates.GateError(f"[4b] 봉인 파일 불일치: {diff}")
        result = {"render": rendered, "manifest_entries": len(sealed["entries"])}
        receipt = gates._record_script_result(
            wp, "[4b]", 0, json.dumps(result, ensure_ascii=False, sort_keys=True), extra={
                "manifest_sha256": gates.sha256_file(wp.manifest),
                "g3_receipt_id": gates._receipt_id(g3),
                "g3_result_summary_sha256": g3.get("result_summary_sha256"),
                "artifacts": [{"path": rel, "sha256": gates.sha256_file(wp.root / rel)}
                              for rel in sealed["extended"][-1]["added"]]})
    except (gates.GateError, OSError, RuntimeError, ValueError) as exc:
        gates.record_script_result(wp, "[4b]", 1, str(exc))
        raise
    return {**result, "receipt": receipt}


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
    allow_no_sandbox = "--allow-no-sandbox" in args
    args = [a for a in args if a != "--allow-no-sandbox"]
    if not args or args[0] == "demo":
        demo()
    elif len(args) >= 1:
        md_path = Path(args[0])
        out = args[1] if len(args) >= 2 else None
        wp = WorkPaths(md_path.parent)
        if md_path.resolve() != wp.report_md.resolve():
            print(f"[render] 렌더 원고 경로 불일치: G3가 봉인한 report.md만 렌더할 수 있습니다: {wp.report_md}",
                  file=sys.stderr)
            sys.exit(1)
        try:
            result = render_and_record(wp, out, allow_no_sandbox=allow_no_sandbox)
        except (gates.GateError, OSError, RuntimeError, ValueError) as exc:
            print(f"[render] 실패: {exc}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
