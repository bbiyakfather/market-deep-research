# SPEC — 배치 2B: 검증 정밀도 강화 (적대적 리뷰 N07·N08·N09·N10·N11·N18·N19·K06 + 잔존 확인)

REASONING: xhigh

## 배경

저장소 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` (HEAD=45f239e,
워킹트리 깨끗). 품질보증 리뷰 `_planning/council-2026-09-05/review-astra-2.md` 의 결함 중
검증 정밀도 계열을 고친다 — 해당 결함 절(N07·N08·N09·N10·N11·N18·N19·K06)을 먼저 읽어라.
재현 절차·파일:라인 근거가 있다. 커밋 금지 — diff 로 남겨라.

주의: P0 수정(claim-review·capture_review·verify_calculations·출고 실검증)과 배치 2A 가
이미 반영돼 있다. 리뷰의 파일:라인은 당시 기준이라 지금과 어긋날 수 있다 — 현재 코드에서
재확인 후 수정하라.

## 수정 항목

### N07 [중대] 음수 부호 소실
- `verify_facts.py`: 본문 숫자 파서에 부호 인식 추가, 대장 `_vals` 의 하이픈 range 분리가
  선행 부호를 삼키지 않게(예: `-45`, `-45~-40`, `45`, `40-45` 모두 정확 파싱).
  대장↔본문 비교에서 부호 보존. 부호 불일치 = FAIL.

### N08 [중대] SI 접두사 대소문자·µW 누락
- `verify_facts.py` 단위 해석: 접두사 대소문자 보존(m=milli, M=mega 구분), `µW`/`uW`/`mW`/
  `W`/`kW`/`MW`/`GW` 및 `Wh` 계열 명시 정규화. 본문 정규식의 re.I 가 단위 접두사를
  뭉개지 않게(단위 토큰만 case-sensitive 매칭). `45 mW` vs `45 MW` = FAIL.
  ※ 기존 대소문자 무관 단위(USD 등 통화·개수 단위)는 동작 유지.

### N09 [중대] 경량 스키마 타입 미검사 잔존
- `facts_db.py` 검증기: 스키마에 선언된 `type`(array/object/string/number/boolean) 실검사,
  배열 item 타입, 이벤트 구조(`at` ISO 형식 등), 공백/빈 값 거부를 v4 에서 강제(v3 legacy
  는 WARN 경로 유지). 특히 `independent_groups` 문자열("AB")이 그룹 2개로 세지는 것 차단
  — 배열 강제.
- `verify_facts.py` 고위험 검사: `counter_search.query` 공백 truthiness → 실질 검사,
  `valid_at`/`observed_at` 날짜 형식 검사.

### N10 [중대] F↔E 역참조 미검사
- G3 전체 대장 검증에서 양방향 검사: F.evidence_ids 의 E 존재(기존) + `E.fact_id == F.id`
  일치 + E→F 존재. 공유 evidence 를 허용할 거면 그 모델을 명시(문서 1줄)하고 검사도 그에
  맞게. 불일치 = v4 FAIL / v3 WARN.

### N11 [중대] claim_key 손실 치환·재계산 없음
- `facts_db.py make_claim_key`: `|`→`/` 손실 치환 대신 무손실 직렬화(구분자 이스케이프 또는
  JSON 직렬화 해시). 키 구성에 `entity_id`·`definition` 포함(entity-identity.md 계약 일치).
- `add_fact`: 제공된 claim_key 를 신뢰하지 말고 재계산 대조 — 불일치 거부.
- `diff_facts`: 중복 키 검출(마지막 행 덮어쓰기 금지 — 오류로).
- 오류 메시지가 지시하는 `merge_evidence` — 실제 구현하거나 메시지에서 제거(존재하지 않는
  API 안내 금지).
- ※ 키 산식 변경은 기존 v3 대장과의 호환에 영향 — v3 대장의 기존 키는 legacy 로 인정하고
  v4 신규 등재부터 새 산식 강제. 이행 규칙을 verification-gates.md 에 2줄.

### N18 [중대] 부록 마커 앞당김으로 검사 완화
- `verify_facts.py`: 부록 마커 위치를 승인 목차(research-plan)의 부록 헤딩과 결박 — 마커
  뒤에 본문 성격 헤딩(Executive/결론/요약 등 목차상 본문 장)이 나오면 FAIL. 부록 뒤 무태그
  수치 완화는 유지하되, 목차에 없는 장이 부록 구역에 나타나면 FAIL.

### N19 [중대] disputed 병기 금지 → 정식 통로 신설
- `report-format.md` 가 요구하는 상충 절 병기를 코드가 허용하게: 명시적 disputed 문맥
  표기(예: 세그먼트에 `[상충]` 마커 또는 disputed 전용 태그 표기 — 네가 기존 표기 체계와
  가장 정합적인 방식을 골라 문서화)에서만 disputed fact 태그 인용 허용. provenance 검사
  (값·단위·출처 결박)는 동일하게 적용, 일반 본문에서의 disputed 인용은 계속 FAIL.
  `report-format.md`·`verification-gates.md` 에 표기법 명시.

### K06 [중대] high-risk 판정 강도 문서↔코드 불일치
- SKILL.md:85 는 "전부 필수" 인데 구현은 일부 WARN. **코드를 문서에 맞춘다**: v4 에서
  high-risk confirmed 본문 사용 fact 는 ①독립 관찰그룹 ≥2(원출처·전재 관계 기반 — 
  evidence 의 observer_group/source_role 과 조인해 실질 계산, 자기신고 배열만으로 불인정)
  ②counter_search 실질 기록 ③primary_source_ref 실재(E-ID 존재 검사) ④시간증거 — 
  전부 FAIL 강제. v3 은 현행 WARN 유지. risk 미표기 회피는: 시장규모·성장률·딜규모·순위
  metric 휴리스틱으로 risk=normal 인데 high 패턴이면 WARN(자동 승격은 하지 않되 표면화).

### 잔존 확인 3건 (수정 아닌 검증 — 테스트로 고정)
- N04(조상 게이트 실패 후 G5 재통과)·N05([2] 후 claim/context 교체)·N13(캡처 실패 재시도
  후 옛 PNG 잔존): P0 수정으로 이미 차단되는지 리뷰의 재현 절차대로 테스트를 작성해 확인.
  차단되면 회귀로 고정만, 잔존하면 최소 수정(발견 내용을 out 에 명시).

## 제약
- 기존 테스트 210개 + 데모 3종(gates/calc/claims) + preflight 통과 유지. 신규 항목별 부정
  +정상 테스트. 신규 의존성 금지, 이중구현 금지, v3 legacy 하위호환(WARN) 원칙 유지.
- 정상 사례 보존에 특히 주의: 통화·범위 표기·기존 단위 파싱의 정상 케이스가 부호/단위
  강화로 오탐되지 않게 기존 테스트가 그 회귀망이다.
- Windows·utf-8 패턴 유지. 커밋 금지.

## 검증 (완료 전 전부, out 파일에 기록)
```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
PYTHONIOENCODING=utf-8 python scripts/gates.py demo
PYTHONIOENCODING=utf-8 python scripts/verify_calculations.py --demo
PYTHONIOENCODING=utf-8 python scripts/verify_claims.py --demo
```

## 완료 보고
out 파일에: 변경 파일 / 항목별 반영 1줄 / 잔존 확인 3건 결과 / 테스트 결과 / 요약 15줄.
질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료. stdout 은 요약만.
