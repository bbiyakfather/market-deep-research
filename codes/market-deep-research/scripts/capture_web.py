"""capture_web.py — 재구성 발췌 렌더 → reconstructed_excerpt (내부용, 증빙 불인정).

★중요: 이 산출물은 연구자가 재구성한 발췌물이다. 원문 실화면이 아니므로 3중 증빙의
'출처 스크린샷(source_capture)'으로 인정하지 않는다. `_reconstructed/` 에만 저장하고,
고객 PDF 증빙에는 쓰지 않는다(원본 캡처 불가 시 대체출처 or '미확인' 유지).
실화면 캡처는 접근가능 웹=브라우저 MCP(agent-browser 우선) / 로컬PDF=capture_pdf.py.

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
    # G4: 재구성 발췌는 증빙 불인정이라 _reconstructed/ 밖에 저장되면 verify_facts 의 capture
    # 신뢰경계 검사를 우회해 증빙처럼 보일 위험이 있다 — 산출 단계에서부터 차단.
    target = Path(out_png).absolute()
    capture_root = next((p for p in target.parents if p.name == "_captures"), None)
    if capture_root is None:
        raise ValueError(f"재구성 발췌는 _captures/_reconstructed/ 하위에만 저장 가능: {out_png}")
    # 승인 루트 자체의 symlink/junction 이탈도 허용하지 않는다.
    expected_capture_root = capture_root.parent.resolve() / "_captures"
    if capture_root.resolve() != expected_capture_root:
        raise ValueError(f"재구성 발췌 경로 이탈: {out_png}")
    capture_root = expected_capture_root
    allowed = capture_root / "_reconstructed"
    out_png = target.resolve()
    if allowed.resolve() != allowed or not out_png.is_relative_to(allowed):
        raise ValueError(f"재구성 발췌 경로 이탈: {out_png}")
    safe = _html.escape(text)
    doc_html = (
        '<div style="font-family:Malgun Gothic,sans-serif;font-size:13px;padding:14px;">'
        '<div style="color:#b00;font-size:11px;border:1px solid #b00;padding:2px 6px;'
        'display:inline-block;margin-bottom:8px;">내부 재구성 발췌 · 증빙 불인정</div>'
        f'<div style="white-space:pre-wrap;line-height:1.5;">{safe}</div>'
        f'<div style="color:#888;font-size:10px;margin-top:10px;">재구성: {_now()} · '
        f'출처(주장): {_html.escape(source_url)}</div></div>')
    doc = fitz.open()
    page = doc.new_page(width=width / 2, height=2000)       # rect 밖은 잘리므로 충분한 높이로 생성
    rect = fitz.Rect(0, 0, width / 2, 2000)
    spare = page.insert_htmlbox(rect, doc_html)             # (남은 높이, scale) 반환 — [0]이 남은 높이
    used_h = 2000 - (spare if isinstance(spare, (int, float)) else spare[0])
    clip = fitz.Rect(0, 0, width / 2, max(40, used_h + 12))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)   # mediabox 조작 대신 클립으로 크롭
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_png))
    doc.close()
    return {"ok": True, "type": "reconstructed_excerpt", "evidence": False,
            "path": str(out_png), "source_url": source_url, "captured_at": _now()}


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r = reconstruct_excerpt("시장 규모는 45조원으로 추정된다(재구성 예시).",
                                "https://example.com/report", Path(td) / "_captures" / "_reconstructed" / "r1.png")
        assert r["type"] == "reconstructed_excerpt" and r["evidence"] is False
        assert Path(r["path"]).stat().st_size > 0
        # V23 회귀 가드: 백지 PNG(수정 전 720x4022, 비백색 픽셀 0개)로 돌아가지 않았는지 확인
        px = fitz.Pixmap(r["path"])
        assert px.height < 400, px.height
        assert any(px.samples[i] < 240 for i in range(0, len(px.samples), 3))
        # G4: _reconstructed/ 밖 출력 경로는 거부(증빙 우회 차단)
        try:
            reconstruct_excerpt("x", "https://example.com", Path(td) / "outside.png")
            assert False, "_reconstructed/ 밖 출력이 통과됨"
        except ValueError:
            pass
    print(f"[{_now()}] capture_web demo OK  (증빙 불인정 산출물)")


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):          # cp949 콘솔/파이프 UnicodeEncodeError 방지
        _reconf = getattr(_stream, "reconfigure", None)
        if _reconf:
            _reconf(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif len(args) >= 3:
        import json
        print(json.dumps(reconstruct_excerpt(args[0], args[1], args[2]), ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
