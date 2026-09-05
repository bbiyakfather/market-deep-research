# SPEC — 배치 2B fixup: 리뷰 발견 R1·R2·R3 수정

REASONING: high

## 배경
`scratchpad/review-astra-2b.md` 전문을 먼저 읽어라(발견 3건의 재현·직접 비교·최소 수정안
포함). 이 3건만 고친다. 저장소 `F:/Claude/skills/market-deep-research/codes/
market-deep-research/` 워킹트리(배치 2B 반영, 미커밋). 커밋 금지.

## 수정 항목 (리뷰 최소 수정안 그대로)

### R1 [중대] 링크 뒤 태그 소실 → disputed 통과
- 상태·태그 존재·상충 문맥 검사는 **URL 제거 전 원문 세그먼트**로 수행 — 숫자 오탐 방지용
  URL 제거와 분리. 링크 목적지만 제거하더라도 뒤의 F태그 보존.
- 대조 테스트: 링크에 붙은 태그/띄운 태그 각각 × confirmed 정상·disputed 무마커 실패·
  명시 상충 정상.

### R2 [중대] 부록 disputed 인용의 문장검토 우회
- `verify_claims` 검토 대상에 명시적 disputed 부록 세그먼트 포함 — 문장 일치·
  reviewed_text_sha256·evidence_revision 동일 검사.
- 테스트: 검토 누락 실패·문장 교체 실패·정식 검토 후 통과.

### R3 [중대] Decimal 범위 파싱 회귀 (`.5~.6`·`1e3~2e3`)
- 범위 양 끝 토큰이 선행 소수점·지수 표기(부호 포함)를 수용하게 확장 — 지수 부호와 범위
  구분자를 구별(`1e3~2e3` ok, `1e-3~2e-3` ok, `40-45` ok, `-45~-40` ok).
- 핵심수치 분류(`:689` 부근)도 같은 파서 결과를 쓰므로 함께 복원됨을 테스트로 확인.
- 테스트: 각 표기 × 같은 값 정상·다른 값 실패·부호 불일치 실패.

## 검증 (완료 전 전부, out 파일에 기록)
```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
PYTHONIOENCODING=utf-8 python scripts/gates.py demo
PYTHONIOENCODING=utf-8 python scripts/verify_claims.py --demo
```
+ 리뷰 재현 스크립트 `scratchpad/astra-2b-review-probes.py` 가 있으면 실행해 3건이 이제
차단됨을 보여라(없으면 리뷰 본문의 재현 절차를 재구성).

## 완료 보고
out 파일에: 변경 파일 / 3건별 차단 결과 / 테스트 결과 / 요약 10줄. 질문하지 말고 가정을
적고 진행. stdout 은 요약만. 커밋 금지.
