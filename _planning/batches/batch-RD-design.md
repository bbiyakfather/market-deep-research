# Batch RD — 조사 설계: "못 찾음"을 기록하고 빠진 곳으로 되돌아가기

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/research-strengthening`).
같은 워크트리에서 RS(`search.py`)·RF1(`fetch.py`)·RE(`_planning/recall-eval/`) 워커가 동시에 일한다. **아래 '손대는 파일' 밖은 고치지 않는다.**

## 왜
이 스킬의 게이트는 "모은 사실이 맞는가"만 본다. "못 모은 것이 있는가"를 보는 장치가 없다.
- 워커는 결과가 없으면 `없음` 만 적는다 — 없는 것과 못 찾은 것과 접근이 막힌 것이 한 칸이다(`agent-briefs.md` 반환 마커).
- 확장·수렴 루프의 종료는 워커가 신고한 EXPAND 리드 수로만 판정한다(`join_workers.py` 의 `convergence`).
- 조사 대상 목록을 빠짐없이 세는 단계가 없다. 과거 조사 7건 실측: 대상의 74~92% 가 사실 1건뿐, 워커 증거의 85~100% 가 코어 수집 로그(`audit/fetch-log.jsonl`)에 없음.

## 먼저 읽을 것
1. `_planning/research-strengthening-2026-10/analysis/a2-design.md`(약점 W표와 강화안), `a4-empirical.md`, `a5-external.md` 의 이식 후보.
2. `codes/market-deep-research/SKILL.md`, `references/agent-briefs.md`, `research-plan.md`, `source-ladder.md`, `competitive-positioning.md`, `verification-gates.md`, `extract-recipes.md`, `codes/mdr-search/SKILL.md`.
3. `codes/market-deep-research/scripts/join_workers.py` 전부, `assets/facts-schema.json`, `scripts/facts_db.py` 의 `validate_fact`/`validate_evidence`.
4. `grep -n "수렴\|충분조건\|EXPAND\|깊이캡" codes/market-deep-research/tests/*.py` — 문서 문구를 단언하는 테스트(`test_adversarial.py` 1265행 부근 등). 문구를 바꾸면 이 테스트도 같이 고친다.

## 손대는 파일
- `codes/market-deep-research/SKILL.md`, `references/agent-briefs.md`, `references/research-plan.md`, `references/source-ladder.md`, `references/verification-gates.md`, `references/competitive-positioning.md`, `codes/mdr-search/SKILL.md`
- `codes/market-deep-research/scripts/join_workers.py`
- `codes/market-deep-research/assets/facts-schema.json` (선택 필드 추가만)
- `codes/market-deep-research/tests/test_rs_design.py` (새로)
- 기존 테스트 파일은 문구·계약 변경으로 깨지는 단언만 최소 수정(파일 전체 재작성 금지, 수정 직전 다시 읽기).

## 문서 작성 규칙
- 이 문서들은 LLM 이 매번 읽는 프롬프트다. **짧게**. 기존 문서의 밀도·표기·번호 체계(【v3-A】 같은 표지 포함)를 따르고, 같은 규칙을 두 문서에 중복해 쓰지 않는다(한 곳에 쓰고 다른 곳은 참조).
- 규칙에는 이유를 한 구절로 붙인다. 순증 분량 목표: 전체 합쳐 120줄 이내.

## 할 일
1. **워커 반환에 `## COVERAGE` 섹션** (`agent-briefs.md` 반환 마커에 추가, `join_workers.py` 가 파싱).
   ```
   ## COVERAGE
   - QUERY: <검색식> — BACKEND: <ddg|searx|WebSearch|MCP:이름> — RESULT: <건수>|BLOCKED|ERROR
   - GAP: <대상·항목> — STATE: NOT_FOUND|UNREACHABLE|NOT_ATTEMPTED — TRIED: <시도한 검색식 수> — WHY: <한 줄>
   ```
   - `NOT_FOUND`=서로 다른 검색식 3회 이상 시도했고 백엔드가 정상 응답했는데 없음. `UNREACHABLE`=검색 백엔드 차단·오류, 또는 출처는 찾았으나 열람 실패. `NOT_ATTEMPTED`=시간·범위 때문에 시도하지 않음.
   - RS 워커가 `search.py` 에 넣는 계약: `--json` 출력의 `backends[].status` 가 `ok|empty|blocked|error`, **종료 코드 2 = 전 백엔드 실패**. 종료 코드 2 는 `NOT_FOUND` 가 아니라 `UNREACHABLE` 로 적게 한다.
   - `join_workers.py`: COVERAGE 를 파싱해 출력에 `coverage`(파일별 질의 수, GAP 목록, 상태별 집계)를 더한다. 형식이 틀린 줄은 다른 섹션과 같은 방식으로 오류 처리.
   - **섹션이 아예 없는 워커 파일은 invalid 로 만들지 않는다**(기존 테스트 픽스처 보호). 대신 `coverage.missing` 에 파일명을 적고, 아래 2번의 수렴 판정에서 미수렴으로 센다.
2. **수렴 판정에 공백을 넣는다.** `convergence` 에 `open_gaps`(UNREACHABLE+NOT_ATTEMPTED 건수)와 `coverage_missing` 을 추가하고, 기존 `empty_expand_wave` 는 그대로 둔다(하위 호환). `SKILL.md` 의 루프 수렴조건에 "열린 공백 0, 또는 각 공백을 `audit/gap-log.md` 에 수용 사유와 함께 기록"을 더한다.
3. **0웨이브 대상 열거.** 목록형 조사(기업·제품·기관·프로젝트를 여럿 다루는 조사)에서는 본조사 전에 대상 목록부터 만든다. `research-plan.md` 에 절차, `SKILL.md` 에 한 줄.
   - 산출물 `audit/universe.md`: 표 `| 대상 | 별칭 | 목록 출처 | 포함/제외 | 사유 |`. 목록 출처는 서로 독립인 것 2개 이상(협회 회원사 명부, 통계·공시 DB, 업계 지도, 특허 출원인 순위 등).
   - `python scripts/join_workers.py coverage <work_dir>` 하위 명령: `audit/universe.md` 의 포함 대상과 사실 대장(`facts_db` 가 쓰는 대장)을 대조해 **사실 0건 대상**과 **1건뿐인 대상**을 나열하고, 증거 URL 중 `audit/fetch-log.jsonl` 에 없는 비율을 경고로 낸다(`api_response`·`negative_search`·`calculation` 증거는 제외). 파일이 없으면 그 검사만 건너뛰고 알린다. 종료 코드는 항상 0(보고용).
4. **축별 충분조건을 서식으로.** `research-plan.md` 의 "축별 충분조건"을 체크리스트 형태로(축마다: 필수 항목, 대상당 최소 사실 수, 독립 출처 수, 기준 시점). 예시는 1개만.
5. **탈락 사실의 복귀 규칙.** 재열람·반박검색·claim-review 에서 탈락한 사실은 사유 코드와 함께 `audit/gap-log.md` 에 적고, 사유별 후속을 정한다: 원문 불일치(워커 의역) → 같은 출처 재발췌 / 출처 접근 불가 → 대체 출처 탐색 / 반박됨 → 반박 근거를 사실로 등재하고 종결. `SKILL.md`·`verification-gates.md` 중 한 곳에만 쓰고 다른 곳은 참조.
6. **워커 지시문 보강** (`agent-briefs.md`).
   - 스폰 메시지의 `3. 프로토콜` 에 질의 설계 블록: 검색식은 서로 다른 각도로 3개 이상(대상명+항목 / 상위 개념+목록어 / 반대·실패 사례), `site:`·`filetype:pdf` 연산자, 한 검색식이 0건이면 표현을 바꿔 재시도.
   - **1차 출처 라우팅**: 공시·재무 → DART(국내)·`search.py --type filing`(해외), 특허 → KIPRIS·특허 DB 도구, 국가 R&D → NTIS, 통계 → KOSIS. 해당 MCP·스킬이 도구 목록에 있으면 웹 검색보다 먼저 쓴다. **`patents.google.com` 은 크롤링하지 않는다**(과거 조사에서 끝내 실패한 URL 의 60% 가 이 도메인) — 특허번호로 DB 도구를 조회한다. 도구로 얻은 응답은 `api_response` 증거로 남긴다.
   - **코어 스택 규칙**: 증거로 쓸 웹 페이지는 발견 경로(WebSearch 포함)와 무관하게 `fetch.py` 로 다시 받아 `audit/fetch-log.jsonl` 과 원본 스냅샷을 남긴다(이유: 내장 WebFetch 로만 본 페이지는 차단·실패 기록도 원본도 남지 않는다).
   - `competitive-positioning.md:16` 의 "서로 다른 검색식 3회 이상 후 미확인 확정"을 공통 규칙으로 올리고 그 문서는 참조만 하게 한다. 반증 탐색 범위를 high-risk 수치 외에 **우열·유일·최초·순위 서술**까지 넓힌다.
7. **문서 내 불일치 정리.** `SKILL.md` 의 기본 깊이캡(3회/12명)과 `research-plan.md` 의 실측값(5~6웨이브/30~40명) 관계를 한 문장으로 정리. 기술동향 분할의 "교차검증1" 워커 임무를 한 줄로 정의.
8. **스키마 선택 필드.** `facts-schema.json` 의 fact 에 선택 필드 `discovery`(`{query, wave, axis, worker}`, 모두 문자열·선택)를 더한다. **기존 대장·기존 테스트가 그대로 통과**해야 한다 — `validate_fact` 가 모르는 필드를 거부하는 구조면 그에 맞게 허용만 추가. 무리가 있으면 이 항목은 하지 말고 보고에 이유를 적는다.
9. **`mdr-search/SKILL.md`** 를 위 1·6번과 맞춘다(종료 코드 2 의 뜻, COVERAGE 기록).
10. **테스트** `tests/test_rs_design.py`: COVERAGE 파싱(정상·형식 오류·섹션 없음) / `open_gaps`·`coverage_missing` 집계 / COVERAGE 없는 기존 형식 워커 파일이 여전히 `ok` / `coverage` 하위 명령이 0건·1건 대상과 로그 밖 증거 비율을 보고(임시 폴더 합성 자료) / 문서에 핵심 표지(`## COVERAGE`, `audit/universe.md`, `audit/gap-log.md`)가 존재.

## 일부러 안 하는 것 (만들지 말 것)
- 대상 열거·충분조건 판정을 강제하는 새 게이트(G 번호 추가): 먼저 보고용 명령으로 쓰고 데이터를 본 뒤 결정한다.
- 다관점 질의 자동 생성기, 한/영 이중 질의 규칙: 효과 측정 전이다.
- `gates.py`·`facts_db.py`·`verify_*.py` 수정.

## 검증 (전부 통과해야 완료)
```bash
cd codes/market-deep-research
python scripts/join_workers.py demo 2>/dev/null || python scripts/join_workers.py --help   # 기존 자가점검이 있으면 통과
python -m pytest -q -p no:cacheprovider tests/test_rs_design.py
python -m pytest -q -p no:cacheprovider --ignore=tests/test_v4_gates.py --ignore=tests/test_v4_semantic.py   # 기준선 602 passed, 줄면 안 됨
```
`tests/test_v4_gates.py`·`test_v4_semantic.py` 는 main 에서 이미 깨져 있다(없는 모듈 import) — 고치지 말고 무시한다.

## 제약
- `git commit`·`git stash`·`git checkout` 금지(워크트리 공유). `.fablize/goals.py` 실행 금지.
- 문서·주석·출력 문구는 한국어, 식별자는 영어.
- 모르는 것은 추측하지 말고 `orca orchestration ask`. 완료 보고에는 바뀐 파일, 검증 명령의 마지막 줄 출력, 문서 순증 줄 수, 하지 않은 항목과 이유를 적는다.
