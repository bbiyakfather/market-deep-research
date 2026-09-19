# 배치 2B 표적 재리뷰 최종 판정

판정: **REQUEST_CHANGES**

기존 R1·R2·R3은 모두 해소됐다. 다만 R1의 URL 제거식 수정이 정상 링크의 괄호 안 숫자를 본문 주장으로 오인하는 새 회귀 R4를 만들었다. 실제 G3 내용 검사가 정상 보고서를 차단하므로 사소 지적으로 분류하지 않는다.

## 범위·가정·검증

- 호출 prompt 폴더에는 입력 자료가 없으므로, 지정된 세 입력이 함께 발견된 이 scratchpad를 산출물의 “같은 폴더”로 해석했다.
- `batch2b-final.diff`와 이전 `batch2b.diff`의 차이로 fixup 범위를 식별했다. 판정은 R1·R2·R3 및 해당 수정의 새 회귀에 한정하며, 이미 해소된 다른 배치 항목은 재리뷰하지 않았다.
- 아래 `scripts/`와 `tests/` 경로는 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 기준이며 라인은 최종 워킹트리 기준이다. 최종 diff에는 신규 `tests/test_batch2b_fixup.py`가 실려 있지 않지만, prompt가 최종본으로 지정한 워킹트리의 해당 파일을 보조 검증 근거로 확인했다.
- 전체 pytest 398개·gates·claims 데모 통과는 팀리드 제공 사실로 수용했다. 전체 검증은 재실행하지 않았다. 표적 테스트는 직접 실행해 `25 passed in 2.29s`를 확인했다: `python -m pytest tests/test_batch2b_fixup.py -q -p no:cacheprovider`.
- 새 회귀는 임시 fixture의 실제 `verify(..., check_only=True)`로 재현했다. 수정 전 비교본은 `git show HEAD:codes/market-deep-research/scripts/verify_facts.py`에 기존 `batch2b.diff`의 해당 파일 hunks를 메모리에서 적용해 복원했으며, context와 삭제 행 일치를 assertion으로 검사했다. 저장소 코드·테스트를 수정하지 않았다.

## 기존 발견 3건의 해소 근거

| 발견 | 판정 | 코드·대조 근거 |
|---|---|---|
| R1: URL 인접 태그의 disputed 차단 누락 | **해소** | `scripts/verify_facts.py:392`에서 `preserve_text=True` 원문 세그먼트를 얻고, `:394`에서 상충 문맥, `:395`에서 태그 존재, `:400`에서 status를 검사한다. URL 제거는 그 뒤 `:403`에서 수치 검사에만 적용된다. `tests/test_batch2b_fixup.py:14`의 12개 조합은 인접/공백 태그 × confirmed/무마커 disputed/명시 상충 disputed × 수치 유무를 실제 G3로 대조하며, `:32`는 미등록 태그 차단을 확인한다. 기존 우회는 차단되고 confirmed와 명시 상충의 정상 대조는 통과한다. |
| R2: disputed 부록 문장검토 누락 | **해소** | `scripts/verify_claims.py:58`에서 명시 상충 마커와 disputed F태그가 있는 부록 세그먼트를 고르고 `:62`에서 본문 검토 대상에 합친다. `:91`의 현재 문장 존재, `:93`의 전체 세그먼트 일치, `:97`의 reviewed_text_sha256, `:99`의 evidence_revision, `:119`~`:122`의 발생 횟수별 검토 누락 검사를 공유한다. `tests/test_batch2b_fixup.py:52`는 일반 문장·링크 인접 태그·표행의 검토 누락 실패/정식 검토 통과/문장 교체 실패를 대조하고, `:70`과 `:77`은 해시·revision 변조 및 실제 disputed context 변경을 차단한다. `:85`의 부분 문장 검토도 실패한다. |
| R3: Decimal 범위 및 핵심수치 분류 회귀 | **해소** | `scripts/verify_facts.py:60`의 공통 숫자 토큰이 선행 소수점과 부호 있는 지수를 수용하고 `:61`~`:63`에서 범위 끝점 부호와 구분자를 구성한다. `:283`~`:288`에서 양 끝점을 Decimal로 읽으며, `:692`는 같은 `_ledger_qty` 결과를 핵심수치 판정에 사용한다. `tests/test_batch2b_fixup.py:94`의 8개 표기는 `.5~.6`, `1e3~2e3`, `1e-3~2e-3`, 명시 양수 지수, 기존 하이픈 범위, 음수 정수·소수·지수 범위를 포함한다. `:112`~`:122`에서 원 표기/동치값 통과와 값/부호 불일치 실패를 후행·접두 통화 양쪽으로 확인하며, `:123`에서 핵심수치 캡처 누락 실패를 확인한다. |

## 새 발견 R4 — 중간(P2): 괄호가 있는 정상 URL의 숫자가 본문 주장으로 검출됨

- **위치:** `scripts/verify_facts.py:136` 및 `scripts/verify_facts.py:403`.
- **원인:** 새 `_URL = re.compile(r"https?://[^\s<>()\[\]]+")`는 링크 뒤 태그를 보존하려고 URL 내부의 여는 괄호에서도 일찍 멈춘다. 정상 Markdown 링크 목적지의 균형 잡힌 괄호까지 URL 경계로 취급하므로 뒤쪽 경로 문자열이 수치 검사 입력에 남는다.
- **재현:** 유효한 v4 confirmed F001(value.raw=`45`, unit=`USD`), 연결 증빙·캡처·전체 문장 검토를 준비하고 다음 문장을 기록한다. F태그는 URL 앞에 있으므로 원 R1의 태그 소실과 독립적인 대조다.

```markdown
Source claims 45 USD(F001) [source](https://example.test/source_(999MW)).
```

- **실제 결과:** 수정 전 배치 2B의 G3 내용 검사는 `ok=true`, failures 0이다. 최종본은 `ok=false`이며 `[무태그] 수치 사실주장에 F태그 없음: '999MW'`를 반환한다. URL 제거 뒤 문자열은 `Source claims 45 USD(F001) [source]((999MW)).`가 된다. 화면에 표시되는 본문 수치는 45 USD뿐이고 999MW는 링크 목적지에만 있다.
- **정상 대조:** URL을 `https://example.test/source_999MW` 또는 `https://example.test/source_%28999MW%29`로 바꾸면 수정 전·최종본 모두 통과한다. 주장·대장·검토 절차는 같고 URL 내부 괄호 표기만 달라진다. 상세 결과는 같은 폴더의 `astra-2b-final-url-probes.json`에 저장했다.
- **영향:** 숫자와 단위가 괄호 안 경로에 포함된 정상 출처 링크를 쓰면 G3가 보고서를 차단한다. 새 테스트 `tests/test_batch2b_fixup.py:22`의 단순 `/999mw` 주소에는 괄호가 없어 이 회귀를 탐지하지 못한다.
- **최소 수정 방향:** 원문 상태·태그 검사 분리는 유지하면서, 숫자 검사에서는 균형 잡힌 괄호를 포함한 Markdown 링크 목적지 전체를 제거하고 링크 바깥 F태그를 보존해야 한다. 괄호 포함/미포함 주소의 정상 통과와 링크 뒤 disputed 태그 차단을 함께 대조하면 두 요구가 동시에 유지되는지 확인할 수 있다.

R1·R2·R3은 재개방하지 않는다. 새 회귀 R4를 해소한 뒤 해당 변경만 표적 재검토하면 된다.

ASTRA_2B_FINAL_DONE verdict=REQUEST_CHANGES
