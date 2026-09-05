---
name: market-deep-research
description: >-
  증빙형(evidence-based) 시장조사 보고서 생성 오케스트레이터. 팀리드(메인 세션)가 병렬
  조사 서브에이전트를 지휘하고, 보고서 진입 전 모든 사실을 원문 재열람으로 전건 재검증하며,
  [사실 → 출처 → 화면캡처] 증거구조로 "조사마다 수치가 달라지는 문제"를 제거한 팩트시트
  PDF(+내부 audit 번들)를 만든다. 유료 API(firecrawl/tavily) 무의존 자체 수집 스택을
  코어로 쓰며, 강방어 사이트 우회(도메인 라우팅·모바일 지문·RSS·OGP)를 코어에 내장한다.
  사용 시점 — "증빙/캡처 포함
  시장조사 보고서", "기술동향·산업동향·기관/기업 실사·기술사업화 실사", "근거 있는 딥리서치
  PDF", "N개 대상 비교·실태·실적·딜 조사". 제외 — 단순 사실확인·한두 출처 요약(WebSearch 직접).
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

작업폴더는 `scripts/skill_paths.py` 가 `research_<주제>_<YYYYMMDD>/` 아래에 생성한다. 모든 스크립트는 `skill_paths` 를 import 하므로 실행 위치와 무관하게 경로가 해석된다.

---

## 오케스트레이션 — 게이트 파이프라인 G0~G5

각 게이트 상세는 `references/verification-gates.md`. 서브에이전트 프롬프트·반환 마커는 `references/agent-briefs.md`.
조사원 = sonnet(병렬·저비용, background). 재검증·종합 = 메인 세션.

```
[G0] preflight ─ 도구/의존성 점검 + 요구사항 확정 + intent-diff 개시
[1]  병렬 조사 ─ 조사원 에이전트 팬아웃(sonnet·background·에이전트별 임시폴더)
[E]  확장→수렴 ─ EXPAND 리드 dedup → 후속워커 → 수렴까지 반복        【v3-A】
[G1] join 게이트 ─ raw 보존 · 스키마검증 등재 · 무출처 즉시 discarded
[2]  팀리드 재검증 ─ ★전건 원문 재열람 → verify_event(by=lead)
[Bx] 반박·claim-graph ─ high-risk 주장: 독립그룹·반박검색·기본소스·시간증거  【v3-B】
[G2] 증빙 게이트 ─ confirmed 전건 source_capture(핵심수치 필수)
[3]  보고서 작성 ─ 고객 report.md(11부) + 내부 audit 번들 동시
[G3] verify_facts + manifest ─ 실패 0 · 무태그·단위 차단(세그먼트 결박) · 해시 고정
[G5c]실행코드 검증 ─ 계산·상충 주장 스크립트 실증(CONFIRMED/REFUTED)   【v3-G5】
[4]  render_pdf ─ GitHub 스타일 오프라인 PDF
[4b] 재봉인 ─ extend-only(기존 항목 불변 확인 실패 시 거부=G3 복귀, 렌더 산출물만 추가, G3 기준선 해시 대조)
[G4] preview ─ 팀리드 육안검증(fitz 이미지 Read)
[G5] 최종 무결성 ─ PDF F태그·링크·캡처 수 재검사 + manifest 재확인
```

### [G0] preflight + 요구사항 확정
- **의존성 점검**: `python scripts/preflight.py` 실행, 상세는 `verification-gates.md` G0 절.
- **요구사항 확정**(사용자 승인): 조사유형(기술동향/산업동향/기관·기업 실사/기술사업화 실사)·범위·**축별 충분조건**·환산옵션(기본 OFF)·출력형식·**승인 목차**(`references/research-plan.md` 서식). 확정 결과는 `audit/research-plan.md` 에 기록(승인 전 팬아웃 금지 — 병렬 조사원 스폰은 확정 후에만).
- **기관·기업 조사면** `references/entity-identity.md` 동일성 게이트를 먼저 통과(법인명·사업자/법인번호·주소·이전상호·해외ID)해 조사 대상을 확정.
- **intent-diff 개시**: `audit/intent-diff.md` 에 "요청 의도가 참이라면 무엇이 참이어야 하는가"를 축별로 기록(G4 에서 발견과 대조해 gap 종결). 【v3-D】
- **영수증**: 승인 후 `python scripts/gates.py record G0 <work_dir> --evidence "..." --refs ...`를 기록하고 `check G0`로 refs를 재검사한다.

### [1] 병렬 조사 → [E] 확장·수렴  【v3-A】
- 조사 분할: **기관·기업**=대상 2~3개/에이전트(entity-identity 선고정, 대상별 축=일반현황/사업현황/재무실적 전건 조사) · **기술동향**=축분할(기술요소·플레이어·시장·정책 + 교차검증1) · **산업동향**=밸류체인 + 통계(KOSIS/DART/KIPRIS 기존 스킬 조합) + 해외 · **기술사업화 실사**=축분할(기술성·권리성·시장성·사업성, 5부 공급·수요 이중매핑은 별도).
- 워커는 에이전트별 `_research/<agent>/` 임시폴더에만 쓴다(파일충돌 방지). **읽기전용**(공식 대장 미기록) — 반환은 마커로. 【v3-F】
- 반환 마커(`agent-briefs.md`): evidence 스키마 JSONL + `## CLAIMS`(CLAIM/RISK/SOURCES/COUNTER/PRIMARY) + `## EXPAND`(LEAD/WHY/ANGLE, DEAD END) + `## FIGURES`(원문 도판 위치·캡션) + `## 인사이트`(사실/추론 구분, 근거 F-ID) + `## 요약`.
- **확장수렴 루프**: 팀리드가 EXPAND 리드를 `AXIS` 필드 기준으로 `audit/expansion-log.md` 에 축별 집계(dedup, 미확인 리드 포함) → 새 리드마다 후속 워커 즉시 스폰. **루프 수렴조건**(G0 에서 사용자와 합의하는 **축별 충분조건**과는 별개 개념 — 전자는 이 루프 자체의 정지조건, 후자는 워커에게 전달되는 조사 깊이 기준): **축별 잔여 리드 각 0**(한 축이라도 잔여 리드가 남으면 미수렴), 또는 연속 2웨이브 무신규, 또는 깊이캡(기본 3회/12명, `research-plan.md` 확정값이 있으면 그 값 우선) 도달(도달 시 사용자에 연장 문의). 드롭 리드는 로깅.

### [G1] join + 수집 게이트
- 전 에이전트 완료/timeout/부분실패 처리. raw 산출물 `_research/` 보존.
- `scripts/facts_db.py` 로 스키마 검증 등재(위반은 제한적 재요청). **출처 없는 주장은 즉시 `discarded`**(audit 기록). 독립성: 같은 보도자료 재전재는 1출처로 계산(`source_role`).
- **영수증**: join 완료 영수증을 남긴 뒤 `python scripts/gates.py check G1 <work_dir>`로 G1 선행조건을 검사한다.

### [2] 팀리드 재검증 (★전건)
- 보고서 진입 후보 **모든 fact** 를 팀리드가 원문 재열람. WebFetch 403 이면 `fetch.py` 로 한 번 더(사다리 상세: `source-ladder.md`). verbatim/locator 대조 → `db.add_verify_event(by="lead")`.
- confirmed 조건(facts_db 강제): 최소 1 evidence + 팀리드 verify_event. 무출처=confirm 불가.
- **영수증**: 재검증 선언은 `gates.py record [2] <work_dir> --evidence "..."`로 기록하고 `check [2]`로 G0·G1을 확인한다.

### [Bx] 반박검색 + claim-graph 게이트  【v3-B】
- 대상 = `risk:"high"` fact(시장규모·성장률·딜규모·순위 등 오류비용 큰 주장). 근거·순서는 `audit/verification-economics.md` 에 기록.
- 검사: v4 본문 사용 confirmed high-risk는 ① 연결 evidence에서 계산한 ≥2 **독립 관찰그룹**(재전재 제외) · ② **능동 반박검색**(실질 query·result와 더 강한 반박 없음) · ③ 실재 연결된 **기본소스**(`primary_source_ref`) · ④ 유효한 ISO **시간증거**(`observed_at` 또는 `valid_at`)가 전부 필수이며 미충족 시 FAIL. v3는 기존 ①② FAIL·③④ WARN, 본문 미사용은 네 요건 부족 모두 WARN을 유지한다(`verification-gates.md`).
- 반박검색 산출물은 `negative_search` 증거유형으로 결박.

### [G2] 증빙 게이트
- confirmed 전건 `source_capture`. 원본 캡처만 증빙 인정, 재구성 발췌 불인정, 상세: `evidence-capture.md`. 원본 캡처 불가 시 대체출처 or "미확인" 유지. 핵심수치는 캡처 필수.

### [3] 보고서 작성
- 고객용 `report.md`: **11부 표준목차**(표지→Executive→개요→테마별 본론→시장수치→플레이어→검증요약→상충→상태변화→한계·반론→요약·인사이트→부록). 조사유형별 변형은 `report-format.md`.
- 내부 `audit/`: facts 전수·폐기목록+사유·실패소스·검증이력·raw·세션 저널.
- **도판**: 워커 `## FIGURES` 부터 수확, 순서·결박은 `image-research.md`. 0~3 소진 뒤에만 자작 차트.

### [G3] verify_facts + manifest (실패 0)
- `python scripts/verify_calculations.py <work_dir>`: G3 전 CAGR 구간 검산 → `audit/calc-check.json`(원문 보존, 충돌은 미해결로 남김).
- `python scripts/verify_claims.py <report.md> <work_dir>`: 문장·근거 리비전과 검토 대장 검사 → `audit/claim-check.json`(두 검사 모두 G3 내 자동 호출, 신규 위반은 v3 WARN/v4 FAIL).
- `scripts/verify_facts.py` CLI PASS 가 기준 `manifest.json` 을 자동 생성하고 G3 영수증에 `manifest_sha256` 을 결박한다. 검사항목 상세는 `verification-gates.md` G3 절.
- **영수증**: CLI PASS는 G1·[2] 영수증을 확인한 뒤 G3 자기기록을 남기며, 누락 시 fail-closed한다.

### [G5c] 실행코드 검증  【v3-G5】
- 계산·상충·성능 주장은 최소 자체포함 스크립트 실행 → stdout 캡처 → `verify-<slug>.md`(CONFIRMED/REFUTED/PARTIAL). 시장조사 접점: 시장규모=수량×ASP·CAGR·통화환산 Decimal 검산.

### [4] render_pdf → [4b] 재봉인 → [G4] preview → [G5] 최종 무결성
- `render_pdf.py` 로 report.pdf 생성(플래그·한글경로: `report-format.md` 렌더 절).
- **[4b] 재봉인**: `manifest.extend` 만 허용(기존 항목 불변 확인 실패 시 거부 = G3 복귀, 렌더 산출물 artifacts 만 추가, G3 기준선 해시 대조). [G3]의 build 시점엔 report.pdf 가 아직 없어 매니페스트에 없으므로, 렌더 직후 기존 항목을 덮어쓰지 않고 report.pdf 등 렌더 산출물만 추가한다. 재봉인을 건너뛰면 report.pdf 는 변조·삭제해도 [G5] 가 잡지 못한다.
- **영수증**: `render_pdf.py` CLI는 렌더 성공 직후 manifest extend와 [4b] 자기기록을 자동 수행한다. `manifest.py verify`는 [4b]·G4 영수증 없이는 실패하며, [4b] 영수증의 `manifest_sha256` 과 현재 `manifest.json` 해시를 대조(G5 가 [4b]↔manifest 결박을 검사)한 뒤 대조 결과를 **G5 영수증으로 자기기록**한다(실패도 기록 — 실패 이력이 원장에서 사라지지 않게).
- `preview_pdf.py`(fitz 페이지 이미지) 로 팀리드 육안검증 + **intent-diff 축별 대조**(개시분과 실제 발견 대조, 절차·복귀 규칙은 `references/verification-gates.md` G4 절 참조).
- 최종: PDF 에서 F태그·링크·캡처 수 재검사 + `manifest.py verify`(재봉인 기준 — 이 시점부턴 신규 파일도 실패로 판정). 복귀 규칙은 `references/verification-gates.md` 참조(파일 변경/intent-diff gap 각각 다른 복귀처).
- **영수증**: preview 전 `python scripts/gates.py check G4 <work_dir>`로 G0 계획 해시 드리프트를 검사하고, 확인 후 `record G4`로 기록한다.
- **영수증 커버리지**: 원장 영수증은 G0·G1·[2]·G3·[4b]·G4·G5 — 소유 스크립트 게이트(G3·[4b]·G5)는 CLI 손기록이 차단되고 소유 스크립트만 기록한다. G2·G5c 는 원장 대신 내용검사로 강제된다(G2=verify_facts 의 캡처 실재 검사, G5c=`audit/verify-<slug>.md` 산출물).

---

## 참조 문서 (필요할 때만 로드)
| 파일 | 언제 |
|---|---|
| `references/agent-briefs.md` | [1] 워커 스폰 직전(프롬프트·반환 마커·철칙) |
| `references/source-ladder.md` | WebFetch 403 시 · [2] 원문 재열람 · 검색 계층 |
| `references/extract-recipes.md` | 증거유형별 추출·PDF fitz·특수소스 recipe |
| `references/evidence-capture.md` | G2 캡처 직전(source_capture vs reconstructed) |
| `references/report-format.md` | [3] 목차 작성 · [4] 렌더 플래그·한글경로 |
| `references/image-research.md` | [3] 도판 수확 직전 |
| `references/verification-gates.md` | 각 게이트 진입 시(G0~G5 상세·claim-graph) |
| `references/research-plan.md` | G0 조사계획 확정(축·축별 충분조건·깊이캡·승인 목차) |
| `references/entity-identity.md` | 기관·기업 조사 G0 직전(동일성 게이트) |
