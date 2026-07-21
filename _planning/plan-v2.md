# 신규 스킬: factsheet-research — 기술사업화 기관용 증빙형 시장조사 보고서 (v2, 합의 반영)

## Context
내비온(기술사업화 기관)의 반복 업무 — 기술동향·산업동향·기관/기업 실사·시장조사 — 를 위한 신규 Claude Code 스킬.
"북미 대학 기술이전 메가딜" 플레이북(`00_WORKFLOW_시장조사보고서_제작가이드.md`)을 범용화하되, **처음부터 새 설계·새 구현**.

사용자 3대 요구:
1. **오케스트레이션** — 팀리드(메인)가 서브에이전트 조사 결과를 **직접 재검증**. 토큰 낭비 OK, 정확성 우선.
2. **차단봇 우회 + extract 강화** — **유료 API(firecrawl/tavily) 무의존 자체 스택**으로 1차출처 수집·추출.
3. **팩트시트 보고서(최중요)** — AI 확률적 답변으로 조사마다 수치가 달라지는 문제를,
   [조사내용→출처→증빙] 증거구조 + 사실대장 + 검증게이트로 해소. GitHub PDF 스타일 + 에이전트별 인사이트.

### 합의(Consensus): Claude ↔ Codex(gpt-5.6-sol/xhigh)
Codex 판정 **DISAGREE(재설계 요구)**, Claude **수용**. 아래 v2는 재설계 반영본.
**사용자 확정 2건**: (A) 보고서 진입 **전건** 팀리드 재검증. (B) 산출물 **고객용/내부 audit 2종 분리**.

핵심 변경 (v1 → v2):
- 단일 `source_url/verbatim/capture` → **`fact` + `evidence[]` 배열** (복수 출처·삼각검증·상충 표현 가능)
- 평면 value → **claim context**(metric·entity·geography·period·as_of·basis·scenario) + 안정적 `claim_key`
- verbatim 필수 → **증거유형 6종**(text_quote/table_cell/chart/api_response/negative_search/calculation)
- htmlbox 재현물을 "출처 스크린샷"에서 **제외**(내부 재구성 발췌로만)
- **run manifest + SHA-256 해시**로 증거 체인 고정, 파일 변경 시 G3 재실행
- fetch.py **보안 경계**(SSRF/injection 방어), 원문 = 불신뢰 데이터
- v1 소스 **축소**: DDG+SearXNG+arXiv+SEC EDGAR+Wikipedia 코어. 나머지(Semantic Scholar·CrossRef·GitHub·HN·Reddit·X·yt-dlp)는 recipe 문서로만.
- A~E 단일등급 → **4차원 등급**(authority/independence/directness/recency)
- 고객 PDF에서 폐기목록·실패URL·미확인의혹 **제거** → 내부 audit 번들로

---

## 산출물 위치
- 개발본(git): `C:\Users\김형일\Documents\Claude\Projects\codes\factsheet-research\`
- 설치본: 완성 후 `C:\Users\김형일\.claude\skills\factsheet-research\` (install.py로 해시검증 복사)
- 기존 market-deep-research 스킬은 수정 금지 (완성 후 폐기 여부만 사용자에게 권고)

## 디렉터리 구조
```
factsheet-research/
├── SKILL.md                      # frontmatter(name/description/트리거) + 팀리드 오케스트레이션 + 게이트 G0~G5
├── references/
│   ├── agent-briefs.md           # 서브에이전트 프롬프트 템플릿 + evidence 반환 스키마 + 철칙
│   ├── source-ladder.md          # search 계층 + fetch 폴백 사다리 + 응답 판정 + 보안 정책
│   ├── extract-recipes.md        # 증거유형별 추출(표/차트/API/부정조회/계산) + PDF fitz 파싱 + 특수소스 recipe(비-v1)
│   ├── evidence-capture.md       # 캡처 유형 구분(source_capture vs reconstructed_excerpt) + 메타 결박
│   ├── report-format.md          # 고객용 보고서 양식(3중 구조·인사이트·한계) + 내부 audit 번들 양식
│   ├── verification-gates.md     # G0~G5 상세 + 오인방지 체크 + 4차원 등급 + 환산옵션(Decimal)
│   └── entity-identity.md        # 기관·기업 동일성 확인 게이트(법인명/사업자번호/법인번호/주소/이전상호/해외ID)
├── scripts/
│   ├── skill_paths.py            # 스킬 루트·작업폴더 경로 해석 공통 모듈(모든 스크립트가 import)
│   ├── search.py                 # 자체 검색 (DDG HTML→SearXNG 로테이션→arXiv/SEC/Wikipedia) + 백오프·헬스체크
│   ├── fetch.py                  # 자체 fetch/extract + 보안경계(SSRF/크기/MIME) + curl_cffi→모바일→Jina→Wayback
│   ├── facts_db.py               # facts.jsonl 원자적 read/append/validate(스키마) + evidence 병합 + claim_key
│   ├── capture_pdf.py            # PDF 하이라이트+크롭 (fitz) — source_capture 생성
│   ├── capture_web.py            # 재구성 발췌 렌더(insert_htmlbox) — reconstructed_excerpt(내부용, 증빙 불인정)
│   ├── manifest.py               # run manifest + SHA-256 해시(source/capture/report/PDF) 기록·검증
│   ├── verify_facts.py           # 본문/부록 분리 파싱 + 무태그 숫자 탐지 + 태그↔대장 의미 대조 게이트
│   ├── render_pdf.py             # pandoc→html→HeadlessChrome PDF (오프라인·한글경로 인코딩)
│   └── preview_pdf.py            # fitz 페이지 이미지 (육안검증)
└── assets/
    ├── style.html                # GitHub 스타일 CSS (Malgun Gothic·A4·증빙박스)
    ├── facts-schema.json         # fact + evidence[] JSON 스키마 (facts_db.py 검증 기준)
    ├── searx-instances.json      # SearXNG 공개 인스턴스 목록(헬스체크 대상)
    └── curated-sources.json      # 조사유형별 1차출처 도메인 + --type 백엔드 매핑
```
작업 폴더(조사 실행 시): `research_<주제>_<날짜>/` 아래
`_sources/`(원본 스냅샷+해시) `_research/`(에이전트 원자료 보존) `_captures/`(source_capture)
`_reconstructed/`(내부 재구성 발췌) `facts.jsonl` `manifest.json`
`report.md`→`report.pdf`(고객용) `audit/`(내부: 폐기목록·실패소스·검증이력·raw agent output).

---

## 핵심 설계 1 — 증거 모델: fact + evidence[] (재현성의 축)

**fact** = 컨텍스트가 고정된 하나의 주장. **evidence[]** = 그 주장을 뒷받침/반박하는 증거들.
```json
// fact
{"claim_key":"revenue|삼성전자|KR|2024|annual|actual",   // 안정적 diff 키(순번 아님)
 "id":"F001", "claim":"...요지...",
 "context":{"metric":"revenue","entity":"삼성전자","entity_id":"사업자/법인번호",
            "geography":"KR","period":"2024","as_of":"2025-03","basis":"annual|actual",
            "scenario":null,"definition":"연결기준 매출"},
 "value":{"raw":"300.9","unit":"KRW_T","decimal":"300900000000000"},
 "grade":{"authority":"A","independence":"B","directness":"A","recency":"A"},
 "status":"confirmed|pending|disputed|superseded|discarded",
 "verified_by":"lead", "verify_events":[...],           // 누적 이벤트(단일 문자열 아님)
 "evidence_ids":["E001","E002"], "discard_reason":null}
// evidence (별도 라인/컬렉션)
{"id":"E001","fact_id":"F001","type":"table_cell|text_quote|chart|api_response|negative_search|calculation",
 "source_url":"최종URL","archived_url":"Wayback/Jina(구분)","local":"_sources/xxx.pdf","sha256":"...",
 "accessed_at":"...","http_status":200,"locator":{"page":12,"row":3,"col":2}|{"selector":"..."},
 "verbatim":"원문 그대로(text_quote일 때)","source_role":"원출처|재인용|보도자료","capture":"_captures/E001.png"}
```
- 보고서 본문 수치엔 `(F001)` 태그. verify_facts.py가 태그↔대장 의미(값·단위·기간·주체) 대조.
- **confirmed 조건**: 최소 1개 evidence + **팀리드 verify_event(원문재열람) 존재**. 무출처=등재 불가=본문 불가.
- 재조사: 이전 facts.jsonl과 `claim_key` 기준 diff → "조사마다 다른 수치"를 데이터로 검출(값 변동/정의 변동 구분).
- 상충: `disputed`(정의 차이·상반 수치 병기) / `superseded`(시계열 갱신). 단순 저등급 폐기 금지.

## 핵심 설계 2 — 오케스트레이션 (게이트 파이프라인 G0~G5)
```
[G0] preflight + 요구사항 확정 ── 도구/의존성 점검(Python·fitz·pandoc·Chrome·playwright·curl_cffi·trafilatura),
      조사유형·범위·조사종료기준·환산옵션(기본OFF)·출력형식·목차 승인. 기관조사면 entity-identity 게이트 선행.
[1]  병렬 조사 ────────── 조사원 에이전트 팬아웃 (sonnet, background, 에이전트별 임시 하위폴더 → 파일충돌 방지)
[G1] join + 수집 게이트 ── 전 에이전트 완료/timeout/부분실패 처리. raw 산출물 _research/ 보존.
      facts_db.py로 스키마 검증 등재(실패 시 제한적 재요청). 출처 없는 주장 즉시 discarded(audit 기록).
[2]  팀리드 재검증 ─────── ★전건. 보고서 진입 모든 fact를 팀리드가 원문 재열람(WebFetch/fetch.py)하여
      verbatim/locator 대조 후 verify_event 기록. 검증 에이전트는 보조의견만(verifier 단독 confirm 금지).
      독립성 판정: 같은 보도자료 재전재는 1출처로 계산(source_role).
[G2] 증빙 게이트 ──────── confirmed 전건 source_capture 생성(실화면/PDF). 핵심수치 캡처 필수.
      재구성 발췌(htmlbox)는 증빙 불인정 → 원본 캡처 불가 시 대체출처 or 미확인 유지.
[3]  보고서 작성 ──────── 고객용 report.md(3중 구조+인사이트+한계) / 내부 audit 번들 동시 생성
[G3] verify_facts + manifest ── 실패 0 필수. 무태그 숫자 탐지·부록 우회 차단. manifest 해시 고정.
[4]  render_pdf.py ────── GitHub 스타일 오프라인 PDF
[G4] preview_pdf.py ───── 팀리드 육안검증(fitz 이미지 Read)
[G5] 최종 무결성 ──────── PDF에서 F태그·링크·캡처 수 재검사 + manifest 해시 재확인. 파일 변경 시 G3 복귀.
```
**조사 분할**: 기관·기업조사=대상 2~3개씩/에이전트(+entity-identity 선고정) / 기술동향=축분할(기술요소·플레이어·시장·정책+교차검증1) / 산업동향=밸류체인+통계(KOSIS·DART·KIPRIS 기존 스킬 조합)+해외.
**모델 분리**: 조사원=sonnet(병렬·저비용), 재검증·종합=메인 세션(고성능).
**서브에이전트 반환**(agent-briefs.md): evidence 스키마 준수 JSONL + `## 인사이트`(사실/추론 구분, 근거 F-ID) + `## 요약`(건수·등급·폐기 리드). 철칙: 원문 미확인 수치 폐기(추정 금지)·딜규모≠실수취액·귀속처 명시.

## 핵심 설계 3 — 자체 search + fetch/extract 스택 (유료 API 무의존)
**① search.py** `python -m ...search "쿼리" [--n 10] [--type web|news|academic|filing]`
- 계층: DuckDuckGo HTML(html.duckduckgo.com) → SearXNG 공개인스턴스 로테이션(헬스체크·백오프) → 전문 무료API: arXiv(academic)·SEC EDGAR full-text(filing)·Wikipedia. `--type`은 curated-sources.json 백엔드 매핑에 있는 것만, **미지원 유형은 명시적 실패**.
- 에이전트는 내장 WebSearch와 병행. "검색 완전성 미보장" 명시. 요청 예산·캐시.

**② fetch.py** `python -m ...fetch <URL> [--out _sources/]`
- **보안경계(선제)**: HTTP(S)만, private/loopback/link-local·리다이렉트 대상 차단, 크기·시간·MIME 제한. 원문은 "신뢰하지 않는 데이터"(프롬프트 인젝션 주의) — 추출 지침에 명시.
- 사다리: curl_cffi(chrome impersonate TLS) → 도메인별 모바일 recipe(범용 변환 금지) → Jina Reader(무료·JS렌더·PDF→MD) → Wayback. **Googlebot UA·범용 캐시 제외**. 로그인/CAPTCHA/paywall 우회 금지(정책).
- 보존: **원본(raw HTML/PDF) + 정제본(trafilatura) 둘 다** 저장 + SHA-256. archived_url(Jina/Wayback)은 원 URL과 **구분 기록**.
- 판정: 본문1,000자+키워드=성공 / OGP만=partial / CAPTCHA·빈SPA=실패(사유코드).
- PDF: 다운로드→`_sources/` 저장→fitz 파싱(표는 `find_tables()`)→캡처 소스 재사용.
- **자체 extract 원칙**: fetch.py가 깨끗한 본문 확보 → 서브에이전트가 evidence 스키마로 구조화(LLM=extractor). 표는 page/row/col, API는 endpoint/param/JSON해시.
- pip(1회): `curl_cffi`,`trafilatura`(+선택 `yt-dlp`). 미설치 계층은 건너뛰고 경고.

## 핵심 설계 4 — 증빙 캡처 (source_capture만 증빙 인정)
| 상황 | 방법 | 유형 | 스크립트 |
|---|---|---|---|
| 로컬/다운로드 PDF | fitz 정확숫자 검색→하이라이트→크롭 | source_capture | capture_pdf.py |
| 접근 가능한 웹 | playwright 스크린샷(실화면) + 메타결박(최종URL·시각·viewport·locator) | source_capture | (MCP 직접) |
| 차단·유실 | insert_htmlbox 재구성 발췌 | **reconstructed_excerpt(내부용, 증빙 불인정)** | capture_web.py |
- 캡처 검색어=정확 숫자(부분문자열 금지), 오귀속 육안확인. 파일명=evidence ID. PDF 숫자 표기변형(쉼표·공백·개행)·스캔PDF는 페이지 육안 fallback + 실패상태.

## 핵심 설계 5 — 팩트시트 보고서 (고객용 / 내부 audit 분리)
**고객용 report.pdf**: 섹션 = 서술본문(배경→메커니즘→수치(F태그)→의의→⚠주의점) → 근거표(사실|수치|출처링크|4차원등급|증빙) → source_capture+캡션(수치↔원문 매핑). 말미: 한눈에요약표 / 조사팀 인사이트(에이전트별+팀리드 코멘트, 사실/추론 구분) / **한계와 반론(개수 고정 없음, 근거 있을 때만)**. **폐기목록·실패URL·미확인의혹 미포함.**
**내부 audit 번들**(`audit/`): facts.jsonl 전수표 / 폐기목록+사유 / 실패소스 / 검증이력 / raw agent output / manifest.
style.html: GitHub markdown + Malgun Gothic + A4 + 증빙박스. pandoc(gfm,--embed-resources)→HeadlessChrome(--print-to-pdf 절대경로·한글경로 퍼센트인코딩, 네트워크 접근 없이 오프라인 렌더).

## 핵심 설계 6 — verify_facts.py + manifest (G3, 실패 0)
1. 본문/생성부록 **분리 파싱**(부록 태그는 본문사용으로 미계산)
2. 본문의 숫자·통화·비율·날짜·표셀 **무태그 탐지**(태그 없는 사실 주장 차단)
3. 모든 `(Fxxx)`가 대장 존재+status∈{confirmed} + 값·단위·기간·주체 **의미 대조**
4. confirmed인데 본문 미사용 사실 목록(유실 점검)
5. evidence 필수필드(source_url·type·sha256·accessed_at·grade) 누락 0, text_quote는 verbatim 필수
6. source_capture 경로 실재(핵심수치 필수)
7. manifest: source/capture/report/PDF SHA-256 기록, 이전과 대조 → 변경 시 G3 재실행 트리거
8. [환산 ON] Decimal 검산(계산식·환율출처·기준일·종가/평균 명시)·표시 반올림 일관성·본문 영어통화단어 0

## 범위 제외
firecrawl/tavily 표준경로 / SearXNG 자체호스팅 / cloakbrowser·프록시 인프라(교훈만: curl_cffi TLS·playwright 스텔스 참고) / Googlebot UA·범용 모바일변환·비계약 캐시 / claude -p 팬아웃 / Semantic Scholar·CrossRef·GitHub·HN·Reddit·X·yt-dlp v1 배선(recipe 문서로) / Excel 자동생성(기존 xlsx 스킬 조합) / 웹UI·스케줄링 / 고정 반론 개수 / 고객 PDF 폐기·실패 노출.

---

## 구현 순서 (shrimp 분해 대상)
1. **뼈대**: 디렉터리 + SKILL.md frontmatter(name/description 트리거) + skill_paths.py(경로 해석)
2. **보안·경로 기반**: fetch.py 보안경계 우선 구현 → search.py → JSON 2종(searx/curated) → 라이브 스모크
3. **데이터 모델**: facts-schema.json + facts_db.py(원자적 write·스키마검증·claim_key·evidence 병합) + manifest.py(해시)
4. **references 7종** 작성
5. **assets**: style.html
6. **캡처·렌더**: capture_pdf → capture_web(내부용 명시) → verify_facts(무태그·부록·의미대조) → render_pdf → preview_pdf
7. **적대적 fixture 테스트**: 무태그숫자·오태그·빈캡처·캡처교체·중복ID·HTML인젝션·redirect SSRF·표PDF·스캔PDF·상충출처 → verify/fetch가 정확히 실패하는지
8. **replay 테스트**: 저장된 동일 source snapshot 2회 추출 → 동일 claim set 재현 확인
9. **E2E 스모크**: 미니 조사 1건(에이전트 2개, 자체 스택만, G0~G5 완주) → 고객PDF+audit 분리 확인 → fitz 육안
10. **설치**: install.py(해시검증 복사) → 새 세션 트리거·오케스트레이션 forward test(기술/산업/기업 각 1)

## 검증 (완료 기준)
- [ ] G0 preflight가 누락 의존성 정확히 탐지
- [ ] fetch.py: 사설IP/redirect SSRF 차단, 크기/MIME 제한, 원본+정제 둘 다 해시 저장. 403성 사이트 TLS/Jina 폴백.
- [ ] search.py: 유료 API 0 호출, 계층 폴백·헬스체크·미지원 --type 실패 동작
- [ ] facts_db.py: 스키마 위반 거부, 원자적 append(부분쓰기·중복ID 방지), claim_key diff
- [ ] verify_facts.py: 적대적 fixture 전건에서 정확히 실패(무태그·오태그·부록우회·캡처교체·의미불일치)
- [ ] manifest: 파일 변경 시 G3 재실행 트리거, 최종 PDF 무결성 재검사
- [ ] replay: 동일 snapshot 2회 → 동일 claim set
- [ ] E2E: 미니 조사가 자체 스택만으로 완주, 고객PDF(폐기·실패 미노출)/audit 분리, fitz로 표·이미지·한글 정상
- [ ] 새 세션 forward test: 기술/산업/기업조사 자연어 트리거 + 오케스트레이션 동작
