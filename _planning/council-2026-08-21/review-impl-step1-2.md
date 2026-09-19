# 구현 검토 보고서 — 카운슬 1·2단계 (fix/council-step1-2)

- 검토자: claude fable (읽기 전용). 기준: `plan-step1-2.md` §2 설계결정 D1~D5 · §3/§4 전후 코드 · §6 신규 테스트 9건 · §7 검증 명령.
- 검토 대상: `git log main..HEAD` — 계획된 6커밋(1713ed0 397819c e796d38 ca530b9 621cf81 d37816a) + **검토 도중 추가된 7번째 커밋 e1991a4**(docs, 23:00:21) 까지 포함. 변경 파일 9개(scripts 5 · tests 2 · assets 1 · references 1). 작업트리는 깨끗함(`git status` → `_planning/` 만 untracked).
- 검증 방법: 코드 diff 정독 + 내가 직접 실행(데모 7종·adversarial·E2E) + **main 을 `git worktree add --detach` 로 따로 체크아웃해 신규 테스트 9건을 변경 전 코드 위에서 실행** + 정규식 오탐 프로브 직접 실행. 모든 숫자는 이 세션 실측.

## 0. 실측 요약 (항목 4)

| 명령(HEAD, `PYTHONUTF8=1`) | 결과 |
|---|---|
| `scripts/{verify_facts,gates,facts_db,manifest,make_chart,harvest_images,skill_paths}.py demo` | **7/7 OK** (gates 는 `owned_gate_cli_blocked: true` 확인) |
| `tests/test_adversarial.py` | **68/68 검출 성공**, exit 0 (계획 §6 기대 60−0+8=68 과 일치) |
| `tests/test_e2e.py` | `E2E OK — facts=2 evidence=2 pdf=66609B pages=2 (자체 스택만, G3 PASS, 무결성 OK)`, exit 0 |
| `install.py` | 실행 안 함(금지) |

구현자 보고(68/68·E2E OK·demo 7/7)와 일치.

## 1. 계획 항목 (a)~(f) — 동작 기준 판정

| 항목 | 근거 | 판정 |
|---|---|---|
| **(c) `_images/**` 봉인** | `scripts/manifest.py:29` `("images", "_images/**/*")` 한 줄 추가. `_scan` 이 `root.glob` + `is_file` 이라 IMAGES.md·index.json 도 같이 봉인(계획 D 방침대로). `harvest_images demo` 무변경 통과 | **PASS** |
| **(a) 부록 검사(D1)** | `verify_facts.py:345` `check_bound_numbers(..., *, lenient_untagged=False, where="")` · `:806` `check_bound_numbers(_appendix, facts, lenient_untagged=True, where="부록 ")` · `used` 는 `:783` 본문 TAG 만(부록 태그 미포함 → 계획 "used 는 본문 태그만" 유지). `[무태그]` 만 `[부록무태그]` WARN, 오태그·미확정·값·단위는 `{loc}` 접두로 FAIL. 본문 메시지는 `'본문 '` 리터럴 그대로라 기존 테스트 문자열 매칭 유지 | **PASS** |
| **(b) 접두 통화·UNIT·한글 수사(D2·D3)** | `:82` `CUR_NUM` · `:86` `KO_NUMERAL` · `:94` `_WEAK_COUNT_UNITS` · `:100` `_plausible`(약한 단위 <100 배제) · `:192` `_KO_SCALE` · `:224` `_dims_compatible`(N↔통화 호환) · `:323` `_body_nums`(CUR 우선 + 겹침 제거) · 폴백/직접결박 두 곳 모두 `_dims_compatible` 로 교체. 계획서 코드와 문자 단위로 동일. **프로브 결과는 §1-b 표** | **PASS** |
| **(f) lead reread `reread_sha256`(D5)** | `facts_db.py:56` `_lead_reread_events` · `:83-87` validate 시 형식 항상 검사 · `:94` confirmed 는 'lead **reread**' 로 좁힘 · `:248-262` `add_verify_event(..., *, reread_sha256=None)` add 시점 거부 · 스키마 description 1줄. G3 WARN: `verify_facts.py:510` 시그니처 tuple 화, `:558-571` `[재열람미결박]`(sha256·verbatim `gates.sha256_text`·local `manifest.sha256_file` 대조, `used` 한정). 호출부 `ec_fail, ec_warn` 분리 | **PASS** |
| **(e) `[2]` 영수증 = 계산 + 투영 다이제스트 결박(D4)** | `facts_db.py:282` `confirmed_digest`(confirmed 행의 id·raw·unit·lead reread (at, sha) 만 — evidence_ids·claim-graph 제외 = 계획 "confirmed 투영" 정의와 동일) · `gates.py:201` `_check_reverification`(facts.jsonl 없으면 GateError, confirmed 전건 `validate_fact`, `facts_db_sha256`+`confirmed_digest_sha256`+`confirmed_count` 기록) · `:368` `record_manual("[2]")` 에서만 호출 · `:219` `_receipt_issues` 가 `successful_receipt(:243)`·`require_receipt(:258)` **2곳만** 교체, `check_gate` 의 자기영수증(:286)은 `_refs_from_record` 유지(계획의 "재기록 불가 교착" 회피). **G3 경로 실행 확인**: `verify_facts.py:930` `gates.check_gate(wp,"G3")` → `PREREQUISITES["G3"]=("G1","[2]")` → `require_receipt("[2]")` → `_receipt_issues` 다이제스트 재계산·대조. `receipt2_…` 테스트가 이 경로로 "재기록" 이슈를 실제 받음 | **PASS** |
| **(d) [Bx] ①② FAIL 승격 범위** | `verify_facts.py:497` `if fid in used and hard:` → FAIL, `:499 elif hard:` → WARN(본문 미사용), soft ③④ 는 항상 WARN. 조건 `risk=="high" and status=="confirmed"` 유지 → **disputed·pending 미적용, low/normal-risk 미적용, 부록(audit 전수표) 태그는 `used` 밖** → 새지 않음. `set(g for g in … if g)` 로 `["dart","dart"]`·빈 라벨 차단. 76건 주석 교체(§5) | **PASS** |
| **⑦ `references/verification-gates.md` 4줄** | 구현자는 "금지 파일" 이라 미적용 주장 → **오판**(계획 §1 "건드리는 파일" 목록과 §9 "허용된 문서 수정(4줄)" 에 명시). 검토 중 e1991a4 로 `:25-27` [Bx] 줄 1건만 반영됨. 남은 3줄: `:23`(lead reread `reread_sha256` 필수) · `:38-41` G3 줄(부록 무태그만 면제·접두 통화·계수 단위) · `:67-69`([2] 영수증 다이제스트 결박·대장 변경 시 재기록) | **FIX-1** |

### 1-b. (b) 정규식 오탐 프로브 — 내가 직접 실행 (`scratchpad/regex_probe.py`, 빈 대장에 `check_bound_numbers`)

계획서 §3(b-6) 회피 케이스 **전부 무매치**: `2024년` `2026-08-21` `12월` `p.45` `표 3`·`각주[12]` `| 3 | 건수 | 12월 건설 |` `2024 has grown` `2023 KT` `EUROPE 2024` `제25조` `3대 핵심 과제` `20~30대` `50대 여성` `3기 신도시` `6개월` `4개 축` `3부` `2025 원문` `제3기 위원회` `Top 5` `T+2` → 무태그 0.
검출 기대 13 + 통화 5 + 추가(`KRW 300조`·`£2.1bn`·`¥500억`·`$1,000`·`US$ 4.5bn`) **전부 검출**, 중복 매치 금지 5케이스 **정확히 1건**. 알려진 미검출(계획 명시) `CAD$240M`·`A$5bn`·`99대` 그대로 미검출.
`_resolve_unit`: `USD_million`→(USD,1e6) · `백만 EUR`→(EUR,1e6) · `십억 USD`→(USD,1e9) · `Mt`→(TON,1e6) · `개`→(개사,1) 정상.

## 2. 신규 테스트 9건 — 변경 전(main) 에서 FAIL 하는가 (항목 2)

방법: `git worktree add --detach <scratch>/wt-main main` → main 의 `scripts/` 와 main 의 `test_adversarial.py` 헬퍼(`_base_db`·`_confirm`·`_H`) 위에 HEAD 의 테스트 함수 소스만 AST 로 옮겨 실행. `add_verify_event` 는 **`reread_sha256` kwarg 를 받아 저장만 하도록 shim** 해서 "kwarg 부재 TypeError" 가 아니라 **검증 부재 자체**로 FAIL 하는지 봤다. 워크트리는 검토 후 `git worktree remove` 로 제거.

| 테스트 (HEAD 줄) | main 결과 | FAIL 이유(=구멍을 잡는 단언) | 판정 |
|---|---|---|---|
| `manifest_image_swap` :710 | FAIL | `TRACKED` 에 `_images/` 없음 | PASS |
| `appendix_value_mismatch_fails` :631 | FAIL | 부록 `999조원(F001)` 이 `ok: True` 로 통과 | PASS |
| `currency_prefix_untagged_and_mistagged` :540 | FAIL | `$4.5B` 무태그 0건 | PASS |
| `count_units_are_claims` :571 | FAIL | `4,500명` 무태그 0건 | PASS |
| `korean_numeral_warned` :595 | FAIL | `[한글수사]` WARN 없음 | PASS |
| `claim_graph_high_risk_used_fails` :1129 | FAIL | ①② 결핍이 `ok: True`(WARN 만) | PASS |
| `receipt2_requires_lead_reread_and_binds_digest` :1390 | FAIL | "lead 이벤트 없는 confirmed 가 [2] 를 통과" | PASS |
| `lead_event_requires_reread_sha256` :923 | FAIL | "reread_sha256=None 가 통과됨" | PASS |
| `reread_sha_unbound_warned` :952 | FAIL | `[재열람미결박]` WARN 없음 | PASS |
| (개정) `numeral_and_energy_units_untagged` :528 | PASS-on-main | 기존 검출 유지 + 긍정형 짝 2줄 삭제뿐 — 예상대로 | — |

9/9 모두 기능 부재 이유로 FAIL → 구멍을 잡는 테스트다.

## 3. 기존 테스트·E2E·데모 수정 — 계획 예고 범위 대조 (항목 3)

| 구분 | 계획 예고 | 실제 diff | 판정 |
|---|---|---|---|
| `add_verify_event(..., reread_sha256=_H)` 추가 | `:166,219,262,438(_confirm),677,693,710,743,791` 9곳 | `mistagged_value`·`high_risk_without_capture`·`failed_capture_claimed_as_evidence`·`_confirm`·`fake_evidence_hash`×3·`capture_outside_workdir`·`status_regrade_blocked` = **9곳 정확히** | PASS |
| `_confirm` 에 high-risk ①② 기본값 | §4(d) 코드 | `setdefault` 두 줄 + `_write_jsonl_atomic`, 계획 코드와 동일 | PASS |
| `numeral_and_energy_units_untagged` 긍정형 짝 2줄 삭제 + docstring | §3(b-7) | 동일 | PASS (약화 아님 — 긍정형 짝은 `count_units_are_claims` 로 이관돼 더 넓게 고정) |
| `claim_graph_fields_warned` → `claim_graph_high_risk_used_fails` 교체 | §4(d) | 동일(이름·단언 5단계) | PASS |
| E2E `:83` `reread_sha256=sha256("e2e-"+fid)` | 1곳 | 동일(evidence sha 와 같아 WARN 0) | PASS |
| 데모 4곳 | verify_facts(reread 2곳 + 부록 단언 뒤집기 + 긍정형 짝) · facts_db(reread 2곳 + 부정형 1줄) · make_chart(`"0"*64`) · gates(`wp.facts.write_text("")`) | 전부 계획 코드와 동일 | PASS |
| 예고 밖 수정 | — | **없음**. 테스트를 약화시켜 통과시킨 곳 없음 | PASS |

## 4. 회귀·커밋 (항목 5)

- §5 실전 폴더 함의: 마이그레이션 스크립트 없음(계획대로), 76건 주석 → (d) 문구로 교체됨(`verify_facts.py:480-485`). 실전 research 폴더 무수정(`git status` 깨끗, 폴더는 저장소 밖).
- 커밋: 6개가 계획 ①~⑥ 순서·단위와 일치, `fix(mdr/<모듈>): …` 접두는 main 관행(`fix(mdr/figures):`) 과 같음. `Co-Authored-By: grok-4.6 <noreply@x.ai>` 형식 적합. **단 본문(body)이 비어 있다** — main 의 최근 커밋(46bae09·058b669)은 "무엇을·왜" 본문을 길게 남기는 관행. 비차단 관찰(O-5).
- `check_evidence_chain` 반환형 변경(list → tuple)의 호출자는 `verify()` 1곳뿐(grep 확인) → 깨진 호출 없음.
- `gates.py` 가 `facts_db` 를 import 하게 됐으나 `facts_db` 는 `skill_paths` 만 import → 순환 없음(데모·테스트 통과로도 확인).

## 5. 비차단 관찰 (FIX 아님 — 다음 PR 후보, 전부 계획서 자체의 설계 그대로 구현된 것)

- **O-1 `KO_NUMERAL` 일반 한국어 오탐(WARN 만)**: 프로브에서 `사건·일대·십대·사기·일기·일명·사명·구명·일원·사대·이명` 이 `[한글수사]` WARN 으로 뜸(`삼성전자·일부` 는 정상 회피). ok 판정엔 무영향이나 실전 보고서에서 경고 소음. 권고: 단위가 `건|명|기|대|배|톤` 일 때는 `[만억조]` 배수어를 필수로, `원|달러|퍼센트|%` 만 배수어 없이 허용(`삼백조원`·`오천억원`·`이십 퍼센트` 유지, 위 오탐 중 `일원` 만 잔존).
- **O-2 통화 종류 불일치는 사실 잡힌다**: `€120M(F002)` vs 대장 `USD_million` → `[단위불일치] 차원=EUR ≠ USD` FAIL(프로브 §F). 양쪽 다 통화 차원이 명시되면 `_dims_compatible` 이 False 라 **계획 D2·`_dims_compatible` docstring 의 "통화 종류($ vs €) 불일치는 안 잡음" 주석이 실제보다 보수적**. 동작은 옳은 방향(한 쪽이 bare `N` 일 때만 호환). 주석 1줄 정정감.
- **O-3 `CUR_NUM` group(0) 뒤 공백**: 배수어가 없으면 `\s*` 가 꼬리 공백을 삼켜 메시지가 `'$1,000 '` 로 찍힘. `$5 Mt` 는 `$5`(USD) 로 잡히고 `5 Mt` 는 겹침 제거됨(경계 케이스, 실전 표기 아님). 정규식 `(?:\s*(bn|…))?` 로 묶으면 해소. 결박(`_bind_pairs`)엔 영향 없음(`$120M(F002)` ok 실측).
- **O-4 `_KO_SCALE` 의 `"천"` 부분문자열**: 대장 unit 에 `천` 이 들어가면(`천만원`·`천억원`) 1e3 으로만 읽음. 변경 전에는 `(None,1)` 로 `[단위미상]`+값 대조라 어차피 FAIL 이었으므로 **회귀 아님**. 실전 대장 unit 실측(`%·건·MW·USD·EUR·백만 EUR·십억 USD·Mt·개·배`)에는 없음. 토큰 단위 매칭으로 바꾸면 깔끔.
- **O-5 커밋 본문 공백** (위 §4). 다음 PR 부터 "왜" 한두 문단 권고.
- **O-6 e1991a4 의 들여쓰기**: `verification-gates.md:27-28` 새 줄이 `   ④`(공백 3) 로 기존 목록(공백 2)과 어긋남 — FIX-1 반영 때 같이 맞추면 됨.

## 6. 문서 후속 — 다음 PR 용 (항목 6, 계획 §9 기준으로 현황 확인)

이번 배치 금지 파일(SKILL.md·README.md)에 아래가 **아직 구버전**임을 이 세션에서 확인했다:

| 파일:줄 | 현재 문구 | 바꿔야 할 내용 |
|---|---|---|
| `SKILL.md:46` | `[2] 팀리드 재검증 ─ ★전건 원문 재열람 → verify_event(by=lead)` | `verify_event(by=lead, reread_sha256=<재열람 원문 해시>)` |
| `SKILL.md:47` | `[Bx] … 독립그룹·반박검색·기본소스·시간증거` | "①독립그룹≥2·②반박검색은 **본문 사용 시 G3 FAIL**, ③④ WARN" |
| `SKILL.md:98-104` [2] 절 | `db.add_verify_event(by="lead")` · "영수증: `gates.py record [2]` 로 기록" | `add_verify_event(by="lead", action="reread", reread_sha256=fetch.py get 의 sha256 / 로컬 PDF 해시 / WebFetch verbatim 의 sha256_text)` · "`record [2]` 는 confirmed 전건 lead reread 검사 후에만 기록되고 `confirmed_digest_sha256` 에 결박 — 이후 confirmed 집합/값이 바뀌면 G3 선행검사에서 '재기록' 요구" |
| `SKILL.md:109-111` [Bx] 통과조건 | 네 요건 나열만 | FAIL/WARN 구분 + "본문 미사용 high-risk 는 WARN" |
| `SKILL.md:131-135` G3 설명 | 부록 검사 언급 없음, 통화 접두·계수 단위 없음 | "부록은 무태그만 면제(→`[부록무태그]` WARN), 오태그·미확정·값·단위는 본문과 동일 FAIL" · "`$4.5B`·`US$175M`·`€120M`·`₩300조` 접두 통화, `건·명·개사·기·위·배·대` 계수 단위도 사실주장" · "`[재열람미결박]`·`[한글수사]` WARN" |
| `SKILL.md:157` 영수증 커버리지 | `[2]` 수동 기록 | "`[2]` 는 수동이되 대장 계산 결과(confirmed_count·digest)를 영수증에 기록" |
| `README.md`(저장소 루트) G3 설명·영수증 표·"검증 현황 60/60" | 구버전 | 부록 무태그만 면제 · `[2]` 다이제스트 결박 · **68/68** |
| `references/verification-gates.md:23,38-41,67-69` | 구버전 | **이번 배치 FIX-1 로 반영**(아래) |
| `verify_facts.py:1-25` 모듈 docstring | 이미 갱신됨(부록·접두 통화·[Bx]·재열람미결박) | — 완료 |

## 판정

**판정: FIX(1건 — 문서 3줄, 코드 변경 없음. 반영 즉시 MERGE-READY)**

### FIX-1 → grok 에게 줄 지시 (파일 1개, 코드 무변경)

`codes/market-deep-research/references/verification-gates.md` — 계획서 §9 "이번 배치에서 허용된 문서 수정(4줄)" 중 남은 3줄. 이 파일은 계획서 §1 "건드리는 파일" 목록에 있고 금지 목록(`install.py` 실행·`README.md`·`SKILL.md`·실전 research 폴더)에 **없다**. 팀리드가 런타임에 읽는 규칙 문서라, 지금 상태면 리드가 `add_verify_event(by="lead")` 를 해시 없이 호출해 `ValidationError` 를 맞는다.

1. `:23` `→ \`add_verify_event(by="lead")\`.` 를 → `` → `add_verify_event(by="lead", action="reread", reread_sha256=<재열람 원문 SHA-256: fetch.py get 의 sha256 / 로컬 PDF 파일 해시 / WebFetch verbatim 의 sha256_text>)` — 해시 없는 lead reread 는 add·validate 모두 거부. `` 로 교체(한 줄, 길면 다음 줄 2칸 들여쓰기로 이어 쓴다).
2. `:38-41` G3 문단의 `무태그 숫자 차단 ·` 뒤에 한 줄: `부록은 [무태그] 만 면제(→ [부록무태그] WARN)하고 오태그·미확정·값·단위는 본문과 동일 FAIL · 접두 통화($4.5B·US$175M·€120M·₩300조)·계수 단위(건·명·개사·기·위·배·대, 숫자에 붙을 때만)도 사실주장 ·`.
3. `:67-69` 영수증 커버리지 문단 끝에 한 문장: `[2] 영수증은 record 시점에 confirmed 전건 lead reread(+reread_sha256) 를 검사해 confirmed 투영 다이제스트(id·raw·unit·lead reread 이벤트)를 기록하며, 이후 confirmed 집합·값이 바뀌면 G3 선행검사가 "재검증 후 record [2] 재기록" 을 요구한다(G2 의 evidence 추가는 무효화하지 않음).`
4. 같은 김에 e1991a4 가 넣은 `:27-28` 두 줄의 들여쓰기를 공백 3 → 2 로 맞춘다(O-6).
5. 커밋 메시지: `docs(mdr/gates): [2] reread_sha256 필수·부록/접두통화 검사·[2] 다이제스트 결박을 verification-gates 에 명시` + 본문 2~3줄(왜: 리드 런타임 규칙 문서가 코드보다 뒤처지면 ValidationError 를 맞는다).

그 외 코드·테스트·데모는 계획서와 문자 단위로 일치하고, 내가 직접 돌린 demo 7/7·adversarial 68/68·E2E OK, 신규 9건의 변경 전 FAIL 까지 확인됐다. O-1~O-5 는 비차단 관찰로 다음 PR 에서 다루면 된다.
