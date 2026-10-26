# Batch RE — 재현율·열람 성공률 측정 도구 (`_planning/recall-eval/`)

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/research-strengthening`).
같은 워크트리에서 RS(`search.py`)·RF1(`fetch.py`)·RD(문서·`join_workers.py`) 워커가 동시에 일한다. **`_planning/recall-eval/` 밖은 고치지 않는다.**

## 왜
이 스킬은 "얼마나 빠뜨리는가"를 잰 적이 없다. 다른 워커들이 검색·열람·조사 설계를 고치는데, 전후를 숫자로 비교할 도구가 없으면 나아졌는지 알 수 없다.
필요한 측정은 둘이다: (1) 대상 재현율 — 정답 대상 목록 중 몇 개를 찾았는가, (2) 열람 성공률 — 과거에 끝내 실패한 URL 을 지금 사다리가 얼마나 여는가.

## 먼저 읽을 것
1. `_planning/research-strengthening-2026-10/analysis/a4-empirical.md` — 과거 조사 7건의 폴더 경로와 산출물 구조가 적혀 있다.
2. `_planning/exa-eval/exa_eval.py` 의 채점 부분(이름 정규화·매칭), `ground_truth.json`, `.gitignore`.
3. `codes/market-deep-research/scripts/fetch.py` 의 `fetch()` 반환 형태와 `audit/fetch-log.jsonl` 한 줄의 모양(읽기만).
4. `codes/market-deep-research/assets/facts-schema.json`(사실 대장의 subject 필드).

## 손대는 파일 (전부 새로)
- `_planning/recall-eval/recall_eval.py`
- `_planning/recall-eval/README.md`
- `_planning/recall-eval/.gitignore`

## 할 일 — 스크립트 하나, 하위 명령 넷
1. `build-truth <조사폴더> --out truth/<이름>.json`
   과거 조사의 사실 대장에서 대상(subject) 목록을 뽑아 `{"name": ..., "aliases": [...], "fact_count": n}` 배열로 저장한다. 조사 폴더마다 대장 위치·형식이 조금씩 다르다(a4 보고 참조) — 못 읽는 형식이면 추측하지 말고 명확한 오류로 끝낸다.
2. `score --truth <truth.json> --found <파일>`
   `--found` 는 사실 대장(jsonl/json), `audit/universe.md` 표, 또는 이름이 한 줄에 하나씩 든 텍스트. 재현율(찾은 정답 수/정답 수), 놓친 정답 목록, 정답지에 없는 추가 대상 목록을 JSON 으로 출력한다. 이름 매칭은 `exa_eval.py` 의 정규화 방식을 재사용한다(import 가 깔끔하면 import, 아니면 그 함수만 옮기고 출처 주석).
   한계 주석 필수: 정답지가 이 스킬 자신의 과거 결과이므로 이 점수는 **회귀 감지용**이지 절대 재현율이 아니다.
3. `failed-urls <조사폴더>... --out urls/<이름>.txt`
   과거 조사의 `audit/fetch-log.jsonl` 에서 **최종적으로 실패한** URL(같은 URL 의 마지막 확보 상태가 fail)을 중복 없이 뽑는다. 도메인별 건수를 stderr 에 요약.
4. `replay <urls.txt> --out runs/<이름>.json [--limit N] [--no-third-party]`
   각 URL 에 `codes/market-deep-research/scripts/fetch.py` 의 `fetch()` 를 1회 호출하고 `{url, status, tier(성공한 계층), reason, seconds}` 를 모은다. 요약: ok/partial/fail 건수와 비율, 계층별 성공 건수, 도메인별 실패 건수. **같은 호스트 연속 요청 사이 2초 대기**, URL 당 1회, 재시도 없음.
   - `fetch.py` 는 다른 워커가 고치는 중이므로 `fetch()` 의 공개 반환 키(`status`, `trace`, `final_url`)만 쓰고 내부 함수에 기대지 않는다. `--no-third-party` 는 환경변수 `MDR_NO_THIRD_PARTY=1` 을 세팅해 넘긴다(RF1 이 구현).
   - `--fetch-script <경로>` 로 다른 사본의 `fetch.py` 를 지정할 수 있게 한다(수정 전 코드와 비교용). 지정한 스크립트의 폴더를 `sys.path` 맨 앞에 넣어 import.
   - 작업 폴더 오염 방지: `fetch.py` 가 현재 폴더에 `audit/` 를 쓰므로 `replay` 는 `tempfile.TemporaryDirectory()` 로 이동해 실행한다.
5. `compare <runs/a.json> <runs/b.json>` — 두 실행의 ok/partial/fail 전환표(fail→ok 몇 건 등)와 URL 목록. 30줄 이내 함수.
6. `.gitignore`: `truth/`, `urls/`, `runs/` 를 통째로 제외한다. **과거 조사의 대상 이름과 URL 은 고객 조사 내용일 수 있어 git 에 넣지 않는다.**
7. `README.md`(40줄 이내): 무엇을 재는지, 명령 4개의 복붙 예시, 점수의 한계.
8. 자가점검: `python recall_eval.py demo` — 임시 폴더에 합성 대장·합성 fetch-log 를 만들어 build-truth·score·failed-urls·compare 를 assert 로 검증(네트워크 없음). replay 는 `fetch` 를 스텁으로 바꿔 요약 집계만 검증.

## 실제 실행 (도구를 만든 뒤 1회)
- a4 보고에 나온 조사 중 **3건 이상**에 `build-truth` 와 `failed-urls` 를 돌려 `truth/`·`urls/` 를 만든다. 조사 폴더는 읽기만 한다.
- `replay` 는 **돌리지 않는다**(코디네이터가 수정 전·후 코드로 직접 돌린다). 만든 URL 목록의 건수와 도메인 분포만 보고한다.

## 일부러 안 하는 것 (만들지 말 것)
- LLM 심판 채점, 사실(수치) 단위 재현율, 대시보드·HTML 보고서, 새 의존성.

## 검증 (전부 통과해야 완료)
```bash
cd _planning/recall-eval
python recall_eval.py demo
git -C ../.. status --short _planning/recall-eval   # truth/ urls/ runs/ 가 목록에 나오면 안 됨
```

## 제약
- `git commit`·`git stash`·`git checkout` 금지(워크트리 공유). `.fablize/goals.py` 실행 금지.
- 과거 조사 폴더의 어떤 파일도 수정·이동·삭제하지 않는다. 보고에는 집계 수치만 쓰고 대상 실명은 옮기지 않는다.
- 주석·문서·출력 문구는 한국어, 식별자는 영어. 표준 라이브러리만.
- 모르는 것은 추측하지 말고 `orca orchestration ask`. 완료 보고에는 만든 파일, demo 마지막 줄, truth·urls 파일별 건수를 적는다.
