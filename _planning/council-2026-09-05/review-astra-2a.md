# 배치 2A 품질보증 리뷰

판정: **APPROVE_WITH_NITS**

검토 대상 7건의 원 재현 조건은 해소됐다. 요청 전 IP 고정과 홉별 가드, 공통 스트리밍 읽기, 렌더 AST 검사와 이미지 내장, PDF 상태 우선 판정, RSS 항목 매칭이 실제 호출 경로에 연결되어 있다. 출고를 막을 중대 결함은 발견하지 않았다. 작업폴더 내부 Windows 절대경로 이미지에 대한 G3/렌더러 정책 불일치 1건을 경미한 호환성 지적으로 남긴다.

## 범위와 검증 전제

- 입력은 이 폴더의 `batch2a.diff`, `spec-batch2a.md`, 저장소 `_planning/council-2026-09-05/review-astra-2.md`의 해당 결함 절이다. 지정 프롬프트 폴더에는 입력 두 파일이 없어, 실제 두 파일이 함께 있는 이 scratchpad를 산출 위치로 해석했다.
- 파일:라인은 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 기준이다. 제공 diff와 현재 `git diff HEAD -- codes/market-deep-research`가 줄바꿈 정규화 후 일치함을 직접 확인했다.
- pytest 209개(기존 154 + 신규 55), gates demo, preflight 통과는 팀리드가 제공한 검증 사실로 채택했다. 전체 검증을 다시 실행하지 않았다.
- 소스·테스트·설치된 curl_cffi 구현을 읽었고, 저장소 밖 임시 폴더에서 내부 이미지의 상대/Windows 절대경로에 대한 G3 검사 및 실제 pandoc HTML 생성만 추가 실행했다. 외부 네트워크 요청과 구현·테스트 수정, 커밋은 하지 않았다.
- N20 provenance 재설계와 나머지 배치 외 결함은 재심사 대상에서 제외했다. 스펙이 허용한 data URI의 저수준 렌더 허용/G3 금지 차이와 명시적 sandbox 실패 폴백은 결함으로 세지 않았다.

## 항목별 해소 판정

| 항목 | 판정 | 근거와 재현 차단 이유 |
|---|---|---|
| N02 오프라인 렌더 | 해소 | `scripts/render_pdf.py:42`에서 원격·UNC·작업폴더 이탈 이미지 거부, `:76`에서 `gfm-raw_html` 및 파싱 sandbox 적용, `:84`에서 RawBlock/RawInline을 텍스트로 바꾸고 모든 AST Image를 검사·내장한다. `:112`의 HTML writer는 검사된 JSON만 받고 종전 `--embed-resources`를 사용하지 않아 pandoc의 원격 이미지 로더를 호출하지 않는다. `:32`·`:105` CSP는 script/connect/frame/object를 금지하며, `:136`은 Chrome 네트워크 억제·프록시 해제·호스트 해석 차단 옵션을 적용한다. 파싱·HTML 변환·Chrome 각각 180초 timeout(`:77`, `:117`, `:148`), 기본 sandbox 및 명시적 오류 폴백(`:149`)이 있다. G3는 외부/data URI/폴더 이탈을 거부한다(`scripts/verify_facts.py:748`). 아래 Windows 절대경로 nit는 별도다. |
| N03 공통 요청 경계 | 해소 | `scripts/fetch.py:175`가 URL·DNS 응답 전체를 검사하고, `:269`는 urllib 연결을 검증 IP로 고정하면서 원 호스트 TLS 검증을 유지한다. `:312` 공통 루프가 매 홉 검사, curl `allow_redirects=False`, RESOLVE와 프록시 해제, urllib 자동 redirect 차단을 적용한다(`:301`, `:320`, `:333`). 최대 5홉(`:319`, `:348`)이고 Content-Length 선제 검사 후 청크마다 누적 상한을 검사하며 모든 응답을 닫는다(`:352`~`:367`). 검색 `_get`, 이미지 검색 `_json_get`, 다운로드가 모두 이 함수를 사용한다(`scripts/search.py:36`, `scripts/harvest_images.py:358`, `:556`). 프록시가 있어도 사후 검사 생략이 없고 한계는 `scripts/fetch.py:216`, `references/source-ladder.md:28`에 명시됐다. |
| N14 재구성 경로 | 해소 | `scripts/capture_web.py:28`~`:42`가 `_captures`와 `_reconstructed` 루트의 resolve 결과를 확인하고 최종 목적지의 내부 포함 여부를 저장 전에 검사한다. `_reconstructed/../forged.png`는 거부되며 정상 하위 경로는 생성된다. 반환 유형 및 `evidence=False`는 유지된다(`:64`). |
| N15 PDF HTTP 오류 | 해소 | transport 결과에서 PDF 매직바이트 검사 이전에 비2xx를 거부한다(`scripts/fetch.py:394`). 사다리에서도 상태를 재검사한 뒤 PDF fast path를 실행하므로 응답 fixture·다른 후보 경로에도 적용된다(`:600`, `:609`, `:624`). 실패 이유와 최종 fail 로그를 남긴다. |
| N16 무관 RSS | 해소 | `scripts/fetch.py:459`에서 RSS/Atom을 파싱하고 URL/GUID/Atom id 또는 제공·확보된 제목으로 유일한 항목만 매칭한다. 해당 entry 본문만 검증·정제 대상으로 사용하고 raw 피드는 보존한다(`:492`~`:507`). 미일치 피드는 partial로 강제하며 성공 셀렉터로 승격하지 않고 사다리를 계속한다(`:603`, `:607`, `:630`). RSS 계층의 가짜 PDF도 매칭 단계에서 거부된다. |
| N22 실패 집계 | 해소 | `scripts/fetch.py:654`가 정상 반환 및 예외에도 URL별 final 로그를 쓰고, `scripts/source_index.py:129`는 실제 `audit/fetch-log.jsonl`의 마지막 상태와 시도 실패 횟수를 구분한다. 표에 상태 열을 출력하고 사용자 지정 출력 경로에서도 작업폴더 로그를 읽는다(`:162`, `:180`, `:192`, `:278`). 완료된 호출의 partial은 최종 실패로 세지 않는 정책이 출력에 명시되어 있다. |
| K07 stdout JSON | 해소 | `scripts/fetch.py:857`에서 전체 JSON을 출력하고 긴 trace는 별도 감사 JSON으로 이동한다. `sha256`·`local` 키는 유지하며 저장되지 않은 smoke/fail은 null을 사용한다. get/smoke 양쪽이 같은 출력 함수를 사용한다(`:873`). |

## 정상 기능과 중복 구현

- 모바일 정상 경로: 기존 지문 그리드, 모바일 UA/헤더, 지원되지 않는 iOS 지문에 대한 safari 폴백 구조가 유지된다(`scripts/fetch.py:541`). `tests/test_batch2a_regressions.py:289`는 direct 403 후 모바일 200의 성공과 지문 순서·헤더를 검사한다. 실제 모바일 사이트나 모든 지문 버전을 재확인한 테스트는 아니다.
- RSS 정상 경로: link/GUID/title/Atom의 대응 entry 확보와 무관 항목 제외를 검사하고(`tests/test_batch2a_regressions.py:254`), 실제 후보 생성 및 RSS/Atom MIME 허용도 검사한다(`:273`). URL·제목 일치가 없는 피드가 partial로 내려가는 것은 의도된 수정이다.
- 재구성 발췌: 정상 중첩 경로에서 실제 PNG 생성·크기·증빙 불인정을 확인한다(`tests/test_batch2a_regressions.py:419`).
- 정상 렌더: 한글 파일명의 실제 로컬 이미지를 pandoc으로 내장하고 Chrome PDF의 이미지 존재와 script 실행 흔적 부재까지 검사한다(`tests/test_batch2a_regressions.py:334`). 제공된 기존 E2E/P0 통과 결과도 정상 출고 경로의 보존 근거다.
- URL/IP 가드, redirect 상한, 본문·이미지 크기 상수 및 스트리밍 구현은 `fetch.py`에 모였다. search의 무검사 fallback은 삭제됐다. caller별 timeout과 이미지 최소 크기·매직바이트 검사는 해당 도구의 정책으로서 공통 SSRF 가드의 이중구현이 아니다.
- 환경 프록시 비사용은 목적지 IP 고정을 위한 명시적 정책 변경이다. 프록시 필수 환경의 접속성까지 보존한다고 해석하지 않으며, 해당 동작은 source-ladder에 문서화되어 있다.

## P0와의 상호작용

claim-review와 계산 검사는 G3의 공통 검증 호출에 그대로 남아 있다(`scripts/verify_facts.py:922`). capture_review 검증 및 재구성 증빙 불인정 경계도 유지된다(`scripts/verify_facts.py:533`, `scripts/facts_db.py:184`). N14는 그 경계 앞에서 재구성 파일의 정상 경로 위장을 차단한다.

렌더는 정규 원고·G3 영수증과 기준 manifest를 확인한 후 실제 반환 artifacts만 봉인한다(`scripts/render_pdf.py:178`). 최종 단계의 현재 원고 재검증도 유지된다(`scripts/manifest.py:169`). 이번 diff는 claim/capture 검토 대장이나 계산검사 결과·최종 출고 실검증을 생략하는 새 경로를 만들지 않는다. 이 판단은 소스 대조와 제공된 P0 회귀 통과에 근거하며 별도 전체 P0 재실행 결과를 뜻하지 않는다.

## 신규 테스트의 실질성 및 한계

신규 테스트는 단순한 문자열 존재 검사에 그치지 않는다. 특히 `tests/test_batch2a_regressions.py:121`은 search/image/image_search × curl/urllib 6개 조합에서 실제 로컬 HTTP 서버의 접근 기록이 `/start` 한 건뿐인지 확인한다. 최초 URL을 공인 호스트로 모사하는 transport fixture는 테스트에만 있으며, private redirect 가드 자체는 실제 구현을 실행한다.

스트리밍 테스트(`:194`)는 전량 `.content` 접근을 금지하고 크기 초과 시 다음 청크에서 중단·close하는지를 두 transport로 확인한다. 다만 이는 응답 fixture 기반이며 실제 curl_cffi의 비동기 수신 큐 최대 메모리나 느린 서버의 벽시계 상한을 측정하지 않는다. 설치 라이브러리의 `iter_content`는 chunk_size를 무시하므로 테스트의 정확한 청크 크기와 실제 curl 수신 청크 크기는 같다고 볼 수 없다. 본 구현의 길이 검사는 청크 크기에 의존하지 않으므로 이를 이번 재현 결함의 미해소로 세지 않았다.

N02는 외부 URL의 inline/reference/HTML 표기에서 서버 요청 0건을 확인하고(`:321`), 실제 PDF의 로컬 이미지와 script 출력 부재까지 확인한다(`:334`). N15는 transport와 사다리 양쪽에서 HTTP 오류 PDF를 검사한다(`:214`, `:227`). N22는 가상 로그 fixture로 집계하며, N15/N16 테스트가 실제 로그 생산 경로를 보완한다. K07은 main 함수를 실행해 stdout을 JSON으로 파싱하고 이동된 trace 전체의 동등성을 검사한다(`:445`). 운영체제 하위 프로세스로 CLI를 실행한 검사는 아니라는 한계는 있다.

## 발견 1건

**경미 / Windows 내부 절대경로 이미지의 G3·렌더러 정책 불일치**

- 위치: `scripts/verify_facts.py:750`~`:754`; 비교 대상 `scripts/render_pdf.py:48`~`:60`.
- 조건: 실제 작업폴더 안의 이미지에 `C:/.../work/_captures/image.png`처럼 Windows 드라이브 절대경로로 참조한다. `urlsplit`이 `c`를 scheme으로 인식하여 G3는 파일 존재·루트 내부 여부를 확인하기 전에 거부한다. 렌더러는 드라이브 경로를 명시적으로 허용하여 동일 이미지를 정상 내장한다.
- 직접 재현: 임시 작업폴더의 같은 PNG를 `_captures/image.png`로 참조하면 `check_figures` 실패 0건 및 실제 pandoc HTML 생성 성공. Windows 절대경로로 참조하면 `[도판경로] 참조 이미지 경로 실재 없음`이 발생하지만 실제 pandoc HTML 생성은 성공했다. 파일 부재나 폴더 이탈이 아닌 정상 파일의 표기 방식 때문에 생긴 차이다.
- 영향: 절대경로를 출력하는 도구의 경로를 원고에 그대로 붙이는 Windows 사용자가 G3에서 막힌다. 상대경로로 바꾸면 진행할 수 있고, 보안 경계 우회나 정상 상대경로의 출고 실패는 아니므로 승인 차단 사유로 보지 않는다.
- 최소 수정안: G3에서도 로컬 Windows 드라이브 절대경로를 먼저 구분한 뒤 resolve한 결과가 작업폴더 내부인지 검사한다. UNC·원격 scheme·외부 파일 거부는 유지한다. 동일 내부 PNG의 상대/절대경로를 대조하는 작은 회귀를 추가하면 정책 불일치를 고정할 수 있다.

ASTRA_2A_DONE verdict=APPROVE_WITH_NITS
