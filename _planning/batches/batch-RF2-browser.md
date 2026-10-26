# Batch RF2 — 브라우저 계층 (`fetch.py`, RF1 완료 후 투입)

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/research-strengthening`). RF1(열람 정비)이 끝난 `fetch.py` 위에서 일한다. **아래 '손대는 파일' 밖은 고치지 않는다.**

## 왜
지금 사다리(`direct → mobile → jina → googlebot → rss → wayback`)에는 JavaScript 로 그려지는 페이지를 여는 계층이 없다. 그런 페이지는 제3자 서비스 Jina 에 간접 의존하는 것이 전부이고, 대외비 조사에서는 그 길도 쓸 수 없다. Playwright 1.58 과 브라우저는 이미 설치돼 있고 화면 캡처(`capture_web.py`)에만 쓰인다.

## 먼저 읽을 것
1. `_planning/research-strengthening-2026-10/analysis/a6-crawl-inventory.md`(계층 표·깨질 계약), `a7-crawl-libs.md`(patchright 근거).
2. `codes/market-deep-research/scripts/fetch.py` 전부(RF1 반영본), `capture_web.py`(Playwright 사용 관례), `preflight.py`, `install.py`, `requirements.txt`.
3. `references/source-ladder.md` 의 계층 설명과 `references/extract-recipes.md:22`.

## 지켜야 할 계약
- RF1 과 같다: verdict 4종, `fetch()` 반환 키, fetch-log 컬럼, `.meta.json` 형식, SSRF 방어.
- 브라우저 계층의 응답도 `_fetch_once` 와 같은 모양(`ok, status, text, final_url, mime, reason`)으로 돌려주고, 판정은 기존 `validate_body` 를 그대로 탄다.

## 손대는 파일
- `codes/market-deep-research/scripts/fetch.py`, `scripts/preflight.py`, `scripts/install.py`, `requirements.txt`
- `codes/market-deep-research/references/source-ladder.md`, `references/extract-recipes.md` (계층 목록·순서 설명만)
- `codes/market-deep-research/tests/test_rs_browser.py` (새로)
- `fetch.py` 의 `demo()` 안 `DEFAULT_ORDER` 단언과, 계층 순서를 단언하는 기존 테스트(최소 수정).

## 할 일
0. **(먼저) RF1 의 의심 페이지 판정 오탐 수정.** 코디네이터 검수에서 회귀가 확인됐다. `_SUSPECT_RULES` 의 문구가 `동의`·`쿠키`·`404`·`로그인`·`삭제된`·`consent` 같은 한 단어라서 정상 기사가 `partial` 로 떨어진다(한국어 뉴스는 대부분 3000자 미만이고, 이 단어들은 기사 본문·제목에 흔하다). `partial` 이 되면 나머지 계층을 전부 헛돈다.
   - **본문 규칙**: 한 단어 금지. 차단 페이지에만 나오는 **구절**로만 판정한다(예: `로그인이 필요`, `로그인 후 이용`, `sign in to continue`, `page not found`, `페이지를 찾을 수 없`, `요청하신 페이지`, `쿠키 사용에 동의`, `accept all cookies`, `access denied`, `접근이 거부`). 그리고 정제 본문이 **1000자 미만**일 때만 본다(1000자 이상은 기존 V27 규칙대로 확정 성공).
   - **제목 규칙**: 제목 안에 단어가 들어 있다는 것만으로 판정하지 않는다. 제목이 그 문구로 **시작**하거나(구분자 `-|·:` 앞 첫 토막이 `404`/`Not Found`/`로그인`/`Sign in`/`Log in`/`Access Denied`/`페이지를 찾을 수 없습니다` 류) 제목 전체가 그 문구일 때만 걸고, **그러면서 정제 본문이 1000자 미만**일 때만 `partial` 로 한다.
   - `tests/test_rs_fetch.py` 에 아래를 **전부** 넣는다(각 페이지는 `<article>` 안에 한국어 문단을 반복해 만든다):
     걸리면 안 됨(`ok`): 1300자 기사+본문 "합병안에 동의했다" / 1300자 기사+본문 "매출은 1,404억 원" / 1300자 기사+본문 "서드파티 쿠키 폐지" / 4200자 기사+제목 "쿠키 없는 광고 시장 전망" / 4200자 기사+제목 "국회, 합병 동의안 통과" / 4200자 기사+제목 "간편 로그인 시장 점유율" / 1300자 기사+제목 "삭제된 영상 논란".
     걸려야 함(`partial`, `suspect:`): 제목 "로그인 - 사이트"+본문 "로그인이 필요한 서비스입니다"(100자) / 제목 "404 Not Found"+짧은 본문 / 제목 "Sign in · Example"+짧은 본문 / 본문 "요청하신 페이지를 찾을 수 없습니다"(짧음).
1. **`browser` 계층 추가.** `DEFAULT_ORDER = ["direct", "mobile", "browser", "jina", "googlebot", "rss", "wayback"]`.
   - `_via_browser(url) -> dict`: 헤드리스 Chromium 으로 열고, 네트워크가 잠잠해질 때까지(상한 20초) 기다린 뒤, 지연 로딩용으로 끝까지 스크롤을 최대 5회(매회 높이가 늘지 않으면 중단), 그다음 `page.content()` 를 `text` 로 돌려준다. `status` 는 주 문서 응답의 HTTP 상태, `final_url` 은 `page.url`.
   - **엔진 선택**: `patchright` 가 import 되면 그것을, 아니면 `playwright` 를 쓴다(API 가 같다). 둘 다 없거나 브라우저 실행 파일이 없으면 이 계층은 `{"ok": False, "reason": "skip:browser 미설치"}` 를 내고 사다리가 다음 계층으로 간다. **선택 의존성**이다 — 없어도 나머지가 전부 동작해야 한다.
   - 환경변수 `MDR_BROWSER=0` 이면 계층을 건너뛴다.
   - RF1 의 404/410 조기 종료 경로에서는 브라우저도 건너뛴다.
2. **SSRF 방어를 브라우저에도.** 브라우저는 `request_bytes` 를 거치지 않으므로 방어가 따로 필요하다.
   - 진입 전 `check_url_safe(url)`.
   - `page.route("**/*", handler)` 로 **모든 요청**(리다이렉트·하위 자원 포함)의 URL 을 `check_url_safe` 로 검사해 사설·루프백·링크로컬·비 http(s) 스킴이면 `route.abort()`. 주 문서가 막히면 `SsrfBlocked` 를 전파한다(기존 사다리가 보안 사건으로 다루는 방식 그대로).
   - 다운로드는 받지 않는다(`accept_downloads=False`). 권한 요청은 전부 거부. 컨텍스트는 호출마다 새로 만들고 닫는다(쿠키·저장소를 남기지 않는다).
   - 이미지·폰트·미디어 요청은 abort 해 속도를 올린다.
3. **patchright 를 선택 의존성으로 등록.** `requirements.txt` 에 선택 항목으로 버전 범위와 함께 적고(PyPI 에서 정확한 패키지명·최신 버전을 직접 확인: `https://pypi.org/pypi/patchright/json`), `preflight.py` SOFT 항목에 "브라우저 계층: patchright / playwright / 없음" 을 출력, `install.py` 의 안내 문구에 설치 명령 2줄(`pip install patchright`, `patchright install chromium`). **이 배치에서 `pip install` 을 실행해도 된다**(patchright 한 개, 철자 확인 후). 설치가 실패하면 playwright 경로로 진행하고 보고한다.
4. **실패 힌트 갱신.** 사다리 전 계층 소진 시 hint 의 "브라우저 MCP(agent-browser 우선…)" 문구를 현재 구조에 맞게 고친다(브라우저 계층이 꺼져 있었는지 포함).
5. **문서.** `source-ladder.md` 의 계층 목록에 브라우저 계층을 넣고 번호를 맞춘다. `MDR_BROWSER`, `MDR_NO_THIRD_PARTY` 두 스위치를 한 표로. `extract-recipes.md:22` 의 계층 나열도 맞춘다. 순증 15줄 이내.
6. **테스트** `tests/test_rs_browser.py`:
   - 네트워크·브라우저 없이: `_via_browser` 를 스텁으로 바꿔 계층 순서(direct·mobile 실패 → browser 호출 → ok 반환, jina 미호출) / `MDR_BROWSER=0` 시 미호출 / 엔진 미설치 시 `skip:` 사유로 다음 계층 진행 / 404 조기 종료 시 미호출.
   - 요청 검사 핸들러 단위 테스트: 가짜 route 객체에 `http://127.0.0.1/`·`http://169.254.169.254/`·`file:///etc/passwd` 를 넣으면 abort, 공인 URL 은 continue.
   - 실제 브라우저 스모크(엔진이 있을 때만, 없으면 `skipTest`): `page.set_content` 또는 `data:` URL 로 "스크립트가 본문을 그리는 페이지"를 열어 렌더링된 텍스트가 `text` 에 들어오는지. 외부 사이트는 호출하지 않는다 — 이 스모크는 `_via_browser` 의 내부 렌더 함수를 직접 호출하도록 함수를 둘로 나눠도 된다(진입 검사 / 렌더).

## 일부러 안 하는 것 (만들지 말 것)
- 챌린지 풀이(Turnstile 클릭 등), 프록시, 로그인·쿠키 주입, 핑거프린트 주입 설정, 브라우저 풀·재사용, Camoufox/nodriver 지원.
- "더 보기" 버튼 자동 클릭: 사이트마다 달라 일반화가 안 된다. 스크롤만 한다.
- 통합 프레임워크 도입.

## 검증 (전부 통과해야 완료)
```bash
cd codes/market-deep-research
python scripts/fetch.py demo
python scripts/preflight.py
python -m pytest -q -p no:cacheprovider tests/test_rs_browser.py tests/test_rs_fetch.py
python -m pytest -q -p no:cacheprovider --ignore=tests/test_v4_gates.py --ignore=tests/test_v4_semantic.py   # RF1 완료 시점 통과 수에서 줄면 안 됨
```

## 제약
- `git commit`·`git stash`·`git checkout` 금지(워크트리 공유). `.fablize/goals.py` 실행 금지.
- 주석·문서·출력 문구는 한국어, 식별자는 영어.
- 외부 사이트에 대한 브라우저 열람 시도는 하지 않는다(실측은 코디네이터가 한다).
- 모르는 것은 추측하지 말고 `orca orchestration ask`. 완료 보고에는 바뀐 파일, 검증 명령의 마지막 줄 출력, 쓴 엔진과 버전, 남긴 한계를 적는다.
