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
high-risk fact 의 `evidence.capture` 파일 실재를 검사(핵심수치 캡처 필수).
