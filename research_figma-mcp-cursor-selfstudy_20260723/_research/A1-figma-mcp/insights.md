# A1-figma-mcp 조사 기록 (observed_at 2026-07-23)

## 방문 URL (성공, 원문 확인함)

- https://developers.figma.com/docs/figma-mcp-server/ (Introduction) — WebFetch 요약 확인
- https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/ — curl raw HTML → 텍스트 추출, 전문 확보 (Claude Code/Codex/Cursor/VS Code/Xcode 절차, mcp.figma.com/mcp, write to canvas 베타 무료 안내 포함)
- https://developers.figma.com/docs/figma-mcp-server/local-server-installation/ — curl raw HTML → 텍스트 추출, 전문 확보 (데스크톱 앱 Dev Mode 토글, 127.0.0.1:3845/mcp, VS Code/Cursor/Claude Code mcp.json 예시 전부 포함)
- https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/ — curl raw HTML 직접 파싱하여 표(table) 원본 구조 확인. WebFetch 요약본은 2회 시도에서 서로 다르게(부정확하게) 표를 재구성해서 신뢰 불가 → raw HTML의 rowspan 구조를 직접 읽어 정확한 매핑을 확정함.
  - 표 실제 구조: Seat=View,Collab 행은 전 플랜 "Up to 6/month". Seat=Dev,Full 행에서 Starter 열은 rowspan으로 View,Collab과 동일한 "Up to 6/month" 셀을 공유(즉 Starter는 시트 종류와 무관하게 월 6회). Professional Dev,Full = "Up to 200/day 10/min", Organization Dev,Full = "Up to 200/day 15/min", Enterprise Dev,Full = "Up to 600/day 20/min".
  - 하단 "What if I'm rate-limited?" 문단에서 "Full or Dev seat on an Organization plan (200 tool calls per day), upgrade to an Enterprise plan (600 tool calls per day)"로 위 매핑을 재확인(교차검증 완료).
- https://developers.figma.com/docs/figma-mcp-server/avoid-large-frames/ — curl raw HTML → 텍스트 추출, 전문 확보 (대형 프레임 선택 시 한계)
- https://developers.figma.com/docs/rest-api/rate-limits/ — curl raw HTML → 텍스트 추출. 핵심: "if you use a personal access token to get the content of a file in a Starter plan, requests to that file are limited to up to 6 per month even if you have a Full seat in a different plan." → 커뮤니티 MCP(개인 액세스 토큰 기반)도 Starter 플랜에서는 동일하게 월 6회 제한.
- https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server — WebFetch 요약. Remote server "available on all seats and plans", Desktop server "available on a Dev or Full seat for all paid plans". Code Connect 관련 best practice 언급.
- https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server — WebFetch 2회(교차 일치) — Cursor 전용 절차. "/add-plugin figma" 플러그인 방식과 데스크톱 수동 mcp.json 방식 모두 확인.
- https://help.figma.com/hc/en-us/articles/39252411778583-Figma-MCP-server-FAQs — curl raw HTML → article-body 파싱. use_figma(write to canvas) 관련 FAQ 전문 확보. "A Full Seat is required to write to Figma files outside of drafts. Dev Seats get read-only access outside of their drafts" 확인. 알려진 한계(20kb 응답 제한, 이미지 미지원, 폰트 업로드 필요 등)도 확인했으나 이번 fact 상한(15건) 내에서는 생략, 필요시 추가 조사 가능.
- https://www.figma.com/pricing/ — curl raw HTML(2.1MB, SPA) → 정규식으로 "Full seat"/"Dev seat"/"$16"/"$12" 등 문맥 직접 확인. Professional 플랜 카드의 "Annual" 토글이 기본 선택된 상태로 Full seat $16/mo, Dev seat $12/mo가 정적 HTML에 렌더링되어 있음(원문 verbatim 확보). Monthly(비연간) 토글의 실제 값은 JS로만 전환되어 이 세션에서는 static HTML로 직접 확인 못함 → 아래 반박검색으로 보완.
  - Starter 플랜: "Free" / "Free limited access to Figma products" 확인.
  - Organization: Full $55/mo, Dev $25/mo (Billed annually 고정, 월간 토글 없음). Enterprise: Full $90/mo, Dev $35/mo (Billed annually 고정).
- https://github.com/GLips/Figma-Context-MCP — WebFetch로 README 확인(Framelink Figma MCP = npm 패키지 figma-developer-mcp, MIT 라이선스, Figma 액세스 토큰 필요). `gh api repos/GLips/Figma-Context-MCP`로 실측: stargazers_count=15481, forks_count=1219, open_issues_count=21, pushed_at=2026-07-03T14:24:36Z.
- https://github.com/figma/mcp-server-guide — WebFetch로 README 확인. Figma 공식 조직(figma) 소유 저장소, best practice(컴포넌트화·Code Connect·변수·시맨틱 네이밍·Auto layout) 원문 인용 확보.
- https://litmers.com/blog/... (2026 피그마 MCP 완벽 가이드, use_figma 캔버스 직접 수정) — WebFetch로 발행일(2026-03-30) 확인, 무료 열람 가능, 중급자 대상. 한국어 자료로 resources에 등재.

## 반박검색(counter, risk:high 항목)

- "Figma MCP rate limit 200/day OR 200 per day Professional Dev seat" 재검색 → 포럼/제3자 소스도 Professional/Organization Dev,Full=200/day, Enterprise=600/day로 일치. rate-limits-access 원문 표와 교차 일치 확인.
- "Figma Professional plan $20 full seat monthly billing $15 dev seat" 재검색 → projectmanagers.net, comparedge.com, userjot.com, toolradar.com 등 제3자 소스 모두 "월간 청구 시 Full $20/mo, Dev $15/mo, 연간 청구 시 Full $16/mo, Dev $12/mo"로 일관 보도. figma.com/pricing 원문 정적 HTML에서는 연간($16/$12)만 verbatim 확보, 월간 수치는 JS 전환값이라 이 세션에서 원문 재확인 못함 — fact의 counter 필드에 이 한계를 명시함.
- "Figma MCP write to canvas beta free usage-based paid feature" 재검색 → bitovi.com, figma.com/blog(the-figma-canvas-is-now-open-to-agents), help.figma.com FAQ 등 다수 소스가 "현재 베타 기간 무료, 추후 사용량 기반 유료 전환 예정"을 동일하게 보도. 원문(developers.figma.com remote-server-installation)과 완전히 일치.
- Starter 플랜 커뮤니티 MCP 제한 관련: developers.figma.com/docs/rest-api/rate-limits/ 원문에서 "Starter 플랜 파일은 개인 액세스 토큰 사용 시에도 월 6회 제한"이라고 명시 확인. Framelink/figma-developer-mcp README 자체는 이 제한을 언급하지 않지만, 사용하는 하부 API(Figma REST API)가 이 제한을 그대로 받으므로 "무료 플랜에서 커뮤니티 MCP가 제한을 우회한다"는 통념은 사실이 아님.

## 실패/열람 불가 URL

- https://www.npmjs.com/package/figma-developer-mcp — WebFetch 403 Forbidden. 주간 다운로드 수(WebSearch 요약상 11,556/week) 등은 원문 미확인, fact에 등재 안 함.
- https://temkit.kr/article/?bmode=view&idx=170511726 (피그마 MCP 핵심 총정리 블로그) — WebFetch 403 Forbidden. 내용 신뢰성 확인 못해 resources에서 제외.
- https://help.figma.com/hc/en-us/articles/35281186390679-Figma-MCP-collection-How-to-setup-the-Figma-desktop-MCP-server-alternative — WebFetch 시 Zendesk 로그인 접근 페이지(302 리다이렉트)로 이동, 원문 확보 실패. 동일 내용을 developers.figma.com/docs/figma-mcp-server/local-server-installation/에서 curl로 대체 확보하여 정보 손실 없음.
- https://developers.figma.com/docs/figma-mcp-server/best-practices/ — 존재하지 않는 URL(404). 실제 사이드바 경로는 structure-figma-file/, write-effective-prompts/, trigger-specific-tools/, add-custom-rules/, avoid-large-frames/ 등으로 세분화되어 있음. 이번 조사에서는 avoid-large-frames/와 figma/mcp-server-guide README로 대체 확보.
- `gh api repos/framelink-ai/figma-mcp` — 404 Not Found. "Framelink"는 별도 GitHub org가 아니라 GLips/Figma-Context-MCP 저장소의 제품 브랜드명(웹사이트 framelink.ai)임을 확인, 잘못된 org 추정이었음.
- https://help.figma.com/hc/articles/360041061034 계열(Manage billing on the Professional plan) — WebFetch는 성공했으나 실제 가격 수치는 페이지 내에 없고 "visit figma.com/pricing"으로만 안내함(수치 출처 아님, fact에 미사용).

## 기타 메모

- Cursor 원격 설치 시 명령어 `/add-plugin figma`는 Cursor의 일반 슬래시 커맨드가 아니라 Figma가 배포하는 "Figma 플러그인"을 에이전트 채팅 안에서 설치하는 방식으로 보임(공식문서 2곳에서 동일하게 확인됨: remote-server-installation과 Cursor 전용 헬프센터 문서).
- VS Code는 mcp.json에서 `"servers"` 키를, Cursor는 `"mcpServers"` 키를 쓴다는 차이를 공식 예시 코드에서 직접 확인(local-server-installation 원문 코드블록 비교).
- write to canvas(use_figma)는 Full 시트가 있어야 드래프트 밖 파일에 실제 쓰기가 가능하고, Dev 시트는 읽기 전용이라는 세부 조건을 FAQ에서 확인 — Q2의 "Dev/Full 시트 요건"에 대한 답을 기능별로 더 정밀하게 만들어줌.
