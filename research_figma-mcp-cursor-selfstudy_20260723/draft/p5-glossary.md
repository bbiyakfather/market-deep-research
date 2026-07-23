# 5. 개념 사전

가이드를 읽다가 모르는 말이 나오면 이 페이지에서 찾아보세요(Ctrl+F / Cmd+F 검색 추천). 한글 용어는 가나다순, 영문 용어는 ABC순입니다. 풀이는 비유 중심의 한 줄로 통일했고, 요금·한도 숫자는 모두 2026-07 기준입니다.

## 한글 용어 (가나다순)

- **결제위젯(Payment Widget)** — 카드·간편결제 등 여러 결제수단을 한 화면에 모아 주는, 토스페이먼츠가 미리 만들어 둔 '완제품 결제 화면 부품'. 주문서에 직접 넣는 주문서형과 버튼 클릭 시 팝업으로 뜨는 결제창형이 있다. 자세히: [결제위젯 이해하기](https://docs.tosspayments.com/guides/v2/payment-widget)
- **노드(Node)** — 자동화 워크플로를 이루는 레고 블록 하나. 예: '웹 요청 보내기' 블록, 'HTML에서 데이터 뽑기' 블록. 자세히: [n8n HTML 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.html/)
- **빌링키(Billing Key)** — 손님의 카드번호를 대신하는 암호화된 열쇠. 매달 자동결제할 때 카드번호 대신 이 값을 쓴다. 자세히: [자동결제(빌링) 이해하기](https://docs.tosspayments.com/guides/v2/billing)
- **셀프호스팅(self-host)** — 회사가 운영해 주는 클라우드 대신 내 컴퓨터나 내가 빌린 서버에 프로그램을 직접 설치해 돌리는 방식. n8n은 Docker(프로그램과 실행 환경을 통째로 포장해 어느 컴퓨터에서든 똑같이 돌리는 컨테이너 기술)로 셀프호스팅하면 무료다(2026-07 기준). 자세히: [Install with Docker](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker)
- **시크릿 키(Secret Key)** — 서버에서 결제를 최종 승인할 때만 쓰는 비밀 열쇠. 금고 열쇠처럼 절대 화면 코드(외부)에 노출하면 안 된다. 자세히: [환경 설정하기](https://docs.tosspayments.com/guides/v2/get-started/environment)
- **아카이브(Archived) 저장소** — GitHub(코드 창고 서비스)에서 '읽기 전용'으로 잠근 코드 창고. 기존 코드는 볼 수 있지만 버그가 나도 더는 고쳐 주지 않으므로 새 학습 자료로는 피한다. 자세히: [supabase-community/auth-ui](https://github.com/supabase-community/auth-ui)
- **워크플로(Workflow)** — 노드(작업 블록)를 순서대로 이어 붙인 자동화 조립 라인 전체. 자세히: [n8n HTTP Request 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)
- **웹훅(Webhook)** — '입금 완료' 같은 사건이 생기면 토스페이먼츠 쪽에서 우리 서버로 먼저 전화를 걸어 알려주는 자동 알림. 자세히: [사업자번호 없이 결제 테스트하기](https://docs.tosspayments.com/blog/how-to-test-toss-payments)
- **정산** — 손님이 낸 돈이 실제 내 사업자 계좌로 들어오는 절차. 테스트 환경에서는 확인할 수 없다. 자세히: [환경 설정하기](https://docs.tosspayments.com/guides/v2/get-started/environment)
- **클라이언트 키(Client Key)** — 화면(브라우저)에서 결제위젯을 띄울 때 쓰는 공개용 열쇠. 노출돼도 되는 '가게 명함' 같은 것. 자세히: [환경 설정하기](https://docs.tosspayments.com/guides/v2/get-started/environment)
- **클론코딩** — 에어비앤비·넷플릭스처럼 이미 있는 서비스를 그대로 따라 만들며 배우는 학습 방식. 명화를 모사하며 그림을 배우는 것과 같다. 자세히: [노마드코더 에어비앤비 클론](https://nomadcoders.co/airbnb-clone)
- **테스트 키 / 라이브 키** — 테스트 키는 가짜 돈으로 연습하는 모드, 라이브 키는 진짜 손님 돈이 오가는 운영 모드. 자세히: [환경 설정하기](https://docs.tosspayments.com/guides/v2/get-started/environment)
- **풀스택(Full-stack)** — 화면(프론트엔드)과 서버·데이터베이스(백엔드)를 모두 직접 만드는 것. 자세히: [Supabase 풀스택 클론 강의](https://www.inflearn.com/course/%EC%9A%94%EC%A6%98%EC%97%94-supabase-%EB%8C%80%EC%84%B8%EC%A7%80-nextjs-%ED%81%B4%EB%A1%A0%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8)

## 영문 용어 (ABC순)

- **Agent 모드(Cursor)** — AI가 여러 파일을 스스로 찾아 고치고 터미널 명령까지 실행하며 일을 끝까지 해내는 자율 모드. '알아서 해줘'에 해당한다. 자세히: [Agent 문서](https://cursor.com/docs/agent/overview)
- **AI credits(Figma)** — Figma의 AI 기능을 쓸 때마다 깎이는 사용량 포인트. Full 시트 기준 Professional 월 3,000, Organization 월 3,500, Enterprise 월 4,250이다(2026-07 기준). MCP 호출이 이 credits를 소모하는지는 공식 문서에 명시가 없다. 자세히: [How AI credits work](https://help.figma.com/hc/en-us/articles/33459875669015-How-AI-credits-work)
- **Ask 모드(Chat)** — 코드는 건드리지 않고 질문·설명만 주고받는 읽기 전용 대화 모드. 자세히: [Ask 모드 문서](https://cursor.com/help/ai-features/ask-mode)
- **Auth(Supabase)** — 회원가입·로그인·비밀번호 재설정을 대신 처리해 주는 Supabase의 '경비실' 모듈. 자세히: [Auth 개요](https://supabase.com/docs/guides/auth)
- **Cmd/Ctrl+K(Inline Edit)** — 코드 일부를 선택하고 단축키를 눌러 채팅창 없이 그 자리에서 바로 고치는 기능. 문서에 포스트잇을 붙여 국소 수정을 지시하는 느낌. 자세히: [Inline Edit 문서](https://cursor.com/docs/inline-edit/overview)
- **CSS Selector** — HTML 페이지 안에서 원하는 부분(제목·가격 등)을 콕 집어 가리키는 주소 같은 표현. 크롤링에서 '어디를 뽑을지' 지정할 때 쓴다. 자세히: [n8n HTML 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.html/)
- **Cursor Rules(.mdc) · AGENTS.md** — AI에게 '우리 프로젝트는 이렇게 코딩해줘'라고 미리 적어 두는 규칙 파일. 세밀한 규칙은 `.cursor/rules` 폴더의 .mdc 파일로, 간단한 지침은 프로젝트 최상단의 AGENTS.md 한 장으로 쓴다. 자세히: [Rules 문서](https://cursor.com/docs/rules)
- **Dev Mode(Figma)** — 디자이너가 만든 화면의 치수·색상·스펙을 개발자와 AI가 읽기 좋게 보여주는 전용 보기 모드(단축키 Shift+D). 자세히: [Cursor and Figma 연동 가이드](https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server)
- **Dev seat / Full seat / View·Collab seat** — Figma 유료 플랜의 좌석 등급. Full은 전체 기능, Dev는 개발자용(드래프트 밖에서는 읽기 전용), View/Collab은 보기·댓글만. MCP를 실습 수준으로 쓰려면 Dev 시트 이상이 필요하다. 자세히: [Figma 요금](https://www.figma.com/pricing/)
- **Expo / Expo Router** — React Native(자바스크립트로 아이폰·안드로이드 앱을 만드는 기술)를 더 쉽게 쓰게 해 주는 도구 모음과 그 화면 이동 관리 기능. Protected Routes로 '로그인 안 하면 못 들어가는 화면'을 만들 수 있다. 자세히: [Expo 소셜 로그인 가이드](https://supabase.com/docs/guides/auth/quickstarts/with-expo-react-native-social-auth)
- **Figma Make** — Figma 안에서 채팅 지시만으로 동작하는 웹앱·프로토타입을 만들어 주는 AI 도구(유료 플랜 Full 시트 대상). 기존 Figma 디자인을 첨부해 쓸 수 있으며, Cursor 연동(MCP)과는 별개 제품이다. 자세히: [Explore Figma Make](https://help.figma.com/hc/en-us/articles/31304412302231-Explore-Figma-Make)
- **GDPR** — 유럽연합의 개인정보 보호법. 크롤링한 데이터에 유럽 이용자의 개인정보가 섞이면 수집한 쪽에도 적용될 수 있다. 자세히: [EDPB 웹스크래핑 가이드라인](https://www.edpb.europa.eu/system/files/2026-07/edpb_guidelines_2020603_webscraping_v1_en_0.pdf)
- **Hobby / Pro 플랜(Cursor)** — Cursor의 무료 등급(Hobby)과 월 $20 유료 등급(Pro)(2026-07 기준). Hobby의 사용량 한도는 'Limited'로만 표기되고 정확한 숫자는 공식 미공개다. 자세히: [Cursor 요금](https://cursor.com/pricing)
- **HTTP Request** — 웹사이트나 API 서버에 "데이터 주세요"라고 보내는 표준 주문서. n8n 크롤링의 시작 노드다. 자세히: [HTTP Request 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)
- **MAU(Monthly Active Users)** — 한 달 동안 실제로 로그인·활동한 사용자 수. Supabase 무료 플랜은 5만 MAU까지 지원한다(2026-07 기준). 자세히: [Supabase 요금](https://supabase.com/pricing)
- **MCP(Model Context Protocol)** — AI가 Figma·토스페이먼츠 같은 외부 도구·문서와 표준화된 방식으로 대화하게 해 주는 연결 규격. 'AI용 USB-C 단자'라는 비유가 널리 쓰인다. 자세히: [Figma MCP 서버 소개](https://developers.figma.com/docs/figma-mcp-server/)
- **mcp.json** — 에디터에 '어떤 MCP 서버에 어떻게 접속할지' 적어 두는 주소록 같은 설정 파일. Cursor는 프로젝트의 `.cursor/mcp.json` 또는 홈 폴더의 `~/.cursor/mcp.json`에 둔다. 자세히: [Cursor MCP 문서](https://cursor.com/docs/mcp)
- **n8n** — 여러 앱과 웹사이트를 블록(노드)으로 이어 반복 작업을 자동으로 처리해 주는 오픈소스 자동화 도구. 자세히: [n8n 요금](https://n8n.io/pricing/)
- **OAuth / 소셜 로그인** — 구글 같은 다른 서비스 계정으로 클릭 한 번에 로그인하게 해 주는 방식. 자세히: [Login with Google](https://supabase.com/docs/guides/auth/social-login/auth-google)
- **Personal access token(개인 액세스 토큰)** — 코드나 커뮤니티 MCP 서버가 내 Figma 데이터를 대신 읽을 수 있게 발급하는 출입증. 커뮤니티 도구도 이 토큰으로 같은 Figma API를 호출하므로 무료 플랜의 호출 제한을 그대로 받는다. 자세히: [Figma REST API rate limits](https://developers.figma.com/docs/rest-api/rate-limits/)
- **Rate limit(요청 제한)** — 일정 기간(월/일/분) 동안 허용되는 호출 횟수의 상한선. Figma MCP는 Starter 월 6회, Professional Dev/Full 시트 1일 200회다(2026-07 기준). 자세히: [Rate limits & access](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/)
- **Remote / Desktop MCP 서버(Figma)** — 원격(Remote) 서버는 Figma가 직접 운영하는 서버(mcp.figma.com/mcp, 공식 권장), 데스크톱 서버는 내 컴퓨터의 Figma 앱이 켜 주는 로컬 서버(127.0.0.1:3845/mcp)다. 자세히: [원격 서버 설치](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)
- **RLS(Row Level Security)** — 표의 줄(행)마다 '누가 이 줄을 보고 고칠 수 있는지'를 데이터베이스가 직접 지키는 보안 규칙. 켜는 순간 정책(policy)을 만들기 전까지 아무것도 안 보이는 것이 정상이다. 자세히: [RLS 문서](https://supabase.com/docs/guides/database/postgres/row-level-security)
- **robots.txt** — 웹사이트가 "여기는 자동으로 긁어가지 마세요"라고 크롤러에게 붙여 둔 안내문. 법적 강제력은 없다. 자세히: [robots.txt 소개](https://developers.google.com/search/docs/crawling-indexing/robots/intro)
- **Tab(Cursor)** — 타이핑 중 다음 코드를 회색 글씨로 미리 보여주고 Tab 키로 받아들이는 AI 자동완성. 메신저의 문장 자동완성과 같은 원리다. 자세히: [Tab 문서](https://cursor.com/docs/tab/overview)
- **Table Editor(Supabase)** — SQL(데이터베이스 질의 언어)을 몰라도 엑셀 시트 다루듯 클릭만으로 표를 만들고 데이터를 넣는 대시보드 화면. 자세히: [Tables 문서](https://supabase.com/docs/guides/database/tables)
- **write to canvas(use_figma)** — AI가 코드 생성을 넘어 Figma 캔버스에 직접 프레임·컴포넌트를 그려 넣는 쓰기 기능. 현재 베타 기간 무료지만 향후 사용량 기반 유료 전환이 공식 예고돼 있다(2026-07 기준). 자세히: [Figma MCP FAQs](https://help.figma.com/hc/en-us/articles/39252411778583-Figma-MCP-server-FAQs)

---
> 📌 이 페이지의 모든 요금·절차는 2026-07-23에 공식 문서에서 직접 확인했습니다.
