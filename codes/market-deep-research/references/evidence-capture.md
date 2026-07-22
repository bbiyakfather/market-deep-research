# evidence-capture — source_capture vs reconstructed_excerpt · 메타 결박

## 두 종류를 절대 혼동하지 않는다
| 상황 | 방법 | 유형 | 증빙 인정 | 저장 |
|---|---|---|---|---|
| 로컬/다운로드 PDF | `capture_pdf.py`(fitz 정확숫자 하이라이트+크롭) | **source_capture** | ✅ | `_captures/E###.png` |
| 접근 가능한 웹 | playwright 실화면 스크린샷(MCP 직접) | **source_capture** | ✅ | `_captures/E###.png` |
| 차단·유실 원문 | `capture_web.py`(insert_htmlbox 재구성) | **reconstructed_excerpt** | ❌ | `_reconstructed/` |

- **재구성 발췌(htmlbox)는 증빙 불인정**: 연구자가 그린 재현물이라 조작 발췌도 통과할 수 있음.
  원본 캡처 불가 시 → 대체출처 확보 or 해당 fact 는 `disputed`/미확인 유지. 고객 PDF 증빙에 쓰지 않음.

## capture_pdf 사용
`python capture_pdf.py <pdf> <number> _captures/E###.png [--page N]`
- 검색어 = **정확 숫자**(부분문자열 지양). 쉼표/공백 변형 자동 재시도(`_variants`).
- 파일명 = evidence ID. 반환 `ok:false`(미발견=표기변형/스캔PDF)면 페이지 전체 렌더 + **실패상태**
  → 팀리드 육안 fallback, confirmed 불가.
- 오귀속 육안 확인(엉뚱한 표의 같은 숫자를 잡지 않았는지).

## playwright 실화면 캡처 시 메타 결박(필수)
스크린샷 evidence 는 **최종 URL · 접근 시각(accessed_at) · viewport · locator(selector)** 를 함께
기록(`evidence.locator`, `evidence.source_url`, `evidence.observed_at`). 결박 없는 스크린샷은 불인정.

## 캡처 ↔ 본문 매핑
근거표/증빙박스에서 각 캡처 캡션은 "본문 수치(Fxxx) ↔ 원문 위치"를 1:1로 명시. `verify_facts.py` 가
**본문에 쓰인 confirmed 핵심수치(수치값 보유) 전건**의 `evidence.capture` 실재를 검사(risk 태깅 무관·강제).
또 **본문 대표 이미지 0장**이면 FAIL, DB에 생성됐으나 본문 미결박 캡처는 WARN 으로 표면화한다.

## 스크롤 실패 페이지 캡처 (find→scroll_to) — 검증된 우회
IEA 스크롤리텔링·비네트 광고·무한스크롤 등 **휠 스크롤·PageDown·좌표 scroll_to 가 목표 문단에
도달하지 못하는** 페이지는 아래 순서로 안정 캡처한다(2026-07 PEM 조사에서 미캡처 4건 전량 해소).
1. `mcp__claude-in-chrome__find` 로 목표 문단의 고유 텍스트(핵심수치 verbatim 일부)를 검색 → `ref` 확보.
2. `mcp__claude-in-chrome__computer` `scroll_to(ref)` — 좌표가 아니라 **요소 ref 기준**으로 이동(광고 오버레이·가상스크롤 무관하게 도달).
3. 도달 후 스크린샷 저장(`_captures/E###.jpg`) + 메타 결박(최종URL·accessed_at·viewport·locator=ref).
- 비네트/동의 배너가 Esc·Close 로 안 닫히면: 먼저 `find` 로 배너 닫기 버튼 ref 를 잡아 클릭, 실패 시
  배너를 피해 target ref 로 `scroll_to` 후 크롭. 그래도 불가하면 **캡처 미확보를 정직 고지**하고
  동일 URL·verbatim 은 `_sources/` 에 팀리드 재열람으로 보존(INDEX 한계 절에 기록).
- 다운로드가 필요한 PDF(예: 초안 T&C)는 **다운로드=권한 사안**이라 수행하지 않고 URL·verbatim 인용으로 대체.
