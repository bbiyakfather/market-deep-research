STATUS: complete
CHANGES: verify_facts.py — 원고 전체 로컬 이미지의 audit/ 경계·실재 검사를 G3 도판검사에 추가(캡션은 본문 유지). facts_db.py — evidence_content_digest 를 운영 필드 2개 제외 행 전체 투영으로 변경. verification-gates.md·claim-review.md — 허용 이미지 위치/봉인, 미인용 high-risk WARN, digest 범위, v4 FAIL/WARN·조건 인용 계약을 문서화. test_batch3a_regressions.py — digest 정규화 1건 수정, locator/역할/그룹/시점 변경 FAIL·accessed_at/note PASS 추가. test_batch3b_regressions.py — 실제 G3 경로로 audit 참조 FAIL·부록 전용 봉인·extend 후 교체 거부 추가. manifest.py 는 audit 제외 정책이 이미 있어 미수정.
VERIFIED: `python -m pytest -q tests/test_batch3a_regressions.py tests/test_batch3b_regressions.py` → `71 passed in 4.65s`. `python -m pytest -q` → `523 passed in 53.26s` (기준선 514 + 신규 9, 0 failed).
JUDGMENT CALLS: 부록 캡션을 본문에 적용하지 않으려고 check_figures 에 선택 인자 report_text 를 두고 verify() 가 전체 원고를 넘기게 했다. 루트 이미지 G3 PASS 픽스처의 캡션에서 (F001) 을 빼 주장검토 누락을 피했다(루트는 F태그 의무가 아님). digest 는 없는 키를 null 로 채우지 않고 행에 있는 키만 넣는다. audit 참조 FAIL 테스트는 본문 `audit/chart.png` 한 경로로 두었다.
GAPS: 없음
