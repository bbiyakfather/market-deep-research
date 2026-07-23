# 4-3. 프로젝트: OTT 스타일 모바일 앱 (로그인)

## 1. 이번 프로젝트에서 만드는 것

**완성 목표**: 넷플릭스 같은 OTT(온라인 동영상 서비스) 느낌의 모바일 앱 화면에, 이메일 회원가입·로그인 기능까지 붙여봅니다. "내 폰에서 내가 만든 앱에 내 계정으로 로그인"이 이 페이지의 결승선입니다.

**선수지식**: 1~3 페이지(환경 세팅·AI 기초·Cursor × MCP 실전)를 먼저 끝내고 오세요. 4-1·4-2 프로젝트와는 독립적이라 이 프로젝트부터 시작해도 되지만, "Cursor에게 시켜서 프로젝트를 만들고 실행하는 감각"은 미리 갖춰야 합니다.

**모바일은 어떻게?** 이번 실습은 React Native(리액트 네이티브)와 Expo(엑스포)를 씁니다. 한 줄로 요약하면 **"웹을 만들 때 쓰는 자바스크립트 기술로 아이폰·안드로이드 앱을 만드는 도구"**입니다. 앱 개발 언어를 새로 배우는 게 아니라, 웹에서 쓰던 재료를 그대로 들고 갑니다.

---

## 2. Supabase 준비 — 앱의 '서버 겸 창고' 만들기

**[무엇을 배우나]** Supabase(수파베이스, 서버와 데이터베이스를 대신 운영해주는 서비스)에서 프로젝트를 만들고, 코드 없이 마우스로 테이블(데이터를 담는 표)을 만드는 법.

**[왜 필요한가]** 로그인 기능은 "누가 가입했는지"를 어딘가에 저장해야 성립합니다. 그 저장소와 로그인 처리 장치를 Supabase가 통째로 제공하므로, 우리는 서버를 직접 만들 필요가 없습니다.

**[따라하기]**

1. supabase.com에 가입한 뒤, 조직(organization)의 Dashboard에서 **New project**를 눌러 새 프로젝트를 만듭니다.
2. 왼쪽 메뉴의 **Table Editor**(테이블 편집기)를 열고 **New Table**로 테이블 이름을 정해 만듭니다. 공식 절차는 [Supabase Tables 문서](https://supabase.com/docs/guides/database/tables)에 있습니다.
3. **New Column**(새 컬럼)으로 열 이름과 데이터 타입(예: text = 글자)을 지정해 추가합니다. 타입은 반드시 지정해야 하지만, 만든 뒤에도 언제든 컬럼을 추가·삭제할 수 있으니 처음부터 완벽할 필요는 없습니다.

**무료 한도 (2026-07 기준)**: 활성 프로젝트 2개, 데이터베이스 500MB, 월간 활성 사용자(MAU, 한 달에 한 번이라도 접속한 사용자 수) 50,000명. 학습용으로는 넉넉합니다. 단 **1주일간 API 요청이 없으면 프로젝트가 자동 일시정지**됩니다 — 고장이 아니라 절전 모드입니다.

**[✅ 이게 보이면 성공]** Table Editor 화면에 내가 만든 테이블과 컬럼이 표 형태로 보입니다.

**[막히면]**
- 며칠 뒤 접속했는데 프로젝트가 안 열림 → 1주 미사용 일시정지입니다. 대시보드에서 프로젝트를 다시 깨우면(Restore) 됩니다.
- 무료 프로젝트를 3개째 만들려는데 안 됨 → 무료 플랜은 활성 2개까지입니다. 안 쓰는 프로젝트를 정리하세요.

---

## 3. 로그인 붙이기 — 공식 quickstart 경로

**[무엇을 배우나]** Supabase 공식 Expo quickstart(퀵스타트, 최단 코스 안내 문서)를 따라 앱에 회원가입·로그인을 붙이는 법.

**[왜 필요한가]** 로그인은 보안이 걸린 기능이라 블로그의 옛날 코드를 베끼면 사고가 납니다. 공식 문서 경로가 가장 안전하고, 막혔을 때 Cursor에게 물어볼 기준점도 됩니다.

**[따라하기]** 공식 문서 [Use Supabase Auth with React Native](https://supabase.com/docs/guides/auth/quickstarts/react-native)의 순서 그대로입니다.

1. Supabase 프로젝트를 만듭니다(2번 섹션에서 완료).
2. `create-expo-app` 명령으로 Expo 앱을 생성합니다.
3. `supabase-js` 등 필요한 패키지(미리 만들어진 코드 묶음)를 설치합니다.
4. `lib/supabase.ts` 헬퍼 파일(내 앱과 Supabase를 연결해주는 설정 파일)을 작성합니다.
5. `App.tsx`에 Auth 컴포넌트(로그인 화면 조각)를 추가합니다. 로그인에 성공하면 화면에 내 사용자 id가 표시되는 예제까지 문서에 포함돼 있습니다.

**Google 소셜 로그인까지 원하면**: [Login with Google 공식 가이드](https://supabase.com/docs/guides/auth/social-login/auth-google)를 따릅니다. 핵심 순서는 — Google Auth Platform 콘솔에서 **Web application 유형의 OAuth 클라이언트**(구글에 "내 앱이 구글 로그인 좀 쓸게요"라고 등록하는 절차)를 만들고 → **Authorized redirect URIs**(로그인 후 돌아올 주소)에 Supabase 콜백 URL을 등록하고 → 발급된 Client ID/Secret을 Supabase 대시보드의 **Google provider** 설정에 입력해 활성화합니다.

**한 단계 더**: 공식 문서 [Build a Social Auth App with Expo React Native](https://supabase.com/docs/guides/auth/quickstarts/with-expo-react-native-social-auth)는 Expo Router의 **protected routes**(로그인한 사람만 들어갈 수 있는 화면 잠금)와 Apple/Google 소셜 로그인을 함께 다룹니다. "로그인 안 하면 메인 화면 못 들어가게" 만들고 싶을 때 이 문서가 정답지입니다.

**[✅ 이게 보이면 성공]** 앱에서 이메일로 회원가입 → 로그인하면 화면에 사용자 id가 표시됩니다.

**[막히면]**
- 로그인 화면이 안 뜸 → `lib/supabase.ts`의 프로젝트 URL과 키를 대시보드 값과 대조하세요. 오타가 대부분의 원인입니다.
- Google 로그인이 되돌아오다 실패 → redirect URI가 정확히 등록됐는지 확인하세요. 한 글자만 달라도 실패합니다.

---

## 4. RLS 이해하기 — 모든 요청에 자동으로 붙는 조건문

RLS(Row Level Security, 행 단위 보안)는 테이블의 줄(행) 하나하나에 "누가 읽고 쓸 수 있는지" 규칙을 붙이는 기능입니다.

비유하면 이렇습니다. RLS를 켜면 정책(policy)이 **모든 쿼리(데이터 요청)에 자동으로 WHERE절(조건문)을 붙여주는 것**과 같습니다 — 내가 "주문 내역 보여줘"라고만 요청해도, 시스템이 뒤에서 "단, 본인 것만"을 강제로 덧붙이는 셈입니다. 이 비유는 [공식 RLS 문서](https://supabase.com/docs/guides/database/postgres/row-level-security)가 직접 쓰는 설명입니다.

규칙은 하나만 기억하세요. **외부에 노출된 스키마의 모든 테이블에는 RLS를 반드시 켠다.** 안 켜면 앱 사용자 누구나 남의 데이터를 읽을 수 있는 상태가 됩니다. 한국어 실습 예시는 [모두의매뉴얼 RLS 설정 글](https://triki.net/prgm/11626)을 참고하세요.

---

## 5. ⚠️ 주의: 낡은 길 하나, 참고 자료 셋

**@supabase/auth-ui는 배우지 마세요.** 로그인 화면을 기성품처럼 끼워주던 이 UI 라이브러리는 2025-10-23 저장소가 아카이브(더 이상 수정하지 않는 보관 상태)됐고, 2024-02부터 Supabase 팀이 유지보수하지 않는다는 공지가 있었습니다. 검색하면 아직 이걸 쓰는 튜토리얼이 많지만, 신규 학습은 3번 섹션의 공식 quickstart 코드 경로로 가는 것이 맞습니다.

**넷플릭스류 UI를 만들 때 참고할 자료** (모두 무료):

| 자료 | 내용 | 주의점 |
|---|---|---|
| [calebnance/expo-netflix](https://github.com/calebnance/expo-netflix) | React Native/Expo로 만든 넷플릭스 UI 클론 코드 | UI(겉모습)만 있고 로그인은 없음 |
| [notjust.dev 넷플릭스 클론 튜토리얼](https://www.notjust.dev/blog/netflix-clone) | Expo Router·TypeScript·Expo Video를 다루는 무료 튜토리얼(2025-05 게시) | 로그인 구현이 핵심은 아니므로 로그인은 공식 문서로 보완 |
| [TortoiseWolfe Gist](https://gist.github.com/TortoiseWolfe/119b16a4c27c559ede0ddec71a9f7786) | Expo Router + Supabase Auth + NativeWind로 회원가입·로그인 페이지와 보호 라우트를 만드는 튜토리얼 | 커뮤니티 자료 — 공식 문서와 코드가 다르면 공식 우선 |

조합 공식은 단순합니다: **화면은 클론 자료에서, 로그인은 공식 문서에서.**

---

## 6. 참고: 앱에 결제까지 넣고 싶다면

결론부터 말하면, 초보 단계에서는 **결제는 웹(4-2)에서 배우는 것을 권장**합니다. 토스페이먼츠의 최신 v2 SDK는 React Native·Flutter 같은 모바일 네이티브 SDK를 아직 지원하지 않아, 모바일 앱 연동은 구버전인 v1을 써야 합니다. 새로 배우는 사람이 구버전 코드로 시작할 이유는 없으니, 결제 학습은 v2를 그대로 쓸 수 있는 웹에서 끝내고 오세요.

---

## 7. 체크리스트

- [ ] Supabase 프로젝트를 만들고 Table Editor에서 테이블 1개를 만들었다
- [ ] 컬럼에 타입(text 등)을 지정해 추가해봤다
- [ ] Expo quickstart 순서대로 앱을 만들고 `lib/supabase.ts`를 작성했다
- [ ] 이메일 회원가입 → 로그인 → 사용자 id 표시까지 확인했다
- [ ] (선택) Google 소셜 로그인을 연결했다
- [ ] 노출된 모든 테이블에 RLS를 켰다
- [ ] @supabase/auth-ui가 아닌 공식 quickstart 경로로 로그인을 구현했다

---
> 📌 이 페이지의 모든 요금·절차는 2026-07-23에 공식 문서에서 직접 확인했습니다.
