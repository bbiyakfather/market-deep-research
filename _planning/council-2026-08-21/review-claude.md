# market-deep-research 적대 리뷰 — 주 렌즈: 스킬 설계·문서 정합·오케스트레이션 (claude)

- 대상: `codes/market-deep-research/` @ main (4196c98), 읽기 전용
- 방법: SKILL.md·references 9종·scripts 15종·tests 2종 전문 열람 + 스크립트 demo 6종·`tests/test_adversarial.py`(60/60)·`tests/test_e2e.py`(PASS) 직접 실행 + 우회 경로 실증 스크립트(임시폴더) 실행. 아래 "실측"은 전부 이 세션의 도구 결과다.
- 범위 주의: `_planning/codex-review.md`(v1 리뷰) 9개 blocker 중 8개는 코드로 반영 확인(§4). 재탕하지 않고 "반영이 실제로 막는가"만 봤다.

---

## 종합 판정: **FIX-FIRST**

뼈대(증거모델·대장·해시봉인·영수증 소유권·적대 테스트)는 건전하고 문서↔CLI 인자·게이트 이름·마커 이름은 대부분 일치한다. 그러나 (a) G3가 "실패 0"을 선언하면서도 고객 PDF에 무검증 수치가 실릴 경로가 2개 실측됐고, (c) 전건 재검증·전수 캡처가 fact 수에 선형 비례하는데 상한·재진입 절차가 없어 실전 1건에서 팀리드 컨텍스트가 먼저 무너진다. 이 둘을 고치기 전엔 "같은 질문에 같은 숫자"라는 약속을 구조가 보증하지 못한다.

### 상위 5개 권고 (순위)
1. **G3 구멍 2건 봉합** — 부록 구간 검사 면제(H1)와 단위 화이트리스트 밖 수치 통과(H2). 둘 다 10줄 내 수정.
2. **규모 설계 추가** — 본문 진입 fact 상한·캡처 tier(high-risk/KPI만 실화면)·워커 JSONL 파일 반환·`gates.py status` 기반 재진입 절차(H3).
3. **[Bx] claim-graph ①독립그룹·②반박검색을 WARN→FAIL 승격**(H4) — 바로 "조사마다 달라지는" 시장규모·CAGR을 겨냥한 유일한 게이트가 현재 권고 수준.
4. **[2] 영수증을 '기록'이 아니라 '계산'으로** + lead verify_event에 재열람 산출물(sha/verbatim) 결박(M1·M2).
5. **축 프리셋 실무 정합(산업동향·실사) + 과잉 제거**(capture_web.py·이미지 검색·도판 0장 FAIL·저널 4종→2종)(M6·§5).

---

## 1. HIGH

### H1. 부록(appendix) 구간은 어떤 검사도 받지 않은 채 고객 PDF에 실린다
- **증상**: `<!-- FACTSHEET:APPENDIX -->` 이후 텍스트는 무태그·오태그·값불일치·미확정 검사 전부 면제. 11부 부록은 고객 PDF의 일부이며 "환산근거(ON 시)"처럼 수치를 담는다.
- **근거**: `scripts/verify_facts.py:81-88`(split) · `:657-665`(`body`만 검사, `_appendix` 미사용) · 자체 demo `:761-764`가 부록의 `999조원(F001)` 통과를 **정상 동작으로 단언** · `references/report-format.md:27-31`(마커 필수) · `:20`(부록=환산근거 포함).
- **실측(probe A)**: 부록에 `매출 999조원(F001), 시장규모 45억달러` → `ok=True`.
- **공격/사고 시나리오**: 작성자가 본문에서 [값불일치]를 맞은 수치를 부록 "방법론/환산근거" 문단으로 옮기면 G3 통과 → 렌더 → 고객 PDF. 악의 없이도 환율·가중치 수치가 무검증으로 나간다.
- **최소 수정**: 부록에도 `[오태그]/[미확정]/값·단위 대조`는 적용하고 **무태그 검사만 면제**(생성 전수표 때문에 만든 면제의 본래 목적만 유지). 3줄: `check_bound_numbers(appendix, facts)`를 한 번 더 호출하되 `[무태그]`는 warning으로 내리는 플래그.

### H2. 단위 화이트리스트 밖 수치는 무태그도, 오값도 통과한다
- **증상**: `$4.5B`, `$999M(F002)`, `1,234건`, `4,500명`, `1위`, `3.2배`, `€120M`, `30 kt`, `3,000만 배럴`, 한글 수사(`삼백조원`) 전부 G3 PASS.
- **근거**: `scripts/verify_facts.py:55-56`(UNIT 화이트리스트: TWh…조원…billion·million·%·원·달러·조·억) · `:62`(METRIC_NUM = 숫자 **뒤** 단위만 인식, 접두 통화기호 없음) · `:300-320`(결박된 수치만 값대조 → 인식 안 되면 대조도 없음).
- **실측(probe B/C/D/E)**: B `$4.5B` 무태그 → ok=True · C `$999M(F002)`(대장 120 USD_million) → ok=True · D 건/명/위/배/€/kt/배럴 전부 통과(유일 검출은 `120 MWp`→`120 MW`) · E 한글 수사 통과. 대조군 F `US$4.5 billion`·G `999 million(F002)`는 정상 FAIL.
- **시나리오**: 영문 시장보고서 관행(`$X.XB`, `USD Xbn`, `€XM`)과 한국 실사 관행(건·명·위·배·기·개사)이 정확히 사각지대. 기관 실사 "직원 4,500명·특허 1,234건·업계 2위"가 전부 태그 없이 나간다.
- **최소 수정**: ① 접두 통화기호 패턴 추가 `(?:US\$|\$|€|£|¥|₩)\s*NUM\s*(?:B|bn|M|mn|K|억|조)?` ② UNIT에 `건|명|개사?|기|위|배|대|배럴|kt|Mt|㎡|ha|EUR|JPY|CNY` 추가 ③ 한글 수사는 WARN(`[한글수사]`)으로 표면화. `test_adversarial.py`에 `numeral_and_energy_units_untagged` 옆에 `currency_prefix_and_count_units_untagged` 1건 추가.

### H3. 규모 설계 부재 — 전건 재검증·전수 캡처가 fact 수에 선형이며 상한·재진입 절차가 없다
- **증상**: 깊이캡(3회/12명)만 있고 **fact 수 상한이 없다**. 본문에 쓰인 **모든 숫자 fact**가 실화면 캡처 + 팀리드 육안 Read 대상. 컨텍스트 압축 후 어디서 이어가는지 SKILL.md에 절차가 없다.
- **근거**:
  - `SKILL.md:84-89` 깊이캡만 정의, fact 상한 없음.
  - 캡처 범위: 문서는 "핵심수치 필수"(`SKILL.md:48,120`, `verification-gates.md:33`)라 쓰지만 코드는 **raw가 Decimal로 파싱되는 모든 confirmed fact**(`verify_facts.py:435-442` `is_core_num or risk==high`). 문서↔코드 불일치이자 규모 폭발 원인.
  - 캡처 1건 = agent-browser 4~5 도구호출 + PNG Read(`evidence-capture.md:29-37`, 5번 육안 "생략 불가" `:45`).
  - 재검증 1건 = WebFetch(+차단 시 fetch.py) + 대조 + `add_verify_event`(`SKILL.md:98-103`).
  - 워커 반환 마커는 `## EVIDENCE (JSONL)` 인라인(`agent-briefs.md:17-18`) → 12명 × 수십 건 JSON이 팀리드 컨텍스트로 들어온다. "임시폴더에만 쓴다"(`SKILL.md:79-80`)와 모순은 아니지만 파일 반환을 명시하지 않음.
  - 재진입: `gates.py status`(`gates.py:385-409`)가 있으나 **SKILL.md 어디에도 등장하지 않음**(grep 0건). `facts.jsonl`의 `verify_events`로 진행률은 복원 가능하지만 절차가 문서화돼 있지 않다.
  - 코드 주석이 실전 대장 "confirmed 76건"을 언급(`verify_facts.py:387`) — 76건 × (재검증 2~4k 토큰 + 캡처 5호출 + 이미지 Read ~1.5k 토큰) ≈ 팀리드 컨텍스트 1~2회 압축 규모.
- **시나리오**: 기술동향 12워커 팬아웃 → 150~300 fact → [2]에서 100건쯤에 컨텍스트 압축 → 팀리드가 "어디까지 했는지"를 대장에서 역산해야 하는데 절차가 없어 중복/누락 재검증 → G2 캡처에서 다시 300×5 호출. 파이프라인이 "멈추진 않지만" 품질(육안 확인)이 먼저 무너진다.
- **최소 수정**: ① `research-plan.md` 확정 필드에 "본문 진입 fact 상한(기본 60)" 추가, 초과분은 audit 전수표로만 ② 캡처 tier: `risk=high` + 1부 KPI 카드 태그만 실화면 캡처 필수, 나머지는 `_sources/` 스냅샷(sha·local) + verbatim 으로 G2 충족 — `verify_facts.py:438` 조건을 `risk==high or fid in kpi_tags`로 ③ `agent-briefs.md` 반환 계약을 "JSONL은 `_research/<agent>/evidence.jsonl`에 쓰고 반환엔 경로+건수+CLAIMS/EXPAND/FIGURES만" ④ SKILL.md에 "재진입" 5줄: `gates.py status` → 현재 게이트 → [2]면 `facts.jsonl`에서 lead verify_event 없는 후보만 재개.

### H4. [Bx] claim-graph(고위험 수치 게이트)는 코드상 경고뿐이다
- **증상**: `risk=high` confirmed fact가 독립그룹 1개·반박검색 없음·기본소스 없음·시간증거 없음이어도 G3 PASS → PDF.
- **근거**: `verify_facts.py:385-399` 전부 `warnings.append` ("failure 승격은 다음 배치" 주석) ↔ `verification-gates.md:25-27` "불통과 → disputed" · `SKILL.md:109-111` "통과 조건(전부)". 스키마 필드는 있다(`facts-schema.json` independent_groups/counter_search/primary_source_ref).
- **시나리오**: 시장규모·CAGR·딜규모 — 정확히 "조사마다 달라지는" 수치 — 가 단일 리서치 펌 보도자료 재인용 1건으로 confirmed. 다음 조사에서 다른 펌 수치가 잡히면 값이 달라진다. 스킬의 존재 이유를 지키는 유일한 기계 게이트가 권고다.
- **최소 수정**: `risk=high ∧ confirmed ∧ used` 에 한해 ①(`independent_groups`≥2)·②(`counter_search` 존재)는 FAIL, ③④는 WARN 유지. 4줄. 기권(`disputed`)으로 남기는 길은 이미 열려 있으므로 실전 마찰은 "정직하게 disputed로 두기"뿐이다.

---

## 2. MEDIUM

### M1. 영수증 원장의 G1·[2] 는 손으로 즉시 위조 가능 → G3 선행조건이 형식에 그친다
- **근거**: `gates.py:32`(MANUAL_GATES=G0·[2]·G4) · `:38`(SCRIPT_OWNED=G3·[4b]·G5) · `:339-382`(`record_script_result` G1을 exit 0으로 누구나) · `:294-336`(`record_manual [2]`는 evidence 문자열만 요구, facts.jsonl과 무관) · `verify_facts.py:800-803`(G3가 G1·[2] 영수증을 요구).
- **실측**: 임시 작업폴더에서 `record_manual G0` → `record_script_result G1 0 "hand"` → `record_manual [2] "hand"` → `check_gate G3` = **ok=True**.
- **시나리오**: 팀리드(또는 자동화)가 [2]를 건너뛰고 영수증만 남겨도 G3·[4b]·G5가 전부 통과. 원장이 "순서·드리프트 기록"으로는 유효하나 "재검증이 있었다"의 증거는 못 된다.
- **최소 수정**: `record_manual("[2]")`에서 `facts.jsonl`을 읽어 `status∈{confirmed}` 전건에 `by=lead` 이벤트가 있는지 검사하고 `facts_db_sha256`을 영수증에 결박(이후 `require_receipt`가 sha 대조). G1 영수증은 삭제하고 G3의 `check_ledger_integrity`(이미 전행 validate)로 대체.

### M2. `by="lead"` 는 관례 — 워커 읽기전용도, 팀리드 실제 재열람도 강제되지 않는다
- **근거**: `facts_db.py:236-244`(아무 호출자나 by="lead") · `:76-82`(confirmed 조건이 lead 이벤트 존재뿐) · `agent-briefs.md:3-5`(워커 읽기전용은 문장 규율) · 스키마 `verified_by`("lead만 confirm 가능")는 validate에서 읽지 않음(dead).
- **시나리오**: sonnet 워커가 Bash로 `db.add_verify_event(fid,"lead",...)` 호출 가능. 더 현실적으로는 팀리드가 원문 미열람 상태로 루프 기록 — 시스템이 둘을 구분 못 한다.
- **최소 수정**: lead verify_event에 `{"evidence_id":..., "reread_sha256":...}` 필수(`fetch.py get`의 sha256 또는 WebFetch 인용 verbatim 해시) → `validate_fact`에서 `action=="reread"`면 필드 존재 검사. "재열람 산출물 없는 lead 이벤트"를 구조적으로 막는다.

### M3. `_images/` 가 manifest 추적 대상이 아니다 → G3 이후 도판 교체를 G5가 못 잡는다
- **근거**: `manifest.py:25-33` TRACKED에 `_images` 없음 ↔ `image-research.md:12` 도판 저장소 `_images/` ↔ `render_pdf.py` `--embed-resources`로 PDF에 내장.
- **실측**: `_images/fig.png` 봉인 후 내용 교체 → `manifest.verify` **ok=True**.
- **최소 수정**: `TRACKED`에 `("images", "_images/**/*")` 1줄 (IMAGES.md 재생성 시점을 G3 전으로 고정하거나 `IMAGES.md`만 제외).

### M4. `fetch.py get --out` 의 `local` 경로 규약이 `verify_facts`와 어긋난다
- **근거**: `fetch.py:481` `"local": str(out / ...)` = **cwd 기준·out 접두 포함·Windows 역슬래시** ↔ `verify_facts.py:426-434` `wp.root / local` → 작업폴더 밖 cwd에서 `--out research_x/_sources`로 받으면 `research_x/research_x/_sources/...` → `[스냅샷유실]` FAIL. 기본값 `_sources`(`fetch.py:571`)는 cwd 아래에 생긴다(워커 여럿이면 공유 폴더 충돌).
- **최소 수정**: `fetch.py get`에 `--work-dir` 추가, `local`을 작업폴더 상대 posix로 기록.

### M5. G5 "PDF F태그·링크·캡처 수 재검사" 를 수행하는 스크립트가 없다
- **근거**: `SKILL.md:55,153` · `verification-gates.md:60-61` ↔ `manifest.py:65-76`는 해시 대조만. TAG 정규식을 쓰는 스크립트는 `verify_facts.py`뿐이며 PDF를 읽지 않는다(grep 실측).
- **최소 수정**: `verify_facts.py --pdf report.pdf` 옵션(fitz 텍스트의 TAG 집합 == report.md 본문 TAG 집합, 내장 이미지 수 ≥ 참조 수) 또는 문서에서 "팀리드 육안"으로 격하.

### M6. 축 프리셋 2종이 한국 실무·자기 규칙과 어긋난다
- **산업동향 "통계(KOSIS·DART·KIPRIS)"**(`report-format.md:41`)는 데이터 출처이지 조사질문이 아니다 — `research-plan.md:47-56`(축=질문형·MECE)과 자기모순이고 밸류체인/해외와 겹친다.
- **기관·기업 실사 "일반현황/사업현황/재무실적"**(`report-format.md:42`)에 기술·IP 현황과 리스크·준법(신용·소송·제재·체납)이 없다 — `entity-identity.md:28-30`이 요구하는 `negative_search`(체납·제재 0건)가 들어갈 축이 없다. 국내 기업실사(투자·기술이전 상대방 실사) 관행은 리스크 장이 필수다.
- **최소 수정**: 산업동향 = 밸류체인 / 국내 시장·수급(통계 출처는 충분조건에) / 해외·정책 · 실사 = 일반현황 / 사업·기술현황 / 재무실적 / 리스크·준법. 기술동향·기술사업화(기술가치평가 실무매뉴얼 체계)는 적절.

### M7. 고객용 11부에 작업 흔적이 노출된다 — 사용자 자신의 교훈과 충돌
- **근거**: `report-format.md:19` 10부 "에이전트별+팀리드 인사이트" · 6~8부 검증 서사 ↔ `lessons.md:47-51` "작업 흔적('조사일','재검증') 본문 배제"(사용자 규칙).
- **최소 수정**: 10부는 "조사팀 인사이트"로 통합(에이전트 구분은 audit), 6부는 집계표 1개로 고정(이미 `:22-25`가 의도).

### M8. 서브에이전트 브리프가 sonnet 워커에게 실행정보를 주지 않는다
- **근거**: `agent-briefs.md:7-13` 스폰 계약 4행 — 스크립트 절대경로·WORK_DIR·`_research/<agent>/` 실제 경로·`assets/facts-schema.json` 절대경로·`sha256/accessed_at/local` 산출 방법 없음. `SKILL.md:31-32`의 "실행 위치 무관"은 스킬루트 해석 얘기지 작업폴더가 아니다.
- **시나리오**: 워커가 `python scripts/fetch.py`(상대)로 실패 → 내장 WebSearch만으로 진행 → `sha256`을 임의 문자열로 채움(스키마는 64자리 16진수만 요구) → 팀리드 재검증 부담 증가.
- **최소 수정**: 스폰 계약에 5행(SKILL_ROOT·WORK_DIR·AGENT_DIR·schema 경로·"sha256/local/accessed_at 는 `fetch.py get` 출력값 복사") 추가.

### M9. claim_key diff(재현성 검출)가 파이프라인에 미배선
- **근거**: `facts_db.py:264-282` `diff_facts` 구현 ↔ `SKILL.md` 에 호출 단계 없음(grep: intent-diff 외 0건).
- **최소 수정**: G0에 "전회 `facts.jsonl` 지정 시 G3 후 `facts_db.py diff` → 7부 상충·8부 상태변화 입력" 1줄.

---

## 3. LOW
- **L1** `SKILL.md:151` "64-65행 개시분" → 실제 intent-diff 개시는 `:70-71`(행 참조 드리프트).
- **L2** `research-plan.md:33-34` "SKILL.md 반영은 별도 배치" 문구 stale(이미 `SKILL.md:64-67` 반영). "G9" 호칭(`research-plan.md:24,58`, `verify_facts.py:15,577`)은 다른 문서에 없음 — G3 하위검사로 이름 통일.
- **L3** `SKILL.md:59-61` preflight가 브라우저/공공 MCP를 "감지"한다 ↔ `preflight.py:321-324`는 "런타임 확인 필요" 표기만.
- **L4** `SKILL.md:95` G1은 `check`만 지시, 기록 명령은 `verification-gates.md:70`에만(`record_script_result`).
- **L5** 스키마 `verified_by` dead 필드(`facts_db.py:76-93` 미사용). `cause-disappearance.md`는 `report-format.md:48`·`skill_paths.py` 주석에만 등장, 정의 없음.
- **L6** `research-plan.md:63-78` 승인목차 예시에 "(해당 시)" 없음 ↔ `report-format.md:14-17`은 표기 → 예시 복붙 시 5·7·8부 의무화(`verify_facts.py:583,633-643`).
- **L7** SKILL.md description ≈ 420자 — 사용자 규칙(200~250자) 초과(상시 로드 비용).
- **L8** `verify_facts.py:797-798` G3 FAIL은 영수증 미기록 ↔ `README.md:58` "실패도 기록"(G5만 해당).
- **L9** `check_toc._find`(`verify_facts.py:621-625`) 부분문자열 양방향 매칭 — 축 "시장"이 1부 소제목 "시장 핵심수치"에 먼저 걸려 통과 가능(느슨).

---

## 4. codex-review(v1) 반영 확인 — 코드로 본 결과
| # | 지적 | 반영 | 비고 |
|---|---|---|---|
| 1 | 전건 팀리드 재검증 | △ | `facts_db.py:76-82` lead 이벤트 강제. 단 이벤트 자체가 관례(M2), [2] 영수증 무결박(M1) |
| 2 | htmlbox 증빙 불인정 | ✓ | `check_capture_path`(`facts_db.py:97-115`), `capture_web.py:25-27` |
| 3 | fact+evidence[] | ✓ | 스키마·DB |
| 4 | claim_key | △ | 생성·유일성 ✓, diff 미배선(M9) |
| 5 | 무태그·부록우회 | △ | 무태그 ✓(단위 한정, H2), 부록=미검사 설계(H1) |
| 6 | manifest 해시 | △ | ✓, `_images` 누락(M3) |
| 7 | 증거유형 6종 | ✓ | |
| 8 | SSRF 경계 | ✓ | adversarial ssrf/redirect/rebinding 3건 PASS 실측 |
| 9 | frontmatter·스킬루트 | ✓ | `skill_paths.py`, demo PASS |

---

## 5. 과잉설계 — 없애도 품질이 안 떨어지는 것
| 대상 | 근거 | 처분 |
|---|---|---|
| `scripts/capture_web.py`(84줄) | 증빙 불인정(`:1-6`), 어떤 게이트도 산출물을 소비하지 않음 | 삭제 |
| `harvest_images.py search`(openverse/commons/searx) | 자체 문서가 "완성 인포그래픽은 openverse에 거의 없다"(`image-research.md:31`) | 제거, `pdf/page/get/index` 유지 |
| G3 `[도판] 0장 FAIL`(`verify_facts.py:542-543`) | 도판 없는 팩트시트는 정당; FAIL이면 `make_chart` 남발 유도 | WARN |
| 세션 저널 4종(`report-format.md:47-48`) | `verification-economics.md`·`cause-disappearance.md` 기계검사 0·정의 없음 | intent-diff·expansion-log 2종으로 |
| G1 영수증 | 무소유·즉시 위조(M1); `check_ledger_integrity`가 실질 검사 | 삭제 |
| 4차원 등급 A~D | 어떤 게이트도 읽지 않음(스키마 enum만) | 표시용으로만 남기고 "게이트" 서술 삭제, 또는 independence를 claim-graph 독립그룹에 연결 |
| G5c | 기계강제 0(`verify-<slug>.md` 존재 검사 없음) | "권장 절차"로 격하 |
| `gates.PREREQUISITES["[4]"]`(`gates.py:49`) | 아무도 기록하지 않음 | 삭제 |

---

## 6. 정합성 전수 대조 — 통과 항목(참고)
- `gates.py record G0 … --evidence --refs` / `check G1` / `record [2]` / `check G4` / `record G4` ↔ `gates.py:419-452` CLI 일치. `[2]` 인자는 bash·PowerShell 모두 literal 전달 실측(`normalize_gate`가 `2`도 수용).
- `verify_facts.py <report.md> <work_dir> [--conversion] [--plan]` ↔ `verification-gates.md:37` 일치. `render_pdf.py` [4b] 자기기록·`manifest.py verify`의 [4b]·G4 전제 ↔ 문서 일치.
- 마커(`## EVIDENCE/CLAIMS/EXPAND/FIGURES/인사이트/요약`, `AXIS`) SKILL↔agent-briefs 일치. 축 프리셋 단일진실원(report-format) ↔ research-plan·SKILL 참조 일치. 부록 마커·`_captures/E###.png`·`_reconstructed/` 경로 일치.
- 실행: demo 6종 PASS(skill_paths·facts_db·gates·manifest·verify_facts·preflight) · adversarial 60/60 · E2E PASS(pandoc+Chrome 렌더 포함) — 본 세션 실측.
- **컨텍스트 예산(추정, tiktoken 미설치)**: SKILL.md 9,338자 + references 9종 25,825자 = **35,163자**. 한·영 혼합 기준 약 **21~28k 토큰** — 전량 로드해도 과하지 않다. 압박은 문서가 아니라 런타임 데이터(재검증 fetch 결과·캡처 PNG Read·워커 JSONL)이며 그 대책이 H3다.

---

## 부록 — 실증 스크립트 요지 (임시폴더, 저장소 미변경)
`probe_verify.py`: 대장 F001(300.9 KRW_T, confirmed+캡처)·F002(120 USD_million, confirmed) 생성 후 7개 본문 케이스를 `verify_facts.verify`에 투입. 결과 A/B/C/D/E ok=True(우회), F/G FAIL(정상). 추가로 G0→G1(손)→[2](손)→`check_gate G3` ok=True, `_images` 교체 후 `manifest.verify` ok=True.
