# 브랜치 정리 기록 — 2026-08-10

`main` 하나만 남기고 원격 브랜치를 모두 삭제했다. 브랜치 삭제는 **커밋을 지우지 않는다** —
아래 해시로 언제든 되살릴 수 있다(GitHub GC 전까지, 통상 수개월).

복구:
```
git fetch origin <해시>            # 원격에서 커밋 회수
git branch <이름> <해시>            # 로컬 브랜치로 복원
git push origin <이름>              # 원격에 재생성
```

| 브랜치 | 삭제 시점 tip 해시 | 비고 |
|---|---|---|
| feat/factsheet-research-skill | 6e38735b9a95e3a5070baf8e6d467e1aee45ce45 | PR #13 으로 main 병합됨(내용 보존) |
| feat/gajae-absorption | a19e0c068036ed801a11ffd3a3fa0e1f4e02b410 | 미병합 |
| feat/mdr-v10-recovery | aa8275c6f687fb396b39471c29d768eb542dae69 | **미병합 14커밋** — run_ledger.py 계열(PR #12) |
| feat/mdr-v5-hardening | 7452b29ffcc515ee83d8db4ad531662b3eeb5a1d | v10 계보 중간단계 |
| feat/mdr-v6-evidence-binding | 2b1a02b09f888bc88f84711dba7932f87b9527fe | v10 계보 중간단계 |
| feat/mdr-v7-ledger-floor | 8d6283fc5a6ec3202e765549779b198d4be3e234 | v10 계보 중간단계 |
| feat/mdr-v8-bx-promotion | aabc821a5306df6c5d8b6665c57bcd9c351e729c | v10 계보 중간단계 |
| feat/mdr-v9-live-capture | 3c0e55b29e7684a762daff3949252afd4933ee9f | v10 계보 중간단계 |
| worktree-factsheet-research-impl | b9f057e2658fe96dc47b77e3a23782038ce57b76 | 구 worktree |
| worktree-figma-mcp-selfstudy-research | 627e018636b5980564c9e58b8f26173766aca9ed | 구 worktree |
| worktree-mdr-fix-batch1 | 94b0887f3db092b43b53ccca5677b3bcbd77e9fa | 구 worktree(main 과의 분기점) |
| worktree-pem-electrolysis-research | ae13d627f43ac46616f9b63ad42875ed5ecfa7e4 | 구 worktree |

정리 시점 main: c76ee07 (PR #14 병합 — 영수증 소유권 확립)

## v10 계열을 버린 이유
main 계열과 v10 계열이 게이트 영수증을 각각 gates.py / run_ledger.py 로 따로 구현해
의미 충돌 상태였다. 2026-08-10 결정으로 main 계열을 정본으로 삼았고, v10 의 강화분
(원장 위조 차단·G5 자기기록)은 PR #14 에서 main 의 gates.py 위에 다시 구현했다.
