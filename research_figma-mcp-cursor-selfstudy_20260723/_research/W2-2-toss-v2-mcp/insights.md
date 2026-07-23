# W2-2. 토스페이먼츠 SDK v2 공식 연동 절차 & 토스페이먼츠 MCP 서버 조사

- axis: W2-2-toss-v2-mcp
- observed_at: 2026-07-23
- 프로토콜: WebSearch 탐색 → 후보는 WebFetch 원문 열람 후 등재. docs.tosspayments.com은 React SPA라 일반 HTML 렌더링으로는 네비게이션만 잡히는 경우가 많아, 공식 문서가 제공하는 **"URL 끝에 `.md`를 붙이면 원문 markdown을 받을 수 있다"**는 자기 문서화 기능(F7~F10 참고)을 활용해 원문을 확인함. 일부 페이지(`payment-widget/integration.md`)는 `.md` 경로가 404였고, r.jina.ai 프록시 경유로 원문 확인.

---

## 사실(Facts)

### Q1. SDK v2 결제위젯 quickstart

**F1. SDK v2 설치 명령**
- statement: 토스페이먼츠 SDK v2(`@tosspayments/tosspayments-sdk`)는 스크립트 태그 또는 npm 패키지로 설치하며, npm 명령은 `npm install @tosspayments/tosspayments-sdk --save`이다.
- risk: normal
- primary_source: docs.tosspayments.com (SDK v2 reference)
- evidence:
  - quote: "npm install @tosspayments/tosspayments-sdk --save"
    locator: "토스페이먼츠 JavaScript SDK > SDK 설치 방법 > npm 패키지 설치"
    url: https://docs.tosspayments.com/sdk/v2/js
    title: 토스페이먼츠 JavaScript SDK
    source_role: 원출처
  - quote: "<script src=\"https://js.tosspayments.com/v2/standard\"></script>"
    locator: "SDK 설치 방법 > HTML 스크립트 태그 방식"
    url: https://docs.tosspayments.com/sdk/v2/js
    title: 토스페이먼츠 JavaScript SDK
    source_role: 원출처

**F2. loadTossPayments → widgets() → setAmount() → renderPaymentMethods() 핵심 흐름**
- statement: v2 연동 핵심 흐름은 `loadTossPayments()`(또는 스크립트 태그의 `TossPayments()`)로 SDK를 초기화 → `widgets({ customerKey })`로 결제위젯 인스턴스 생성 → `renderPaymentMethods()` 호출 전에 반드시 `setAmount()`로 금액을 설정 → `renderPaymentMethods({ selector, variantKey })`를 비동기로 호출해 UI를 렌더링하는 순서다.
- risk: normal
- primary_source: docs.tosspayments.com (마이그레이션 가이드 + SDK reference)
- evidence:
  - quote: "const tosspayments = TossPayments(clientKey);\nconst widgets = tosspayments.widgets({\n  customerKey,\n  brandpay?: {\n    redirectUrl: 'https://tosspayments.com/auth'\n  }\n});"
    locator: "마이그레이션하기 > 결제위젯 > (v2 코드블록)"
    url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
    title: 마이그레이션하기
    source_role: 원출처
  - quote: "await widgets.setAmount({\n  value: 10000,\n  currency: \"KRW\",\n});\n\nconst paymentMethodWidget = await widgets.renderPaymentMethods({\n  selector: \"#payment-methods\",\n  variantKey: \"widgetA\",\n});"
    locator: "마이그레이션하기 > 결제위젯 > UI 렌더링 및 결제 금액 설정 (v2 코드블록)"
    url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
    title: 마이그레이션하기
    source_role: 원출처
  - quote: "결제 금액을 설정하는 `setAmount()` 메서드가 추가되었습니다. `renderPaymentMethods()`를 호출하기 전에 해당 메서드로 반드시 결제 금액을 설정하세요."
    locator: "마이그레이션하기 > 결제위젯 > UI 렌더링 및 결제 금액 설정"
    url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
    title: 마이그레이션하기
    source_role: 원출처

**F3. requestPayment 및 서버 승인(confirm) 플로우**
- statement: 구매자가 결제수단을 고른 뒤 `widgets.requestPayment({ orderId, orderName, successUrl, failUrl, ... })`를 호출하면 결제창이 뜨고, 성공 시 `successUrl`로 `paymentKey`·`orderId`·`amount` 쿼리 파라미터와 함께 리다이렉트되며, 가맹점 서버는 이 `amount`가 최초 요청 금액과 일치하는지 검증한 뒤 시크릿 키로 `POST /v1/payments/confirm`(결제 승인 API)을 호출해 결제를 최종 완료해야 한다.
- risk: normal
- primary_source: docs.tosspayments.com (SDK v2 reference / 결제위젯 연동 가이드)
- evidence:
  - quote: "응답으로 받은 `WidgetPaymentResult` 객체에서 `paymentKey`, `orderId`, `amount` 정보를 확인하고, \"결제 승인 API를 호출하여 결제를 최종 완료\"해야 합니다."
    locator: "토스페이먼츠 JavaScript SDK > 결제 요청"
    url: https://docs.tosspayments.com/sdk/v2/js
    title: 토스페이먼츠 JavaScript SDK
    source_role: 원출처
  - quote: "Validate that the redirected `amount` parameter matches the originally set amount to prevent client-side manipulation"
    locator: "결제위젯 연동 가이드 > Important Security Notes"
    url: https://docs.tosspayments.com/guides/v2/payment-widget/integration
    title: 결제위젯(주문서형) 연동하기
    source_role: 원출처(SPA 렌더링 이슈로 r.jina.ai 프록시 경유 확인)

### Q2. v1 → v2 차이 및 마이그레이션 주의점

**F4. 통합 SDK로 전환 — v1은 서비스별 SDK 3개, v2는 1개**
- statement: v1에서는 결제위젯·브랜드페이·결제창이 각각 별도 스크립트(`/v1/payment-widget`, `/v1/brandpay`, `/v1/payment`)로 분리돼 있었으나, v2부터는 스크립트 하나(`/v2/standard`)와 SDK 하나(`@tosspayments/tosspayments-sdk`)로 모든 결제 서비스를 초기화한다. API 엔드포인트와 API 키는 v1·v2 공통으로 변경 없이 그대로 쓸 수 있다.
- risk: normal
- primary_source: docs.tosspayments.com (공식 마이그레이션 가이드)
- evidence:
  - quote: "토스페이먼츠 SDK v1에서는 결제위젯, 브랜드페이, 결제창이 각자 다른 SDK로 분리되어 있었어요... 토스페이먼츠 SDK v2부터는 모든 결제 서비스를 하나의 토스페이먼츠 SDK로 사용할 수 있어요."
    locator: "마이그레이션하기 (도입부)"
    url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
    title: 마이그레이션하기
    source_role: 원출처
  - quote: "API도 v2 엔드포인트가 나왔나요? 아니요, API는 이전과 같이 `v1` 엔드포인트를 사용하면 됩니다."
    locator: "마이그레이션하기 > FAQ"
    url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
    title: 마이그레이션하기
    source_role: 원출처

**F5. 결제위젯 API 변경점 — updateAmount 제거, 동기→비동기, ready 이벤트 제거, destroy() 추가**
- statement: v1의 `updateAmount()` 메서드는 v2에서 제거되고 `setAmount()`로 대체됐으며, `renderPaymentMethods()`/`renderAgreement()`가 동기에서 비동기(Promise)로 바뀌었다. v1의 `ready` 이벤트 및 Pro 커스텀 이벤트(`customRequest` 등)는 모두 제거되고 `paymentMethodSelect` 이벤트로 통합됐고, 렌더링된 UI를 지우는 `destroy()` 메서드가 새로 추가됐다(한 페이지에 결제수단 UI·약관 UI는 각 1개만 렌더링 가능하므로 재렌더링 전 destroy 필요).
- risk: normal
- primary_source: docs.tosspayments.com (공식 마이그레이션 가이드)
- evidence:
  - quote: "결제 금액을 별도의 메서드로 설정하기 때문에... 해당 렌더링 메서드가 비동기적으로 바뀌었습니다. 렌더링이 언제 완료되었는지 편리하게 확인할 수 있기 때문에 결제위젯 SDK v1에서 제공된 `on()` 메서드의 `ready` 이벤트가 제거됩니다."
    locator: "마이그레이션하기 > 결제위젯 > UI 렌더링 및 결제 금액 설정"
    url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
    title: 마이그레이션하기
    source_role: 원출처
  - quote: "생성한 결제 UI의 인스턴스를 삭제할 수 있는 `destroy()` 메서드가 추가됐습니다. 한 페이지 내에서 2 개 이상의 결제 UI를 렌더링할 수 없기 때문에 새로운 결제 UI를 렌더링하고 싶다면 해당 메서드로 인스턴스를 먼저 삭제해주세요."
    locator: "마이그레이션하기 > 결제위젯 > 결제 UI 삭제"
    url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
    title: 마이그레이션하기
    source_role: 원출처

**F6. v1은 여전히 필요한 경우가 있음(모바일 네이티브) + 옛 튜토리얼 주의**
- statement: v2는 아직 React Native·Flutter 같은 모바일 네이티브 SDK를 지원하지 않으므로 모바일 앱 연동은 v1을 써야 하며, 토스페이먼츠 공식 블로그의 대표 React 튜토리얼("React로 결제 페이지 개발하기", 2023.03.06 발행)조차 `@tosspayments/payment-widget-sdk`의 `loadPaymentWidget`/`updateAmount` 등 v1 API 기준으로 작성되어 있어, 학습자가 검색으로 만나는 자료 상당수가 v1일 수 있다는 점에 주의해야 한다.
- risk: normal
- primary_source: docs.tosspayments.com(마이그레이션 가이드) + tosspayments.com 공식 블로그(2023년 글, v1 예시)
- evidence:
  - quote: "v2는 React Native, Flutter 등 모바일 SDK를 지원하나요? 아니요, v2는 아직 모바일 SDK를 지원하지 않아요. 앞으로 지원할 계획은 있지만 출시되기 전까지는 SDK v1을 사용해주세요."
    locator: "마이그레이션하기 > FAQ"
    url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
    title: 마이그레이션하기
    source_role: 원출처
  - quote: "import { loadPaymentWidget, PaymentWidgetInstance } from \"@tosspayments/payment-widget-sdk\""
    locator: "React로 결제 페이지 개발하기 (2023.03.06) 코드 예시"
    url: https://www.tosspayments.com/blog/articles/paytech-4
    title: React로 결제 페이지 개발하기 (ft. 결제위젯)
    source_role: 원출처(토스페이먼츠 공식 블로그, v1 기준 게시물)

### Q3. 토스페이먼츠 MCP 서버 (Cursor+MCP 강의 주제 직결 — 상세)

**F7. 공식 MCP 서버 제공 여부 및 설치 방법**
- statement: 토스페이먼츠는 PG 업계 최초로 공식 MCP(Model Context Protocol) 서버 `@tosspayments/integration-guide-mcp`를 제공하며, `npx -y @tosspayments/integration-guide-mcp@latest` 명령으로 실행되는 JSON 설정(`mcp.json`)을 Cursor(`~/.cursor/mcp.json`, 자동 설치 딥링크 지원), VS Code(`.vscode/mcp.json`, 자동 설치 지원), Claude Code(`.mcp.json` 프로젝트 루트 또는 `~/.claude.json`), Claude Desktop(`claude_desktop_config.json`), Windsurf(`~/.codeium/windsurf/mcp_config.json`), Codex(`~/.codex/config.toml`, TOML 변환 필요) 등에 등록해 설치한다. 언론 보도에 따르면 기존 평균 1~2주(길게는 최대 3개월) 걸리던 결제 연동을 AI 도구로 약 10분 만에 마칠 수 있게 됐다고 소개된다.
- risk: normal
- primary_source: docs.tosspayments.com (공식 문서, AI 도구로 결제 연동하기)
- evidence:
  - quote: "토스페이먼츠 MCP 서버를 설치하면 AI 도구가 토스페이먼츠 docs를 직접 검색해서 답변해요. 아래 JSON 설정을 추가하면 AI 도구와 MCP 서버가 연결돼요."
    locator: "AI 도구로 결제 연동하기 > MCP 서버 활용하기"
    url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
    title: AI 도구로 결제 연동하기
    source_role: 원출처
  - quote: "{\n  \"mcpServers\": {\n    \"tosspayments-integration-guide\": {\n      \"command\": \"npx\",\n      \"args\": [\"-y\", \"@tosspayments/integration-guide-mcp@latest\"]\n    }\n  }\n}"
    locator: "AI 도구로 결제 연동하기 > MCP 서버 활용하기 (mcp.json 코드블록)"
    url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
    title: AI 도구로 결제 연동하기
    source_role: 원출처
  - quote: "개발자는 단 10분 만에 결제 연동을 마치는 새로운 개발 환경을 경험할 수 있게 됐다"
    locator: "기사 본문"
    url: https://www.itworld.co.kr/article/4008892
    title: "결제 연동 10분 시대 개막" 토스페이먼츠, AI 연동 MCP 서버 도입
    source_role: 재인용(언론 보도)

**F8. MCP 서버가 제공하는 4가지 도구**
- statement: 토스페이먼츠 MCP 서버는 (1) 버전 미지정 질문 시 자동 검색되는 V2 문서 도구 `get-v2-documents`(기본 동작), (2) "V1으로 작성해줘" 등 명시적 요청 시 쓰이는 `get-v1-documents`, (3) 결제수단·용어 질문에 쓰이는 용어집 조회 도구 `get-glossary-documents`, (4) 특정 페이지 원문 전체를 문서 ID로 조회하는 `document-by-id`, 총 4개 도구를 제공한다.
- risk: normal
- primary_source: docs.tosspayments.com (공식 문서, AI 도구로 결제 연동하기)
- evidence:
  - quote: "`get-v2-documents` — \"결제위젯 코드 짜줘\" 등 버전을 명시하지 않은 질문에 → AI가 V2 문서를 자동으로 검색해요 (기본 동작)"
    locator: "AI 도구로 결제 연동하기 > MCP 서버가 제공하는 도구 (표)"
    url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
    title: AI 도구로 결제 연동하기
    source_role: 원출처
  - quote: "`document-by-id` — 특정 페이지 디테일이 필요할 때 → AI가 문서 ID로 원본 전체를 조회해요"
    locator: "AI 도구로 결제 연동하기 > MCP 서버가 제공하는 도구 (표)"
    url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
    title: AI 도구로 결제 연동하기
    source_role: 원출처

**F9. MCP 연결 문제 해결 및 활용 예시(자연어 명령)**
- statement: 공식 문서는 "결제창을 연결해줘", "정기결제 연동하고 싶어" 류의 자연어 요청 예시로 "V2 SDK로 주문서 안에 결제위젯을 삽입하는 코드를 작성해줘", "구독 결제(빌링) 흐름을 처음부터 끝까지 만들어줘" 등을 제시하며, MCP가 잘 안 붙을 때는 (a) AI 도구의 MCP 설정 화면에서 서버 활성 상태 확인, (b) `npx` 실행 가능 여부(Node.js 설치, 회사망 npm 레지스트리 차단 여부) 확인, (c) "토스페이먼츠 MCP를 사용해서 답변해줘"처럼 명시적으로 도구 사용을 요청하라고 안내한다.
- risk: normal
- primary_source: docs.tosspayments.com (공식 문서, AI 도구로 결제 연동하기)
- evidence:
  - quote: "AI 도구의 MCP 설정 화면에서 `tosspayments-integration-guide` 서버가 활성 상태인지 확인하세요. `npx` 명령이 실행 가능한 환경인지(Node.js 설치 여부) 확인하세요. 회사 네트워크에서는 npm 레지스트리 접근이 차단될 수 있어요."
    locator: "AI 도구로 결제 연동하기 > MCP 서버 설치하기 > MCP 서버가 잘 연결되지 않을 때"
    url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
    title: AI 도구로 결제 연동하기
    source_role: 원출처
  - quote: "\"V2 SDK로 주문서 안에 결제위젯을 삽입하는 코드를 작성해줘\" / \"구독 결제(빌링) 흐름을 처음부터 끝까지 만들어줘\""
    locator: "AI 도구로 결제 연동하기 > LLM에 질문하기 > 활용 예시 > 코드 생성"
    url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
    title: AI 도구로 결제 연동하기
    source_role: 원출처

**F10. MCP 외 AI 보조 자원 — LLM Quick Reference · llms.txt · `.md` 원문 접근**
- statement: 토스페이먼츠는 MCP 서버 외에도 결제 연동 핵심을 압축한 "LLM Quick Reference"(`/guides/v2/get-started/llms-quick-reference`, 영문), 문서 전체 구조를 담은 표준 인덱스 `llms.txt`(`https://docs.tosspayments.com/llms.txt`), 그리고 모든 docs 페이지 URL 끝에 `.md`를 붙이면 원문 markdown을 그대로 받을 수 있는 기능(탭에 숨겨진 콘텐츠까지 노출)을 함께 제공해 AI 도구에 컨텍스트로 붙여넣기 쉽게 하고 있다.
- risk: normal
- primary_source: docs.tosspayments.com (공식 문서, AI 도구로 결제 연동하기)
- evidence:
  - quote: "모든 docs 페이지는 URL 끝에 `.md`를 붙이면 markdown 원본을 받을 수 있어요. AI 도구의 컨텍스트로 직접 전달할 때 편리하고, HTML 파싱이 필요 없어 토큰 효율도 좋아요. 탭에 숨겨진 콘텐츠도 모두 노출돼요."
    locator: "AI 도구로 결제 연동하기 > 추가 Tip > 페이지 markdown 원본 접근"
    url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
    title: AI 도구로 결제 연동하기
    source_role: 원출처
  - quote: "llms.txt는 LLM이 웹사이트 정보를 효과적으로 탐색하도록 돕는 표준 파일이에요."
    locator: "AI 도구로 결제 연동하기 > llms.txt"
    url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
    title: AI 도구로 결제 연동하기
    source_role: 원출처

### Q4. v2 정기결제(빌링) 연동 문서 경로 & 테스트 범위

**F11. v2 자동결제(빌링) 연동 5단계 — 자체 스케줄러는 없음**
- statement: v2 자동결제(빌링/정기결제) 공식 가이드(`/guides/v2/billing/integration`)는 (1) `payment.requestBillingAuth({ method: "CARD", ... })`로 카드 등록창 오픈 → (2) 성공 시 `successUrl`에 `customerKey`·`authKey` 쿼리 파라미터로 리다이렉트 → (3) 시크릿 키 Basic 인증으로 "카드 자동결제 빌링키 발급 API" 호출해 `billingKey` 발급(재조회 불가, customerKey와 매핑해 서버 저장) → (4) 결제 주기마다 `billingKey`로 "카드 자동결제 승인 API" 호출 → (5) HTTP 200 및 `card` 필드 포함 Payment 객체로 검증하는 순서이며, 토스페이먼츠는 결제 주기를 자동으로 실행해주는 스케줄러를 제공하지 않으므로 가맹점이 직접 스케줄링(크론 등)을 구현해야 한다.
- risk: normal
- primary_source: docs.tosspayments.com (자동결제(빌링) 결제창 연동하기)
- evidence:
  - quote: "async function requestBillingAuth() {\n  await payment.requestBillingAuth({\n    method: \"CARD\",\n    successUrl: window.location.origin + \"/success\",\n    failUrl: window.location.origin + \"/fail\",\n    customerEmail: \"customer123@gmail.com\",\n    customerName: \"김토스\",\n  });\n}"
    locator: "자동결제(빌링) 결제창 연동하기 > Step 1: SDK 초기화 및 카드 등록 요청"
    url: https://docs.tosspayments.com/guides/v2/billing/integration
    title: 자동결제(빌링) 결제창 연동하기
    source_role: 원출처
  - quote: "토스페이먼츠에서는 자체적으로 스케줄링 기능을 제공하지 않아요."
    locator: "자동결제(빌링) 결제창 연동하기 > Step 4: 정기 결제 처리"
    url: https://docs.tosspayments.com/guides/v2/billing/integration
    title: 자동결제(빌링) 결제창 연동하기
    source_role: 원출처

**F12. 빌링 테스트 환경에서 가능한 범위**
- statement: 테스트(샌드박스) 환경에서는 본인인증 문자가 발송되지 않고 인증창이 뜨면 인증번호 `000000`을 입력하면 되며, 카드 번호는 앞 6자리(BIN 번호)만 유효해도 자동결제 등록이 되는 등 실카드 없이도 전체 플로우를 검증할 수 있다. 다만 자동결제(빌링)는 국내에서 발급한 카드만 지원하므로 해외카드·해외결제는 테스트/실서비스 모두 불가하며, 실계약 및 별도 리스크 검토를 거쳐야 실서비스로 전환할 수 있다.
- risk: high
- primary_source: docs.tosspayments.com (자동결제(빌링) 결제창 연동하기)
- counter: "반박 검색 결과, 상충하는 공식 자료는 발견되지 않음. 다만 결제수단별(계좌이체/퀵계좌이체) 자동결제 가이드(`/guides/v2/billing/integration-quick.md`)에도 동일하게 \"토스페이먼츠에서는 자체적으로 스케줄링 기능을 제공하지 않아요\"라는 문구가 확인되어, 카드가 아닌 계좌이체 자동결제도 스케줄러 부재는 동일함을 교차 확인함."
- evidence:
  - quote: "테스트 환경에서는 본인인증 문자가 발송되지 않습니다. 본인인증창이 뜨면 인증번호로 `000000`을 입력하세요."
    locator: "자동결제(빌링) 결제창 연동하기 > 테스트 환경 안내"
    url: https://docs.tosspayments.com/guides/v2/billing/integration
    title: 자동결제(빌링) 결제창 연동하기
    source_role: 원출처
  - quote: "테스트 환경에서는 카드 번호의 앞 여섯 자리(BIN 번호)만 유효해도 자동결제가 등록됩니다."
    locator: "자동결제(빌링) 결제창 연동하기 > 테스트 환경 안내"
    url: https://docs.tosspayments.com/guides/v2/billing/integration
    title: 자동결제(빌링) 결제창 연동하기
    source_role: 원출처
  - quote: "현재 자동결제 결제수단은 국내에서 발급한 카드만 지원합니다."
    locator: "자동결제(빌링) 결제창 연동하기 > Important Constraints"
    url: https://docs.tosspayments.com/guides/v2/billing/integration
    title: 자동결제(빌링) 결제창 연동하기
    source_role: 원출처

---

## 용어집(Glossary)

1. **결제위젯(Payment Widget)** — plain_ko: 카드·간편결제·계좌이체 등 모든 결제수단을 한 번에 보여주는, 토스페이먼츠가 미리 만들어 둔 결제 UI 부품. 주문서 화면에 바로 붙이는 "주문서형"과 팝업으로 띄우는 "결제창형" 두 가지가 있음. detail_url: https://docs.tosspayments.com/guides/v2/payment-widget
2. **빌링키(Billing Key)** — plain_ko: 카드번호 대신 쓰는 암호화된 "결제 열쇠". 한 번 카드를 등록하면 이 열쇠만으로 다음부터는 카드 정보 없이도 결제를 요청할 수 있음(정기결제/구독 결제의 핵심). detail_url: https://docs.tosspayments.com/guides/v2/billing
3. **variantKey** — plain_ko: 위젯 어드민(관리 화면)에서 코드 없이 만든 "결제 UI 디자인판"을 구분하는 이름표. 여러 개의 UI 버전(A/B테스트 등)을 만들었을 때 어떤 버전을 렌더링할지 지정하는 값.
4. **customerKey** — plain_ko: "이 사람이 누구인지" 구분하는 구매자 고유 식별자(2~50자). 이메일처럼 남이 추측하기 쉬운 값이 아니라 UUID 같은 무작위 값을 쓰라고 권장되며, 비회원 결제는 `ANONYMOUS`라는 고정값을 씀.
5. **MCP(Model Context Protocol)** — plain_ko: AI 모델이 특정 회사의 문서·도구를 스스로 검색해서 답하도록, Anthropic이 만든 "연결 규격". 토스페이먼츠 MCP를 설치하면 Cursor 같은 AI 코딩 툴이 토스페이먼츠 공식 문서를 실시간으로 찾아 읽고 코드를 짜줌. detail_url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide

## FAQ (신규)

1. q: "인터넷에서 찾은 토스페이먼츠 결제위젯 React 예제를 그대로 따라 했는데 `updateAmount is not a function` 에러가 나요. 왜 그런가요?"
   a_hint: 그 예제가 v1(`@tosspayments/payment-widget-sdk`, `loadPaymentWidget`) 기준일 가능성이 높음. v2(`@tosspayments/tosspayments-sdk`)는 `updateAmount()`를 없애고 `setAmount()`로 분리했으므로, import 문에 `payment-widget-sdk`가 보이면 v1 예제로 간주하고 v2 마이그레이션 가이드를 참고해야 함.
   source_url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide
2. q: "Cursor에서 토스페이먼츠 MCP를 설치했는데 AI가 계속 v1 코드를 짜줘요."
   a_hint: MCP는 버전을 명시하지 않으면 기본으로 `get-v2-documents`(V2 문서 검색)를 쓰지만, 프로젝트에 남아있는 v1 코드나 과거 대화 맥락 때문에 AI가 v1 패턴을 따라할 수 있음. "V2 SDK(@tosspayments/tosspayments-sdk) 기준으로 다시 짜줘"처럼 버전을 명시적으로 요청하면 개선됨.
   source_url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide
3. q: "정기결제(빌링)를 연동하면 매달 자동으로 결제가 되나요?"
   a_hint: 아니요. 토스페이먼츠는 빌링키 발급/승인 API만 제공하고 "몇 월 며칠에 결제를 실행하라"는 스케줄링 기능은 제공하지 않음. 서버에서 크론(cron) 등으로 직접 주기를 관리하며 승인 API를 호출해야 함.
   source_url: https://docs.tosspayments.com/guides/v2/billing/integration
4. q: "테스트 키만으로 정기결제 전체 플로우(카드 등록→빌링키 발급→자동결제 승인)를 끝까지 확인할 수 있나요?"
   a_hint: 네, 가능함. 본인인증은 `000000` 입력, 카드번호는 앞 6자리(BIN)만 맞으면 등록되므로 실제 카드 없이도 전체 플로우 테스트 가능. 단, 국내 발급 카드 케이스만 시뮬레이션되고 해외카드 케이스는 테스트 불가.
   source_url: https://docs.tosspayments.com/guides/v2/billing/integration

## Resources (참고자료 — 학습자용)

1. title: 결제위젯 이해하기 (Version 2) — url: https://docs.tosspayments.com/guides/v2/payment-widget — type: 공식문서 — difficulty: 입문 — language: ko — related_part: SDK v2 연동 개요/방식 비교 — free: true — reason: v2 결제위젯의 주문서형/결제창형 선택 기준과 연동 진입점을 한눈에 정리한 공식 허브 페이지.
2. title: 결제위젯(주문서형) 연동하기 — url: https://docs.tosspayments.com/guides/v2/payment-widget/integration — type: 공식문서(퀵스타트) — difficulty: 입문 — language: ko — related_part: loadTossPayments→widgets()→renderPaymentMethods 실코드 — free: true — reason: npm 설치·SDK 초기화·결제 요청·서버 승인까지 실제 코드 스니펫이 있는 quickstart 원문(SPA라 일반 브라우저로 직접 열람 권장).
3. title: 토스페이먼츠 JavaScript SDK (레퍼런스) — url: https://docs.tosspayments.com/sdk/v2/js — type: 공식 API 레퍼런스 — difficulty: 중급 — language: ko — related_part: widgets(), setAmount(), renderPaymentMethods(), requestPayment() 전체 파라미터 — free: true — reason: 메서드별 파라미터·반환값을 정확히 확인해야 할 때 필요한 1차 레퍼런스.
4. title: 마이그레이션하기 (v1 → v2) — url: https://docs.tosspayments.com/guides/v2/get-started/migration-guide — type: 공식문서 — difficulty: 중급 — language: ko — related_part: v1/v2 코드 비교표, FAQ — free: true — reason: 옛 v1 튜토리얼을 보다가 v2로 전환할 때 반드시 참고해야 할 변경점 전체 목록(코드 비교 포함).
5. title: AI 도구로 결제 연동하기 (MCP 서버) — url: https://docs.tosspayments.com/guides/v2/get-started/llms-guide — type: 공식문서 — difficulty: 입문 — language: ko — related_part: MCP 서버 설치·Cursor 연동 — free: true — reason: 강의 핵심 주제(Cursor+MCP)와 정확히 일치하는 공식 설치/사용 가이드, mcp.json 설정 그대로 포함.
6. title: 자동결제(빌링) 결제창 연동하기 — url: https://docs.tosspayments.com/guides/v2/billing/integration — type: 공식문서 — difficulty: 중급 — language: ko — related_part: 정기결제(빌링) 5단계 연동, 테스트 환경 — free: true — reason: 구독형 서비스(정기결제) 구현 시 필요한 전 단계와 테스트 환경 제약을 명시한 1차 문서.
7. title: LLM Quick Reference — url: https://docs.tosspayments.com/guides/v2/get-started/llms-quick-reference — type: 공식문서(AI 컨텍스트용) — difficulty: 중급 — language: en — related_part: AI에게 전달할 결제 연동 핵심 요약 — free: true — reason: Cursor/Claude 등에 붙여넣어 "정답 컨텍스트"로 쓰도록 설계된 압축 페이지 — 강의에서 "프롬프트에 이 URL을 함께 주라"고 안내하기 좋음.
8. title: tosspayments/browser-sdk (GitHub) — url: https://github.com/tosspayments/browser-sdk — type: 공식 오픈소스 저장소 — difficulty: 고급 — language: ko/TypeScript — related_part: @tosspayments/tosspayments-sdk 실제 구현체 — free: true — reason: SDK 내부 동작이 궁금하거나 이슈를 검색해야 할 때 참고할 1차 소스코드 저장소.

## failed_urls

- https://www.npmjs.com/package/@tosspayments/tosspayments-sdk (HTTP 403 Forbidden — WebFetch로 열람 불가, npm 페이지 정보는 WebSearch 요약 및 sdk/v2/js 공식 문서로 대체 확인)
- https://docs.tosspayments.com/guides/v2/payment-widget/integration.md (HTTP 404 — `.md` 접미사 경로 미제공. 대신 r.jina.ai 프록시 경유로 일반 HTML 렌더링을 확인함)

## 조사 중 확인한 오해 소지 / Dead ends

- "결제위젯 React 공식 예제"를 찾으면서 tosspayments.com 블로그 인기글("React로 결제 페이지 개발하기", 2023.03.06)이 여전히 검색 상위에 노출되는데, 이 글은 v1(`@tosspayments/payment-widget-sdk`) 기준이라 v2 학습 자료로 그대로 쓰면 `loadPaymentWidget`/`updateAmount` 등 존재하지 않는 API를 배우게 됨 — 강의 자료에서 "v1/v2 구분 주의" 경고 박스로 반드시 짚어야 함(F6).
- 토스페이먼츠 GitHub 조직(github.com/tosspayments)에는 v2 전용 React/Next.js 샘플 저장소가 별도로 없음(`tosspayments-sample`, `tosspayments-sample-v1`, `payment-samples`는 있으나 v2 전용 React 샘플 부재). React 적용 시 참고할 공식 자료는 SDK reference의 프레임워크 비종속 코드 + 블로그의 `useEffect`/`useState` Hook 가이드(`docs.tosspayments.com/blog/react-use-effect`, `react-use-state`) 정도이며, 완결된 Next.js 퀵스타트 저장소는 확인되지 않음.
