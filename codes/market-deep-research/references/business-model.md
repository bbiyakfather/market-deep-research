# business-model — BM 칸을 사실·가설·미닫힘으로 가르기 (독자 A 기술이전 · B 예비창업 · C 상대 BM 해부)

**로드 시점**: G0 에서 핵심 메시지에 BM 명사(수익 구조·과금·수요기업·사업모델·이전 조건)가 들어가거나 독자 유형이 A/B/C 일 때. §0·§1·§5(해당 분야 행)는 공통, 그다음은 **해당 독자 § 하나만**, G3 직전에 §6. 독자 라벨은 `reader-goal.md` 프리셋 행 — A = 기술이전 희망 연구자, B = 예비창업자·창업팀, C = 사업화 주관기관·컨소시엄 및 기관 내부 기술사업화 판단. E1/E2/I/X 기호는 audit 에서만 쓰고 본문은 기존 표기(Fxxx·`(분석)`·`미확인`·`목표(계획서 인용)`)만. 연도 없는 링크는 페이지에 연도가 없는 것이라 재열람일을 대신 적는다. 새 조사유형이 아니다 — 기술사업화 실사·기관기업 실사 축 위에 얹는 횡단 모듈(`competitive-positioning.md` 와 같은 지위). 증빙(F태그·재열람·캡처)은 MDR 엔진이 하고, 이 문서는 **무엇을 어떤 칸으로 묻고 어느 칸을 사실로 올리면 안 되는지**만 정한다. 근거: 방법론 조사 2026-10-08(`docs/prd-business-model_261008.md` §1.7, 공개자료만).

## 0. 증거 등급 → 기존 스키마 (새 enum·필드·본문 표기 없음)
| 등급 | 뜻 | 대장·본문 처리 |
|---|---|---|
| E1 | 공개 URL 의 원문 문장·표를 다시 열어 캡처할 수 있다 | `observed`·confirmed·캡처 필수 → 본문 (Fxxx) |
| E2 | 검색 발췌·2차 요약 페이지만 봤다 | 본문 금지. audit 에 재열람 과제로만, 칸은 `미확인` |
| I | 고객·구매자·내부 운영의 말·행동 없이는 안 닫힌다 | `hypothesis`, 인터뷰는 attribution. 문장 앞 `(분석)` + required_qualification |
| X | 비공개·페이월·로그인·거절·이번에 못 엶 | `미확인` + 사유. 평균·업계값·"보통" 으로 메우지 않는다 |
BM 칸은 절반이 I 다. 이 모듈의 일은 I 가 E1 처럼 본문에 오르는 경로를 막는 것이다.
정의 앵커(E1, 패러프레이즈 금지): [Teece 2010](https://v-assets.cdnsw.com/fs/root/8jig8-businessmodelsbusinessstrategy.pdf) "articulates the logic and provides data and other evidence that demonstrates how a business creates and delivers value to customers … the architecture of revenues, costs, and profits"(LRP 43, 출판사 OA 아님) · [Zott & Amit 2010](https://faculty.wharton.upenn.edu/wp-content/uploads/2012/05/businessModelDesign_Amitzott_LRP2010.pdf) "a system of interdependent activities that transcends the focal firm and spans its boundaries".

## 1. 공통 절차 6단계 (독자 무관 · 건너뛰면 뒤의 벤치마크가 다른 사업을 평가한다)
| 단계 | 작업 | 산출물(1~3 은 G0 승인 전 `audit/research-plan.md` §BM, 4~6 은 G0 뒤라 `audit/intent-diff.md` §BM — research-plan 은 G0 해시 동결) | 없으면 보고서에 쓸 문장(태그가 아니라 문장 예시) |
|---|---|---|---|
| 1 거래 한 문장 | 누가 누구에게 무엇을 얼마에, 돈은 언제 들어오고, 회사가 중간에 무엇(재고·신용·임상·제작비·설치)을 부담하나. 피치덱 업종명·'플랫폼'·'딥테크' 는 이 문장 뒤에만 | 문장 1개 | "비즈니스 모델 미확정" |
| 2 단위 고정 | 고객·거래·양품·프로그램·주문·구독자·마일스톤 중 **1개**. 둘이면 표를 나눈다(§5 혼합형) | 정의 1줄 | "단위경제 비교 불가" |
| 3 과금 방식 분류 | 산업이 아니라 **과금**으로: 구독 / 거래 수수료 / 마켓 테이크 / 엔터프라이즈 계약 / 사용량 / 상품 판매 / 광고 / 마일스톤·LOI(하드테크·바이오) — [YC Epstein 9유형](https://www.ycombinator.com/library/Gh-yc-guide-to-business-models) · §5 분야 행 | 유형 1개 + 버린 유형·이유 | "주 모델 미판정" |
| 4 매출 다리 | 계약액(bookings)·청구액·회계매출·반복매출(ARR)·총거래액(GMV/TPV)·순수익을 한 표에, 차이를 설명 — [a16z 16 metrics](https://a16z.com/16-startup-metrics/)·[16 more](https://a16z.com/16-more-startup-metrics/) | 대조표 | "매출 정의가 회사 제시에 의존" |
| 5 병목 질문 | §5 해당 분야 행의 질문에 답(답마다 E1/I 등급) 또는 `미확인`. 가정값을 넣은 계산은 `(분석)` | 답/`미확인` 표 | "핵심 위험 미검증" |
| 6 집중·코호트 → 미닫힘 선언 | 상위 고객·도시·작품·부품·부처 비중, 초기 vs 후기 코호트(초기 코호트가 좋은 건 자기선택일 수 있다 — [a16z 13 metrics](https://a16z.com/13-metrics-for-marketplace-companies/)). 의사결정에 영향 있는 I·X 칸만 **9부 앞머리**에, 나머지는 audit(`competitive-positioning.md` §1.3 과 같은 기준) | 미닫힘 목록 | "평균이 소수의 결과일 수 있음" |

## 2. 독자 A — 출연연·대학 연구자: 보유 기술로 가능한 BM 과 수요기업 (5부 이중매핑과 1:1)
질문은 "어떤 회사가 이 기술을 사서 어떤 모델로 돈을 버는가". 기술 = 제품이라는 가정을 A3 에서 끊는다. 칸 이름은 [기술평가 실무가이드 2021](https://www.valuation.or.kr/data/2021%EB%85%84+%EA%B8%B0%EC%88%A0%ED%8F%89%EA%B0%80%EC%8B%A4%EB%AC%B4%EA%B0%80%EC%9D%B4%EB%93%9C.pdf) 표 9~12(기술성·권리성·시장성·사업성 — `report-format.md` 의 2018 매뉴얼 체계와 같은 4요인)를 쓴다. 부록5(p.233~243) 5점 척도의 시장·사업성 14항목(시장진입 장애 수·성장전망 CAGR 구간·준비기간·소요자금·매출 성장·수익성 등)은 **앵커 문장은 E1 인용, 대상에 매긴 점수는 `(분석)`**. 부록5 에는 가중치가 없고, 투자용 평점모형 가중치(p.313 — 같은 숫자를 p.264 가 "예시·기관 조정 가능" 이라 적음)도 **점수 합산에 쓰지 않는다**. 투자용 등급 정의(p.267 AAA~C)는 이름만. 이전 형태는 [ETRI 유형](https://itec.etri.re.kr/httx/itec/sub01/sub01_02.do) 양도/실시(전용·통상·독점·비독점) 분류, 기술료는 [ETRI 절차](https://itec.etri.re.kr/httx/itec/sub01/sub01_03.do) 의 "기술가치 평가를 통해 산정" 까지만 E1.
| 단계 | 작업 | 증거원 (E1 / I) |
|---|---|---|
| A1 기술 식별 | 표 9: 기술 개요·적용 제품·추가 필요기술. 장치/방법/HW/SW/서비스 명시, 청구항↔제품 대응표 | KIPRIS 공보·논문 E1 / 연구자 메모·미공개 성능값 I(`reader-goal.md` "연구팀 제시값") |
| A2 권리로 후보 제한 | 표 10: 청구범위·패밀리·법적 상태·회피 가능성 → 이전 형태(통상·전용·양도)는 **후보로만** | 등록원부 E1 / 무효 의견은 변리 검토 전 I |
| A3 SISP 검사 | 기술 문장이 고객 고통 문장보다 앞이면 실패(solution in search of a problem — [YC Hale](https://www.ycombinator.com/blog/startup-school-week-1-recap-kevin-hale-and-eric-migicovsky/)). 고통 문장 없으면 "문제 미확인" | 규정·가이드라인 원문 E1 / 고통의 강도 I |
| A4 BM 후보 3~5 | Who/What/How/Why([Gassmann 백서](https://cdn.prod.website-files.com/6888c528fb8adf9c48159ccb/69df7a462355bc3a757d1fb0_Business%20Model%20Navigator%20Whitepaper.pdf)) + CVP·수익식·핵심자원·핵심프로세스([Johnson HBR 2008](https://hbr.org/2008/12/reinventing-your-business-model))로 생성. 패턴은 [패턴 페이지](https://businessmodelnavigator.com/explore) URL 결박, 억지 배정 금지(책 55개 vs 사이트 60개 — 수를 하나로 닫지 않는다) | 패턴 페이지 E1 / 적합성은 I |
| A5 수요기업 롱리스트 | 수익이 나는 **제품의 KSIC**(가이드 업종 규칙: 로봇 제조가 아니라 청소 용역이면 N74211) → 그 업종의 제조·적용·유통사를 **시장 대리신호 6종**(VC/PE 투자 · 공공 조달 · 대기업 R&D · 스타트업 설립 · 오프테이크/파트너십 · 의무수요 규제 — [academic-commercialization-agent](https://github.com/shuxiachai/academic-commercialization-agent/blob/main/src/academic_agent/config/tasks.yaml)) + KIPRIS 출원인 + NTIS 수행기관에서. 행마다 신호 유형·URL·F태그 | 공시·출원인·조달 E1 / "살 의향" I |
| A6 위험 분리 | 만드는 게 불확실하면 1차 지표 = technical milestone, 살 사람이 불확실하면 수요 증거(LOI·유료 파일럿). 상업 성숙도 단계 이름은 [KTH CRL·BRL 1~9 공개 PDF](https://kthinnovationreadinesslevel.com/wp-content/uploads/sites/9/2021/02/Customer-Readiness-Level_F.pdf)(CRL4 = 복수 고객이 문제 확인, B2B 5~10·집중 시장 2~5 는 예시 / BRL6 = 테스트 판매로 가격 확인([BRL PDF](https://kthinnovationreadinesslevel.com/wp-content/uploads/sites/9/2021/02/Business-Readiness-Level_B.pdf))) — 단계 이름만, 점수 아님 — [Friedman](https://www.ycombinator.com/library/8G-advice-for-hard-tech-and-biotech-founders)·[Seibel KPI 4갈래](https://www.ycombinator.com/library/9i-how-to-choose-a-metric-and-set-your-kpi) | 논문·인증·인허가 E1 / 고객 수용 I |
| A7 사업주체별 사업성 | 표 12: 후보 기업마다 생산·영업·자본·준비기간을 공시로. 같은 기술도 주체가 바뀌면 사업성이 바뀐다 | 공시 E1 / 경영 역량 I |
| A8 이전 조건 스케치 | 선급·경상·최소구매·개량발명 귀속은 협상 항목으로 분리. 가격은 시장접근법 전제(비교 가능 거래·유사성)를 충족하는 **비교 거래 캡처가 있을 때만**, 적용 가격은 `(분석)`. [KAIST Type 1~5](https://itvc.kaist.ac.kr/sub0301) 는 KAIST 교원창업 조건이지 시장 로열티 통계가 아니다 | 비교 거래 없으면 `미확인` |
보고서 위치: 5부 수요 행 = A5(신호 유형 열 필수), 5부 공급 행 = A1·A2, A3·A6 → 기술성·시장성 축(표 11 시장성 항목은 `competitive-positioning.md` 경쟁 대안 지도로), A4·A7 → 사업성 축, A8 → 10부 권고(recommendation). 신호·공시 값은 E1, 거기서 끌어낸 수요 후보 판단은 `(분석)`. 공개자료로 닫히는 것: 권리 범위·법적 상태·출원인 지도·KSIC·공시 매출 품목·인허가 존재. 닫히지 않는 것: 수요기업이 그 고통에 돈을 쓰는지·기술기여도·예상 점유율·이전 가격.

## 3. 독자 B — 예비창업자·창업팀: 자기 BM 가설 (절차표·가정 지도·실험 카드 필드는 다음 B 사례 때 — PRD §2.6-3, 지금은 증거 표만)
캔버스 9칸(문제·고객·UVP·솔루션·핵심 행동·채널·비용·수익·불공정 우위 — [Maurya 2010](https://ashmaurya.com/blog/how-to-document-your-business-model-on-1-page))은 채움 순서 정답이 없고 **검증은 가장 위험한 가정부터**([Maurya, 재열람 2026-10-08](https://blog.leanstack.com/what-is-the-right-fill-order-for-a-lean-canvas/)). 검증 순서는 캔버스 스냅샷 → 고객·문제 인터뷰(약 2다스) → 데모·오퍼 → 사겠다는 고객이 있을 때만 MVP(Demo-Sell-Build — [Maurya](https://medium.com/lean-stack/dont-start-with-an-mvp-aa883de5cd18)). 칸마다 가설 ID, 세그먼트가 둘이면 캔버스 둘. 보고서 칸 이름은 K-Startup 초기창업 양식의 "경쟁사 분석·목표 시장 진입 전략·비즈니스 모델(수익화 모델)·투자유치(자금확보) 전략"([초기창업패키지 별첨1 사업계획서 hwp](https://www.mss.go.kr/common/board/Download.do?bcIdx=1065082&cbIdx=254&streFileNm=a92bd373-5d9a-4fde-a5cc-bf5aaab02ca1.zip), 공고 2026-38호)과 맞춘다. 사업계획서·피치덱 문장은 `목표(계획서 인용)` 로 표기하고 사실로 올리지 않는다.
| 칸 | 스킬이 닫는 것(E1) | "미실시" 로 선언(I) | 합격 증거 | 불합격 |
|---|---|---|---|---|
| 문제·고객 | 규정·가이드라인·공개 리뷰 | job 의 중요도·마지막 발생 장면 | 인터뷰 기록(attribution) — 응답이 수렴해 새 정보가 안 늘면 Discovery 종료([Blank 2009](https://steveblank.com/2009/09/17/the-path-of-warriors-and-winners/)); 인터뷰는 '말'이라 증거 점수 상한 2/5([Strategyzer 2021](https://www.strategyzer.com/library/business-testing-is-your-hypothesis-really-validated)) | "쓸 것 같다" 설문 |
| 대안·가격 | 경쟁 가격표·약관·채널 단가·공시 | 지불의사·전환율 | 결제·유료 파일럿·LOI 조건, "반복 가능한 판매 과정을 선언할 만큼의 초기 매출"(Blank Validation 출구, 3~5 vs 300~500 은 채널 예시) | 의향 설문·시장 규모 문장·기능 목록·경쟁사보다 싼 가격만으로 수요 입증([Caldwell](https://www.ycombinator.com/library/7M-most-startups-are-undercharging)) |
| 채널·비용 | 광고 단가·견적·규제 비용 | 전환율·유지 | 코호트 잔존 | 첫 주 ROAS |
| 불공정 우위 | 특허·인허가 **존재** | 복제 불가능성 | 공개자료로 거의 안 닫힘 | 특허 = 해자 |
이번 주 손으로 할 일이 비면 아이디어가 아니라 메모다([PG, Do Things That Don't Scale](https://www.paulgraham.com/ds.html)).
제품 전 가설 칸 이름은 [NASA I-Corps 7영역](https://www.nasa.gov/sbir_sttr/icorps) 원문 그대로: Value Proposition · Customer/User-case and pain point · Demand Creation · Channel Development · Revenue Model · Partnership Strategy · Resource Requirement. 인터뷰 용량 참고치는 NSF 국가팀 7주 최소 100회·최소 주 15시간([NSF](https://www.nsf.gov/funding/initiatives/i-corps/information-accepted-national-teams)), NASA Phase I 50회 — 한국 과제의 합격선이 아니다.

## 4. 독자 C — 사업화 주관기관·사업개발: 경쟁사·후보기업 BM 을 공개자료로 해부 (인터뷰 불가가 기본값)
| 단계 | 작업 | 증거원 |
|---|---|---|
| C1 대상 고정 | `entity-identity.md` 선통과. 법인·브랜드·제품·지역 분리, 그룹사 다른 모델을 섞지 않는다 | 등기·공시·약관 E1 |
| C2 6요소 해부 | [BCG 2009](https://web-assets.bcg.com/img-src/BCG_Business_Model_Innovation_Dec_09_tcm9-121706.pdf): 누구의 어떤 니즈 · 오퍼링 · 수익 모델 / 가치사슬(내부 vs 외주) · 원가 · 조직. 칸마다 URL 또는 `미확인` | 공시·약관·가격 페이지 E1 / 조직 역량은 채용공고로 간접, 실제는 I |
| C3 정합 | [Deloitte 2024](https://www.deloitte.com/content/dam/assets-zone3/us/en/docs/services/consulting/2024/business-model-innovation-and-resiliency-pov.pdf) 3요소(가치제안·차별화 역량·수익화)가 서로 받치는지. 안 받치면 모순을 적고 결론 유보 | 양쪽 출처 있을 때만 E1 |
| C4 수익식 역산 | [Johnson HBR 2008](https://hbr.org/2008/12/reinventing-your-business-model) profit formula: 가격×수량·원가·마진·회전. **없는 변수는 `미확인`**, 업계 평균으로 메우지 않는다. 역산 결과는 `(분석)` | 공시 재무 E1 / 거래량 추정은 I |
| C5 과금별 공개 대리변수 | 구독: 가격 인상 이력·연간 청구·채용의 CS/세일즈 비율(NRR 은 보통 X) · 거래형: 약관 요율(GTV 는 X 일 수 있음) · 마켓: 양측 가입 문구(한쪽만이면 치킨에그 미해결) · 엔터프라이즈: contact-sales·고객 사례(YC 의 미국 대기업 기준 정의를 한국 중견에 억지 적용 금지) · 사용량: 단위가·원가 단서 · 상품: 판매가·입점 수수료 · 광고: 등록자 ≠ DAU · 하드테크: 논문·인허가·LOI 보도(없으면 `미확인(고객 관심)`) | 가격 페이지·약관 E1(열람일 필수) / 대리변수에서 끌어낸 지표 추론은 `(분석)` |
| C6 가장자리 모델 | 신규 진입자·비이용 대체재는 `competitive-positioning.md` §1 의 4유형 행(현상 유지·기존 방식·직접·간접)으로. "경쟁사 없음" 은 실사 실패 | 상대 가격·설명 E1 |
| C7 상업 준비 | [ARENA CRI](https://arena.gov.au/assets/2014/02/Commercial-Readiness-Index.pdf) 8지표(규제·이해관계자·기술 성과·비용·수익·공급망·시장 기회·회사 성숙)의 **증거 유무만**, 점수 없음, 재생에너지 지수임을 각주. 에너지 밖이면 KTH CRL·BRL 단계 이름(§2 A6). 클라우드·반복매출이면 [Bessemer 10 Laws](https://www.bvp.com/atlas/10-laws-of-cloud) Law 1~3, Law 5 의 5C(CAC 회수 SMB 6~18개월·엔터프라이즈 24~36, CLTV/CAC ≥3, 상위 엔터프라이즈 연 로고 이탈 <7%)와 Law 7(월 gross churn <1%) — 기간이 달라 합치지 않음, 소비자 앱이면 [Blomfield](https://www.ycombinator.com/library/KT-consumer-startup-metrics) 월 활성 성장 15% 좋음·10% 보통·5% 이하 부족, 유기 ≥50%, NPS +50 — 전부 질문 설계용, 한국 비상장사 기준 아님 | 고시·인증서 E1 |
| C8 미닫힘 목록 | 실제 마진·해지율·영업 생산성·전환 이유·내부 프로세스는 데이터룸 없이 X → 9부 앞머리 | — |
한국 상장사 공시는 [OpenDartReader](https://github.com/FinanceData/OpenDartReader) 로 받되 "사업의 내용"·매출 구성·고객 집중은 항목 API 에 없다 — 원문 문단을 접수번호와 함께 인용. 결과물은 회사 카드 1장: 고객·지불자·과금·가격 URL·매출 구성 인용·주요 의존·결측 목록·재열람 URL. 매수 의견·FTO 는 넣지 않는다.

## 5. 부록 — 분야 × 단위 × 매출 다리 함정 × 1차 출처 × 병목 질문 (상세 KPI·출처는 PRD §1.7 근거 파일)
| 분야 | 단위 | 매출 다리 함정 | 1차 출처 유형 | 병목 질문 |
|---|---|---|---|---|
| SaaS/구독 | 유료 고객·로고 | 한 달 총액×12 = ARR, 용역·구축 포함 ARR, NRR 만 제시(GRR 숨김) | DART·EDGAR 수익 인식 주석, 가격표, [Bessemer 벤치마크(2021, 질문 설계용)](https://www.bvp.com/atlas/scaling-to-100-million) | ARR 정의에서 용역 뺐나 · 로고/달러 해지 코호트 · CAC 에 할인·파트너·구현 포함 · 선결제·이연수익 vs 현금 · 리스트 가격 vs 실제 ACV |
| 플랫폼/마켓 | 성사된 거래 | GMV = 매출, 취소·세금·배송비 포함 GMV, 쿠폰 전 수수료 | 수수료표·약관, 공시 부문, [a16z 마켓 용어](https://a16z.com/the-marketplace-glossary/) | GMV 에 취소·환불·대납 할인 · 지역·시간대별 유동성 · 테이크는 프로모션·결제비 후 · 반복 쌍의 유출(멀티호밍) · 결제 흐름 안에 있나 |
| 제조/하드웨어 | 출하 양품 1개 | 시제품 단가 = 양산 단가, 수율 가정만 넣고 현재 수율 각주, 툴링·인증·운임 원가 제외 | 공급사 견적·BOM, 재고 주석, 현금흐름표, [a16z 공장 경제](https://a16z.com/a-primer-on-factory-economics-for-startups/) | BOM 이 견적/샘플/MOQ 중 뭔가 · 수율은 실적인가 목표인가 · 금형·인증·반품 충당 밖에 남았나 · CCC 며칠 · 고객·부품·공장 1곳 집중 |
| 바이오/제약 | 프로그램 1건 | 마일스톤 총액 = 자사 매출, 과제비 = 매출, 전체 평균 LOA 를 개별 자산에 곱함 | ClinicalTrials·MFDS·DART 제약바이오 기재사항, [BIO 성공률 2011-2020](https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf) | 등록부와 적응증·단계·평가변수 일치 · 성공확률이 그 적응증 분포 안인가 · 현재 매출이 선급/마일스톤/로열티/제품/용역 중 뭔가 · 런웨이가 다음 readout 까지 · 규제 경로·특허 만료·국가 R&D IP 귀속 |
| 핀테크 | 거래 또는 잔액 | TPV = 매출, 총수수료율만 제시(리워드·사기·네트워크비 전), 성장기 분모 확대로 손실률 착시 | DART·EDGAR 순이자·대손 주석, 카드사 인터체인지표, 한국은행 지급결제 통계, 금융위·금감원 인가 공고 | 단위가 거래/계좌/대출잔액 중 뭔가 · 수수료인가 이자인가(금리 100bp 민감도) · 연체 버킷·코호트 손실 · 어떤 인허가, 파트너 은행 바뀌면 남나 · 리워드·수수료 상한이 순테이크를 얼마나 깎나 |
| 커머스/D2C | 주문 1건 + 고객 1명 | 출고액 = 매출(반품·할인 전), 왕복 물류를 판관비로, 자연 유입 섞은 blended CAC | 가격·반품 약관, 입점 수수료표, KOSIS 온라인쇼핑, DART 반품충당부채, [NRF 반품률(미국, 질문 설계용)](https://nrf.com/media-center/press-releases/consumers-expected-to-return-nearly-850-billion-in-merchandise-in-2025) | 반품 창 전 매출 확정하나 · 주문 1건 공헌이익에 결제·포장·반품 운임·폐기 포함 · LTV 가 매출인가 공헌이익인가 · 채널별 수수료·반품 조건 · 광고비 급증 뒤 코호트 |
| 콘텐츠/미디어 | 유료 구독자 또는 노출 | 무료·체험·번들을 유료 구독자에, 조회수 → 광고 매출 환산, 히트 시즌 연환산 | 요금제·약관, 광고 상품 단가, KOCCA 콘텐츠산업통계, 상장 OTT·게임사 가입자·상각 주석 | 매출이 구독/광고/판권/라이브 중 · 해지가 구독자 기준인가 매출 기준인가 · 제작비·최소보증 상각 시점 · 광고 매출이 청구인가 추정인가 · 상위 1~5 작품 빠지면 |
| 딥테크/B2G | 마일스톤 + 양산 단위 | 과제비 = 반복매출, LOI·예산 요구 = 수주 잔고, 연구 시제 원가 = 납품 원가 | NTIS, 나라장터 낙찰 단가, KIPRIS, [NASA TRL](https://www.nasa.gov/directorates/somd/space-communications-navigation-program/technology-readiness-levels/), [DARPA Heilmeier 8문](https://www.darpa.mil/about/heilmeier-catechism) | 24개월 현금이 과제/용역/납품/라이선스 중 · TRL 증거가 논문/시제품/현장 시험/인증 중 · 경쟁 입찰인가 수의인가 혁신제품인가 · 양산 가정이 제조 행 질문으로 닫히나 · 국가 R&D IP·실시권 귀속 |
혼합형(하드웨어+구독 · 마켓+직매입 · SaaS+결제 · 바이오+CDMO · 콘텐츠+커머스 · 딥테크+양산): 최근 12개월 현금 매출 비중으로 주 모델을 정하고 **표를 두 장**(지금 버는 모델 / 아직 증명 안 된 모델)으로 나눈다. 합치면 좋은 쪽 지표만 남는다.

## 6. 금지 서술 (G3 직전 본문 grep 0건 · 허용 표현으로 치환)
| 금지 | 허용 |
|---|---|
| "경쟁사 없음" · "국내 유일" | "조사 범위(DB·기간·검색식) 내에서 확인된 바로는" + 대안 4유형 행 |
| GMV·TPV·결제액·거래액을 매출로 | "총거래액 X, 그중 플랫폼 매출 Y(순테이크 Z%)" |
| 과제비·용역비를 반복매출·ARR 로 | "과제 수입 X(종료일), 제품 매출 Y — 별도 행" |
| LOI·의향서·예산 요구를 수주로 | "비구속 LOI N건(조건), 체결 계약 M건" |
| TRL ≥ 6 을 상업 견인력으로 | "TRL n(증거: …), 고객 결제·파일럿은 미확인" |
| NRR 만·blended CAC 만으로 "건강" | "NRR X%, GRR Y%(총해지)" · "paid CAC X, blended CAC Y"([a16z](https://a16z.com/16-startup-metrics/)) |
| 시제품 마진을 양산 마진으로 | "시제 원가 X(수율 y%), 양산 원가는 견적·수율 실적 전 미확인" |
| 등록자·다운로드·조회수를 활성·매출로 | "유료 구독자 X / 활성 사용자 정의 … / 판매된 노출" |
| 전체 평균 성공률·업계 평균 마진을 개별 자산에 | "`(분석)` 같은 적응증·단계·규모의 분포(Fxxx) 참고, 개별 자산의 확률·마진은 `미확인`" |
| YC·Bessemer·NRF 수치를 한국 합격선으로 | "질문 설계용 기준점(출처·연도·표본)이며 국내 합격선 아님. 국내 값은 원문 (Fxxx) 이 있을 때만, 없으면 `미확인`" |
| Gassmann 패턴 억지 배정 | "관찰 가능한 과금 방식만 … 패턴 URL 과 안 맞는 이유 병기" |
grep 으로 바로 잡히는 문자열은 1행뿐이다. 나머지는 조사별로 `audit/intent-diff.md` 금지 목록에 패턴(예: `GMV.*매출`, `LOI.*수주`, `과제.*ARR`)으로 옮겨 [3] 뒤 원고 grep 0건(`reader-goal.md` 운용 규칙 2).

## 7. 빈 슬롯 (1·2차 조사가 못 연 것 — 닫히기 전까지 모듈에 넣지 않는다. 2차(2026-10-08, PRD §1.8)로 닫힌 것은 위 § 에 들어갔다)
Strategyzer 실험 43종의 이름·비용·시간·증거강도 표(비공개, Playbook 유료 — 공개 이름 10개만 예시 가능) · Running Lean 3판 본문 · Blank 3·4단계(Creation·Company Building) 출구 문장 · Jolly 1997·Quicklook 1998 · EU 번호형 Commercialisation Readiness Level(Innovation Radar 는 4분류일 뿐)·Innovate UK/UKRI 공식 MRL 번호표 · NFX·Point Nine "BM 실사 질문집"(**부재 확정**, 검색식 NFX 9·Point Nine 7) · YC 라이브 지원서 문항(로그인)·Khilnani 바이오 강의(**부재 확정**)·Startup School 가입 뒤 과제 · TIPS 운영사 추천 배점·붙임4 · 예비창업패키지 별첨1 수익모델 문항 · KIAT·STEPI·특허청 IP-R&D 의 사업화 단계 본문(PDF 텍스트 없음) · 실무가이드 기술역량 소항목 8 vs 9, 창업기업1/2 명칭 충돌(원문 충돌로 둔다) · McKinsey Global Payments 수치(검색 요약) · GitHub 한국어 저장소(`기술이전` 3건은 플랫폼 README·데모·포트폴리오, `기술사업화` 4건 중 교재 1, `수요기업`·`특허 출원인 매칭`·NTIS 는 **부재 확정**).
