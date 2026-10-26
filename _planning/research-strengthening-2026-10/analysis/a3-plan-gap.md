# A3 계획 반영도 · Exa 평가 교훈 보고

기준: 저장소 F:/Claude/skills/market-deep-research, 브랜치 feat/purpose-modules, 2026-10-13. 읽기 전용 분석. 네트워크 호출 없음.
표기: [확인] = 파일/커밋에서 직접 봄, [추정] = 내 해석.

## 0. 먼저 알아둘 것

`_planning/enhancement-directions.md` 는 2026-07-22 작성본이다. 그룹 A~F, H 는 그 뒤 v3 로 이미 코드와 문서에 들어갔다. 이 문서 본문은 아직 "후보 카탈로그" 상태라서, 읽으면 미착수로 오해한다 [확인]. 미커밋 변경 20줄은 §I(Exa 벤치마크 결론)뿐이다.

## 1. 그룹 A~I 상태표

| 그룹 | 제안 한 줄 | 상태 | 근거 |
|---|---|---|---|
| A | 단일 웨이브를 확장·수렴 루프로 | 부분 (문서+파서만, 루프 구동 코드 없음) | SKILL.md:48, 71-75 에 [E] 단계, 종료조건(축별 잔여 리드 0 / 연속 2웨이브 무신규 / 깊이캡 기본 3회·12명). `join_workers.py:148-169` 가 EXPAND·DEAD END 를 파싱하고 fingerprint 로 dedup, `:200-201` 에 `empty_expand_wave`. 후속 워커를 스폰하는 코드는 없고 팀리드(LLM)가 수행한다. `expansion-log.md` 는 `skill_paths.py:97` 이 경로만 안다. gates.py 에 수렴 검사 없음 [확인] |
| B | 반박검색 + claim-graph | 반영됨 (가장 강하게 코드화) | SKILL.md:88-91 [Bx]. `facts_db.py:223-225` 가 반박 발견 시 confirmed 거부. `verify_facts.py:622,727` 이 observer_group·observed_at/valid_at 검사. v4 본문 사용 high-risk 는 독립그룹 2·반박·기본소스·시간증거 미충족 시 FAIL (verification-gates.md:36-38). `facts-schema.json:70-101` 에 필드 [확인] |
| C | fetch Phase0 API·4계층 검증·WAF 정찰 | 반영됨 (Phase0 는 "기회적 사용" 수준) | `fetch.py` `validate_body`(ok/partial/challenge/empty), `CHALLENGE_MARKERS:45`, `ROUTES:64`. source-ladder.md:17-30 Phase0, :59-72 4계층·WAF 정찰. Phase0 MCP(opendart·KOSIS·KIPRIS) 호출은 오케스트레이터가 세션에 있으면 쓰는 방식이고 코드 배선은 없다 (extract-recipes.md:33). `preflight.py` 는 MCP 를 "런타임 확인 필요"로만 표시 [확인] |
| D | 세션 저널 세트 | 부분 (문서 규칙만, 기계 강제 없음) | SKILL.md:46,68 intent-diff 개시, :89 verification-economics, report-format.md:71 목록. `skill_paths.py:97` 경로 헬퍼만. 저널 파일 존재를 검사하는 게이트는 못 찾음 [확인]. visual-first.md:42 는 "gates.py 가 강제하지 않는다"고 명시 |
| E | observed_at/valid_at 분리 + 상태변경 추적 | 부분 | 스키마 필드와 G3 FAIL 조건은 있음 (위 B 근거). `cause-disappearance.md` 는 경로 언급만 있고 절차·게이트는 못 찾음. report-format.md:17 8부 "상태 변화·주의"는 서식 규정 [확인] |
| F | 워커 마커 + 읽기전용 | 반영됨 | agent-briefs.md:16-31 (CLAIMS/EXPAND/FIGURES 필수, 없으면 `없음`), SKILL.md:73 워커는 `_research/<agent>/` 에만 기록. `join_workers.py` 가 섹션·JSONL 전건 검증, verdict ok/blocked/invalid. 8/21 카운슬의 C3 (마커 파서 부재) 가 해소됨 [확인] |
| G1 | CloakBrowser 위장 Chromium | 미착수 | 코드·문서에서 못 찾음 (grep cloak 0건) |
| G2 | curl_cffi impersonate 그리드 | 반영됨 (축소판) | `fetch.py:41` `IMPERSONATE_GRID=["chrome","safari","chrome110"]`, `:58` 모바일 `safari180_ios`. 계획의 "TLS×UA×Referer×Playwright 전수 격자"보다 작다 [확인] |
| G3 | 쿠키 추출·복호화 | 미착수 | `extract_cookies.py` 없음. 정책선(본인 세션만)은 source-ladder.md:81 에 명시 |
| G4 | agent-reach 플랫폼 리더 | 미착수 (의도적 제외) | source-ladder.md:77-79 "시장조사 범위 밖이라 의도적 제외: yt-dlp, X/Twitter, Reddit, GitHub·HN·arXiv 전용 API". extract-recipes.md 에 recipe 문서만 있고 yt-dlp 는 SOFT 의존성으로만 점검 |
| G5 | 계산·상충 실행코드 검증 | 반영됨 | `verify_calculations.py`(154줄), `facts_db.py:181-186` 가 호출, SKILL.md `[G5c]`. 렌더 신선도 검증은 선반영 완료 (render_pdf unlink) |
| H | 11부 표준목차 | 반영됨 | report-format.md:8-17 표, SKILL.md:96 [3] 11부 표준목차. 조사유형별 변형 report-format.md:50 |
| I | Exa 벤치마크 결론 | 결론만 기록, 구현 없음 | 코드·문서에서 exa 언급 0건 [확인]. 조건부 착수("두 번째 실측에서 recall 이득 재현 시", enhancement-directions.md:209) |

선반영 4건(캡처 강제, find→scroll_to, render 무결성, codex-image)은 문서 말미 표 기준으로 모두 "반영됨"이고, 내가 본 범위에서 모순은 없다.

## 2. 조사(수집) 능력에 직접 해당하는 항목과 미착수 이유

| 항목 | 수집 능력과의 관계 | 미착수·부분인 이유가 문서에 있나 |
|---|---|---|
| A 확장·수렴 루프 | 재현율의 핵심 장치 | 루프 구동이 자동화되지 않은 이유는 문서에 없음. 팀리드 수행으로 두는 설계로 보임 [추정]. 깊이캡 근거(BM 실측 3건이 5~6웨이브/30~40명)는 research-plan.md 에 적혀 있음 |
| C Phase0·WAF 정찰 | 접근 성공률 | 기회적 사용이라고 명시 (유료 무의존 유지). 이유 기재됨 |
| G1·G3 (위장 브라우저·쿠키) | 강방어 사이트 접근 | 이유가 한 줄도 없음. enhancement-directions.md:134 는 "전량 이식"을 말했지만 v3 에서 G2·G5 만 들어갔고 G1·G3·G4 가 왜 빠졌는지는 plan 문서에 기록이 없다. G4 는 source-ladder.md:77 에 사유 있음 |
| 검색 계층(search.py) | 후보 발굴 | 계획 그룹에 없음. 아래 §5 참조 |
| I Exa 후보 확장기 | 후보 발굴 재현율 | 이유 기재됨: 1회 실행, Ultra 미시험, 채점기 교차 리뷰 미완. 그러나 2차 실행이 이미 있다 (§3) |

결론: 조사 능력에서 실제 격차가 큰 곳은 "후보를 넓게 찾는 단계"다. 계획의 A(리드 확장)는 워커가 이미 찾은 단서를 파고드는 방식이어서, 첫 웨이브가 못 본 영역은 못 메운다. 이 문제를 직접 겨냥한 항목은 I 뿐이고 구현되지 않았다 [추정].

## 3. Exa Agent 평가 (runs/ 에 2회 실행분이 모두 있음, 미완 아님)

runs/ 는 `.gitignore` 로 git 제외(`exa-eval/.gitignore`)지만 로컬에는 있다 [확인]. enhancement-directions.md §I 는 1차만 기록하고 2차 결과는 아직 반영하지 않았다.

| 항목 | 1차 20260928-233622 | 2차 20260928-235139 |
|---|---|---|
| 질문 | question_v1 (산문형, 3각도 요약) | question.md (v2: 포함/제외/증거기준/종료조건 명시, up to 60 items) |
| maxItems | 요청에 없음 | 60 |
| 후보 수 | 39 (oss 23, commercial 12, dataset 4) | 56 (oss 30, commercial 18, dataset 6, other 2) |
| 재현율 (정답 12건, 채점기 기준) | 3/12 = 0.25 | 5/12 = 0.417 |
| 재현율 (Upstage 오매칭 제외) | 2/12 | 4/12 |
| secondary 6건 | 1/6 (PaddleOCR) | 0/6 |
| 새 후보 (미검증) | 35 | 51 |
| 인용 링크 생존 | 46/49 (93.9%) | 66/68 (97.1%) |
| 비용 | $0.4084 (에이전트 $0.3004 + 검색 $0.108) | $0.7088 (에이전트 $0.5168 + 검색 $0.192) |
| 시간 | 408초 (약 6.8분) | 254초 (약 4.2분) |
| 검색 횟수 | 22 | 38 |

맞춘 것: 1차 Donut·CLOVA OCR·Upstage(오매칭). 2차 CORD·Donut·Receipt-OCR-Pipeline(F012)·CLOVA OCR·Upstage(오매칭).
Upstage 오매칭: 정답지의 Upstage 는 상용 문서 API 로 보이는데, Exa 는 `UpstageAILab/upstage-ai-final-ocr1` (한국어 영수증 텍스트검출 데이터셋 저장소)를 냈고 채점기가 이름 별칭으로 맞다고 쳤다 [확인: 두 report 의 매칭 행 URL].

### Exa 가 찾고 mdr 이 놓친 것 (정답지에 없던 것, 전부 미검증)
- 한국어 영수증 자원: KORIE(벤치마크), HumynLabs Korean Receipts Dataset, 한국어 영수증 텍스트검출 가중치(wchoi189 PAN-ResNet18), BatiAI batisee, Corepin(2원/장 공개가격), Eagle Doc(한국어 명시).
- Azure Document Intelligence 영수증 모델의 한국어 공식 지원 (두 실행 모두). enhancement-directions §I 가 "mdr 이 부재로 판정한 영역"이라 적은 부분이다.
- C 각도(스키마 검증·산술 검증·검토 UI) 후보가 2차에서 크게 늘었다: docket, DocLens, receipt-to-voucher-demo, CogniClaim, expense-autopilot, receipt-ai-scanner 등. docket·Receiptory·ocr-to-structured-json·extraction-pipeline·tinvois-parser 는 두 실행에 모두 나와 수렴 신호다 [확인, 두 report 대조].
- 상용 API 폭: 1차 12개, 2차 18개 (Tabscanner, Nanonets, Asprise, Microblink, Cloudmersive, Docsumo, Base64 등). 가격은 2차에서 더 많이 공개값으로 채워짐.

### mdr 만 찾은 것 (Exa 두 번 다 놓침)
Receipt Wrangler (F005), TaxHacker (F006), instructor (F008), invoice2data (F001), hovduc/ocr-invoice (F007), mocharil/OCR-Gemini (F014). 두 실행 공통으로 놓친 정답은 6건 + Google Cloud Vision(F004, 2차 질문의 제외 규칙과 충돌, 아래) 이다. Receipt Wrangler·TaxHacker 는 enhancement-directions §I 가 "우리 결론의 핵심 근거"라 부른 항목인데, 2차 질문이 "self-hosted expense/receipt-management apps"를 명시했는데도 못 찾았다 [확인].
기능이 비슷한 대체 후보는 2차에서 나옴 (Receiptory, BudgetLens, CogniClaim 등). 같은 항목을 찾은 것은 아니다.

### 평가 방법의 한계
1. 정답지가 mdr 자신의 결과물이다 [확인: README, ground_truth.json]. 재현율은 "mdr 과 얼마나 같은가"이지 "실제 지형을 얼마나 덮었나"가 아니다. 정답지에 없는 Exa 후보 51건의 정밀도·유용성은 측정되지 않았다. 반대로 Exa 가 더 많이 찾았어도 점수에 안 잡힌다.
2. 2차 질문의 제외 규칙이 정답지 항목을 구조적으로 배제한다 [추정, 내 해석]. question.md 는 "generic OCR engines with no receipt-specific feature"와 "invoice-only tools with no receipt support"를 제외한다. 정답지의 Google Cloud Vision(F004)은 전자에, invoice2data(F001)는 후자에 걸릴 소지가 있다. 이 둘은 2차에서 감점 요인이 아닌 설계상 상한 제약일 수 있다.
3. 질문이 1차와 2차에서 동시에 바뀌었다 (질문 v2 + maxItems). 개선분이 질문 때문인지 상한 때문인지 분리할 수 없다. 단일 실행이므로 우연 가능성도 있다 (§I 가 이미 인정).
4. 채점은 이름·URL 별칭 매칭이다. 오매칭(Upstage)이 이미 한 건 났다. `WEAK_ALIASES` 로 흔한 낱말 오탐은 막았지만 의미 오매칭은 못 잡는다. 정답지 ID 에 F010·F013 이 비어 있다 (제거 사유는 확인 못 함).
5. 채점기 교차 리뷰 미완 (§I: sonnet 칸 grok 도구 한도 350 < 449).
6. "인용 링크 생존"은 링크가 열리는지만 본다. 인용이 주장을 뒷받침하는지(내용 일치)는 검사 안 함. mdr 의 원문 재열람 기준과 동일 선상이 아니다.
7. 단일 도메인(영수증 OCR, 소프트웨어 도구 목록) 하나. 시장규모·딜·기관 실사 같은 수치 중심 조사에서의 성능은 시험되지 않았다.
8. Ultra 모드 미시험. 비용은 auto 모드 기준.

교훈: ① Exa 는 "넓게 후보를 모으는 일"에서 싸고 빠르다 ($0.4~0.7, 4~7분). 한국어 자원처럼 mdr 이 "없다"고 단정했던 영역에서 후보를 냈다. ② 질문을 구조화(각도·제외·증거기준·종료조건)하고 상한을 두면 재현율과 후보 수가 같이 올랐다. 이 개선은 mdr 의 워커 브리프에도 이식할 만하다 [추정]. ③ 단독 사용 시 mdr 의 핵심 근거 일부를 놓친다 (Receipt Wrangler·TaxHacker). 후보는 증거가 아니므로 G2 재검증을 통과시켜야 한다. ④ 두 실행에서 반복해 나온 후보(docket 등)는 수렴 신호로 우선순위를 줄 수 있다.

## 4. v4(a4cd7f3..202aa12, 2026-10-08)가 조사 단계에 더하는 부담

범위: 커밋 15c3f78 (코어 + mdr-hwpx), 202aa12 (README). 코어 변경 11개 파일, 테스트 2개 신설.

| v4 요소 | 수집 엔진에 걸리는 새 부담 | 근거 |
|---|---|---|
| reader-goal (G0 최선행, `research-plan.md` §0) | 조사 질문이 "핵심 메시지 가설"에서 파생됨. 워커는 스폰 첫 줄 `0. 독자·목표`를 받고, 가설을 입증/기각할 근거를 찾아야 한다. 반증 탐색이 수집 단계의 의무가 된다 (Fails-if 가 촉발되면 메시지 교체). 반증을 찾는 능력은 검색 재현율에 직결 | reader-goal.md 운용 규칙 1-2, SKILL.md:63-68 |
| 9부 반박 근거 | "2차 독자의 첫 반박에 답하는 근거(실패 사례·업계 회의론)"를 찾아야 한다. 못 찾으면 '반박 근거 미발견'으로 기록. 부정적 정보는 검색 엔진이 가장 약한 영역 [추정] | reader-goal.md G4 독자 테스트 2 |
| visual-first | 수치 데이터는 그림이 기본. 시계열은 3시점 이상, 항목 비교는 3~20개 같은 최소 데이터량이 필요하다. 수집 단계에서 시계열·전수 비교표 형태로 모아야 하고, 단일 시점 수치만 모으면 그림이 안 된다. 값은 confirmed fact 에서만 | visual-first.md §1, §3 |
| image-research / 원문 도판 우선 | 원문 도판 → 캡처 → 자작 순서. 워커가 `## FIGURES`(원문 도판 위치·캡션)를 반환해야 한다. 완성 인포그래픽 탐색이 수집 부담 | SKILL.md:74, :97 |
| competitive-positioning (조사 웨이브 4개) | 경쟁 조사가 핵심이면 대안 4유형(현상유지·기존방식·직접경쟁·간접대체) 전부 행으로 채워야 한다. 못 찾은 칸은 "서로 다른 검색식 3회 이상 후에야 미확인 확정". 국내 후보 우선 탐색, 제품 단위 식별자, 허가·가격 셀마다 시간증거. 의료기기·IVD 는 MFDS·FDA·ClinicalTrials·HIRA·조달청·KIPRIS·NTIS 등 규제·공공 DB 다수가 1차 근거원 | competitive-positioning.md §1, §3, §6 |
| 웨이브 구조 | 경쟁 조사는 4웨이브(식별 → 항목 채우기 → 진입경로·구매구조 → 신흥·반증). 깊이캡 기본 3회/12명을 넘기기 쉽다. research-plan 이 BM·사업화 실측 5~6웨이브/30~40명을 안내 | competitive-positioning.md §3, research-plan.md |
| 문서 쪽 | 동적 DB·로그인 필요 DB 는 캡처 가능 여부를 사전 점검, 불가하면 "미확인" (정책선). 대량 `risk:high` 지정은 금지(셀 수십 개 high 화 금지) | competitive-positioning.md §2 |

종합: v4 는 수집 요구를 "찾은 사실의 검증"에서 "무엇을 어디서 찾아야 하는지가 독자 목표에서 정해지고, 반증과 부재를 능동적으로 입증"하는 쪽으로 넓혔다. 이 요구는 검색 재현율과 부정적 증거 탐색에 의존하는데, 그 하부 엔진(search.py)은 v2 때 구조 그대로다 (§5).

## 5. 계획 문서에 없지만 리뷰·평가에 반복해 나오는 조사 단계 문제

1. 검색 계층이 사실상 DDG 단층이다 [확인 + 추정]. 8/21 카운슬(grok 렌즈)이 SearXNG 공개 풀 5/5 JSON 실패를 BLOCKER 로 보고했다 (`council-2026-08-21/review-grok.md:32-54`, SYNTHESIS.md:24). 현재 `assets/searx-instances.json` 의 `_updated` 는 여전히 2026-07-22 이고 같은 5개 인스턴스이며, `search.py` 에서 `health_path` 를 읽는 코드를 못 찾았다. 8/21 이후 search.py 변경은 2A(SSRF 가드) 뿐이다 (`git log -- search.py`). 이번에 라이브 재측정은 하지 않았으므로 "여전히 실패"는 추정이다. 이 문제는 enhancement-directions 의 A~I 어디에도 없다. 코어가 "에이전트는 내장 WebSearch 와 병행, 검색 완전성 미보장"에 의존한다 (search.py 헤더, source-ladder.md:9).
2. 검색 유형이 web/news/academic(arXiv)/filing(SEC EDGAR) 뿐이다 (`curated-sources.json` type_backends). 특허·논문(국내)·공공 DB 는 세션의 MCP 에 기회적으로 의존하며 코드가 모른다.
3. 재현율을 재는 장치가 없다. Exa 평가가 처음이고, mdr 자신의 누락률은 측정된 적이 없다. 정답지가 mdr 결과라 mdr 재현율은 정의상 12/12 이다.
4. 마커·EXPAND 규율은 있지만 첫 웨이브 설계가 약하면 확장도 약하다. 축 3~5개를 사용자가 승인하는 구조 (research-plan.md 확정 절차)라서, 축 밖 영역은 EXPAND 에 오르지 않는다. Exa 가 찾은 "한국어 영수증 데이터셋"은 이 구조에서는 축 정의에 따라 아예 조사 대상이 아니었을 수 있다 [추정].
5. 컨텍스트 규모 문제 (8/21 claude 렌즈 C?): fact 상한 없음, 압축 후 재진입 절차 부재. 조사량이 늘면 악화될 항목이다 [확인: SYNTHESIS.md:35 "규모 설계 부재"; 현재 해소 여부는 못 확인].
6. 반복해 나온 수집 스택 약점: 파생본(Jina/Wayback/OGP) 처리, WebFetch 요약을 재확인으로 쓰는 실수(SKILL.md:85 에 규칙화됨). 이 계열은 대부분 2A·2B 배치로 닫힘.
7. bd 열린 과제 2건(RR3-02 한국어 조사 붙은 수치, RR3-03 띄어 쓴 원화)은 검증 쪽이며 수집과 무관 [확인].

## 6. 남은 격차 우선순위 (조사 능력 중심)

1. 후보 확장 단계 (Exa 연동 또는 동등물). 1차·2차 모두 mdr 이 놓친 영역에서 후보를 냈다. 선결: 재현성 확인용 세 번째 도메인 실측과 후보 수준 정밀도 측정 (Exa 후보 51건 중 G2 통과 수). §I 의 착수 조건은 "두 번째 실측에서 재현"이며, 영수증 OCR 은 이미 두 실행이 있으므로 새 도메인이 필요하다.
2. 검색 백엔드 건강 점검과 복구. SearXNG 풀 실효성 재측정, 죽었으면 코어에서 제외하거나 자가호스트, G0 에 검색 계층 상태를 기록. 하부가 약하면 v4 의 반증·부재 입증 요구가 공회전한다.
3. 확장·수렴 루프의 기계 지원. join_workers 의 dedup·무신규 판정은 있으니, `expansion-log.md` 집계와 수렴 판정을 스크립트로 내리고 gates 에서 확인하면 팀리드 수행의 편차를 줄인다 (선택 사항, 비용 중간).
4. 질문 구조화 템플릿의 워커 브리프 이식. Exa 2차에서 구조화한 질문(각도·제외·증거기준·종료조건)이 재현율을 올린 단서가 있다 (질문과 상한이 동시에 바뀐 점은 한계). agent-briefs.md 스폰 계약에 "종료조건: 상한 N건 내에서 각도별 소진"을 넣는 작은 변경. 효과는 분리 실험 후 판단.
5. mdr 재현율 측정 장치. 독립 정답지(mdr 결과가 아닌 것)로 누락률을 재거나, 최소한 Exa 후보를 G2 로 재검증해 mdr 이 놓친 사실 건수를 센다.
6. G1·G3 (위장 브라우저, 쿠키) 는 문서에 미착수 사유가 없으므로 "채택 / 명시적 보류" 중 하나로 결정 기록만 남기면 된다. 구현 우선순위는 낮음 (유지비, 정책선 부담).
7. enhancement-directions.md 갱신. A~F·H 를 "반영됨"으로, §I 에 2차 실행을 추가. 안 하면 다른 분석이 같은 일을 중복 착수한다.

## 7. 확인하지 못한 것

- search.py 의 현재 라이브 동작 (네트워크 금지로 미측정). SearXNG 5/5 실패 여부는 8/21 기록 + 코드/자산 무변경에 근거한 추정.
- 정답지의 원본 질문과 mdr 의 원래 조사 결과물(2026-07-22 영수증 OCR 조사)은 저장소에서 못 찾음. Exa 질문이 원 조사 질문과 얼마나 같은지 모름.
- F010·F013 이 정답지에서 빠진 이유.
- council-2026-09-19 의 batch3·review 문서는 목록과 키워드 grep 만 봤다. 조사 단계(재현율) 관련 지적은 그 grep 에서 나오지 않았고 검증 정밀도 중심이다.
- 테스트 통과 여부 (실행하지 않음). B·F 의 "반영됨"은 코드·문서 존재 기준이다.
