# Batch B — 목적① "검색만" 스킬 `mdr-search` + 코어 `source_index.py`

작업 루트: `F:/Claude/skills/market-deep-research/` (브랜치 `feat/purpose-modules`, 워크트리 공유 — **다른 워커가 `tests/`·`SKILL.md`·`references/verification-gates.md`·`README.md` 를 동시에 고치는 중**이니 그 파일들은 건드리지 말 것)

## 배경
market-deep-research 는 G0~G5 전체 파이프라인(보고서 초안)이다. 사용자는 "검색만 필요한 경우"를 별도 진입점으로 원한다: 사실대장·재검증·게이트·캡처·PDF 없이 **출처목록 + 원문 스냅샷**만. 코드는 코어(`codes/market-deep-research/`)에 두고, `mdr-search` 는 그 코어 스크립트를 호출하는 얇은 스킬(SKILL.md)이다. 설계 근거: `_planning/council-2026-08-22/review-codex-modularize.md` 5절(한 코드 트리 + 얇은 래퍼), 사용자 확정 "목적별 모듈화".

먼저 읽을 것: `codes/market-deep-research/SKILL.md`(전체 흐름), `scripts/skill_paths.py`, `scripts/fetch.py`(특히 `fetch()` 반환 dict 와 `save()`), `scripts/search.py` CLI, `references/source-ladder.md`.

## 손대는 파일
- 신규 `codes/mdr-search/SKILL.md`
- 신규 `codes/market-deep-research/scripts/source_index.py`
- 수정 `codes/market-deep-research/scripts/fetch.py` — `save()` 에 메타 사이드카 추가(아래), 기존 동작·반환 호환 유지, demo 에 단언 추가
- (선택) `codes/market-deep-research/references/source-ladder.md` 에 "검색만 모드" 한 절(3~5줄)

## 할 일
1. **`fetch.save()` 메타 사이드카**: 현재 `_sources/<sha12>_raw.<ext>` 와 `<sha12>_clean.txt` 만 쓴다. 같은 폴더에 `<sha12>.meta.json` 을 추가로 쓴다: `{"url": 요청 URL, "final_url", "http_status", "mime", "is_pdf", "sha256", "accessed_at", "title", "raw": 파일명, "clean": 파일명|null, "status": ok|partial, "fetch_ref"}`. `title` 은 HTML 이면 `<title>` 또는 og:title(기존 `_ogp_partial` 재사용 가능)에서 뽑고 PDF/없음이면 null. `save()` 는 요청 URL 을 모르므로 시그니처에 `url: str | None = None` 키워드 인자를 추가하고 CLI `get` 에서 넘길 것(기존 호출자 호환). `demo()` 에 오프라인 단언(가짜 result dict 로 save → meta.json 필드 존재) 추가. 기존 `python scripts/fetch.py demo` 통과 유지.
2. **`scripts/source_index.py`** (코어, `skill_paths` import 패턴 따를 것):
   - `build_index(work_dir) -> list[dict]`: `_sources/*.meta.json` 을 읽어(없으면 raw/clean 파일명에서 최소 정보로 폴백) 번호·제목·발행처(최종 URL 의 호스트)·접근시각·URL·최종URL·sha256(앞 12자)·로컬 파일·발췌(clean 텍스트 첫 200~300자, 공백 정규화) 목록을 만든다.
   - `write_markdown(rows, out_path)`: `sources.md` — 머리말(주제·생성시각·건수) + 표(번호 | 제목 | 발행처 | 접근일 | URL | sha256 | 로컬) + 각 출처별 "발췌" 블록. 링크는 최종 URL. 실패 URL 은 `audit/fetch-failures.jsonl` 같은 게 있으면 부록에 건수만(없으면 생략).
   - CLI: `python source_index.py <work_dir> [--topic "..."] [--out sources.md]` · `python source_index.py demo`(임시 폴더에 가짜 meta/clean 파일을 만들어 표가 생성되고 행 수·발췌·링크가 맞는지 assert).
   - 출력 인코딩: `skill_paths` import 로 UTF-8 전파됨.
3. **`codes/mdr-search/SKILL.md`**:
   - frontmatter: `name: mdr-search`, `description`(200~250자, 트리거를 약간 밀어붙이는 톤): 무엇(출처 찾기+원문 스냅샷 확보, 강방어 사이트 우회 fetch 포함)·언제("자료/출처/원문/링크 모아줘", "이 주제 관련 보고서·기사·공시 찾아줘", "403 뜨는 사이트 본문 가져와줘", 시장조사 **전 단계** 자료수집만)·제외(수치 검증·증빙 PDF·보고서 초안이 필요하면 `market-deep-research`).
   - 본문(100줄 이내): ① 전제 — 코어 스킬 `market-deep-research` 가 설치돼 있어야 하며 스크립트는 그 스킬의 `scripts/`(개발본 `codes/market-deep-research/scripts/`, 설치본 `~/.claude/skills/market-deep-research/scripts/`)에 있다. ② 워크플로: 요구 확정(주제·기간·언어·출처유형·목표 건수, 1~2문장 확인) → 작업폴더 `python scripts/skill_paths.py "<주제>"` 로 경로 확인(동일 규칙이라 나중에 보고서 모드로 승격 가능) → 검색(내장 WebSearch 병행 + `search.py "<q>" --n 10 --type web|news|academic|filing`, 쿼리 3~6개 변형) → 확보(`fetch.py get <url> --out <wd>/_sources`; WebFetch 403 이어도 포기 말고 fetch.py — source-ladder 참조) → `source_index.py <wd> --topic "<주제>"` → 사용자에게 `sources.md` 경로·건수·실패 URL 요약 보고. ③ 하지 않는 것: 사실대장·재검증·게이트·캡처·PDF(그건 market-deep-research). ④ 보안: SSRF 차단은 fetch.py 내장, 로그인 필요 자료는 시도하지 않음. ⑤ 산출물 구조(`_sources/`, `sources.md`, `audit/`).
4. **실행 증거**: `PYTHONIOENCODING=utf-8 python codes/market-deep-research/scripts/fetch.py demo` · `python .../source_index.py demo` · (네트워크 가능하면) `search.py "PEM 수전해 시장" --n 3` 과 `fetch.py get https://example.com --out <임시>/_sources` 후 `source_index.py <임시>` 로 `sources.md` 가 실제 생성되는지 1회 스모크. 결과 마지막 줄들을 worker_done body 에.

## 제약
- Windows·cp949: `PYTHONIOENCODING=utf-8`. `curl_cffi`·`trafilatura` 설치돼 있음.
- `git commit` 금지. `.fablize/goals.py` 실행 금지. 코어 `SKILL.md`·`tests/`·`README.md` 수정 금지(다른 배치 소유).
- 모르는 것은 `orca orchestration ask` 로 질문.
