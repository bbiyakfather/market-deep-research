# v10 — 복구·개선 계획 (2026-08-07)

> 5-에이전트 팀 감사(23 에이전트, 200만 토큰) + 스카우트(29 에이전트, 228만 토큰) 결과.
> 감사는 각 발견을 **별도 에이전트가 적대적으로 반증 시도**한 뒤 살아남은 것만 실었다.

## 베이스라인 (착수 시점 실측)

| 검증 | 결과 |
|---|---|
| `python tests/test_adversarial.py` | 72/72 검출 성공 |
| `python tests/test_run_ledger.py` | 20/20 검출 성공 |
| `python tests/test_e2e.py` | PASS (PDF 2쪽) |
| `python scripts/preflight.py` | HARD 4/4 OK, SOFT 3/4 (yt_dlp 누락) |
| `python scripts/install.py --check` | 드리프트 0 |

**즉 "깨진 곳"은 테스트가 잡는 표면이 아니다.** 이번 감사가 노린 것은 테스트가 그린인 채로
실제 조사 실행에서만 터지는 잠복 결함이다. 17건이 나왔고 그중 6건이 HIGH다.

## 과거 배치 상태 정정

v5 우선순위 문서의 "유예 12건" 중 다음은 **이미 착지**했다(v6/v9). 다시 손대지 않는다.

| 항목 | 착지 위치 |
|---|---|
| `EV-1` evidence 실파일 해시 결박 | `verify_facts.py:488-502` `[해시미결박]` FAIL |
| `EV-2+EV-3` 캡처 사후교체 검출 | `verify_facts.py:555-560` `[캡처해시]` |
| `SC-4` 백지 캡처 기계검출 | `capture_pdf.is_blank_pixmap()` 전수 계산 |
| 픽스처 마이그레이션 (5건의 선행 조건) | `tests/_confirm()` 이 실파일 스냅샷·실해시·진짜 PNG 생성 |

선행 조건이 풀렸으므로 나머지 유예분은 이번·다음 배치에서 개별 판단한다.

---

# 1부 — 복구 (확인된 결함 17건)

## HIGH (6건)

### C1. `search.py:44` — `_get()` 이 리다이렉트를 자동추종해 홉별 SSRF 검증을 우회
`_get()` 은 초기 URL 만 `check_url_safe` 하고 `creq.get(...)` 에 `allow_redirects` 를 넘기지
않는다. curl_cffi 기본값은 `True`(소스 실측). 반면 `fetch.py:_fetch_once` 는
`allow_redirects=False` 로 수동 루프를 돌며 **매 홉** `check_url_safe(cur)` 를 호출한다.
검증자가 로컬 2서버로 실제 재현: 내부 주소로의 GET 이 **실제로 발생**했다(blind SSRF).
`check_response_ip` 가 최종 IP 만 사후 점검해 본문 유출은 막지만 요청 자체는 이미 나갔다.
진입점은 `search_with_diagnostics` 의 전 백엔드(DDG/SearXNG/arXiv/SEC)가 공유하고,
SearXNG 5개 인스턴스는 **프로젝트가 통제하지 않는 제3자 서버**다.
회귀 테스트도 없다 — `dns_rebinding_post_connect` 의 `_FakeCreq.get` 은 `kw` 를 통째로 무시해
`allow_redirects=False` 전달 여부를 검증하지 못한다.

**수리**: `_get()` 을 `fetch.py` 와 같은 홉별 검증 루프로 통일. 테스트 목이 `kw` 를 관찰하도록 승격.

### C2. `search.py:99` — `is_blocked_page()` 가 `_searx()` 에 배선되지 않음
`_searx()` 는 `429/503` 일 때만 `blocked` 에 기록하고, 200 + 비JSON 은 조용히 다음 인스턴스로
넘어가며 아무것도 남기지 않는다. `is_blocked_page()`/`block_markers` 는 정의만 되고
`_ddg()` 에서만 호출된다.

**라이브 실측(2026-08-07)**: 5개 인스턴스 중 JSON 을 주는 곳이 **0개**. `searx.be` 는 200 으로
봇확인 페이지를 주고 `is_blocked_page()` 는 그걸 `True` 로 정확히 판별하는데 호출되지 않아 무시된다.
`_searx(...)` 직접 실행 결과 `results=[] · blocked=[]`.
→ `source-ladder.md:77-80` 의 계약("결과 0건 + blocked 비어있지 않음을 무출처로 결론내지 말 것")이
**지금 이 순간 성립하지 않는다**. 커버리지 공백이 "이 주제는 출처가 없다"는 서술로 굳을 수 있다.

**수리**: `_searx()` 에 `is_blocked_page()` 배선. `searx-instances.json` 갱신.

### C3. `verify_facts.py:748` — `capture_mode="mcp"` 가 약결박 WARN 을 전혀 못 받는다
`_capture_mode_warnings()` 는 `"screen"`/`"print"` 만 분기하고 `"mcp"` 는 `return []` 로 빠진다.
그런데 `facts-schema.json:99` 는 "mcp(브라우저 MCP). 약한 경로는 verify_facts 가 WARN 으로
표면화한다"고 약속한다. MCP 경로는 `screen` 과 동일하게 텍스트레이어가 없어 `capture_verbatim`
기계확인이 불가하며, `evidence-capture.md` 자체가 **agent-browser 가 백지를 저장하면서
success:true 를 반환한 실제 사고**를 기록하고 있다.
→ 가장 백지 위험이 큰 경로(로그인 게이트 소스)만 유일하게 재확인 지시를 안 받는다.

**수리**: `mode in ("screen", "mcp")` 동일 처리.

### C4. `run_ledger.py:178` — "미처분 충돌 잔존 시 G2 진입 불가"가 미구현
`kind:conflict` 만 기록하고 대응 `kind:disposition` 없이 `checkpoint(G2, PASS)` 를 호출하면
floor (b)/(c) 어디에도 안 걸리고 그대로 PASS 된다. SKILL.md 167-168행의 명시적 약속이 코드에 없다.

**수리**: `_floor_scan` 에 (e) 추가 — 미처분 conflict 존재 시 G2 이상 게이트 BLOCK 강제.

### C5. `run_ledger.py:172` — `evidence.jsonl` 변조가 신선도 판정에서 완전히 빠짐
`target_hashes` 에 기록만 되고 어디서도 대조되지 않는다. `gates.json` 의 어떤 게이트도
`evidence` 를 `watches` 에 넣지 않는다. → **G2 PASS 이후 evidence 의 verbatim/source_url 만
바꿔치기해도 `status` 는 계속 `fresh/PASS`**. "수치를 확정한 뒤 증거 원문을 조용히 바꾼다"가
신선도 시스템에 안 걸린다.

**수리**: `gates.json` 의 G2/G3/G5C/G5 `watches` 에 `evidence` 추가 + `_watch_file()` 매핑 추가.
※ `test_run_ledger.py:60` 의 화이트리스트 assert 동반 갱신 필요.

### C6. `manifest.py:23` — `bm-summary.md` 가 재봉인 대상에서 누락
`report-format.md:134` 가 "[4b] 재봉인 대상에 포함(manifest 해시 고정)"이라 명시하지만
`TRACKED` 글롭에 대응 패턴이 없고 `WorkPaths` 에 속성 자체가 없다. → BM 조사 유형의 별도 산출물이
변조·교체돼도 `manifest.py verify` 가 잡지 못한다.

**수리**: `TRACKED` 에 `("bm_summary", "bm-summary.md")` + `WorkPaths.bm_summary`.

## MEDIUM (7건)

| # | 위치 | 결함 | 수리 |
|---|---|---|---|
| C7 | `fetch.py:504` | `status:fail` 힌트가 v9 이전 문구("브라우저 MCP 부터") — 에이전트가 이 힌트만 보고 코어 내장 `capture_live()` 를 건너뛴다 | 힌트 문구 갱신 |
| C8 | `verify_facts.py:895` | `--conversion` 이 Decimal 검산을 **하지 않는다** — `decimal` 필드 존재만 확인. `억달러/조원` 등 자기 코드가 `UNIT_SCALE` 에 정의한 한국어 표기는 `unit.startswith(('USD','$'))` 에 안 걸려 검사 자체가 미발동. 명백히 틀린 환산값도 0 경고 | `UNIT_SCALE` 기반 실제 Decimal 재계산 |
| C9 | `facts_db.py:76` | `dispute_kind='refuted'` + `superseded_by` 없음이 어디서도 안 잡힌다 — 반박된 fact 가 영구 미해결로 대장 잔존 | `validate_fact` 조건 추가 |
| C10 | `run_ledger.py:420` | G5C 대상 선별(`derivation=computed` / `evidence.type=calculation`)과 `verify-<slug>.md` 존재를 기계 대조하는 코드 없음 — 전적으로 수기 점검 의존 | G5C floor 추가 |
| C11 | `verify_facts.py:168` | 한국어 복합 수사 부분매치 — `4천5백억원` 에서 `4천` 을 놓치고 `5백억원` 만 매칭(500억 vs 실제 4500억). **정상 원문이 `[값불일치]` 거짓 FAIL** | 좌→우 누적합산 파서 |
| C12 | `run_ledger.py:316` | G5 의 `run_receipt` 자기참조 해시가 write-only — G5 PASS 후 `run-receipt.md` 변조를 못 잡는데 docstring 은 "무결성 anchor"라 주장 | 감시 대상 편입 or docstring 정정 |
| C13 | `SKILL.md:71` 외 4곳 | 문서는 `G5c`(소문자), CLI enum 은 `G5C`(대문자) — 문서대로 입력하면 거부 | CLI 에서 `upper()` 정규화(문서 5곳 수정보다 짧고 향후 흔들림도 흡수) |

## LOW (4건)

| # | 위치 | 결함 | 수리 |
|---|---|---|---|
| C14 | `search.py:81` | DDG title 의 HTML 엔티티 미해제 — `AT&T`, `Procter & Gamble` 이 `&amp;` 로 손상된 채 대장·보고서에 실림. 코드베이스 전체 `html.unescape` 0건 | `html.unescape()` |
| C15 | `fetch.py:42` | `mime_allowed()` 의 `if not mime: return True` — Content-Type 을 비운 서버는 화이트리스트를 통째로 우회 | 빈 헤더는 매직바이트 판정으로 폴백 |
| C16 | `fetch.py:442` | `assets/domain-recipes.json` — 문서 4곳(SKILL.md:248 외)이 약속하는 영속 학습 파일이 **존재하지 않고 어떤 코드도 읽지 않는다**(grep 0건). `_tier_order` 는 하드코딩 `ROUTES` 만 참조 | 얇은 optional 로드 배선 |
| C17 | `tests:1557` | `survey_type_parity()` 가 5종 중 4종만 순회 — **비즈니스 모델 조사** 누락. BM 프리셋 축이 드리프트해도 72개 전부 그린 | 목록에 추가 |

## 반증되어 기각한 것 (1건)
- `merge_evidence()` 가 `independent_groups` 를 fact 에 영구반영하지 않음 → 재현은 됐으나
  **코드 주석에 명시된 의도적 설계**. 결함 아님.

---

# 2부 — 개선 (채택 4건)

스카우트 29에이전트가 24건을 제안, 심사관이 실재·중복·비용을 검증해 **4건만 통과**.
15건 기각(대부분 "이미 구현돼 있음" 또는 "URL 이 죽었음" 또는 "의존성 비용 > 값").

### I1. `assets/style.html` — `word-break: keep-all` (점수 85)
`body` 규칙에 `word-break` 지정이 **전혀 없어** 브라우저 기본값(음절 단위 강제 줄바꿈)이 그대로
적용된다. 한국어 납품물의 가장 흔한 조판 흠이고 표준 CSS 한 줄로 닫힌다.
`overflow-wrap: break-word` 동반(표 안 긴 URL 넘침 방지). 기존 `a { word-break: break-all }` 은 유지.

### I2. `assets/style.html` — `thead { display: table-header-group }` (점수 80)
현재 `table` 규칙에 페이지 분할 규칙이 0건. 근거표가 페이지 중간에서 헤더 없이 잘리면
**어느 열이 무슨 값인지 알아볼 수 없다** — 증빙형 보고서에서 치명적.
`tr { break-inside: avoid }` 동반. Chrome 은 이미 HARD 의존성이라 추가 설치 0.

### I3. `verify_facts.py` — `text_quote` verbatim ↔ 원문 스냅샷 대조 (점수 74)
현재 `verify_facts.py:483` 은 `verbatim` 이 **비어있지 않은지만** 본다. 그 인용문이 실제로
원문에 있는지는 아무도 대조하지 않는다 → **출처는 진짜인데 인용은 발명된** 상태가 통과한다.
`sha256` 결박(EV-1)으로도 못 잡는다(파일이 진짜여도 인용은 지어낼 수 있으므로).

`fetch.py:519-536` 의 `save()` 가 **이미** trafilatura 정제본 경로를 `clean` 키로 반환하는데
스키마·`facts_db` 어디에도 연결돼 있지 않다 — 죽은 의존성이 아니라 **절반짜리 배선**이다.
`difflib`(stdlib)로 부분/근사(90%) 일치 판정. **`[인용불일치]` WARN 티어로 먼저 배선**하고
오탐 관측 후 FAIL 승격 검토(기존 `[캡처약결박]` 선례 그대로).

### I4. `run_ledger.py` — `prev_hash` 해시체인 (점수 72)
지금 append-only 는 **이름만** append-only 다. 파일을 직접 열어 과거 BLOCK 판정을 지우거나
`answer` 레코드를 위조해도 검출 수단이 0이다. RFC6962(머클)는 이미 기각됐지만 단순 해시체인은
`hashlib` + 기존 `_canon_sha` 재사용으로 신규 의존성 0.
⚠ **레거시 레코드(prev_hash 필드 없음)는 체인 검사 생략**을 반드시 명시 — 빠뜨리면 기존 완료
조사폴더가 전부 오탐 BLOCK 된다.

## 유예 5건 (다음 배치)
`자체 SVG 차트 생성기`(58) · `curl_cffi impersonate 프로파일 갱신`(55) ·
`Chrome --dump-dom screen 오라클`(55) · `FILE_APPEND_DATA 원자적 어펜드`(55) ·
`urllib.robotparser`(42). 상세 근거는 스카우트 원본 참조.

---

# 실행 순서

파일 소유권을 나눠 병렬 편집한다(같은 파일을 두 에이전트가 만지지 않는다).
테스트 추가는 **배리어 이후 단일 에이전트**가 한다 — `test_adversarial.py` 는 공유 파일이다.

| 레인 | 소유 파일 | 항목 |
|---|---|---|
| L1 | `search.py`, `searx-instances.json` | C1 C2 C14 |
| L2 | `fetch.py` | C7 C15 C16 |
| L3 | `verify_facts.py`, `facts-schema.json` | C3 C8 C11 **I3** |
| L4 | `run_ledger.py`, `gates.json` | C4 C5 C10 C12 C13 **I4** |
| L5 | `manifest.py`, `skill_paths.py`, `facts_db.py`, `style.html` | C6 C9 **I1 I2** |
| L6 (배리어 후) | `tests/*`, `references/*` | C17 + 전 항목 회귀 케이스 + 문서 정합 |

## 완료 기준 (영수증)
1. `python tests/test_adversarial.py` — 기존 72건 전부 유지 + 신규 케이스 전건 검출
2. `python tests/test_run_ledger.py` — 기존 20건 유지 + 신규
3. `python tests/test_e2e.py` — PASS
4. `python scripts/preflight.py` — HARD 4/4
5. `python scripts/install.py --check` — 드리프트 0
6. 신규 pip 의존성 **0건** (스카우트 채택 4건 전부 stdlib/CSS)
