# claim-review — 문장과 근거의 의미 검토

원문에 단어나 숫자가 있다는 사실만으로 보고서의 주체·속성·범위·기간·조건이 모두 성립하지는
않는다. 검토자는 원문과 작성 문장을 함께 읽고 지원 범위와 누락된 한계를 판정한다.
스크립트는 의미를 추론하지 않고 검토의 누락·변경·미지원 판정이 최종본으로 넘어가는 것을 막는다.

## 절차
1. 원문 재열람과 수치 원자화·검산을 완료한다. 불일치는 원문을 보존하고 충돌로 남긴다.
2. 본문 문장 및 표 행에서 사실·계산·가정·권고를 구분한다. 숫자 없는 사실 문장도 검토한다.
3. 각 문장의 모든 F-ID와 연결 E-ID를 실제 근거와 대조한다. 반박검색에서 확인한 한계가
   본문에도 유지되는지 확인하고, 근거에 없는 속성은 삭제하거나 가정/미확인으로 명시한다.
4. `audit/claim-review.jsonl`에 아래 형식으로 기록한다. 문장 축소나 근거 변경 후에는 다시 읽고
   기록을 갱신한다. 오래된 partial 행을 현재 검토 파일에 방치하거나 해시만 새로 계산하지 않는다.
5. `python scripts/verify_claims.py <report.md> <work_dir>`를 실행한다. G3에서도 자동 실행된다.

## 기록 형식
```json
{
  "sentence_id": "S001",
  "claim_type": "observed",
  "fact_ids": ["F001"],
  "evidence_ids": ["E001"],
  "support": "supported",
  "unsupported_terms": [],
  "required_qualification": "에너지원 적용 여부는 미확인",
  "sentence_text": "센서 인증과 노선 적용은 확인되며, 에너지원 적용 여부는 미확인이다(F001).",
  "reviewed_text_sha256": "<sentence_text UTF-8 바이트의 SHA-256>",
  "evidence_revision": "<facts_db.confirmed_digest(FactsDB(work).facts())>"
}
```
필드는 모두 필수이며 `unsupported_terms`와 `required_qualification`은 빈 배열/문자열을 허용한다.
`sentence_text`는 현재 본문의 문장 또는 표 행 전체를 공백·줄바꿈까지 그대로 복사한다.
태그는 기존 `(F001)` 및 `[F001]` 형식을 공통 TAG 정규식으로 검사한다.
같은 문장이 반복되면 위치별로 고유 sentence_id를 가진 검토 행을 남긴다. 부록은 문장 검토의
전건성 검사 대상에서 제외되며 기존 숫자·태그 검사는 계속 적용한다. 태그 없는 주장도 수동 검토
대상이지만 자동 전건성은 태그가 붙은 문장에 한정된다. `tagged_sentences()`로 검사 단위를 확인할 수 있다.

## 판정 기준과 차단
| support | 의미 | observed/derived | hypothesis/recommendation |
|---|---|---|---|
| supported | 문장 전체가 근거 범위 내이며 한계도 보존됨 | 통과 | 통과 |
| partial | 일부 속성·범위만 지원 | 축소 후 재검토 | 가정/조건 명시를 검토한 경우 허용 |
| unsupported | 연결 근거가 주장을 지지하지 않음 | 차단 | 차단 |
| contradicted | 근거와 충돌 | 차단 | 가정/반론의 표현인지 검토한 경우 허용 |
| unresolved | 필요한 판단이 아직 미해결 | 차단 | 미확인 조건을 명시한 경우 허용 |

가정/권고의 조건 명시 여부 자체는 검토자가 판단한다. supported인데 unsupported_terms가 남아
있으면 모순된 검토이므로 차단한다. 지원 불충분 문장을 가정 유형으로 이름만 바꿔 통과시키지 않는다.
판정 외에도 필드·enum·F/E 연결·본문 실재·문장 해시·현재 근거 리비전을 검사한다.
문장 변경, 근거 변경, 문장 일부만 검토, 전건 기록 누락은 재검토 대상이다.

결과는 `audit/claim-check.json`, CLI는 v4 실패 시 exit 1이다. schema_version 생략은 v3이며
신규 검토 문제는 WARN으로 남긴다. WARN은 의미 검증 완료가 아니다. v4 이행은
`verification-gates.md`의 리비전/이행 절차를 따른다.
