---
name: mdr-search
description: >-
  출처 찾기와 원문 스냅샷을 확보한다. 강방어 사이트는 코어 fetch 사다리로 우회한다.
  사용 시점 — "검색만 해줘", "자료/출처/원문/링크 모아줘", "이 주제 관련 보고서·기사·공시 찾아줘",
  "403 뜨는 사이트 본문 가져와줘", 시장조사 전 단계 자료수집만. 제외 — 수치 검증·증빙 PDF·보고서
  초안이 필요하면 market-deep-research.
---

# mdr-search — 검색만 (출처목록 + 원문 스냅샷)

사실대장·재검증·게이트·캡처·PDF 없이 출처를 찾고 원문 스냅샷만 남긴다.
같은 작업폴더를 나중에 `market-deep-research` 가 보고서 모드로 승격할 수 있다.

## 전제

코어 스킬 `market-deep-research` 가 설치돼 있어야 한다. 스크립트는 그 스킬의 `scripts/` 에 있다.

- 개발본 `<core>`: `codes/market-deep-research`
- 설치본 `<core>`: `~/.claude/skills/market-deep-research`

cwd 는 반드시 작업폴더(`research_<주제>_<YYYYMMDD>/`)다. 스크립트는 `<core>/scripts/x.py`
절대경로로 호출한다. `fetch.py` 는 cwd 의 `audit/` 에 fetch 로그·스냅샷을 쓴다.
인코딩은 `PYTHONIOENCODING=utf-8`.

## 워크플로

1. **요구 확정** (1~2문장 확인): 주제 · 기간 · 언어 · 출처유형(`web`/`news`/`academic`/`filing`) · 목표 건수.
2. **작업폴더**: `python <core>/scripts/skill_paths.py "<주제>"` 로 경로 확인한 뒤 그 폴더를 cwd 로 고정(동일 규칙이라 보고서 모드 승격 가능).
3. **검색**: 내장 WebSearch 병행(도구 목록에 없으면 deferred — ToolSearch 로 먼저 로드) + `python <core>/scripts/search.py "<q>" --n 10 --type web|news|academic|filing`. 쿼리 3~6개 변형(`site:` `filetype:pdf` `intitle:` `"정확구문"`). 검색 완전성 미보장.
4. **확보**: `python <core>/scripts/fetch.py get <url> --out _sources`. WebFetch 가 403 이어도 포기하지 말고 fetch.py 사다리를 탄다 — `references/source-ladder.md`.
5. **목록**: `python <core>/scripts/source_index.py . --topic "<주제>"` → `sources.md`.
6. **보고**: 사용자에게 `sources.md` 경로 · 건수 · 실패 URL 요약을 알린다.

## 하지 않는 것

사실대장 · 재검증 · 게이트 · 캡처 · PDF. 그건 `market-deep-research`.

## 보안

SSRF 차단은 `fetch.py` 내장(HTTP(S)만, 사설/루프백 차단). 로그인·CAPTCHA·paywall 필요 자료는 시도하지 않는다.

## 산출물

```
research_<주제>_<YYYYMMDD>/
  _sources/   <sha12>_raw.* · <sha12>_clean.txt · <sha12>.meta.json
  sources.md  출처 표 + 발췌
  audit/      fetch 로그 · 실패목록(있으면)
```
