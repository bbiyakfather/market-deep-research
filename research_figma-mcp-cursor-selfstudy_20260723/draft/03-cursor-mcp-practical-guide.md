# 3. Cursor × MCP 실전 가이드 (Part 2 대응)

> 앞 페이지에서 도구 설치를 마쳤다면, 이번에는 Cursor(AI 코드 에디터)에 MCP를 연결하고 Figma 디자인을 실제 코드로 바꿔 봅니다. 강의 기준으로는 Part 2(Cursor·MCP 활용)에 해당하는 주제를 공개 자료로만 다룹니다.

## 1. MCP를 비유로 이해하기 — "AI용 USB-C 단자"

**MCP**(Model Context Protocol, AI가 다른 프로그램과 대화할 때 쓰는 표준 연결 규격)는 이름만 보면 어렵지만, 비유 하나면 충분합니다. 모비인사이드 기사(2025-06-25)의 표현을 빌리면 MCP는 **"AI용 USB-C 단자"**입니다. 노트북에 USB-C 단자가 하나 있으면 모니터·충전기·외장하드를 제조사와 상관없이 같은 방식으로 꽂을 수 있습니다. 마찬가지로 Cursor에 MCP라는 단자가 있으면 Figma든 Supabase든 토스페이먼츠든, 서비스마다 전용 연결법을 따로 배울 필요 없이 같은 방식으로 붙습니다. 같은 기사는 이 조합으로 Figma 디자인을 React(웹 화면을 만드는 기술) 코드로 바꾸는 데 약 10분이 걸렸다고 소개합니다.

역할은 둘로 나뉩니다.

| 역할 | 비유 | 예 |
|---|---|---|
| MCP 서버 | 정보를 내보내는 "기기" 쪽 | Figma, Supabase, 토스페이먼츠 문서 |
| MCP 클라이언트 | 단자가 달린 "노트북" 쪽 | Cursor, VS Code, Claude Code |

한 가지 알아둘 점: Figma 공식 MCP 서버는 아무 프로그램이나 받아주지 않고, Figma가 승인 목록(MCP Catalog)에 올린 클라이언트만 연결을 허용합니다. Cursor는 이 목록에 들어 있으므로 안심해도 됩니다.

## 2. Cursor에 MCP 등록하는 3가지 방법

**[무엇을 배우나]** 외부 서비스를 Cursor에 "꽂는" 3가지 등록 방법입니다. **[왜 필요한가]** 서비스마다 지원하는 방식이 다르고, 인터넷의 안내 문서도 제각각이라 3가지를 모두 알아두면 어떤 문서를 만나도 당황하지 않습니다.

### 방법 1 — Customize 페이지에서 원클릭 (가장 쉬움)

2026년 6월 Cursor v3.9 업데이트로 플러그인·MCP·규칙을 한 곳에서 관리하는 **Customize** 페이지가 새로 생겼습니다([Cursor 체인지로그](https://cursor.com/changelog)). 이 페이지의 마켓플레이스에서 원하는 서비스의 **Add to Cursor** 버튼을 누르고 OAuth(내 계정으로 로그인해 연결을 승인하는 방식) 인증만 마치면 끝입니다. 조금 오래된 문서나 블로그에는 이 메뉴가 'Settings > Tools & MCP'라는 예전 이름으로 적혀 있을 수 있는데, 같은 기능입니다.

### 방법 2 — mcp.json 파일 직접 작성

설정 파일을 직접 만드는 방법입니다. 파일을 두는 위치에 따라 적용 범위가 달라집니다.

| 파일 위치 | 적용 범위 |
|---|---|
| 프로젝트 폴더 안 `.cursor/mcp.json` | 이 프로젝트에서만 |
| 홈 디렉터리 `~/.cursor/mcp.json` | 내 컴퓨터의 모든 프로젝트 |

작성 형식은 두 가지입니다. 먼저 **url 방식**(서버가 인터넷에 있어서 주소만 적으면 되는 방식):

```json
{
  "mcpServers": {
    "supabase": {
      "url": "https://mcp.supabase.com/mcp"
    }
  }
}
```

다음은 **stdio 방식**(내 컴퓨터에서 프로그램을 직접 실행해 연결하는 방식으로, command·args·env 항목을 적습니다):

```json
{
  "mcpServers": {
    "tosspayments-guide": {
      "command": "npx",
      "args": ["-y", "@tosspayments/integration-guide-mcp@latest"]
    }
  }
}
```

주의할 점 하나: 맨 바깥 키는 반드시 `mcpServers`여야 합니다. VS Code는 같은 상황에서 `servers`라는 다른 키를 쓰기 때문에, VS Code용 예제를 그대로 복사하면 Cursor에서 동작하지 않습니다. 전체 형식은 [Cursor 공식 MCP 문서](https://cursor.com/docs/mcp)에 있습니다.

### 방법 3 — 딥링크

딥링크(클릭하면 특정 앱이 바로 열리는 특수 링크)를 지원하는 서비스는 공식 문서에 있는 설치 버튼 하나로 끝납니다. 버튼을 누르면 Cursor 앱이 열리면서 설치 확인 창이 뜨고, 승인하면 자동 등록됩니다. Figma와 토스페이먼츠 공식 문서가 이 방식을 지원합니다.

**[✅ 이게 보이면 성공]** Customize 페이지의 설치된 MCP 서버 목록에 해당 서버가 나타나고, 연결(Connect) 인증까지 마치면 Agent 채팅에서 그 서버의 도구를 부를 수 있습니다.

## 3. Figma 디자인 → 코드 워크플로

**[무엇을 배우나]** Figma에서 고른 화면 조각을 Cursor Agent(복잡한 코딩 작업을 대신 수행하는 Cursor의 AI 비서)에게 넘겨 코드로 받는 기본 흐름입니다. **[왜 필요한가]** 이 흐름이 이 학습 경로 전체의 핵심 반복 단위이기 때문입니다. 한 번 손에 익으면 어떤 화면이든 같은 순서로 만들 수 있습니다.

**[따라하기]**

1. Figma 연결을 준비합니다. 공식 권장 경로는 Cursor의 Agent 채팅창에 `/add-plugin figma`를 입력해 Figma 플러그인을 설치한 뒤, 설정에서 **Connect**를 눌러 계정 인증을 마치는 것입니다([Figma 공식 연결 가이드](https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server)).
2. Figma 파일에서 변환할 대상을 선택합니다. 화면 전체가 아니라 버튼·카드처럼 **작은 컴포넌트(재사용하는 디자인 부품) 단위**로 고르는 것이 요령입니다.
3. Cursor Agent 채팅에 요청합니다. 예: "지금 Figma에서 선택한 카드 컴포넌트를 React 컴포넌트로 만들어 줘."
4. 결과를 확인합니다. 생성된 코드의 문구·색·간격이 원본 디자인과 맞는지 눈으로 대조하고, 다르면 "버튼 색이 디자인과 달라. 디자인 값으로 다시 맞춰 줘"처럼 이어서 요청합니다.

**[✅ 이게 보이면 성공]** Agent 응답 과정에 Figma MCP 도구를 호출했다는 표시가 뜨고, 내가 선택한 프레임(Figma에서 화면 한 장을 담는 틀)의 문구와 색이 코드에 반영돼 있습니다.

**잘 되게 하는 디자인 습관 4가지.** AI가 읽는 것은 결국 내 Figma 파일의 "정리 상태"입니다. Figma 공식 가이드 저장소 [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide)가 권장하는 습관은 다음과 같습니다.

- 버튼·카드·인풋처럼 반복되는 요소는 **컴포넌트**로 만들어 둔다.
- 레이어 이름을 'Group 5' 대신 'CardContainer'처럼 **의미가 드러나게** 짓는다.
- 간격·색상·모서리 라운드·글꼴은 **변수**(variable, 디자인 값에 붙이는 이름표)로 관리한다.
- **Auto Layout**(요소의 간격·정렬을 자동으로 맞춰 주는 Figma 기능)으로 "이 화면은 이렇게 늘어난다"는 의도를 표현한다.

**한계도 알아두세요.** 큰 화면(대형 프레임)을 통째로 선택해 코드 생성을 요청하면 느려지거나, 오류가 나거나, 응답이 불완전해질 수 있습니다. 공식 권장 대응은 화면을 컴포넌트·논리적 단위로 잘게 쪼개서 요청하는 것입니다.

**[막히면]** 연결 자체가 안 될 때는 아래 5번의 점검 순서를 위에서부터 따라가면 됩니다.

## 4. 같이 쓰면 좋은 MCP

Figma 외에도, 이 학습 경로에서 쓸 서비스들이 공식 MCP를 제공합니다.

| MCP | 무엇이 좋아지나 | 등록 방법 |
|---|---|---|
| Supabase 공식 MCP | Agent가 내 데이터베이스 구조를 직접 알고 답함 | `.cursor/mcp.json`에 url 방식 한 줄 |
| 토스페이먼츠 MCP | 결제 연동 문서를 Agent가 직접 검색 | stdio 방식(npx) 또는 딥링크 |
| MCP Apps | MCP 결과를 대화형 화면으로 채팅 안에 표시 | Cursor v2.6(2026-03)부터 기본 기능 |

- **Supabase 공식 MCP**: 위 2번의 url 예시(`https://mcp.supabase.com/mcp`)가 바로 이 서버입니다. 설정 방법은 [Supabase MCP 공식 문서](https://supabase.com/docs/guides/getting-started/mcp)에 있습니다.
- **토스페이먼츠 MCP**: PG(결제대행사) 업계 최초의 공식 MCP 서버입니다([AI 도구로 결제 연동하기](https://docs.tosspayments.com/guides/v2/get-started/llms-guide)). `npx -y @tosspayments/integration-guide-mcp@latest`로 실행되며, 문서 검색 도구 4종을 제공합니다 — 최신 v2 문서 검색(get-v2-documents, 기본), 구버전 v1 문서 검색(get-v1-documents), 결제 용어 사전(get-glossary-documents), 특정 문서 원문 전체 조회(document-by-id).
- **MCP Apps**: 별도 설치가 아니라 Cursor 자체 기능으로, MCP 서버가 보내는 결과를 표·다이어그램 같은 대화형 화면으로 채팅 안에 띄웁니다. Figma 다이어그램을 Cursor 밖으로 나가지 않고 바로 볼 수 있습니다.

## 5. 연결이 안 될 때: 점검 순서

"안 돼요"의 원인은 대부분 아래 넷 중 하나입니다. 위에서부터 순서대로 확인하세요.

- [ ] **1. 서버가 켜져 있나** — 데스크톱 방식이라면 Figma 앱의 Dev Mode(개발자에게 디자인 수치를 보여주는 모드, 단축키 Shift+D)에서 'Enable desktop MCP server'가 켜져 있는지 확인합니다(주소 `http://127.0.0.1:3845/mcp`). 원격 방식(`https://mcp.figma.com/mcp`)이라면 Figma 로그인 인증을 마쳤는지 확인합니다.
- [ ] **2. 시트·플랜 한도** — Figma 무료 Starter 플랜은 MCP 호출이 월 6회(2026-07 기준)로 제한됩니다. 어제까지 되다가 갑자기 안 되면 한도 소진일 가능성이 큽니다. 커뮤니티 대체 도구(Framelink)를 써도 이 한도는 그대로 적용됩니다. 지속 실습에는 Professional 플랜의 Dev 시트(1인당 이용권) — $12/월, 연간 청구(2026-07 기준) — 부터 1일 200회 호출이 열립니다([호출 한도 공식 문서](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/)).
- [ ] **3. mcp.json 문법** — 맨 바깥 키가 `mcpServers`인지(`servers`는 VS Code용), 중괄호와 쉼표의 짝이 맞는지 확인합니다.
- [ ] **4. Cursor 재시작** — 설정을 바꿨는데 반영이 안 되면 Cursor를 완전히 껐다 켠 뒤, Customize 페이지에서 서버 상태를 다시 확인합니다.

여기까지 해도 안 되면 등록을 지우고 방법 1(원클릭)로 처음부터 다시 설치하는 것이 가장 빠른 길입니다.

---
> 📌 이 페이지의 모든 요금·절차는 2026-07-23에 공식 문서에서 직접 확인했습니다.
