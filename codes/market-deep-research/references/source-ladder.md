# source-ladder — 검색 계층 · fetch 폴백 · Phase0 API · 4계층 검증 · WAF 정찰 · 위임

## 검색 (`scripts/search.py`)
`python search.py "쿼리" --n 10 --type web|news|academic|filing`
- 계층: DuckDuckGo HTML → SearXNG 공개인스턴스 로테이션(헬스체크·백오프) → 전문 API(arXiv=academic,
  SEC EDGAR full-text=filing, Wikipedia). `--type` 은 `curated-sources.json` 에 있는 것만, 미지원 명시 실패.
- 실패 계층은 경고 후 건너뜀(빈결과). "검색 완전성 미보장" — 내장 WebSearch 병행.
- **검색 연산자**: `site:` `filetype:pdf` `intitle:` `"정확구문"` `-제외` `OR` `after:/before:`. 영문 우선.

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
1. **보안경계(선제+사후)**: HTTP(S)만 · private/loopback/link-local/reserved IP 및 리다이렉트 대상
   차단(SSRF, DNS 사전검증) · **연결 후 실접속 IP(primary_ip) 재검증**(DNS 리바인딩 TOCTOU 방지)
   · 크기(8MB)·시간(25s)·**MIME 허용목록**(실제 게이트 — PDF 는 매직바이트`%PDF-` 로 판정, 확장자/헤더는 불신).
   원문=불신뢰(추출만, 실행 금지).
2. **curl_cffi TLS 그리드**(chrome/safari/chrome110 전수, R6). 각 홉 SSRF 재검증. CA 번들은 ASCII 경로로.
3. **모바일**(`safari180_ios` TLS 지문 + iPhone UA + ko-KR). 모바일 URL 재작성 —
   네이버 블로그는 `m.blog.naver.com/PostView.naver?blogId=..&logNo=..`(**logNo 가 숫자일 때만**),
   그 외는 `m.` 서브도메인 시도 후 원 URL 재시도.
   **실전 핵심 계층** — 데스크톱 지문 3종이 전부 403인 Cloudflare 사이트가 여기서 뚫린다(GVR 실측).
   ⚠ WebFetch 가 403 이라고 "원문확인불가"로 넘기지 말 것 — `fetch.py` 로 한 번 더 확인한다.
   실제로 WebFetch·데스크톱 지문이 전부 막힌 GVR 이 모바일 계층으로 열렸고, 스니펫으로만
   확인해 "일치" 판정했던 건에서 오류가 나왔다(2026-07-31).
4. **Jina Reader**(`r.jina.ai`, JS렌더·정제) → `archived_url` 구분 기록.
5. **Googlebot UA** — 봇 화이트리스트 사이트용.
6. **RSS** — `rss.blog.naver.com/{id}.xml` · `/feed` · `/rss` · `/rss.xml` → `archived_url` 구분.
7. **Wayback**(`archive.org/wayback/available`) → snapshot → `archived_url` 구분.
8. **OGP 메타**(og:title·og:description) — 본문 실패 시 제목+요약만 `partial` 로(속성 순서 양방향 파싱).
9. **소진 → `status:"fail"`**: 브라우저 MCP(JS 렌더링 — agent-browser 우선, playwright 폴백) 또는 대체출처로.

**도메인 라우팅**(`fetch.ROUTES`): 네이버 블로그→모바일·RSS, 네이버 뉴스/증권→Jina,
디시·펨코·요즘IT→모바일, 티스토리→RSS, 미디엄·서브스택→Jina·RSS 등.
⚠ 라우팅은 **폴백 순서만** 바꾼다 — `direct`(원 URL·원본 충실도 최고)가 **항상 먼저**다.
라우팅을 앞세우면 헛요청이 늘고, 더 나쁘게는 RSS 요약본이 본문보다 먼저 `partial` 로 잡혀
원문 대신 반환된다(한경 실측).

⚠ **파생 URL의 SSRF·미해석은 그 후보만 건너뛴다**(`_try_derived`) — 차단은 그대로 유효하되
사다리를 죽이지 않는다. 원 URL 과 `direct` 계층의 SSRF 는 계속 전파(리다이렉트 내부망 이탈 = 보안 사건).

## 4계층 성공검증 (R2) — HTTP200 ≠ 성공
`fetch.validate_body`: ⓪ **HTTP 4xx/5xx 는 본문 무관 즉시 실패**(상태코드 우선) ① 성공 셀렉터 최우선
② 본문 길이(≥1000자면 확정 성공 — 긴 기사 속 챌린지 문구 인용은 오탐 아님) ③ 챌린지 마커(짧은
인터스티셜만 해당) ④ 비정상 크기(<200B). 판정 `ok`(셀렉터 또는 본문≥1000자) / `partial`(얇은 본문) /
`challenge`/`empty`(실패).

## WAF 조기감지 정찰 (R7) — ⚠ 이 항목만 playwright 우선
반복의도 조회에서 초기 2~3회 challenge면: 백그라운드로 fetch 격자 계속 + 포어그라운드로
브라우저 MCP 로 페이지 로드 → 네트워크 요청에서 내부 `/api/`·`/graphql`·`.json` XHR 포착 →
그 JSON 엔드포인트를 fetch 로 직접 호출(대부분 API 는 HTML 보다 방어 약함). 신규 인프라 0.
- **도구 선택**: `agent-browser 에는 네트워크 요청 목록 도구가 없다` — 정찰만은
  `mcp__*playwright*`(`browser_network_requests`)를 1순위로 쓴다. playwright 가 없으면
  `agent_browser_eval` 로 `performance.getEntriesByType('resource')` 를 읽어 대체(리소스 URL 목록만
  나오고 요청/응답 본문은 못 본다 — 열위 폴백임을 인지할 것).

## 코어 내장 (구 insane-search 위임분)
- 강방어 우회는 `fetch.py` 사다리에 **내장**됐다 — 도메인 라우팅·모바일 지문·Googlebot·RSS·OGP.
  `status:"delegate"` 는 폐지(현재 `ok`/`partial`/`fail`).
- **내장하지 않은 것**(시장조사 범위 밖이라 의도적 제외): 미디어 자막·메타(yt-dlp, 1,858 사이트),
  X/Twitter Syndication, Reddit `.json`, GitHub·HN·arXiv 등 플랫폼 전용 공개 API.
  이런 소스가 필요하면 `references/extract-recipes.md` 의 recipe 를 직접 쓴다.

## 정책선 (완화 불가)
인가된 대상·본인 세션만. **무단 login/CAPTCHA/paywall 우회 금지**. Googlebot UA·범용 캐시 제외.
보존: 원본(raw) + 정제본(trafilatura clean) 둘 다 + SHA-256. archived_url 은 원 URL 과 구분.
