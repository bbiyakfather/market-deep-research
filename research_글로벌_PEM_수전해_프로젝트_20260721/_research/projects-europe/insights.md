## 인사이트

- [사실] Air Liquide Normand'Hy(프랑스 Port-Jerome)는 200MW PEM 전해조로, Siemens Energy가 전해조를 공급하며 2026년 상업가동을 목표로 건설중이다 (TF001,TF002,TF003).
- [사실] Air Liquide ELYgator(네덜란드 로테르담 Maasvlakte)는 200MW 규모지만 PEM과 알칼라인을 한 부지에 결합한 최초 사례이며, PEM 스택만 Air Liquide-Siemens Energy 합작사가 공급한다. 2021년 계획상으로는 PEM/알칼라인이 100MW씩 균등분할이었으나 최종 확정 비율은 원문상 재확인되지 않았다 (TF004,TF007).
- [사실] Shell REFHYNE 프로젝트는 독일 Wesseling에서 10MW(2021년 가동, ITM Power 공급)로 시작해 100MW(REFHYNE II, FID 2024년, ITM Power TRIDENT 스택+Linde EPC)로 10배 확장 중이며, 유럽에서 PEM 전해조를 단계적으로 스케일업한 대표 사례다 (TF008,TF011).
- [사실] Iberdrola Puertollano(스페인)는 Nel ASA의 Proton PEM 기술(1.25MW 스택 16기, 총 20MW)로 2022년부터 가동중이며 Fertiberia 암모니아공장에 원료를 공급한다 (TF013).
- [사실] Håeolus(노르웨이 Varanger)는 알칼라인 1기+PEM 1기를 결합한 결합용량 2MW의 소규모 실증 프로젝트로, PEM 단독 용량은 이번 조사의 원문에서 특정되지 않았다 (TF016).
- [사실] 영국 West Wales Hydrogen(Milford Haven, Trafigura 자회사 MorGen Energy)은 ITM Power POSEIDON 20MW PEM 모듈로 2026년 3월 FID를 완료했고 2028년 가동을 목표로 한다 (TF017,TF019).
- [추론] 유럽 PEM 대형 전해조 프로젝트는 정유사(Air Liquide, Shell)가 자사 정유단지 탈탄소화 목적으로 주도하는 경향이 뚜렷하며, 전해조 OEM은 Siemens Energy(Air Liquide 합작)와 ITM Power(영국) 두 곳에 집중되어 있다 (TF001,TF004,TF008,TF011,TF017 근거).
- [추론] PEM 기술은 200MW급 대형 프로젝트에서도 알칼라인과 혼합 배치되는 경우(ELYgator)가 나타나는데, 이는 PEM의 급속 응답성(그리드 안정화)과 알칼라인의 비용 이점을 함께 취하려는 설계 전략으로 보인다 (TF004 근거).
- [추론] 같은 로테르담 Maasvlakte 지역에 위치한 Shell Holland Hydrogen I(200MW)과 Air Liquide ELYgator(200MW)는 흔히 혼동되기 쉬우나, 전자는 thyssenkrupp Uhde Chlorine Engineers의 알칼라인 기술로 확인되어 본 PEM 조사 범위에서 제외된다 (TF004 note 근거, 아래 폐기리드 참고).

## 요약

- 제안 fact 건수: 19건 (프로젝트 7건: Normand'Hy, ELYgator, REFHYNE II, REFHYNE I, Iberdrola Puertollano, Håeolus, West Wales Hydrogen/Milford Haven)
- Evidence 건수: 34건 (원문 fetch 완료, 로컬 저장 및 sha256 기록됨. 프로젝트당 평균 1.8건, 핵심 용량 수치는 대부분 2개 이상 독립 출처로 교차확인)
- 등급분포(evidence 34건, proposed_grade 기준, 스크립트로 재계산 확인):
  - authority: A 6건 / B 25건 / C 3건
  - independence: A 4건 / B 14건 / C 16건
  - directness: A 31건 / B 3건
  - recency: A 17건 / B 11건 / D 6건
- 담당 범위(EU27+영국+노르웨이+아이슬란드) PEM 프로젝트 최소 6~8건 기준 충족(7건 확보, PEM 명시 원문 전건 확인).

### 폐기 리드 (근거 부족·PEM 불확정으로 등재 보류)

- Shell Holland Hydrogen I(네덜란드 로테르담 Maasvlakte, 200MW) — thyssenkrupp 공식 보도자료가 "20 MW **알칼라인** water electrolysis module" 기반이라고 명시(로컬: `_research/projects-europe/raw/1cdefcea30a9_clean.txt`). PEM 아님이 원문으로 확정되어 담당 범위 제외.
- HyDeal España(스페인, ArcelorMittal/Enagás/Fertiberia/DH2 Energy 주도, 목표 3.3GW 전해조) — 다수 매체·공식 보도자료를 검토했으나 전해조 방식(PEM/알칼라인/AEM)을 명시한 원문을 찾지 못함. GW급 대형 프로젝트라 매력적이나 PEM 확정 불가로 폐기.
- Repsol Petronor Bilbao(스페인, 100MW, COD 2029) — 기존 2.5MW(2023 가동)·10MW(2026, Sunfire 공급) 단계는 확인했으나 신규 100MW 전해조의 방식(PEM 여부)을 확인하는 원문을 찾지 못함. Sunfire는 통상 알칼라인/SOEC 공급사여서 PEM 여부 불확실.
- Håeolus PEM 단독 용량 — 일부 2차 자료(웹검색 스니펫)가 "2.5MW PEM 전해조"라고 언급하나, 이번에 fetch한 1차 출처(EU Clean Hydrogen Partnership 공식 프로젝트 저장소)는 "combined capacity of 2 MW"(알칼라인+PEM 합산)만 명시하고 PEM 단독 수치는 특정하지 않음. 정확한 PEM 단독 MW는 폐기(TF016 note 참고, 팀리드가 SINTEF 1차 문헌 등으로 추가 확인 시 등재 가능).
- ITM Power/West Wales Hydrogen "120MW 전기입력용량" — Trafigura 보도자료 각주 수치(120MW)가 ITM Power 발표 "20MW POSEIDON 모듈"과 같은 개념인지 다른 개념(그리드 연계용량 등)인지 원문에 설명이 없어 별도 fact(TF018)로만 분리 기록, 정식 등재 여부는 팀리드 판단 필요.
- 검색 백엔드(search.py DDG) 다수 쿼리에서 요청 제한(202/차단)으로 결과 0건 — 내장 WebSearch로 대부분 대체했으나, 완전성은 보장되지 않음("못 찾음"이 "존재하지 않음"을 의미하지 않음).
