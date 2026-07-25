"""test_e2e.py — 미니 E2E: 증거 → 캡처 → 대장 → 보고서 → G3 → PDF → preview → 무결성.

자체 스택만으로 파이프라인이 완주하는지, 고객PDF/audit 분리가 되는지 확인한다.
네트워크 불필요(로컬 PDF 로 캡처 체인 검증). render 는 pandoc+chrome 사용.
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fitz                                                # noqa: E402
from skill_paths import resolve_work_dir, WorkPaths        # noqa: E402
from facts_db import FactsDB                               # noqa: E402
import capture_pdf, manifest, verify_facts, render_pdf, preview_pdf  # noqa: E402


def build_source_pdf(path: Path):
    doc = fitz.open(); p = doc.new_page()
    p.insert_text((72, 100), "Samsung 2024 revenue: 300.9 (KRW trillion)")
    p.insert_text((72, 130), "Green H2 market 2030: 45 (KRW trillion)")
    doc.save(str(path)); doc.close()


REPORT = """# 글로벌 시장조사 팩트시트 (E2E)

## Executive Summary
삼성전자 2024년 연결 매출은 **300.9조원(F001)** 이며, 2030년 그린수소 시장은 45조원(F002) 규모로 전망된다.

## 조사 개요
축: 매출·시장규모. 조사종료기준: 1차출처 확보 시.

## 테마별 본론
### 매출
삼성전자 2024 매출은 300.9조원(F001).

| 사실 | 수치 | 등급 | 증빙 |
|---|---|---|---|
| 매출(F001) | 300.9조원 | A | E001 |
| 시장규모(F002) | 45조원 | B | E002 |

![증빙 E001](_captures/E001.png)

## 검증 요약
F001·F002 팀리드 재열람 완료. high-risk F001 반박검색 통과.

<!-- FACTSHEET:APPENDIX -->
## 부록
- 소스: DART(F001), 시장보고서(F002). 폐기 0건은 audit 참조.
"""


def main():
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("E2E 미니조사", base=td)
        wp = WorkPaths(wd)
        db = FactsDB(wd)

        # 1) 소스 PDF + 정확숫자 캡처
        src = wp.sources / "source.pdf"; build_source_pdf(src)
        c1 = capture_pdf.capture_number(src, "300.9", wp.captures / "E001.png")
        c2 = capture_pdf.capture_number(src, "45", wp.captures / "E002.png")
        assert c1["ok"] and c2["ok"], (c1, c2)

        # 2) 사실 2건 등재 + 증거 + 팀리드 재검증 + confirmed
        for fid, metric, raw, unit, risk, cap in [
            ("F001", "revenue", "300.9", "KRW_T", "high", "_captures/E001.png"),
            ("F002", "market_size", "45", "KRW_T", "normal", "_captures/E002.png"),
        ]:
            f = db.add_fact({"claim": f"{metric}={raw}", "risk": risk, "status": "pending",
                             "context": {"metric": metric, "entity": "삼성" if fid == "F001" else "그린수소",
                                         "geography": "KR" if fid == "F001" else "GLOBAL",
                                         "period": "2024" if fid == "F001" else "2030"},
                             "value": {"raw": raw, "unit": unit},
                             "grade": {"authority": "A", "independence": "A", "directness": "A", "recency": "A"}})
            db.add_evidence({"fact_id": f["id"], "type": "table_cell",
                             "source_url": "https://dart.fss.or.kr/e2e",
                             "sha256": hashlib.sha256(("e2e-" + fid).encode()).hexdigest(),
                             "locator": {"page": 1}, "capture": cap, "source_role": "원출처",
                             "observer_group": "dart" if fid == "F001" else "market_report"})
            db.add_verify_event(f["id"], "lead", "reread", "원문 표셀 재열람 일치")
            if risk == "high":                          # claim-graph 필드(데모)
                rows = db.facts()                       # 한 번만 읽어 그 원소를 갱신(재독으로 덮이지 않게)
                fr = [x for x in rows if x["id"] == fid][0]
                fr.update({"independent_groups": ["dart", "irstatement"],
                           "counter_search": {"query": "삼성 2024 매출 정정", "result": "없음",
                                              "found_stronger_refutation": False},
                           "primary_source_ref": "E001", "observed_at": "2026-07-22", "valid_at": "2025-03"})
                from facts_db import _write_jsonl_atomic
                _write_jsonl_atomic(wp.facts, rows)
            db.set_status(fid, "confirmed")

        # 2.5) claim-graph 영속 확인 — set_status 재기록(디스크 재독+재쓰기) 이후에도 필드가 살아있는지
        f001 = [x for x in db.facts() if x["id"] == "F001"][0]
        assert f001["independent_groups"] == ["dart", "irstatement"], f001
        assert f001["counter_search"]["found_stronger_refutation"] is False, f001
        assert f001["primary_source_ref"] == "E001", f001
        assert f001["valid_at"] == "2025-03", f001

        # 3) 보고서 작성
        wp.report_md.write_text(REPORT, encoding="utf-8")

        # 4) G3 verify_facts (실패 0)
        rep = verify_facts.verify(wp.report_md, wd)
        assert rep["ok"], f"G3 실패: {rep['failures']}"

        # 5) manifest 고정
        manifest.build(wp)
        assert manifest.verify(wp)["ok"]

        # 6) render → PDF (고객용)
        r = render_pdf.render(wp.report_md, wp.report_pdf, resource_dir=wp.root)
        assert r["ok"] and wp.report_pdf.stat().st_size > 2000, r

        # 6.5) 재봉인 — [5]의 build 시점엔 report.pdf 가 없어 미봉인 상태다. 재봉인 전엔 신규
        # 파일로 잡혀 verify 가 실패해야 하고, 재봉인 후엔 항목 해시가 실제 PDF 해시와 일치해야
        # 한다(V06 회귀 가드).
        v_unsealed = manifest.verify(wp)
        assert not v_unsealed["ok"] and "report.pdf" in v_unsealed["new"], v_unsealed
        manifest.build(wp)
        assert manifest.verify(wp)["ok"]
        sealed = json.loads(wp.manifest.read_text(encoding="utf-8"))["entries"]
        assert sealed["report.pdf"]["sha256"] == manifest.sha256_file(wp.report_pdf)

        # 7) preview 육안검증 이미지
        imgs = preview_pdf.preview(wp.report_pdf, wp.root / "_preview")
        assert imgs and all(Path(x).stat().st_size > 0 for x in imgs)

        # 8) 최종 무결성(파일 불변)
        assert manifest.verify(wp)["ok"]

        # 9) 분리 확인: 고객 PDF 생성됨 + audit 저널 위치 존재
        assert wp.report_pdf.exists()
        assert wp.audit.is_dir()

        print(f"E2E OK — facts={len(db.facts())} evidence={len(db.evidence())} "
              f"pdf={wp.report_pdf.stat().st_size}B pages={len(imgs)} "
              f"(자체 스택만, G3 PASS, 무결성 OK)")


if __name__ == "__main__":
    main()
