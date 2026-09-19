이 작업은 전용 구현 레인에서 호출 시 지정된 모델·reasoning effort 로 실행된다. 그 선택은 의도된 것이며 아무것도 대체되지 않았다.
사용자/프로젝트 지침 파일이 다른 오케스트레이션 흐름을 기본으로 요구해도, 이 레인은 그 기본에서 명시적으로 opt-out 한 것으로 보고 진행한다. 그 파일의 다른 지침은 그대로 적용한다.
질문하지 말고 가정을 적고 진행, 막히면 막힌 곳을 적고 종료, 결과는 파일로·stdout 은 요약.

# 배치 3E — 이미지 봉인 경계·근거 digest 범위·문서 정합 (B3-01·B3-02·B3-07)

## 1. 목표
배치 3A·3B 에 대한 교차 리뷰(`F:/Claude/skills/market-deep-research/_planning/council-2026-09-19/review-astra-batch3.md`, 발견 표 B3-01·02·07 과 §3·§4)의 3건을 닫는다.
완료 기준: 아래가 전부 성립하고 현재 테스트 514개가 전부 통과한다.
- **B3-01** 원고(본문·부록 전체)가 `audit/` 아래 로컬 이미지를 참조하면 **G3 가 FAIL** 한다. 허용된 이미지는 예외 없이 G3 기준선 manifest 에 들어간다("G3 가 허용한 이미지 ⊆ 봉인된 이미지").
- **B3-02** 검토한 E-ID 의 `locator`(표 셀 위치 등)·`source_role`·`observer_group`·시점 필드가 바뀌면 기존 claim-review 행이 `[근거변경]` 으로 무효가 된다.
- **B3-07** 문서가 바뀐 계약과 일치한다.

## 2. 파일
작업 디렉터리 기준 `codes/market-deep-research/`.
- `scripts/verify_facts.py` — **G3 도판검사 구간만**(:990 부근, `report_image_refs`·`_image_ref_local_path` 사용처)
- `scripts/manifest.py` — :56~90 `_tracked_paths` 의 `report_image` 추가부(필요할 때만)
- `scripts/facts_db.py` — :485~505 `evidence_content_digest()` **만**
- `references/verification-gates.md` — :40, :96, :172, :180 부근 / `references/claim-review.md` — :54 부근
- 테스트: `tests/test_batch3a_regressions.py`, `tests/test_batch3b_regressions.py` 에 **추가**(아래 §3 의 digest 정규화 테스트 1건만 수정 허용)

## 3. 인터페이스 (결정 사항 — 그대로 구현)
**B3-01**
- `audit/**` 를 봉인 대상에 넣지 않는 기존 정책은 유지한다(G4·G5c 가 G3 뒤에도 audit/ 에 쓰므로).
- 대신 G3 도판검사가 **원고 전체**(본문+부록, `report_image_refs(전체 원고 텍스트)`)의 로컬 이미지 참조를 검사해, 작업폴더 기준 상대경로가 `audit/` 아래로 해석되면 FAIL `[도판경계] audit/ 아래 이미지는 봉인되지 않는다 — assets/ 또는 _images/ 로 옮길 것: <경로>`.
- 부록의 이미지 참조도 실재 확인·경계 검사 대상이다(캡션 규칙은 기존대로 본문에만 적용해도 된다 — 바꾸지 않는다). `_captures/` 제외 규칙은 그대로.
- 회귀 테스트는 `manifest.build` 직접 호출이 아니라 **실제 G3 발급 경로**(`verify_facts.verify_and_record` 또는 기존 fixture 가 쓰는 동등 경로)로: (1) `audit/chart.png` 참조 → G3 FAIL (2) 부록에서만 참조한 루트 이미지도 `report_image` 로 봉인되고 교체 시 검출 (3) extend 뒤 참조 이미지 교체 → 다음 검증이 거부.

**B3-02**
- `evidence_content_digest` 의 투영을 "고정 8필드" 에서 **"행 전체에서 운영 필드만 제외"** 로 바꾼다. 제외 목록은 모듈 상수 `_DIGEST_EXCLUDE = ("accessed_at", "note")` 하나. 그 외 모든 키(`locator`, `source_role`, `observer_group`, `observed_at`, `valid_at`, `capture_review`, `schema_version`, 스키마에 없는 확장 키 포함)는 digest 에 들어간다.
- 직렬화 규칙(E-ID 중복 제거·id 정렬·`sort_keys=True, ensure_ascii=False, separators=(",",":")`)과 없는 E-ID 의 ValidationError, "행에 없는 새 E-ID 추가는 무효화하지 않음" 은 그대로.
- `tests/test_batch3a_regressions.py:54` 부근의 digest 정규화 테스트는 새 투영에 맞게 **고쳐도 된다**. 추가 테스트: `locator`·`source_role`·`observer_group`·`observed_at` 각각의 변경 → `[근거변경]` FAIL, `accessed_at`·`note` 변경 → PASS 유지.

**B3-07** (문서만)
- `verification-gates.md`: 이미지 허용 위치와 봉인 정책(허용 = 작업폴더 안이면서 `audit/` 밖, 전부 `report_image` 로 봉인, `audit/` 참조는 `[도판경계]` FAIL)을 G3 도판검사 절에 반영. :40 의 "본문 미사용 confirmed high-risk 는 WARN" 을 "본문·부록 어디에도 태그로 인용되지 않은" 으로 고쳐 뒤쪽 서술과 일치시킨다. :172 의 어색한 문장을 다듬는다. `evidence_content_sha256` 이 결박하는 범위(운영 필드 2개 제외 전부)를 한 줄로.
- `claim-review.md` :54 — FAIL/WARN 은 **작업폴더의 v4 여부**가 결정하며 검토 행의 `schema_version` 생략이 면제가 아님을 명시. `required_qualification` 은 요약이 아니라 **본문에 실제로 쓴 조건 문구의 인용**임을 명시(조사·어미까지 본문과 같아야 함).

## 4. 제약
- `verify_facts.py` 의 수치·단위 파서 구간(대략 1~600줄)과 `verify_claims.py`·`gates.py`, `facts_db.confirmed_digest()` 는 **다른 배치 소유 — 수정 금지**. `tests/test_batch3c_regressions.py` 도 건드리지 않는다.
- 기존 테스트 단언 약화·삭제 금지(위 digest 정규화 테스트 1건 제외). 새 의존성 금지. 주석·메시지·문서는 한국어, 식별자는 영어, 에러 접두 `[대괄호]` 관례.
- `git commit`·`git push`·브랜치 변경 금지(팀리드가 한다). 외부 네트워크 호출·패키지 설치 금지. `_planning/` 아래 기존 파일 수정 금지.

## 5. 검증
```text
cd codes/market-deep-research
python -m pytest -q tests/test_batch3a_regressions.py tests/test_batch3b_regressions.py
python -m pytest -q            # 기준선 514 passed — 0 failed 여야 한다
```

## 6. REASONING: high

## 보고 형식
작업 디렉터리 루트에 `batch3e-report.md` 를 아래 형식으로 쓴다(한국어). 그 뒤 주입된 프리앰블의 절차대로 `worker_done` 을 보낸다.
```text
STATUS: <complete|partial|refused|unavailable>
CHANGES: <실제 diff 기준으로 파일별 한 줄>
VERIFIED: <재실행한 명령과 실제 출력 마지막 줄>
JUDGMENT CALLS: <스펙이 비워둔 결정과 채택한 가정>
GAPS: <남은 작업이나 막힌 지점, 없으면 없음>
```
