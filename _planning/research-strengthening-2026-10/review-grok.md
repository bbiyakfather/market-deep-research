# research-strengthening 리뷰 (fetch / search / join_workers)

대상은 `feat/research-strengthening` 의 미커밋 diff 중 `codes/market-deep-research/scripts/fetch.py`, `search.py`, `join_workers.py` 와 `tests/test_rs_*.py` 다. 소스 파일은 고치지 않았다. 아래 재현은 로컬 프로세스와 `127.0.0.1` 만 썼다.

HIGH 3, MED 4, LOW 2.

## HIGH

### 1. 흔한 소프트 404 제목이 긴 본문이면 성공으로 확정된다

`codes/market-deep-research/scripts/fetch.py:83-84`, 판정은 `343`, 성공 반환은 `348-349`.

`_DEAD_TITLE_RE` 는 문자열 시작만 보고, `404` 와 `not found` / `error` 사이에 `-`, `|`, `:` 를 허용하지 않는다. `error\s*404` 도 가운데 `:` 나 `-` 를 통과시키지 못한다. 본문이 1000자 이상이면 `_title_suspect` 는 호출되지 않는다. 사다리는 `verdict == ok` 이면 그 응답으로 끝낸다 (`1025-1026`).

재현: `<title>` 아래 본문 약 3659자.

| 제목 | 결과 |
| --- | --- |
| `404 - Page Not Found` | `ok`, `body 3659 chars` |
| `404 \| Not Found` | `ok` |
| `404: Not Found` | `ok` |
| `Error: 404 Not Found` | `ok` |
| `Error - 404` | `ok` |

같은 함수로 `404 Error \| Analog Devices`, `HTTP 404: Page Not Found`, `Page not found \| Air Liquide` 는 `partial` 이다. 테스트가 잠근 형태만 걸리고, 구분자가 들어간 가장 흔한 404 제목은 메뉴가 긴 없는 페이지를 확보 성공으로 돌려준다.

`Error: 404 Not Found` 는 본문이 1000자 미만이어도 `suspect` 가 아니다. 콜론으로 나눈 첫 토막이 `error` 이고, 전체 문자열이 `404` 나 `not found` 로 시작하지 않아 `_title_suspect` (`288-300`) 도 놓친다. 짧은 쪽 재현 결과는 `thin body` 였다.

### 2. `_get_trusted` 가 지정 호스트 밖 리다이렉트를 따라가고, 그 본문을 검색 결과로 올린다

`codes/market-deep-research/scripts/search.py:64-80`. 파싱은 `_judge_searx` (`213-247`).

초기 URL 의 스킴만 보고 `urllib.request.urlopen` 에 넘긴다. 표준 라이브러리는 `http`/`https` 리다이렉트를 최대 10회 따라가며, 도착 호스트를 `fetch.check_url_safe` 에 다시 넣지 않는다. `resp.read()` 에도 바이트 상한이 없다.

재현: `127.0.0.1` 의 `/go` 가 다른 포트의 `/meta` 로 302. `/meta` 본문은 `{"results":[{"title":"secret","url":"http://10.0.0.9/hidden","content":"iam-cred"}]}`.

- `_get_trusted` 는 최종 200 과 그 JSON 을 반환했다. 두 포트 모두 요청이 도착했다.
- 같은 `/meta` 주소에 `check_url_safe` 를 호출하면 `차단 IP(127.0.0.1)` 로 거부된다.
- `_judge_searx(200, body, 5, "127.0.0.1")` 는 `ok` 와 결과 `url=http://10.0.0.9/hidden` 을 돌려준다.

`MDR_SEARX_URL` 로 허용한 프로세스가 `Location` 만으로 링크 로컬·사설·다른 내부 HTTP 로 나가고, 응답이 SearXNG 모양이면 검색 히트로 에이전트에 들어온다. 공개 인스턴스를 이 환경변수에 넣어도 같은 우회가 적용된다 (`_searx_targets`, `205-210`).

### 3. 브라우저 계층은 WebSocket 을 검사하지 않고, 받은 내용을 본문으로 반환한다

`codes/market-deep-research/scripts/fetch.py:767-786` (`page.route("**/*")` 만 설치, `849-850`). `ws://` 용 `route_web_socket` 이 없다.

`check_url_safe` 는 `http`/`https` 가 아니면 거부한다 (`215-216`). 라우트가 WebSocket 을 보면 스킴에서 끊긴다. 로컬 재현에서는 악수까지 완료됐다 (`WS_SENT`). 페이지 자체를 루프백에 두느라 `_ip_is_unsafe` 만 잠시 끈 상태에서 `_render_url` 은 `ok: True` 였고, 렌더 HTML 의 `<p id="o">` 는 `SECRET_FROM_WS` 였다. 그 문자열은 `ws://127.0.0.1` 서버가 보낸 프레임이다.

공개 페이지는 라우트와 `server_addr` 를 통과한다. 그 페이지의 스크립트는 `ws://127.0.0.1` 또는 `ws://169.254.169.254` 로 붙을 수 있고, 받은 텍스트를 DOM 에 쓰면 사다리가 그 HTML 을 성공 본문으로 가져간다. `server_addr` 는 HTTP 응답에만 붙는다.

## MED

### 4. `_DEAD_TITLE_RE` 가 단어 끝 없이 접두만 맞아, 긴 정상 글을 partial 로 내린다

`fetch.py:83-84`, 적용은 `343`.

`page not found`, `error\s*404`, `http\s*404`, `404\s*(error|not found)`, `페이지를 찾을 수 없` 에는 끝 경계가 없다. `not found\b` 만 경계가 있다. `.match` 라 제목 앞에서 접두가 맞으면 본문 길이와 상관없이 `suspect:not_found` 다.

재현 (본문 약 3659자, 모두 `partial` / `suspect:not_found`):

- `Page Not Founders Summit` (`page not found` 가 `founders` 의 접두)
- `404 Not Founders Club`
- `페이지를 찾을 수 없는 공공데이터`
- `Error 4040년 시장`
- `HTTP 4040 센서`

사다리는 partial 에서 멈추지 않는다. 다음 계층이 `ok` 를 주면 원문 대신 그 응답을 반환한다. 아래 5번이 그 경로다.

### 5. Jina 본문은 죽은 제목 검사를 건너뛰고, 원본 오류 경고는 앞 1000자만 본다

경고 처리 `fetch.py:557-559`. 제목 추출 `1085-1101` 은 `<title>` 과 `og:title` 만 본다.

재현 1. direct 입력은 테스트와 같은 `Page not found | Air Liquide` + 긴 메뉴 HTML 이라 `validate_body` 가 `partial` / `suspect:not_found` 다. 같은 글의 Jina 형태는 다음이고, `validate_body` 는 `ok` / `body 2090 chars` 다.

```text
Title: Page not found | Air Liquide

URL Source: https://origin.test/x

Markdown Content:
메뉴 항목입니다. ...
```

`_candidates` 를 이 두 응답으로 바꾸면 `_fetch_ladder` 결과는 `status=ok`, `note=jina`, `archived_url` 은 `https://r.jina.ai/...` 다. direct 가 죽은 페이지로 표시한 글이 Jina 각색본으로 성공 처리된다. `Title:` 줄은 `_html_title` 이 읽지 않기 때문이다. 소프트 404 는 HTTP 200 이라 `direct_dead` (`1038-1040`) 도 켜지지 않아 Jina 가 생략되지 않는다.

재현 2. `Title: ` 뒤에 `가` 1100자, 그 다음 줄 `Warning: Target URL returned error 404: Not Found`. `text[:1000]` 안에서는 경고가 없고, 전체 문자열에서는 있다. `_via_jina` 는 `ok` 인 응답의 앞 1000자만 보므로, 머리말이 길면 원본 404/403 을 200 성공으로 넘긴다. 경고가 앞 1000자 안에 있고 줄 시작이 `Warning: Target URL returned error 404` 인 테스트 형태는 실패로 잘 떨어진다.

### 6. 브라우저 HTTP 는 DNS 를 고정하지 않는다. 사후 검사는 전송 뒤이고, 실패하면 연다

라우트 `fetch.py:767-775`, `778-786`. 사후 검사 `837-847`. curl 쪽은 `448-449` 에서 `CurlOpt.RESOLVE` 로 검사한 주소를 고정한다. 브라우저는 `check_url_safe` 로 한 번 푼 뒤 `route.continue_()` 만 한다. Chromium 이 다시 푼다.

응답이 온 뒤에야 `response.server_addr()` 로 사설 IP 를 `blocked` 에 넣고, 본문을 읽은 다음 `SsrfBlocked` 를 낸다 (`867-868`). 주석(`841`) 그대로 요청은 이미 나갔다. `server_addr()` 가 `None` 이거나 예외면 `except: pass` 로 그 응답을 유지한다.

로컬에서 동기 `page.on("response")` 안의 `server_addr()` 는 멈추지 않고 `{'ipAddress': '127.0.0.1', 'port': ...}` 를 반환했다. 설치된 Playwright 는 리스너를 `EventGreenlet` 에서 돌리고 `_sync` 가 디스패처로 양보한다 (`playwright/_impl/_connection.py` 의 이벤트 리스너 루프). 이 호출 자체의 데드락은 재현되지 않았다.

남는 구멍: TTL 0 재바인딩이나 리졸버가 어긋나면 브라우저는 사설 주소로 붙는다. 페이지 스크립트는 그 본문을 읽어 공개 URL 로 `fetch` 할 수 있고, 그 공개 요청은 라우트가 허용한다. 파이썬이 `blocked` 를 보고 렌더 결과를 버리는 시점에는 이미 나가 있다. 사설 응답이 서브리소스여도 `blocked` 에 들어가면 사다리 전체가 `SsrfBlocked` 로 중단된다 (`_via_browser` `894-895`, 사다리 `1032-1033`). 메시지 문구는 `브라우저 주 문서 차단` 이다.

서비스 워커는 `service_workers="block"` (`833`) 이라 이번 변경의 공식 차단 경로를 쓴다. 다운로드는 `accept_downloads=False` 이고 문서 요청은 같은 라우트를 탄다. 이 두 가지는 결함으로 보지 않았다. 리터럴 사설 주소로의 리다이렉트가 홉마다 라우트에 다시 들어오는지는, 첫 응답의 `server_addr` 가 먼저 차단해 홉을 분리해 보지 못했다. 미확인.

### 7. 문서 40MB 상한이 상한을 넘기지 않은 호출자에게도 붙는다

`fetch.py:456-458`, 판정 `323-328`. `DOC_MAX_BYTES` 는 40MB, 기본 `MAX_BYTES` 는 8MB.

`max_bytes == MAX_BYTES` 이고 Content-Type 이 PDF·`_DOC_MIME`(여기에는 `text/csv`, `application/zip` 포함)이거나, `application/octet-stream` 이면서 경로 확장자가 문서이면 상한이 40MB 가 된다. 서버가 준 Content-Type 을 믿는다.

Content-Length 로 확인한 결과:

| 호출 | 응답 | 결과 |
| --- | --- | --- |
| 기본 상한 (`search._get` `58-61`, `harvest_images._json_get` `358-359`) | `text/html` 9MB | 거부 |
| 기본 상한 | `text/csv` 또는 `application/pdf` 20MB | 길이 검사를 통과 (40MB 미만) |
| 기본 상한 | `text/csv` 41MB | 거부 |
| `max_bytes=MAX_IMG_BYTES` (`harvest_images.download` `559-560`, 15MB) | csv/pdf 20MB | 거부 |

이미지 바이트 다운로드는 40MB 로 커지지 않는다. 검색과 이미지 JSON 검색은 상한을 넘기지 않으므로, 공개 SearXNG·Openverse 가 `Content-Type: text/csv` 또는 `application/zip` 을 주면 최대 40MB 를 메모리에 담는다. 예전에 이 호출자들이 기대하던 기본 상한은 8MB 다.

## LOW

### 8. 짧은 본문의 제목 검사는 `404` 만 숫자 경계를 본다

`fetch.py:278-285`, `288-300`. 본문 1000자 미만일 때만 돈다.

`_title_starts` 는 문구가 `404` 일 때만 다음 문자가 숫자면 제외한다. 재현:

- `404억 원 매출` → `not_found` (`억` 은 숫자가 아님)
- `Not Founders` → `not_found` (`not found` 가 `not founders` 의 접두)
- `4040억` → `None` (이 경우만 제외가 동작)

`sign in` 도 같은 접두 규칙이라 `Sign Industry` 는 `login` 이 된다. 긴 본문에서는 이 함수가 호출되지 않아 `404 Media` 류는 `ok` 다.

### 9. 짧은 본문 구절은 부분 문자열이면 걸린다

`fetch.py:268-275`, 구절 목록 `70-75`. 재현: 본문 `요청하신 페이지와 비슷한 문서` → `not_found`. `access denied by the court` → `access_denied`. `로그인이 필요한 서비스가 늘었다` → `login`.

1000자 미만 기사 안에 그 구절이 한 번만 있어도 `partial` 이다. 긴 인용은 길이 게이트 때문에 `ok` 로 남는 것을 확인했다.

## 결함으로 보지 않은 것

종료 코드 2 (`search.py:486-493`). 결과가 있으면 0. 시도한 백엔드가 전부 `blocked` 또는 `error` 이면 2. `empty` 가 하나라도 있으면 0. 주석과 같다. `blocked`+`empty` 를 호출해 0, `blocked`+`error` 를 호출해 2 를 확인했다.

`direct` 가 모두 404/410 이면 `wayback` 만 남긴다 (`979-982`, `1038-1040`). `MDR_NO_THIRD_PARTY=1` 또는 `no_third_party=True` 이면 `jina` 와 `wayback` 을 그 앞에서 건너뛴다 (`976-978`). 죽은 페이지를 아카이브로 보내지 않는 쪽이다. `test_rs_fetch.py` 의 `test_direct_404_skips_to_wayback`, `test_no_third_party_skips_jina_and_wayback` 과 맞다. 소프트 404(HTTP 200) 를 여기서 죽이지 않는 것은 주석대로이고, 그 구멍은 1번과 5번이다.

`join_workers.py` 의 COVERAGE 파서, `open_gaps`(UNREACHABLE+NOT_ATTEMPTED, NOT_FOUND 제외), 섹션이 없는 파일을 `missing` 으로만 두는 동작, `coverage` 명령이 항상 0 으로 끝나는 동작은 `agent-briefs.md` 와 `test_rs_design.py` 의 계약과 맞다. 여기서 계약 위반은 찾지 못했다.

브라우저 `try/finally` (`870-873`) 는 컨텍스트와 브라우저를 닫는다. `SsrfBlocked` 경로도 예외가 호출자까지 나오고 함수가 반환된 것을 로컬에서 봤다. `context.close()` 가 예외를 내면 `browser.close()` 는 실행되지 않는다. 그 다음 `sync_playwright` 종료가 자식 프로세스를 거두는지는 미확인.

403/503 뒤 `wait_for_event` (`859-864`) 는 이미 지난 응답을 다시 보지 않고, 이후의 최상위 document 2xx 를 기다린다. 상태 코드 갱신은 먼저 등록된 `on_response` 가 한다. 새 document 응답 없이 DOM 만 바뀌면 상태 코드는 403/503 으로 남아 렌더 본문을 성공으로 쓰지 않는다. 그 챌린지 형태는 사이트를 열지 않아 미확인이다.
