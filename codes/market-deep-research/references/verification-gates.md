# verification-gates — G0~G5 상세 · 4차원 등급 · claim-graph · 환산

## 4차원 등급 (grade, 각 A~D) — 단일등급 금지
| 차원 | 의미 | A | D |
|---|---|---|---|
| authority | 출처 권위 | 1차 공시·표준·규제기관 | 익명 블로그·미검증 |
| independence | 독립성 | 이해무관 복수 독립집계 | 당사자 자기발표만 |
| directness | 직접성 | 원데이터·원문 직접 | 3차 재인용·요약 |
| recency | 최신성 | 조사시점 기준 최신 | 수년 경과·갱신됨 |

## G0 preflight
`python scripts/preflight.py`(HARD: python·fitz·pandoc·chrome / SOFT: curl_cffi·trafilatura·
insane-search / RUNTIME: playwright MCP·무료 공공 MCP). 요구사항 확정(유형·범위·**축별 충분조건**·
환산옵션 OFF·출력형식·**승인 목차**) — 통과조건: `audit/research-plan.md` 존재 + 승인 기록 +
승인 목차(`references/research-plan.md` 서식) 포함, 확정 전 팬아웃 금지. 기관조사면
`entity-identity.md` 선행. `audit/intent-diff.md` 개시.

## G1 join + 수집 게이트
전 워커 완료/timeout/부분실패 처리 → raw `_research/` 보존 → `facts_db.py` 스키마 검증 등재
(위반은 제한적 재요청). **무출처 즉시 `discarded`**(audit 기록).

## G2 팀리드 재검증(전건) + [Bx] claim-graph
- 전건: 보고서 진입 후보 모든 fact 를 팀리드가 원문 재열람 → `add_verify_event(by="lead")`.
  verifier 단독 confirm 금지. confirmed = ≥1 evidence + lead verify_event(facts_db 강제).
- **claim-graph 게이트(risk=high 만)**: ① ≥2 **독립 관찰그룹**(`observer_group` 상이, 재전재 제외)
  ② **1회 반박검색**(`counter_search.found_stronger_refutation=false`) ③ **기본소스**(`primary_source_ref`)
  ④ **시간증거**(`observed_at`+`valid_at`). 불통과 → `disputed`/Unresolved(기권이 정답, audit 기록).
  판단 근거·순서는 `audit/verification-economics.md`(오류비용 vs 검증비용 vs 잔여위험).

## G2 증빙 게이트
confirmed 전건 `source_capture`(capture_pdf 또는 playwright 실화면). htmlbox 재구성은 **불인정**.
high-risk 핵심수치는 캡처 필수(`verify_facts.py` 가 실재 검사).

## G3 verify_facts + manifest (실패 0)
`verify_facts.py <report.md> <work_dir> [--conversion] [--plan <research-plan.md>]`:
본문/부록 분리(주석 `<!-- FACTSHEET:APPENDIX -->` 우선, 없으면 '## 부록' 헤딩 최후 출현) ·
본문을 문장·표행 세그먼트로 나눠 수치↔(Fxxx) 1:1 최근접 결박(태그 하나가 줄 전체를 면제하지
않음) · 무태그 숫자 차단 · (Fxxx) 존재+confirmed+값·**단위** 의미대조(Decimal 스케일·차원,
불일치 시 `[단위불일치]`/`[값불일치]`) · evidence 필수필드 · text_quote verbatim ·
high-risk 캡처 실재 · **목차 기계검사**(`--plan` 미지정 시 `audit/research-plan.md` 자동탐지,
그마저 없으면 생략 — 계획 파일 없는 기존 조사는 이 검사만으로 FAIL 하지 않음). →
`manifest.py build`(해시 고정 — 이 시점은 report.pdf 생성 전이라
렌더 산출물은 [4] 이후 재봉인에서 추가됨).

## G5c 실행코드 검증(계산·상충)
자체포함 스크립트 실행 → stdout → `audit/verify-<slug>.md`(CONFIRMED/REFUTED/PARTIAL).

## G4 preview → G5 최종 무결성
report.pdf 생성 후 **재봉인**(`manifest.py build` 재실행 — [G3] 항목은 보존한 채 report.pdf 등
렌더 산출물 해시를 추가) → `preview_pdf.py` 육안검증 + **intent-diff 축별 대조**
(`audit/intent-diff.md` 개시분의 축별 "참이어야 하는가" 목록을 실제 보고서 발견과 대조 —
축마다 gap 유무 판정, 결과를 `audit/intent-diff.md` 에 추기) → PDF F태그·링크·캡처 수 재검사
+ `manifest.py verify`(재봉인 기준 — 신규 파일도 실패로 판정).
**복귀 규칙**: 파일 변경 검출 시 G3 복귀. intent-diff gap(개시분 대비 누락 발견) 검출 시
**[E] 확장수렴 루프로 복귀**(gap 난 축만 후속 워커 재스폰 — 축 전건 재조사 아님).

## 환산 옵션(기본 OFF)
ON 시 Decimal 검산(계산식·환율출처·기준일·종가/평균 명시), 표시 반올림 일관, 본문 영어통화단어 0.
`value.decimal` 에 검산값. 오차 표기(±)는 근거 있을 때만.

## 상태 모델
`confirmed`(검증완료) · `pending`(미검증) · `disputed`(정의차·상반 병기) · `superseded`(시계열 갱신,
`last_seen`) · `discarded`(무출처·저품질, `discard_reason`). 단순 저등급 폐기 금지 — disputed/superseded 우선.
