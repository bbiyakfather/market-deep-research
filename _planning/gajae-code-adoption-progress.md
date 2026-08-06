# gajae-code-adoption 구현 진행 기록 (재개용)

> 2026-08-06 세션 중단 시점 스냅샷. 정본 계획 = `_planning/gajae-code-adoption.md` (v1.2).
> 오케스트레이션: Orca run `run_61b7a063b09f` (11개 태스크 DAG 등록 상태 유지 — `orca orchestration task-list --json`으로 조회).

## 태스크 상태

| 태스크 | 내용 | 상태 |
|---|---|---|
| T2 `task_8ec41188853b` | R2a fetch-log 기계 기록(fetch.py) | **완료·검증됨** (opencode gpt-5.6-luna 작업, 팀리드 검증: py_compile·적대 48/48·diff 범위 정상. 커밋 540ef9b에 포함) |
| T1 `task_a78310ac700c` | R1+N8 게이트 영수증 원장 | **~70% 부분작업** — gates.py 513줄 작성됨(codex gpt-5.6-luna 산출, **팀리드 미감사** — 커밋 540ef9b에 포함), 훅 4개 파일(verify_facts +20·render_pdf +27·manifest +9·SKILL.md +1)은 이번 WIP 커밋분. 컴파일 OK·적대 48/48 통과했으나 **스펙 대비 완성도 감사 미실시** |
| T3~T11 | 계획서 R2~R9·N군 | 미착수 (Orca DAG pending) |

## 재개 시 다음 단계 (사용자 최종 지시 반영)

1. **워커 방식 전환 확정**: codex/opencode CLI 워커는 건별 승인 마찰로 회수·종료함(터미널 닫음). 사용자 지시 = **Claude Agent(Opus 5) 서브에이전트로 이어서 구현**, Fable(메인)이 리드·검토.
2. 첫 작업 = **T1 마감**: codex가 쓴 `scripts/gates.py` 513줄을 계획서 R1·N8 스펙 대비 전면 감사(자기신고 금지·fail-closed·record/check/status/record_script_result/N8 해시 결박) → 미비 보완 → 훅 4파일 완성도 확인 → 자체 데모(record→check→status→변조 검출→해시 드리프트) 실행.
3. 이후 DAG 순서: T3(R2 검증 3종)·T5(N1-G0)·T6(R4 파서) 병렬 → T4(R3 단독) → T7(R5) → T8(R6+N7) → T9(N1-G3) → T10(N5+N6) → T11(문서 묶음). 파일 파티션은 계획서 구현 순서 절 참조.

## 실측 주의사항 (재개 세션 필독)

- **테스트 실행법**: pytest 수집 안 됨(`def test` 0개) — 반드시 `python tests/test_adversarial.py` · `python tests/test_e2e.py` 직접 실행. e2e는 이번 중단 시점에 미실행(적대 테스트만 통과 확인).
- **커밋 540ef9b 혼입**: 다른 세션(PEM 보고서)이 lessons.md 커밋에 우리 진행분(계획서·fetch.py·gates.py)을 동반 커밋함. 내용 유실 없음, 이력만 혼합.
- 워커 규율(계획서 공통 스펙): git commit 금지(리드가 검토 후 커밋), fail-closed, 지정 파일 외 수정 금지, worker_done에 검증 증거 포함.
