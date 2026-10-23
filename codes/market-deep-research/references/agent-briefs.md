# agent-briefs — 서브에이전트 프롬프트·반환 마커·철칙

조사원(explorer) 서브에이전트는 **중간 등급 모델·background**로 팬아웃한다(Claude Code: sonnet /
Codex: `[agents].default_subagent_model`). 판단이 필요 없는 기계적 후속 웨이브(확정 리드의 fetch+스키마
구조화만)는 더 작은 모델로 내려도 된다. 워커는 **읽기전용**:
자기 `_research/<agent>/` 임시폴더의 raw 만 쓰고, 공식 대장(facts.jsonl 등)은 **오케스트레이터
(팀리드)만** 기록한다. 워커는 아래 마커로 반환하고, 팀리드가 파싱해 등재·확장한다.

## 스폰 메시지 계약
```
0. 독자·목표: <핵심 메시지 한 문장> / 관점 <주어> / 금지 서술 <목록> (`audit/intent-diff.md` 의 '현행 메시지:' 줄, 없으면 research-plan §0)
1. TASK: <역할> + <축 이름>(`report-format.md` 축 프리셋 참조 — 여기서 새 축 이름을 짓지 않는다, 한 줄)
2. 범위: <대상/기간/지역/축별 충분조건>
3. 프로토콜: search.py/fetch.py 사다리 사용 + 내장 WebSearch 병행(WebSearch/WebFetch 가
   도구 목록에 없으면 deferred — ToolSearch 로 먼저 로드). 질의는 서로 다른 각도로 3개 이상
   (대상명+항목 / 상위 개념+목록어 / 반대·실패 사례). `site:`·`filetype:pdf` 를 쓰고,
   한 검색식이 0건이면 표현을 바꿔 재시도한다. 1차 출처·코어 스택은 아래 철칙.
   원문 확보 후 evidence 스키마로 구조화.
   모든 스크립트는 `cd <WD>` 후 절대경로로 실행 — 스킬 폴더에는 아무것도 쓰지 않는다.
4. 반환: 아래 마커 블록(JSONL + CLAIMS + EXPAND + COVERAGE + FIGURES + 인사이트/요약). 질문하지 말고 가정을 적고 진행.
```

## 반환 마커 (팀리드가 기계 파싱)
EVIDENCE/CLAIMS/EXPAND/FIGURES/인사이트/요약은 모두 필수이며 결과가 없으면 `없음`을 적는다.
`## COVERAGE` 도 필수다. 구형 반환과의 호환 때문에 누락이 invalid 는 아니지만, `coverage.missing` 으로 남아 수렴 판정에서 미수렴으로 센다.
부분 실패는 첫 줄 `BLOCKED: 사유`로 표시한다. 누락 섹션은 이때만 허용하며, 반환된 행의 오류는 여전히 invalid다. COVERAGE 형식 오류 줄도 같다.
F/E-ID는 워커 파일 안에서만 유효한 잠정 ID다. `join_workers.py`의 파일별 재매핑 표(`central_id: null`)를 팀리드가 `add_fact`/`add_evidence` 반환 ID로 채우고 인사이트의 F-ID 참조까지 치환한다.
```
## EVIDENCE (JSONL)
{"fact": {...}, "evidence": [{...}]}      # assets/facts-schema.json 준수. status=pending 로.

## CLAIMS
- CLAIM: <주장> — RISK: high|normal — SOURCES: <도메인1, 도메인2>
  — COUNTER: <반박검색 시도 결과 or 없음> — PRIMARY: <기본소스 URL or 없음>

## EXPAND
- LEAD: <미발견 리드> — AXIS: <소속 축, `report-format.md` 프리셋 중 하나 또는 '미분류'> — WHY: <중요성> — ANGLE: <검색어/접근>
- DEAD END: <소진된 리드> — AXIS: <소속 축>

## FIGURES
- FIG: <도판 캡션 원문 그대로>
  WHERE: <문서명 p.12  또는  URL>
  KIND: infographic|map|chart|diagram|photo
  AXIS: <어느 조사축에 속하는가 — EXPAND 의 AXIS 와 같은 이름체계>
  WHY: <어느 단락을 이해시키는가, 한 줄>
  SOURCE_URL: <원문 URL 또는 확보한 PDF 경로>
  LICENSE_HINT: <기관 재사용 조건 단서. 모르면 unknown — 빈칸 금지>

## 인사이트
- <사실>: 근거 F-ID. <추론>: "추론" 명시(사실과 구분).

## 요약
- 수집 N건 · 등급분포 · 폐기 리드 M건

## COVERAGE
- QUERY: <검색식> — BACKEND: ddg|searx|WebSearch|MCP:이름 — RESULT: <건수>|BLOCKED|ERROR
- GAP: <대상·항목> — STATE: NOT_FOUND|UNREACHABLE|NOT_ATTEMPTED — TRIED: <시도 수> — WHY: <한 줄>
```
`NOT_FOUND`=서로 다른 검색식 3회 이상이고 백엔드가 정상 응답했는데 없음. `UNREACHABLE`=검색 백엔드 차단·오류, 또는 출처는 찾았으나 열람 실패. `search.py --json` 의 `backends[].status` 는 `ok|empty|blocked|error` 이고, **종료 코드 2(전 백엔드 실패)는 `NOT_FOUND` 가 아니라 `UNREACHABLE`**. `NOT_ATTEMPTED`=시간·범위 때문에 시도하지 않음.
`AXIS: 미분류` 리드는 팀리드가 다음 웨이브 스폰 전에 가장 가까운 기존 축으로 재분류하거나,
승인 목차에 없는 신규 축이 필요한지 사용자에게 확인한다(축 도출 체인을 워커가 임의로
우회하지 못하게 — `references/research-plan.md` 축 도출 체인 참조).

`## FIGURES` 는 원문을 읽는 동안 발견한 **완성된 도판 후보의 위치만** 신고한다. 무출처
도판은 증빙과 같은 철칙상 본문에 쓸 수 없으므로 신고하지 않고, 캡션은 검색·대조가 가능하도록
요약하지 말고 **원문 그대로(verbatim)** 적는다. 워커는 읽기전용이므로 이미지를 직접 내려받지
않으며, 실제 수확·검증은 팀리드가 `harvest_images.py` 로 수행한다. 후보가 0건이어도 섹션을
생략하지 말고 `## FIGURES` 아래 `없음`이라고 적는다 — 섹션 누락과 탐색했으나 없음은 다른
상태이기 때문이다.

EXPAND의 `AXIS`+정규화 LEAD 텍스트 지문과 같은 URL 지문은 중복 후보를 찾는 보조 신호다.
이름만 바뀐 재제출도 URL로 비교하되 완전 동등성·이전 웨이브 대비 신규 여부는 팀리드가 판단한다.

## 작성자(writer) 브리프 고정 문구 — [3] 원고 작성자 스폰 시
- `0. 독자·목표` 줄은 조사원과 같다. 추가 1줄: "수치 데이터는 그림이 기본. 표를 만들기 전에 `visual-first.md` 결정표로
  형식을 정하고, 표로 남기면 사유를 `audit/visual-decisions.json` 에 적는다."

## 철칙 (절대)
- **원문 미확인 수치는 폐기**(추정 금지). 무출처 주장은 CLAIM 에 올리되 SOURCES 없음으로 표시 → 팀리드가 `discarded`.
- **딜 규모 ≠ 실수취액**. 총액·순액·분할지급 구분해 `definition` 에 명시.
- **귀속처 명시**: 누가 발표/집계했는지(`source_role`: 원출처/재인용/보도자료). 같은 보도자료 재전재는 독립 아님 → 같은 `observer_group`.
- **high-risk 주장**(시장규모·성장률·딜규모·순위)은 COUNTER(반박검색) 1회를 반드시 시도.
- **미확인은 검색식 3회 후**: 서로 다른 검색식 3회 이상, 백엔드 정상 응답 뒤에만 미확인을 확정한다. 경쟁 칸도 이 규칙을 따른다(`competitive-positioning.md` 는 참조만). 반증 탐색은 high-risk 수치 외에 우열·유일·최초·순위 서술에도 한다.
- **1차 출처 라우팅**: 공시·재무 → DART(국내)·`search.py --type filing`(해외), 특허 → KIPRIS·특허 DB, 국가 R&D → NTIS, 통계 → KOSIS. 해당 MCP·스킬이 도구 목록에 있으면 웹 검색보다 먼저. `patents.google.com` 은 크롤링하지 않는다(과거 실패 URL 의 다수가 이 도메인) — 특허번호로 DB 도구를 조회하고, 도구 응답은 `api_response` 증거로 남긴다.
- **코어 스택**: 증거로 쓸 웹 페이지는 발견 경로(WebSearch 포함)와 무관하게 `fetch.py` 로 다시 받아 `audit/fetch-log.jsonl` 과 원본 스냅샷을 남긴다. 내장 WebFetch 만 본 페이지는 차단·실패 기록도 원본도 남지 않기 때문이다.
- **경쟁 조사 워커**: 스폰 메시지 `2. 범위` 에 제품명·모델·규제·인증코드(해당 시)·기준일을 넣고, 미확인 항목은 조회 범위를 EXPAND/negative_search 로 반환한다. 서식·근거원은 `references/competitive-positioning.md`(팀리드가 TASK 에 요점 인용).
- 표는 page/row/col, API 는 endpoint/param/JSON 해시로 locator 결박.
- **임시 ID 는 W접두**(`W3-F012`), 대장 F/E-ID 는 리드만 부여 — 워커가 대장 ID 처럼 쓴 43건 오등재 사례.
- **verbatim 은 원문 리터럴**(재구성·요약 금지 — "Royal Assent" ≠ "This bill received royal assent"), sha256 은 raw 파일 기준. 논문은 원문 첫 쪽의 제1저자·실제 학술지(교신저자·추정 학술지 금지).
- **수치에는 지표 성격(설치/제조/출하/누적)·시점·가격 성격(거래가/호가)을 함께** 기록. 등락률은 같은 출처·같은 시점만. 2차 집계 DB(IEA·시장조사기관) 값은 1차 자료 교차 전까지 `pending`.
- 실행 중 팀리드로의 중간 전송 채널은 없다(서브에이전트는 완료 시 최종 보고 하나만 반환).
  막히면 질문하지 말고 `BLOCKED: <이유>` 를 최종 보고 맨 앞줄에 적고 종료한다 — 그때까지
  수집한 마커 블록은 빈손으로 버리지 말고 그대로 반환.
