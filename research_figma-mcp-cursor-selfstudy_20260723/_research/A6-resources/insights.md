# A6-resources 조사 raw 기록 (observed_at 2026-07-23)

## 조사 범위
FastCampus "Figma MCP, Cursor로 만드는 웹/앱 서비스" 3개 프로젝트(에어비앤비 클론/디즈니+·넷플릭스 OTT 클론(결제)/넷플릭스 모바일 앱(로그인)) 대체 학습경로용 공개 자료 큐레이션.
FastCampus 강의 페이지(fastcampus.co.kr, media.fastcampus.co.kr)는 프로토콜상 방문/인용 금지 — 검색 결과에 노출되어도 의도적으로 WebFetch하지 않았음.

## WebFetch 성공 (원문 확인 완료 → fact 등재)
- https://nomadcoders.co/airbnb-clone — 에어비앤비 클론코딩, Django/DRF+ReactJS/Chakra UI, 유료, 191개 영상 30h+, 중급
- https://nomadcoders.co/carrot-market — 캐럿마켓(당근마켓) 클론, Next.js14+TS+Prisma+Tailwind+Zod+Vercel+Twilio+Supabase+Cloudflare, 유료(6개월 할부 월6만원=정가 36만원), 중급, 바닐라JS+React 선수지식 요구
- https://nomadcoders.co/nextjs-for-beginners — Next.js 무료 입문강의, App Router/Server Components/Dynamic Pages, 4시간 32영상, 1.6만명 수강
- https://nomadcoders.co/javascript-for-beginners — JS 무료강의, 8시간 60영상, "초급 기본. HTML.CSS.JS 이해도 필요" 원문 그대로
- https://www.inflearn.com/course/%EC%9A%94%EC%A6%98%EC%97%94-supabase-%EB%8C%80%EC%84%B8%EC%A7%80-nextjs-%ED%81%B4%EB%A1%A0%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8 — 로펀 강사, Next.js14+Supabase, Dropbox/Netflix/Instagram 3클론, 유료, "난이도 초급"(단 상태관리/API 기초 권장). 결제 기능 언급 없음 → 프로젝트2 "결제 포함" 요건 완전충족 아님, 캐비어트로 기록.
- https://www.inflearn.com/course/%EC%9B%B9%EA%B0%9C%EB%B0%9C-%EA%B8%B0%EC%B4%88-html-css — 무료, 2h34m 11강, "초보자분들 또한 쉽게 배울 수 있도록"
- https://www.notjust.dev/blog/netflix-clone — RN+Expo+Expo Router+TS+Expo Video, 2025-05-31 게시, 튜토리얼 자체 무료(심화 자료는 유료), 로그인/인증 기능 언급 없음
- https://github.com/Lordhacker756/Netflix — React Native(Expo 명시 없음). 저장소 설명(About)엔 "user authentication allows users to sign up, sign in..." 있으나 README 본문엔 인증 구현 설명 없음 → 설명-실제 불일치, 신뢰도 낮음으로 판단
- https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server — 공식. Cursor 명령 팔레트 `/add-plugin figma` → 설정에서 Connect. 원격서버가 대다수 사용자에게 적합("The remote Figma MCP server is the version most users need and has the broadest set of features.")
- https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/ — 공식 개발자문서, 동일 절차(플러그인 설치 권장, 딥링크로 MCP Install→Connect)
- https://docs.tosspayments.com/guides/payment-widget/integration — 공식, 이해하기→어드민사용하기→연동하기→배포체크리스트 4단계. 이 발췌 콘텐츠엔 프레임워크별 지원목록 없음(SDK 레퍼런스는 JS SDK로 추정)
- https://github.com/tosspayments/tosspayments-sample — 공식 샘플저장소, README에 Express+React/Vue/JS, PHP+JS, ASP+JS, JSP+JS, Spring+JS, Django+JS만 존재. **Next.js 샘플 없음** 확인.
- https://brunch.co.kr/@zitopd/8 — "비개발자를 위한 Cursor-figma-MCP 사용법", 2025-03-24, 프로덕트 디자이너 대상. "많은 프로덕트 디자이너들이 플러그인 설치 과정에서 어려움을 겪고 있다는 피드백을 받았습니다."
- https://www.mobiinside.co.kr/2025/06/25/mcp/ — 저자 유훈식(AI-Powered Design Lab), 2025-06-25. MCP="AI용 USB-C 단자" 비유, Figma디자인→React코드 변환 "약 10분 소요"
- https://www.builder.io/blog/figma-to-cursor-for-designers — 저자 Matt Abrams, 2026-03-07(가장 최신). 5단계 워크플로: 연결/프롬프트 → 제약조건설정(Keep logic intact) → 시각편집(Element Selector) → diff검토 → QA체크리스트
- https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=261986672 — 책 『클론 코딩으로 시작하는 Next.js』, 이창주, 비제이퍼블릭, **2021-01-29 출간** → Pages Router 시대로 추정, 2025-2026 최신성 요건 미충족 → dead_end 처리, resources 미등재

## WebFetch 실패 (403 등) → failed_urls, 내용 추측 금지
- https://opentutorials.org/course/3084 (생활코딩 WEB1) — 403
- https://opentutorials.org/course/3083 (생활코딩 WEB) — 403
- https://wikidocs.net/160511 — 403
- https://www.figma.com/ko-kr/community/development/code-generators — 403
- https://www.udemy.com/course/mastering-nextjsbuild-an-airbnb-clone-from-scratch-2024/ — 403 (WebSearch 스니펫에서만 "Next.js 14+, TypeScript, Clerk Auth, Prisma, Supabase, Tailwind, Shadcn-ui, updated Jan 2025" 확인, 원문 미확인이므로 fact 미등재, resources에는 스니펫 기준임을 명시하여 등재)
- https://blog.toktokhan.dev/... → medium.com 리다이렉트, 후속 fetch 미수행(시간상 생략)

## 반박검색(counter) 수행 — risk:high 항목
- "노마드코더 캐럿마켓 클론코딩 가격" 재검색 → "정가 36만원, 예약구매 특가 28만원 사례 있음" → 최초 관측치(6개월 할부 월6만원=36만원)와 정합. counter 결과 일치로 확인.

## YouTube (본문 열람 불가/미시도, search-snippet만 → fact 금지, resources 등재 시 locator="search-snippet")
- "피그마로 웹사이트 10초 안에 베껴오기" (youtube.com/watch?v=MAdq_B4_4_w)
- "Cursor AI로 코딩하기 (코딩 몰라도 됨..)" (youtube.com/watch?v=ru8IpLK9NyY)
- "Design to Code with Figma MCP and Cursor" (youtube.com/watch?v=H6FL3LU-cck, 영어)
- "Figma MCP + Cursor: The New AI Design System Workflow" (youtube.com/watch?v=09VgyFFLrOw, 영어)

## 조사 중 못 찾은 것(gap, expand_leads로 전달)
- 프로젝트1: **Next.js 기반 + 한국어 + 2025~2026** 조건을 모두 만족하는 "에어비앤비 클론" 전용 튜토리얼은 끝내 확인하지 못함. 가장 근접한 것은 노마드코더 "캐럿마켓"(당근마켓, Next.js14, 국내 마켓플레이스 패턴)과 노마드코더 "에어비앤비 클론코딩"(정확히 에어비앤비지만 Django+React, 최신성 불명확)이며 둘 다 스택 또는 소재 중 하나가 어긋남.
- 프로젝트2: "결제 기능까지 포함"하는 Next.js OTT 클론 한국어 자료는 확정적으로 찾지 못함. 로펀 인프런 강의(Next.js14+Supabase, 넷플릭스 포함 3클론)가 가장 근접하나 결제 기능 언급이 원문에 없어 별도로 토스페이먼츠 공식 문서를 조합 학습하는 경로를 제안함(추론).
- 프로젝트3: React Native/Expo 넷플릭스 클론 중 "로그인 포함"이 원문으로 확실히 검증된 자료를 찾지 못함(notjust.dev는 언급 없음, GitHub 저장소는 설명-실제 불일치). Expo 공식 Authentication 문서를 별도 결합 학습하는 경로를 제안함(추론).
