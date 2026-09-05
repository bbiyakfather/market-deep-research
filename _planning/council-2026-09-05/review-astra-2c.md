# 배치 2C 품질보증 리뷰

판정: **APPROVE**

N12·N17·N20·N21은 `spec-batch2c.md`의 승인 범위에서 모두 해소됐다. 판정 대상 diff에서 승인 차단 결함이나 별도로 수정해야 할 경미 결함을 발견하지 않았다. 코드·테스트·설정은 수정하지 않았다.

## 범위와 가정

- 기준 저장소: `F:/Claude/skills/market-deep-research/`. 아래 `scripts/`, `references/`, `tests/`는 별도 표시가 없으면 `codes/market-deep-research/` 기준이다. 라인은 현재 워킹트리 기준이다.
- 호출용 `prompt.md` 폴더에는 입력 diff와 스펙이 없었다. 두 파일이 함께 있는 `C:/Users/eicic.AIDEN-DESKTOP/AppData/Local/Temp/claude/F--Claude-skills-market-deep-research/c262ea17-e2bd-49a6-a58e-625f250250a5/scratchpad/`를 요청의 “같은 scratchpad 폴더”로 해석하여 이 리뷰와 재현 증적을 저장했다.
- `batch2c.diff`와 현재 `git diff HEAD --no-ext-diff`가 일치함을 확인했다. 원 결함 정의는 `_planning/council-2026-09-05/review-astra-2.md`의 N12·N17·N20·N21을 대조했다.
- 코어 pytest 431개, gates demo, join demo, HWPX 6 passed·1 skipped는 팀리드가 검증한 사실로 수용했으며 전체 실행을 반복하지 않았다.
- 단일 writer, 강제 종료 복구 미보장, 수동 HWPX 헤딩 매핑, 지문의 보조적 사용은 명시된 설계 경계로 평가했다. 이번 승인은 원 리뷰의 다른 결함이나 전체 제품 품질을 재판정한 것이 아니다.

## 항목별 판정

| 항목 | 해소 판정 | 근거 파일:라인 및 확인 결과 |
|---|---|---|
| N12 두 대장 갱신 원자성·로드 fsck | **해소** | `scripts/facts_db.py:434`에서 evidence의 존재 여부와 원래 바이트를 보존하고, 두 번째 저장 예외 시 `:440`에서 기존 파일 복원 또는 새 파일 삭제를 수행한다. `_write_bytes_atomic`(`:345`)의 flush·fsync·동일 볼륨 replace·임시파일 정리는 유지된다. `:306`의 `check_ledger_references`를 로드 fsck(`:372`)와 G3(`scripts/verify_facts.py:546`)가 함께 호출하므로 N10 참조 검사의 이중구현이 아니다. v4 참조 위반은 생성자 예외, v3는 WARN이다(`scripts/facts_db.py:367`). 기존/신규 evidence 파일의 쓰기·replace 실패 4개 경우와 정상 add 1개 경우가 통과했다. 별도 두 번째 fsync 실패 주입에서도 두 파일의 바이트가 동일하게 복원되고 정상 재시도됐다. |
| N17 워커 join 계약 | **해소** | 필수 6개 섹션·명시적 없음·첫 줄 BLOCKED를 구분한다(`scripts/join_workers.py:66`). BLOCKED 단독은 blocked, 섹션 누락은 invalid, BLOCKED 내부 잘못된 JSON도 invalid다. 행 검증은 기존 fact/evidence 검증기를 재사용한다(`:98`). 파일 경로를 포함한 잠정 ID 범위와 참조 위치를 만든다(`:87`, `:135`, `:178`). 따라서 서로 다른 워커의 F001/E001은 구별되고, 같은 파일의 중복 정의는 오류다. AXIS+텍스트 및 URL 지문(`:152`)으로 이름이 바뀐 동일 URL 리드도 중복 후보로 표시했다. blocked/invalid는 수렴 관측에서 제외하고, 하나라도 있으면 empty_expand_wave를 false로 둔다(`:185`, `:198`). 문서의 필수 섹션·부분 실패·중앙 ID 수동 채움·보조 지문 계약(`references/agent-briefs.md:18`, `:58`) 및 G1 실행/refs 지시(`references/verification-gates.md:23`)와 일치한다. |
| N20 URL별 provenance·하위호환 | **해소** | `scripts/fetch.py:737`에서 기존 최상위 메타 필드를 보존하면서 조회별 URL·최종 URL·상태·접근시각·fetch_ref를 urls 배열에 누적한다. urls 없는 legacy sidecar도 최초 기록을 배열에 편입한다. `scripts/source_index.py:115`는 legacy 폴백과 URL별 최신 조회 선택을 수행하고, 같은 blob의 URL 집합을 각 행에 붙인다. 실제 표에는 최초 URL→최종 URL, 접근일, 상태, 동일 본문 URL 집합이 출력된다(`:181`, `:185`). legacy A 저장 후 동일 본문 B partial 저장 재현에서 최상위 필드는 전부 보존되고 A ok/B partial 두 행을 얻었다. 동일 URL의 과거 조회는 meta에 남고 표는 그 URL의 최신 조회를 표시한다. |
| N21 HWPX 인계·명시 실패 | **해소** | `codes/mdr-hwpx/scripts/build_hwpx.py:610`에서 로마숫자 부 0개, `:613`에서 기대 부 수 불일치를 출력 디렉터리 생성 전에 거부한다. CLI는 ValueError를 exit 1로 변환한다(`:789`), 옵션은 `:833`에 연결된다. 기존 분할·헤딩 승격·상대경로 보정은 유지되며, Ⅺ/Ⅻ 문자를 지원한다(`:71`). 코어 표준목차 1~11과 Ⅰ~Ⅺ의 대응·서문·사전 outline·expect-parts 11 명령은 `codes/mdr-hwpx/SKILL.md:50`에 명시되어 `references/report-format.md:9`의 목차와 일치한다. 직접 CLI 실행에서 0부와 개수 불일치는 exit 1/출력 0개, 정상 11부는 exit 0/서문 포함 12개 파일이었다. |

## 발견 및 회귀 검토

**발견 0건.** 심각도·결함 파일:라인·최소 수정안으로 보고할 수정 요구는 없다.

- 정상 `add_fact`는 기존 경로대로 원자 저장하며, `add_evidence`는 두 저장이 성공한 뒤에만 반환한다. 롤백은 디스크에서 읽은 pre-image를 사용하므로 JSON 재직렬화로 공백·CRLF를 바꾸지 않는다. 기존 파일이 없었던 경우도 absence를 복원한다. 두 번째 fsync 실패 이후 동일 E002 재등재까지 확인했으므로 실패가 다음 정상 add를 막는 회귀는 관찰하지 않았다.
- 공통 참조 검사를 옮기면서 G3는 `FactsDB` 생성자의 선행 예외 대신 원시 대장을 직접 읽고 검사 결과를 FAIL/WARN으로 합친다(`scripts/verify_facts.py:986`, `:1018`). 잘못된 v4 참조를 후속 대장 재로드 단계로 넘기지 않는 조기 반환도 실패 판정을 유지한다.
- `tests/test_p0_regressions.py:57`의 fixture 변경은 손상 대장을 G3에 전달하기 위해 생성자 fsck를 우회한 것이다. G3의 실제 참조 검사를 제거하거나 음성 사례를 정상 대장으로 바꾸지 않았다.
- 출처 표의 상태 열과 legacy/raw-only 폴백은 유지된다. URL별 행 증가와 동일 URL 최신 조회 선택은 provenance 보존 요구에 따른 의도된 변경이다.
- 중앙 ID 확정·인사이트 치환 및 이전 웨이브 대비 신규 여부 판단은 팀리드 단계다. join 결과의 null 중앙 ID를 자동 등재 완료로 오인하게 하는 계약은 없으며, 검증기는 대장에 쓰지 않는다.

## 신규 테스트의 실질성 및 직접 재현

신규 테스트는 문서 문자열이나 반환값 존재만 검사하는 수준을 넘어 실제 파일·실패 주입·CLI 종료코드를 확인한다.

| 대상 | 실질적 검증 |
|---|---|
| N12 | `tests/test_batch2c_regressions.py:23`: 첫 기록/기존 기록 × 저장 함수/실제 replace 실패, 두 파일 바이트 비교, fsck, 임시파일 제거. `:52`: 정상 두 증거 연결. `:64`: 네 참조 손상 × v3/v4의 WARN/FAIL 구분. |
| N17 | `tests/test_batch2c_regressions.py:102`: 6개 섹션 각각의 누락. `:109`: 없음/BLOCKED/오류 구분. `:119`: 잘못된 JSONL 행별 라인 번호. `:126`: 공통 스키마의 v3/v4 차이. `:139`: 파일별 ID 및 실제 중앙 add. `:171`: 링크·중복 ID·인사이트 오류. `:194`: 이름 변경 URL 중복과 수렴 제외. `:215`: 실제 CLI JSON 파일·stdout·종료코드 일치. |
| N20 | `tests/test_batch2c_regressions.py:234`: 신규/legacy meta 모두에서 A·B·B 조회 이력, fetch_ref와 상태 보존, URL별 표 확인. `:260`: 잘못된 이력 구조를 덮어쓰지 않음. |
| N21 | `codes/mdr-hwpx/tests/test_hwpx.py:314`: 실제 CLI로 0부·기대 개수·중복 파일명 거부 및 기존 출력 보존. `:338`: 서문을 제외한 11부 계산과 헤딩 승격. |

직접 실행한 집중 검사: `python -B -m pytest codes/market-deep-research/tests/test_batch2c_regressions.py -q -p no:cacheprovider -k 'n12_second_write_failure or n12_success'` → **5 passed, 27 deselected**.

추가 독립 재현은 같은 폴더의 `astra-2c-probes.py`와 `astra-2c-probes.json`에 남겼다. 두 번째 fsync 실패·복원·재시도, 원 리뷰의 워커 4가지 사례, legacy 메타/URL 표, HWPX 부정 2개/정상 1개를 확인했고 모든 assertion이 통과했다. 기존 전체 테스트 성공 사실은 이번 집중 재현 결과와 구분하여 사용했다.

ASTRA_2C_DONE verdict=APPROVE
