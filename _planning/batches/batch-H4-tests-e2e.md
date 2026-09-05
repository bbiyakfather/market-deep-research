# Batch H4 — `mdr-hwpx/tests/test_hwpx.py` (H1·H2 완료 후 투입)

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/purpose-modules`). H1(`build_hwpx.py`·`form_probe.py`·프로필·양식 사본)과
H2(`merge_hwpx.py`·`export_pdf.py`·`grade_pdf.py`)가 끝난 상태다. **스크립트를 고치지 말고 테스트만 쓴다** — 결함을 찾으면 고치지 말고
`orca orchestration escalate` 로 코디네이터에게 올린다(어느 파일 몇 행, 재현 명령, 기대/실제).

## 먼저 읽을 것
1. `_planning/council-2026-08-22/hwpx-module-design.md` (CLI 계약·프로필).
2. `codes/mdr-hwpx/scripts/*.py` 전부 + `profiles/navion-2026.json` + `codes/mdr-hwpx/SKILL.md`.
3. `codes/market-deep-research/tests/test_adversarial.py` 앞 80행 — 테스트 작성 관례(표준 라이브러리 `unittest`/assert 기반, 외부 프레임워크 없음, `_CLI_ENV` 로 `PYTHONIOENCODING=utf-8` 지정, `subprocess` 로 CLI 실행).

## 손대는 파일 (새로)
- `codes/mdr-hwpx/tests/test_hwpx.py`

## 할 일 — 한글 없이 도는 부분이 본체, 한글·COM 은 있을 때만 스모크
1. **빌드 구조 검사** (템플릿 `assets/forms/navion-2026.hwpx`, 프로필 `navion-2026`, 임시 원고를 tmp 에 생성 — 제목 4단계·①제목/①본문·❍/- 본문·굵게·각주 마커·각주 정의·`<표>`+표+출처·작은 그림(PIL 로 200×100 PNG 생성)+`[그림]` 캡션·60행 큰 표):
   - zip 첫 항목이 `mimetype` STORED; `Contents/header.xml`·`section0.xml`·`content.hpf` 존재; `BinData/image1.PNG` 1개; content.hpf 에 `id="image1"` 항목 1개·hashkey 있음; 템플릿 예시 이미지 항목 없음.
   - section0.xml: 첫 문단 첫 run 안에 `<hp:secPr`; 프로필 ID 사용(title 23/46, body1 27/50, 캡션 32/52, 표 머리 38/55…); 본문 굵게 run 의 charPr 이 header 의 새 ID 이고 `<hh:bold/>` 를 가짐; itemCnt 가 +1.
   - 작은 표 `treatAsChar="1"`, 큰 표 `treatAsChar="0"`, 둘 다 `pageBreak="CELL"` `repeatHeader="1"`; 출처행 `colSpan=열수`·borderFill 16; 캡션 `side="TOP"`(표)·`side="BOTTOM"`(그림).
   - 그림: `imgClip right = px_w*75`, `orgSz` 원본 좌표, `curSz` 폭 = body_w(200×100 은 가로가 길어 폭 기준).
   - 원고의 `❍ `·`- ` 접두 기호가 `<hp:t>` 에 남아 있지 않음(이중 불릿 방지). `&` 이스케이프.
   - 없는 그림 경로 → 건너뛰고 JSON `skipped_images` 에 기록, exit 0.
2. **split / outline**: tmp 에 `report.md`(서문 + `# Ⅱ. 가` + `# Ⅲ. 나`, 그림 `assets/x.png` 참조) → `split --out tmp/manuscript` 가 `00_서문.md`·`Ⅱ_가.md`·`Ⅲ_나.md` 를 만들고 이미지 경로가 `../assets/x.png` 로 보정됨. `outline --json` 이 모듈별 제목 수·표/그림 캡션 목록을 돌려줌.
3. **form_probe**: 양식 사본에 `--profile profiles/navion-2026.json` → exit 0; 프로필 사본에서 존재하지 않는 ID(예: charPr 9999)를 넣으면 exit 1 + 그 ID 가 출력에.
4. **merge**: 1번 원고로 모듈 2개(그림 1개씩) 빌드 → merge → header 동일; 문단 수 = 합; 두 번째 모듈 첫 문단 `pageBreak="1"`; secPr 1개; `BinData/image1.PNG`·`image2.PNG`; content.hpf 항목 2개·id 중복 없음; 한 모듈의 header.xml 을 1바이트 바꾼 사본을 섞으면 `ValueError`.
5. **export/grade 스모크** (`HWPFrame.HwpObject` Dispatch 가 되고 Hwp.exe 경로가 있을 때만 — 아니면 `skipTest`): 4번 merged.hwpx → `export_pdf.py` → PDF 존재·쪽수 ≥ 2 → `grade_pdf.py --md <1번 원고>` 의 JSON 에 `defects` 키 4개·`images` ≥ 1. **한글 창을 띄웠으면 Quit 까지 확인**(프로세스 잔존 금지).
6. **실행 증거**: `PYTHONIOENCODING=utf-8 python codes/mdr-hwpx/tests/test_hwpx.py` 전건 PASS(스킵 수 포함 마지막 줄). 발견한 결함은 escalate 본문에 전부.

## 제약
- `git commit` 금지. `.fablize/goals.py` 실행 금지. `tests/test_hwpx.py` 외 수정 금지.
- 임시 파일은 `tempfile.TemporaryDirectory()` 안에만. PEM 작업폴더는 쓰지 않는다(읽기도 불필요).
- 모르는 것은 `orca orchestration ask`.
