"""capture_web.py — 재구성 발췌 렌더 → reconstructed_excerpt (내부용, 증빙 불인정).

★중요: 이 산출물은 연구자가 재구성한 발췌물이다. 원문 실화면이 아니므로 3중 증빙의
'출처 스크린샷(source_capture)'으로 인정하지 않는다. `_reconstructed/` 에만 저장하고,
고객 PDF 증빙에는 쓰지 않는다(원본 캡처 불가 시 대체출처 or '미확인' 유지).
실화면 캡처는 접근가능 웹=playwright(MCP 직접) / 로컬PDF=capture_pdf.py.

CLI: python capture_web.py demo
"""
from __future__ import annotations

import html as _html
import sys
from datetime import datetime
from pathlib import Path

import fitz


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def reconstruct_excerpt(text: str, source_url: str, out_png: Path | str,
                        width: int = 720, zoom: float = 2.0) -> dict:
    safe = _html.escape(text)
    doc_html = (
        '<div style="font-family:Malgun Gothic,sans-serif;font-size:13px;padding:14px;">'
        '<div style="color:#b00;font-size:11px;border:1px solid #b00;padding:2px 6px;'
        'display:inline-block;margin-bottom:8px;">내부 재구성 발췌 · 증빙 불인정</div>'
        f'<div style="white-space:pre-wrap;line-height:1.5;">{safe}</div>'
        f'<div style="color:#888;font-size:10px;margin-top:10px;">재구성: {_now()} · '
        f'출처(주장): {_html.escape(source_url)}</div></div>')
    doc = fitz.open()
    page = doc.new_page(width=width / 2, height=1)          # 높이는 자동확장
    rect = fitz.Rect(0, 0, width / 2, 2000)
    spare = page.insert_htmlbox(rect, doc_html)             # 남은 높이 반환
    used_h = 2000 - (spare if isinstance(spare, (int, float)) else spare[1])
    page.set_mediabox(fitz.Rect(0, 0, width / 2, max(40, used_h + 12)))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_png))
    doc.close()
    return {"ok": True, "type": "reconstructed_excerpt", "evidence": False,
            "path": str(out_png), "source_url": source_url, "captured_at": _now()}


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r = reconstruct_excerpt("시장 규모는 45조원으로 추정된다(재구성 예시).",
                                "https://example.com/report", Path(td) / "r1.png")
        assert r["type"] == "reconstructed_excerpt" and r["evidence"] is False
        assert Path(r["path"]).stat().st_size > 0
    print(f"[{_now()}] capture_web demo OK  (증빙 불인정 산출물)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif len(args) >= 3:
        import json
        print(json.dumps(reconstruct_excerpt(args[0], args[1], args[2]), ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
