판정: **APPROVE**

재리뷰 2차의 잔여 3건은 fixup4에서 해소됐다. 신뢰 경계 문서는 실제 구현의 보장 범위와 일치하며, 이번 변경에서 승인을 막을 실질 결함이나 새 회귀를 발견하지 못했다.

범위와 가정:

- 판정 대상은 `p0-final4.diff`이며 SHA-256은 `15b836852db7a68121c7f31eb4fbb6f59dba19fdbf5e674392c5ffa7762caefb`다. diff의 14개 파일 모두 새 Git blob 식별자가 현재 워킹트리의 `git hash-object` 결과와 일치했다.
- `spec-p0-fixups4.md`와 `review-astra-rereview2.md`를 읽고, `p0-final3.diff` 대비 변경분 및 관련 호출 경로를 검토했다. 이미 해소된 항목은 전면 재검증하지 않았다.
- 지시 파일 옆에는 입력 자료가 없으므로, diff·스펙·선행 리뷰가 모인 scratchpad를 산출물의 “같은 폴더”로 해석했다.
- pytest 154개·데모 3종 통과와 forged_status·plan_option 차단은 팀리드가 확인한 사실로 인정했다. 이번 리뷰에서는 테스트를 재실행하지 않았으며, 아래 테스트 인용은 해당 회귀 조건을 코드로 확인한 근거다.
- 파일:라인은 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 기준이다. 저장소 코드와 테스트는 수정하지 않았다.

1. **스냅샷 결박(I3): PASS.** `scripts/manifest.py:322`의 `_final_snapshot`은 manifest entries 전체, TRACKED 경로 전체, manifest 자체, 정규 report.md·report.pdf·claim-review·계획을 포함한다. 없는 정규 입력은 `missing`으로 기록해 이후 생성도 구별한다. `scripts/manifest.py:339`에서 검사 전 해시를 수집하고, 실제 검증 호출 뒤 `scripts/manifest.py:344`에서 전체 집합을 다시 해시·대조한다. 불일치나 재해시 오류는 실패로 전환된다. 성공 시 검사 전 스냅샷을 내부 파라미터로 넘기고(`scripts/manifest.py:352`), 원장에 `snapshot_hashes`와 정규 JSON 요약 해시를 함께 보존한다(`scripts/gates.py:582`). 따라서 판정은 그 해시 집합의 리비전에 결박된다. `references/verification-gates.md:85`에 단일 작업자·락 부재·판정 리비전·사후 드리프트 계약이 명시되어 있다. 무제한 동시 쓰기나 마지막 대조 이후 교체까지 원자적으로 막는 계약은 아니며, 이번 스펙에서 명시적으로 제외한 한계다. 검증 직후 11종 입력 변경을 실패 처리하는 회귀 조건은 `tests/test_p0_regressions.py:808`에 있다.

2. **status 신뢰: PASS.** `scripts/gates.py:530`에서 `final_verification`, 관련 요약 해시, 스냅샷 필드의 extra 주입을 선행조건 검사·원장 쓰기 전에 거부한다. finalize는 extra 대신 내부 전용 파라미터를 사용하므로 정상 성공·실패 기록이 유지된다(`scripts/manifest.py:352`, `scripts/manifest.py:359`). `scripts/manifest.py:377`은 저장된 실검증 성공과 결과 요약 해시를 검사하고, `scripts/manifest.py:386`은 현재 전체 스냅샷·스냅샷 요약 해시를 대조한다. 이어 refs·manifest·봉인 파일·검증 코드까지 확인한 후 문제가 없을 때만 `최종(판정시점)`을 표시한다(`scripts/manifest.py:392`, `scripts/manifest.py:403`). 근거와 재확인 명령도 `basis`에 명시된다(`scripts/manifest.py:370`). 이 조건을 충족하지 못한 G5는 status 완료 목록에서 제외한다(`scripts/gates.py:615`). 주입 부정 테스트는 `tests/test_p0_regressions.py:744`, 정상 finalize·스냅샷 보존·상태 표시의 긍정 테스트는 `tests/test_p0_regressions.py:835`다. 내부 파라미터는 프로세스 권한을 제한하는 보안 장치가 아니며, 코드도 이를 명시한다(`scripts/gates.py:534`). 승인 근거는 문서화된 원장 기반 상태 계약이다.

3. **plan 통일: PASS.** `scripts/verify_facts.py:932`는 기록 경로의 다른 계획 경로를 거부하고, 실제 검증은 정규 계획을 사용하는 기본 인자로 실행한다. 직접 verify 호출도 custom plan은 check_only일 때만 허용한다(`scripts/verify_facts.py:852`). CLI 진단 분기는 기록 함수 호출 전에 종료한다(`scripts/verify_facts.py:1047`). G3 refs에 정규 계획의 해시 또는 `missing`이 포함되므로, 계획 변경·추가도 이후 영수증 현행성 검사에 걸린다(`scripts/gates.py:576`, `scripts/gates.py:188`). finalize 역시 기본 계획으로 재검증하므로 G3와 G5의 입력 설정이 같다(`scripts/manifest.py:173`). 다른 계획의 진단 성공이 G3 발급으로 이어지지 않는 조건과 정규 계획의 독립 결박은 `tests/test_p0_regressions.py:768`, `tests/test_p0_regressions.py:794`에 고정됐다. 기본 G0→G5 및 변경 후 재출고 경로는 `tests/test_p0_regressions.py:184`, 사용자 지정 PDF 정상 완주는 `tests/test_p0_regressions.py:729`에서 유지된다. 정규 계획이 없는 기존 조사에 대한 호환 동작도 문서에 명시되어 있어 새 누락으로 판단하지 않는다(`references/verification-gates.md:53`).

4. **신뢰 경계 문서: PASS.** `references/verification-gates.md:85`의 6줄은 구현과 일치한다. PDF 검사기는 실제 PDF 형식·페이지를 확인하고 F태그·링크 Counter 부족분과 이미지 배치 수를 대조한다(`scripts/manifest.py:285`, `scripts/manifest.py:299`). 따라서 문장·캡처 내용 동일성은 G4 팀리드 육안검증의 몫이라는 설명이 정확하다. 출고 호출은 원장에 저장된 `final_verification`을 성공 근거로 재사용하지 않고, 원고 검사와 PDF 검사를 새로 실행해 봉인·선행조건 검사와 함께 판정한다(`scripts/manifest.py:173`, `scripts/manifest.py:176`, `scripts/manifest.py:197`). 문서의 “위조 기록이 판정을 바꾸지 못한다”는 설명은 이 기계적 실검증 실패를 성공 기록으로 우회할 수 없다는 범위에서 타당하다. G4의 인간 판단을 기계적으로 입증하거나 동일 프로세스의 임의 코드 실행까지 막는 보장은 아니며, 해당 권한과 PDF 내용 동일성은 같은 절에서 명시적으로 경계를 정했다. 이 한계를 추가 결함으로 세지 않는다.

5. **fixup4 새 회귀: 발견 없음.** 변경은 스냅샷 수집·대조와 기록, 상태 조회, 예약 필드, 계획 경로 제한 및 관련 문서·테스트에 집중되어 있다. 성공과 실패의 G5 기록이 모두 내부 인자로 이행되어 예약 필드 차단에 자기 경로가 막히지 않는다. custom.pdf는 manifest entries를 통해 스냅샷에 포함되고, 정규 report.pdf 부재는 `missing`으로 처리되어 기존 정상 경로를 깨지 않는다(`scripts/manifest.py:324`, `tests/test_p0_regressions.py:835`). 일반 감사 출력은 새 스냅샷 대상에 추가되지 않으므로 검증 로그 갱신으로 발생하는 불필요한 무효화도 도입하지 않았다. 제공된 전체 테스트 통과 사실과 위 호출 경로 검토를 종합하면 이번 라운드를 종결할 수 있다.

nits: 없음.

ASTRA_VERDICT_DONE verdict=APPROVE
