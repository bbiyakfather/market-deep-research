# HANDOFF — factsheet-research 스킬 제작

> 작성 2026-07-21. 상태: **설계 확정(v2), 구현 착수 전.** 다음 세션이 이 문서만 읽고 이어가도록 정리.

## 무엇을 만드나 (한 줄)
기술사업화 기관(내비온)용 **증빙형 시장조사 보고서 생성 Claude Code 스킬**.
기술동향·산업동향·기관/기업 실사·시장조사를 팀리드+서브에이전트로 수행하고,
[조사내용 → 출처 → 스크린샷] 증거구조로 **조사마다 수치가 달라지는 문제**를 제거한 팩트시트 PDF를 낸다.

## 사용자 3대 요구 (우선순위)
1. **오케스트레이션** — 팀리드(메인 세션)가 서브에이전트 조사결과를 **보고서 진입 전건 재검증**. 토큰 낭비 OK, 정확성 최우선.
2. **차단봇 우회 + extract** — **유료 API(firecrawl/tavily) 무의존 자체 스택**으로 1차출처 수집·추출.
3. **팩트시트 보고서(최중요)** — fact+evidence 증거모델 + 검증게이트 + GitHub PDF 스타일. 에이전트별 인사이트 챕터.

## 확정 사항
- **설계 원본 뿌리**: `C:\Users\김형일\Documents\카카오톡 받은 파일\00_WORKFLOW_시장조사보고서_제작가이드.md` (검증된 8단계 플레이북).
- **접근**: 기존 `market-deep-research` 스킬 패치가 아니라 **신규 제작**. 기존 스킬은 수정 금지(완성 후 폐기 여부 사용자 판단).
- **적대적 리뷰**: Codex(gpt-5.6-sol/xhigh)가 v1 계획을 **DISAGREE(재설계)** 판정. Claude 수용 → v2 반영. → `_planning/codex-review.md`
- **사용자 결정 2건**:
  - (A) 팀리드 재검증 = **보고서 진입 전건** (핵심수치만 아님).
  - (B) 산출물 = **고객용 report.pdf + 내부 audit 번들 2종 분리** (폐기목록·실패URL·미확인 의혹은 고객 PDF 미노출).

## v1 → v2 핵심 변경 (Codex 합의 반영)
- 단일 `source_url/verbatim/capture` → **`fact` + `evidence[]` 배열** (복수출처·삼각검증·상충 표현)
- 평면 value → **claim_key + context**(metric·entity·geography·period·as_of·basis·scenario) ← "수치 달라짐" 근본 해결
- verbatim 필수 → **증거유형 6종**(text_quote/table_cell/chart/api_response/negative_search/calculation)
- htmlbox 재현물 = **출처 스크린샷 불인정**(내부 reconstructed_excerpt로만)
- **run manifest + SHA-256** 증거체인 고정, 파일 변경 시 G3 재실행
- fetch.py **보안경계**(SSRF/사설IP/크기/MIME, 원문=불신뢰)
- v1 소스 **축소**: DDG+SearXNG+arXiv+SEC+Wikipedia. 나머지는 recipe 문서로만.
- A~E 단일등급 → **4차원**(authority/independence/directness/recency)

## 산출물 위치
- 개발본(이 repo): `codes/factsheet-research/`  →  완성 후 설치본 `~/.claude/skills/factsheet-research/`
- 스킬 구조: `SKILL.md` + `references/`(7종) + `scripts/`(11종) + `assets/`(4종). 상세 트리는 plan-v2.md.

## 지금까지 한 일 (DONE)
- [x] 원본 플레이북 분석 + 기존 스킬 3종(market-deep-research, insane-search, deep-research×2) 실측
- [x] 외부 6개 repo 벤치마크(insane-research/cloakbrowser/open_deep_research/market-research topics/startup-skill/hoolulu)
- [x] v1 계획 → Codex 적대적 리뷰 → v2 재설계 (`_planning/plan-v2.md`, `_planning/codex-review.md`)
- [x] 사용자 결정 2건 반영
- [x] shrimp-task-manager: `plan_task` → `analyze_task` 완료

## 다음 할 일 (NEXT — 여기서 이어가기)
1. shrimp 체인 마저: `reflect_task` → `split_tasks`(원자 작업 DAG). ※ 사용자가 handoff/push 요청으로 중단시킨 지점.
2. 구현 순서(plan-v2.md "구현 순서" 절):
   ① 뼈대(SKILL.md frontmatter + skill_paths.py) → ② fetch.py(보안경계 우선)+search.py+JSON → 라이브 스모크
   → ③ facts-schema.json+facts_db.py+manifest.py → ④ references 7종 → ⑤ style.html
   → ⑥ capture/verify/render/preview → ⑦ 적대적 fixture 테스트 → ⑧ replay → ⑨ E2E 미니조사 → ⑩ install.py
3. 완료 기준: plan-v2.md "검증" 절 체크리스트 전부 통과 (특히 무료 스택만으로 E2E, 적대적 fixture 전건 실패 검출).

## 환경 메모
- Windows 11, Python 3.12, `PYTHONUTF8=1`(한글 콘솔). 신규 pip: `curl_cffi`,`trafilatura`(+선택 `yt-dlp`)만.
- 기존 보유: PyMuPDF(fitz)·pandoc·HeadlessChrome·playwright MCP·openpyxl.
- 재사용 코드 패턴(원가이드): fitz 하이라이트 캡처 / verify 정규식 / pandoc(gfm→html,--embed-resources)→Chrome(--print-to-pdf 절대경로·한글경로 퍼센트인코딩).

## 참고 파일
- `_planning/plan-v2.md` — 확정 설계(권위본). 원본은 `~/.claude/plans/codex-setup-to-gpt-jazzy-lampson.md`
- `_planning/codex-review.md` — Codex 적대적 리뷰 전문
