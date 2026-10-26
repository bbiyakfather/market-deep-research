# HTTP 임퍼소네이션·무료 검색 백엔드 조사 (2026-10-13)

조사 주체: aside 에이전트(grok-4.7), 공개 PyPI·GitHub·공식 문서만. 의뢰: 수집 스택 재점검 후속(검색 강화).

## 결정
- fetch: `curl_cffi` 유지(0.16.3 활성, `chrome`/`safari` 별칭이 최신 지문으로 풀림). `wreq` 0.13.0(다른 TLS 스택)은 통과율 근거가 없어 **보류**.
- 검색: `ddgs` 9.16.0 을 1차(다중 백엔드·news), DDG HTML(curl_cffi) 폴백, 공개 SearXNG 는 JSON 전멸이라 **자체 호스트 등록 시만**.
- 유료·크레딧형(Brave·Exa·Tavily·Jina 키·Mojeek)은 제외.

## 원문 (aside 최종 답변)

2026-10-13 기준 공개 PyPI, GitHub, 공식 문서만 봤습니다. TLS 임퍼소네이션은 JS 챌린지를 풀지 못하고, 유료 검색 API는 무료 크레딧이 있어도 제외하는 기준으로 정리했습니다.

## 1. HTTP 임퍼소네이션 라이브러리

| 라이브러리 | 최신 버전 / 날짜 | 유지보수 | 임퍼소네이션 대상 | async | Windows + Python 3.12 | 알려진 한계 | 출처 |
|---|---|---|---|---|---|---|---|
| curl_cffi | 안정판 0.16.3, 2026-09-02. pre 0.16.4b1은 2026-09-20 | 활성. 스타 6705, push 2026-10-09. Python >=3.10 | Chrome 131/136/142/145/146, Android `chrome131_android`, Safari 18.0/18.4/26.0과 iOS 동일 버전, Firefox 133/135/144/147. `impersonate="chrome"`은 최신 프리셋 | `AsyncSession` 있음 | `curl_cffi-0.16.3-cp310-abi3-win_amd64.whl` 있음 | JS를 실행하지 않음. 오픈소스는 일부 Chrome 버전을 건너뜀. 상용 핑거프린트는 impersonate.pro. Cloudflare 403 이슈 #786은 2026-06-22에 닫혔고, 범용 우회는 아님 | https://pypi.org/project/curl-cffi/ https://github.com/lexiforest/curl_cffi https://curl-impersonate.readthedocs.io/en/latest/fingerprints.html https://github.com/lexiforest/curl_cffi/issues/786 |
| rnet | pip 기본은 2.4.2, 2025-08-02. 마지막 업로드는 pre 3.0.0rc22, 2026-02-24 | 저장소는 wreq-python으로 이어짐. 스타 1486, push 2026-10-12. 안정판 PyPI는 2025-08-02에서 멈춤 | 2.4.2 프리셋 목록은 이번 조사에서 재확인하지 않음. rc22 문서는 Safari 26을 언급. 현재 후속은 wreq | 예전 API도 async `Client`. rc22는 Python >=3.11 | 2.4.2는 `cp312-win_amd64`. rc22는 `cp311-abi3-win_amd64` | 이름만 남고 개발은 wreq로 이동. rc22 분류자에 GPLv3. 안정판을 폴백 기본으로 두면 핑거프린트가 한 세대 이상 뒤짐 | https://pypi.org/project/rnet/ https://pypi.org/project/rnet/3.0.0rc22/ https://github.com/0x676e67/rnet |
| primp | 2.0.1, 2026-09-13. 구명 `pyreqwest-impersonate` | 활성. 스타 612, push 2026-09-13. Python >=3.10 | Chrome 144–153과 `chrome`, Safari 18.5/26/26.3/26.4, Edge 144–153, Firefox 140/146–151, Opera 126–135. OS를 android/ios/linux/macos/windows로 분리 | `AsyncClient` 있음 | `primp-2.0.1-cp310-abi3-win_amd64.whl` 있음 | 브라우저 DOM/JS 없음. README는 교육용 고지. ddgs의 DuckDuckGo 요청 로그에 primp가 찍힘 | https://pypi.org/project/primp/ https://github.com/deedy5/primp https://github.com/deedy5/primp/blob/main/crates/primp-python/docs/async_client.md https://github.com/deedy5/ddgs/issues/480 |
| wreq (구 rnet / rquest 계열) | 0.13.0, 2026-10-05. PyPI 패키지명 `rquest`는 404 | 활성. Python 바인딩 스타 1486, Rust `wreq` 스타 1067, push 2026-10-12. Apache-2.0. Python >=3.11 | Chrome 100–154, Edge 101–148, Firefox 109–152와 Android 135, Safari 15–26.4, `SafariIos26`/`SafariIos26_2`, OkHttp 3/4/5, Opera 116–131. 플랫폼 분리 가능 | async `Client`와 `wreq.blocking.Client` | `wreq-0.13.0-cp311-abi3-win_amd64.whl`. 분류자에 3.12 | 공식 문서: JS와 DOM은 하지 않음. BoringSSL 기반이라 curl_cffi와 스택이 다름. `0x676e67/rquest`는 Rust 크레이트일 뿐 Python 바인딩이 아님 | https://pypi.org/project/wreq/ https://github.com/0x676e67/wreq-python https://raw.githubusercontent.com/0x676e67/wreq-python/main/python/wreq/emulation.py https://github.com/0x676e67/rquest |
| tls-client | 2.0.0, 2026-10-10. 직전 안정판은 1.0.1, 2024-02-02 | 재개. 스타 821, push 2026-10-10. 상위 Go `bogdanfinn/tls-client` 스타 1885, push 2026-09-04 | main `settings.py` 기준 Chrome 103–152, Firefox 102–148, Safari iOS 15.5–26.0, OkHttp Android 7–13. README 예시는 `chrome_152` | README는 동기 `Session`만. asyncio API는 없음 | `tls_client-2.0.0-py3-none-win_amd64.whl` 있음 | Go 공유 라이브러리 FFI. JS 챌린지 없음. 릴리스 직후 main과 휠 설명의 예시 버전(`chrome_112` vs `chrome_152`)이 어긋남 | https://pypi.org/project/tls-client/ https://github.com/FlorianREGAZ/Python-Tls-Client https://raw.githubusercontent.com/FlorianREGAZ/Python-Tls-Client/main/tls_client/settings.py |
| hrequests | 0.9.2, 2024-12-01 | 사실상 정지. 스타 1027, 마지막 push 2024-12-01. 오픈 이슈 53 | README는 Go 백엔드 TLS 복제와 BrowserForge 헤더만 적음. Chrome 13x/14x 프리셋 목록은 현재 README에 없음 | gevent `async_get`. asyncio 세션은 아님 | 플랫폼 휠 없음. `py3-none-any`만 | 22개월 미갱신. 브라우저는 Camoufox/Patchright 추가 설치. 지금 WAF 폴백으로는 프리셋이 낡음 | https://pypi.org/project/hrequests/ https://github.com/daijro/hrequests |
| impit (2025–2026) | 0.14.1, 2026-09-07 | 활성. 스타 611, push 2026-10-12. Apache-2.0. Python >=3.10 | master `database.rs`: Chrome 100–151 중 일부, Firefox 128/133/135/144, Safari `ios_18`, OkHttp 3/4/5. rustls 기반 | `AsyncClient`와 동기 클라이언트. httpx 인터페이스는 부분 구현 | `impit-0.14.1-cp312-cp312-win_amd64.whl` 확인. 이번 파일 목록에 win_arm64는 없었음 | httpx 기능 일부 미구현. 2026-08-06 비교는 HTTP/2 불일치를 지적했으나, 그 글의 Chrome 124 한도는 현재 트리와 맞지 않음 | https://pypi.org/project/impit/ https://github.com/apify/impit https://raw.githubusercontent.com/apify/impit/master/impit/src/fingerprint/database.rs |
| tls-client-python (2026) | 1.16.0.6, 2026-10-02 | 신규 CFFI 바인딩. bogdanfinn/tls-client를 묶음. Python >=3.6, <3.15 | 프로필 전수 목록은 이번 조사에서 휠 내부를 열지 않음. requests 및 Python-Tls-Client 호환을 주장 | 문서상 requests 호환 동기 API | `tls_client_python-1.16.0.6-py3-none-win_amd64.whl` 있음 | tls-client와 엔진이 같아 JS 한계도 같음. 두 패키지를 같이 쓰면 네이티브 라이브러리가 겹칠 수 있음 | https://pypi.org/project/tls-client-python/ https://github.com/bogdanfinn/tls-client |
| wafer-py (2026) | 0.7.7, 2026-10-08 | 실험. 스타 9. Python >=3.12. wreq 0.13 의존 | wreq 프로필을 사용. README 예시에 Edge 148, Safari iOS 26.2, Chrome 149 | `AsyncSession` 있음 | 플랫폼 휠 없음. `py3-none-any`이고 TLS는 wreq 휠 | 작성자가 프로덕션 부적합이라고 명시. 브라우저 솔버는 patchright 추가 설치. 폴백 기본값으로 두기엔 이름과 API가 자주 바뀔 수 있음 | https://pypi.org/project/wafer-py/ https://github.com/Averyy/wafer |

Cloudflare, Akamai, DataDome에 대한 독립 통과율 표는 찾지 못했습니다. wreq 문서는 에뮬레이션이 JS와 DOM을 하지 않는다고 하고, curl_cffi도 전송 계층 핑거프린트만 맞춥니다. ProxyHat의 2026-07-08 글은 Turnstile, DataDome interstitial, Akamai sensor를 JS 런타임이 필요한 한계로 적습니다. https://python.wreq.org 가 아닌 원문은 https://raw.githubusercontent.com/0x676e67/wreq-python/main/docs/source/guide/emulation.md 와 https://proxyhat.com/blog/tls-impersonation-curl-cffi-guide 입니다.

## 2. 무료 또는 저비용 검색 백엔드

| 백엔드 | 2026-10-13 상태 | 한도 / 조건 | 한국 시장조사용 메모 | 출처 |
|---|---|---|---|---|
| ddgs 9.16.0, 2026-08-26. 구 duckduckgo_search | 유지 중. 스타 3017, push 2026-08-26. Python >=3.10, 순수 파이썬 휠 | 공식 검색 API가 아님. text 백엔드: bing, brave, duckduckgo, google, grokipedia, mojeek, startpage, yandex, yahoo, wikipedia | DuckDuckGo만 쓰면 위험. 이슈 #480(2026-07-25, 열린 상태)은 HTML 200 뒤 `news.js` 403. #482는 동영상 403. Bing은 그 제보에서 동작 | https://pypi.org/project/ddgs/ https://github.com/deedy5/ddgs https://github.com/deedy5/ddgs/issues/480 https://github.com/deedy5/ddgs/issues/482 |
| DuckDuckGo 봇 차단 | Instant Answer API만 공식이고 SERP가 아님. HTML 수집은 비공식 | 2026-06-22 안내도 프록시와 지연을 전제. 라이브러리만으로 차단이 사라졌다는 공식 발표는 없음 | 키 없는 보조 백엔드로는 남기되, 단일 실패점으로 두지 말 것 | https://iproyal.com/blog/duckduckgo-api https://github.com/deedy5/ddgs/issues/480 |
| Brave Search API | 유료 API에 월 크레딧이 붙은 형태. 아직 가입 가능 | Search는 1,000요청당 $5, 월 $5 크레딧, 최대 50 QPS. 무료 크레딧만 써도 카드 등록 필요, 그 범위에서는 청구하지 않는다고 함 | 카드와 종량제가 있어 이번 제약에는 부적합 | https://brave.com/search/api/ |
| Jina `s.jina.ai` | Reader 검색 엔드포인트는 살아 있음 | 키 없음 칸은 비어 있음. 무료 키 100 RPM. 요청당 최소 1만 토큰. 신규 키 1,000만 토큰 후 유료. 결과는 상위 5건 | 약 1,000회 뒤 과금이라 무과금 도구의 본선이 아님 | https://jina.ai/reader |
| SearXNG / searx.space | 페이지 표기는 70 online. `instances.json` 시각은 2026-10-13T06:39:02Z, 목록 92 | HTTPS·normal·`http.error` 없음 76곳을 집계. `format=json` 필드는 없음. 같은 날 11곳 GET은 JSON 0건: 대부분 429, 2곳은 봇 체크 HTML | 공개 인스턴스 JSON은 오늘 이 네트워크에서 확인되지 않음. JSON이 필요하면 자체 인스턴스 | https://searx.space/ https://searx.space/data/instances.json |
| Mojeek API | 상용 API. 셀프서브 무료 티어 없음 | Startup은 1,000쿼리당 £2, 종량제. 무료 체험은 문의. 문서상 하위 한도는 5 QPS, 일 10만, 요청당 10건 | 키와 과금이 필요. ddgs의 mojeek 백엔드는 별개의 HTML 수집 | https://www.mojeek.com/services/search/web-search-api/ https://github.com/deedy5/ddgs |
| Marginalia | `api2.marginalia-search.com`, 문서 갱신 2025-12-08 | 키 `public`는 공유 속도 제한, 숫자 한도는 문서에 없음. 무료 비상업 키는 이메일 신청. CC-BY-NC-SA 4.0 | 비상업 라이선스이고 소형/비영리 웹 색인이라 한국 기업 조사의 본선이 아님 | https://about.marginalia-search.com/article/api |
| Exa | 무료 시작 가능, 종량 유료 | 월 $10 크레딧 + 가입 $10, 카드 불필요. 연 $120 이상이라고 표기. Instant Search는 1,000요청당 $4, 기본 10건 | 크레딧이 떨어지면 유료. 무과금 제약과 충돌 | https://exa.ai/pricing |
| Tavily | Researcher 무료 플랜 유지 | 월 1,000크레딧, 카드 불필요. basic search 1크레딧, advanced 2크레딧. 초과분은 크레딧당 $0.008 | 월 상한이 있는 유료 API의 무료 구간 | https://docs.tavily.com/documentation/api-credits |

## 권고

1. 수집 사다리는 `curl_cffi` 0.16.3을 기본으로 두고, TLS 스택이 다른 `wreq` 0.13.0을 한 단계 뒤에 둔다. `primp` 2.0.1은 ddgs가 이미 쓰므로 OS를 바꿔 재시도할 때만 넣는다.
2. `rnet` 2.4.2와 `hrequests` 0.9.2는 프리셋이 낡아 폴백에서 빼는 편이 낫다. `tls-client` 2.0.0은 Chrome 152와 Safari iOS 26이 있지만 동기 API라 세 번째 후보로만 둔다.
3. 검색은 <citation refs="3WUon-AgFXENbmno4mXb_,cmdDHyUF173Q-PPWnvS3a,aaQF2d95FiTKaNMKHmV7F,1JKZRNpm_Ei3uktXZGfKD,p1Tjdrsq-yyNYRljl06Ad">Brave, Exa, Tavily, Jina, Mojeek API처럼 크레딧이나 카드가 있는 유료 API를 쓰지 않는다</citation>. `ddgs` 9.16.0은 DuckDuckGo만 믿지 말고 Bing 등 다른 backend로 돌린다.
4. 공개 SearXNG는 건강한 HTTPS가 수십 곳이어도 `format=json`은 카탈로그에 없고, 오늘 11곳 프로브는 JSON이 0이었다. JSON이 필요하면 자체 인스턴스를 둔다.
5. Marginalia `public` 키는 비상업 라이선스와 공유 제한이라 본선이 아니다. ddgs 엔진 목록에 네이버와 다음이 없으니, 한국 포털 공백은 별도 수집으로 남긴다.
