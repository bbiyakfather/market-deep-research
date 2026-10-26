# market-deep-research

**증빙형(evidence-based) 시장조사 보고서 스킬** — `market-deep-research`(+ `mdr-search` 검색만, `mdr-hwpx` 납품 양식화)의 정본 저장소입니다. **Claude Code 와 Codex 양쪽에서** 같은 SKILL.md 로 동작하고, 주제(기술동향·기업 실사·구매의향·경쟁분석 등)에 묶이지 않습니다. 팀원 설치는 [설치·실행](#설치실행).

![fact → source → capture 증거 체인과 게이트](docs/img/evidence-chain.png)

AI 딥리서치는 같은 질문을 두 번 물으면 다른 숫자를 내놓고, 근거 링크를 눌러 보면 그 숫자가 없는 일이 흔합니다. 이 스킬은 그 문제를 **구조로** 막습니다 — 모든 수치·주장을 **[사실(fact) → 출처(source) → 화면캡처(capture)]** 로 결박하고, 게이트를 통과한 것만 보고서에 실립니다. 그리고 2026-10 부터는 조사를 시작하기 전에 **"누가 이 문서를 들고 누구를 설득해 무엇을 결정하는가"** 를 먼저 정합니다 — 사실 검증이 완벽해도 독자와 목표가 비어 있으면 "내용에 코어가 없는" 보고서가 나오기 때문입니다.

```
codes/market-deep-research/   ← 스킬 본체 (정본)
codes/mdr-hwpx/               ← 원고 md → 발주처 양식 hwpx 변환 스킬
_planning/                    ← 설계·리뷰 기록
lessons.md                    ← 실전에서 얻은 교훈 누적
```

조사 실행 산출물(`research_*/`)과 수집 로그(`audit/`)는 저장소에 커밋하지 않습니다(`.gitignore`).

---

## 2026-10 업데이트 — 무엇이 달라졌나

네 건의 실전 조사(연간 업데이트 보고서·출연연 기술 BM·문헌 조사·사업화 전략 용역)에서 반복된 사고를 스킬로 올렸습니다.

| 들어온 것 | 왜 | 어디 |
|---|---|---|
| **독자·목표 설계 §0** — 의뢰인·1차 독자·설득 대상·독자의 결정·**핵심 메시지 가설**·관점·우리 기술 근거·입력 자료 지위를 G0 맨 앞에서 확정 | 조사가 끝난 뒤 독자·관점을 재정의해 전면 재집필한 사고 3건. 핵심 메시지는 **가설**로 두고 축별 intent-diff 가 검증, 반증되면 교체·기록 | `references/reader-goal.md` |
| **시각화 우선(visual-first)** — 수치 데이터는 그림이 기본, 표는 식별자·비교표·값 참조일 때만. `visual_audit.py` 가 본문 표 중 시각화 후보를 뽑아 표마다 판정을 남김 | 납품본이 표 23 : 그림 10 으로 쏠림. 증빙 체계가 셀 단위 F태그 결박에 최적화돼 작성자가 표로 도피 | `references/visual-first.md` · `scripts/visual_audit.py` · `docs/prd-visual-first_261008.md` |
| **G0 확정 필드 5개 추가** — 선행 문서 기준선, 의뢰인 확인 채널, high-risk 완화 방식, 납품 형식, 폐기 수치 grep | 전년판을 안 읽고 취소된 프로젝트를 '성공 모델'로 서술 · 표지·목차를 끝에서 두 번 재작업 · 완화를 기록 없이 해 반박검색이 조용히 무력화 | `references/research-plan.md` |
| **경쟁·포지셔닝 템플릿** — 대안 지도 → 비교표 → 열세 시나리오, 경쟁 범위가 갈리면 두 범주 병기 | 기술사업화 실사의 시장성 축이 조사마다 다른 구조로 나옴 | `references/competitive-positioning.md` |
| **워커 철칙 보강** — 임시 ID W접두, verbatim 리터럴, 수치에 지표 성격·시점 병기, WD 에서만 실행 | 임시 ID 오등재 43건, 재구성 인용, 스킬 폴더에 조사 로그가 쌓여 공유 저장소로 푸시 | `references/agent-briefs.md` |
| **납품본 변환 규칙** — 작성 주체 표현·내부 코드 명칭화·불확실 정보 처리·분량·참고문헌 | 증빙판 표현('조사팀 판단'·F-ID·분류 코드)이 발주처 납품본에 그대로 나가 사후 치환 130건 | `codes/mdr-hwpx/references/deliverable-rules.md` |
| **G4 독자 테스트** — 1차 독자·설득 대상·신규 독자·핵심 메시지 귀결·시각화·인쇄 가독성 | G4 육안검증이 사실·도판 정확성만 보고 "읽히는가"는 보지 않았음 | `reader-goal.md` G4 절 |
| **flint 차트 엔진 내장**(2026-10-26) — microsoft/flint-chart 의 파이썬 포트를 `scripts/flint/` 에 그대로 내장(MIT, 파일 해시 고정). `make_chart.py` 가 confirmed fact 에서 16종 차트를 Vega-Lite 로 만들고 사이드카 `.vl.json` 으로 그림 값↔사실대장을 G3 가 대조 | 자작 차트가 막대·선 2종뿐이었고, 그림 속 숫자가 대장과 같은지는 아무도 검사하지 않았음 | `visual-first.md` §1a·§1b · `scripts/make_chart.py` · `visual_audit.py --figures` |
| **요약→세부→원문 결박**(2026-10-26, imozuru 번안) — 근거 인용(verbatim)이 원문 clean 텍스트 어느 행에 글자 그대로 있는지 `span` 으로 기록·대조, F태그 문장마다 대조 통과 인용이 없으면 v4 FAIL, 실패 시 PDF 미생성·기존 PDF 보존, `audit/evidence.html` 증빙판(문장→인용→앞뒤 6행→원문) | verbatim 이 원문에 실재하는지는 규칙만 있고 기계가 막지 않았음 | `scripts/span_tools.py` · `build_evidence_html.py` · `verification-gates.md` §[2]·§G3 |
| **검색 전건 기록·학술 출처 계층**(2026-10-26, scientific-agent-skills 번안) — 모든 검색을 `audit/search-log.jsonl` 에 기록, `--type academic` 이 OpenAlex→Crossref→Europe PMC→Semantic Scholar→arXiv 폴스루, 학술 출처 6규칙·기술동향 축별 충분조건 기본값·근거 확실성 라벨·TRL 증거표 | 학술 검색이 arXiv 뿐이었고 어떤 검색식으로 몇 건을 봤는지 남지 않았음 | `source-ladder.md` · `academic-apis.md` · `trl-evidence.md` · `research-plan.md` |

---

## 2026-10-14 업데이트 — 조사·크롤링 강화

이 스킬은 "모은 사실이 맞는가"는 두껍게 검사했지만 "못 모은 것이 있는가"는 재지도 막지도 않았습니다. 과거 조사 7건을 집계해 보니 사실이 1건뿐인 조사 대상이 다수였고, 검색이 차단돼도 "결과 없음"으로 보고됐습니다. 그래서 **실패를 보이게 하고, 빠진 곳으로 되돌아가게** 고쳤습니다.

| 들어온 것 | 왜 | 어디 |
|---|---|---|
| **검색 백엔드 상태** — 결과와 함께 백엔드별 `ok·empty·blocked·error` 를 돌려주고, 전 백엔드가 막히면 종료 코드 2 | 차단·오류가 빈 목록으로 바뀌어 워커가 "자료 없음"으로 읽음 | `scripts/search.py` (`search_report`, `--json`, `health`) |
| **워커 `## COVERAGE`** — 시도한 검색식과, 못 채운 항목을 `NOT_FOUND`(찾아봤는데 없음)·`UNREACHABLE`(막혀서 못 봄)·`NOT_ATTEMPTED` 로 구분 보고. 열린 공백이 남으면 조사 루프가 수렴하지 않음 | 없는 것과 못 찾은 것이 한 칸이었고, 루프 종료가 워커의 자기 신고에만 달려 있었음 | `references/agent-briefs.md` · `scripts/join_workers.py` |
| **0웨이브 대상 열거** — 목록형 조사는 본조사 전에 `audit/universe.md` 로 대상 목록부터 만들고, `join_workers.py coverage` 가 사실 0건·1건 대상을 보고 | 대상 목록을 빠짐없이 세는 단계가 없어 누락된 대상은 어떤 게이트도 못 잡음 | `references/research-plan.md` |
| **탈락 사실의 복귀** — 재열람·반박검색에서 떨어진 사실을 사유 코드와 함께 `audit/gap-log.md` 에 남기고 사유별로 재조사 | 탈락하면 그대로 버려져 공백이 숨음 | `references/verification-gates.md` |
| **의심 페이지 판정** — 로그인벽·동의창·없는 페이지 안내를 `partial` 로 강등. Jina 가 알려 주는 원 페이지 오류 코드를 반영 | 성공 판정이 "본문 1000자 이상" 하나라 죽은 페이지가 성공으로 저장됨(아래 벤치마크) | `scripts/fetch.py` (`validate_body`) |
| **브라우저 계층** — `patchright`(없으면 `playwright`) 헤드리스 Chromium. 내부망 응답 차단, 호출마다 새 컨텍스트 | JS 로 그려지는 페이지를 여는 로컬 계층이 없어 제3자 서비스에 의존 | `scripts/fetch.py` (`browser` 계층) |
| **대외비 스위치** — `MDR_NO_THIRD_PARTY=1` 이면 Jina·Wayback 계층을 건너뜀 | 열람 대상 URL 이 외부 서비스로 나감 | `references/source-ladder.md` |
| **문서 파일·인코딩** — HWP·HWPX·XLSX·DOCX·PPTX·CSV·ZIP 원본 저장, 문서 상한 40MB, `<meta charset>` 인식, 지문 프로필 갱신(`chrome110`→`firefox`, `safari180_ios`→`safari_ios`) | 한국 공공·공시 자료가 모든 계층에서 실패, 2023년 지문 사용 | `scripts/fetch.py` · `requirements.txt` |

### 벤치마크 (2026-10-14)

과거 조사 4건에서 **끝내 열지 못했던 URL** 을 수정 전·후 코드로 한 번씩 다시 열었습니다. 원래 실패했던 어려운 표본이라 절대 성공률은 낮습니다. 측정 도구는 `_planning/recall-eval/recall_eval.py` 입니다.

| 설정 (56건) | 진짜 확보 | 가짜 확보 | 부분 확보 | 실패 |
|---|---|---|---|---|
| 수정 전 | 10 | **8** | 19 | 19 |
| 수정 후 | **16** | 0 | 3 | 37 |
| 수정 후 + `MDR_NO_THIRD_PARTY=1` | 5 | 0 | 3 | 48 |
| 수정 후 + `MDR_NO_THIRD_PARTY=1` + `MDR_BROWSER_HEADED=1` | 10 | 0 | 2 | 44 |

- **가짜 확보**는 직접 요청이 404·410 인 죽은 페이지(56건 중 15건)를 "확보"로 집계한 건수입니다. 수정 전 코드는 Jina 가 200 으로 감싸 준 "Page not found" 안내문을 길이만 보고 통과시켰습니다.
- 진짜 확보가 10 → 16건으로 늘었고(같은 표본을 한 번 더 쟀을 때는 18건 — 측정 간 편차 2건), 수정 전에 열었던 살아 있는 페이지를 수정 후에 잃은 경우는 없습니다. 실패가 늘어난 것은 죽은 페이지와 의심 페이지가 제자리(실패)로 분류됐기 때문입니다.
- 남은 실패는 대부분 봇 차단(403)입니다. 헤드리스 브라우저는 `curl_cffi` 와 같은 403 을 받았고, 창을 띄우는 방식(`MDR_BROWSER_HEADED=1`)에서만 일부 JS 챌린지가 풀렸습니다(브라우저 계층 확보 3건).
- 제3자 계층을 끄면 확보가 16 → 5건으로 줄어듭니다. 대외비 조사에서는 이만큼의 손실을 감수해야 합니다.
- 검색 백엔드 실측: DuckDuckGo 는 정상, 공개 SearXNG 5곳은 JSON 응답 0곳(403·429·캡차·DNS 실패). 자체 인스턴스는 `assets/searxng/` 의 구성 파일로 띄우고 `MDR_SEARX_URL` 로 연결합니다.

한계: 설정당 1~2회 측정, 단일 IP 입니다. `patents.google.com` 22건은 반복 측정 중 IP 단위로 차단(503)돼 표본에서 뺐습니다 — 특허는 크롤링 대신 특허 DB 도구로 조회하도록 워커 지침을 바꿨습니다. "얼마나 빠뜨리는가"(대상 재현율)는 도구만 만들었고, 독립 정답지로 잰 수치는 아직 없습니다.

---

## 3대 절대 규칙

1. **원문 미확인 수치는 폐기** — 추정 금지. 출처 없는 주장은 사실대장(`facts.jsonl`)에 등재 자체가 불가하며, 등재되지 않은 것은 본문에 쓸 수 없습니다.
2. **팀리드 전건 재검증** — 병렬 조사원(서브에이전트)이 수집한 모든 fact 를 팀리드(메인 세션)가 **원문을 직접 다시 열람**해 인용문(verbatim)과 위치(locator)를 대조한 뒤에만 confirmed 처리합니다. 조사원 단독 확정 금지. WebFetch 요약 답은 재확인 근거가 아닙니다.
3. **고객용 / 내부 audit 분리** — 고객 PDF 에는 검증 통과분만, 폐기 목록·실패 URL·반박 상세·검증 이력은 내부 audit 번들에 전량 보존.

검증에 불통과한 모순은 침묵 폐기하지 않고 `disputed` 로 남깁니다 — **"기권이 정답"** 인 상태를 인정하는 것도 설계의 일부입니다.

---

## 어떻게 돌아가나

![독자·목표 → G0 → 병렬 조사 → 리드 재검증 → 보고서 → 게이트](docs/img/pipeline.png)

```
[§0]  독자·목표 ─ 의뢰인·1차 독자·설득 대상·독자의 결정·핵심 메시지 가설 확정(승인 후 동결)
[G0]  preflight ─ 의존성 점검 + 확정 필드(축·충분조건·납품 형식·승인 목차) + intent-diff 개시
[1]   병렬 조사 ─ 조사원 에이전트 팬아웃(sonnet, 에이전트별 임시폴더, 읽기전용, 스폰 첫 줄 = 독자·목표)
[E]   확장→수렴 ─ EXPAND 리드 dedup → 후속 워커 → 축별 잔여 리드 0까지 반복
[G1]  join      ─ raw 보존 · 스키마 검증 등재 · 무출처 즉시 discarded
[2]   팀리드 재검증 ─ ★전건 원문 재열람 → verify_event(by=lead)
[Bx]  반박·claim-graph ─ high-risk: 독립 관찰그룹 2+ · 반박검색 · 기본소스 · 시간증거
[G2]  증빙 게이트 ─ confirmed 전건 source_capture(핵심수치 필수)
[3]   보고서 작성 ─ 11부 표준목차 + 핵심 메시지 귀결 점검 + 시각화 판정(visual_audit) + 내부 audit
[G3]  verify_facts + manifest ─ 실패 0 · 무태그 수치 차단 · 도판검사 · CLI PASS 가 기준 manifest 봉인
[G5c] 실행코드 검증 ─ 계산·상충 주장을 스크립트로 실증(CONFIRMED/REFUTED)
[4]   render_pdf ─ pandoc → Headless Chrome, 오프라인 PDF
[4b]  재봉인    ─ extend-only(기존 항목 불변 확인, 렌더 산출물만 추가)
[G4]  preview   ─ 팀리드 육안 검증 + intent-diff 축별 대조 + 독자 테스트 + 대장→원고 역방향 고아 검사
[G5]  최종 무결성 ─ PDF F태그·링크·캡처 수 재검사 + manifest verify
```

**축 도출 체인**은 한 줄로 이어집니다: `독자·목표(핵심 메시지) → 의사결정 용도 → 조사질문 → 축 → 에이전트 배정 → 3부 챕터`. 축 이름이 이 체인 바깥에서 생기면 그 챕터는 채워지지 않습니다.

### 게이트 영수증 (`audit/gates.jsonl`)

통과 주장은 append-only 영수증으로만 성립합니다. 핵심은 **누가 기록할 수 있는가**입니다.

| 구분 | 게이트 | 기록 주체 |
|---|---|---|
| 수동 | G0 · [2] · G4 | 팀리드가 `gates.py record` (사람의 판단이 필요한 게이트) |
| **소유 스크립트 자기기록** | G3 · [4b] · G5 | `verify_facts.py` · `render_pdf.py` · `manifest.py verify` — **CLI 손기록 차단** |
| 무소유 | G1 · G5c 등 | `gates.py record_script_result` |

G3·[4b]·G5 는 손으로 기록할 수 없습니다. 소유 스크립트를 **실제로 돌린 영수증**과 안 돌리고 적은 영수증을 구별할 수 없다면 그 영수증은 영수증이 아니기 때문입니다. 실패도 기록됩니다. G0 영수증의 `--refs` 는 research-plan 같은 고정 산출물만 결박합니다 — intent-diff 처럼 수시로 바뀌는 문서를 결박하면 영수증이 무효화됩니다. 같은 이유로 §0 독자·목표는 승인 시점에 동결되고, 핵심 메시지가 반증돼 바뀌면 `intent-diff.md` 의 `현행 메시지:` 줄에 적습니다.

---

## 도판과 시각화 — 두 결정을 분리한다

![표가 아니라 그림: visual-first](docs/img/visual-first.png)

**(가) 그림이냐 표냐** 는 데이터 형태로 정합니다. 시간 추이·항목 비교·비중·분포·두 변수 관계는 **그림이 기본**이고, 표는 식별자·텍스트 속성, 열마다 성격이 다른 비교표, 정확한 값 참조(부록)일 때만 남습니다. 그림을 넣었으면 같은 데이터의 표는 본문에서 뺍니다(`references/visual-first.md`).

```bash
python scripts/visual_audit.py report.md --decisions audit/visual-decisions.json
# 본문 표 중 행 3개↑·수치열 1개↑(연번·출처 열 제외)를 후보로 뽑아 제안 형식을 붙인다.
# 해결 = keep + 사유. chart 는 표를 실제로 지워야 해결. 미결 0건이 G4 조건.
```

**(나) 그림을 어디서 가져오나** — 좋은 인포그래픽은 이미 소스 보고서 안에 있습니다. 찾아서 출처와 함께 결박하는 것이 정공법입니다.

```
0. 워커 ## FIGURES 신고분   ← 원문을 직접 읽은 조사원이 지목한 도판. 가장 정확하다.
1. 소스 PDF 도판 크롭       ← 인포그래픽 점수 랭킹(명시캡션·면적·벡터밀도 ↑ / 반복 로고 ↓)
2. 확보한 웹페이지 이미지    ← og:image · figure/figcaption
3. 이미지 검색             ← 기관 도메인 직격(--sites) + openverse·commons
4. 자작 차트              ← 원문에 대응 도판이 없는 수치 데이터. make_chart.py / matplotlib, 값은 confirmed fact 에서만
```

**G3 도판검사** — 수치에 적용되는 증빙 철칙이 그림에도 같은 강도로 걸립니다.

| 검사 | 조건 |
|---|---|
| `[도판]` | 본문 대표 이미지 0장 차단 |
| `[도판경로]` | 참조 경로 실재 — 건별 판정 |
| `[도판출처]` | 참조 뒤 2줄 이내 `[그림]` 캡션 + `출처:` **값** |
| `[도판무결박]` | `assets/` 자작 차트는 캡션에 `(Fxxx)` 최소 1개 |
| `[도판커버리지]` | 3부 축 챕터별 도판 유무 — 경고 |

---

## 조사 유형 4종과 독자 유형 5종

축(조사질문 = 에이전트 분할 = 3부 챕터)은 `references/report-format.md` 의 축 프리셋이 단일 진실원입니다.

| 조사 유형 | 3부 축 |
|---|---|
| 기술동향 | 기술요소 / 플레이어 / 시장 / 정책 |
| 산업동향 | 밸류체인 / 통계(KOSIS·DART·KIPRIS) / 해외 |
| 기관·기업 실사 | 일반현황 / 사업현황 / 재무실적 (entity-identity 선고정) |
| 기술사업화 실사 | 기술성 / 권리성 / 시장성(경쟁 대안 지도 → 비교표 → 열세 시나리오) / 사업성 |

독자 유형은 §0 을 채울 때 고르는 프리셋입니다(`references/reader-goal.md`).

| 독자 유형 | 설득 대상 → 결정 | 핵심 메시지가 답해야 할 것 |
|---|---|---|
| 기술이전 희망 연구자 | 수요기업 → 기술이전 검토 착수 | 시장이 실재·성장하고, 기존 대안 대비 이 기술이 푸는 문제가 구체적이며, 도입 기업이 얻는 것이 수치로 보임 |
| 예비창업자·창업팀 | 투자자·본인 → 사업 착수·입증 과제 | 우리 접근이 경쟁 지형 어디에 서고 무엇을 입증해야 하나 |
| 사업화 주관기관·컨소시엄 | 경영진 → 어디서 먼저 사업하나 | 경쟁사 대비 강약점 → 시장·규제 → 진출 순서 |
| 연간 업데이트 독자(두 층) | 전년 독자 + 신규 독자 → 변화 파악 | 전년 기준선·올해 변화·전년 결론 판정이 한 본문에서 |
| 기관 내부 기술사업화 판단 | 자기 조직 → 진입 시장·파트너·타이밍 | 사업화 기술이 들어갈 시장과 주체의 변화 |

---

## 수집 스택 (유료 API 무의존)

- **검색** (`scripts/search.py`): ddgs 다중 백엔드(`--type news` 는 ddgs news) 1차 → DuckDuckGo HTML 폴백 → SearXNG(`MDR_SEARX_URL` 자체 인스턴스 등록 시만) → 전문 무료 API(SEC EDGAR·Wikipedia; 학술은 OpenAlex→Crossref→Europe PMC→Semantic Scholar→arXiv 폴스루, `references/academic-apis.md`). 백엔드별 상태를 함께 돌려주고, 전 백엔드 실패는 종료 코드 2. 호출마다 `<작업폴더>/audit/search-log.jsonl` 에 전건 기록. 내장 WebSearch 와 병행.
- **fetch** (`scripts/fetch.py`): 강방어 사이트 우회 사다리 — 도메인 라우팅 → curl_cffi TLS 지문 → **모바일 iOS 지문** → **브라우저**(patchright·선택) → Jina Reader → Googlebot UA → RSS → Wayback → OGP. 성공 판정은 HTTP 200 이 아니라 본문 검증(의심 페이지는 `partial`). `MDR_NO_THIRD_PARTY=1` 이면 Jina·Wayback 을 건너뜁니다. 원본(raw)+정제본을 SHA-256 과 함께 보존.
- fetch.py 는 **현재 폴더** `audit/` 에 로그·스냅샷을 씁니다 — 모든 스크립트는 작업폴더(WD)에서 절대경로로 실행합니다. 스킬 폴더에서 돌리면 조사 원문이 저장소에 섞입니다.

로그인·CAPTCHA·paywall 우회는 하지 않습니다.

---

## 저장소 구조

```
codes/market-deep-research/
├─ SKILL.md                  # 오케스트레이터 본체 (파이프라인·3대 절대 규칙·참조 문서 표)
├─ assets/                   # facts-schema.json · curated-sources.json · searx-instances.json · style.html
├─ references/               # 단계별 규정 문서 13종
│  ├─ reader-goal.md         #   §0 독자·목표·핵심 메시지 가설·독자 테스트            ← 2026-10 신설
│  ├─ visual-first.md        #   그림 vs 표 결정표·차트 규칙·visual_audit 운영          ← 2026-10 신설
│  ├─ competitive-positioning.md  # 경쟁 대안 지도·비교표·포지셔닝 서술              ← 2026-10 신설
│  ├─ research-plan.md       #   G0 확정 필드·축 도출 체인·승인 목차 서식
│  ├─ agent-briefs.md        #   워커 계약·반환 마커·철칙·작성자 브리프
│  ├─ verification-gates.md  #   게이트 상세·4차원 출처등급·claim-graph
│  ├─ report-format.md       #   11부 표준목차·축 프리셋·납품본 인계 주의
│  ├─ claim-review.md        #   문장↔근거 의미 검토(원문 일치 ≠ 주장 성립)
│  ├─ source-ladder.md · evidence-capture.md · entity-identity.md · extract-recipes.md · image-research.md
├─ scripts/                  # 실행 도구 20종
│  ├─ gates.py · verify_facts.py · verify_claims.py · verify_calculations.py · manifest.py
│  ├─ facts_db.py · join_workers.py · source_index.py
│  ├─ fetch.py · search.py · capture_pdf.py · capture_web.py
│  ├─ harvest_images.py · make_chart.py · visual_audit.py                       ← visual_audit 2026-10 신설
│  └─ render_pdf.py · preview_pdf.py · preflight.py · install.py · skill_paths.py
├─ docs/                     # PRD 등 설계 기록 (prd-visual-first_261008.md)
└─ tests/                    # 적대 케이스·v4 게이트·의미 검토 테스트

codes/mdr-hwpx/              # 원고 md → 발주처 양식 hwpx (부별 모듈 빌드·정합성 검토·합본)
└─ references/deliverable-rules.md   # 증빙판 → 납품본 변환 규칙                        ← 2026-10 신설

template/                    # 새 조사 프로젝트 폴더 골격 — AGENTS.md(규칙 본문)·CLAUDE.md(@AGENTS.md)·.gitignore·tasks/lessons.md
```

## 조사 1건의 산출물

```
research_<주제>_<YYYYMMDD>/
├─ report.pdf            # 고객용 팩트시트 (11부 표준목차, 수치마다 (F###) 태그)
├─ report.md             # 생성 소스 (직접 수정 금지 — facts.jsonl 수정 후 재렌더)
├─ _captures/            # fact별 원문 화면캡처 (E###.png + 메타)
├─ _images/              # 대표 도판 + IMAGES.md 인덱스
├─ assets/               # 자작 차트 (스크립트와 PNG 모두 여기)
└─ audit/                # 내부 전용: research-plan.md(§0 포함) · intent-diff.md · facts.jsonl ·
                         # gates.jsonl · visual-decisions.json · 폐기 목록 · raw 워커 출력 · manifest
```

**단일 진실원은 `facts.jsonl`입니다.** 보고서는 생성물이므로 본문 수치를 직접 고치는 행위는 금지되며, 대장을 고치고 재렌더해야 합니다 — G3/G5 게이트가 이 동기화를 기계로 강제합니다.

## 설치·실행

| 목적 | 스킬 |
|---|---|
| ① 검색만 | `mdr-search` |
| ② 증빙형 보고서 초안(MD/PDF) | `market-deep-research` |
| ③ 양식화: 원고 md → 양식 hwpx | `mdr-hwpx` |

### 팀원 설치 — 5분

```bash
git clone https://github.com/bbiyakfather/market-deep-research.git
cd market-deep-research
pip install -r codes/market-deep-research/requirements.txt   # 수집·PDF 스택 (python>=3.10)
python codes/market-deep-research/scripts/preflight.py        # HARD: PyMuPDF·pandoc·chrome / SOFT: curl_cffi·trafilatura …

# Claude Code 사용자 → ~/.claude/skills/ 에 3개 스킬 설치 (SHA-256 검증 복사)
python codes/market-deep-research/scripts/install.py

# Codex 사용자 → ~/.agents/skills/ 에 설치 (Codex 가 사용자 스킬을 읽는 위치)
python codes/market-deep-research/scripts/install.py --target ~/.agents/skills

# 설치본이 저장소와 같은지 대조만 (불일치 시 exit 1). Codex 설치본은 --target 을 같이 준다
python codes/market-deep-research/scripts/install.py --check
python codes/market-deep-research/scripts/install.py --check --target ~/.agents/skills
```

`install.py` 는 allowlist 3개 스킬 폴더 안만 mirror-sync(초과 파일 삭제) 하고 그 밖의 스킬은 건드리지 않습니다. 둘 다 쓰는 사람은 두 번 실행합니다.

### 새 조사 프로젝트 시작 — 주제 무관

```bash
cp -r template/ ~/work/<프로젝트명>/ && cd ~/work/<프로젝트명>/ && git init
# AGENTS.md 의 <조직> 자리만 채운다. 조사마다 research_<주제>_<YYYYMMDD>/ 가 그 아래 생긴다.
```

| | Claude Code | Codex |
|---|---|---|
| 규칙 파일 | `CLAUDE.md`(`@AGENTS.md` 한 줄) | `AGENTS.md` |
| 시작 | `/market-deep-research <주제>` 또는 "증빙 포함 시장조사 보고서" 류 자연어 | `$market-deep-research <주제>` 또는 같은 자연어(`/skills` 로 설치 확인) |
| 병렬 조사원 | `Agent` 서브에이전트(sonnet·background) | 내장 서브에이전트(기본 켜짐). 모델은 `~/.codex/config.toml` 의 `[agents].default_subagent_model` |
| 원문 재열람 | WebFetch → 403 이면 `fetch.py` | `fetch.py`(증빙 스냅샷은 늘 이 경로) |

도구 이름만 다르고 게이트·대장·검증 절차는 동일합니다(`SKILL.md` 「실행 환경」 표). 대외비 조사는 `MDR_NO_THIRD_PARTY=1` 로 Jina·Wayback 계층을 끕니다. 실전에서는 설치본에서 고친 변경이 먼저 생기기도 하므로, 조사 직전 `--check` 로 드리프트를 확인하고 변경분은 이 저장소 `codes/` 로 동기화합니다.

## 검증 현황 (2026-10-26)

```
pytest (v4 2개 파일 제외)  : 647 passed  (2026-09 기준선 602 + 신규 45)
교차 리뷰                  : grok 1회(높음 3·중간 4 지적 → 6건 반영, 1건 한계로 수용)
fetch.py demo / search.py demo : OK
visual_audit.py --selftest : OK  (실전 report.md 1건: 후보 11건 추출, 연번 열 오탐 0)
verify_facts.py demo       : OK  (승인 목차 파서 12부·4축 그대로)
독립 리뷰                  : opus 2회(독자·목표 묶음 13건·시각화 묶음 13건 지적 → 반영)
pytest                     : 739 passed (병합 후 재측정; test_e2e·test_v4_gates·test_v4_semantic 제외)
flint 내장                 : 픽스처 17건 JS 출력과 바이트 동일, 한글 라벨 가로막대 실렌더 육안 확인(vl-convert 1.9.0)
독립 리뷰                  : opus 2회 추가(외부 스킬 반영 1차 차단 3·권고 9, 2차 차단 3·권고 8 → 전부 반영)
알려진 결함                : tests/test_v4_gates.py·test_v4_semantic.py 가 finalize_report 모듈 부재로 수집 실패 · v4 문장 단위 인용 강제의 오탐률은 실제 조사로 미측정
```

## 개발 이력

| 변경 | 내용 |
|---|---|
| 2026-10-26 | 외부 스킬 3종 반영 — flint-chart 파이썬 포트 내장(16종 차트·사이드카 값 대조·SVG 린트), imozuru 강화 H1~H11(span 글자 대조·문장 단위 인용 강제·빌드 중단·증빙판 HTML·PDF 본문 하한), scientific-agent-skills(검색 전건 기록·학술 API 4종·축별 충분조건·확실성 라벨·TRL). 분석·반영안 `_planning/research-skill-repos-adoption-2026-10-26.md` |
| 2026-10-14 | 조사·크롤링 강화 — 검색 백엔드 상태·워커 COVERAGE·대상 열거·탈락 사실 복귀·의심 페이지 판정·브라우저 계층·대외비 스위치·문서 파일 저장 + 열람 벤치마크 |
| 2026-10-08 (T2) | 표 형식 다양화 — 사용자 편집 학습(대상별 묶음 세로 표 A·두 열 라벨형 B·가로 행렬 matrix), `visual-first.md` §2b 선택 규칙과 캡션 태그 `{형식=A\|B}`, `visual_audit.py` 표 키·`render_pdf.py` 에서 태그 제거. 빌더 쪽(mdr-hwpx `build_hwpx.py` A/B 렌더러)은 별도 세션 (`_planning/batches/batch-T2-table-format.md`) |
| 2026-10-08 (T1) | 컨텍스트 예산 리팩토링 — SKILL.md 게이트 절을 카드(목적·절대규칙·영수증·포인터)로 줄이고 상세는 `verification-gates.md` 한 곳에, description ≤250자·본문 ≤12KB(목표 10KB) 가드 테스트, mdr-hwpx 통과 기준 1사본화 (`_planning/batches/batch-T1-context-budget.md`) |
| 2026-10-08 | 독자·목표 설계(reader-goal) G0 신설 · 시각화 우선(visual-first) PRD·규칙·`visual_audit.py` · G0 필드 5개 · 워커 철칙 · 납품본 변환 규칙(mdr-hwpx) |
| [#18](https://github.com/bbiyakfather/market-deep-research/pull/18) | 목적별 모듈화(mdr-search / market-deep-research / mdr-hwpx) + P0 검증 결함 수정 + 적대적 리뷰 결함 29건 처리 |
| [#17](https://github.com/bbiyakfather/market-deep-research/pull/17) | README 를 실제 main 상태로 재작성 |
| [#16](https://github.com/bbiyakfather/market-deep-research/pull/16) | 도판검사 우회로 4건 차단 + 설치본 드리프트 감시(`--check`) |
| [#15](https://github.com/bbiyakfather/market-deep-research/pull/15) | 완성 인포그래픽 탐색 하네스 — `## FIGURES` 마커, 도판 랭킹, G3 도판검사 |
| [#14](https://github.com/bbiyakfather/market-deep-research/pull/14) | 영수증 소유권 확립 — 소유 게이트 CLI 손기록 차단, G5 자기기록 |
| [#13](https://github.com/bbiyakfather/market-deep-research/pull/13) | 스킬 고도화 — 수집·검증 하네스 |

브랜치 정리(2026-08-10) 기록과 복구 명령은 `_planning/branch-cleanup-2026-08-10.md` 에 있습니다.
