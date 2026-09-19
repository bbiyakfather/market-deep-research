# Batch H2 — `mdr-hwpx/scripts/merge_hwpx.py` + `export_pdf.py` + `grade_pdf.py`

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/purpose-modules`, 워크트리 공유 — 다른 워커가
`codes/mdr-hwpx/scripts/{build_hwpx,form_probe}.py`·`profiles/`·`assets/`·`SKILL.md`·`references/`·코어 파일을 동시에 만든다.
**그 파일은 건드리지 말 것.** `build_hwpx.py` 가 아직 없을 수 있다 — grade_pdf 의 import 는 지연 import 로 두고, 없으면 낱말 잘림 지표만 건너뛰게.)

## 먼저 읽을 것
1. `_planning/council-2026-08-22/hwpx-module-design.md` — CLI 계약(merge/export/grade). **표기 그대로 구현.**
2. `codes/market-deep-research/references/hwpx-form.md` — 「검증 — 정적 검사는 검증이 아니다」절(COM→PDF 코드, 4지표 표), 「그림」절(imgClip), 「쪽 경계」절.
3. 참조 구현 `F:/Claude/work/navion-market-research/global pem projects/research_글로벌PEM수전해_2026_20260807/audit/build_hwpx.py` 의 `build()` 끝부분 — 산출 hwpx 의 zip 구성(mimetype STORED 첫 항목, Contents/header.xml·section0.xml·content.hpf, BinData/imageN.EXT, content.hpf 의 `<opf:item id="imageN" href=… hashkey=…>`).
4. 실물: 같은 폴더 `manuscript/모듈_Ⅱ_데이터분석_양식.hwpx`, `모듈_Ⅲ_지역별정책동향_양식.hwpx`, `모듈_Ⅴ_결론_양식.hwpx` (모두 같은 템플릿으로 만든 것 — merge 테스트 입력), `manuscript/Ⅴ_결론.md`(grade 의 --md 입력).

## 손대는 파일 (새로 만든다)
- `codes/mdr-hwpx/scripts/merge_hwpx.py`
- `codes/mdr-hwpx/scripts/export_pdf.py`
- `codes/mdr-hwpx/scripts/grade_pdf.py`

## 할 일
1. **merge_hwpx.py** `merge(paths, out) -> dict`
   - 입력 hwpx 들의 `Contents/header.xml` 바이트가 모두 같아야 한다(다르면 `ValueError("header.xml 이 다름: …")`). 같은 템플릿+같은 빌더 산출물만 합친다는 뜻.
   - section0.xml: 첫 모듈의 `<?xml…><hs:sec …>` 머리 + 첫 모듈 본문(secPr 포함) + 이후 모듈의 `<hp:p …>` 들(각 모듈 **첫 문단의 `pageBreak="0"` → `"1"`**; 이후 모듈의 secPr/colPr run 은 제거) + `</hs:sec>`.
   - BinData 재번호: 모듈 k 의 `imageN.EXT` → 전역 순번 `imageM.EXT`. `binaryItemIDRef="imageN"` 과 content.hpf `<opf:item id="imageN" href="BinData/imageN.EXT" …>` 를 같이 고친다(한 모듈 안에서 치환할 때 이미 바뀐 번호를 다시 치환하지 않도록 **임시 토큰 경유**). hashkey 는 그대로.
   - 나머지 항목(mimetype·version.xml·settings.xml·META-INF/*·Preview/*)은 첫 모듈 것. mimetype 은 STORED 로 첫 항목.
   - 반환 `{"ok":True,"out":str,"artifacts":[str],"modules":n,"images":n}`; CLI 는 stdout 마지막 줄에 JSON. `--demo`: 작은 hwpx 두 개를 메모리에서 만들어(zip 으로 직접 조립 — 템플릿 없이, 최소 header/section/hpf) 합친 뒤 단락 수·pageBreak 1개·image 재번호·header 불일치 시 에러를 assert.
2. **export_pdf.py** — hwpx-form.md 의 COM 절 그대로. `HWPFrame.HwpObject` Dispatch 실패(`서버 실행에 실패`) 시 `C:/Program Files (x86)/Hnc/Office 2024/HOffice130/Bin/Hwp.exe -Automation` 을 `subprocess.Popen` 으로 띄우고 최대 20초 재시도. `RegisterModule("FilePathCheckDLL","FilePathCheckerModule")`. 절대경로 변환. 산출 PDF 존재·크기>0 확인. 끝에 `Quit()` (예외 시에도). 함수 `export(src, out) -> dict {"ok","pdf","size"}`. 한글 미설치 환경이면 exit 2 + 메시지("한글 없음").
3. **grade_pdf.py** `grade(pdf, md=None, profile="navion-2026") -> dict` — PyMuPDF(`fitz`).
   - 그림 종횡비: `page.get_images()` 순서대로 내장 이미지 (w,h) 를 뽑고, `--md` 의 `![…](path)` 를 문서 순서대로 PIL 로 열어 원본 종횡비와 비교, 오차 2% 초과 → 결함 (원고 그림 수와 PDF 그림 수가 다르면 그 사실도 보고). 양식 템플릿이 싣고 온 예시 이미지는 build 가 버리므로 없음.
   - 낱말 잘림: `--md` 의 표마다 `build_hwpx.col_widths(rows, ncol)` 로 열폭 재계산, 열별 `max(_disp_len(낱말))×COL_UNIT > 열폭−IN_MARGIN` 인 셀 목록. (`build_hwpx` import 는 `sys.path.insert(0, 스크립트 폴더)` 후 try — 없으면 `"skipped"`.) 프로필 상수는 `build_hwpx.load_profile` 에서.
   - 표 쪽걸침: 쪽마다 `page.get_drawings()` 의 긴 가로선(폭 ≥ 본문폭 80%) 수를 세고, 그 쪽 텍스트에 `<표>` 캡션이 없는데 가로선 ≥ 3 이면 "표가 앞 쪽에서 넘어옴" 후보.
   - 여백 낭비: 쪽별 `본문 하단 y − 마지막 텍스트/그림 블록 bottom` 이 3.5cm(≈99pt) 초과인 쪽 목록(마지막 쪽 제외).
   - `--render <dir>`: 결함 의심쪽만 `page.get_pixmap(dpi=90)` PNG. `--out grade.json`. stdout 마지막 줄 JSON 요약 `{"pages","images","defects":{"aspect":n,"word_cut":n,"table_spill":n,"gap":n},"suspect_pages":[…]}`.
   - `--demo`: PyMuPDF 로 2쪽짜리 PDF 를 메모리에서 만들어(텍스트+사각형 선) gap/spill 판정이 도는지 assert.
4. **실행 증거** (`PYTHONIOENCODING=utf-8`, 산출물은 스크래치패드 `C:/Users/eicic.AIDEN-DESKTOP/AppData/Local/Temp/claude/F--Claude-skills-market-deep-research/6c15f635-5db3-4504-b6cb-bcefad7d36b8/scratchpad/h2/`):
   - 세 스크립트 `--demo` 전부 "demo ok".
   - `merge_hwpx.py` 로 실물 모듈 Ⅱ·Ⅲ·Ⅴ 세 개를 합쳐 `merged.hwpx` 생성 → `export_pdf.py merged.hwpx` 로 PDF → 쪽수·크기 보고. (한글이 뜨는 PC 다. 보안 대화상자로 멈추면 RegisterModule 누락이다.)
   - `grade_pdf.py <PEM폴더>/manuscript/모듈_Ⅴ_결론_양식.pdf --md <PEM폴더>/manuscript/Ⅴ_결론.md --render …/h2/render` 의 JSON 요약과 렌더된 PNG 파일명.
   - `grade_pdf.py merged.pdf`(md 없이) 요약.
   worker_done 본문에 위 출력과 마지막 줄.

## 제약
- `git commit` 금지. `.fablize/goals.py` 실행 금지. 위 3개 파일 외 수정 금지. PEM 작업폴더는 **읽기만**.
- 의존성: `fitz`(PyMuPDF)·`PIL`·`win32com`(이미 설치됨). 새 패키지 추가 금지.
- 변수·함수명 영어, 주석·docstring 한국어. `sys.stdout.reconfigure(encoding="utf-8")`.
- 모르는 것은 `orca orchestration ask`.
