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
- **AI credits(Figma)** — Figma의 AI 기능을 쓸 때마다 깎이는 사용량 포인트. Professional Full 시트 월 3,000, Dev·Collab·View 시트는 공통 월 500이다(2026-07 기준). 자세히: [How AI credits work](https://help.figma.com/hc/en-us/articles/33459875669015-How-AI-credits-work)
- **Ask 모드(Chat)** — 코드는 건드리지 않고 질문·설명만 주고받는 읽기 전용 대화 모드. 자세히: [Ask 모드 문서](https://cursor.com/help/ai-features/ask-mode)
- **Auth(Supabase)** — 회원가입·로그인·비밀번호 재설정을 대신 처리해 주는 Supabase의 '경비실' 모듈. 자세히: [Auth 개요](https://supabase.com/docs/guides/auth)
- **Cmd/Ctrl+K(Inline Edit)** — 코드 일부를 선택하고 단축키를 눌러 채팅창 없이 그 자리에서 바로 고치는 기능. 문서에 포스트잇을 붙여 국소 수정을 지시하는 느낌. 자세히: [Inline Edit 문서](https://cursor.com/docs/inline-edit/overview)
- **CSS Selector** — HTML 페이지 안에서 원하는 부분(제목·가격 등)을 콕 집어 가리키는 주소 같은 표현. 크롤링에서 '어디를 뽑을지' 지정할 때 쓴다. 자세히: [n8n HTML 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.html/)
- **Cursor Rules(.mdc) · AGENTS.md** — AI에게 '우리 프로젝트는 이렇게 코딩해줘'라고 미리 적어 두는 규칙 파일. 세밀한 규칙은 `.cursor/rules` 폴더의 .mdc 파일로, 간단한 지침은 프로젝트 최상단의 AGENTS.md 한 장으로 쓴다. 자세히: [Rules 문서](https://cursor.com/docs/rules)
- **Dev Mode(Figma)** — 디자이너가 만든 화면의 치수·색상·스펙을 개발자와 AI가 읽기 좋게 보여주는 전용 보기 모드(단축키 Shift+D). 자세히: [Cursor and Figma 연동 가이드](https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server)
- **Dev seat / Full seat / View·Collab seat** — Figma 유료 플랜의 좌석 등급. Full은 전체 기능, Dev는 개발자용(드래프트 밖에서는 읽기 전용), View/Collab은 보기·댓글만. MCP를 실습 수준으로 쓰려면 Dev 시트 이상이 필요하다. 자세히: [Figma 요금](https://www.figma.com/pricing/)
- **Expo / Expo Router** — React Native(자바스크립트로 아이폰·안드로이드 앱을 만드는 기술)를 더 쉽게 쓰게 해 주는 도구 모음과 그 화면 이동 관리 기능. Protected Routes로 '로그인 안 하면 못 들어가는 화면'을 만들 수 있다. 자세히: [Expo 소셜 로그인 가이드](https://supabase.com/docs/guides/auth/quickstarts/with-expo-react-native-social-auth)
- **Figma Make** — Figma 안에서 채팅 지시만으로 동작하는 웹앱·프로토타입을 만들어 주는 AI 도구(Full 시트 포함). Cursor 연동(MCP)과는 별개 제품이며, 세밀한 코드 제어는 어렵다. 자세히: [Explore Figma Make](https://help.figma.com/hc/en-us/articles/31304412302231-Explore-Figma-Make)
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

<!-- PAGE-BREAK: faq -->

# 6. FAQ & 트러블슈팅

막히는 순간 가장 먼저 열어볼 페이지입니다. 증상이나 궁금증을 주제별로 찾아보세요. 답은 모두 2026-07-23에 공식 문서에서 확인한 사실만 담았고, 요금·한도 숫자는 2026-07 기준입니다.

## 세팅 (설치·연결)

**Q.** Figma MCP를 Cursor에 연결하는 공식적으로 맞는 방법이 뭔가요?
**A.** Cursor의 에이전트 채팅창에 `/add-plugin figma`를 입력해 Figma 플러그인을 설치한 뒤, 설정의 Installed MCP Servers에서 Connect를 눌러 Figma 계정으로 인증하면 됩니다. 참고로 Figma 가이드는 이 메뉴를 'Settings > Tools & MCP'로, Cursor 최신 문서는 'Customize' 페이지로 부르는데, 2026-06 UI 개편으로 명칭이 병존할 뿐 절차는 같습니다. 자세히: [Cursor and Figma 연동 가이드](https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server), [Cursor MCP 문서](https://cursor.com/docs/mcp)

**Q.** 원격(remote) 서버와 데스크톱 서버 중 어느 것을 먼저 세팅해야 하나요?
**A.** Figma 공식 권장은 원격 서버(mcp.figma.com/mcp)입니다. 데스크톱 앱 설치 없이 쓸 수 있고 접속 시 Figma 로그인(OAuth)만 거치면 됩니다. 데스크톱 서버(127.0.0.1:3845/mcp)는 데스크톱 앱의 Dev Mode에서 별도로 켜는 방식입니다. 자세히: [원격 서버 설치](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)

**Q.** VS Code에서 쓰던 mcp.json을 그대로 복사했는데 Cursor가 인식을 못 해요.
**A.** 설정 파일의 최상위 키 이름이 다르기 때문입니다. Cursor는 `"mcpServers"`, VS Code는 `"servers"`를 쓰므로 편집기를 바꿀 때 키 이름을 함께 바꿔야 합니다. 자세히: [데스크톱 서버 설치 가이드](https://developers.figma.com/docs/figma-mcp-server/local-server-installation/)

**Q.** MCP 서버를 등록하면 설정이 어디에 저장되나요?
**A.** 지금 프로젝트에서만 쓰려면 프로젝트 폴더 안 `.cursor/mcp.json`, 모든 프로젝트 공용이면 홈 폴더의 `~/.cursor/mcp.json`입니다. 설정 UI로 넣어도 되고 이 파일을 직접 편집해도 됩니다. 자세히: [Cursor MCP 문서](https://cursor.com/docs/mcp)

**Q.** Cursor 에디터 화면(메뉴·버튼)을 한국어로 바꿀 수 있나요?
**A.** 공식 설치·도움말 문서에는 에디터 UI를 한국어로 바꾸는 설정이 확인되지 않습니다. 웹사이트(cursor.com)는 한국어를 지원하지만 앱과는 별개이므로, 영어 UI 기준으로 시작한다고 생각하는 편이 안전합니다. 자세히: [Cursor 설치 문서](https://cursor.com/help/getting-started/install)

**Q.** Cursor에서 Supabase를 쓰려면 무슨 프로그램을 따로 설치해야 하나요?
**A.** 프로그램 설치가 아니라 설정 몇 줄이면 됩니다. `.cursor/mcp.json`에 `{"mcpServers":{"supabase":{"url":"https://mcp.supabase.com/mcp"}}}`를 추가하는 URL 방식이 현재 공식 방법입니다. 자세히: [Supabase MCP 문서](https://supabase.com/docs/guides/getting-started/mcp)

## 요금·플랜

**Q.** 무료(Starter) 플랜에서도 Figma MCP를 쓸 수 있나요?
**A.** 켤 수는 있지만 월 6회 호출 제한(2026-07 기준)이라 사실상 개념 체험용입니다. 실습을 이어가려면 유료 플랜의 Dev 또는 Full 시트가 필요하며, Professional Dev 시트($12/월, 연간 청구, 2026-07 기준)면 1일 200회까지 쓸 수 있습니다. 자세히: [Rate limits & access](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/), [Figma 요금](https://www.figma.com/pricing/)

**Q.** Framelink 같은 커뮤니티 MCP를 쓰면 무료 플랜의 월 6회 제한을 피할 수 있나요?
**A.** 아니요. 커뮤니티 도구도 결국 개인 액세스 토큰으로 같은 Figma REST API를 호출하기 때문에, Starter 플랜 파일에는 똑같이 월 6회 제한이 걸립니다. '무료 우회'는 통념과 달리 불가능합니다. 자세히: [Framelink 저장소](https://github.com/GLips/Figma-Context-MCP), [Rate limits & access](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/)

**Q.** AI가 Figma 캔버스에 직접 그려 주는 기능(write to canvas)도 무료인가요?
**A.** 지금은 베타 기간이라 무료입니다. 다만 Figma가 향후 사용량 기반 유료 기능으로 전환할 계획이라고 공식적으로 밝혔으므로, 나중에 요금이 붙을 수 있다는 점을 감안하세요. 자세히: [Figma MCP FAQs](https://help.figma.com/hc/en-us/articles/39252411778583-Figma-MCP-server-FAQs)

**Q.** Figma MCP를 쓰면 Figma AI credits가 줄어드나요?
**A.** 공식 미공개입니다. credits를 소모하는 기능 목록에 MCP·Dev Mode 항목이 없어 소모하지 않을 가능성이 높지만, '소모하지 않는다'는 확정 문장도 공식 문서에 없어 확인 불가로 남습니다. 자세히: [How AI credits work](https://help.figma.com/hc/en-us/articles/33459875669015-How-AI-credits-work)

**Q.** Cursor 무료(Hobby) 플랜으로 하루에 AI를 몇 번이나 쓸 수 있나요?
**A.** 공식 요금 페이지는 'Limited Agent requests / Limited Tab completions'라는 표현만 쓰고 정확한 숫자는 공개하지 않습니다(2026-07 기준). 인터넷에 도는 구체적인 횟수는 공식 근거가 없으므로, 본인 계정 대시보드의 사용량 화면으로 확인하는 것이 정확합니다. 자세히: [Cursor 요금](https://cursor.com/pricing)

## Figma MCP 활용

**Q.** 화면 전체를 한 번에 선택해서 코드를 뽑으면 안 되나요?
**A.** 대형 프레임을 통째로 요청하면 느려지거나 오류가 나거나 응답이 불완전해질 수 있습니다. 공식 권장은 카드·헤더 같은 컴포넌트(재사용 단위) 단위로 잘게 쪼개서 요청하는 것입니다. 자세히: [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide)

**Q.** 디자인 파일을 어떻게 만들어 두면 코드가 잘 나오나요?
**A.** 버튼·카드처럼 반복되는 요소는 컴포넌트로 만들고, 간격·색상·타이포그래피는 변수(variable)로 관리하고, 레이어 이름을 'Group 5' 대신 'CardContainer'처럼 의미 있게 짓고, Auto Layout(화면 크기에 따라 자동 정렬되는 기능)을 쓰는 것이 공식 best practice입니다. 자세히: [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide)

**Q.** Figma Make와 Figma MCP(Cursor 연동)는 같은 건가요?
**A.** 다릅니다. Figma Make는 Figma 안에서 프롬프트만으로 앱을 만들어 주는 자체 실행형 도구(Full 시트 포함)이고, MCP 서버는 디자인 정보를 Cursor 같은 외부 에디터에 넘겨 그쪽에서 코드를 짜게 하는 연결 통로입니다. 공식 문서도 둘을 별개 제품으로 소개합니다. 자세히: [Explore Figma Make](https://help.figma.com/hc/en-us/articles/31304412302231-Explore-Figma-Make), [Guide to the Figma MCP server](https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server)

## Cursor 활용

**Q.** Tab, Cmd/Ctrl+K, Ask, Agent — 언제 뭘 쓰나요?
**A.** 타이핑 중 자동완성은 Tab, 선택한 코드 몇 줄만 그 자리에서 고칠 땐 Cmd/Ctrl+K, 코드를 안 바꾸고 질문·탐색만 할 땐 Ask 모드, 여러 파일 수정과 명령 실행까지 맡길 땐 Agent 모드입니다. '읽기만 = Ask, 고치기 = Agent'로 기억하면 됩니다. 자세히: [Cursor Quickstart](https://cursor.com/docs/get-started/quickstart)

**Q.** 예전 자료에 나오는 .cursorrules 파일을 지금도 써야 하나요?
**A.** 현재 공식 문서에는 .cursorrules 언급 자체가 없습니다. 대신 `.cursor/rules` 폴더의 .mdc 파일(세밀한 규칙) 또는 프로젝트 최상단의 AGENTS.md(간단한 지침) 두 가지가 공식 형식입니다. 자세히: [Rules 문서](https://cursor.com/docs/rules)

## Supabase

**Q.** 무료 플랜 프로젝트를 한동안 안 쓰면 어떻게 되나요?
**A.** 1주일간 API 요청이 없으면 프로젝트가 자동으로 일시정지됩니다(2026-07 기준, 공식 요금 정책). 실습 기간에는 최소 주 1회 접속해 요청을 일으키는 습관을 들이면 정지를 피할 수 있습니다.

**Q.** RLS를 켰더니 데이터가 하나도 안 보여요. 고장난 건가요?
**A.** 정상 동작입니다. RLS는 정책(policy)이 모든 조회에 자동으로 조건(WHERE절)을 붙이는 방식이라, 정책을 만들기 전에는 접근이 허용되지 않습니다. '누가 어떤 행을 볼 수 있는지' 정책을 추가하면 다시 보입니다. 자세히: [RLS 문서](https://supabase.com/docs/guides/database/postgres/row-level-security)

**Q.** 구글 로그인 버튼 하나 달려고 코드를 많이 짜야 하나요?
**A.** 대부분은 코드가 아니라 설정 작업입니다. Google 콘솔에서 OAuth 클라이언트를 만들어 리다이렉트 주소를 등록하고, 발급된 Client ID/Secret을 Supabase 대시보드의 Google provider 화면에 붙여넣는 것이 핵심입니다. 자세히: [Login with Google](https://supabase.com/docs/guides/auth/social-login/auth-google)

**Q.** Next.js가 아니라 React Native(Expo) 앱에서도 Supabase 로그인을 쓸 수 있나요?
**A.** 가능합니다. React Native/Expo 전용 공식 quickstart가 따로 있고, Expo Router의 protected routes(로그인 안 한 사용자를 차단하는 자동 문지기)와 소셜 로그인을 함께 다루는 공식 가이드도 있습니다. 자세히: [React Native quickstart](https://supabase.com/docs/guides/auth/quickstarts/react-native), [Expo 소셜 로그인 가이드](https://supabase.com/docs/guides/auth/quickstarts/with-expo-react-native-social-auth)

**Q.** 로그인 화면을 기성품 컴포넌트(@supabase/auth-ui-react)로 만들어도 되나요?
**A.** 권장하지 않습니다. 해당 저장소는 2025-10-23 아카이브(읽기 전용) 처리됐고 2024-02부터 유지보수 중단이 공지된 상태입니다. 새 프로젝트라면 공식 Auth 문서 기준으로 로그인 화면을 직접 구성하는 편이 안전합니다. 자세히: [Auth 개요](https://supabase.com/docs/guides/auth)

## n8n·크롤링

**Q.** n8n은 완전 무료인가요?
**A.** 직접 설치(셀프호스트)하는 Community Edition은 무료입니다. 회사가 운영해 주는 Cloud는 유료로, Starter가 20유로/월(연간 결제, 월 2,500회 실행, 2026-07 기준)이며 Starter/Pro는 신용카드 없이 체험할 수 있습니다. 자세히: [n8n 요금](https://n8n.io/pricing/)

**Q.** 비개발자인데 Docker 셀프호스팅을 꼭 배워야 하나요?
**A.** 공식 문서 스스로가 셀프호스트를 서버·보안 역량을 갖춘 'expert users'에게 권장합니다. 비개발자는 카드 등록 없이 되는 Cloud 체험으로 시작하고, 셀프호스팅은 자동화에 익숙해진 뒤로 미루는 편이 현실적입니다. 자세히: [Install with Docker](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker)

**Q.** 강의·블로그에 나오는 'HTML Extract 노드'가 문서에 없어요.
**A.** 버전 0.213.0부터 이름이 'HTML' 노드로 바뀌었을 뿐입니다. CSS Selector로 원하는 데이터를 뽑는 기능은 동일하니 HTML 노드 문서를 그대로 따라 하면 됩니다. 자세히: [HTML 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.html/)

**Q.** 아무 사이트나 크롤링해서 데이터를 모아도 법적으로 괜찮나요?
**A.** 주의가 필요합니다. robots.txt는 법적 강제력이 없는 안내문일 뿐이고, 개인정보가 섞인 데이터를 모으면 GDPR 같은 개인정보 보호법이 적용될 수 있습니다(EDPB 2026-07 가이드라인). 한국에는 크롤링 전용 종합 가이드라인이 없음을 확인했으며, 개인정보보호위원회의 2024-07 AI 안내서가 가장 가까운 공식 참고자료입니다. 자세히: [robots.txt 소개](https://developers.google.com/search/docs/crawling-indexing/robots/intro), [EDPB 가이드라인](https://www.edpb.europa.eu/system/files/2026-07/edpb_guidelines_2020603_webscraping_v1_en_0.pdf)

**Q.** 크롤링으로 모은 데이터는 어디에 쌓아야 하나요?
**A.** n8n 공식 템플릿 갤러리에 HTTP Request로 모은 데이터를 Supabase 테이블과 Google Sheets에 동시에 적재하는 예시 워크플로가 있어 그대로 참고할 수 있습니다. 이 가이드의 스택(Supabase)과도 맞아떨어지는 구성입니다. 자세히: [공식 템플릿 예시](https://n8n.io/workflows/14996-aggregate-multi-source-job-boards-to-supabase-and-google-sheets/)

## 결제 (토스페이먼츠)

**Q.** 사업자 등록 없이도 결제 연동을 연습할 수 있나요?
**A.** 네. 이메일·전화번호만으로 가입하는 '개발 연동 체험 상점' 단계에서 API 로그 확인, 웹훅 연결, 가상계좌 모의입금까지 됩니다. 테스트 결제는 가상으로만 승인되어 실제 돈이 빠져나가지 않으며, 테스트 환경 API는 분당 100건 제한(2026-07 기준)이 있습니다. 자세히: [사업자번호 없이 결제 테스트하기](https://docs.tosspayments.com/blog/how-to-test-toss-payments)

**Q.** 테스트 결제는 성공했는데 정산 내역이 안 보여요.
**A.** 정산 기록은 라이브(실서비스) 환경에서만 조회됩니다. 또 테스트용 가상계좌는 번호 앞에 'X'가 붙는 가짜 계좌라 실제 입금도 불가능합니다. 학습 목표를 '결제 흐름 이해'까지로 한정하세요. 자세히: [환경 설정하기](https://docs.tosspayments.com/guides/v2/get-started/environment)

**Q.** 인터넷 튜토리얼이 v1인지 v2인지 어떻게 구분하나요? 따라 했더니 updateAmount is not a function 에러가 나요.
**A.** import 문을 보면 됩니다. `@tosspayments/payment-widget-sdk`(loadPaymentWidget)가 보이면 구버전 v1, `@tosspayments/tosspayments-sdk`(loadTossPayments)면 v2입니다. v2는 updateAmount()를 없애고 setAmount()로 바꿨기 때문에 v1 예제를 v2에 섞으면 이 에러가 납니다. 2023~24년 한국어 자료 상당수가 v1 기준이니 실습 전 버전부터 확인하세요. 자세히: [v1 → v2 마이그레이션 가이드](https://docs.tosspayments.com/guides/v2/get-started/migration-guide)

**Q.** 카카오페이로 테스트했는데 결제 수단이 안 붙어요.
**A.** 카카오페이는 일반 테스트 키로는 연동이 안 되고, 전자결제 계약 후 발급되는 상점 전용 테스트 키로만 가능합니다. 페이코도 테스트 키 대신 라이브 키로만 테스트해야 하므로, 학습 단계에서는 다른 결제수단으로 먼저 연습하세요. 자세히: [환경 설정하기](https://docs.tosspayments.com/guides/v2/get-started/environment)

**Q.** 정기결제(빌링)를 연동하면 매달 자동으로 결제되나요?
**A.** 아니요. 토스페이먼츠는 빌링키 발급·승인 API만 제공하고 '며칠에 결제를 실행하라'는 스케줄링은 개발자가 서버에서 직접 구현해야 합니다. 또 실서비스 사용에는 리스크 검토와 별도 계약이 필요하고, 정기 구독형 서비스가 아니면 정책상 제한됩니다. 자세히: [자동결제(빌링) 연동](https://docs.tosspayments.com/guides/v2/billing/integration)

**Q.** 테스트 키만으로 정기결제 전체 흐름(카드 등록→빌링키→자동 승인)을 끝까지 확인할 수 있나요?
**A.** 가능합니다. 테스트 환경에서는 본인인증 문자 대신 인증번호 000000을 입력하고, 카드번호 앞 6자리(BIN)만 유효하면 등록되므로 실제 카드 없이 전체 플로우를 연습할 수 있습니다. 단, 빌링은 국내 발급 카드만 지원해 해외카드 케이스는 테스트할 수 없습니다. 자세히: [자동결제(빌링) 연동](https://docs.tosspayments.com/guides/v2/billing/integration)

**Q.** Cursor에 토스페이먼츠 MCP를 설치했는데 AI가 자꾸 v1 코드를 짜 줘요.
**A.** MCP는 버전을 지정하지 않으면 v2 문서(get-v2-documents)를 기본으로 검색하고, v1 문서는 명시적으로 요청할 때만 씁니다. 따라서 프롬프트에 "V2 SDK(@tosspayments/tosspayments-sdk) 기준으로 짜줘"처럼 버전을 못 박는 것이 가장 확실합니다. 자세히: [AI 도구로 결제 연동하기](https://docs.tosspayments.com/guides/v2/get-started/llms-guide)

**Q.** 토스페이먼츠 공식 샘플에 Next.js가 없는데 어떻게 하나요?
**A.** 맞습니다. 공식 샘플 저장소에는 Express+React 등만 있고 Next.js 전용 샘플은 없는 것으로 확인됐습니다. Next.js 환경의 결제위젯 연동(단건결제)은 2024-01 velog 튜토리얼이 있으니 참고하고, 서버 승인 로직은 공식 v2 가이드를 기준으로 옮기세요. 자세히: [tosspayments-sample](https://github.com/tosspayments/tosspayments-sample), [Next.js 결제위젯 예시](https://velog.io/@sanghyeon/토스-페이먼츠-API를-이용한-결제-위젯-구현하기-Feat.-NextJS-TypeScript)

**Q.** 넷플릭스 같은 구독 서비스를 Next.js로 만드는 완성형 한국어 튜토리얼이 있나요?
**A.** 2026-07-23 기준 딱 맞는 단일 한국어 자료는 없음을 확인했습니다. 토스페이먼츠 공식 블로그의 '구독 결제 서비스 구현하기'(백엔드 로직, Express 기반)와 v2 빌링 가이드를 조합하는 것이 현실적 경로이고, 영어 자료로는 Next.js+Stripe 조합의 최신 가이드와 Vercel 공식 스타터가 있습니다. 자세히: [구독 결제 구현(공식 블로그)](https://docs.tosspayments.com/blog/subscription-service-1), [Stripe+Next.js 가이드](https://www.pedroalonso.net/blog/stripe-nextjs-complete-guide-2025/), [nextjs/saas-starter](https://github.com/nextjs/saas-starter)

---
> 📌 이 페이지의 모든 요금·절차는 2026-07-23에 공식 문서에서 직접 확인했습니다.
