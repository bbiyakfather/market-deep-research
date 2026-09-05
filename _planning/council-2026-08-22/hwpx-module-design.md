# mdr-hwpx — 한글 양식화 목적 스킬 설계 (2026-08-22)

목적 ③ "hwpx 양식화만". 원고 마크다운(부별 모듈)을 발주처 「본보고서 양식.hwpx」 그대로인 HWPX 로 만들고,
모듈 간 정합성을 검토한 뒤 한 문서로 합쳐 공식 양식에 맞춘다.
참조 구현(실제로 한글 출력까지 확인된 것): `F:/Claude/work/navion-market-research/global pem projects/research_글로벌PEM수전해_2026_20260807/audit/build_hwpx.py` + `audit/form_spec.md`.
지식 노트: `codes/market-deep-research/references/hwpx-form.md` ([공통]=HWPX 규칙 / [양식별]=실측 ID·판형).

## 작업 흐름 (3단계)

```
① 모듈 빌드 (부별 병렬 — 워커 1명 = 원고 1부)
   manuscript/Ⅲ_x.md ──build_hwpx.py build──▶ 모듈_Ⅲ_x_양식.hwpx ──export_pdf.py──▶ .pdf ──grade_pdf.py──▶ grade.json + 의심쪽 png
   결함(그림 크롭·낱말 잘림·쪽 밀림)은 원고 md 수준에서 고치고 재빌드. 양식·코드는 건드리지 않는다.

② 정합성 검토 (코디네이터)
   build_hwpx.py outline manuscript/*.md  → 제목 트리·표/그림 캡션·각주 요약을 놓고 references/consistency-review.md 체크리스트로 본다.
   (부 번호·표/그림 번호 연속, 목차↔제목 일치, 같은 수치가 부마다 같은가, 용어 표기, 전년판 대비 문구)

③ 공식 양식 맞추기 (코디네이터)
   merge_hwpx.py 모듈_Ⅱ… 모듈_Ⅲ… … --out 본보고서_초안.hwpx → export_pdf.py → grade_pdf.py → 한글에서 눈으로 확인.
   표지·목차 생성·개별 그림 폭 미세조정은 한글에서 사람이 한다 (스킬이 만들지 않는다).
```

## 스킬 구조

```
codes/mdr-hwpx/
├── SKILL.md
├── scripts/
│   ├── build_hwpx.py      build | split | outline | --demo   (참조 구현 일반화: 템플릿 경로 + 프로필 JSON)
│   ├── form_probe.py      양식 hwpx 실측(판형·사용 중인 paraPr/charPr 조합) · --profile 로 ID 존재 검사
│   ├── merge_hwpx.py      모듈 hwpx N개 → 한 hwpx (같은 템플릿 전제, BinData 재번호, secPr 1회)
│   ├── export_pdf.py      한글 COM → PDF
│   └── grade_pdf.py       PyMuPDF 4지표 채점 + 의심쪽 PNG
├── profiles/navion-2026.json      양식별 ID 매핑·판형 (양식이 바뀌면 여기만 추가)
├── assets/forms/navion-2026.hwpx  내비온 본보고서 양식 사본 (데모·테스트용 템플릿)
├── references/hwpx-form.md        코어에서 이동
├── references/consistency-review.md
└── tests/test_hwpx.py             한글 없이 도는 구조 검사 + (한글 있으면) export/grade 스모크
```

## CLI 계약 (배치 간 공유 — H3 문서는 이 표기 그대로 쓴다)

```
python build_hwpx.py build <원고.md> --template <양식.hwpx> [--profile navion-2026|<path.json>] [--out <out.hwpx>]
    기본 out: <원고 폴더>/모듈_<원고stem>_양식.hwpx. stdout 마지막 줄 JSON {"ok","out","blocks":{종류:수},"images":n,"skipped_images":[...]}
python build_hwpx.py split <report.md> --out <dir>
    최상위 `# <로마숫자>. 제목` 단위로 <로마숫자>_<제목>.md 분할. --out 이 report.md 폴더의 하위면 이미지 상대경로 앞에 ../ 보정.
python build_hwpx.py outline <md> [<md> ...]
    모듈별 제목 트리(레벨·텍스트), <표>/[그림] 캡션 목록(순번 포함), 출처 수, 각주 정의 수, 단락 수. 사람이 읽는 표 + --json
python build_hwpx.py --demo
python form_probe.py <양식.hwpx> [--profile <json>] [--json]
    판형(secPr) + 본문에서 실제 쓰인 (paraPr,charPr) 조합을 header.xml 정의와 조인(글꼴·pt·굵기·정렬·좌여백·줄간격).
    --profile 이 있으면 프로필의 모든 ID 가 header.xml 에 존재하는지 검사, 없으면 exit 1.
python merge_hwpx.py <m1.hwpx> <m2.hwpx> ... --out <out.hwpx>
    header.xml 동일성 검사(다르면 에러: 같은 템플릿·같은 빌더로 만든 것만 합친다). 첫 모듈의 secPr 유지,
    이후 모듈 첫 문단 pageBreak="1". BinData/content.hpf 재번호. 함수 merge(paths, out)->{"ok","out","artifacts":[out],"modules":n,"images":n}
python export_pdf.py <in.hwpx> [<out.pdf>]
    Hwp.exe 미기동이면 `-Automation` 으로 기동 후 HWPFrame.HwpObject. RegisterModule("FilePathCheckDLL","FilePathCheckerModule"),
    Open(...,"HWPX","forceopen:true"), FileSaveAsPdf. 절대경로. 실패 시 exit 1 + 이유.
python grade_pdf.py <pdf> --md <원고.md> [--profile ...] [--out grade.json] [--render <dir>]
    지표: 그림 종횡비(내장 이미지 vs 원고 그림 파일, 오차 2%), 낱말 잘림(원고 표의 열폭을 build_hwpx.col_widths 로 재계산해
    최장 낱말×COL_UNIT > 열폭−IN_MARGIN 인 셀), 표 쪽걸침(캡션 없는 쪽의 긴 가로선 다수), 여백 낭비(쪽 하단 공백 > 3.5cm).
    의심쪽만 90dpi PNG. exit 0 이라도 결함 수는 JSON 에.
```

## 프로필 JSON (profiles/navion-2026.json) — form_spec.md 실측값

```json
{"name":"navion-2026","template_hint":"본보고서 양식.hwpx",
 "page":{"body_w":48188,"body_h":70012,"tbl_w":48178,"img_max_h":58000},
 "styles":{"title":[23,46],"h1":[24,47],"h2":[25,48],"h3":[26,49],"body1":[27,50],"body2":[29,51],
           "caption":[32,52],"th":[38,55],"td":[35,56],"tsrc":[37,57],"para_center":53,"body_bold_base":29},
 "border_fill":{"th":{"first":10,"mid":11,"last":12},"td":{"first":13,"mid":9,"last":15},"src":16,"tbl":9},
 "table":{"min_col":3300,"in_margin":1020,"col_unit":500,"label_max":12,"data_cap":30,"th_line":1300,"td_line":1600,"cell_vpad":282}}
```

## 만들지 않는 것
- 표지·목차 자동 생성, 그림 폭 개별 조정, 각주 개체(각주는 평문 마커 유지) — 한글에서 사람이.
- 코어 봉인(manifest.extend) 연동 — `merge()` 가 `artifacts` 를 돌려주는 계약만 지키고, 결박은 차후.
- kordoc 경로(`_hwpx용.md`·post_steps.json) — 폐기. 템플릿 방식만 남긴다.
