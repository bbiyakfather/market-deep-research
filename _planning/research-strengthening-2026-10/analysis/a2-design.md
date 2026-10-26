# a2-design: 조사 설계·오케스트레이션 약점 분석 (정적 분석)

경로 약칭: MDR = codes/market-deep-research. 확인 = 파일에서 직접 읽음, 추정 = 그 위에서의 해석.

## 1. 현재 흐름 도식

```
G0 독자·목표 §0 + research-plan(축 3~5, 축별 충분조건, 깊이캡) + intent-diff   [사용자 승인, SKILL.md:62-69]
 -> [1] 워커 팬아웃 (sonnet, 축/대상 분할, 에이전트별 _research/<agent>/)       [SKILL.md:71-74]
      입력: 스폰메시지 0~4 (agent-briefs.md:8-17)
      출력: EVIDENCE JSONL / CLAIMS / EXPAND / FIGURES / 인사이트 / 요약 (또는 BLOCKED)
 -> [E] 확장수렴 루프: 리드 집계(expansion-log.md, 수작업) -> 후속 워커 -> 종료(잔여리드 0 | 2웨이브 무신규 | 깊이캡)  [SKILL.md:75]
 -> G1 join_workers.py(형식검증만) -> facts_db 등재, 무출처 즉시 discarded       [SKILL.md:77-80]
 -> [2] 팀리드 전건 재열람 verify_event(by=lead)
 -> [Bx] high-risk 반박검색/독립그룹/기본소스/시간증거
 -> G2 캡처 -> [3] 집필 -> G3 -> G5c -> [4] -> [4b] -> G4 -> G5
복귀: G4 intent-diff gap -> [E] 로 (gap 난 축만 재스폰)  [verification-gates.md:126-128]
      파일변경 -> G3 / 독자테스트 실패 -> [3]
```
루프는 있다. 단 "조사 -> 재열람 -> 반박" 구간(G1~Bx)에서 부족분이 조사로 되돌아가는 정식 경로는 없다. 복귀는 G4 한 곳뿐이다.

## 2. 질문별 답

### Q1 단일 웨이브 여부 / 종료 기준
- 확장수렴 루프가 있고 종료 기준이 명시돼 있다(SKILL.md:75). 단 이 루프는 워커가 스스로 신고한 `EXPAND` 리드가 소진되는지만 본다. 리드 신고는 워커 재량이므로 "워커가 못 본 것"은 종료 판정에 들어오지 않는다(추정, 구조상).
- "축별 충분조건"은 필드로만 존재하고 형식이 없다. 예시가 "1차출처 확보·N건 교차확인 등"(research-plan.md:29) 한 줄뿐이다. 이를 판정하는 코드·체크리스트·기록 서식이 없다. SKILL.md:75는 충분조건과 수렴조건을 "별개"라고 선을 긋지만, 충분조건 달성 여부를 누가 언제 어떤 산출물로 판정하는지는 어디에도 없다. grep 결과 scripts에 "충분조건" 참조가 없다(확인).
- 이 판정이 안 되면 루프 종료 3조건 중 "잔여 리드 0"이 사실상 유일한 의미 있는 종료인데, 이는 충분성이 아니라 워커의 신고 소진이다.

### Q2 완전성(recall)
- 대상 열거 단계가 없다. 기관·기업 조사는 "대상 2~3개/에이전트"로 분할(SKILL.md:72)하지만 그 대상 목록이 어디서 오는지(누가, 어떤 질의로 전체 모집단을 열거했는지)는 규정이 없다. entity-identity.md는 이미 정해진 후보의 동일성 확인만 한다(entity-identity.md:18-21).
- 경쟁·포지셔닝만 예외로 "대안 4유형 전부 행으로"(competitive-positioning.md:7-14)와 "서로 다른 검색식 3회 이상 후 미확인 확정"(:16)이 있다. 이 규칙이 다른 조사유형(시장 플레이어, 정책, 기술요소)에는 일반화돼 있지 않다.
- 포화 판정: report-format.md:18 "포화가 못 답한 것"과 :10 "커버리지 선언"이 보고서 쪽에 있으나, 포화를 어떻게 측정하는지(신규 사실 비율, 신규 출처 도메인 수 등)는 정의가 없다. "포화"라는 단어는 사용되지만 조작적 정의가 없음(확인).
- 워커 간 중복: 같은 claim_key면 `add_evidence`로 병합(verification-gates.md:25), 리드 중복은 지문 비교(join_workers.py:32-34, 186-197). 이것은 사후 dedup이다. 사전 분할은 MECE 권고뿐(research-plan.md:62-63)이고 중복 수집 방지 장치(워커별 제외 목록, 이미 수집된 claim_key 목록 전달)는 스폰 계약에 없다(agent-briefs.md:8-17).
- 공백: 축 사이 경계(교차 주제), 어느 워커도 안 맡은 대상을 찾는 장치 없음. "교차검증1" 워커가 SKILL.md:72에 언급되나 임무 정의 없음.
- 교차 출처 대조: high-risk에 한해 독립 관찰그룹 2 이상(SKILL.md:90). normal 사실은 단일 출처 허용 구조.

### Q3 워커 지시문
- 구체적인 부분: 반환 마커 형식, 철칙(원문 미확인 폐기, 귀속처, verbatim, W접두 ID), high-risk COUNTER 1회 의무(agent-briefs.md:70-72), BLOCKED 규약(:79-81).
- 약한 부분:
  - 질의 설계 지침 없음. 프로토콜은 "search.py/fetch.py 사다리 + WebSearch 병행"(agent-briefs.md:13-15) 한 줄. 질의 변형 수, 언어 확장, 동의어·약어·상호 변경, `site:`/`filetype:` 사용 지침은 mdr-search/SKILL.md:30("쿼리 3~6개 변형")에만 있고 보고서 모드 워커 브리프에는 없다(두 문서 불일치). "검색 완전성 미보장"(mdr-search/SKILL.md:30, source-ladder.md:7)만 경고하고 보완책은 없다.
  - 반대 증거 탐색은 high-risk 한정(agent-briefs.md:72). normal 주장·경쟁 우위·"유일/최초" 외 일반 서술에는 반증 의무 없음. 반증 검색도 "1회"로 하한만 있고 질의 다양성 기준이 없다(competitive-positioning의 3회 규칙과 불일치).
  - 출처 계층 준수: 워커 브리프에는 source-ladder 사다리(fetch 폴백)만 있고, "어떤 종류의 출처를 우선 찾는가"(1차 공시 > 2차 집계 > 보도) 지시는 grade.authority와 철칙 한 줄(agent-briefs.md:77 "2차 집계 DB는 1차 교차 전까지 pending")이 전부. 출처 우선순위 탐색 지시 없음.
  - **"없음" vs "못 찾음" 구분 결함 (핵심)**: 
    - `CLAIMS`/`EVIDENCE`가 비면 `없음`(agent-briefs.md:21). 이것은 "탐색했으나 결과 0"과 "탐색 못 함/접근 불가"를 구분하지 않는다. FIGURES만 "섹션 누락과 탐색했으나 없음은 다른 상태"라고 명시(:58-59).
    - `negative_search`는 evidence_type enum에 있으나(facts-schema.json:10) 이를 사용하는 코드가 scripts에 없다(grep: negative_search 0건, 확인). fact 단위 증거라서 "대상 X의 Y를 찾았으나 없음"을 기록하려면 가짜 fact(claim)를 만들어야 하는 구조(추정).
    - 접근 불가(403, 로그인, 유료벽)를 구조화해 반환하는 마커가 없다. fetch.py 로그는 audit/에 남지만 워커 반환 형식에는 FAILED_SOURCES 같은 섹션이 없다. EXPAND의 DEAD END는 "소진된 리드"이지 원인(없음/차단/미도달)을 구분하지 않는다(agent-briefs.md:33, join_workers.py:152-159는 DEAD END를 단순 목록으로 보관만 하고 수렴 계산에 쓰지 않음).
    - 반환 요약(`수집 N건·등급분포·폐기 리드 M건`, agent-briefs.md:48)에 시도한 질의 수·소스 수·실패 수가 없다.

### Q4 사실 스키마
- 있는 것: 시점(as_of, observed_at, valid_at, last_seen), 상충 상태(`disputed`/`superseded` status), 4차원 등급, counter_search(query/result), claim_key.
- 없는 것(facts-schema.json 전체 확인):
  - 수집 질의/경로(어떤 query·검색엔진·사다리 계층으로 얻었나): fact/evidence 어디에도 없음. evidence에 `http_status`, `archived_url`만(:119-121, 124).
  - 상충 사실 연결: `disputed`는 status 값이지만 "무엇과 상충하는가"를 가리키는 필드(conflicts_with, claim_key 그룹 외)가 없다. 같은 claim_key 안에서 값이 다르면 암묵적으로 묶일 뿐(추정). 병기 서식은 보고서 쪽에서만 정의(report-format.md:22-27).
  - 미해결 질문/조사 공백: fact 단위로 "이 사실에서 파생된 확인 필요 항목" 필드 없음. EXPAND 리드는 마커 텍스트이고 스키마 밖.
  - 수집자(workers) 식별: 워커가 `W3-F012` 임시 ID(agent-briefs.md:75)만 쓰고 최종 fact에 worker/wave 필드 없음(스키마 확인). 어느 웨이브에서 나왔는지 추적 불가 -> 웨이브별 신규율(포화 측정)을 계산할 수 없음.
  - 조사 축(AXIS) 필드: EXPAND와 FIGURES는 AXIS를 가지나(agent-briefs.md:32, 38) fact에는 없다. 축별 충분조건 판정과 3부 챕터 커버리지를 fact 수준에서 집계할 수 없음.
  - 신뢰도 점수: 4차원 grade만(A~D). 의도적 선택일 수 있음(competitive-positioning.md:71이 "H/M/L 신뢰도" 비채택을 명시). 따라서 결함이라기보다 설계 결정.

### Q5 검증 게이트 탈락 사실의 처리
- 탈락 경로 3종:
  1. 무출처 -> 즉시 `discarded` (SKILL.md:79). 재조사 트리거 없음.
  2. [2] 재열람 불일치 -> 문서에 명시된 처리 없음. 상태 enum의 `disputed`/`discarded`로 보내는 것까지만 규정(verification-gates.md:198-200, "단순 저등급 폐기 금지 — disputed/superseded 우선"). 폐기·강등된 fact가 어느 축의 어느 조사 질문을 비우는지 확인해 후속 워커를 보내는 단계 없음.
  3. [Bx] 불통과 -> `disputed`/Unresolved "기권이 정답, audit 기록"(verification-gates.md:42). 즉 기권으로 종결. 부족한 독립그룹·기본소스를 찾으러 가는 지시가 없다.
- 유일한 되먹임: G4의 intent-diff gap -> [E] 복귀(verification-gates.md:126-128). 이는 보고서 완성 후, 최후 단계다. [2]/[Bx] 탈락이 [E]로 돌아가는 경로는 문서에 없음(확인). 결과적으로 high-risk 사실이 독립 2그룹을 못 채우면 G3 FAIL(SKILL.md:90) -> 그제야 사람이 판단해 수동으로 조사 재개(추정).
- facts_db.set_status는 status와 discard_reason만 갱신(facts_db.py:468-483). "재조사 필요" 플래그·사유 코드가 없다.

### Q6 문서 간 모순·중복·모호
(아래 약점 목록 W9~W13 참조)

## 3. 약점 목록 (심각도·근거·영향)

| ID | 심각도 | 약점 | 근거 | 영향 |
|---|---|---|---|---|
| W1 | 상 | 탈락/기권 사실이 조사로 되돌아가는 폐루프 부재. 복귀는 G4 한 곳 | SKILL.md:79, verification-gates.md:42, 126-128; facts_db.py:468-483 | 독립그룹·기본소스 부족으로 high-risk가 `disputed` 처리되면 보고서에서 구멍으로 남음. 재조사는 사람 판단 |
| W2 | 상 | "못 찾음/접근 불가/없음" 3분 보고 양식 없음. negative_search는 enum만 있고 코드·반환 마커 연결이 없음 | agent-briefs.md:21, 33, 48; facts-schema.json:10; scripts에 negative_search 0건 | 팀리드가 "해당 사실 없음"과 "워커가 못 도달함"을 구분 못 해, 공백이 `미확인`으로 뭉개짐. 재조사 대상 선별 불가 |
| W3 | 상 | 축별 충분조건이 서식·판정 절차·산출물 없이 필드명만 존재. 루프 종료는 워커 자기신고 EXPAND 소진에 의존 | research-plan.md:29, 39; SKILL.md:75; join_workers.py:198-201(무신규=EXPAND 기준) | 조사 깊이가 팀리드 감에 의존(문서가 스스로 지목한 위험, research-plan.md:29). 워커가 리드를 안 쓰면 조기 수렴 |
| W4 | 상 | 대상(모집단) 열거·포화 판정 장치 없음. 포화는 용어만 있고 지표 정의 없음 | SKILL.md:72, entity-identity.md:18-21, report-format.md:10, 18 | "N개 대상 비교" 조사에서 대상 누락 시 어떤 게이트도 못 잡음(G3~G5는 이미 등재된 fact만 검사) |
| W5 | 중상 | 질의 설계 지침이 워커 브리프에 없음(mdr-search에만 "3~6개 변형"). 반증 탐색은 high-risk 한정·1회 하한 | agent-briefs.md:13-15, 72; mdr-search/SKILL.md:30; competitive-positioning.md:16 | 워커마다 질의 폭이 다름 -> 재현성·recall 편차. 한국어·영어·약어·이전 상호 확장이 보장 안 됨 |
| W6 | 중상 | 스키마에 수집 질의·웨이브·축·워커 필드 없음, 상충 대상 연결 필드 없음 | facts-schema.json:19-111 전체 | 포화·충분조건을 fact 데이터로 계산 불가. 상충 쌍 추적은 claim_key 암묵 의존 |
| W7 | 중 | 사전 중복 방지 없음(스폰 시 이미 수집된 claim_key/출처 목록 미전달) | agent-briefs.md:8-17; 사후 dedup만 verification-gates.md:25, join_workers.py:186-197 | 웨이브가 늘수록 같은 출처 재수집, 토큰·재열람 비용 증가 |
| W8 | 중 | join_workers.py는 형식 검증기이며 의미 판정(커버리지, 축 정합, 중복 사실)은 안 함. 워커 fact는 pending 고정만 강제 | join_workers.py:66-169, 107-108 | G1이 품질 게이트처럼 읽히나 실제론 파서. "invalid"만 재요청 대상이고 내용 부족은 못 잡음 |
| W9 | 중 | 충분조건/수렴조건/깊이캡이 3개 개념으로 나뉘고 상호 우선순위가 불명확. "깊이캡 도달 시 연장 문의"는 있으나 충분조건 미달 상태의 처리는 없음 | SKILL.md:75; research-plan.md:30-31 | 캡 도달 + 충분조건 미달일 때 "미달 선언 후 진행" 규칙 부재 -> 보고서 2부 커버리지 선언에 반영 근거가 없음 |
| W10 | 중 | 깊이캡 기본값 3회/12명과 실측 5~6웨이브/30~40명이 문서 안에서 병존 | SKILL.md:75 vs research-plan.md:31 | 기본값이 현실과 어긋난다고 문서가 인정. 초안에서 사람이 매번 덮어써야 함 |
| W11 | 중 | 축 이름 사용 규칙 충돌 소지: agent-briefs.md:11은 새 축 이름 금지, 그러나 EXPAND에 `미분류`가 허용되어 우회 경로가 됨. 처리 규칙은 있으나(:50-52) join_workers는 AXIS 값을 승인 축 목록과 대조하지 않음 | agent-briefs.md:11, 32, 50-52; join_workers.py:152-157 | 오타·변형 축 이름이 expansion-log에서 별개 축으로 집계될 수 있음(추정) |
| W12 | 하중 | "교차검증1" 워커(기술동향 축분할) 임무·반환 방식이 정의 안 됨 | SKILL.md:72 | 가장 필요한 recall 보완 워커가 방치. 워커마다 다르게 해석 |
| W13 | 하중 | 서로 다른 문서에서 "미확인 확정" 기준이 다름(경쟁 3회 검색식 vs 일반 규칙 없음), COUNTER도 1회 vs 3회 | agent-briefs.md:72 vs competitive-positioning.md:16 | 같은 "못 찾음"의 기준이 영역별로 상이 |
| W14 | 하 | 무신규 웨이브는 ok 워커 EXPAND만으로 판정, blocked 비율이 높은 웨이브도 "무신규"로 수렴될 수 있음(blocked는 제외만 되고 재시도 규칙 없음) | research-plan.md:39; join_workers.py:185-201 | BLOCKED 워커가 많은 웨이브에서 잘못된 수렴(추정) |

## 4. 강화안

| # | 안 | 종류 | 크기 | 효과 |
|---|---|---|---|---|
| S1 | 워커 반환에 `## COVERAGE` 섹션 추가: 시도 질의 목록(언어 포함)·열람 소스 수·`NOT_FOUND`(탐색했으나 없음)/`UNREACHABLE`(차단·로그인·유료벽, URL+사유)/`NOT_ATTEMPTED` 3분류. agent-briefs.md 마커와 join_workers.py SECTIONS에 반영 | 문서+코드 | 문서 ~25줄, 코드 ~40줄(SECTIONS, 파서, 테스트) | W2, W5 해소의 기반. 빈 결과와 접근 불가 분리 |
| S2 | [2]/[Bx] 탈락 되먹임: 탈락 사유 코드(`no_primary`, `single_group`, `reread_mismatch`, `no_source`)를 `audit/gap-log.md`(또는 jsonl)에 기록하고 사유별로 후속 워커 TASK 템플릿 제공. 규칙: "탈락 N건 이상 또는 해당 축 핵심 fact 탈락이면 [E]에 편입". SKILL.md [2]/[Bx]와 verification-gates.md에 복귀 규칙 추가 | 문서(코드는 선택: 사유 코드 필드) | 문서 ~20줄 | W1 해소. G4까지 기다리지 않음 |
| S3 | 축별 충분조건 서식 고정: `축 / 필수 사실 목록(체크리스트) / 최소 독립출처 수 / 1차 출처 종류 / 포화 기준(연속 2웨이브 신규 사실 0 또는 신규 도메인 0)`을 research-plan.md 표로 정의하고 expansion-log.md에 웨이브별 달성표 작성. 종료 판정은 충분조건 달성표 AND 잔여 리드 0 | 문서 | ~30줄 | W3, W4, W9 |
| S4 | 모집단 열거 워커 의무화: 기관·플레이어·경쟁 대상이 있는 조사는 "0웨이브: 대상 열거" 단계(서로 다른 소스 유형 3종, 예: 공시 DB·협회 명단·특허 출원인·뉴스)를 두고 열거 결과를 `audit/universe.md`에 기록. 이후 분할은 이 목록 기준. G4에서 목록 대비 미조사 대상 역검사 | 문서(+선택: universe 대비 entity_id 커버리지 스크립트 ~60줄) | 문서 ~30줄, 코드 선택 | W4 핵심 해소 |
| S5 | 워커 브리프에 질의 설계 블록 추가: 최소 질의 수, 한/영 병행, 약어·이전 상호·제품명 변형, `site:`/`filetype:` 사용, 질의 로그를 S1 COVERAGE에 기록. 반증 탐색을 high-risk 외 "우열·유일·최초·순위 서술"까지 확대하고 "서로 다른 검색식 3회" 기준을 competitive-positioning에서 agent-briefs 공통 철칙으로 승격 | 문서 | ~20줄 | W5, W13 |
| S6 | 스키마에 선택 필드 추가: `discovery`{query, wave, worker, axis}, `conflicts_with`[F-ID], `open_questions`[string]. 모두 optional로 v4 호환 유지. facts_db 검증은 형식만. 웨이브별 신규 fact 수·축별 fact 수 집계 스크립트 | 스키마+코드 | 스키마 ~15줄, 집계 스크립트 ~50줄 | W6, 포화 지표 계산 기반 |
| S7 | 스폰 메시지에 `5. 기수집`(이미 등재된 claim_key/주요 URL 목록과 축별 부족 항목) 추가. join_workers에 AXIS 값을 research-plan 축 목록과 대조해 불일치 경고 | 문서+코드 | 문서 ~10줄, 코드 ~20줄 | W7, W11 |
| S8 | "교차검증" 워커 임무 정의: 다른 워커의 CLAIMS 중 단일 출처 normal 주장 표본을 독립 질의로 재탐색하고 결과를 COUNTER/COVERAGE로 반환 | 문서 | ~15줄 | W12 |

우선순위(효과 대비 비용): S1 > S3 > S2 > S4 > S5 > S6 > S7 > S8. S1은 S2·S5의 선행 기반(탈락 사유와 질의 로그를 담을 곳).

## 5. 확인하지 못한 것
- scripts/gates.py, verify_facts.py, search.py, fetch.py 내부(조사 단계 로직 포함 여부)는 읽지 않음. 따라서 "코드에 없다"는 주장은 facts_db.py·join_workers.py·manifest.py 및 scripts 전체 grep(negative_search, 충분조건)에 한정.
- manifest.py는 함수 목록 수준만 확인. 조사 단계 상태 추적은 없고 봉인·해시 검증 중심으로 보임(추정).
- claim-review.md, evidence-capture.md, extract-recipes.md는 본문 미열람(grep 발췌만).
- tests/test_adversarial.py:1265-1354가 "충분조건·수렴조건" 문구 존재를 문서 회귀 테스트로 지킴(발췌 확인) -> 문서 수정 시 해당 테스트 갱신 필요(추정, 실행 금지라 미확인).
- 실제 조사 실측(어느 웨이브에서 몇 건이 새로 나왔는지) 데이터는 못 봄.
