"""capture_web.py — reconstructed_excerpt(재구성 발췌, 증빙 **불인정**) 생성기.

차단·유실된 원문을 fitz `insert_htmlbox`로 재현한 그림을 만든다. evidence-capture.md
§1의 규범: **원본이 아니므로 증빙이 될 수 없다** — 내부 audit 전용이며 고객 보고서·
증빙표에 싣지 않는다. 그래서 두 가지를 강제한다:
  1) 시각 워터마크("재구성 발췌 — 증빙 아님", 반투명 대각선)를 이미지에 새긴다.
  2) 메타 JSON에 kind="reconstructed_excerpt", not_evidence=true를 못박는다.
그리고 출력은 `_reconstructed/`에만 쓴다 — `_captures/`(증빙 인정 폴더) 경로는 거부.

CLI:
    capture_web.py --text <파일|문자열> --evidence E012 [--out _reconstructed/] [--source-url URL]
    capture_web.py --selfcheck

한글 렌더는 Malgun Gothic을 아카이브 폰트로 등록해 보장한다(Windows 전용 스킬).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_paths  # noqa: E402,F401  (import 시 UTF-8 콘솔 부트스트랩 1회)

import argparse  # noqa: E402
import html as _html  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import fitz  # noqa: E402  (PyMuPDF; insert_htmlbox·TextWriter)


MALGUN = r"C:\Windows\Fonts\malgun.ttf"
WATERMARK = "재구성 발췌 — 증빙 아님"
_ID_RE = re.compile(r"[A-Za-z0-9_-]+")

_CSS = (
    "@font-face{font-family:mg;src:url(malgun.ttf);} "
    "*{font-family:mg;} "
    "body{font-size:15px;line-height:1.6;color:#111;} "
    "h4{margin:0 0 10px;color:#555;font-size:12px;font-weight:normal;} "
    "div.body{white-space:pre-wrap;}"
)


def _safe_id(evidence: str) -> str:
    if not evidence or not _ID_RE.fullmatch(evidence):
        raise ValueError(f"evidence ID는 [A-Za-z0-9_-]만 허용: {evidence!r}")
    return evidence


def _forbid_captures(out_dir) -> None:
    """재구성물은 증빙 인정 폴더(_captures/)에 절대 쓰지 않는다(경로 강제)."""
    parts = [p.lower() for p in Path(out_dir).parts]
    if "_captures" in parts:
        raise ValueError("capture_web은 _captures/에 쓸 수 없다(재구성물은 증빙 불인정)")


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _build_html(text: str, source_url: str | None) -> str:
    """원문 텍스트를 안전하게 escape해 재현용 HTML로 감싼다(원문은 신뢰하지 않음)."""
    label = "재구성 발췌(증빙 아님)"
    if source_url:
        label += " · 원출처: " + _html.escape(source_url)
    body = _html.escape(text or "")
    return f"<h4>{label}</h4><div class='body'>{body}</div>"


def _watermark(page, font_path: str, top: float, bottom: float, width: float) -> None:
    """반투명 붉은 대각선 워터마크를 crop 영역 중앙을 가로지르게 반복 배치.

    회전 전 좌표에서 pivot(crop 중앙)을 지나는 수평 평행선들에 텍스트를 깔면,
    pivot 중심 회전 후 그 선들이 crop 중앙을 지나는 대각선이 된다 — 콘텐츠가
    짧아도 워터마크가 본문 위에 확실히 겹쳐 보인다.
    """
    font = fitz.Font(fontfile=font_path)
    tw = fitz.TextWriter(page.rect, opacity=0.18, color=(0.82, 0, 0))
    cx, cy = width / 2, (top + bottom) / 2
    text = WATERMARK + "    " + WATERMARK      # 가로로 충분히 길게(대각선 폭 확보)
    lines = max(1, int((bottom - top) // 130))  # crop 높이에 따라 줄 수 적응
    for k in range(-(lines // 2), lines - lines // 2):
        tw.append(fitz.Point(-width * 0.1, cy + k * 130), text, font=font, fontsize=22)
    tw.write_text(page, morph=(fitz.Point(cx, cy), fitz.Matrix(30)))  # 30° 대각선


def reconstruct(text: str, evidence: str, out_dir="_reconstructed",
                source_url: str | None = None, width: float = 720,
                font_path: str = MALGUN, zoom: float = 2.0) -> dict:
    """재구성 발췌 PNG + 메타 생성. _captures/ 경로는 거부."""
    _safe_id(evidence)
    _forbid_captures(out_dir)
    if not Path(font_path).is_file():
        raise FileNotFoundError(f"한글 폰트 없음(Malgun Gothic 필요): {font_path}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    H = 1600
    margin = 36
    doc = fitz.open()
    page = doc.new_page(width=width, height=H)
    arch = fitz.Archive()
    arch.add(font_path, "malgun.ttf")  # @font-face url(malgun.ttf) 참조원
    rect = fitz.Rect(margin, margin, width - margin, H - margin)
    spare, _scale = page.insert_htmlbox(rect, _build_html(text, source_url),
                                        css=_CSS, archive=arch)
    used_h = H - max(spare, 0)               # 콘텐츠 하단 + 하단여백
    used_h = min(max(used_h, 160), H)
    _watermark(page, font_path, 0, used_h, width)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                          clip=fitz.Rect(0, 0, width, used_h))
    png = out / f"{evidence}.png"
    pix.save(png)
    doc.close()

    meta = {
        "kind": "reconstructed_excerpt", "not_evidence": True,
        "status": "reconstructed", "evidence": evidence, "source_url": source_url,
        "reconstructed_png": str(png.resolve()), "watermark": WATERMARK,
        "note": ("원문 재현물 — 증빙 불인정. 고객 보고서·증빙표 사용 금지"
                 "(내부 audit 전용). 원본 캡처는 capture_pdf.py/실화면 스크린샷으로."),
        "created_at": _now(),
    }
    (out / f"{evidence}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def _resolve_text(val: str) -> str:
    """--text 값이 존재하는 파일이면 내용을, 아니면 문자열 그대로."""
    try:
        p = Path(val)
        if p.is_file():
            return p.read_text(encoding="utf-8")
    except OSError:
        pass
    return val


# ── selfcheck ────────────────────────────────────────────────────────────
def _reddish_and_nonwhite(png_path):
    """PNG를 다시 열어 (붉은 워터마크 픽셀 수, non-white 픽셀 수) 반환."""
    pix = fitz.Pixmap(str(png_path))
    data, step = pix.samples, pix.n
    red = nonwhite = 0
    for i in range(0, len(data), step):
        r, g, b = data[i], data[i + 1], data[i + 2]
        if r > g + 15 and r > b + 15:
            red += 1
        if not (r > 245 and g > 245 and b > 245):
            nonwhite += 1
    return red, nonwhite


def _selfcheck() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out = td / "_reconstructed"

        # ⑤ 재구성 발췌: _reconstructed/에만 생성, 메타 not_evidence=true
        m = reconstruct("차단된 원문입니다.\n매출 300,900 백만원(추정).",
                        "E012", out_dir=out, source_url="https://example.com/blocked")
        assert m["kind"] == "reconstructed_excerpt", m
        assert m["not_evidence"] is True, m
        assert (out / "E012.png").is_file(), "E012.png 없음"
        assert (out / "E012.json").is_file(), "E012.json 없음"
        # _captures/ 폴더는 만들어지지 않아야 한다
        assert not (td / "_captures").exists(), "_captures/에 생성됨(경로 금지 위반)"

        # 워터마크(붉은 픽셀) + 한글(non-white) 렌더 확인
        red, nonwhite = _reddish_and_nonwhite(out / "E012.png")
        assert red > 50, f"워터마크 붉은 픽셀 부족: {red}"
        assert nonwhite > 500, f"본문 렌더 픽셀 부족(한글 미표시?): {nonwhite}"

        # _captures 경로 강제 거부(폴더 경로에 _captures 포함 시 ValueError)
        try:
            reconstruct("x", "E013", out_dir=td / "work" / "_captures")
        except ValueError:
            pass
        else:
            raise AssertionError("_captures 경로 허용됨(금지 위반)")

    print("SELFCHECK OK")
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="capture_web", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--text", help="재현할 원문(파일 경로 또는 문자열)")
    p.add_argument("--evidence", help="evidence ID(파일명이 됨, 예: E012)")
    p.add_argument("--out", default="_reconstructed", help="저장 폴더(기본 _reconstructed/)")
    p.add_argument("--source-url", default=None, help="원출처 URL(메타/라벨 표기용)")
    p.add_argument("--selfcheck", action="store_true", help="내부 자기검증")
    args = p.parse_args(argv)

    if args.selfcheck:
        return _selfcheck()
    if not (args.text and args.evidence):
        p.error("--text, --evidence가 필요합니다 (또는 --selfcheck)")

    try:
        meta = reconstruct(_resolve_text(args.text), args.evidence,
                           out_dir=args.out, source_url=args.source_url)
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(json.dumps({"status": "error", "reason": str(e)}, ensure_ascii=False))
        return 2

    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
