"""verify_facts.py — G3 검증 게이트 (plan-v2 핵심설계6). 실패 0 이어야 통과.

검사:
  1. 본문/생성부록 분리 파싱(부록의 F태그는 '본문 사용'으로 미계산)
  2. 본문의 무태그 숫자(통화·비율·수량단위) 탐지 → 태그 없는 사실주장 차단
  3. 모든 (Fxxx) 가 대장 존재 + status∈{confirmed} + 값 의미 대조(태그 앞 숫자 ↔ 대장 value)
  4. confirmed 인데 본문 미사용 사실(유실 점검)
  5. evidence 필수필드 누락 0, text_quote 는 verbatim 필수
  6. source_capture 실재(risk=high 핵심수치 필수)

부록 경계 마커: '<!-- FACTSHEET:APPENDIX -->' 또는 '## 부록' 이후는 부록.

CLI: python verify_facts.py <report.md> <work_dir> [--conversion]
     python verify_facts.py demo
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

from facts_db import FactsDB
from skill_paths import WorkPaths

APPENDIX_MARKERS = ("<!-- FACTSHEET:APPENDIX -->", "## 부록", "## Appendix")
# 사실주장으로 취급하는 수치(통화·비율·수량+단위). 연도 단독/섹션번호는 제외.
# 주의: 한국어는 교착어라 단위 뒤에 조사가 붙는다("45조원으로") → 후행 \b 금지(매칭 실패).
METRIC_NUM = re.compile(
    r"\d[\d,\.]*\s*(?:조원|억원|만원|억달러|백만달러|억달러|MW|GW|kW|㎿|톤|t/y|USD|KRW|billion|million|퍼센트|원|달러|조|억|%)",
    re.I)
TAG = re.compile(r"\(F\d{3,}\)")
# gap 에 줄바꿈/표구분자(|) 금지 — E001 등 증거ID 숫자가 다음 행 F태그와 오연결되는 것 차단.
NUM_BEFORE_TAG = re.compile(r"([\d][\d,\.]*)\s*[^()\d\n|]{0,8}?\(?(F\d{3,})\)")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def split_body_appendix(md: str) -> tuple[str, str]:
    idx = len(md)
    for mk in APPENDIX_MARKERS:
        p = md.find(mk)
        if p != -1:
            idx = min(idx, p)
    return md[:idx], md[idx:]


def _digits(s: str) -> str:
    return re.sub(r"[^\d]", "", s or "")


def verify(report_md: Path | str, work: WorkPaths | Path | str, conversion: bool = False) -> dict:
    md = Path(report_md).read_text(encoding="utf-8")
    body, _appendix = split_body_appendix(md)
    db = FactsDB(work)
    facts = {f["id"]: f for f in db.facts()}
    evidence = {e["id"]: e for e in db.evidence()}
    failures: list[str] = []
    warnings: list[str] = []

    # 3. 본문 F태그: 존재 + confirmed + 값 의미 대조
    for m in NUM_BEFORE_TAG.finditer(body):
        num, fid = m.group(1), m.group(2)
        f = facts.get(fid)
        if not f:
            failures.append(f"[오태그] 본문 {fid} 이(가) 대장에 없음"); continue
        if f.get("status") != "confirmed":
            failures.append(f"[미확정] 본문 {fid} status={f.get('status')} (confirmed 아님)")
        want = _digits((f.get("value") or {}).get("raw", ""))
        if want and _digits(num) and want != _digits(num):
            failures.append(f"[값불일치] 본문 {fid}: 표기 '{num}' ≠ 대장 '{f['value']['raw']}'")

    # 존재하는 모든 본문 F태그(숫자 없이 참조된 것 포함) 대장·상태 검사
    for fid in set(re.findall(r"\(F\d{3,}\)", body)):
        fid2 = fid.strip("()")
        f = facts.get(fid2)
        if not f:
            failures.append(f"[오태그] 본문 {fid2} 대장에 없음")
        elif f.get("status") != "confirmed":
            failures.append(f"[미확정] 본문 {fid2} status={f.get('status')}")

    # 2. 무태그 숫자(사실주장) 탐지 — 문장 단위
    for ln in body.splitlines():
        if METRIC_NUM.search(ln) and not TAG.search(ln):
            warnings_or_fail = ln.strip()[:80]
            failures.append(f"[무태그] 수치 사실주장에 F태그 없음: '{warnings_or_fail}'")

    # 4. confirmed 인데 본문 미사용
    used = {fid.strip("()") for fid in re.findall(r"\(F\d{3,}\)", body)}
    for fid, f in facts.items():
        if f.get("status") == "confirmed" and fid not in used:
            warnings.append(f"[미사용] confirmed {fid} 본문에서 안 쓰임")

    # 5·6. evidence 필수필드 + text_quote verbatim + capture 실재(high)
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    for f in facts.values():
        if f.get("status") != "confirmed":
            continue
        for eid in f.get("evidence_ids", []):
            e = evidence.get(eid)
            if not e:
                failures.append(f"[증거유실] {f['id']} → {eid} 없음"); continue
            for k in ("source_url", "type", "sha256", "accessed_at"):
                if not e.get(k):
                    failures.append(f"[증거필드] {eid} '{k}' 누락")
            if e.get("type") == "text_quote" and not e.get("verbatim"):
                failures.append(f"[verbatim] {eid} text_quote 인데 verbatim 없음")
        if f.get("risk") == "high":
            caps = [evidence.get(e, {}).get("capture") for e in f.get("evidence_ids", [])]
            caps = [c for c in caps if c]
            if not caps:
                failures.append(f"[증빙] high-risk {f['id']} source_capture 없음")
            else:
                for c in caps:
                    if not (wp.root / c).exists() and not Path(c).exists():
                        failures.append(f"[증빙유실] {f['id']} 캡처 파일 없음: {c}")

    if conversion:
        for f in facts.values():
            v = f.get("value", {})
            if v.get("unit", "").startswith(("USD", "$")) and not v.get("decimal"):
                warnings.append(f"[환산] {f['id']} decimal 검산값 없음")

    return {"ok": len(failures) == 0, "failures": failures, "warnings": warnings,
            "stats": {"facts": len(facts), "evidence": len(evidence),
                      "body_tags": len(used)}}


def _print(rep: dict) -> None:
    print(f"[G3 verify] facts={rep['stats']['facts']} evidence={rep['stats']['evidence']} "
          f"본문태그={rep['stats']['body_tags']}")
    for f in rep["failures"]:
        print("  ✗ " + f)
    for w in rep["warnings"]:
        print("  ⚠ " + w)
    print("  결과:", "PASS" if rep["ok"] else f"FAIL ({len(rep['failures'])}건)")


def demo() -> None:
    import tempfile
    from skill_paths import resolve_work_dir
    from facts_db import FactsDB as DB
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("검증 데모", base=td)
        db = DB(wd)
        # 정상 confirmed fact F001 = 300.9
        db.add_fact({"claim": "매출 300.9조",
                     "context": {"metric": "revenue", "entity": "삼성", "geography": "KR", "period": "2024"},
                     "value": {"raw": "300.9", "unit": "KRW_T"},
                     "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"},
                     "risk": "normal", "status": "pending"})
        db.add_evidence({"fact_id": "F001", "type": "table_cell",
                         "source_url": "https://dart.fss.or.kr", "sha256": "h"})
        db.add_verify_event("F001", "lead", "reread")
        db.set_status("F001", "confirmed")

        wp = WorkPaths(wd)
        good = "삼성전자 2024년 매출은 300.9조원(F001) 입니다.\n"
        (wp.root / "good.md").write_text(good, encoding="utf-8")
        assert verify(wp.root / "good.md", wd)["ok"], "정상 보고서가 FAIL"

        bad_untag = "시장 규모는 45조원으로 성장했다.\n"          # 무태그
        (wp.root / "u.md").write_text(bad_untag, encoding="utf-8")
        assert not verify(wp.root / "u.md", wd)["ok"], "무태그 미검출"

        bad_val = "매출은 999조원(F001) 이다.\n"                  # 값불일치
        (wp.root / "v.md").write_text(bad_val, encoding="utf-8")
        r = verify(wp.root / "v.md", wd)
        assert not r["ok"] and any("값불일치" in x for x in r["failures"]), r

        # 부록의 태그는 본문 사용으로 미계산
        appx = good + "\n## 부록\n- F001 전수표 999조원(F001)\n"
        (wp.root / "a.md").write_text(appx, encoding="utf-8")
        assert verify(wp.root / "a.md", wd)["ok"], "부록이 본문검사 오염"
    print(f"[{_now()}] verify_facts demo OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif len(args) >= 2:
        rep = verify(args[0], args[1], conversion="--conversion" in args)
        _print(rep)
        sys.exit(0 if rep["ok"] else 1)
    else:
        print(__doc__); sys.exit(2)
