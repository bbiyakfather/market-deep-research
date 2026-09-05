# verification-gates — G0~G5 상세 · 4차원 등급 · claim-graph · 환산

## 4차원 등급 (grade, 각 A~D) — 단일등급 금지
| 차원 | 의미 | A | D |
|---|---|---|---|
| authority | 출처 권위 | 1차 공시·표준·규제기관 | 익명 블로그·미검증 |
| independence | 독립성 | 이해무관 복수 독립집계 | 당사자 자기발표만 |
| directness | 직접성 | 원데이터·원문 직접 | 3차 재인용·요약 |
| recency | 최신성 | 조사시점 기준 최신 | 수년 경과·갱신됨 |

## G0 preflight
`python scripts/preflight.py`(HARD: python·fitz·pandoc·chrome / SOFT: curl_cffi·trafilatura·
openpyxl·yt-dlp / RUNTIME: 브라우저 MCP(agent-browser 우선)·무료 공공 MCP). 미설치 계층은
"건너뜀+경고"로 진행(자체 스택이 보장 코어). ※ `curl_cffi` 는 사실상 필수 — 내장 우회(모바일
iOS 지문 등)가 전부 그 위에 얹혀 있다. 요구사항 확정(유형·범위·**축별 충분조건**·
환산옵션 OFF·출력형식·**승인 목차**) — 통과조건: `audit/research-plan.md` 존재 + 승인 기록 +
승인 목차(`references/research-plan.md` 서식) 포함, 확정 전 팬아웃 금지. 기관조사면
`entity-identity.md` 선행. `audit/intent-diff.md` 개시.

## G1 join + 수집 게이트
전 워커 완료/timeout/부분실패 처리 → raw `_research/` 보존 → `facts_db.py` 스키마 검증 등재
(위반은 제한적 재요청). **무출처 즉시 `discarded`**(audit 기록).

## [2] 팀리드 재검증(전건) + [Bx] claim-graph
- 전건: 보고서 진입 후보 모든 fact 를 팀리드가 원문 재열람 →
  `add_verify_event(by="lead", action="reread", reread_sha256=<재열람 원문 SHA-256: fetch.py get 의 sha256 / 로컬 PDF 파일 해시 / WebFetch verbatim 의 sha256_text>)`
  — 해시 없는 lead reread 는 add·validate 모두 거부. verifier 단독 confirm 금지. confirmed = ≥1 evidence + lead verify_event(facts_db 강제).
- **claim-graph 게이트(risk=high 만)**: ① ≥2 **독립 관찰그룹**(`observer_group` 상이, 재전재 제외)
  ② **1회 반박검색**(`counter_search.found_stronger_refutation=false`) ③ **기본소스**(`primary_source_ref`)
  ④ **시간증거**(`observed_at` 또는 `valid_at`). ①② 는 본문 사용 confirmed high-risk 에 한해 G3 FAIL, ③④ WARN.
  ②의 기록 유무는 `counter_search.query`로 검사하고 더 강한 반박이 있으면 confirmed 자체를 거부한다.
  본문 미사용 confirmed high-risk는 ①~④ 누락 모두 WARN이다. 이 기존 판정 강도는 v3/v4에 동일하다.
  불통과 → `disputed`/Unresolved(기권이 정답, audit 기록).
  판단 근거·순서는 `audit/verification-economics.md`(오류비용 vs 검증비용 vs 잔여위험).

## G2 증빙 게이트
confirmed 전건 `source_capture`(capture_pdf 또는 브라우저 MCP 실화면 — 계층·recipe 는
`evidence-capture.md`). htmlbox 재구성은 **불인정**.
본문 사용 confirmed 핵심수치 또는 high-risk는 캡처 필수(`verify_facts.py`의 기존 FAIL 조건).
v4의 연결 캡처는 `capture_review`가 존재하고, 현재 이미지 해시 일치·content·accept·주장/문맥
확인을 충족해야 유효 증빙이다. 차단·로그인·백지·불명 화면은 0건으로 계산하며 사실 반증으로
취급하지 않는다. v3의 신규 검토 누락/부적격은 WARN으로 노출한다. 디코딩·크기·단색 비율 보조검사는
내용의 진위를 판단하지 못하므로 육안 확인 기록을 대체하지 않는다(`evidence-capture.md`).

## G3 verify_facts + manifest (실패 0)
`verify_facts.py <report.md> <work_dir> [--conversion]`:
본문/부록 분리(주석 `<!-- FACTSHEET:APPENDIX -->` 우선, 없으면 '## 부록' 헤딩 최후 출현) ·
본문을 문장·표행 세그먼트로 나눠 수치↔(Fxxx) 1:1 최근접 결박(태그 하나가 줄 전체를 면제하지
않음) · 무태그 숫자 차단 · 부록은 [무태그] 만 면제(→ [부록무태그] WARN)하고 오태그·미확정·값·단위는
본문과 동일 FAIL · 접두 통화($4.5B·US$175M·€120M·₩300조)·계수 단위(건·명·개사·기·위·배·대, 숫자에
붙을 때만)도 사실주장 · (Fxxx) 존재+confirmed+값·**단위** 의미대조(Decimal 스케일·차원,
불일치 시 `[단위불일치]`/`[값불일치]`) · evidence 필수필드 · text_quote verbatim ·
high-risk 캡처 실재 · **목차 기계검사**(정규 `audit/research-plan.md` 자동탐지,
그마저 없으면 생략 — 계획 파일 없는 기존 조사는 이 검사만으로 FAIL 하지 않음). →
`verify_facts.py` CLI PASS 가 기준 `manifest.json` 을 자동 생성하고 G3 영수증에
`manifest_sha256` 을 결박한다(이 시점은 report.pdf 생성 전이라 렌더 산출물은 [4] 이후
extend 로만 추가됨).
G3 refs에는 정규 `audit/research-plan.md` 해시(없으면 `missing`)도 결박한다.
사용자 지정 계획은 `--check-only --plan <경로>` / `verify(..., check_only=True, plan=...)` 진단
전용이다. 기록 경로 `verify_and_record`는 다른 계획 경로를 거부하며 진단은 영수증을 만들지 않는다.

**v4 추가 조건**: `verify_calculations.py <work_dir>`와
`verify_claims.py <report.md> <work_dir>`를 G3가 자동 호출한다. 의미 판정은 검토자의 책임이며
문장/근거 해시·검토 전건성·support를 기계적으로 강제한다(`claim-review.md`).
계산 결과는 `audit/calc-check.json`, 문장 검사 결과는 `audit/claim-check.json`에 남긴다.
검토 대장 누락·문장 변경·근거 리비전 변경·미지원 사실 문장은 v4 FAIL, v3 WARN이다.
CAGR의 confirmed 충돌은 v4 FAIL이며 자동 수정하지 않는다. disputed 충돌은 WARN으로 남아
본문의 사실 확정 인용은 기존 `[미확정]` 검사로 차단된다. high-risk CAGR/기간 전망의 원자화 미기록은
v4 FAIL/v3 WARN이다. 일부 입력이나 해당 CAGR 기간의 끝값이 없으면 `NOT_CHECKABLE`과 누락 필드를
남기고 WARN으로 노출한다. 끝값의 연도와 CAGR 기간이 다르면 같은 끝값으로 강제 검산하지 않는다.
끝값 문자열의 최소 표시단위 절반으로 CAGR 구간을 계산한다. `4.50` 같은 표시 정밀도를 보존하려면
원자 수치도 문자열로 기록한다. `scale`/`currency`는 양 끝값의 공통 단위이며 자동 환산은 하지 않는다.
v4의 `value`와 `capture_review`에 알 수 없는 필드가 있으면 오탈자로 검사를 건너뛰지 않도록 거부한다.

**G3 도판검사**: `_captures/` 증빙캡처는 G2 소관이라 제외하고, 본문 대표 이미지 0장을
차단하며 각 참조 경로의 실재를 확인한다. 각 이미지 참조 뒤 2줄 이내에 `[그림]`으로 시작하고
`출처:`를 포함한 캡션이 없으면 `[도판출처]`로 FAIL하며, `assets/` 이하 자작 차트의 캡션에
`(Fxxx)`가 최소 1개 없으면 `[도판무결박]`로 FAIL한다. 출처와 사실 대장을 기계적으로
역추적하고 증빙캡처를 이중 판정하지 않기 위한 검사다.

## G5c 실행코드 검증(계산·상충)
자체포함 스크립트 실행 → stdout → `audit/verify-<slug>.md`(CONFIRMED/REFUTED/PARTIAL).

## G4 preview → G5 최종 무결성
단일 작업자를 전제로 하며 검증 중 동시 쓰기는 허용하지 않는다. 검사·기록 원자성 락은 제공하지 않는다.
finalize는 봉인 항목 전체와 정규 원고·PDF·claim-review·계획을 검사 전후 재해시하고, 불일치하면 실패한다.
출고 판정은 G5 `snapshot_hashes` 해시 집합이 가리키는 리비전에 대한 것이다. 이후 변경은 status/재verify가 드리프트로 탐지한다.
G5 PDF 검사는 형식·개수 기반(F태그·링크·캡처 수)이며 내용 동일성을 보장하지 않는다. 그 확인은 G4 팀리드 육안검증의 역할이다.
같은 프로세스 권한의 원장·기록 위조는 신뢰 경계 밖이다. 출고 판정(`manifest.py verify`)은 영수증이 아닌 실검증으로 계산하므로 위조 기록이 판정을 바꾸지 못한다.
status의 `최종(판정시점)`은 원장 기반 결과와 현재 스냅샷의 일치를 뜻하며, 재확인은 `manifest.py verify`로 수행한다.
report.pdf 생성 후 **재봉인**(`manifest.extend` — 기존 항목 불변 확인 실패 시 거부 = G3 복귀,
렌더 산출물 artifacts 만 추가, G3 기준선 해시 대조) → `preview_pdf.py` 육안검증 + **intent-diff 축별 대조**
(`audit/intent-diff.md` 개시분의 축별 "참이어야 하는가" 목록을 실제 보고서 발견과 대조 —
축마다 gap 유무 판정, 결과를 `audit/intent-diff.md` 에 추기) → PDF F태그·링크·캡처 수 재검사
+ `manifest.py verify`(재봉인 기준 — 신규 파일도 실패로 판정. [4b]·G4 영수증 확인 +
[4b]↔manifest 결박 대조 후 결과를 G5 영수증으로 자기기록).
**복귀 규칙**: 파일 변경 검출 시 G3 복귀. intent-diff gap(개시분 대비 누락 발견) 검출 시
**[E] 확장수렴 루프로 복귀**(gap 난 축만 후속 워커 재스폰 — 축 전건 재조사 아님).
**참고**: [G2]가 만드는 실패 캡처 `.FAILED` 산출물도 `_captures/**` 글롭에 잡힌다 — 재봉인(extend)
이후 캡처를 재시도하면 그 결과물이 신규 파일로 잡혀 verify 가 실패로 뜬다. 내용 검토와 G3를
다시 수행한 뒤 렌더·재봉인한다. 검토가 끝나지 않은 신규 근거를 최종 단계에서 바로 추가하지 않는다.

## 영수증 커버리지
원장(`audit/gates.jsonl`) 영수증: G0·[2]·G4=수동(`gates.py record`), G3·[4b]·G5=소유
스크립트 자기기록(공개 API·CLI 성공 손기록 차단, 실패 기록 허용 — verify_facts.py·render_pdf.py·manifest.py verify),
G1·G5c 등 무소유 게이트=`gates.py record_script_result`. G3 CLI PASS 가 기준 manifest 를
만들고 영수증에 해시를 결박하며, [4b] 는 그 기준선을 extend-only 로 확장하고, G5 는
[4b]↔manifest 결박을 검사한다. G2·G5c 의 실질 강제는 원장이
아니라 내용검사다(G2=verify_facts 캡처 실재, G5c=`audit/verify-<slug>.md`).
[2] 영수증은 record 시점에 confirmed 전건 lead reread(+reread_sha256) 를 검사해 confirmed 투영
다이제스트를 기록한다. v3는 id·raw·unit·lead reread 이벤트, v4는 추가로 전체 value·claim·context·
claim_type을 결박한다. G2의 evidence ID 추가는 이 투영을 바꾸지 않으며 G3의 대장 refs에서 검사한다.

## 리비전과 영수증 재발급
- `revision_id`는 `facts_db.confirmed_digest`다. `input_digest`는 해당 게이트 refs 해시 묶음,
  `receipt_id`는 영수증 ID, `supersedes_receipt`는 직전 같은 게이트 ID다. ID 없는 과거 행은 정규 JSON
  해시로 참조한다. `run_id`는 실행 식별용 최소 필드이고 병렬 실행 제어는 하지 않는다.
- `code_sha256`는 실행 스크립트와 스키마의 해시 묶음이다. 미커밋 변경도 구분하며, 과거 코드로
  실행된 기록을 현재 코드가 실행된 것처럼 바꾸지 않는다. 과거 원장 행은 수정·삭제하지 않는다.
- `check_prerequisites()`는 선행 영수증의 현행성만 검사한다. `check_current_receipt()`는 자기
  영수증의 refs·revision·선행 영수증 ID 변경을 감지한다. `check`/`status`의 **재실행 필요**는
  새 발급을 금지한다는 뜻이 아니다. `record_manual`/`record_script_result`의 성공 기록은 선행조건만
  만족하면 재발급 가능하다. 실패 실행도 원장에 남는다.
- confirmed 리비전이 바뀌면 [2] 이후 기존 영수증이 무효화된다. 같은 리비전에서도 선행 영수증이
  교체되면 하위 영수증은 재실행해야 한다. G3는 facts/evidence/report/claim-review/정규 계획의 변경도 검사한다.
  audit 전체를 봉인하지 않으므로 일반 검토 로그의 추가는 불필요한 무효화를 일으키지 않는다.

재발급 예:
```text
자료 수정·원문 재열람 → calc-check와 claim-review 갱신
gates.py record [2] <work_dir> --evidence "변경 후 전건 재열람" --refs facts.jsonl audit/reread-report.md
verify_facts.py <report.md> <work_dir>
render_pdf.py <report.md>
preview_pdf.py <report.pdf> <preview_dir>
gates.py record G4 <work_dir> --evidence "육안·intent-diff 확인" --refs report.pdf audit/intent-diff.md
manifest.py verify <work_dir>
```
선행 refs도 바뀌었다면 해당 게이트부터 순서대로 재발급한다. G3 재실행은 기존 PDF를 입력 봉인에서
제외하고 새 렌더 결과를 [4b]에서 추가하므로, 옛 PDF가 남아 있어도 정상 재출고할 수 있다.

**최종 출고의 단일 경로**는 `manifest.py verify` → `finalize_report()`다. 현행 G3·[4b]·G4와
manifest의 동일 revision_id 및 [4b] 해시 결박, 정규 원고 검사 전용 재검증과 PDF F태그·링크·캡처 수
대조를 모두 통과해야 같은 리비전의 G5 성공 영수증을 자기기록한다. 실패도 이력으로 보존한다.
`gates.py status`의 `최종(판정시점)`은 저장된 실검증 결과와 현재 결박 해시가 일치한다는 표시이며,
출고를 새로 승인하는 검사는 아니다. 원고 재검증은 `manifest.py verify`에서 실행한다.
`render_pdf.render()` 직접 호출은 초안이며 출고를 승인하지 않는다. 호환용 `manifest.verify()`
함수는 파일 해시 대조만 수행하므로 이 함수의 ok를 최종 승인으로 해석하지 않는다.

## v3 → v4 이행
기존 파일은 보존하고 이행 사본에서 fact/evidence마다 `schema_version: 4`를 명시한다.
fact의 `claim_type`, 시장 전망의 원자화 value, 캡처별 해시 결박 검토, 모든 본문 태그 문장의
`audit/claim-review.jsonl`을 준비한다. 혼합 폴더는 문장 검토를 v4로 강제하고 계산·캡처의
행별 판정은 해당 fact/evidence 버전을 따른다. v3 신규 검사 경고는 검증 완료를 의미하지 않는다.
대장에 schema_version이 전혀 없는 순수 v3의 구형 영수증·manifest는 revision_id 누락만 WARN으로
처리하고 기존 refs·계획·confirmed·manifest 해시 결박은 유지한다. 신규 영수증은 revision_id 필수이며
v4 이행 시 [2]부터 재발급한다. v3의 독립 G1 join 기록 API는 호환되며 후속 [2]는 G0·G1 둘 다 요구한다.
알 수 없는 schema_version은 거부한다.

## 환산 옵션(기본 OFF)
ON 시 Decimal 검산(계산식·환율출처·기준일·종가/평균 명시), 표시 반올림 일관, 본문 영어통화단어 0.
`value.decimal` 에 검산값. 오차 표기(±)는 근거 있을 때만.

## 상태 모델
`confirmed`(검증완료) · `pending`(미검증) · `disputed`(정의차·상반 병기) · `superseded`(시계열 갱신,
`last_seen`) · `discarded`(무출처·저품질, `discard_reason`). 단순 저등급 폐기 금지 — disputed/superseded 우선.
