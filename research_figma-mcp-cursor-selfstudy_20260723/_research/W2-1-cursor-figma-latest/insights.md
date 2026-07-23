# W2-1 Cursor 공식문서·changelog / Figma AI credits·Figma Make 보강조사

조사일: 2026-07-23
조사자: 서브에이전트 (조사원 W2-1)

## 방문 URL 로그

| # | URL | 상태 | 메모 |
|---|-----|------|------|
| 1 | https://cursor.com/docs/mcp | 200 OK | Cursor 공식 MCP 문서. 헤딩: What is MCP? / Installing MCP servers / Enterprise admin controls 등 |
| 2 | https://cursor.com/help/getting-started/install | 200 OK | "Download and install Cursor" — Windows/Mac 설치 절차 |
| 3 | https://docs.cursor.com/get-started/installation | 308 리다이렉트 → https://cursor.com/docs | Wave1에서 403이었던 페이지. 이번엔 403이 아니라 308 리다이렉트로 확인됨. 리다이렉트 목적지는 문서 홈(cursor.com/docs)이며 별도 "Installation" 전용 페이지가 아님 |
| 4 | https://cursor.com/docs/get-started/installation | 200 OK (실제로는 Quickstart 콘텐츠 반환) | "get-started/installation" 경로가 실제로는 Quickstart 페이지("# Quickstart")와 동일 콘텐츠를 서빙. 별도의 "Installation"이라는 제목 섹션은 존재하지 않음 — dead end로 기록 |
| 5 | https://cursor.com/changelog | 200 OK | 최신 changelog 목록 (2026-07-22 ~) |
| 6 | https://cursor.com/changelog/page/2 | 200 OK | 2026-06월 항목들 |
| 7 | https://cursor.com/changelog/cli-jan-08-2026 | 200 OK | "New CLI Features and Improved CLI Performance" (2026-01-08) |
| 8 | https://cursor.com/changelog/2-6 | 200 OK | "MCP Apps and Team Marketplaces for Plugins" (2026-03-03) |
| 9 | https://cursor.com/changelog/sdk-updates-jun-2026 | 200 OK | "Custom stores, custom tools, and auto-review for the Cursor SDK" (2026-06-04) |
| 10 | https://cursor.com/changelog/customize | 200 OK | "Customize Cursor" (버전 3.9, 2026-06-22) |
| 11 | https://help.figma.com/hc/en-us/articles/33459875669015-How-AI-credits-work | 200 OK | 플랜별 AI credits 배정 + credits 소모 기능 전체 목록 |
| 12 | https://help.figma.com/hc/en-us/articles/35865276858647-Manage-AI-credits | 200 OK | credits 관리/구매 방법. MCP/API 언급 없음 |
| 13 | https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server | 200 OK | Figma MCP 서버 가이드. "캔버스 쓰기" 기능의 향후 유료화(베타 중 무료) 언급 |
| 14 | https://developers.figma.com/docs/figma-mcp-server/ | 200 OK | 개발자 문서. AI credits 용어 자체는 등장하지 않음. 캔버스 쓰기 기능 유료화 예정 문구만 반복 |
| 15 | https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server | 200 OK | Cursor+Figma MCP 연동 공식 가이드. Cursor 쪽 UI 경로로 "Cursor Settings > Tools & MCP > Installed MCP Servers > Connect" 명시 (cursor.com/docs/mcp의 최신 "Customize" 명칭과 다름 — Figma 문서가 구버전 UI 스냅샷일 가능성) |
| 16 | https://help.figma.com/hc/en-us/articles/31304412302231-Explore-Figma-Make | 200 OK | Figma Make 공식 소개 |
| 17 | https://help.figma.com/hc/en-us/articles/31722591905559-Figma-Make-FAQs | 200 OK | Figma Make FAQ. Dev Mode/MCP/Cursor와의 관계 비교 설명 없음 |

## 핵심 메모

### Q1. Cursor MCP 설정 (cursor.com/docs/mcp)
- 서버 등록 UI: "Install and manage MCP servers from the Customize page" (헤딩: What is MCP?)
- One-click 설치: "Browse the Customize page for official plugins" / "Click 'Add to Cursor' on a marketplace entry to install it" (헤딩: Installing MCP servers > One-click installation)
- mcp.json 형식 3종 (stdio/npx, stdio/python, remote url+headers) — 헤딩: Using mcp.json
- 위치: project-scoped `.cursor/mcp.json`, global `~/.cursor/mcp.json`
- transport: stdio, SSE, Streamable HTTP (헤딩: What is MCP? / How it works)
- Enterprise: "Team Settings > MCP Configuration" (헤딩: Enterprise admin controls)
- **주의**: Figma 공식 문서(help.figma.com, #15)는 Cursor 쪽 경로를 "Cursor Settings > Tools & MCP > Installed MCP Servers"로 안내 — cursor.com/docs/mcp 최신 문구인 "Customize"와 명칭이 다름. Cursor UI가 최근(2026-06-22 changelog #10) "Tools & MCP" 개별 설정에서 "Customize" 통합 페이지로 개편되었을 가능성이 있고, Figma 쪽 문서가 갱신되지 않았을 가능성. 두 명칭 모두 원문 그대로 기록.

### Q2. Cursor 설치 문서
- docs.cursor.com/get-started/installation → 308 → cursor.com/docs (전용 Installation 페이지 없음)
- 실질적 설치 안내는 두 공식 페이지에 분산:
  - cursor.com/help/getting-started/install: "Windows: Run the installer and follow the prompts" / "Mac: Drag Cursor into your Applications folder" / "Open Cursor from your applications menu or desktop"
  - cursor.com/docs/get-started/quickstart: 헤딩 "macOS"/"Windows"/"Linux" 아래 "Download Cursor. Open the app and sign in. Then pick a folder and start with a small task." + 요구사항(macOS 12+, Windows 10+, Native installer .dmg/.exe, Apple Silicon+Intel 지원)

### Q3. Changelog (H1 2026, 4건)
1. 2026-01-08 "New CLI Features and Improved CLI Performance": `/mcp enable`, `/mcp disable` 커맨드 추가, MCP 서버명에 공백 지원 — 기능 변경, 요금 변경 없음
2. 2026-03-03 (v2.6) "MCP Apps and Team Marketplaces for Plugins": "MCP Apps support interactive user interfaces like charts from Amplitude, diagrams from Figma, and whiteboards from tldraw directly inside Cursor." — 기능 변경, 요금 변경 없음
3. 2026-06-04 "Custom stores, custom tools, and auto-review for the Cursor SDK": local.customTools, local.autoReview, JSONL 커스텀 스토어, nested subagents — SDK 대상, 가격 변경 언급 없음
4. 2026-06-22 (v3.9) "Customize Cursor": "You can now add and manage plugins, skills, MCPs, subagents, rules, commands, and hooks at the user, team, or workspace level, and even bring your own custom MCPs." — UI 통합 개편, 요금 변경 없음

### Q4. Figma AI credits
- 플랜별 월간 배정 (Full seat 기준, help.figma.com #11):
  - Starter: 500 credits/month (일부 문서 표현상 "150/day, up to 500/month" 병기하는 3자 자료 있으나 공식 페이지 원문은 500/month로 확인)
  - Professional: 3,000 credits/month
  - Organization: 3,500 credits/month
  - Enterprise: 4,250 credits/month
  - Dev/Collab/View seat: 모든 플랜 공통 500 credits/month
- 반박검색: 2026-03-18 크레딧 한도 강제 적용(enforcement) 발표 이후에도 Professional 3,000/월 수치가 그대로 유지됨을 별도 소스(forum.figma.com 공지, X/구 Twitter 공식 계정)에서 교차 확인 — 상충 없음
- credits 소모 기능 전체 목록 (원문, #11): Figma Make / AI search / Rename layers / Summarize stickies, Cluster stickies, Update visual(FigJam) / Generate templates and diagrams(FigJam) / Remove background / Vectorize image / Boost image resolution / Erase object / Isolate object / Expand image / Make image / Edit image / Add interactions / Generate Figma files in ChatGPT for Figma Slides
  - 이 목록에 "MCP", "Dev Mode", "code generation" 관련 항목 없음 (간접 근거)
- MCP 도구 호출과 credits 관계: help.figma.com 및 developers.figma.com 어디에도 "MCP 호출은 AI credits를 소모하지 않는다"는 명시적 문장은 없음. 유일한 관련 문구(#13, #14 공통, 헤딩 "Let your agent write directly to the canvas in Figma Design and FigJam"): "We're quickly improving how Figma supports AI agents. This will eventually be a usage-based paid feature, but is currently available for free during the beta period." — 이는 MCP의 "캔버스에 쓰기(write)" 기능에 한정된 별도의 향후 유료화 계획이며, 기존 AI credits 시스템과 명시적으로 연결되지 않음. **결론: 공식문서 기준 "MCP는 AI credits를 직접 소모하지 않는다"는 간접적으로 뒷받침되나(소모 목록 미포함), 명시적 확인 문장은 없음 — 확인 불가로 기록.**

### Q5. Figma Make
- 공식 정의 (#16): "Figma Make is an AI-driven, prompt-to-app tool that lets you bring ideas and existing Figma designs to life as functional prototypes, web apps, and interactive UI."
- 용도: "Preview the look and feel of your designs in a functional form, Turn proposals and ideas into prototypes to help hone your product approach, Explore a variety of solutions for a problem you're trying to solve"
- 좌석: "Figma Make is included on the Full seat for paid plans, though users with a Dev, Collab or View seat can also try Figma Make in drafts."
- Dev Mode와 대비: Dev Mode = "Translate designs into code" / Figma Make = "Prompt to code anything you can imagine" (제품 목록 페이지 병기, 직접 비교 설명 문단은 아님)
- Figma MCP·Cursor 워크플로와의 관계: help.figma.com의 Figma Make 소개/FAQ 페이지(#16, #17) 어디에도 Figma MCP 서버나 Cursor 같은 외부 코드 에디터와의 관계를 직접 설명하는 문장 없음. Figma Make는 Figma 내부에서 자체 실행되는 prompt-to-app 도구이고, Figma MCP 서버는 Cursor 등 외부 에이전트에 디자인 컨텍스트를 넘겨주는 별개 경로 — 공식문서상 두 제품은 별도 목록 항목으로만 병기되며 상호 연계 설명은 없음 (dead end).

## Dead ends
- docs.cursor.com/get-started/installation은 전용 "Installation" 문서가 아니라 Quickstart로 리다이렉트/통합됨 — Wave1의 403은 재현되지 않았고, 대신 "그런 페이지가 독립적으로 없다"는 구조적 사실을 확인.
- Figma Make와 Figma MCP/Cursor 워크플로 간의 공식 문서상 직접적 관계 설명 없음.
- "MCP 호출이 AI credits를 소모하지 않는다"는 명시적 1차 출처 문장 없음 (목록 기반 간접 추정만 가능).
