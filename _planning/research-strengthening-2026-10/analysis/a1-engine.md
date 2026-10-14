# A1 조사 엔진 분석 (검색·열람 코드)

경로 약칭: S=`codes/market-deep-research/scripts/`. 정적 분석만 수행(실행·네트워크 없음). "확인"=코드에서 직접 본 사실, "추정"=코드 정황 기반 추측.

## 1. 현재 동작 요약

### 검색 (S/search.py, 208줄)
- 백엔드: DuckDuckGo HTML 스크래핑(search.py:43), 결과가 `max(3, n//2)` 미만이면 공개 SearXNG 5개 인스턴스 순회(search.py:150-154, assets/searx-instances.json). `academic`=arXiv(search.py:92), `filing`=SEC EDGAR full-text(search.py:109). `news` 는 `web` 과 같은 백엔드(curated-sources.json type_backends).
- 질의 확장: 없음. 다국어: 없음(arXiv/EDGAR 는 영문 전제, Wikipedia 는 lang 인자가 있으나 CLI/--type 에 연결 안 됨 search.py:132,162,207). 날짜/도메인 필터: 코드 없음(문서가 사람/LLM 에게 `site:` `after:` 연산자를 쓰라고 권할 뿐 — source-ladder.md, mdr-search/SKILL.md:step3). 중복 제거: SearXNG 보강 시 URL 문자열 완전일치뿐(search.py:153). 순위화: 없음(백엔드 순서 그대로). ddg snippet 은 항상 빈 문자열(search.py:56).
- 백엔드 사망 시: 예외 삼키고 `[]` 반환 + stderr 경고(search.py:48-50). 호출자는 "0건" 과 "백엔드 전멸" 을 구분 못 함(반환형이 list 뿐).

### 열람 (S/fetch.py, 906줄)
- 사다리(fetch.py:60,566-581): direct(curl_cffi 지문 chrome/safari/chrome110 3회) → mobile(iOS 지문+m. 서브도메인 재작성) → jina(r.jina.ai) → googlebot UA → rss → wayback → OGP 메타(partial). 도메인 ROUTES 는 폴백 순서만 조정(fetch.py:64-74).
- 공통 transport `request_bytes`: SSRF 사전검증+IP 고정+수동 리다이렉트 5홉+8MB 캡+25s 마감(fetch.py:312-368). 이 경계는 견고함.
- 성공 판정 `validate_body`(fetch.py:228-246): 비2xx 실패 → success_selector 부분문자열 일치 → 정제 본문 ≥1000자면 ok → 챌린지 마커 → <200B empty → 나머지 partial.
- PDF: 매직바이트 `%PDF-` 이면 무조건 ok(fetch.py:397,609-625). 텍스트는 추출하지 않음(`text=""`), save 에서 clean=None(fetch.py:714).
- 저장: raw+clean+sha256+meta.json, URL 이력 누적(fetch.py:701-753), 시도마다 audit/fetch-log.jsonl.

### 출처 계층
- S/source_index.py 는 `_sources` 스냅샷을 표로 묶는 포매터일 뿐. 출처 등급 분류·1차/2차 구분·정렬 로직 없음(source_index.py:68-134: publisher=호스트명만).
- references/source-ladder.md "Phase0 공식/무료 API 우선" 은 문서 권고. `phase0_apis`·`mcp_phase0` 키는 어떤 .py 도 읽지 않음(grep 확인: 코드에서 읽는 건 `curated_domains` 하나, 그것도 이미지 검색 harvest_images.py:415-432 한 곳).

## 2. 약점 목록 (심각도 상·중·하)

| # | 심각도 | 약점 | 근거 | 영향 |
|---|---|---|---|---|
| W1 | 상 | `validate_body` 가 정제 본문 ≥1000자면 무조건 ok. 소프트404("페이지를 찾을 수 없습니다" + 내비게이션/푸터), 쿠키동의, 로그인벽, 페이월 티저, 사이트맵형 목록 페이지가 1000자를 넘기면 성공 처리. 요청 URL/주제와 본문 관련성 검사는 RSS 경로의 제목 대조뿐 | fetch.py:237-239, 616-617 | 엉뚱한 본문이 `ok` 로 저장되어 이후 사실추출·증빙에 오염. 가장 위험(조용한 실패) |
| W2 | 상 | trafilatura 미설치 시 `extract_text` 폴백이 정규식 태그 제거만 수행 → `<script>`/`<style>` 내용 포함해 길이 부풀림 → 빈 SPA 셸도 ≥1000자로 ok. preflight 는 trafilatura 를 SOFT 로만 취급(경고만) | fetch.py:249-256, preflight.py:SOFT_PY | JS 렌더 필요 페이지가 ok 로 통과. 환경 의존적 비결정성(추정: 설치본에 따라 결과 달라짐) |
| W3 | 상 | 인코딩: `response_text` 는 Content-Type charset 헤더만 신뢰, 없으면 utf-8 시도 후 `errors="replace"`. `<meta charset=euc-kr>` 만 있는 한국 사이트는 깨진 문자열이 길이 조건을 통과해 ok | fetch.py:371-378 | 한국 공공/구형 사이트(go.kr 등)에서 모지바케 본문이 증빙화. 확인된 코드 경로, 실제 빈도는 추정 |
| W4 | 상 | 허용 MIME 이 html/text/json/xml/pdf/rss 뿐. HWP/HWPX/XLSX/DOCX/CSV/ZIP/octet-stream 은 `mime:` 사유로 실패. 정부·통계 1차 출처의 상당수가 이 형식 | fetch.py:42-44, 398-399 | 공공통계·정부 보고서 첨부 확보 불가. (kordoc MCP 가 별도로 있으나 fetch 와 연결 안 됨) |
| W5 | 상 | 8MB 캡. 연차보고서·통계 PDF(20~100MB)는 oversize 로 모든 계층 실패. 사다리는 oversize 도 다음 계층으로 계속 시도(낭비) | fetch.py:36,353-362, 388-389 | 1차 출처(공시·시장보고서 PDF) 접근 실패 |
| W6 | 상 | 1차 출처 접근이 코드로 지원되지 않음. 검색 유형은 web/news/academic(arXiv)/filing(SEC 영문)뿐. DART·KOSIS·KIPRIS·특허·통계·KCI/RISS 백엔드 없음. `phase0_apis`/`mcp_phase0` 는 데이터일 뿐 사용처 없음. source_index 는 등급화 안 함 | curated-sources.json type_backends; grep 결과(.py 에서 phase0_apis 미사용); source_index.py:68-134 | "증빙형" 이라 하면서 1차 출처 우선순위가 LLM 의 자율 판단에만 의존 |
| W7 | 중 | 검색 실패와 무결과 구분 불가. ddg 가 202/캡차 페이지를 줘도 `_get` 은 상태코드를 안 보고 정규식 0건 → `[]`. arXiv/EDGAR/Wikipedia 도 status 미검사 | search.py:36-39,46-59,95,112 | 에이전트가 "검색 결과 없음" 으로 오판할 수 있음(조용한 실패) |
| W8 | 중 | SearXNG 백오프 로직이 주석과 반대: 429/비200 은 즉시 `break`(재시도 안 함), 예외(타임아웃·연결오류)일 때만 `continue` 로 1/2/4초 재시도. 인스턴스 5개 × (10s 타임아웃×4+7s) 최악 약 4분 | search.py:73-89 | 죽은 인스턴스 목록에서 검색 1회가 수 분 블로킹. 의도(429 대비)와 실제 동작 불일치 |
| W9 | 중 | 공개 SearXNG 5개는 SLA 없음, `health_path` 는 정의돼 있으나 헬스체크 코드는 없음(미사용). 인스턴스 목록은 2026-07-22 이후 갱신 이력 없음 | searx-instances.json, grep 에서 health_path 사용처 없음 | 보강 경로가 사실상 죽어 있을 가능성(추정). ddg 단일 장애점 |
| W10 | 중 | 열람 사다리 낭비/예의 부족: 404·410·401 등 확정 상태에서도 3지문→모바일→jina→…→wayback 전부 소진(최대 10여 요청, 각 25s). 호스트별 rate limit·robots.txt·캐시·재시도(429 Retry-After) 없음. 병렬성 없음(순차) | fetch.py:596-639; grep: sleep 은 search.py:76 하나뿐, robots/cache 없음 | 같은 호스트 연속 호출 시 차단 유발, 존재하지 않는 URL 에 시간 낭비. 재현성: 동일 URL 재호출 시 항상 재요청(캐시 없음) |
| W11 | 중 | 파생 URL 의 동일성 미검증: `m.` 서브도메인 재작성, Wayback "closest" 스냅샷(날짜 무관), Jina 결과가 원문과 같은 문서인지 확인 없이 ≥1000자면 ok. Wayback 스냅샷 날짜는 archived_url 에만 있고 결과 필드엔 별도 없음 | fetch.py:428-441, 412-425, 628-629 | 오래된/다른 페이지가 ok 로 반환(증빙 시점 불일치) |
| W12 | 중 | 정책 문서와 코드 불일치: source-ladder 정책선은 "Googlebot UA 제외" 라고 하지만 사다리 5단계가 Googlebot UA 사칭. Jina 는 대상 URL 을 제3자(r.jina.ai)로 보냄 → 대외비 주제 시 URL 유출 | source-ladder.md 정책선 vs fetch.py:55,554-555,404-409 | 정책 위반 소지·보안 고려(대외비 규칙과 충돌 가능) |
| W13 | 중 | PDF 는 매직바이트만으로 ok. 스캔 PDF(텍스트층 없음)·암호화 PDF·일부만 받은 PDF 구분 없음. fetch 는 PDF 텍스트를 추출·저장하지 않음 | fetch.py:397,609-625,714 | 텍스트 없는 PDF 가 "확보 ok" 로 계산 |
| W14 | 중 | `success_selectors` 가 raw HTML 소문자 부분문자열 일치(CSS selector 아님)로 최우선 ok. 이름과 달리 오탐 쉬움 | fetch.py:234-235 | 호출자가 잘못 쓰면 챌린지 페이지도 ok |
| W15 | 하 | SEC EDGAR 는 식별 가능한 User-Agent 를 요구하나 `Mozilla/5.0` 고정 → 403 위험(추정). 질의를 따옴표 구문검색으로 강제 | search.py:36-39,110 | filing 검색 불안정 가능 |
| W16 | 하 | arXiv `all:` + 공백 인코딩, 한글 질의 무의미, 결과 n건 중 중복/관련도 필터 없음 | search.py:93 | academic 정밀도 낮음 |
| W17 | 하 | 테스트 빈약: search/fetch 관련 매칭이 3개 파일(test_adversarial 51줄 참조, test_batch2a 28, test_batch2c 6)이며 tests/ 총 13개 파일. search 백엔드의 실제 파싱(ddg HTML)·searx 백오프·CHALLENGE 오탐 경로에 대한 고정 픽스처 테스트가 적음. 대부분 `demo()` 내부 assert | `grep` 결과; search.py:166-196 demo | 위 W1~W8 같은 결함이 회귀 테스트로 보호되지 않음(추정: 정확한 케이스 수는 미집계) |

## 3. 조용한 실패 경로 (질문 2 직답)
1. 소프트404/동의창/로그인벽/페이월 티저 ≥1000자 → ok (W1).
2. trafilatura 없음 + SPA 셸 → script 텍스트로 ok (W2).
3. euc-kr 모지바케 → ok (W3).
4. 파생 URL(m., wayback closest, jina) 이 다른 문서 → ok (W11).
5. 검색이 차단돼도 `[]` (W7).
6. 스캔 PDF → ok (W13).
JS 렌더링: 코드에 브라우저 계층 없음. 사다리 소진 시 `hint` 문자열로 브라우저 MCP 를 권할 뿐(fetch.py:650-651). 로그인벽/페이월: 정책상 우회 금지, 탐지 코드 없음(챌린지 마커 목록에 login/paywall 문구 없음: fetch.py:45-47).

## 4. 강화안 (예상 코드 크기·위험)

| 순위 | 강화안 | 크기 | 위험 |
|---|---|---|---|
| 1 | 본문 품질 게이트 확장: 소프트404/로그인/동의창/페이월 문구 마커(한·영) + 요청 URL slug·expected_title 과의 토큰 겹침 검사 + 인코딩 meta charset/chardet 폴백 + 폴백 정제 시 script/style 제거. 새 verdict `suspect` 추가 | 약 80~120줄 + 픽스처 테스트 | 낮음. 오탐 증가 시 partial 로 강등하는 보수 방향. 기존 demo assert 조정 필요 |
| 2 | 1차 출처 검색 백엔드 추가: `--type stats|patent|filing_kr|paper_kr` 로 DART/KOSIS/KIPRIS/KCI OpenAPI(키는 환경변수, 무료) 직접 호출, 결과에 `tier` 필드(primary/secondary) 부여. 키 없으면 명시적 실패 | 백엔드당 40~60줄, 합 200줄 내외 | 중. API 키·응답 스키마 변동, 네트워크 테스트는 픽스처 필요 |
| 3 | 검색 결과 후처리: URL 정규화(utm 제거·www/슬래시)·도메인 중복 제한·`curated_domains` 기반 등급 점수 정렬·`after:` 날짜 연산자 pass-through, 한/영 이중 질의 자동 생성 옵션. 반환에 `backend_status`(ok/blocked/empty) 추가해 W7 해소 | 약 80줄 | 낮음. 반환형을 list→dict 로 바꾸면 호출자 영향(추정: harvest_images 는 search 를 안 씀, 확인 필요) — 하위호환 위해 별도 함수 권장 |
| 4 | fetch 효율·예의: 확정 4xx(404/410/451)는 사다리 조기 종료, 429/503 은 Retry-After 반영 1회 재시도, 호스트별 최소 간격(예: 1s) 모듈 전역 dict, 오프라인 URL→sha 캐시(`_sources` meta 재사용, `--refresh` 옵션), robots.txt 는 최소한 경고 로그 | 약 70~100줄 | 중. 조기 종료가 CDN 가짜 404 를 놓칠 수 있어 404 는 mobile 1회까지만 시도하는 절충 권장 |
| 5 | 형식·용량 확장: 허용 MIME 에 xlsx/docx/csv/hwp/hwpx/zip 추가(raw 저장 전용, 텍스트는 kordoc/fitz 로 후처리), PDF 용량 한도 상향(예: 40MB, Content-Length 사전 판정)과 PDF 텍스트층 검사(fitz 로 첫 N페이지 글자 수, 0이면 `partial/scanned`) | 약 60~90줄 | 중. 보안경계(실행 금지·저장만) 유지 필요, fitz 는 HARD 의존이라 가능 |
| 6 | SearXNG 정리: 백오프 조건 수정(429 만 재시도), 인스턴스 동시 헬스체크 후 생존분만 사용·캐시, 전체 시간 상한(예: 30s), 죽은 인스턴스 목록 갱신 | 약 40줄 | 낮음 |
| 7 | 정책 정합: Googlebot 계층을 옵트인(`--allow-googlebot`)으로 바꾸거나 문서 수정, Jina 사용 시 대외비 모드에서 건너뛰는 플래그 | 약 15줄 | 낮음. 동작 변경이므로 사용자 결정 필요 |

## 5. 확인하지 못한 것
- 실제 네트워크 동작(ddg/SearXNG 현재 생존, EDGAR UA 거부 여부)은 실행 금지라 미확인 — W9, W15 는 추정.
- tests/ 개별 테스트 케이스 수(파일 단위만 집계), 테스트 내용의 W1~W3 커버 여부 미정밀 확인.
- harvest_images.py(783줄)는 grep·발췌 위주로만 봄. 이미지 검색은 같은 request_bytes 경계를 쓰고(harvest_images.py:359,559) searx 를 독자 순회함(388-412, 백오프 없음)까지만 확인.
- capture_web/capture_pdf 는 증빙 캡처 단계이며 수집 엔진 약점 범위 밖이라 개요만 확인(capture_web 는 재구성 발췌=증빙 불인정으로 설계됨).
- skill_paths.py, facts_db._write_bytes_atomic 는 읽지 않음.
