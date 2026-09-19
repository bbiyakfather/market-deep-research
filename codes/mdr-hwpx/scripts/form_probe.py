"""양식 HWPX 실측 — 판형과 본문이 쓰는 (paraPr, charPr) 조합.

표 내부 문단은 본문과 섞이므로 <hp:tbl>…</hp:tbl> 을 지우고 센다.
--profile 이 있으면 프로필이 가리키는 모든 charPr/paraPr/borderFill ID 가
header.xml 에 있는지 검사하고, 없으면 목록을 찍고 exit 1.

실행:
    python form_probe.py <양식.hwpx> [--profile navion-2026|<path.json>] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"
HWPUNIT_PER_MM = 7200 / 25.4


def _hwp_to_mm(v: int) -> str:
    mm = v / HWPUNIT_PER_MM
    if abs(mm - round(mm)) < 0.05:
        return f"{int(round(mm))} mm"
    return f"{mm:.1f} mm"


def load_profile_json(name_or_path: str) -> dict:
    raw = Path(name_or_path)
    if raw.is_file():
        path = raw
    else:
        path = PROFILES_DIR / f"{raw.stem}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def profile_ids(prof: dict) -> dict[str, set[int]]:
    """프로필이 참조하는 charPr / paraPr / borderFill ID 집합."""
    st = prof["styles"]
    char_ids: set[int] = set()
    para_ids: set[int] = set()
    for key in ("title", "h1", "h2", "h3", "body1", "body2", "caption", "th", "td", "tsrc"):
        char_ids.add(int(st[key][0]))
        para_ids.add(int(st[key][1]))
    para_ids.add(int(st["para_center"]))
    char_ids.add(int(st["body_bold_base"]))
    bf = prof["border_fill"]
    bf_ids = {
        int(bf["th"]["first"]), int(bf["th"]["mid"]), int(bf["th"]["last"]),
        int(bf["td"]["first"]), int(bf["td"]["mid"]), int(bf["td"]["last"]),
        int(bf["src"]), int(bf["tbl"]),
    }
    return {"charPr": char_ids, "paraPr": para_ids, "borderFill": bf_ids}


def _hangul_fonts(header: str) -> dict[int, str]:
    m = re.search(r'<hh:fontface lang="HANGUL"[^>]*>(.*?)</hh:fontface>', header, re.S)
    if not m:
        return {}
    return {int(i): face for i, face in re.findall(r'<hh:font id="(\d+)" face="([^"]+)"', m.group(1))}


def _parse_charpr(header: str, fonts: dict[int, str]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for m in re.finditer(r'<hh:charPr id="(\d+)"([^>]*)>(.*?)</hh:charPr>', header, re.S):
        cid = int(m.group(1))
        blob = m.group(0)
        hm = re.search(r'height="(\d+)"', blob)
        height = int(hm.group(1)) if hm else 0
        fr = re.search(r'<hh:fontRef hangul="(\d+)"', m.group(3))
        font_id = int(fr.group(1)) if fr else None
        bold = bool(re.search(r"<hh:bold\s*/>", m.group(3)) or re.search(r"<hh:bold>", m.group(3)))
        out[cid] = {
            "font": fonts.get(font_id, "") if font_id is not None else "",
            "height": height,
            "pt": height / 100,
            "bold": bold,
        }
    return out


def _parse_parapr(header: str) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for m in re.finditer(r'<hh:paraPr id="(\d+)"[^>]*>(.*?)</hh:paraPr>', header, re.S):
        pid = int(m.group(1))
        body = m.group(2)
        al = re.search(r'<hh:align horizontal="([^"]+)"', body)
        case = re.search(
            r"<hp:case[^>]*>.*?<hc:left value=\"(\d+)\"", body, re.S
        )
        if case:
            left = int(case.group(1))
        else:
            lm = re.search(r'<hc:left value="(\d+)"', body)
            left = int(lm.group(1)) if lm else None
        ls_case = re.search(
            r"<hp:case[^>]*>.*?<hh:lineSpacing type=\"([^\"]+)\" value=\"(\d+)\"",
            body, re.S,
        )
        if ls_case:
            ls_type, ls_val = ls_case.group(1), int(ls_case.group(2))
        else:
            ls = re.search(r'<hh:lineSpacing type="([^"]+)" value="(\d+)"', body)
            ls_type, ls_val = (ls.group(1), int(ls.group(2))) if ls else ("", None)
        if ls_val is None:
            spacing = ""
        elif ls_type == "PERCENT":
            spacing = f"{ls_val}%"
        else:
            spacing = str(ls_val)
        out[pid] = {
            "align": al.group(1) if al else "",
            "left": left,
            "line_spacing": spacing,
        }
    return out


def _parse_page(section: str) -> dict:
    page = re.search(
        r'<hp:pagePr[^>]*width="(\d+)"[^>]*height="(\d+)"[^>]*>'
        r'\s*<hp:margin([^>]*)/>',
        section, re.S,
    )
    if not page:
        # 속성 순서가 다를 수 있다
        pr = re.search(r"<hp:pagePr\b([^>]*)>", section)
        mg = re.search(r"<hp:margin\b([^>]*)/>", section)
        if not pr or not mg:
            raise ValueError("secPr pagePr/margin 을 찾지 못했다")
        attrs_pr, attrs_mg = pr.group(1), mg.group(1)
        width = int(re.search(r'width="(\d+)"', attrs_pr).group(1))
        height = int(re.search(r'height="(\d+)"', attrs_pr).group(1))
        def _m(name: str) -> int:
            m = re.search(rf'{name}="(\d+)"', attrs_mg)
            return int(m.group(1)) if m else 0
        left, right, top, bottom = _m("left"), _m("right"), _m("top"), _m("bottom")
        header, footer = _m("header"), _m("footer")
    else:
        width, height = int(page.group(1)), int(page.group(2))
        attrs_mg = page.group(3)
        def _m(name: str) -> int:
            m = re.search(rf'{name}="(\d+)"', attrs_mg)
            return int(m.group(1)) if m else 0
        left, right, top, bottom = _m("left"), _m("right"), _m("top"), _m("bottom")
        header, footer = _m("header"), _m("footer")
    body_w = width - left - right
    body_h = height - top - bottom - header - footer
    return {
        "width": width,
        "height": height,
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "header": header,
        "footer": footer,
        "body_w": body_w,
        "body_h": body_h,
    }


def probe(hwpx: Path) -> dict:
    with zipfile.ZipFile(hwpx) as z:
        header = z.read("Contents/header.xml").decode("utf-8")
        section = z.read("Contents/section0.xml").decode("utf-8")
    fonts = _hangul_fonts(header)
    charpr = _parse_charpr(header, fonts)
    parapr = _parse_parapr(header)
    page = _parse_page(section)
    scope = re.sub(r"<hp:tbl .*?</hp:tbl>", "", section, flags=re.S)
    use = Counter(re.findall(
        r'<hp:p id="\d+" paraPrIDRef="(\d+)"[^>]*>\s*<hp:run charPrIDRef="(\d+)"',
        scope,
    ))
    usage = []
    for (pid, cid), n in use.most_common():
        pid_i, cid_i = int(pid), int(cid)
        pp = parapr.get(pid_i, {})
        cp = charpr.get(cid_i, {})
        usage.append({
            "paraPr": pid_i,
            "charPr": cid_i,
            "n": n,
            "font": cp.get("font", ""),
            "pt": cp.get("pt"),
            "bold": bool(cp.get("bold")),
            "align": pp.get("align", ""),
            "left": pp.get("left"),
            "line_spacing": pp.get("line_spacing", ""),
        })
    defined = {
        "charPr": {int(x) for x in re.findall(r'<hh:charPr id="(\d+)"', header)},
        "paraPr": {int(x) for x in re.findall(r'<hh:paraPr id="(\d+)"', header)},
        "borderFill": {int(x) for x in re.findall(r'<hh:borderFill[^>]*id="(\d+)"', header)},
    }
    return {"page": page, "usage": usage, "defined": defined}


def _fmt_pt(pt) -> str:
    if pt is None:
        return ""
    return str(int(pt)) if abs(pt - round(pt)) < 1e-9 else f"{pt:.1f}"


def format_probe(data: dict) -> str:
    p = data["page"]
    rows = [
        "판형",
        "| 항목 | HWPUNIT | 환산 |",
        "|---|---|---|",
        f"| 용지 | {p['width']} × {p['height']} | A4 |",
        f"| 좌·우 여백 | {p['left']} · {p['right']} | {_hwp_to_mm(p['left'])} |",
        f"| 상·하 여백 | {p['top']} · {p['bottom']} | {_hwp_to_mm(p['top'])} |",
        f"| 머리말·꼬리말 | {p['header']} · {p['footer']} | {_hwp_to_mm(p['header'])} |",
        f"| 본문 폭 | {p['body_w']} | 용지폭 − 좌우여백 |",
        f"| 본문 높이 | {p['body_h']} | 용지높이 − 상하여백 − 머리말·꼬리말 |",
        "",
        "(paraPr, charPr) 사용 조합 — 표 제외",
        "| paraPr | charPr | n | 글꼴 | pt | 굵기 | 정렬 | 좌여백 | 줄간격 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for u in data["usage"]:
        bold = "B" if u["bold"] else "–"
        left = "" if u["left"] is None else str(u["left"])
        rows.append(
            f"| {u['paraPr']} | {u['charPr']} | {u['n']} | {u['font']} | "
            f"{_fmt_pt(u['pt'])} | {bold} | {u['align']} | {left} | {u['line_spacing']} |"
        )
    return "\n".join(rows)


def check_profile(defined: dict[str, set[int]], prof: dict) -> dict[str, list[int]]:
    want = profile_ids(prof)
    missing = {
        kind: sorted(ids - defined[kind])
        for kind, ids in want.items()
    }
    return {k: v for k, v in missing.items() if v}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hwpx")
    parser.add_argument("--profile")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    hwpx = Path(args.hwpx)
    if not hwpx.exists():
        print(f"양식 없음: {hwpx}")
        return 1
    data = probe(hwpx)
    missing = {}
    prof = None
    if args.profile:
        prof = load_profile_json(args.profile)
        missing = check_profile(data["defined"], prof)

    if args.json:
        payload = {
            "page": data["page"],
            "usage": data["usage"],
            "missing": missing,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_probe(data))
        if missing:
            print()
            print("프로필 ID 없음")
            for kind, ids in missing.items():
                print(f"  {kind}: {ids}")
    if missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
