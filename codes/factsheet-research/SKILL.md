---
name: factsheet-research
description: >-
  기술사업화 기관용 증빙형(fact + evidence) 시장조사 보고서를 생성한다. 기술동향·산업동향·
  기관/기업 실사·시장조사 요청에 사용한다. 트리거 예: "OO 기술동향 조사해줘", "OO기업 실사해줘",
  "OO 시장조사 보고서 만들어줘", "OO 산업동향 정리해줘", "OO 기관 실사 자료". 모든 수치를
  [조사내용 → 출처 → 스크린샷] 증거구조로 고정하고, 팀리드가 전건 재검증한 뒤 GitHub 스타일
  PDF(고객용)와 내부 audit 번들을 함께 낸다. 단순 웹검색·사실 한두 개 확인·요약 등 증빙형
  보고서가 필요 없는 일반 질문에는 트리거하지 않는다.
---

# factsheet-research — 증빙형 시장조사 보고서 스킬

> **한 줄**: 조사마다 수치가 달라지는 문제를 [조사내용 → 출처 → 증빙] 증거구조 + 사실대장 +
> 검증게이트로 제거하고, 고객용 팩트시트 PDF와 내부 audit 번들을 분리 산출한다.

<!-- N10에서 확정: 아래 각 게이트의 상세 본문(에이전트 브리프 인용·판정 기준·실패 처리)을
     채운다. 현재는 오케스트레이션 골격과 1줄 요약만. references/ 7종이 상세를 담당. -->

## 오케스트레이션 파이프라인 (게이트 G0~G5)

```
[G0] preflight + 요구사항 확정 ── 도구/의존성 점검(skill_paths.py --preflight),
      조사유형·범위·조사종료기준·환산옵션(기본 OFF)·출력형식·목차 승인.
      기관/기업 조사면 entity-identity 게이트(법인명·사업자/법인번호·주소·이전상호) 선행.
[1]  병렬 조사 ────────── 조사원 에이전트 팬아웃 (sonnet·background, 에이전트별 임시 하위폴더로 파일충돌 방지)
[G1] join + 수집 게이트 ── 전 에이전트 완료/timeout/부분실패 처리, raw 산출물 _research/ 보존.
      facts_db.py 스키마 검증 등재, 출처 없는 주장 즉시 discarded(audit 기록).
[2]  팀리드 재검증 ─────── ★전건. 보고서 진입 모든 fact를 팀리드가 원문 재열람하여
      verbatim/locator 대조 후 verify_event 기록(verifier 단독 confirm 금지).
[G2] 증빙 게이트 ──────── confirmed 전건 source_capture 생성(실화면/PDF). 재구성 발췌는 증빙 불인정.
[3]  보고서 작성 ──────── 고객용 report.md(3중 구조+인사이트+한계) / 내부 audit 번들 동시 생성
[G3] verify_facts + manifest ── 무태그 숫자 탐지·부록 우회 차단·태그↔대장 의미 대조, 실패 0 필수. 해시 고정.
[4]  render_pdf ───────── GitHub 스타일 오프라인 PDF (pandoc → HeadlessChrome)
[G4] preview_pdf ──────── 팀리드 육안검증 (fitz 페이지 이미지 Read)
[G5] 최종 무결성 ──────── PDF에서 F태그·링크·캡처 수 재검사 + manifest 해시 재확인. 변경 시 G3 복귀.
```

## G0 — preflight + 요구사항 확정
의존성(fitz·pandoc·Chrome·playwright·curl_cffi·trafilatura)을 점검하고 조사유형/범위/종료기준/출력형식을 승인받는다. <!-- 상세 N10 -->

## G1 — join + 수집 게이트
팬아웃 조사원 결과를 합류시키고 스키마 검증 후 사실대장에 등재하며, 무출처 주장을 폐기한다. <!-- 상세 N10 -->

## G2 — 팀리드 재검증 + 증빙 게이트
보고서 진입 모든 fact를 팀리드가 원문 재열람해 대조하고, confirmed 전건에 source_capture를 생성한다. <!-- 상세 N10 -->

## G3 — verify_facts + manifest
본문/부록 분리 파싱·무태그 숫자 탐지·태그↔대장 의미 대조를 통과(실패 0)하고 증거 체인을 해시로 고정한다. <!-- 상세 N10 -->

## G4 — 렌더 + 육안검증
오프라인 GitHub 스타일 PDF를 렌더하고 팀리드가 fitz 페이지 이미지로 육안 확인한다. <!-- 상세 N10 -->

## G5 — 최종 무결성
PDF에서 F태그·링크·캡처 수를 재검사하고 manifest 해시를 재확인한다. 파일 변경 시 G3로 복귀한다. <!-- 상세 N10 -->

## 참조 문서 (references/)
- `agent-briefs.md` — 서브에이전트 프롬프트 + evidence 반환 스키마 + 철칙
- `source-ladder.md` — search 계층 + fetch 폴백 사다리 + 보안 정책
- `extract-recipes.md` — 증거유형별 추출 + PDF 파싱 + 특수소스 recipe
- `evidence-capture.md` — source_capture vs reconstructed_excerpt 구분
- `report-format.md` — 고객용 보고서 양식 + 내부 audit 번들 양식
- `verification-gates.md` — G0~G5 상세 + 4차원 등급 + 환산옵션
- `entity-identity.md` — 기관/기업 동일성 확인 게이트
