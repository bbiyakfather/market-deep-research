# 외부 크롤링 선택지 조사 (기준일 2026-10-13)

## 0. 읽는 법 / 검증 수준
- **[P]** = PyPI JSON(`https://pypi.org/pypi/<pkg>/json`)을 직접 조회해 얻은 값 (버전·최신 업로드일·라이선스 표기). 가장 신뢰.
- **[G]** = GitHub README/Releases/문서를 WebFetch 로 열람(요약 모델 경유라 세부 표현은 원문 재확인 필요).
- **[S]** = 검색 요약만 본 것. 제작사 블로그는 이해관계가 있으므로 "자체 주장"으로 표기.
- 확인 못 한 것은 "미확인". 패키지 설치·실행·우회 시도는 하지 않았다(문서 조사만).
- PyPI "최신"은 정식(stable) 기준. 베타는 따로 적음.

## 1. 범주별 비교표

### A. HTTP 클라이언트 (TLS/HTTP2/HTTP3 지문)
| 후보 | 최신 정식(날짜) [P] | 최근 6개월 활동 | 라이선스 | Windows | 비동기 | 비고 |
|---|---|---|---|---|---|---|
| **curl_cffi** | 0.16.3 (2026-09-02); 베타 0.16.4b1 (09-20) | 활발 (8~9월 연속 릴리스) | MIT | win_amd64/arm64 wheel 약 2MB [P] | 예 | HTTP/2·HTTP/3·WebSocket [G]. 타깃: chrome 99~150, safari 153~2601(+ios), firefox 133~147, edge 99/101, tor 145, chrome_android [G docs]. HTTP/3 은 chrome145/146/150·firefox147 만 [G docs] |
| **wreq** (Rust, rquest 후신으로 추정) | 0.13.0 (2026-10-05) | 활발 (9~10월 3회) | Apache-2.0 | 소스 빌드 대상에 포함, 배포 wheel 은 미확인 | 예 | Python>=3.11. "100+ 프로필", 예제에 Chrome154 [G]. HTTP/3 언급 없음. 독립 지문 검증 못 찾음 |
| rnet | 2.4.2 (2025-08-02) GPL-3.0; 3.0.0rc22 (2026-02-24) | 정식은 정체, rc 이후 PyPI 상 없음 | GPL-3.0 | - | 예 | `0x676e67/rnet` URL 이 `wreq-python` 저장소로 열림 → wreq 로 개명·이관된 것으로 판단(추정). 신규 도입은 wreq 로 |
| **primp** | 2.0.1 (2026-09-13) | 활발 (5~9월) | MIT | 미확인 | 예 | Rust. 독립 테스트 1건에서 Chrome JA4 일치 [S] |
| tls-client | 2.0.0 (2026-10-10), 직전 정식은 2024-02 | 갑자기 재개 | MIT | win_amd64 wheel 8MB [P] | 미확인 | Go 공유 라이브러리 래퍼. 2.5년 공백 후 재개라 장기 신뢰는 관찰 필요 |
| hrequests | 0.9.2 (2024-12-01) | **없음** | Apache-2.0 | - | - | 사실상 정체 |
| niquests | 3.21.2 (2026-09-23) | 활발 | Apache-2.0 | 순수 Python 계열 | 예 | HTTP/2·3 지원 requests 후계. **브라우저 TLS 지문 흉내는 아님**(미확인이나 설계 목적이 다름) |
| httpx | 0.28.1 (2024-12-06); 1.0.dev6 (2026-08-31) | 정식 정체 | BSD-3 | 예 | 예 | 독립 테스트: HTTP/2 이지만 Chrome JA4 와 불일치 [S] |

### B. 탐지 회피 브라우저
| 후보 | 최신(날짜) [P] | 라이선스 | 엔진 | 비고 |
|---|---|---|---|---|
| **patchright** | 1.63.0 (2026-09-20) | Apache-2.0 | Playwright 패치(Chromium/Chrome) | Playwright API 드롭인. 벤치마크 작성자: `channel=chrome` 이 패치보다 중요 [S] |
| **camoufox** (PyPI 래퍼) | 0.5.8 (2026-10-06); 0.5.9b3 (10-13) | MIT(래퍼), 브라우저 MPL-2.0 | 패치 Firefox | GitHub 릴리스는 v156.0.1-beta.38 (10-13), 모두 beta 표기 [G]. README: "프로덕션 안정 사용에 부적합할 수 있음", Firefox 신원만 제공 |
| **nodriver** | 0.50.6 (2026-10-08) | **AGPL-3.0** | 시스템 Chrome 직접 CDP | 31 타깃 벤치 1위 [S]. AGPL 검토 필요 |
| zendriver | 0.17.1 (2026-10-02) | **AGPL-3.0** | nodriver 포크 | 커뮤니티 PR 수용, 이슈 58 건 [G] |
| pydoll | 3.0.0 (2026-09-29) | MIT [G] | 순수 CDP | 1인 유지, "다소 벅차다" 공지 [G]. Turnstile 은 "우회 아님" 이라고 스스로 명시 |
| SeleniumBase (UC/CDP) | 4.56.1 (2026-10-12) | MIT | Chrome | Windows 지원 명시 [G]. 우회 주장은 자체 주장 |
| cloakbrowser | 0.6.2 (2026-10-12) | 래퍼 MIT, **바이너리는 별도 약관** | 패치 Chromium 바이너리 ~200MB | v148+ 는 Pro 구독 필요, 다운로드 vendor 도메인 [G] |
| rebrowser-playwright | 1.52.0 (2025-05-09) | Apache-2.0 | - | 벤치에서 순정 Playwright 와 차단 집합 동일 [S] |
| undetected-chromedriver | 3.5.5 (2024-02-17) | GPL-3.0 | - | **정체** |
| botasaurus / -driver | 4.0.97 (2026-01-06) / 4.0.101 (2026-08-10) | MIT | - | 드라이버는 활동, 프레임워크 본체는 9개월 정체 |
| playwright-stealth | 2.0.3 (2026-04-04) | MIT | JS 주입 | 약한 방식 |

### C. 통합 프레임워크
| 후보 | 최신(날짜) [P] | 라이선스 | 자동 승격 | 비고 |
|---|---|---|---|---|
| Scrapling | 0.4.15 (2026-08-23) | BSD-3 | 문서상 자동 승격 설명 없음 [G] | Fetcher/DynamicFetcher/StealthyFetcher 3계층, 스파이더 포함. 우회 주장은 자체 주장 |
| Crawlee (Python) | 1.10.4 (2026-10-06) | Apache-2.0 | AdaptivePlaywrightCrawler 가 HTTP/브라우저 예측·전환 [G] | 대량 크롤 지향. 기본 HTTP 클라이언트가 impit(지문 흉내 범위 미확인) |
| crawl4ai | 0.9.4 (2026-09-23) | Apache-2.0 (+표기 요청) | 아니오 | 브라우저 기반 + Docker API |
| Scrapy | 2.19.0 (2026-09-10) | BSD-3 | 아니오 | 플러그인 조합 필요 |

### D. Firecrawl 대체
| 후보 | URL 이 제3자로? | 로컬 실행 | 라이선스 | 비고 |
|---|---|---|---|---|
| Firecrawl 자체호스팅 | 아니오 | 가능 | **AGPL-3.0** (SDK는 MIT) [G] | v2.11.162 기준 문서: Fire-engine 없음, 스크린샷·액션 불가, agent/interact 클라우드 전용, 인증 기본 꺼짐 [G]. 우리 요건(캡처)과 충돌 |
| crawl4ai | 아니오 | Docker/로컬 | Apache-2.0 | stealth·undetected 어댑터, 영속 프로필, CDP 원격 브라우저 [G] |
| Jina Reader OSS | 아니오 | Docker `ghcr.io/jina-ai/reader:oss` | Apache-2.0 | 2026-04 SaaS 코드와 재동기화, 이미지에 Chrome·LibreOffice·CJK 폰트 포함 [G]. 지문 우회 기능은 언급 없음 |
| Steel Browser | 아니오 | Docker | Apache-2.0 | 공개 베타, 세션·스크린샷·scrape API, 안티디텍션 플러그인 [G]. steel-sdk 0.19.0 (2026-06-23) |
| Spider | 로컬 크롤러는 아니오 | 가능 | MIT | `spider_rs`. `spider_cloud` 쪽은 API 키 필요 [G] |
| Stagehand | 로컬 모드는 LLM 에 페이지 맥락이 감 | 가능(Chrome) | MIT | 4.2.1 (2026-10-10) [P]. LLM 필수 성격 → 대외비 부적합 |
| ScrapeGraphAI | LLM 경유 | 가능 | 표기 없음 | 2.3.1 (2026-10-06) [P]. LLM 의존 |
| Tavily Extract | **예** | 불가 | - | `POST api.tavily.com/extract`, 1~20 URL, basic 5건당 1크레딧 [G docs] |
| Exa contents | **예**(호스팅 API로 판단, 문서 본문은 리다이렉트로 못 열었음 → 미확인) | 불가 | - | exa-py 2.25.0 (2026-10-01) [P] |
| Browserbase | **예** | 불가 | (Stagehand 는 MIT) | 클라우드 브라우저 |
| ScrapingBee / Zyte | 예(통상 SaaS) | 불가 | - | 이번 조사에서 문서 미열람 → 미확인 |

### E. 본문 추출·문서 변환
| 후보 | 최신(날짜) [P] | 라이선스 | 비고 |
|---|---|---|---|
| **trafilatura** | 2.3.1 (2026-10-06); 2.3.0 (10-02); 2.2.0 (07-31) | Apache-2.0 | 활발. 2.3.0: 폼·링크팜·무한스크롤·중첩 리스트·Markdown 개선, 다운로드 로직 개편 [G] |
| readability-lxml | 0.9 (2026-08-27) | Apache-2.0 | 18개월 공백 후 재개 |
| resiliparse | 1.0.9 (2026-07-20) | Apache-2.0 | WCXB 에서 F1 0.797(재현율↑, 보일러플레이트↑) [S]. Windows wheel 여부 미확인 |
| magic-html | 0.1.8 (2026-06-28) | Apache-2.0 | WebMainBench 행에 따라 0.514~0.714 로 엇갈림 [S] |
| MarkItDown | 0.1.8 (2026-09-21) | MIT | Office/PDF → Markdown |
| docling | 2.138.0 (2026-10-12) | MIT | 매우 활발 |
| MinerU | 4.0.12 (2026-10-11) | "MinerU Open Source License"(Apache 2.0 + 추가 조건) [G] | `mineru[full]` 약 5GB, Windows 가능, 한국어 OCR 언어 지원은 미확인 |
| magic-pdf | 1.3.12 (2025-05-24) | AGPL-3.0 | MinerU 구버전. 정체 |
- 독립 벤치: WCXB(2,008 페이지, 13 시스템, 기사형 최고 F1 0.93, 구조형 0.41~0.84) https://arxiv.org/abs/2605.21097 [G]. 한국어 포함 여부와 개별 시스템 점수는 초록에 없어 **미확인**. WebMainBench: Readability 0.654 / Trafilatura 0.640 / Resiliparse 0.629 (ROUGE-N F1) https://github.com/opendatalab/WebMainBench [S].
- 한국어 페이지·표·PDF 품질에 대한 독립 비교는 **못 찾음**.

### F. 챌린지 대응의 현실
- **독립·통제 벤치는 사실상 없다.** 대부분 상용 우회 서비스의 블로그(Scrapfly, Browserless 등)이며 자체 주장.
- 가장 쓸 만한 독립 비교(개인 블로그, 단일 주거 IP·1야간): 31 타깃 × 7 도구 × 3회 https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi/ [G]
  - OK/제한(gated)/차단: nodriver 28/3/0, CloakBrowser 26/3/2, **curl_cffi 0.15.0 26/3/2**, Patchright 25/3/3, Camoufox 25/3/3, 순정 Playwright 24/2/5, rebrowser 24/2/5.
  - curl_cffi 는 6.4MB wheel, 피크 RSS 57.9MB 로 130MB 패치 Chromium 과 같은 점수. Patchright 는 13.3GB. 작성자 결론: nodriver 는 Cloudflare 제한 타깃, JS 불필요 타깃은 curl_cffi.
  - 한계: 단일 IP·단일 OS·단일 밤, 브라우저 버전이 136~148 로 제각각, 타깃이 도중에 안티봇 벤더를 바꾼 사례 있음.
- 대립 결과: techinz/browsers-benchmark(회전 주거 프록시, 날짜 미확인) 는 patchright 100% > cloakbrowser·camoufox_headless 90% > nodriver 80% (nodriver headless 40%, camoufox 비헤드리스 30%). Cloudflare·DataDome·Akamai·PerimeterX·Kasada 등을 포함하나 버전 미기재 https://github.com/techinz/browsers-benchmark [G]. 두 벤치의 순위가 IP 조건에 따라 뒤집힌다 = IP 평판이 도구 선택보다 큰 변수.
- Browserless 글(자체 판매자): Turnstile 은 지문·행동·네트워크·IP 평판을 종합하며, Managed 체크박스 단계는 일관된 방법이 없다고 인정. 토큰 300초·1회용. 자사 해결률 89.9~96.6% 는 내부 수치 https://www.browserless.io/blog/turnstile-bypass [G].
- Akamai·DataDome·PerimeterX 에 대해 **독립 수치는 못 찾음(미확인)**. DataDome 에서 Camoufox 가 Patchright 보다 낫다는 건 일화 수준 [S].
- 결론: 오픈소스로 "된다"는 보장은 없고, 우리 용도(수십~수백 URL 정밀 열람, 한국 사이트 중심)에서는 우회 성능 경쟁보다 **실패를 정직하게 기록하는 사다리**가 더 중요.

## 2. 후보별 한 단락

**curl_cffi** — 0.16.3(2026-09-02)이 정식 최신이고 0.16.4b1 베타가 있다. 8~9월 연속 릴리스로 활발하며 Python 3.14·Android wheel·Win64 소켓 버그 수정이 있었다. 타깃은 chrome150, safari2601 이 권장이고 HTTP/3 는 chrome145/146/150·firefox147 에서만 문서화됐다. README 는 `curl-cffi update` 로 Safari·Chrome·Firefox 지문을 무료 갱신한다고 한다(v0.15.1~). 추가 지문·상용 지원은 impersonate.pro 유료. 위 벤치에서 비브라우저 기준선으로 26/3/2 를 기록, 패치 브라우저와 동급. **교체할 이유가 없다.** 주의: 가짜 패키지 `cffi-curl`(OSV MAL-2025-47752)이 있으니 철자 확인(https://osv.dev/vulnerability/MAL-2025-47752, [S]).

**wreq / rnet / primp / tls-client** — 모두 같은 일(JA3/JA4·HTTP2 흉내)을 다른 엔진으로 한다. wreq(Rust·BoringSSL, Apache-2.0)가 가장 활발하고 프로필 수가 많다고 주장하나 독립 검증은 없다. rnet 은 wreq 로 흡수된 것으로 보이며 구 2.x 는 GPL-3.0 이라 피한다. primp·tls-client·curl_cffi 3종이 같은 Chrome JA4(`t13d1516h2_8daaf6152771_02713d6af862`)를 냈다는 판매사 블로그 1건이 유일한 독립 근거 https://apiserpent.com/blog/python-tls-fingerprint-impersonation-tested [G]. 실질 차이는 프로필 개수와 속도 정도이고 우리 규모(수백 URL)에선 이득이 없다.

**niquests / httpx / hrequests** — httpx 는 HTTP/2 를 해도 Chrome JA4 와 다르다. hrequests 는 2024-12 이후 정체. niquests 는 활발하나 지문 흉내가 목적이 아님.

**patchright** — Playwright 의 CDP 누출(Runtime.enable 등)을 패치한 드롭인. 1.63.0(2026-09-20), Apache-2.0. 기존 Playwright 캡처 코드를 거의 그대로 쓸 수 있다는 점이 우리에겐 결정적. 벤치에서 `channel=chrome`(실제 설치 Chrome) 사용이 핵심. 헤드리스에선 약해진다는 결과(techinz: headless 40%)가 있어 **헤드풀 + 실 Chrome** 권장.

**Camoufox** — 패치 Firefox. 래퍼 0.5.8(2026-10-06), 브라우저 릴리스 v156.0.1-beta.38(2026-10-13)로 매우 활발하지만 전부 beta. 과거 유지보수자의 장기 부재 이력이 있었으나(검색 요약, 날짜 미확인) 최근 릴리스가 연속이다. Firefox 신원만 제공하므로 curl_cffi·Chromium 계열과 **지문 계열이 달라** 보완 효과가 있다. 단일 IP 벤치에서 25/3/3.

**nodriver / zendriver** — 시스템 Chrome 을 직접 CDP 로 몬다. 벤치 1위(28/3/0). 하지만 **AGPL-3.0**. 내부 스크립트로만 쓰고 네트워크 서비스로 제공하지 않으면 통상 문제 소지가 작지만, 판단은 사용자(법무)가 할 일이라 "채택 전 검토 필요"로 표기. zendriver 는 nodriver 포크로 이슈 대응이 더 열려 있음.

**pydoll / SeleniumBase / botasaurus** — MIT. pydoll 3.0(2026-09-29)은 1인 유지·Windows 명시 없음. SeleniumBase 는 Windows 명시, 릴리스가 매우 잦고 CDP 모드 보유하나 제품 규모가 커서 도입 비용이 큼. botasaurus 본체는 2026-01 이후 정체.

**CloakBrowser** — 패치 Chromium 바이너리(~200MB, vendor 도메인에서 다운로드, Ed25519 검증). 래퍼는 MIT 지만 **v148 이후 바이너리는 Pro 구독 필요**, 무료 최신판은 GitHub 로그인·동시 1세션, 버전 고정은 유료 키. README 자체가 "홍보성 강함"으로 읽히고 성능은 자체 주장. 벤치에서 curl_cffi 와 동점.

**Scrapling** — Fetcher(HTTP)/DynamicFetcher/StealthyFetcher 3계층 + 스파이더. BSD-3, 0.4.15(2026-08-23). 문서(choosing 페이지)에 자동 승격은 서술되지 않았고, 내부 엔진도 거기서 확인 못 함. 이미 사다리가 있는 우리에겐 파서(적응형 셀렉터) 외 이득이 작다.

**Crawlee for Python** — AdaptivePlaywrightCrawler 가 HTTP/브라우저를 예측·학습해 전환하며 필요 시 양쪽을 돌려 비교한다. 설계가 대량 크롤용이고, 증빙(원문 발췌+캡처) 단위 기록과 맞추려면 래핑이 필요하다. 1.10.4(2026-10-06), Apache-2.0.

**crawl4ai** — 0.9.4(2026-09-23), Apache-2.0(표기 요청). `enable_stealth`, undetected 어댑터, 영속 프로필, 원격 CDP 브라우저, Docker REST API(포트 11235, 토큰 필요), MCP 지원. 열람 요약서는 LLM 친화 Markdown 이 주목적이라 우리의 trafilatura 와 역할이 겹친다.

**Firecrawl 자체호스팅** — AGPL-3.0. 공식 문서 기준 Fire-engine(안티봇) 미포함, 스크린샷·페이지 액션 불가, agent·interact 는 클라우드 전용. 증빙 캡처가 필수인 우리에겐 대체재가 못 된다.

**Jina Reader OSS** — Apache-2.0, Docker 한 줄 실행, 이미지에 Chrome·CJK 폰트 포함. `http://localhost:3000/<url>` 형태. 지문 우회 능력은 기대하지 말 것. 로컬이므로 URL 이 밖으로 나가지 않는다. 스크린샷 기능 여부는 이번에 미확인.

**Steel Browser** — 로컬 Docker 브라우저 API(세션·스크린샷·scrape·안티디텍션 플러그인). 공개 베타.

**Tavily Extract / Exa / Browserbase** — 모두 URL 이 서비스로 전송됨. Tavily 는 이미 MCP 가 연결돼 있고 단가가 낮음(basic 5건당 1크레딧). 비대외비 URL 의 최후 폴백으로만.

**trafilatura 외 추출기** — trafilatura 가 2026-07~10 사이 3회 릴리스로 가장 활발. 독립 벤치에서 resiliparse·readability 와 점수 차가 작아(WebMainBench 0.63~0.65) 교체 이득이 불확실. 표·PDF 는 docling(MIT)·MarkItDown(MIT)이 가볍게 시도할 후보, MinerU 는 약 5GB·특수 라이선스라 후순위. HWP 는 별도(kordoc).

## 3. 권고

### 3-1. curl_cffi: 교체 X, 버전·프로필 상향 O, 옆에 브라우저 계층 하나 O
- 근거: ① 최신(0.16.3)이 활발히 유지, ② 독립 벤치에서 패치 Chromium 과 동점이며 메모리 1/200, ③ 대안 Rust 계열은 독립 검증이 없고 프로필 수 외 이득이 불명.
- 할 일: 정식 0.16.3 으로 고정(0.16.4b1 베타는 피함), `impersonate` 를 `chrome`/`safari`/`firefox` 별칭이 아닌 **명시 버전(chrome150, safari2601, firefox147)**으로 두되 별칭 폴백 허용, `curl-cffi update` 가 우리 환경에서 되는지 확인. HTTP/3 는 한국 사이트에서 이득이 확인되지 않아 보류.
- "HTTP 가 막히면 같은 지문을 쓰는 다른 HTTP 라이브러리"는 의미가 약하다(같은 BoringSSL 계열). 막히면 **엔진 계열을 바꾸는** 브라우저 계층이 맞다.

### 3-2. 브라우저 계층
1순위 **patchright** (Apache-2.0, 기존 Playwright 캡처 코드 재사용, `channel=chrome` 헤드풀). 
2순위 **Camoufox** (MIT, Firefox 계열이라 지문 다양화; 단 beta 이므로 버전 고정과 스모크 테스트 필수). 
조건부 **nodriver**: 벤치 1위지만 AGPL 검토 후에만. 
공통: 헤드리스 단독은 약하므로 Windows 데스크톱에선 헤드풀, 홈서버(Linux)에선 Xvfb 가 필요할 수 있음(nodriver README 권장 [G]).

### 3-3. 통합 프레임워크는 도입하지 않는다
- 우리는 이미 사다리(curl_cffi → 모바일/RSS/OGP → 아카이브 → 리더)와 증빙 구조가 있다. Scrapling·Crawlee 는 "HTTP→브라우저 승격"만 대체하는데, 그 한 단(段)은 우리가 patchright 호출 한 함수로 추가하는 편이 싸다. 프레임워크는 증빙 저장·실패 사유 기록 규약과 충돌하기 쉽다.
- 예외: Scrapling 의 적응형 셀렉터 파서는 단독 참고 가치 있음(필수 아님).

### 3-4. Firecrawl 대체
- **로컬 1순위: 새 도구를 들이지 않고 "trafilatura + patchright 캡처"를 유지.** 통합 API 가 꼭 필요하면 **crawl4ai**(Apache-2.0, Docker, 로컬 전용).
- **보조(유료·선택) 1개: Tavily Extract** — 비대외비 URL 한정, 소액 단가, 이미 연결돼 있음. URL 이 제3자로 나간다는 점을 보고서 메타에 명시.

### 3-5. 도입하지 말 것
1. **CloakBrowser** — 최신 바이너리가 구독제·vendor 서버 다운로드·버전 고정 유료. 벤치 이득도 없음(curl_cffi 와 동점). 대외비 환경에 부적합한 공급망.
2. **Firecrawl 자체호스팅** — AGPL 이고 캡처·안티봇이 빠져 있어 대체재가 아님.
3. **undetected-chromedriver / hrequests / rebrowser-playwright / rnet 2.x** — 각각 2024-02, 2024-12, 2025-05 이후 정체이거나 GPL, 벤치에서 순정과 차이 없음.
4. (참고) 패키지 이름 오타 공격: `cffi-curl`, `playwrightr` 같은 가짜가 보고됨 → 의존성은 해시 고정.

## 4. 미확인 / 한계
- wreq·primp 의 Windows wheel 존재 여부, resiliparse Windows 지원: 미확인.
- Akamai·DataDome·PerimeterX 에 대한 독립 수치: 못 찾음.
- 한국어 페이지·표·PDF 추출 품질 독립 비교: 못 찾음. MinerU 한국어 OCR 지원: 미확인.
- Exa contents·ScrapingBee·Zyte·Browserbase 요금/정책: 문서 미열람.
- Crawlee 의 curl_cffi 연동 여부, Scrapling 내부 엔진: 문서에서 확인 못 함.
- WebFetch 요약 모델 경유 값(스타·기능 목록)은 원문 대조 전 확정 금지. 벤치 두 건 모두 조건(IP·시점)이 달라 순위는 참고용.

## 5. 출처 요약
- PyPI JSON 직접 조회: `https://pypi.org/pypi/<pkg>/json` (curl_cffi, wreq, rnet, primp, tls-client, hrequests, niquests, httpx, camoufox, nodriver, zendriver, patchright, rebrowser-playwright, seleniumbase, pydoll-python, cloakbrowser, botasaurus, undetected-chromedriver, scrapling, crawl4ai, crawlee, scrapy, firecrawl-py, scrapegraphai, trafilatura, resiliparse, magic-html, markitdown, docling, magic-pdf, mineru, readability-lxml, tavily-python, exa-py, stagehand, steel-sdk, playwright-stealth)
- GitHub: lexiforest/curl_cffi, daijro/camoufox(+releases), D4Vinci/Scrapling, CloakHQ/CloakBrowser, ultrafunkamsterdam/nodriver, cdpdriver/zendriver, 0x676e67/wreq-python, autoscrape-labs/pydoll, seleniumbase/SeleniumBase, unclecode/crawl4ai, jina-ai/reader, firecrawl/firecrawl, steel-dev/steel-browser, spider-rs/spider, browserbase/stagehand, adbar/trafilatura(releases), opendatalab/MinerU, techinz/browsers-benchmark
- 문서: https://curl-cffi.readthedocs.io/en/latest/impersonate/targets.html , https://docs.firecrawl.dev/contributing/self-host , https://crawlee.dev/python/docs/guides/adaptive-playwright-crawler , https://scrapling.readthedocs.io/en/latest/fetching/choosing/ , https://docs.tavily.com/documentation/api-reference/endpoint/extract
- 벤치/해설: ianlpaterson.com(위), apiserpent.com(위), browserless.io(위), arxiv 2605.21097, OSV MAL-2025-47752(검색 요약)
