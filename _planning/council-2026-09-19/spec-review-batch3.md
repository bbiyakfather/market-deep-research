# 코드 리뷰 — 배치 3A·3B·3C 통합 diff (R01~R09 보완)

REASONING: xhigh

## 목표
저장소 `F:/Claude/skills/market-deep-research`, 브랜치 `feat/purpose-modules`. 리뷰 범위는 `git diff a07a3c7..HEAD` (커밋 3개: 3C 파서 · 3B 이미지 봉인 · 3A 검토 결박·버전·부록).
이 변경은 3차 리뷰 `_planning/council-2026-09-19/review-astra-pr18-adversarial.md` 의 R01~R09 를 닫기 위한 것이다. 구현이 아니라 **리뷰만** 한다.
찾을 것은 두 가지다: (가) 잘못된 보고서가 검증을 PASS 하는 정확성 결함, (나) 정상 보고서가 부당하게 FAIL 하는 오탐.

## 읽을 것
- 스펙(결정 사항의 근거): `_planning/council-2026-09-19/spec-batch3a.md`, `spec-batch3b.md`, `spec-batch3c.md`
- 워커 보고: 같은 폴더의 `batch3a-report.md`, `batch3b-report.md`, `batch3c-report.md`
- diff 는 직접 뽑는다: `git diff a07a3c7..HEAD --stat`, 파일별 `git diff a07a3c7..HEAD -- <path>`

## 확인할 질문
1. R01~R09 각각이 스펙대로 닫혔는가. 3차 리뷰 표의 "재현 입력 상태" 를 기준으로, 고친 뒤 기대 결과가 실제로 나오는지 기존 검증 함수와 테스트 fixture 로 확인한다.
2. 세 배치가 합쳐진 뒤의 상호작용 — 3C 가 바꾼 `split_segments`(괄호 내부 보호)가 3A 의 claim-review 문장 단위·부록 문장 검토와 어긋나는 곳, 3B 의 `report_image` 항목이 3A 의 finalize 재해시·`extend` 계약과 어긋나는 곳.
3. 팀리드가 미리 본 의심점에 대한 판정:
   - 3B: 원고가 `audit/` 아래 이미지를 참조하면 봉인에서 제외된다(`manifest._tracked_paths`). G3 도판검사에서 `audit/` 참조를 FAIL 시키는 것이 맞는가, 아니면 다른 처리가 맞는가.
   - 3B: `report.md` 읽기 실패 시 조용히 이미지 봉인을 건너뛴다 — 문제인가.
   - 3A: `schema_version` 오타 정규식 `(?i)^schema[\W_]*ver` 가 정상 키를 오탐하거나 흔한 오타(`shema_version`, `schemaVersion`, `version`)를 놓치는가. 어디까지가 합리적 범위인가.
   - 3A: R03 의 "required_qualification 이 sentence_text 의 부분 문자열" 요구가 정상 검토를 과도하게 막는가(조사·어미 차이). 더 나은 최소 기준이 있는가.
   - 3A: `evidence_content_digest` 의 필드 선택이 충분한가(빠진 필드로 내용을 바꿀 수 있는가), 새 E-ID 추가 허용이 의도대로인가.
   - 3C: `[수치미인식]` 이 흔한 한국어 보고서 문장(연도·순번·조항 번호·"3분기"·"2030년 목표" 등 수치가 아닌 숫자)에서 오탐을 내는가.
4. 새 테스트(`tests/test_batch3a_regressions.py`, `test_batch3b_regressions.py`, `test_batch3c_regressions.py`)가 구현을 베낀 단언이 아니라 실제 동작을 검증하는가. 빠진 부정 사례.
5. 문서(`references/claim-review.md`, `references/verification-gates.md`)가 바뀐 계약과 일치하는가. 세 배치가 같은 문서를 고치며 생긴 모순·중복.

## 제약
- 코드·문서·테스트 **수정 금지**, 커밋 금지. 테스트 실행과 읽기 전용 스크립트 실행은 허용(`python -m pytest -q -p no:cacheprovider`, 임시 입력은 OS 임시 폴더). 외부 네트워크·패키지 설치 금지.
- 범위는 위 diff 와 그 직접 호출 경로다. 경로 주입·설치기 보안 검토는 이번 범위가 **아니다** — 하지 않는다.
- 발견마다 `파일:줄` 과 "입력 상태 → 관찰 결과" 를 서술로 적는다. 확인 못 한 것은 "의심" 으로 분리한다.

## 산출물
`F:/Claude/skills/market-deep-research/_planning/council-2026-09-19/review-astra-batch3.md` (한국어) 하나만 쓴다:
1. 판정 한 줄: APPROVE / APPROVE-WITH-FIXUPS / REQUEST-CHANGES
2. R01~R09 종결표(닫힘/부분/안 닫힘 + 근거 한 줄)
3. 발견 표: ID · 심각도(P1 검증 공백 / P2 오탐·품질 / P3 문서·테스트) · `파일:줄` · 입력 상태 → 관찰 결과 · 최소 수정 방향
4. 질문 3 의 의심점별 판정(문제 아님 / 고쳐야 함 + 어떻게)
5. 실행한 테스트 명령과 출력 마지막 줄

## 진행 규칙
- 질문하지 말고 가정을 적고 진행한다. 막히면 막힌 곳을 산출물에 적고 종료한다.
- 시간 예산 30분. orca CLI 는 이 샌드박스에서 동작하지 않으니 heartbeat·worker_done 은 **시도하지 말고**, 파일 작성 후 요약 10줄만 출력하고 끝낸다.
