---
name: market-deep-research
description: >-
  증빙형(evidence-based) 시장조사 보고서 생성 오케스트레이터. 팀리드(메인 세션)가 병렬
  조사 서브에이전트를 지휘하고, 보고서 진입 전 모든 사실을 원문 재열람으로 전건 재검증하며,
  [사실 → 출처 → 화면캡처] 증거구조로 "조사마다 수치가 달라지는 문제"를 제거한 팩트시트
  PDF(+내부 audit 번들)를 만든다. 유료 API(firecrawl/tavily) 무의존 자체 수집 스택을
  코어로 쓰고, 강방어 사이트는 insane-search 스킬로 위임한다. 사용 시점 — "증빙/캡처 포함
  시장조사 보고서", "기술동향·산업동향·기관/기업 실사", "근거 있는 딥리서치 PDF", "N개 대상
  비교·실태·실적·딜 조사". 제외 — 단순 사실확인·한두 출처 요약(WebSearch 직접).
---

# market-deep-research — 증빙형 시장조사 보고서

내비온(기술사업화 기관)의 반복 업무(기술동향·산업동향·기관/기업 실사·시장조사)를 위한
스킬. **AI 확률적 답변으로 조사마다 수치가 달라지는 문제**를, `fact + evidence[]` 증거모델
+ 사실대장 + 팀리드 전건 재검증 + 검증게이트로 해소한다.

## 3대 원칙 (절대 규칙)
1. **원문 미확인 수치는 폐기**(추정 금지). 무출처 주장은 대장 등재 불가 = 본문 사용 불가.
2. **팀리드(메인 세션) 전건 재검증**: 보고서에 들어갈 모든 fact 는 팀리드가 원문을 직접
   재열람(WebFetch/fetch.py)해 verbatim/locator 대조 후 `verify_event(by=lead)` 기록.
   검증 서브에이전트는 보조의견만 — verifier 단독 confirm 금지.
3. **고객용 / 내부 audit 분리**: 폐기목록·실패URL·미확인 의혹·반박 상세는 고객 PDF 미노출.

## 산출물
- `report.pdf`(고객용, 11부 표준목차 → `references/report-format.md`)
- `audit/`(내부: facts 전수·폐기·실패소스·검증이력·세션 저널·raw agent output·manifest)

작업폴더는 `scripts/skill_paths.py` 가 `research_<주제>_<YYYYMMDD>/` 아래에 생성한다.
모든 스크립트는 `skill_paths` 를 import 하므로 실행 위치와 무관하게 경로가 해석된다.

---

## 오케스트레이션 — 게이트 파이프라인 G0~G5

각 게이트 상세·오인방지 체크는 `references/verification-gates.md`.
서브에이전트 프롬프트·반환 마커는 `references/agent-briefs.md`.

```
[G0] preflight ─ 도구/의존성 점검 + 요구사항 확정 + intent-diff 개시
[1]  병렬 조사 ─ 조사원 에이전트 팬아웃(sonnet·background·에이전트별 임시폴더)
[E]  확장→수렴 ─ EXPAND 리드 dedup → 후속워커 → 수렴까지 반복        【v3-A】
[G1] join 게이트 ─ raw 보존 · 스키마검증 등재 · 무출처 즉시 discarded
[2]  팀리드 재검증 ─ ★전건 원문 재열람 → verify_event(by=lead)
[Bx] 반박·claim-graph ─ high-risk 주장: 독립그룹·반박검색·기본소스·시간증거  【v3-B】
[G2] 증빙 게이트 ─ confirmed 전건 source_capture(핵심수치 필수)
[3]  보고서 작성 ─ 고객 report.md(11부) + 내부 audit 번들 동시
[G3] verify_facts + manifest ─ 실패 0 · 무태그숫자 차단 · 해시 고정
[G5c]실행코드 검증 ─ 계산·상충 주장 스크립트 실증(CONFIRMED/REFUTED)   【v3-G5】
[4]  render_pdf ─ GitHub 스타일 오프라인 PDF
[G4] preview ─ 팀리드 육안검증(fitz 이미지 Read)
[G5] 최종 무결성 ─ PDF F태그·링크·캡처 수 재검사 + manifest 재확인
```

### [G0] preflight + 요구사항 확정
- **의존성 점검**: `python scripts/preflight.py` — python·fitz·pandoc·HeadlessChrome·
  curl_cffi·trafilatura 유무, playwright MCP·insane-search 스킬·무료 공공 MCP(opendart·
  KOSIS·KakaoMap 등) 감지. 미설치 계층은 "건너뜀+경고"로 진행(자체 스택이 보장 코어).
- **요구사항 확정**(사용자 승인): 조사유형(기술동향/산업동향/기관·기업 실사)·범위·**조사
  종료기준**·환산옵션(기본 OFF)·출력형식·**보고서 목차 승인**.
- **기관·기업 조사면** `references/entity-identity.md` 동일성 게이트를 먼저 통과(법인명·
  사업자/법인번호·주소·이전상호·해외ID)해 조사 대상을 확정.
- **intent-diff 개시**: `audit/intent-diff.md` 에 "요청 의도가 참이라면 무엇이 참이어야
  하는가"를 축별로 기록(G4 에서 발견과 대조해 gap 종결). 【v3-D】

### [1] 병렬 조사 → [E] 확장·수렴  【v3-A】
- 조사 분할: **기관·기업**=대상 2~3개/에이전트(entity-identity 선고정) · **기술동향**=축분할
  (기술요소·플레이어·시장·정책 + 교차검증1) · **산업동향**=밸류체인 + 통계(KOSIS/DART/KIPRIS
  기존 스킬 조합) + 해외.
- 조사원 = **sonnet**(병렬·저비용, background). 에이전트별 `_research/<agent>/` 임시폴더에만
  쓴다(파일충돌 방지). 워커는 **읽기전용**(공식 대장 미기록) — 반환은 마커로. 【v3-F】
- 반환 마커(`agent-briefs.md`): evidence 스키마 JSONL + `## CLAIMS`(CLAIM/RISK/SOURCES/
  COUNTER/PRIMARY) + `## EXPAND`(LEAD/WHY/ANGLE, DEAD END) + `## 인사이트`(사실/추론 구분,
  근거 F-ID) + `## 요약`.
- **확장수렴 루프**: 팀리드가 EXPAND 리드를 `audit/expansion-log.md` 로 dedup(미확인 리드
  포함) → 새 리드마다 후속 워커 즉시 스폰. **수렴(유일 종료조건)**: 미확인 리드 0, 또는
  연속 2웨이브 무신규, 또는 깊이캡 도달(도달 시 사용자에 연장 문의). 드롭 리드는 로깅.

### [G1] join + 수집 게이트
- 전 에이전트 완료/timeout/부분실패 처리. raw 산출물 `_research/` 보존.
- `scripts/facts_db.py` 로 스키마 검증 등재(위반은 제한적 재요청). **출처 없는 주장은 즉시
  `discarded`**(audit 기록). 독립성: 같은 보도자료 재전재는 1출처로 계산(`source_role`).

### [2] 팀리드 재검증 (★전건)
- 보고서 진입 후보 **모든 fact** 를 팀리드가 원문 재열람(WebFetch → 차단 시 fetch.py →
  강방어 시 insane-search 위임)하여 verbatim/locator 대조 → `db.add_verify_event(by="lead")`.
- confirmed 조건(facts_db 강제): 최소 1 evidence + 팀리드 verify_event. 무출처=confirm 불가.

### [Bx] 반박검색 + claim-graph 게이트  【v3-B】
- 대상 = `risk:"high"` fact(시장규모·성장률·딜규모·순위 등 오류비용 큰 주장). 근거·순서는
  `audit/verification-economics.md` 에 기록.
- 통과 조건(전부): ① ≥2 **독립 관찰그룹**(재전재 제외) 수렴 · ② **1회 능동 반박검색**
  (`counter_search`, 더 강한 반박 없음) · ③ **기본소스**(공시·표준·원데이터, `primary_source_ref`)
  · ④ **시간증거**(`observed_at`/`valid_at`). 불통과 → `disputed`/`Unresolved` 로 남김(기권이 정답).
- 반박검색 산출물은 `negative_search` 증거유형으로 결박.

### [G2] 증빙 게이트
- confirmed 전건 `source_capture` 생성: 로컬/다운로드 PDF=`capture_pdf.py`(fitz 정확숫자
  하이라이트+크롭), 접근가능 웹=playwright 실화면 스크린샷(최종URL·시각·viewport·locator 결박).
- **재구성 발췌(htmlbox)는 증빙 불인정** → `capture_web.py` 산출물은 `_reconstructed/`(내부용).
  원본 캡처 불가 시 대체출처 or "미확인" 유지. 핵심수치는 캡처 필수.

### [3] 보고서 작성
- 고객용 `report.md`: **11부 표준목차**(표지→Executive→개요→테마별 본론→시장수치→플레이어→
  검증요약→상충→상태변화→한계·반론→요약·인사이트→부록). 조사유형별 변형은 `report-format.md`.
- 내부 `audit/`: facts 전수·폐기목록+사유·실패소스·검증이력·raw·세션 저널.
- **세부주제별 대표 이미지(도판)**: `harvest_images.py` 로 ① 소스 PDF 도판 크롭(출처 자동
  일치·최우선) ② 확보 페이지 이미지 ③ 이미지 검색(openverse·commons) 순 수확 → 팀리드
  육안 선별(Read) → `[그림]` 캡션+출처 결박(`references/image-research.md`). `_images/` 저장.

### [G3] verify_facts + manifest (실패 0)
- `scripts/verify_facts.py`: 본문/생성부록 분리 파싱 · 무태그 숫자·통화·비율·표셀 탐지(태그
  없는 사실주장 차단) · 모든 `(Fxxx)` 대장 존재+status∈{confirmed} + 값·단위·기간·주체 의미
  대조 · evidence 필수필드 누락 0 · source_capture 실재(핵심수치) · [환산 ON] Decimal 검산.
- `scripts/manifest.py build`: source/capture/report/PDF/대장 SHA-256 고정.

### [G5c] 실행코드 검증  【v3-G5】
- 계산·상충·성능 주장은 최소 자체포함 스크립트 실행 → stdout 캡처 → `verify-<slug>.md`
  (CONFIRMED/REFUTED/PARTIAL). 시장조사 접점: 시장규모=수량×ASP·CAGR·통화환산 Decimal 검산.

### [4] render_pdf → [G4] preview → [G5] 최종 무결성
- `render_pdf.py`(pandoc gfm→html --embed-resources → HeadlessChrome --print-to-pdf,
  한글경로 퍼센트인코딩·오프라인). `preview_pdf.py`(fitz 페이지 이미지) 로 팀리드 육안검증.
- 최종: PDF 에서 F태그·링크·캡처 수 재검사 + `manifest.py verify`. **파일 변경 시 G3 복귀.**

---

## 모델 분리 / 자원 재사용
- 조사원 = sonnet(병렬·저비용). 재검증·종합 = 메인 세션(고성능).
- **수집 사다리**(`references/source-ladder.md`): WebFetch → fetch.py(curl_cffi TLS→모바일
  →Jina→Wayback, 보안경계) → **강방어 시 insane-search 스킬 위임**(이중구현 금지). 무료 공공
  MCP(opendart·KOSIS 등)는 있으면 Phase0 1차소스로 기회적 활용(유료 무의존 유지).

## 참조 문서 (필요할 때만 로드)
| 파일 | 언제 |
|---|---|
| `references/agent-briefs.md` | 서브에이전트 프롬프트·반환 마커·철칙 |
| `references/source-ladder.md` | 검색 계층·fetch 폴백·Phase0 API·4계층 성공검증·WAF 정찰 |
| `references/extract-recipes.md` | 증거유형별 추출·PDF fitz·특수소스 recipe |
| `references/evidence-capture.md` | source_capture vs reconstructed_excerpt·메타 결박 |
| `references/report-format.md` | 고객 11부 목차·유형변형·내부 audit 양식 |
| `references/image-research.md` | 세부주제 대표 이미지(도판) 수확·선별·라이선스 |
| `references/verification-gates.md` | G0~G5 상세·4차원 등급·claim-graph·환산 |
| `references/entity-identity.md` | 기관·기업 동일성 확인 게이트 |
