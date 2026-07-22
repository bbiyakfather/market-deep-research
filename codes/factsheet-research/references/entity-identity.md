# entity-identity — 기관·기업 동일성 확인 게이트 (기관조사 G0 선행)

동명이인·유사상호·지주사/자회사 혼동으로 **엉뚱한 대상의 수치**를 섞는 오귀속을 막는다.
기관·기업 조사는 조사 착수 전 대상을 **식별자로 확정**한다.

## 확정 필드 (가능한 만큼 결박 → fact.context.entity_id)
| 필드 | 소스 예 |
|---|---|
| 법인명(정식) + 영문명 | 등기·공시 |
| 사업자등록번호 | 국세청 진위확인 |
| 법인등록번호 | 등기 |
| 대표자·설립일·업종 | 금융위 기업개요·DART 개황 |
| 본점 주소 | 등기·인허가 |
| 이전 상호(연혁) | 공시 연혁 |
| 해외 식별자 | SEC CIK · LEI · OpenCorporates ID |

## 확정 절차
1. 후보 명칭으로 조회 → 복수 후보면 사업자/법인번호로 유일 확정.
2. 지주사/자회사/브랜드명 구분(연결 vs 별도 재무 — `context.definition` 에 명시).
3. 확정 결과를 `audit/` 및 보고서 0부(표지·메타)에 기록. 이후 모든 fact 의 `entity_id` 고정.

## 무료 공공 MCP/스킬 활용 (있으면)
- `nts-business-registration`(사업자 진위·상태), `fsc-corporate-info`(법인 개요),
  `k-dart`/`opendart-*`(공시·재무·개황), `national-pension-workplace`(직원규모),
  `nts-tax-delinquency`(체납), `g2b-sanctioned-supplier`(부정당제재), `biz-health-check`(교차 실사).
- 이들 응답은 `api_response` 증거로 결박(사업자번호 입력↔응답 교차검증).

## 실사 주의
- 같은 숫자라도 **연결/별도, 총액/순액, 발표주체**가 다르면 다른 fact(다른 claim_key).
- 미확인·상충은 `disputed`/미확인 유지(추정 금지). 부정적 사실(체납·제재 0건)은 `negative_search` 증거.
