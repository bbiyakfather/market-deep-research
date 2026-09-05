---
name: mdr-hwpx
description: >-
  원고 md를 발주처 한글 양식(hwpx)으로 변환한다. 부별 모듈 병렬 빌드·정합성 검토·공식 양식 합본.
  발주처가 준 양식 파일 그대로. 사용 시점 — "한글로 만들어줘", "hwpx로", "양식에 맞춰",
  "발주처 양식", "보고서 양식화" 류 요청이면 이 스킬. 제외 — 조사·검색·보고서 초안이
  필요하면 market-deep-research / mdr-search.
---

# mdr-hwpx — 한글 양식화 (원고 md → 발주처 양식 hwpx)

원고 마크다운(부별 모듈)을 발주처 「본보고서 양식.hwpx」 그대로인 HWPX 로 만들고,
모듈 간 정합성을 검토한 뒤 한 문서로 합쳐 공식 양식에 맞춘다.
사실대장·재검증·게이트·검색은 하지 않는다. 그건 `market-deep-research` / `mdr-search`.

## 전제

코어(`market-deep-research`) 설치와 무관하게 **단독 실행 가능**. 스크립트는 `<this>/scripts`.
개발본 `<this>`: `codes/mdr-hwpx` · 설치본: `~/.claude/skills/mdr-hwpx`.
Windows. 한글(`Hwp.exe`)·PyMuPDF·PIL·pywin32. cwd = 작업폴더(원고 `manuscript/`, 그림 `assets/`).
스크립트는 `<this>/scripts/x.py` 절대경로. 인코딩 `PYTHONIOENCODING=utf-8`.
템플릿은 사용자가 주는 `양식.hwpx`. 내비온 양식 동봉: `assets/forms/navion-2026.hwpx` + `profiles/navion-2026.json`.

## 워크플로 (3단계)

### ① 모듈 빌드 (부별 병렬 — 워커 1명 = 원고 1부)

```
manuscript/Ⅲ_x.md ──build_hwpx.py build──▶ 모듈_Ⅲ_x_양식.hwpx ──export_pdf.py──▶ .pdf ──grade_pdf.py──▶ grade.json + 의심쪽 png
```

결함(그림 크롭·낱말 잘림·쪽 밀림)은 **원고 md 수준에서만** 고치고 재빌드. 양식·코드는 건드리지 않는다.
워커는 build→export→grade 후 worker_done 에 grade 요약을 담는다.

```
python <this>/scripts/build_hwpx.py build <원고.md> --template <양식.hwpx> [--profile navion-2026|<path.json>] [--out <out.hwpx>]
    기본 out: <원고 폴더>/모듈_<원고stem>_양식.hwpx. stdout 마지막 줄 JSON {"ok","out","blocks":{종류:수},"images":n,"skipped_images":[...]}
python <this>/scripts/build_hwpx.py split <report.md> --out <dir> [--expect-parts N]
    `#` 또는 `## <로마숫자>. 제목` 단위 분할. 헤딩 0개 또는 기대 부 수 불일치는 exit 1(서문 제외). --out 이 report.md 폴더의 하위면 이미지 상대경로 앞에 ../ 보정.
python <this>/scripts/export_pdf.py <in.hwpx> [<out.pdf>]
    Hwp.exe 미기동이면 `-Automation` 으로 기동 후 HWPFrame.HwpObject. RegisterModule("FilePathCheckDLL","FilePathCheckerModule"),
    Open(...,"HWPX","forceopen:true"), FileSaveAsPdf. 절대경로. 실패 시 exit 1 + 이유.
python <this>/scripts/grade_pdf.py <pdf> --md <원고.md> [--profile ...] [--out grade.json] [--render <dir>]
    지표: 그림 종횡비(내장 이미지 vs 원고 그림 파일, 오차 2%), 낱말 잘림(원고 표의 열폭을 build_hwpx.col_widths 로 재계산해
    최장 낱말×COL_UNIT > 열폭−IN_MARGIN 인 셀), 표 쪽걸침(캡션 없는 쪽의 긴 가로선 다수), 여백 낭비(쪽 하단 공백 > 3.5cm).
    의심쪽만 90dpi PNG. exit 0 이라도 결함 수는 JSON 에.
python <this>/scripts/build_hwpx.py --demo
```

코어 인계: 승인된 `report.md`의 HWPX용 사본에서 부 헤딩을 `# Ⅰ. Executive Summary` 형식으로 수동 매핑하고 하위 축은 그 아래 유지한다(원문·F-ID·부록 마커 보존).
Ⅰ Executive Summary · Ⅱ 조사 개요 · Ⅲ 테마별 본론 · Ⅳ 시장 수치 종합 · Ⅴ 플레이어·경쟁 구도 · Ⅵ 검증 요약 · Ⅶ 상충·모순 · Ⅷ 상태 변화·주의 · Ⅸ 한계와 반론 · Ⅹ 한눈 요약표 + 조사팀 인사이트 · Ⅺ 부록. 부 0 표지·메타는 서문으로 둔다.
split 전 `python <this>/scripts/build_hwpx.py outline <HWPX용.md>`로 승인 목차의 순서·11부를 확인하고 해당 없음도 승인된 부 헤딩 아래 명시한다.
`python <this>/scripts/build_hwpx.py split <HWPX용.md> --out manuscript --expect-parts 11`로 확인된 사본을 분할한다. 헤딩 변환은 사람·빌더의 원고 계약이며 자동 변환하지 않는다.

### ② 정합성 검토 (코디네이터)

```
python <this>/scripts/build_hwpx.py outline <md> [<md> ...]
    모듈별 제목 트리(레벨·텍스트), <표>/[그림] 캡션 목록(순번 포함), 출처 수, 각주 정의 수, 단락 수. 사람이 읽는 표 + --json
```

출력과 `references/consistency-review.md` 체크리스트로 본다
(부 번호·표/그림 번호 연속, 목차↔제목 일치, 같은 수치가 부마다 같은가, 용어 표기, 전년판 대비 문구).

### ③ 공식 양식 맞추기 (코디네이터)

```
python <this>/scripts/merge_hwpx.py <m1.hwpx> <m2.hwpx> ... --out <out.hwpx>
    header.xml 동일성 검사(다르면 에러: 같은 템플릿·같은 빌더로 만든 것만 합친다). 첫 모듈의 secPr 유지,
    이후 모듈 첫 문단 pageBreak="1". BinData/content.hpf 재번호. 함수 merge(paths, out)->{"ok","out","artifacts":[out],"modules":n,"images":n}
```

`merge` → `export_pdf.py` → `grade_pdf.py` → 한글에서 눈으로 확인.
표지·목차 생성·개별 그림 폭 미세조정은 한글에서 사람이 한다 (스킬이 만들지 않는다).

## 원고 마크다운 문법

빌더는 아래만 해석한다. 더 늘리지 않는다. 불릿 접두 기호(`❍` · `-`)는 양식이 그리므로 원고에 남겨도 빌더가 뗀다.

| 표기 | 역할 |
|---|---|
| `# ## ### ####` | 제목 4단계 |
| `① ` | 짧으면 3단계 제목, 설명이 길면 본문 |
| `❍ ` / 평문 | 본문 1단 |
| `- ` | 본문 2단 |
| `<표>` | 바로 뒤 표의 캡션 (표보다 먼저 나온다) |
| `\| a \| b \|` | 표 |
| `* 출처 :` | 직전 표의 출처행 / 직전 그림의 출처 문단 |
| `![]()` | 그림 |
| `[그림]` | 직전 그림의 캡션 |
| `**굵게**` | 굵은 run — 양식에 12pt 굵게가 없으면 본문 charPr 을 복제해 `<hh:bold/>` 만 넣어 추가 |
| `<sup>` | 각주 마커(평문 유지). 문서 끝 각주 정의 문단은 본문 불릿을 붙이면 안 된다 |

## 새 양식을 만났을 때

코드는 고치지 않는다. 양식 파일을 갈아끼우고 프로필 ID 만 맞춘다.

```
python <this>/scripts/form_probe.py <양식.hwpx> [--profile <json>] [--json]
    판형(secPr) + 본문에서 실제 쓰인 (paraPr,charPr) 조합을 header.xml 정의와 조인(글꼴·pt·굵기·정렬·좌여백·줄간격).
    --profile 이 있으면 프로필의 모든 ID 가 header.xml 에 존재하는지 검사, 없으면 exit 1.
```

`form_probe.py 양식.hwpx` 실측 → `profiles/<이름>.json` 작성 → `form_probe.py --profile` 로 ID 존재 검사 → `build`.

## 통과 기준

- `grade_pdf.py` 4지표 결함 0 (또는 사유 기록).
- 한글에서 열어 **의심쪽 PNG 를 사람이 본다**. XML 이 스키마에 맞아도 크롭·세로쏟아짐·쪽 밀림은 전부 통과한다 — **정적 검사는 검증이 아니다.**

## 만들지 않는 것

- 표지·목차 자동 생성, 그림 폭 개별 조정, 각주 개체(각주는 평문 마커 유지) — 한글에서 사람이.
- 코어 봉인(manifest.extend) 연동 — `merge()` 가 `artifacts` 를 돌려주는 계약만 지키고, 결박은 차후.
- kordoc 경로(`_hwpx용.md`·post_steps.json) — 폐기. 템플릿 방식만 남긴다.

## 참조 문서 (필요할 때만 로드)

| 파일 | 언제 |
|---|---|
| `references/hwpx-form.md` | 새 양식 실측·그림/표 깨질 때 |
| `references/consistency-review.md` | ② 단계 |
