# Batch RF1 — 열람 정비 (`fetch.py`)

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/research-strengthening`).
같은 워크트리에서 RS(`search.py`)·RD(문서·`join_workers.py`)·RE(`_planning/recall-eval/`) 워커가 동시에 일한다. **아래 '손대는 파일' 밖은 고치지 않는다.**
이 배치가 끝나면 RF2(브라우저 계층)가 같은 `fetch.py` 를 이어서 고친다 — 계층 추가는 여기서 하지 않는다.

## 왜
열람 성공 판정이 "정제 본문 1000자 이상" 하나라서(`validate_body` 237행) 로그인벽·동의창·없는 페이지 안내문이 성공으로 저장된다.
과거 조사 7건 실측: 모바일 계층이 `m.` 을 붙여 DNS 실패를 반복, 한 조사에서 끝내 실패한 URL 이 19%. HWP·XLSX·8MB 초과 PDF 는 모든 계층에서 실패한다.

## 먼저 읽을 것
1. `_planning/research-strengthening-2026-10/analysis/a1-engine.md`, `a6-crawl-inventory.md`(계층 표·교체 시 깨질 계약), `a4-empirical.md` 의 수집 실패 부분.
2. `codes/market-deep-research/scripts/fetch.py` 전부(906줄), `preflight.py`, `install.py` 의 의존성 부분.
3. `grep -n "fetch\.\|validate_body\|IMPERSONATE_GRID\|DEFAULT_ORDER" codes/market-deep-research/tests/*.py codes/market-deep-research/scripts/*.py` — 호출처와 테스트가 단언하는 계약 전부.

## 지켜야 할 계약
- `validate_body` 의 verdict 는 **`ok|partial|challenge|empty` 4종 그대로**. 새 verdict 를 만들지 않는다.
- `fetch()` 반환 키, `audit/fetch-log.jsonl` 의 컬럼, `save()` 의 `.meta.json` 형식(`source_index.py` 가 읽는다), reason 접두(`mime:`, `http `)를 바꾸지 않는다. 키 **추가**는 된다.
- `request_bytes` 시그니처와 SSRF 방어(`check_url_safe`, `_resolve_safe`, 고정 IP)는 약화하지 않는다.
- `DEFAULT_ORDER` 는 이 배치에서 바꾸지 않는다(RF2 가 바꾼다). Googlebot 계층도 그대로 둔다(정책 문서가 서로 어긋나 사용자 결정 대기 중).

## 손대는 파일
- `codes/market-deep-research/scripts/fetch.py`, `scripts/preflight.py`, `scripts/install.py`
- `codes/market-deep-research/requirements.txt` (새로)
- `codes/market-deep-research/tests/test_rs_fetch.py` (새로)
- 기존 테스트 파일은 아래 변경으로 깨지는 단언만 최소 수정(파일 전체 재작성 금지, 수정 직전 다시 읽기). 예: `tests/test_batch2a_regressions.py:300` 은 `fetch.IMPERSONATE_GRID` 를 참조하므로 값만 바꾸면 그대로 통과해야 한다.

## 할 일
1. **지문 프로필 갱신.** `IMPERSONATE_GRID` 의 `chrome110`(2023년 초)을 설치본이 지원하는 **다른 엔진 계열** 최신 별칭으로 바꾼다(후보 `firefox`). `MOBILE_IMPERSONATE` 는 `safari180_ios` 대신 최신 iOS 별칭(후보 `safari_ios`).
   - 설치본(`curl_cffi` 0.16.2)이 그 별칭을 실제로 받는지 **코드로 확인하고** 고른다. 네트워크 없이 확인할 방법이 없으면 `https://example.com` 1회 요청은 허용.
   - `MOBILE_UA`(iOS 17.0)가 TLS 지문과 어긋난다. `MOBILE_HEADERS` 에서 `User-Agent` 를 빼서 프로필이 넣는 UA 를 쓰게 하거나, 프로필과 같은 버전으로 맞춘다. 어느 쪽인지와 이유를 주석 한 줄로.
   - 미지원 별칭일 때 mobile 계층의 degrade 조건(reason 이 `error:` 로 시작)이 실제로 동작하는지 확인하고, 안 하면 고친다.
2. **성공처럼 보이는 실패 걸러내기.** `validate_body` 에서 길이 판정(②) **앞에** "의심 페이지" 검사를 넣고, 걸리면 verdict `partial`, reason 은 `suspect:<종류>` 로 돌려준다(`partial` 이면 사다리가 다음 계층을 계속 시도하고, 끝까지 못 구하면 partial 로 보고된다).
   - 판정은 **`<title>` 기준**이 1차: 404·not found·페이지를 찾을 수 없·존재하지 않는·삭제된 / 로그인·sign in·log in / access denied·접근이 거부 / 쿠키·consent 동의. 본문 문구 검사는 정제 본문이 3000자 미만일 때만 쓴다 — 긴 기사가 "로그인"을 인용했다고 걸리면 안 된다(기존 V27 과 같은 취지).
   - `success_selectors` 가 맞으면 기존대로 최우선 `ok`.
3. **정제 폴백 보강.** `extract_text` 의 정규식 폴백이 `<script>`·`<style>` 내용까지 길이에 넣는다 → 태그 제거 전에 두 블록을 먼저 지운다.
4. **인코딩.** `response_text` 가 `Content-Type` 헤더의 charset 만 본다 → 헤더에 charset 이 없으면 본문 앞 2048바이트에서 `<meta charset=...>` / `<meta http-equiv="Content-Type" content="...charset=...">` 를 찾아 쓴다. 헤더가 있으면 헤더 우선(기존 동작 유지).
5. **헛요청 줄이기.**
   - direct 계층의 응답이 전부 404 또는 410 이면 mobile·jina·googlebot·rss 를 건너뛰고 wayback 만 시도한다(죽은 페이지의 아카이브는 정당한 대체물).
   - `_mobile_urls` 가 만든 `m.` 호스트가 DNS 로 풀리지 않으면 그 후보를 조용히 건너뛴다(시도 로그에 실패 줄을 남기지 않는다).
   - direct 에서 429 를 받으면 같은 계층의 남은 프로필을 더 치지 않는다.
6. **문서 파일 원본 저장.** HWP·HWPX·XLSX·XLS·DOCX·PPTX·CSV·ZIP 을 허용 MIME 에 넣고, PDF 와 같은 방식(본문 판정 없이 원본 저장, verdict `ok`, note 로 종류 표시)으로 다룬다. `save()` 의 확장자도 맞춘다. MIME 이 `application/octet-stream` 이면 URL 확장자로 판단한다. PDF·문서 파일의 크기 상한만 40MB 로 올리고 HTML 은 8MB 그대로.
7. **제3자 계층 끄기.** 환경변수 `MDR_NO_THIRD_PARTY=1` 또는 CLI `--no-third-party` 이면 `jina`·`wayback` 계층을 건너뛴다(대외비 조사에서 열람 대상 URL 이 외부 서비스로 나가지 않게). 건너뛴 사실은 trace 에 남긴다.
8. **버전 고정.** `requirements.txt` 에 필수·선택 의존성을 설치본 기준 범위로 적는다(`curl_cffi>=0.16.2,<0.17` 식. 패키지 철자 주의 — `curl_cffi` 를 흉내 낸 악성 패키지 `cffi-curl` 이 보고돼 있다). `preflight.py` 는 주요 패키지 버전을 출력하고, 코드가 쓰는 impersonate 별칭이 설치본에서 미지원이면 SOFT 경고를 낸다. `install.py` 가 의존성을 설치하는 자리가 있으면 `requirements.txt` 를 쓰게 한다.
9. **테스트** `tests/test_rs_fetch.py` (네트워크 없이): 의심 페이지 4종이 `partial`+`suspect:` / 긴 기사 안의 "로그인" 문구는 `ok` / script·style 만 있는 SPA 셸은 `ok` 가 아님 / 헤더 없는 EUC-KR 페이지가 meta charset 으로 깨지지 않고 디코드 / 404 조기 종료 시 계층 호출 순서 / 풀리지 않는 `m.` 후보 건너뜀 / HWP·XLSX 응답이 원본 저장되고 확장자가 맞음 / 40MB 상한이 문서에만 적용 / `MDR_NO_THIRD_PARTY` 시 jina·wayback 미호출. `python scripts/fetch.py demo` 의 기존 단언도 통과.

## 일부러 안 하는 것 (만들지 말 것)
- **열람 캐시**: 이 스킬은 보고서 진입 전 원문을 다시 여는 것이 증빙의 핵심이라, 캐시는 그 재검증을 무력화한다.
- 프로세스 간 속도 제한, robots.txt 파서, 프록시, 로그인 쿠키, 새 의존성.
- 브라우저 계층(RF2), `curl_cffi` 교체.

## 검증 (전부 통과해야 완료)
```bash
cd codes/market-deep-research
python scripts/fetch.py demo
python scripts/preflight.py
python -m pytest -q -p no:cacheprovider tests/test_rs_fetch.py
python -m pytest -q -p no:cacheprovider --ignore=tests/test_v4_gates.py --ignore=tests/test_v4_semantic.py   # 기준선 602 passed, 줄면 안 됨
```
`tests/test_v4_gates.py`·`test_v4_semantic.py` 는 main 에서 이미 깨져 있다(없는 모듈 import) — 고치지 말고 무시한다.

## 제약
- `git commit`·`git stash`·`git checkout` 금지(워크트리 공유). `.fablize/goals.py` 실행 금지. 패키지 설치·업그레이드 금지.
- 주석·문서·출력 문구는 한국어, 식별자는 영어. 주변 코드의 주석 밀도와 관례를 따른다.
- 외부 사이트 호출은 위 1번의 별칭 확인 1~2회까지만.
- 모르는 것은 추측하지 말고 `orca orchestration ask`. 완료 보고에는 바뀐 파일, 검증 명령의 마지막 줄 출력, 고른 프로필 별칭과 근거, 남긴 한계를 적는다.
