이 작업은 전용 구현 레인에서 호출 시 지정된 모델·reasoning effort 로 실행된다. 그 선택은 의도된 것이며 아무것도 대체되지 않았다.
질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료, 결과는 파일로·stdout 은 요약.

# 배치 3F — 쉼표 뒤 수치 누락 회귀 (RR3-01) — 이것 하나만

## 1. 목표
재리뷰 `F:/Claude/skills/market-deep-research/_planning/council-2026-09-19/review-astra-batch3-rereview.md` 의 RR3-01 을 닫는다.
배치 3D 가 넣은 숫자 시작 경계 `(?<![A-Za-z0-9.,+−-])` 에 쉼표가 들어 있어, `출력은 45mW,999mW(F001)이다.`(대장 `45 mW`)에서 두 번째 수치 `999mW` 가 후보에서 빠지고 G3 가 통과한다. 3D 이전에는 `[값불일치]` FAIL 이었다.
완료 기준: 아래 표가 성립하고 현재 테스트 596개가 전부 통과한다.

| 대장 | 본문 | 기대 |
|---|---|---|
| `45 mW` | `출력은 45mW,999mW(F001)이다.` | `[값불일치]` FAIL |
| `45 mW` | `출력은 45mW, 999mW(F001)이다.` | `[값불일치]` FAIL (지금도 FAIL — 유지) |
| `45 mW` | `출력은 45mW(F001)이다.` | PASS |
| `45999 mW` 또는 기존 천단위 fixture | `45,999mW(F001)` | 천단위 구분으로 하나의 수 — 기존 동작 유지 |
| `45 USD` | `X45 USD` 가 든 문장, 표 행 `\| 매출 \| $45 B2B \| (F001) \|` | 3D 의 식별자 내부 시작 금지·B2B 양성 대조 유지 |
| `1.5 GW` | `1.5 GW(F001)` | 소수 표기 유지 |

## 2. 파일
`codes/market-deep-research/scripts/verify_facts.py` :87, :96, :99 의 시작 경계(같은 후방탐색을 쓰는 세 정규식)만. 테스트는 `tests/test_batch3c_regressions.py` 에 **추가만**.

## 3. 인터페이스 (결정 사항)
쉼표는 "바로 앞이 숫자일 때만" 시작 금지다(천단위 구분 `1,234` 의 중간 재시작 방지). 즉 시작 경계를 `(?<![A-Za-z0-9.+−-])(?<!\d,)` 형태로 나눈다 — 앞 글자가 영숫자·소수점·부호이면 시작 불가, 앞 두 글자가 `숫자+쉼표` 여도 시작 불가, 그 외 쉼표(단위·문자 뒤 쉼표) 뒤에서는 시작 가능. 세 정규식에 동일하게 적용한다. 그 외 파서 동작은 바꾸지 않는다.

## 4. 제약
다른 함수·다른 파일 수정 금지. 기존 테스트 수정·삭제 금지. `git commit`·`push` 금지. 새 의존성·네트워크 금지. 주석은 한국어 한 줄로 이유를 남긴다.

## 5. 검증
```text
cd codes/market-deep-research
python -m pytest -q tests/test_batch3c_regressions.py
python -m pytest -q            # 기준선 596 passed — 0 failed
```

## 6. REASONING: high

## 보고 형식
작업 디렉터리 루트에 `batch3f-report.md`(STATUS / CHANGES / VERIFIED / JUDGMENT CALLS / GAPS, 한국어)를 쓰고, 주입된 프리앰블의 절차대로 `worker_done` 을 보낸다.
