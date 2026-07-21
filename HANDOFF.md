# HANDOFF — market-research-assistant 스킬 (구 factsheet-research)

> 갱신 2026-07-21. 상태: **구현 완료 + 설치 완료.** 남은 것은 아래 "사용자 확인 항목" 2건뿐.

## 무엇을 만들었나 (한 줄)
기술사업화 기관(내비온)용 **증빙형 시장조사 보고서 생성 Claude Code 스킬**.
기술동향·산업동향·기관/기업 실사·시장조사를 팀리드+서브에이전트로 수행하고,
[조사내용 → 출처 → 스크린샷] 증거구조로 **조사마다 수치가 달라지는 문제**를 제거한 팩트시트 PDF를 낸다.
※ 스킬명은 사용자 지시로 `factsheet-research` → **`market-research-assistant`** 변경됨.

## 완료 요약 (2026-07-21, shrimp 14작업 전건 검증 통과)
- **개발본**: `codes/market-research-assistant/` — SKILL.md(G0~G5 오케스트레이션 전문) + references 7종 + scripts 11종 + assets 4종 + tests 3종.
- **설치본**: `~/.claude/skills/market-research-assistant/` (install.py 해시검증 설치, 22파일 verify OK). 설치 직후 세션 스킬 목록 등록 확인.
- **검증 통과**: preflight 전항목 OK(pandoc 3.10 winget 설치·trafilatura 2.1.0 pip 설치 포함) / 전 스크립트 selfcheck / 적대적 fixture 10종 정확 실패 / replay 결정론 / **E2E 미니조사(RISC-V) G0~G5 완주**(confirmed 5·disputed 4·discarded 1·캡처 5, 고객PDF/audit 분리, G3 violation 0, G5 무결성 OK).
- plan-v2 "검증" 절 9개 체크박스 중 8개 실증 완료. 마지막 1개(forward test)만 아래 참조.

## 사용자 확인 항목 (남은 것)
1. **forward test**: 새 세션에서 자연어("OO 기술동향 조사해줘" / "OO기업 실사" / "OO 시장조사 보고서")로 스킬이 트리거되고 G0부터 오케스트레이션이 개시되는지 확인.
2. **기존 market-deep-research 스킬 폐기 여부 결정**: 이번 작업은 기존 스킬을 수정하지 않았음(권고: 신규 스킬 forward test 통과 후 폐기 검토).

## 설계 문서 (권위본, 열람용)
- `_planning/plan-v2.md` — 확정 설계 v2 (Codex 적대적 리뷰 합의 반영)
- `_planning/codex-review.md` — v1→v2 재설계 근거

## 환경 메모 (이 머신 실측)
- Windows 11, **Python 3.13.14**, `PYTHONUTF8=1`. pandoc 3.10(winget, PATH 미반영 시 skill_paths.find_pandoc 폴백), trafilatura 2.1.0, curl_cffi 0.15.0, fitz 1.27.2.3, Chrome, playwright.
- 의존성 판단은 문서가 아니라 `python <스킬>/scripts/skill_paths.py --preflight` 실행 결과 기준.
