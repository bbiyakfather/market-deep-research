# Batch C — 코어 SKILL.md 슬림화 + 목적별 모드 라우팅

작업 루트: `F:/Claude/skills/market-deep-research/codes/` (브랜치 `feat/purpose-modules`, 워크트리 공유 — 다른 워커가 `market-deep-research/scripts/install.py`·`README.md` 를 동시에 고치는 중이니 그 파일은 건드리지 말 것)

## 배경
사용자 확정: 스킬을 **목적별**로 나눈다 — ① 검색만(`mdr-search`, 이미 생성됨) ② 보고서 초안 MD/PDF(`market-deep-research` 코어, 현행 G0~G5) ③ hwpx 양식화(차후 별도 세션). 목적은 컨텍스트 절약·유지보수·부분 실행.
Codex 리뷰(`_planning/council-2026-08-22/review-codex-modularize.md` M10·5절)의 결론: 코어 `SKILL.md`(현재 184줄·약 9,300자)에서 뺄 수 있는 것은 **백엔드 사용법**(fetch 사다리 계층 상세, pandoc/Chrome 플래그, 이미지 검색 구현, 캡처 CLI 레시피, 모델 분리 메모 등)이고, **영수증 순서·증빙 인정 기준·confirmed-only·3대 원칙·게이트 파이프라인**은 남아야 한다. 상세는 이미 `references/*.md` 에 있다 — SKILL.md 는 **언제 어떤 참조를 읽을지** 가리키는 라우터가 되면 된다.

먼저 읽을 것: `market-deep-research/SKILL.md` 전체, `references/` 9개 파일 제목·절 목록, `mdr-search/SKILL.md`, 그리고 **`market-deep-research/tests/test_adversarial.py` 에서 `_read("SKILL.md")`·`_read("references/...")` 로 문서를 정규식 검사하는 케이스들**(약 1220~1330행: 조사 분할 불릿 `- 조사 분할:`, `**확장수렴 루프**` 블록, `intent-diff` 2회 이상, `[4] render_pdf` 절이 `verification-gates.md` 참조, frontmatter description ≤1024자 + "기술사업화 실사" 포함, report-format/agent-briefs 정합 등). **이 케이스들이 계속 통과해야 한다.**

## 손대는 파일
`market-deep-research/SKILL.md` · `market-deep-research/references/*.md`(이관·보강) · `mdr-search/SKILL.md`(아래 4번)

## 할 일
1. **모드 라우팅 절 추가**(SKILL.md 상단, 3대 원칙 바로 뒤, 8줄 이내): 사용자의 의도가 ① "자료/출처/원문만 모아줘" → 이 스킬이 아니라 `mdr-search`(같은 작업폴더 규칙, 나중에 ②로 승격 가능) ② 증빙형 보고서 초안(MD/PDF) → 이 스킬 G0~G5 ③ hwpx 양식화 → 차후 `mdr-hwpx`(미구현, 지금은 안내만). ①로 시작한 작업폴더를 ②로 승격할 때의 규칙 한 줄(`_sources/` 스냅샷·`sources.md` 는 재사용, 사실대장은 G1 부터 새로).
2. **백엔드 사용법 이관**: 다음을 SKILL.md 에서 한 줄 포인터로 줄이고 상세는 해당 reference 로 옮긴다(이미 있으면 중복 삭제만):
   - [G0] preflight 의 도구 나열 상세 → `verification-gates.md` G0 절(이미 있음 → SKILL 은 "`preflight.py` 실행, 상세는 G0 절" 로)
   - [2]·"모델 분리/자원 재사용" 절의 fetch 사다리 계층 나열·GVR 실측 사례 → `source-ladder.md`(있음) — SKILL 에는 "WebFetch 403 이면 `fetch.py` 로 한 번 더(사다리 상세: source-ladder)" 한 줄만
   - [G2] 의 agent-browser selector 백지 경고·recipe → `evidence-capture.md`(있음) — SKILL 은 "원본 캡처만 증빙 인정, 재구성 발췌 불인정, 상세: evidence-capture" 로
   - [3] 도판 수확 순서 상세 → `image-research.md`(있음)
   - [G3] 검사항목 나열 → `verification-gates.md` G3 절(있음) — SKILL 은 "실패 0 + 기준 manifest 자동 봉인 + 영수증 결박" 수준
   - [4] pandoc/Chrome 플래그·한글경로 → `report-format.md` 렌더 절
   - "참고: .FAILED 글롭" 문단 → verification-gates G4/G5 절
   영수증 규칙(누가 무엇을 기록, extend-only, G5 결박)·게이트 순서도·3대 원칙·산출물·조사 분할·확장수렴 루프 수렴조건·[Bx] 통과조건은 **남긴다**.
3. **목표 분량**: SKILL.md 110~135줄(의미 손실 없이). 참조 문서 표는 유지하되 "언제" 열을 더 구체적으로(예: "G2 캡처 직전", "WebFetch 403 시").
4. **`mdr-search/SKILL.md` 수정**: `fetch.py` 는 **현재 작업 디렉터리(cwd)의 `audit/`** 에 fetch 로그·스냅샷을 쓴다(`scripts/fetch.py` `_audit_fetch_attempt`, `Path("audit")`). 지금 문서는 "scripts/ 를 cwd 로 두거나"라고 써서 로그가 스킬 폴더에 쌓이게 된다 → **cwd = 작업폴더**로 고정하고 스크립트는 절대경로(`<core>/scripts/x.py`)로 부르도록 2·3·4·5단계 명령 표기를 통일. 그 외 내용은 유지.
5. **검증**: `PYTHONIOENCODING=utf-8 python market-deep-research/tests/test_adversarial.py` 전건 PASS(현재 71/71), `wc -l SKILL.md`, frontmatter 가 YAML 로 파싱되는지(`python -c "import yaml..."` 또는 테스트가 확인). worker_done body 에 before/after 줄수·글자수와 테스트 마지막 줄.

## 제약
- `git commit` 금지. `.fablize/goals.py` 실행 금지. `scripts/*.py`·`tests/*.py`·`README.md`·`install.py` 수정 금지.
- 문장을 새로 지어내기보다 **이미 references 에 있는 문장으로 대체**(중복 제거가 목적). 삭제 전 해당 내용이 reference 에 실제로 있는지 확인하고, 없으면 옮겨 붙인 뒤 삭제.
- 모르는 것은 `orca orchestration ask`.
