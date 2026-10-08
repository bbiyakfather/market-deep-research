"""본문 표 가운데 시각화 후보를 뽑는다 — 표 만능 교정(`references/visual-first.md` §4).

사용: python visual_audit.py <report.md 또는 manuscript/<모듈>.md> [--decisions audit/visual-decisions.json]
      python visual_audit.py --selftest
- 후보 = 부록 마커(<!-- FACTSHEET:APPENDIX -->) 앞의 표 중 행 3개 이상·수치열 1개 이상(연번·'출처' 열 제외).
- decisions 파일: [{"key": "<표 키>", "decision": "chart|keep", "reason": "..."}]
  해결 = `keep` + 사유. `chart` 는 표를 지워 후보에서 사라져야 해결(표가 남아 있으면 '미전환').
  표 키 = 캡션에서 번호를 뗀 제목, 캡션이 없으면 "머리행 / 첫 행 20자"(원고 문장을 고쳐도 표 자체가 안 바뀌면 유지).
- 종료코드: 0 미결 없음 / 1 미결 있음 / 2 입력·판정 파일 오류.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

APPENDIX = re.compile(r"<!--\s*FACTSHEET:APPENDIX\s*-->")  # verify_facts.py 와 같은 허용 폭
SEP = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
FTAG = re.compile(r"\s*\((?:[A-Z]\d+[,\s]*)+\)")
# ponytail: 한 셀 = (접두)숫자(범위 허용) + 10자 이내 단위. "1단계 100MW"·"2027년 하반기 첫 생산 목표" 같은 혼합 셀은 텍스트로 본다.
NUM = re.compile(r"^(약|~|≈|±|[+\-−]|[A-Z]{0,2}[$€¥₩])?\s*\d[\d,.]*(\s*[~\-–]\s*\d[\d,.]*)?\s*[^\d|]{0,10}$")
YEAR = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
CAPTION = re.compile(r"^(<표>\s*)?\**\[?표\]?\s*[\d{][^.\s]*[.\s]*\**\s*")
SERIAL_HEADERS = {"#", "no", "no.", "순번", "순위", "연번", "번호"}


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_num(cell: str) -> bool:
    cell = FTAG.sub("", cell.replace(" ", " ")).strip()
    return cell not in {"", "-", "–", "—"} and bool(NUM.match(cell))


def parse_tables(lines: list[str]) -> list[tuple[int, int, list[str], list[list[str]]]]:
    """(시작줄, 끝줄, header, rows) 목록 — 1-based 줄번호, 부록 이후 제외."""
    out, i, n = [], 0, len(lines)
    while i < n:
        if APPENDIX.search(lines[i]):
            break
        if lines[i].lstrip().startswith("|") and i + 1 < n and SEP.match(lines[i + 1]):
            header, rows, j = _cells(lines[i]), [], i + 2
            while j < n and lines[j].lstrip().startswith("|"):
                rows.append(_cells(lines[j]))
                j += 1
            out.append((i + 1, j, header, rows))
            i = j
        else:
            i += 1
    return out


def classify(header: list[str], rows: list[list[str]]) -> tuple[int, str | None]:
    """(수치열 수, 제안 형식). 후보가 아니면 (0, None)."""
    if len(rows) < 3 or any("출처" in h for h in header):  # 증빙판 근거표(…|출처|등급|증빙)는 검증 구조라 제외
        return 0, None
    n, numeric = len(rows), []
    for k, h in enumerate(header):
        col = [r[k] for r in rows if k < len(r)]
        if h.strip().lower() in SERIAL_HEADERS or col == [str(i) for i in range(1, n + 1)]:
            continue  # 연번·순위 열은 수치가 아니다
        if sum(_is_num(c) for c in col) >= 0.6 * n:
            numeric.append(k)
    if not numeric:
        return 0, None
    head = " ".join(header)
    years_head = len(YEAR.findall(head))
    years_first = len(YEAR.findall(" ".join(r[0] for r in rows if r)))
    if years_head == 2:
        return len(numeric), "2시점 비교 → 병렬 막대·덤벨"
    if years_head >= 3 or years_first >= 3:
        return len(numeric), "시계열 → 선/세로 막대"
    if "%" in head or re.search(r"비중|점유|구성", head):
        return len(numeric), "비중 → 100% 누적 막대(5개 이하·합 100%면 원그래프 가능)"
    if len(numeric) >= 2:
        return len(numeric), "2변수 이상 → 산점도·덤벨 또는 지표별 막대 묶음"
    return len(numeric), "항목 비교 → 정렬한 가로 막대(20개 초과면 상위 N + 기타)"


def key_for(lines: list[str], start: int, header: list[str], rows: list[list[str]]) -> str:
    """캡션 제목(번호 제거) → 없으면 머리행 / 첫 행 20자. 줄번호·선도문은 원고 수정에 흔들려 쓰지 않는다."""
    for k in range(start - 2, max(-1, start - 5), -1):
        s = lines[k].strip()
        if CAPTION.match(s) and CAPTION.sub("", s).strip(" *"):
            return CAPTION.sub("", s).strip(" *")
    return " | ".join(header) + " / " + " ".join(rows[0])[:20]


def figure_nearby(lines: list[str], start: int, end: int, span: int = 8) -> bool:
    lo, hi = max(0, start - 1 - span), min(len(lines), end + span)
    return any("![" in ln for ln in lines[lo:hi])


def audit(text: str, decisions: dict[str, dict]) -> tuple[list[dict], int, set[str]]:
    lines = text.splitlines()
    rows_out, unresolved, used = [], 0, set()
    for start, end, header, rows in parse_tables(lines):
        ncols, suggestion = classify(header, rows)
        if not suggestion:
            continue
        key = key_for(lines, start, header, rows)
        dec = decisions.get(key)
        used.add(key)
        reason = str((dec or {}).get("reason", "")).strip()
        if dec is None:
            status = "미결"
        elif dec.get("decision") == "keep" and reason:
            status = "keep"
        elif dec.get("decision") == "chart":
            status = "chart 미전환"  # 표가 아직 남아 있다
        else:
            status = "keep 사유 없음"
        if status != "keep":
            unresolved += 1
        rows_out.append({"line": start, "key": key, "shape": f"{len(rows)}x{len(header)}", "numeric_cols": ncols,
                         "suggestion": suggestion, "figure_nearby": figure_nearby(lines, start, end),
                         "status": status, "reason": reason})
    return rows_out, unresolved, set(decisions) - used


def _selftest() -> None:
    sample = "\n".join([
        "## 2. 추이", "<표> 표 1. 연도별 용량",
        "| 연도 | 용량(MW) |", "|---|---|", "| 2023 | 100 (F001) |", "| 2024 | 150 (F002) |", "| 2025 | 220 (F003) |",
        "", "(허가) 국내 허가 현황",
        # ponytail: '2등급' 같은 숫자 접두 범주는 수치로 잡힌다(리드가 keep 으로 닫음) — 시험은 비수치 표기로
        "| # | 제품 | 허가번호 | 등급 |", "|---|---|---|---|", "| 1 | A | 제허 23-123 | Ⅱ등급 |", "| 2 | B | 제허 24-001 | Ⅱ등급 |", "| 3 | C | 제허 25-009 | Ⅲ등급 |",
        "", "| 사실 | 수치 | 출처 | 증빙 |", "|---|---|---|---|", "| a | 1 | x | y |", "| b | 2 | x | y |", "| c | 3 | x | y |",
        "", "| 국가 | 2025 | 2026 |", "|---|---|---|", "| 독일 | 31 | 29 (F010) |", "| 영국 | 12 | 19 |", "| 프랑스 | 16 | 9 |",
        "", "| 항목 | 값 |", "|---|---|", "| a | 1 |", "| b | 2 |",
        "", "<!--  FACTSHEET:APPENDIX  -->", "## 부록",
        "| 국가 | 2024 | 2025 |", "|---|---|---|", "| 한 | 1 | 2 |", "| 미 | 3 | 4 |", "| 일 | 5 | 6 |",
    ])
    for cell in ["1.2~1.5", "12.47$", "300 kg Ir/GW", "4.2억 달러", "+3.1%p", "109점", "약 3만", "220 (F003)", "US$1,200"]:
        assert _is_num(cell), cell
    for cell in ["1단계 100MW", "2027년 하반기 첫 생산 목표", "진전", "-", "제허 23-123"]:
        assert not _is_num(cell), cell
    found, unresolved, unmatched = audit(sample, {})
    assert [r["key"] for r in found] == ["연도별 용량", "국가 | 2025 | 2026 / 독일 31 29 (F010)"], [r["key"] for r in found]
    assert found[0]["suggestion"].startswith("시계열") and found[1]["suggestion"].startswith("2시점"), found
    assert unresolved == 2 and not unmatched
    dec = {"연도별 용량": {"decision": "chart"},
           "국가 | 2025 | 2026 / 독일 31 29 (F010)": {"decision": "keep", "reason": "값 참조용, 그림 4 뒤"},
           "옛 키": {"decision": "keep", "reason": "x"}}
    found, unresolved, unmatched = audit(sample, dec)
    assert [r["status"] for r in found] == ["chart 미전환", "keep"] and unresolved == 1 and unmatched == {"옛 키"}, found
    print("selftest OK")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", nargs="?", help="report.md 또는 납품 원고 모듈 .md")
    ap.add_argument("--decisions", help="판정 JSON (visual-first.md §4). 없으면 첫 실행으로 보고 전건 미결")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        _selftest()
        return 0
    if not args.report:
        ap.error("report.md 경로 또는 --selftest")
    try:
        text = Path(args.report).read_text(encoding="utf-8-sig")
        decisions: dict[str, dict] = {}
        if args.decisions and Path(args.decisions).exists():
            decisions = {d["key"]: d for d in json.loads(Path(args.decisions).read_text(encoding="utf-8-sig"))}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"입력 오류: {exc}", file=sys.stderr)
        return 2
    found, unresolved, unmatched = audit(text, decisions)
    print(f"시각화 후보 {len(found)}건 · 미결 {unresolved}건" + (f" · 짝 잃은 판정 키 {len(unmatched)}건: {sorted(unmatched)}" if unmatched else ""))
    for r in found:
        fig = "그림 인접" if r["figure_nearby"] else "그림 없음"
        print(f"L{r['line']:<5} {r['shape']:<7} 수치열 {r['numeric_cols']}  {fig:<6} [{r['status']}] {r['key']} → {r['suggestion']}"
              + (f"  ({r['reason']})" if r["reason"] else ""))
    return 1 if unresolved else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # Windows 콘솔
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
