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
- 파일명 = evidence ID. 반환 `ok:false`(미발견/부분문자열만 발견돼 강등)면 원본 `out_png` 가 아니라
  `E###.FAILED.png` 로 저장(페이지 전체 렌더, 팀리드 육안 fallback) — `out_png` 자체는 생성되지
  않으므로 대장이 그 경로를 가리켜도 `verify_facts.py` 가 파일부재로 **[증빙유실] FAIL** 을 내며,
  재작업 전까지 confirmed 불가.
- 부분문자열 오귀속(예: '45'가 '2045' 안에서 히트)은 rect 인접 문자 검사로 자동 필터링된다.
  그래도 엉뚱한 표의 같은 숫자를 잡지 않았는지 육안 확인은 유지.

## playwright 실화면 캡처 시 메타 결박(필수)
스크린샷 evidence 는 **최종 URL · 접근 시각(accessed_at) · viewport · locator(selector)** 를 함께
기록(`evidence.locator`, `evidence.source_url`, `evidence.observed_at`). 결박 없는 스크린샷은 불인정.

## 캡처 ↔ 본문 매핑
근거표/증빙박스에서 각 캡처 캡션은 "본문 수치(Fxxx) ↔ 원문 위치"를 1:1로 명시. `verify_facts.py` 가
**본문에 쓰인 confirmed 핵심수치(수치값 보유) 전건**의 `evidence.capture` 실재를 검사(risk 태깅 무관·강제).
또 **본문 대표 이미지 0장**이면 FAIL, DB에 생성됐으나 본문 미결박 캡처는 WARN 으로 표면화한다.
캡처 파일 자체의 **구조검사**도 수행한다: 바이트 하한 미달·백지/단색(픽셀 표준편차·유니크 컬러 하한
미달) 캡처는 WARN — "파일이 존재한다"와 "원문 화면이 담겼다"를 분리 검증한다. 【v4-Q】

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
