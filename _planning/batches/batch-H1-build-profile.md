# Batch H1 — `mdr-hwpx/scripts/build_hwpx.py` + `form_probe.py` + 프로필 + 양식 사본

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/purpose-modules`, 워크트리 공유 — 다른 워커가
`codes/mdr-hwpx/scripts/{merge_hwpx,export_pdf,grade_pdf}.py`·`codes/mdr-hwpx/SKILL.md`·`references/`·코어 파일을 동시에 고친다.
**그 파일은 건드리지 말 것.**)

## 먼저 읽을 것 (순서대로)
1. `_planning/council-2026-08-22/hwpx-module-design.md` — 전체 설계·CLI 계약·프로필 JSON. **계약 표기 그대로 구현한다.**
2. `codes/market-deep-research/references/hwpx-form.md` — HWPX 규칙([공통]) 과 양식 실측([양식별]). 특히 imgClip 좌표계·열폭 배분·treatAsChar.
3. 참조 구현 `F:/Claude/work/navion-market-research/global pem projects/research_글로벌PEM수전해_2026_20260807/audit/build_hwpx.py` (537줄, `--demo` 있음) 와 같은 폴더 `form_spec.md`.
4. 실물 샘플: 같은 폴더 `manuscript/Ⅴ_결론.md`(원고), `manuscript/본보고서 양식.hwpx`(템플릿), `manuscript/모듈_Ⅴ_결론_양식.hwpx`(참조 구현이 만든 결과).

## 손대는 파일 (새로 만든다)
- `codes/mdr-hwpx/scripts/build_hwpx.py`
- `codes/mdr-hwpx/scripts/form_probe.py`
- `codes/mdr-hwpx/profiles/navion-2026.json`
- `codes/mdr-hwpx/assets/forms/navion-2026.hwpx` ← `manuscript/본보고서 양식.hwpx` 를 **그대로 복사**(수정 금지)

## 할 일
1. **build_hwpx.py** — 참조 구현을 옮겨 오되 세 가지를 바꾼다.
   - 하드코딩 상수(TITLE~CELL_VPAD, BF_*, PAGE_*, TBL_W, IMG_MAX_H, TEMPLATE) → `--profile` JSON 로드(이름이면 `<스크립트 폴더>/../profiles/<이름>.json`, 경로면 그 파일; 기본 `navion-2026`) + `--template` 필수 인자. 프로필 키 이름은 설계 문서의 JSON 그대로.
   - 서브커맨드 `build` / `split` / `outline` / `--demo` (설계 문서 CLI 계약). `build` 의 stdout 마지막 줄은 JSON 한 줄.
   - 본문 굵게 charPr 은 프로필 `styles.body_bold_base`(29) 를 복제해 `<hh:bold/>` 를 넣은 새 ID(기존 itemCnt 다음 번호 — 참조 구현처럼 200 고정이 아니라 **header 의 itemCnt 를 읽어 그 값**으로; 충돌 방지) 로 만든다.
   - 파싱 규칙(`parse_md`)·열폭(`col_widths`)·높이 어림(`est_height`)·표/그림 XML·조립(`build`) 로직은 **그대로 유지**(검증된 것이니 새로 짜지 말 것). 함수 이름 유지 — grade_pdf.py(다른 워커)가 `from build_hwpx import col_widths, _disp_len, parse_md, load_profile` 로 가져다 쓴다. `load_profile(name_or_path) -> dict` 를 반드시 노출.
   - `split`: `^# ([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)\.\s*(.+)$` 최상위 제목 단위로 자른다. 출력 파일명 `<로마숫자>_<제목에서 공백·/·: 제거>.md`. `--out` 이 report.md 폴더의 하위 디렉터리면 `](assets/` `](_captures/` 같은 상대경로 앞에 `../` 를 붙인다(정확히는 `](` 뒤가 `http`·`/`·`..` 로 시작하지 않는 상대경로 전부). 첫 제목 앞의 서문은 버리지 말고 `00_서문.md` 로.
   - `outline`: 모듈별로 제목(레벨·텍스트) 트리, `<표>` 캡션 순번 목록, `[그림]` 캡션 순번 목록, `* 출처` 수, 각주 정의(`<sup>n)</sup>` 행) 수, 단락 수를 사람이 읽는 표로; `--json` 이면 JSON.
2. **form_probe.py** — hwpx-form.md "실측 방법 [공통]" 코드 그대로: `<hp:tbl>` 제거 후 본문 (paraPr,charPr) 조합 Counter → header.xml 의 `<hh:paraPr>`/`<hh:charPr>` 정의와 조인해 글꼴명·크기(pt=height/100)·굵기·정렬·좌여백(`<hc:left value>`)·줄간격 표 출력. 판형은 secPr 의 pagePr/margin 에서 읽어 본문 폭·높이 환산까지. `--profile` 주면 프로필이 가리키는 모든 charPr/paraPr/borderFill ID 가 header.xml 에 존재하는지 검사, 없으면 목록 출력 후 exit 1. `--json`.
3. **navion-2026.json** — 설계 문서 JSON 그대로. 그리고 `form_probe.py assets/forms/navion-2026.hwpx --profile profiles/navion-2026.json` 이 exit 0 인지 확인(실측으로 ID 존재 검증).
4. **데모/증거** (`PYTHONIOENCODING=utf-8`):
   - `python codes/mdr-hwpx/scripts/build_hwpx.py --demo` → 참조 구현의 demo 단언 전부 유지 + 프로필 로드 단언 추가. "demo ok".
   - 실물: `python codes/mdr-hwpx/scripts/build_hwpx.py build "<PEM폴더>/manuscript/Ⅴ_결론.md" --template codes/mdr-hwpx/assets/forms/navion-2026.hwpx --out <스크래치패드>/V.hwpx` 가 성공하고, 만들어진 `Contents/section0.xml` 을 참조 구현 산출물 `manuscript/모듈_Ⅴ_결론_양식.hwpx` 의 것과 비교해 **charPr/paraPr ID 사용 분포가 같은지**(Counter 비교; 굵게 ID 번호만 다를 수 있음) 보고. BinData 수·content.hpf 항목 수 일치.
   - `split`: `<PEM폴더>/report.md` 를 스크래치패드에 분할해 파일 목록·각 파일 첫 줄 보고. 이미지 경로 보정 확인 1건.
   - `outline`: `<PEM폴더>/manuscript/Ⅱ_데이터분석.md Ⅴ_결론.md` 출력 앞 30줄.
   - `form_probe.py` 출력(판형 표 + 조합 표) 앞 30줄.
   worker_done 본문에 위 출력 요약과 마지막 줄.

## 제약
- `git commit` 금지. `.fablize/goals.py` 실행 금지. 위 "손대는 파일" 외 수정 금지(PEM 작업폴더는 **읽기만** — 원본 hwpx/md 를 쓰거나 덮지 말 것; 산출물은 스크래치패드 `C:/Users/eicic.AIDEN-DESKTOP/AppData/Local/Temp/claude/F--Claude-skills-market-deep-research/6c15f635-5db3-4504-b6cb-bcefad7d36b8/scratchpad/h1/`).
- Windows: `PYTHONIOENCODING=utf-8`, 경로는 `pathlib`. 외부 의존성은 PIL 만(참조 구현과 동일).
- 변수·함수명 영어. 주석·docstring 한국어.
- 모르는 것은 `orca orchestration ask`.
