# Codex 적대적 리뷰 (gpt-5.6-sol / xhigh) — v1 계획 대상

> 실행: `codex task --model gpt-5.6-sol --effort xhigh` 로 v1 계획 전문을 적대적 리뷰.
> 판정: **DISAGREE — 핵심 증거 모델과 검증 게이트를 재설계한 뒤 구현해야 한다.**
> Claude 판정: 수용(AGREE). 아래 지적을 v2(plan-v2.md)에 반영함.

## 1. 치명 결함(blocker)
1. **팀리드 재검증 요구 위반** — 핵심수치만 재열람하고 보조수치는 검증 에이전트에 위임, `verified_by:"verifier"` 허용은 "메인이 서브 전부 재검증" 요구와 다름. → 보고서 진입 전 사실은 팀리드 원문 재열람 기록이 있어야 confirmed. verifier 단독 confirm 금지.
2. **`capture_web.py` htmlbox 산출물은 출처 스크린샷이 아님** — 연구자가 그린 재현물, 원문 실재 증거 아님, 조작 발췌도 통과. → `source_capture` vs `reconstructed_excerpt` 분리, 재현물은 3중 증빙의 "출처 스크린샷" 불인정.
3. **단일 `source_url/verbatim/capture`로 삼각검증 표현 불가** — 복수 출처·상이 문구·상충 증거·복수 캡처 연결 불가. → 사실마다 `evidence[]`, 각 증거에 URL·로컬원본·해시·접근시각·locator·verbatim·역할. 검증 이력은 누적 이벤트.
4. **반복 숫자 선택 근본원인 미해결** — `45.2 USD_M`만으론 기준연도·조사시점·국가·시장정의·명목/실질·실적/전망 구별 불가. 순번형 `F001`은 안정적 diff 키 아님. → 안정적 `claim_key` + metric·entity·geography·period·as_of·definition·basis·scenario 필수.
5. **`verify_facts.py`가 무태그 주장·의미 불일치 미차단** — 존재하는 `(Fxxx)`만 확인, 태그 없는 숫자 통과, 부록 전수표가 태그 다 포함하면 "미사용" 검사 무력. → 본문/생성부록 분리 파싱, 무태그 탐지, 값·단위·기간·주체 대조.
6. **증거 체인·게이트 이후 불변성 없음** — source 파일·URL·시각·상태·해시 미연결, G3 이후 파일 교체 가능. → source/capture/report/PDF SHA-256 run manifest, 변경 시 G3 재실행, 최종 PDF 재검사.
7. **verbatim 필수가 표·차트·API·부정조회에 부적용** — 표셀·차트 수치, "제재 0건" 실사결과엔 문장 없음. → 증거유형 `text_quote·table_cell·chart·api_response·negative_search·calculation`.
8. **임의 URL fetch 보안경계 없음** — SSRF·내부주소·리다이렉트 우회·대용량·프롬프트 인젝션·악성 HTML. → HTTP(S)만·private/loopback/link-local 차단·크기/시간/MIME 제한·오프라인 PDF 렌더·원문 불신뢰.
9. **Claude Code 스킬 실행경로 미정의** — frontmatter 미명시, 작업폴더서 `scripts/` 상대경로 실행 시 못 찾음. → frontmatter name/description 명시, 스크립트 스킬루트 기준 해석, 새 세션 트리거 검증.

## 2. 위험(risk) — 요지
DDG/공개SearXNG/Jina SLA 없음(백오프·헬스체크·완전성 미보장) · TLS위장·Googlebot UA 정책 취약(paywall/로그인 우회 금지) · 모바일 URL 도메인별 recipe 필요 · trafilatura 표/각주 누락(원본+정제 둘 다 보존) · Wayback/Jina≠원본(구분) · playwright 스크린샷 URL/시각/viewport 메타 결박 · PDF 정확숫자 검색 표기변형·스캔PDF 취약 · "2출처"≠독립성(재전재 1출처) · A~E 단일등급이 권위/독립/직접/최신 혼합 · 서브에이전트 JSONL 오류율(스키마검증+재요청) · 병렬 파일충돌(에이전트별 폴더) · 환산 `±0.06억` 불완전(Decimal·환율출처·기준일) · 폐기주장 고객노출 실사위험 · `--type patent|news` 백엔드 불일치(미지원 명시 실패).

## 3. 누락(missing) — 요지
기관·기업 동일성 확인 게이트 · run manifest · 조사 종료기준 · 오케스트레이션 join barrier(완료/timeout/재시도/부분실패) · 원본 에이전트 산출물 보존 · 인사이트 검증규칙(사실/추론·근거 F-ID) · `disputed`·`superseded` 상태 · 원자적 기록·복구 · 의존성 preflight · replay 테스트 · 적대적 fixture · 깨끗한 세션 forward test · 설치본 동기화 검증.

## 4. 과잉(overbuilt) — 요지
초기에 전문 API 과다통합(arXiv·SemScholar·CrossRef·SEC·GitHub·Wikipedia·HN) · Reddit/X/YouTube/SE/gh recipe 우선순위 낮음 · Googlebot UA·범용 모바일변환·비계약 캐시 제거 후보 · `capture_web.py`를 증빙 도구로 유지 오해유발 · 반론 3~8개 고정할당 불필요 · 고객 PDF에 폐기목록·실패URL 전수 과도.

## 5. 최종 판정: DISAGREE (우선순위 수정)
1. 보고서 사실 전건 팀리드 재검증 강제 2. 단일출처→복수 evidence·locator·검증이벤트 3. HTML 재현물 증빙 제외 4. claim context + 안정 claim_key 5. 무태그·부록우회·캡처교체 차단 게이트 6. 해시·run manifest 증거체인 7. 표·차트·API·부정조회·계산 증거유형 8. fetch/LLM/HTML 보안경계 9. frontmatter·스킬루트·preflight 10. 범위 축소 후 replay·적대적 fixture·깨끗한 세션 E2E.
