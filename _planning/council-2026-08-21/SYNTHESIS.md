# 모델 카운슬 종합 — market-deep-research (2026-08-21)

- 참여: **grok-4.6 xhigh**(실전 수집·운영 렌즈, `review-grok.md`) · **claude-fable-5**(설계·문서 정합 렌즈, `review-claude.md`)
- 불참: codex gpt-5.6-sol xhigh(적대적 게이트 렌즈) — 약 25분간 worker_done 없음, 사용자 판단으로 중단. 게이트 위조 관점은 두 모델의 30% 조망분으로 일부 보완됨.
- 종합 판정: **FIX-FIRST** (2/2 일치). 재설계 불요. 뼈대(증거모델·대장·해시봉인·영수증 소유권·적대 60종)는 건전하고 양쪽 모두 실측으로 확인.

---

## 1. 두 모델이 독립적으로 같은 결론에 도달한 것 (최우선)

| # | 합의 지적 | grok | claude | 최소 수정 |
|---|---|---|---|---|
| C1 | **[Bx] claim-graph 4요건이 WARN** — high-risk 시장규모·CAGR 이 1출처로 confirmed 가능. "조사마다 다른 숫자"를 막는 유일한 기계 게이트가 권고 수준 | HIGH-G | H4 | `verify_facts.py:385-399` — `risk=high ∧ confirmed ∧ used` 에 한해 ①독립그룹≥2 ②반박검색 존재를 FAIL 승격. 기권은 `disputed` |
| C2 | **G1 영수증 CLI 손기록 가능, [2] 영수증이 facts.jsonl 과 무결박** → G3 선행조건이 형식 | HIGH-H | M1 (실측 ok=True) | G1 영수증 삭제(`check_ledger_integrity` 가 실질) · `record_manual [2]` 가 confirmed 전건 lead 이벤트 검사 + `facts_db_sha256` 결박 |
| C3 | **워커 반환 마커 파서 부재 + 스폰 계약에 실행정보 없음** → LLM 출력 변동이 그대로 입력단 오류 | HIGH-5 | M8·H3③ | `scripts/parse_markers.py`(필수 섹션·JSONL 전건 `json.loads`·FIGURES 없음/누락 구분) + `agent-briefs.md` 에 SKILL_ROOT/WORK_DIR/AGENT_DIR/schema 경로 5행 + JSONL 은 파일로 반환 |
| C4 | **도판 결박 약함** — `_images/` manifest 미추적(교체 후 verify ok 실측), 핫링크 G3 통과, 라이선스 `unknown` 고정 | HIGH-4 | M3 | `manifest.py TRACKED` 에 `_images/**` 1줄 · 본문 도판은 `_images/`/`assets/` 외 FAIL · `license` 를 search→download→IMAGES.md 로 전달, NC/ND·unknown 은 고객 PDF 금지 |
| C5 | **G5c "내용검사 강제" 가 코드에 없음** | HIGH-H | §5 과잉 | `audit/verify-*.md` 글롭 검사 추가하거나 "권장 절차" 로 격하 — 둘 중 하나로 문서↔코드 일치 |
| C6 | **lead 재열람이 자가신고** — `by="lead"` 누구나 호출, fetch-log 와 무관 | MEDIUM-2 | M2 | lead verify_event 에 `reread_sha256`(또는 fetch_ref) 필수, `validate_fact` 에서 검사 |
| C7 | `capture_web.py` 는 게이트 소비처 없음 → 삭제 후보 | (v1 과잉 재확인) | §5 | 삭제 |

## 2. 한쪽만 잡은 것 — 렌즈 고유 발견 (모두 실측 근거 있음)

### grok 고유 (수집 스택)
- **BLOCKER** SearXNG 공개 풀 5/5 JSON 실패(HTML·429·403·DNS) → 검색 2계층이 DDG 단층. 429 가 `break`(`search.py:84-102`), `health_path` 미사용.
- **BLOCKER** `validate_body` 가 본문 ≥1000자면 챌린지보다 먼저 ok(`fetch.py:204-208`) → 페이월 티저 장문 승격. Jina/Wayback/OGP 파생본 `archived_url` 비필수. Jina 라이브 CF 403, Wayback HTTPS reset.
- HIGH Googlebot UA 가 v2 합의(제외)와 달리 `DEFAULT_ORDER` 복귀(`fetch.py:51`) — 정책 문장과 코드 공존.
- HIGH `harvest_images.download`·`search._get` 은 리다이렉트 SSRF 무방비(`allow_redirects` 기본, `check_response_ip` 없음), 빈 MIME 통과, `HTTP_PROXY` 시 검사 전부 스킵.
- HIGH 원문→프롬프트 인젝션 방어가 문서 한 줄뿐(펜스·플래그 없음).
- MEDIUM `capture_pdf` 첫 히트 고정(같은 숫자 다른 표), fetch-log 가 cwd `audit/` 에 기록(work_dir 아님), `claim_key` 중복 거부가 상충 수치를 조용히 버림.

### claude 고유 (G3 검사 구멍·규모·문서)
- **HIGH** 부록(`FACTSHEET:APPENDIX` 이후)은 **무검사**로 고객 PDF 진입(`verify_facts.py:657-665`, 실측 `999조원(F001)` 통과).
- **HIGH** 단위 화이트리스트 밖 수치 전부 PASS — `$4.5B`(무태그), `$999M(F002)`(오값), `건·명·위·배·€·kt·배럴`, 한글 수사(`verify_facts.py:55-62`). 영문 시장보고서·한국 실사 관행이 정확히 사각지대.
- **HIGH** 규모 설계 부재 — fact 수 상한 없음, 코드는 **모든** 숫자 fact 에 실화면 캡처 요구(문서는 "핵심수치")(`verify_facts.py:435-442`), `gates.py status` 가 SKILL.md 에 0회 → 압축 후 재진입 절차 없음.
- MEDIUM G5 "PDF F태그·캡처 수 재검사" 스크립트 없음(manifest 는 해시만) · `fetch.py get --out` 의 `local` 경로가 `verify_facts` 규약과 어긋남 · 축 프리셋: 산업동향 "통계" 는 출처지 질문 아님, 실사에 리스크·준법 축 없음 · 10부 에이전트별 인사이트는 사용자 lessons(작업 흔적 배제)와 충돌 · `diff_facts` 미배선.
- 컨텍스트 예산 실측: SKILL+references 35,163자 ≈ 21~28k 토큰 — 문서 자체는 과하지 않음.

## 3. 과잉 — 빼는 것이 수정 (양쪽 합집합)
`capture_web.py` · `harvest_images search`(openverse/commons/searx) · dcinside 등 커뮤니티 ROUTES · Googlebot 홉 · 공개 SearX 로테이션 · WAF XHR 정찰 · 도판 0장 FAIL(→WARN) · 저널 4종→2종 · G1 영수증 · `PREREQUISITES["[4]"]` · 4차원 등급 "게이트" 서술.

## 4. 권고 실행 순서 (작은 diff, 큰 구멍부터)
1. **G3 구멍 3건** — 부록 검사(무태그만 면제) · 접두 통화기호+단위 확장 · `_images` manifest 추적. 각 10줄 내. 적대 테스트 3건 추가.
2. **[Bx] ①② FAIL 승격** + `record_manual [2]` sha 결박 + lead 이벤트 `reread_sha256` 필수. (C1·C2·C6)
3. **수집 사다리 fail-closed** — `validate_body` 챌린지/페이월 우선, 파생본 `archived_url` 필수+directness 상한, Googlebot 제거, SearX 코어 제외(또는 자가호스트), harvest/search 에 fetch 와 같은 홉 SSRF.
4. **`parse_markers.py` + 스폰 계약 실행정보** + JSONL 파일 반환. (C3)
5. **규모 설계** — fact 상한(기본 60) · 캡처 tier(high-risk+KPI 만 실화면) · SKILL.md 재진입 5줄.
6. 과잉 제거(§3) · 축 프리셋 2종 수정 · G5c/G5 문서↔코드 일치.

## 5. 검증 기록
- 두 워커 모두: 스크립트 demo · `tests/test_adversarial.py` 60/60 · (claude) `test_e2e.py` PASS 를 직접 실행. 우회 실증은 임시폴더 probe 로 수행, 저장소 무변경.
- grok 라이브 프로브(2026-08-21): DDG 5건 1.35s 정상 / SearXNG 0/5 JSON / Jina CF 403 / Wayback HTTPS reset·HTTP 200 / Openverse `by-nc` 필드 download 시 유실.
