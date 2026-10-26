# Batch RS — 검색 실패를 보이게 하기 + 검색 겹 늘리기 (`search.py`)

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/research-strengthening`).
같은 워크트리에서 RF1(`fetch.py`)·RD(문서·`join_workers.py`)·RE(`_planning/recall-eval/`) 워커가 동시에 일한다. **아래 '손대는 파일' 밖은 고치지 않는다.**

## 왜
`search.py` 는 백엔드가 차단·오류여도 빈 목록 `[]` 을 돌려준다(`_ddg` 44-50행, `_searx` 71-89행). 워커는 이것을 "자료 없음"으로 읽는다.
2026-10-13 실측에서 공개 SearXNG 5곳 중 JSON 을 준 곳은 0곳 — 지금 검색은 DuckDuckGo 한 겹이다.

## 먼저 읽을 것
1. `_planning/research-strengthening-2026-10/analysis/a1-engine.md` 의 검색 부분, `a6-crawl-inventory.md` 의 실측 부분.
2. `codes/market-deep-research/scripts/search.py` 전부, `assets/searx-instances.json`, `assets/curated-sources.json` 의 `type_backends`.
3. `codes/market-deep-research/tests/test_adversarial.py` 앞 80행(테스트 관례)과 `grep -n "search\." tests/*.py` 로 기존 search 테스트.

## 손대는 파일
- `codes/market-deep-research/scripts/search.py`
- `codes/market-deep-research/assets/searx-instances.json`
- `codes/market-deep-research/assets/searxng/docker-compose.yml`, `assets/searxng/settings.yml` (새로)
- `codes/market-deep-research/tests/test_rs_search.py` (새로)
- 기존 테스트 파일은 search 계약 변경으로 깨지는 단언만 최소 수정(파일 전체 재작성 금지, 수정 직전 다시 읽기 — 다른 워커가 같은 파일을 만질 수 있다).

## 할 일
1. **백엔드 상태 반환.** `search_report(query, n=10, type="web") -> dict` 를 추가한다:
   `{"results": [...], "backends": [{"name": "ddg", "status": "ok|empty|blocked|error", "count": int, "detail": str}, ...]}`.
   - `ok`=결과 1건 이상, `empty`=정상 응답인데 0건, `blocked`=HTTP 403/429/챌린지·캡차 페이지, `error`=예외·5xx·파싱 불가.
   - `_ddg` 는 지금 버리는 HTTP 상태값을 본다. 200 인데 `result__a` 가 0개면 본문에서 캡차/anomaly 표지를 찾아 `blocked` 와 `empty` 를 가른다.
   - 기존 `search()` 는 시그니처·반환형(list) 그대로 두고 `search_report(...)["results"]` 를 돌려주는 얇은 래퍼로 만든다. arxiv·sec_edgar·wikipedia 도 같은 상태 규칙을 따른다(지금 `_sec_edgar` 는 경고도 없이 삼킨다).
2. **CLI.** 기존 출력은 유지하고 다음을 더한다.
   - 결과 뒤 stderr 에 백엔드별 한 줄: `backend ddg: blocked (http 429)`.
   - `--json` 이면 stdout 에 `search_report` 전체를 JSON 으로.
   - **종료 코드 2**: 결과 0건이고 시도한 백엔드가 전부 `blocked|error` 일 때("찾아봤는데 없음"이 아니라 "찾아보지 못함"). 결과 0건이고 하나라도 `empty` 면 0.
   - `python scripts/search.py health` : `searx-instances.json` 의 `health_path` 와 ddg 를 각 1회 찔러 상태표를 출력(재시도 없음).
3. **SearXNG 재시도 규칙 바로잡기.** 지금은 주석과 반대로 429 에 즉시 포기하고 예외에만 1/2/4초를 기다린다.
   - 429·5xx 에만 백오프 재시도, DNS 실패·타임아웃 같은 예외는 즉시 다음 인스턴스.
   - 한 번의 `_searx` 호출 전체에 시간 상한(예: 30초)을 둔다.
4. **자체 호스팅 인스턴스.** 환경변수 `MDR_SEARX_URL`(쉼표로 여러 개)이 있으면 공개 목록보다 **먼저** 쓴다.
   - 주의: `_get` 은 `fetch.request_bytes` 를 타고, 그 안의 SSRF 방어가 사설 IP·localhost 를 막는다. `MDR_SEARX_URL` 은 운영자가 직접 지정한 신뢰 엔드포인트이므로 **이 URL 에 한해서만** 표준 라이브러리 `urllib.request` 로 직접 호출한다. `fetch.py` 의 SSRF 방어는 건드리지 않는다(그 파일은 RF1 소유).
   - `assets/searxng/docker-compose.yml` + `settings.yml`: 공식 `searxng/searxng` 이미지, `search.formats` 에 `json` 허용, `127.0.0.1:8888` 바인딩, limiter 끔. 파일 머리 주석에 실행 명령 2줄과 `MDR_SEARX_URL=http://127.0.0.1:8888` 설정법. **컨테이너를 실제로 띄우지는 않는다**(사용자가 한다).
5. **결과 중복 제거.** URL 정규화 함수 하나(호스트 소문자, fragment 제거, `utm_*`·`fbclid`·`gclid` 제거, 끝 슬래시 정리)로 ddg+searx 병합 시 중복을 판정한다. 결과의 `url` 값 자체는 원본 그대로 둔다.
6. **테스트** `tests/test_rs_search.py` (네트워크 없이, `_get` 을 스텁으로 교체):
   ddg 429 → `blocked`·종료 코드 2 / ddg 200+캡차 → `blocked` / ddg 200+정상 0건 → `empty`·종료 코드 0 / 예외 → `error` /
   `search()` 반환형이 list 그대로 / searx: 429 는 백오프 후 재시도·DNS 예외는 즉시 다음 인스턴스(`time.sleep` 스텁으로 호출 횟수 확인) /
   `MDR_SEARX_URL` 우선·urllib 경로 사용 / URL 정규화 중복 제거. `demo()` 의 기존 단언도 계속 통과해야 한다.

## 일부러 안 하는 것 (만들지 말 것)
- 공시·통계·특허용 새 검색 백엔드(DART/KIPRIS 등): 워커가 기존 MCP·스킬로 조회하도록 RD 가 문서로 라우팅한다.
- 날짜 필터·한/영 이중 질의·순위 재정렬: 효과 측정 전이다.
- 새 의존성 추가.

## 검증 (전부 통과해야 완료)
```bash
cd codes/market-deep-research
python scripts/search.py demo
python -m pytest -q -p no:cacheprovider tests/test_rs_search.py
python -m pytest -q -p no:cacheprovider --ignore=tests/test_v4_gates.py --ignore=tests/test_v4_semantic.py   # 기준선 602 passed, 줄면 안 됨
```
`tests/test_v4_gates.py`·`test_v4_semantic.py` 는 main 에서 이미 깨져 있다(없는 모듈 import) — 고치지 말고 무시한다.

## 제약
- `git commit`·`git stash`·`git checkout` 금지(워크트리 공유). `.fablize/goals.py` 실행 금지.
- 주석·문서·출력 문구는 한국어, 식별자는 영어. 주변 코드의 주석 밀도와 관례를 따른다.
- 실제 외부 검색 호출은 `health` 수동 확인 1회까지만. 부하 테스트 금지.
- 모르는 것은 추측하지 말고 `orca orchestration ask`. 완료 보고에는 바뀐 파일, 검증 명령의 마지막 줄 출력, 남긴 한계를 적는다.
