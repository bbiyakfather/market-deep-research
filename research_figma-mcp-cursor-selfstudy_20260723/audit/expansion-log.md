# expansion-log — Wave 1 → Wave 2 확장 판단 (2026-07-23, 팀리드)

Wave 1: 6축 전원 반환. fact 83(high 18) · resources 65 · glossary 53 · faq 33 · unique URL 80.
리드 20건 접수 → dedup·분류 결과:

## Wave 2 채택 (3 워커)

- **W2-1 cursor-figma-latest**: docs.cursor.com의 MCP 설정·Figma 플러그인 상세(A1-lead1,
  A2 failed_urls 재커버) + cursor.com/changelog 최근 변경(A2-lead2) + Figma AI credits와
  MCP 호출 과금 관계(A1-lead2) + Figma Make 개요·Cursor 연계(A6-lead2)
- **W2-2 toss-v2-mcp**: @tosspayments/tosspayments-sdk v2 공식 연동 quickstart 원문
  (A5-lead2 — 확보본이 2023 v1 기준이라 학습자 오도 위험) + 토스페이먼츠 MCP 서버
  (A5-lead4 — 강의 주제와 직결) + v2 기준 정기결제 학습 경로
- **W2-3 project-gaps**: P2 요건(결제 포함 OTT 클론 한국어 자료) 재탐색(A6-lead3) +
  P3 요건(Expo Router+Supabase Auth 로그인 확실 자료 2025~26)(A6-lead4) + Vercel 배포
  공식 가이드(A3-lead4) + Supabase auth-ui·Storage quickstart(A3-lead1,2) +
  한국 개인정보보호위원회 크롤링 관련 지침 유무(A4-lead2)

## 팀리드 재검증 단계로 흡수 (워커 불필요)

- A2-lead: cursor.com/changelog 발행 직전 재점검 → 링크 게이트에서 수행
- A5-lead1: YouTube 영상 실검증 → 링크 게이트(oEmbed/메타)에서 수행
- A6-lead1: Udemy 403 재시도 → 링크 게이트(fetch.py/insane-search)에서 수행
- A4-lead1: n8n execution 정의 원문 → 해당 fact 재검증 시 원문 재열람으로 수행

## 드롭 (사유 기록)

- forum.cursor.com Hobby 실한도 체감치: 비공식·변동성 커서 fact 불가. 가이드에는
  "공식 미공개, 체감 한도는 변동" 으로만 기술.
- Cursor 앱 Settings 실측 스크린샷: 이 환경에 Cursor 미설치. 공식 문서 절차 텍스트
  + 공식 문서 링크로 대체(스크린샷은 학습자가 직접 보는 공식 페이지에 있음).
- 토스 상점관리자 실캡처: 로그인 필요 영역이라 캡처 불가. 공식 문서 절차 인용으로 대체.
- Code Connect 난이도 심층: 타깃 학습자(비개발자)에겐 "고급 주제·선택" 딱지로 충분.

## 수렴 판단
Wave 2 (3워커) 후 신규 리드가 기존 커버리지 안이면 수렴 종료(깊이캡 2웨이브 도달).


## Wave 2 결과 및 수렴 종료 (팀리드, 2026-07-23)
Wave 2: 3워커 전원 반환. fact 36(high 4) · resources 25. 주요 획득: 토스페이먼츠 공식 MCP 서버,
Cursor v3.9 Customize UI 개편(문서 간 명칭 불일치 해소), auth-ui 아카이브 확인, Supabase 공식
Expo Social Auth 문서, PIPC AI 안내서(+전용 크롤링 가이드 부재의 negative 확인).
Wave 2 신규 리드 9건 검토: 전부 세부 보강(스크린샷 확보·credits 견적·브랜드페이 상세·PortOne 우회·
정책 모니터링)으로 가이드 필수 범위 밖 → 드롭(사유: 커버리지 충분·비필수). **깊이캡 2웨이브 도달,
수렴 종료.** 단, W2-2 리드 중 결제위젯 연동 페이지 실열람은 팀리드 재검증 단계에서 수행.
