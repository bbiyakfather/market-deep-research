"""capture_pdf.py — PDF 정확숫자 하이라이트+크롭 → source_capture (plan-v2 핵심설계4).

로컬/다운로드 PDF 에서 대상 숫자를 검색해 하이라이트하고 **좌우 페이지 전폭 + 상하 한 문단**
범위를 크롭한 PNG 를 만든다(국소 크롭 금지 — 문맥이 잘리면 증빙 신빙성이 떨어진다, V16).
파일명 = evidence ID. 정확 숫자 검색(부분문자열 금지 지향) — 표기변형(쉼표·공백)은 변형 재시도.
스캔PDF(텍스트레이어 없음)·표기변형 실패 시 페이지 전체 렌더 + 실패상태(육안 fallback).

CLI: python capture_pdf.py demo
     python capture_pdf.py page <pdf> <N> <out.png>   # 페이지 전면(검색 불가 원문)
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


def _merge_runs(rects: list) -> list:
    """[v9] 한 번의 히트가 여러 span 에 걸쳐 쪼개진 rect 를 하나로 합친다.

    `search_for` 는 매치가 서로 다른 span 에 걸치면 조각난 rect 들을 돌려준다 —
    실측(웹 페이지를 Chrome 이 print 렌더한 PDF): `820.5` → `820` / `.` / `5` 3조각.
    조각을 개별 히트로 보면 **조각마다 옆 글자가 숫자**라서 V15 부분문자열 필터가 전부
    버리고 '숫자 미발견'이 난다(정상 수치인데 캡처 실패). 합쳐야 바깥 경계로 판정된다.
    같은 줄에서 가로로 맞닿은(간격 1pt 미만) 조각만 합치므로, 공백으로 떨어진 별개
    출현은 합쳐지지 않는다. 폭 추정(`r.width/len`)도 합친 뒤라야 맞다.
    """
    out: list = []
    for r in sorted(rects, key=lambda x: (round(x.y0, 1), x.x0)):
        if out and abs(out[-1].y0 - r.y0) < 1.0 and r.x0 - out[-1].x1 < 1.0:
            out[-1] = out[-1] | r                     # fitz.Rect 합집합
        else:
            out.append(fitz.Rect(r))
    return out


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


def _context_clip(page, r, pad: int) -> "fitz.Rect":
    """증빙 크롭 원칙(V16): **좌우는 페이지 전폭**, 상하는 **한 문단만큼** 확장.
    숫자 주변만 오린 국소 크롭은 문서 맥락(제목·표머리·단위)이 잘려 신빙성이 떨어진다.
    문단 = fitz 텍스트 블록. 히트 블록의 위/아래 인접 블록까지 포함하고, 블록을 못 찾으면
    최소 여백(pad*3)으로 대체한다."""
    y0, y1 = r.y0 - pad * 3, r.y1 + pad * 3
    blocks = sorted((b for b in page.get_text("blocks") if b[6] == 0), key=lambda b: b[1])
    hits = [i for i, b in enumerate(blocks) if fitz.Rect(b[:4]).intersects(r)]
    if hits:
        y0 = min(y0, fitz.Rect(blocks[max(0, min(hits) - 1)][:4]).y0 - pad)
        y1 = max(y1, fitz.Rect(blocks[min(len(blocks) - 1, max(hits) + 1)][:4]).y1 + pad)
    try:                                   # 표 셀 히트 → 표 전체(열 제목 포함)까지 확장
        tabs = [fitz.Rect(t.bbox) for t in page.find_tables().tables]
        hit_t = [t for t in tabs if t.intersects(r)]
        # 합계행·이어지는 조각이 별도 표로 인식되는 경우가 흔하다 → 세로로 맞닿은(간격
        # 3*pad 이내) 표를 반복 병합해 열 제목이 잘리지 않게 한다.
        changed = bool(hit_t)
        while changed:
            changed = False
            ty0, ty1 = min(t.y0 for t in hit_t), max(t.y1 for t in hit_t)
            for t in tabs:
                if t in hit_t:
                    continue
                if t.y0 < ty1 + pad * 3 and t.y1 > ty0 - pad * 3:
                    hit_t.append(t); changed = True
        if hit_t:
            y0 = min(y0, min(t.y0 for t in hit_t) - pad)
            y1 = max(y1, max(t.y1 for t in hit_t) + pad)
    except Exception:                      # find_tables 미지원/파싱실패는 문단 크롭 유지
        pass
    # 경계 스냅: 절단선이 텍스트 블록 **내부**를 지나면 글자가 반쯤 잘려 보여 "잘린 증빙"이
    # 된다 → 걸린 블록 바깥으로 밀어낸다(확장하며 새 블록에 걸릴 수 있어 몇 회 반복).
    for _ in range(3):
        moved = False
        for b in blocks:
            bb = fitz.Rect(b[:4])
            if bb.y0 < y0 < bb.y1:
                y0, moved = bb.y0 - 2, True
            if bb.y0 < y1 < bb.y1:
                y1, moved = bb.y1 + 2, True
        if not moved:
            break
    return fitz.Rect(0, max(0, y0), page.rect.width, min(page.rect.height, y1))


# [v6/SC-4] 백지 판정 임계 — 추정이 아니라 실측으로 잡았다(4000픽셀 표본, 2026-08-06):
#   완전 백지 unique=1 ink=0.000 | 정상 표 unique=3 ink=0.0097 | 텍스트1줄 unique=7 ink=0.0067
#   본문 30줄 unique=8 ink=0.0042 | 캡처 픽스처 unique=13 ink=0.0077
# 유니크 컬러 수는 신호가 아니다(정상 표 3 < 텍스트 7) — 첫 시도의 'unique<8' 임계는 정상
# 문서를 잡았다. 확실히 가를 수 있는 것은 '사실상 단일색 화면'뿐이라 거기까지만 기계로 잡고,
# 얇지만 비어있지 않은 캡처는 여전히 사람 눈의 몫으로 남긴다(과잉 차단이 더 나쁘다).
BLANK_MAX_COLORS = 2            # 이하이면 사실상 단일색
BLANK_MAX_INK = 0.0005          # 최빈색과 다른 픽셀 비율 하한(정상 최저 0.0032 대비 6배 여유)


def is_blank_pixmap(pix) -> tuple[bool, dict]:
    """[v6/SC-4] 렌더 결과가 백지·단색인지 픽셀로 판정.

    종전에는 '백지 캡처'를 팀리드 육안(PNG Read)만이 잡을 수 있었다 — 확정 사실 수에 비례해
    이미지 토큰이 들어서 비용 압박이 오면 표본만 보게 되고, 그 순간 유일한 검출 장치가 사라진다.
    생성 시점에 기계로 거르면 육안은 '기계 통과분의 표본'으로 줄어든다.
    """
    try:
        import collections
        s, n = pix.samples, pix.n
        step = max(1, (len(s) // n) // 4000) * n            # 최대 ~4000픽셀만 표본
        px = [s[i:i + n] for i in range(0, len(s) - n, step)]
        if not px:
            return False, {"unique": -1, "ink_ratio": -1}
        cnt = collections.Counter(px)
        ink = 1 - cnt.most_common(1)[0][1] / len(px)
        stat = {"unique": len(cnt), "ink_ratio": round(ink, 5)}
        return (len(cnt) <= BLANK_MAX_COLORS and ink <= BLANK_MAX_INK), stat
    except Exception:
        return False, {"unique": -1, "ink_ratio": -1}        # 판독 불가는 실패로 위장하지 않는다


def _save_checked(pix, out_png: Path) -> dict | None:
    """백지면 저장 자체를 실패로 돌린다(.FAILED 사이드카로). 통과 시 None."""
    blank, stat = is_blank_pixmap(pix)
    if not blank:
        return None
    failed = out_png.with_name(out_png.stem + ".FAILED" + out_png.suffix)
    failed.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(failed))
    return {"ok": False, "type": "source_capture",
            "reason": f"백지·단색 렌더(유니크 {stat['unique']}, 잉크율 {stat['ink_ratio']})",
            "path": str(failed), "captured_at": _now()}


def capture_page(pdf_path: Path | str, page: int, out_png: Path | str, zoom: float = 2.0) -> dict:
    """지정 페이지를 **전면** 캡처(하이라이트 없음). 텍스트레이어가 없거나(스캔) 폰트 인코딩이
    깨져 `search_for` 가 원문을 못 찾는 PDF 의 정당한 증빙 경로. 페이지 전체라 발췌 조작 여지가
    없고 크롭 원칙(전폭+문맥)도 자동 충족한다. 위치는 evidence.locator 로 지정한다."""
    out_png = Path(out_png)
    doc = fitz.open(str(pdf_path))
    try:
        pno = max(0, min(page - 1, doc.page_count - 1))
        p = doc.load_page(pno)
        pix = p.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        bad = _save_checked(pix, out_png)
        if bad:
            return {**bad, "mode": "page", "page": pno + 1}
        out_png.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_png))
        return {"ok": True, "type": "source_capture", "mode": "page", "page": pno + 1,
                "path": str(out_png), "captured_at": _now()}
    finally:
        doc.close()


def capture_number(pdf_path: Path | str, number: str, out_png: Path | str,
                   page_hint: int | None = None, zoom: float = 2.0, pad: int = 40) -> dict:
    out_png = Path(out_png)
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
                filtered = _standalone_rects(page, _merge_runs(raw), v)
                if filtered:
                    matched, rects = v, filtered
                    break
            if not rects:
                continue
            r = rects[0]
            for rr in rects:                              # 하이라이트(필터 후 목록만 — 오귀속 방지)
                try:
                    page.add_highlight_annot(rr)
                except ValueError:                        # 비정상 quad(0폭 rect 등)로 fitz 가 죽는
                    pass                                  # 경우가 있다 → 하이라이트만 포기, 크롭은 유지
            clip = _context_clip(page, r, pad)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
            bad = _save_checked(pix, out_png)      # 숫자는 찾았는데 렌더가 백지면 증빙이 아니다
            if bad:
                return {**bad, "page": pno + 1, "matched": matched}
            out_png.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(out_png))
            return {"ok": True, "type": "source_capture", "page": pno + 1,
                    "matched": matched, "rect": [r.x0, r.y0, r.x1, r.y1],
                    "clip": [clip.x0, clip.y0, clip.x1, clip.y1],
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
        # V16: 크롭은 좌우 페이지 전폭 + 상하 인접 문단(아래 140pt 줄까지) 포함
        pw = fitz.open(str(pdf))[0].rect.width
        assert r["clip"][0] == 0 and abs(r["clip"][2] - pw) < 0.01, r
        assert r["clip"][1] < 88 and r["clip"][3] > 140, r
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

        # V16b: 페이지 전면 모드 — 검색 불가 원문(스캔·깨진 인코딩)의 정당한 증빙 경로
        e6 = Path(td) / "e6.png"
        r6 = capture_page(pdf, 1, e6)
        assert r6["ok"] and r6["mode"] == "page" and e6.stat().st_size > 0, r6

        # [v9] span 파편화 병합. 합성 PDF 로는 파편화를 재현할 수 없어(fitz 가 같은 폰트·
        # 같은 줄을 한 span 으로 뭉친다) 여기서는 순수 함수를 단위로 고정하고, 실제 재현
        # (Chrome print 렌더에서 '820.5' → '820'/'.'/'5' 3조각)은 capture_web.demo_live 가 맡는다.
        R = fitz.Rect
        merged = _merge_runs([R(116, 87, 136, 101), R(136, 87, 139, 99), R(139, 87, 146, 101)])
        assert len(merged) == 1 and merged[0].x0 == 116 and merged[0].x1 == 146, merged
        # 별개 출현은 삼키지 않는다: 공백만큼 떨어졌거나(x 간격) 다른 줄이면 따로
        assert len(_merge_runs([R(100, 87, 120, 101), R(126, 87, 146, 101)])) == 2
        assert len(_merge_runs([R(100, 87, 120, 101), R(100, 140, 120, 154)])) == 2
        # 긍정형 짝: 병합을 넣어도 V15 오귀속 차단은 그대로 — '2045' 안의 45 는 여전히 버린다
        r7 = capture_number(pdf2, "45", Path(td) / "e7.png")
        assert r7["ok"] and r7["rect"][1] > 120, r7
    print(f"[{_now()}] capture_pdf demo OK")


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):          # cp949 콘솔/파이프 UnicodeEncodeError 방지
        _reconf = getattr(_stream, "reconfigure", None)
        if _reconf:
            _reconf(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif args[0] == "page" and len(args) >= 4:            # page <pdf> <N> <out.png>
        import json
        print(json.dumps(capture_page(args[1], int(args[2]), args[3]), ensure_ascii=False))
    elif len(args) >= 3:
        pg = int(args[args.index("--page") + 1]) if "--page" in args else None
        import json
        print(json.dumps(capture_number(args[0], args[1], args[2], pg), ensure_ascii=False))
    else:
        print(__doc__); sys.exit(2)
