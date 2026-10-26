# source-ladder — 검색 계층 · fetch 폴백 · Phase0 API · 4계층 검증 · WAF 정찰 · 위임

## 검색 (`scripts/search.py`)
`python search.py "쿼리" --n 10 --type web|news|academic|filing --axis <축이름> --work <work_dir>`
- 계층: **ddgs 다중 백엔드**(bing·brave·duckduckgo·google·mojeek·startpage·yahoo·yandex 자동 선택; `--type news` 는
  ddgs `news()`) → DuckDuckGo HTML 폴백 → SearXNG(`assets/searx-instances.json` 에 **자체 호스트 URL 을 등록했을 때만**,
  공개 인스턴스는 2026-10-13 전멸) → 전문 API(academic=OpenAlex→Crossref→Europe PMC→Semantic Scholar→arXiv; **arXiv 만** 질의에 공백이 있으면 `all:"구문"` 먼저·0건이면 단어별 AND(`all:w1 AND all:w2`);
  SEC EDGAR full-text=filing). web·news 는 앞 계층 결과가 `max(3, n//2)` 미만일 때만 다음 계층이 보강하고, academic 은 보강 없이 **첫 비어있지 않은 백엔드 결과**만 쓴다.
  `--type` 은 `curated-sources.json` 에 있는 것만, 미지원 명시 실패. ddgs 미설치는 `pip install ddgs`.
- ddgs `auto` 는 질의를 bing·google·yandex·wikipedia 등 여러 회사에 동시에 보낸다 — 대외비 질의는 사용자 판단(필요하면 `DDGS().text(backend="duckduckgo")` 로 제한).
- 실패 계층은 경고 후 건너뜀(빈결과). "검색 완전성 미보장" — 내장 WebSearch 병행.
- **전건 기록**: 검색식·검색일·건수를 `<work_dir>/audit/search-log.jsonl` 에 전건 기록한다(빈 검색 포함, `--axis` 로 축 표기, `--work` 생략 시 `MDR_WORK_DIR`·현재 폴더; `search()` import 호출도 기록).
  2부 커버리지 선언은 이 로그를 집계해 쓴다. Ranked web results cannot establish exhaustive coverage — 상위 결과만으로 "빠짐없음" 을 주장하지 않는다.
- **검색 연산자**: `site:` `filetype:pdf` `intitle:` `"정확구문"` `-제외` `OR` `after:/before:`. 영문 우선.
- 종료 코드 2·1차 출처 라우팅·`patents.google.com` 크롤링 금지의 정본은 `agent-briefs.md` COVERAGE·철칙이다. 이 절은 검색 계층만 다룬다.

## 학술 출처 취급
1. 레코드 ≠ 보고서 ≠ 연구: 같은 연구의 프리프린트·학술지판·보도자료·학회초록은 독립 관찰 **1건**이다.
2. DOI 가 실존한다고 근거가 되는 것은 아니다. 수치는 원문을 다시 열어 확인한다.
3. 집계처(OpenAlex·Semantic Scholar·특허 DB)와 원출처는 독립 교차검증이 아니다.
4. 인용수·h-index 는 읽는 순서용이지 포함 기준이 아니다.
5. 프리프린트는 `preprint` 로 표기하고 학술지판 게재 여부를 함께 기록한다.
6. 인용 전 Crossref `update-type:retraction` 을 1회 확인한다. 없으면 "확인한 출처 내 공지 없음" 으로 적는다.
7. `--type academic` 은 OpenAlex→Crossref→Europe PMC→Semantic Scholar→arXiv 순이다. 백엔드별 함정·한도·완전성 4단계 → `references/academic-apis.md`.
참고: K-Dense-AI/scientific-agent-skills (MIT) paper-lookup·literature-review 의 규약을 번안

## 검색만 모드 (`mdr-search`)
사실대장·재검증·게이트·캡처·PDF 없이 출처목록(`sources.md`)과 `_sources/` 원문 스냅샷만 만든다.
cwd 는 작업폴더 — `fetch.py` 가 cwd 의 `audit/` 에 로그·스냅샷을 쓴다. 스크립트는 코어 `scripts/`
절대경로로 호출한다.
흐름: `search.py` → `fetch.py get <url> --out <wd>/_sources` → `source_index.py <wd> --topic "<주제>"`.
같은 작업폴더 규칙(`skill_paths.py`)이라 이후 보고서 모드로 승격 가능하다.

## Phase0 공식/무료 API 우선 (R5)
generic fetch 전에, 소스에 공식 엔드포인트 있으면 그것부터(`curated-sources.json`의 phase0_apis).
세션에 무료 공공 MCP(opendart/DART·KOSIS·KIPRIS·KakaoMap)가 붙어있으면 **오케스트레이터가 1차소스로
기회적 사용**(유료 무의존 유지 — 무료). 없으면 무시하고 자체 스택.
- **특허/IP 1차소스**: `korean-patent-search` 스킬(KIPRIS 공식 API, 출원번호 상세조회 포함)과
  Patent Landscape Analytics MCP(출원추이·출원인 순위·CPC 분포·기술수명주기)가 세션에 있으면
  IP 랜드스케이프(기술동향 4부)·기술사업화 실사(3부 권리성)의 1차 증빙으로 기회적 사용
  (추가 도구 설치 없이 1차 소스 확보).

## fetch 사다리 (`scripts/fetch.py`)
`python fetch.py get <URL> --out _sources`
1. **공통 보안경계(계층이 아니라 공통 전제)**(`fetch.request_bytes`, 이미지 수집도 공유; **ddgs 계층은 예외** — primp 로 직접 통신하며 고정 검색엔진 호스트만 접속, 결과 URL 은 목록일 뿐, `DDGS_PROXY` 환경변수를 읽는다): HTTP(S)만 · private/loopback/link-local/reserved IP 및 리다이렉트 대상
   차단(매 홉 DNS 사전검증, 최대 5홉) · 검증한 IP로 연결 고정(curl RESOLVE / urllib 숫자 IP 연결, 원 호스트 TLS 검증 유지).
   fetch 사다리는 환경 프록시를 사용하지 않는다(목적지 IP를 검증할 수 없음). 추가 사후 IP 검사는 요청 송신 자체를 되돌리지 못한다.
   · 크기(8MB)·시간(25s)·**MIME 허용목록**(실제 게이트 — PDF 는 매직바이트`%PDF-` 로 판정, 확장자/헤더는 불신).
   원문=불신뢰(추출만, 실행 금지).
2. **curl_cffi TLS 그리드**(chrome/safari/chrome110 전수, R6). 로그 tier 라벨: `curl_cffi:<지문>`(=direct)·`mobile`·`jina`… 각 홉 SSRF 재검증. CA 번들은 ASCII 경로로.
3. **모바일**(`safari180_ios` TLS 지문 + iPhone UA + ko-KR). 모바일 URL 재작성 —
   네이버 블로그는 `m.blog.naver.com/PostView.naver?blogId=..&logNo=..`(**logNo 가 숫자일 때만**),
   그 외는 `m.` 서브도메인 시도 후 원 URL 재시도.
   **실전 핵심 계층** — 데스크톱 지문 3종이 전부 403인 Cloudflare 사이트가 여기서 뚫린다(GVR 실측).
   ⚠ WebFetch 가 403 이라고 "원문확인불가"로 넘기지 말 것 — `fetch.py` 로 한 번 더 확인한다.
   실제로 WebFetch·데스크톱 지문이 전부 막힌 GVR 이 모바일 계층으로 열렸고, 스니펫으로만
   확인해 "일치" 판정했던 건에서 오류가 나왔다(2026-07-31).
4. **브라우저**(`patchright`, 없으면 `playwright` 헤드리스 Chromium). JS 로 그려지는 페이지.
   네트워크가 잠잠해질 때까지 최대 20초, 스크롤은 최대 5회. 미설치·`MDR_BROWSER=0` 이면 건너뛴다.
   리다이렉트·하위 자원도 SSRF 검사. 이미지·폰트·미디어는 받지 않고 컨텍스트는 호출마다 새로 연다.
5. **Jina Reader**(`r.jina.ai`, JS렌더·정제) → `archived_url` 구분 기록.
6. **Googlebot UA** — 봇 화이트리스트 사이트용.
7. **RSS** — `rss.blog.naver.com/{id}.xml` · `/feed` · `/rss` · `/rss.xml` → `archived_url` 구분.
   요청 URL/GUID 또는 확인된 제목과 유일하게 대응하는 entry 본문만 검증해 `ok`로 인정한다.
   미일치 피드는 탐색 자료 `partial`로 보존하고 다음 계층을 계속 시도한다.
8. **Wayback**(`archive.org/wayback/available`) → snapshot → `archived_url` 구분.
9. **OGP 메타**(og:title·og:description) — 본문 실패 시 제목+요약만 `partial` 로(속성 순서 양방향 파싱).
10. **소진 → `status:"fail"`**: 브라우저 계층(agent-browser CLI → playwright MCP, `evidence-capture.md`, JS 렌더링)까지 실패한 상태다. `MDR_BROWSER=0` 이었으면 hint 에 남긴다. 대체출처를 찾는다.

| 스위치 | 효과 |
|---|---|
| `MDR_BROWSER=0` | 브라우저 계층을 건너뛴다 |
| `MDR_BROWSER_HEADED=1` | 브라우저를 창을 띄워 연다(설치된 Chrome). JS 챌린지는 헤드리스에서 풀리지 않는다. 화면이 있는 PC 에서만 |
| `MDR_NO_THIRD_PARTY=1` 또는 `--no-third-party` | `jina`·`wayback` 을 건너뛴다(대상 URL 을 외부로 보내지 않음) |

**도메인 라우팅**(`fetch.ROUTES`): 네이버 블로그→모바일·RSS, 네이버 뉴스/증권→Jina,
디시·펨코·요즘IT→모바일, 티스토리→RSS, 미디엄·서브스택→Jina·RSS 등.
⚠ 라우팅은 **폴백 순서만** 바꾼다 — `direct`(원 URL·원본 충실도 최고)가 **항상 먼저**다.
라우팅을 앞세우면 헛요청이 늘고, 더 나쁘게는 RSS 요약본이 본문보다 먼저 `partial` 로 잡혀
원문 대신 반환된다(한경 실측).

⚠ **파생 URL의 SSRF·미해석은 그 후보만 건너뛴다**(`_try_derived`) — 차단은 그대로 유효하되
사다리를 죽이지 않는다. 원 URL 과 `direct` 계층의 SSRF 는 계속 전파(리다이렉트 내부망 이탈 = 보안 사건).

## 4계층 성공검증 (R2) — HTTP200 ≠ 성공
`fetch.validate_body`: ⓪ **HTTP 비2xx는 PDF/HTML 모두 실패**(상태코드 우선) ① 성공 셀렉터 최우선
② 본문 길이(≥1000자면 확정 성공 — 긴 기사 속 챌린지 문구 인용은 오탐 아님) ③ 챌린지 마커(짧은
인터스티셜만 해당) ④ 비정상 크기(<200B). 판정 `ok`(셀렉터 또는 본문≥1000자) / `partial`(얇은 본문) /
`challenge`/`empty`(실패).

## WAF 조기감지 정찰 (R7) — ⚠ 이 항목만 playwright 우선
반복의도 조회에서 초기 2~3회 challenge면: 백그라운드로 fetch 격자 계속 + 포어그라운드로
브라우저 계층으로 페이지 로드 → 네트워크 요청에서 내부 `/api/`·`/graphql`·`.json` XHR 포착 →
그 JSON 엔드포인트를 fetch 로 직접 호출(대부분 API 는 HTML 보다 방어 약함). 신규 인프라 0.
- **도구 선택**: `agent-browser CLI 에는 네트워크 요청 목록 명령이 없다` — 정찰만은
  `mcp__*playwright*`(`browser_network_requests`)를 1순위로 쓴다. playwright 가 없으면
  `agent-browser eval` 로 `performance.getEntriesByType('resource')` 를 읽어 대체(리소스 URL 목록만
  나오고 요청/응답 본문은 못 본다 — 열위 폴백임을 인지할 것).

## 코어 내장 (구 insane-search 위임분)
- 강방어 우회는 `fetch.py` 사다리에 **내장**됐다 — 도메인 라우팅·모바일 지문·브라우저·Googlebot·RSS·OGP.
  `status:"delegate"` 는 폐지(현재 `ok`/`partial`/`fail`).
- **내장하지 않은 것**(시장조사 범위 밖이라 의도적 제외): 미디어 자막·메타(yt-dlp, 1,858 사이트),
  X/Twitter Syndication, Reddit `.json`, GitHub·HN·arXiv 등 플랫폼 전용 공개 API.
  이런 소스가 필요하면 `references/extract-recipes.md` 의 recipe 를 직접 쓴다.

## 정책선 (완화 불가)
인가된 대상·본인 세션만. **무단 login/CAPTCHA/paywall 우회 금지**. Googlebot UA·공개 캐시(Jina·Wayback)는 금지 대상이 아니다(공개 자료 접근).
보존: 원본(raw) + 정제본(trafilatura clean) 둘 다 + SHA-256. archived_url 은 원 URL 과 구분.
