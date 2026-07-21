"""capture_pdf.py — source_capture(증빙 인정) 생성기.

로컬/다운로드 PDF에서 fitz로 **정확 숫자**를 찾아 하이라이트→크롭 PNG를 만든다.
evidence-capture.md §2.1 규범 구현:
  - 부분문자열 오매칭 금지(단어 경계 확인) — `3000`을 `300`으로 잘못 잡지 않는다.
  - 숫자 표기 변형(쉼표 유무·공백·NBSP·개행 분리) 정규화 매칭. 개행으로 나뉜
    `300,\n900`도 원문 words 재구성(get_text("words"))으로 매칭한다.
  - 파일명 = evidence ID. 성공 캡처는 오직 진짜 발견 시에만 `<ID>.png`로 남는다.

CLI:
    capture_pdf.py --pdf <path> --needle "300,900" --evidence E001 [--out _captures/] [--page N]
    capture_pdf.py --selfcheck

상태(status) / exit:
    ok            발견 → _captures/<ID>.png + <ID>.json            (exit 0)
    not_found     텍스트는 있으나 needle 미발견 → <ID>.json만        (exit 1)
    fallback_page 스캔 PDF(텍스트레이어 없음) → <ID>.fallback.png   (exit 1)

절대 실패를 성공으로 위장하지 않는다: not_found·fallback_page는 `<ID>.png`(성공
파일명)를 만들지 않으며 exit 1로 실패를 알린다. 재구성물이 아니라 원문 캡처만
`_captures/`에 남는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_paths  # noqa: E402,F401  (import 시 UTF-8 콘솔 부트스트랩 1회)

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import fitz  # noqa: E402  (PyMuPDF; preflight 필수 의존성)
from manifest import sha256_file as _sha256_file  # noqa: E402  (증거 해시 유틸 재사용)


MALGUN = r"C:\Windows\Fonts\malgun.ttf"  # selfcheck용 한글 렌더 폰트(Windows 전용 스킬)
_ID_RE = re.compile(r"[A-Za-z0-9_-]+")
_WS_RE = re.compile(r"\s+")


def _safe_id(evidence: str) -> str:
    """evidence ID는 파일명이 되므로 경로 traversal을 막는다(신뢰경계 검증)."""
    if not evidence or not _ID_RE.fullmatch(evidence):
        raise ValueError(f"evidence ID는 [A-Za-z0-9_-]만 허용: {evidence!r}")
    return evidence


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _normalize(s: str, strip_comma: bool = False) -> str:
    """숫자 표기 변형 흡수: NBSP·전각공백·공백류(스페이스/탭/개행) 제거.
    strip_comma=True면 반각/전각 쉼표까지 제거(쉼표 유무 변형 대응)."""
    s = (s or "").replace(" ", "").replace("　", "")
    s = _WS_RE.sub("", s)
    if strip_comma:
        s = s.replace(",", "").replace("，", "")
    return s


def _boundary_ok(joined: str, idx: int, end: int) -> bool:
    """매칭 구간 [idx,end)가 더 긴 수의 일부가 아닌지(단어 경계) 확인.

    거부 조건:
      - 앞/뒤 문자가 숫자 → 숫자 연속(`3000`의 `300`, `300`의 뒤 `1`).
      - 뒤가 `,`+숫자 또는 앞이 숫자+`,` → 천단위 쉼표 연속(`300,900,000`의 `300,900`).
    """
    before = joined[idx - 1] if idx > 0 else ""
    after = joined[end] if end < len(joined) else ""
    if before.isdigit() or after.isdigit():
        return False
    if after == "," and end + 1 < len(joined) and joined[end + 1].isdigit():
        return False
    if before == "," and idx - 2 >= 0 and joined[idx - 2].isdigit():
        return False
    return True


def _find_matches(page, needle: str):
    """페이지에서 needle을 표기변형 강건하게 찾는다.

    반환:
      None            → 텍스트 레이어 없음(words 부재, 스캔 PDF 신호)
      []              → 텍스트는 있으나 미발견
      [(rects, union), ...] → 매칭들(rects=word별 Rect, union=합집합 Rect)
    """
    words = page.get_text("words")  # (x0,y0,x1,y1, word, block, line, wno)
    if not words:
        return None
    for strip_comma in (False, True):  # 쉼표 유지 매칭 우선, 실패 시 쉼표 제거
        target = _normalize(needle, strip_comma)
        if not target:
            continue
        buf: list[str] = []
        owner: list[int] = []  # buf의 각 문자가 온 word 인덱스
        for wi, w in enumerate(words):
            for ch in _normalize(w[4], strip_comma):
                buf.append(ch)
                owner.append(wi)
        joined = "".join(buf)
        matches = []
        start = 0
        while True:
            hit = joined.find(target, start)
            if hit < 0:
                break
            end = hit + len(target)
            if _boundary_ok(joined, hit, end):
                w0, w1 = owner[hit], owner[end - 1]
                rects = [fitz.Rect(words[i][:4]) for i in range(w0, w1 + 1)]
                union = fitz.Rect(rects[0])
                for r in rects[1:]:
                    union |= r
                matches.append((rects, union))
            start = hit + 1
        if matches:
            return matches
    return []


def _write_meta(out: Path, evidence: str, meta: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{evidence}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_capture(page, pi, rects, union, pdf_path, needle, evidence, out, zoom, n,
                  pad: float = 90):
    """하이라이트 annot 추가 → 문맥 크롭 PNG 저장 + 메타. status=ok.

    파편 크롭 방지: 가로는 **페이지 전폭**, 세로는 pad(기본 90pt)만큼 주변 문맥을
    포함한다. 숫자만 잘린 조각은 사용자가 "그 수치가 그 주장의 값"인지 캡처만으로
    판단할 수 없어 증빙 가치가 떨어진다 — 주변 문장·표 헤더·제목이 함께 보여야 한다."""
    out.mkdir(parents=True, exist_ok=True)
    annot = page.add_highlight_annot(rects)  # word별 quad 하이라이트
    annot.update()
    clip = fitz.Rect(page.rect.x0, union.y0 - pad,
                     page.rect.x1, union.y1 + pad) & page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    png = out / f"{evidence}.png"
    pix.save(png)  # doc 저장 아님 → 원본 PDF(_sources) 불변, sha256은 원본 그대로
    meta = {
        "kind": "source_capture", "status": "ok", "evidence": evidence,
        "pdf_path": str(Path(pdf_path).resolve()), "page": pi,
        "rect": [round(v, 2) for v in (union.x0, union.y0, union.x1, union.y1)],
        "clip": [round(v, 2) for v in (clip.x0, clip.y0, clip.x1, clip.y1)],
        "needle": needle, "match_count": n, "pad": pad,
        "sha256_pdf": _sha256_file(pdf_path),
        "capture_png": str(png.resolve()), "created_at": _now(),
    }
    _write_meta(out, evidence, meta)
    return meta


def _save_fallback(page, first, pdf_path, needle, evidence, out, zoom):
    """스캔 PDF: 페이지 전체 이미지 fallback. 성공 파일명(<ID>.png)은 쓰지 않는다."""
    out.mkdir(parents=True, exist_ok=True)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    png = out / f"{evidence}.fallback.png"
    pix.save(png)
    meta = {
        "kind": "source_capture", "status": "fallback_page", "evidence": evidence,
        "pdf_path": str(Path(pdf_path).resolve()), "page": first, "needle": needle,
        "sha256_pdf": _sha256_file(pdf_path), "fallback_png": str(png.resolve()),
        "reason": "텍스트 레이어 없음(스캔 PDF 추정) — 육안 확인 필요, 자동 캡처 불가",
        "created_at": _now(),
    }
    _write_meta(out, evidence, meta)
    return meta


def _fail_not_found(pdf_path, needle, evidence, out):
    meta = {
        "kind": "source_capture", "status": "not_found", "evidence": evidence,
        "pdf_path": str(Path(pdf_path).resolve()), "needle": needle,
        "sha256_pdf": _sha256_file(pdf_path),
        "reason": "needle 미발견(표기변형 포함) — 대체출처 필요, confirmed 불가",
        "created_at": _now(),
    }
    _write_meta(out, evidence, meta)
    return meta


def capture(pdf_path, needle: str, evidence: str, out_dir="_captures",
            page_no: int | None = None, zoom: float = 2.0, pad: float = 90) -> dict:
    """PDF에서 needle을 찾아 캡처. 상태 dict 반환(성공/실패 위장 없음).

    pad = 매칭 주변 세로 문맥(pt). 표가 크거나 문단이 길면 120~150으로 키운다."""
    _safe_id(evidence)
    if not needle or not _normalize(needle, strip_comma=True):
        raise ValueError("needle이 비었거나 숫자/문자가 없다")
    pdf_path = Path(pdf_path)
    out = Path(out_dir)
    doc = fitz.open(pdf_path)
    try:
        if page_no is not None:
            if not (0 <= page_no < doc.page_count):
                raise ValueError(f"page {page_no} 범위 밖(0..{doc.page_count - 1})")
            page_list = [page_no]
        else:
            page_list = list(range(doc.page_count))

        any_text = False
        for pi in page_list:
            page = doc[pi]
            res = _find_matches(page, needle)
            if res is None:
                continue  # 이 페이지 텍스트 레이어 없음
            any_text = True
            if res:
                rects, union = res[0]  # 첫 매치(오귀속 최종판단은 육안확인 몫)
                return _save_capture(page, pi, rects, union, pdf_path, needle,
                                     evidence, out, zoom, len(res), pad=pad)
        if not any_text:
            first = page_list[0]
            return _save_fallback(doc[first], first, pdf_path, needle,
                                  evidence, out, zoom)
        return _fail_not_found(pdf_path, needle, evidence, out)
    finally:
        doc.close()


# ── selfcheck (PYTHONUTF8=1 권장) ────────────────────────────────────────
def _selfcheck() -> int:
    import tempfile

    def _mk_text_pdf(path):
        d = fitz.open()
        pg = d.new_page(width=440, height=320)
        pg.insert_text(fitz.Point(50, 70), "매출 현황 보고", fontfile=MALGUN,
                       fontname="mg", fontsize=16)
        pg.insert_text(fitz.Point(50, 110), "합계 300, 900 백만원", fontfile=MALGUN,
                       fontname="mg", fontsize=16)      # 공백 표기변형
        pg.insert_text(fitz.Point(50, 150), "재고 3000 개, 순수 300 명", fontfile=MALGUN,
                       fontname="mg", fontsize=16)      # 오매칭 함정(3000, 독립 300)
        d.save(path)
        d.close()

    def _mk_scan_pdf(path):
        raster = fitz.open()
        rp = raster.new_page(width=300, height=150)
        rp.insert_text(fitz.Point(30, 80), "300,900", fontfile=MALGUN,
                       fontname="mg", fontsize=22)
        pm = rp.get_pixmap()                   # 텍스트를 래스터화
        s = fitz.open()
        sp = s.new_page(width=300, height=150)
        sp.insert_image(sp.rect, pixmap=pm)    # 이미지만 삽입 → 텍스트 레이어 없음
        s.save(path)
        raster.close()
        s.close()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        pdf1 = td / "doc1.pdf"
        _mk_text_pdf(pdf1)
        out = td / "_captures"

        # ① 존재 숫자 "300,900" → ok, 파일명 정확히 E001.png
        m = capture(pdf1, "300,900", "E001", out_dir=out)
        assert m["status"] == "ok", m
        assert (out / "E001.png").is_file(), "E001.png 없음"
        assert (out / "E001.json").is_file(), "E001.json 없음"
        # 문맥 크롭: 가로 전폭(파편 크롭 방지) — doc1 폭 440pt
        assert m["clip"][2] - m["clip"][0] >= 430, ("전폭 크롭 아님", m["clip"])

        # ② 표기변형: 문서엔 "300, 900"(공백), 검색은 "300,900"(공백없음) → 성공
        assert m["match_count"] == 1, ("표기변형 매치 수", m)

        # ②-b 개행 분리("12,\n345") → 원문 words 재구성 매칭(get_text words 경로)
        pdf_nl = td / "doc_nl.pdf"
        dn = fitz.open()
        pn = dn.new_page(width=300, height=200)
        pn.insert_text(fitz.Point(50, 80), "값 12,", fontfile=MALGUN,
                       fontname="mg", fontsize=16)      # 첫 줄 끝에 "12,"
        pn.insert_text(fitz.Point(50, 115), "345 원", fontfile=MALGUN,
                       fontname="mg", fontsize=16)      # 다음 줄 앞에 "345"
        dn.save(pdf_nl)
        dn.close()
        mnl = capture(pdf_nl, "12,345", "E020", out_dir=out)
        assert mnl["status"] == "ok" and mnl["match_count"] == 1, ("개행 분리 매칭", mnl)
        assert mnl["rect"][3] - mnl["rect"][1] > 20, ("두 줄 걸친 union", mnl["rect"])

        # 부분문자열 오매칭 방지: "300" 검색은 3000·300,900의 300을 제외한 1건만
        m300 = capture(pdf1, "300", "E300", out_dir=out)
        assert m300["status"] == "ok" and m300["match_count"] == 1, m300
        m3000 = capture(pdf1, "3000", "E3000", out_dir=out)
        assert m3000["status"] == "ok" and m3000["match_count"] == 1, m3000

        # ③ 없는 숫자 → not_found + exit 1, 성공 파일명 미생성
        mnf = capture(pdf1, "999,999", "E999", out_dir=out)
        assert mnf["status"] == "not_found", mnf
        assert not (out / "E999.png").exists(), "not_found인데 성공 png 생성(위장 금지 위반)"
        rc = main(["--pdf", str(pdf1), "--needle", "999,999",
                   "--evidence", "EX", "--out", str(out)])
        assert rc == 1, ("not_found exit code", rc)

        # ④ 텍스트레이어 없는 이미지 PDF → fallback_page + exit 1
        pdf2 = td / "scan.pdf"
        _mk_scan_pdf(pdf2)
        mfb = capture(pdf2, "300,900", "E010", out_dir=out)
        assert mfb["status"] == "fallback_page", mfb
        assert (out / "E010.fallback.png").is_file(), "fallback png 없음"
        assert not (out / "E010.png").exists(), "fallback인데 성공 파일명 생성(위장 금지 위반)"
        rc2 = main(["--pdf", str(pdf2), "--needle", "300,900",
                    "--evidence", "E011", "--out", str(out)])
        assert rc2 == 1, ("fallback exit code", rc2)

        # 파일명↔ID 결박 + 원본 PDF 불변(캡처는 원본을 저장하지 않음)
        meta1 = json.loads((out / "E001.json").read_text(encoding="utf-8"))
        assert meta1["sha256_pdf"] == _sha256_file(pdf1), "원본 PDF 해시 불일치(원본 변조?)"
        assert meta1["evidence"] == "E001"

    print("SELFCHECK OK")
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="capture_pdf", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pdf", help="대상 PDF 경로(_sources/의 원본)")
    p.add_argument("--needle", help="찾을 정확 숫자 문자열(예: 300,900)")
    p.add_argument("--evidence", help="evidence ID(파일명이 됨, 예: E001)")
    p.add_argument("--out", default="_captures", help="캡처 저장 폴더(기본 _captures/)")
    p.add_argument("--page", type=int, default=None, help="특정 페이지만 검색(0-기반)")
    p.add_argument("--pad", type=float, default=90,
                   help="매칭 주변 세로 문맥(pt, 기본 90). 표·긴 문단은 120~150 권장")
    p.add_argument("--selfcheck", action="store_true", help="내부 자기검증")
    args = p.parse_args(argv)

    if args.selfcheck:
        return _selfcheck()
    if not (args.pdf and args.needle and args.evidence):
        p.error("--pdf, --needle, --evidence가 모두 필요합니다 (또는 --selfcheck)")

    try:
        meta = capture(args.pdf, args.needle, args.evidence,
                       out_dir=args.out, page_no=args.page, pad=args.pad)
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(json.dumps({"status": "error", "reason": str(e)}, ensure_ascii=False))
        return 2

    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0 if meta["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
