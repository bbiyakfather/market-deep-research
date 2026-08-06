# source-ladder — 검색 계층 · fetch 폴백 · Phase0 API · 4계층 검증 · WAF 정찰 · 위임

## 검색 (`scripts/search.py`)
`python search.py "쿼리" --n 10 --type web|news|academic|filing`
- 계층: DuckDuckGo HTML → SearXNG 공개인스턴스 로테이션(헬스체크·백오프) → 전문 API(arXiv=academic,
  SEC EDGAR full-text=filing, Wikipedia). `--type` 은 `curated-sources.json` 에 있는 것만, 미지원 명시 실패.
- 실패 계층은 경고 후 건너뜀(빈결과). "검색 완전성 미보장" — 내장 WebSearch 병행.
- **검색 연산자**: `site:` `filetype:pdf` `intitle:` `"정확구문"` `-제외` `OR` `after:/before:`. 영문 우선.

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
4. **Jina Reader**(`r.jina.ai`, JS렌더·정제) → `archived_url` 구분 기록.
5. **Googlebot UA** — 봇 화이트리스트 사이트용.
6. **RSS** — `rss.blog.naver.com/{id}.xml` · `/feed` · `/rss` · `/rss.xml` → `archived_url` 구분.
7. **Wayback**(`archive.org/wayback/available`) → snapshot → `archived_url` 구분.
8. **OGP 메타**(og:title·og:description) — 본문 실패 시 제목+요약만 `partial` 로(속성 순서 양방향 파싱).
9. **소진 → `status:"fail"`**: 【v9】 JS 렌더링은 먼저 **코어 내장**으로 시도한다 —
   `capture_web.capture_live()` 가 Chrome 헤드리스로 페이지를 통째로 렌더하므로 증빙 캡처는
   MCP 없이 확보된다(`references/evidence-capture.md`). 본문 **텍스트**가 더 필요하면 그 다음이
   브라우저 MCP(agent-browser 우선, playwright 폴백) 또는 대체출처.

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

### v5 보강 — '성공했다는 착각' 3종 차단
- **피드 항목 대조**: `rss` 계층이 낸 본문이 피드(`<item>`/`<entry>`)면, 대상 URL 과 일치하는
  항목이 있을 때만 `ok`. 없으면 `partial` + `feed item mismatch`. `_rss_urls` 는 사이트 공용
  피드(`/rss`,`/feed`)를 합성하므로, 이 대조가 없으면 **남의 기사 10건 요약이 그 URL 의 원문으로
  저장·해시**된다 — 재검증도 같은 바이트열을 다시 열어 완벽 일치라 원리적으로 미검출이다.
- **인코딩 판독**: 선언 charset → `<meta charset>` → utf-8 → cp949 순 strict 재시도 후에만
  replace 로 떨어진다. 읽을 수 없는 문자열이 '수집 성공'으로 남으면 원문 대조 자체가 불가능해진다.
  【v9 정정】 강등 조건은 **비율 `MOJIBAKE_MAX`(10%) 초과 그리고 개수 `MOJIBAKE_MIN_CHARS`(8)
  이상**, 둘 다 넘을 때다(`is_mojibake`). 종전엔 비율 2%만 봤는데 — 실측상 진짜 디코드
  미스매치는 33~59%(cp949→utf-8 45개/76자 = 0.592, utf-8→cp949 28개/84자 = 0.333)라 임계가
  **16배 낮았고**, 비율만으로는 길이에 따라 판정이 뒤집혔다: 짧은 본문의 대체문자 **1개**
  (40자 중 1개 = 0.025)는 강등되는데 긴 본문의 **20개**(2000자 중 = 0.010)는 통과했다.
  공시 요약표처럼 정상적으로 짧은 원문이 여기 걸린다. 백지 판정과 같은 계열의 실수다
  (`evidence-capture.md` 백지 캡처 절 참조 — **비율만으로는 크기에 따라 뒤집힌다**).
  강등에 못 미치더라도 대체문자가 하나라도 있으면 `mojibake` 비율을 증거에 병기한다.
- **MIME**: 정확일치가 아니라 `+xml` 접미 규칙(feedparser 규약). 종전에는 실서비스 피드가 쓰는
  `application/rss+xml`·`atom+xml` 이 전량 차단되고 애매한 `text/xml` 만 통과하는 역선택이었다.
  허용 범위 확대는 XML 계열까지이며 그 밖의 타입(`video/mp4` 등) 차단은 그대로다.
- **Wayback**: 조회는 `https` 고정(평문이면 중간자가 스냅샷 URL 을 바꿔 증거 원문을 통째로 교체할
  수 있다), 본문은 배너 없는 `id_` URL, 결과에 `snapshot_date` 병기. **5년 전 스냅샷이 '현재
  원문'으로 결박되지 않도록 시점은 팀리드가 판단**한다(창을 좁히면 폐업·개편 사이트의 유일한
  증거가 사라지므로 자동 강등은 하지 않는다).
- **검색 차단 ≠ 무결과**: `search_with_diagnostics()` 가 `{results, blocked_engines}` 를 준다.
  봇 차단 페이지는 HTTP 200 으로 오므로 마커(`assets/searx-instances.json` 의 `block_markers`)로
  판정하고, SearXNG 429/503 은 백오프 재시도한다. **결과 0건 + blocked_engines 비어있지 않음**을
  '이 주제엔 출처가 없다'로 결론내면 커버리지 공백이 보고서 서술로 굳는다.

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

## research-memory — 도메인 수집 레시피 축적 【v4-M】【v4-R】

### 레시피 축적 (G5 후)
G5 완료 선언 후, 이번 조사에서 실측으로 확인된 도메인별 수집 레시피를 `assets/domain-recipes.json`
에 **도메인 키드 머지**로 기록한다 — 전체 재작성 금지, 해당 도메인 키만 추가·갱신(타 도메인 항목
보존). 기록 항목: 도달한 사다리 계층 · 성공 셀렉터/엔드포인트(WAF 정찰로 포착한 내부 API 포함) ·
차단 양상 · 마지막 확인일. 계획 단계 실행가능성 리뷰의 fetch.py 실측 프로브 결과도 같은 파일에
머지한다(실측 실패는 REJECT 사유가 아니라 진단 — 레시피 갱신 입력).

### 휴리스틱 원칙 (verbatim)
> 메모리는 절차·과거 결정에 유용한 휴리스틱 맥락일 뿐 현재 상태의 권위가 아니다. 메모리 유래
> 수치·평판은 재검증 게이트 통과 없이 대장 등재 불가, 현재 원문과 충돌하면 stale 처리

레시피(어떻게 접근하나)는 재사용하되, 내용(무엇이 사실인가)은 매 조사 현재 원문으로 다시 세운다.

### 폴백 기록 규율
레시피가 있는데도 하위 계층·위임으로 폴백한 경우 기록 없이 넘어가지 않는다: ① 폴백 사유(레시피
실패 양상) ② 시도한 요청(URL·계층) ③ 기대했던 동작 — 세 가지를 세션 저널(`expansion-log.md`)에
남긴다. 이 기록이 다음 조사의 레시피 승격(갱신)의 입력이 된다.

## 정책선 (완화 불가)
인가된 대상·본인 세션만. **무단 login/CAPTCHA/paywall 우회 금지**. Googlebot UA·범용 캐시 제외.
보존: 원본(raw) + 정제본(trafilatura clean) 둘 다 + SHA-256. archived_url 은 원 URL 과 구분.
