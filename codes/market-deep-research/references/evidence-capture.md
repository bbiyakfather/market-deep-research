# evidence-capture — source_capture vs reconstructed_excerpt · 메타 결박

## ⛔ 크롭 원칙 (모든 캡처 공통, V16)
**국소 크롭 금지.** 수치 주변만 오린 이미지는 제목·표머리·단위·기준연도가 잘려 사용자가 그
자리에서 원문을 확인할 수 없고, 증빙으로서 신빙성이 떨어진다. 캡처는 항상:
- **좌우 = 문서(또는 뷰포트) 전폭** — 잘라내지 않는다.
- **상하 = 대상 문단 ± 인접 한 문단** — 위아래 문맥이 최소 한 문단씩 보여야 한다.
- **표 안의 수치는 표 전체**(열 제목·단위행 포함) — 값만 보이고 열 이름이 없으면 증빙이 아니다.
PDF 는 `capture_pdf.py` 가 이 규격을 강제하고(`_context_clip`), 웹은 **selector 크롭 없이
뷰포트 캡처**(`scrollIntoView({block:'center'})` → 대상이 화면 중앙 = 상하 문맥 확보)로 맞춘다.

## 두 종류를 절대 혼동하지 않는다
| 상황 | 방법 | 유형 | 증빙 인정 | 저장 |
|---|---|---|---|---|
| 로컬/다운로드 PDF | `capture_pdf.py`(fitz 정확숫자 하이라이트 + 전폭·문단 크롭) | **source_capture** | ✅ | `_captures/E###.png` |
| 접근 가능한 웹 | 실화면 스크린샷(브라우저 MCP — 아래 계층순) | **source_capture** | ✅ | `_captures/E###.png` |
| 차단·유실 원문 | `capture_web.py`(insert_htmlbox 재구성) | **reconstructed_excerpt** | ❌ | `_reconstructed/` |

- **재구성 발췌(htmlbox)는 증빙 불인정**: 연구자가 그린 재현물이라 조작 발췌도 통과할 수 있음.
  원본 캡처 불가 시 → 대체출처 확보 or 해당 fact 는 `disputed`/미확인 유지. 고객 PDF 증빙에 쓰지 않음.

## capture_pdf 사용
`python capture_pdf.py <pdf> <number> _captures/E###.png [--page N]`
- 검색어 = **정확 숫자**(부분문자열 지양). 쉼표/공백 변형 자동 재시도(`_variants`).
- 크롭 = **좌우 전폭 + 상하 인접 문단 + (표 히트 시)표 전체**(`_context_clip`, `find_tables`).
  반환 `clip` 필드로 실제 범위 확인 가능.
- **검색 불가 원문**(스캔PDF, 폰트 인코딩이 깨져 `search_for` 가 못 찾는 PDF)은
  `python capture_pdf.py page <pdf> <N> _captures/E###.png` 로 **페이지 전면 캡처**를 쓴다.
  하이라이트는 없지만 페이지 전체라 발췌 조작 여지가 없고, 위치는 `evidence.locator` 로 지정한다.
  ※ 깨진 인코딩은 폰트 서브셋의 일괄 코드 시프트인 경우가 있어(Sourcewell 계약서 = -0x1D),
  `chr(ord(c)+오프셋)` 로 복호화하면 **팀리드 원문 대조**는 가능하다 — 대조는 복호화, 캡처는 전면.
  `pad` 를 줄여 국소 크롭으로 되돌리지 말 것 — 위 크롭 원칙 위반.
- 파일명 = evidence ID. 반환 `ok:false`(미발견/부분문자열만 발견돼 강등)면 원본 `out_png` 가 아니라
  `E###.FAILED.png` 로 저장(페이지 전체 렌더, 팀리드 육안 fallback) — `out_png` 자체는 생성되지
  않으므로 대장이 그 경로를 가리켜도 `verify_facts.py` 가 파일부재로 **[증빙유실] FAIL** 을 내며,
  재작업 전까지 confirmed 불가.
- 부분문자열 오귀속(예: '45'가 '2045' 안에서 히트)은 rect 인접 문자 검사로 자동 필터링된다.
  그래도 엉뚱한 표의 같은 숫자를 잡지 않았는지 육안 확인은 유지.

## 실화면 캡처 — 브라우저 계층 + 메타 결박(필수)
계층(위에서부터 시도): **1순위 `capture_web.capture_live()`(코어 내장)** → 2순위 `agent-browser`
→ 3순위 playwright MCP → 4순위 claude-in-chrome(브라우저에 이미 로그인 세션이 있어야 열리는 페이지).

### 【v9】 1순위 = 코어 내장 (`capture_web.capture_live`)
MCP 가 안 붙어 있으면 증빙 캡처가 통째로 불가능하던 상태를 닫았다 — `fetch.py` 가 강방어 우회를
코어에 내장한 것과 같은 이유로, **증거능력을 외부 연결에 걸지 않는다**. Chrome CLI 만 쓰므로 새
의존성 0(preflight HARD 의 chrome·fitz 재사용).

```
capture_live(url, number, out_png, allow_domains=[...], pdf_out=None)
 ①  chrome --print-to-pdf  →  capture_pdf.capture_number()   # 정확숫자 하이라이트 + V16 크롭
 ②  chrome --screenshot --window-size=1440,3000               # ①의 텍스트 오라클이 죽었을 때만
 ③  소진 → 브라우저 MCP(로그인·상호작용) 또는 대체출처
```

①이 1순위인 이유 두 가지 — **(a) 스크롤 도달 실패가 구조적으로 사라진다**(문서 전체가 렌더되므로
무한스크롤·비네트 광고·가상스크롤과 무관, 아래 '스크롤 실패 페이지' 절의 문제 자체가 소멸).
**(b) verbatim 을 기계가 확인한다** — PDF 텍스트레이어에서 그 수치를 찾아 크롭하므로 "캡처 안에
수치가 실재하는가"가 육안에만 의존하지 않는다(PNG 는 텍스트레이어가 없어 육안이 유일했다).

**②로 내려가는 조건은 좁다(fail-closed).** ①이 실패했는데 print 렌더에 텍스트가 남아 있으면
그 수치는 **렌더된 원문에 없는 것**이므로 화면 캡처로 내려가지 않고 실패로 돌린다 — 내려가면
"그 수치가 없는 이미지"가 `source_capture` 로 등재된다(백지 캡처·캡처 돌려막기와 같은 계열).
②는 텍스트 오라클 자체가 죽었을 때만 정당하다(SPA 가 print 에서 빈 페이지 · print CSS 가 본문을
통째로 감춤 · 렌더 실패). 실측(2026-08-06): 오라클이 죽은 경우는 전부 **0자**, 정상 짧은 페이지는
38자, 본문 일부만 print 에서 사라진 경우는 47자 — 낮은 구간에서 길이는 신호가 아니므로 **0자만**
기계로 잡고, 부분 소실 페이지는 사람이 `number=None` 으로 화면 캡처를 명시하게 한다(조용한
강등보다 명시적 결정이 감사에 남는다).

**경로 강도 기록**: evidence 에 `capture_mode`(print|screen|mcp) · `capture_verbatim`(기계확인된
문자열)을 남긴다. `verify_facts` 가 **`[캡처약결박]` WARN** 으로 표면화 — screen 모드는 "수치
실재를 기계가 확인할 수 없음(육안 필수)", **mcp(브라우저 MCP) 도 텍스트레이어가 없어 같은
사유로 WARN** — 메시지는 screen 과 구분되며 "백지저장 사고 이력이 있는 경로이니 팀리드 육안
확인 필수"를 명시한다(2순위 `agent-browser` 의 selector 백지 사고, 위 ⛔ 절 참조). print 인데
`capture_verbatim` 이 없으면 "기계확인 산출물 없이 강한 경로를 주장". 후자가 없으면
`capture_mode` 를 print 로 적는 것만으로 경고를 지울 수 있다.

**한계(정직 고지)**: ⓐ Chrome CLI 는 리다이렉트 후 **최종 URL 을 보고하지 않는다** — 결박용
최종 URL 은 `fetch.py` 가 확정한 값을 넘겨야 한다(`capture_live` 는 받은 URL 을 그대로 기록만
한다). ⓑ 로그인 세션·동의배너 클릭·펼침 상호작용은 불가 → MCP 계층의 고유 역할로 남는다.
ⓒ `--screenshot` 은 지정한 창 높이까지만 담는다(기본 1440×3000, `viewport=` 로 조정).
ⓓ `capture_verbatim` 이 그 fact 의 **값과 같은 수인지**까지는 대조하지 않는다(값 820.5 /
원문 표기 820,500,000 처럼 단위 스케일이 다른 정당한 경우를 오탐하게 되므로).

**allowedDomains 대체**: `allow_domains=[대상, 자원CDN]` → `--host-resolver-rules=MAP * ~NOTFOUND,
EXCLUDE …`. 실측 확인(허용 시 본문 렌더 / 미허용 시 Chrome 오류 페이지). 대상 도메인만 남기면
CSS·이미지 CDN 이 막혀 렌더가 깨지는 페이지가 많으므로 자원 도메인을 함께 넘긴다. ※ DNS 규칙
이라 `file://` 에는 적용되지 않는다.

### 2순위 = agent-browser (연결돼 있을 때)
`path` 로 `_captures/E###.png` 에 **직접 저장** · `allowedDomains` 로 대상 도메인 밖 트래픽 차단
(`fetch.py` 보안경계와 정합) · `eval` 로 스크롤·메타를 직접 제어. 내장 경로가 실패했고 로그인·
상호작용이 필요할 때 쓴다.

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
캡처 파일 자체의 **구조검사**도 수행한다: 바이트 하한 미달·백지/단색 캡처는 WARN — "파일이
존재한다"와 "원문 화면이 담겼다"를 분리 검증한다. 【v4-Q】

## 증거 결박 — 해시가 '기록'이 아니라 '대조 대상'이 되게 【v6】
`fact → source → capture` 체인은 **재계산해 대조할 수 있을 때만** 증거다(in-toto 규약).

- **원문 결박(EV-1)**: `evidence.local` 에 `_sources/` 스냅샷 경로가 있어야 하고 `sha256` 은 그
  파일의 실해시여야 한다. `local` 이 없으면 sha256 은 대조 대상이 없어 **아무 64자 hex 나
  통과**하므로, confirmed fact 의 증거에 `local` 부재는 `[해시미결박]` FAIL 이다. `fetch.py` 는
  이미 원본을 `_sources/` 에 저장하므로 그 경로를 그대로 실으면 된다.
- **캡처 결박(EV-2·EV-3)**: `capture_sha256`(선택 필드)을 함께 싣는다. 등재 후 이미지가 바뀌면
  `[캡처해시]` FAIL. 그리고 **같은 캡처가 서로 다른 fact 의 증빙으로 쓰이면 `[캡처재사용]`
  FAIL** — 정당한 캡처 1장을 복제해 수십 건의 증빙을 채우는 경로를 닫는다.
- **재검증 결박(EV-5)**: 팀리드 재검증은 `add_verify_event(..., evidence_id=E###)` 로 **무엇을
  재열람했는지** 지목한다. 지목이 없으면 `[재검증미결박]`, 재검증 시각이 증거 확보보다 앞서면
  `[재검증시각]` FAIL. 남의 fact 의 증거를 지목하면 등재 시점에 거부된다.
- **인용 대조(I3)**: `text_quote` evidence 는 `verbatim` 이 **비어있지 않은지**뿐 아니라 원문
  스냅샷(`evidence.clean` 우선, 없으면 `local`)에 실제로 있는지도 대조한다 — sha256 결박(EV-1)은
  파일이 진짜인지만 보증하고 그 안에서 인용을 지어냈는지는 못 잡는다. 완전 substring 이면 통과,
  아니면 `difflib` 최장일치가 인용문 길이의 90% 이상이면 근사 통과(파라프레이즈 허용), 그 밖은
  `[인용불일치]` **WARN**(FAIL 아님 — `[캡처약결박]` 선례처럼 오탐 관측 후 승격 검토). `clean`/
  `local` 이 둘 다 없거나 실재하지 않으면 조용히 생략(기존 evidence 호환).
- **백지 캡처(SC-4)**: `capture_pdf` 가 생성 시점에 픽셀로 판정해 백지·단색이면 `.FAILED` 로
  돌린다. 【v9 정정】 판정 기준은 **절대 잉크픽셀 수**(최빈색과 다른 픽셀 수) `<= 16` — 전수
  계산(`color_topusage()`)이다. 종전 v6 은 ~4000픽셀 **표본**으로 비율을 추정했는데, 표본 간격이
  이미지 크기에 비례해 벌어지는 탓에 **1440×3000 전면 스크린샷에서는 정상 페이지도 백지로
  판정**됐다(실측). 크롭 크기에서만 재고 넘어간 임계의 대가다. 실측(잉크픽셀): 완전 백지 0 ·
  짧은 선 1개 160 · 스크린샷 한 줄 896 · 크롭 텍스트1줄 2,488 · 크롭 표 20,760 · 스크린샷 정상
  페이지 28,744. **비율이 아니라 절대 픽셀 수가 캔버스 크기에 무관한 신호다.** 얇지만 비어있지
  않은 캡처는 여전히 육안의 몫이며, 과잉 차단이 백지 통과보다 나쁘다.

한계: 이 결박들은 **위조를 비싸게 만들 뿐 불가능하게 만들지는 않는다**. 같은 세션의 에이전트가
스냅샷 파일까지 지어내면 해시는 자기 일관되게 맞는다 — 최종 방어선은 팀리드의 실제 재열람이다.

## 표면별 증거 규칙 【v4-N】
**서술 텍스트만으로는 어떤 fact 도 G2(증빙 게이트)를 통과할 수 없다** — 출처 매체(표면)별로 요구
증거가 다르다:
| 표면 | 최소 증거 |
|---|---|
| 수치 주장 | 해당 수치가 **실제 보이는** 캡처(구조검사 통과) |
| 웹 페이지 | 최종 URL + accessed_at + 캡처(메타 결박) |
| PDF 문서 | 페이지 번호 + 해당 페이지 크롭(`capture_pdf.py`) |
| API/데이터셋 | endpoint + 파라미터 + 응답 발췌(`api_response`, JSON 해시) |
| 계산 파생치 | 스크립트 전문 + stdout(`calculation`, `audit/verify-<slug>.md`) |

**honest unknown**: 캡처·수집 부수효과가 "성공 여부 불명"으로 끝나면(타임아웃·중단) 실패로 위장하지
말고 `unknown` 으로 정직 기록한다 — 파일 존재 검증으로 finalize 하고, 불가하면 재시도 후보로 승격.
기록 부재 = "결과를 알 수 없음"이지 "실행되지 않았음"이 아니다.

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
