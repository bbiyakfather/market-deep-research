# A5-tosspayments 리서치 raw 기록

조사일: 2026-07-23
조사원: A5 (토스페이먼츠 결제위젯 연동 학습 경로)

## 방문 URL 목록 (WebFetch로 원문 확인 성공)

1. https://docs.tosspayments.com/guides/v2/get-started — "시작하기". 문서 구조(시작하기→환경설정하기→결제이해하기), 결제서비스 목록(일반결제/브랜드페이/자동결제/해외결제), 업종 제한 안내, GitHub 코드샘플·실시간 문의·llms.txt 링크 확인.
2. https://docs.tosspayments.com/guides/v2/payment-widget — "결제위젯 이해하기". 결제위젯 정의, 주문서형/결제창형 2가지 연동방식, 3단계 연동절차(어드민설정→variantKey확인→연동), 구매자 결제시간 약 70% 단축 문구 확인.
3. https://docs.tosspayments.com/resources/faq — FAQ. 간편결제별 테스트키 가능여부(토스페이·네이버페이·애플페이·삼성페이·SSG페이·엘페이·핀페이는 개발연동체험상점/MID 테스트키로 가능, 페이코는 라이브키 필수), 가상계좌 테스트환경 "X" 접두사, 입금취소 이벤트 웹훅 안내.
4. https://docs.tosspayments.com/blog/how-to-test-toss-payments — "회원가입, 사업자번호 없이 결제 테스트하기" (공식블로그, risk:high 핵심소스). 1단계 문서용 테스트키(가입불필요, API로그/웹훅/가상계좌 불가) vs 2단계 개발연동체험상점(이메일·전화번호 가입만, API로그/웹훅/가상계좌 가능) 2단계 구조 확인. 카카오페이 불가, 네이버페이 포인트/계좌결제 일부 제한, 영수증 실데이터 미생성 등.
5. https://docs.tosspayments.com/guides/v2/get-started/environment — "환경 설정하기". 테스트/라이브 환경 차이 상세: 카드 실승인 안됨, 카카오페이는 계약후 MID 테스트키만 가능, 페이코는 라이브키 필수, 가상계좌 "X" 접두사, 자동결제는 카드 BIN 6자리만 유효해도 등록됨, 계좌이체는 가상값으로 테스트, **정산기록은 라이브 환경에서만 조회 가능**, ARS결제·휴대폰본인인증·지급대행KYC는 테스트환경 미제공, API 요청 분당100건 제한, 지원 브라우저 목록.
6. https://docs.tosspayments.com/guides/v2/billing — "자동결제(빌링) 이해하기". 카드/계좌이체 지원, 정기배송·음악스트리밍 등 구독형 서비스용, **"리스크 검토 및 추가 계약 후 사용 가능"**, "정기 구독형 서비스가 아니면 정책적으로 사용 제한", 연동 4단계(SDK로 정보수집+본인인증→빌링키발급→빌링키-구매자ID매핑저장→결제주기마다 자동결제승인 API 호출), 스케줄링 기능 자체 미제공(직접구현 필요).
7. https://github.com/tosspayments/payment-widget-sample — "토스페이먼츠 SDK v1 샘플 프로젝트" (구 tosspayments-sample-v1). README에 "더 편리하고 매끄러운 결제 연동 경험을 위해서는 SDK Version 2를 사용하세요" 안내. /payment-widget, /brandpay, /payment 폴더. React/Next.js 명시 언급 없음(HTML/ASP/CSS 위주). → v1이므로 최신 학습에는 주의 필요.
8. https://github.com/tosspayments/tosspayments-sample — "토스페이먼츠 결제연동 샘플 프로젝트". Express+React, Express+Vue, Express+JavaScript, PHP+JS, ASP+JS, JSP+JS, Spring+JS, Django+JS 등 프레임워크별 샘플 폴더 존재 확인(상세 폴더별 코드는 재열람 필요).
9. https://github.com/tosspayments/payment-samples — "토스페이먼츠 결제 API 샘플 코드". /payment-cancel-api, /payment-inquiry-api, /payment-keyin-api, /payment-virtualaccount-api 등 서버사이드 API 샘플 위주. Classic ASP 62.4%, Python 9.3% 등 — React/Next.js 결제위젯 학습 목적과는 결이 다름 (dead end로 별도 기록).
10. https://www.tosspayments.com/blog/articles/paytech-4 — "React로 결제 페이지 개발하기 (ft. 결제위젯)" 공식블로그(토스페이먼츠 작성, 2023.03.06). Vite React 프로젝트 생성→react-router-dom→`npm install @tosspayments/payment-widget-sdk`→nanoid 순서. `loadPaymentWidget`, `renderPaymentMethods`, `requestPayment` 코드 예시 확인. **주의: v1 패키지(@tosspayments/payment-widget-sdk) 기준, 2023년 글이라 2025-2026 최신 v2 SDK와 다를 수 있음.**
11. https://docs.tosspayments.com/blog/react-use-effect — "결제위젯으로 React의 useEffect 사용해보기" 공식 개발자센터 블로그, 발행일 2024년 10월 31일. useEffect 개념 설명 위주(구체 코드 스니펫은 페이지 내 별도 임베드로 텍스트 추출 안됨). 실제 코드 샘플은 github.com/tosspayments (sample 검색)로 안내.
12. https://docs.tosspayments.com/sdk/v2/js — "토스페이먼츠 JavaScript SDK". `TossPayments(clientKey)`, `tossPayments.widgets(params)`, `widgets.setAmount`, `widgets.requestPayment`, `widgets.renderPaymentMethods`, `widgets.renderPaymentWindow`, `widgets.renderAgreement` 함수 확인. npm 패키지명은 이 페이지에서 명시적으로 확인 안됨(스크립트태그 방식 위주 서술). React/Vue SPA에서 `payment.destroy()` 권장 언급으로 React 호환 시사.
13. https://docs.tosspayments.com/resources/glossary/dev-center — "개발자센터" 용어설명. 문서, API키, 테스트내역, 웹훅등록 등을 개발자센터가 제공한다는 요약 확인(2번 검색결과 요약에 반영).

## 열람 실패

- https://www.npmjs.com/package/@tosspayments/tosspayments-sdk — HTTP 403 Forbidden. v2 SDK npm 패키지명(`@tosspayments/tosspayments-sdk`)은 WebSearch 스니펫으로만 확인, WebFetch 원문 확인 실패 → fact에 미등재, failed_urls 기록.
- https://docs.tosspayments.com/guides/payment-widget/integration — WebFetch시 네비게이션/사이드바만 추출되고 본문(코드 예시)이 렌더링 안됨(SPA 특성으로 추정). 재시도(다른 프롬프트)도 동일. → fact 미사용, 대신 v2/payment-widget(개요) + v2/get-started/environment + 공식블로그 paytech-4 로 대체.
- https://docs.tosspayments.com/guides/v2/payment-widget/integration — 위와 동일 증상(사이드바만 추출, "주문서형 연동하기" 본문 미추출).
- https://github.com/tosspayments/browser-sdk — README 본문 미추출(메타데이터만: star 123, v1.3.1 릴리즈 2021.10.28 표시 — 이 값은 오래된 릴리즈 태그로 보이며 실제 v2 SDK와 별개 저장소일 가능성, 확인 안됨 → 사용 안함).

## YouTube 검색 스니펫만 확보 (본문 미열람, resources에만 등재, fact 금지)

- "NextJs 결제연동하기 (feat. Toss/토스페이먼츠)" — https://www.youtube.com/watch?v=lpfO2mebYQk — Next.js 특정, 이 학습경로에 가장 적합해 보임. locator: search-snippet.
- "토스페이먼츠 | 5분 만에 결제 연동하기" — https://www.youtube.com/watch?v=HtwLMwzTG5c — 검색요약상 2023.09 무렵, JavaScript+Node 결제위젯 가이드로 추정. locator: search-snippet.
- "[CCOMMIT] 경력/비전공자 토스페이먼츠 결제 API 연동" — https://www.youtube.com/watch?v=5DiSLv-n6l0 — 비전공자 타깃이라는 제목이 이 조사 대상 학습자(기획자/디자이너)와 부합. locator: search-snippet.
- "1강, 토스페이먼츠 위젯 활용" / "2강, 토스페이먼츠 연동 샘플" — https://www.youtube.com/watch?v=BYYXMKSYvP0 , https://www.youtube.com/watch?v=KfKDiGJBk6I — 시리즈물로 추정(2024.09 무렵), 실제 채널·최신성 미검증. locator: search-snippet.

## 반박검색(counter) 기록

- Q2(risk high, 사업자등록 없이 테스트범위): "토스페이먼츠 테스트 키 사업자 등록 없이 테스트 결제 발급" 검색 → docs.tosspayments.com/blog/how-to-test-toss-payments 결과와 재검색 결과가 서로 모순 없이 일치(문서용 테스트키 vs 개발연동체험상점 2단계 구조, 가입만으로 사업자등록 불필요 확인). 상충 없음.
- Q4(risk high, 자동결제 계약 필요 여부): "토스페이먼츠 자동결제 빌링 계약 없이 테스트 가능 여부" 재검색 → "실제 운영은 계약 필요, 테스트키로는 계약 전에도 빌링키발급~결제승인 전 과정 검증 가능, BIN 6자리 유효성 테스트 규칙"이 environment 페이지 내용과 일치. 상충 없음.

## 메모 (팀리드 참고)

- 이 학습경로의 핵심 리스크는 "v1 vs v2 SDK 패키지 혼동"이다. 공식 GitHub v1 샘플(payment-widget-sample)조차 README에서 v2 사용을 권장하지만, 검색 상위에 노출되는 한국어 튜토리얼(공식 블로그 paytech-4 포함, velog 다수)은 2023년 기준 v1 패키지(@tosspayments/payment-widget-sdk)를 사용 중이라 2025-2026 학습자가 최신 문서(v2, @tosspayments/tosspayments-sdk 추정)와 혼동할 가능성이 높음. 팀리드는 노션 가이드에 "v1/v2 SDK 이름이 다르니 문서 상단 버전 확인 필수"라는 경고 문구 삽입을 고려할 것.
- 정기결제(빌링)는 "리스크 검토+추가 계약" 필요가 정책적으로 명시되어 있어, OTT 구독 재현 과제는 "테스트 키 범위 내 빌링키 발급~승인 흐름만 실습, 실제 서비스 전환 시 별도 계약 필요"로 학습자에게 기대치를 명확히 안내해야 함.
- payment-samples(github) 저장소는 이 축의 목적(React/Next.js 결제위젯)과 안 맞아 dead end로 분류.
