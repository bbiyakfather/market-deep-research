# SPEC — P0 diff 리뷰 지적 4건 수정 (sol REQUEST_CHANGES 반영)

REASONING: high

## 배경

저장소 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 워킹트리에는
P0 결함 수정 diff(미커밋)가 있다. 교차 리뷰(`scratchpad/review-sol-p0.md` — 전문을 먼저
읽어라)가 REQUEST_CHANGES 4건을 냈다. 이 4건만 고친다. 다른 리팩터·신규 기능 금지.
원 스펙 `spec-p0-fixups.md` 와 같은 폴더의 `spec-p0-fixes.md` 의 §4 제약(신규 의존성 금지·
이중구현 금지·v3 하위호환·Decimal·utf-8·커밋 금지)은 그대로 유효하다.

## 수정 항목 (리뷰 번호와 일치)

### 1. [치명] 공개 record_script_result 로 소유 게이트(G3·[4b]·G5) 영수증 위조 가능
- `gates.py`: 범용 `record_script_result()` 는 `SCRIPT_OWNED` 게이트의 **성공 기록을 무조건
  거부**한다(실패 기록은 허용 — 실패 이력 보존 원칙 유지).
- 소유 스크립트(verify_facts·render_pdf·manifest)가 쓰는 전용 기록 경로를 둔다. 전용
  경로는 결박값(manifest_sha256 등)을 **호출자 extra 로 주입받지 말고 디스크에서 자체
  재계산·검증**한 뒤 기록한다. 같은 프로세스 신뢰 한계(원장 직접 편집 가능)는 이미 문서화된
  기지 사항 — 목표는 "정상 API 조합만으로 우회"를 막는 것이다.
- 부정 회귀 테스트: 검증·렌더를 건너뛰고 영수증 API 만 호출해 finalize 를 시도 → 최종 출고
  실패를 assert.

### 2. [치명] G3 가 검사한 원고와 봉인·렌더하는 원고가 다를 수 있음
- `verify_facts.py` CLI 진입 시 `Path(args[0]).resolve() == WorkPaths(args[1]).report_md
  .resolve()` 강제, 불일치 exit 1 (명확한 한국어 오류 메시지).
- 회귀 테스트: 같은 작업폴더에 clean.md(대장 일치)/report.md(미지원 주장) 를 두고
  `verify(clean.md, work)` 가 거부되는지 assert.

### 3. [중대] revision_id 없는 v3 구형 영수증 일괄 무효화 — 스펙 §4 하위호환 위반
- `gates.py _receipt_issues`: 작업폴더가 순수 v3(대장에 schema_version 없음)이고 영수증에
  revision_id 가 없으면 legacy 형식으로 해석 — 기존 refs/결박 검사는 유지하고 revision 검사만
  WARN. 신규 발급 영수증부터 revision_id 필수.
- 회귀 테스트: 구형(revision_id 없는) G0→G5 원장을 합성해 v3 작업폴더에서 require_receipt/
  finalize 가 통과하는지, v4 작업폴더에서는 거부되는지 둘 다 assert.

### 4. [경미] SKILL.md 3번 원칙이 "미확인 사항 고객 표시" 규칙과 충돌
- SKILL.md 3대 원칙 3번을 리뷰 제안대로 좁힌다: "실패 URL·운영 로그·비핵심 반박 상세는
  내부 audit. 의사결정에 영향을 주는 미확인 조건·반론은 고객 문서에도 표시." (2줄 이내,
  슬림 유지)

## 검증 (완료 전 전부, out 파일에 결과 기록)

```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q      # 기존 106 + 신규 부정 테스트 전부 통과
PYTHONIOENCODING=utf-8 python scripts/gates.py demo
PYTHONIOENCODING=utf-8 python scripts/verify_calculations.py --demo
PYTHONIOENCODING=utf-8 python scripts/verify_claims.py --demo
```

## 완료 보고
out 파일에: 변경 파일 목록(git diff --stat 신구 비교) / 리뷰 4건별 반영 방식 1줄 /
테스트 결과 / 요약 15줄. 질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료.
stdout 은 요약만. 커밋 금지.
