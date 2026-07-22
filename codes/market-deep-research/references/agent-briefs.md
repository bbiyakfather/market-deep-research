# agent-briefs — 서브에이전트 프롬프트·반환 마커·철칙

조사원(explorer) 서브에이전트는 **sonnet·background**로 팬아웃한다. 워커는 **읽기전용**:
자기 `_research/<agent>/` 임시폴더의 raw 만 쓰고, 공식 대장(facts.jsonl 등)은 **오케스트레이터
(팀리드)만** 기록한다. 워커는 아래 마커로 반환하고, 팀리드가 파싱해 등재·확장한다.

## 스폰 메시지 계약
```
1. TASK: <역할> + <축 이름> (한 줄)
2. 범위: <대상/기간/지역/조사종료기준>
3. 프로토콜: search.py/fetch.py 사다리 사용 + 내장 WebSearch 병행. 원문 확보 후 evidence 스키마로 구조화.
4. 반환: 아래 4개 마커 블록(JSONL + CLAIMS + EXPAND + 인사이트/요약)
```

## 반환 마커 (팀리드가 기계 파싱)
```
## EVIDENCE (JSONL)
{"fact": {...}, "evidence": [{...}]}      # assets/facts-schema.json 준수. status=pending 로.

## CLAIMS
- CLAIM: <주장> — RISK: high|normal — SOURCES: <도메인1, 도메인2>
  — COUNTER: <반박검색 시도 결과 or 없음> — PRIMARY: <기본소스 URL or 없음>

## EXPAND
- LEAD: <미발견 리드> — WHY: <중요성> — ANGLE: <검색어/접근>
- DEAD END: <소진된 리드>

## 인사이트
- <사실>: 근거 F-ID. <추론>: "추론" 명시(사실과 구분).

## 요약
- 수집 N건 · 등급분포 · 폐기 리드 M건
```

## 철칙 (절대)
- **원문 미확인 수치는 폐기**(추정 금지). 무출처 주장은 CLAIM 에 올리되 SOURCES 없음으로 표시 → 팀리드가 `discarded`.
- **딜 규모 ≠ 실수취액**. 총액·순액·분할지급 구분해 `definition` 에 명시.
- **귀속처 명시**: 누가 발표/집계했는지(`source_role`: 원출처/재인용/보도자료). 같은 보도자료 재전재는 독립 아님 → 같은 `observer_group`.
- **high-risk 주장**(시장규모·성장률·딜규모·순위)은 COUNTER(반박검색) 1회를 반드시 시도.
- 표는 page/row/col, API 는 endpoint/param/JSON 해시로 locator 결박.
- 장기 워커는 `WORKING: <작업>-<단계>` 정기 전송, `BLOCKED: <이유>` 즉시 전송.
