# market-deep-research

**증빙형(evidence-based) 시장조사 보고서 스킬 제작 워크스페이스** — Claude Code 스킬 `market-deep-research`의 소스 저장소이자, 이 스킬로 생산한 실제 조사 산출물의 보관소입니다.

이 스킬은 "AI의 확률적 답변 때문에 조사할 때마다 수치가 달라지는 문제"를 해결하기 위해 만들어졌습니다. 모든 수치·주장을 **[사실(fact) → 출처(source) → 화면캡처(capture)]** 증거 체인으로 결박하고, 11개 검증 게이트를 통과한 것만 보고서에 실리는 팩트시트 PDF 생성 파이프라인입니다.

```
저장소 = codes/market-deep-research/   ← 스킬 본체 (정본, single source of truth)
       + _planning/                    ← 설계 문서 (v2 계획, gajae-code 흡수 맵 등)
       + research_*/                   ← 실제 조사 산출물 (예: 글로벌 PEM 수전해 조사)
       + HANDOFF.md                    ← 초기 세션 인수인계 문서
```

---

## 왜 만들었나

일반적인 AI 딥리서치는 같은 질문을 두 번 물으면 다른 숫자를 내놓습니다. 근거 링크가 있어도 클릭해 보면 그 숫자가 없는 경우도 흔합니다. 이 스킬은 그 문제를 **구조로** 막습니다:

1. **원문 미확인 수치는 폐기** — 추정 금지. 출처 없는 주장은 사실대장(facts.jsonl)에 등재 자체가 불가하며, 등재되지 않은 것은 보고서 본문에 쓸 수 없습니다.
2. **팀리드 전건 재검증** — 병렬 조사원(서브에이전트)이 수집한 모든 fact를 팀리드(메인 세션)가 **원문을 직접 다시 열람**해 인용문(verbatim)과 위치(locator)를 대조한 뒤에만 confirmed 처리합니다. 조사원 단독 확정은 금지.
3. **고객용 / 내부 audit 분리** — 고객 PDF에는 검증 통과분만 싣고, 폐기 목록·실패 URL·반박 상세·검증 이력은 내부 audit 번들에 전량 보존합니다.

검증에 불통과한 모순은 침묵 폐기하지 않고 `disputed`로 남깁니다 — **"기권이 정답"** 인 상태를 인정하는 것도 설계의 일부입니다.

---

## 파이프라인 (게이트 11종)

게이트 정의의 정본은 `assets/gates.json`이며, 통과 주장은 전부 `scripts/run_ledger.py`의 append-only 영수증(run-ledger.jsonl)으로만 성립합니다.

```
[G0]   preflight ─ 의존성 점검 + 규모판정 + 심층 인터뷰(13필드 브리프)
[PLAN] 계획 합의 ─ 조사질문을 claim 스키마(반례 선설계)로 → 2레인 적대 리뷰 → 사용자 consent
[1]    병렬 조사 ─ 레인별 워커 팬아웃 (역할 로스터 4종: collector·counter-searcher·specialist·verifier)
[E]    확장→수렴 ─ 리드가 dedup 후 후속 워커 반복 스폰
[G1]   join      ─ raw 보존·RECEIPT sha 대조·스키마 검증 등재·무출처 즉시 폐기
[LV]   팀리드 재검증 ─ ★ 전건 원문 재열람 (verify_event by=lead)      ┐
[BX]   반박·claim-graph ─ 독립 출처그룹·반례쿼리 소진·시간 증거      ┼ 동결 코호트 3레인
[정합]  단위·연도·정의·entity_id 스윕                                 ┘
[G2]   증빙 게이트 ─ confirmed 전건 화면캡처(핵심 수치 필수), 전폭 크롭 원칙
[3]    보고서 작성 ─ 고객 report.md(11부 표준목차) + 내부 audit 번들 동시 생성
[G3]   verify_facts + manifest ─ 실패 0 강제: 수치↔F태그 결박·단위 대조·금지패턴·SHA-256 봉인
[G5c]  실행코드 검증 ─ 계산형(calculation/derivation=computed) fact 를 스크립트로 실증
[4]    render_pdf ─ pandoc → Headless Chrome, 오프라인 PDF + manifest 재봉인
[G4]   preview   ─ 페이지 이미지 육안 검사 + intent-diff 축별 대조
[G5]   최종 무결성 ─ PDF F태그·링크·캡처 수 재검사 + run-receipt 발행
```

**완료 선언 = 영수증**: "보고서 완성"이라는 말은 `run_ledger.py status`가 11개 게이트 전부 신선(fresh) PASS/WATCH(BLOCK 0)를 출력할 때만 성립합니다. *"진행 기억·산문 선언은 증거가 아니다."* 나아가 confirmed인데 증거가 없거나 스키마를 위반한 fact가 있으면 팀리드가 PASS를 요청해도 기계가 BLOCK을 강제합니다(기계 하한).

## 조사 유형 5종

| 유형 | 요지 |
|---|---|
| 기술동향 | 특정 기술의 성숙도·플레이어·로드맵 |
| 산업동향 | 시장 규모·성장률·밸류체인·정책 |
| 기관·기업 실사 | 대상 동일성(entity identity) 확정 후 실적·딜·평판 |
| 기술사업화 실사 | 기술→사업 전환 가능성·선행사례 |
| 비즈니스 모델 조사 | BM 렌즈 L1~L9 적용, `bm-summary.md`(2~3쪽 이식용 요약) 추가 산출 |

BM 렌즈(`references/business-frameworks.md`): L1 BMC 9블록 · L2 가치제안(JTBD) · L3 수익모델 9유형 · L4 가격 구조 · L5 방어력 · L6 red-team 부하가정 공격 · L7 경쟁사 격차표 · L8 선행사례 벤치마크 · L9 시장규모·밸류체인.

## 수집 스택 (유료 API 무의존)

firecrawl/tavily 같은 유료 API 없이 동작하는 자체 수집 스택이 코어입니다.

- **검색** (`scripts/search.py`): DuckDuckGo HTML → SearXNG 공개 인스턴스 로테이션 → 전문 무료 API(arXiv·SEC EDGAR·Wikipedia). 내장 WebSearch와 병행.
- **fetch** (`scripts/fetch.py`): 강방어 사이트 우회 사다리 내장 — 도메인 라우팅 → curl_cffi TLS 지문 그리드 → **모바일 iOS 지문**(실전 핵심: Cloudflare 403 통과 실측) → Jina Reader → Googlebot UA → RSS → Wayback → OGP. 성공 판정은 HTTP 200이 아니라 4계층 본문 검증. 원본(raw)+정제본을 SHA-256과 함께 보존. 로그인·CAPTCHA·paywall 우회는 하지 않습니다.

## 저장소 구조

```
codes/market-deep-research/
├─ SKILL.md                  # 오케스트레이터 본체 (파이프라인·운영 계약·3대 절대 규칙)
├─ assets/
│  ├─ gates.json             # 게이트 11종 enum 정본
│  ├─ facts-schema.json      # fact + evidence[] 스키마
│  └─ style.html …           # PDF 스타일, 큐레이션 소스, SearXNG 인스턴스
├─ references/               # 단계별 규정 문서 10종
│  ├─ research-plan.md       #   G0 인터뷰·계획 확정 게이트
│  ├─ agent-briefs.md        #   워커 스폰 계약·역할 로스터·반환 마커
│  ├─ verification-gates.md  #   게이트 상세·4차원 출처등급·완료 선언 규칙
│  ├─ report-format.md       #   고객 PDF 11부 표준목차·산출물 규약
│  ├─ source-ladder.md       #   검색·fetch 사다리·WAF 정찰·research-memory
│  ├─ evidence-capture.md    #   캡처 규율 (source_capture vs reconstructed)
│  ├─ entity-identity.md     #   조사 대상 동일성 확정·대상 스펙
│  ├─ extract-recipes.md     #   증거유형 6종 추출·locator 규칙
│  ├─ business-frameworks.md #   BM 렌즈 L1~L9
│  └─ image-research.md      #   대표 도판 수확 규율
├─ scripts/                  # 실행 도구 12종
│  ├─ run_ledger.py          #   게이트 영수증 상태머신 (신선도·기계 하한)
│  ├─ verify_facts.py        #   G3 기계 검증 (실패 0 강제)
│  ├─ facts_db.py            #   사실대장 원자적 read/append + claim_key
│  ├─ fetch.py · search.py   #   수집 스택
│  ├─ capture_pdf.py · capture_web.py · harvest_images.py   # 증빙 캡처·도판
│  ├─ render_pdf.py · manifest.py · preview_pdf.py          # 렌더·봉인·프리뷰
│  └─ preflight.py · install.py · skill_paths.py            # 점검·설치·경로
└─ tests/
   ├─ test_adversarial.py    # 적대 케이스 59종 — 조작·오류를 "실패로 검출"해야 성공
   ├─ test_run_ledger.py     # 영수증 상태머신 13케이스
   └─ test_e2e.py            # 증거→대장→보고서→PDF→무결성 전 구간 1시나리오

_planning/                   # 설계 문서 (plan-v2, gajae-absorption-map, codex-review …)
research_글로벌_PEM_수전해_프로젝트_20260721/   # 실증 조사 산출물 (report + audit 전체)
```

## 조사 1건의 산출물

```
research_<주제>_<YYYYMMDD>/
├─ report.pdf            # 고객용 팩트시트 (11부 표준목차, 수치마다 [F###] 태그)
├─ report.md             # 생성 소스 (직접 수정 금지 — facts.jsonl 수정 후 재렌더)
├─ bm-summary.md         # BM 조사 유형만: 문서 이식용 2~3쪽 요약
├─ _captures/            # fact별 원문 화면캡처 (E###.png + 메타 json)
└─ audit/                # 내부 전용: facts.jsonl·run-ledger.jsonl·폐기 목록·
                         # 실패 소스·검증 이력·raw 워커 출력·manifest(SHA-256)·품질 메트릭
```

**단일 진실원은 facts.jsonl**입니다. 보고서는 생성물이므로 본문 수치를 직접 고치는 행위는 금지되며, 대장을 고치고 재렌더해야 합니다 — G3/G5 게이트가 이 동기화를 기계로 강제합니다.

## 설치·실행

```bash
# 의존성 점검 (HARD: python>=3.10, PyMuPDF, pandoc, chrome / SOFT: curl_cffi, trafilatura …)
python codes/market-deep-research/scripts/preflight.py

# ~/.claude/skills/market-deep-research/ 로 설치 (SHA-256 해시 검증 복사)
# ⚠ mirror-sync 방식: 인자 없이 즉시 실행되며, 대상 폴더의 초과 파일을 삭제합니다
python codes/market-deep-research/scripts/install.py
```

설치 후 Claude Code에서 "증빙/캡처 포함 시장조사 보고서", "BM 보고서", "근거 있는 딥리서치 PDF" 류의 요청이 이 스킬로 라우팅됩니다. **이 스킬의 정본은 이 저장소입니다** — 설치본을 직접 수정하지 말고, 저장소를 수정한 뒤 install.py로 반영합니다.

## 방법론 계보

| 단계 | 내용 | PR |
|---|---|---|
| v1~v2 | 스킬 신규 빌드 + PEM 수전해 조사로 실증 | [#3](https://github.com/bbiyakfather/market-deep-research/pull/3) (merged) |
| 검증 게이트 1차 배치 | 적대 감사로 찾은 취약점 35/37 보수 + 조사계획·목차 게이트 강화 | [#5](https://github.com/bbiyakfather/market-deep-research/pull/5) (draft) |
| **v4: gajae-code 흡수** | 코딩 에이전트 하네스 [gajae-code](https://github.com/Yeachan-Heo/gajae-code)의 운영 규율을 조사 도메인으로 이식 — 12개 흡수 패키지(【v4-*】 태그) | [#6](https://github.com/bbiyakfather/market-deep-research/pull/6) (draft) |

v4에서 이식된 핵심 메커니즘: **게이트 영수증 상태머신**(완료 선언=신선 영수증, fact 단위 content-hash 신선도, 기계 하한) · **G0 심층 인터뷰 규율**(라운드당 1질문·restate·승인 3단) · **계획 claim 스키마**(반례 선설계) · **2레인 적대 계획 리뷰** · **레인 섹션 워커 계약**(RECEIPT/BLOCKERS) · **동결 코호트 3레인 검증 + 델타 라체트** · **asks 프로토콜**(활성 ask 1개·멱등) · **research-memory**(도메인 수집 레시피). 설계 근거와 28건 리뷰 처분표는 `_planning/gajae-absorption-map.md` 참고.

브랜치 체인: `main` ← `worktree-mdr-fix-batch1`(PR #5) ← `feat/gajae-absorption`(PR #6). **최신 개발 헤드는 `feat/gajae-absorption`** 이며, 라이브 설치본은 이 브랜치와 동기화되어 있습니다.

## 검증 현황

- 적대 스위트 59/59 통과 — 조작된 대장·위조 캡처·무출처 주장을 "실패로 검출"하는 것이 성공 조건
- 게이트 영수증 상태머신 13/13 통과
- E2E 1시나리오(증거 수집→캡처→대장→보고서→G3→PDF→preview→무결성) 통과
