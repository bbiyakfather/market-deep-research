# A6 크롤링 능력 재고 (mdr, 2026-10-13)

경로 약칭: S=`codes/market-deep-research/scripts/`, R=`.../references/`, A=`.../assets/`. "확인"=코드/실행 결과로 직접 본 것, "추정"=정황.
저장소 파일은 수정하지 않았다. 일회용 스크립트는 scratchpad 의 `probe_searx.py` 하나(`python -I`).

## 0. a1 보고 재확인 결과
| a1 주장 | 판정 | 근거 |
|---|---|---|
| 성공 판정 정제 본문 >=1000자 -> ok | 맞음 | fetch.py:237-238 (success_selector 가 그보다 먼저, 234-235) |
| 인코딩: Content-Type charset 만 신뢰, 없으면 utf-8, 실패 시 replace | 맞음 | fetch.py:371-378. `<meta charset>` 은 안 봄. 테스트는 헤더 charset=euc-kr 만 검증(test_adversarial.py:382-396) -> meta 전용 케이스는 미보호 |
| MIME 허용목록, 8MB 캡 | 맞음 | fetch.py:36, 42-44, 398-399; oversize 는 DownloadLimitError(353-362) |
| 사다리 순서 direct->mobile->jina->googlebot->rss->wayback->OGP | 맞음 | fetch.py:60, 566-581, 644-649 |
| Googlebot UA 사칭 / 정책문서와 모순 | 맞음 | fetch.py:55, 554-555 vs source-ladder.md:81 ("Googlebot UA·범용 캐시 제외") |
| Jina 경유 = URL 이 제3자로 나감 | 맞음 | fetch.py:405 (`https://r.jina.ai/`+원URL) |
| tests/ 총 13개 파일 | **틀림: 12개** | `ls tests`: adversarial, batch2a, 2b_fixup, 2b_regressions, 2c, 3a, 3b, 3c, e2e, p0, v4_gates, v4_semantic |
| "chrome/safari/chrome110 지문" | 맞으나 불완전 | "chrome"/"safari" 는 별칭이라 설치본에서 chrome150/safari2601 로 풀린다(아래 §2). 즉 "낡은 지문 3종"이 아니라 최신 2 + 낡은 1 |
| search.py SearXNG 백오프 로직 반대 동작 (W8) | 맞음 | search.py:73-88: 비200/429 는 `break`, 예외만 `continue` |
| W9 SearXNG 인스턴스 사망 추정 | **실측으로 확정** | §4: 5개 중 JSON 응답 0개 |

## 1. 계층 표 (fetch 사다리)
공통 transport `request_bytes`(fetch.py:312-368): 호출당 timeout 25s(리다이렉트 포함 단일 마감, 40,318), 최대 5홉, 8MB, 환경 프록시 비사용(`CurlOpt.PROXY:""` 337, urllib `ProxyHandler({})` 301), 매 홉 DNS 사전검증+RESOLVE 로 IP 고정(331-337), `verify=_CA_BUNDLE or True`(335; 비ASCII 홈이면 CA 를 ASCII 경로로 복사 86-119). 계층 간 지연·병렬·재시도 없음(순차).

| # | 계층 | 라이브러리 | 흉내 대상 | 요청 수 | 타임아웃 | 다음으로 넘기는 조건 | 제3자 유출 |
|---|---|---|---|---|---|---|---|
| 1 | direct (fetch.py:543-545) | curl_cffi `impersonate` | `chrome`(->chrome150), `safari`(->safari2601), `chrome110`; UA 는 impersonate 기본값(헤더 미지정) | 최대 3(성공 즉시 중단) | 25s/건 | verdict 가 ok 아님이면 다음 지문(ok 가 아닌 partial 도 계속). SSRF 만 예외 전파 | 없음 |
| 2 | mobile (546-551, 428-441) | curl_cffi | `safari180_ios` + iPhone UA + `Accept-Language ko-KR` + `Referer m.naver.com`(50-58); 후보: 네이버 블로그 PostView, `m.`+호스트, 원 URL | 후보 2-3 (에러 시 `safari` 로 1회 더) | 25s/건 | 비ok 면 다음 후보. SSRF/에러는 후보만 skip(`_try_derived` 526-538) | 없음 |
| 3 | jina (404-409, 552) | curl_cffi `chrome` | (대리 크롤러) | 1 | 25s | 비ok | **예: 원 URL 전체가 r.jina.ai 로 전송** |
| 4 | googlebot (554-555) | curl_cffi `chrome` TLS + Googlebot UA 문자열 | UA 만 사칭(TLS 는 Chrome 이라 IP/rDNS 불일치 -> 봇검증 사이트엔 무력, 추정) | 1 | 25s | 비ok | 없음 |
| 5 | rss (556-561, 444-507) | curl_cffi `chrome` + ElementTree | `/rss` `/feed` `/rss.xml`(+네이버 `rss.blog.naver.com/{id}.xml`) | 3-4 | 25s/건 | 단일 entry 매칭 시 ok, 아니면 partial 로 보존하고 계속 | 없음 |
| 6 | wayback (412-425) | curl_cffi `chrome` | `http://archive.org/wayback/available`(평문 http) -> closest 스냅샷 | 2 | 25s/건 | 스냅샷 없음/비ok | **예: URL 이 archive.org 로** |
| 7 | OGP (510-523, 644-649) | 정규식 | 직전 실패 HTML 의 og:title/description | 0 | - | 40자 이상이면 partial | 없음 |
| - | 소진 | - | - | - | - | `status:"fail"` + `hint`(브라우저 MCP 권고, 650-651) | - |

- 도메인 ROUTES(fetch.py:64-74, 566-581)는 direct 이후 폴백 순서만 재배열한다. 9개 패턴, 거의 전부 한국 사이트(네이버·디시·펨코·티스토리·브런치·한경 등).
- 최악의 경우 단일 URL 에 약 13 요청 x 25s (추정: 코드 경로 합산. 실측 아님). 404/410/401 도 조기 종료 없이 전 계층 소진(596-639).
- 성공 판정 validate_body(228-246): 비2xx -> empty / success_selector(원문 소문자 부분문자열) -> ok / 정제본 >=1000자 -> ok / 챌린지 마커 8개(45-47) -> challenge / <200B empty / 나머지 partial. PDF 는 `%PDF-` 매직바이트면 ok(397, 609-625), 텍스트 추출 없음.
- 브라우저 계층 없음. JS 렌더는 fetch 사다리 안에 전무(Jina 의 서버측 렌더에 간접 의존). 브라우저는 "오케스트레이터가 MCP 로" 문서 지시뿐(source-ladder.md:48, 65-73; evidence-capture.md:26).
- 다른 네트워크 경로: 검색 `search._get`(search.py:36-39, UA `Mozilla/5.0`, curl_cffi 기본 지문 `chrome`), 이미지 `harvest_images`(UA `...market-deep-research/1.0` 라 impersonate 기본 chrome 과 UA 불일치, 359, 559). 둘 다 같은 request_bytes 경계. harvest_images 는 `page_images()` 에서 fetch 사다리를 재사용(345-346).
- 검색 백엔드: DDG HTML(search.py:43) -> 결과 `<max(3,n//2)` 이면 SearXNG 5개(150-154). arXiv(92), SEC EDGAR(109), Wikipedia(132, CLI 미연결). 이미지: openverse·commons·searx(harvest_images.py:543).

## 2. 의존성 재고 (이 PC 실측)
Python 3.13.14. `importlib.metadata` 로 확인.

| 패키지 | 코드 사용처 | 필수/선택 | 없을 때 동작 | 설치 버전 |
|---|---|---|---|---|
| curl_cffi | fetch.py:76-79 (`creq`), search/harvest 가 `creq` 재사용 | preflight 는 SOFT 로 분류(preflight.py:24)하나 주석은 "사실상 필수"(9). | `creq=None` -> `request_bytes` 가 urllib 경로(311-339)로 degrade. TLS 지문·모바일 계층이 사실상 무력화(urllib 은 impersonate 무시). 경고 없이 진행 | 0.16.2 |
| trafilatura | fetch.py:80-83, `extract_text` | SOFT | 정규식 태그 제거로 폴백(249-256): script/style 내용 포함 -> 1000자 판정 부풀림(a1 W2 확정) | 2.1.0 |
| PyMuPDF (fitz) | capture_pdf/capture_web/harvest_images 상단 import | HARD(preflight.py:23) | import 실패로 스크립트 기동 불가. fetch.py 자체는 fitz 미사용 | 1.27.2.3 |
| certifi | fetch.py:95 (_ascii_ca) | 암묵적(curl_cffi 의존으로 존재) | None 이면 verify=True 기본 번들 | 2026.7.22 |
| openpyxl | preflight SOFT 만 선언. 크롤링 코드 import 없음(grep) | 선택 | - | 3.1.5 |
| yt_dlp | preflight SOFT 선언만, 코드 import 없음. extract-recipes.md 가 수동 CLI 안내 | 선택(미배선) | - | 2026.8.19 |
| urllib/http.client/ET/ssl | fetch.py 표준 라이브러리 | 필수 | - | stdlib |
| playwright | 코드 import 없음. 문서에서 "MCP" 로만 언급 | 코드상 의존 없음 | - | 1.58.0 설치됨, 브라우저 `ms-playwright/chromium-1208, 1234` 존재(확인) |
| httpx / requests | 코드 import 없음(grep) | 미사용 | - | 0.28.1 / 2.34.2 (다른 용도로 설치) |
| easyocr | 코드 import 없음 | 미사용 | - | 1.7.2 (설치만 되어 있음 -> 스캔 PDF OCR 후보로 이미 PC 에 있음) |
| 기타 PC 에 있는 것 | 코드와 무관 | - | - | selenium 4.43.0, undetected-chromedriver 3.5.5, olefile 0.47, pyhwpx 1.7.2, lxml 6.1.1, beautifulsoup4 4.15.0, markdownify 1.2.3, charset_normalizer 3.4.7. chardet 없음 |
| 외부 바이너리 | pandoc(3.10 확인), Chrome(`C:\Program Files\Google\Chrome\...` 확인) | HARD | PDF 렌더용. 크롤링 아님 | - |

requirements.txt / pyproject.toml / setup.cfg: **없음**(`ls` 확인). install.py 는 파일 복사/해시 검증만 하고 pip 설치를 하지 않는다(grep: pip 문자열 없음). 의존성 선언의 유일한 출처는 preflight.py 의 메시지 `pip install curl_cffi trafilatura`(83) 한 줄 -> 버전 핀 없음.

### curl_cffi 프로필 대조 (설치 0.16.2)
`BrowserType` 지원 목록(44개): chrome99..146/150, `chrome110`, safari153..2601, `safari180_ios`, `safari260_ios`, firefox133/135/144/147, tor145, edge99/101.

| 코드의 문자열 | 위치 | 설치본에서의 실제 의미 | 낡음 |
|---|---|---|---|
| `chrome` | fetch.py:41, 406, 555 등 | `REAL_TARGET_MAP`: -> **chrome150**(DEFAULT_CHROME) | 최신. 라이브러리 업그레이드 시 자동 갱신(별칭) |
| `safari` | fetch.py:41, 550 | -> **safari2601** | 최신 |
| `chrome110` | fetch.py:41 | 그대로 chrome110 (Chrome 110, 2023-02 경, 추정) | **낡음(약 40 메이저 뒤처짐)**. 의도는 "다른 TLS 지문 변종". 현대 WAF 가 오래된 Chrome 지문을 의심할 수 있음(추정) |
| `safari180_ios` | fetch.py:58 | 그대로 iOS Safari 18.0 (2024-09 경) | 별칭 `safari_ios`(->safari260_ios)가 있는데 쓰지 않음. UA 는 `iPhone OS 17_0`/`Version/17.0`(50-51)으로 **지문(18.0)과 UA(17.0) 불일치** |
| firefox / edge / tor | 코드 미사용 | - | 지문 다양성 0(chrome 계열 2 + safari 2) |
- 고정 프로필이 문자열 3개뿐이라 curl_cffi 가 새 프로필을 추가해도 `chrome110`, `safari180_ios` 만 수동 갱신 대상이다. 업그레이드 시 `impersonate` 이름 제거/개명 위험: 다음 메이저에서 `chrome110` 이 빠지면 direct 3번째 시도가 에러 처리됨(추정; `_fetch_once` 가 ValueError/OSError 만 잡음 -> 다른 예외는 `_fetch_ladder` 의 광범위 except(636)로 흡수).
- 모바일 폴백 조건 `reason.startswith("error:")`(fetch.py:549) 은 `_try_derived` 가 예외를 잡았을 때만 참. curl_cffi 가 미지원 프로필에서 ValueError/OSError 계열을 던지면 `_fetch_once` 가 잡아 `error:` 가 아니게 되어 폴백 안 탈 수 있음(추정, 미검증).

## 3. 능력 격차 표
| 항목 | 판정 | 근거 |
|---|---|---|
| JS 로 그려지는 SPA | **불가**(Jina 간접 의존 = 부분) | 코드에 브라우저 없음; fetch.py:650-651 hint 만. trafilatura 없으면 빈 셸이 ok 로 통과(249-256). 브라우저 MCP 는 오케스트레이터 몫(source-ladder.md:48) |
| Cloudflare 류 챌린지 | **부분** | TLS 지문+모바일+Jina 만. 챌린지 마커 8개로 감지(45-47) 후 사다리 계속. 자바스크립트 챌린지/Turnstile 해결 불가. 정책상 CAPTCHA 우회 금지(fetch.py:10) |
| 무한 스크롤·더 보기 | **불가**(코드), MCP 로 수동 | 코드에 스크롤/클릭 로직 없음. evidence-capture.md 의 find->scroll_to 레시피는 캡처용 |
| 로그인/쿠키 필요 페이지 | **불가** | cookie 처리 코드 0(grep). G3 쿠키 추출은 계획서에만(enhancement-directions.md:140); 정책상 무단 우회 금지. `success_selectors` 만 있음 |
| 사이트 전체 크롤·사이트맵·링크 따라가기 | **불가** | sitemap/link-follow 코드 0(grep). `_rss_urls` 가 `/rss` 류 후보를 추측하는 것뿐. harvest_images 가 한 페이지의 img 만 파싱 |
| 페이지네이션 | **불가** | 전용 로직 없음. 호출자(LLM)가 URL 을 만들어 반복 호출 |
| PDF | **부분** | 수신·저장·sha 는 가능(397, 609-625, 710). 8MB 초과 불가(36). 텍스트 추출은 fetch 가 안 함(text=""); 정확숫자 캡처는 capture_pdf.py(fitz). 스캔 PDF 는 "OCR 한계 고지+실패상태"(capture_pdf.py:5-6, extract-recipes.md:26-28) |
| HWP/HWPX/XLSX/DOCX/CSV/ZIP | **불가**(fetch 단계) | ALLOWED_MIME 에 없음 -> `mime:` 실패(42-44, 398-399). 변환은 별도 kordoc/mdr-hwpx(fetch 와 비연결) |
| 이미지 OCR | **불가** | OCR 코드 0(grep). easyocr 는 설치만. harvest_images 는 도판 크롭·다운로드까지 |
| 구조화 추출(표·JSON-LD) | **부분** | trafilatura `include_tables=True`(251). PDF 표는 문서상 fitz `find_tables()` 안내만(extract-recipes.md:23). JSON-LD/microdata 코드 0 |
| 동시 요청 | **불가** | 전부 순차(스레드/async 없음, grep) |
| 호스트별 속도 제한 | **불가** | 호스트 간격 로직 없음; `time.sleep` 은 search.py:76 한 곳뿐 |
| 캐시 | **불가** | 같은 URL 재호출 시 항상 재요청. `_sources/<sha12>.meta.json` 은 결과 저장일 뿐 사전 조회 안 함(save 701-753) |
| 재시도 | **부분** | 지문 3종 순회가 사실상의 재시도. 429/503 Retry-After 처리 없음(grep). SearXNG 만 예외 시 1/2/4s |
| robots 준수 | **불가** | robots 처리 코드 0(grep). 정책선은 "인가된 대상"(fetch.py:10) |
| 프록시 | **불가(의도적)** | 환경 프록시 의도적 미사용(fetch.py:219-221, 301, 337). IP 고정 SSRF 방어와 상충하므로 도입 시 설계 변경 필요 |
| 감사·재현성 | 가능 | audit/fetch-log.jsonl + `_fetch_snapshots`(126-161), sha256, URL 이력(701-753) |
| SSRF/DNS 리바인딩 방어 | 가능 | 5홉 재검증, RESOLVE 고정, 사후 primary_ip 검사(fetch.py:175-224, 312-368) |

## 4. 실측 결과 (읽기 전용)
**preflight** (`python -I scripts/preflight.py`, exit 0): HARD 전부 OK(python 3.13.14, fitz, pandoc 3.10, chrome). SOFT 전부 OK(curl_cffi, trafilatura, openpyxl, yt_dlp). 파일 쓰기 시도 없음. 단, preflight 는 **버전을 출력하지 않고** playwright/easyocr 존재도 보지 않는다.

**SearXNG 생존** (`probe_searx.py`, 인스턴스당 GET 1회, 타임아웃 8s, UA `Mozilla/5.0`, `/search?q=test&format=json`):
| 인스턴스 | 결과 |
|---|---|
| searx.be | HTTP 200 이지만 **본문이 JSON 아님**(format=json 차단 추정) -> search.py:79 의 `startswith("{")` 에서 탈락 |
| searx.tiekoetter.com | 429 |
| search.brave4u.com | DNS 해석 실패(getaddrinfo 11001) |
| priv.au | 429 |
| search.rhscz.eu | 429 |
-> **JSON 을 돌려준 인스턴스 0/5.** 현재 SearXNG 보강 경로는 사실상 죽어 있고, 검색은 DDG 단일 장애점(a1 W9 확정). 단, 429 는 IP 단위 제한일 수 있어 다른 네트워크에선 다를 수 있음(추정). 이 외 사이트 접촉·부하 시험은 하지 않았다.

미실행: pytest 전체(`-I` 로는 `finalize_report` 임포트 실패 — 테스트가 scripts 를 sys.path 에 기대는 구조, 실행 안 함), DDG·Jina·Wayback 라이브 호출.

## 5. 테스트 보호 범위와 교체 시 깨질 계약
### 이미 보호되는 것 (fetch 관련 테스트)
- test_adversarial.py: SSRF 목록(145-153), 챌린지 인용(155-158), 4xx 본문 불신(319-333), 위조 PDF(336-357), 비허용 MIME(360-379), euc-kr **헤더** 디코드(382-396), 리다이렉트/홉 SSRF(399-431), DNS 리바인딩 사후 IP(434-470, `_FakeCreq` 로 curl_cffi 흉내).
- test_batch2a_regressions.py: request_bytes 리다이렉트·크기캡(176-210), 감사 로그(218-226), PDF 503(228-230), RSS 매칭 4종(246-292), **모바일 폴백**: `IMPERSONATE_GRID` 앞 3호출 순서와 `MOBILE_HEADERS` 검증(290-301).
- test_batch2c_regressions.py: `fetch.save` 이력 누적(236-266). fetch.py `demo()` 자체 assert(757-866): validate_body, _tier_order, _mobile_urls, _rss_urls, _ogp_partial, meta 사이드카.
- 테스트 함수 수(`def test` 개수): 2a 24, 2b_fixup 6, 2b 28, 2c 14, 3a 13, 3b 9, 3c 29, p0 44, v4_gates 36, v4_semantic 30. adversarial/e2e 는 `@case` 데코레이터 방식이라 0으로 집계됨(자체 러너).

### 보호되지 않는 것
소프트404/로그인벽 >=1000자 ok(a1 W1), trafilatura 부재 시 폴백 정제, `<meta charset>`-only 인코딩, Jina 호출 경로(`_via_jina`)·Wayback 파싱(`_via_wayback`)·Googlebot 계층·OGP 분기, search.py 의 DDG HTML 파싱·SearXNG 백오프(grep: `_ddg`/`_searx` 를 참조하는 테스트 0), ROUTES 의 실제 요청 순서(demo assert 만), 타임아웃/마감 경로.

### 라이브러리 교체 시 계약 (호출처 grep 결과)
| 계약 | 정의 | 호출처 |
|---|---|---|
| `creq` (curl_cffi.requests 모듈 또는 None) 과 `client.get(url, impersonate=, timeout=, allow_redirects=False, stream=True, headers=, verify=, curl_options={CurlOpt.RESOLVE, CurlOpt.PROXY})`, 응답의 `.status_code .headers .iter_content() .primary_ip .close()` | fetch.py:76-79, 329-337, 222 | search.py:26,37; harvest_images.py:32,359,559; 테스트 `_FakeCreq`/`SimpleNamespace(get=...)`(test_adversarial.py:99, batch2a 290) 가 이 모양을 흉내 -> **새 라이브러리는 같은 모양의 어댑터가 필요**하고 `creq` 이름을 monkeypatch 하는 테스트도 다수 |
| `request_bytes(url,*,impersonate,headers,timeout,max_bytes,max_redirects,client) -> {status, headers(소문자 키), raw, final_url}` | fetch.py:312 | search._get, harvest_images._json_get/download, fetch._fetch_once, 테스트 batch2a:176-210 |
| `response_text(response)->str` | fetch.py:371 | search.py:39, harvest_images.py:362 |
| `_fetch_once -> {ok, reason, status, text, final_url, mime, raw, is_pdf}` | fetch.py:381 | `_candidates`, `_via_jina`, `_via_wayback`, 테스트 다수 |
| `validate_body -> {verdict: ok|partial|challenge|empty, reason}` | fetch.py:228 | `_fetch_ladder:612`; test_adversarial:156,327,329,346; demo |
| 사다리 내부 상태 `acquisition_status ∈ {ok, partial, fail}` | fetch.py:613 | `_audit_fetch_attempt`(149) -> `audit/fetch-log.jsonl` 의 `status` 컬럼 -> **source_index.py:139, 207, 245 가 이 로그를 읽음**; batch2a:222 |
| `fetch(url, success_selectors, expected_title) -> {status: ok|partial|fail, final_url, http_status, archived_url, mime, text, raw, is_pdf, trace, note, fetch_ref, fetch_refs, hint?}` | fetch.py:654, 673-678 | harvest_images.py:345-351 (`r.get("raw")`, `"text"`, `"final_url"`, `"note"`), CLI(890-895), 테스트 batch2a:220,248 |
| `note ∈ {direct 이외 계층명: mobile|jina|googlebot|rss|wayback|ogp|pdf}`, trace 항목 라벨 `curl_cffi:<imp>`, `mobile`, ... | fetch.py:545-563 | test_n03 가 `note=="mobile"` 단언(batch2a:299). 감사 로그 `tier` 필드 |
| `save(result, out_dir, url) -> meta {url, final_url, http_status, mime, is_pdf, sha256, accessed_at, title, raw, clean, status, fetch_ref, urls[]}` + `_raw/_clean/.meta.json` 파일 규약 | fetch.py:701-753 | mdr-search 흐름(source-ladder.md:21), facts_db 가 sha256 로 결박(facts_db.py:456), batch2c 테스트 |
| 클래스 `SsrfBlocked`, `DownloadLimitError`, 상수 `IMPERSONATE_GRID`, `MOBILE_IMPERSONATE`, `MOBILE_HEADERS`, `MAX_BYTES`, `CHUNK_BYTES` | fetch.py | 테스트가 직접 참조(batch2a:196,209,300-301) |
| `search(query, n, type) -> list[{title,url,snippet,source}]` | search.py:145 | CLI/mdr-search 문서. 반환형 list 는 실패/무결과 구분 불가(a1 W7) |
| `ALLOWED_MIME` 문자열 reason `mime:<type>`, `http <n>`, `oversize` | fetch.py:399, 396, 354 | test_adversarial:368 이 `startswith("mime:")` 단언 |

핵심 교체 지점은 `request_bytes` 한 곳(검색·이미지·fetch 가 공유)이며 거기서 `client` 인자로 주입 가능한 구조라 어댑터 삽입이 쉽다. 반면 브라우저(JS 렌더) 계층을 추가하려면 `_candidates` 에 새 tier 이름과 `DEFAULT_ORDER`(60), `ROUTES` 를 건드려야 하고, demo 의 `plain == DEFAULT_ORDER`(792), `len(order)==len(DEFAULT_ORDER)`(797) assert 가 영향받는다.

## 6. 확인하지 못한 것
- 실제 사이트 대상 성공률(실측 금지 범위), DDG 현재 생존·차단 여부, Jina/Wayback 응답.
- 전체 pytest 통과 여부(실행 안 함), `chrome110` 정확한 릴리스 시점은 일반 지식(Chrome 110 = 2023-02)이지 curl_cffi 문서 확인은 아님.
- curl_cffi 가 미지원 impersonate 이름에서 던지는 예외 타입(모바일 폴백 조건과 관련).
- harvest_images.py 는 import/네트워크 부분만 읽음(783줄 전수 아님).
