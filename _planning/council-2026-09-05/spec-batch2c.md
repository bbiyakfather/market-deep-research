# SPEC — 배치 2C: 대장 원자성·워커 join 계약·출처 provenance·HWPX 인계 (N12·N17·N20·N21)

REASONING: xhigh

## 배경

저장소 `F:/Claude/skills/market-deep-research/` (HEAD=e0b980e, 워킹트리 깨끗).
품질보증 리뷰 `_planning/council-2026-09-05/review-astra-2.md` 의 마지막 결함 4건 —
해당 절(N12·N17·N20·N21)을 먼저 읽어라. P0·배치 2A·2B 가 이미 반영돼 있어 리뷰의
파일:라인은 어긋날 수 있다 — 현재 코드에서 재확인 후 수정. 커밋 금지 — diff 로 남겨라.
코어는 `codes/market-deep-research/`, HWPX 목적 스킬은 `codes/mdr-hwpx/`.

## 수정 항목

### N12 [중대] 두 대장(facts/evidence) 갱신의 원자성
- `facts_db.py`: evidence 저장 성공 후 facts 저장 실패 시 **선기록 롤백**(pre-image 복원)
  으로 두 파일 정합 유지. 파일별 fsync+replace 는 유지.
- `FactsDB` 로드 시 경량 정합 검사(fsck): dangling E(fact 미연결)·역참조 불일치를 v4 FAIL/
  v3 WARN 으로 노출(N10 검사 재사용 — 이중구현 금지).
- 분산 락은 만들지 않는다 — 단일 writer 전제는 이미 문서화됨. 회귀: 두 번째 쓰기 실패
  주입 → 롤백 후 정합 확인.

### N17 [중대] 워커 마커의 join 검증기 (계약을 코드로)
- 신규 `scripts/join_workers.py`: 워커 raw 산출물 파일(들)을 받아 검증하는 CLI+함수.
  - **완전성**: 필수 섹션(EVIDENCE/CLAIMS/EXPAND/FIGURES/인사이트/요약) 전부 존재 —
    누락 섹션은 명시 오류(없음 표기 `없음` 은 유효). `BLOCKED:` 첫 줄 envelope 은 부분
    산출물로 인정하되 결과에 `blocked` 상태로 표시.
  - **EVIDENCE JSONL**: facts-schema 로 행별 검증(facts_db 검증기 재사용), 위반 행 목록.
  - **ID 네임스페이스**: 워커가 적은 F/E-ID 는 잠정 ID 다 — join 결과에 잠정→중앙 재매핑
    표를 만들고, 등재는 팀리드가 `add_fact`/`add_evidence` 로(중앙이 ID 부여). 인사이트의
    F-ID 참조도 재매핑 대상으로 보고.
  - **EXPAND dedup**: `AXIS`+정규화 리드 텍스트로 지문(fingerprint)을 만들어 중복 리드
    식별(이름만 바꾼 재제출 탐지 보조). 완전 동등성 판정은 팀리드 몫 — 지문은 보조 신호로
    문서화.
  - 결과: 파일별 verdict(ok/blocked/invalid) + 오류 목록 JSON. exit: invalid 있으면 1.
- `references/agent-briefs.md`: 마커 계약에 위 envelope 규칙(필수 섹션·BLOCKED·잠정 ID)
  2~3줄 보강. `references/verification-gates.md` G1 절: join 시 이 검증기 실행을 절차로
  명시(G1 영수증 refs 에 join 결과 포함).
- 수렴 카운팅: "무신규 웨이브" 판정은 **ok 워커의 EXPAND 기준**(blocked/invalid 워커는
  무신규로 세지 않음)을 G1/확장수렴 문서에 1줄 명시.

### N20 [중대] 동일 본문 URL 의 provenance 덮어쓰기
- `fetch.py` save: 같은 raw 해시라도 **URL 별 조회 기록 보존** — meta 에 `urls` 배열
  누적(덮어쓰기 금지) 또는 URL 해시 기반 별도 기록. 어느 쪽이든 기존 meta 스키마와의
  하위호환을 지켜라(기존 소비자: source_index).
- `source_index.py`: blob 1행이 아니라 **URL 단위 provenance** 를 표에 반영(같은 본문을
  가진 URL 집합 표시 — 전재 관계 후속조사 입력). 상태 열(2A)은 유지.

### N21 [중대] 코어 보고서 → HWPX split 의 침묵 서문화
- `codes/mdr-hwpx/scripts/build_hwpx.py split`: 로마숫자 부 헤딩이 **0개면 exit 1** +
  안내 메시지(코어 11부 목차 → 로마숫자 부 변환 절차 참조). `--expect-parts N` 옵션:
  분할 결과가 N 과 다르면 실패.
- 코어→HWPX 인계 절차를 `codes/mdr-hwpx/SKILL.md` 에 3~4줄: 코어 report.md 의 11부
  목차를 로마숫자 부 헤딩으로 매핑하는 규칙(어느 장이 Ⅰ~Ⅺ 인지)과 split 전 확인 명령.
  변환 자동화 스크립트는 만들지 않는다(원고 수준 조작은 사람+빌더 계약) — 실패를 침묵에서
  명시로 바꾸는 것이 목표.

## 제약
- 기존 테스트 399개 + 데모 3종 + preflight 통과 유지. mdr-hwpx 는 `tests/test_hwpx.py`
  가 있으면 그것도(한글 COM 필요 테스트는 건너뛰어도 됨 — 기존 skip 정책 따름).
- 항목별 부정+정상 테스트. 신규 의존성 금지, 이중구현 금지, v3 legacy WARN 원칙 유지.
- Windows·utf-8 패턴. 커밋 금지.

## 검증 (완료 전 전부, out 파일에 기록)
```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
PYTHONIOENCODING=utf-8 python scripts/gates.py demo
PYTHONIOENCODING=utf-8 python scripts/join_workers.py --demo
cd ../mdr-hwpx && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```

## 완료 보고
out 파일에: 변경 파일 / 항목별 반영 1줄 / 테스트 결과 / 요약 15줄. 질문하지 말고 가정을
적고 진행, 막히면 막힌 곳을 적고 종료. stdout 은 요약만.
