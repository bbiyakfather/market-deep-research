# 재리뷰 — 배치 3D·3E (B3-01~B3-07 종결 확인)

REASONING: xhigh

## 목표
저장소 `F:/Claude/skills/market-deep-research`, 브랜치 `feat/purpose-modules`. 범위는 `git diff 9d915d8..HEAD` (커밋 2개: 3D 파서 2차 · 3E 이미지 경계·digest·문서).
직전 리뷰 `_planning/council-2026-09-19/review-astra-batch3.md` 의 B3-01~B3-07 이 닫혔는지 확인하고, 이번 수정이 새로 만든 정확성 결함·오탐이 있는지 본다. **리뷰만** 한다.

## 읽을 것
- 스펙: `_planning/council-2026-09-19/spec-batch3d.md`, `spec-batch3e.md` / 워커 보고: 같은 폴더 `batch3d-report.md`, `batch3e-report.md`
- diff 는 직접: `git diff 9d915d8..HEAD --stat`, 파일별 diff

## 확인할 질문
1. B3-01~07 각각: 직전 리뷰의 "입력 상태" 를 기존 검증 함수·fixture 로 다시 넣었을 때 기대 결과가 나오는가.
2. 3D 의 한국어 단위 목록·비수량 제외 목록이 흔한 한국어 시장조사 문장에서 내는 오탐/미탐 — 특히 `원`(통화) 판정, `3개사`·`45개국`·`12억 달러`·`300조 원`·`1.2조원`·`5천만 달러` 같은 혼합 표기, 정성 인용 문장.
3. 3E 의 digest 범위 확대(운영 필드 2개만 제외)가 정상 흐름에서 불필요한 재검토를 강제하는 곳이 있는가 — 검토 뒤에 파이프라인이 기존 evidence 행을 정상적으로 고치는 단계가 있는지(`facts_db.py` 의 evidence 갱신 경로, G2 캡처·capture_review 기록 순서).
4. 3E 의 `check_figures(report_text=...)` 변경이 기존 본문 도판 규칙(대표 이미지 0장 차단·캡션·`_captures/` 제외)을 바꾸지 않았는가.
5. 문서(`verification-gates.md`, `claim-review.md`)와 `codes/market-deep-research/SKILL.md`(작업 트리의 미커밋 수정 포함)가 코드와 일치하는가.

## 제약
- 코드·문서·테스트 수정 금지, 커밋 금지. 테스트·읽기 전용 스크립트 실행은 허용(임시 입력은 OS 임시 폴더, pytest 는 `-p no:cacheprovider --basetemp <임시폴더>`). 외부 네트워크·패키지 설치 금지.
- 범위는 위 diff 와 직접 호출 경로다. 경로 주입·설치기 보안 검토는 범위가 아니다.
- 이 환경에는 pandoc 이 없을 수 있다. 렌더 의존 실패는 환경 제약으로 분리해 적는다(팀리드 환경에서는 596 passed 확인됨).

## 산출물
`F:/Claude/skills/market-deep-research/_planning/council-2026-09-19/review-astra-batch3-rereview.md` (한국어) 하나만:
1. 판정 한 줄: APPROVE / APPROVE-WITH-FOLLOWUPS / REQUEST-CHANGES
2. B3-01~07 종결표
3. 새 발견 표(있으면): ID · 심각도(P1/P2/P3) · `파일:줄` · 입력 상태 → 관찰 결과 · 최소 수정 방향 · **머지 전 필수 여부**
4. 실행한 명령과 출력 마지막 줄

## 진행 규칙
- 질문하지 말고 가정을 적고 진행. 시간 예산 20분. orca CLI 는 이 샌드박스에서 동작하지 않으니 heartbeat·worker_done 은 시도하지 말고, 파일 작성 후 요약 10줄만 출력하고 끝낸다.
