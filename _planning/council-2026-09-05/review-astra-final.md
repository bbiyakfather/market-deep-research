# market-deep-research P0 최종 diff 리뷰

판정: **REQUEST_CHANGES**

범용 성공 기록 API는 차단됐지만, 새 전용 기록 함수를 조합하면 G3 검증 실패 원고와 렌더하지 않은 PDF를 여전히 최종본으로 승인할 수 있다. 선행 ①은 부분 해소이며, ②·③·④는 해소다.

## 범위·가정

- 판정 대상은 `p0-final.diff` 2,201줄이다. SHA-256: `2a66beb7f80d84a93d643c7ce6f05cca8d068b510267cf461e0c84183c51b2f4`.
- diff에 포함된 14개 파일의 새 Git blob 식별자를 워킹트리와 대조해 모두 일치함을 확인했다. 아래 파일·라인은 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 기준이다.
- 지시 파일 옆에는 입력 문서가 없어, 실제 입력 네 파일이 함께 있는 scratchpad를 “같은 폴더”로 해석하고 이 판정서도 그곳에 기록했다.
- 원 스펙, fixup 스펙, 선행 리뷰 및 원 수정 제안서를 읽었다. pytest 121개·데모 3종·KERI 재현 통과는 제공된 검증 사실로 받아들였고 재실행하지 않았다.
- 위협 범위는 이번 요청에 명시된 **전용 기록 경로의 임의 호출 조합**까지 포함한다. 소스 수정·monkeypatch·원장 직접 편집·해시 위조는 재현에 사용하지 않았다. 함수명에 밑줄을 붙이거나 docstring에서 내부 호출을 신뢰 경계 밖으로 선언하는 것만으로 이 요구를 제외할 수는 없다.
- 저장소 구현·테스트·KERI 원본은 수정하지 않았다. 추가 실행은 임시 폴더의 합성 픽스처로 수행한 두 가지 집중 재현이다.

## 선행 지적 4건 해소 판정

| 선행 지적 | 판정 | 근거 |
|---|---|---|
| ① 소유 게이트 성공 기록 거부 + 전용 경로 결박값 자체 계산 | **부분** | `scripts/gates.py:477`–`487`은 범용 API의 G3/[4b]/G5 성공을 거부한다. `scripts/gates.py:502`–`528`은 manifest·산출물 해시를 디스크에서 재계산하고 `extra`도 받지 않는다. 그러나 검증·렌더 실행을 요구하지 않아 전용 경로만 호출하는 최종 출고 우회가 남는다. 아래 발견 1 참조. |
| ② G3 검증 원고와 봉인·렌더 원고 동일성 | **해소** | `scripts/verify_facts.py:1010`–`1014`에서 CLI 입력의 resolve 경로를 정규 report.md와 비교하고 불일치 시 exit 1. `scripts/verify_facts.py:863`–`865`는 정규 원고가 존재하는 함수 호출도 실패 처리한다. `scripts/render_pdf.py:108`–`112`도 정규 원고만 허용한다. `tests/test_p0_regressions.py:403`–`429`에 clean.md/alternate.md 부정 사례가 있다. |
| ③ 순수 v3의 revision_id 없는 구형 영수증 | **해소** | `scripts/gates.py:253`–`269`은 facts·evidence 모든 행에 schema_version이 없고 새 영수증 메타데이터도 없는 경우만 revision 누락을 WARN으로 처리한다. refs·input digest·[2] confirmed 결박 검사는 `scripts/gates.py:273`–`305`에 유지된다. manifest도 `scripts/manifest.py:122`, `172`에서 같은 판정을 재사용한다. `tests/test_p0_regressions.py:432`–`515`는 구형 v3 승인·v4 거부·기존 결박·신규 영수증 revision 삭제 차단을 다룬다. |
| ④ 내부 운영 로그와 고객 표시 한계 구분 | **해소** | `SKILL.md:22`에서 내부 대상은 실패 URL·운영 로그·비핵심 반박 상세로 한정하고, 의사결정에 영향을 주는 미확인 조건·반론은 고객 문서에 표시하도록 명시했다. |

## 발견 1 — [치명] 전용 기록 경로가 파일 일치만 확인해 실패 원고·미렌더 PDF의 최종 출고를 허용

**위치:** `scripts/gates.py:490`–`528`, 특히 G3 분기 `510`–`513`, [4b] 분기 `514`–`522`, 무조건 성공 기록 `528`. 최종 신뢰 지점은 `scripts/manifest.py:165`–`175`, `181`–`197`.

**근거와 원인:** `_record_owned_result(work, gate, result_summary)`는 G3에서 manifest와 report.md가 현재 파일과 일치하는지만 검사한다. `verify_facts.verify()`의 PASS 여부는 확인하지 않으며, 호출자가 임의로 쓴 결과 요약도 그대로 해시한다. [4b]에서는 `manifest.extend()`가 만든 확장 기록의 이전 manifest 해시와 추가 경로만 검사한다. 실제 렌더 실행이나 렌더 결과 여부는 확인하지 않는다. 두 분기 모두 마지막에 exit 0을 발급한다.

따라서 해시를 정확히 재계산해도, 검증되지 않은 입력과 임의 산출물의 바이트를 정확히 봉인할 뿐이다. `finalize_report()`는 이렇게 발급된 영수증을 실제 소유 단계 PASS와 구분하지 못한다. `gates.py:494`의 “Python 내부 함수 호출 … 신뢰 경계 밖” 문구는 원장 직접 편집에 대한 기존 한계를 이번 수정 대상인 전용 기록 경로 호출까지 확장하고 있다.

**집중 재현 A: G3가 실제로 실패하는 원고를 최종 승인**

기존 합성 `work` 픽스처를 임시 폴더에 만들고, 본문만 `EXPANDED` 문장으로 바꿨다. 실제 `verify_facts.verify()`는 문장 변경·검토 누락으로 FAIL이었다. 이후 다음 함수 조합은 모두 성공했다.

```python
# wp는 합성 v4 작업폴더이며 G0 → G1 → [2]는 정상 기록된 상태다.
manifest.build(wp, for_g3=True)
g3 = gates._record_owned_result(wp, "G3", "owner record without PASS")

wp.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
manifest.extend(wp, [wp.report_pdf],
                expected_sha256=g3["manifest_sha256"])
gates._record_owned_result(wp, "[4b]", "owner record without render")
gates.record_manual(wp, "G4", "review declaration", refs=["report.pdf"])
result = manifest.finalize_report(wp)
```

원고는 미지원 속성을 포함하고 PDF는 19바이트의 가짜 파일인데도 결과는 다음과 같았다.

```json
{"scenario":"failed_g3","actual_g3_ok":false,"final_ok":true,"publication_state":"최종","g5_current":true}
```

실제 G3 실패 메시지는 `현재 본문에 sentence_text 없음 — 문장 변경 후 재검토 필요`와 `검토 누락(1건)`이었다. 실패 검사 결과를 diagnostic으로 확인했을 뿐, 정상 G3 PASS 발급 경로를 실행하지 않았다.

**집중 재현 B: 실제 G3 PASS 이후 렌더만 생략**

별도의 정상 합성 v4 작업폴더에서 `verify_facts.py` CLI를 실제 실행해 exit 0과 G3 영수증을 받았다. 이후 위 코드의 가짜 PDF 생성·extend·전용 [4b] 기록·G4·finalize 부분만 실행했다. `render_pdf.render()` 및 렌더 CLI는 호출하지 않았다.

```json
{"scenario":"skipped_render","actual_g3_ok":true,"final_ok":true,"publication_state":"최종","g5_current":true}
```

이는 G3 위조를 먼저 성공시켜야만 생기는 문제가 아니다. 정상 G3 뒤에도 전용 [4b] 기록 경로가 독립적으로 렌더 소유 조건을 우회한다.

**기존 추가 테스트가 놓치는 이유:** `tests/test_p0_regressions.py:358`–`400`은 차단된 범용 `record_script_result()`만 호출한다. `518`–`531`은 전용 함수의 extra 주입·확장 누락·파일 드리프트 거부를 확인하지만, 디스크 해시가 모두 맞는 상태에서 실제 검증·렌더를 생략하는 위 조합은 검사하지 않는다.

**최소 수정안:** G3와 [4b]의 전용 진입점을 해당 소유 작업을 실행하는 함수로 바꿔야 한다. G3는 정규 원고에 기존 `verify_facts.verify()`를 실행해 PASS인 경우에만 봉인·기록하고, [4b]는 기존 `render_pdf.render()`를 실행해 반환된 산출물만 확장·기록하도록 묶는다. CLI도 이 경로를 재사용해 검증·렌더와 성공 발급이 분리되지 않게 한다. 디스크 해시·임의 결과 요약만으로 성공을 발급하는 별도 전용 경로는 제거하거나, 소유 작업 완료 없이는 발급할 수 없도록 바꾼다. 기존 검사·렌더 구현은 재사용하고 새 의존성은 필요하지 않다. 위 두 시나리오를 부정 회귀로 추가해 `finalize_report()["ok"] == False`와 현행 G5 부재를 검증해야 한다.

## 그 밖의 대조 결과

- legacy 예외는 schema_version이 한 행이라도 존재하면 적용되지 않고, 신규 영수증에서 revision_id만 지워도 적용되지 않는다. 검토한 범위에서 ③ 자체가 v4를 legacy로 잘못 승인하는 별도의 우회는 확인하지 못했다.
- `confirmed_digest()`의 v3 투영은 보존되며 v4는 전체 value·claim·context·claim_type을 추가 결박한다. 신규 영수증은 append 모드로 기록하고 supersedes·선행 영수증 식별자를 남긴다.
- CAGR은 Decimal과 표시 정밀도 기반 끝값 구간을 사용한다. 입력 부족·기간 불일치의 NOT_CHECKABLE 처리와 자동 덮어쓰기 금지에 대해 별도의 중대 위반을 발견하지 못했다.
- claim 검사는 기존 TAG·세그먼트 함수를 import하고, capture 검사는 기존 경계·해시 함수와 fitz를 활용한다. 추가 런타임 외부 의존성, P1/P2 기능 확장, KERI 실데이터·파일명의 diff 유입은 확인하지 못했다. 신규 테스트의 pytest 사용은 원 스펙에 명시된 검증 경로다.
- UTF-8 콘솔 설정은 공통 `scripts/skill_paths.py:29`–`34`를 통해 신규 CLI에도 적용된다.

ASTRA_REVIEW_DONE verdict=REQUEST_CHANGES
