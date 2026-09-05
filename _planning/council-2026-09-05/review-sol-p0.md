# market-deep-research P0 수정 diff 교차 리뷰

## 판정

**REQUEST_CHANGES**

최종 출고 봉인을 우회할 수 있는 경로가 남아 있고, 스펙이 요구한 v3 하위호환도 충족하지 않는다. 테스트 106개와 데모·preflight가 통과했다는 제공 사실은 재확인하지 않았으며, 본 리뷰는 제공된 `p0.diff`, `spec-p0-fixes.md`, 수정 제안서 전체 및 저장소 문맥을 정적 대조한 결과다.

## 가정

- 위협 모델은 임의 바이트 변조 공격만이 아니라, 자동화/호출자가 공개 Python API를 잘못 조합해 소유 스크립트 검사를 건너뛰는 경우도 포함한다. 스펙이 함수 직접 렌더 우회와 “최종 판정 단일 경로”를 명시했기 때문이다.
- CLI의 `<report.md>`는 문서에 적힌 공개 인터페이스이므로 `<work_dir>/report.md`와 다른 경로도 현재 계약상 유효한 입력으로 간주했다. 구현이 이를 지원하지 않으려면 명시적으로 동일 경로를 강제해야 한다.
- schema_version이 없는 기존 v3 작업폴더에는 이번 변경 전 형식의 게이트 영수증(`revision_id` 없음)이 존재할 수 있다고 보았다.

## 발견 사항

### 1. [치명] 공개 기록 API로 G3·[4b] 소유 검사를 건너뛰고 최종 출고 가능

- 위치: `scripts/gates.py:454`, `scripts/gates.py:477-518`, `scripts/gates.py:647-653`; 관련 최종 신뢰 지점 `scripts/manifest.py:154-180`
- 근거: `record_script_result()`는 `SCRIPT_OWNED` 여부를 검사하지 않고, 호출자가 넘긴 `exit_code=0`과 `extra`의 `manifest_sha256` 등을 그대로 영수증에 넣는다. 소유 게이트 차단은 CLI 분기에서만 수행된다. 따라서 Python 호출자는 다음 순서로 `verify_facts.py`와 `render_pdf.py`의 소유 로직을 건너뛸 수 있다.
  1. G0·G1·[2]만 정상 기록한다.
  2. `manifest.build(..., for_g3=True)` 후 `record_script_result(..., "G3", 0, extra={"manifest_sha256": ...})`를 직접 호출한다.
  3. PDF를 직접 만들고 `manifest.extend()` 후 `[4b]` 성공 영수증도 같은 API로 직접 기록한다.
  4. G4를 기록하면 `finalize_report()`는 영수증·revision·manifest 해시가 모두 맞는 것으로 보고 G5를 통과시킨다.
- 영향: 의미 검토, CAGR 검사, 캡처 검토 및 실제 렌더 소유 단계가 실행되지 않아도 최종 상태가 `최종`이 될 수 있다. T11은 직접 `render()` 뒤 선행 영수증이 전혀 없는 경우만 검사하므로 이 우회를 다루지 않는다.
- 최소 수정안: 범용 `record_script_result()`에서 `SCRIPT_OWNED` 성공 기록을 무조건 거부하고, G3·[4b]·G5별 전용 기록 함수를 둔다. 전용 함수는 해당 단계가 생성한 필수 결박값을 자체 계산·검증해야 하며 임의 `extra`로 주입받지 않아야 한다. 이어서 “검증/렌더는 건너뛰고 영수증 API만 호출”하는 부정 회귀 테스트를 추가한다.

### 2. [치명] 검증한 report 경로와 G3가 봉인하는 report 경로가 달라질 수 있음

- 위치: `scripts/verify_facts.py:1007-1025`, `scripts/gates.py:508-512`
- 근거: CLI는 `verify(args[0], args[1])`로 사용자가 넘긴 임의 보고서를 검사하지만, PASS 뒤에는 `WorkPaths(args[1])`의 고정 `report.md`를 `manifest.build()`와 G3 `refs`로 봉인한다. 두 경로가 같은지 확인하지 않는다.
- 우회 시나리오: 같은 작업폴더에 검토 대장과 일치하는 `clean.md`를 두고 실제 `<work>/report.md`에는 미지원 주장을 둔다. `verify_facts.py clean.md <work>`는 clean.md를 검사한 뒤, 검사하지 않은 `<work>/report.md`를 G3 기준선과 영수증에 결박한다. 이후 `render_pdf.py <work>/report.md`, G4, `manifest.py verify`를 수행하면 report.md 바이트는 G3 이후 변하지 않았으므로 최종 출고가 통과할 수 있다.
- 영향: revision_id를 바꾸지 않고도 F130 의미 검토를 포함한 G3 전체를 다른 파일에 수행해 실제 출고 원고를 세탁할 수 있다.
- 최소 수정안: G3 CLI 진입 시 `Path(args[0]).resolve() == WorkPaths(args[1]).report_md.resolve()`를 강제하고 불일치면 실패한다. 또는 실제 검증 경로를 manifest와 G3 refs에 일관되게 전달하되, 최종 렌더도 동일한 정규 경로만 허용한다. 서로 다른 `clean.md`/`report.md` 픽스처로 최종 출고 차단 회귀 테스트를 추가한다.

### 3. [중대] revision_id 없는 기존 v3 하위 게이트 영수증이 일괄 무효화됨

- 위치: `scripts/gates.py:266-271`
- 근거: `_receipt_issues()`는 `[2]`, G2, G3, G5c, [4], [4b], G4, G5 모두에 `revision_id`를 요구한다. 누락 시 기존 `confirmed_digest_sha256`로 대체하는 예외는 `[2]`에만 있다. 이번 변경 전 형식의 v3 G3/[4b]/G4/G5 영수증에는 `revision_id`가 없으므로 자료와 refs가 그대로여도 `require_receipt()`에서 “revision_id 불일치/누락”으로 실패한다.
- 영향: “schema_version 없음=v3는 기존 검사만으로 통과 가능, 신규 검사는 WARN”이라는 §4 하위호환 결정과 충돌한다. 신규 claim/capture/calculation은 WARN이어도 기존 최종 작업폴더는 게이트 영수증 형식 때문에 통과하지 못한다. 신규 테스트 `test_legacy_new_checks_warn_without_silently_validating`는 대장 검사만 다루고 구형 영수증 체인은 만들지 않아 이 회귀를 놓친다.
- 최소 수정안: 작업폴더가 순수 v3일 때 기존 영수증의 revision 누락을 legacy 형식으로 해석해 기존 refs/결박 검사를 유지하거나 WARN으로 처리한다. v4 또는 새 형식 영수증부터 `revision_id`를 필수로 강제한다. 변경 전 형식의 G0→G5 원장을 합성한 회귀 테스트를 추가한다.

### 4. [경미] 고객 문서의 필수 한계 공개와 절대 규칙 문구가 충돌함

- 위치: `SKILL.md:22-23`
- 근거: 3대 절대 규칙은 여전히 “미확인 의혹·반박 상세는 고객 PDF 미노출”이라고 포괄적으로 지시한다. 바로 다음 줄은 범위·조건을 넘는 표현을 축소·재검토하라고만 한다. 수정 제안서는 운영 로그는 내부에 두되 의사결정에 영향을 주는 미확인 사항과 반론은 고객 문서에도 표시하도록 기존 원칙을 조정하라고 했다. F130 정상 문장도 “EH 적용 여부 미확인”을 고객 본문에 남겨야 하므로 현재 두 지시는 실행자에게 상충한다.
- 영향: 검토자는 required qualification을 만들었어도 “미확인 의혹 미노출” 절대 규칙을 따라 고객 원고에서 다시 제거할 수 있다.
- 최소 수정안: 3번 원칙을 “실패 URL·운영 로그·비핵심 반박 상세는 내부 audit, 의사결정에 영향을 주는 미확인 조건·반론은 고객 문서에도 표시”로 좁혀 쓴다.

## 그 밖의 대조 결과

- `verify_calculations.py`는 Decimal과 표시 정밀도 기반 끝값 구간을 사용하며 자동 덮어쓰기를 하지 않는다. 제공된 허용 수치 패턴 외 KERI 실제 기관명·파일명·사례 식별자는 diff에서 발견되지 않았다.
- `capture_review`는 이미지 해시·page_state·accept를 함께 요구하고, 차단/로그인/백지는 사실 반증이 아닌 유효 증빙 0건으로 처리한다.
- `claim-review`는 공통 `TAG`와 공통 세그먼트 분할 함수를 import해 정규식 이중구현을 피했고, 반복 문장 수까지 확인한다.
- T01~T06·T10~T12는 명명된 기본 성공/실패 사례를 실질적으로 assert하지만, 위 1~3의 API 조합 우회·경로 불일치·구형 영수증 호환 사례는 빠져 있다.

SOL_REVIEW_DONE verdict=REQUEST_CHANGES
