# Batch T1 — 컨텍스트 예산 리팩토링 (ponytail 레슨 적용)

작업 루트: `D:/skills/market-deep-research/` (브랜치 `refactor/context-budget`, 2026-10-08). 계기: [dietrichgebert/ponytail](https://github.com/dietrichgebert/ponytail) 벤치마크(Opus 5.5, 39과제×5회)에서 출력 토큰 -45%·턴 -22% 의 비결이 "항상 켜지는 프롬프트를 작게(SKILL.md 3.5KB), 지금 적용되는 규칙만 주입, 색인은 두고 상세는 필요할 때" 였다는 점. 이 저장소를 같은 잣대로 재서 고친다.

## 배경 — 측정 (탐색 에이전트 2개, 읽기 전용)

| 항목 | 전 | 후 | 비고 |
|---|---|---|---|
| market-deep-research description | 414자 | **226자** (워커 174자 → 리뷰 보강) | 모든 세션의 스킬 목록에 실림. 전역 규칙 200~250자 |
| market-deep-research SKILL.md 본문 | 16,205B (LF) · 파일 17,296B (CRLF) | **10,540B** (−35%; 워커 10,228B → 리뷰 보강 +312B) | 스킬이 켜지면 매 턴 재전송. 가드 상한 12,288B(목표 10KB) |
| 그중 게이트 절 G0~G5 | 약 10.8KB | 약 4.8KB (카드 10개) | `verification-gates.md` 22,317B → 약 23,5xxB (SKILL 에만 있던 문장 13줄 + verbatim/locator 복원). 순감 ≈ SKILL −5.7KB, VG +1.2KB → 상주량 −4.5KB |
| mdr-hwpx SKILL.md 본문 | 8,603B · description 208자 | **8,163B** · 208자 | 통과 기준 정본 = consistency-review.md 「통과」, SKILL·hwpx-form 은 포인터 |
| mdr-search SKILL.md | 2,764B · 203자 | 변경 없음 | |
| 워커 브리프(agent-briefs.md) | 계약 ~2.8KB, 구조화 마커 반환 | "(파일충돌 방지)" 한 구절만 | 이미 날씬함 |
| 테스트 | 609 passed (test_v4_gates·test_v4_semantic 은 finalize_report 부재로 수집 실패, README 알려진 결함) | **609 passed** (가드 2건 포함) | 줄끝 CRLF 보존 확인(CR 수 113/207/127) |
| `git diff --stat` | | 10 files, +74 −79 | SKILL.md 98줄, VG 13줄, test 9줄, mdr-hwpx 4파일 24줄 |

도구 메모: `bd`·`codegraph` 가 이 PC 의 Git Bash PATH 에 없어 beads 노드화 대신 이 파일이 과제 목록을 대신한다.

## 손대는 파일
- `codes/market-deep-research/SKILL.md` — description 축약 + 게이트 절을 카드로.
- `codes/market-deep-research/references/verification-gates.md` — SKILL 에만 있던 상세 문장의 정본 위치.
- `codes/market-deep-research/references/{agent-briefs,report-format,reader-goal,research-plan}.md` — 받아 줄 문장이 있을 때만.
- `codes/market-deep-research/tests/test_adversarial.py` — `skill_frontmatter_intact` 에 예산 가드(description ≤250자, 본문 ≤10,240B).
- `codes/mdr-hwpx/SKILL.md`, `codes/mdr-hwpx/references/{consistency-review,deliverable-rules,hwpx-form}.md` — 통과 기준 1사본화 + 포인터.
- `README.md` 개발 이력 1행, `lessons.md` 2026-10-08 절.

## 할 일
- **T1** SKILL.md: description ≤250자(트리거 구절·"기술사업화 실사" 유지). 게이트 절 10개 → 카드(목적 · 절대 규칙 · 영수증 명령 · `→ verification-gates.md §X`). 지운 문장은 VG 해당 절에 있는지 확인, 없으면 원문 그대로 이사. **삭제만 하는 문장은 없다.** 테스트가 고정한 문장(조사 분할 불릿, 확장수렴 루프 블록, "기술사업화 실사", "intent-diff"×2, "축별 충분조건"·"루프 수렴조건", [4] 절의 `verification-gates.md`) 은 그대로.
- **T2** 가드 테스트 (리드 직접, 완료).
- **T3** mdr-hwpx 중복 6곳 → 정본 1곳 + 포인터. `scripts/build_hwpx.py:625` 런타임 문구는 불변.
- **T4** 이 파일 · README · lessons (리드 직접).

## 제약
- 동작·규칙 삭제 금지(리팩토링). 단정→권고 약화, 주체 변경 금지.
- 저장소에 CLAUDE.md 없음 → chk-scope "불변 규칙 없음".
- 산출물 2파일↑ → 다른 모델(opus) 독립 리뷰 통과 후에만 완료.

## 일부러 뺀 것
- facts ID 색인 CLI(`facts_db.py index`): 새 기능. 다음 배치 후보.
- `verification-gates.md` 게이트별 분할: 한 세션에서 전 게이트를 지나므로 상주량이 안 줄어든다.
- 워커 브리프 축소, [2] 전건 재검증 위임, GLOBAL.md 축소: 범위 밖.

## 워커 보고 (sonnet, T1·T3 대응표 — 줄 번호는 main 기준 SKILL.md)

워커 가정: 10,240B 상한을 맞추려 카드의 "목적 한 줄" 은 G0·[3]·G3·[4]~G5 에만 남김. 카드 제목의 `【v3-x】` 태그는 흐름도에 있어 [1] 외에는 뺌. 참조 표에 `claim-review.md` 행 추가. "통과 기준 3사본" 은 문장이 완전히 같지 않아(consistency-review 통과 절은 ②→③ 진입 조건) SKILL·hwpx-form 에만 있던 `grade_pdf.py` 결함 0·의심쪽 PNG 육안 확인 문장을 consistency-review 「통과」 로 옮기고 나머지는 포인터.

**verification-gates.md 로 이사(원문 그대로)**: G0 `--refs` 수시 변경 문서 결박 경고 · G1 `check G1` · [2] `record/check [2]` · Bx `negative_search` 결박 · G3 fail-closed · G5c 계산·상충·성능 문구 + "시장조사 접점" · G4 `check G4` 드리프트, 역방향 고아 검사 괄호, "재봉인을 건너뛰면 G5 가 못 잡는다".
**다른 파일로**: agent-briefs "(파일충돌 방지)" · deliverable-rules `HWPX_TABLE_FLOAT_ALL` 사유, `make_references.py --style`.

| SKILL.md 원래 줄 | 처리 |
|---|---|
| L62~65 G0 | 카드 잔류. 상세 VG L11~19 · research-plan. L63 §0 서식은 reader-goal L7~10·35~38 에 이미 있음. L64 VG L12~13 에 이미 있음 |
| L66, L67 | 포인터만. entity-identity 표 · competitive-positioning 에 이미 있음 |
| L68 intent-diff 개시 | VG L18~19 에 이미 있음 |
| L69 영수증 | 명령은 카드 잔류, `--refs` 경고는 VG G0 로 이사 |
| L72 조사 분할, L75 확장수렴 루프 | **원문 그대로 유지**(테스트 고정) |
| L73~74 워커 규칙·반환 마커 | agent-briefs L5·10·15·19~48 에 이미 있음. 카드에 한 줄 |
| L78~80 G1 | VG L22~23·39 에 이미 있음. 무출처 discarded 는 카드 잔류. `check G1` 은 VG G1 로 이사 |
| L83~86 [2] | VG L33~36 에 이미 있음. 403 사다리는 source-ladder L38. 2차 DB 교차는 agent-briefs L77. `record/check [2]` 는 VG 로 이사 |
| L89~91 Bx | VG L36~43 에 이미 있음. 4요건은 카드 잔류. `negative_search` 결박은 VG Bx 로 이사(extract-recipes L12 에도) |
| L94 G2 | VG L46~48 · evidence-capture L11 에 이미 있음 |
| L97~100 [3] | report-format L3~29·68~72 · image-research · visual-first L42 · VG L122~123 · reader-goal L40~44 에 이미 있음 |
| L101 의미 대조 검수 | 카드 잔류(다른 곳에 없음) |
| L104~107 G3 | VG L64~66·81~86 · claim-review L52 에 이미 있음. fail-closed 는 VG G3 로 이사 |
| L110 G5c | VG G5c 로 이사 |
| L113~119 [4]~G5 | 카드에 extend-only·check G4·record G4·verify·v4 출고 잔류. 나머지 VG L118~128·134~139·171~173·180·188~189 에 이미 있음. "건너뛰면" 문장·고아 검사 괄호·`check G4` 는 VG G4 로 이사 |

| mdr-hwpx 원래 줄 | 처리 |
|---|---|
| SKILL.md L34 | `HWPX_TABLE_FLOAT_ALL` 사유 → deliverable-rules L32. 환경변수 지시는 SKILL 잔류 |
| SKILL.md L50~51 | `--style` 인자 → deliverable-rules §5. SKILL 은 2줄 |
| SKILL.md L68~69 | consistency-review (a)~(f) 에 이미 있음 → "체크리스트(a~m)" 포인터 |
| SKILL.md L112~115 | consistency-review 「통과」 로 이사. SKILL 은 한 줄 요약+포인터 |
| hwpx-form.md L167 | "정적 검사는 검증이 아니다" 원칙 → consistency-review 「통과」 정본, 포인터로 교체 |

## 독립 리뷰 (opus, 읽기 전용 — 워커 보고를 믿지 않고 diff 에서 직접 대조)

결론: **수정 후 통과**. A 항 누락 후보 13건은 전부 정본에 있음을 확인(VG:20·26·38·47·70·114·128·131·132·140~146·195~196, agent-briefs:71·77, image-research:24, reader-goal:43, visual-first:42, report-format:69). 테스트 고정 문장은 main 과 동일. 줄끝은 `core.autocrlf=true` 라 정상. mdr-hwpx 는 통과 기준이 consistency-review 「통과」 한 곳, build_hwpx.py 변경 0줄.

| 지적 | 처리 (리드 직접) |
|---|---|
| **필수** [2] 팀리드 "verbatim/locator 대조" 가 카드·VG §[2] 양쪽에서 빠짐(3대 원칙 2 에만 잔존) | VG §[2] 전건 줄에 "·verbatim/locator 대조" 복원 |
| **필수** 본문 예산 여유 12B — 카드 한 단어 추가로 가드가 깨짐 | 가드 상한 10,240→12,288B(목표 10KB 는 docstring·lessons 에 명시, `ponytail:` 주석) |
| description 174자가 전역 하한 200자 미달 | 리뷰어 226자 안 채택(병렬 서브에이전트·원문 재열람·팩트시트 PDF·WebSearch 직접 복원) |
| [G2] "영수증 없음" 이 비강제로 읽힘 | "(`verify_facts` 의 캡처 실재 검사로 강제)" 추가 |
| [G1] "영수증을 남긴 뒤" 누락 | 복원 |
| [G5] "명시해야만 통과·legacy_v3" 누락, 포인터에 v3→v4 이행 없음 | 둘 다 복원 |
| [3] 운용 규칙 3 파일명 없음, "점검" 이 "답하며" 로 약화 | `reader-goal.md` 명시, "점검" 복원 |
| [G0] preflight.py 명령 없음(선택) | 목적 줄에 추가 |
| 참조 표 힌트(agent-briefs [2] 철칙, visual-first 결정표, competitive §6) | 복원 |

리뷰어 가정: 정본 대조는 grep 결과를 사람이 읽어 판정(문장 단위 기계 대조 아님). 실행한 테스트는 test_adversarial.py 만 — 전체 609건은 리드가 재실행.
