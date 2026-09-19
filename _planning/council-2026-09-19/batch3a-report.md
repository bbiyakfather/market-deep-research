STATUS: complete

CHANGES:
- `codes/market-deep-research/scripts/facts_db.py`: 버전 필드 오타를 거부하고 지정 E-ID의 근거 내용 정규 JSON SHA-256 함수를 추가했다.
- `codes/market-deep-research/scripts/verify_claims.py`: 근거 내용 결박 누락·변경, 가정/권고 조건 누락·본문 불일치를 검사하고 v4 부록 문장·목록을 전건 검토에 포함했다.
- `codes/market-deep-research/scripts/verify_facts.py`: 본문·부록 태그를 사용 집합으로 합쳐 high-risk·캡처 검사를 적용하고, v4 폴더에서 인용된 v3 사실·연결 증거를 거부한다.
- `codes/market-deep-research/scripts/manifest.py`: 순수 v3 출고의 기본 거부와 `allow_legacy_v3`/`--allow-legacy-v3` 명시적 허용을 추가하고 G5의 `legacy_v3` 및 status 설명을 기록한다.
- `codes/market-deep-research/assets/facts-schema.json`: 버전 오타·혼합 인용·순수 v3 출고 계약을 설명에 명시했다.
- `codes/market-deep-research/references/claim-review.md`: 근거 내용 해시, 조건 문구, 부록 검토 범위를 해당 절에 반영했다.
- `codes/market-deep-research/references/verification-gates.md`: 혼합 버전 인용 차단과 v3 호환 출고 및 부록 인용 계약을 이행 절에 반영했다.
- `codes/market-deep-research/tests/test_batch3a_regressions.py`: 지정된 R01·R03·R04·R05와 정상 대조군 55개를 새 파일 하나에 추가했다.
- `codes/market-deep-research/tests/test_p0_regressions.py`: 정상 검토 픽스처의 해시·조건 문구를 갱신하고 구형 v3 출고 테스트 두 호출에 호환 플래그를 추가했다.
- `codes/market-deep-research/tests/test_batch2b_fixup.py`: 검토 픽스처의 E-ID를 E002로 바꿀 때 E002의 근거 내용 해시도 함께 설정했다.
- `codes/market-deep-research/tests/test_adversarial.py`: 기존 v3 최종 출고 CLI 호출에 `--allow-legacy-v3`만 추가했다.
- `codes/market-deep-research/tests/test_e2e.py`: 기존 v3 E2E 최종 출고 CLI 호출에 `--allow-legacy-v3`만 추가했다.
- `batch3a-report.md`: 작업 결과·실제 검증·판단 사항을 기록했다.

VERIFIED:
- `codes/market-deep-research`에서 `python -m pytest -q tests/test_batch3a_regressions.py` → `55 passed in 4.07s`.
- 같은 위치에서 `python -m pytest -q` → `486 passed in 54.95s` — 기존 431개 및 신규 55개, 실패 0개.
- `git -c core.safecrlf=false diff --check` → 출력 없음, exit 0.
- Git HEAD와 현재 소스의 AST 함수 본문을 대조했다: `confirmed_digest`, `manifest.build/extend/_scan`, `verify_facts.check_figures/split_segments/check_bound_numbers` 모두 동일하다.
- `gates.py` diff가 비어 있음을 확인했다. `TRACKED`·렌더/봉인 스캔·수치/단위 파서·도판 검사는 수정하지 않았다.
- 외부 네트워크 호출·패키지 설치·커밋·푸시·브랜치 변경·기존 `_planning/` 파일 수정 없이 수행했다.

JUDGMENT CALLS:
- 실제 주입된 Dispatch 지침이 worker_done 1회와 heartbeat를 요구하고 Orca CLI도 정상 동작하므로, 지시서의 과거 샌드박스 전제에 따른 CLI 금지 대신 현재 Dispatch 수명주기 규칙을 적용했다.
- 근거 내용 해시는 지정 E-ID를 중복 제거·정렬하고 고정 필드의 누락을 JSON null로 표현한다. `capture_review`는 존재할 때 중첩 객체 전체를 포함하며, `confirmed_digest`와 `evidence_revision`의 의미·값은 바꾸지 않았다.
- claim-review 행의 선택적 `schema_version`은 3/4만 허용하고 오타는 v3에서도 FAIL이다. 근거 결박·조건 검사의 FAIL/WARN 수준은 기존과 동일하게 작업 폴더의 v4 여부를 따른다.
- 부록의 일반 대장 투영 표는 기존 면제를 유지한다. 기존 `test_batch2b_fixup.py`가 요구하는 명시적 disputed 상충 표의 검토는 유지하여 기존 안전성 단언을 약화하지 않았다.
- `gates.py` 수정 금지와 status의 호환 출고 표시를 함께 만족시키기 위해 `manifest.publication_state()`의 `basis`에 `legacy(v3) 출고`를 추가했다. G5 최상위 payload와 해시로 결박된 `final_verification` 양쪽에 `legacy_v3: true`를 기록한다.
- `stats.body_tags`는 기존처럼 본문 태그 수를 유지하고 실제 검증용 `used`에만 부록 태그를 합쳤다.
- 기존 테스트 수정: `test_p0_regressions.py:25,61,64`는 새 필수 해시를 정상 픽스처에 추가하고 기존 조건 문구를 실제 LIMITED 문장의 부분 문자열로 맞췄다. 기존 단언은 변경하지 않았다.
- 기존 테스트 수정: `test_batch2b_fixup.py:11,74,104`는 E-ID 변경 뒤 실제 검토 대상 E002의 해시를 설정했다. 기존 부정 테스트의 문장 일부 검토·리비전 변경 차단 단언도 그대로 유지했다.
- v3 호환 플래그만 추가한 기존 호출: `test_p0_regressions.py:470,511`, `test_adversarial.py:1405`, `test_e2e.py:159`.
- 번호 목록의 `1.`을 분리하는 기존 문장 파서는 유지했다. 신규 회귀는 `tagged_sentences()`가 제공하는 실제 검토 문장을 사용한다.

GAPS: 없음. 통합·커밋은 조정자 소관이며 이 워크트리에 검토 가능한 변경을 남겼다.
