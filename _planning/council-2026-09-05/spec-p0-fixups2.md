# SPEC — P0 fixup 2차: 전용 기록 경로를 소유 작업 실행에 결박 (astra 최종 리뷰 발견 1)

REASONING: high

## 배경

저장소 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 워킹트리의
P0 diff(미커밋)에 대한 최종 리뷰 `scratchpad/review-astra-final.md` 가 치명 1건을 남겼다
(전문을 먼저 읽어라 — 재현 코드 A·B 포함). **이 1건만 고친다.** ②③④ 해소분·기타 구현은
건드리지 않는다. 기존 스펙 제약(`spec-p0-fixes.md` §4) 유효.

## 수정 내용 (리뷰 최소 수정안 그대로)

- `gates.py` 의 `_record_owned_result` 처럼 **디스크 해시 일치만으로 성공을 발급하는 전용
  경로를 제거**하거나 소유 작업 완료 없이는 발급 불가로 바꾼다:
  - **G3**: 정규 원고에 기존 `verify_facts.verify()` 를 실행해 **PASS 인 경우에만** 봉인·
    기록하는 단일 진입점으로 묶는다. 호출자가 결과 요약을 임의로 넣을 수 없다.
  - **[4b]**: 기존 `render_pdf.render()` 를 실행해 **그 반환 산출물만** extend·기록하는
    단일 진입점으로 묶는다. 렌더 없이 [4b] 성공 발급 불가.
  - CLI(`verify_facts.py`·`render_pdf.py`)도 이 단일 경로를 재사용한다 — 검증·렌더 실행과
    성공 발급이 분리되지 않게. 기존 검사·렌더 구현 재사용(이중구현 금지), 새 의존성 금지.
  - 실패 기록(exit≠0) 은 지금처럼 남길 수 있어야 한다(실패 이력 보존).
- **부정 회귀 테스트 2건** (리뷰 재현 A·B 그대로):
  A) G3 실패 원고 상태에서 전용 경로 호출 조합 → 성공 영수증 미발급 + `finalize_report()["ok"] == False`.
  B) 정상 G3 PASS 후 렌더를 생략하고 가짜 PDF + extend + [4b] 기록 시도 → [4b] 발급 실패 +
  finalize 실패. (기존 테스트 121개는 계속 통과해야 한다 — 정상 경로 테스트가 새 진입점을
  쓰도록 필요한 최소 수정은 허용)

## 검증 (완료 전 전부, out 파일에 기록)

```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
PYTHONIOENCODING=utf-8 python scripts/gates.py demo
PYTHONIOENCODING=utf-8 python scripts/verify_calculations.py --demo
PYTHONIOENCODING=utf-8 python scripts/verify_claims.py --demo
```

## 완료 보고
out 파일에: 변경 파일 목록 / 재현 A·B 가 이제 실패(=차단)함을 보이는 실행 결과 /
테스트 결과 / 요약 10줄. 질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료.
stdout 은 요약만. 커밋 금지.
