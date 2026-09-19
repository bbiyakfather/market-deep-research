STATUS: complete

CHANGES:
- `codes/market-deep-research/scripts/verify_facts.py`: 통화코드 단위의 전체 문법을 먼저 검증하여 `USD_million_extra`·`USD_billionTypo`를 `[단위미지원]`으로 차단했다. 미인식 후보를 알려진 영문 단위의 대소문자 변형·한국어 단위명으로 제한하고, 목록 밖 숫자+한글은 비수량 문맥을 제외하여 `[수치미인식?]` 경고로 구분했다. 영숫자 식별자 내부 수치 시작을 막고 표 셀 값일치 폴백으로 인정된 태그를 결박 집합에 포함했다.
- `codes/market-deep-research/references/verification-gates.md`: G3의 3C 추가 설명을 전체 단위 검증·미인식 후보와 경고·표 셀 결박 규칙에 맞췄다(순증 2줄).
- `codes/market-deep-research/tests/test_batch3c_regressions.py`: 기존 내용을 그대로 보존하고 73개 회귀 사례를 추가했다. 지시서 표 전 행, B2B/M2M/T1 표 행, 비수량 인용, 한국어 접두 단위, 개국 경고, 미인식 판정 발동 조건을 검사한다.
- `batch3d-report.md`: 실행 결과와 판단 가정을 기록했다.

VERIFIED:
- 최초 `git log --oneline -1`: `9d915d8 fix(mdr): 배치 3A — 검토 근거 결박·조건 명시·버전 고정·부록 인용 검증 (R01·R03·R04·R05)`.
- `codes/market-deep-research`에서 `PYTHONUTF8=1`로 `python -m pytest -q tests/test_batch3c_regressions.py`: `94 passed in 0.11s` (exit 0).
- 같은 위치·환경에서 `python -m pytest -q`: `587 passed in 49.93s` (exit 0). 기존 514개와 추가 73개 전부 통과했다.
- `git diff --check`: 공백 오류 없이 exit 0. Git의 LF→CRLF 변환 예고만 출력됐다.
- Python으로 HEAD의 기존 테스트 전체가 현재 파일의 동일한 접두 원문임을 검증하고, AST로 변경된 함수가 `_resolve_unit`·`_unrecognized_num_tokens`·`check_bound_numbers`뿐임을 검증했다: `BASE_TESTS_AND_SCOPE_OK` (exit 0).

JUDGMENT CALLS:
- 기존 테스트가 요구하는 `USD billion` 같은 단일 공백 구분은 밑줄로 정규화한 다음 전체 문법을 검사하여 호환성을 유지했다. 기존 괄호 부연 제거도 유지했다.
- 지시서가 명시한 thousand/trillion 별칭을 공통 통화 배수 목록에 포함했다. 통화코드는 기존 파서와 동일하게 영문 3글자로 취급하며 외부 ISO 목록 의존성은 추가하지 않았다.
- 한국어 단위 뒤 일반적인 조사·접미사는 허용하지만 `원문` 같은 단어는 단위명으로 인정하지 않는다. `원`은 지시서의 제한을 따라 바로 앞 문자가 숫자·억·조·만·천인 경우만 미인식 단위 후보로 인정했다.
- 연도·월일·분기·순번·법조문 외에 기존 문서 구조와 약한 계수 표현(부·장·절·권·회·쪽·페이지·개월·개·대·기)도 비수량 경고 제외 대상으로 유지했다. 같은 세그먼트에 확실한 단위 후보와 모호한 후보가 함께 있으면 실패 후보를 우선 보고한다.
- 시작 시 이미 존재한 미추적 `batch3c-report.md`는 수정하지 않았다. 별도 에이전트 호출, 외부 네트워크, 설치, 커밋, 푸시, 브랜치 변경은 수행하지 않았다.

GAPS: 없음.
