# Batch T2 — 표 형식 다양화 (사용자 편집 학습: matrix / A / B)

작업 루트: `D:/skills/market-deep-research/` (브랜치 `refactor/context-budget` 위, 2026-10-08). 계기: 실전 보고서 v20 에서 사용자가
빌더 출력의 가로 행렬 표(나라 × 속성 4~5열, 문장형 칸)를 손으로 **대상별 묶음 세로 표(A)** 와 **두 열 라벨형(B)** 으로 고침.
그 형식을 스킬 규칙과 빌더에 옮긴다. 사양·전후 이미지는 고객 작업폴더 `audit/table_format_v20/`(대외비 — 이 저장소에는 형식·비율·규칙만).

## 분담 (두 세션)
| 쪽 | 담당 | 파일 |
|---|---|---|
| 빌더(mdr-hwpx) | `claude-sync-f8` 세션 (C:/claude-sync 설치본에서 작업 중, 미커밋) | `build_hwpx.py`(FMT_RE `{형식=(A\|B\|matrix)}`, `pick_table_format`: 열≥4·칸 최대 25자↑ → A, 아니면 matrix, B 는 수동), mdr-hwpx `SKILL.md` 「표 형식」, `deliverable-rules.md` §4 공통 서식, 프로필 `table.group_ratio` |
| 스킬(market-deep-research) | 이 세션 | 아래 |

f8 에 보낸 세션 간 메시지(분담 제안 + D:/skills 쪽 미커밋 충돌 경고)는 **권한 모드 차이로 전달되지 않고 만료**됐다. 같은 내용을
고객 작업폴더 `audit/table_format_v20/조율_메모_to_f8.md` 에 남겼고, 사용자가 f8 세션에 읽히면 된다. f8 이 설치본 변경을 D:/skills 로
되가져올 때 T1 위에 얹어야 한다.

## 이 세션이 한 것
- `references/visual-first.md` §2b 신설: 형식 선택표(칸 글 15자/25자·행 대상이 비교 대상이냐 개념이냐), 캡션 태그 규칙(B 는
  반드시 `{형식=B}`), 원고는 가로 행렬 그대로(1열=대상/구분, 머리행=속성명), `, ` 분리·괄호 안 쉼표 보존, 작성자 몫 공통 서식,
  일반화한 예 1개.
- `references/agent-briefs.md` 작성자 고정 문구에 형식 선택 한 줄.
- `SKILL.md` [3] 카드에 "표로 남기면 형식 matrix/A/B 와 캡션 태그 §2b".
- `scripts/visual_audit.py`: `TABLE_FMT_TAG`·`strip_table_format_tags()` 추가, 표 키 계산에서 태그 제거(태그를 붙여도
  `visual-decisions.json` 의 keep 결정이 유지), selftest 에 태그 케이스.
- `scripts/render_pdf.py`: 증빙판 PDF 로 가기 전 캡션 태그 제거(pandoc 에 stdin 으로 전달). 스모크: 태그 캡션이 HTML 에서 사라지고
  칸 가운데의 `{형식=A}` 문자열은 남는다(줄 끝만 지움).

## 검증
- `python scripts/visual_audit.py --selftest` OK · pandoc 스모크 OK · 대외비 단어(회사·제품·바이오마커) grep 0건.
- 전체 테스트: 609 passed(T1 과 동일, SKILL.md 예산 가드 포함). `git diff --stat`: visual-first +27, agent-briefs 5, SKILL.md 1, visual_audit +10/−2, render_pdf +5/−2.
- 독립 리뷰(opus, 읽기 전용): **수정 후 통과**. 코드 (1) 태그 정규식이 빌더 FMT_RE 와 같은 태그를 잡고 CRLF 보존 (2) pandoc stdin 전환은 이미지(resource_dir 기준)·`--sandbox`·빈 입력·900KB 입력 모두 정상, n02 테스트 16건 통과 (3) 표 키 selftest OK (4) tests 에 pandoc 인자 고정 없음. 범위: mdr-hwpx/scripts 변경 0.
  필수 2건 반영: §2b 예시 `국가별 진입 경로 {형식=B}` 가 규칙(나라=비교 대상=A)과 모순 → `리스크별 대응 {형식=B}`; "숫자 뒤 괄호 주석 다음 줄로" 는 빌더 미구현(`<br>` 처리 없음)이라 작성자 몫에서 빼고 "원고에 `<br>` 금지, 한글 후편집 몫" 으로. 권장 반영: 16~24자 matrix 명시, 날짜 `YYYY.M.D.` 작성자 몫.
  권장 미반영(이유): 캡션 가운데 태그 경고 — 빌더도 같은 동작이라 회귀 아님, 규칙 한 줄로 충분. §2b 가 가리키는 빌더 문서 절은 f8 이 D:/skills 로 되가져오기 전까지 참조가 끊김(동기화 후 해소).
  f8 쪽 발견 2건(예시 모순, deliverable-rules §4 실제 수치 유출)은 `조율_메모_to_f8.md` 에 추가.

## 일부러 뺀 것
- 증빙판 PDF 에서 A/B 를 실제로 세로 병합으로 그리기: 고객 납품은 hwpx 라 빌더가 그린다. PDF 는 태그만 지운다.
- 형식 자동 판정 코드: 빌더(f8) 한 곳에만 둔다 — 같은 판정이 두 곳에 살면 어긋난다.

## 미해결
- f8 답변 대기: (b) 원고 모양 확인, (c) 숫자 뒤 괄호 주석 줄바꿈·속성명 의미 단위 줄바꿈을 원고에서 어떻게 표기하는지(빌더 규칙).
  답이 오면 §2b 마지막 불릿을 그 규칙으로 맞춘다.
