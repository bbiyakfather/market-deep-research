---
name: market-deep-research
description: >-
  증빙형(evidence-based) 시장조사 보고서 생성 오케스트레이터. 팀리드(메인 세션)가 병렬
  조사 서브에이전트를 지휘하고, 보고서 진입 전 모든 사실을 원문 재열람으로 전건 재검증하며,
  [사실 → 출처 → 화면캡처] 증거구조로 "조사마다 수치가 달라지는 문제"를 제거한 팩트시트
  PDF(+내부 audit 번들)를 만든다. 유료 API(firecrawl/tavily) 무의존 자체 수집 스택을
  코어로 쓰고, 강방어 사이트는 insane-search 스킬로 위임한다. 사용 시점 — "증빙/캡처 포함
  시장조사 보고서", "기술동향·산업동향·기관/기업 실사·기술사업화 실사", "근거 있는 딥리서치
  PDF", "N개 대상 비교·실태·실적·딜 조사". 제외 — 단순 사실확인·한두 출처 요약(WebSearch 직접).
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

## 운영 계약 【v4-S】
- **단일 진실원**: report.md/PDF 는 생성물 — 본문 수치를 직접 고치지 말고 facts.jsonl(생성기)을
  고친 뒤 재렌더한다. G3/G5 가 동기화를 강제한다.
- **고정 표면**: 게이트 11종(`assets/gates.json` 정본)과 audit 산출물 로스터(`report-format.md`)는
  고정 — 임의 단계 추가·생략 금지. 변경은 명시적 결정 + 문서정합 테스트 갱신 동반.
- **완료 선언 = 영수증**: "보고서 완성" = `run_ledger.py status` 가 11개 게이트 신선
  PASS/WATCH(BLOCK 0) 출력. **진행 기억·산문 선언은 증거가 아니다.** WATCH 잔존 시 9부 한계 고지.
- **게이트 완화 조건**: 게이트 강도 완화(전건→샘플링 등)는 완화 전후 품질 메트릭 실측 비교 +
  사용자 승인이 audit 로 제출될 때만. 메트릭 배선 부재 자체가 preflight 결함.
- 용어: **"사실(fact)"** = facts.jsonl 레코드(보고서 문장 아님) · **"축"** = 조사질문 =
  에이전트 분할 = 3부 챕터(1:1).

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
[G0]  preflight ─ 규모판정·앵커 게이트 → 도구점검 + 심층 인터뷰(13필드) + intent-diff 개시 【v4-I】
[PLAN]계획 합의 ─ 항목 스키마(반례 선설계) → 2레인 리뷰(CLEAR+OKAY) → consent 승인    【v4-C/P】
[1]   병렬 조사 ─ 레인 섹션 팬아웃(로스터 4종·verifier 상시·sonnet·background)        【v4-W】
[E]   확장→수렴 ─ EXPAND 리드 dedup → 후속워커 → 수렴까지 반복        【v3-A】
[G1]  join 게이트 ─ raw 보존 · RECEIPT sha 대조 · 스키마검증 등재 · 무출처 즉시 discarded
[2]   팀리드 재검증 ─ ★전건 원문 재열람 → verify_event(by=lead) ┐
[Bx]  반박·claim-graph ─ 독립그룹·반례쿼리 소진·기본소스·시간증거 ┼ 동결 코호트 3레인 【v4-V】
[정합] 단위·연도·정의·entity_id 스윕                              ┘ (join before repairing)
[G2]  증빙 게이트 ─ confirmed 전건 source_capture(핵심수치 필수) · 미처분 충돌 시 진입 불가
[3]   보고서 작성 ─ 고객 report.md(11부) + 내부 audit 번들 동시
[G3]  verify_facts + manifest ─ 실패 0 · 무태그·단위 차단 · 금지패턴·메트릭 【v4-Q】 · 해시 고정
[G5c] 실행코드 검증 ─ calculation/derivation=computed 대상 스크립트 실증   【v3-G5/v4-N】
[4]   render_pdf ─ GitHub 스타일 오프라인 PDF
[4b]  재봉인 ─ manifest.py build 재실행(기존 항목 보존 + report.pdf 등 렌더 산출물 해시 추가)
[G4]  preview ─ g4-visual-check 체크리스트 + (선택) fresh-context 팩트체커 【v4-V】
[G5]  최종 무결성 ─ PDF F태그·링크·캡처 수 재검사 + manifest 재확인 + run-receipt
```

**게이트 영수증 【v4-L】**: 모든 게이트 통과 주장은 `python scripts/run_ledger.py checkpoint
<gate> --verdict PASS|WATCH|BLOCK --evidence "..."` 영수증(`audit/run-ledger.jsonl`, append-only)
으로만 성립한다. 게이트 enum 정본은 `assets/gates.json`(G0·PLAN·G1·LV·BX·G2·G3·G5C·RENDER·
G4·G5). 기계 하한: confirmed 무증거·스키마 위반 대장은 팀리드가 PASS 를 요청해도 BLOCK 강제
(레거시 단일 대장은 WATCH+migration_required 완화). 신선도는 fact 단위(claim_key content-hash)
— fact 1건 수정은 그 fact 만 재검증 대상(partial_stale), report 파일은 전체 실효. 계획 변경
(steering)·사용자 개입(ask/answer)·출처 충돌(conflict/disposition)도 같은 대장에 `kind` 레코드로
기록한다(별도 파일 신설 금지).

### [G0] preflight + 요구사항 확정
- **규모 판정 게이트 【v4-I】**: 단순 사실확인·한두 출처 요약이면 파이프라인 미가동 — 직접
  경로(WebSearch)를 안내하고 종료(사용자 고집 시 진행). 이어 **브리프 앵커 게이트**: 앵커
  7종(대상명·기간·지역·언어·비교축·산출형식·용도) 0개면 팬아웃 금지, 인터뷰로 라우팅.
- **의존성 점검**: `python scripts/preflight.py` — python·fitz·pandoc·HeadlessChrome·
  curl_cffi·trafilatura 유무, playwright MCP·insane-search 스킬·무료 공공 MCP(opendart·
  KOSIS·KakaoMap 등) 감지. 미설치 계층은 "건너뜀+경고"로 진행(자체 스택이 보장 코어).
- **요구사항 확정 = 심층 인터뷰 【v4-I】**(`references/research-plan.md` 규율): 라운드당
  1질문 · 최약 차원 조준 · **사실/결정 라우팅**(사실은 예비탐색 인용확인, 결정만 질문) ·
  자동확정 3연속 상한 · 케이던스 1-2 자동/3+ 착수확인/5 하드캡(조기 착수 갭은 가정으로 9부
  승계) · **restate 게이트**(목적 1문장 verbatim 확인 → `restated_goal`). 조사유형(기술동향/
  산업동향/기관·기업 실사/기술사업화 실사)·범위·**축별 충분조건**·환산옵션(기본 OFF)·출력형식·
  **승인 목차** 확정 결과는 `audit/research-plan.md` 에 기록.
- **승인 3단 【v4-I】**: clarity(브리프) → feasibility([PLAN] 계획 합의 루프) → **consent**
  (명시 승인 후에만 팬아웃 — 계획이 존재한다는 이유로 조사를 자동 시작하지 않는다).
- **기관·기업 조사면** `references/entity-identity.md` 동일성 게이트 + **대상 스펙 【v4-S】**
  (별칭·표기 변형·기대 1차출처 도메인 cited_domains·조사 언어)을 먼저 확정.
- **intent-diff 개시**: `audit/intent-diff.md` 에 "요청 의도가 참이라면 무엇이 참이어야
  하는가"를 축별로 기록(G4 에서 발견과 대조해 gap 종결). 【v3-D】

### [PLAN] 계획 합의 + consent 【v4-C/P】
- 축별 조사질문은 **5열 항목 스키마**(질문|예상 claim|필요한 증거|반례 쿼리|폐기 조건)로 작성 —
  수치형 기본 반례 3종(타기관·타연도·타정의)은 생략 금지(반례 선설계 → Bx 게이트가 소진 검사).
- 가정으로 때운 확정치는 **의도 확정(Intent Reconciliation)** 으로 1개씩 사용자 확인·박제.
- **2레인 리뷰**: 커버리지(CLEAR/WATCH/BLOCK) + 실행가능성(OKAY/ITERATE/REJECT, `fetch.py`
  실측 프로브 필수 — 실측 실패는 REJECT 사유가 아니라 진단). 두 레인 클린일 때만 consent.
  반복 상한 3회 → PLANNING-STUCK(최선안 보존 + 사용자 승인 요청, 자동 팬아웃 금지).
- 확정 후 계획 변경은 run-ledger `kind:steering` 경유만 — **"산문은 상태를 변이하지 않는다"**.
  사용자 확정 스코프·게이트 기준은 조향 불가.

### [1] 병렬 조사 → [E] 확장·수렴  【v3-A】
- 조사 분할: **기관·기업**=대상 2~3개/에이전트(entity-identity 선고정, 대상별 축=일반현황/
  사업현황/재무실적 전건 조사) · **기술동향**=축분할(기술요소·플레이어·시장·정책 + 교차검증1) ·
  **산업동향**=밸류체인 + 통계(KOSIS/DART/KIPRIS 기존 스킬 조합) + 해외 · **기술사업화 실사**=
  축분할(기술성·권리성·시장성·사업성, 5부 공급·수요 이중매핑은 별도).
- 조사원 = **sonnet**(병렬·저비용, background). 에이전트별 `_research/<agent>/` 임시폴더에만
  쓴다(파일충돌 방지). 워커는 **읽기전용**(공식 대장 미기록) — 반환은 마커로. 【v3-F】
- **레인 섹션 스폰 【v4-W】**(`agent-briefs.md`): `### Lane <id> — <축>` 섹션당 정확히 1명,
  역할 로스터 4종(collector/counter-searcher/specialist/**verifier 상시 1레인**), 확정 브리프
  블록(`# Research brief (authoritative)`) verbatim 주입. 워커는 모호하면 질문 대신 가정을
  기록하고 진행(headless) — blocker 는 resolvable(우회 소진 의무) vs human_blocked(로그인·유료만)
  2분류. 재스폰은 사건당 2회 상한·3회째 fail-closed. **타임아웃은 관찰 창**(부분 산출물 검사 후
  판단). 진행 보고는 증거 파일 경로 동반.
- 반환 마커(`agent-briefs.md`): evidence 스키마 JSONL + `## CLAIMS`(CLAIM/RISK/SOURCES/
  COUNTER/PRIMARY) + `## EXPAND`(LEAD/WHY/ANGLE, DEAD END) + `## 인사이트`(사실/추론 구분,
  근거 F-ID) + `## 요약` + `## RECEIPT`(part_file·sha256 — **파일이 정본**, 인라인 EVIDENCE 는
  10건 이하만) + `## BLOCKERS`(시도한 우회 동반). 【v4-W】
- **확장수렴 루프**: 팀리드가 EXPAND 리드를 `AXIS` 필드 기준으로 `audit/expansion-log.md` 에
  축별 집계(dedup, 미확인 리드 포함) → 새 리드마다 후속 워커 즉시 스폰. **루프 수렴조건**(G0
  에서 사용자와 합의하는 **축별 충분조건**과는 별개 개념 — 전자는 이 루프 자체의 정지조건,
  후자는 워커에게 전달되는 조사 깊이 기준): **축별 잔여 리드 각 0**(한 축이라도 잔여 리드가
  남으면 미수렴), 또는 연속 2웨이브 무신규, 또는 깊이캡(기본 3회/12명, `research-plan.md`
  확정값이 있으면 그 값 우선) 도달(도달 시 사용자에 연장 문의). 드롭 리드는 로깅.

### [G1] join + 수집 게이트
- 전 에이전트 완료/timeout/부분실패 처리. raw 산출물 `_research/` 보존.
- `scripts/facts_db.py` 로 스키마 검증 등재(위반은 제한적 재요청). **출처 없는 주장은 즉시
  `discarded`**(audit 기록). 독립성: 같은 보도자료 재전재는 1출처로 계산(`source_role`).

### [2] 팀리드 재검증 (★전건) — 동결 코호트의 1레인 【v4-V】
- G1 후 대장을 **동결**(fact 단위 content-hash)하고 3레인이 같은 동결본 검사: ① 재검증(이 절 —
  권한은 팀리드 전속) ② 반박([Bx]) ③ 정합성(단위·연도·정의·entity_id 스윕). **join before
  repairing** — 레인별 수리 금지, 통합 blocker 배치 후 일괄 보수 → 재동결·generation+1.
- 보고서 진입 후보 **모든 fact** 를 팀리드가 원문 재열람(WebFetch → 차단 시 fetch.py →
  강방어 시 insane-search 위임)하여 verbatim/locator 대조 → `db.add_verify_event(by="lead")`.
- confirmed 조건(facts_db 강제): 최소 1 evidence + 팀리드 verify_event. 무출처=confirm 불가.
- **2세대+ 델타 라체트**: 변경·신규 fact 만 재검증. 기통과 fact 신규 반박은 "왜 이전 패스에서
  안 보였나" 정당화 필수. 발견은 전건 처분(accept/rebut — 침묵 폐기 금지). 출처 충돌은
  `kind:conflict` → typed 처분 후에만 통과, **미처분 충돌 잔존 시 G2 진입 불가**. 모순 fact 는
  삭제 대신 disputed→supersede 체인(`dispute_kind`).

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

### [G3] verify_facts + manifest (실패 0)
- `scripts/verify_facts.py`: 본문/생성부록 분리 파싱(부록 경계는 주석 우선, 없으면 헤딩 최후
  출현) · 본문을 문장·표행 세그먼트로 나눠 수치↔`(Fxxx)`를 1:1 최근접 결박(태그 하나가 줄
  전체를 면제하지 않음) · 무태그 숫자·통화·비율·표셀 탐지(태그 없는 사실주장 차단) · 모든
  `(Fxxx)` 대장 존재+status∈{confirmed} + 값·**단위**(Decimal 스케일·차원, `[단위불일치]`)
  대조 · evidence 필수필드 누락 0 · source_capture 실재(핵심수치) · [환산 ON] Decimal 검산.
- **【v4-Q】 추가 검사**: 금지 패턴(플레이스홀더·비밀/내부경로 FAIL, 무각주 헤지 WARN) ·
  캡처 구조검사(백지·단색 WARN) · 기대출처(cited_domains) 미달 WARN · `--min-confirmed` 정량
  하한(기본 OFF) · 품질 메트릭(`--metrics-out audit/quality-metrics.json` — 도메인 편중>40%
  경고·1차출처율·Bx 생존율).
- `scripts/manifest.py build`: source/capture/report/PDF/대장 SHA-256 고정.

### [G5c] 실행코드 검증  【v3-G5/v4-N】
- **대상 선별(기계 규칙)**: `evidence.type=calculation` 존재 OR fact `derivation=computed`.
  대상인데 `verify-<slug>.md` 없으면 G5 에서 지적. 자체포함 스크립트 실행 → stdout 캡처 →
  표준 템플릿(입력/스크립트 전문/stdout verbatim/판정 CONFIRMED|REFUTED|PARTIAL).
- **Evidence discipline**: 직접 계산해 보지 않은 지표·결론 보고 금지 · 계산 실패 은폐 금지
  (실패 시 해당 fact 미검증 강등) · shows vs infer 구분. 시장조사 접점: 시장규모=수량×ASP·
  CAGR·통화환산 Decimal 검산.

### [4] render_pdf → [4b] 재봉인 → [G4] preview → [G5] 최종 무결성
- `render_pdf.py`(pandoc gfm→html --embed-resources → HeadlessChrome --print-to-pdf,
  한글경로 퍼센트인코딩·오프라인)로 report.pdf 생성.
- **[4b] 재봉인**: `scripts/manifest.py build` 재실행. [G3]의 build 시점엔 report.pdf 가 아직
  없어 매니페스트에 영구 누락되므로, 렌더 직후 다시 build 해 **기존 항목(source/capture/
  facts/evidence/report_md)은 그대로 둔 채** report.pdf 등 렌더 산출물의 해시만 추가한다.
  재봉인을 건너뛰면 report.pdf 는 변조·삭제해도 [G5] 가 잡지 못한다.
- `preview_pdf.py`(fitz 페이지 이미지) 로 팀리드 육안검증 + **intent-diff 축별 대조**(G0
  개시분과 실제 발견 대조, 절차·복귀 규칙은 `references/verification-gates.md` G4 절 참조).
  **G4 이원화 【v4-V】**: 육안 결과는 `audit/g4-visual-check.md` 체크리스트로 기록(블랙박스
  제거) + 선택 레인으로 **fresh-context 팩트체커**(입력은 report.md+facts.jsonl+research-plan.md
  만, 마지막 줄 `VERDICT: APPROVE|REQUEST_CHANGES` 고정 파싱, 파싱 불가는 fail-closed).
- 최종: PDF 에서 F태그·링크·캡처 수 재검사 + `manifest.py verify`(재봉인 기준 — 이 시점부턴
  신규 파일도 실패로 판정). G5 직전 `audit/run-receipt.md`(범위·경계·답할 수 있는/없는 질문·
  Caveats) 작성 — 무결성은 G5 영수증 target_hashes 자기참조. 복귀 규칙은
  `references/verification-gates.md` 참조(파일 변경/intent-diff gap 각각 다른 복귀처).
  G5 후 도메인 수집 레시피를 `assets/domain-recipes.json` 에 머지(【v4-M】 `source-ladder.md`).
- **참고**: [G2]가 만드는 실패 캡처 `.FAILED` 산출물도 `_captures/**` 글롭에 잡힌다 — 재봉인
  이후 캡처를 재시도하면 그 결과물이 신규 파일로 잡혀 verify 가 실패로 뜬다. 의도된 동작이며
  이 경우도 재봉인이 해법이다.

---

## 모델 분리 / 자원 재사용
- 조사원 = sonnet(병렬·저비용). 재검증·종합 = 메인 세션(고성능).
- **수집 사다리**(`references/source-ladder.md`): WebFetch → fetch.py(curl_cffi TLS→모바일
  →Jina→Wayback, 보안경계) → **강방어 시 insane-search 스킬 위임**(이중구현 금지). 무료 공공
  MCP(opendart·KOSIS 등)는 있으면 Phase0 1차소스로 기회적 활용(유료 무의존 유지).

## 참조 문서 (필요할 때만 로드)
| 파일 | 언제 |
|---|---|
| `references/agent-briefs.md` | 레인 섹션 스폰·역할 로스터·반환 마커(RECEIPT/BLOCKERS)·리뷰어 브리프·워커 경계·철칙 |
| `references/source-ladder.md` | 검색 계층·fetch 폴백·Phase0 API·4계층 성공검증·WAF 정찰·research-memory(domain-recipes) |
| `references/extract-recipes.md` | 증거유형별 추출·PDF fitz·특수소스 recipe·derivation/verdict 결박 |
| `references/evidence-capture.md` | source_capture vs reconstructed_excerpt·메타 결박·표면별 증거 규칙·캡처 구조검사 |
| `references/report-format.md` | 고객 11부 목차·유형변형·audit 로스터(고정 표면)·run-receipt/handoff/드래프트 규약 |
| `references/verification-gates.md` | G0~G5 상세·run-ledger 영수증·동결 코호트·라체트·asks 정본·4차원 등급·claim-graph·환산 |
| `references/research-plan.md` | G0 인터뷰 규율·조사계획 확정(항목 스키마·반례 선설계·의도 확정·계획 합의 루프·깊이캡·승인 목차) |
| `references/entity-identity.md` | 기관·기업 동일성 확인 게이트·대상 스펙(cited_domains) |
