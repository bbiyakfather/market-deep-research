STATUS: complete

CHANGES:
- `codes/market-deep-research/scripts/verify_facts.py`: `METRIC_NUM`·`_LOOSE_CLAIM`·`_LOOSE_KO_CLAIM`의 시작 경계를 `(?<![A-Za-z0-9.,+−-])`에서 `(?<![A-Za-z0-9.+−-])(?<!\d,)`로 나눴다. 쉼표는 바로 앞이 숫자일 때만 시작 금지(천단위 `45,999` 중간 재시작 방지)이고, 단위 뒤 쉼표(`45mW,999mW`)에서는 다음 수치가 시작된다.
- `codes/market-deep-research/tests/test_batch3c_regressions.py`: 기존 테스트를 수정·삭제하지 않고 RR3-01 표 6행을 추가했다.
- `batch3f-report.md`: 실행 결과와 판단 가정을 기록했다.

VERIFIED:
- 최초 `git log --oneline -1`: `cc0d3af docs(mdr): SKILL.md 를 배치 3 계약에 맞춤 — 부록 인용·근거 내용 결박·v3 출고 플래그`. 브랜치 `bbiyakfather/mdr-batch3c`.
- 수정 전 재현: 대장 `45 mW` / 본문 `출력은 45mW,999mW(F001)이다.` → 실패·경고 0건. 같은 문장에 쉼표 뒤 공백이 있으면 `[값불일치]` FAIL.
- 수정 후 같은 입력: `[값불일치] 본문 F001: 표기 '999mW' ≠ 대장 '45'`.
- `codes/market-deep-research`에서 `PYTHONUTF8=1`로 `python -m pytest -q tests/test_batch3c_regressions.py`: `100 passed in 0.08s` (exit 0). 기존 94개 + 추가 6개.
- 같은 위치·환경에서 `python -m pytest -q`: `602 passed in 49.93s` (exit 0). 기준선 596개 + 추가 6개, 0 failed.
- `git diff --stat`: `verify_facts.py` 8줄, `test_batch3c_regressions.py` 29줄 순증. `git diff --check`: 공백 오류 없음. Git의 LF→CRLF 변환 예고만 출력됐다.

JUDGMENT CALLS:
- 시작 경계는 지시서가 적은 `(?<![A-Za-z0-9.+−-])(?<!\d,)`를 세 정규식에 그대로 인라인했다. 공유 상수는 만들지 않았고 `CUR_NUM`·다른 함수는 건드리지 않았다.
- `X45 USD` 문장은 기존 식별자 회귀와 같은 꼴(`X45 USD 시장 전망이다(F001).`)로 두어, 식별자 내부 시작 금지가 유지되는지 확인했다.
- `45mW,999mW(F001)`에서 첫 수치 `45mW`는 대장 값과 같아 표 셀 값일치 폴백으로 결박되고, 태그 최근접인 `999mW`가 `[값불일치]`를 낸다. 폴백 로직은 바꾸지 않았다.
- 프로젝트 `CLAUDE.md` 불변 규칙 섹션은 없다. 기존 미추적 `batch3c-report.md`·`batch3d-report.md`와 `_planning` 파일은 수정하지 않았다. 커밋·푸시·브랜치 변경·외부 네트워크·패키지 설치는 수행하지 않았다.

GAPS: 없음.
