REQUEST-CHANGES

검토 기준은 `feat/purpose-modules`, `a07a3c7..9d915d84d8cafe021d1f89a251d9027abab0d9f0`의 14개 파일이다. 세 배치의 스펙·작업 보고와 기존 R01~R09를 대조하고, 신규 회귀 83개 및 코어 전체 514개를 실행했다. 기존 재현의 대부분은 차단됐지만 **P1 검증 공백 4건, P2 오탐 2건, P3 문서 불일치 1건**이 남았다. 특히 `audit/` 참조 이미지가 G3를 통과하면서 봉인에서 빠지는 현상은 실제 G3 발급까지 재현했다.

가정과 범위: 검토자의 의미 판정·육안 캡처 판정은 기존 신뢰 경계를 따른다. 메타데이터 변경 뒤 검토의 현행성이 유지되는지를 검사했으며, 검토자 신고의 진실성 자동 판정을 요구하지 않았다. 로컬 검증 함수와 기존 합성 fixture만 사용했고, 임시 입력은 OS 임시 폴더에 생성했다. 외부 네트워크·패키지 설치·커밋·제품 코드 및 테스트 수정은 하지 않았다. 지정 리뷰 지시서의 명시적 예외에 따라 Orca heartbeat·worker_done도 시도하지 않았다.

아래 `scripts/`, `tests/`, `references/`는 `codes/market-deep-research/` 기준이다. **G3 내용검사, 실제 G3 영수증 발급, manifest 해시 검사, 최종 G5 출고를 구분한다.** 현재 환경의 `pandoc` 부재 때문에 정상 렌더부터 최종 G5까지의 종단 성공은 확인하지 못했다.

## 1. R01~R09 종결표

| ID | 판정 | 확인 근거 |
|---|---|---|
| R01 근거 내용 교체 | **부분** | 기존과 똑같이 E001의 `verbatim`과 `sha256`을 함께 바꾸면 사실 revision은 같아도 G3가 `[근거변경]`으로 실패한다. 지정 필드·새 E-ID 허용 계약은 구현됐다. 다만 `table_cell.locator` 변경은 기존 검토를 무효화하지 않는다(B3-02). |
| R02 이미지 봉인 | **부분** | 루트 `chart.png`는 실제 G3 발급 시 `report_image`로 봉인되고 교체 시 `changed=['chart.png']`가 된다. 동일 흐름의 `audit/chart.png`는 G3 PASS 후에도 봉인·최종 스냅샷에서 빠진다(B3-01). |
| R03 빈 조건 가정 | **닫힘** | 원래의 확정형 문장을 그대로 두고 `hypothesis/partial`, 빈 조건으로 검토하면 `[조건미명시]` FAIL이다. 두 유형×세 지원 상태의 빈 조건·본문 누락·공백 정규화 양성 대조가 통과했다. |
| R04 버전 강등 | **부분 — 종단 실행 미확인** | `schema_verison`으로 바꾸고 캡처·문장 검토를 제거한 원래 입력은 FAIL이며, 인용 fact/evidence 혼합 버전 6개 사례도 FAIL이다. 순수 v3 기본 거부·명시 플래그·영수증 및 status 표시는 코드에 구현됐으나, 해당 회귀는 렌더의 `pandoc` 호출에서 중단되어 성공 출고·기록까지 실증하지 못했다. |
| R05 부록 인용 | **닫힘** | 부록의 `45 USD(F001)`에 high-risk 요건·캡처·문장 검토가 없는 원래 입력에서 `[반박게이트]`, `[증빙]`, `[주장검토] 검토 누락`이 모두 FAIL이다. 부록 문장·목록 검토와 일반 대장 표 행 면제의 회귀도 통과했다. |
| R06 통화 배수 | **부분** | `4.5 USD_B` 대장에 `$4.5B`는 PASS, `$4.5`는 `[값불일치]` FAIL이다. `_MN/_BN` 등도 통과한다. 그러나 `USD_million_extra`처럼 배수 단어 뒤 미해석 접미사가 있는 단위는 무경고 통과한다(B3-03). |
| R07 미인식 수치 | **부분** | `999 mw`는 `[수치미인식]`, `C$999`는 `[단위불일치]`로 막고 mW/MW 구분은 유지한다. 한국어 단위의 명백한 수치 주장은 여전히 무경고 G3 PASS이며(B3-04), 식별자에는 새 오탐이 생겼다(B3-05·06). |
| R08 B2B 접미사 | **부분** | 원래 일반 문장과 M2M/T1 대조는 PASS다. 그러나 동일 값의 정상 표 행은 `B2B` 내부 `2B`를 미인식 수치로 잡아 FAIL한다(B3-05). |
| R09 괄호 내부 분할 | **닫힘** | 원래 `(주1. 연결 기준)` 문장은 PASS다. 괄호·대괄호·마크다운 링크를 각각 본문 및 v4 부록에 둔 6개 추가 입력도 문장 전체 검토로 G3 PASS였으며, 미닫힘 괄호 폴백 회귀도 통과했다. |

‘부분’ 중 R04는 확인된 구현 결함을 뜻하지 않는다. 환경 때문에 남은 출고 검증이다. 나머지 부분 항목은 원래 재현은 고쳤으나 같은 계약의 공백 또는 오탐이 관찰된 경우다.

## 2. 확인된 발견

| ID | 심각도 | 파일:줄 | 입력 상태 → 관찰 결과 | 최소 수정 방향 |
|---|---|---|---|---|
| B3-01 | **P1 검증 공백** | `scripts/manifest.py:80`, `scripts/verify_facts.py:990`, `scripts/manifest.py:344` | 정상 v4 fixture에 유효한 로컬 PNG `audit/chart.png`와 출처 캡션을 넣고 실제 `verify_and_record`를 실행 → **G3 ok=true**, manifest에는 이미지 없음. 이후 이미지 바이트만 교체 → **manifest.verify ok=true**, 전후 `_final_snapshot` 동일. 루트 `chart.png` 대조군은 G3 봉인 후 같은 교체를 검출했다. | 현재의 `audit/**` 봉인 금지 정책을 유지한다면 G3에서 **원고 전체의 audit 이미지 참조를 명시적으로 FAIL**하고 `assets/` 등으로 옮기게 한다. 본문만 검사하면 부록 이미지가 남으므로 전체 원고의 공용 참조 파서를 사용한다. 대안은 실제 참조 이미지에 한해서만 봉인하는 정책 변경이나, 이는 현 스펙의 audit 제외와 함께 재합의해야 한다. |
| B3-02 | **P1 검증 공백** | `scripts/facts_db.py:489`, `scripts/verify_claims.py:115` | E001을 유효한 `table_cell`로 두고 `locator={page:1,row:2,col:3}`, 검토 완료 상태에서 정상 G3 PASS를 확인했다. 같은 원문·E-ID를 유지한 채 locator만 `{page:12,row:20,col:9}`로 변경 → **내용 digest 동일, 기존 claim-review PASS, G3 PASS**. 검토한 표의 셀 위치가 달라져도 재검토를 요구하지 않는다. | 최소한 `locator`를 내용 digest에 넣는다. `source_role`, `observer_group`, `observed_at`도 검토의 근거 맥락으로 쓰는 필드이므로 결박 대상으로 명시할지 정한다. 모든 운영 로그 필드를 무조건 해시할 필요는 없다. **현재 구현은 3A의 명시 필드 목록을 준수하므로 스펙 자체의 보완 사항**이다. |
| B3-03 | **P1 검증 공백** | `scripts/verify_facts.py:314`, `scripts/verify_facts.py:325` | 대장 `raw=4.5, unit=USD_million_extra`에 `$4.5M(F001)` → 수치검사 **failures=[], warnings=[]**. `USD_billionTypo`와 `$4.5B`도 동일하다. `_SCALE_TOKEN.search`가 배수 단어를 찾자마자 반환하여 뒤의 미지원 접미사 검사를 건너뛴다. `USD_FOO` 대조군은 정상적으로 FAIL한다. | 통화코드가 있는 단위는 허용된 전체 문법을 먼저 검증하고, 배수 뒤의 나머지도 소비됐는지 확인한다. 자유서식 배수 검색보다 미해석 접미사 판정을 우선한다. `_million_extra`, `_billionTypo` 부정 회귀를 추가한다. |
| B3-04 | **P1 검증 공백** | `scripts/verify_facts.py:94`, `scripts/verify_facts.py:468`, `scripts/verify_facts.py:556` | 대장 `45 mW`, 본문 `출력은 999 밀리와트(F001)이다.` → 수치검사 **실패·경고 0건**, 정상 캡처·검토 fixture를 갖춘 전체 **G3도 ok=true**. `_LOOSE_CLAIM`은 통화기호 또는 숫자 뒤 영문만 수집하여 한국어 단위가 붙은 숫자는 검사 대상에서 사라진다. | 미인식 후보 수집에 한국어 단위 표기·태그에 인접한 수치 주장을 포함한다. 연도·조항·순번 등 비수량 문맥은 별도로 제외해야 한다. 단위를 지원하지 않더라도 이 입력은 최소 `[수치미인식]`으로 차단한다. |
| B3-05 | **P2 오탐** | `scripts/verify_facts.py:95`, `scripts/verify_facts.py:511`, `scripts/verify_facts.py:558` | 대장 `45 USD`, 정상 표 행 `\| 매출 \| $45 B2B \| (F001) \|` → `$45`는 기존 표 셀 간 값 일치 폴백을 만족한다. 그런데 폴백으로 인정한 태그는 `bound`에 없고, `B2B` 속 `2B`가 leftover가 되어 **`[수치미인식]` FAIL**, 전체 G3도 FAIL이다. 일반 문장의 `$45 B2B`는 PASS다. | 식별자 내부에서 숫자 토큰을 시작하지 않도록 경계를 둔다. 또한 표 셀 폴백에서 유효하게 대조한 태그를 후속 미인식 판정에 반영한다. 표 행의 B2B/M2M/T1 양성 대조를 추가한다. |
| B3-06 | **P2 오탐** | `scripts/verify_facts.py:94`, `scripts/verify_facts.py:569` | 수치가 있는 전망 fact를 정성적으로 인용한 `5G 시장 전망이다(F001).` → **`5G`를 미인식 수치로 판정하여 전체 G3 FAIL**. `2024 OECD 전망이다(F001).`도 `2024 OECD`를 하나의 미지원 수치로 잡는다. 대조군 `2024년 기준`, `3분기`, `제25조`, `2030년 목표`는 실패·경고 0건이다. | ‘숫자+영문’ 전체를 수량으로 단정하지 않고 기술 식별자·연도+기관명을 구별한다. 지원되지 않는 단위 후보와 문서 식별자를 분리하고, 불명확한 비수량 문맥에는 적절한 진단을 준다. |
| B3-07 | **P3 문서** | `references/verification-gates.md:40`, `references/verification-gates.md:96`, `references/verification-gates.md:180`, `references/claim-review.md:54` | 문서는 ‘위치와 무관하게 모든 로컬 이미지 봉인’이라고 하지만 B3-01 입력은 제외된다. 같은 게이트 문서 앞부분은 ‘본문 미사용 high-risk는 모두 WARN’이라 하고 뒤에서는 ‘부록 인용도 동일 요건’이라고 한다. 실제 부록-only high-risk 입력은 FAIL이었다. claim-review 문서의 ‘schema_version 생략은 v3·WARN’도 행 버전과 작업폴더 엄격 모드의 구분이 빠져 있다. | 이미지 허용 위치/봉인 정책과 본문·부록 사용 집합을 기존 절에도 반영한다. claim-review의 FAIL/WARN은 **작업폴더의 v4 여부**가 결정하며 검토 행의 버전 생략이 면제가 아님을 명시한다. `verification-gates.md:172`의 ‘계산·캡처의 본문·부록이…’ 문장도 다듬는다. |

B3-01은 해시 검증 누락을 실제로 관찰한 것이며 최종 G5 성공을 주장하지 않는다. B3-02는 증거의 진위 자동 판독 요구가 아니라 **이미 검토한 근거 위치가 변경됐다는 사실의 검출 누락**이다. B3-03·04는 원래의 정확한 예시가 실패하는지와 별도로, 이번 배치가 선언한 미해석 입력 차단 계약을 검사한 결과다.

## 3. 사전 의심점 판정

| 의심점 | 판정과 이유 |
|---|---|
| `audit/` 이미지 제외 | **고쳐야 함.** B3-01로 재현됐다. audit 전체를 봉인하지 않는 이유는 타당하지만, 제외된 파일을 렌더 입력으로 허용하면 결박 공백이 남는다. 현 스펙 아래 최소 수정은 원고 전체의 해당 참조를 G3에서 거부하고 안정된 이미지 폴더로 이동시키는 것이다. |
| `report.md` 읽기 실패 시 이미지 봉인 생략 | **최종 출고 우회 문제는 아님.** 잘못된 UTF-8 원고에서 `manifest.build`와 해시 전용 `manifest.verify`는 성공하는 것을 확인했다. 하지만 정규 G3는 `verify_facts.py:1141`에서 원고를 먼저 읽고, 최종 검사는 `manifest.py:195`에서 같은 검증을 실행해 읽기 실패를 `[원고검사]` FAIL로 바꾼다. 동시 쓰기를 허용하지 않는 현재 계약에서는 이 예외 처리만으로 출고 PASS가 되지 않는다. 수동 build의 성공 오해를 줄이려면 읽기 오류를 전파하거나 명시적 진단을 남기는 보완은 유용하다. |
| 버전 오타 정규식의 범위 | **현재 출고 차단 계약에는 문제 아님, 지원 범위 문서화 필요.** 실측상 `schemaVersion`은 이미 거부하고 `shema_version`·`version`은 v3로 읽는다. `schema_verification_note` 같은 키도 prefix 때문에 거부된다. 이는 임의 확장 키에는 오탐 소지가 있지만 현재 공식 스키마의 정상 필드가 차단되는 사례는 없었다. `schema…ver` 계열을 예약하고 알려진 `shema_version`만 추가 거부하는 정도는 합리적이다. 의미가 넓은 `version` 전면 금지나 모든 오타의 유사도 판정은 권하지 않는다. 놓친 오타도 순수 v3 기본 출고 거부·혼합 인용 금지로 최종 게이트에서 보호된다. |
| required_qualification 부분 문자열 | **현재 최소 계약에는 문제 아님.** 본문 `무전원 적용 여부는 미확인이다`에 검토 문구 `무전원 적용 여부가 미확인이다`를 쓰면 `[조건본문누락]`, 본문에서 실제 문구를 복사하면 PASS였다. 이 필드를 요약이 아닌 **본문의 조건 인용문**으로 정의하면 조사·어미 차이 없이 작성할 수 있다. 공백 정규화+실제 인용은 조건 명시 결박의 단순하고 결정적인 최소 기준이다. 필요하면 설명용 필드를 따로 두거나 인용 span을 쓰되, 형태소 제거·유사도만으로 자동 허용하면 부정·조건의 차이를 놓칠 수 있다. |
| evidence_content_digest 필드 선택·새 E-ID | **필드 선택은 고쳐야 함, 새 E-ID 허용은 의도대로.** `locator` 변경의 검토 재사용이 B3-02로 재현됐다. 역할·관찰그룹·관찰시점도 변경 후 digest가 같다는 것을 확인했다. 한편 검토 행이 참조하지 않는 E002를 추가하는 기존 테스트는 실제 G3 PASS였고, 이는 스펙의 명시적 범위다. 검토 대상 E-ID 집합 변경이나 기존 내용 교체와 구별해야 한다. |
| 한국어 문서의 비수량 숫자 오탐 | **일부 고쳐야 함.** 지정된 한국어 연도·순번 문맥 중 `2024년`, `3분기`, `제25조`, `2030년 목표`에는 오탐이 없었다. 다만 기술 식별자 `5G`, `2024 OECD` 및 표의 B2B에는 B3-05·06 오탐이 있다. 반대로 한국어 단위의 실제 수량은 B3-04처럼 누락되므로, 영문 여부만으로 범위를 정하는 현재 기준은 양쪽 모두 보완해야 한다. |

## 4. 배치 간 상호작용과 테스트 품질

3C의 분할기와 3A의 본문·부록 검토를 함께 실행했다. `45 USD(주1. 연결 기준)(F001)`, 대괄호 주석, `[주1. 설명](https://example.test/x)` 링크의 세 형태를 본문/부록에 각각 넣고 **원문 전체를 sentence_text로 기록**했을 때 6개 모두 G3 PASS였다. 같은 `split_segments(..., preserve_text=True)`를 공유하므로 이번 괄호 보호 변경에서 분할 단위의 불일치는 확인되지 않았다. 분할 결과를 그대로 복사한 단언만으로 판단하지 않고 예상 원문 전체를 검토 행에 직접 넣었다.

3B의 루트 `report_image`는 3A의 `_final_snapshot`에 포함된다. `manifest.build(for_g3=True)` 뒤 임시 렌더 산출물을 `extend`한 정상 흐름은 해시 검사 PASS였고, 이후 참조 이미지를 바꾸면 다음 extend가 ‘기존 봉인 항목 변조/소실’로 거부했다. 이 검사는 PDF 내용 검사가 아니라 **extend와 이미지 해시 결박의 상호작용**이다. 실제 PDF 렌더·finalize는 환경 제약 때문에 별도 미확인이다.

| 테스트 묶음 | 평가와 빠진 사례 |
|---|---|
| `tests/test_batch3a_regressions.py` | 내용 변경 후 claim 검사와 G3를 함께 확인하고, 조건의 18개 조합·버전 혼합·부록 검토를 실행하므로 유효한 동작 회귀다. `:54`의 canonical digest 테스트는 구현과 같은 필드 목록을 재작성하므로 정규화 확인에는 유용하지만 **필드 선택의 충분성**은 검증하지 않는다. `locator` 등 맥락 필드 변경이 빠졌다. `:156`의 실제 렌더부터 시작하는 legacy 출고 회귀는 좋은 종단 테스트지만 이번 환경에서는 이후 단언에 도달하지 못했다. |
| `tests/test_batch3b_regressions.py` | 실제 파일 바이트를 바꿔 `changed`와 snapshot을 확인하는 점은 유효하다. 다만 `:35`, `:46`은 실제 G3 발급이 아니라 `manifest.build(for_g3=True)` 직접 호출이고 PNG도 헤더 형태의 합성 바이트다. **G3가 허용한 이미지가 모두 봉인되는가**라는 교집합을 검사하지 못해 audit 참조를 놓쳤다. 실제 G3 발급 및 부록 참조, extend 후 변경의 회귀가 필요하다. |
| `tests/test_batch3c_regressions.py` | 기대 PASS/FAIL을 원래 예시로 고정하며 구현의 내부값을 복사하지 않아 기본 회귀는 유효하다. 다만 한국어 단위, 비수량 식별자, 표 셀 폴백+B2B, 배수 단어 뒤 잔여 접미사, 본문/부록 claim-review 연동이 빠졌다. |
| 기존 테스트 수정 | `test_p0_regressions.py`의 조건 문구·digest fixture, `test_batch2b_fixup.py`의 E002 digest, 기존 출고 호출의 legacy 플래그 추가를 직접 diff로 확인했다. 기존 안전성 단언을 삭제하거나 약화한 변경은 없었다. 조건 문구 fixture 갱신은 새 명시 계약에 맞춘 것이며, 별도 의역 허용 테스트가 있다는 뜻은 아니다. |

## 5. 실행 결과와 미확인 사항

환경은 Windows/Python 3.13이다. 테스트에는 `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `-p no:cacheprovider`를 적용했다. 아래 명령은 `codes/market-deep-research`에서 실행했다. 공용 `pytest-of-eicic` 디렉터리의 접근 오류 때문에 최초 기본 임시폴더 실행은 setup 단계에서 다수 오류가 났고, 이후 OS 임시 폴더에 독립 `--basetemp`를 만들어 다시 실행했다. 재실행 결과를 제품 판정의 근거로 삼았다.

전체 코어:

```text
python -m pytest -q -p no:cacheprovider --tb=line --basetemp C:\Users\eicic.AIDEN-DESKTOP\AppData\Local\Temp\mdr-batch3-review-6wav4exg\pytest
39 failed, 475 passed in 24.31s
```

세 배치만 분리하여 실패 위치 확인:

```text
python -m pytest -q -p no:cacheprovider --tb=short --basetemp C:\Users\eicic.AIDEN-DESKTOP\AppData\Local\Temp\mdr-batch3-focused-oojfvwi3\pytest tests/test_batch3a_regressions.py tests/test_batch3b_regressions.py tests/test_batch3c_regressions.py
1 failed, 82 passed in 2.78s
```

두 pytest 프로세스의 exit code는 1이다. 신규 테스트의 유일한 실패는 `test_r04_legacy_finalize_requires_explicit_flag_and_records_mode`이며, `tests/test_batch3a_regressions.py:156` → `scripts/render_pdf.py:76`의 `subprocess.run(["pandoc", ...])`에서 `FileNotFoundError: [WinError 2]`가 났다. `shutil.which('pandoc')`도 `None`이었다. 전체 실패 39건은 출력상 같은 실행 파일 부재 또는 그로 인한 렌더/PDF 예상 결과 실패였다. 이를 제품 결함 39건으로 집계하지 않았고, 반대로 워커들의 개별 환경 통과 보고를 이번 통합 환경의 전체 통과로 대신하지 않았다.

읽기 전용 검증 스크립트는 PowerShell here-string을 `python -`로 전달하여 기존 fixture의 `work.__wrapped__`와 실제 검증 함수들을 호출했다. 원고·대장은 모두 새 OS 임시 폴더에 썼다. 콘솔 인코딩 때문에 첫 탐침의 한글 리터럴이 `?`로 바뀐 것을 확인하여, 한글은 Unicode escape로 전달한 **재실행 결과만 채택**했다. 초기 스크립트의 괄호 문법 오류도 수정 후 재실행했으며 발견 근거로 사용하지 않았다. 확인용 실행의 마지막 줄은 다음과 같다.

```text
CONFIRMED_PROBES_COMPLETE
INTERACTION_PROBES_COMPLETE
ORIGINAL_AND_FULL_G3_PROBES_COMPLETE
R05_ORIGINAL_PROBE_COMPLETE
```

각 실행은 차례대로 이미지 실제 G3 발급/변경·숫자 문맥, 단위 잔여 접미사·부록/분할·locator·조건 인용·읽기 실패·extend, 원래 R01/R03/R04와 전체 G3 재현, 원래 R05를 확인했고 exit 0으로 끝났다. `git diff a07a3c7..HEAD --check`는 출력 없이 exit 0이었다.

**미확인:** 정상 PDF를 렌더한 뒤 실제 G5까지 완료하는 경로와 그 상태에서의 이미지 변경 재검증, 순수 v3 명시 플래그의 성공 영수증/status 출력은 `pandoc`가 준비된 환경에서 다시 실행해야 한다. 동시 쓰기·경로 주입·설치기 보안은 이번 리뷰 범위가 아니다. 추가 의심을 확인된 결함으로 집계하지 않았다.

검토 중 `codes/market-deep-research/SKILL.md`에 별도 미커밋 변경이 나타난 것을 확인했다. 본 작업은 해당 파일을 쓰지 않았고 되돌리지 않았으며, 지정된 커밋 diff 밖의 변경으로 분리했다. 저장소 내 이번 리뷰 산출물은 이 파일 하나다.
