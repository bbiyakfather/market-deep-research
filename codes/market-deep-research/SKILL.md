---
name: market-deep-research
description: >-
  증빙형 시장조사 보고서 오케스트레이터. 병렬 조사 서브에이전트 + 팀리드 원문 재열람 전건 재검증,
  [사실→출처→캡처] 증거구조로 팩트시트 PDF 를 만든다. 사용 시점 — "증빙/캡처 포함 시장조사 보고서",
  "기술동향·산업동향·기관/기업 실사·기술사업화 실사", "근거 있는 딥리서치 PDF",
  "N개 대상 비교·실태·실적·딜 조사". 제외 — 단순 사실확인·한두 출처 요약(WebSearch 직접).
---

# market-deep-research — 증빙형 시장조사 보고서

내비온(기술사업화 기관)의 반복 업무(기술동향·산업동향·기관/기업 실사·시장조사)를 위한 스킬.
**AI 확률적 답변으로 조사마다 수치가 달라지는 문제**를, `fact + evidence[]` 증거모델 + 사실대장 + 팀리드 전건 재검증 + 검증게이트로 해소한다.

## 3대 원칙 (절대 규칙)
1. **원문 미확인 수치는 폐기**(추정 금지). 무출처 주장은 대장 등재 불가 = 본문 사용 불가.
2. **팀리드(메인 세션) 전건 재검증**: 보고서에 들어갈 모든 fact 는 팀리드가 원문을 직접 재열람(WebFetch/fetch.py)해 verbatim/locator 대조 후 `verify_event(by=lead)` 기록. 검증 서브에이전트는 보조의견만 — verifier 단독 confirm 금지.
3. **고객용 / 내부 audit 분리**: 실패 URL·운영 로그·비핵심 반박 상세는 내부 audit. 의사결정에 영향을 주는 미확인 조건·반론은 고객 문서에도 표시.
원문 일치 ≠ 주장 성립: 주체·속성·범위·기간·조건을 넘는 표현은 `references/claim-review.md`에 따라 축소·재검토한다.
캡처 존재 ≠ 내용 검증: 이미지 해시에 결박한 `capture_review`가 필요하며 차단·로그인·백지 화면은 증빙 불인정이다.

## 목적별 모드
① 자료/출처/원문만 → 이 스킬이 아니라 `mdr-search`(같은 작업폴더 규칙, 나중에 ② 승격 가능).
② 증빙형 보고서 초안(MD/PDF) → 이 스킬 G0~G5.
③ hwpx 양식화 → `mdr-hwpx`(원고 md → 발주처 양식 hwpx; 부별 모듈 빌드·정합성 검토·합본)
①→② 승격: `_sources/` 스냅샷·`sources.md` 는 재사용, 사실대장은 G1 부터 새로.

## 산출물
- `report.pdf`(고객용, 11부 표준목차 → `references/report-format.md`)
- `audit/`(내부: facts 전수·폐기·실패소스·검증이력·세션 저널·raw agent output·manifest)

작업폴더(WD)는 `scripts/skill_paths.py` 가 `research_<주제>_<YYYYMMDD>/` 아래에 생성한다. 대장·manifest 경로는 `skill_paths` 가 해석하지만 `fetch.py` 는 **현재 폴더** `audit/` 에 로그·스냅샷을 쓰므로 모든 스크립트는 WD 에서 절대경로로 실행한다(스킬 폴더에서 돌리면 조사 원문이 claude-sync 로 푸시된다).

---

## 오케스트레이션 — 게이트 파이프라인 G0~G5

각 게이트 상세는 `references/verification-gates.md`. 서브에이전트 프롬프트·반환 마커는 `references/agent-briefs.md`.
조사원·손일 = sonnet·effort medium(병렬, background; 외부 워커 금지). 재검증·종합 = 메인 세션. 산출물 리뷰는 전역 규칙.

```
[G0] preflight ─ 도구/의존성 점검 + 요구사항 확정 + intent-diff 개시
[1]  병렬 조사 ─ 조사원 에이전트 팬아웃(sonnet·background·에이전트별 임시폴더)
[E]  확장→수렴 ─ EXPAND 리드 dedup → 후속워커 → 수렴까지 반복        【v3-A】
[G1] join 게이트 ─ raw 보존 · 스키마검증 등재 · 무출처 즉시 discarded
[2]  팀리드 재검증 ─ ★전건 원문 재열람 → verify_event(by=lead) + span_tools.py 로 verbatim 행 확정(span)
[Bx] 반박·claim-graph ─ high-risk 주장: 독립그룹·반박검색·기본소스·시간증거  【v3-B】
[G2] 증빙 게이트 ─ confirmed 전건 source_capture(핵심수치 필수)
[3]  보고서 작성 ─ 고객 report.md(11부) + 내부 audit 번들 동시
[G3] verify_facts + manifest ─ 실패 0 · 무태그·단위 차단(세그먼트 결박) · 해시 고정 · [span불일치]·[문장인용없음]·[도판값불일치] 차단 · FAIL 이 있으면 PDF 미생성(기존 report.pdf 보존)
[G5c]실행코드 검증 ─ 계산·상충 주장 스크립트 실증(CONFIRMED/REFUTED)   【v3-G5】
[4]  render_pdf ─ GitHub 스타일 오프라인 PDF
[4b] 재봉인 ─ extend-only(기존 항목 불변 확인 실패 시 거부=G3 복귀, 렌더 산출물만 추가, G3 기준선 해시 대조)
[G4] preview ─ 팀리드 육안검증(fitz 이미지 Read)
[G5] 최종 무결성 ─ PDF F태그·링크·캡처 수 재검사 + manifest 재확인
```

### [G0] preflight + 요구사항 확정
- 목적: `python scripts/preflight.py` 의존성 점검 → §0 독자·목표(`reader-goal.md`) 최선행 확정 → 조사유형·범위·**축별 충분조건**(기술동향 기본값 표·용어 확장표는 `research-plan.md`)·승인 목차를 `audit/research-plan.md` 에 기록, `audit/intent-diff.md` 개시 【v3-D】.
- 절대 규칙: **승인 전 팬아웃 금지**. §0 은 승인 후 동결(교체는 intent-diff `현행 메시지:` 줄). 기관·기업이면 `entity-identity.md` 동일성 게이트 선통과, 경쟁이 핵심이면 `competitive-positioning.md`, BM 명제(과금·수요기업·이전 조건)가 핵심이거나 독자 유형이 A/B/C 이면 `business-model.md`(§0·§1·§5 분야 행 + 해당 독자 §, G3 직전 §6).
- 영수증: `gates.py record G0 <work_dir> --evidence "..." --refs <고정 산출물만>` → `check G0`. → `verification-gates.md` §G0 · `research-plan.md`

### [1] 병렬 조사 → [E] 확장·수렴
- 조사 분할: **기관·기업**=대상 2~3개/에이전트(entity-identity 선고정, 대상별 축=일반현황/사업현황/재무실적 전건 조사) · **기술동향**=축분할(기술요소·플레이어·시장·정책 + 교차검증1) · **산업동향**=밸류체인 + 통계(KOSIS/DART/KIPRIS 기존 스킬 조합) + 해외 · **기술사업화 실사**=축분할(기술성·권리성·시장성·사업성, 5부 공급·수요 이중매핑은 별도).
- 워커는 `_research/<agent>/` 에만 쓰고 대장은 기록하지 않는다(읽기전용). 검색은 `search.py --axis <축>` 으로 호출해 `audit/search-log.jsonl` 에 전건 기록(2부 커버리지 선언의 근거). 【v3-F】 스폰 첫 줄은 `0. 독자·목표`. 반환 마커 6종·스폰 계약은 `agent-briefs.md`.
- **확장수렴 루프**: 팀리드가 EXPAND 리드를 `AXIS` 필드 기준으로 `audit/expansion-log.md` 에 축별 집계(dedup, 미확인 리드 포함) → 새 리드마다 후속 워커 즉시 스폰. **루프 수렴조건**(G0 에서 사용자와 합의하는 **축별 충분조건**과는 별개 개념 — 전자는 이 루프 자체의 정지조건, 후자는 워커에게 전달되는 조사 깊이 기준): **축별 잔여 리드 각 0**(한 축이라도 잔여 리드가 남으면 미수렴), 또는 연속 2웨이브 무신규, 또는 깊이캡(기본 3회/12명, `research-plan.md` 확정값이 있으면 그 값 우선) 도달(도달 시 사용자에 연장 문의). 드롭 리드는 로깅. **증거 기반 종료**: 축별 충분조건 논점마다 span 대조를 통과한 confirmed fact ≥1, 미충족 축은 미수렴(G3 `[축근거부족]` WARN).

### [G1] join + 수집 게이트
- **무출처 즉시 `discarded`**, 같은 보도자료 재전재는 1출처. 영수증: join 영수증을 남긴 뒤 `gates.py check G1 <work_dir>`. → `verification-gates.md` §G1

### [2] 팀리드 재검증 (★전건)
- 보고서 진입 후보 **전건**을 팀리드가 원문 재열람(403 이면 `fetch.py`) → `add_verify_event(by="lead")`. **verifier 단독 confirm 금지**, 무출처=confirm 불가. WebFetch 요약 답은 재확인 근거가 아니다 — 원문에서 문자열 검색.
- 영수증: `gates.py record [2] <work_dir> --evidence "..."` → `check [2]`. → `verification-gates.md` §[2]+[Bx] · `agent-briefs.md` 철칙

### [Bx] 반박검색 + claim-graph 게이트
- `risk:"high"` fact 대상. v4 본문·부록 인용 confirmed high-risk 는 독립 관찰그룹 ≥2 · 능동 반박검색 · 기본소스 · 시간증거 전부 필수, 미충족 FAIL. 영수증 없음(G3 가 검사). → `verification-gates.md` §[2]+[Bx] · `audit/verification-economics.md`

### [G2] 증빙 게이트
- 원본 캡처만 증빙 인정, 재구성 발췌 불인정, 핵심수치는 캡처 필수. 영수증 없음(`verify_facts` 의 캡처 실재 검사로 강제). → `verification-gates.md` §G2 · `evidence-capture.md`

### [3] 보고서 작성
- `report.md`(11부·`report-format.md`)와 `audit/` 동시 작성. 납품 원고는 분리(`mdr-hwpx/references/deliverable-rules.md`, 관점·말투 `reader-goal.md`)하고 재작성 뒤 **의미 대조 검수**(단정 강화·주체 바뀜·방향 반전). 요약·각 장·10부 권고가 '독자의 결정'에 답하는지 점검(`reader-goal.md` 운용 규칙 3), 금지 서술 grep 0건.
- 도판 `image-research.md`(자작 차트는 `make_chart.py --engine flint` — 내장 flint-py 16종, 사이드카 `.vl.json` 이 G3 값 대조 대상) · 수치는 그림 기본, 표로 남기면 형식 matrix/A/B 와 캡션 태그 `visual-first.md` §2b(`visual_audit.py` 미결 0건 = G4 조건).

### [G3] verify_facts + manifest (실패 0)
- `verify_calculations.py`·`verify_claims.py` 는 G3 가 자동 호출. 근거의 인용·출처·캡처를 바꾸면 그 문장을 다시 검토한다(`claim-review.md`).
- 영수증: `verify_facts.py <report.md> <work_dir>` PASS 가 manifest 를 만들고 G3 영수증에 결박(손기록 불가). → `verification-gates.md` §G3

### [G5c] 실행코드 검증
- 계산·상충·성능 주장은 자체포함 스크립트로 실증 → `audit/verify-<slug>.md`(CONFIRMED/REFUTED/PARTIAL). → `verification-gates.md` §G5c

### [4] render_pdf → [4b] 재봉인 → [G4] preview → [G5] 최종 무결성
- [4] `render_pdf.py`(`report-format.md` 렌더 절)가 렌더 직후 manifest extend·[4b] 를 자동 기록. [4b] 재봉인은 **extend-only**(기존 항목 불변 확인 실패 시 거부 = G3 복귀, 렌더 산출물만 추가).
- [G4] `gates.py check G4 <work_dir>` → `preview_pdf.py` 육안검증 + intent-diff 축별 대조 + 독자 테스트(`reader-goal.md`) + 대장→원고 역방향 고아 검사 → `record G4`. 캡처·도판은 리드가 눈으로 연다.
- [G5] `manifest.py verify` 가 PDF F태그·링크·캡처 수를 재검사하고 G5 자기기록. 새 조사는 v4, 순수 v3 는 `--allow-legacy-v3` 를 명시해야만 통과(영수증에 `legacy_v3`, ≠ v4 검증 완료). 영수증 커버리지·복귀 규칙·v3→v4 이행 → `references/verification-gates.md`

---

## 참조 문서 (필요할 때만 로드)
| 파일 | 언제 |
|---|---|
| `references/reader-goal.md` | G0 최선행 · [3] 귀결 점검 · G4 독자 테스트 |
| `references/agent-briefs.md` | [1] 워커 스폰 직전 · [2] 서지·수치 철칙 |
| `references/source-ladder.md` | WebFetch 403 · [2] 원문 재열람 · 학술 검색 시 `references/academic-apis.md` |
| `references/extract-recipes.md` | 증거유형별 추출·특수소스 recipe |
| `references/evidence-capture.md` | G2 캡처 직전 |
| `references/claim-review.md` | G3 문장·근거 검토 |
| `references/report-format.md` | [3] 목차·audit 번들 · [4] 렌더 · TRL 판정 시 `references/trl-evidence.md` |
| `references/image-research.md` | [3] 도판 수확 직전 |
| `references/visual-first.md` | [3] 표 만들기 직전(그림 vs 표 결정표) · G4 시각화 판정 |
| `references/verification-gates.md` | 각 게이트 진입 시 · 참조문서 운영 규약(말미) |
| `references/research-plan.md` | G0 조사계획 확정 |
| `references/entity-identity.md` | 기관·기업 조사 G0 직전 |
| `references/competitive-positioning.md` | 경쟁·포지셔닝 핵심 시 G0 · 경쟁 챕터 직전(의료기기·IVD 는 §6) |
| `references/business-model.md` | BM 명제가 핵심이거나 독자 A/B/C 일 때 G0(§0·§1·§5 분야 행 + 해당 독자 §) · 5부 수요 표·9부 미닫힘 직전 · G3 직전 §6 금지 서술 grep |
