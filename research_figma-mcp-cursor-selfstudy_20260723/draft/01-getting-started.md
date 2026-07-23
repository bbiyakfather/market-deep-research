# 1. 시작하기: 환경 세팅 체크리스트

이 페이지의 목표는 하나입니다. **Cursor(AI가 코드를 대신 써 주는 편집기)가 내 Figma 디자인을 읽어오도록 연결을 끝내는 것.** 이 연결에 쓰이는 기술이 MCP(AI가 다른 프로그램과 대화하는 표준 연결 규격)입니다. 계정 준비부터 연결 확인까지, 처음이라면 반나절 정도 여유를 잡는 것을 권합니다. "1시간 만에 뚝딱"은 세팅이 이미 끝난 사람 기준입니다.

---

## 1) 준비물 한눈에

앞으로 쓸 서비스는 다섯 가지입니다. 지금 당장 전부 가입할 필요는 없지만, 여기서 한 번에 정리해 두면 뒤 페이지에서 "계정이 없어서 멈추는" 일이 사라집니다.

| 서비스 | 무엇에 쓰나 | 무료 범위 (2026-07 기준) | 유료가 필요한 시점 |
|---|---|---|---|
| [Figma](https://www.figma.com/pricing/) | 디자인 작업 + MCP로 디자인을 AI에게 전달 | Starter 플랜: MCP 호출 월 6회 — 사실상 맛보기 | 실습을 본격 시작할 때. Professional Dev 시트 $12/월(연간 청구) |
| [Cursor](https://cursor.com/pricing) | AI 코드 에디터. 이 학습의 메인 작업대 | Hobby 플랜 무료(신용카드 불필요). 한도는 'Limited'로만 표기, 정확한 숫자는 공식 미공개 | 무료 한도가 답답해질 때. Pro $20/월 |
| [Supabase](https://supabase.com/docs/guides/getting-started/quickstarts/nextjs) | 데이터베이스·로그인 등 백엔드(화면 뒤에서 데이터를 저장·처리하는 부분) | 프로젝트 2개, DB 500MB, 월 활성 사용자 5만 명. 1주일간 사용이 없으면 프로젝트 자동 일시정지 | 학습 목적이라면 무료로 충분 |
| [n8n](https://n8n.io/pricing/) | 자동화 도구(반복 작업을 흐름도처럼 이어 붙이는 프로그램) | 셀프호스트(내 컴퓨터에 직접 설치) Community Edition 무료. Cloud는 카드 없이 체험 가능 | Cloud를 계속 쓰고 싶을 때. Starter 20유로/월(연간 결제) |
| [토스페이먼츠 개발자센터](https://docs.tosspayments.com/guides/v2/get-started) | 결제 기능 연습 | 테스트 키(가짜 결제만 일어나는 연습용 열쇠) 무료, 사업자등록 불필요 | 실제 돈이 오가는 서비스를 열 때(전자결제 계약 필요 — 이 학습 범위 밖) |

---

## 2) 비용 현실 체크

시작 전에 돈 이야기를 정직하게 하고 넘어가겠습니다.

**Figma MCP는 무료로 계속 쓸 수 없습니다.** 무료 Starter 플랜에서도 MCP 서버를 켤 수는 있지만, 호출이 **월 6회**(2026-07 기준)로 제한됩니다. 6회면 "연결이 되는구나"를 확인하는 순간 거의 소진됩니다. 플랜별 한도는 [공식 Rate limits 문서](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/)에 표로 나와 있습니다.

**"무료 대체재로 우회하면 된다"는 통념도 사실이 아닙니다.** 커뮤니티 대체재인 [Framelink Figma MCP](https://github.com/GLips/Figma-Context-MCP)도 내부적으로 Figma의 공식 API를 호출하기 때문에, 무료 플랜 파일에는 똑같이 월 6회 제한이 걸립니다. 도구를 바꿔도 한도는 그대로입니다.

**현실적 최소선은 Professional Dev 시트 $12/월(연간 청구, 2026-07 기준)입니다.** 시트란 유료 플랜에서 1인에게 부여되는 이용권입니다. Dev 시트가 있으면 MCP 호출이 하루 200회로 늘어나 실습에 지장이 없습니다. 참고로 AI가 Figma 캔버스에 직접 그리는 기능까지 쓰려면 Full 시트($16/월, 연간 청구)가 필요하지만, 디자인을 코드로 바꾸는 이 학습에는 Dev 시트로 충분합니다. 월간 청구 가격은 공식 페이지에서 확인되지 않아 연간 기준으로만 안내합니다.

**Cursor는 무료로 시작해도 됩니다.** Hobby 플랜은 신용카드 없이 가입되며, 한도에 걸려 불편해지는 시점에 Pro($20/월, 2026-07 기준)를 검토하면 됩니다. 처음부터 결제할 이유는 없습니다.

> 요약: 시작 시점의 고정 지출은 Figma Dev 시트 $12/월 하나입니다. 나머지(Cursor·Supabase·n8n 셀프호스트·토스 테스트 키)는 전부 무료로 진행할 수 있습니다.

---

## 3) 설치 따라하기

### ① Cursor 설치

**[무엇을 배우나]** AI 코드 에디터 Cursor를 내 컴퓨터에 설치하고 로그인합니다.

**[왜 필요한가]** 앞으로 모든 코드는 Cursor 안에서 AI와 대화하며 만듭니다. 작업대가 없으면 아무것도 시작할 수 없습니다.

**[따라하기]**
1. 내 컴퓨터가 요구사항을 충족하는지 확인합니다: **macOS 12(Monterey) 이상 / Windows 10 이상** (2026-07 기준).
2. [Cursor 공식 설치 안내](https://cursor.com/help/getting-started/install)에서 내 운영체제용 설치 파일을 다운로드합니다.
3. **Windows**: 설치 파일을 실행하고 화면의 안내를 따릅니다. **Mac**: 다운로드한 Cursor 아이콘을 Applications 폴더로 드래그합니다.
4. 무료 Cursor 계정을 만들고, 첫 실행 시 안내에 따라 로그인합니다.

**[✅ 이게 보이면 성공]** 로그인이 끝나고 Cursor 에디터 창이 정상적으로 열립니다.

**[막히면]**
- 설치가 진행되지 않음 → 운영체제 버전부터 확인하세요(macOS 12 미만·Windows 10 미만은 지원 대상이 아닙니다).
- 첫 실행에서 로그인 화면만 반복됨 → 계정 생성이 선행 조건입니다. 가입을 먼저 마친 뒤 로그인하세요.

### ② Figma 데스크톱 앱 + Dev Mode MCP 서버 켜기

**[무엇을 배우나]** Figma 데스크톱 앱 안에 숨어 있는 MCP 서버를 켭니다. 이 서버가 내 디자인을 AI가 읽을 수 있는 형태로 내보내는 창구입니다.

**[왜 필요한가]** 이 스위치를 켜지 않으면 Cursor가 아무리 똑똑해도 내 디자인에 접근할 방법이 없습니다.

**[따라하기]** ([공식 데스크톱 서버 설치 문서](https://developers.figma.com/docs/figma-mcp-server/local-server-installation/) 기준)
1. Figma 데스크톱 앱을 설치하고 최신 버전으로 업데이트합니다.
2. Figma Design 파일을 하나 엽니다.
3. 하단 툴바에서 **Dev Mode**(개발자에게 디자인 수치·구조를 보여주는 보기 모드)로 전환합니다. 단축키는 **Shift+D**입니다.
4. Inspect 패널의 **MCP server** 섹션에서 **Enable desktop MCP server**를 클릭합니다.

**[✅ 이게 보이면 성공]** 로컬 서버 주소 `http://127.0.0.1:3845/mcp`가 고정 표시됩니다. 127.0.0.1은 내 컴퓨터 안에서만 열리는 주소라서, 외부에서 내 디자인에 접근할 수는 없습니다.

**[막히면]**
- Dev Mode 버튼이 안 보임 → 앱을 최신 버전으로 업데이트했는지, 그리고 Figma Design 파일을 연 상태인지 확인하세요.
- 데스크톱 앱 설치 자체가 부담스러움 → Figma가 공식 권장하는 **원격 서버** 경로가 있습니다. 앱 설치 없이 주소 `https://mcp.figma.com/mcp`를 쓰고, 접속 시 Figma OAuth(비밀번호 입력 대신 "이 앱에 내 계정 접근을 허용" 버튼으로 승인하는 로그인 방식) 절차를 거칩니다. 자세한 절차는 [원격 서버 설치 문서](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)를 따르세요.

### ③ Cursor에 Figma MCP 연결하기

**[무엇을 배우나]** ①의 Cursor와 ②의 Figma MCP 서버를 서로 연결합니다.

**[왜 필요한가]** 서버를 켜기만 해서는 아무 일도 일어나지 않습니다. Cursor 쪽에서 "이 서버의 말을 듣겠다"고 등록해야 비로소 대화가 시작됩니다. 참고로 Figma MCP는 아무 편집기나 연결되는 것이 아니라 Figma가 등재한 클라이언트(Cursor, VS Code, Claude Code 등)만 허용되는데, Cursor는 공식 지원 대상입니다.

**[따라하기 — 권장 경로]** ([Figma 공식 가이드](https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server) 기준)
1. Cursor의 에이전트 채팅창에 `/add-plugin figma`를 입력해 Figma 플러그인을 설치합니다.
2. Cursor 설정의 **Customize** 페이지 → **Installed MCP Servers**에서 figma 항목의 **Connect**를 클릭합니다.
3. 브라우저가 열리면 Figma 계정으로 로그인해 접근을 승인합니다.

> 메뉴 이름이 문서마다 다를 수 있습니다. Cursor가 2026-06 업데이트(v3.9)에서 MCP 관리 화면을 **Customize** 페이지로 통합했는데, Figma 쪽 가이드에는 아직 구명칭 **Settings > Tools & MCP**로 적혀 있습니다. 같은 화면이니 당황하지 마세요.

**[따라하기 — 수동 경로]** 데스크톱 서버를 직접 등록하고 싶다면 mcp.json(연결할 MCP 서버 목록을 적어 두는 설정 파일)을 씁니다. 위치는 이 프로젝트에서만 쓸 거면 프로젝트 폴더의 `.cursor/mcp.json`, 모든 프로젝트에서 쓸 거면 홈 디렉터리의 `~/.cursor/mcp.json`입니다. 내용은 다음 한 줄이면 됩니다. ([Cursor MCP 공식 문서](https://cursor.com/docs/mcp) 참고)

```json
{ "mcpServers": { "figma-desktop": { "url": "http://127.0.0.1:3845/mcp" } } }
```

**[✅ 이게 보이면 성공]** Installed MCP Servers 목록에 figma가 나타나고, Connect 인증이 완료된 상태로 표시됩니다.

**[막히면]**
- VS Code용 자료를 보고 따라 했는데 안 됨 → VS Code는 설정 파일의 최상위 키가 `"servers"`이고, Cursor는 `"mcpServers"`입니다. 키 이름 하나 차이로 인식이 안 됩니다.
- 연결은 됐는데 몇 번 쓰다가 응답이 막힘 → 무료 Starter 플랜의 월 6회 한도에 걸렸을 가능성이 큽니다. 2)의 비용 현실 체크로 돌아가세요.

---

## 4) 연결 확인

각 단계의 성공 신호를 한 번에 점검합니다.

| 단계 | ✅ 이게 보이면 성공 |
|---|---|
| Cursor 설치 | 로그인 후 에디터 창이 정상적으로 열린다 |
| Figma MCP 서버 | Enable 클릭 후 `http://127.0.0.1:3845/mcp` 주소가 고정 표시된다 |
| Cursor 연결 | Customize(구 Tools & MCP) > Installed MCP Servers에 figma가 인증 완료 상태로 보인다 |
| 최종 확인 | Figma 파일에서 작은 프레임 하나를 선택하고 Cursor 에이전트에 요청했을 때 오류 없이 응답이 돌아온다 |

무료 플랜이라면 최종 확인 호출도 월 6회 한도에서 차감된다는 점을 기억하세요. 확인은 1회로 아끼는 것이 좋습니다.

---

## 5) 전체 체크리스트

- [ ] Figma 계정 가입(무료 Starter로 시작)
- [ ] Figma 결제 방침 결정: 무료 월 6회로 개념만 체험할지, Dev 시트($12/월·연간 청구, 2026-07 기준)로 실습 준비를 마칠지
- [ ] Cursor 무료 계정 가입
- [ ] Supabase 계정 가입(무료)
- [ ] n8n 이용 방식 결정(셀프호스트 무료 또는 Cloud 무료 체험)
- [ ] 토스페이먼츠 개발자센터 가입(이메일·전화번호만으로 가능, [테스트 안내 문서](https://docs.tosspayments.com/blog/how-to-test-toss-payments) 참고)
- [ ] 운영체제 요구사항 확인(macOS 12+ / Windows 10+) 후 Cursor 설치
- [ ] Cursor 첫 실행 및 로그인 완료
- [ ] Figma 데스크톱 앱 설치 및 최신 버전 업데이트
- [ ] Figma Design 파일 열기 → Shift+D로 Dev Mode 진입 확인
- [ ] Enable desktop MCP server 클릭 → `127.0.0.1:3845` 주소 표시 확인(또는 원격 서버 `mcp.figma.com/mcp` 로그인)
- [ ] Cursor 채팅에 `/add-plugin figma` 입력 → 플러그인 설치
- [ ] Customize(구 Tools & MCP) 페이지에서 Connect 인증 완료
- [ ] 작은 프레임 1개로 연결 테스트 1회 성공

---

> 📌 이 페이지의 모든 요금·절차는 2026-07-23에 공식 문서에서 직접 확인했습니다.
