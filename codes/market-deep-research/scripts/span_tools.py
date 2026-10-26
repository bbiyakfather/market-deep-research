#!/usr/bin/env python3
"""span_tools.py — evidence.verbatim 이 `_sources/<sha12>_clean.txt` 원문에 글자 그대로 있는지 행 단위로 대조한다.

  python span_tools.py find <work_dir> <sha12> "<verbatim>"     # verbatim 의 행 범위 탐색(리드 재열람 때 span 채움)
  python span_tools.py context <work_dir> <sha12> <line> <end>  # 앞뒤 6행 맥락(적중 행 '>' 표시)

규칙(의도적으로 엄격 — 한 글자라도 다르면 실패):
- 행 분할은 `split("\\n")` 만. `splitlines()` 는 \\f 등을 줄바꿈으로 세어 `grep -n` 과 행 번호가 어긋난다.
- 정규화는 공백류 압축과 행머리 불릿 제거뿐. 그 외 글자는 바꾸지 않는다.
- verbatim 의 줄임은 `…` 로만 허용: 조각이 원문에 **순서대로** 나와야 한다.
의미 검사가 아니다. 확인되는 것은 "인용이 원문에 있다"까지다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_BULLET = re.compile(r"^\s*(?:[•·▪‣●○◦]\s*|[-*]\s+)")  # '-5%' 의 부호는 지우지 않도록 -/* 는 뒤 공백 요구
_WS = re.compile(r"\s+")
MAX_WINDOW = 40  # shortcut: find_span 창 상한 40행, 더 긴 인용은 `…` 로 나누거나 상한을 올린다


_REF = re.compile(r"[0-9a-f]{12}(_clean\.txt)?|[0-9a-f]{64}")


def clean_path(work_dir, sha12) -> Path:
    if not isinstance(sha12, str) or not _REF.fullmatch(sha12):
        raise ValueError(f"clean 참조 형식 오류(sha12 또는 <sha12>_clean.txt): {sha12!r}")
    name = sha12 if sha12.endswith(".txt") else f"{sha12[:12]}_clean.txt"
    return Path(work_dir) / "_sources" / name


def load_clean(work_dir, sha12: str) -> list[str]:
    # bytes 로 읽어 \r 단독 치환을 막는다(universal newline 이 행 번호를 어긋나게 함)
    return clean_path(work_dir, sha12).read_bytes().decode("utf-8", errors="replace").split("\n")


def normalize(s: str) -> str:
    return _WS.sub(" ", _BULLET.sub("", s)).strip()


def _frags(verbatim: str) -> list[str]:
    # verbatim 조각은 공백 압축만(불릿 제거는 clean 행에만 — "- 5%" 의 부호를 지우지 않는다)
    return [f for f in (_WS.sub(" ", p).strip() for p in verbatim.split("…")) if f]


def _digit_edge(text: str, i: int, step: int) -> bool:
    """text[i] 가 숫자의 일부로 이어지는가: 숫자이거나, '.'/',' 뒤에 다시 숫자가 오는 경우."""
    if not 0 <= i < len(text):
        return False
    if text[i].isdigit():
        return True
    return text[i] in ".," and 0 <= i + step < len(text) and text[i + step].isdigit()


def _contains(text: str, frags: list[str]) -> bool:
    pos = 0
    for f in frags:
        while True:
            i = text.find(f, pos)
            if i < 0:
                return False
            # 숫자 경계: "12.5" 가 "12.57" 에, "3조" 가 "13조" 에 걸리지 않게 한다
            if (f[0].isdigit() and _digit_edge(text, i - 1, -1)) or                (f[-1].isdigit() and _digit_edge(text, i + len(f), 1)):
                pos = i + 1
                continue
            break
        pos = i + len(f)
    return True


def _join(nl: list[str]) -> str:
    return " ".join(nl)


def find_span(lines: list[str], verbatim: str) -> tuple[int, int] | None:
    """verbatim 이 들어 있는 가장 짧은 행 범위(1부터, 양끝 포함). 없으면 None."""
    frags = _frags(verbatim)
    nl = [normalize(x) for x in lines]  # 정규화는 한 번만
    if not frags or not _contains(_join(nl), frags):
        return None
    n = len(nl)
    for s in range(n):
        for e in range(s, min(n, s + MAX_WINDOW)):
            if _contains(_join(nl[s:e + 1]), frags):
                while s < e and _contains(_join(nl[s + 1:e + 1]), frags):
                    s += 1  # 첫 조각이 뒤 행에서 시작하면 앞을 잘라 범위를 조인다
                return s + 1, e + 1
    return None


def check_span(lines: list[str], verbatim: str, line: int, end: int, slack: int = 2) -> bool:
    if not (1 <= line <= end <= len(lines)):
        return False
    frags = _frags(verbatim)
    return bool(frags) and _contains(_join([normalize(x) for x in lines[max(0, line - 1 - slack):end + slack]]), frags)


def context(lines: list[str], line: int, end: int, n: int = 6) -> str:
    lo, hi = max(1, line - n), min(len(lines), end + n)
    return "\n".join(f"{i:>5}{'>' if line <= i <= end else ' '} {lines[i - 1]}" for i in range(lo, hi + 1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="verbatim ↔ clean 원문 행 대조 도구")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find", help="verbatim 의 행 범위 탐색")
    f.add_argument("work_dir"); f.add_argument("sha12"); f.add_argument("verbatim")
    c = sub.add_parser("context", help="행 범위 앞뒤 맥락 출력")
    c.add_argument("work_dir"); c.add_argument("sha12")
    c.add_argument("line", type=int); c.add_argument("end", type=int)
    a = ap.parse_args(argv)
    try:
        lines = load_clean(a.work_dir, a.sha12)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"clean 파일 없음: {exc.filename}", file=sys.stderr)
        return 2
    if a.cmd == "context":
        print(context(lines, a.line, a.end))
        return 0
    hit = find_span(lines, a.verbatim)
    if hit is None:
        print("원문에서 찾지 못함 — confirm 불가(글자·순서·줄임표 확인)", file=sys.stderr)
        return 1
    print(json.dumps({"clean": clean_path(a.work_dir, a.sha12).name, "line": hit[0], "end": hit[1]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
