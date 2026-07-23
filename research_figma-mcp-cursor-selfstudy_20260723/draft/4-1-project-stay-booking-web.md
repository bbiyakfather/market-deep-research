# 4-1. 프로젝트: 숙박 예약 스타일 웹 (데이터 수집)

에어비앤비처럼 숙소 카드가 늘어선 목록 화면과, 카드를 누르면 나오는 상세 화면을 직접 만드는 프로젝트입니다. 화면만 만들면 "빈 껍데기"라서, 이번 프로젝트의 진짜 핵심은 **n8n(코드 없이 블록을 이어 자동화를 만드는 도구)으로 공개 데이터를 수집해 화면을 채우는 것**까지입니다.

---

## 1. 완성 목표와 필요 선수지식

**완성했을 때 손에 남는 것:**

- Figma로 디자인한 숙소 **목록 화면**(카드 그리드)과 **상세 화면**(사진·이름·가격·설명)
- n8n이 공개 웹페이지에서 자동으로 모아 온 데이터가 Supabase(회원·데이터베이스 기능을 대신 운영해 주는 백엔드 서비스) 또는 Google Sheets에 쌓이는 파이프라인
- 그 데이터가 실제로 화면에 표시되는 작은 서비스

**시작 전에 반드시 끝내야 할 페이지:**

| 선행 페이지 | 여기서 갖춰야 할 것 |
|---|---|
| 1. 시작하기 | Figma·Cursor 계정, Cursor 설치, Figma MCP 연결 완료 |
| 2. AI 기초 개발 | Agent 모드로 작은 결과물을 만들어 본 경험 |
| 3. Cursor × MCP 실전 | Figma 디자인 → 코드 변환 흐름을 한 번 완주한 경험 |

위 세 페이지를 건너뛰면 이번 프로젝트 중간에 계정·설치 문제로 반드시 멈추게 됩니다. 세팅은 미리, 실습은 한 번에 — 이것이 이 커리큘럼의 원칙입니다.

---

## 2. 화면 만들기 — Figma 디자인을 Cursor로 코드로

**[무엇을 배우나]** 숙소 목록/상세 화면을 Figma에서 디자인하고, Cursor의 Agent(복잡한 코딩 작업을 대신 수행하는 AI 비서 모드)가 그 디자인을 읽어 코드로 옮기게 하는 흐름입니다.

**[왜 필요한가]** 디자인을 눈으로 보고 코드로 "손 번역"하는 일은 개발자에게도 오래 걸리는 작업입니다. Figma MCP를 쓰면 AI가 디자인의 크기·색·간격 정보를 직접 읽으므로, 비개발자도 화면을 코드로 바꾸는 경험을 할 수 있습니다.

**[따라하기]**

1. Figma에서 목록 화면과 상세 화면을 그립니다. 직접 그리기 부담스러우면 Figma 안의 Community 탭에서 공유된 무료 숙소 예약 UI 템플릿을 복제해 시작해도 됩니다.
2. [Figma 공식 가이드](https://github.com/figma/mcp-server-guide)가 권장하는 대로 준비하세요 — 버튼·카드처럼 반복되는 요소는 컴포넌트로 만들고, 레이어 이름은 "Group 5" 대신 "RoomCard"처럼 뜻이 보이게 짓고, Auto Layout(요소 간격을 자동으로 유지해 주는 Figma 기능)을 적용합니다. 이 준비가 코드 품질을 좌우합니다.
3. 시작하기 페이지에서 한 대로 Cursor 에이전트 채팅에 `/add-plugin figma`로 연결한 뒤([공식 절차](https://help.figma.com/hc/en-us/articles/39889260656407-Cursor-and-Figma-Set-up-the-MCP-server)), Figma에서 **카드 컴포넌트 하나만** 선택하고 "이 디자인으로 숙소 카드 컴포넌트를 만들어 줘"라고 요청합니다.
4. 카드가 잘 나오면 목록 화면 → 상세 화면 순서로 범위를 넓힙니다. 화면 전체를 통째로 선택하면 응답이 느려지거나 불완전해질 수 있어, 공식 문서도 논리적 단위로 쪼개 요청하라고 안내합니다.

주의: 무료 Starter 플랜의 MCP 호출은 월 6회(2026-07 기준)라 이 프로젝트 실습에는 부족합니다. Professional Dev 시트($12/월, 연간 청구, 2026-07 기준)면 하루 200회까지 쓸 수 있습니다([한도표](https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/)).

**[✅ 이게 보이면 성공]** 브라우저 미리보기에서 숙소 카드 여러 장이 격자로 보이고, 카드를 누르면 상세 화면으로 이동합니다.

**[막히면]**

| 증상 | 해결 |
|---|---|
| 생성된 화면이 디자인과 많이 다름 | 프레임을 더 작게 쪼개 다시 요청, 레이어 이름·Auto Layout부터 정리 |
| MCP 호출이 안 됨 | 시작하기 페이지의 연결 절차 재확인, 이번 달 호출 한도 소진 여부 확인 |

**구조가 궁금할 때 참고할 학습 자료** (필수 아님, 구조 참고용):

| 자료 | 성격 | 유의점 |
|---|---|---|
| [노마드코더 에어비앤비 클론코딩](https://nomadcoders.co/airbnb-clone) | 유료 한국어 강의, 검색·찜·예약·후기까지 | 백엔드가 Django 스택 — 이 커리큘럼(Next.js)과 다르므로 "어떤 기능이 필요한가"의 구조 참고용 |
| [Mastering Next.js 14 - Build Airbnb Clone](https://www.udemy.com/course/mastering-nextjsbuild-an-airbnb-clone-from-scratch-2024/) | Udemy 유료 영문 강의 | Next.js 14 기반이라 스택은 맞지만 영어 진행 |
| [SashenJayathilaka/Airbnb-Build](https://github.com/SashenJayathilaka/Airbnb-Build) | 무료 오픈소스 완성 코드 | 강의가 아닌 결과물 코드 — Cursor에게 "이 저장소 구조를 설명해 줘"라고 묻는 용도로 적합 |

---

## 3. n8n으로 데이터 수집 — 화면에 진짜 데이터 채우기

**[무엇을 배우나]** n8n으로 공개 웹페이지의 텍스트를 자동 수집(크롤링: 프로그램이 웹페이지를 읽어 데이터를 모으는 것)해 Supabase나 Google Sheets에 쌓는 워크플로입니다.

**[왜 필요한가]** 숙소 100개를 손으로 입력할 수는 없습니다. 자동화 도구가 대신 모아 주면, 여러분은 "무엇을 모을지"만 설계하면 됩니다. 이것이 기획자가 데이터 파이프라인을 이해하는 가장 빠른 길입니다.

**[따라하기 — 1단계: n8n 시작하기 (세 가지 방법)]**

1. **Cloud 체험** — 가장 쉬운 길. [n8n Cloud](https://n8n.io/pricing/)는 Starter/Pro 플랜을 신용카드 없이 체험할 수 있습니다. 체험 후 계속 쓰려면 Starter 20유로/월(연간 결제, 2026-07 기준)입니다.
2. **Docker(내 컴퓨터에 프로그램을 통째로 담아 실행하는 컨테이너 도구)로 직접 설치** — 무료. 터미널에 아래 두 줄을 순서대로 입력한 뒤 브라우저에서 `localhost:5678`을 엽니다([공식 문서](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker)).
   - `docker volume create n8n_data`
   - `docker run -it --rm --name n8n -p 5678:5678 -e GENERIC_TIMEZONE=Asia/Seoul -e TZ=Asia/Seoul -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n`
3. **Community Edition 확인** — 직접 설치판(셀프호스트)은 GitHub에서 무료로 제공되는 표준 버전입니다. 다만 직접 설치는 서버·보안 지식이 없으면 부담될 수 있으니, 어렵게 느껴지면 Cloud 체험으로 시작하세요. 영어가 부담이면 [인포그랩의 n8n 한국어 문서](https://n8n-docs.infograb.net/courses/level-two/chapter-2/)가 단계별 커리큘럼을 제공합니다.

**[따라하기 — 2단계: 수집 워크플로 만들기]**

1. 새 워크플로에 [HTTP Request 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)(노드: n8n에서 작업 한 개를 뜻하는 블록)를 추가하고, GET 방식으로 수집할 공개 페이지 주소를 넣어 실행합니다. 페이지의 HTML(웹페이지의 뼈대 문서)이 통째로 응답에 담겨 옵니다.
2. [HTML 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.html/)를 이어 붙이고 'Extract HTML Content' 동작을 선택합니다. CSS Selector(웹페이지에서 특정 요소를 콕 집어내는 주소 표기법)를 넣고 반환 유형을 '텍스트'로 지정하면, 숙소 이름·가격 같은 원하는 값만 뽑혀 나옵니다.
3. 뽑은 데이터를 Supabase 테이블 또는 Google Sheets에 적재합니다. 처음부터 만들 필요 없이 [공식 템플릿 "여러 소스를 Supabase와 Google Sheets에 동시 적재"](https://n8n.io/workflows/14996-aggregate-multi-source-job-boards-to-supabase-and-google-sheets/)를 복제해 내 대상에 맞게 고치는 편이 빠릅니다. 참고로 GitHub의 awesome-n8n-templates 저장소에는 이런 무료 템플릿이 280개 이상 모여 있습니다.

**[✅ 이게 보이면 성공]** 워크플로를 실행할 때마다 Supabase Table Editor나 Google Sheets에 숙소 데이터 행이 새로 쌓이고, 그 데이터가 2장에서 만든 목록 화면에 표시됩니다.

**[막히면]**

| 증상 | 해결 |
|---|---|
| `localhost:5678`이 안 열림 | Docker Desktop이 실행 중인지, `docker run` 명령이 오류 없이 끝났는지 확인 |
| HTML 노드 결과가 비어 있음 | CSS Selector 오타 확인 — 브라우저 개발자 도구로 요소를 다시 확인하고, 위키백과처럼 구조가 단순한 페이지로 먼저 연습 |
| Cloud 체험이 끝남 | Docker 설치(무료)로 전환하거나 Starter 결제 검토 |

---

## 4. ⚠️ 크롤링 전에 알아야 할 것

수집 기술보다 먼저 지켜야 할 규칙이 있습니다. 이 섹션은 반드시 실습 전에 읽으세요.

- **robots.txt(사이트가 크롤러에게 "여기는 읽지 마세요"라고 알려 주는 안내 파일)** — [Google 공식 문서](https://developers.google.com/search/docs/crawling-indexing/robots/intro)에 따르면 이 지침에 법적 강제력은 없고 크롤러가 자발적으로 따를지에 달려 있습니다. 강제력이 없더라도 **존중이 원칙**입니다. 수집 전 `대상사이트/robots.txt`를 열어 확인하세요.
- **이용약관** — 많은 사이트가 약관에서 자동 수집을 제한합니다. robots.txt와 별개로 대상 사이트의 약관을 확인하는 습관을 들이세요.
- **개인정보는 공개돼 있어도 보호 대상입니다** — 유럽 개인정보 감독기구 EDPB가 2026년 7월 7일 채택한 [웹 스크래핑 가이드라인](https://www.edpb.europa.eu/system/files/2026-07/edpb_guidelines_2020603_webscraping_v1_en_0.pdf)은 스크래핑이 개인정보의 수집·저장을 포함하면 GDPR(유럽 개인정보보호법)이 적용된다고 명시합니다. 국내에서도 개인정보보호위원회가 2024년 7월 공개한 「인공지능(AI) 개발·서비스를 위한 공개된 개인정보 처리 안내서」가 웹에 공개된 개인정보를 수집·처리할 때의 법적 기준을 다룹니다(원문은 개인정보보호위원회 누리집의 안내서 게시판에서 제목으로 검색). 참고로 '웹크롤링' 자체를 표제로 한 국내 종합 공식 가이드라인은 현재 확인되지 않습니다.

**이 학습에서의 실천 수칙:**

> 1. 로그인해야 보이는 페이지는 수집하지 않는다.
> 2. 이름·연락처·리뷰 작성자 닉네임 등 개인정보는 수집 대상에서 뺀다.
> 3. 학습·실습은 공개 데이터(공공데이터, 위키류, 자기 소유 페이지)로만 한다.

---

## 5. 단계별 체크리스트

- [ ] 시작하기·Part 1·Part 2 페이지의 준비물을 모두 갖췄다
- [ ] Figma에서 숙소 목록/상세 화면을 그렸다 (또는 Community 템플릿을 복제했다)
- [ ] 카드 컴포넌트·시맨틱 레이어 이름·Auto Layout을 정리했다
- [ ] Cursor에서 카드 → 목록 → 상세 순서로 화면을 생성했다
- [ ] n8n을 Cloud 체험 또는 Docker로 실행해 `localhost:5678`(또는 Cloud 주소)에 접속했다
- [ ] HTTP Request 노드로 공개 페이지의 HTML을 받아 왔다
- [ ] HTML 노드의 CSS Selector로 숙소 이름·가격 텍스트를 추출했다
- [ ] 추출한 데이터를 Supabase 또는 Google Sheets에 적재했다
- [ ] 수집 전 robots.txt와 이용약관을 확인했고, 개인정보는 수집 대상에서 제외했다
- [ ] 목록 화면에 수집된 진짜 데이터가 표시된다

---
> 📌 이 페이지의 모든 요금·절차는 2026-07-23에 공식 문서에서 직접 확인했습니다.
