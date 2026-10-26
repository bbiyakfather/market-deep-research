# 외부 스킬 저장소 3종 분석 → mdr 반영안 (2026-10-26)

대상: microsoft/flint-chart · MaryCache/imozuru · K-Dense-AI/scientific-agent-skills (셋 다 MIT).
방식: 저장소를 스크래치패드에 clone(코드 미실행·정적 열람) → sonnet 조사원 3명 병렬 분석 → 리드가 mdr 코드·참조문서와 대조.
조사원 원보고 3건은 세션 스크래치패드 `analysis-{flint-chart,imozuru,scientific-agent-skills}.md`(세션 종료 시 소멸, 요지는 이 문서에 전부 옮김).
사용자 지시: ① flint 는 최대한 반영 ② imozuru 의 "요약→세부→원문" 보존은 꼭 포함 ③ scientific 은 기술동향 분석 관점.

## 한 줄 요약
mdr 는 "원문이 실제로 있었다"(해시·캡처·리드 재열람)는 강하지만, **"그림이 사실대장과 같은 값인가"(flint)**, **"발췌가 원문 어느 행에 글자 그대로 있는가"(imozuru)**, **"검색을 어떤 식으로 몇 건 했는가"(scientific)** 세 가지를 기계로 묶지 못한다. 세 저장소는 각각 이 빈칸 하나씩을 메운다.

비유: mdr 는 영수증(캡처)과 봉인(해시)이 있는 회계장부다. flint 는 "차트는 장부 숫자로만 그려라"는 그래프 규정, imozuru 는 "인용마다 쪽·행을 적고 대조하라"는 각주 규정, scientific 은 "조사 절차 자체를 기록하라"는 실험노트 규정이다.

```
[요약층] report.md 문장 + F태그 ──┐
                                   ├─ 글자 대조(imozuru) ─▶ _sources/<sha12>_clean.txt:line-end  [원문층]
[세부층] evidence.verbatim ────────┘                          ▲ 해시·캡처(mdr 기존)
[그림]   assets/x.svg + x.chart.json{fact_id,value} ─ 값 대조(flint) ─▶ facts.jsonl confirmed
[절차]   audit/search-log.jsonl {query,n_returned,n_kept} (scientific) ─▶ 2부 커버리지 선언
```

---

## 1. flint-chart — "최대한 반영"

### 1.1 저장소가 하는 일
에이전트는 차트 유형·필드↔채널 매핑·시맨틱 타입만 JSON 으로 쓰고, 축·0기준선·색·포맷은 컴파일러가 결정한다. 52종 차트, 백엔드 5(Vega-Lite 등), `renderSvg()` 는 DOM 없이 SVG 생성(npm 의존). 번들 폰트에 한글 글리프 없음. 파이썬 배포 없음.

### 1.2 mdr 와의 격차(핵심)
| 항목 | flint | mdr 현재 | 판단 |
|---|---|---|---|
| 차트 유형 | 52 | `make_chart.py` 세로막대·선 2종 | visual-first 결정표 기본값인 **가로막대조차 없음** |
| 카디널리티 게이트 | 시리즈 12·히트맵 25·파이 8 | 막대 20 | 보강 |
| 그림↔사실대장 값 대조 | 없음(마크별 출처 없음) | F-ID·캡션태그·`[도판무결박]` 만 | **양쪽 없음 → mdr 가 만들 것** |
| 스펙 사이드카 | JSON=차트 | SVG 만 남음 | 재생성·감사 불가 |
| 0 기준선 | 길이 마크만 강제 | 선도 0 강제 | 선 납작해짐 |
| 색·접근성·헤드라인 규칙 | 3분류·대비 하한·제목=발견 문장 | 없음 | 문서 보강 |
| 값 라벨 | 유효숫자 3자리 반올림 | `value.raw` | **mdr 유지**(원칙 1) |
| 렌더 | vega·resvg(npm) | 자체 SVG→Chrome(의존 0) | mdr 유지 |

### 1.3 반영 항목
**A. 문서(쉬움, 전부 반영)**
- `visual-first.md` §1: 카디널리티 게이트(시리즈 12·히트맵 25·파이는 mdr 기존 5 유지 + "범주당 1행일 때만"), 식별자·연번 열은 축·색 금지, 독자 질문별 색인(순위=정렬 막대 / 구성=누적 / 추이=선 / 관계=산점), 막대 3종(단일 Bar · 부분-전체 Stacked · 값 비교 Grouped), 0 기준선(막대 0 고정, 선은 0 미포함 시 축 절단 표시), 사전 점검 3(합계행 혼합·단위 혼합·그룹 1개 붕괴), 색 3분류(범주/순서/발산)+낮을수록 좋은 지표의 경고색 방향, 접근성(대비 하한 면 1.25·선 1.6·라벨 3, 색만으로 구분 금지, 직접 라벨), 제목=발견 한 문장·부제=대상·기간·단위(fact 범위 초과 금지), 값 라벨은 `value.raw` 그대로(반올림 금지 명문화), 단위는 코드만·한정어는 부제.
- `image-research.md` §4: 자작 도판 Step 절차 + 검증 체크리스트(아래 §1.4 번안).
- `agent-briefs.md`: 워커는 차트 유형·F-ID·제목만 제안, 값·좌표·색 hex 금지. "모호하면 최소 선택지로 리드에 올린다".
- `verification-gates.md` §G4 육안 항목: 빈 차트·잘린 마크·라벨 겹침·범례 불가독·잘못된 인코딩·깨진 척도·축 누락·왜곡. 자동 지적은 확인 후 반영.
- 문서 말미 고지 1줄: `부분 인용: microsoft/flint-chart (MIT License, Copyright (c) Microsoft Corporation)`.

**B. 스크립트(순수 파이썬, flint 실행 없음)**
| # | 대상 | 내용 | 난도 |
|---|---|---|---|
| B1 | `make_chart.py` | `hbar`(값 정렬 가로)·`grouped`·`stacked100`·`scatter` 추가, confirmed 로더·단위 검사 재사용 | 중 |
| B2 | `make_chart.py` | `--sort`·`--top`; 막대 20·시리즈 12 초과는 **거부+기록**(flint 식 조용한 절단은 불채택) | 하 |
| B3 | `make_chart.py` | 선 차트 `--zero auto/include/data`, 0 미포함 시 SVG 에 표시 | 하 |
| B4 | 신규 사이드카 | `assets/<slug>.chart.json` = chart_spec + `data.values[{label,value,unit,fact_id}]` | 중 |
| B5 | `verify_facts.py` | `[도판값불일치]`: 사이드카 fact_id 가 confirmed · `value.raw`·unit 일치 · 캡션 F태그 포함. 사이드카 없는 기존 차트는 WARN | 중 · **핵심** |
| B6 | `visual_audit.py --figures` 또는 `chart_lint.py` | SVG 린트: 9pt↑·title/desc·FACTS 주석↔캡션·외부 URL 없음·한글 폰트 스택·대비 | 중 |
| B7 | `visual_audit.py` | 식별자 열 제외 확대·합계 행 혼합 경고 | 하 |
| B9 | `tests/test_chart_docs_sync.py` | 문서 유형명↔`make_chart` 지원 목록, 캡션 정규식↔`visual_audit`·`render_pdf` 일치(flint `skills.test.ts` 모방) | 하 |
| B8/B10 | `recommend_chart.py` 점수표 이식 / 하단 출처 기관·문서명 | 낮은 우선 |

**C. flint 본체 내장 — 주경로(2026-10-26 사용자 지시 "최대한 원문 가까이 내장, 그래프 다양하게")**

리드가 정적으로 확인한 사실(코드 미실행):
- `packages/flint-py` = flint 컴파일러의 **순수 파이썬 포트**(의존성 `python-dateutil` 1개, 약 11,400줄, MIT). 같은 `ChartAssemblyInput` 을 받아 **Vega-Lite 스펙 JSON** 을 낸다. PyPI 미배포("source-only preview") → **소스 내장(vendoring)이 곧 원문 내장**.
- 지원 유형 29종(템플릿 26): Bar·Grouped Bar·Stacked Bar·Bar Table·Line·Area·Streamgraph·Scatter·Connected Scatter·Regression·Strip·Jitter·Boxplot·Violin·Density·ECDF·Histogram·Heatmap·Pie·Rose·Radar·Pyramid·Lollipop·Bump·Slope·Ranged Dot·Waterfall·Candlestick·Gantt·KPI Card·Map/Geo. `tests/FULL_GALLERY_REPORT.md`: 갤러리 658/658 건이 JS 출력과 **바이트 동일**(Sunburst 만 JS 도 미지원).
- 폰트 패밀리를 스펙에 넣지 않음 → mdr 래퍼가 `config.font` 로 한글 폰트 주입 가능. 단 `core/compute_layout.py` 글자폭 추정 `APPROX_CHAR_WIDTH_RATIO=0.62` 는 라틴 기준 → 한글 라벨은 래퍼가 폭 보정(비율 ~1.0) 또는 라벨 길이 상한.
- 렌더: Vega-Lite→SVG 는 `vl-convert-python`(pip 휠, Node 불필요, 오프라인, `register_font_directory` 로 한글 폰트 등록)으로 가능 → 기존 `render_pdf.py` 경로 그대로. npm·vega 설치 불필요.

구성:
```
facts.jsonl(confirmed) ─▶ make_chart.py 래퍼 ─▶ ChartAssemblyInput{data.values[{…,fact_id}], semantic_types, chart_spec}
   │                         (vendored) scripts/flint/ assemble_vegalite() ─▶ Vega-Lite JSON ─▶ assets/<slug>.vl.json (사이드카, 재생성·감사)
   │                         vl_convert.vegalite_to_svg(+한글 폰트) ─▶ assets/<slug>.svg (+FACTS 주석)
   └─ verify_facts [도판값불일치]: vl.json data.values ↔ facts value.raw/unit, 캡션 F태그 ─▶ FAIL
```
- 내장 위치: `scripts/flint/`(flint-py `flint/` 패키지를 그대로 복사, LICENSE 동봉, 수정은 래퍼에서만 — 업스트림 추적 가능). 픽스처 `shared/test-data/` 일부(유형별 1건)도 `tests/fixtures/flint/` 로 가져와 **바이트 동일 테스트**를 mdr 에서 재현.
- 원칙 1 보호(래퍼에서 강제): ① 행은 confirmed fact 만, 행마다 `fact_id` ② `filter_overflow` 절단 발생 시 **FAIL**(조용한 절단 불허, `--top N` 으로 명시 선택만) ③ 집계(aggregate) 옵션 금지 — 값은 사실대장 그대로 ④ 값 라벨 포맷은 `value.raw` 문자열 필드로 공급(반올림 금지) ⑤ `logScale` 기본 off, 쓰면 캡션에 표기 ⑥ `includeZero` 막대 강제·선은 미포함 시 캡션 표기.
- `visual-first.md` 결정표 ↔ flint `chartType` 이름 매핑표를 문서에 두고 B9 테스트가 `scripts/flint` 템플릿 목록과 대조.
- 선검증(사용자 실행 필요, 외부 코드 실행 권한): 스크래치 venv 에 flint-py·vl-convert 설치 → 한글 라벨 10개 가로막대 1장 렌더 → 글리프·폭 확인(§5 명령).
- 기존 `make_chart.py` 의 자체 SVG 2종은 flint 경로 도입 후 폴백으로만 남기거나 제거.

**미반영(충돌)**: 호스팅 MCP(`flint.data-formulator.ai`)·Image-Charts(데이터 외부 송출, 대외비·오프라인 원칙 위배) / flint-js·flint-mcp(Node 경로, 파이썬 포트로 대체) / 인터랙션·보드·테마 14종·Excel 백엔드 / 값 반올림·k/M 압축·자동 절단.

### 1.4 그대로 옮길 원문 조각(`agent-skills/flint-chart-author/SKILL.md`)
- "Rule of thumb: comparing parts-to-whole → Stacked; comparing values side-by-side → Grouped; single series → Bar."
- "Sanity-read the values first — don't chart blind."(합계 혼합·단위·단일 엔티티 3항)
- 출처: "Never invent or guess one." / unit 은 데이터·문맥이 확증할 때만
- Validation checklist 7항 번안: ① 유형명이 지원 목록에 있음 ② 참조 필드(F-ID) 전부 실재 ③ 단위 명시 ④ 유형별 필수 채널 충족 ⑤ 옵션 범위 내 ⑥ 데이터 인라인·스타일 수작업 없음 ⑦ 합계/소계 행이 구성 행과 한 채널에 섞이지 않음
- `chart-type-recommendation.ts:209-211` 상수: `LOW_CARD_SERIES=12`, `LOW_CARD_AXIS=25`, `PIE_MAX_SLICES=8`

---

## 2. imozuru — "요약→세부→원문" 보존(필수 포함)

### 2.1 저장소가 하는 일
스킬 1개(`skills/imozuru`), 표준 라이브러리만. 해설 문장·발췌마다 `(file, line, end, 원문 그대로 text)` 를 붙이고, `report.verify` 가 원문 지정 행 ±2행에 그 text 가 **글자 그대로** 없으면 HTML 을 만들지 않는다(이전 산출물은 보존). 통과하면 앞뒤 6행을 `<details>` 로 접어 붙인다. 독자 UX: 해설 문장 클릭→바로 아래 인용→"前後を読む" ±6행→원 URL. 자기 한계를 명시: "대조로 확인되는 것은 인용이 원문에 있다는 데까지"(의미 검사 아님). 원문 재배포 금지, 번들에서 sources 제외.

### 2.2 mdr 와의 격차(핵심)
| 항목 | imozuru | mdr | 판단 |
|---|---|---|---|
| 원문 보존 | 이름 파일, 해시 없음 | `_sources/<sha12>_raw/_clean/.meta.json` | mdr 우위 |
| 원문 주소 | file+line+end | `evidence.locator` 자유형식, clean.txt 와 미연결 | 행 주소 없음 |
| 발췌↔원문 대조 | ±2행 글자 포함, 실패=빌드 중단 | `verify_facts.py:793~` verbatim **필드 존재·sha256 만**(리드 직접 확인) | **핵심 격차** — "원문에서 문자열 검색" 철칙이 규칙일 뿐 기계가 안 막음 |
| 앞뒤 맥락 | 항상 6행 | 없음 | 격차 |
| 의미 검사·캡처 | 없음 | claim-review·capture_review | mdr 우위 |
| 재배포 정책 | 명문 | `research-plan.md:33` 점검만 | 미명문 |

### 2.3 설계안 — 새 파일 체계 없이 세 층을 잇는다
층 정의: **원문층** = `_sources/<sha12>_clean.txt`(현행) / **세부층** = `evidence.verbatim` + 새 `span` / **요약층** = report.md F태그 문장(현행).

(a) 스키마: `assets/facts-schema.json` evidence 에 선택 필드 `span: {clean, line, end}`(locator 는 원 문서 좌표로 유지, span 은 clean.txt 행 좌표). 행 계산은 `split("\n")` 만(`splitlines()` 는 `\f` 를 세어 `grep -n` 과 어긋남 — imozuru 교훈).
(b) 게이트: `verify_facts.check_evidence_chain` 에 `verbatim ⊂ clean[line-2:end+2]` 대조(`…` 분절 허용, 공백·불릿 정규화). **v4 FAIL · v3 WARN**. `find_span` 실패 = 리드 confirm 불가(§[2] 철칙의 도구화).
(c) 도구: 신규 `scripts/span_tools.py` — `find_span`(verbatim 으로 행 자동 탐색, 리드 재열람 때 채움·워커는 행을 세지 않음) · `context`(±6행).
(d) 세부층 산출물: 신규 `build_evidence_pack.py`(~80줄, 읽기 전용) → `audit/evidence-pack/F###.md` + `INDEX.md`. 카드 = fact 1줄+status, evidence 별 verbatim·span·출처·접근시각·sha256·캡처 링크·앞뒤 6행. 새 서술 생성 없음. 같은 clean 의 다른 행을 인용한 evidence 는 같은 `observer_group`. `span.clean_sha256` 을 manifest 봉인에 얹을 수 있음.
(e) 고객/audit 분리(원칙 3·저작권):

| 층 | 고객 PDF | audit |
|---|---|---|
| 요약+F태그 | O | O |
| verbatim 단문+출처 | 현행 근거표 수준, 늘리지 않음 | O |
| 앞뒤 6행 맥락창 | X | O |
| 원문 전문 | **X** | O |

저작권법 제28조(공표 저작물의 인용)상 고객 PDF 는 단문 인용+출처가 안전선(법률 자문 아님, 배포 정책은 사용자 확인). evidence-pack 헤더에 `redistributable: true/false/unknown`, false/unknown 이면 audit 에도 해시·행 주소만 남기는 옵션(고객이 audit 번들을 함께 받는 경우 대비).
(f) 문서 수정: `extract-recipes.md` locator 표 1줄 / `agent-briefs.md` 철칙 "verbatim 은 clean 에서 글자 그대로 검색돼야 하며 줄임은 `…` 로만" / `verification-gates.md` §[2]·§G3 1줄씩 / `report-format.md` audit 절에 evidence-pack / `research-plan.md` 재배포 정책 명문.
(g) 수렴 조건 추가: [E] 루프에 "논점마다 원문 위치(span)가 붙었는가"(증거 기반 종료).

### 2.4 강화안(2026-10-26 사용자 지시 "현 계획보다 강화") — imozuru 의 거부·드릴다운·기록 장치를 전부 가져온다
위 (a)~(g) 는 evidence 단위 대조에 그친다. imozuru 가 실제로 하는 것은 **"인용 없는 문장은 산출물에 못 들어간다"** 이므로, 대조 단위를 문장으로 올리고 실패 시 산출물 생성 자체를 막는다.

| # | 강화 항목 | imozuru 원형 | mdr 반영 | 난도 |
|---|---|---|---|---|
| H1 | **문장 단위 인용 강제** | digest.py: summary·terms·answers 전부 quotes 필수, 없으면 거부 | report.md 의 F태그 문장마다 뒷받침 evidence(text_quote+span) ≥1 을 G3 가 검사. 캡처만 있는 fact 도 verbatim 필수(캡처 불가 사유 기록 시만 예외). v4 FAIL | 중 |
| H2 | **뒷받침 상태 3종** | extracts.json 상태 根拠あり/一部のみ/根拠なし | fact 에 `support: full/partial/none` 을 G3 가 자동 기입(verbatim 이 주체·수치·기간을 전부 덮으면 full, 일부면 partial). partial 은 본문에 `(일부 근거)` 표기 강제, none 은 본문 금지 → `claim-review.md` 축소 규칙과 결합 | 중 |
| H3 | **빌드 중단·이전 산출물 보존** | report.verify 실패 1건이면 HTML 미생성, `os.replace` 로 이전 페이지 유지 | `render_pdf.py` 가 G3 영수증 없으면 거부(현행) + 대조 실패 1건이면 PDF 미생성·기존 `report.pdf` 보존. v3 도 측정 기간 후 FAIL 로 승격 | 하 |
| H4 | **증빙판 HTML 드릴다운** | digest.html: 문장 클릭→인용→"前後を読む" ±6행→원 URL, `<details>` 접기 | 신규 `build_evidence_html.py` → `audit/evidence.html`(단일 파일·오프라인): 본문 문장 → 인용 카드(verbatim·span·출처·접근시각·sha256·캡처 썸네일) → ±6행 맥락 → `_sources/<sha12>_clean.txt` 상대 링크. 근거를 절 끝에 모으지 않고 문장 바로 아래. **고객 증빙판**은 `--customer` 로 맥락창·전문 링크 제거(§2.3(e) 분리표 준수) | 중 |
| H5 | **검색 전건 기록** | queries.jsonl: 빈 검색어 포함 전건 | §3.3 S1 `audit/search-log.jsonl` 과 동일 항목 → 하나로 통합. evidence.html 끝에 "검색 기록" 절 자동 생성 | 하 |
| H6 | **본문 하한(벽·404 판정)** | fetch.py: PDF 3,000자·HTML 1,000자 미만은 본문 아님 | `fetch.py validate_body` 에 글자 수 하한 추가(PDF 3,000·HTML 1,000, 한글은 별도 측정 후 조정). 미달은 `audit/failed-sources` 로, 스냅샷 불인정 | 하 |
| H7 | **원문 보정 금지 표지** | 자동자막 등 불완전 원문은 고치지 않고 표지 | evidence 에 `raw_quality: ocr/auto-caption/scan` 표지, verbatim 은 원문 그대로(오타 포함), 대조도 원문 기준 | 하 |
| H8 | **특수 원문 locator** | 영상 `[mm:ss]`, 2단 PDF 분절 `…` 순서 대조 | span 에 `t: "mm:ss"`(영상·오디오) 허용, 분절 verbatim 은 조각 순서대로 포함 검사 | 하 |
| H9 | **증거 기반 종료** | 논점마다 파일:행+인용 붙으면 종료, 확신도 아님 | [E] 수렴 조건에 "research-plan 논점(축별 충분조건)마다 span 붙은 confirmed fact ≥1" 추가, 미충족 축은 미수렴 | 하 |
| H10 | **출처 유형 표지** | 〔論文〕〔本人〕〔観察〕〔まとめ〕〔公式〕 점수 없음 | 인용 카드에 `source-ladder.md` 계층 표지(1차 공시/공식통계/동료심사/보도/2차 종합) 표시, 점수화 금지 | 하 |
| H11 | **테스트 번안** | test_digest·test_report_links | 바꿔 쓴 인용 거부 · 인용 없는 문장 거부 · `_sources` 밖 경로 거부 · 실패 시 이전 PDF 유지 · URL↔파일 수 불일치 시 링크 미부착 | 중 |

난도·순서: (a)(b)(c) span+대조 **WARN 으로 기존 불일치율 측정**(기존 v3 는 한국어·PDF 줄바꿈 불일치 많을 가능성) → H6·H7·H8 fetch·스키마 → H1·H2 문장 단위 FAIL(신규 v4) → H3 빌드 중단 → H4·H5 evidence.html → H9·H10 → H11 테스트.
일부러 뺀 것: Lv1~3 난이도별 해설·퀴즈·대시보드(전 조사 이력)·watch.py RSS(별도 `mdr-search` 영역).

---

## 3. scientific-agent-skills — 기술동향 분석 관점

### 3.1 저장소가 하는 일
177 스킬(v2.72.0), 생명과학 중심. **기술동향 전용 스킬(TRL·bibliometrics·토픽모델·특허동향)은 0건.** 가져올 가치는 방법론·규약 5가지: 검색 재현 규약 / 학술 API 18종의 "HTTP 200 인데 실패" 함정 / 기록·보고서·연구 독립성 규칙 / claim ledger 필드 / 스킬 품질 자동화.

적합도 상: `paper-lookup`(학술 API 18종 재현 조회, 대부분 키 불필요) · `literature-review`(체계적 고찰 7단계) · `market-research-reports`(증거추적 ledger, 완전 오프라인). 하(충돌): 유료 검색(parallel/exa/research-lookup)·OpenRouter 도식·timesfm 모델 예측·scholar-evaluation 점수화.

### 3.2 mdr 와의 격차
| 항목 | 저장소 | mdr | 격차 |
|---|---|---|---|
| 학술 출처 계층 | API 18종+선택표+함정 문서 | `search.py --type academic` = arXiv 만 | **큼** |
| 검색 기록 | DB·검색일·검색식·건수 템플릿, "Fail visible, not plausible." | 로그·스냅샷은 있으나 쿼리별 건수 비정형 | 중 |
| 완전성 대조 | 총건수 선계수→안정 정렬→기대/회수/필터후 대조 | `max(3, n//2)` 보강·"완전성 미보장" 고지 | 중 |
| 선별 기록 | 단계별 제외 건수·사유 | 없음 | 중 |
| 문장 분류 | 7종(fact/estimate/calc/forecast/opinion…) | `risk` 2단계+증거유형 6종 | 전망·의견 구분 없음 |
| 근거 등급 | GRADE 하향 5요인(합산 금지) | 표 `* 주 :` 단서 | 중 |
| 철회·정정 | Crossref `update-type:retraction` | 없음 | 소 |
| 사실 검증·특허·오프라인 PDF | CSV 매핑 감사 / USPTO(중단) / pandoc | 전건 재열람·캡처·해시 / KIPRIS·Patent MCP / Chrome | **mdr 우위** |
| 서지 지표·TRL·축별 충분조건 기본값 | 없음 | 없음(필드만) | 양쪽 공백 → mdr 가 채움 |

### 3.3 반영 항목
| # | 어디에 | 무엇을 | 무료 | 난도 |
|---|---|---|---|---|
| S1 | `search.py`·`source-ladder.md`·`research-plan.md` | `audit/search-log.jsonl` 호출마다 `{ts,axis,tier,query,filters,n_requested,n_returned,n_kept}`; 2부 커버리지 선언을 여기서 집계. research-plan 에 **용어 확장표**(동의어·약어·한영·상하위어) 1행 | — | 하~중 |
| S2 | `search.py --type academic` + 신규 `references/academic-apis.md` | OpenAlex·Crossref·Europe PMC·Semantic Scholar 어댑터. 함정: arXiv `Error` 항목·1req/3s, bioRxiv 키워드 검색 없음→Europe PMC, Unpaywall 실이메일, Crossref `mailto` polite pool, OpenAlex 10,000 상한→cursor, "Never present metadata as full text." | 키 없이 가능(OpenAlex 는 예산제: 키 없이 $0.10/일·무료키 $1/일, 단건 무료 — 약관 재확인) | 중 |
| S3 | `source-ladder.md` 학술 소절 6줄 | ① 레코드≠보고서≠연구: 프리프린트·학술지판·보도자료·학회초록은 독립 관찰 **1건** ② DOI 실존≠근거, 수치는 원문 재열람 ③ 집계처(OpenAlex·S2·특허DB)≠독립 교차 ④ 인용수는 읽는 순서용, 포함 기준 아님 ⑤ `preprint` 태그+학술지판 상태 ⑥ Crossref 철회 1회 확인, 없으면 "확인한 출처 내 공지 없음" | — | 하 |
| S4 | `facts_db.py`·`extract-recipes.md` | `statement_class`(사실/추정/계산/전망/의견), `retrieved`/`as_of` 분리, `revision_status`, `taxonomy_version`. 전망을 사실로 쓰는 사고를 기계로 차단 | — | 하~중 |
| S5 | `research-plan.md` | 기술동향 **축별 충분조건 기본값 표**(축 이름은 report-format 단일진실원 참조): 기술요소=분류체계 1·방식별 1차 문헌 1↑·OpenAlex 연도별 건수 곡선(검색식·일자·건수 기록) / 플레이어=OpenAlex 기관 집계+특허 출원인 순위·자체 공시 1↑·ROR 동일성·보도자료 단독 금지 / 시장=기준 보고서 1+독립 근거 1·정의·기간·지역·단위 일치표·발행처 수치는 estimate / 정책=법령 원문·시행일·개정이력·부재는 `negative_search` / 교차="Never choose the most convenient number silently." | — | 하 |
| S6 | `extract-recipes.md` | OpenAlex 서지 레시피: `group_by=publication_year`·기관 상위 N·국가 비중·토픽·철회 필터. 건수·비중·CAGR 한정, 색인 범위 변화 단서 1줄 | 무료 범위 | 중 |
| S7 | 신규 `references/trl-evidence.md`(또는 report-format 4부) | TRL 단계별 인정 증거(시연 논문·파일럿·상용 출시·인증)/불인정(보도자료 "개발 성공" 단독). 외부 표준(NASA·ISO 16290) 출처 조사 필요 | — | 하~중 |
| S8 | `verification-gates.md` G3·`report-format.md` 6부 | 축별 근거 확실성 라벨 1개 + 하향 사유 코드 5(벤더·보도자료 / 출처간 상충 / 정의·지역·기간 불일치 / 단일출처·범위폭 / 부정결과 미관측). **점수화·합산 금지** | — | 하 |

금지: 유료 검색 의존·OpenRouter 도식·모델 예측·PRISMA 정식 흐름도(4줄 계수표로 충분)·2인 독립 선별·점수화.

### 3.4 스킬 운영 규약에서 가져올 것(mdr 참조문서 관리)
1. 참조 링크 실존 린트(`references/*.md` 상호참조 깨짐 탐지, 의존 0). 2. 단일진실원 grep(축 이름 재등장 탐지). 3. 외부 의존 주장에 `(검증 YYYY-MM-DD)`. 4. 스크립트 첫머리 능력·한계 선언. 5. reference 길이 기준(예 150줄). 6. `--help` 계약을 `preflight.py` 에. 7. 외부 코드 도입은 스캐너보다 줄 단위 수동 검토(저장소 자체 스캔에서 서지 스킬 다수가 Critical). 8. 로그의 api_key·email 마스킹 점검. 9. "이 스킬이 하지 않는 것" 범위 규약.

---

## 4. 통합 우선순위(제안)
(2026-10-26 사용자 지시 반영: flint 본체 내장·imozuru 강화가 주경로)

| 순 | 항목 | 이유 |
|---|---|---|
| 0 | **flint-py 선검증**(§5 명령, 사용자 실행) | 한글 라벨·vl-convert 렌더가 안 되면 C 경로 설계가 바뀜 |
| 1 | imozuru §2.3 (a)(b)(c): span 필드 + verbatim 글자 대조 WARN + `find_span` | 원칙 2 의 철칙을 처음으로 기계화. 현 불일치율 측정이 선행 |
| 2 | **flint C 내장**: `scripts/flint/` vendoring + 래퍼 + `.vl.json` 사이드카 + `[도판값불일치]`(B4·B5 흡수) + 바이트 동일 테스트 | 29종 차트를 원문 그대로, 그림↔사실대장 결박 |
| 3 | flint A 문서 전부(결정표↔chartType 매핑표 포함) + B2·B3·B6·B7·B9 | 래퍼 규칙·린트 |
| 4 | imozuru 강화 H6·H7·H8 → H1·H2·H3 → H4·H5 | 문장 단위 인용 강제·빌드 중단·증빙판 HTML |
| 5 | scientific S1(=H5)·S3·S5 → S4 → S2·S6·S7·S8 | 기술동향 조사 품질 |
| 6 | imozuru H9·H10·H11, scientific §3.4 운영 규약 | 마무리 |
| 보류 | flint-js/flint-mcp Node 경로, scientific 유료·모델 예측 | 파이썬 포트로 대체 / 원칙 충돌 |

## 5. 리드가 직접 확인한 것 / 못 한 것
- 확인: `verify_facts.py:793~873` 은 verbatim **존재·sha256** 만 검사(원문 포함 검사 없음). flint 상수 `chart-type-recommendation.ts:209-211`, Validation checklist 7항 원문. flint-py 존재·의존성·29종·658건 바이트 동일 보고서·폰트 미지정·글자폭 0.62(정적 열람).
- 못 함: 세 저장소 모두 코드 미실행(외부 코드 실행 권한 거부). scientific 은 177 중 ~25 스킬만 열람. TRL 외부 표준·OpenAlex 가격·저작권 해석은 추가 확인 필요. imozuru §5 잔여 아이디어는 전송 잘림으로 일부 누락(핵심은 §2.4 H9 에 반영).
- **flint-py 선검증 명령**(사용자가 `!` 로 실행; 스크래치 venv, 저장소 밖):
```bash
cd "C:/Users/김형일/AppData/Local/Temp/claude/D--skills-market-deep-research/064204d7-44e9-4844-ab33-0a960ecfa846/scratchpad"   # 세션 스크래치패드
python -m venv flintenv                                                            # 격리 venv
flintenv/Scripts/python -m pip install -q -e repos/flint-chart/packages/flint-py vl-convert-python pytest   # flint-py 소스 + 렌더러
flintenv/Scripts/python -I probe_flint_ko.py                                       # 한글 가로막대 1장 → probe_ko.svg/png
cd repos/flint-chart/packages/flint-py && ../../../../flintenv/Scripts/python -m pytest -q    # 바이트 동일 픽스처 테스트
```
확인할 것: `probe_ko.png` 에서 한글 라벨 글리프·잘림, pytest 통과 수(보고서상 658 pass).
- 다음 단계(사용자 결정 후): memory 교정대로 **조사 PRD → 모듈 PRD** 순. 이 문서가 조사 결과이며, 반영 PRD 는 별도.
