REQUEST-CHANGES

기존 B3-01~B3-07의 **원래 재현 입력은 모두 기대 결과로 바뀌었다.** 다만 3D에서 추가한 수치 시작 경계가 쉼표 직후의 정상 수치까지 제외하여, 이전에는 실패하던 불일치 수치가 **실제 G3 성공 영수증(exit=0)** 을 받는 새 회귀 1건을 확인했다. 이 회귀는 머지 전에 수정해야 한다. 한국어 조사·띄어쓰기와 관련된 잔여 미탐 2건은 이전 버전에도 있던 공백이므로 후속 보완으로 구분했다.

검토 범위는 `feat/purpose-modules`, `9d915d8..cc0d3afa09c9975035124b7e13a7b350c1635d52`이다. 지시서에는 두 커밋이라고 적혀 있지만 실제 HEAD에는 3D(`d83c7d7`), 3E(`09c3a94`), SKILL 문서 정합(`cc0d3af`) 세 커밋이 있어 지정된 범위 전체를 검토했다. 확인 시점의 `codes/market-deep-research/SKILL.md` 미커밋 diff는 비어 있었다. 아래 파일 경로는 특별한 설명이 없으면 `codes/market-deep-research/` 기준이다.

가정과 제약: 의미 검토의 진실성은 기존 검토자 신뢰 경계를 따른다. 합성 fixture의 지원 판정을 유지한 채 숫자 검사·이미지 경계·검토 내용 결박을 시험했으며, 실제 외부 근거의 진위를 주장하지 않는다. 동시 쓰기·경로 주입·설치기 보안은 범위 밖이다. 외부 네트워크·설치·커밋 없이 실행했고 제품 코드·문서·테스트는 수정하지 않았다. 임시 입력은 OS 임시 폴더에만 만들었으며 저장소 산출물은 이 보고서 하나다. 지시서의 명시적 예외에 따라 Orca heartbeat·worker_done·check는 호출하지 않았다.

## 1. B3-01~B3-07 종결표

| ID | 원래 재현 판정 | 재검증 결과 |
|---|---|---|
| B3-01 audit 이미지 봉인 공백 | **닫힘** | 정상 v4 fixture에 `audit/chart.png`를 넣은 실제 `verify_and_record`가 `[도판경계]`로 실패한다. 부록 전용 audit 참조도 동일하게 실패했다. 부록 전용 루트 `chart.png`는 실제 G3에서 `report_image`로 봉인된다. 추가된 회귀의 이미지 교체 검출·extend 이후 교체 거부도 통과했다. |
| B3-02 근거 위치 변경 무검출 | **닫힘** | E001을 실제 `table_cell`로 만들고 `locator={page:1,row:2,col:3}`에서 정상 G3를 확인했다. 같은 E-ID·원문을 유지한 채 `{page:12,row:20,col:9}`로 바꾸면 claim 검사와 전체 G3 모두 `[근거변경]`으로 실패한다. 역할·관찰그룹·관찰시점 변경도 회귀 테스트에서 차단된다. |
| B3-03 통화 배수 뒤 잔여 문자 | **닫힘** | `4.5 USD_million_extra` + `$4.5M(F001)`, `4.5 USD_billionTypo` + `$4.5B(F001)` 모두 `[단위미지원]` FAIL이다. 지원 별칭의 양성 대조도 통과했다. |
| B3-04 한국어 단위 수치 누락 | **원 재현 닫힘, 후속 범위 있음** | 대장 `45 mW`, `출력은 999 밀리와트(F001)이다.`는 수치 함수와 실제 G3 모두 `[수치미인식]` FAIL이다. 메가와트 등 목록 단위도 차단된다. 조사와 띄어쓴 원화에는 잔여 미탐이 있다(RR3-02·03). |
| B3-05 표 행 B2B 오탐 | **닫힘** | 대장 `45 USD`, `\| 매출 \| $45 B2B \| (F001) \|`는 실패·경고 0건이다. M2M/T1 및 표 셀 폴백 회귀도 통과했다. 같은 배치의 수치 시작 경계에서 별도의 새 회귀 RR3-01이 발생했다. |
| B3-06 정성 식별자 오탐 | **닫힘** | 수치 fact를 인용한 `5G 시장 전망이다(F001).`, `2024 OECD 전망이다(F001).` 모두 실패·경고 0건이다. 4K·3D·한국어 연월일·분기·법조문 대조도 통과한다. |
| B3-07 문서 불일치 | **닫힘** | 이미지 허용/봉인 경계, 본문·부록 어디에도 인용하지 않은 high-risk만 WARN, 작업폴더 v4 여부에 따른 claim 검사 강도, 실제 조건 문구 인용, 두 운영 필드를 제외한 digest 범위가 반영됐다. 현재 SKILL.md의 부록 인용·내용 해시·v3 출고 플래그 설명도 해당 코드와 일치한다. |

‘닫힘’은 원래 입력과 정해진 계약을 확인했다는 뜻이며 모든 자연어 수치 표현을 지원한다는 뜻은 아니다. G3 내용검사·G3 영수증 발급·manifest 해시 검증을 구분했고, 이 환경에서 실제 PDF 렌더 후 G5 성공까지 확인했다고 주장하지 않는다.

## 2. 새 발견과 잔여 보완

| ID | 심각도 | 파일:줄 | 입력 상태 → 관찰 결과 | 최소 수정 방향 | 머지 전 필수 여부 |
|---|---|---|---|---|---|
| **RR3-01** | **P1 — 새 검증 회귀** | `scripts/verify_facts.py:87` (`:96`, `:99`도 같은 시작 경계) | 대장 `45 mW`, 본문 `출력은 45mW,999mW(F001)이다.` → 이전 `9d915d8`은 `999mW`에 `[값불일치]` FAIL, 현재는 **수치 실패·경고 0건**. 캡처·전체 문장 검토를 갖춘 fixture에서 **G3 ok=true, 영수증 exit=0**까지 확인했다. 쉼표 뒤 공백을 넣으면 현재도 정상 FAIL이다. | 식별자 내부·숫자 토큰 중간의 재시작은 막되, 단위를 마친 열거 항목 뒤의 쉼표를 새 수치 시작 금지 문자로 취급하지 않는다. `45mW,999mW`와 공백 있는 대조, `X45mW`, 소수·천단위 표기를 함께 회귀로 고정한다. | **예.** 기존에 막던 대장 불일치 수치가 새로 통과한다. |
| RR3-02 | P2 — 한국어 단위의 잔여 미탐 | `scripts/verify_facts.py:108`, `:493` | 대장 `45 mW`, `출력은 999 밀리와트보다 크다(F001).` → 알려진 단위인데 `[수치미인식?]` **WARN만**, 실제 G3 PASS. `999 킬로그램부터`, `999 리터보다`도 같은 분류다. `밀리와트(F001)` 대조는 FAIL한다. | 단위명 뒤의 `보다`·`부터`·`까지` 등 일반 조사도 명시적으로 분리해 알려진 단위 후보로 처리한다. 단위명으로 시작하는 일반 단어를 무조건 수량으로 바꾸지 않는 음성 대조를 유지한다. | **아니오, 후속 권고.** 이전 버전에서도 미탐이었고 이번에는 WARN이 추가됐다. B3-04의 정확한 재현은 해결됐으나 한국어 단위 차단 범위를 넓힐 때 보완해야 한다. |
| RR3-03 | P2 — 띄어쓴 원화의 잔여 미탐 | `scripts/verify_facts.py:99`, `:494` (기존 `_TIGHT_KRW_UNITS` 판정과 상호작용) | 대장 `45 KRW`, `가격은 999 원(F001)이다.` → `[수치미인식?]` WARN만, 실제 G3 PASS. 대장 `45 KRW_T`, `규모는 300조 원(F001)이다.`도 WARN만 남기고 G3 PASS한다. `999원`·`1.2조원`처럼 붙인 표기는 수치 대조한다. | `원` 바로 앞 한 글자 대신 허용 공백과 숫자/배수의 문맥을 확인하고, `300조 원`의 배수+통화까지 후보로 묶는다. `2024 원문`은 단위 후보가 되지 않도록 유지한다. 전체 값을 해석하지 않더라도 확실한 통화 후보는 FAIL로 분류할 수 있다. | **아니오, 후속 권고.** 기존 버전에서도 같은 입력은 통과했다. 3D 보고서는 ‘바로 앞 문자’ 제한을 명시적으로 채택했으므로 새 회귀로 집계하지 않았다. |

RR3-01의 원인은 새 음성 후방탐색 `(?<![A-Za-z0-9.,+−-])`이다. 두 번째 수치의 첫 글자 앞에 쉼표가 있어 후보가 시작되지 않고, 나머지 자리에서도 앞 숫자 때문에 재시작하지 못한다. 결과적으로 파서에는 `45mW`만 남아 F001과 일치한다. 이 결론은 코드 추정만이 아니라 **같은 입력의 이전/현재 함수 결과 및 현재 실제 G3 발급**으로 확인했다.

RR3-02·03의 WARN을 성공적인 수치 검증으로 해석하면 안 된다. 다만 둘은 기존 미탐을 악화시킨 변경이 아니므로 이번 머지를 막는 새 회귀와 구분했다. 이번 `REQUEST-CHANGES`를 결정하는 필수 수정은 RR3-01이다.

## 3. 요청된 한국어 혼합 표기·정성 인용 점검

모두 `(F001)`을 붙인 수치 fact 인용으로 실행했다. 일치 대조와 불일치 대조는 별도로 입력했다.

| 본문 표기 | 일치 대장 예 | 일치/불일치 결과와 해석 |
|---|---|---|
| `3개사` | `3 개사` | 일치 시 실패·경고 없음, 대장 4이면 `[값불일치]`. |
| `45개국` | `45 개국` | 대장 45와 999 모두 `[수치미인식?]` WARN. 목록 밖 한글은 WARN이라는 3D 계약에 따른 결과이며 값 비교는 수행하지 않는다. |
| `12억 달러` | `12 USD_억` | 일치 시 깨끗한 PASS, 대장 45이면 FAIL. 이전 버전의 `USD_억` 배수 해석 불일치도 이번 단위 별칭 확대로 해소됐다. |
| `300조 원` | `300 KRW_T` | 일치/불일치 모두 `300조` 후보에 WARN만. RR3-03. |
| `1.2조원` | `1.2 KRW_T` | 일치 시 깨끗한 PASS, 대장 45이면 FAIL. |
| `5천만 달러` | `50 USD_M` | 값 비교는 정상이며 대장 45이면 FAIL. 일치해도 `천만 달러`에 기존 `[한글수사]` WARN이 남는다. 이전 버전에도 같은 경고가 있어 이번 회귀는 아니다. |

정성 인용의 `5G`·`4K`·`3D`·`2024 OECD`, `2024년 9월 19일`, `제3장`, `제12쪽`은 실패·경고 없이 통과했다. `2024 원문을 참고했다(F001).`, `2024 보고서에 따른 전망이다(F001).`, `표 3에서 확인한 전망이다(F001).`는 새 `[수치미인식?]` WARN을 낸다. 이는 ‘목록 밖 숫자+한글은 경고’ 정책의 잡음이며 새 FAIL 오탐으로 집계하지 않았다. 필요하면 문서 참조 문맥을 좁게 추가 제외할 수 있다.

## 4. digest 확대와 정상 처리 순서

**정상 파이프라인이 검토 후 기존 evidence 행을 자동 갱신하여 불필요하게 재검토를 강제하는 경로는 확인하지 못했다.**

- `scripts/facts_db.py:418`의 `add_evidence`는 새 E-ID를 추가하고 연결 fact의 `evidence_ids`를 갱신한다. 기존 E-ID의 upsert가 아니며 중복 ID는 거부한다. 기본값으로 추가하는 `accessed_at`은 digest 제외 대상이다.
- `add_verify_event`·`set_status`는 facts를 쓰며 기존 evidence 행을 쓰지 않는다. G3와 claim/calculation 검사도 결과를 audit에 기록하고 evidence를 자동 수정하지 않는다.
- G2 캡처 및 `capture_review` 작성은 문장 작성·claim-review보다 앞선다. 캡처 검토 정보는 **이전 digest에도 이미 포함**되어 있었다. 검토 후 캡처를 교체하거나 재판정한 경우의 재검토 요구를 이번 범위 확대의 새 오탐으로 볼 근거가 없다.
- 정상 fixture에서 `start_chain → verify_and_record → verify → claims.verify`를 실행한 뒤 evidence 원문 바이트가 그대로임을 확인했다. 이후 E002 추가에도 E001의 digest와 기존 claim 검토는 유지되고 G3가 통과했다.
- `locator`, `valid_at`, 확장 키, `schema_version`, `capture_review.reviewed_at` 변경은 digest가 바뀌고 `[근거변경]`을 낸다. `source_role`·`observer_group`·`observed_at`은 추가된 회귀에서 같은 동작을 확인했다. `accessed_at`·`note` 변경은 digest와 검토가 유지됐다.

행 전체 투영 때문에 누락 키를 새로 추가하거나 값의 구조를 바꾸면 재검토가 필요해지는 것은 3E의 명시적 계약이다. 이를 자동 정규화가 실제로 일으키는 경로는 이번 직접 호출 범위에서 찾지 못했다. 이 판단은 모든 향후 외부 작성 도구가 운영 메타데이터를 같은 방식으로 다룬다는 보장은 아니다.

## 5. 도판 및 문서 정합

이전 모듈을 `git show 9d915d8:.../verify_facts.py`에서 메모리로 불러와 현재 `check_figures(report_text=...)`와 열 가지 사례를 대조했고, 기존 본문 판정은 모두 같았다.

- 본문 이미지 없음·부록에만 이미지 있음은 둘 다 본문 대표 이미지 0장 FAIL이다.
- `_captures/`만 본문에 있는 경우는 이전과 동일하게 대표 이미지로 세며 캡션·F태그를 요구하지 않는다. `_captures/` 제외는 캡션·F태그 검사 면제이지 이미지 개수에서 제거한다는 뜻이 아니다.
- 캡션 없음·빈 `출처:`·세 줄 뒤 캡션은 FAIL이고 두 줄 이내 유효 캡션은 PASS다.
- 본문 `assets/` 차트는 F태그가 없으면 FAIL, 있으면 PASS다. 부록 캡션·F태그 면제는 그대로이며 부록 파일 실재 검사는 새로 적용된다.

본문/부록 audit 참조 차단, 부록 루트 이미지의 실제 G3 봉인, 부록 파일 누락 FAIL은 독립 probe에서도 확인했다. 이미지 교체 및 extend 이후 교체 검출은 추가된 실제 G3 경로 테스트가 통과했다. 해당 extend 테스트의 PDF는 합성 바이트이므로 렌더/PDF 내용 검사 성공을 뜻하지 않는다.

`verification-gates.md`와 `claim-review.md`의 이번 수정 및 현재 SKILL.md는 지정 계약과 일치한다. 게이트 문서 앞부분의 `본문 사용` 표현(`:37`, `:47`)은 뒤의 본문·부록 적용 설명과 맞춰 더 명료하게 쓸 수 있으나, 기존의 ‘본문 미사용이면 전부 WARN’이라는 잘못된 일반화는 제거됐다. 새 문서 결함으로 별도 집계하지 않았다.

## 6. 실행 명령과 마지막 출력

테스트는 `codes/market-deep-research`에서 실행했다. 공통 환경 및 임시폴더 생성은 다음과 같다. 아래 `$reviewTemp`는 각 실행마다 실제 GUID로 생성한 OS 임시 경로다.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$reviewTemp = Join-Path ([System.IO.Path]::GetTempPath()) ('mdr-batch3-rereview-' + [guid]::NewGuid().ToString('N'))
python -m pytest -q -p no:cacheprovider --tb=line --basetemp $reviewTemp
```

마지막 출력: **`39 failed, 557 passed in 24.80s`**, pytest exit 1.

```powershell
$reviewTemp = Join-Path ([System.IO.Path]::GetTempPath()) ('mdr-batch3-focused-' + [guid]::NewGuid().ToString('N'))
python -m pytest -q -p no:cacheprovider --tb=short --basetemp $reviewTemp tests/test_batch3a_regressions.py tests/test_batch3b_regressions.py tests/test_batch3c_regressions.py
python -c "import shutil; print('pandoc=' + str(shutil.which('pandoc')))"
```

pytest 마지막 출력: **`1 failed, 164 passed in 3.24s`**. 후속 환경 조회 마지막 출력: **`pandoc=None`**. pytest는 실패했으며 후속 환경 조회가 성공하여 이 PowerShell 호출 전체의 종료값은 0이었다. 이를 pytest 성공으로 해석하지 않았다.

분리 실행의 유일한 실패는 `test_r04_legacy_finalize_requires_explicit_flag_and_records_mode`다. `tests/test_batch3a_regressions.py:188 → render_pdf.py:191 → :168 → :76`의 `subprocess.run(["pandoc", ...])`에서 `FileNotFoundError: [WinError 2]`로 중단됐다. 전체 39건도 출력상 같은 실행 파일 부재 또는 그에 따른 렌더/PDF 예상 결과 실패였다. 따라서 제품 결함 39건으로 집계하지 않았으며, 지시서의 팀리드 환경 `596 passed`도 이번 환경의 전건 통과로 대신하지 않았다.

나머지 명령은 저장소 루트에서 실행했다.

| 명령/읽기 전용 probe | 마지막 출력 또는 결과 |
|---|---|
| `git diff 9d915d8..HEAD --stat` | `8 files changed, 315 insertions(+), 74 deletions(-)` |
| `git log 9d915d8..HEAD --oneline` | `d83c7d7 fix(mdr): 배치 3D — 단위 전체 문법 검증·한국어 단위 미인식 차단·식별자 오탐 제거 (B3-03~06)` |
| `git rev-parse HEAD` | `cc0d3afa09c9975035124b7e13a7b350c1635d52` |
| `git diff -- codes/market-deep-research/SKILL.md` | 출력 없음, exit 0 |
| `git diff 9d915d8..HEAD --check` | 출력 없음, exit 0 |
| PowerShell here-string → `python -`: 이전/현재 파서 원재현·한국어 문장 매트릭스 | `PARSER_MATRIX_COMPLETE`, exit 0 |
| 같은 방식: 쉼표 경계 및 실제 G3, 본문/부록 이미지, table_cell digest·정상 evidence 보존 | `IMAGES_AND_DIGEST_PROBES_COMPLETE`, exit 0. 중간 묶음 종료는 `BOUNDARY_AND_G3_PROBES_COMPLETE` |
| 같은 방식: 이전/현재 본문 도판 열 사례·원래 locator 변경의 전체 G3 | `FIGURE_RULES_AND_LOCATOR_COMPLETE`, exit 0 |
| 같은 방식: 지정 혼합 표기의 일치/불일치 및 쉼표 사례 실제 영수증 | `MIXED_NOTATION_AND_RECEIPT_COMPLETE`, exit 0. 직전 줄 `comma_actual_G3_receipt_exit=0` |
| `git status --short --untracked-files=no`, `git diff --numstat` | 기존 `.gitignore` 수정만 있으며 numstat는 `3 0 .gitignore`. 본 리뷰에서 해당 파일은 쓰지 않았다. |

읽기는 지시서·이전 리뷰·두 배치 스펙/보고의 UTF-8 전체 조회, 지정 8개 파일별 diff, 관련 함수·호출 경로의 `Get-Content`/`rg`로 수행했다. 최초 기본 인코딩 조회가 깨져 UTF-8로 다시 읽었으며, 판정은 정상 재조회 내용을 사용했다. probe의 한글은 Unicode escape로 전달했다. 초기 보조 스크립트의 영수증 `ok` 키 접근 오류와 존재하지 않는 `WorkPaths.assets` 속성 오류는 바로잡아 재실행했고, 오류로 중단된 실행을 성공 검증으로 집계하지 않았다.

미확인 사항은 정상 PDF 렌더부터 G5까지의 종단 성공 및 legacy-v3 성공 출고 기록이다. `pandoc`가 있는 환경에서 확인해야 하며, 이번 리뷰의 확정 결함 RR3-01은 렌더와 무관하게 기존 수치 함수 및 실제 G3 발급에서 재현된다.
