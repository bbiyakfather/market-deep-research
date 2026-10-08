"""원고 수정 전후 숫자 보존 검사. 사용: BEFORE_DIR=<백업 폴더> python check_numbers.py <원고stem> [...] (cwd = manuscript/)
<BEFORE_DIR>/<stem>.md 의 숫자 토큰(다중집합)이 수정본에 전부 남아 있는지 본다. 새로 생긴 숫자(EXTRA)는 사실 추가 의심.
빠진 숫자가 있으면 MISSING 으로 출력하고 exit 1 (사실 유실 의심 → 되돌려 넣는다).
"""
import os
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path.cwd()
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
HEAD = re.compile(r"^(#{1,4} .*|!\[\]\(.*\)|\[그림\].*|\* 출처 :.*)$", re.M)


def toks(s):
    return Counter(NUM.findall(s))


def heads(s):
    return [m.group(0).strip() for m in HEAD.finditer(s) if m.group(0).startswith("#")]


bad = 0
for stem in sys.argv[1:]:
    before = (HERE / os.environ.get("BEFORE_DIR", "_before") / f"{stem}.md").read_text(encoding="utf-8")
    after = (HERE / f"{stem}.md").read_text(encoding="utf-8")
    missing = toks(before) - toks(after)
    extra = toks(after) - toks(before)
    hb, ha = heads(before), heads(after)
    print(f"[{stem}] 수정 전 숫자 {sum(toks(before).values())} → 후 {sum(toks(after).values())} | 빠짐 {sum(missing.values())} | 새로 생김 {sum(extra.values())}")
    if missing:
        bad += 1
        print("  MISSING:", dict(missing))
    if extra:
        print("  EXTRA(새 숫자는 허용 안 됨, 표 번호·연도 재배치만 허용):", dict(extra))
    if hb != ha:
        bad += 1
        print("  HEADINGS CHANGED:", [h for h in hb if h not in ha], "->", [h for h in ha if h not in hb])
sys.exit(1 if bad else 0)
