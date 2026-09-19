# market-deep-research 모듈화 설계안 (하이브리드) — 적대적 리뷰 요청본

작성: Claude(지휘 세션) 2026-08-22 · 상태: **제안(미착수)**. 코드 이동 전 반박을 받기 위한 문서.

## 0. 사용자 확정 사항(전제 — 뒤집지 말 것)
- 형태: **하이브리드**. 하네싱(사실대장·게이트·영수증·검증)과 오케스트레이션(SKILL.md 파이프라인)은 코어에 남긴다.
- 목적: ① 컨텍스트 절약 ② 유지보수·테스트 용이 ③ 부분 실행(수집만/캡처만/렌더만).
- 차후 **hwpx 등 양식(출력) 모듈**을 추가로 붙일 예정 → 양식 모듈 계약이 필요.

## 1. 현재 구조 (실측: `codes/market-deep-research/`)
| 기능 | 스크립트(줄) | 참조문서/자산 | 내부 import |
|---|---|---|---|
| ① 수집 | `fetch.py`(577) `search.py`(221) | source-ladder.md extract-recipes.md · searx-instances.json curated-sources.json | search→fetch, skill_paths(ASSETS) |
| ② 대장·영수증 | `facts_db.py`(433) `gates.py`(564) | verification-gates.md · facts-schema.json | skill_paths |
| ③ 증빙 캡처 | `capture_pdf.py`(163) `capture_web.py`(84) | evidence-capture.md | 없음(fitz) |
| ④ 도판 | `harvest_images.py`(791) `make_chart.py`(286) | image-research.md | harvest→fetch+ASSETS(searx/curated) · make_chart→facts_db(FactsDB, _write_jsonl_atomic)+skill_paths |
| ⑤ 검증·봉인·렌더 | `verify_facts.py`(945) `manifest.py`(136) `render_pdf.py`(127) `preview_pdf.py`(65) | report-format.md · style.html | verify→facts_db,gates,manifest · manifest→gates · render→gates,manifest,preflight(_find_chrome),skill_paths |
| ⑥ 오케스트레이션 | SKILL.md(184) `preflight.py`(97) `skill_paths.py`(134) `install.py`(171) | agent-briefs research-plan entity-identity | — |

- 테스트: `tests/test_adversarial.py`(84 함수, `python tests/test_adversarial.py` 직접 실행, pytest 미사용) · `tests/test_e2e.py`. 둘 다 `sys.path.insert(0, scripts/)` 후 전 모듈 import.
- 설치: `install.py` 가 `~/.claude/skills/market-deep-research/` 로 해시검증 복사(+`--check` 드리프트 감시, stale 정리).
- 영수증 원칙: G3·[4b]·G5 는 **소유 스크립트만 자기기록**(verify_facts.py · render_pdf.py · manifest.py verify). CLI 손기록 차단.
- `skill_paths.py` 는 import 부수효과로 stdout/stderr UTF-8 재설정(cp949 방지)을 전 스크립트에 전파.

## 2. 제안 구조
```
codes/
├── market-deep-research/      ← 코어 (트리거 스킬, 파이프라인 G0~G5·게이트·영수증)
│   scripts/ skill_paths facts_db gates verify_facts manifest preflight install
│            + render_report.py (신규: 양식 모듈 디스패처 — [4b] 영수증·manifest build 는 여기서)
│   references/ verification-gates agent-briefs research-plan entity-identity report-format
│   assets/ facts-schema.json        tests/ (통합 테스트 유지)
├── mdr-collect/       수집  — fetch.py search.py · source-ladder extract-recipes · searx/curated json
├── mdr-capture/       증빙캡처 — capture_pdf.py capture_web.py · evidence-capture.md
├── mdr-figures/       도판  — harvest_images.py make_chart.py · image-research.md   (→ mdr-collect 사용)
└── mdr-render-pdf/    양식:PDF — render_pdf.py preview_pdf.py · style.html  (차후 mdr-render-hwpx 동일 계약)
```
각 모듈 = 독립 스킬 폴더(SKILL.md + scripts/ + references/ + assets/). 설치 시 `~/.claude/skills/<모듈명>/`.

## 3. 의존 규칙
1. **모듈은 코어를 import 하지 않는다.** 경로(work_dir·입출력 파일)를 인자로 받는 순수 도구. 대장(facts/evidence) 쓰기·영수증 기록은 코어만.
2. 코어 `skill_paths.module_scripts("<모듈명>")` 이 형제 모듈 위치를 찾아 `sys.path` 에 넣는다 — 탐색 순서: `SKILL_ROOT.parent/<모듈명>`(개발본 `codes/`) → `~/.claude/skills/<모듈명>`(설치본). 없으면 명시적 에러.
3. 모듈→모듈은 허용(figures→collect). 같은 로케이터 로직을 모듈 쪽에 최소 복제(5줄) 또는 subprocess CLI 호출.
4. 각 모듈 SKILL.md 는 짧은 description(≤150자)으로 **단독 트리거** 가능("이 403 사이트 본문만 가져와" → mdr-collect).

## 4. 풀어야 할 결합 3건(실제 작업)
1. `render_pdf.py` ← gates/manifest/preflight: 영수증·봉인은 코어 `render_report.py --format pdf` 로 이동. 모듈에는 `render(md_path, out_path, resource_dir) -> {"ok","out","size","at"}` 와 `preview(out_path, out_dir) -> [png]` 만 남김 = **양식 모듈 계약**. `_find_chrome` 은 render 모듈로 이동, 코어 preflight 가 로케이터로 import(없으면 "모듈 미설치"로 표시).
2. `make_chart.py` ← FactsDB: confirmed 사실 읽기는 facts.jsonl 직접 읽기(~10줄)로 대체. `_write_jsonl_atomic` 은 demo 에서만 쓰므로 demo 내부로 인라인.
3. `install.py`: `codes/*/SKILL.md` 를 가진 폴더 전부를 각 `~/.claude/skills/<폴더명>/` 로 설치·`--check`.

## 5. 트레이드오프(인지된 것)
- 모듈 4개 description 이 모든 세션에 상시 로드(합계 ~600자). 부분 실행의 대가.
- 테스트는 코어에 두고 `module_scripts()` 로 경로만 추가해 84건 그린 유지가 1차. 모듈별 테스트 분리는 2차.
- 참조 문서 안의 `scripts/fetch.py` 같은 상대경로 언급은 전부 모듈 경로로 갱신 필요.

## 6. 리뷰어에게 묻는 것
- 이 분할 경계가 틀린 곳(같이 움직여야 하는데 갈라진 것 / 갈라야 하는데 붙은 것).
- 의존 규칙 1~3 이 실제 코드에서 깨지는 지점(특히 gates 영수증 소유권, manifest 해시 대상, UTF-8 부수효과).
- 양식 모듈 계약이 hwpx 에서도 성립하는가(hwpx 는 md→hwpx 변환이 pandoc/chrome 과 전혀 다름).
- 컨텍스트 절약이 실제로 나는가(코어 SKILL.md 에서 무엇이 빠질 수 있는가).
- 더 싼 대안(한 스킬 내 하위폴더 등)이 목적 ①②③을 충족하지 못한다는 근거가 충분한가.
