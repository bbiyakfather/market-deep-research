# 배치 2B 품질보증 리뷰

판정: **REQUEST_CHANGES**

8개 항목 중 6개는 해소, N07·N19는 부분 해소다. 일반 본문 disputed 인용 차단의 회귀, 부록 disputed 인용의 v4 문장검토 누락, 기존 Decimal 범위 파싱의 회귀를 재현했다. 모두 현재 G3 내용 검사에서 잘못된 입력이 `ok=true`로 통과하며, 단순 문구·테스트 스타일 지적이 아니다.

## 범위·가정·검증 근거

- 판정 대상은 같은 scratchpad의 `batch2b.diff`, 요구사항은 `spec-batch2b.md`다. 최초 호출용 prompt 폴더에는 두 입력이 없어 실제 입력을 발견한 이 scratchpad를 산출물의 “같은 폴더”로 해석했다.
- 원 결함은 `F:/Claude/skills/market-deep-research/_planning/council-2026-09-05/review-astra-2.md`와 대조했다. 아래 `scripts/`, `tests/`, `references/` 경로는 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 기준이며 라인은 현재 워킹트리 기준이다.
- 구현·테스트·문서를 수정하지 않았다. 추가 재현은 임시 조사에서 수행했고 이 폴더에 리뷰 증적만 저장했다. 변경 전 숫자·태그 검사와의 비교는 `git show HEAD:codes/market-deep-research/scripts/verify_facts.py`를 별도 모듈로 읽어 수행했다.
- pytest 373개·데모 3종·preflight 통과는 팀리드가 제공한 검증 사실로 수용했다. 전체 검증을 재실행했다고 주장하지 않는다. 자체 실행은 아래 추가 재현과 v3 키 호환 확인이다.
- 재현 스크립트: `astra-2b-review-probes.py`; 결과: `astra-2b-review-probes.json`. 세 재현군과 정상/차단 대조군의 assertion이 모두 통과했다. 이때 “assertion 통과”는 결함이 재현됐다는 뜻이다. G3는 `verify(..., check_only=True)`로 검사했으며 G5 최종 출고까지 실행한 결과는 아니다.
- v3의 기존 WARN 정책, risk 휴리스틱의 WARN만 수행하는 정책, 본문 미사용 high-risk 조건의 WARN 정책은 결함으로 세지 않았다.

## 항목별 해소 판정

| 항목 | 판정 | 근거 및 실질 평가 |
|---|---|---|
| N07 음수 부호 | **부분** | `scripts/verify_facts.py:61`, `scripts/verify_facts.py:265`, `scripts/verify_facts.py:365`: 부호 있는 scalar·범위와 접두 통화의 부호를 보존한다. `tests/test_batch2b_regressions.py:43`, `tests/test_batch2b_regressions.py:53`은 원 양방향 부호 불일치를 검사한다. 그러나 새 범위 문법이 기존 `.5~.6`·`1e3~2e3`를 파싱하지 않아 값 비교와 핵심수치 판정을 생략한다(R3). |
| N08 SI 접두사 | **해소** | `scripts/verify_facts.py:68`, `scripts/verify_facts.py:202`, `scripts/verify_facts.py:220`: SI 토큰만 대소문자를 구분하고 µ/μ/u/m/k/M/G/T 및 W·Wh 차원을 보존한다. 통화는 기존 대소문자 무관 경로를 유지한다. `tests/test_batch2b_regressions.py:61`, `tests/test_batch2b_regressions.py:72`, `tests/test_batch2b_regressions.py:78`은 정상 스케일, 잘못된 값, mW↔MW, W↔Wh, 통화·Mt·개수·주석 단위를 대조한다. 이 범위에서 추가 회귀를 발견하지 않았다. |
| N09 스키마·시간 | **해소** | `scripts/facts_db.py:76`, `scripts/facts_db.py:99`, `scripts/facts_db.py:147`: 재귀 타입·배열 item·공백·유한 숫자·이벤트 datetime을 검사하고 v3 새 위반은 WARN으로 노출한다. `scripts/verify_facts.py:579`, `scripts/verify_facts.py:584`, `scripts/verify_facts.py:591`은 문자열 AB·공백 query·허위 날짜를 그대로 신뢰하지 않는다. `tests/test_batch2b_regressions.py:89`, `tests/test_batch2b_regressions.py:120`, `tests/test_batch2b_regressions.py:140`, `tests/test_batch2b_regressions.py:152`에 부정·정상·v3·G3 경로가 있다. |
| N10 F↔E 역참조 | **해소** | `scripts/verify_facts.py:545`: 모든 상태의 F→E 존재·소유 fact 일치와 E→F 존재·역목록 포함을 검사한다. 양쪽 어느 행이든 v4면 강제하고 기존 v3의 신규 역참조 문제는 WARN이다. `references/verification-gates.md:25`에 한 evidence는 한 fact 소유라는 모델을 명시했다. `tests/test_batch2b_regressions.py:166`은 confirmed에 국한하지 않고 pending 대장도 양방향 검사한다. |
| N11 claim_key | **해소** | `scripts/facts_db.py:284`, `scripts/facts_db.py:291`, `scripts/facts_db.py:346`, `scripts/facts_db.py:447`: entity_id·definition 포함 JSON 해시, v4 재계산 대조, v3 산식/기존 키 보존, diff 중복키 거부 및 실제 add_evidence 안내가 구현됐다. 이행 규칙은 `references/verification-gates.md:23`. `tests/test_batch2b_regressions.py:187`, `tests/test_batch2b_regressions.py:196`, `tests/test_batch2b_regressions.py:217`과 별도 직접 실행으로 기존 opaque v3 키의 G3 통과·보존, 키 없는 신규 v3 행의 구 산식 생성, v3 diff의 값 변경 검출을 확인했다. |
| N18 부록 경계 | **해소** | `scripts/verify_facts.py:905`, `scripts/verify_facts.py:1031`: 마커 직후 부록 헤딩, 승인 부록 제목, 뒤따르는 본문·미승인 헤딩을 검사한다. `tests/test_batch2b_regressions.py:293`, `tests/test_batch2b_regressions.py:303`, `tests/test_batch2b_regressions.py:315`은 원 Executive conclusions 재현, 승인 본문·미승인 장, 정상 환산 부록의 WARN 유지와 헤딩 앞 수치를 검사한다. 승인 목차 없는 legacy의 축소 검사 정책은 문서에 명시돼 있다. |
| N19 disputed 병기 | **부분** | `scripts/verify_facts.py:392`, `scripts/verify_facts.py:656`, `scripts/facts_db.py:424`: 명시 문장·표행의 병기, 값·단위·증빙 검사 및 v4 disputed 내용의 revision 결박은 구현됐다. 그러나 URL 제거 뒤에 상태 검사를 수행하면서 일반 본문 disputed 태그를 누락한다(R1). 부록 인용은 증빙 검사에만 추가돼 문장검토를 우회한다(R2). |
| K06 고위험 강제 | **해소** | `scripts/verify_facts.py:472`, `scripts/verify_facts.py:575`: 연결된 E의 fact_id·source_role·observer_group을 조인하고 같은 그룹·URL·해시는 병합한다. v4 그룹 수는 independent_groups 자기신고와 무관하다. query/result/반박 없음·실재 연결 primary E·유효 시점을 본문 사용 confirmed에서 모두 FAIL로 강제한다. `tests/test_batch2b_regressions.py:242`의 원출처 하나·재인용·동일 그룹/URL/해시 대조가 실질적이며 `tests/test_batch2b_regressions.py:267`, `tests/test_batch2b_regressions.py:282`는 정책상 WARN을 고정한다. 출처 역할·그룹 라벨 자체의 사실 적합성은 문서대로 팀리드가 확인하는 범위다. |

## 발견 사항

### R1 — 중대: 링크 뒤 태그가 제거되어 일반 본문 disputed 인용이 통과

- **변경 근거:** `scripts/verify_facts.py:390`, `scripts/verify_facts.py:393`. 종전 전역 태그 검사가 `split_segments(body)` 안으로 이동했다. 이 함수의 기본 경로는 `scripts/verify_facts.py:149`에서 `https?://\S+`를 제거하므로 링크 닫는 괄호에 붙은 실제 본문 태그까지 없앤다.
- **재현:** 유효한 v4 F001/E001 및 캡처를 준비하고 F001을 disputed로 둔다. `[상충]` 없이 `Certification is verified [source](https://example.test/source)(F001).`를 본문에 쓴다. 이 문장에 대한 정상 형식의 supported 검토 행을 기록한다. 승인 목차도 갖춘 현재 G3는 **`ok=true`, failures 0**이다. 숫자가 없는 주장도 status 검사의 대상이라는 기존 계약에 해당한다.
- **직접 비교:** 변경 전 `check_bound_numbers`는 `[미확정] ... status=disputed`로 차단했다. 현재 세그먼트는 `Certification is verified [source](`만 남는다. 링크와 태그 사이에 공백 하나를 넣으면 현재 G3도 `[미확정]`으로 차단한다. 문장검토는 태그·증거 결박을 확인하지만 status를 검사하지 않아 이 회귀를 보완하지 못한다.
- **영향:** N19에서 명시적으로 요구한 일반 본문 disputed 차단이 약화됐다. 수치가 없는 확정적 표현을 링크 뒤 태그로 인용할 때 발생하며, 검토 행이 있다는 사실만으로 disputed 인용이 허용돼서는 안 된다.
- **최소 수정안:** 상태·태그 존재·상충 문맥 검사는 URL 제거 전의 원문 세그먼트로 수행하고 숫자 오탐 방지용 URL 제거와 분리한다. 링크 목적지만 제거할 경우에도 뒤의 F태그는 보존해야 한다. 링크에 붙은 태그/띄운 태그 각각에 대해 confirmed 정상·disputed 무마커 실패·명시 상충 정상 대조를 추가한다.

### R2 — 중대: 부록 disputed 문장에는 v4 문장검토가 적용되지 않음

- **변경 근거:** `scripts/verify_facts.py:1050`에서 부록 disputed 태그를 추가하지만 넘기는 곳은 `check_evidence_chain`뿐이다. `scripts/verify_claims.py:55`는 여전히 부록을 버리고 본문만 검토한다. 새 문서 `references/report-format.md:25`, `references/verification-gates.md:66`은 상충 인용에 v4 문장검토도 동일하게 적용한다고 명시한다.
- **재현:** 검토가 완료된 정상 F001 본문 뒤에 승인된 부록을 두고, 정상 E002·캡처를 연결한 v4 disputed F002를 `[상충] Source claims 45 USD(F002).`로 인용한다. claim-review.jsonl에는 F001 본문 행만 기록하되 revision은 현재 대장에 맞춘다. 승인 목차는 `# 부 1. 본론`과 `# 부 11. 부록`이다. **G3는 `ok=true`, failures 0**이며 F002 문장 검토 누락 경고도 없다.
- **변경 감지 대조:** 부록 문장을 `An entirely different interpretation asserts ...`로 바꾸고 검토 대장은 그대로 두어도 G3가 통과한다. 반면 E002의 image_sha256을 변조하면 실패하므로 증빙 검사는 실제로 실행되며 빠진 것은 문장검토 경로다.
- **영향:** 이번에 새로 허용한 부록 상충 인용에서 P0의 문장 전체 검토·문장 변경 감지를 적용하지 못한다. 기존 일반 부록 전체를 재검토하자는 지적이 아니라, 새 disputed 허용 통로와 문서의 결박 약속에 한정된 결함이다.
- **최소 수정안:** 기존 verify_claims의 대상 집합에 명시적 disputed 부록 세그먼트를 포함한다. 해당 문장도 전체 문장 일치·reviewed_text_sha256·evidence_revision을 검사하고, 검토 누락/문장 교체 실패와 정식 검토 후 정상 통과를 대조한다.

### R3 — 중대: 기존 Decimal 범위를 자유서식으로 간주해 값 불일치를 놓침

- **변경 근거:** `scripts/verify_facts.py:281`. 단일 값은 Decimal로 읽지만 범위는 `_NUM_CORE` 기반 `_VALUE.fullmatch`로 제한한다. 따라서 기존에 양 끝을 Decimal로 파싱하던 `.5~.6` 및 `1e3~2e3`가 이제 `None`이 된다.
- **재현:** v4 confirmed F001의 value를 `{raw: '.5~.6', unit: 'USD'}`로 두고 본문에 `Range 9~10 USD(F001).`를 기록한다. 정상 증거·캡처·본문 검토·승인 목차를 갖춘 현재 G3는 **`ok=true`**, `[값미대조]` WARN만 반환한다. `1e3~2e3`도 동일하다.
- **직접 비교:** 변경 전 `.5~.6`은 `[Decimal('0.5'), Decimal('0.6')]`, `1e3~2e3`은 `[Decimal('1E+3'), Decimal('2E+3')]`로 읽혀 위 본문을 `[값불일치]`로 차단했다. 현재 두 범위 모두 None이다. 일반 `40-45` 범위는 전후 모두 정상이다.
- **영향:** 기존 정상 대장 표기가 수식/자유서식으로 재분류돼 잘못된 본문 수치를 검출하지 못한다. 같은 파싱 결과를 사용하는 `scripts/verify_facts.py:689`의 핵심수치 분류도 사라진다. 이는 자유서식에 WARN을 주는 기존 정책에 대한 이의가 아니라, 기존에 읽던 숫자가 새 문법에서 누락된 회귀다.
- **최소 수정안:** 범위 양 끝의 부호 있는 Decimal 토큰도 선행 소수점·지수 표기를 수용하도록 확장하되, 지수의 부호와 범위 구분자를 구별한다. 각 표기에 같은 값 정상·다른 값 실패·부호 불일치 실패 대조를 추가한다.

## 잔존 확인 3건

| 항목 | 원 재현과 신규 테스트의 대응 | 판정 |
|---|---|---|
| N04 | `tests/test_batch2b_regressions.py:383`은 실제 G3·렌더·G5 완료 후 G1 실패를 append하고 계획을 변경한다. G5 현재 영수증 무효, finalize 실패, manifest CLI exit 1, 마지막 성공 영수증 부재를 확인한다. 원 공격 순서를 실질 재현한다. 계획 변경만의 독립 원인 분리는 이 테스트 하나로 입증하지 않지만 원 복합 재현의 회귀 고정에는 충분하다. | 해소 확인 |
| N05 | `tests/test_batch2b_regressions.py:394`는 [2] 이후 claim/entity/entity_id/period/definition을 각자 변경한다. raw·unit·lead 이벤트를 유지하며 claim_key는 새 context에 맞게 재계산하므로 N11의 키 오류 때문에 실패하는 테스트가 아니다. digest 변화, [2] 무효, G3 CLI 차단을 확인한다. | v4 해소 확인. v3 구 digest 유지 정책은 제외 |
| N13 | `tests/test_batch2b_regressions.py:408`은 실제 PDF에서 45를 성공 캡처한 뒤 같은 파일로 999를 재요청한다. CLI exit 1·기존 PNG 삭제·FAILED sidecar 생성·증빙유실과 정상 재시도 복구를 확인한다. `scripts/capture_pdf.py:62`의 선제 무효화 및 `scripts/capture_pdf.py:165`의 종료코드 수정이 원 재현을 직접 차단한다. | 잔존 수정으로 해소 |

## P0·배치 2A 상호작용 및 신규 테스트 평가

- N05 회귀 테스트는 키를 갱신한 후에도 [2]가 무효임을 확인해 P0의 문맥 결박과 N11의 새 키 강제를 구분한다. v4 confirmed의 기존 digest 구조는 유지하고 disputed만 포함한 변경(`scripts/facts_db.py:428`)도 문장검토 revision과 연결돼 있다. N19 본문 context 변경 테스트(`tests/test_batch2b_regressions.py:354`)는 재검토 전 실패·재검토 후 통과를 확인한다.
- 캡처 실패 재시도는 옛 이미지 삭제 후 G3 증빙 검사에서 차단되므로 P0의 image_sha256 검토를 약화시키지 않는다. 정상 음수·통화·SI 비교에서도 P0의 계산 원자값 처리를 대체하지 않는다. 게이트/manifest 및 배치 2A의 fetch·출처 수집 구현은 이번 diff에서 변경되지 않았다.
- 반면 R1은 N19 상태 차단이 P0 문장검토로 보완되지 않는 실제 통합 회귀이며, R2는 새 허용 범위가 P0 문장검토 대상에 전파되지 않은 누락이다. R3는 G3 수치 비교뿐 아니라 핵심수치 캡처 요구의 분류에도 영향을 준다.
- 신규 테스트는 단순 실행 성공만 검사하지 않는다. 값·차원 차이, 쓰기 거부 후 파일 불변, 중복키 양쪽 입력, E의 실제 역할/그룹/URL/해시, 실제 CLI·PNG 실패와 정상 복구를 대조하므로 전반적으로 실질적이다. 163개라는 수에는 parameterization이 포함되며 독립적인 163개 시나리오로 과장하지 않는다.
- 남은 회귀망의 구체적인 빈틈은 URL 인접 태그, 부록 disputed 문장검토 누락/교체, Decimal 범위의 선행 소수점·지수다. `tests/test_batch2b_regressions.py:83`은 이 숫자 형식을 scalar로만 다루고, `tests/test_batch2b_regressions.py:371`은 부록 상충의 증거 누락만 다룬다. 따라서 기존 373개 통과와 이번 발견은 모순되지 않는다.

세 발견을 수정하고 해당 부정·정상 대조를 보강한 뒤 재검토가 필요하다. 그 외 범위 확장이나 v3 정책 변경은 승인 조건으로 요구하지 않는다.

ASTRA_2B_DONE verdict=REQUEST_CHANGES
