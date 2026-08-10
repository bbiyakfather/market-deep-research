# evidence-capture — source_capture vs reconstructed_excerpt · 메타 결박

## 두 종류를 절대 혼동하지 않는다
| 상황 | 방법 | 유형 | 증빙 인정 | 저장 |
|---|---|---|---|---|
| 로컬/다운로드 PDF | `capture_pdf.py`(fitz 정확숫자 하이라이트+크롭) | **source_capture** | ✅ | `_captures/E###.png` |
| 접근 가능한 웹 | 실화면 스크린샷(브라우저 MCP — 아래 계층순) | **source_capture** | ✅ | `_captures/E###.png` |
| 차단·유실 원문 | `capture_web.py`(insert_htmlbox 재구성) | **reconstructed_excerpt** | ❌ | `_reconstructed/` |

- **재구성 발췌(htmlbox)는 증빙 불인정**: 연구자가 그린 재현물이라 조작 발췌도 통과할 수 있음.
  원본 캡처 불가 시 → 대체출처 확보 or 해당 fact 는 `disputed`/미확인 유지. 고객 PDF 증빙에 쓰지 않음.

## capture_pdf 사용
`python capture_pdf.py <pdf> <number> _captures/E###.png [--page N]`
- 검색어 = **정확 숫자**(부분문자열 지양). 쉼표/공백 변형 자동 재시도(`_variants`).
- 파일명 = evidence ID. 반환 `ok:false`(미발견/부분문자열만 발견돼 강등)면 원본 `out_png` 가 아니라
  `E###.FAILED.png` 로 저장(페이지 전체 렌더, 팀리드 육안 fallback) — `out_png` 자체는 생성되지
  않으므로 대장이 그 경로를 가리켜도 `verify_facts.py` 가 파일부재로 **[증빙유실] FAIL** 을 내며,
  재작업 전까지 confirmed 불가.
- 부분문자열 오귀속(예: '45'가 '2045' 안에서 히트)은 rect 인접 문자 검사로 자동 필터링된다.
  그래도 엉뚱한 표의 같은 숫자를 잡지 않았는지 육안 확인은 유지.

## 실화면 캡처 — 브라우저 계층 + 메타 결박(필수)
계층(위에서부터 시도): **1순위 `agent-browser`** → 2순위 playwright MCP → 3순위 claude-in-chrome
(브라우저에 이미 로그인 세션이 있어야 열리는 페이지). agent-browser 가 1순위인 이유 = `path` 로
`_captures/E###.png` 에 **직접 저장** · `allowedDomains` 로 대상 도메인 밖 트래픽 차단(`fetch.py`
보안경계와 정합) · `eval` 로 스크롤·메타를 직접 제어.

### 표준 recipe (agent-browser) — 2026-08-03 실측 확인
1. `agent_browser_open(url, allowedDomains=[대상도메인, 이미지CDN])` — 반환 `data.url` 이 리다이렉트
   후 **최종 URL**(http→https 실측 확인).
2. `agent_browser_wait_for_text(핵심수치 verbatim 일부)` — 렌더 완료 + 도달 검증 겸용.
3. `agent_browser_eval` 로 **목표 요소를 화면에 올리고 메타를 한 번에 취득**:
   `el.scrollIntoView({block:'center'})` 후 `innerWidth+'x'+innerHeight`(viewport) ·
   `location.href`(최종 URL) · 요소 rect 를 반환. → `evidence.locator` 에 이때 쓴 CSS selector 기록.
4. `agent_browser_screenshot(path="_captures/E###.png", format="png")` — **selector 없이 뷰포트 캡처**.
5. 저장된 PNG 를 **팀리드가 Read 로 육안 확인**(핵심수치가 실제로 찍혔는지). 미확인이면 3~4 재시도.

### ⛔ `selector` 크롭 금지 — 2026-08-03 실측 반증
`agent_browser_screenshot(selector=…)` 는 **크롭 크기만 맞고 내용은 백지**로 저장되면서
`success:true` 를 반환한다(요소가 화면 안이든 밖이든 동일, `scrollIntoView` 후에도 동일).
`fullPage:true` 와 함께 주면 selector 는 **조용히 무시**된다. 자동 검출이 불가능한 백지 증빙이
`source_capture` 로 등재되는 최악의 경로이므로 **증빙 캡처에 selector 를 쓰지 않는다**.
크롭이 필요하면 뷰포트 캡처 + 캡션으로 위치를 지정한다(원문 맥락이 함께 보이는 편이 증빙에 유리).
⚠ 이 때문에 **5번 육안 확인은 생략 불가** — 도구의 `success:true` 는 캡처 성공을 보장하지 않는다.

### 메타 결박 (계층 무관 동일 적용)
스크린샷 evidence 는 **최종 URL · 접근 시각(accessed_at) · viewport · locator(selector)** 를 함께
기록(`evidence.locator`, `evidence.source_url`, `evidence.observed_at`). 결박 없는 스크린샷은 불인정.

## 캡처 ↔ 본문 매핑
근거표/증빙박스에서 각 캡처 캡션은 "본문 수치(Fxxx) ↔ 원문 위치"를 1:1로 명시. `verify_facts.py` 가
**본문에 쓰인 confirmed 핵심수치(수치값 보유) 전건**의 `evidence.capture` 실재를 검사(risk 태깅 무관·강제).
또 **본문 대표 이미지 0장**이면 FAIL, DB에 생성됐으나 본문 미결박 캡처는 WARN 으로 표면화한다.

## 스크롤 실패 페이지 캡처 — 검증된 우회
IEA 스크롤리텔링·비네트 광고·무한스크롤 등 **휠 스크롤·PageDown·좌표 scroll_to 가 목표 문단에
도달하지 못하는** 페이지(2026-07 PEM 조사에서 미캡처 4건 발생 → 전량 해소).

**1순위 — agent-browser `eval` + `scrollIntoView`** (2026-08-03 실측: 뷰포트 높이 569 밖인 문서
y=2702 위치의 표가 `scrollIntoView({block:'center'})` 후 뷰포트 캡처에 정확히 담겼다).
`agent_browser_eval` 로 목표 요소를 셀렉터/텍스트로 찾아 `scrollIntoView` → 뷰포트 캡처.
좌표가 아니라 **요소 기준**이라 광고 오버레이·가상스크롤과 무관하게 도달한다.

**3순위 폴백 — claude-in-chrome `find` → `scroll_to`** (agent-browser 미연결이거나 브라우저의
기존 로그인 세션이 필요할 때):
1. `mcp__claude-in-chrome__find` 로 목표 문단의 고유 텍스트(핵심수치 verbatim 일부)를 검색 → `ref` 확보.
2. `mcp__claude-in-chrome__computer` `scroll_to(ref)` — 좌표가 아니라 **요소 ref 기준**으로 이동(광고 오버레이·가상스크롤 무관하게 도달).
3. 도달 후 스크린샷 저장(`_captures/E###.jpg`) + 메타 결박(최종URL·accessed_at·viewport·locator=ref).
- 비네트/동의 배너가 Esc·Close 로 안 닫히면: 먼저 배너 닫기 버튼을 잡아 클릭, 실패 시
  배너를 피해 목표 요소로 이동 후 캡처. 그래도 불가하면 **캡처 미확보를 정직 고지**하고
  동일 URL·verbatim 은 `_sources/` 에 팀리드 재열람으로 보존(INDEX 한계 절에 기록).
- 다운로드가 필요한 PDF(예: 초안 T&C)는 **다운로드=권한 사안**이라 수행하지 않고 URL·verbatim 인용으로 대체.
