"""capture_web.py — 웹 캡처 2종. 실화면(증빙 인정) + 재구성 발췌(증빙 불인정).

`capture_live()` = **실화면 캡처**(source_capture). 브라우저 MCP 없이 Chrome CLI 만으로
원문을 렌더한다 — 【v9】 MCP 미연결 환경에서 증빙 캡처가 통째로 불가능하던 구멍을 닫는다
(`fetch.py` 가 강방어 우회를 코어에 내장한 것과 같은 이유: 외부 연결에 증거능력을 걸지 않는다).

`reconstruct_excerpt()` = **재구성 발췌**(reconstructed_excerpt). 연구자가 다시 그린 것이라
원문 실화면이 아니므로 3중 증빙의 '출처 스크린샷'으로 인정하지 않는다. `_reconstructed/`
에만 저장하고 고객 PDF 증빙에 쓰지 않는다(원본 캡처 불가 시 대체출처 or '미확인' 유지).
두 함수는 서로의 출력 경로를 **양방향으로 거부**한다 — 섞이면 증빙 신뢰경계가 무너진다.

CLI: python capture_web.py demo
     python capture_web.py live <url> <number> <out.png> [--allow a.com,b.com] [--pdf-out p.pdf]
"""
from __future__ import annotations

import html as _html
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import fitz

import capture_pdf
from preflight import _find_chrome


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# --- 【v9】 실화면 캡처 (Chrome CLI 사다리) -----------------------------------
CHROME_TIMEOUT = 90         # 초 — 렌더가 걸려도 파이프라인이 멈추지 않게 죽인다
VIRTUAL_TIME = 8000         # ms — JS 렌더 대기. agent-browser 의 wait_for_text 대체지만
                            # '텍스트가 뜰 때까지'가 아니라 '이만큼 기다림'이라 더 무디다.
SHOT_VIEWPORT = (1440, 3000)
# ponytail: 스크린샷은 이 창 크기만 담는다(스크롤 아래는 잘림). 더 긴 페이지는 viewport=
# 로 높이를 올린다 — 자동 계산은 페이지 높이를 읽을 JS 실행이 필요해 CDP 를 물어야 한다.

# 【v9】 "print 렌더의 텍스트를 오라클로 믿어도 되는가" 임계 — 추정이 아니라 실측(2026-08-06):
#   빈 body 0자 | print 로 body 전체 숨김 0자 | SPA 미렌더 0자
#   print 로 본문만 숨김(헤더 잔존) 47자 | 정상 짧은 페이지 38자 | 정상 리포트 592자
# 낮은 구간에서 길이는 신호가 아니다(오라클이 깨진 47자 > 정상 38자). 확실히 가를 수 있는
# 것은 **0자뿐**이므로 거기까지만 기계로 잡는다. 본문 일부만 print 에서 사라진 페이지는
# fail-closed 로 두고(사유·힌트 반환), 화면 캡처가 필요하다는 판단은 사람이 `number=None`
# 으로 명시하게 한다 — 조용한 강등보다 명시적 결정이 감사에 남는다.
TEXT_ORACLE_MIN = 1


def _chrome(*args: str, timeout: int = CHROME_TIMEOUT) -> str:
    """Chrome 을 헤드리스로 1회 실행하고 stderr 꼬리를 돌려준다(실패 원인 노출용)."""
    chrome = _find_chrome()
    if not chrome:
        raise RuntimeError("Chrome 미발견 — G0 preflight 확인")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
           f"--virtual-time-budget={VIRTUAL_TIME}", *args]
    try:
        # encoding 명시: 한글 Windows(cp949) 기본 디코딩이 Chrome stderr 에서 죽는다(render_pdf 동일)
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"timeout({timeout}s)"
    return (r.stderr or "").strip()[-200:]


def _host_rules(allow: list[str] | None) -> list[str]:
    """agent-browser `allowedDomains` 대체 — 실측: `MAP * ~NOTFOUND` 로 전면 차단하고
    `EXCLUDE <도메인>` 으로 필요한 곳만 연다(부정형 짝 확인: 대상 도메인을 빼면 Chrome
    오류 페이지가 렌더된다). None 이면 제한 없음 — 대상 도메인만 남기면 CSS/이미지 CDN 이
    막혀 렌더가 깨지는 페이지가 많으므로, 호출자가 대상+자원 CDN 을 함께 넘기는 게 원래 사용법."""
    if not allow:
        return []
    return ["--host-resolver-rules=" + "MAP * ~NOTFOUND, " + ", ".join(f"EXCLUDE {d}" for d in allow)]


def _failed_sidecar(out_png: Path) -> Path:
    return out_png.with_name(out_png.stem + ".FAILED" + out_png.suffix)


def capture_live(url: str, number: str | None, out_png: Path | str, *,
                 allow_domains: list[str] | None = None,
                 pdf_out: Path | str | None = None,
                 viewport: tuple[int, int] = SHOT_VIEWPORT) -> dict:
    """웹 원문 **실화면 캡처** — 브라우저 MCP 없이 Chrome CLI 만으로. source_capture 인정.

    사다리: ① `--print-to-pdf` → `capture_pdf.capture_number`(정확숫자 하이라이트 + V16
    전폭·문단 크롭) ② `--screenshot` 뷰포트 렌더 ③ 소진(브라우저 MCP·대체출처로).

    ①이 1순위인 이유 두 가지 — (a) 문서 **전체**가 렌더돼 스크롤 도달 실패(무한스크롤·
    비네트 광고·가상스크롤)가 구조적으로 발생하지 않는다. (b) PDF 텍스트레이어 덕에
    "캡처 안에 그 수치가 실재하는가"를 **기계가** 확인한다 — PNG 만으로는 육안이 유일한
    검출 장치였다. ①의 실패 대표 원인은 print CSS 가 내용을 지운 페이지이고(실측 확인),
    그건 ②가 정확히 메운다. 즉 "수치를 찾아야 한다"는 기존 조건이 print-CSS 탐지기를 겸한다.

    ⚠ `url` 은 **리다이렉트가 해소된 최종 URL**을 넘길 것. Chrome CLI 는 최종 URL 을
    보고하지 않으므로(agent-browser `data.url` 대체 불가) 결박용 최종 URL 은 `fetch.py` 가
    확정한 값을 쓴다 — 이 함수는 받은 URL 을 그대로 기록할 뿐 검증하지 않는다.
    `number=None` 이면 ①을 건너뛰고 화면 캡처만 한다(수치 지정 없는 페이지 증빙).
    """
    out_png = Path(out_png)
    # 재구성 발췌와 실화면은 신뢰등급이 다르다 — 경로가 섞이면 증빙 경계가 무너지므로 양방향 차단.
    if "_reconstructed" in out_png.as_posix().split("/"):
        raise ValueError(f"실화면 캡처는 _reconstructed/ 하위에 저장할 수 없다: {out_png}")
    rules = _host_rules(allow_domains)
    tried: list[str] = []

    oracle_len: int | None = None       # 렌더된 원문의 텍스트 길이(None = 오라클 없음)
    if number:
        with tempfile.TemporaryDirectory() as td:
            # Chrome 은 --print-to-pdf 상대경로를 자기 cwd 기준으로 해석한다 → 항상 절대경로.
            pdf = (Path(pdf_out).resolve() if pdf_out else Path(td) / "live.pdf")
            pdf.parent.mkdir(parents=True, exist_ok=True)
            err = _chrome("--no-pdf-header-footer", f"--print-to-pdf={pdf}", *rules, url)
            if pdf.exists() and pdf.stat().st_size:
                r = capture_pdf.capture_number(pdf, number, out_png)
                if r.get("ok"):
                    return {**r, "capture_mode": "print", "capture_verbatim": r.get("matched"),
                            "source_url": url, "rendered_pdf": str(pdf) if pdf_out else None}
                tried.append(f"print:{r.get('reason', '크롭 실패')}")
                # capture_pdf 가 남긴 .FAILED 는 여기선 오해를 부른다 — 2순위가 성공하면
                # 성공한 캡처 옆에 '실패' 파일이 남아 감사에서 잘못 읽힌다. 사유는 tried 로 반환.
                _failed_sidecar(out_png).unlink(missing_ok=True)
                doc = fitz.open(str(pdf))
                try:
                    oracle_len = sum(len(doc.load_page(i).get_text().strip())
                                     for i in range(doc.page_count))
                finally:
                    doc.close()
            else:
                tried.append(f"print:렌더 실패({err or 'PDF 미생성'})")

    # ★ 폴백 조건을 좁히는 지점. 텍스트 오라클이 **살아 있는데** 수치가 없다면 그 수치는
    # 렌더된 원문에 없는 것이다 — 여기서 화면 캡처로 내려가면 "그 수치가 없는 이미지"가
    # source_capture 로 등재된다(백지 캡처·캡처 돌려막기와 같은 계열의 구멍). 화면 폴백은
    # 오라클 자체가 죽었을 때(SPA 가 print 에서 빈 페이지로 나옴 · print CSS 가 본문을
    # 통째로 감춤 · 렌더 실패)만 정당하다.
    if oracle_len is not None and oracle_len >= TEXT_ORACLE_MIN:
        return {"ok": False, "type": "source_capture", "source_url": url,
                "reason": f"렌더된 원문({oracle_len}자)에 '{number}' 없음 — {' / '.join(tried)}",
                "hint": "수치 표기·연도를 재확인하거나(대장 오기 가능) 로그인·상호작용이 필요한 "
                        "페이지면 브라우저 MCP(claude-in-chrome)로",
                "captured_at": _now()}

    w, h = viewport
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "shot.png"
        err = _chrome(f"--window-size={w},{h}", f"--screenshot={tmp}", *rules, url)
        if tmp.exists() and tmp.stat().st_size:
            blank, stat = capture_pdf.is_blank_pixmap(fitz.Pixmap(str(tmp)))
            if blank:
                tried.append(f"screen:백지·단색(유니크 {stat['unique']}, 잉크율 {stat['ink_ratio']})")
            else:
                out_png.parent.mkdir(parents=True, exist_ok=True)
                out_png.write_bytes(tmp.read_bytes())
                return {"ok": True, "type": "source_capture", "capture_mode": "screen",
                        "capture_verbatim": None, "path": str(out_png), "source_url": url,
                        "viewport": f"{w}x{h}", "captured_at": _now(),
                        "note": "verbatim 기계확인 불가(텍스트레이어 없음) — 팀리드 육안 확인 필수"}
        else:
            tried.append(f"screen:렌더 실패({err or 'PNG 미생성'})")

    # 소진: out_png 를 만들지 않는다(V04) — 대장이 이 경로를 가리키면 [증빙유실] FAIL 로 잡힌다.
    return {"ok": False, "type": "source_capture", "source_url": url,
            "reason": " / ".join(tried) or "시도 없음",
            "hint": "로그인·상호작용(동의배너·클릭확장) 필요 페이지 — 브라우저 MCP"
                    "(claude-in-chrome) 또는 대체출처로",
            "captured_at": _now()}


def reconstruct_excerpt(text: str, source_url: str, out_png: Path | str,
                        width: int = 720, zoom: float = 2.0) -> dict:
    # G4: 재구성 발췌는 증빙 불인정이라 _reconstructed/ 밖에 저장되면 verify_facts 의 capture
    # 신뢰경계 검사를 우회해 증빙처럼 보일 위험이 있다 — 산출 단계에서부터 차단.
    if "_reconstructed" not in Path(out_png).as_posix().split("/"):
        raise ValueError(f"재구성 발췌는 _reconstructed/ 하위에만 저장 가능: {out_png}")
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


_DEMO_PAGE = """<html><head><meta charset="utf-8"><style>{style}</style></head><body>
<h1>Global Market Report 2024</h1><nav>Home About Contact</nav>
<div class="main"><h2>Market Size</h2>
<table border=1><tr><th>Year</th><th>USD mn</th></tr><tr><td>2024</td><td>820.5</td></tr></table>
<p>The global market was valued at USD 820.5 million in 2024, up from 2045 units.</p></div>
</body></html>"""


def _demo_url(td: Path, name: str, style: str = "") -> str:
    f = td / name
    f.write_text(_DEMO_PAGE.format(style=style), encoding="utf-8")
    return f.resolve().as_uri()


def demo_live() -> None:
    """【v9】 실화면 캡처 사다리 자체검사. file:// 로컬 페이지만 쓰므로 네트워크 불요."""
    import tempfile
    with tempfile.TemporaryDirectory() as _td:
        td = Path(_td)
        cap = td / "_captures"

        # ① 정상 경로 — print 렌더에서 수치를 찾아 V16 크롭. verbatim 이 기계로 확인된다.
        r = capture_live(_demo_url(td, "ok.html"), "820.5", cap / "E001.png")
        assert r["ok"] and r["capture_mode"] == "print", r
        assert r["capture_verbatim"] == "820.5", r
        assert (cap / "E001.png").stat().st_size > 0, r

        # ② 부분문자열 오귀속은 여전히 차단(capture_pdf 의 V15 가 그대로 물린다) —
        #    '45' 는 '2045'/'820.5' 안에만 있으므로 독립 히트가 없어 통과되면 안 된다.
        e2 = cap / "E002.png"
        r2 = capture_live(_demo_url(td, "ok2.html"), "45", e2)
        assert not r2["ok"] and not e2.exists(), r2

        # ③ print CSS 가 본문을 통째로 지운 페이지 → 텍스트 오라클이 죽었으므로(0자)
        #    화면 캡처로 폴백. verbatim 은 기계확인 불가로 표시된다.
        r3 = capture_live(_demo_url(td, "hidden.html", "@media print{body{display:none}}"),
                          "820.5", cap / "E003.png")
        assert r3["ok"] and r3["capture_mode"] == "screen", r3
        assert r3["capture_verbatim"] is None and "육안" in r3["note"], r3

        # ④ ★fail-closed: 오라클이 살아 있는데 수치가 없으면 화면 캡처로 내려가지 않는다.
        #    (내려가면 '그 수치가 없는 이미지'가 source_capture 로 등재된다)
        e4 = cap / "E004.png"
        r4 = capture_live(_demo_url(td, "ok3.html"), "999999", e4)
        assert not r4["ok"] and not e4.exists(), r4
        assert "없음" in r4["reason"], r4
        assert not _failed_sidecar(e4).exists(), "실패 사이드카가 성공 캡처처럼 남았다"

        # ⑤ number=None → 오라클 없이 화면 캡처(수치 지정 없는 페이지 증빙)
        r5 = capture_live(_demo_url(td, "ok4.html"), None, cap / "E005.png")
        assert r5["ok"] and r5["capture_mode"] == "screen" and r5["viewport"] == "1440x3000", r5

        # ⑥ 신뢰경계 — 실화면 캡처를 _reconstructed/ 에 쓰려 하면 거부(반대 방향은 아래 demo)
        try:
            capture_live("https://example.com", "1", td / "_reconstructed" / "x.png")
            assert False, "_reconstructed/ 출력이 통과됨"
        except ValueError:
            pass

        # ⑦ allowedDomains 대체 규칙의 형태. **네트워크 차단 자체는 이 데모가 검증하지 않는다** —
        #    host-resolver-rules 는 DNS 규칙이라 file:// 에는 적용되지 않고(실측 확인), 원격
        #    검증은 네트워크를 타야 해서 오프라인 자체검사에 넣을 수 없다. 차단 동작은
        #    2026-08-06 실측으로 확인했다(example.com 허용 시 본문 렌더 / 미허용 시 Chrome 오류 페이지).
        assert _host_rules(None) == []
        assert _host_rules(["a.com", "cdn.b.net"]) == [
            "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE a.com, EXCLUDE cdn.b.net"]
    print(f"[{_now()}] capture_web live demo OK  (print→screen 사다리 · fail-closed)")


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r = reconstruct_excerpt("시장 규모는 45조원으로 추정된다(재구성 예시).",
                                "https://example.com/report", Path(td) / "_reconstructed" / "r1.png")
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
    demo_live()


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):          # cp949 콘솔/파이프 UnicodeEncodeError 방지
        _reconf = getattr(_stream, "reconfigure", None)
        if _reconf:
            _reconf(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif args[0] == "live" and len(args) >= 4:         # live <url> <number|-> <out.png>
        import json
        allow = next((a.split("=", 1)[1].split(",") for a in args if a.startswith("--allow=")), None)
        pdf_out = next((a.split("=", 1)[1] for a in args if a.startswith("--pdf-out=")), None)
        num = None if args[2] == "-" else args[2]
        print(json.dumps(capture_live(args[1], num, args[3], allow_domains=allow,
                                      pdf_out=pdf_out), ensure_ascii=False))
    elif len(args) >= 3:
        import json
        print(json.dumps(reconstruct_excerpt(args[0], args[1], args[2]), ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
