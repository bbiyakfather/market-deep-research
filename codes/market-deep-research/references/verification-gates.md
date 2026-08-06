# verification-gates — G0~G5 상세 · 4차원 등급 · claim-graph · 환산

## 4차원 등급 (grade, 각 A~D) — 단일등급 금지
| 차원 | 의미 | A | D |
|---|---|---|---|
| authority | 출처 권위 | 1차 공시·표준·규제기관 | 익명 블로그·미검증 |
| independence | 독립성 | 이해무관 복수 독립집계 | 당사자 자기발표만 |
| directness | 직접성 | 원데이터·원문 직접 | 3차 재인용·요약 |
| recency | 최신성 | 조사시점 기준 최신 | 수년 경과·갱신됨 |

## 게이트 영수증 · run-ledger 【v4-L】
게이트 정본은 `assets/gates.json`(11종, 순서 고정): G0 → PLAN → G1 → LV([2] 팀리드 재검증) →
BX → G2(증빙) → G3 → G5C → RENDER([4]+[4b]) → G4 → G5. 작업 단계 [1] 팬아웃·[E] 확장수렴·
[3] 집필은 게이트가 아니므로 영수증 대상 아님(그 결과는 G1/G3 영수증에 담김).
- **영수증**: 게이트 통과 주장은 `scripts/run_ledger.py`(스크립트 정본) `checkpoint <gate>
  --verdict PASS|WATCH|BLOCK --evidence "..."` 가 `audit/run-ledger.jsonl` 에 append 하는
  레코드로만 성립. verdict 는 `PASS|WATCH|BLOCK` 3값 고정 — 리뷰 레인 원어(CLEAR/OKAY/
  APPROVE 등)는 `lane_verdicts: [{lane, token}]` 에 원어 보존, 게이트 verdict 환산은 팀리드가 기록.
- **신선도는 fact 단위**: watches 에 facts 가 든 게이트는 영수증의 `fact_hashes`(claim_key→sha)
  와 현재 대장을 대조 — 변경 0 이면 fresh, 있으면 partial_stale + 변경 claim_key 목록만
  재검증(전건 재검증 강제 아님 — 아래 델타 라체트와 정합). report_md/report_pdf 는 파일 해시
  전체 실효(렌더 산출물은 원자 단위가 파일). `generation` 카운터·대조 규칙의 구현 정본은
  `run_ledger.py` — 이 문서는 절차만 서술한다.
- **join phase 어휘**(G1 checkpoint `phase`): `complete | awaiting_verification | failed |
  cancelled | blocked_partial`. 다음 게이트 checkpoint 거부는 **failed·cancelled 만**.
  awaiting_verification 은 [2] 진입이 정상 경로. blocked_partial(human_blocked 레인 잔존)은
  진행 허용하되 G5 완료 선언 시 보고서 9부 한계 고지 필수.
- **완료 선언 규칙**: "보고서 완성" = run-ledger 에 11개 게이트 전부 신선 PASS 또는
  WATCH(BLOCK 0). WATCH 가 하나라도 있으면 9부 한계 고지 필수. 진행 기억·산문 선언은
  증거가 아니다.
- **기계 하한(floor) 【v7】**: 팀리드가 PASS 를 요청해도 스크립트가 강제로 낮추는 사유 —
  `floor(b)` confirmed 인데 증거 참조가 없거나 대상이 실재하지 않음(댕글링) · `floor(c)` 대장
  스키마 위반 · `floor(d)` **LV 한정**, 직전 LV 영수증 이후 내용이 바뀐 confirmed fact 에 lead
  재검증이 늘지 않음. (블로커 문자열이 그대로 영수증에 남으므로 이 태그로 grep 하면 된다.)
  `floor(d)`가 없으면 "수치를 고치고 재열람 없이 checkpoint 만 다시 찍어 신선도 복귀"가 성립해 fact
  단위 신선도 모델 자체가 무의미해진다. 기준선은 영수증에 실린 claim_key 별 재검증 횟수다 —
  타임스탬프는 초 단위라 같은 초에 벌어진 수정과 재검증을 구분하지 못한다.
  ⚠ "evidence.jsonl 이 없으면 (c)를 WATCH 로 완화"하던 규칙은 **폐지**했다. 완화가 보호하던
  구 스키마 폴더가 실은 테스트 샘플이라 지킬 실데이터가 없었고, 남은 효과는 "증거 대장을 안
  만들면 위반이 강등된다"는 우회로뿐이었다. 완화 조건이 '증거가 없음'인 것 자체가 설계 오류다.
- **산출물 부재 = 미완료(fail-closed) 【v5】**: 감시 대상 파일이 아예 없는 게이트는
  `missing_watch` 로 분리되어 완료 집계에서 빠지고, `ROSTER_REQUIRED` audit 산출물이 하나라도
  없으면 완료 선언이 불가하다. 부재를 '해시 변경 없음'으로 읽으면 아무것도 만들지 않은 run 이
  전 게이트 PASS 로 보인다(v5 실측 재현).
- **동의 기록의 한계 【v5】**: `record answer` 는 `--resolved-by` 를 명시해야 하며 기본값이
  없다. 다만 에이전트가 CLI 를 직접 호출하는 이 실행모델에서 '사용자가 쓴 답'과 '에이전트가 쓴
  user 답'은 **기계적으로 구분할 수 없다** — 이 레코드는 감사 흔적이지 인증이 아니다.
  동의가 실제로 필요한 지점에서는 대화 기록이 최종 근거다.

## G0 preflight
`python scripts/preflight.py`(HARD: python·fitz·pandoc·chrome / SOFT: curl_cffi·trafilatura·
openpyxl·yt-dlp / RUNTIME: 브라우저 MCP(agent-browser 우선)·무료 공공 MCP). 요구사항 확정(유형·범위·**축별 충분조건**·
환산옵션 OFF·출력형식·**승인 목차**) — 통과조건: `audit/research-plan.md` 존재 + 승인 기록 +
승인 목차(`references/research-plan.md` 서식) 포함, 확정 전 팬아웃 금지. 기관조사면
`entity-identity.md` 선행. `audit/intent-diff.md` 개시.

## G1 join + 수집 게이트
전 워커 완료/timeout/부분실패 처리 → raw `_research/` 보존 → `facts_db.py` 스키마 검증 등재
(위반은 제한적 재요청). **무출처 즉시 `discarded`**(audit 기록). join 결과는 G1 checkpoint
`phase`(위 join phase 어휘)로 기록.

**중복 수집의 정규 출구 【v5】**: 병렬 레인이 같은 지표를 독립 수집하는 것은 설계된 정상 동작이다.
같은 `claim_key` 는 `db.merge_evidence(fact)` 로 합류시킨다 — **값이 같을 때만** evidence 합집합,
값이 다르면 병합을 거부하고 conflict 처분 경로로 보낸다(자동 채택·유사도 자동병합 금지: 오병합은
값 위조보다 발견이 어렵다). 반환되는 `observer_groups` 는 **독립 관찰그룹 수 확인용**이다 — 같은
출처를 여러 번 담아도 그룹은 하나이며, 그래야 [Bx] 의 '독립 그룹 ≥2' 가 병합만으로 가짜 충족되지
않는다. JSONL 손편집은 원자 쓰기 경로를 우회하므로 금지.

## 동결 스냅샷 검증 코호트 【v4-V】
G1 join 후 대장을 동결(파일 sha + fact 단위 content-hash)하고, 3레인이 **같은 동결본**을
검사한다: ① 재검증([2] — 권한은 팀리드 전속) ② 반박([Bx]) ③ **정합성**(단위·연도·정의·
entity_id 스윕).
- **join before repairing**: 레인별 수리 금지 — 발견을 통합 blocker 배치로 모아 일괄 보수 후
  재동결·`generation`+1(run-ledger checkpoint 필드). 다른 해시의 동결본에 대한 verdict 는 무효.
- **2세대+ 델타 라체트**: ① 변경·신규 fact 만 재검증(`run_ledger.py status` 의 partial_stale
  목록과 정합) ② 기통과 fact 에 대한 신규 반박은 "왜 이전 패스에서 안 보였나" 정당화 필수 —
  없으면 non-blocking 강등 ③ 이전 blocker 전부 해소 시 판정 악화 금지 ④ carryover P1/P2 는
  세대 무관 블로킹 ⑤ 과잉 반박(스코프 인플레이션)은 팀리드가 리뷰 결함으로 기각 가능.
- **전건 처분**: 검증 발견은 accept(수정·강등) 또는 rebut(원문 인용 반박문) — 침묵 폐기 금지.
  처분 요약은 run-ledger `kind:disposition`(disposition: `accept|rebut`), 상세 반박문은
  `audit/bx-report.md` 처분표 절. 수정된 fact 는 게이트 영수증에서 fact 단위 실효.
  재반박 2라운드 상한 — 초과 시 disputed 강등 + 보고서 9부 한계 명기.
- **출처 충돌 typed 처분**: 모순 수치 자동 채택 금지(abort-and-report) — run-ledger
  `kind:conflict` 기록 후 `kind:disposition`(`accept_a|accept_b|synthesize_range|
  defer_to_report_caveat|reject_both` + rationale)이 있어야 해당 fact 재검증 통과.
  **미처분 충돌 잔존 시 G2 진입 불가**(fail-closed) — 여기서 G2 는 아래 **증빙 게이트**를
  말한다.
- **모순 트리거 4종**:
  | 트리거 | 처리 |
  |---|---|
  | A 출처 상호 모순 | `kind:conflict` → typed 처분 |
  | B 단위·기간·정의 불일치 | 정합성 레인, claim_key 분리 |
  | C 주장만 있고 근거 없음 | 등급 하향·discard 후보 |
  | D 신규 범위 발견 | [E] 확장수렴 리드로 회송 |
  새 증거가 기존 fact 를 뒤집으면 삭제 대신 disputed→supersede 체인 — "모순된 fact 를 절대
  삭제하지 않는다". 구분은 `dispute_kind: refuted|definition_conflict|unresolved`(additive)
  로 기록, supersede 체인은 refuted 에만 요구.
- **bx-report 양식**(`audit/bx-report.md`): 머리에 심각도 집계(P1×n…)+Top-N → 발견마다
  `P1~P3 — <분류>: 한 줄 — F###` 앵커 + 메커니즘(evidence 인용 결박) + Suggestion → 말미
  Healthy Areas + Scope examined. P1=수치·출처 불일치(본문 진입 차단) · P2=증거 약함 ·
  P3=표현·범위.

## [2] 팀리드 재검증(전건) + [Bx] claim-graph
- 전건: 보고서 진입 후보 모든 fact 를 팀리드가 원문 재열람 → `add_verify_event(by="lead")`.
  verifier 단독 confirm 금지. confirmed = ≥1 evidence + lead verify_event(facts_db 강제).
- **claim-graph 게이트(risk=high 만)**: ① ≥2 **독립 관찰그룹**(`observer_group` 상이, 재전재 제외)
  ② **반례 쿼리 소진**(계획 시점 반례 쿼리 — research-plan 항목 스키마의 `반례 쿼리` — 전건
  소진 + `counter_search.found_stronger_refutation=false`, 더 강한 반박 없음; `verify_facts.py`
  검사는 warning 유지) ③ **기본소스**(`primary_source_ref`)
  ④ **시간증거**(`observed_at`+`valid_at`). 불통과 → `disputed`/Unresolved(기권이 정답, audit 기록).
  판단 근거·순서는 `audit/verification-economics.md`(오류비용 vs 검증비용 vs 잔여위험).

## G2 증빙 게이트
confirmed 전건 `source_capture`(capture_pdf 또는 브라우저 MCP 실화면 — 계층·recipe 는
`evidence-capture.md`). htmlbox 재구성은 **불인정**.
high-risk 핵심수치는 캡처 필수(`verify_facts.py` 가 실재 검사). 실재 검사는 파일 유무만 보므로
**백지 캡처는 걸러내지 못한다** — 저장된 PNG 팀리드 육안 확인이 게이트의 일부다.

## G3 verify_facts + manifest (실패 0)
`verify_facts.py <report.md> <work_dir> [--conversion] [--plan <research-plan.md>]`:
본문/부록 분리(주석 `<!-- FACTSHEET:APPENDIX -->` 우선, 없으면 '## 부록' 헤딩 최후 출현) ·
본문을 문장·표행 세그먼트로 나눠 수치↔(Fxxx) 1:1 최근접 결박(태그 하나가 줄 전체를 면제하지
않음) · 무태그 숫자 차단 · (Fxxx) 존재+confirmed+값·**단위** 의미대조(Decimal 스케일·차원,
불일치 시 `[단위불일치]`/`[값불일치]`) · evidence 필수필드 · text_quote verbatim ·
high-risk 캡처 실재 · **목차 기계검사**(`--plan` 미지정 시 `audit/research-plan.md` 자동탐지,
그마저 없으면 생략 — 계획 파일 없는 기존 조사는 이 검사만으로 FAIL 하지 않음). →
`manifest.py build`(해시 고정 — 이 시점은 report.pdf 생성 전이라
렌더 산출물은 [4] 이후 재봉인에서 추가됨).

## G5c 실행코드 검증(계산·상충) 【v4-N】
자체포함 스크립트 실행 → stdout → `audit/verify-<slug>.md`(CONFIRMED/REFUTED/PARTIAL).
- **대상 선별**: `evidence.type=calculation` 존재 OR fact `derivation=computed`. 대상인데
  `verify-<slug>.md` 없으면 G5 에서 지적.
- **verify-<slug>.md 표준 템플릿** — 계산 하나 = 기록 하나:
  ```
  입력: <fact_id> · <값>
  스크립트 전문: <자체포함 스크립트>
  stdout: <verbatim>
  판정: CONFIRMED|REFUTED|PARTIAL — 근거 1줄
  ```
- **Evidence discipline 3규칙**: ① 가리킬 수 있는 실행 출력에만 근거 — 직접 계산해 보지
  않은 지표·결론 보고 금지 ② 계산 실패는 원인을 고쳐 계속 — 은폐 금지(실패 시 해당 fact
  미검증 강등) ③ shows(데이터가 보여주는 것) vs infer(추론) 구분, 가정 명시.
- **honest unknown**: 캡처·수집이 성공 여부 불명으로 끝나면 `unknown` 정직 기록(실패 위장
  금지) — 파일 존재 검증으로 finalize, 불가면 재시도 후보. "기록 부재 = 알 수 없음이지
  미실행이 아니다."

## G4 preview → G5 최종 무결성
report.pdf 생성 후 **재봉인**(`manifest.py build` 재실행 — [G3] 항목은 보존한 채 report.pdf 등
렌더 산출물 해시를 추가) → `preview_pdf.py` 육안검증 + **intent-diff 축별 대조**
(`audit/intent-diff.md` 개시분의 축별 "참이어야 하는가" 목록을 실제 보고서 발견과 대조 —
축마다 gap 유무 판정, 결과를 `audit/intent-diff.md` 에 추기) → PDF F태그·링크·캡처 수 재검사
+ `manifest.py verify`(재봉인 기준 — 신규 파일도 실패로 판정).
BM 렌즈를 쓴 조사면 추가 2항목(`references/business-frameworks.md`): ① L6 부하가정의
Fails if 촉발 여부 대조(촉발분은 9부 기재) ② 블록 간 정합 3문항(불일치는 7부 후보).
**복귀 규칙**: 파일 변경 검출 시 G3 복귀. intent-diff gap(개시분 대비 누락 발견) 검출 시
**[E] 확장수렴 루프로 복귀**(gap 난 축만 후속 워커 재스폰 — 축 전건 재조사 아님).
**G4 이원화 【v4-V】**: (a) 육안검증은 `audit/g4-visual-check.md` 체크리스트 산출물로 기록
(페이지·확인 항목·결과 — 육안 블랙박스 제거). (b) **선택 레인: fresh-context 팩트체커** —
입력은 report.md + facts.jsonl + research-plan.md **만**(조사 저널·대화 서사 주입 금지:
저작 세션의 프레이밍 미공유가 목적). 반환 마지막 비공백 줄 `VERDICT: APPROVE|REQUEST_CHANGES`
고정 파싱 — 파싱 불가, 또는 미해결 P1 동반 APPROVE 는 malformed → fail-closed(불가해 응답을
APPROVE 로 매핑 금지). 팩트체커 발견은 동결 코호트의 전건 처분 루프에 물린다.

## 환산 옵션(기본 OFF)
ON 시 Decimal 검산(계산식·환율출처·기준일·종가/평균 명시), 표시 반올림 일관, 본문 영어통화단어 0.
`value.decimal` 에 검산값. 오차 표기(±)는 근거 있을 때만.

## 사용자 개입 프로토콜(asks) 【v4-A】
이 절이 ask 프로토콜의 **정본**이다(`references/research-plan.md` 는 G0·PLAN 개입 지점
목록만 참조). 기록은 run-ledger 레코드로만 — 별도 파일 없음:
```
ask    {kind, ask_id, gate_id, question, options[], recommended?, supersedes?, at}
answer {kind, ask_id, answer, resolved_by: user|timeout, at}
```
- **활성 ask 1개**: 개입 지점 중첩 시 큐잉 후 하나씩. 팀리드 권고는 `recommended` 표시만 —
  기록되는 답은 **사용자 원답만**.
- **멱등·계보**: 같은 답 재적용은 no-op, 다른 답은 conflict 기록. 재시작 후 옛 활성 ask 는
  quarantined + 새 ask_id 재발행(`supersedes` 계보) — 옛 답을 새 질문에 적용 금지.
- **이중확인**: 고비용·파괴 행동(웨이브 연장·fact 일괄 무효화·전면 재캡처)은 계획 시 허용
  클래스 합의 + 실행 시점 명시 승인 — 둘 중 하나라도 없으면 fail-closed. **파괴적 승인 자동
  합성 금지**.
- **목차 승인 = prepared→bind→activate**: join 후 보고서 단계는 prepared(목차 후보만, 본문
  보류) → 승인 기록(bind) → activate 후 집필. 재승인은 no-op.
- **알림 의도 매핑**: 게이트 통과→notify(요약만) · 승인 대기→ask(**판단에 필요한 전체 맥락
  필수** — 후보 목차 전문·예상 추가 비용; 가리면 답할 수 없다) · 게이트 실패→failed+blocker
  요약 · 중단→cancelled.

## 상태 모델
`confirmed`(검증완료) · `pending`(미검증) · `disputed`(정의차·상반 병기) · `superseded`(시계열 갱신,
`last_seen`) · `discarded`(무출처·저품질, `discard_reason`). 단순 저등급 폐기 금지 — disputed/superseded 우선.
