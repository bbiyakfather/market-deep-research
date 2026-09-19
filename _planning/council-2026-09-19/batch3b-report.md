STATUS: complete
CHANGES: verify_facts.py — 도판 파서를 report_image_refs 로 공개하고 작업폴더 밖 참조에 [도판경계] 추가 / manifest.py — _tracked_paths 가 report.md 로컬 이미지를 report_image 로 봉인(기존 라벨 유지, audit/ 제외) / verification-gates.md — G3 도판검사 계약 4줄 추가 / tests/test_batch3b_regressions.py — R02 회귀 7건 신설
VERIFIED: `python -m pytest -q tests/test_batch3b_regressions.py` → `7 passed in 0.12s` ; `python -m pytest -q` → `438 passed in 46.60s`
JUDGMENT CALLS: 작업폴더 밖 참조는 [도판경계]와 기존 [도판경로]를 함께 낸다(기존 단언이 "도판경로" 부분문자열을 요구하므로 약화하지 않음). audit/ 이미지는 TRACKED 주석의 무한복귀 경고를 따라 봉인에서 뺀다. report_image_refs 는 원격·data·UNC 를 제외한 원고 표기 경로를 그대로 반환하고, manifest 키는 resolve 된 작업폴더 상대경로다. file:// 는 기존 _exists 와 같이 scheme 있는 원격으로 분류한다.
GAPS: 없음
