# finalize 실검증 전환 표적 재리뷰 2차

판정: **REQUEST_CHANGES**

기본 설정·변경 없는 입력에서 finalize가 현재 원고와 PDF를 직접 검사하는 구조 전환은 구현됐다. 검사 전용 모드는 내용 검사를 생략하지 않는다. 그러나 **검사 후 파일 교체에 대한 I3가 깨지며, 반환 시점의 I1도 실제로 깨진다.** 별도로 status는 호출자가 위조한 실검증 결과를 받아 최종 상태를 표시한다. 사용자 지정 승인 계획의 재검증 설정도 보존되지 않는다.

## 범위와 가정

- 판정 대상: `p0-final3.diff`. SHA-256: `86d7545e3e4fdc2b21cbe66d6e78bfffee988439662f99c5bcd532397ee57e32`.
- diff의 14개 파일 모두 새 Git blob 식별자가 워킹트리와 일치했다. 아래 구현 파일:라인은 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 기준이다.
- 지시 파일 옆에는 입력 자료가 없으므로, diff·스펙·선행 리뷰가 모여 있는 scratchpad를 산출물의 “같은 폴더”로 해석했다.
- pytest 135개·데모 3종 통과 및 기존 재현 A·B 차단은 제공된 사실로 인정하고 재실행하지 않았다. 300건 1.69초는 제공된 측정치로 취급하며 독립 벤치마크를 수행하지 않았다.
- 저장소 구현·테스트는 수정하지 않았다. 추가 재현은 별도 임시 작업폴더에서 실행했다. 실행 코드와 결과는 이 문서 옆 `astra-rereview2-probes.py`, `astra-rereview2-probes.json`에 보존했다.
- 경쟁 조건 재현은 `sys.settrace`로 지정된 줄에 도달했을 때 **입력 파일만** 변경해 실행 순서를 결정했다. 검증 함수·반환값·원장을 monkeypatch하거나 검증 조건을 수정하지 않았다. 이는 가능한 파일 교체 순서를 재현한 것이며, 실제 동시 실행의 발생 빈도를 측정한 것은 아니다.
- 동시 변경이 없는 경우와 반환 순간까지 입력이 동일해야 하는 경우를 구분한다. 사용자 지정 PDF는 기존 허용 계약으로 인정한다. 따라서 custom.pdf만 있는 정상 경로를 report.pdf 부재만으로 결함 판정하지 않는다.

## 1. I1 — 기본 검사 목록 동일성 PASS, 무조건적 반환 시점 보장은 FAIL

`manifest.py:173`은 정규 `wp.report_md`에 `verify_facts.verify(..., check_only=True)`를 호출한다. 본검증 진입점은 `verify_facts.py:929`의 같은 함수다. `check_only`가 내용 검사 분기를 제거하는 부분은 없다.

| 검사 항목 | 양쪽 모드의 공통 실행 근거 | 판정 |
|---|---|---|
| 정규 report.md 경로 일치 | `verify_facts.py:864` | 동일 |
| 본문·부록 분리, 부록 마커 중복, 빈 본문 | `verify_facts.py:852`, `:872`, `:879` | 동일 |
| 본문 수치의 태그·confirmed·값·단위 결박 | `verify_facts.py:882`, 실제 검사 `:359` | 동일 |
| 부록 수치 검사, 무태그만 WARN | `verify_facts.py:886` | 동일 |
| 대장 원시행 스키마·오염·중복 ID/claim_key·미사용 | `verify_facts.py:890`, 실제 검사 `:439` | 동일 |
| 고위험 confirmed 본문 사용의 독립그룹·반박검색 및 기타 경고 | `verify_facts.py:500` | 동일 |
| 증거 필드·연결·verbatim·스냅샷 실해시·캡처 경계 | `verify_facts.py:893`, 실제 검사 `:569` | 동일 |
| 캡처 디코딩·검토 상태·이미지 해시·유효 캡처 수·재열람 결박 | `verify_facts.py:524`, `:619`, `:635` | 동일 |
| 도판 실재·출처·차트 태그·축별 경고 | `verify_facts.py:897` | 동일 |
| 승인 목차·빈 장·축 누락 | `verify_facts.py:901` | 함수는 동일. 아래 사용자 지정 plan 예외 존재 |
| CAGR 원자화·표시 정밀도 기반 계산·충돌 및 버전별 FAIL/WARN | `verify_facts.py:908`, `verify_calculations.py:88` | 동일 |
| 문장 검토 대장의 타입·문장·리비전·F/E 연결·지원 판정·누락 | `verify_facts.py:909`, `verify_claims.py:49` | 동일 |
| conversion 옵션의 decimal 누락 경고 | `verify_facts.py:913` | finalize는 기본 False. 경고만 달라지고 PASS/FAIL에는 영향 없음 |

검사 전용 모드가 생략하는 것은 `verify_calculations.py:116`의 calc-check.json 쓰기와 `verify_claims.py:122`의 claim-check.json 쓰기뿐이다. 결과 객체는 각각 그 이전 `:115`, `:119`에서 완성된다. finalize는 `verify_and_record`를 호출하지 않으므로 `verify_facts.py:937`의 manifest 재봉인과 `:938`의 G3 기록도 실행하지 않는다. WorkPaths/FactsDB 생성도 여기서는 파일을 생성하지 않는다(`skill_paths.py:70`, `facts_db.py:272`). G5 성공·실패 기록은 finalize의 의도된 별도 부작용이다.

따라서 **동일한 기본 인자와 변경 없는 입력**에 대해 검사 전용 모드의 PASS/FAIL 누락은 발견하지 못했다. 다만 아래 3항의 경쟁 조건에서는 finalize가 ok를 반환하는 순간 실제 verify는 FAIL이다.

### [P2] 사용자 지정 plan이 최종 재검증에 전달·결박되지 않음

본검증은 `verify_facts.py:924`와 CLI `:1040`에서 plan을 지원하지만, finalize `manifest.py:173`은 기본 계획만 사용한다. `check_toc`는 `verify_facts.py:800`에서 인자가 없으면 audit/research-plan.md를 선택한다. G3 refs(`gates.py:565`)와 최종 refs(`manifest.py:319`)에도 사용자 지정 계획은 없다.

실행 재현은 기본 audit 계획을 유지한 정상 작업에서 `verify_and_record(wp, plan=custom_plan)`을 통과시키고 정상 render_and_record/G4를 완료한 뒤, custom-plan.md에 원고에 없는 필수 장을 추가했다. 그 결과:

```json
{"scenario":"plan_option","final_ok":true,"actual_facts_ok":false,"manifest_now_ok":true,"status_now":"최종(판정시점)"}
```

같은 승인 계획을 지정한 verify는 “부 1. Missing chapter” 목차 이탈로 FAIL이다. 반면 기본 인자의 verify는 PASS이므로, 이것은 check_only 자체의 검사 삭제가 아니라 **실검증을 재현하는 설정 누락**이다. I1을 기본 인자의 verify로만 한정하면 반례가 아니며, 실제 G3에서 승인한 전체 검사를 재실행한다는 계약에는 반례다. 선택한 계획 경로·해시를 검증 입력으로 보존하고 finalize에서도 같은 계획을 검사하거나, 출고 경로에서 승인 계획을 정규 경로로 통일해야 한다.

## 2. I2 — 변경 없는 입력의 명시된 기계 조건은 PASS, PDF 내용 동일성 보장은 제한됨

`manifest.py:176`에서 PDF 검사를 실제 실행하고, `:187`에서 [4b] manifest 해시, `:189`에서 리비전, `:192`에서 봉인 파일의 changed/missing/new를 검사한다. 최종 ok는 이 결과와 facts.ok·pdf.ok의 논리곱이다(`:197`).

PDF는 fitz로 열어 PDF 형식·암호·페이지 존재를 검사한다(`manifest.py:285`). 원고는 렌더와 같은 GFM 입력 형식으로 pandoc JSON 파싱하며(`:205`), 참조형 링크·원시 HTML·표시 태그·캡처 수를 수집한다(`:211`, `:224`). F태그와 링크는 Counter 부족분, 캡처는 이미지 배치 총수 부족을 검사한다(`:299`). 사용자 지정 render 라벨 PDF도 대상이다(`:264`).

따라서 19바이트 가짜 PDF, 태그/링크/이미지 배치 수가 부족한 PDF가 단지 정확히 봉인됐다는 이유로 통과하는 기존 경로는 닫혔다. 관련 추가 테스트는 `tests/test_p0_regressions.py:609`, `:659`, `:729`이다.

그러나 **형식과 개수만 맞춘 비정상 PDF는 여전히 통과한다.** 직접 만든 한 페이지 PDF에 “Evidence (F001)”과 실제 증거 대신 흰색 이미지 한 장만 넣었다. 정상 원고는 원래의 제한 조건 문장과 실제 E001 캡처를 포함한다. 이 PDF를 봉인하고 기존 하위 기록 API로 [4b]/G4를 구성하면:

```json
{"scenario":"counts_only_pdf","final_ok":true,"stored_facts_ok":true,"stored_pdf_ok":true,"manifest_now_ok":true,"status_now":"최종(판정시점)"}
```

원인은 `manifest.py:291`이 **모든 이미지**를 합산하고, `:302`·`:304`는 부족한 태그/링크만 검사하기 때문이다. 원고의 실제 문장·캡처 픽셀·태그 위치·숨김 여부·초과 항목은 대조하지 않는다. 현재 테스트도 정상 원고 대신 “Evidence (F001)”만 넣은 PDF의 통과를 의도적으로 허용한다(`tests/test_p0_regressions.py:666`, `:677`).

이 재현은 **“봉인 일치 + 현재 정의된 G5 개수 검사 통과”라는 좁은 I2 자체를 깨지는 않는다.** 그 조건으로 “원고와 같은 내용을 담은 정상 PDF”까지 보장할 수 없음을 보여준다. 출고 신뢰 모델에는 이 한계를 명시해야 한다. 실제 캡처 동일성까지 요구한다면 총 이미지 수 대신 대응하는 캡처를 대조해야 한다. 동시 교체가 허용되면 아래 3항 때문에 봉인 일치의 반환 시점 보장도 성립하지 않는다.

## 3. I3 — FAIL: 검증 후 입력이 바뀌어도 성공 반환·기록 가능 [P1]

`manifest.py:325`에서 시작 전 refs를 잡지만, 그 대상은 manifest.json·claim-review.jsonl·research-plan.md **세 파일뿐**이다(`:315`). 원고·PDF·캡처·원본의 바이트를 하나의 고정 스냅샷으로 읽지 않는다. `:326`의 실검증 이후 `:327`은 그 세 refs만 재대조하며, `:332`의 기록 호출은 전체 manifest 파일 대조나 내용 검사를 다시 하지 않는다.

추가 재현 두 건은 **정상 verify_and_record → 정상 render_and_record → G4**를 마친 작업에서 수행했다. 영수증 위조 없이 입력 파일 교체만으로 재현된다.

| 교체 시점과 입력 | 실제 결과 | 영향 |
|---|---|---|
| `manifest.py:327` 직전, 실검증이 반환한 뒤 _captures/E001.png를 디코딩 불가능한 바이트로 교체 | finalize.ok=true, 반환 상태=최종. 직후 verify.ok=false, manifest.verify.ok=false | 캡처는 G3 기본 refs에도 없으므로 G5 성공 기록 시 선행조건 재검사로 잡히지 않는다. I1과 I3의 실제 반례 |
| `gates.py:134` 직전, G5 선행조건 검사가 끝난 뒤 원장 append 전에 report.md를 미검토 확장 문장으로 교체 | finalize.ok=true, 반환 상태=최종. 직후 verify.ok=false, manifest.verify.ok=false | G5는 낡은 원고 검사 결과로 성공 기록된다. refs 검사 횟수를 늘리는 것만으로 마지막 검사와 기록 사이의 틈은 사라지지 않는다 |

실행 결과 핵심:

```json
{"scenario":"capture_race","final_ok":true,"stored_facts_ok":true,"actual_facts_ok":false,"manifest_now_ok":false,"status_now":"재검토 필요"}
{"scenario":"report_race","final_ok":true,"stored_facts_ok":true,"actual_facts_ok":false,"manifest_now_ok":false,"status_now":"재검토 필요"}
```

두 번째 교체 시점에는 PDF도 이미 닫혔고 모든 검사도 끝났으므로, 그때 report.pdf를 교체해도 기존 PDF 검사 결과로 성공을 기록할 수 있는 구조다. PDF 교체 자체는 별도로 실행하지 않았으며, 이는 `gates.py:134` 이후 쓰기(`:137`) 및 `manifest.py:342` 반환 흐름에 대한 정적 판단이다.

사후 status는 봉인 대조(`manifest.py:368`)로 두 실행의 변경을 발견해 “재검토 필요”를 표시했다. 이는 유효한 사후 탐지지만, 이미 반환한 finalize.ok=true 및 CLI exit=0(`:458`)을 취소하지 않는다. 경쟁 조건이 없다는 전제라면 이 문제는 나타나지 않지만, 요청된 I3에는 그 전제가 없다.

수정 방향은 검증·봉인 대조·판정 기록·실제 전달 산출물을 동일한 불변 스냅샷에 묶는 것이다. 협조하는 쓰기 주체들에 대한 작업 단위 잠금도 가능하다. 무제한 외부 쓰기까지 가정하면 “가변 경로의 현재 내용”을 반환 이후까지 보장할 수 없으므로, 출고 결과가 가리키는 불변 리비전과 산출물 해시를 계약으로 삼아야 한다. 마지막에 일부 refs를 한 번 더 읽는 것만으로 I3를 충족했다고 볼 수 없다.

## 4. 정상 운영 경로와 성능 — 기본 경로 PASS, 성능 수치는 조건부 타당

- T10 방식의 합법 재검증은 자기 과거 실패 영수증 때문에 막히지 않는다. `verify_facts.py:934` 및 `manifest.py:179`는 자기 현재 영수증이 아닌 선행조건을 확인한다.
- G3 재봉인은 옛 report.pdf와 이전 render 산출물을 기준선에서 제외한다(`manifest.py:73`). 이후 실제 렌더 결과를 extend하고 대조한다(`render_pdf.py:94`, `:97`). 따라서 옛 PDF가 남은 상태에서 G3 → 재렌더 → G5로 복귀하는 기본 경로는 유지된다. `tests/test_p0_regressions.py:184`가 리비전 변경 뒤 두 번째 완주까지 검사한다.
- N06 류 재렌더도 새 G3 기준선을 만든 뒤 렌더하는 순서라면 같은 경로다. 이미 extend된 manifest에 G3 재검증 없이 render_and_record만 재호출하는 경우는 `render_pdf.py:92`에서 거부되며, 이번 실검증 추가가 만든 새 회귀는 아니다.
- 사용자 지정 PDF 경로는 `manifest.py:264`에서 재검사하며 긍정 테스트도 있다(`tests/test_p0_regressions.py:729`). 사용자 지정 **계획**의 누락은 1항의 별도 문제다.
- finalize의 verify_facts 실행은 한 번(`manifest.py:173`), PDF 원고 파싱도 한 번(`:268`)이다. `_diff`는 저장 파일을 해시한 뒤 신규 탐지를 경로 스캔만으로 처리한다(`:106`, `:113`). 네트워크 재열람이나 Chrome 재렌더를 finalize에서 실행하지 않으므로 합성 300건에서 1.69초라는 제공 측정은 구조상 충분히 가능하다.
- 다만 입력 크기에 관계없는 선형 비용이나 1.69초 상한은 아니다. facts/evidence를 계산·주장 검사가 다시 읽고(`verify_facts.py:854`, `verify_calculations.py:91`, `verify_claims.py:52`), 영수증 DAG 재귀는 원장·refs·confirmed를 반복 읽는다(`gates.py:273`). 문장 포함 검사도 원고 전체와 문장 리스트에 반복 수행된다(`verify_claims.py:86`). 캡처는 디코딩·축소가 필요하고(`verify_facts.py:537`), 봉인 원본 전체 바이트는 해시해야 한다. 따라서 대형 원본·고해상도 캡처·긴 원장에 대한 수 분 이내 성능을 “300건”만으로 일반화할 수 없다.

### [P1] status의 최종 상태는 여전히 하위 기록 API로 위조 가능

스펙 fixup3의 2항은 G5 성공 영수증 존재가 아니라 실제 finalize 결과와 현재 상태의 일치를 요구한다. 그런데 `manifest.py:353`은 원장에 든 final_verification을 읽고, `:355`는 ok·facts.ok·pdf.ok 세 불리언만 확인한다. `:360`의 요약 해시도 호출자가 제공한 같은 객체를 해시한 값이라 실행 출처를 증명하지 않는다.

`gates._record_script_result`의 extra는 final_verification·refs·manifest_sha256을 허용한다(`gates.py:568`). 실제 코드 해시와 실행 ID도 이 기록 함수가 정상 발급한다(`:126`). 그래서 기존 A·B와 같은 권한 범위에서 다음 조합이 가능하다.

```python
fake = {"ok": True, "facts": {"ok": True}, "pdf": {"ok": True}}
gates._record_script_result(
    wp, "G5", 0, json.dumps(fake, ensure_ascii=False, sort_keys=True),
    extra={"manifest_sha256": gates.sha256_file(wp.manifest),
           "refs": manifest._final_refs(wp), "final_verification": fake},
)
```

정상 G3 뒤 19바이트 가짜 PDF를 봉인하고 [4b]/G4를 구성한 임시 작업에서, finalize를 실행하지 않고 이 호출만 추가한 실제 결과:

```json
{"scenario":"forged_status","status":"최종(판정시점)","bindings_match":true,"g5_completed":true,"actual_pdf_ok":false,"actual_finalize_ok":false}
```

즉 **finalize 자체는 가짜 PDF를 거부한다**는 개선은 유지된다. 하지만 status와 publication_state는 실행되지 않은 finalize의 성공을 표시하고 G5를 완료 목록에 넣는다(`gates.py:597`). `tests/test_p0_regressions.py:715`의 부정 테스트는 final_verification 없이 성공 영수증만 넣어 이 변종을 놓친다.

이 문제는 I1/I2의 “finalize가 ok를 반환하면” 명제와는 별개지만, 이번 스펙의 상태 표시 요구를 충족하지 못한다. 저장된 불리언·해시를 실검증 실행의 증거로 승격하면 동일한 영수증 신뢰 문제가 반복된다. 상태 조회에서도 검증하거나, 호출자가 임의 기록할 수 없는 신뢰 경계에 실제 판정 결과를 두어야 한다. 그 경계를 두지 않는 설계라면 표시를 검증된 최종 상태가 아닌 원장의 미검증 주장으로 제한하고 계약을 명시적으로 조정해야 한다.

## 5. 이전 해소 항목의 퇴행 — 기존 ②·③·④ 유지, ①은 출고 호출 개선 / 상태 표시 미완

| 선행 항목 | 판정 및 diff 범위의 근거 |
|---|---|
| ① 기록 존재와 실제 검증 실행의 분리 | 기존 실패 원고·19바이트 PDF에 대한 finalize 우회는 실검증으로 해소(`manifest.py:173`, `:176`, `:197`). 다만 위 status 위조와 경쟁 조건은 남음 |
| ② 검증·봉인·렌더 원고 동일성 | 경로 가드는 `verify_facts.py:865`, `:1036`, `render_pdf.py:142`에 유지. finalize도 정규 report.md 사용. 정적 경로의 퇴행 없음; 시간상 동일성은 3항 별도 |
| ③ 순수 v3의 revision 없는 구형 영수증 호환 | `gates.py:253`은 버전 없는 대장과 구형 메타데이터 조건을 유지하고, `:273`의 기존 refs·선행조건·confirmed 결박 검사도 유지. `manifest.py:189`에서 같은 리비전 검사를 사용. v4 예외 확대 없음 |
| ④ 내부 운영 로그와 고객 표시 한계 구분 | `SKILL.md:22`의 중요 미확인 조건·반론 고객 표시 규칙 유지. 최종 refs가 감사 출력 전체를 봉인하지 않으므로 calc-check 등 정상 로그 갱신 때문에 자동 무효화하는 새 퇴행도 없음(`manifest.py:315`) |
| 의미 검토·캡처 검토·CAGR 내용 검사 | check_only는 결과 쓰기만 생략. 기존 실패 조건과 v3 WARN/v4 FAIL 분기는 유지(`verify_claims.py:119`, `verify_calculations.py:109`, `verify_facts.py:625`) |
| G5 호환 기록 진입점 | `gates._record_owned_result`도 `manifest.finalize_report`로 연결됨(`gates.py:503`). 이 경로가 검사 없이 별도 승인하는 퇴행은 없음 |

승인 전에는 적어도 **I3의 판정 대상 고정**과 **status의 위조 가능한 판정 신뢰**를 해결해야 한다. 사용자 지정 계획은 같은 검증 설정으로 재실행되도록 결박해야 한다. PDF의 개수 기반 검사는 현재 I2의 좁은 계약을 충족하지만, 실제 보고서·증거 내용의 동일성까지 보장한다는 표현은 피해야 한다.

ASTRA_REREVIEW2_DONE verdict=REQUEST_CHANGES

