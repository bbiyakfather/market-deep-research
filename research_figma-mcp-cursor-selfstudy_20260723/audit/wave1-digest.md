# Wave 1 join digest (G1)

## A1-figma-mcp — facts 15 (high 6) · res 10 · gloss 9 · faq 6 · leads 3 · failed_urls 0
- F[A1-figma-mcp#0] (normal) Figma 데스크톱 앱에서 MCP 서버를 켜는 절차는 앱을 최신 버전으로 업데이트 → Figma Design 파일을 열고 하단 툴바에서 Dev Mode로 전환(단축키 Shift+D) → Inspec
- F[A1-figma-mcp#1] (normal) Figma가 공식적으로 권장하는 방식은 데스크톱 앱 설치 없이 쓸 수 있는 원격(remote) MCP 서버이며, 엔드포인트는 https://mcp.figma.com/mcp 이고 접속 시 Figma 
- F[A1-figma-mcp#2] (normal) Figma MCP 서버는 아무 편집기나 연결되는 것이 아니라 Figma MCP Catalog에 등재된 클라이언트(VS Code, Cursor, Claude Code 등)만 연결이 허용된다.
- F[A1-figma-mcp#3] (high) 무료 Starter 플랜에서도 Figma MCP 서버(원격) 자체는 켤 수 있지만 월 6회 호출로 제한되며, 이 제한을 풀려면 유료 플랜(Pro/Organization/Enterprise)으로 업그
- F[A1-figma-mcp#4] (high) MCP 서버 접근에는 유료 플랜의 Dev 또는 Full 시트가 필요하며, 그중에서도 Figma 파일에 실제로 쓰기(write to canvas, use_figma 도구)까지 하려면 Full 시트가 
- F[A1-figma-mcp#5] (high) Figma Professional 플랜 가격은 공식 페이지 정적 렌더링 기준(연간 청구가 기본 선택된 상태) Full seat $16/mo, Dev seat $12/mo이다.
- F[A1-figma-mcp#6] (high) Figma MCP 서버 호출 한도는 시트·플랜별로 표로 정해져 있다: 모든 플랜의 View/Collab 시트와 Starter 플랜은 시트 종류와 무관하게 월 6회, Professional Dev/F
- F[A1-figma-mcp#7] (normal) Cursor에서 원격 MCP 서버를 붙이는 공식 권장 방법은 Cursor 에이전트 채팅창에 `/add-plugin figma`를 입력해 Figma 플러그인(설정+Agent Skills 포함)을 설치
- F[A1-figma-mcp#8] (normal) Figma 데스크톱 서버를 Cursor에 수동으로 붙일 때는 mcp.json에 {"mcpServers": {"figma-desktop": {"url": "http://127.0.0.1:3845/mc
- F[A1-figma-mcp#9] (normal) Cursor에서 원격 서버를 수동으로 붙이는 방법도 별도로 있는데, Figma가 제공하는 'Figma MCP server deep link'를 클릭해 Cursor 안에서 MCP 설정을 열고 Inst
- F[A1-figma-mcp#10] (normal) 무료 플랜 사용자를 위한 대표적 커뮤니티 대체재는 Framelink Figma MCP(npm 패키지명 figma-developer-mcp, GitHub 저장소 GLips/Figma-Context-M
- F[A1-figma-mcp#11] (high) Framelink Figma MCP(figma-developer-mcp) 같은 커뮤니티 대체재도 내부적으로 Figma 개인 액세스 토큰(personal access token)으로 Figma RES
- F[A1-figma-mcp#12] (normal) Figma 공식(figma/mcp-server-guide 저장소)이 제시하는 디자인→코드 품질 향상 best practice는 버튼·카드·인풋처럼 재사용되는 요소를 컴포넌트로 만들고, 그 컴포넌트를
- F[A1-figma-mcp#13] (normal) Figma MCP 서버의 핵심 한계는 한 번에 너무 큰 화면(대형 프레임)을 통째로 선택해서 코드 생성을 요청하면 느려지거나 오류가 나거나 응답이 불완전해질 수 있다는 것이며, 공식 권장 대응은 화
- F[A1-figma-mcp#14] (high) Figma MCP의 'write to canvas'(코드/에이전트가 Figma 캔버스에 직접 컴포넌트·변수·프레임을 쓰는 기능, use_figma 도구)는 2026-07-23 기준 베타 기간 동안 
  resources:
  - [공식문서/입문/en/공통] Introduction | Figma MCP Server Developer Docs :: https://developers.figma.com/docs/figma-mcp-server/
  - [공식문서/초급/en/공통] Set up the remote server (recommended) | Developer Docs :: https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/
  - [공식문서/초급/en/공통] Set up the desktop server (using desktop app) | Developer Docs :: https://developers.figma.com/docs/figma-mcp-server/local-server-installation/
  - [공식문서/초급/en/공통] Rate limits & access | Developer Docs :: https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/
  - [공식문서/입문/en/공통] Plans & Pricing | Figma :: https://www.figma.com/pricing/
  - [공식문서/초급/en/공통] Cursor and Figma: Set up the MCP server – Figma Learn - Help Center :: https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server
  - [공식문서/중급/en/공통] Figma MCP server FAQs – Figma Learn - Help Center :: https://help.figma.com/hc/en-us/articles/39252411778583-Figma-MCP-server-FAQs
  - [GitHub/중급/en/공통] GitHub - figma/mcp-server-guide :: https://github.com/figma/mcp-server-guide
  - [GitHub/중급/en/공통] GitHub - GLips/Figma-Context-MCP (Framelink Figma MCP / npm figma-developer-mcp) :: https://github.com/GLips/Figma-Context-MCP
  - [블로그/중급/ko/공통] 2026 피그마 MCP 완벽 가이드: use_figma로 캔버스 직접 수정하기 (Claude Code 연동 후기) :: https://litmers.com/blog/%ED%94%BC%EA%B7%B8%EB%A7%88-mcp-%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80-%EA%B5%AC%ED%98%84-%ED%81%B4%EB%A1%9C%EB%93%9C-%EC%BD%94%EB%93%9C-%EC%97%B0%EB%8F%99-%ED%9B%84%EA%B8%B0

## A2-cursor — facts 15 (high 2) · res 6 · gloss 9 · faq 6 · leads 3 · failed_urls 4
- F[A2-cursor#0] (normal) Windows에서는 설치 파일(installer)을 실행하고 화면의 안내(prompt)를 따르면 설치가 완료된다.
- F[A2-cursor#1] (normal) Mac에서는 다운로드한 Cursor 아이콘을 Applications 폴더로 드래그하면 설치가 완료된다.
- F[A2-cursor#2] (normal) Cursor를 쓰려면 사전에 무료 Cursor 계정을 만들어야 하고, 설치 후 첫 실행 시 안내에 따라 로그인해야 한다.
- F[A2-cursor#3] (normal) Cursor 공식 웹사이트(cursor.com)는 한국어 등 여러 언어로 제공되지만, 에디터 앱 자체의 인터페이스(UI) 언어를 한국어로 바꾸는 공식 설정은 공식 문서(설치/도움말 페이지)에서 확인
- F[A2-cursor#4] (normal) Tab은 Cursor의 AI 자동완성 기능으로, 최근 편집 이력·주변 코드·린터 오류를 근거로 타이핑 중 코드를 제안한다.
- F[A2-cursor#5] (normal) Cmd/Ctrl+K(Inline Edit)는 채팅 패널을 열지 않고 선택한 코드 범위를 즉시, 국소적으로 수정하는 기능이다.
- F[A2-cursor#6] (normal) Chat(Ask 모드)는 코드를 변경하지 않고 코드베이스를 이해·탐색하며 질문에 답하는 읽기 전용(read-only) 모드다.
- F[A2-cursor#7] (normal) Agent 모드는 기능을 처음부터 만들고, 리팩터링하고, 버그를 고치고, 테스트를 작성하고, 셸 명령을 실행하는 등 복잡한 코딩 작업을 독립적으로 수행하는 Cursor의 어시스턴트다.
- F[A2-cursor#8] (normal) Cursor Rules는 Agent에게 주는 시스템 수준 지시문으로, 프롬프트·스크립트 등을 하나로 묶어 팀 전체가 워크플로를 관리·공유할 수 있게 한다.
- F[A2-cursor#9] (normal) 프로젝트 규칙(Project Rules)은 프로젝트 폴더 안 .cursor/rules 경로에 .mdc 확장자 파일로 저장되며 버전관리(git) 대상이 된다.
- F[A2-cursor#10] (normal) AGENTS.md는 메타데이터 없이 순수 마크다운으로 에이전트 지시사항을 정의하는 파일로, 프로젝트 루트에 두며 .cursor/rules의 대안으로 쓸 수 있다. 현재 공식 문서에는 .cursorr
- F[A2-cursor#11] (normal) MCP 서버는 (1) Customize 화면의 Cursor Marketplace에서 원클릭 설치, (2) Cursor Settings UI, (3) mcp.json 파일 수동 작성 중 하나로 등록할
- F[A2-cursor#12] (normal) mcp.json은 프로젝트 전용이면 프로젝트 폴더의 .cursor/mcp.json, 모든 프로젝트에서 공용으로 쓰려면 홈 디렉터리의 ~/.cursor/mcp.json에 두며, mcpServers 객
- F[A2-cursor#13] (high) 2026년 7월 현재 Hobby 플랜은 신용카드 없이 무료로 가입 가능하며, 'Limited Agent requests'와 'Limited Tab completions'로만 한도가 표시될 뿐 공식 
- F[A2-cursor#14] (high) 2026년 7월 현재 Pro(Individual) 플랜은 월 $20이며, Tab 자동완성은 무제한, Agent 사용 한도는 확장(extended)되고 Bugbot·Cloud Agents 접근이 포함
  resources:
  - [공식문서/입문/en/공통] Cursor Docs — Rules (프로젝트 규칙 공식 문서) :: https://cursor.com/docs/rules
  - [공식문서/초급/en/공통] Cursor Docs — Model Context Protocol (MCP) :: https://cursor.com/docs/mcp
  - [공식문서/입문/en/공통] Cursor · Pricing (공식 요금 페이지) :: https://cursor.com/pricing
  - [무료강의/입문/ko/공통] [지금 무료][연재형] WE CAN Cursor AI! :: https://www.inflearn.com/en/course/we-can-cusor-ai
  - [YouTube/입문/ko/공통] 왕초보도 개발 가능 | 커서 AI 설치부터 기본 사용법 강의 :: https://www.youtube.com/watch?v=he0gEZ5wg0Q
  - [YouTube/입문/ko/공통] 이제 코딩 3배 빨라진다고? 커서 AI 실화? (25분 완벽 정리) :: https://www.youtube.com/watch?v=_oEhh8666pA
  failed_urls: ['https://docs.cursor.com/en/get-started/installation', 'https://cursor.com/docs/chat/overview', 'https://cursor.com/docs/agent/chat/overview', 'https://wikidocs.net/278669']

## A3-supabase — facts 12 (high 1) · res 10 · gloss 8 · faq 5 · leads 4 · failed_urls 1
- F[A3-supabase#0] (normal) Supabase 대시보드에서 새 프로젝트를 만드는 첫 단계는 조직(organization)의 Dashboard에서 New project를 생성하는 것이다.
- F[A3-supabase#1] (normal) 테이블은 코드 없이 대시보드의 Table Editor에서 New Table로 이름을 정해 만들고, New Column으로 컬럼명과 데이터 타입(예: text)을 지정해 추가한다.
- F[A3-supabase#2] (normal) 테이블 생성 시 각 컬럼의 데이터 타입을 반드시 지정해야 하며, 생성 후에도 언제든 컬럼을 추가/삭제할 수 있다.
- F[A3-supabase#3] (normal) Supabase Next.js quickstart는 프로젝트 생성 → instruments 테이블·샘플 데이터 생성 및 Row Level Security(RLS) 활성화 → Next.js 앱에서 데
- F[A3-supabase#4] (normal) Supabase Auth는 이메일/비밀번호 방식의 회원가입·로그인을 공식 기능으로 제공하며, Google을 포함한 소셜 로그인(Social Auth)을 별도 가이드로 지원한다.
- F[A3-supabase#5] (normal) Google 소셜 로그인을 붙이려면 Google Auth Platform 콘솔에서 Web application 유형 OAuth 클라이언트를 만들어 Authorized redirect URIs에 Su
- F[A3-supabase#6] (normal) Next.js용 Auth quickstart는 프로젝트 생성 → Next.js 앱 생성 → .env.example을 .env.local로 바꿔 Supabase 연결 변수 채우기 → 개발 서버 실행 
- F[A3-supabase#7] (normal) React Native/Expo용 Auth quickstart는 프로젝트 생성 → create-expo-app으로 앱 생성 → supabase-js 등 의존성 설치 → lib/supabase.ts 
- F[A3-supabase#8] (high) Supabase 무료(Free) 플랜 한도는 활성 프로젝트 최대 2개, 데이터베이스 500MB, 월간 활성 사용자(MAU) 50,000명, egress 5GB(+캐시된 egress 5GB), 파일 
- F[A3-supabase#9] (normal) Supabase는 Cursor 등 AI 에디터가 Supabase 프로젝트와 직접 대화할 수 있게 하는 공식 MCP(Model Context Protocol) 서버를 제공하며, Cursor에서는 .c
- F[A3-supabase#10] (normal) MCP(Model Context Protocol)는 대형 언어 모델(LLM)이 Supabase 같은 플랫폼과 대화하는 방식을 표준화한 프로토콜이며, Cursor 연동 시 npx로 실행하는 방식은 개
- F[A3-supabase#11] (normal) RLS(Row Level Security)는 노출된(exposed) 스키마의 모든 테이블에 반드시 켜야 하며, 켜져 있으면 정책(policy)이 모든 쿼리에 자동으로 WHERE절을 추가하는 것과 같
  resources:
  - [공식문서/입문/en/공통] Use Supabase with Next.js (Quickstart) :: https://supabase.com/docs/guides/getting-started/quickstarts/nextjs
  - [공식문서/입문/en/공통] Tables | Supabase Docs (Table Editor로 테이블 만들기) :: https://supabase.com/docs/guides/database/tables
  - [공식문서/초급/en/P3로그인] Auth | Supabase Docs (Auth 개요) :: https://supabase.com/docs/guides/auth
  - [공식문서/초급/en/P3로그인] Use Supabase Auth with Next.js :: https://supabase.com/docs/guides/auth/quickstarts/nextjs
  - [공식문서/초급/en/P3로그인] Use Supabase Auth with React Native :: https://supabase.com/docs/guides/auth/quickstarts/react-native
  - [공식문서/중급/en/P3로그인] Login with Google | Supabase Docs :: https://supabase.com/docs/guides/auth/social-login/auth-google
  - [공식문서/중급/en/공통] Model context protocol (MCP) | Supabase Docs :: https://supabase.com/docs/guides/getting-started/mcp
  - [YouTube/중급/en/공통] Supabase MCP with Cursor — Step-by-step Guide :: https://www.youtube.com/watch?v=wa9-d63velk
  - [공식문서/중급/en/P3로그인] Row Level Security | Supabase Docs :: https://supabase.com/docs/guides/database/postgres/row-level-security
  - [블로그/초급/ko/P3로그인] [Supabase] 데이터베이스 테이블에 RLS 설정하기 – 모두의매뉴얼 :: https://triki.net/prgm/11626
  failed_urls: ['https://supabase.com/docs/guides/getting-started/quickstarts/reactnative']

## A4-n8n — facts 11 (high 1) · res 10 · gloss 10 · faq 5 · leads 3 · failed_urls 4
- F[A4-n8n#0] (high) n8n Cloud는 연간 결제 기준 Starter 20€/월(2,500 executions), Pro 50€/월(10,000 executions), Business 667€/월(40,000 exec
- F[A4-n8n#1] (normal) n8n Cloud는 Starter/Pro 플랜에 신용카드 없이 체험 가능하고, Business 플랜은 신용카드 등록이 필요한 14일 체험을 제공한다.
- F[A4-n8n#2] (normal) n8n의 self-hosted Community Edition은 GitHub에서 무료로 제공되는 표준 버전이다.
- F[A4-n8n#3] (normal) n8n을 Docker로 self-host하는 공식 절차는 `docker volume create n8n_data` 실행 후 `docker run -it --rm --name n8n -p 5678:5
- F[A4-n8n#4] (normal) HTTP Request 노드는 REST API를 가진 모든 앱/서비스에서 데이터를 조회하도록 요청을 보내는 n8n의 범용 노드로, DELETE/GET/HEAD/OPTIONS/PATCH/POST/PU
- F[A4-n8n#5] (normal) n8n의 HTML 노드(버전 0.213.0부터 이전 HTML Extract 노드를 대체)는 'Extract HTML Content' 동작에서 CSS Selector와 반환 유형(속성/HTML/텍스트
- F[A4-n8n#6] (normal) n8n 공식 워크플로 템플릿 갤러리에는 HTTP Request 노드로 여러 공개 API를 매일 수집해 정규화한 뒤 Supabase(Postgres) 테이블과 Google Sheets에 동시에 적재하
- F[A4-n8n#7] (normal) GitHub의 커뮤니티 저장소 awesome-n8n-templates는 280개 이상의 무료 n8n 자동화 템플릿을 모아두었고, 이 중 Google Drive&Sheets 카테고리에 13개, Sup
- F[A4-n8n#8] (normal) robots.txt는 검색엔진 크롤러에게 접근 가능한 URL을 알려주는 파일이지만, Google Search Central 공식 문서에 따르면 이 지침에 법적 강제력은 없고 크롤러가 자발적으로 따를
- F[A4-n8n#9] (normal) 유럽개인정보보호위원회(EDPB)가 2026년 7월 7일 채택한 가이드라인은 웹 스크래핑이 개인정보 처리(수집·저장·조직화·검색)를 포함할 경우 GDPR이 적용된다고 명시한다.
- F[A4-n8n#10] (normal) 인포그랩(InfoGrab)이 자체 개발한 자동번역 프로그램으로 n8n 공식 문서의 한국어판을 국내 최초로 제공하며, Level 1(기초 편집기 UI·미니 워크플로)·Level 2(데이터 구조·병합·
  resources:
  - [공식문서/입문/en/공통] n8n Pricing (Cloud plans, self-hosted) :: https://n8n.io/pricing/
  - [공식문서/중급/en/Part1크롤링] Install with Docker | n8n Docs :: https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker
  - [공식문서/입문/en/Part1크롤링] HTTP Request | Nodes | n8n Docs :: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/
  - [공식문서/입문/en/Part1크롤링] HTML | Nodes | n8n Docs :: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.html/
  - [블로그/입문/ko/Part1크롤링] n8n에서 HTTP 요청 노드 활용하기 - 지니코딩랩 :: https://www.jiniai.biz/2025/03/20/n8n%EC%97%90%EC%84%9C-http-%EC%9A%94%EC%B2%AD-%EB%85%B8%EB%93%9C-%ED%99%9C%EC%9A%A9%ED%95%98%EA%B8%B0/
  - [공식문서/중급/en/공통] Aggregate multi-source job boards to Supabase and Google Sheets | n8n workflow t :: https://n8n.io/workflows/14996-aggregate-multi-source-job-boards-to-supabase-and-google-sheets/
  - [공식문서/중급/en/공통] Guidelines 03/2026 on web scraping in the context of generative AI :: https://www.edpb.europa.eu/system/files/2026-07/edpb_guidelines_2020603_webscraping_v1_en_0.pdf
  - [공식문서/입문/en/공통] Introduction to robots.txt | Google Search Central :: https://developers.google.com/search/docs/crawling-indexing/robots/intro
  - [블로그/입문/ko/공통] n8n 공식 기술 문서 한글판 (InfoGrab) :: https://n8n-docs.infograb.net/courses/level-two/chapter-2/
  - [YouTube/입문/ko/공통] 당신이 원하던 n8n 2026 버전 마스터클래스! 8시간 완전정복 기초강의 :: https://www.youtube.com/watch?v=LR2vONAVEYk
  failed_urls: ['https://docs.n8n.io/hosting/installation/docker/', 'https://docs.n8n.io/hosting/installation/docker', 'https://docs.n8n.io/code/cookbook/http-node/', 'https://ico.org.uk/about-the-ico/what-we-do/our-work-on-artificial-intelligence/response-to-the-consultation-series-on-generative-ai/the-lawful-basis-for-web-scraping-to-train-generative-ai-models/']

## A5-tosspayments — facts 15 (high 7) · res 10 · gloss 9 · faq 5 · leads 4 · failed_urls 4
- F[A5-tosspayments#0] (high) 테스트 환경에서는 카드 번호 등 실제 결제 정보를 입력해도 결제가 가상으로만 승인되며, 실제 결제수단에서 돈이 출금되지 않는다.
- F[A5-tosspayments#1] (high) 이메일·전화번호만으로 가입하는 '개발 연동 체험 상점' 단계에서는 사업자등록 없이도 API 로그 확인, 웹훅 설정·연결, 가상계좌 모의입금까지 테스트할 수 있다.
- F[A5-tosspayments#2] (high) 정산(실제 결제금이 사업자 계좌로 입금되는) 기록은 라이브 환경에서만 조회할 수 있어, 테스트 키만으로는 실제 정산 과정까지 학습할 수 없다.
- F[A5-tosspayments#3] (high) 테스트 환경에서 발급되는 가상계좌는 번호 앞에 'X'가 붙는 가짜 계좌라 실제로 입금할 수 없다.
- F[A5-tosspayments#4] (high) 카카오페이는 테스트 키로 연동 자체가 불가능하며 전자결제 계약 체결 후 발급되는 상점 전용 MID 테스트 키로만 가능하고, 페이코는 테스트 키 대신 라이브 키로만 테스트해야 한다.
- F[A5-tosspayments#5] (high) 자동결제(빌링)는 리스크 검토와 별도 계약을 완료해야 실제 서비스에 쓸 수 있고, 정기 구독형 서비스가 아니면 정책적으로 사용이 제한된다.
- F[A5-tosspayments#6] (high) 테스트 환경에서는 카드번호 앞 여섯 자리(BIN 번호)만 유효해도 자동결제(빌링키)가 등록되므로, 실계약 전에도 빌링키 발급~자동결제 흐름을 연습할 수 있다.
- F[A5-tosspayments#7] (normal) 결제위젯은 주문서 페이지에 결제 UI 영역을 직접 넣는 '주문서형'과, 결제하기 버튼 클릭 시 팝업으로 호출하는 '결제창형' 두 가지 연동 방식을 제공한다.
- F[A5-tosspayments#8] (normal) 결제위젯 연동은 상점관리자(어드민)의 '결제 UI 설정 메뉴'에서 UI를 만든 뒤, 해당 variantKey를 복사해 코드에 넣는 절차로 진행된다.
- F[A5-tosspayments#9] (normal) 개발자센터는 결제위젯 연동을 시작하기 전, 내 상점의 업종이 입점 불가·제한 업종인지부터 확인하라고 안내한다.
- F[A5-tosspayments#10] (normal) 공식 GitHub의 SDK v1 샘플 저장소(payment-widget-sample)조차 README에서 더 편리한 연동을 위해 SDK v2 사용을 직접 권장하고 있어, 한국어 튜토리얼을 볼 때 v
- F[A5-tosspayments#11] (normal) 공식 GitHub 저장소 tosspayments-sample은 결제연동 샘플 프로젝트로, Express+React·Express+Vue 등 프레임워크 조합별 폴더를 제공한다.
- F[A5-tosspayments#12] (normal) 공식 블로그(토스페이먼츠 작성, 2023.03.06) 'React로 결제 페이지 개발하기'는 Vite 기반 React 프로젝트에서 npm install @tosspayments/payment-wid
- F[A5-tosspayments#13] (normal) 자동결제 승인은 구독 서비스의 결제 주기(결제일)마다 저장해둔 빌링키로 원하는 금액을 승인 요청하는 방식으로 이뤄지며, 이 승인 API를 언제 호출할지 정하는 스케줄링 자체는 개발자가 별도로 구현해
- F[A5-tosspayments#14] (normal) 테스트 환경에서는 각 API가 분당 100건의 요청 제한을 두고 있어, 반복 실습 시 이 한도를 감안해야 한다.
  resources:
  - [공식문서/입문/ko/P2결제] 시작하기 | 토스페이먼츠 개발자센터 :: https://docs.tosspayments.com/guides/v2/get-started
  - [공식문서/입문/ko/P2결제] 결제위젯 이해하기 | 토스페이먼츠 개발자센터 :: https://docs.tosspayments.com/guides/v2/payment-widget
  - [공식문서/입문/ko/P2결제] 회원가입, 사업자번호 없이 결제 테스트하기 | 토스페이먼츠 개발자센터 :: https://docs.tosspayments.com/blog/how-to-test-toss-payments
  - [공식문서/초급/ko/P2결제] 환경 설정하기 | 토스페이먼츠 개발자센터 :: https://docs.tosspayments.com/guides/v2/get-started/environment
  - [공식문서/중급/ko/P2결제] 자동결제(빌링) 이해하기 | 토스페이먼츠 개발자센터 :: https://docs.tosspayments.com/guides/v2/billing
  - [GitHub/초급/ko/P2결제] GitHub - tosspayments/tosspayments-sample :: https://github.com/tosspayments/tosspayments-sample
  - [공식블로그/초급/ko/P2결제] React로 결제 페이지 개발하기 (ft. 결제위젯) :: https://www.tosspayments.com/blog/articles/paytech-4
  - [공식블로그/입문/ko/P2결제] 결제위젯으로 React의 useEffect 사용해보기 | 토스페이먼츠 개발자센터 :: https://docs.tosspayments.com/blog/react-use-effect
  - [YouTube/초급/ko/P2결제] NextJs 결제연동하기 (feat. Toss/토스페이먼츠) :: https://www.youtube.com/watch?v=lpfO2mebYQk
  - [YouTube/입문/ko/P2결제] [CCOMMIT] 경력/비전공자 토스페이먼츠 결제 API 연동 :: https://www.youtube.com/watch?v=5DiSLv-n6l0
  failed_urls: ['https://www.npmjs.com/package/@tosspayments/tosspayments-sdk', 'https://docs.tosspayments.com/guides/payment-widget/integration', 'https://docs.tosspayments.com/guides/v2/payment-widget/integration', 'https://github.com/tosspayments/browser-sdk']

## A6-resources — facts 15 (high 1) · res 19 · gloss 8 · faq 6 · leads 4 · failed_urls 6
- F[A6-resources#0] (normal) 노마드코더의 '에어비앤비 클론코딩'은 백엔드 Django/DRF, 프론트엔드 ReactJS/Chakra UI 스택의 유료 강의(191개 영상, 30시간 이상, 중급)로, 숙소 검색·찜·예약·후기 기
- F[A6-resources#1] (high) 노마드코더의 '캐럿마켓(당근마켓) 클론코딩'은 Next.js 14, TypeScript, Prisma, Tailwind, Zod, Vercel, Twilio, Supabase, Cloudflare 
- F[A6-resources#2] (normal) 노마드코더의 Next.js 무료 입문강의는 App Router, Server Components, Dynamic Pages, React Suspense, CSS Modules 등을 다루며 4시간 3
- F[A6-resources#3] (normal) 노마드코더의 자바스크립트 무료 강의('자바스크립트로 웹 서비스 만들기')는 8시간 60개 영상 분량이며, 강의 페이지에는 'HTML.CSS.JS 이해도 필요'라는 선수지식 표기가 있다.
- F[A6-resources#4] (normal) 인프런 로펀 강사의 유료 강의 '[풀스택 완성] Supabase로 웹사이트 3개 클론하기'는 Next.js 14 + Supabase + Tailwind + React Query + Recoil 스택
- F[A6-resources#5] (normal) 인프런 무료 강의 '1. 웹개발 기초 [HTML, CSS]'는 총 2시간 34분, 11개 강의로 구성된 입문 난이도의 무료 강좌다.
- F[A6-resources#6] (normal) notjust.dev의 'Build a Netflix Clone App with React Native and Expo' 튜토리얼은 2025년 5월 31일 게시됐으며 Expo Router, Type
- F[A6-resources#7] (normal) GitHub 저장소 Lordhacker756/Netflix는 저장소 설명(About)에는 '사용자 인증으로 회원가입·로그인 가능'이라 적혀 있지만, 실제 README 본문에는 Home/Details
- F[A6-resources#8] (normal) Figma 공식 Help Center 문서에 따르면 Cursor에 Figma MCP 서버를 연결하는 권장 방법은 Figma 플러그인 설치(Cursor 명령창에서 /add-plugin figma)이며
- F[A6-resources#9] (normal) Figma 공식 개발자 문서(원격 서버 설치 가이드)도 동일하게 Cursor 플러그인 설치를 권장 방법으로 안내하며, MCP 딥링크를 통해 Install 후 Connect하는 절차를 구체적으로 제시
- F[A6-resources#10] (normal) 토스페이먼츠 공식 개발자센터의 결제위젯 연동 가이드는 '이해하기 → 어드민 사용하기 → 연동하기 → 배포 체크리스트' 4단계로 구성돼 있으며, 이 페이지 발췌 내용만으로는 프레임워크별(Next.js
- F[A6-resources#11] (normal) 토스페이먼츠 공식 샘플 저장소(tosspayments-sample)의 README에는 Express+React/Vue/JS, PHP+JS, ASP+JS, JSP+JS, Spring+JS, Djang
- F[A6-resources#12] (normal) 브런치 글 '비개발자를 위한 Cursor-figma-MCP 사용법'(2025-03-24 게시)은 프로덕트 디자이너를 대상으로 Cursor-Figma MCP 연결 과정을 단계별로 설명하며, 다수 디자
- F[A6-resources#13] (normal) 모비인사이드 기사(2025-06-25, 저자 유훈식)는 MCP를 'AI용 USB-C 단자'에 비유하며, Figma 디자인을 받아 React 코드로 자동 변환하는 데 약 10분이 소요된다고 설명한다.
- F[A6-resources#14] (normal) Builder.io 블로그의 'Cursor for Designers Tutorial #3: Figma to Code and Beyond'는 2026년 3월 7일 게시된 최신 글로, Figma MCP
  resources:
  - [무료강의/중급/ko/Part1] 에어비앤비 클론코딩 (Django, REST Framework, Chakra UI) :: https://nomadcoders.co/airbnb-clone
  - [무료강의/중급/ko/Part1] 캐럿마켓(당근마켓) 클론코딩 (Next.js 14, Tailwind, Prisma) :: https://nomadcoders.co/carrot-market
  - [무료강의/입문/ko/Part1] NextJS 무료 강의: 앱 라우터로 웹사이트 만들기 :: https://nomadcoders.co/nextjs-for-beginners
  - [무료강의/중급/en/Part1] Mastering Next.js 14 - Build Airbnb Clone from Scratch :: https://www.udemy.com/course/mastering-nextjsbuild-an-airbnb-clone-from-scratch-2024/
  - [GitHub/중급/en/Part1] SashenJayathilaka/Airbnb-Build (오픈소스 코드) :: https://github.com/SashenJayathilaka/Airbnb-Build
  - [무료강의/초급/ko/Part2] [풀스택 완성] Supabase로 웹사이트 3개 클론하기 (Next.js 14) - Dropbox/Netflix/Instagram :: https://www.inflearn.com/course/%EC%9A%94%EC%A6%98%EC%97%94-supabase-%EB%8C%80%EC%84%B8%EC%A7%80-nextjs-%ED%81%B4%EB%A1%A0%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8
  - [공식문서/중급/ko/Part2] 연동하기 (결제위젯 통합 가이드) :: https://docs.tosspayments.com/guides/payment-widget/integration
  - [GitHub/중급/ko/Part2] tosspayments-sample (공식 결제 연동 샘플 저장소) :: https://github.com/tosspayments/tosspayments-sample
  - [무료강의/초급/ko/Part2] [무작정 플러터] 넷플릭스 클론 코딩 with Flutter/Firebase :: https://www.inflearn.com/course/flutter-netflix-clone-app
  - [무료강의/중급/en/Part3] Build a Netflix Clone App with React Native and Expo — Full Tutorial :: https://www.notjust.dev/blog/netflix-clone
  - [GitHub/중급/en/Part3] Lordhacker756/Netflix (React Native 넷플릭스 클론, 인증 포함 주장) :: https://github.com/Lordhacker756/Netflix
  - [GitHub/중급/en/Part3] calebnance/expo-netflix (Netflix UI Clone with React Native & Expo) :: https://github.com/calebnance/expo-netflix
  - [공식문서/중급/en/Part3] Authentication in Expo and React Native apps :: https://docs.expo.dev/develop/authentication/
  - [공식문서/입문/en/공통] Cursor and Figma: Set up the MCP server :: https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server
  - [공식문서/중급/en/공통] Set up the remote server (recommended) | Figma Developer Docs :: https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/
  - [블로그/입문/ko/공통] 비개발자를 위한 Cursor-figma-MCP 사용법 :: https://brunch.co.kr/@zitopd/8
  - [블로그/중급/en/공통] Cursor for Designers Tutorial #3: Figma to Code and Beyond :: https://www.builder.io/blog/figma-to-cursor-for-designers
  - [무료강의/입문/ko/공통] [무료] 1. 웹개발 기초 [HTML, CSS] :: https://www.inflearn.com/course/%EC%9B%B9%EA%B0%9C%EB%B0%9C-%EA%B8%B0%EC%B4%88-html-css
  - [무료강의/입문/ko/공통] 자바스크립트로 웹 서비스 만들기 (무료) :: https://nomadcoders.co/javascript-for-beginners
  failed_urls: ['https://opentutorials.org/course/3084', 'https://opentutorials.org/course/3083', 'https://wikidocs.net/160511', 'https://www.figma.com/ko-kr/community/development/code-generators', 'https://www.udemy.com/course/mastering-nextjsbuild-an-airbnb-clone-from-scratch-2024/', 'https://blog.toktokhan.dev/%EB%94%94%EC%9E%90%EC%9D%B4%EB%84%88%EC%9D%98-ai-%EB%B0%94%EC%9D%B4%EB%B8%8C-%EC%BD%94%EB%94%A9-%EC%B2%B4%ED%97%98%EA%B8%B0-feat-cursor-8e2c3a17e4b2']


# TOTALS: {'facts': 83, 'high': 18, 'resources': 65, 'glossary': 53, 'faq': 33} · unique_urls 80

# EXPAND LEADS (전축 취합, dedup 전)
- [A1-figma-mcp] Cursor 자체 공식문서(docs.cursor.com)의 MCP 일반 설정법과 Figma 플러그인 상세 페이지 — why: 이번 조사는 Figma 쪽 공식문서를 기준으로 Cursor 연결 절차를 확인했지만, docs.cursor.com/tools/mcp 같은 Curs — angle: site:docs.cursor.com MCP 또는 Figma plugin add-plugin
- [A1-figma-mcp] Figma AI credits(크레딧) 소모 구조와 MCP 도구 호출이 이 크레딧을 쓰는지 여부 — why: 요금 페이지에 시트별 'AI credits/mo'가 별도로 표시되는데, MCP 도구 호출(get_design_context 등)이 이 크레딧을  — angle: Figma AI credits MCP tool call consumption help center
- [A1-figma-mcp] Code Connect를 비개발자/기획자가 실제로 설정할 수 있는 난이도인지 — why: best practice 문서에서 반복적으로 Code Connect 연결을 강조하지만, 이 강의의 타깃(코드 모르는 기획자·디자이너)이 직접 설 — angle: Figma Code Connect setup guide beginner non-developer
- [A2-cursor] forum.cursor.com에서 Hobby 플랜 실사용자들이 보고하는 최신(2026년 하반기) 실제 한도 사례 수집 — why: 공식 페이지가 숫자를 공개하지 않으므로, 노션 가이드에 '대략 이 정도'라는 체감치를 실사용자 리포트로 보강할 수 있음(단, 비공식이므로 fac — angle: forum.cursor.com Hobby limit 2026 실사용자 리포트
- [A2-cursor] cursor.com/changelog에서 Agent/Tab/MCP 관련 최근 변경 이력 확인 — why: 이 분야는 변화가 매우 빠르므로, 노션 가이드 발행 직전에 changelog로 기능·요금 변경 여부를 한 번 더 점검할 필요. — angle: cursor.com/changelog 최신 릴리즈 노트
- [A2-cursor] Cursor 공식 Settings UI 스크린샷/경로(Settings > Tools & MCP 등)를 실제 앱에서 직접 캡처해 MCP 등록 절차를 그림으로 보강 — why: 공식 문서 텍스트에는 정확한 메뉴명(Settings > Tools & MCP 등)이 명시되지 않아, 비개발자용 가이드에는 스크린샷 기반 스텝이  — angle: 실제 Cursor 앱 설치 후 Settings 메뉴 캡처
- [A3-supabase] Supabase Storage(파일 저장) 대시보드 quickstart — why: 로그인 이후 프로필 사진 업로드처럼 실습 확장 시 필요한데 이번 축에서는 다루지 않음. — angle: Supabase Storage quickstart dashboard
- [A3-supabase] Supabase Auth UI 컴포넌트(@supabase/auth-ui-react)로 로그인 화면을 코드 최소로 만드는 법 — why: 비개발자가 처음부터 로그인 폼을 직접 그리지 않아도 되는 방법이라 Part1/Part2 학습 부담을 줄여줄 수 있음. — angle: supabase auth-ui-react quickstart
- [A3-supabase] Supabase CLI + 로컬 개발(supabase start)과 Cursor MCP 병행 사용법 — why: 실제 서비스로 배포하기 전 로컬에서 안전하게 테스트하는 흐름이 이번 조사에서 빠져 있음. — angle: supabase local development cli getting started
- [A3-supabase] Next.js 앱을 Vercel에 배포해 Supabase와 연결하는 공식 가이드 — why: 코스 최종 목표(실제 서비스 배포)와 직결되는데 이번 축 범위 밖이라 다루지 않음. — angle: supabase vercel deployment guide
- [A4-n8n] n8n 공식 문서의 'execution' 정의/과금 단위 페이지 직접 확인 — why: 요금 리스크(risk:high) 정확도를 더 높이기 위해 실행 횟수 정의 자체를 1차 출처로 재확인할 필요 — angle: docs.n8n.io execution definition billing
- [A4-n8n] 한국 개인정보보호위원회(PIPC)의 웹크롤링/스크레이핑 관련 가이드라인 존재 여부 — why: 한국어 학습자 대상으로 국내 법적 맥락(EDPB는 EU 기준)을 보완하면 실무 적용성이 높아짐 — angle: 개인정보보호위원회 웹 크롤링 가이드라인
- [A4-n8n] Supabase 공식문서 내 n8n 연동/REST API 가이드 — why: DB 적재 단계에서 n8n 커뮤니티 노드가 아닌 Supabase 공식 REST API 사용법을 1차 출처로 보강하면 신뢰도가 올라감 — angle: supabase.com/docs n8n integration REST API
- [A5-tosspayments] 토스페이먼츠 상점관리자(어드민)의 '결제 UI 설정' 화면 실제 캡처/경로 확보 — why: variantKey를 어디서 어떻게 복사하는지는 비개발자가 GUI로 따라할 스크린샷이 필요한데 이번 조사는 텍스트 설명만 확보했다. — angle: 토스페이먼츠 상점관리자 결제 UI 설정 스크린샷 캡처
- [A5-tosspayments] @tosspayments/tosspayments-sdk(v2) 공식 React 코드 예제 원문 확보 — why: 확보한 React 예제(paytech-4 블로그)는 2023년 v1 패키지(@tosspayments/payment-widget-sdk) 기준이고 — angle: docs.tosspayments.com widgets() renderPaymentMethods React 2
- [A5-tosspayments] YouTube 'NextJs 결제연동하기' 등 영상의 실제 자막/난이도 확인 — why: 검색 스니펫만 확보했고 본문(자막) 열람이 안 돼 실제 난이도, v1/v2 여부, 최신성이 검증되지 않았다. — angle: YouTube 자막 추출 도구(insane-search 등)로 재확인
- [A5-tosspayments] toss.tech에 소개된 '토스페이먼츠 MCP 서버' 관련 기사 — why: 검색 결과 중 'AI 기반 코딩 도구로 결제 연동을 돕는 MCP 서버' 언급이 있었는데, 이 조사 대상 강의 주제(Figma MCP, Curso — angle: toss.tech tosspayments-mcp 기사 원문 열람
- [A6-resources] Udemy 'Mastering Next.js 14 Airbnb Clone' 원문 재열람 — why: WebFetch가 403으로 실패해 검색 스니펫만으로 resources에 등재됨. Next.js+Airbnb 정확 매칭 자료라 가치가 높아 팀리 — angle: insane-search 스킬로 우회 접근하거나 Udemy 강의 소개 페이지를 다른 경로로 재시도
- [A6-resources] Figma Make(신규 AI 디자인 생성 도구)와 Cursor 연계 워크플로 — why: 2026 패스트캠퍼스 검색결과에서 'Figma Make'라는 신규 기능이 언급됨. MCP와는 별도 경로일 수 있어 2026년 최신 워크플로 변화 — angle: "Figma Make Cursor 워크플로 2026" 검색
- [A6-resources] 결제 기능까지 포함한 Next.js OTT 클론 한국어 자료 추가 탐색 — why: 로펀 인프런 강의는 넷플릭스 클론은 포함하나 결제 기능 여부가 원문에서 확인 안 됨. 프로젝트2 요건(결제 포함)을 완전히 충족하는 자료를 찾지 — angle: "Next.js 구독결제 OTT 클론 토스페이먼츠 정기결제 2025" 검색
- [A6-resources] React Native/Expo 넷플릭스 클론 + 로그인 확실한 자료 확인 — why: notjust.dev와 GitHub 저장소 모두 로그인 기능 포함 여부가 불확실하거나 설명-실제 불일치가 있어 프로젝트3 요건을 완전히 충족하는 — angle: "Expo Router authentication netflix clone tutorial 2025 2026