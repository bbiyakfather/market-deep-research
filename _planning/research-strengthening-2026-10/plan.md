# 조사·크롤링 강화 계획 (2026-10-13 수립, 10-14 착수)

## 한 줄 요약
이 스킬은 "모은 사실이 맞는가"는 두껍게 검사하지만 "못 모은 것이 있는가"는 재지도 막지도 않는다.
강화의 중심은 `curl_cffi` 교체가 아니라 ① 실패를 보이게 하고 ② 빠진 곳으로 되돌아가게 하고 ③ 브라우저 계층을 하나 더하는 일이다.

## 근거
`analysis/` 의 일곱 보고: a1 수집 엔진 · a2 조사 설계 · a3 기존 계획 대조 · a4 과거 조사 7건 실측 · a5 외부 기법 · a6 크롤링 스택 재고 · a7 최신 라이브러리.

## 배치
| 배치 | 내용 | 지시서 | 선행 |
|---|---|---|---|
| RS | 검색 백엔드 상태 반환, 종료 코드 2, SearXNG 재시도·자체 호스팅 | `../batches/batch-RS-search.md` | — |
| RF1 | 지문 프로필 갱신, 의심 페이지 판정, 인코딩, 문서 파일, 제3자 계층 스위치 | `../batches/batch-RF1-fetch.md` | — |
| RD | 워커 COVERAGE, 수렴 판정에 공백 반영, 대상 열거, 탈락 사실 복귀 | `../batches/batch-RD-design.md` | — |
| RE | 대상 재현율·열람 성공률 측정 도구 | `../batches/batch-RE-recall-eval.md` | — |
| RF2 | 브라우저 계층(patchright, 없으면 playwright) | `../batches/batch-RF2-browser.md` | RF1 |
| RM | 수정 전·후 실패 URL 재생 비교, 측정 결과로 5단계 결정 | — | RF2, RE |

## 크롤링 결론
- `curl_cffi` 는 교체하지 않는다(설치본 0.16.2 는 최신 계열). 낡은 것은 코드에 박힌 `chrome110`·`safari180_ios` 프로필이다.
- 브라우저 계층 1순위는 `patchright`(Apache-2.0, Playwright API 호환). Camoufox 는 베타, `nodriver` 는 AGPL.
- Firecrawl 대체는 따로 들이지 않는다. 로컬은 `trafilatura` + 브라우저 계층. 필요 시 `crawl4ai`, 유료 보조는 Tavily Extract(비대외비 URL 만).
- 기존 계획 G1 의 CloakBrowser 는 폐기 권고(새 바이너리가 유료 구독제).

## 일부러 뺀 것
열람 캐시(재검증을 무력화), 통합 프레임워크(Scrapling·Crawlee), 프록시 회전, 로그인 쿠키 추출(G3),
한/영 이중 질의·다관점 질의·Exa 후보 확장(측정 후 결정).

## 사용자 결정 대기
- `source-ladder.md` 가 Googlebot UA 계층을 42행에서는 쓰고 82행에서는 "제외"라고 한다. 계층을 뺄지 문서를 고칠지.
- `main` 의 `tests/test_v4_gates.py`·`test_v4_semantic.py` 가 저장소에 없는 코드(`finalize_report.py`, `facts_db._write_text_atomic`)를 불러와 깨져 있다.

## 결과 (2026-10-14)
- 배치 RS·RF1·RD·RE·RF2 전부 검수 통과. pytest 647 passed(v4 2개 파일 제외, 기준선 602).
- 코디네이터 검수에서 잡아 고친 것: 의심 페이지 판정의 한 단어 오탐(RF1 → RF2 0번), 브라우저 계층의 리다이렉트 경유 내부망 응답(route 는 첫 주소만 본다),
  Jina 가 죽은 페이지를 200 으로 감싸는 경로, `MDR_SEARX_URL` 의 file:// 허용, 워커 지시문의 "COVERAGE 권장" 문구.
- 열람 벤치마크(과거 실패 URL 56건, 죽은 페이지 15건 포함): 진짜 확보 10 → 16(재측정 편차 16~18), 가짜 확보 8 → 0. 표와 한계는 `README.md`.
- 브라우저 계층: 헤드리스는 봇 차단(403) 사이트에서 `curl_cffi` 와 같은 결과. 창 띄움(`MDR_BROWSER_HEADED=1`)에서만 JS 챌린지 일부 통과.

## 5단계 결정
| 후보 | 결정 | 근거 |
|---|---|---|
| Exa 후보 확장 | 보류 | 대상 재현율을 독립 정답지로 잰 수치가 아직 없다. `recall_eval.py score` 로 새 도메인 1건을 잰 뒤 결정 |
| 다관점 질의 자동 생성 | 보류 | 워커 지시문의 "서로 다른 각도 3개 이상" 규칙의 효과를 먼저 본다 |
| 한/영 이중 질의 | 하지 않음(현재) | 언어가 흩어지면 재현율이 떨어진다는 보고가 있고 올린다는 근거는 못 찾음(a5) |
| 자체 SearXNG | 구성 파일만 제공 | 컨테이너 기동은 운영 환경(홈서버) 작업. `assets/searxng/` + `MDR_SEARX_URL` |

## 남은 일
- 설치본(`~/.claude/skills`, claude-sync) 동기화: `install.py` 실행은 사용자 판단.
- `patents.google.com` 22건 재측정(IP 차단 해제 후), 대상 재현율 실측.
- Googlebot UA 계층과 v4 테스트 2개 파일은 위 "사용자 결정 대기" 그대로.

## 교차 리뷰 (grok, `review-grok.md`)
| 지적 | 처리 |
|---|---|
| 높음 1·중간 4 — 구분자 낀 404 제목 누락, 접두만 같은 정상 제목 오탐 | `_DEAD_TITLE_RE` 재작성 + 회귀 테스트 |
| 높음 2 — `_get_trusted` 가 리다이렉트를 따라가 내부망 응답을 검색 결과로 올림 | 리다이렉트 금지 opener, 읽기 8MB 상한 + 로컬 서버 테스트 |
| 높음 3 — 브라우저 계층이 WebSocket 을 검사하지 않음 | `route_web_socket` 으로 전부 닫음, 실제 브라우저로 미도달 확인 |
| 중간 5 — Jina 각색본의 `Title:` 줄 미검사, 경고를 앞 1000자만 봄 | 머리말 전체(`Markdown Content:` 앞)에서 경고·제목 검사 |
| 중간 7 — 문서 40MB 상한이 검색·이미지 호출에 상속 | `request_bytes(doc_cap=)` 로 열람 경로만 |
| 중간 6 — 브라우저는 DNS 를 고정하지 못함(요청은 나간 뒤 내용만 버림) | 수용. 코드에 `shortcut:` 주석. 송신까지 막으려면 필터링 프록시 |
| 낮음 8 — 짧은 본문 제목 접두 검사에 단어 경계 없음 | 경계 추가 |
| 낮음 9 — 짧은 본문(1000자 미만) 구절이 부분 문자열로 걸림 | 수용. `partial` 은 사다리를 계속 타고 내용도 반환된다 |
