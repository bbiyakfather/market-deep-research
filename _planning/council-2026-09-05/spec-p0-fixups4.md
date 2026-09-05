# SPEC — P0 fixup 4차: 출고 판정의 스냅샷 결박·상태 표시 신뢰·plan 통일 (최종 라운드)

REASONING: high

## 배경

`scratchpad/review-astra-rereview2.md` 전문을 먼저 읽어라. finalize 실검증 전환은 인정됐고
(검사 목록 동일·가짜 PDF 차단·정상 경로 유지·퇴행 없음), 남은 3건만 고친다. **이번이 마지막
수정 라운드다** — 리뷰가 지적한 이론적 잔여 한계(무제한 동시 쓰기·프로세스 밖 행위)는 코드가
아니라 신뢰 경계 문서화로 종결한다. 저장소: `F:/Claude/skills/market-deep-research/codes/
market-deep-research/` (워킹트리 = fixup 3차 반영본). 기존 스펙 제약 유효.

## 수정 항목

### 1. [P1] 판정을 불변 스냅샷에 결박 (리뷰 3항 I3)
- finalize 는 실검증 완료 후, 봉인 대상 전체(manifest entries + 정규 report.md·report.pdf·
  검증이 읽은 claim-review·plan)를 **재해시해 검사 전 해시와 대조** — 불일치면 실패
  ("검증 중 입력 변경"). 현재는 refs 3개만 재대조(`manifest.py:315`·`:327`).
- G5 성공 영수증에는 그 **스냅샷 해시 집합**을 기록하고, 계약을 문서에 명시: "출고 판정은
  이 해시 집합이 가리키는 리비전에 대한 것이다. 이후 파일 변경은 status/재verify 가 드리프트
  로 탐지한다." (검사-기록 원자성 락은 만들지 않는다 — 단일 작업자 전제를 문서화)

### 2. [P1] status 의 최종 상태 표시 신뢰 (리뷰 4항 [P1])
- `final_verification`(및 그 요약 해시 필드)을 `_record_script_result` 의 **extra 예약
  필드로 승격**해 외부 주입을 거부. finalize 만 내부 전용 파라미터로 기록할 수 있게 한다.
- status/publication_state 는: G5 영수증의 스냅샷 해시가 현재 파일과 일치할 때만
  "최종(판정시점)" 을 표시하고, 표시 옆에 근거(원장 기반, 재확인은 `manifest.py verify`)를
  명시. 위조 조합(리뷰의 forged_status 재현)을 부정 테스트로 고정.

### 3. [P2] 승인 계획 경로 통일 (리뷰 1항 [P2])
- 기록 경로(`verify_and_record`)는 **정규 `audit/research-plan.md` 만** 사용 — custom plan
  인자는 check_only(진단) 전용으로 제한하고, 기록 경로에서 custom plan 이 오면 거부.
- G3 refs 에 `audit/research-plan.md` 해시 포함(현재 최종 refs 에만 있음 → G3 결박에 추가).
- 리뷰의 plan_option 재현을 부정 테스트로 고정(정규 계획과 다른 계획으로 통과시킨 검증이
  최종 출고로 이어지지 않음).

### 4. 신뢰 경계 문서화 (리뷰 2항 한계 명시 포함)
`references/verification-gates.md` G5 절에 4~6줄:
- 단일 작업자 전제(검증 중 동시 쓰기 없음), 판정은 스냅샷 해시 집합 기준.
- G5 PDF 검사는 형식·개수 기반(F태그·링크·캡처 수) — **내용 동일성은 보장하지 않으며
  그 확인은 G4 팀리드 육안검증의 역할**임을 명시.
- 같은 프로세스 권한의 원장·기록 위조는 신뢰 경계 밖이되, 출고 판정(`manifest.py verify`)은
  영수증이 아닌 실검증으로 계산되므로 위조 기록이 판정을 바꾸지 못함.

## 검증 (완료 전 전부, out 파일에 기록)
```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
PYTHONIOENCODING=utf-8 python scripts/gates.py demo
PYTHONIOENCODING=utf-8 python scripts/verify_calculations.py --demo
PYTHONIOENCODING=utf-8 python scripts/verify_claims.py --demo
```
+ 리뷰의 forged_status·plan_option 재현이 이제 차단됨을 실행 결과로 보여라.

## 완료 보고
out 파일에: 변경 파일 / 재현 차단 결과 / 테스트 결과 / 요약 10줄. 질문하지 말고 가정을
적고 진행, 막히면 막힌 곳을 적고 종료. stdout 은 요약만. 커밋 금지.
