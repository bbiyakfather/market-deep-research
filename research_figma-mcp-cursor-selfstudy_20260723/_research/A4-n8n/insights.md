# A4-n8n 조사 raw 기록 (observed_at 2026-07-23)

## 방문/열람 URL (성공)

- https://n8n.io/pricing/ — 공식 요금 페이지. Starter 20€/mo(연간청구, 2.5K executions), Pro 50€/mo(연간, 10K), Business 667€/mo(연간, 40K, monthly billing 시 800€/mo). Starter/Pro는 무카드 체험, Business는 카드 필요 14일 체험. self-host Community Edition은 GitHub 무료 언급.
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/ — HTTP Request 노드 공식 문서. 목적/메서드(DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT)/인증/쿼리파라미터/헤더/바디/페이지네이션/타임아웃 옵션 확인.
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.html/ — HTML 노드 공식 문서(한국어 자동번역판으로 렌더된 듯). v0.213.0부터 HTML Extract 노드를 대체. Extract HTML Content에서 CSS Selector + 반환유형(속성/HTML/텍스트/값) 지정.
- https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker.md — Docker self-host 공식 절차. `docker volume create n8n_data` 후 `docker run -it --rm --name n8n -p 5678:5678 -e GENERIC_TIMEZONE=... -e TZ=... -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true -e N8N_RUNNERS_ENABLED=true -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n`. PostgreSQL 연동 시 DB_TYPE 등 env 추가. self-host 필요 역량: "Setting up and configuring servers and containers, Managing application resources and scaling, Securing servers and applications" / "n8n recommends self-hosting for expert users".
- https://docs.n8n.io/sitemap.md — 구 URL(hosting/installation/docker)이 deploy/host-n8n/install-options/install-with-docker.md 로 이동했음을 확인(문서 개편).
- https://n8n.io/workflows/14996-aggregate-multi-source-job-boards-to-supabase-and-google-sheets/ — 공식 템플릿 갤러리 예시. Schedule Trigger → HTTP Request(배치5) → 정규화 → "Deduplicated results are upserted to a Supabase (Postgres) table and written to Google Sheets". DB 적재 워크플로 패턴 확인용.
- https://github.com/enescingoz/awesome-n8n-templates — 커뮤니티 템플릿 모음(280+ free templates, 19k+ stars). Google Drive&Sheets 카테고리 13개 템플릿, Supabase 관련 5개 템플릿(insert/upsert/search, Telegram bot memory, Notion→Supabase vector store 등).
- https://developers.google.com/search/docs/crawling-indexing/robots/intro — robots.txt 공식 설명(Google Search Central). "The instructions in robots.txt files cannot enforce crawler behavior... it's up to the crawler to obey them." 법적 구속력 없음, 관례적 준수.
- https://www.edpb.europa.eu/system/files/2026-07/edpb_guidelines_2020603_webscraping_v1_en_0.pdf — EDPB(유럽개인정보보호위원회) "Guidelines 03/2026 on web scraping in the context of generative AI", Version 1.0, Adopted 07 July 2026. PDF 직접 다운로드 후 Read 도구로 1~3페이지 열람. Executive summary: "The GDPR applies to web scraping when it includes personal data processing operations, such as collection, storage, organisation and retrieval." 최신(2026-07) 공식 규제기관 문서라 신뢰도 높음.
- https://n8n-docs.infograb.net/courses/level-two/chapter-2/ — 인포그랩(InfoGrab)이 OpenAI 기반 자동번역으로 제공하는 n8n 공식문서 한글판(국내 최초 언급). Level1(기초 UI, 미니 워크플로)/Level2(데이터 구조·병합·분할·에러처리) 커리큘럼 구조 확인.
- https://www.jiniai.biz/2025/03/20/n8n%EC%97%90%EC%84%9C-http-%EC%9A%94%EC%B2%AD-%EB%85%B8%EB%93%9C-%ED%99%9C%EC%9A%A9%ED%95%98%EA%B8%B0/ — 한국어 블로그(2025-03-20 게시). HTTP Request 노드 실습 3단계: JSONPlaceholder API 호출→분할, Wikipedia 랜덤 페이지 크롤링(기사 제목 추출), GitHub API 페이지네이션. 초보자 따라하기 가능한 수준.

## 검색만 하고 원문 미확인(스니펫 기반, resources 후보로만 사용)

- YouTube: "당신이 원하던 n8n 2026 버전 마스터클래스" 8시간 완전정복 기초강의 (watch?v=LR2vONAVEYk) — 검색 스니펫 기준. 본문(영상) 열람 불가라 fact 미등재.
- YouTube 재생목록: "n8n 강의/강좌"(youtube.com/playlist?list=PL6skWNka9B4v9h1mm57TzTzqXjWICUQTQ), "n8n 사용법 기초 클래스"(playlist?list=PLkt-u2nHD3yOvA6L1MAeZtA4UXIjyG_2e) — 스니펫만.
- knockknows.com "N8N 사용법 - HTTP Request 노드 및 HTTP 메소드 이해" — 검색 스니펫만 확인, 미열람.

## 실패/차단 URL (failed_urls)

- https://docs.n8n.io/hosting/installation/docker/ — 404 (문서 개편으로 URL 이동, deploy/host-n8n/install-options/install-with-docker.md 로 대체 확인됨)
- https://docs.n8n.io/hosting/installation/docker — 404 (동일)
- https://docs.n8n.io/code/cookbook/http-node/ — 404 (문서 개편, 정확한 대체 URL 미확인)
- https://ico.org.uk/about-the-ico/what-we-do/our-work-on-artificial-intelligence/response-to-the-consultation-series-on-generative-ai/the-lawful-basis-for-web-scraping-to-train-generative-ai-models/ — HTTP 403 Forbidden (WebFetch 차단). EDPB 공식 PDF로 대체 확보.

## 방문 안 함 (저작권/스코프 제외)

- fastcampus.co.kr/biz_online_n8n — 검색 결과에 노출되었으나 지시에 따라 방문/인용하지 않음.

## 판단 메모

- risk:high 대상은 n8n Cloud 요금(Starter/Pro/Business 가격·실행횟수)뿐. 공식 pricing 페이지 직접 열람 + 별도 표현("n8n cloud pricing Starter Pro Business monthly cost per execution official")으로 재검색한 결과, 여러 독립 애그리게이터(sliplane.io, connectsafely.ai, costbench.com 등)가 동일 수치(연간 20/50/667€, 월간 24/60/800€)로 수렴 → counter 결과 "일치, 반박 없음"으로 기록.
- 무료체험 조건(카드 필요 여부)은 가격 수치 자체가 아니라 정책이라 risk는 normal로 낮춤.
- HTML 노드 문서 페이지가 한국어로 렌더링된 것은 WebFetch가 브라우저 로케일/번역을 반영한 것으로 보이며, 영어 원문 UI 텍스트(예: "Extract HTML Content")는 별도로 확인됨.
- EDPB 가이드라인(2026-07-07 채택)은 이 시점 기준 가장 최신·최고 권위 출처라 판단해 로컬 PDF Read로 verbatim 확보.
