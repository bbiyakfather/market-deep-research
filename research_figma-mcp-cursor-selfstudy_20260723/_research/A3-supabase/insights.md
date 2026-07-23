# A3-supabase 조사 raw 기록 (observed_at 2026-07-23)

## 방문/열람 URL (WebFetch 성공)

1. https://supabase.com/docs/guides/getting-started
   - 실제 절차 없음. 프레임워크별 quickstart 링크 모음(허브)일 뿐. fact 소스로 부적합 → 사용 안 함.
2. https://supabase.com/docs/guides/database/overview
   - "Tables and data: Create tables and relationships, and edit rows from the Dashboard." / "Table Editor" 언급만. 상세 절차는 별도 페이지(tables) 참조.
3. https://supabase.com/docs/guides/database/tables ← **핵심 소스 (Q1)**
   - 섹션 "Creating tables": Table Editor 페이지 이동 → New Table → 이름 지정(todos) → Save → New Column → 이름/타입(task, text) → Save.
   - "You must define the data type of each column when it is created" / "You can add and remove columns at any time after creating a table"
4. https://supabase.com/docs/guides/getting-started/quickstarts/nextjs ← **핵심 소스 (Q1 전체 흐름)**
   - Create a Supabase project → Set up your database(instruments 테이블+샘플데이터, RLS 활성화) → Next.js 앱 생성 → 쿼리 → 실행.
5. https://supabase.com/docs/guides/auth ← Auth 개요, 이메일/비번+소셜 링크 확인
   - "Auth with email and password: Sign up and sign in users with email and password." Social Auth 섹션에 Google 링크.
6. https://supabase.com/pricing ← **Q3 risk:high 기본소스**
   - Free: "Limit of 2 active projects" / "500 MB database size (Shared CPU • 500 MB RAM)" / "50,000 monthly active users" / "5 GB egress" + "5 GB cached egress" / "1 GB file storage" / "Free projects are paused after 1 week of inactivity"
7. https://supabase.com/docs/guides/getting-started/mcp ← **핵심 소스 (Q4, Cursor 설정)**
   - 섹션 "IDE > Cursor": `.cursor/mcp.json`에 `{"mcpServers":{"supabase":{"url":"https://mcp.supabase.com/mcp"}}}` 추가.
   - "Next steps": "Depending on the client, you may need to restart it to connect and detect all tools after authorization"
8. https://supabase.com/docs/guides/database/postgres/row-level-security ← **핵심 소스 (Q5)**
   - "Supabase allows convenient and secure data access from the browser, as long as you enable RLS."
   - "RLS *must* always be enabled on any tables stored in an exposed schema."
   - "You can just think of them as adding a WHERE clause to every query." (Policies 섹션)
   - 예시 정책 "Individuals can view their own todos." → select 시 자동으로 `where auth.uid() = todos.user_id` 필터.
   - "RLS is incredibly powerful and flexible, allowing you to write complex SQL rules that fit your unique business needs."
9. https://supabase.com/docs/guides/auth/social-login/auth-google ← **핵심 소스 (Q2 Google 로그인)**
   - Prerequisites: Google Auth Platform에서 Audience/Data Access(Scopes: openid, userinfo.email, userinfo.profile)/Branding 설정.
   - Project setup > Web application: Google Auth Platform Clients에서 OAuth 클라이언트 생성(Web application) → Authorized JavaScript origins → Authorized redirect URIs(로컬: http://127.0.0.1:54321/auth/v1/callback) → Client ID/Secret을 Supabase Dashboard Google provider에 입력.
   - Local dev: `supabase/config.toml`의 `[auth.external.google]` + env로 client_id/secret 관리.
10. https://supabase.com/docs/guides/auth/quickstarts/nextjs ← **핵심 소스 (Q2 Next.js)**
    - 섹션: Create a new Supabase project / Create a Next.js app / Declare Supabase Environment Variables / Start the app.
    - ".env.example → .env.local 이름 변경 후 연결변수 채우기" / "localhost:3000/auth/sign-up 에서 Sign up 클릭"
11. https://supabase.com/docs/guides/auth/quickstarts/react-native ← **핵심 소스 (Q2 RN/Expo)**
    - Create a new Supabase project / create-expo-app으로 React 앱 생성 / supabase-js 등 의존성 설치 / lib/supabase.ts 헬퍼 생성 / App.tsx에 Auth 컴포넌트 추가 / 로그인 시 user id 화면 출력 / 앱 실행.
12. https://supabase.com/blog/mcp-server ← Q4 배경 (공식 블로그, 게시일 2025-04-04)
    - "MCP stands for Model Context Protocol. It standardizes how Large Language Models (LLMs) talk to platforms like Supabase."
    - Cursor 연동 JSON: `{"mcpServers":{"supabase":{"command":"npx","args":["-y","@supabase/mcp-server-supabase@latest","--access-token","<personal-access-token>"]}}}`
    - "Some clients expect a slightly modified JSON format, and Windows users will have to prefix this command with `cmd /c`"
13. https://supabase.com/features/row-level-security ← Q5 보조 (공식, "Benefits: Control access to individual rows based on user attributes or roles." — 너무 짧아 fact엔 안 씀, resource 후보에서도 제외, RLS 공식 가이드가 더 나음)
14. https://supabase.com/solutions/beginners ← 비개발자 대상 소개 페이지. "Learning to build a full-stack application is exciting. Supabase gives you the tools, documentation, and community" / "Ship faster and learn by doing with Supabase." 참고용으로만 확인, fact/resource 미채택(구체 절차 없음).
15. https://triki.net/prgm/11626 (한글 블로그, 게시일 2025.07.30) ← Q5 한글 자료 후보로 채택
    - "RLS 의 역할을 간단하게 설명하자면, 해당 테이블에 접근하는 유저가 어떤 행동을 할 수 있을지 권한을 부여하는 것이죠."
    - 평가: 개념 설명은 쉬우나 실제 설정 단계에서는 Policy Command, Target Roles 등 용어가 추가 설명 없이 등장 → 중간 난이도.

## 검색 스니펫만 확인 (본문 미열람, resources 후보 - YouTube)

- YouTube "Supabase MCP with Cursor — Step-by-step Guide" (zazencodes, watch?v=wa9-d63velk)
  - 검색 스니펫: "setting up the official Supabase MCP server with Cursor and building a React app with database and auth integrations" / "personal access token generation and Cursor integration" / ".cursor/mcp.json configuration" / "Building a To-Do App with AI Assistance" / "Adding Authentication with Supabase Auth"
  - locator: search-snippet (본문 미열람) → fact 금지, resources에만 등재.

## risk:high 반박검색(counter) 기록 — Q3 무료 티어 한도

1차 검색 쿼리: "Supabase pricing free tier limits projects database" → makerkit.dev, uibakery.io 등 블로그 요약이 공식 pricing 페이지 수치와 일치(500MB DB, 50,000 MAU, 5GB egress, 2 active projects).
2차(반박) 검색 쿼리: `"Supabase" free plan "2 organizations" OR "active projects" limit 2026 site:supabase.com` →
  - "You are entitled to two active free projects... The project limit applies across all organizations where you are an Owner or Administrator" — supabase.com/docs/guides/troubleshooting/keeping-free-projects-after-pro-upgrade-Kf9Xm2 요지와 일치.
  - "500 MB database, 1 GB file storage, 5 GB egress bandwidth, 50,000 monthly active users... up to 2 active projects" — 공식 pricing 페이지 원문 수치와 완전 일치. counter 결과: 상충 없음, 수치 확정.

## failed_urls

- https://supabase.com/docs/guides/getting-started/quickstarts/reactnative → HTTP 404. (정확한 경로는 /docs/guides/auth/quickstarts/react-native 였음, DB quickstart용 React Native 페이지는 별도 확인 못함)

## 채택하지 않은 소스 (dead ends)

- https://www.quickstart.md/quickstarts/supabase/ — 비공식 미러/집계 사이트로 보여 방문하지 않음(공식문서 우선 원칙).
- https://supabase.com/docs/guides/getting-started (허브) — 실제 절차 없어 fact 소스로 미채택.
- https://supabase.com/features/row-level-security — 문장이 너무 짧아(한 줄) fact/resource 모두 미채택, RLS 공식 가이드(postgres/row-level-security)로 대체.
