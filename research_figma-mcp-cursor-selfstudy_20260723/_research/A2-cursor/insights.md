# A2-cursor 조사 raw 기록 (observed_at 2026-07-23)

## 방문 URL (성공, WebFetch 원문 확인)
- https://cursor.com/docs/rules — Cursor Rules 정의, .cursor/rules/.mdc, AGENTS.md 관계. .cursorrules 레거시 언급 없음(현재는 .cursor/rules + AGENTS.md만 공식)
- https://cursor.com/help/ai-features/agent — Agent 모드: "Agent can build features from scratch, refactor existing code, fix bugs, write tests, and run shell commands." / "Use Agent for most tasks. Switch to Ask when you want answers without changes."
- https://cursor.com/docs/agent/overview — Agent 정의: "Cursor's assistant that can complete complex coding tasks independently, run terminal commands, and edit code. Access in sidepane with Cmd+I." (주의: 이 페이지엔 Chat/Ask 관련 내용 없음, Agent 전용)
- https://cursor.com/help/ai-features/ask-mode — Ask(Chat) 모드: "Ask mode is a read-only mode for understanding your codebase. Agent answers questions and explores code without making any edits." + "For questions that lead to code changes, switch back to Agent mode"
- https://cursor.com/pricing — Hobby: Free/No credit card required/Limited Agent requests/Limited Tab completions. Individual(Pro): $20/mo, Extended limits on Agent, Generous limits for Grok & Composer, Access to frontier models, MCPs/skills/hooks, Cloud agents, Bugbot(usage-based). 숫자(정확한 요청 횟수) 명시 없음. FAQ: "Every plan includes a set amount of model usage." → 자세한 건 /docs/account/pricing로 링크.
- https://cursor.com/docs/account/pricing — Hobby 플랜 언급 자체가 없음(Pro만). Pro $20/mo, "unlimited tab completions, extended agent usage limits on all models, access to Bugbot, and access to Cloud Agents". 두 풀: Cursor Models pool(월별 할당) vs Other Models pool(3rd-party API rate, Pro는 최소 $20 포함). 초과 시 on-demand 과금 또는 업그레이드. 구체적 일일/월 요청 개수 없음.
- https://cursor.com/docs/mcp — "Installing MCP servers" 섹션: 1) Marketplace one-click install from Customize, 2) Cursor Settings UI, 3) 수동 .cursor/mcp.json(project) 또는 ~/.cursor/mcp.json(global). JSON 포맷: {"mcpServers": {"server-name": {"command":..., "args":[...], "env":{...}}}} (로컬 stdio) 또는 {"url":..., "headers":{...}} (원격 SSE). 팀 관리자는 Dashboard > Integrations & MCP / Dashboard > Plugins.
- https://cursor.com/docs/tab/overview — Tab: "Tab is Cursor's AI-powered autocomplete. It suggests code as you type, based on your recent edits, surrounding code, and linter errors." 멀티라인 편집, jump-in-file, 타 파일 연관 수정 제안.
- https://cursor.com/docs/inline-edit/overview — Cmd/Ctrl+K: "Inline edit lets you make quick, targeted code changes without opening the chat panel." 코드 선택 후 Cmd/Ctrl+K → 지시 입력 → Enter → 인라인 diff, Tab으로 accept/Esc로 reject.
- https://cursor.com/help/getting-started/install — 설치: "Windows: Run the installer and follow the prompts" / "Mac: Drag Cursor into your Applications folder" / 로그인: "Sign in with your Cursor account when prompted" / 사전요구: "A Cursor account. Sign up free at cursor.com if you don't have one". 한국어 UI 언급 없음.
- https://cursor.com/ko — 웹사이트(마케팅 페이지) 자체는 한국어 등 9개 언어 지원(언어 선택 메뉴 존재). 단, 에디터 앱 UI의 한국어 지원 여부는 이 페이지에 명시 없음.
- https://www.inflearn.com/en/course/we-can-cusor-ai — 무료("Free now"), 대상 "Zero coding knowledge is perfectly fine!" / "Non-developers welcome", 평점 4.9(106리뷰), 수강생 2,556명, 12강 5시간55분, 설치·오리엔테이션부터 포트폴리오/챗봇/블로그생성기/Claude MCP 실습까지.
- https://www.youtube.com/watch?v=he0gEZ5wg0Q — 본문 메타데이터(채널/게시일) 확인 불가, 제목만 확인: "왕초보도 개발 가능 | 커서 AI 설치부터 기본 사용법 강의". search-snippet 기반으로만 resources 등재.
- https://www.youtube.com/watch?v=_oEhh8666pA — 본문 메타데이터 확인 불가, 제목만: "이제 코딩 3배 빨라진다고? 커서 AI 실화? (25분 완벽 정리)". search-snippet 기반으로만 resources 등재.
- https://blog.insightbook.co.kr/2025/11/07/... — 비개발자 대상 Cursor 설치~협업 가이드 블로그(2025-11-07). 단, 도서(『시작해요, 커서』) 홍보글이라 핵심 콘텐츠는 유료 도서 구매 유도. 무료 자료로 채택 안 함(resources 미등재).

## 반박검색(counter-search) — 요금제 (risk:high)
- 1차 검색: "Cursor pricing Hobby Pro plan 2026 request limits" → 공식 페이지 숫자 비공개, "Older articles often repeat 2,000 completions and 50 premium requests, but that wording is not on the current official page."
- 2차 검색(다른 표현): "Cursor Hobby plan free limits 2026 monthly agent requests" → 동일 결론 재확인. "Cursor's public page does not state one universal numeric quota... Limits can vary as Cursor changes product packaging". 커뮤니티 리포트(월 2,000 Tab / 50 premium)는 2025년 6월 usage-based billing 전환 이전 수치로 현재 공식 문서에 없음.
- 결론: 공식 cursor.com/pricing, cursor.com/docs/account/pricing 어디에도 정확한 숫자 한도 없음. "Limited"라는 표현만 존재. → fact에는 정성적 표현만 등재, 숫자는 미확정으로 명시.

## 실패 URL (failed_urls)
- https://docs.cursor.com/en/get-started/installation — 308 redirect → https://cursor.com/docs 로 이동했으나 해당 페이지는 SPA 쉘이라 타이틀("Cursor Docs — Agent, Rules, MCP, Skills & CLI")만 잡히고 본문 콘텐츠 미확인.
- https://cursor.com/docs/chat/overview — 404 Not Found
- https://cursor.com/docs/agent/chat/overview — 404 Not Found
- https://wikidocs.net/278669 — 403 Forbidden (한국어 위키독스 "바이브 코딩" 페이지, 열람 실패)

## 메모
- .cursorrules(레거시 단일 파일)는 여전히 동작은 하지만 공식 문서(cursor.com/docs/rules)에서 신규 기능 대상이 아니며 사실상 .cursor/rules/*.mdc + AGENTS.md로 대체됨 — 단, 이 "레거시 지원 지속" 문구 자체는 이번 조사에서 cursor.com/docs/rules 원문에서 명시적으로 확인하지 못했음(초기 WebSearch 요약에는 있었으나 WebFetch 원문 재확인 시 해당 문장 미검출) → fact에는 "레거시 계속 작동" 주장을 넣지 않고 "현재 공식 형식은 .cursor/rules(.mdc)와 AGENTS.md"로만 기재.
- Cursor 에디터가 VS Code 기반이라는 점, 별도 인터페이스 언어 설정이 없고 언어팩 확장을 설치해야 한다는 내용은 forum.cursor.com(커뮤니티, 비공식) 스니펫에서만 확인됨 → risk 표시하고 fact 문구는 "공식 문서에 한국어 UI 관련 명시 없음"으로 보수적으로 기재.
