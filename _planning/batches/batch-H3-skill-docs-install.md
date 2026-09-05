# Batch H3 — `mdr-hwpx/SKILL.md` + `references/` + 코어 라우팅·install allowlist·README

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/purpose-modules`, 워크트리 공유 — 다른 워커가
`codes/mdr-hwpx/scripts/*`·`profiles/`·`assets/` 를 동시에 만든다. **그 폴더는 건드리지 말 것.** 스크립트가 아직 없어도
문서는 설계 문서의 CLI 계약 표기를 그대로 쓰면 된다.)

## 먼저 읽을 것
1. `_planning/council-2026-08-22/hwpx-module-design.md` — 전체 설계·3단계 흐름·CLI 계약·"만들지 않는 것".
2. `codes/market-deep-research/references/hwpx-form.md` (전문) — 옮길 대상.
3. `codes/mdr-search/SKILL.md` — 목적 스킬의 문체·구조(전제: 코어 설치, cwd=작업폴더, 절대경로 `<core>/scripts`). **같은 톤으로.**
4. `codes/market-deep-research/SKILL.md` 의 「목적별 모드」절(27행 근처 `③ hwpx 양식화 → 차후 mdr-hwpx(미구현…)`).
5. `codes/market-deep-research/tests/test_adversarial.py` 에서 `_read("SKILL.md")` 로 문서를 정규식 검사하는 케이스들 — 코어 SKILL.md 한 줄을 고친 뒤에도 **전건 통과**해야 한다.
6. `codes/market-deep-research/scripts/install.py`(SKILLS allowlist, INCLUDE) 와 `README.md` 설치 절(175행 근처).
7. 참고(정합성 체크리스트 재료): `F:/Claude/work/navion-market-research/global pem projects/CLAUDE.md` 의 시각자료 규칙·교훈 절, 같은 폴더 `research_…/audit/form_spec.md` 「원고 마크다운 → 양식 변환 규칙 요약」.

## 손대는 파일
- 새로: `codes/mdr-hwpx/SKILL.md`, `codes/mdr-hwpx/references/hwpx-form.md`(코어 것을 **복사** — 코어 원본 삭제는 코디네이터가 한다), `codes/mdr-hwpx/references/consistency-review.md`
- 수정: `codes/market-deep-research/SKILL.md`(③ 한 줄만), `codes/market-deep-research/scripts/install.py`(`SKILLS` 튜플에 `"mdr-hwpx"` 추가 + docstring 한 줄 + `demo()` 가 세 스킬을 다루도록 최소 수정), `README.md`(설치 절 "세 스킬" 로 갱신 + 목적별 스킬 표에 mdr-hwpx 한 줄)

## 할 일
1. **`codes/mdr-hwpx/SKILL.md`** (90~130줄)
   - frontmatter: `name: mdr-hwpx`, `description`(200~250자, 조금 "pushy"): 원고 md → 발주처 한글 양식(hwpx) 변환, 부별 모듈 병렬 빌드·정합성 검토·공식 양식 합본. "한글로/hwpx로/양식에 맞춰/발주처 양식/보고서 양식화" 류 요청이면 이 스킬. 조사·검색·보고서 초안 작성은 제외(→ market-deep-research / mdr-search).
   - 전제: 코어(`market-deep-research`) 설치 여부와 무관하게 **단독 실행 가능**(스크립트는 `<this>/scripts`), 한글(Hwp.exe)·PyMuPDF·PIL·pywin32 가 있는 Windows. cwd = 작업폴더(원고 `manuscript/`, 그림 `assets/`). 템플릿은 사용자가 주는 `양식.hwpx` 경로; 내비온 양식은 `assets/forms/navion-2026.hwpx` + `profiles/navion-2026.json` 동봉.
   - **3단계 흐름**(설계 문서 그대로): ① 모듈 빌드(부별 병렬 — 오케스트레이션 시 워커 1 = 원고 1부, 워커는 build→export→grade 후 결함을 **원고 md 수준에서만** 고치고 재빌드, 양식·코드 수정 금지, worker_done 에 grade 요약) ② 정합성 검토(`build_hwpx.py outline` 출력 + `references/consistency-review.md`) ③ 공식 양식 맞추기(`merge_hwpx.py` → `export_pdf.py` → `grade_pdf.py` → 한글에서 눈으로). 각 단계의 명령을 설계 문서 CLI 계약 표기 그대로.
   - 원고 마크다운 문법 표(hwpx-form.md 끝의 "원고 마크다운 문법" 블록을 요약 — `# ## ### ####`·`① `·`❍ `·`- `·`<표>`·`| |`·`* 출처 :`·`![]()`·`[그림]`·`**굵게**`·`<sup>`). 불릿 접두 기호는 양식이 그리므로 원고에 남겨도 빌더가 뗀다는 것.
   - 새 양식을 만났을 때: `form_probe.py 양식.hwpx` 로 실측 → `profiles/<이름>.json` 작성 → `form_probe.py --profile` 로 ID 존재 검사 → `build` — 코드는 고치지 않는다.
   - 통과 기준: grade 4지표 결함 0(또는 사유 기록), 한글에서 열어 **의심쪽 PNG 를 사람이 본다**(정적 검사는 검증이 아니다).
   - "만들지 않는 것" 절(설계 문서 그대로). 참조 문서 표(`references/hwpx-form.md` — 언제: 새 양식 실측·그림/표 깨질 때; `references/consistency-review.md` — 언제: ② 단계).
2. **`references/consistency-review.md`** (40~70줄) — ② 단계 체크리스트. 항목: (a) 부 번호·순서가 목차와 일치 (b) `<표>`/`[그림]` 순번이 부 안에서 1부터 연속·중복 캡션 없음 (c) 같은 수치가 여러 부에 나오면 값·시점·단위 동일(예: Ⅱ 집계값 ↔ Ⅴ 결론 인용) (d) 용어·고유명사 표기 통일(영문 병기 첫 등장 1회) (e) 각주 마커 ↔ 정의 짝 맞음 (f) 전년판 대비 문구("전년" 기준 연도 명시) (g) 출처행 형식 `* 출처 : 기관 (연도)` 통일 (h) 그림 파일 존재·ASCII 경로(한글 파일명 임베드 실패 교훈) (i) 원고에 남은 마크다운 잔재(`\<표\>`, 링크 문법). 각 항목에 "어떻게 확인"(outline 출력의 어느 열 / grep 패턴) 한 줄.
3. **코어 `SKILL.md`** ③ 줄을 `③ hwpx 양식화 → \`mdr-hwpx\`(원고 md → 발주처 양식 hwpx; 부별 모듈 빌드·정합성 검토·합본)` 로. 그 외 변경 금지. 수정 후 `PYTHONIOENCODING=utf-8 python codes/market-deep-research/tests/test_adversarial.py` 전건 PASS 확인.
4. **`install.py`**: `SKILLS = ("market-deep-research", "mdr-search", "mdr-hwpx")`. `demo()` 가 세 스킬 모두 `<tmp>/<name>/SKILL.md` 로 설치되는지 확인하도록 최소 수정(기존 단언 유지). `python codes/market-deep-research/scripts/install.py demo` PASS, `--dry-run` 출력(세 스킬 파일 수). **실제 설치 금지**(코디네이터가 한다).
5. **`README.md`**: 설치 절을 "세 스킬" 로, 목적별 표/문단이 있으면 `mdr-hwpx` 한 줄(③ 양식화: 원고 md → 양식 hwpx). 파이프라인 블록·영수증 표는 건드리지 말 것.

## 제약
- `git commit` 금지. `.fablize/goals.py` 실행 금지. 위 파일 외 수정 금지(특히 `codes/mdr-hwpx/scripts/*` 금지).
- 문장은 새로 지어내기보다 설계 문서·hwpx-form.md·mdr-search SKILL 의 문장을 재사용.
- 모르는 것은 `orca orchestration ask`.
