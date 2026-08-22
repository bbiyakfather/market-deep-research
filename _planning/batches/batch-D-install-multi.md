# Batch D — `install.py` 다중 스킬 설치(명시 allowlist) + README 설치 절

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/purpose-modules`, 워크트리 공유 — 다른 워커가 `codes/market-deep-research/SKILL.md`·`references/*`·`codes/mdr-search/SKILL.md` 를 동시에 고치는 중이니 그 파일은 건드리지 말 것)

## 배경
`codes/` 아래에 이제 스킬이 둘이다: `market-deep-research/`(코어) + `mdr-search/`(목적① 얇은 스킬, SKILL.md 만). 현 `codes/market-deep-research/scripts/install.py` 는 `SKILL_ROOT` 한 트리만 `~/.claude/skills/market-deep-research/` 로 해시검증 복사하고 `--check` 로 드리프트를 본다(`INCLUDE`, stale 정리, 자기복사 가드, 줄바꿈 정규화 해시 등 — 먼저 읽을 것). Codex 리뷰 M6: 다중 스킬 설치는 **명시 allowlist·stale 정리·`--target` 의미 정의**가 필요하다(`SKILL_ROOT.parent/*` 를 무작정 스캔하면 설치본에서 실행할 때 사용자의 모든 스킬이 후보가 된다).

## 손대는 파일
`codes/market-deep-research/scripts/install.py` · 저장소 루트 `README.md` 의 설치/실행 절만

## 할 일
1. `install.py` 에 **`SKILLS = ("market-deep-research", "mdr-search")`** allowlist 를 둔다. 소스 루트는 `SKILL_ROOT.parent`(개발본 `codes/`) 아래 각 이름의 폴더; 이름 폴더에 `SKILL.md` 가 없으면 명시적 에러(조용히 건너뛰지 말 것). 설치 대상은 `<skills_parent>/<name>/` — `--target` 의 의미를 **스킬 부모 디렉터리**(기본 `~/.claude/skills`)로 바꾸고 docstring·`--help` 에 명시(단일 스킬 경로를 넘기던 구 의미는 폐기; 구 호출과 구분되도록 `--target` 경로 안에 `SKILL.md` 가 바로 있으면 "부모 디렉터리를 넘기라"는 에러).
2. `install()`·`check()` 를 스킬별로 돌려 결과를 `{"ok", "skills": {name: {...기존 필드...}}}` 로 합친다. 기존 per-skill 로직(INCLUDE 필터·해시검증·stale 정리·줄바꿈 정규화 `--check`)은 그대로 재사용. `mdr-search` 처럼 `scripts/`·`references/`·`assets/` 가 없는 스킬도 SKILL.md 만으로 정상 설치돼야 한다.
3. **stale 스킬 폴더는 건드리지 않는다**(allowlist 밖 `~/.claude/skills/*` 는 사용자 것). 다만 `--check` 결과에 "allowlist 에 있으나 설치본 없음" 을 `missing_skills` 로 보고.
4. 자기복사 가드 유지(소스 루트 == 타깃 또는 하위). `--dry-run` 유지.
5. `demo()` 갱신: 임시 디렉터리를 부모로 두고 두 스킬이 각각 `<tmp>/<name>/SKILL.md` 로 설치되는지, `mdr-search` 가 SKILL.md 1개로 설치되는지, stale 정리·변조 검출(`--check`)·자기복사 가드가 여전히 동작하는지 assert. 기존 단언은 가능한 유지.
6. `README.md` 의 설치/실행 안내 절(있으면 — `install.py` 언급 부분)에 "두 스킬이 함께 설치됨, `--target` 은 부모 디렉터리" 를 2~3줄로 갱신. 파이프라인 블록·영수증 표는 건드리지 말 것(다른 배치 소유).
7. **실행 증거**: `PYTHONIOENCODING=utf-8 python codes/market-deep-research/scripts/install.py demo` PASS, `python install.py --dry-run` 출력(두 스킬 파일 수), `python install.py --check`(설치본 드리프트 — 지금 설치본은 구버전이라 differs 가 나오는 게 정상; 그 출력 요약을 보고). **실제 설치(`python install.py`)는 하지 말 것** — 다른 배치가 SKILL.md 를 편집 중이라 최종 배치(E)에서 코디네이터가 수행한다.

## 제약
- `git commit` 금지. `.fablize/goals.py` 실행 금지. `install.py`·README 설치 절 외 수정 금지.
- Windows: `PYTHONIOENCODING=utf-8`. 경로는 `pathlib`.
- 모르는 것은 `orca orchestration ask`.
