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
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
            pending_caption = s[3:].strip()

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
                blocks.append({"t": "table", "rows": rows, "caption": pending_caption or "", "src": ""})
                pending_caption = None

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


def cell(text: str, style: tuple[int, int], bf: int, col: int, row: int,
         width: int, height: int, colspan: int = 1) -> str:
    cid, pid = style
    return (
        f'<hp:tc name="" header="{1 if row == 0 else 0}" hasMargin="0" protect="0" editable="0" '
        f'dirty="0" borderFillIDRef="{bf}">'
        f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
        f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" '
        f'hasNumRef="0">'
        f'<hp:p id="0" paraPrIDRef="{pid}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'{runs(text, cid, TH[0] if style is TD else None)}</hp:p>'
        f'</hp:subList>'
        f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
        f'<hp:cellSpan colSpan="{colspan}" rowSpan="1"/>'
        f'<hp:cellSz width="{width}" height="{height}"/>'
        f'<hp:cellMargin left="0" right="0" top="0" bottom="0"/>'
        f'</hp:tc>'
    )


def render_table(b: dict) -> str:
    rows = b["rows"]
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    widths = col_widths(rows, ncol)
    nrow = len(rows) + (1 if b["src"] else 0)
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

    if b["src"]:
        trs.append("<hp:tr>" + cell(b["src"], TSRC, BF_SRC, 0, len(rows), TBL_W, 500,
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
            f'merged="0">{runs("<표> " + b["caption"], cid)}</hp:p>'
            f'</hp:subList></hp:caption>'
        )

    tbl = (
        f'<hp:tbl id="{uid()}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
        f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
        f'rowCnt="{nrow}" colCnt="{ncol}" cellSpacing="0" borderFillIDRef="{BF_TBL}" noAdjust="1">'
        f'<hp:sz width="{TBL_W}" widthRelTo="ABSOLUTE" height="{nrow * 900}" '
        f'heightRelTo="ABSOLUTE" protect="0"/>'
        # 글자처럼 취급된(treatAsChar=1) 표는 쪽 경계에서 나뉘지 않는다. 한 쪽에 들어가는 표는
        # 작년 완성본대로 1 로 두고, 한 쪽을 넘는 표만 0 으로 풀어 쪽을 걸쳐 이어지게 한다
        # (1 로 두면 들어갈 자리가 영영 없어 통째로 밀린다). 작년본 실측: 38건 중 33건이 1.
        f'<hp:pos treatAsChar="{0 if tall else 1}" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
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
            f'merged="0">{runs("[그림] " + txt, cid)}</hp:p>'
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
    print("demo ok")


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
