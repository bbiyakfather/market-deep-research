# market-deep-research

**증빙형(evidence-based) 시장조사 보고서 스킬** — Claude Code 스킬 `market-deep-research`의 정본 저장소입니다.

이 스킬은 "AI의 확률적 답변 때문에 조사할 때마다 수치가 달라지는 문제"를 해결하기 위해 만들어졌습니다. 모든 수치·주장을 **[사실(fact) → 출처(source) → 화면캡처(capture)]** 증거 체인으로 결박하고, 게이트를 통과한 것만 보고서에 실리는 팩트시트 PDF 생성 파이프라인입니다.

```
codes/market-deep-research/   ← 스킬 본체 (정본, single source of truth)
_planning/                    ← 설계·운영 기록
lessons.md                    ← 실전에서 얻은 교훈 누적
```

조사 실행 산출물(`research_*/`)은 저장소에 커밋하지 않습니다(`.gitignore`).

---

## 왜 만들었나

일반적인 AI 딥리서치는 같은 질문을 두 번 물으면 다른 숫자를 내놓습니다. 근거 링크가 있어도 클릭해 보면 그 숫자가 없는 경우도 흔합니다. 이 스킬은 그 문제를 **구조로** 막습니다.

1. **원문 미확인 수치는 폐기** — 추정 금지. 출처 없는 주장은 사실대장(`facts.jsonl`)에 등재 자체가 불가하며, 등재되지 않은 것은 본문에 쓸 수 없습니다.
2. **팀리드 전건 재검증** — 병렬 조사원(서브에이전트)이 수집한 모든 fact를 팀리드(메인 세션)가 **원문을 직접 다시 열람**해 인용문(verbatim)과 위치(locator)를 대조한 뒤에만 confirmed 처리합니다. 조사원 단독 확정은 금지.
3. **고객용 / 내부 audit 분리** — 고객 PDF에는 검증 통과분만 싣고, 폐기 목록·실패 URL·반박 상세·검증 이력은 내부 audit 번들에 전량 보존합니다.

검증에 불통과한 모순은 침묵 폐기하지 않고 `disputed`로 남깁니다 — **"기권이 정답"** 인 상태를 인정하는 것도 설계의 일부입니다.

---

## 파이프라인

```
[G0]  preflight ─ 의존성 점검 + 요구사항·승인 목차 확정 + intent-diff 개시
[1]   병렬 조사 ─ 조사원 에이전트 팬아웃(sonnet, 에이전트별 임시폴더, 읽기전용)
[E]   확장→수렴 ─ EXPAND 리드 dedup → 후속 워커 → 축별 잔여 리드 0까지 반복
[G1]  join      ─ raw 보존 · 스키마 검증 등재 · 무출처 즉시 discarded
[2]   팀리드 재검증 ─ ★전건 원문 재열람 → verify_event(by=lead)
[Bx]  반박·claim-graph ─ high-risk: 독립 관찰그룹 2+ · 반박검색 · 기본소스 · 시간증거
[G2]  증빙 게이트 ─ confirmed 전건 source_capture(핵심수치 필수)
[3]   보고서 작성 ─ 고객 report.md(11부 표준목차) + 내부 audit 번들
[G3]  verify_facts + manifest ─ 실패 0 · 무태그 수치 차단 · 도판검사 · SHA-256 봉인
[G5c] 실행코드 검증 ─ 계산·상충 주장을 스크립트로 실증(CONFIRMED/REFUTED)
[4]   render_pdf ─ pandoc → Headless Chrome, 오프라인 PDF
[4b]  재봉인    ─ manifest 재빌드(렌더 산출물 해시 추가)
[G4]  preview   ─ 팀리드 육안 검증 + intent-diff 축별 대조
[G5]  최종 무결성 ─ PDF F태그·링크·캡처 수 재검사 + manifest verify
```

### 게이트 영수증 (`audit/gates.jsonl`)

통과 주장은 append-only 영수증으로만 성립합니다. 핵심은 **누가 기록할 수 있는가**입니다.

| 구분 | 게이트 | 기록 주체 |
|---|---|---|
| 수동 | G0 · [2] · G4 | 팀리드가 `gates.py record` (사람의 판단이 필요한 게이트) |
| **소유 스크립트 자기기록** | G3 · [4b] · G5 | `verify_facts.py` · `render_pdf.py` · `manifest.py verify` — **CLI 손기록 차단** |
| 무소유 | G1 · G5c 등 | `gates.py record_script_result` |

G3·[4b]·G5는 손으로 기록할 수 없습니다. 소유 스크립트를 **실제로 돌린 영수증**과 안 돌리고 적은 영수증을 구별할 수 없다면, 그 영수증은 영수증이 아니기 때문입니다. 실패도 기록됩니다 — PASS만 남기면 실패 이력이 원장에서 사라집니다.

G2·G5c는 원장이 아니라 **내용검사**로 강제됩니다(G2=캡처 실재 검사, G5c=`audit/verify-<slug>.md` 산출물).

---

## 도판 하네스 — 찾은 도판이 그린 도판보다 낫다

좋은 인포그래픽(IEA·DOE·EC 정책지도·밸류체인 도해)은 **이미 소스 보고서 안에 있습니다.** 우리가 그릴 것이 아니라 찾아서 출처와 함께 결박하는 것이 정공법입니다.

**확보 우선순위**

```
0. 워커 ## FIGURES 신고분   ← 원문을 직접 읽은 조사원이 지목한 도판. 가장 정확하다.
1. 소스 PDF 도판 크롭       ← 인포그래픽 점수 랭킹(명시캡션·면적·벡터밀도 ↑ / 반복 로고 ↓)
2. 확보한 웹페이지 이미지    ← og:image · figure/figcaption
3. 이미지 검색             ← 기관 도메인 직격(--sites) + openverse·commons
4. 자작 차트(최후 수단)      ← make_chart.py
```

0번이 핵심입니다. 조사원 워커는 원문을 읽는 **유일한 존재**인데, 반환 마커에 도판 항목이 없으면 그 지식이 버려지고 팀리드가 처음부터 다시 탐색하게 됩니다.

**G3 도판검사** — 수치에 적용되는 증빙 철칙이 그림에도 같은 강도로 걸립니다.

| 검사 | 조건 |
|---|---|
| `[도판]` | 본문 대표 이미지 0장 차단 |
| `[도판경로]` | 참조 경로 실재 — 건별 판정(한 장이라도 깨지면 FAIL) |
| `[도판출처]` | 참조 뒤 2줄 이내 `[그림]` 캡션 + `출처:` **값**(라벨만 있고 비면 불인정) |
| `[도판무결박]` | `assets/` 자작 차트는 캡션에 `(Fxxx)` 최소 1개 |
| `[도판커버리지]` | 3부 축 챕터별 도판 유무 — 경고(외부 자료 가용성에 달린 조건이라 FAIL 아님) |

`_captures/` 증빙캡처는 G2 소관이라 이 검사 대상이 아닙니다.

**`make_chart.py`는 값을 CLI로 받지 않습니다.** `facts.jsonl`의 confirmed fact에서만 읽습니다 — 임의 숫자를 그려 F태그 없는 차트가 본문에 들어가는 경로를 설계로 막은 것입니다. 새 의존성 없이 표준 라이브러리로 SVG를 생성하며, 렌더 경로(`pandoc → Chrome`)가 그대로 그립니다.

---

## 조사 유형 4종

축(조사질문 = 에이전트 분할 = 3부 챕터)은 `references/report-format.md`의 축 프리셋이 단일 진실원입니다.

| 유형 | 3부 축 |
|---|---|
| 기술동향 | 기술요소 / 플레이어 / 시장 / 정책 |
| 산업동향 | 밸류체인 / 통계(KOSIS·DART·KIPRIS) / 해외 |
| 기관·기업 실사 | 일반현황 / 사업현황 / 재무실적 (entity-identity 선고정) |
| 기술사업화 실사 | 기술성 / 권리성 / 시장성 / 사업성 |

---

## 수집 스택 (유료 API 무의존)

firecrawl/tavily 같은 유료 API 없이 동작하는 자체 수집 스택이 코어입니다.

- **검색** (`scripts/search.py`): DuckDuckGo HTML → SearXNG 공개 인스턴스 로테이션 → 전문 무료 API(arXiv·SEC EDGAR·Wikipedia). 내장 WebSearch와 병행.
- **fetch** (`scripts/fetch.py`): 강방어 사이트 우회 사다리 내장 — 도메인 라우팅 → curl_cffi TLS 지문 그리드 → **모바일 iOS 지문** → Jina Reader → Googlebot UA → RSS → Wayback → OGP. 성공 판정은 HTTP 200이 아니라 본문 검증. 원본(raw)+정제본을 SHA-256과 함께 보존.

모바일 계층이 실전 핵심입니다 — Cloudflare 403이 데스크톱 지문 3종을 다 막아도 iOS 지문으로 통과한 사례가 실측됐습니다(2026-07-31, grandviewresearch.com).

로그인·CAPTCHA·paywall 우회는 하지 않습니다.

---

## 저장소 구조

```
codes/market-deep-research/
├─ SKILL.md                  # 오케스트레이터 본체 (파이프라인·3대 절대 규칙)
├─ assets/
│  ├─ facts-schema.json      #   fact + evidence[] 스키마
│  ├─ curated-sources.json   #   기관 도메인·Phase0 API 목록
│  ├─ searx-instances.json   #   SearXNG 인스턴스 풀
│  └─ style.html             #   PDF 스타일
├─ references/               # 단계별 규정 문서 9종
│  ├─ research-plan.md       #   G0 계획 확정(축·충분조건·깊이캡·승인 목차)
│  ├─ agent-briefs.md        #   워커 계약·반환 마커(JSONL/CLAIMS/EXPAND/FIGURES/인사이트)
│  ├─ verification-gates.md  #   게이트 상세·4차원 출처등급·claim-graph
│  ├─ report-format.md       #   11부 표준목차·축 프리셋·audit 양식
│  ├─ source-ladder.md       #   검색·fetch 사다리·WAF 정찰
│  ├─ evidence-capture.md    #   캡처 규율(source_capture vs reconstructed)
│  ├─ entity-identity.md     #   조사 대상 동일성 확정
│  ├─ extract-recipes.md     #   증거유형별 추출·locator 규칙
│  └─ image-research.md      #   도판 확보 우선순위·결박·라이선스
├─ scripts/                  # 실행 도구 15종
│  ├─ gates.py               #   게이트 영수증 원장(선행조건·소유권·드리프트 검출)
│  ├─ verify_facts.py        #   G3 기계 검증(실패 0 강제)
│  ├─ facts_db.py            #   사실대장 원자적 read/append
│  ├─ fetch.py · search.py   #   수집 스택
│  ├─ capture_pdf.py · capture_web.py           # 증빙 캡처
│  ├─ harvest_images.py · make_chart.py         # 도판 수확 · 최후수단 차트
│  ├─ render_pdf.py · manifest.py · preview_pdf.py   # 렌더·봉인·프리뷰
│  └─ preflight.py · install.py · skill_paths.py     # 점검·설치·경로
└─ tests/
   ├─ test_adversarial.py    # 적대 케이스 60종 — 조작·오류를 "실패로 검출"해야 성공
   └─ test_e2e.py            # 증거→대장→보고서→PDF→무결성 전 구간 1시나리오
```

모든 스크립트는 `python <script>.py demo`로 오프라인 자가검사를 돌릴 수 있습니다(pytest 미사용).

## 조사 1건의 산출물

```
research_<주제>_<YYYYMMDD>/
├─ report.pdf            # 고객용 팩트시트 (11부 표준목차, 수치마다 (F###) 태그)
├─ report.md             # 생성 소스 (직접 수정 금지 — facts.jsonl 수정 후 재렌더)
├─ _captures/            # fact별 원문 화면캡처 (E###.png + 메타)
├─ _images/              # 대표 도판 + IMAGES.md 인덱스
├─ assets/               # 자작 차트(SVG)
└─ audit/                # 내부 전용: facts.jsonl · gates.jsonl · 폐기 목록 ·
                         # 실패 소스 · 검증 이력 · raw 워커 출력 · manifest(SHA-256)
```

**단일 진실원은 `facts.jsonl`입니다.** 보고서는 생성물이므로 본문 수치를 직접 고치는 행위는 금지되며, 대장을 고치고 재렌더해야 합니다 — G3/G5 게이트가 이 동기화를 기계로 강제합니다.

## 설치·실행

```bash
# 의존성 점검 (HARD: python>=3.10, PyMuPDF, pandoc, chrome / SOFT: curl_cffi, trafilatura …)
python codes/market-deep-research/scripts/preflight.py

# ~/.claude/skills/market-deep-research/ 로 설치 (SHA-256 해시 검증 복사)
# ⚠ mirror-sync 방식: 인자 없이 즉시 실행되며, 대상 폴더의 초과 파일을 삭제합니다
python codes/market-deep-research/scripts/install.py

# 설치본이 개발본과 같은지 쓰지 않고 대조 (불일치 시 exit 1)
python codes/market-deep-research/scripts/install.py --check
```

`--check`가 따로 있는 이유는 `install()`이 대조 **전에 복사부터** 하기 때문입니다 — 묻는 행위가 답을 바꿔버려서 "설치본이 최신인가"를 물을 수단이 못 됩니다. 조사 직전에 `--check`로 확인하면 옛 코드로 조사가 도는 사고를 미리 잡습니다.

설치 후 Claude Code에서 "증빙/캡처 포함 시장조사 보고서", "기술동향·산업동향 조사", "근거 있는 딥리서치 PDF" 류의 요청이 이 스킬로 라우팅됩니다. **정본은 이 저장소입니다** — 설치본을 직접 수정하지 말고, 저장소를 수정한 뒤 `install.py`로 반영합니다.

## 검증 현황

```
적대 스위트 : 60/60   조작된 대장·위조 영수증·무출처 도판을 "실패로 검출"해야 성공
E2E        : PASS    증거 수집 → 대장 → 보고서 → G3 → PDF → preview → 무결성
스크립트 demo : 15종 전부 오류 없이 실행
설치 해시검증 : 29/29 (`--check` 드리프트 0)
```

## 개발 이력

| PR | 내용 |
|---|---|
| [#13](https://github.com/bbiyakfather/market-deep-research/pull/13) | 스킬 고도화 — 수집·검증 하네스 |
| [#14](https://github.com/bbiyakfather/market-deep-research/pull/14) | 영수증 소유권 확립 — 소유 게이트 CLI 손기록 차단, G5 자기기록 |
| [#15](https://github.com/bbiyakfather/market-deep-research/pull/15) | 완성 인포그래픽 탐색 하네스 — `## FIGURES` 마커, 도판 랭킹, G3 도판검사, 최후수단 차트 |
| [#16](https://github.com/bbiyakfather/market-deep-research/pull/16) | 도판검사 우회로 4건 차단 + 설치본 드리프트 감시(`--check`) |

2026-08-10 브랜치를 `main` 단일로 정리했습니다. 삭제된 12개 브랜치의 tip 해시와 복구 명령은 `_planning/branch-cleanup-2026-08-10.md`에 있습니다 — 브랜치 삭제는 커밋을 지우는 것이 아니라 이름표를 떼는 것이라, 해시만 있으면 되살릴 수 있습니다.
