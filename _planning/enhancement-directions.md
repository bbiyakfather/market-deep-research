# factsheet-research 고도화 방향 메모

> 작성 2026-07-22 · 출처 벤치마크: `oh-my-openagent` v4.13.0 (insane-search / ultraresearch=ulw-research / ultimate-browsing 실제 SKILL.md 3종 정독)
> 대상: `_planning/plan-v2.md`(설계확정·구현 전) 고도화
> 성격: **방향 추천 메모(취사선택용)**. 이번 문서는 구현·설계개정이 아니라, 형일 님이 v3 반영 여부를 고르기 위한 후보 카탈로그.

## 한 줄 요약
우리 스킬(숫자마다 영수증이 붙는 증빙형 시장조사 공장)에, oh-my-openagent에서 검증된 **7군(A~F 핵심 + G 고강도 수집 인프라)**을 우리 게이트/파일에 어떻게 이식할지 정리했다. 각 항목은 `왜 / 어디에 / 얼마나 / v2 대비 diff` 4요소로 기술했고, **제외 없이 전량 수록**(고강도 인프라 G 포함)하되 유지비·정책선을 정직하게 병기했다.

---

## 0. 겹침·격차 한눈표

| 축 | 우리 v2가 이미 가진 것 | oh-my-openagent가 더 가진 것 | 이식 그룹 | 우선순위 |
|---|---|---|---|---|
| 증거 구조 | `fact`+`evidence[]`, 6증거유형, 4차원 등급, 재전재=1출처 | 독립**관찰그룹** 수렴, **반박검색(COUNTER)**, 기본소스 필수 | **B** | P0 |
| 오케스트레이션 | 축분할 1회 팬아웃 + join(G1) | **확장→수렴 루프**(EXPAND 마커·dedup·무리드 종료) | **A** | P0 |
| 수집(fetch) | 선형 사다리(curl_cffi→모바일→Jina→Wayback) | **Phase0 공식API 색인**, 4계층 성공검증, WAF 내부API 정찰 | **C** | P1 |
| 시간 | `context.as_of` + `accessed_at` | **observed_at vs valid_at** 분리, cause-disappearance | **E** | P1 |
| 감사·재현 | audit 번들(facts전수·폐기·실패·이력·manifest) | 살아있는 **세션 저널 세트**(intent-diff 등 5종) | **D** | P2 |
| 워커 반환 | 자유서술 + evidence JSONL | **마커 규율**(CLAIMS/EXPAND), 워커 읽기전용 | **F** | P2 |
| 보고서 구조 | 3중 구조 + 말미(요약·인사이트·한계) 골격 | **Executive→테마→검증→모순→간격→확장추적** 종합구조 | **H** | ★추가요청 |
| 우회 엔진 | 축소 사다리(교훈만) | **위장 브라우저·TLS 그리드·쿠키 재사용·플랫폼 리더·실행검증** | **G** | 요구#2 완결용(전량) |

**핵심 통찰**: 우리 증거모델은 이미 강하다. 격차는 ① 검증이 "존재 확인"에 머물고 **반증을 안 한다**, ② 조사가 **1회 웨이브로 끝나 완전성이 약하다**, ③ 자체 우회 스택의 **실제 엔진(G)이 비어 있어 강방어 사이트를 못 뚫는다**, 이 셋에 집중된다.

---

## P0 — 증빙형 정확성 직결 (즉효)

### B. 능동적 반박검색 + claim-graph 검증게이트  ★최고 레버리지
- **왜**: v2 stage [2]의 팀리드 재열람은 "원문에 그 수치가 **존재**하는가"만 확인한다. 그러나 증빙형 보고서의 진짜 적은 **잘 인용됐지만 틀린 수치** — 보도자료가 부풀린 값을 여러 매체가 그대로 재전재하면, 출처도 있고 verbatim도 맞지만 1차 공시와 상충한다. ultraresearch Phase 3b는 high-risk 주장에 대해 **① ≥2 독립 소스 도메인, ② ≥2 독립 관찰그룹 수렴, ③ 1회 능동 반박검색(COUNTER), ④ 기본소스(공시·표준·원데이터) 뒷받침, ⑤ 시간증거**를 통과해야만 결론에 진입시킨다. 불통과는 폐기가 아니라 `Unresolved`/`Refuted` 명시(기권이 정답).
- **어디에**:
  - `references/verification-gates.md` — G2에 **반박검색 단계** 신설(팀리드가 "이 수치가 틀렸다는 더 강한 증거는 없는가"를 1회 능동 조회).
  - `assets/facts-schema.json` — fact에 `risk:"high|normal"`, `independent_groups:[]`, `counter_search:{query,result}`, `primary_source_ref` 필드 추가.
  - `scripts/facts_db.py` — high-risk confirmed 판정에 위 5조건 검사.
  - 반박 결과 산출물은 **우리가 이미 정의한 `negative_search` 증거유형**을 그대로 재활용(신규 유형 불필요).
- **얼마나**: 中上. 스키마 필드 + 게이트 로직 + 문서. high-risk 대상만 적용해 저위험 주장 과검증 방지(위험도 태깅은 아래 D-verification-economics가 근거 제공).
- **v2 diff**: `confirmed = 1 evidence + 팀리드 재열람` → **high-risk confirmed = + 독립그룹 수렴 + 반박검색 + 기본소스 + 시간증거**. 전건 재검증(사용자 잠금)은 유지, 그 위에 high-risk 심화 레이어 추가.
- **[실증 2026-07 PEM]** 스킬 파이프라인 **G2 증빙게이트**가 `risk=="high"` 태그에만 캡처를 강제해, `[Bx]` 반박게이트 미실행 시 **캡처 0건·대표이미지 0장으로도 "완료" 통과**하던 구멍을 실측(→ `/chk-scope` 발단). **베이스 스킬에 선반영 완료**: `verify_facts.py`를 "본문 사용 confirmed 핵심수치 **전건** 캡처 강제(risk 태깅 무관) + 대표이미지 0장 FAIL + 미결박 캡처 WARN"으로 수정. B의 high-risk 심화 레이어는 이 강제 위에 얹히는 구조 — B는 "틀린 수치"를, 이 선반영은 "증빙 누락"을 각각 막는다.

### A. 단일 웨이브 → 확장·수렴 루프
- **왜**: v2 stage [1]은 축분할 후 1회 병렬 팬아웃 → G1 join으로 종료한다. 이 구조는 **완전성에 취약** — 첫 웨이브가 top-3 경쟁사 하나, 더 최신 데이터소스, 상충 연구를 통째로 놓치면 그대로 보고서로 간다(시장조사에서 주요 플레이어 누락은 실질 실패). ultraresearch는 워커가 남긴 **EXPAND 리드**(미발견 단서)를 오케스트레이터가 dedup 후 **후속 워커로 즉시 확장**, "연속 N웨이브 무신규 리드 / 미해결 리드 0 / 깊이 상한 도달" 중 하나가 될 때까지 반복한다(수렴이 유일한 종료 기준).
- **어디에**:
  - `SKILL.md` — stage [1]과 [G1] 사이에 **확장수렴 루프** 삽입. 종료조건·깊이캡·비용캡 명시.
  - `references/agent-briefs.md` — 서브에이전트 반환에 `## EXPAND`(LEAD/WHY/ANGLE, DEAD END) 마커 추가.
  - audit 번들에 `expansion-log.md`(웨이브별 스폰 워커·획득 리드·개시/종료 리드).
- **얼마나**: 中. 오케스트레이션 로직 + 반환 스키마 + 신규 저널 1종.
- **v2 diff**: 단일 join barrier → **경계된 확장수렴 루프**. 무한 방지 위해 깊이·비용 상한과 드롭항목 로깅을 명시(원칙이 아니라 안전장치).

---

## P1 — 신뢰성·완전성

### C. fetch Phase0 공식API 색인 + 4계층 성공검증 + WAF 내부API 정찰
> ⚠ 이 항목은 **수집 규율**(어떻게 접근·판정할지)이다. 실제 우회 **엔진**(위장 브라우저·TLS 그리드·쿠키)은 아래 **Group G**에서 완전 이식한다. C와 G는 한 몸이다.
- **왜**: v2 fetch 사다리는 선형이고 성공판정이 "본문 1000자+키워드"로 느슨하다. insane-search 엔진의 규율을 이식하면 데이터 품질·성공률이 오른다.
  - **(C1) Phase0 공식·무료 API 우선(R5)**: generic fetch 전에, 소스에 공식/무료 API가 있으면 그것부터. 기보유(SEC EDGAR·arXiv·Wikipedia) + **이미 이 세션에 붙은 무료 MCP**(opendart/DART·KOSIS·KakaoMap·YouTube)를 G0 preflight에서 **감지**해 기회적 1차 소스로 활용. → 유료 무의존 원칙 유지(이들은 무료), 자체 HTTP 스택이 보장 코어.
  - **(C2) HTTP200 ≠ 성공, 4계층 검증(R2)**: ① 챌린지 마커(`Just a moment…`/`Access Denied`/DataDome), ② 비정상 크기(<3KB·WAF fingerprint), ③ 쿠키 센서(`_abck=~-1~`), ④ 성공 셀렉터 매칭. → v2의 partial/실패 판정을 이 4계층으로 정밀화.
  - **(C3) WAF 조기감지 병렬 분기(R7)**: 반복의도 조회에서 초기 2~3회가 challenge면, 백그라운드로 격자 계속 + 포어그라운드로 **playwright가 내부 `/api/`·`/graphql`·`.json` XHR을 포착 → JSON 엔드포인트 직접 호출**. 시장데이터 SPA는 마케팅 페이지만 강방어, 내부 API는 기본 방어라 고수율. → **기보유 playwright MCP** 사용, 신규 인프라 0.
  - **(C4) 그리드 전수 후 실패선언(R6)**: 부분 시도로 "차단"이라 결론짓지 말고 격자 전수 후 판정.
- **어디에**: `references/source-ladder.md`(Phase0 API 색인표·4계층 판정), `references/extract-recipes.md`(WAF 정찰 recipe), `scripts/fetch.py`(Phase0 절·판정 로직), `SKILL.md` G0(MCP 도구 감지).
- **얼마나**: 中. 대부분 recipe/문서 + 소량 로직.
- **v2 diff**: 선형 사다리 → **Phase0-우선 + 4계층 검증 + WAF 정찰**. 접근 규율 이식(엔진은 G).
- **[실증 2026-07 PEM]** IEA 스크롤리텔링·비네트광고 페이지에서 휠·PageDown·좌표 scroll_to가 목표 문단에 도달 못해 **캡처 4건 실패**(E010~E013). **베이스 스킬에 선반영 완료**: `evidence-capture.md`에 `find`(요소 텍스트→ref)→`computer.scroll_to(ref)` 우회 레시피 추가(좌표 아닌 요소 ref 기준 이동 → 광고 오버레이·가상스크롤 무관 도달). C3 WAF 정찰과 같은 "접근 규율" 계열의 캡처판 실증.

### E. 시간증거 분리 + 상태변경 추적
- **왜**: v2는 `context.as_of`(주장 기준시점) + `evidence.accessed_at`(접근시각)만 있다. ultraresearch는 **observed_at(우리가 관측한 시점)**과 **valid_at/claim_valid_at(주장이 유효한 시점)**을 분리하고, `cause-disappearance`(원인 원장)로 "한때 참이었던 것"의 소멸을 추적한다. **시장조사는 대상 상태가 변한다** — 발표됐다가 취소·지연되는 프로젝트, 갱신되는 수치(직전 PEM 수전해 프로젝트 조사가 정확한 사례). 관측/유효 시점을 섞으면 "취소된 프로젝트를 진행 중으로 보고"하는 오류가 난다.
- **어디에**: `assets/facts-schema.json`(`observed_at`·`valid_at`·`last_seen`), `references/verification-gates.md`(시점 정합 체크), audit `cause-disappearance.md`(예상 진실·이전 관측·last_seen·반박·대체원인·상태).
- **얼마나**: 小. 스키마 필드 + 게이트 체크 + 저널 1종.
- **v2 diff**: `as_of` 단일 → **관측/유효 2축 + last_seen**. 기존 `superseded`(시계열 갱신)/`disputed`(상충) 상태를 상태변경 추적으로 확장.

---

## P2 — 감사·재현성 (전체 이식)

### D. audit 번들 → ultraresearch 세션 저널 세트
- **왜**: v2 audit(facts전수·폐기목록·실패소스·검증이력·raw·manifest)는 정적 산출물 목록이다. ultraresearch의 저널은 **살아있는 감사추적 + 컨텍스트 유실 시 복구지점**이다.
- **이식 대상**:
  - `intent-diff.md` — "요청 의도가 참이라면 무엇이 참이어야 하는가" vs 실제 발견. **gap 표면화**에 강력(무엇을 아직 못 찾았는지 드러냄). G0에서 개시, G4에서 종결.
  - `expansion-log.md` — (A와 공유) 웨이브별 리드 추적.
  - `verification-economics.md` — 주장별 오류비용 vs 검증비용 vs 경로 vs 잔여위험. 우리는 전건 재검증이라 "검증 생략" 결정은 없지만, **재검증 깊이·순서 + high-risk 반박 발동 근거**로 활용 + 감사가치.
  - `observation-manifest.md`·`claim-graph.md` — **신규 파일 아님**. 우리 `evidence[]`를 관측원장으로, `facts.jsonl`을 claim-graph로 **재프레이밍**(노드=claim, 독립그룹·반박·수렴 필드는 B에서 이미 추가). 중복 회피.
- **어디에**: `references/report-format.md`(audit 절), `SKILL.md`(게이트별 저널 개시/갱신 지침).
- **얼마나**: 中. 대부분 문서/스키마 + 신규 저널 2~3종(intent-diff·verification-economics·cause-disappearance).
- **v2 diff**: 정적 audit 목록 → **살아있는 저널 세트**. facts/evidence 재프레이밍으로 신규 파일 최소화.

### F. 워커 마커 프로토콜 + 읽기전용 규율
- **왜**: v2 서브에이전트 반환은 자유서술 + JSONL이라 오케스트레이터가 파싱·확장을 자동화하기 어렵다. ultraresearch는 **구조화 마커**로 반환해 오케스트레이터가 기계적으로 저널링·확장한다. 또 워커는 **읽기전용**(저널은 오케스트레이터만 작성)이라 파일 충돌·오염을 원천 차단.
- **이식**: `## CLAIMS`(CLAIM/RISK/SOURCES/COUNTER/PRIMARY) + `## EXPAND`(LEAD/WHY/ANGLE, DEAD END) 구조화 반환. 장기 워커는 `WORKING:`/`BLOCKED:` 신호. 워커는 자기 임시폴더의 raw만 쓰고 공식 저널 미작성.
- **어디에**: `references/agent-briefs.md`(반환 스키마·철칙).
- **얼마나**: 小~中. 문서 중심.
- **v2 diff**: 자유서술 반환 → **마커 규율**. B·A의 counter/EXPAND 필드와 자연 결합.

---

## H. 보고서 목차 설계 강화 (report-format.md)  ★사용자 추가 요청

- **왜**: v2 report-format(핵심설계5)은 "3중 구조(서술→근거표→증빙캡처) + 말미(요약·인사이트·한계)"로 **골격만** 있고, **목차 계층·챕터별 필수 구성요소·조사유형별 변형**이 명시돼 있지 않다. 조사원마다·조사마다 보고서 골격이 흔들리면 "매번 다른 보고서" 문제가 목차 층위에서 재발한다. ultraresearch 종합 구조(Executive→테마별→소스순위→검증주장→모순→간격→확장추적)와 우리 증거모델·신규 게이트(B 반박검색·E 상태변화)를 결합해 **파라메트릭 표준목차**로 고정한다.

### 고객용 `report.pdf` 표준 목차 (11부)

| 부 | 제목 | 필수 구성요소 | 연결 |
|---|---|---|---|
| 0 | 표지·메타 | 주제·범위·**기준일(as_of/valid_at)**·조사팀·면책·전체 신뢰수준 배지 | E |
| 1 | Executive Summary | 핵심답변 2~3문단 + **핵심수치 카드**(최상위 지표, F태그) | — |
| 2 | 조사 개요 | 조사질문(축) · 조사종료기준 · 방법 요약 · 한계 한 줄 | A |
| 3 | 테마별 본론(축=챕터) | [서술본문: 배경→메커니즘→수치(F)→의의→⚠주의] → [근거표: 사실\|수치\|**맥락(claim_key)**\|출처\|4차원등급\|증빙] → [source_capture+캡션] | 전 게이트 |
| 4 | 시장 수치 종합 | claim_key별 지표표(값·단위·기간·정의·시나리오·등급) + 시계열/비교 차트(Mermaid·matplotlib) | E |
| 5 | 플레이어·경쟁 구도(해당 시) | 엔티티 매핑(**entity_id 결박**), 지배구조/재무(실사 시) | entity-identity |
| 6 | **검증 요약(신설)** | 삼각검증 통과 현황 · 독립그룹 수 · **반박검색 결과 요지** → 수치 신뢰 근거를 고객에게 가시화 | **B** |
| 7 | **상충·모순(강화)** | A vs B 상반 수치 · `disputed` 병기 · 정의차 해설 | **B/E** |
| 8 | **상태 변화·주의(신설)** | 취소·지연·갱신 항목 · `valid_at` 경고 | **E/cause-disappearance** |
| 9 | 한계와 반론 | 포화가 못 답한 것 · 반대 논거(근거 있을 때만, 개수 고정 없음) | A |
| 10 | 한눈 요약표 + 조사팀 인사이트 | 에이전트별 + 팀리드 코멘트(**사실/추론 구분·근거 F-ID**) | F |
| 11 | 부록 | 번호매김 소스(접근일·**아카이브 구분**)·방법론·용어정의·환산근거(ON 시) | C/G5 |

> **고객/audit 분리 유지(사용자 잠금)**: 6·7·8은 고객용엔 **요지만**. 폐기목록·실패URL·미확인의혹·반박 상세는 내부 audit 번들로(고객PDF 미노출).

### 조사유형별 목차 변형 (파라메트릭)
- **기술동향**: 3부 축 = 기술요소/성숙도/플레이어/정책 · 4부 = 기술지표(TRL·특허·성능) · 5부 = 주요 연구기관 매핑.
- **산업동향**: 3부 = 밸류체인 단계별 · 4부 = 시장규모·성장률(KOSIS·DART 결합) · 8부(규제·정책 변화) 비중↑.
- **기관·기업 실사**: 0부에 **entity-identity 결과 선고정** · 5부 = 지배구조·재무·연혁 · 6부(검증 요약) 비중↑(실사 리스크).

### 어디에 / 얼마나 / v2 diff
- **어디에**: `references/report-format.md`(표준목차 + 챕터별 필수요소 + 유형변형), `assets/style.html`(목차 앵커·신뢰수준 배지·수치카드 스타일), `SKILL.md` stage [3].
- **얼마나**: 中. 문서 중심 + style.html에 목차/배지/카드 CSS.
- **v2 diff**: 골격만 → **11부 표준목차 + 챕터별 필수 구성요소 + 조사유형별 변형 + 검증(6)·상충(7)·상태변화(8) 챕터 신설**. 신규 게이트(B·E) 산출물이 보고서에 자연 착지 → 목차 자체가 "매번 다른 보고서"를 억제.

---

## Group G — 고강도 수집·검증 인프라 (완전 이식, 제외 없음)

> **왜 별도 트랙인가**: 사용자 요구 #2 = "차단봇 우회 + extract, **유료 무의존 자체 스택**". v2의 축소 사다리는 Akamai/DataDome/Cloudflare 강방어를 못 뚫어 **자체 우회 스택이 사실상 미완성**이다. 아래 엔진들을 전량 이식해야 요구 #2가 완결된다. **전부 무료 → 유료 무의존 원칙과 무충돌.** (앞서 '경량 원칙'으로 제외했던 판단을 뒤집음 — plan-v2 156~157줄 "범위 제외"는 v3 구현 시 개정 필요.)

| ID | 인프라 | 왜(완결성) | 어디에 | v2 diff | 유지비/리스크 |
|---|---|---|---|---|---|
| **G1** | CloakBrowser (소스레벨 위장 Chromium) | webdriver 흔적 제거 실 브라우저로 봇탐지 우회, 로그인·클릭·스크린샷 | `references/chrome-stealth.md`(신규) + capture/fetch 최종 폴백 | playwright MCP 스크린샷 → 위장 브라우저 CDP 자동화 추가 | Chromium 빌드·버전핀 관리, 디스크 |
| **G2** | curl_cffi 대규모 impersonate 그리드 | TLS지문×UA×Referer×Playwright폴백 **전수 격자**(R6) | `scripts/fetch.py` 그리드 엔진 | 선형 4단 → 격자 전수(`max_attempts`) | TLS 프로파일 유지, 시도시간↑ |
| **G3** | 크로스플랫폼 쿠키 추출/복호화 (DPAPI/Keychain/libsecret) | **본인** 로그인 세션 재사용으로 인가된 자료 접근 | `scripts/extract_cookies.py`(신규) | 없음 → 신규 | OS별 복호화 분기, 보안 취급 주의 |
| **G4** | agent-reach 플랫폼 네이티브 리더 | yt-dlp/mcporter로 미디어·소셜·(중국)플랫폼 1차 API 직접 | `references/agent-reach.md`(신규) + `extract-recipes.md` | recipe 문서로만 → 실배선 | 플랫폼 API 변동 추적 |
| **G5** | Phase 3 실행코드 검증 | 계산·상충·성능 주장을 스크립트 실행→stdout→CONFIRMED/REFUTED 실증 | `scripts/verify_facts.py` + `verification-gates.md`, `verify-<slug>.md` | 재열람만 → 실행증거 | 샌드박스·재현성 관리 |

- **G5 시장조사 접점**: 시장규모=수량×ASP, CAGR, 통화환산을 **Decimal 검산 스크립트**로 돌려 stdout을 `calculation` 증거로 결박(파생수치 오류 차단). v2의 환산 Decimal 검산을 일반화.
- **[실증 2026-07 PEM]** 스킬 파이프라인 **G3/G5 무결성**의 사각: `render_pdf.py`가 잠긴(뷰어 오픈) 옛 PDF를 `size≠0`만으로 "성공" 판정해, **G4 육안검증이 옛 파일을 검증**하던 false positive를 실측. **베이스 스킬에 선반영 완료**: 렌더 전 `unlink`(잠김→명시적 에러) + Chrome stderr `utf-8` 디코딩(에러 원인 항상 노출). "정적 통과 ≠ 실제 반영"(G5의 실행증거 원칙)을 렌더 무결성에 적용한 사례. G5 실행검증 도입 시 이 교훈(출력 신선도까지 검증)을 함께 반영.
- **정책선 (유일 하드 가드레일, 완화 불가)**: 인가된 대상·본인 세션에 한함. **무단 login/CAPTCHA/paywall 우회는 합법·정책 경계라 금지.** 이 선만 지키면 위 인프라는 전부 이식 가능. (원칙이 아니라 법/정책 문제라 유지)
- **정직한 트레이드오프**: 신규 pip·바이너리(`yt-dlp`·`browser_cookie3`·Chromium 등), 유지보수 부담, OS별 분기 증가. → **완결성 vs 유지비**는 형일 님이 선택. 각 항목 유지비를 위 표에 병기했으니, 예컨대 "G1·G2·G5는 채택, G3·G4는 보류" 같은 부분 선택도 가능.

---

## 부록 — 원천 매핑 대조표

| 우리 이식 항목 | oh-my-openagent 원천 | 출처 SKILL 위치 |
|---|---|---|
| B 반박검색·claim-graph | Phase 3b 비코드 주장 잠금(≥2도메인·≥2관찰그룹·반박·기본소스·시간) | ulw-research |
| A 확장수렴 루프 | Phase 1 포화웨이브 + Phase 2 수렴(EXPAND·dedup) | ulw-research |
| C1 Phase0 API | R5 공식API 우선 + Phase 0 API 색인 | insane-search |
| C2 4계층 검증 | R2 200≠성공 4계층 | insane-search |
| C3 WAF 정찰 | R7 WAF 조기감지 병렬 분기 | insane-search |
| C4 그리드 전수 | R6 전수후 실패선언 | insane-search |
| D 저널 세트 | intent-diff/claim-graph/observation-manifest/verification-economics/cause-disappearance | ulw-research |
| E 시간증거 | observed_at/valid_at + cause-disappearance | ulw-research |
| F 마커 규율 | CLAIMS/EXPAND 마커·워커 읽기전용·제기법칙 | ulw-research |
| G1~G4 우회 엔진 | Tier1 insane-search / Tier1.5 agent-reach / Tier2 Chrome stealth + 쿠키 | ultimate-browsing |
| G5 실행검증 | Phase 3 실행코드 검증(CONFIRMED/REFUTED/PARTIAL) | ulw-research |
| H 보고서 목차 | Phase 4 종합 구조(Executive→테마→소스순위→검증→모순→간격→확장추적) + Phase 5 산출물 기본값 | ulw-research |

**사용자 잠금 결정과의 무충돌 확인**:
- 팀리드 **전건 재검증** → B는 그 위에 high-risk 심화만 얹음(완화 없음). ✅
- 고객PDF/내부audit **분리** → D 저널·G 실패로그·반박 결과는 전부 내부 audit행, 고객PDF 미노출. ✅
- 유료 API 무의존 → C의 무료 MCP·G의 무료 인프라 모두 무료. ✅

---

## 우선순위 요약 (형일 님 선택 가이드)

1. **즉시 반영 권장 (P0)**: B(반박검색), A(확장수렴) — 증빙형 정확성·완전성의 핵심. 비용 낮고 효과 큼.
2. **보고서 골격 확정 (H, ★추가요청)**: 11부 표준목차 + 조사유형별 변형. "매번 다른 보고서"를 목차 층위에서 억제하고, B·E 산출물의 착지점을 만든다. 문서 중심이라 저비용·고효과.
3. **완결성 확보 (P1 + G)**: C(수집 규율) + G(우회 엔진)는 한 몸. 요구 #2를 실제로 완성하려면 함께. G는 유지비 보고 부분 선택 가능.
4. **감사 강화 (P2)**: D·E·F — 재현성·추적성. 여유 있을 때.

> 다음 단계 후보: 이 메모에서 채택 항목을 고르면 → `plan-v2.md`를 **v3로 개정**(특히 156~157줄 "범위 제외" 갱신) → 중단됐던 shrimp `reflect_task`→`split_tasks` 재개.

### 베이스 스킬 선반영 현황 (2026-07 PEM 조사 실증분 — v3 계획 시 중복 착수 금지)
직전 PEM 조사에서 **실측된 결함·우회**는 v3를 기다리지 않고 현재 스킬 코드/문서에 이미 반영됨. v3 설계 시 아래는 "완료"로 두고 그 위에 심화만 얹는다.
- **G2 증빙게이트 강제** (§B 실증): `verify_facts.py` — 본문 핵심수치 전건 캡처 + 대표이미지 게이트. ✅ 반영
- **캡처 우회 레시피** (§C 실증): `evidence-capture.md` — find→scroll_to. ✅ 반영
- **렌더 무결성** (§Group-G G5 실증): `render_pdf.py` — 렌더 전 unlink + stderr utf-8. ✅ 반영
- **codex-image 저장 우회**(연계 스킬): `codex-image/SKILL.md` — 런타임홈 newest cp(정책훅 차단 대응). ✅ 반영 (이 메모의 factsheet 스택 범위 밖이나 도판 생성 파이프라인에서 재사용).
