---
name: market-research-assistant
description: >-
  기술사업화 기관용 증빙형(fact + evidence) 시장조사 보고서를 생성한다. 기술동향·산업동향·
  기관/기업 실사·시장조사 요청에 사용한다. 트리거 예: "OO 기술동향 조사해줘", "OO기업 실사해줘",
  "OO 시장조사 보고서 만들어줘", "OO 산업동향 정리해줘", "OO 기관 실사 자료". 모든 수치를
  [조사내용 → 출처 → 스크린샷] 증거구조로 고정하고, 팀리드가 전건 재검증한 뒤 GitHub 스타일
  PDF(고객용)와 내부 audit 번들을 함께 낸다. 단순 웹검색·사실 한두 개 확인·요약 등 증빙형
  보고서가 필요 없는 일반 질문에는 트리거하지 않는다.
---

# market-research-assistant — 증빙형 시장조사 보고서 스킬

> **한 줄**: 조사마다 수치가 달라지는 문제를 [조사내용 → 출처 → 증빙] 증거구조 + 사실대장 +
> 검증게이트로 제거하고, 고객용 팩트시트 PDF와 내부 audit 번들을 분리 산출한다.

## 원칙 (읽고 시작)

- **팀리드(메인 세션)가 오케스트레이터**다. 조사원은 sonnet 서브에이전트(팬아웃·저비용). 수집·1차구조화는 조사원, **재검증·확정·종합은 팀리드**가 한다.
- 모든 사실성 수치는 **fact(F) + evidence(E)** 로 대장에 등재되고, 본문에서 `(Fxxx)` 태그를 단다. 무출처 주장은 등재 불가·본문 불가.
- **confirmed는 팀리드만** 만든다(원문 재열람 이벤트 필수). verifier 서브에이전트를 써도 그 의견은 보조일 뿐이다.
- 증빙은 **source_capture만 인정**(원문 실화면/PDF 크롭). 재구성 발췌는 증빙이 아니다.
- 산출물은 **고객용 report.pdf**(확정된 것만)와 **내부 audit 번들**(폐기·실패·검증이력)로 **분리**한다.

## 스크립트 호출 규약 (필수)

- **반드시 직접 경로**로 호출한다: `python <SKILL>/scripts/<name>.py …`. `<SKILL>` = 스킬 루트 절대경로(예: 설치본 `~/.claude/skills/market-research-assistant`).
- `python -m scripts.<name>` 형태는 쓰지 않는다 — 전 스크립트가 sys.path 부트스트랩으로 `-m`에서도 동작은 하지만, 규약은 **직접 경로 한 가지로 통일**한다(경로 혼동·회귀 방지).
- 팀리드는 **작업폴더(`<WORK>`)를 현재 디렉터리로** 두고 실행한다 → 스크립트의 상대 기본값(`_sources/`·`_captures/`·`facts.jsonl` 등)이 그대로 맞는다. work_dir 인자는 `.`로 넘긴다.
- 모든 스크립트는 `--selfcheck`를 갖는다(설치 후 스모크에 사용).

### 스크립트 CLI (소스 argparse와 1:1)

| 스크립트 | 호출 | exit / 판정 |
|---|---|---|
| skill_paths | `skill_paths.py --preflight [--json]` | 필수 의존성 하나라도 없으면 **exit 1** |
| search | `search.py "쿼리" [--n 10] [--type web\|news\|academic\|filing] [--json] [--no-cache]` | 결과 有=0 / 無=1 / **미지원 --type=2** |
| fetch | `fetch.py <URL> [--out _sources/] [--keywords k1,k2] [--max-bytes N] [--timeout S] [--json]` | ok·partial_ogp=0 / 그 외=2 |
| facts_db | `facts_db.py ingest <WORK> <input.jsonl> [--dry-run]` | 스키마위반·중복ID·tid누락 시 exit 1. `--dry-run`=쓰지 않고 **전 위반 수집** 보고(위반 有=exit 1) — 조사원 자가검증·팀리드 사전스캔용 |
| facts_db | `facts_db.py add-event <WORK> <fact_id> --action reread --result match [--by lead] [--evidence-id E..] [--source-url ..] [--note ..]` | — |
| facts_db | `facts_db.py set-status <WORK> <fact_id> {pending\|confirmed\|disputed\|superseded\|discarded} [--by lead] [--note ..] [--discard-reason ..]` | 전이 위반 시 exit 1 |
| facts_db | `facts_db.py set-capture <WORK> <evidence_id> <capture_path>` | 파일부재·_reconstructed 경로 시 exit 1 |
| facts_db | `facts_db.py diff <old.jsonl> <new.jsonl>` | 값변동/정의변동/추가/삭제 리포트 |
| manifest | `manifest.py update <WORK>` · `manifest.py verify <WORK>` | verify: 변경 有 시 **exit 1**(G3 재실행 트리거) |
| capture_pdf | `capture_pdf.py --pdf <path> --needle "300,900" --evidence E001 [--out _captures/] [--page N] [--pad 90]` | ok=0 / not_found·fallback_page=1 / error=2. 기본 크롭=가로 전폭+세로 ±pad(문맥 포함) |
| capture_web | `capture_web.py --text <파일\|문자열> --evidence E012 [--out _reconstructed/] [--source-url URL]` | 재구성물(증빙 **불인정**), `_captures/` 경로 거부 |
| verify_facts | `verify_facts.py --report report.md --facts facts.jsonl [--work .] [--strict] [--convert-on] [--json]` | violation 1건이라도 있으면 **exit 1** |
| render_pdf | `render_pdf.py --md report.md [--style <SKILL>/assets/style.html] [--out report.pdf]` | 실패 시 exit 2 |
| preview_pdf | `preview_pdf.py --pdf report.pdf [--pages 1-3,5] [--dpi 110] [--out _preview/]` | 페이지별 PNG 생성 |

## 작업폴더 규약

`skill_paths` 모듈이 규약을 정의한다(전용 CLI 없음 — 아래 스니펫으로 생성).

```
python -c "import sys; sys.path.insert(0, r'<SKILL>/scripts'); import skill_paths as S; \
w=S.work_dir('<주제>', create=True); S.subdirs(w, create=True); print(w)"
```

생성 결과 `research_<슬러그>_<YYYYMMDD>/`(충돌 시 `_2`,`_3` …) 아래:

```
<WORK>/
  _sources/         원본 스냅샷 + SHA-256 (팀리드)
  _research/<agent>/  조사원 원자료 보존 (에이전트별 전용, 무수정)
  _captures/        source_capture — 증빙 인정 (E<ID>.png)
  _reconstructed/   재구성 발췌 — 증빙 불인정 (내부용)
  _media/           대표이미지·개요도 — 참고 삽화 (증빙 아님, 출처 캡션 필수)
  audit/            내부 audit 번들
  facts.jsonl  manifest.json  report.md  report.pdf
```

`<WORK>`의 **부모(조사 실행 루트)** 에는 여러 조사가 공유하는 `ref/`(엄선한 A급 원문 리포트 보존, `report-format.md §3b`)를 둔다.

이후 팀리드는 `<WORK>`를 cwd로 두고 작업한다.

## 오케스트레이션 파이프라인 (게이트 G0~G5)

```
[G0] preflight + 조사계획 확정 ── skill_paths.py --preflight(누락 시 중단),
      AskUserQuestion으로 조사유형·범위·조사종료기준·환산옵션(기본 OFF)·출력형식 확정,
      보고서 목차 초안(장별 핵심질문·필요수치·담당) 선제안·승인 + 기준출처(anchor) 합의.
      기관/기업 조사면 entity-identity 게이트(entity_id 확정) 선행.
[1]  병렬 조사 ────────── 조사원 sonnet 서브에이전트 팬아웃(background),
      에이전트별 _research/<agent>/ 전용 폴더, agent-briefs 브리프, 반환=temp JSONL.
[G1] join + 수집 게이트 ── 완료/timeout/부분실패 처리, raw 보존,
      facts_db.py ingest(채번 F/E·재매핑·스키마검증). 무출처 주장 즉시 discarded.
[2]  팀리드 재검증 ─────── ★전건. 각 fact 원문 재열람 → add-event(reread/match) → set-status confirmed.
[G2] 증빙 게이트 ──────── confirmed 전건 source_capture(capture_pdf / 실화면 스크린샷).
      재구성 발췌는 증빙 불인정 → 캡처 불가 시 대체출처 or 미확인 유지.
[3]  보고서 작성 ──────── 고객용 report.md(3중 구조) + audit/ 번들 동시 생성.
[G3] verify_facts + manifest ── manifest update → verify_facts 실패 0 필수. 위반 시 수정 후 재실행.
[4]  render_pdf ───────── GitHub 스타일 오프라인 PDF (pandoc → HeadlessChrome).
[G4] preview_pdf ──────── 팀리드가 페이지 PNG를 Read로 육안검증.
[G5] 최종 무결성 ──────── manifest verify + PDF에서 F태그·링크·캡처 수 재검사. 변경 시 G3 복귀.
```

각 게이트는 **통과/차단 이분법**이다("대충 됐음" 없음). 판정 문장은 `references/verification-gates.md`가 단일 기준이다.

---

## G0 — preflight + 조사계획 확정

1. **의존성 점검**: `python <SKILL>/scripts/skill_paths.py --preflight`. 필수(python·fitz·curl_cffi·trafilatura·playwright·pandoc·chrome) 중 하나라도 `ABSENT`면 **exit 1** — 진행하지 말고 누락 목록을 사용자에게 보고하고 설치를 안내한다(yt_dlp는 optional, 경고만).
2. **요구사항 확정 — AskUserQuestion 도구 사용**(필수): 조사유형 · 범위 · **조사 종료 기준**(예: 핵심 수치 N건 확인 또는 1차출처 소진) · **환산옵션(기본 OFF)** · 출력형식을 **선택지 형태(권장안 명시)** 로 묻는다. 모호함을 안고 팬아웃하면 조사원 토큰 전체가 헛돌기 때문에, 가장 싼 지점(G0)에서 모호함을 제거한다.
3. **목차 선제안**: "하나의 보고서를 쓴다"는 계획으로, 팬아웃 **전에** 목차 초안(각 장 = 핵심 질문 + 필요 수치 + 담당 조사원)을 사용자에게 제안·승인받는다. 이 목차가 조사원 분담과 보고서 구조의 단일 기준이다.
4. **기준출처(anchor source) 합의**: 기관마다 수치가 갈리는 지표(시장규모·설치용량 등)는 대표 기준 출처(예: 수소 분야 IEA)를 사용자와 합의해 목차에 명시한다. 타 출처는 병기(disputed)하되 본문 대표 서술은 기준출처를 따른다.
5. **기관/기업 조사면 entity-identity 게이트 선행**: 조사원 팬아웃 **전에** 각 대상의 `context.entity_id`(사업자등록번호 > 법인등록번호 > 정식법인명+주소, 해외는 LEI/CIK/DUNS)를 확정한다. 미확정 대상은 조사하지 않는다. 규범은 `references/entity-identity.md`.
6. **작업폴더 생성**: 위 「작업폴더 규약」 스니펫으로 `<WORK>` + 하위폴더를 만들고 cwd를 `<WORK>`로 옮긴다.

→ 상세: `references/verification-gates.md §G0`, `references/entity-identity.md`.

## [1] 병렬 조사 (조사원 팬아웃)

- **모델·실행**: 조사원 = **sonnet 서브에이전트**, background 병렬. 재검증·종합은 메인 세션(팀리드). 팀리드가 메인 세션이 아닌 컨텍스트(서브 세션/백그라운드 잡)면 **이름 없는(anonymous) 서브에이전트**로 팬아웃한다(named 팬아웃은 거부될 수 있음).
- **파일 충돌 방지**: 각 조사원은 **자기 전용 `_research/<agent명>/` 폴더에만** 쓴다. `_sources/`·`_captures/`·`facts.jsonl`·`manifest.json`은 **팀리드 전용**(조사원 접근 금지).
- **브리프**: 팀리드는 `references/agent-briefs.md §1` 골격에 담당범위·조사유형변형(§3)·확정된 `entity_id`를 채워 각 조사원에 넣는다. **철칙(§4)은 전문 그대로** 포함(축약 금지 — 원문 지시 방어). **스키마 하드룰(§2)** — source_role enum 3종 그대로·locator null 금지·verbatim 원문 그대로 — 도 브리프에 명시한다(실전에서 가장 많이 깨진 지점).
- **제출 전 자가검증**: 조사원은 `python <SKILL>/scripts/facts_db.py ingest _research/<agent> _research/<agent>/output.jsonl --dry-run`으로 **위반 0을 확인한 뒤에만 제출**한다(한 라인 위반이 파일 전체 등재를 막는다).
- **도구**(조사원 브리프에 명시): 검색 `python <SKILL>/scripts/search.py "쿼리" --n 10 --type …`(+내장 WebSearch 병행), 수집 `python <SKILL>/scripts/fetch.py <URL> --out _research/<agent>/raw/`. source-ladder 폴백은 `references/source-ladder.md`, 추출·locator는 `references/extract-recipes.md`.
- **반환**: `_research/<agent>/output.jsonl`(temp 스키마 — `tid`/`fact_tid`/`evidence_tids`/`proposed_grade`, **정식 F/E ID·확정 grade 아님**) + `insights.md`(`## 인사이트` [사실]/[추론] 구분·근거 TF-ID, `## 요약` 건수·등급분포·폐기 리드).

→ 상세: `references/agent-briefs.md`, `references/source-ladder.md`, `references/extract-recipes.md`.

## G1 — join + 수집 게이트

1. **join**: 전 조사원의 완료/timeout/부분실패를 처리한다. timeout·부분실패 에이전트가 낸 분까지는 살리되, 무엇이 누락됐는지 기록한다.
2. **raw 보존**: `_research/<agent>/` 산출물을 무수정 보존(audit 대상).
3. **등재**: `python <SKILL>/scripts/facts_db.py ingest . _research/<agent>/output.jsonl`(에이전트별로). ingest가 temp ID(TF/TE)를 **run 단위 전역 순번으로 채번**(F###/E###)하고 참조를 재매핑하며, `proposed_grade`→`grade` 승격·`claim_key` 생성·`status=pending` 설정 후 **정식 스키마 검증**(`assets/facts-schema.json`)을 통과한 것만 원자적 append한다. 중복 ID·tid 누락·스키마 위반은 거부(exit 1).
4. **거부 처리**: 본등재(ingest)는 첫 위반에서 멈춘다. 위반이 나오면 같은 파일을 `--dry-run`으로 다시 돌려 **전 위반 목록을 일괄 확보**(dry-run은 멈추지 않고 전건 수집)한 뒤, 조사원에 **제한적 재요청 1회**로 끝낸다. 반복 실패는 폐기.
5. **무출처 폐기**: 근거(evidence) 없는 주장은 즉시 `discarded` — `set-status . <fact_id> discarded --discard-reason "무출처"` 후 `audit/discarded.md`에 사유 기록.
6. 등재 초기 status: 근거 있으나 미재검증 = `pending`, 상충 = `disputed`(note 필수), 시계열 갱신 = `superseded`(note 필수).

→ 상세: `references/verification-gates.md §G1`, 스키마 = `assets/facts-schema.json`.

## [2] 팀리드 재검증 (보고서 진입 전건)

**★ 보고서 본문에 오를 모든 fact는 팀리드가 원문을 직접 재열람해 확정한다.** 조사원 신뢰로 건너뛰지 않는다.

각 fact마다:
1. **원문 재열람**: evidence의 `source_url`/`local`을 팀리드가 직접 다시 연다(WebFetch 또는 `python <SKILL>/scripts/fetch.py <URL>`). 로컬 PDF는 `_sources/`의 원본(SHA-256 고정)을 fitz로 확인.
2. **대조**: `verbatim`(text_quote) 또는 `locator`(page/row/col 등)가 원문과 **정확히 일치**하는지 육안 확인. 값·단위·기간·주체(entity)·정의가 fact `context`와 맞는지 본다.
3. **이벤트 기록**: `python <SKILL>/scripts/facts_db.py add-event . <fact_id> --by lead --action reread --result match --evidence-id <E..> --source-url <URL>`. 불일치면 `--result mismatch`로 남기고 confirmed로 올리지 않는다.
4. **확정**: `python <SKILL>/scripts/facts_db.py set-status . <fact_id> confirmed`. facts_db가 **evidence ≥ 1 AND lead의 {reread,match} 이벤트 존재**를 강제하므로, 둘을 만족해야만 confirmed가 된다(그 외엔 거부).
5. **독립성 판정**: 같은 보도자료를 여러 매체가 전재한 경우 각 evidence를 `source_role:"보도자료"`로 두고 **1출처로 합산**한다. 독립 출처 수를 부풀리지 않는다.
6. **verifier 단독 금지**: 검증 서브에이전트를 쓰더라도 confirm은 팀리드(`--by lead`)만 한다.

→ 상세: `references/verification-gates.md §G2`, 등급 판정 = `§4`.

## G2 — 증빙 게이트

confirmed 전건에 **source_capture**를 만든다(핵심 수치는 필수).

- **로컬/다운로드 PDF**: `python <SKILL>/scripts/capture_pdf.py --pdf _sources/<file>.pdf --needle "<정확한 숫자>" --evidence <E..> --out _captures/`. `--needle`은 **정확 숫자**(부분문자열 금지 — `300`으로 `3000`을 잡지 않도록). ok면 `_captures/<E..>.png` 생성(exit 0), `not_found`/`fallback_page`(스캔 PDF)면 exit 1 — 성공 파일명을 만들지 않으므로 **대체출처 or 미확인 유지**로 처리. 기본 크롭은 **가로 전폭 + 세로 ±90pt 문맥 포함**(`--pad`로 조정) — 숫자만 잘린 **파편 크롭은 증빙 가치가 없다**(주변 문장·표 헤더가 보여야 함).
- **접근 가능한 웹**: playwright MCP로 **실화면 스크린샷**(재구성 아님) + 메타 결박(최종 URL·시각·viewport·locator). 로그인/CAPTCHA/paywall 뒤 화면은 촬영하지 않는다(우회 금지).
- **캡처 결박**: 생성한 캡처 경로를 해당 evidence의 `capture` 필드에 기록한다 — `python <SKILL>/scripts/facts_db.py set-capture . <E..> _captures/<E..>.png`. 파일이 실재해야 하고 `_reconstructed/` 경로는 거부되며(증빙 불인정), 스키마 재검증 후 원자적으로 재작성된다(위반 시 exit 1). 오귀속 여부는 `references/evidence-capture.md §6` 체크리스트로 육안 확인.

- **재구성 발췌 금지선**: `capture_web.py`(insert_htmlbox)는 **증빙 불인정**(`_reconstructed/`, 워터마크). 내부 audit 참고용일 뿐 고객 보고서·증빙표에 싣지 않으며 confirmed 근거가 될 수 없다.

→ 상세: `references/evidence-capture.md`, `references/verification-gates.md §G2`.

## [3] 보고서 작성

`references/report-format.md` 양식으로 **두 산출물을 동시** 생성한다.

- **고객용 `report.md`** — 섹션마다 3중 구조: ① 서술 본문(배경→메커니즘→수치→의의→⚠주의점, 수치엔 `(Fxxx)` 태그) ② 근거표(사실|수치|출처링크|4차원 등급|증빙) ③ source_capture + 캡션(수치↔원문 위치 매핑, 문맥 크롭) ④(선택) 대표 이미지·개요도(`_media/`, 출처 캡션 필수, F태그 없음 — `evidence-capture.md §5`). 말미: 한눈에 요약표 / 조사팀 인사이트([사실]/[추론]·근거 F-ID) / 한계와 반론(개수 고정 없음, 근거 있을 때만). **폐기목록·실패 URL·미확인 의혹은 넣지 않는다.**
  - 렌더 문법(render_pdf가 `gfm+fenced_divs+bracketed_spans`로 파싱): 주의박스 `::: {.caution}`, 증빙박스 `::: {.evidence-box}`, 강조 태그 `[300조 원]{.ftag}`. 캡처는 상대경로 `![캡션](_captures/E001.png)`.
- **내부 audit/ 번들** — `facts_all`(전수표), `discarded.md`(폐기+사유), `failed_sources.md`(실패 URL+사유코드), `verify_log.md`(verify_events 전개), `raw_agent_output/`(_research 복사), `manifest.json`.

→ 상세: `references/report-format.md`.

## G3 — verify_facts + manifest (실패 0)

report.md·캡처·원본이 모두 최종 상태일 때:
1. `python <SKILL>/scripts/manifest.py update .` — `_sources/`·`_captures/`·`_reconstructed/`·`facts.jsonl`·`report.md`의 SHA-256을 고정.
2. `python <SKILL>/scripts/verify_facts.py --report report.md --facts facts.jsonl --work .` — 아래 8검사 중 **violation 0**이어야 통과(하나라도 있으면 exit 1). 환산 ON이면 `--convert-on` 추가, 연도 단독 무태그까지 막으려면 `--strict`.
   1. 본문/부록 분리 파싱(부록 태그는 본문 사용으로 미계산 — 부록 우회 차단)
   2. 본문 무태그 사실성 숫자 탐지
   3. `(Fxxx)` 태그 존재 + `status:"confirmed"` + lead reread match + 값·단위·기간·주체 **의미 대조**(오태그 차단)
   4. confirmed인데 본문 미사용 fact(경고)
   5. evidence 필수필드(`source_url·type·sha256·accessed_at·grade` 4차원, text_quote는 `verbatim`) 전 레코드 재검증
   6. source_capture 실재 + 파일명↔ID + `_reconstructed` 증빙 불인정
   7. manifest 해시 대조(변경 시 위반 → G3 재실행)
   8. `[--convert-on]` 본문 영어 통화단어 0 + calculation 재계산 대조
3. **위반 수정 루프**: violation이 있으면 원인을 고친 뒤 **`manifest.py update .` → `verify_facts …`를 다시** 돈다(파일을 고치면 규칙 7이 반드시 재발화하므로 매번 재고정 필요).

→ 상세: `references/verification-gates.md §G3`, 환산 = `§5`.

## [4] + G4 — 렌더 + 육안검증

1. `python <SKILL>/scripts/render_pdf.py --md report.md --style <SKILL>/assets/style.html --out report.pdf` — pandoc(self-contained HTML, 캡처 PNG는 `--embed-resources`로 인라인) → HeadlessChrome(`--print-to-pdf`)로 **오프라인** A4 PDF. pandoc/chrome 미탐지 시 exit 2(설치 안내).
2. `python <SKILL>/scripts/preview_pdf.py --pdf report.pdf` — 페이지별 PNG를 `_preview/`에 생성.
3. **팀리드 육안검증**: 생성된 PNG를 **Read 도구로 열어** 표·이미지·한글·캡처가 정상 렌더됐는지 확인한다. 문제가 있으면 원인(보통 report.md)을 고치고 **G3로 복귀**(파일이 바뀌면 검증을 다시 통과해야 함).

→ 상세: `references/verification-gates.md §G4`, `references/report-format.md §4`.

## G5 — 최종 무결성

1. `python <SKILL>/scripts/manifest.py update .`(report.pdf 포함) → `python <SKILL>/scripts/manifest.py verify .` — **변경 0**(exit 0). 예상치 못한 변경이 있으면 G3로 복귀.
2. PDF 재검사: 본문 `(Fxxx)` 태그 수 · 출처 링크 · 캡처 이미지 수가 대장/근거표와 일치하는지 확인.
3. 통과하면 고객용 `report.pdf`와 내부 `audit/`를 최종 산출물로 확정한다.
4. **ref/ 보존**: 이번 조사에서 발견한 A급 원문 리포트(기준출처로 재사용할 것)를 엄선해 조사 실행 루트의 `ref/`에 사본 저장하고 `ref/README.md` 색인을 갱신한다(`report-format.md §3b`).

→ 상세: `references/verification-gates.md §G5`.

---

## 조사 분할 · 모델 분리

- **기관/기업 실사**: 대상 **2~3개씩** 에이전트에 배정, **entity-identity 선고정** 후 팬아웃. 재무·지분·임원은 DART/OpenDART 공시 원문(`type:"api_response"`). 딜/투자 규모는 **딜규모 ≠ 실수취액** 철칙 적용.
- **기술동향**: **축 분할**(기술요소 / 주요 플레이어 / 시장·규모 / 정책·규제) + 교차검증 담당 1명. 1차출처 우선순위 = 논문(`--type academic`)·표준·특허·기술백서 > 언론.
- **산업동향**: **밸류체인 단계별 + 국내 통계 + 해외 동향** 배정. 국내 통계는 기존 스킬 조합(KOSIS·DART/OpenDART·KIPRIS) 우선, 응답은 `api_response`.
- **모델 분리**: 조사원 = sonnet(병렬·저비용), **재검증·종합 = 메인 세션(팀리드)**.

## references 진입 지도 (언제 무엇을 읽나)

| 단계 | 읽을 문서 |
|---|---|
| G0 | `verification-gates.md §G0`, (기관/기업) `entity-identity.md` |
| [1] 팬아웃 | `agent-briefs.md`(브리프·철칙·반환스키마), `source-ladder.md`(검색/fetch 계층·보안·사유코드), `extract-recipes.md`(증거 6종·locator·PDF 파싱) |
| G1 | `verification-gates.md §G1`, `assets/facts-schema.json` |
| [2]·G2 | `verification-gates.md §G2·§4`(등급), `evidence-capture.md`(캡처 규범) |
| [3] | `report-format.md`(고객용 3중 구조 + audit 번들) |
| G3 | `verification-gates.md §G3·§5`(환산) |
| G4·G5 | `verification-gates.md §G4·§G5`, `report-format.md §4`(렌더) |

## 용어 (단일 기준)

- **2층 등급**: `evidence.grade`(출처별 4차원 A~D — **필수**, 등급의 1차) + `fact.grade`(대표 4차원, 기본값 = 최고 권위 evidence의 등급, 팀리드가 G2에서 확정). 종합 한 글자 등급은 쓰지 않는다. 4차원 = authority / independence / directness / recency(`verification-gates.md §4`).
- **status 5종**: `pending`(근거 有·미재검증) · `confirmed`(evidence≥1 + lead reread match) · `disputed`(상충 병기, note 필수) · `superseded`(시계열 갱신, note 필수) · `discarded`(폐기, discard_reason 필수). 저등급이라고 자동 폐기하지 않는다.
- **fetch 사유코드 12종**(`source-ladder.md §3` = `fetch.py` enum 1:1): `ok`·`partial_ogp`·`blocked_captcha`·`blocked_paywall`·`empty_spa`·`ssrf_blocked`·`too_large`·`bad_mime`·`timeout`·`dns_fail`·`http_4xx`·`http_5xx`. `ok`만 evidence 추출 대상, 실패는 `audit/failed_sources.md`로.
- **캡처 2종**: `source_capture`(원문 그대로, `_captures/`, **증빙 인정**) / `reconstructed_excerpt`(재현물, `_reconstructed/`, **증빙 불인정**).

## 범위 제외 (v1 미배선)

유료 API(firecrawl/tavily) 표준경로 · SearXNG 자체호스팅 · 프록시/스텔스 브라우저 인프라 · Googlebot UA·범용 모바일변환·비계약 캐시 · claude -p 팬아웃 · Semantic Scholar/CrossRef/GitHub/HN/Reddit/X/yt-dlp 자동 배선(`extract-recipes.md §4` recipe 문서로만) · Excel 자동생성(기존 xlsx 스킬 조합) · 웹UI·스케줄링 · 고정 반론 개수 · 고객 PDF의 폐기·실패 노출.

## 참조 문서 (references/)
- `agent-briefs.md` — 서브에이전트 프롬프트 + evidence 반환 스키마 + 철칙
- `source-ladder.md` — search 계층 + fetch 폴백 사다리 + 사유코드 + 보안 정책
- `extract-recipes.md` — 증거유형 6종 추출 + locator + PDF 파싱 + 특수소스 recipe
- `evidence-capture.md` — source_capture vs reconstructed_excerpt + 메타 결박
- `report-format.md` — 고객용 보고서 양식 + 내부 audit 번들 양식
- `verification-gates.md` — G0~G5 상세 + 4차원 등급 + 환산옵션
- `entity-identity.md` — 기관/기업 동일성 확인 게이트
