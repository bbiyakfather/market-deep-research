"""모듈 원고(md) → 발주처 「본보고서 양식」 그대로인 HWPX.

양식 파일을 템플릿으로 쓴다. header.xml(글꼴·글자모양·문단모양 정의 전부)을 통째로
복사하고 section0.xml 만 원고로부터 새로 조립하므로, 스타일을 코드에서 다시 정의할
일이 없다. 양식이 바뀌면 양식 파일과 profiles/*.json 의 ID 만 맞춘다.

실행:
    python build_hwpx.py build <원고.md> --template <양식.hwpx> [--profile navion-2026] [--out out.hwpx]
    python build_hwpx.py split <report.md> --out <dir> [--expect-parts N]
    python build_hwpx.py outline <md> [<md> ...] [--json]
    python build_hwpx.py --demo
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")   # 경고도 한글이라 같이 — cp949 콘솔에서 깨지면 못 읽는다
except Exception:
    pass

SCRIPTS = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS.parent
PROFILES_DIR = SKILL_ROOT / "profiles"

# ── 기본값 = navion-2026 실측. load_profile() 이 덮어쓴다. ──────────────
PROFILE: dict = {}
TITLE = (23, 46)
H1 = (24, 47)
H2 = (25, 48)
H3 = (26, 49)
BODY1 = (27, 50)
BODY2 = (29, 51)
CAPTION = (32, 52)
TH = (38, 55)
TD = (35, 56)
TSRC = (37, 57)
PARA_CENTER = 53
BODY_BOLD_BASE = 29
BODY_BOLD = 0                 # patch_header 가 header itemCnt 로 할당
BF_TH = {"first": 10, "mid": 11, "last": 12}
BF_TD = {"first": 13, "mid": 9, "last": 15}
BF_SRC = 16
BF_TBL = 9
PAGE_W = 48188
PAGE_H = 70012
TBL_W = 48178
IMG_MAX_H = 58000
PX2HWP = 75                   # 1px(96dpi) = 75 HWPUNIT — 원본 이미지 좌표
MIN_COL = 3300
IN_MARGIN = 1020
COL_UNIT = 500
LABEL_MAX = 12
DATA_CAP = 30
TH_LINE = 1300
TD_LINE = 1600
CELL_VPAD = 282
CELL_BULLET = 0               # patch_header 가 header itemCnt 로 할당 (셀 안 왼쪽정렬 + '-' 글머리)
# 세로 묶음 표 열 너비 비율(%) — 실측 3567/9027/35584, 8953/39225
GROUP_RATIO = {"A": (8, 18, 74), "B": (19, 81)}
# 원고 표 캡션 끝의 명시 형식 표시 — 자동 판정보다 우선한다
# 이름이 틀려도({형식=C}) 떼어낸다 — 발주처 문서에 표시가 인쇄되면 안 된다
FMT_RE = re.compile(r"\s*\{형식=([^}]*)\}\s*$")

# report.md 의 로마숫자 부는 `# Ⅰ.` 또는 `## Ⅰ.` 로 온다. 그룹 1 = 해시.
CHAPTER_RE = re.compile(r"^(#{1,2})\s+([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+)\.\s*(.+)$")
# ## 부로 잘린 모듈만 제목을 한 단계 올린다 (##→#, ###→##, … #####→####).
HEADING_PROMOTE_RE = re.compile(r"^(#{2,5})(\s+.*)$")

_uid = [1174400000]


def uid() -> int:
    _uid[0] += 1
    return _uid[0]


def load_profile(name_or_path: str | Path | None = None) -> dict:
    """프로필 JSON 로드. 이름이면 profiles/<name>.json, 경로면 그 파일."""
    if name_or_path is None:
        name_or_path = "navion-2026"
    raw = Path(name_or_path)
    if raw.is_file():
        path = raw
    else:
        path = PROFILES_DIR / f"{raw.stem}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    apply_profile(data)
    return data


def apply_profile(prof: dict) -> None:
    """프로필 키를 모듈 전역 상수에 반영한다. col_widths 등이 이 값을 읽는다."""
    global TITLE, H1, H2, H3, BODY1, BODY2, CAPTION, TH, TD, TSRC
    global PARA_CENTER, BODY_BOLD_BASE
    global BF_TH, BF_TD, BF_SRC, BF_TBL
    global PAGE_W, PAGE_H, TBL_W, IMG_MAX_H
    global MIN_COL, IN_MARGIN, COL_UNIT, LABEL_MAX, DATA_CAP
    global TH_LINE, TD_LINE, CELL_VPAD, PROFILE
    st = prof["styles"]
    TITLE = tuple(st["title"])
    H1 = tuple(st["h1"])
    H2 = tuple(st["h2"])
    H3 = tuple(st["h3"])
    BODY1 = tuple(st["body1"])
    BODY2 = tuple(st["body2"])
    CAPTION = tuple(st["caption"])
    TH = tuple(st["th"])
    TD = tuple(st["td"])
    TSRC = tuple(st["tsrc"])
    PARA_CENTER = int(st["para_center"])
    BODY_BOLD_BASE = int(st["body_bold_base"])
    bf = prof["border_fill"]
    BF_TH = {"first": int(bf["th"]["first"]), "mid": int(bf["th"]["mid"]),
             "last": int(bf["th"]["last"])}
    BF_TD = {"first": int(bf["td"]["first"]), "mid": int(bf["td"]["mid"]),
             "last": int(bf["td"]["last"])}
    BF_SRC = int(bf["src"])
    BF_TBL = int(bf["tbl"])
    pg = prof["page"]
    PAGE_W = int(pg["body_w"])
    PAGE_H = int(pg["body_h"])
    TBL_W = int(pg["tbl_w"])
    IMG_MAX_H = int(pg["img_max_h"])
    tb = prof["table"]
    MIN_COL = int(tb["min_col"])
    IN_MARGIN = int(tb["in_margin"])
    COL_UNIT = int(tb["col_unit"])
    LABEL_MAX = int(tb["label_max"])
    DATA_CAP = int(tb["data_cap"])
    TH_LINE = int(tb["th_line"])
    TD_LINE = int(tb["td_line"])
    CELL_VPAD = int(tb["cell_vpad"])
    PROFILE = prof


# ── 1. 원고 파싱 ─────────────────────────────────────────────────────────
def parse_md(text: str) -> list[dict]:
    """원고 마크다운을 블록 리스트로. 양식이 아는 종류만 만든다."""
    blocks: list[dict] = []
    lines = text.splitlines()
    i = 0
    pending_caption: str | None = None      # <표> 캡션은 표보다 먼저 나온다
    pending_fmt = ""                        # 캡션 끝 {형식=A} 표시 — 표 블록으로 넘긴다

    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            i += 1
            continue

        if m := re.match(r"^(#{1,4})\s+(.*)$", s):
            lvl = len(m.group(1))
            blocks.append({"t": ["title", "h1", "h2", "h3"][lvl - 1], "text": m.group(2)})

        elif re.match(r"^[①-⑳]\s", s):
            # ① 은 두 용법이 섞인다 — "① 기술 공급사"처럼 짧으면 3단계 제목,
            # "① 1단계, 프로젝트 설계 : …" 처럼 설명이 붙어 길면 본문 문단이다.
            blocks.append({"t": "h3" if _disp_len(s) <= 60 else "body1", "text": s})

        elif m := re.match(r"^<sup>(\d+\))</sup>\s+(.*)$", s):
            # 문서 끝에 모아 둔 각주 정의 — 본문 불릿을 붙이면 안 된다
            blocks.append({"t": "footnote", "text": f"{m.group(1)} {m.group(2)}"})

        elif s.startswith("<표>"):
            cap = s[3:].strip()
            m = FMT_RE.search(cap)
            pending_fmt = ""
            if m:
                name = m.group(1).strip()
                name = "matrix" if name.lower() == "matrix" else name.upper()
                if name in ("A", "B", "matrix"):
                    pending_fmt = name
                else:                                   # 모르는 이름은 자동 판정으로 넘긴다
                    print(f"  ! 알 수 없는 표 형식 {{형식={m.group(1)}}} — 자동 판정 사용: {cap}",
                          file=sys.stderr)
            pending_caption = FMT_RE.sub("", cap)       # 표시는 출력 문서에 남기지 않는다

        elif s.startswith("[그림]"):                       # 직전 그림의 캡션
            for b in reversed(blocks):
                if b["t"] == "image":
                    b["caption"] = s[4:].strip()
                    break

        elif m := re.match(r"^!\[(.*?)\]\((.+?)\)$", s):
            blocks.append({"t": "image", "alt": m.group(1), "src": m.group(2), "caption": ""})

        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):   # 구분행은 버린다
                    rows.append(cells)
                i += 1
            i -= 1
            if rows:
                blocks.append({"t": "table", "rows": rows, "caption": pending_caption or "", "src": "",
                               "fmt": pending_fmt})
                pending_caption = None
                pending_fmt = ""

        elif m := re.match(r"^\* ([^:\n]{1,20}) : (.*)$", s):
            # "* 출처 : ..." — 직전이 표면 표의 출처행으로, 그림이면 캡션 아래 문단으로
            note = f"* {m.group(1)} : {m.group(2)}"
            if blocks and blocks[-1]["t"] == "table" and not blocks[-1]["src"]:
                blocks[-1]["src"] = note
            else:
                blocks.append({"t": "note", "text": note})

        elif s.startswith(("❍ ", "○ ")):
            blocks.append({"t": "body1", "text": s[2:]})

        elif s.startswith("- "):
            blocks.append({"t": "body2", "text": s[2:]})

        else:
            blocks.append({"t": "body1", "text": s})       # (전년판 요약) 같은 개요 문단

        i += 1
    return blocks


# ── 2. 인라인 서식 ───────────────────────────────────────────────────────
def runs(text: str, char_id: int, bold_id: int | None = None) -> str:
    """**굵게** 와 <sup>1)</sup> 만 해석한다. 나머지는 평문."""
    text = re.sub(r"<sup>(.*?)</sup>", r"\1", text)         # 각주 마커는 평문 유지
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", text)       # 링크는 표시 텍스트만
    out = []
    for part in re.split(r"(\*\*.+?\*\*)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            cid = bold_id if bold_id is not None else char_id
            out.append(f'<hp:run charPrIDRef="{cid}"><hp:t>{escape(part[2:-2])}</hp:t></hp:run>')
        else:
            out.append(f'<hp:run charPrIDRef="{char_id}"><hp:t>{escape(part)}</hp:t></hp:run>')
    return "".join(out) or f'<hp:run charPrIDRef="{char_id}"><hp:t></hp:t></hp:run>'


def para(text: str, style: tuple[int, int], bold_id: int | None = None) -> str:
    cid, pid = style
    return (f'<hp:p id="0" paraPrIDRef="{pid}" styleIDRef="0" pageBreak="0" columnBreak="0" '
            f'merged="0">{runs(text, cid, bold_id)}</hp:p>')


# ── 3. 표 ────────────────────────────────────────────────────────────────
def _disp_len(s: str) -> int:
    """열폭 배분용 폭 — 한글·한자는 2칸으로 센다."""
    return sum(2 if ord(c) > 0x2E80 else 1 for c in s)


def col_widths(rows: list[list[str]], ncol: int) -> list[int]:
    """열별 하한을 내용에서 먼저 정하고, 남은 폭만 내용 길이에 비례 배분한다.

    단순 비례로만 나누면 두 가지가 깨진다 — 서술이 긴 열이 폭을 독식해 짧은 라벨 열이 글자 폭
    아래로 눌리고(`구분`이 한 글자씩 세로로 쏟아짐), 열 폭이 어절보다 좁아 낱말 중간이 잘린다
    (`에너지다변화절약연구소(IDAE` / `)`). 그래서 하한을 내용에서 계산해 먼저 확보한다.
    """
    need, prop = [], []
    for c in range(ncol):
        cells = [r[c] for r in rows if c < len(r)]
        longest_cell = max((_disp_len(t) for t in cells), default=1)
        longest_word = max((_disp_len(t) for cl in cells for t in cl.split()), default=1)
        # 라벨 열(`구분`·`정책 입안` 등 짧은 열)은 통째로 한 줄에 — 표마다 줄 수가 달라지지 않게.
        # 서술 열은 최소한 낱말이 안 잘릴 만큼. 어느 쪽이든 한 열이 표의 절반을 넘지는 않는다.
        lo = (longest_cell if longest_cell <= LABEL_MAX else longest_word) * COL_UNIT + IN_MARGIN
        need.append(max(MIN_COL, min(lo, TBL_W // 2)))

        head = _disp_len(rows[0][c]) if c < len(rows[0]) else 1
        data = max((_disp_len(t) for t in cells[1:]), default=1)
        prop.append(max(3, head, min(data, DATA_CAP)))      # 서술이 긴 셀은 상한에서 끊어 센다

    total_need = sum(need)
    if total_need >= TBL_W:                                 # 하한만으로 꽉 차면 하한끼리 비례 축소
        out = [x * TBL_W // total_need for x in need]
    else:
        free, tp = TBL_W - total_need, sum(prop)
        out = [need[i] + free * prop[i] // tp for i in range(ncol)]
    out[-1] += TBL_W - sum(out)                             # 반올림 오차는 끝 열이 흡수
    return out


def est_height(rows: list[list[str]], widths: list[int], has_src: bool) -> int:
    """표가 몇 HWPUNIT 을 차지할지 어림한다 — 한 쪽을 넘는지 판정하는 용도.

    셀 글자가 열 폭에 맞춰 몇 줄로 접히는지 세고, 줄 수 × 줄 높이 + 셀 상하 여백으로 더한다.
    정확한 조판 높이가 아니라 판정용 어림값이다.
    """
    h = 0
    for ri, r in enumerate(rows):
        line_h = TH_LINE if ri == 0 else TD_LINE
        lines = 1
        for ci, txt in enumerate(r):
            avail = widths[ci] - IN_MARGIN
            if avail > 0:
                lines = max(lines, -(-_disp_len(txt) * COL_UNIT // avail))
        h += lines * line_h + CELL_VPAD
    if has_src:
        h += TD_LINE + CELL_VPAD
    return h


def cell(text: str | list[str], style: tuple[int, int], bf: int, col: int, row: int,
         width: int, height: int, colspan: int = 1, rowspan: int = 1) -> str:
    """text 가 list 면 항목마다 글머리 문단 하나씩(줄바꿈 문자로 흉내내지 않는다)."""
    cid, pid = style
    bold = TH[0] if style is TD else None
    if isinstance(text, list):
        # 셀은 <hp:p> 를 최소 1개 가져야 한다 — 빈 목록이면 한글이 파일을 못 연다
        body = "".join(f'<hp:p id="0" paraPrIDRef="{CELL_BULLET}" styleIDRef="0" pageBreak="0" '
                       f'columnBreak="0" merged="0">{runs(t, cid, bold)}</hp:p>'
                       for t in text or ["-"])
    else:
        body = (f'<hp:p id="0" paraPrIDRef="{pid}" styleIDRef="0" pageBreak="0" columnBreak="0" '
                f'merged="0">{runs(text, cid, bold)}</hp:p>')
    return (
        f'<hp:tc name="" header="{1 if row == 0 else 0}" hasMargin="0" protect="0" editable="0" '
        f'dirty="0" borderFillIDRef="{bf}">'
        f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
        f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" '
        f'hasNumRef="0">'
        f'{body}'
        f'</hp:subList>'
        f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
        f'<hp:cellSpan colSpan="{colspan}" rowSpan="{rowspan}"/>'
        f'<hp:cellSz width="{width}" height="{height}"/>'
        f'<hp:cellMargin left="0" right="0" top="0" bottom="0"/>'
        f'</hp:tc>'
    )


def _table_label(caption: str) -> str:
    """캡션 '표 1. 제목' → '<표1> 제목' (번호 없으면 '<표> 제목'). 발주처 지적(2026-10-02): '<표> 표 1.' 중복."""
    m = re.match(r"^표\s*([\d.]+?)\.?\s+(.*)$", caption)
    return f"<표{m.group(1)}> {m.group(2)}" if m else f"<표> {caption}"


def _figure_label(caption: str) -> str:
    """캡션 '그림 1. 제목' → '[그림1] 제목' (번호 없으면 '[그림] 제목'). 표의 '<표> 표 1.' 중복 수정과 같은 규칙."""
    m = re.match(r"^그림\s*([\d.]+?)\.?\s+(.*)$", caption)
    return f"[그림{m.group(1)}] {m.group(2)}" if m else f"[그림] {caption}"


def pick_table_format(rows: list[list[str]]) -> str:
    """칸 글이 문장형이면 세로 묶음("A"), 아니면 가로 행렬("matrix").

    기준은 표시 폭(_disp_len)이 아니라 글자 수 — 묻는 것이 "문장형이냐"라서다. 1열은 대상 라벨이라 뺀다.
    ponytail: A/B 는 행 대상이 비교 대상(나라·제품)이냐 개념(리스크·단계)이냐로 갈리는데 그건 의미
    판정이라 코드가 모른다(속성 수·1열 중복으로는 실사례에서 맞지 않았다). 그래서 자동은 A 까지만 하고,
    B 는 원고의 `{형식=B}` 로 지정한다. 명시 표시는 항상 이 판정을 덮어쓴다.
    """
    ncol = max(len(r) for r in rows)
    longest = max((len(c) for r in rows[1:] for c in r[1:]), default=0)
    if ncol <= 3 or longest < 25:                 # 16~24자 구간도 matrix (이미 좁지 않다)
        return "matrix"
    return "A"


def _split_items(text: str) -> list[str]:
    """쉼표로 이은 항목을 나눈다. 괄호 안 쉼표("심사 80일(보완 포함, 1회)")는 자르지 않는다."""
    out, depth, start = [], 0, 0
    for i, c in enumerate(text):
        depth = max(0, depth + (c in "(（[") - (c in ")）]"))   # 짝 없는 `1)` 이 음수로 새지 않게
        if c == "," and depth <= 0 and text[i + 1:i + 2] == " ":
            out.append(text[start:i].strip())
            start = i + 2
    out.append(text[start:].strip())
    return [t for t in out if t] or ["-"]


def _grouped_rows(rows: list[list[str]], fmt: str) -> list[tuple[str, list[tuple[str, list[str]]]]]:
    """가로 행렬 → [(대상, [(속성명, [문단...]), ...])].

    A 는 속성마다 한 행(속성명이 가운데 열). B 는 속성명이 칸 안 "(속성명) " 접두로 들어가
    대상당 한 행뿐이라 항목이 ("", 전 문단) 하나다. 머리행 칸이 비어도 데이터는 버리지 않는다 —
    속성명을 "" 로 두고 열을 살린다(이웃 머리글을 물려 쓰는 건 작성자 의도 추측이라 하지 않는다).
    """
    head = rows[0]
    out = []
    for r in rows[1:]:
        items = []
        for ci in range(1, len(head)):
            val = r[ci].strip() if ci < len(r) else ""
            items.append((head[ci], _split_items(val) if val not in ("", "-") else ["-"]))
        if fmt == "B":
            items = [("", [f"({a}) {t}" if a.strip() else t for a, ps in items for t in ps])]
        out.append((r[0], items or [("", ["-"])]))      # 속성 열이 없어도 본문 행을 잃지 않는다
    return out


def _grouped_trs(rows: list[list[str]], fmt: str) -> tuple[list[str], int, int, int]:
    """세로 묶음 표의 <hp:tr> 목록. (trs, 열 수, 본문 행 수, 어림 높이) 를 돌려준다.

    rowSpan>1 셀은 첫 행에만 쓰고, 병합에 먹히는 아래 행은 그 자리 <hp:tc> 를 아예 쓰지 않는다.
    colAddr/rowAddr 는 병합 전 격자 좌표다.
    """
    ratio = GROUP_RATIO[fmt]
    widths = [TBL_W * r // sum(ratio) for r in ratio]
    widths[-1] += TBL_W - sum(widths)                       # 반올림 오차는 끝 열이 흡수
    ncol = len(widths)
    last = ncol - 1
    avail = widths[last] - IN_MARGIN

    def lines(ps: list[str]) -> int:
        return sum(max(1, -(-_disp_len(t) * COL_UNIT // avail)) for t in ps)

    # 머리행: 대상 열 제목 + "세부 내용"(A 는 속성명 열까지 2열 병합)
    trs = ["<hp:tr>" + cell(rows[0][0], TH, BF_TH["first"], 0, 0, widths[0], 1467)
           + cell("세부 내용", TH, BF_TH["last"], 1, 0, sum(widths[1:]), 1467, colspan=ncol - 1)
           + "</hp:tr>"]
    h, ri = TH_LINE + CELL_VPAD, 1
    for target, items in _grouped_rows(rows, fmt):
        n = len(items)
        for j, (attr, paras) in enumerate(items):
            tcs = []
            # ponytail: rowSpan 셀은 한글이 쪽 경계에서 나눌 수 없어 대상 묶음째 다음 쪽으로 밀리고,
            # 앞 쪽 하단에 공백이 날 수 있다. 확인은 한글에서 긴 표를 직접 열어 보는 수밖에 없다.
            if j == 0:
                tcs.append(cell(target, TD, BF_TD["first"], 0, ri, widths[0], 800 * n, rowspan=n))
            if fmt == "A":
                tcs.append(cell(attr, TD, BF_TD["mid"], 1, ri, widths[1], 800))
            tcs.append(cell(paras, TD, BF_TD["last"], last, ri, widths[last], 800))
            trs.append("<hp:tr>" + "".join(tcs) + "</hp:tr>")
            h += lines(paras) * TD_LINE + CELL_VPAD
            ri += 1
    return trs, ncol, ri, h


def render_table(b: dict) -> str:
    rows = b["rows"]
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    fmt = b.get("fmt") or pick_table_format(rows)
    if fmt == "matrix":
        h = (len(rows) + (1 if b["src"] else 0)) * 900      # 선언 높이 (기존 값)
        widths = col_widths(rows, ncol)
        nbody = len(rows)
        tall = est_height(rows, widths, bool(b["src"])) > PAGE_H

        trs = []
        for ri, r in enumerate(rows):
            tcs = []
            for ci, txt in enumerate(r):
                pos = "first" if ci == 0 else ("last" if ci == ncol - 1 else "mid")
                if ri == 0:
                    tcs.append(cell(txt, TH, BF_TH[pos], ci, ri, widths[ci], 1467))
                else:
                    tcs.append(cell(txt, TD, BF_TD[pos], ci, ri, widths[ci], 800))
            trs.append("<hp:tr>" + "".join(tcs) + "</hp:tr>")
    else:
        for ci, name in enumerate(rows[0][1:], 2):
            if not name.strip():
                print(f"  ! 표 '{b['caption']}' 머리행 {ci}번째 열이 비어 속성명 없이 그립니다", file=sys.stderr)
        trs, ncol, nbody, h = _grouped_trs(rows, fmt)
        # 세로 묶음 표는 거의 한 쪽을 넘는다 — 새 행·문단 수로 다시 어림해 쪽 넘김을 맞춘다
        h += TD_LINE + CELL_VPAD if b["src"] else 0
        tall = h > PAGE_H
    nrow = nbody + (1 if b["src"] else 0)

    if b["src"]:
        trs.append("<hp:tr>" + cell(b["src"], TSRC, BF_SRC, 0, nbody, TBL_W, 500,
                                    colspan=ncol) + "</hp:tr>")

    caption = ""
    if b["caption"]:
        cid, pid = CAPTION
        caption = (
            f'<hp:caption side="TOP" fullSz="0" width="8504" gap="850" lastWidth="{TBL_W}">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" '
            f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" '
            f'hasNumRef="0">'
            f'<hp:p id="0" paraPrIDRef="{pid}" styleIDRef="0" pageBreak="0" columnBreak="0" '
            f'merged="0">{runs(_table_label(b["caption"]), cid)}</hp:p>'
            f'</hp:subList></hp:caption>'
        )

    tbl = (
        f'<hp:tbl id="{uid()}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
        f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
        f'rowCnt="{nrow}" colCnt="{ncol}" cellSpacing="0" borderFillIDRef="{BF_TBL}" noAdjust="1">'
        f'<hp:sz width="{TBL_W}" widthRelTo="ABSOLUTE" height="{h}" '
        f'heightRelTo="ABSOLUTE" protect="0"/>'
        # 글자처럼 취급된(treatAsChar=1) 표는 쪽 경계에서 나뉘지 않는다. 한 쪽에 들어가는 표는
        # 작년 완성본대로 1 로 두고, 한 쪽을 넘는 표만 0 으로 풀어 쪽을 걸쳐 이어지게 한다
        # (1 로 두면 들어갈 자리가 영영 없어 통째로 밀린다). 작년본 실측: 38건 중 33건이 1.
        f'<hp:pos treatAsChar="{0 if (tall or os.environ.get("HWPX_TABLE_FLOAT_ALL")) else 1}" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" '
        f'horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="141" right="141" top="141" bottom="141"/>'
        f'{caption}'
        f'<hp:inMargin left="510" right="510" top="141" bottom="141"/>'
        f'{"".join(trs)}'
        f'</hp:tbl>'
    )
    return (f'<hp:p id="0" paraPrIDRef="{PARA_CENTER}" styleIDRef="0" pageBreak="0" '
            f'columnBreak="0" merged="0"><hp:run charPrIDRef="{TD[0]}">{tbl}</hp:run></hp:p>')


# ── 4. 그림 ──────────────────────────────────────────────────────────────
def render_image(b: dict, bin_id: str) -> str:
    px_w, px_h = b["_px"]
    w = PAGE_W
    h = int(w * px_h / px_w)
    if h > IMG_MAX_H:                                       # 세로로 긴 그림은 높이 기준으로 맞춘다
        h = IMG_MAX_H
        w = int(h * px_w / px_h)
    # 원본 이미지 좌표계(HWPUNIT). 한글은 imgClip 을 표시 크기가 아니라 이 좌표로 읽는다 —
    # 여기에 표시 폭(48188)을 넣으면 원본의 그 만큼만 잘라 쓰고 프레임에 늘려 그려서 확대·크롭된다.
    org_w, org_h = px_w * PX2HWP, px_h * PX2HWP

    caption = ""
    if b["caption"] or b["alt"]:
        cid, pid = CAPTION
        txt = b["caption"] or b["alt"]
        caption = (
            f'<hp:caption side="BOTTOM" fullSz="0" width="8504" gap="850" lastWidth="{w}">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" '
            f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" '
            f'hasNumRef="0">'
            f'<hp:p id="0" paraPrIDRef="{pid}" styleIDRef="0" pageBreak="0" columnBreak="0" '
            f'merged="0">{runs(_figure_label(txt), cid)}</hp:p>'
            f'</hp:subList></hp:caption>'
        )

    pic = (
        f'<hp:pic id="{uid()}" zOrder="0" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" '
        f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" '
        f'instid="{uid()}" reverse="0">'
        f'<hp:offset x="0" y="0"/>'
        f'<hp:orgSz width="{org_w}" height="{org_h}"/>'
        f'<hp:curSz width="{w}" height="{h}"/>'
        f'<hp:flip horizontal="0" vertical="0"/>'
        f'<hp:rotationInfo angle="0" centerX="{w // 2}" centerY="{h // 2}" rotateimage="1"/>'
        f'<hp:renderingInfo>'
        f'<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        f'<hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        f'<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        f'</hp:renderingInfo>'
        f'<hc:img binaryItemIDRef="{bin_id}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
        f'<hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="{org_w}" y="0"/>'
        f'<hc:pt2 x="{org_w}" y="{org_h}"/><hc:pt3 x="0" y="{org_h}"/></hp:imgRect>'
        f'<hp:imgClip left="0" right="{org_w}" top="0" bottom="{org_h}"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        f'<hp:sz width="{w}" widthRelTo="ABSOLUTE" height="{h}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" '
        f'vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        f'{caption}'
        f'</hp:pic>'
    )
    return (f'<hp:p id="0" paraPrIDRef="{PARA_CENTER}" styleIDRef="0" pageBreak="0" '
            f'columnBreak="0" merged="0"><hp:run charPrIDRef="{BODY1[0]}">{pic}</hp:run></hp:p>')


# ── 5. header.xml 보강 (양식 원본 ID 는 건드리지 않고 뒤에 덧붙인다) ────────
def patch_header(header: str) -> str:
    global BODY_BOLD
    # 본문 굵게 charPr — 양식엔 12pt 굵게가 없다. body_bold_base 를 복제해 <hh:bold/> 만 넣는다.
    # 새 ID 는 header 의 itemCnt (0..itemCnt-1 다음 번호). 200 고정은 다른 양식에서 충돌한다.
    cnt = int(re.search(r'<hh:charProperties itemCnt="(\d+)"', header).group(1))
    BODY_BOLD = cnt
    base = re.search(
        rf'<hh:charPr id="{BODY_BOLD_BASE}".*?</hh:charPr>', header, re.S
    ).group(0)
    bold = (base.replace(f'id="{BODY_BOLD_BASE}"', f'id="{BODY_BOLD}"', 1)
                .replace("<hh:underline", "<hh:bold/><hh:underline", 1))
    header = header.replace("</hh:charProperties>", bold + "</hh:charProperties>", 1)
    header = header.replace(f'<hh:charProperties itemCnt="{cnt}"',
                            f'<hh:charProperties itemCnt="{cnt + 1}"', 1)

    # 셀 안 왼쪽정렬 + '-' 글머리 문단 — 양식엔 없다(셀 문단은 전부 가운데 정렬). 셀 본문 문단(TD)을
    # 복제해 정렬·글머리만 바꾼다. 글머리 문자 '-' 는 양식에 이미 정의돼 있어 그 ID 를 찾아 쓴다.
    global CELL_BULLET
    pcnt = int(re.search(r'<hh:paraProperties itemCnt="(\d+)"', header).group(1))
    CELL_BULLET = pcnt
    bullet = re.search(r'<hh:bullet id="(\d+)" char="-"', header)
    if not bullet:                                          # 모르는 양식에 글머리를 조용히 꽂지 않는다
        raise ValueError("양식 header.xml 에 글머리 문자 '-' 의 <hh:bullet> 정의가 없습니다")
    bullet_id = int(bullet.group(1))
    pbase = re.search(rf'<hh:paraPr id="{TD[1]}".*?</hh:paraPr>', header, re.S).group(0)
    # 여백·들여쓰기는 전부 0 그대로(사용자 최종본 실측) — '-' 가 칸 왼쪽 끝에서 시작하고 줄 간격 160% 는 TD 원본 값
    cellp = (pbase.replace(f'id="{TD[1]}"', f'id="{CELL_BULLET}"', 1)
                  .replace('<hh:align horizontal="CENTER"', '<hh:align horizontal="LEFT"', 1)
                  .replace('<hh:heading type="NONE" idRef="0"',
                           f'<hh:heading type="BULLET" idRef="{bullet_id}"', 1))
    header = header.replace("</hh:paraProperties>", cellp + "</hh:paraProperties>", 1)
    header = header.replace(f'<hh:paraProperties itemCnt="{pcnt}"',
                            f'<hh:paraProperties itemCnt="{pcnt + 1}"', 1)
    return header


# ── 6. 조립 ──────────────────────────────────────────────────────────────
def build(md_path: Path, out_path: Path, template: Path | None = None) -> dict:
    """원고 md 를 양식 템플릿에 채워 HWPX 로 쓴다. 반환 dict 가 stdout JSON 과 같다."""
    if not PROFILE:
        load_profile()
    if template is None:
        raise ValueError("template 경로가 필요합니다")
    md_path = Path(md_path)
    out_path = Path(out_path)
    template = Path(template)
    blocks = parse_md(md_path.read_text(encoding="utf-8"))

    with zipfile.ZipFile(template) as z:
        tpl = {n: z.read(n) for n in z.namelist()}
    header = patch_header(tpl["Contents/header.xml"].decode("utf-8"))

    # 그림 실물을 확보하고 BinData 이름을 배정한다
    images: list[tuple[str, Path]] = []
    skipped: list[str] = []
    for b in blocks:
        if b["t"] != "image":
            continue
        p = (md_path.parent / b["src"]).resolve()
        if not p.exists():
            print(f"  ! 그림 없음, 건너뜀: {b['src']}")
            skipped.append(b["src"])
            b["t"] = "skip"
            continue
        with Image.open(p) as im:
            b["_px"] = im.size
        bin_id = f"image{len(images) + 1}"
        b["_bin"] = bin_id
        images.append((bin_id, p))

    body = []
    for b in blocks:
        t = b["t"]
        if t == "title":
            body.append(para(b["text"], TITLE))
        elif t == "h1":
            body.append(para(b["text"], H1))
        elif t == "h2":
            body.append(para(b["text"], H2))
        elif t == "h3":
            body.append(para(b["text"], H3))
        elif t == "body1":
            body.append(para(b["text"], BODY1, BODY_BOLD))
        elif t == "body2":
            body.append(para(b["text"], BODY2, BODY_BOLD))
        elif t == "note":
            body.append(para(b["text"], (TSRC[0], CAPTION[1])))
        elif t == "footnote":
            body.append(para(b["text"], (TSRC[0], TSRC[1])))
        elif t == "table":
            body.append(render_table(b))
        elif t == "image":
            body.append(render_image(b, b["_bin"]))

    # 양식의 판형 설정(secPr)을 첫 문단에 그대로 이식한다 — 여백·용지가 곧 양식이다.
    tpl_sec = tpl["Contents/section0.xml"].decode("utf-8")
    secpr = re.search(r"<hp:secPr .*?</hp:secPr>", tpl_sec, re.S).group(0)
    colpr = '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/></hp:ctrl>'
    head = re.match(r'<\?xml.*?<hs:sec[^>]*>', tpl_sec, re.S).group(0)
    first = body[0] if body else para("", BODY1)
    first = first.replace(f'<hp:run charPrIDRef=', f'<hp:run charPrIDRef="{TITLE[0]}">{secpr}{colpr}</hp:run><hp:run charPrIDRef=', 1)
    section = head + first + "".join(body[1:]) + "</hs:sec>"

    # content.hpf 의 그림 등록부 교체 (양식의 image1 은 예시라 버린다)
    hpf = tpl["Contents/content.hpf"].decode("utf-8")
    # 속성값에 '/' 가 있으므로([^/]* 는 href=BinData/… 에서 막힌다) [^>]* 로 항목 끝까지 먹는다
    hpf = re.sub(r'<opf:item id="image\d+"[^>]*/>', "", hpf)
    items = ""
    for bin_id, p in images:
        mt = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else f"image/{p.suffix.lower().lstrip('.')}"
        key = base64.b64encode(hashlib.md5(p.read_bytes()).digest()).decode()
        items += (f'<opf:item id="{bin_id}" href="BinData/{bin_id}{p.suffix.upper()}" '
                  f'media-type="{mt}" isEmbeded="1" hashkey="{key}"/>')
    hpf = hpf.replace('<opf:item id="section0"', items + '<opf:item id="section0"', 1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", tpl["mimetype"], zipfile.ZIP_STORED)
        for name, data in tpl.items():
            if name in ("mimetype", "Contents/header.xml", "Contents/section0.xml",
                        "Contents/content.hpf") or name.startswith("BinData/"):
                continue
            z.writestr(name, data)
        z.writestr("Contents/header.xml", header.encode("utf-8"))
        z.writestr("Contents/section0.xml", section.encode("utf-8"))
        z.writestr("Contents/content.hpf", hpf.encode("utf-8"))
        for bin_id, p in images:
            z.writestr(f"BinData/{bin_id}{p.suffix.upper()}", p.read_bytes())

    kinds: dict[str, int] = {}
    for b in blocks:
        kinds[b["t"]] = kinds.get(b["t"], 0) + 1
    print(f"  {out_path.name}  {out_path.stat().st_size:,}B  {kinds}")
    return {
        "ok": True,
        "out": str(out_path.resolve()),
        "blocks": kinds,
        "images": len(images),
        "skipped_images": skipped,
    }


# ── 7. split / outline ───────────────────────────────────────────────────
def _safe_title(title: str) -> str:
    """파일명용 — 공백·/·: 를 제거한다."""
    return re.sub(r"[\s/:]+", "", title)


def _rewrite_rel_links(text: str) -> str:
    """`](` 뒤가 http·/·.. 로 시작하지 않는 상대경로 앞에 ../ 를 붙인다."""
    def repl(m: re.Match) -> str:
        url = m.group(1)
        if url.startswith(("http", "/", "..")):
            return m.group(0)
        return f"](../{url})"
    return re.sub(r"\]\(([^)]*)\)", repl, text)


def _is_subdir(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return child.resolve() != parent.resolve()
    except ValueError:
        return False


def _promote_headings(lines: list[str]) -> list[str]:
    """## 부 제목으로 잘린 모듈의 제목을 한 단계 올려 원고 문법과 맞춘다."""
    out: list[str] = []
    for line in lines:
        m = HEADING_PROMOTE_RE.match(line)
        out.append((m.group(1)[1:] + m.group(2)) if m else line)
    return out


def split_report(md_path: Path, out_dir: Path, expect_parts: int | None = None) -> list[Path]:
    """로마숫자 부 수를 검증한 뒤 분할한다. 서문은 기대 부 수에 포함하지 않는다."""
    md_path = Path(md_path)
    out_dir = Path(out_dir)
    text = md_path.read_text(encoding="utf-8")
    nested = _is_subdir(out_dir, md_path.parent)

    parts: list[tuple[str | None, str, list[str], bool]] = []
    key: str | None = None
    title = ""
    buf: list[str] = []
    promote = False
    for line in text.splitlines():
        m = CHAPTER_RE.match(line)
        if m:
            parts.append((key, title, buf, promote))
            hashes, key, title = m.group(1), m.group(2), m.group(3)
            buf = [line]
            promote = hashes == "##"
        else:
            buf.append(line)
    parts.append((key, title, buf, promote))

    chapters = [part for part in parts if part[0] is not None]
    if not chapters:
        raise ValueError("로마숫자 부 헤딩 0개: mdr-hwpx/SKILL.md의 코어 11부 목차 → "
                         "로마숫자 부 변환 절차를 따라 # Ⅰ. 제목 ~ # Ⅺ. 부록으로 매핑하세요.")
    if expect_parts is not None and (expect_parts < 1 or len(chapters) != expect_parts):
        raise ValueError(f"부 수 불일치: 기대 {expect_parts}, 실제 {len(chapters)} (서문 제외)")
    names = [f"{part[0]}_{_safe_title(part[1])}.md" for part in chapters]
    if len(names) != len(set(names)):
        raise ValueError("분할 파일명 중복: 부 번호·제목을 확인하세요")
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for key, title, buf, promote in parts:
        if promote:
            buf = _promote_headings(buf)
        body = "\n".join(buf)
        if body and not body.endswith("\n"):
            body += "\n"
        if nested:
            body = _rewrite_rel_links(body)
        if key is None:
            if not body.strip():
                continue
            name = "00_서문.md"
        else:
            name = f"{key}_{_safe_title(title)}.md"
        dest = out_dir / name
        dest.write_text(body, encoding="utf-8")
        written.append(dest)
    return written


def outline_md(md_path: Path) -> dict:
    """모듈 하나에서 제목 트리·표/그림 캡션·출처·각주·단락 수를 뽑는다."""
    md_path = Path(md_path)
    blocks = parse_md(md_path.read_text(encoding="utf-8"))
    level_of = {"title": 1, "h1": 2, "h2": 3, "h3": 4}
    titles = [{"level": level_of[b["t"]], "text": b["text"]}
              for b in blocks if b["t"] in level_of]
    table_blocks = [b for b in blocks if b["t"] == "table"]
    tables = [(b.get("caption") or "(캡션 없음)") for b in table_blocks]
    figures = [b["caption"] or b.get("alt", "") for b in blocks if b["t"] == "image"]
    figures = [c for c in figures if c]
    n_src = sum(1 for b in blocks if b["t"] == "table" and b.get("src"))
    n_src += sum(1 for b in blocks if b["t"] == "note")
    n_fn = sum(1 for b in blocks if b["t"] == "footnote")
    n_para = sum(1 for b in blocks if b["t"] in ("body1", "body2", "note", "footnote"))
    return {
        "file": str(md_path),
        "titles": titles,
        "tables": tables,
        "tables_total": len(table_blocks),
        "figures": figures,
        "sources": n_src,
        "footnotes": n_fn,
        "paragraphs": n_para,
    }


def format_outline(info: dict) -> str:
    lines = [f"# {Path(info['file']).name}", "", "제목"]
    lines.append("| 레벨 | 텍스트 |")
    lines.append("|---|---|")
    for t in info["titles"]:
        lines.append(f"| {t['level']} | {t['text']} |")
    lines += ["", "<표>"]
    if info["tables"]:
        for i, cap in enumerate(info["tables"], 1):
            lines.append(f"{i}. {cap}")
    else:
        lines.append("(없음)")
    lines += ["", "[그림]"]
    if info["figures"]:
        for i, cap in enumerate(info["figures"], 1):
            lines.append(f"{i}. {cap}")
    else:
        lines.append("(없음)")
    lines += [
        "",
        f"출처 {info['sources']}  각주 정의 {info['footnotes']}  단락 {info['paragraphs']}",
        "",
    ]
    return "\n".join(lines)


def demo() -> None:
    """의존성 없이 도는 자체 점검 — 파싱과 열폭 배분이 깨지면 여기서 걸린다."""
    prof = load_profile("navion-2026")
    assert prof["name"] == "navion-2026"
    assert tuple(prof["styles"]["title"]) == TITLE == (23, 46)
    assert prof["page"]["tbl_w"] == TBL_W == 48178
    assert prof["table"]["min_col"] == MIN_COL == 3300
    assert BODY_BOLD_BASE == 29
    md = (
        "# Ⅴ. 결론\n\n## 1. 개요\n\n### (1) 세부\n\n① 공급사\n\n"
        "(전년판 요약) 개요 문단\n\n❍ (정화) 본문 **굵게** 와 각주<sup>1)</sup>\n\n"
        "- 하위 근거\n\n"
        "① 1단계, 프로젝트 설계 : 설명이 길게 붙은 원 숫자는 제목이 아니라 본문이어야 한다\n\n"
        "<sup>1)</sup> 각주 정의 문단\n\n"
        "<표> 표 제목\n\n| A | 나나나 |\n|---|---|\n| 1 | 2 |\n\n"
        "* 출처 : 어딘가\n\n![대체글](../assets/없는파일.png)\n\n[그림] 그림 제목\n"
    )
    b = parse_md(md)
    got = [x["t"] for x in b]
    assert got == ["title", "h1", "h2", "h3", "body1", "body1", "body2",
                   "body1", "footnote", "table", "image"], got
    assert b[3]["text"].startswith("①") and b[7]["text"].startswith("① 1단계")  # 짧은 ①만 제목
    assert b[8]["text"].startswith("1) 각주")
    assert b[9]["caption"] == "표 제목" and b[9]["src"] == "* 출처 : 어딘가"
    assert b[9]["rows"] == [["A", "나나나"], ["1", "2"]], b[9]["rows"]   # 구분행 제거
    assert b[10]["caption"] == "그림 제목"
    w = col_widths(b[9]["rows"], 2)
    assert sum(w) == TBL_W and all(x >= MIN_COL for x in w), w
    # 서술이 긴 셀이 섞여도 짧은 머리글 열이 최소폭 아래로 눌리지 않는다
    wide = col_widths([["구분", "내용"], ["가", "설" * 200]], 2)
    assert sum(wide) == TBL_W and wide[0] >= MIN_COL, wide
    many = col_widths([["가"] * 20], 20)                                 # 열이 최소폭×n 을 넘길 때
    assert sum(many) == TBL_W and min(many) > 0, many
    # 라벨 열은 통째로 한 줄, 서술 열은 낱말이 안 잘릴 만큼은 확보한다
    lab = col_widths([["구분", "기관"], ["정책 입안", "에너지다변화절약연구소(IDAE)"]], 2)
    assert lab[0] >= _disp_len("정책 입안") * COL_UNIT + IN_MARGIN, lab
    assert lab[1] >= _disp_len("에너지다변화절약연구소(IDAE)") * COL_UNIT + IN_MARGIN, lab
    assert sum(lab) == TBL_W, lab
    # 한 쪽에 들어가는 표와 넘는 표를 갈라 본다 — 넘는 표만 글자처럼 취급을 푼다
    small = [["구분", "내용"]] + [["가", "나"]] * 5
    assert est_height(small, col_widths(small, 2), False) <= PAGE_H
    big = [["구분", "내용"]] + [["가", "나"]] * 60
    assert est_height(big, col_widths(big, 2), False) > PAGE_H
    tall_xml = render_table({"rows": big, "caption": "", "src": ""})
    assert 'treatAsChar="0"' in tall_xml and 'pageBreak="CELL"' in tall_xml
    assert 'treatAsChar="1"' in render_table({"rows": small, "caption": "", "src": ""})
    r = runs("본문 **굵게** 와 <sup>1)</sup>", BODY1[0], BODY_BOLD)
    assert f'charPrIDRef="{BODY_BOLD}"' in r and "<sup>" not in r and "1)" in r
    assert "&amp;" in runs("A & B", 1)                                   # XML 이스케이프
    # 하위 폴더 분할 시 상대 그림 경로 보정
    got_rw = _rewrite_rel_links(
        "![a](assets/x.png) ![b](_captures/y.png) ![c](http://h/z) ![d](/abs) ![e](../keep)"
    )
    assert got_rw == (
        "![a](../assets/x.png) ![b](../_captures/y.png) ![c](http://h/z) ![d](/abs) ![e](../keep)"
    ), got_rw
    # ## 부 제목은 한 단계 승격해 원고 문법(# 부 / ## 1단계)과 같게
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        src = td_p / "report.md"
        src.write_text("## Ⅱ. 가\n### 1. 나\n", encoding="utf-8")
        split_report(src, td_p / "out")
        plines = (td_p / "out" / "Ⅱ_가.md").read_text(encoding="utf-8").splitlines()
        assert plines[0] == "# Ⅱ. 가", plines[:3]
        assert plines[1] == "## 1. 나", plines[:3]
        bare = td_p / "bare.md"
        bare.write_text("| A | B |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
        info = outline_md(bare)
        assert info["tables_total"] == 1, info
        assert info["tables"] == ["(캡션 없음)"], info
    _demo_grouped_tables()
    print("demo ok")


def _check_grid(xml: str) -> None:
    """rowCnt×colCnt 격자가 <hp:tc> 로 빈틈·겹침 없이 덮이는지 — 병합으로 생략된 셀까지 감안한다."""
    rc, cc = (int(x) for x in re.search(r'rowCnt="(\d+)" colCnt="(\d+)"', xml).groups())
    trs = re.findall(r"<hp:tr>(.*?)</hp:tr>", xml, re.S)
    assert len(trs) == rc, (len(trs), rc)
    seen = set()
    for ti, tr in enumerate(trs):
        for ca, ra, cs, rs in re.findall(
                r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"/><hp:cellSpan colSpan="(\d+)" '
                r'rowSpan="(\d+)"/>', tr):
            ca, ra, cs, rs = int(ca), int(ra), int(cs), int(rs)
            assert ra == ti, (ra, ti)                       # tc 는 자기 시작 행의 tr 안에 있다
            for r in range(ra, ra + rs):
                for c in range(ca, ca + cs):
                    assert (r, c) not in seen, ("겹침", r, c)
                    seen.add((r, c))
    assert seen == {(r, c) for r in range(rc) for c in range(cc)}, "격자 빈틈"


def _demo_grouped_tables() -> None:
    """세로 묶음 표(A/B) 자체 점검 — 형식 판정·명시 표시·병합 좌표·쉼표 분리."""
    tpl = SKILL_ROOT / "assets" / "forms" / "navion-2026.hwpx"
    if not tpl.exists():                                    # 양식이 없으면 글머리 ID 를 알 수 없다
        return
    with zipfile.ZipFile(tpl) as z:                         # 글머리 문단이 header 에 실제로 생기는지
        hdr0 = z.read("Contents/header.xml").decode("utf-8")
    hdr = patch_header(hdr0)
    n0 = int(re.search(r'<hh:paraProperties itemCnt="(\d+)"', hdr0).group(1))
    assert CELL_BULLET == n0, (CELL_BULLET, n0)
    assert f'<hh:paraProperties itemCnt="{n0 + 1}"' in hdr
    pp = re.search(rf'<hh:paraPr id="{CELL_BULLET}".*?</hh:paraPr>', hdr, re.S).group(0)
    assert 'horizontal="LEFT"' in pp and 'type="BULLET"' in pp, pp[:200]
    short = [["구분", "값"], ["가", "1"], ["나", "2"]]
    assert pick_table_format(short) == "matrix"
    four = [["지역", "경로", "예상 기간", "선행 조건"],
            ["가 지역", "인증 취득 후 등록해야 하며 절차가 길다", "심사 80일(보완 포함, 1회), 현장 실사 및 사후 점검", "제조업 등록, 시험 성적서"],
            ["나 지역", "사전 신고", "심사 2~3개월", "현지 대리인 지정"]]
    assert pick_table_format(four) == "A"                   # 속성 3개
    five = [r + ["비고 항목이 문장형으로 길게 적힌다"] for r in four]
    five[0][-1] = "비고"
    assert pick_table_format(five) == "A"                   # 속성 수로 B 를 고르지 않는다
    assert pick_table_format([r[:3] for r in four]) == "matrix"     # 열 3 이하
    # 괄호 안 쉼표는 자르지 않고, 빈 값은 "-"
    assert _split_items("심사 80일(보완 포함, 1회), 현장 실사") == ["심사 80일(보완 포함, 1회)", "현장 실사"]
    assert _grouped_rows([["지역", "경로"], ["가", ""]], "A") == [("가", [("경로", ["-"])])]
    # 명시 표시가 자동 판정을 덮어쓰고 캡션엔 남지 않는다
    blk = parse_md("<표> 표 11. 지역별 진입 경로 {형식=B}\n\n| 지역 | 경로 | 기간 | 조건 |\n"
                   "|---|---|---|---|\n| 가 | 1 | 2 | 3 |\n")[0]
    assert blk["fmt"] == "B" and "{형식" not in blk["caption"] and blk["caption"] == "표 11. 지역별 진입 경로"
    xml_b = render_table(blk)
    assert 'colCnt="2"' in xml_b and "{형식" not in xml_b
    # A: 열 3, rowSpan 합 = 대상별 속성 수 합, 격자 일관
    xml_a = render_table({"rows": four, "caption": "표 1. 진입", "src": "* 출처 : x", "fmt": ""})
    assert 'colCnt="3"' in xml_a and "{형식" not in xml_a
    spans = [int(x) for x in re.findall(r'<hp:cellAddr colAddr="0" rowAddr="[1-9]\d*"/>'
                                        r'<hp:cellSpan colSpan="1" rowSpan="(\d+)"', xml_a)]
    assert sum(spans) == 3 * 2, spans                       # 대상 2 × 속성 3
    assert "심사 80일(보완 포함, 1회)" in xml_a and xml_a.count(f'paraPrIDRef="{CELL_BULLET}"') == \
        sum(len(ps) for _, its in _grouped_rows(four, "A") for _, ps in its)
    _check_grid(xml_a)
    _check_grid(xml_b)
    _check_grid(render_table({"rows": five, "caption": "", "src": "", "fmt": "B"}))
    # 경계 케이스: 머리행 속성 칸이 전부 빔 / 하나만 빔 — 빈 subList 없이 본문 행·데이터 보존
    for f in ("A", "B"):
        x = render_table({"rows": [["구분", "", ""], ["가", "x1", "x2"]], "caption": "", "src": "", "fmt": f})
        assert "<hp:subList" in x and "<hp:p " in x and "x1" in x and "x2" in x, f
        assert re.search(r"<hp:subList[^>]*></hp:subList>", x) is None, f
        _check_grid(x)
        x = render_table({"rows": [["구분", "경로", ""], ["가", "x1", "x2"]], "caption": "", "src": "", "fmt": f})
        assert "x1" in x and "x2" in x, f
        _check_grid(x)
    x = render_table({"rows": [["구분"], ["가"]], "caption": "", "src": "", "fmt": "A"})
    assert x.count("<hp:tr>") == 2 and "<hp:p " in x           # 속성 열이 없어도 본문 행 생존
    _check_grid(x)
    assert _split_items("1) 가(ㄱ, ㄴ)") == ["1) 가(ㄱ, ㄴ)"]    # 짝 없는 닫는 괄호
    for mark in ("b", "C", "세로"):
        blk = parse_md(f"<표> 표 1. ㄱ {{형식={mark}}}\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")[0]
        assert "{형식" not in blk["caption"], blk["caption"]
        assert blk["fmt"] == ("B" if mark == "b" else ""), (mark, blk["fmt"])
    # 긴 세로 묶음 표는 쪽을 걸쳐 이어지게 풀린다
    long_rows = [four[0]] + [[f"대상{i}"] + four[1][1:] for i in range(40)]
    assert 'treatAsChar="0"' in render_table({"rows": long_rows, "caption": "", "src": "", "fmt": "A"})


def _cmd_build(args: argparse.Namespace) -> int:
    load_profile(args.profile)
    md = Path(args.md)
    if not md.exists():
        print(f"원고 없음: {md}")
        return 1
    template = Path(args.template)
    if not template.exists():
        print(f"양식 없음: {template}")
        return 1
    out = Path(args.out) if args.out else md.with_name(f"모듈_{md.stem}_양식.hwpx")
    print(f"{md.name} →")
    result = build(md, out, template)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _cmd_split(args: argparse.Namespace) -> int:
    md = Path(args.md)
    if not md.exists():
        print(f"원고 없음: {md}")
        return 1
    try:
        written = split_report(md, Path(args.out), expect_parts=args.expect_parts)
    except ValueError as exc:
        print(f"분할 실패: {exc}", file=sys.stderr)
        return 1
    for p in written:
        first = p.read_text(encoding="utf-8").splitlines()[:1]
        print(f"{p.name}\t{first[0] if first else ''}")
    return 0


def _cmd_outline(args: argparse.Namespace) -> int:
    infos = []
    for raw in args.md:
        p = Path(raw)
        if not p.exists():
            print(f"원고 없음: {p}")
            return 1
        infos.append(outline_md(p))
    if args.json:
        print(json.dumps(infos if len(infos) > 1 else infos[0], ensure_ascii=False, indent=2))
    else:
        print("\n".join(format_outline(i) for i in infos).rstrip())
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--demo"]:
        demo()
        return 0
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="원고 md → 양식 HWPX")
    p_build.add_argument("md")
    p_build.add_argument("--template", required=True)
    p_build.add_argument("--profile", default="navion-2026")
    p_build.add_argument("--out")
    p_build.set_defaults(func=_cmd_build)

    p_split = sub.add_parser("split", help="report.md 를 로마숫자 부로 분할")
    p_split.add_argument("md")
    p_split.add_argument("--out", required=True)
    p_split.add_argument("--expect-parts", type=int, help="기대 로마숫자 부 수(서문 제외)")
    p_split.set_defaults(func=_cmd_split)

    p_outl = sub.add_parser("outline", help="제목 트리·표/그림 캡션 요약")
    p_outl.add_argument("md", nargs="+")
    p_outl.add_argument("--json", action="store_true")
    p_outl.set_defaults(func=_cmd_outline)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
