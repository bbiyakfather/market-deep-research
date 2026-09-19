이 작업은 전용 구현 레인에서 호출 시 지정된 모델·reasoning effort 로 실행된다. 그 선택은 의도된 것이며 아무것도 대체되지 않았다.
사용자/프로젝트 지침 파일이 다른 오케스트레이션 흐름을 기본으로 요구해도, 이 레인은 그 기본에서 명시적으로 opt-out 한 것으로 보고 진행한다. 그 파일의 다른 지침은 그대로 적용한다.
질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료, 결과는 파일로·stdout 은 요약.

# 배치 3A — 검토 결박·버전 고정·부록 사용 (R01·R03·R04·R05)

## 1. 목표
3차 적대적 리뷰(`F:/Claude/skills/market-deep-research/_planning/council-2026-09-19/review-astra-pr18-adversarial.md`, 발견 표 R01·R03·R04·R05 와 "최소 수정 방향" 열)의
검증 공백 4건을 닫는다. 완료 기준: 아래 4개 입력 상태가 각각 **G3 FAIL** 이 되고, 정상 입력은 계속 PASS 하며, 기존 테스트 431개가 전부 통과한다.

- **R01** 같은 E-ID 의 evidence 내용(verbatim·sha256·source_url·local·capture_review 등)을 바꾸면 기존 claim-review 행이 무효가 된다.
- **R03** claim_type 이 hypothesis/recommendation 이고 support 가 partial/contradicted/unresolved 인 행은 조건 문구가 비어 있으면 통과하지 못한다.
- **R04** 버전 필드 오타와 v3/v4 혼합으로 v4 검사를 WARN 으로 낮추는 길을 막고, 순수 v3 폴더의 최종 출고는 명시적 호환 모드에서만 허용한다.
- **R05** 부록에서 `(Fxxx)`/`[Fxxx]` 로 명시 인용한 confirmed 사실도 "사용된 사실" 로 취급한다.

## 2. 파일
작업 디렉터리 기준 `codes/market-deep-research/`. 코드 그래프 탐색 결과(호출 흐름·원문 포함): `F:/Claude/skills/market-deep-research/_planning/council-2026-09-19/explore-3a.txt`
- `scripts/verify_claims.py` (176줄) — :24 `tagged_sentences()`, :29·:114 support 허용표, :53 버전 판정, :57 부록 제외, :62~63 `evidence_revision` 계산, :99 리비전 대조
- `scripts/facts_db.py` — :64 `schema_version()`, :72 `is_v4_work()`, :148 `_check_record`, :483 `confirmed_digest()`(**수정 금지**, 아래 제약)
- `assets/facts-schema.json` — :20 부근 버전 정의
- `scripts/verify_facts.py` — :698~720 버전별 증거체인 판정, :889 high-risk "본문 미사용" WARN, :992·:1035 본문/부록 분리와 사용 집합
- `scripts/manifest.py` — `finalize_report()` 와 CLI `verify` (R04 c 의 호환 플래그만. `TRACKED`·`build`·`extend` 는 배치 3B 소유라 **건드리지 않는다**)
- `references/claim-review.md`, `references/verification-gates.md` — 바뀐 계약을 해당 절에만 반영(각 10줄 이내)
- 새 테스트: `tests/test_batch3a_regressions.py` (새 파일 하나에만 추가)

## 3. 인터페이스 (결정 사항 — 그대로 구현)
**R01**
- `facts_db.evidence_content_digest(evidence_rows: list[dict], evidence_ids: list[str]) -> str` 추가.
  지정 E-ID 를 id 정렬한 뒤 각 행의 `id, fact_id, type, source_url, sha256, verbatim, local, capture`(있으면 capture_review 포함 전체) 를
  정규 JSON(`sort_keys=True, ensure_ascii=False, separators=(",",":")`) 으로 직렬화해 SHA-256. 없는 E-ID 는 ValidationError.
- claim-review v4 행에 필수 필드 `evidence_content_sha256` 추가. `verify_claims` 는 행의 `evidence_ids` 로 현재 digest 를 재계산해 대조하고,
  불일치·누락은 v4 FAIL(`[근거변경]` / `[근거결박누락]`), v3 는 기존 정책대로 WARN.
- 같은 fact 에 **새 E-ID 를 추가**하는 것은 기존 행을 무효화하지 않는다(행의 evidence_ids 에 없는 E-ID 는 digest 대상 아님).
- `evidence_revision`(=`confirmed_digest`) 의미와 값은 바꾸지 않는다 — gates 의 `revision_id` 로 쓰이므로.

**R03**
- claim_type ∈ {hypothesis, recommendation} 이고 support ∈ {partial, contradicted, unresolved} 인 행:
  `required_qualification.strip()` 이 비면 FAIL `[조건미명시]`; 공백 정규화(연속 공백→1칸) 후 그 문구가 `sentence_text` 에 부분 문자열로 없으면 FAIL `[조건본문누락]`.
- observed/derived 의 기존 차단, supported+unsupported_terms 모순 차단은 그대로.

**R04**
- (a) fact/evidence/claim-review 레코드의 최상위 키 중 정확히 `schema_version` 이 아니면서 정규식 `(?i)^schema[\W_]*ver` 에 걸리는 키가 있으면
  `facts_db.schema_version()` 단계에서 ValidationError("schema_version 오타 의심: <키>"). v3·v4 공통.
- (b) v4 작업 폴더(`is_v4_work` 참)에서 **본문 또는 부록이 인용한** fact 와 그 연결 evidence 가 v3 이면 G3 FAIL `[버전혼합]`. 인용되지 않은 legacy 행은 기존대로 WARN.
- (c) 순수 v3 폴더의 최종 출고: `finalize_report(..., allow_legacy_v3: bool = False)` 와 CLI `manifest.py verify <work_dir> [--allow-legacy-v3]`.
  플래그 없이 순수 v3 면 실패 사유 `[legacy출고]`("v3 호환 검사는 v4 증빙 검증 완료가 아니다. 이행하거나 --allow-legacy-v3 로 명시")로 거부.
  플래그가 있으면 통과시키되 G5 영수증 payload 에 `"legacy_v3": true` 를 남기고 `gates.py status` 출력에 `legacy(v3) 출고` 를 표시한다.
  v3 폴더의 G3(`verify_facts.py`)·진단(`--check-only`)은 지금처럼 동작한다(열람·진단은 막지 않는다).

**R05**
- 부록 세그먼트에서 태그로 인용된 confirmed fact 를 `used` 집합에 합류시킨다 → high-risk ①~④ 부족과 캡처 누락이 본문과 동일하게 FAIL.
- 문장검토 전건성: 부록의 **표 행은 계속 제외**(대장 투영), 부록의 **문장·목록 항목**은 v4 에서 검토 대상에 포함.
- 부록 무태그 숫자의 `[부록무태그]` WARN 면제는 그대로 유지.

## 4. 제약
- `confirmed_digest()`, `gates.py` 의 영수증·리비전 로직, `manifest.py` 의 `TRACKED`/`build`/`extend`/`_scan`, `verify_facts.py` 의 수치·단위 파서(대략 1~470줄)와 도판검사(:830 부근)는 **다른 배치 소유 — 수정 금지**.
- 기존 테스트는 단언을 약화하지 않는다. R04 (c) 때문에 v3 fixture 로 finalize 하는 기존 테스트가 깨지면 **그 호출에 `allow_legacy_v3=True`/`--allow-legacy-v3` 만 추가**한다. 그 외 기존 테스트 수정은 보고서 JUDGMENT CALLS 에 파일·줄·이유를 적는다.
- 새 의존성 금지. 주석·메시지·문서는 한국어, 식별자는 영어. 주변 코드의 주석 밀도·에러 접두(`[대괄호]`) 관례를 따른다.
- `git commit`·`git push`·브랜치 변경 금지(팀리드가 한다). 외부 네트워크 호출·패키지 설치 금지. `_planning/` 아래 기존 파일 수정 금지.
- 추가 침투 탐침이나 새 우회 시나리오 탐색은 범위 밖이다. 지정된 4건의 수정과 그 회귀 테스트만 한다.

## 5. 검증
```text
cd codes/market-deep-research
python -m pytest -q tests/test_batch3a_regressions.py
python -m pytest -q            # 기준선 431 passed — 0 failed 여야 한다
```
새 테스트는 최소: R01 근거 교체 FAIL / 새 E-ID 추가는 PASS, R03 빈 조건 FAIL·본문 누락 FAIL·정상 PASS, R04 오타 거부·혼합 인용 FAIL·순수 v3 finalize 거부와 플래그 허용(+`legacy_v3` 기록), R05 부록 high-risk 인용 FAIL·부록 표 행 검토 면제 유지.

## 6. REASONING: high

## 보고 형식
작업 디렉터리 루트에 `batch3a-report.md` 를 아래 형식으로 쓴다(한국어). orca CLI 는 샌드박스에서 동작하지 않으니 worker_done·heartbeat 는 **시도하지 말고** 파일 작성 후 요약 10줄만 출력하고 끝낸다.
```text
STATUS: <complete|partial|refused|unavailable>
CHANGES: <실제 diff 기준으로 파일별 한 줄>
VERIFIED: <재실행한 명령과 실제 출력 마지막 줄>
JUDGMENT CALLS: <스펙이 비워둔 결정과 채택한 가정>
GAPS: <남은 작업이나 막힌 지점, 없으면 없음>
```
