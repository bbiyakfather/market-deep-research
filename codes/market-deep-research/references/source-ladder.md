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

## fetch 사다리 (`scripts/fetch.py`)
`python fetch.py get <URL> --out _sources`
1. **보안경계(선제)**: HTTP(S)만 · private/loopback/link-local/reserved IP 및 리다이렉트 대상 차단(SSRF)
   · 크기(8MB)·시간(25s)·MIME 제한. 원문=불신뢰(추출만, 실행 금지).
2. **curl_cffi TLS 그리드**(chrome/safari/chrome110 전수, R6). 각 홉 SSRF 재검증. CA 번들은 ASCII 경로로.
3. **Jina Reader**(`r.jina.ai`, JS렌더·정제) → `archived_url` 구분 기록.
4. **Wayback**(`archive.org/wayback/available`) → snapshot → `archived_url` 구분.
5. **소진 → `status:"delegate"`**: 오케스트레이터가 **insane-search 스킬**로 위임(강방어 사이트).

## 4계층 성공검증 (R2) — HTTP200 ≠ 성공
`fetch.validate_body`: ① 챌린지 마커(Just a moment/DataDome/Access Denied 등) ② 비정상 크기(<200B)
③ 쿠키/빈SPA ④ 성공 셀렉터. 판정 `ok`(본문≥1000자) / `partial`(OGP만) / `challenge`/`empty`(실패).

## WAF 조기감지 정찰 (R7, playwright MCP)
반복의도 조회에서 초기 2~3회 challenge면: 백그라운드로 fetch 격자 계속 + 포어그라운드로
`mcp__*playwright*` 로 페이지 로드 → 네트워크 요청에서 내부 `/api/`·`/graphql`·`.json` XHR 포착 →
그 JSON 엔드포인트를 fetch 로 직접 호출(대부분 API 는 HTML 보다 방어 약함). 신규 인프라 0.

## 위임 트리거 (insane-search 스킬)
- fetch `status:"delegate"` · X/Reddit/YouTube/GitHub/Threads/Mastodon/네이버 등 플랫폼 · 미디어 자막/메타.
- 위치: `~/.claude/plugins/.../insane-search`. 이중구현 금지 — 자체 스택 소진 후 위임.

## 정책선 (완화 불가)
인가된 대상·본인 세션만. **무단 login/CAPTCHA/paywall 우회 금지**. Googlebot UA·범용 캐시 제외.
보존: 원본(raw) + 정제본(trafilatura clean) 둘 다 + SHA-256. archived_url 은 원 URL 과 구분.
