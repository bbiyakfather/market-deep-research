# agent-briefs — 서브에이전트 프롬프트·반환 마커·철칙

조사원(explorer) 서브에이전트는 **sonnet·background**로 팬아웃한다. 판단이 필요 없는
기계적 후속 웨이브(확정 리드의 fetch+스키마 구조화만)는 haiku 로 내려도 된다. 워커는 **읽기전용**:
자기 `_research/<agent>/` 임시폴더의 raw 만 쓰고, 공식 대장(facts.jsonl 등)은 **오케스트레이터
(팀리드)만** 기록한다. 워커는 아래 마커로 반환하고, 팀리드가 파싱해 등재·확장한다.

## 스폰 메시지 계약
```
1. TASK: <역할> + <축 이름>(`report-format.md` 축 프리셋 참조 — 여기서 새 축 이름을 짓지 않는다, 한 줄)
2. 범위: <대상/기간/지역/축별 충분조건>
3. 프로토콜: search.py/fetch.py 사다리 사용 + 내장 WebSearch 병행(WebSearch/WebFetch 가
   도구 목록에 없으면 deferred — ToolSearch 로 먼저 로드). 원문 확보 후 evidence 스키마로 구조화.
4. 반환: 아래 마커 블록(JSONL + CLAIMS + EXPAND + FIGURES + 인사이트/요약)
```

## 반환 마커 (팀리드가 기계 파싱)
EVIDENCE/CLAIMS/EXPAND/FIGURES/인사이트/요약은 모두 필수이며 결과가 없으면 `없음`을 적는다.
부분 실패는 첫 줄 `BLOCKED: 사유`로 표시한다. 누락 섹션은 이때만 허용하며, 반환된 행의 오류는 여전히 invalid다.
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
```
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

## 철칙 (절대)
- **원문 미확인 수치는 폐기**(추정 금지). 무출처 주장은 CLAIM 에 올리되 SOURCES 없음으로 표시 → 팀리드가 `discarded`.
- **딜 규모 ≠ 실수취액**. 총액·순액·분할지급 구분해 `definition` 에 명시.
- **귀속처 명시**: 누가 발표/집계했는지(`source_role`: 원출처/재인용/보도자료). 같은 보도자료 재전재는 독립 아님 → 같은 `observer_group`.
- **high-risk 주장**(시장규모·성장률·딜규모·순위)은 COUNTER(반박검색) 1회를 반드시 시도.
- 표는 page/row/col, API 는 endpoint/param/JSON 해시로 locator 결박.
- 실행 중 팀리드로의 중간 전송 채널은 없다(서브에이전트는 완료 시 최종 보고 하나만 반환).
  막히면 질문하지 말고 `BLOCKED: <이유>` 를 최종 보고 맨 앞줄에 적고 종료한다 — 그때까지
  수집한 마커 블록은 빈손으로 버리지 말고 그대로 반환.
