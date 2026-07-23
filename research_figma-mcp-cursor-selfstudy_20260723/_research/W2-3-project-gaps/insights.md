# W2-3. 실습 프로젝트 3종 자료 갭 보강 조사

- 조사일: 2026-07-23
- axis: W2-3-project-gaps
- 프로토콜: WebSearch 탐색 → WebFetch 원문 직접 열람 후 fact 등재. 원문 미확인 주장 없음.

---

## Q1. 결제 포함 OTT/구독형 서비스 클론 튜토리얼 (Next.js + 토스페이먼츠/Stripe 정기결제, 2024~2026)

### 결론 (중요)
**"Next.js + 토스페이먼츠 + OTT 클론 + 정기결제"를 한 번에 만족하는 한국어 단일 튜토리얼은 2026-07-23 기준 검색으로 확인되지 않음.** 가장 근접한 자료는 아래처럼 (a) 토스페이먼츠 공식 구독결제 백엔드 로직 가이드(단, Express/EJS 예시이며 2023년 자료)와 (b) Next.js+Toss 결제위젯 연동 예시(단, 2024년 자료지만 단건결제만 다룸)를 **조합**하는 방식이다. 영어 자료는 Next.js+Stripe 조합으로 완성도 높은 2025~2026 가이드가 존재한다.

### Fact 1. 토스페이먼츠 공식 구독 결제 구현 가이드(빌링키 발급 + 스케줄링) — Next.js 아님, 2023년 자료
- statement: 토스페이먼츠 개발자센터 공식 블로그의 "구독 결제 서비스 구현하기 (1)(2)"는 빌링키 발급→DB 관리→스케줄링(cron)으로 이어지는 구독 결제 로직을 다루지만, 예시 코드는 Next.js가 아닌 Express+EJS 기반이며 발행일은 2023년으로 요청된 2024~2026 범위 밖이다.
- risk: normal
- evidence:
  - url: https://docs.tosspayments.com/blog/subscription-service-1
    title: 구독 결제 서비스 구현하기 (1) 빌링키 발급 | 토스페이먼츠 개발자센터
    quote: "2023년 9월 6일" / "빌링키를 발급받은 뒤 빌링키와 고객 정보, 구독 정보를 데이터베이스에서 관리"
    locator: 본문 상단 작성일 표기 + "빌링키 발급" 섹션
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: 토스페이먼츠
  - url: https://docs.tosspayments.com/blog/subscription-service-2
    title: 구독 결제 서비스 구현하기 (2) 스케줄링 | 토스페이먼츠 개발자센터
    quote: "하나의 플랜을 가지고 정기결제를 내는 로직만 구현" / node-cron 기반 "'0 0 1 * *'" 예시로 "월간 플랜을 매달 1일에 실행"
    locator: "스케줄링" 섹션
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: 토스페이먼츠

### Fact 2. Next.js + 토스페이먼츠 결제위젯 연동 예시(2024) — 정기결제 아닌 단건결제만
- statement: velog "토스 페이먼츠 API를 이용한 결제 위젯 구현하기 (Feat. NextJS, TypeScript)"(2024-01-11)는 Next.js 환경에서 토스페이먼츠 결제위젯 SDK로 `requestPayment()` 단건결제를 구현하는 예시이며, 정기결제/구독 로직은 다루지 않는다.
- risk: normal
- evidence:
  - url: https://velog.io/@sanghyeon/토스-페이먼츠-API를-이용한-결제-위젯-구현하기-Feat.-NextJS-TypeScript
    title: 토스 페이먼츠 API를 이용한 결제 위젯 구현하기 (Feat. NextJS, TypeScript)
    quote: "2024년 1월 11일" / requestPayment() 기반 단건결제 승인 플로우, 정기결제 언급 없음
    locator: 본문 작성일 및 코드 예제
    observed_at: 2026-07-23
    source_role: 재인용(개인 블로그, 토스 공식 SDK 사용법 정리)
    publisher: velog (@sanghyeon)

### Fact 3. Vercel 공식 Next.js+Stripe 구독 SaaS 템플릿 — 구모델 아카이브, 신모델로 대체(영어)
- statement: Vercel 공식 Next.js+Stripe 구독 결제 템플릿(`vercel/nextjs-subscription-payments`)은 2025-01-23 아카이브(보관) 처리되었고, 후속 템플릿 `nextjs/saas-starter`가 Stripe Checkout/Customer Portal 기반 구독 관리 기능을 이어받아 현재도 유지되고 있다.
- risk: normal
- evidence:
  - url: https://github.com/vercel/nextjs-subscription-payments
    title: vercel/nextjs-subscription-payments
    quote: "This repo has been sunset and replaced by a new template: https://github.com/nextjs/saas-starter"
    locator: README 상단 공지
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: Vercel (GitHub)
  - url: https://github.com/nextjs/saas-starter
    title: nextjs/saas-starter
    quote: "Subscription management with Stripe Customer Portal" / "Pricing page (`/pricing`) which connects to Stripe Checkout"
    locator: README 기능 목록
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: Vercel/Next.js (GitHub)

### Fact 4. Next.js 15 + Stripe 정기결제 완전 가이드(영어, 2025~2026)
- statement: pedroalonso.net의 "Stripe + Next.js 15: The Complete 2025 Guide"는 Stripe Checkout `mode: 'subscription'`, 웹훅, 고객 포털을 포함한 Next.js 구독 결제 전체 플로우를 다루며 2025-10-12 게시, 2026-06-07 업데이트된 최신 자료다.
- risk: normal
- evidence:
  - url: https://www.pedroalonso.net/blog/stripe-nextjs-complete-guide-2025/
    title: Stripe + Next.js 15: The Complete 2025 Guide
    quote: "October 12, 2025 • Updated: June 7, 2026" / "One-time payments are great, but recurring revenue is what scales a SaaS" / "`mode: 'subscription'` — tells Stripe this is recurring"
    locator: 게시일 메타데이터 + "Part 2: Subscriptions" 섹션
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: Pedro Alonso (개인 기술 블로그)

---

## Q2. Expo Router + Supabase Auth 로그인 포함 튜토리얼 (2025~2026)

### Fact 5. Supabase 공식 Expo 소셜 로그인 퀵스타트 — Expo Router 보호 라우트 + Apple/Google 로그인 확인
- statement: Supabase 공식 문서 "Build a Social Auth App with Expo React Native"는 Expo Router의 protected routes로 네비게이션을 보호하고, Supabase Auth로 Apple/Google 소셜 로그인을 구현하는 방법을 원문에서 명시적으로 다룬다.
- risk: normal
- evidence:
  - url: https://supabase.com/docs/guides/auth/quickstarts/with-expo-react-native-social-auth
    title: Build a Social Auth App with Expo React Native | Supabase Docs
    quote: "Using Expo Router's protected routes, you can secure navigation" / "Supabase Auth enables users to log in through social authentication providers (Apple and Google)"
    locator: 가이드 개요 섹션
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: Supabase (공식 문서)

### Fact 6. 커뮤니티 Expo Router + Supabase Auth 가이드(2025-08-09 최종 활동) — 이메일 회원가입/로그인 구현 확인
- statement: GitHub Gist "Expo Router + Supabase Auth + NativeWind Tutorial"(최종 활동 2025-08-09)은 `supabase.auth.signUp()`/`signInWithPassword()`로 회원가입·로그인 페이지를 만들고, 세션 유무에 따라 보호된 라우트로 리다이렉트하는 로그인 플로우를 원문에서 구체적으로 다룬다.
- risk: normal
- evidence:
  - url: https://gist.github.com/TortoiseWolfe/119b16a4c27c559ede0ddec71a9f7786
    title: Expo Router + Supabase Auth + NativeWind Tutorial
    quote: "Last active August 9, 2025" / "Create Sign-Up & Login Pages" / "if (!data.session) { router.replace(\"/(auth)/signIn\"); }"
    locator: 문서 상단 활동일 + "7~8. Sign-Up & Login Pages" 섹션
    observed_at: 2026-07-23
    source_role: 재인용(커뮤니티 작성 튜토리얼)
    publisher: GitHub Gist (TortoiseWolfe)

참고: Supabase 공식 "Build a User Management App with Expo React Native"(`/docs/guides/getting-started/tutorials/with-expo-react-native`)는 로그인(이메일 인증)은 포함하지만 **Expo Router를 사용하지 않음**(기본 `create-expo-app` + 일반 네비게이션)을 원문 확인함 — Q2 채택 기준(Expo Router 필수) 미충족으로 fact에서 제외. 공식 Expo 문서(`docs.expo.dev/guides/using-supabase/`)도 Supabase Auth 소셜 로그인은 언급하나 Expo Router 통합은 다루지 않아 제외.

---

## Q3. Next.js → Vercel 배포 + Supabase 연결 공식 가이드 (최단 경로)

### Fact 7. Vercel 공식 Next.js+Supabase 템플릿 — Deploy 버튼 원클릭
- statement: Vercel 공식 템플릿 페이지는 "Deploy to Vercel" 버튼 클릭 한 번으로 Supabase 계정/프로젝트 생성을 안내하고 Supabase Integration 설치 후 관련 환경변수를 자동으로 프로젝트에 할당해, 비개발자가 별도 수동 설정 없이 배포까지 도달하는 최단 경로를 제공한다.
- risk: normal
- evidence:
  - url: https://vercel.com/templates/next.js/supabase
    title: Supabase & Next.js App Router Starter Template for Auth - Vercel
    quote: "Vercel deployment will guide you through creating a Supabase account and project. After installation of the Supabase integration, all relevant environment variables will be assigned to the project so the deployment is fully functioning."
    locator: "Deploy to Vercel" 섹션
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: Vercel (공식)

### Fact 8. Supabase 공식 Vercel Marketplace 연동 문서 — 현재 "공개 알파" 상태, 일부 섹션 미완성
- statement: Supabase 공식 문서 "Vercel Marketplace"는 Next.js+Supabase 배포 시 POSTGRES_URL, SUPABASE_URL 등 환경변수 자동 동기화를 설명하지만, Marketplace를 통한 구체적 설치 단계 섹션은 "Details coming soon.."으로 아직 미완성 상태이며 템플릿 기반 배포(Fact 7)가 현재 권장 경로로 제시된다.
- risk: normal
- evidence:
  - url: https://supabase.com/docs/guides/integrations/vercel-marketplace
    title: Vercel Marketplace | Supabase Docs
    quote: "Details coming soon.."
    locator: "Installing via the Vercel Marketplace" 섹션
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: Supabase (공식 문서)

---

## Q4. Supabase 편의 기능 현재 상태

### Fact 9. @supabase/auth-ui-react — GitHub 저장소 아카이브(2025-10-23), 유지보수 중단 공지(2024-02-07)
- statement: `@supabase/auth-ui-react`(로그인 화면 기성 컴포넌트)를 담은 `supabase-community/auth-ui` 저장소는 2025-10-23 소유자에 의해 아카이브(read-only)되었으며, README에는 2024-02-07부로 Supabase 팀이 더 이상 유지보수하지 않는다는 공지가 있다. npm 패키지 자체가 npm 상에서 공식적으로 "deprecated" 태그가 붙은 것은 아니지만 사실상 유지보수 중단 상태다.
- risk: high
- evidence:
  - url: https://github.com/supabase-community/auth-ui
    title: supabase-community/auth-ui
    quote: "This repository was archived by the owner on Oct 23, 2025. It is now read-only." / "As of 7th Feb 2024, this repository is no longer maintained by the Supabase Team."
    locator: 저장소 상단 Archived 배너 + README 공지 섹션
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: Supabase Community (GitHub)
  - url: https://registry.npmjs.org/@supabase/auth-ui-react
    title: "@supabase/auth-ui-react" npm registry metadata
    quote: "dist-tags" 최신 버전 "0.4.7"
    locator: registry.npmjs.org JSON 응답 dist-tags 필드
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: npm registry
- counter: "supabase auth-ui-react still works 2026 alternative maintained fork" 반박 검색 결과, 유지보수 중인 포크나 대체 공식 패키지는 확인되지 않았고, Supabase 팀은 대안으로 Auth Helpers/커스텀 UI 구현을 권고하는 정황만 확인됨(별도 활성 포크 없음).

### Fact 10. Supabase Storage Quickstart — 현재 활성 공식 문서, deprecated 아님
- statement: Supabase 공식 "Storage Quickstart" 문서는 대시보드/SQL/JS 클라이언트로 버킷 생성 및 파일 업로드하는 방법을 현재도 안내하는 활성 문서이며, deprecated 표시나 경고 문구는 확인되지 않는다.
- risk: normal
- evidence:
  - url: https://supabase.com/docs/guides/storage/quickstart
    title: Storage Quickstart | Supabase Docs
    quote: "insert into storage.buckets (id, name) values ('avatars', 'avatars');" / "supabase.storage.from('avatars').upload('public/avatar1.png', avatarFile)"
    locator: "Create a bucket" / "Upload a file" 섹션
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: Supabase (공식 문서)

---

## Q5. 한국 PIPC/KISA의 웹 크롤링·스크레이핑 관련 공식 지침

### Fact 11. PIPC 안내서에 "공개된 개인정보"의 웹 크롤링/스크레이핑 수집을 명시적으로 다룸(2024-07-19, AI 맥락 한정)
- statement: 개인정보보호위원회가 2024-07-19 공개한 「인공지능(AI) 개발·서비스를 위한 공개된 개인정보 처리 안내서」는 위키백과·블로그·커먼크롤 등 "웹사이트에 공개된 데이터"를 대규모로 수집(웹 스크래핑)하는 방식을 AI 학습의 현실적 데이터 수집 방식으로 인정하고, 개인정보 보호법 제15조 제1항 제6호(정당한 이익)를 적법 근거로 제시한다. 단, 이는 **AI 개발·서비스 맥락에 한정된 안내서**이며, 전자상거래 가격수집·콘텐츠 스크레이핑 등 일반 목적의 독립된 "웹크롤링/스크레이핑 가이드라인"은 아니다.
- risk: normal
- evidence:
  - url: https://www.pipc.go.kr/np/cop/bbs/selectBoardArticle.do?bbsId=BS217&mCode=D010030000&nttId=10375
    title: 인공지능(AI) 개발·서비스를 위한 공개된 개인정보 처리 안내서
    quote: "주로 위키백과, 블로그, 커먼 크롤 등 다양한 웹사이트에 공개된 데이터가 학습에 이용되고 있습니다." / "공개된 개인정보는 굉장히 많은 대규모 웹 스크래핑을 전제로 하기 때문에"
    locator: 안내서 본문 및 Q&A 부분
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: 개인정보보호위원회

### Fact 12. 일반 목적의 독립된 "웹크롤링/스크레이핑" 전용 가이드라인은 PIPC/KISA 어디에서도 확인되지 않음 — 없음 확인
- statement: 개인정보보호위원회 공식 안내서 게시판(bbsId=BS217) 목록 및 KISA 관련 검색 결과 어디에서도 "웹크롤링" 또는 "스크래핑"을 표제로 한 별도의 종합 가이드라인·해설서는 확인되지 않았다. Fact 11의 AI 안내서를 제외하면, 크롤링의 법적 허용 기준은 현재 공식 지침이 아닌 법무법인 등 3자 해설(예: 로펌 뉴스레터)에 의존하고 있는 상태다.
- risk: normal
- evidence:
  - url: https://www.pipc.go.kr/np/cop/bbs/selectBoardList.do?bbsId=BS217&mCode=D010030000
    title: 안내서 | 개인정보보호위원회
    quote: "안내서들은 개인정보 전송요구권, 보건의료데이터 활용, 개인정보 처리방침, 가명정보 처리, 생성형 인공지능(AI) 개발·활용 등을 다루고 있으며, 웹 데이터 수집 기법에 관한 안내서는 목록에 포함되어 있지 않습니다."
    locator: 안내서 게시판 목록 전체
    observed_at: 2026-07-23
    source_role: 원출처
    publisher: 개인정보보호위원회

---

## dead_ends
- "Next.js + 토스페이먼츠" 순정 조합의 OTT/구독 클론 튜토리얼(한국어, 2024~2026)은 검색으로 확인되지 않음. 실무에서는 공식 구독결제 백엔드 가이드(Express 예시, 2023)와 Next.js 결제위젯 연동 예시(2024, 단건결제)를 조합해서 쓰는 것이 현실적 경로로 보임.
- KISA(한국인터넷진흥원)의 전용 웹크롤링/스크레이핑 가이드라인은 검색으로 확인되지 않음.
- 인프런/노마드코더 등 국내 강의 플랫폼에서 "Next.js + 토스페이먼츠 정기결제 OTT 클론"을 표제로 한 강의는 검색으로 확인되지 않음(강의 상세 페이지 저작권 문제로 직접 열람도 지양).

## failed_urls
- https://www.npmjs.com/package/@supabase/auth-ui-react (HTTP 403 Forbidden — registry.npmjs.org API로 대체 확인)
- https://blog.kweiza.com/35 (SSL 인증서 만료 오류로 열람 실패 — PortOne V2+Next.js+정기결제 예시로 추정되나 미확인)
