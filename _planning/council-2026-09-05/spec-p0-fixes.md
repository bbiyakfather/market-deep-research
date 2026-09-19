# SPEC — market-deep-research P0 결함 4건 수정 + 회귀 테스트

REASONING: xhigh

## 0. 배경 (필독)

실제 보고서 검증에서 발견된 결함 4건의 수정. 근거 문서(수정 제안서)는
`F:/Claude/work/navion-market-research/keri-business-model/market-deep-research_스킬_수정방안.md`
— 반드시 먼저 전체를 읽어라. 이 스펙은 그 문서의 P0 항목만 구현 범위로 확정한 것이다.
P1/P2(전력예산·부재/최상급 주장·점수화·report-format 점수 서식)는 **구현하지 않는다**.

대상 저장소(개발본): `F:/Claude/skills/market-deep-research/codes/market-deep-research/`
(이하 `<core>`). 설치본(`~/.claude/skills/...`)은 건드리지 않는다.

사례 자료(재현 확인용, **읽기 전용 — 절대 수정·삭제 금지**):
`F:/Claude/work/navion-market-research/keri-business-model/research_KERI_EH-PMIC_사업화BM_20260905/`
(facts.jsonl, evidence.jsonl, report.md, _captures/E130.png, audit/gate-note.md)

## 1. 목표

1. **F130 의미 확장 차단**: 본문 문장이 근거 fact 의 주체·속성·범위·기간·조건을 넘는 것을
   문장별 검토 대장(claim-review)으로 잡고, 미해결 시 최종 승격을 차단.
2. **E130 차단화면 캡처 불인정**: 캡처 파일 존재만으로 증빙 인정하던 것을, 내용 검토
   기록(capture_review)을 이미지 해시에 결박해 차단/백지/로그인 화면은 유효 증빙 0건으로.
3. **F091 CAGR 검산**: 복합 수치 문자열을 원자화하고 CAGR 를 전수 검산, 불일치는 자동
   덮어쓰기 없이 충돌로 공개·confirmed 승격 차단.
4. **게이트 영수증 재발급**: 대장 변경 후 적법한 재검증이 막히는 문제를 리비전 모델로 해소.
   과거 영수증은 불변 보존, 새 영수증은 supersedes 로 연결, 하위 게이트는 자동 무효화.
   G3 미완료 상태의 함수 직접 렌더는 초안까지만 — 최종 출고 판정은 단일 경로.

회귀 테스트: 제안서 §13 의 T01~T06, T10~T12 (T07~T09 는 P1 이라 제외).

## 2. 파일 (수정 · 신설)

기존 구조 참고 — 주요 함수:
- `scripts/gates.py`: `_read_records/_append/_latest/_receipt_issues(219)/successful_receipt(231)/require_receipt(248)/check_gate(264)/record_manual(325)/record_script_result(372)/status/demo`
- `scripts/facts_db.py`: `load_schema/validate_fact(61)/check_capture_path(109)/validate_evidence(130)/FactsDB(190)/confirmed_digest(282)/diff_facts`
- `scripts/verify_facts.py`: `check_bound_numbers(345)/check_ledger_integrity(425)/check_evidence_chain(510)/check_figures/check_toc/verify(773)` — G3 CLI, PASS 시 기준 manifest 생성
- `scripts/manifest.py`: build/extend/verify (G5 가 [4b]↔manifest 결박 검사)
- `scripts/render_pdf.py`: 렌더 성공 직후 manifest extend + [4b] 자기기록
- `assets/facts-schema.json`: v3 경량 스키마(required/enum/const 만 검사)
- `tests/test_e2e.py`, `tests/test_adversarial.py`: 기존 테스트 — **깨뜨리지 말 것**

| 대상 | 작업 |
|---|---|
| `assets/facts-schema.json` | `schema_version` 도입(v4). fact.value 에 원자화 필드, fact 에 `claim_type`, evidence 에 `capture_review` (아래 §3) |
| `scripts/facts_db.py` | 신규 필드 검증(조건부 필수 포함 — 경량 검증기가 실제로 검사하게), v3 레코드는 legacy 로 통과 |
| 신규 `scripts/verify_calculations.py` | CAGR 검산 CLI (§3.3) |
| 신규 `scripts/verify_claims.py` | claim-review 대장 검사 CLI (§3.1) |
| `scripts/verify_facts.py` | capture_review 검사(§3.2) + verify_calculations·verify_claims 결과를 G3 PASS 조건에 편입 |
| `scripts/gates.py` | `check_prerequisites()`/`check_current_receipt()` 분리, 영수증 `revision_id`·`supersedes_receipt`·`input_digest`, 재발급 경로 (§3.4) |
| `scripts/manifest.py`, `scripts/render_pdf.py` | 리비전 결박: 최종 verify 는 동일 revision_id 의 유효 영수증 체인 요구. 초안 렌더는 허용하되 최종 판정 실패 |
| `references/verification-gates.md` | 리비전 모델·재발급 절차·판정 강도(문서↔코드 불일치 정리: high-risk 기본소스·시간증거의 WARN/FAIL 을 코드와 일치시켜 명기) |
| `references/evidence-capture.md` | capture_review 필드·page_state·"파일 존재 ≠ 내용 검증" 규칙 |
| 신규 `references/claim-review.md` | 문장별 검토 절차·support 판정 기준·기록 서식 |
| `SKILL.md` | 3대 원칙에 2줄 내로 반영(원문 일치≠주장 성립 / 캡처 존재≠내용 검증), G3 절에 두 신규 CLI 한 줄씩. **슬림 유지 — 장문 금지** |
| `tests/test_p0_regressions.py` (신규) | T01~T06·T10~T12, 합성 픽스처 |

## 3. 인터페이스 (결정 사항 — 임의 변경 금지)

### 3.1 claim-review (F130)
- 대장: `audit/claim-review.jsonl`. 레코드 필드(제안서 §5.2 그대로):
  `sentence_id, claim_type(observed|derived|hypothesis|recommendation), fact_ids[], evidence_ids[],
  support(supported|partial|unsupported|contradicted|unresolved), unsupported_terms[],
  required_qualification, sentence_text, reviewed_text_sha256, evidence_revision`.
  `reviewed_text_sha256` = sentence_text 의 sha256. 의미 판정 자체는 모델(팀리드)이 기록하고,
  스크립트는 부기·차단만 강제한다.
- `verify_claims.py <report.md> <work_dir>` 검사:
  ① 레코드 스키마·enum. ② `sentence_text` 가 현재 report.md 본문에 실재(verbatim)하고 해시
  일치 — 불일치 = 문장 변경 후 미재검토 → FAIL. ③ 본문에서 F-태그(`[F\d+]` 류, 기존
  verify_facts 의 태그 정규식 재사용 — **이중구현 금지, import 해서 쓸 것**)가 붙은 문장은
  전건 레코드 존재 — 누락 FAIL. ④ claim_type=observed/derived 문장의
  support ∈ {partial, unsupported, contradicted, unresolved} → FAIL (축소·한계 명기 후 재검토
  해야 통과). hypothesis/recommendation 은 support=unsupported 만 FAIL(가정 명시 조건부 게재 허용).
  ⑤ `evidence_revision` 이 현재 대장 confirmed_digest 와 다르면 FAIL(근거 변경 후 미재검토).
- exit 0/1 + `audit/claim-check.json` 리포트. verify_facts.verify() 가 이 검사를 호출해
  G3 PASS 조건에 포함(파일 자체가 없으면 FAIL — legacy v3 작업폴더는 §4 참조).

### 3.2 capture_review (E130)
- evidence.capture_review: `{image_sha256, reviewed_by, reviewed_at,
  page_state(content|blocked|login|blank|unknown), claim_visible(bool), context_visible(bool),
  verdict(accept|reject)}`.
- 자동 보조검사(verify_facts 내): 이미지 디코딩 가능(fitz 사용 — 신규 의존성 금지)·최소 크기·
  백지 의심(단색 비율 휴리스틱, `ponytail:` 주석으로 한계 명기). OCR 은 하지 않는다.
  자동검사는 후보 선별용 — 최종 인정은 capture_review 기록만.
- 판정: confirmed fact 의 source_capture 는 ① capture_review 존재 ② verdict=accept ③
  page_state=content ④ image_sha256 == 현재 파일 해시(불일치 = 교체 → 재검토 요구 FAIL, T04)
  을 모두 충족해야 유효 증빙. blocked/login/blank → 유효 증빙 0건으로 계산하되 **fact 를
  거짓 판정하지는 않는다**(증빙 부족 상태로만).

### 3.3 verify_calculations (F091)
- 스키마 원자화 필드(value 안, 전부 optional): `base_value, base_year, forecast_value,
  forecast_year, reported_cagr, cagr_start_year, cagr_end_year, scale, currency`.
  `value.raw` 원문 문자열은 그대로 보존.
- `verify_calculations.py <work_dir>`: Decimal 로
  `((forecast/base)**(1/(end-start))-1)*100` 검산. 허용오차는 임의 ±상수 금지 — 원문 표시
  정밀도 기반 구간산술(끝값 각각 ±반 최소표시단위 → CAGR 구간, reported 가 구간 밖이면 충돌).
  입력 부족 → `NOT_CHECKABLE` + 누락 필드 목록(오류 아님). 충돌 fact 가 status=confirmed 면
  exit 1 (disputed 로 내리거나 본문·대장에 불일치 명시 후 재실행). 자동 수정·덮어쓰기 금지.
- 리포트 `audit/calc-check.json`. verify_facts 가 호출해 G3 조건 편입.
- high-risk + 시장수치(reported_cagr 또는 기간 전망 포함) fact 가 원자화 미기록이면 v4 에서
  FAIL, v3 legacy 는 WARN.

### 3.4 게이트 리비전 모델
- 영수증 필드 추가: `revision_id`(= facts_db.confirmed_digest — 기존 함수 재사용),
  `input_digest`(해당 게이트 refs 해시 묶음), `supersedes_receipt`(이전 영수증 id), `run_id`.
- `check_prerequisites(work, gate)`: 선행 게이트들의 **현행 유효** 영수증 존재 검사.
- `check_current_receipt(work, gate)`: 최신 영수증의 refs·revision 을 지금 상태와 대조.
  드리프트 = "재검증 필요" 신호이지 기록 차단 사유가 아니다.
- `record_manual`/`record_script_result`: 선행 게이트가 유효하면, 기존 영수증이 드리프트
  상태여도 **새 영수증 발급 가능**(supersedes 연결). 과거 레코드는 절대 수정·삭제 금지
  (append-only 유지). 대장(confirmed_digest) 변경 시 [2] 이후 게이트의 기존 영수증은
  자동으로 현행성 상실 → status/check 가 "재실행 필요" 로 표시 (T10).
- 최종 출고: `manifest.py verify` 가 G3~G5 영수증이 **동일 revision_id** 인지 검사.
  G3 없이 render_pdf 함수 직접 호출 → PDF 파일은 생성돼도(초안) manifest verify 실패 (T11).
- 실행 버전 기록: 영수증에 스킬 코드 식별자(git HEAD 해시 or 스크립트 해시) 1개 필드 (T12).

## 4. 제약

- **v3 하위호환**: 기존 대장/작업폴더(schema_version 없음 = v3)는 기존 검사만으로 통과
  가능해야 한다(신규 검사는 WARN). v4 (schema_version: 4 명시) 부터 신규 검사가 FAIL 로
  강제. 알 수 없는 필드를 자동 검증완료 처리하지 않는다.
- **원본 보존**: KERI 사례 폴더는 읽기 전용. 재현 확인은 스크래치패드 사본
  (`C:/Users/eicic.AIDEN-DESKTOP/AppData/Local/Temp/claude/F--Claude-skills-market-deep-research/c262ea17-e2bd-49a6-a58e-625f250250a5/scratchpad/keri-copy/`)
  에 복사해서 수행. **KERI 데이터·파일명·수치를 저장소(테스트 픽스처 포함)에 커밋 금지** —
  테스트 픽스처는 구조만 모사한 합성 데이터로 만든다(예: F130→"FX01 속성확장", E130→합성
  차단화면 PNG(fitz 로 생성), F091→4.5→12.8/17.8% 수치 패턴은 공개된 산술이므로 사용 가능).
- 신규 외부 의존성 금지(fitz·stdlib 만). 금액·비율 계산은 Decimal. Windows cp949 콘솔 대비
  기존 스크립트들의 utf-8 reconfigure 패턴 유지.
- 기존 테스트(test_e2e/test_adversarial) 전부 통과 유지. 기존 판정·상수·정규식은 재사용
  (이중구현 금지).
- 코드 스타일: 기존 파일들과 동일(한국어 주석·docstring CLI 사용법). 과설계 금지 —
  제안서의 개념 중 P0 구현에 불필요한 것(run_id 기반 병렬 실행 관리 등)은 최소 필드만.
- 커밋하지 말 것 — diff 는 워킹트리에 남겨라(팀리드가 리뷰 후 커밋).

## 5. 검증 명령 (완료 전 전부 실행, 결과를 out 파일에 기록)

```
cd F:/Claude/skills/market-deep-research/codes/market-deep-research
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q                 # 기존+신규 전부
PYTHONIOENCODING=utf-8 python scripts/gates.py demo               # 게이트 데모 통과
PYTHONIOENCODING=utf-8 python scripts/verify_calculations.py --demo
PYTHONIOENCODING=utf-8 python scripts/verify_claims.py --demo
python scripts/preflight.py                                       # exit 0 유지
```
+ KERI 사본 재현: 스크래치패드 사본에서 ① E130 캡처가 유효 증빙 불인정되는지
② F091 이 충돌 검출되는지 ③ gate-note.md 의 재기록 시나리오가 새 경로로 통과하는지
실행해 stdout 을 out 파일에 인용(사본 경로만, 원본 무변경 확인 `git status` 포함).

## 6. 완료 보고 (out 파일에)

변경 파일 목록(`git diff --stat`) / 실행한 검사와 결과 / 미해결 항목 / 기존 v3 작업폴더의
이행 방법(무엇이 WARN 으로 남고, v4 승격에 무엇이 필요한지) / 요약 20줄.

질문하지 말고 가정을 적고 진행하라. 막히면 막힌 지점을 out 파일에 적고 종료하라.
stdout 은 요약만 — 상세는 파일로.
