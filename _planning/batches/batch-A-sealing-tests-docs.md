# Batch A — 봉인 버그(C1·C2) 수정 마무리: 테스트 + 문서

작업 루트: `F:/Claude/skills/market-deep-research/codes/market-deep-research/` (브랜치 `feat/purpose-modules`, 워크트리 공유 — **다른 워커가 동시에 작업 중**이니 아래 "손대는 파일" 밖은 건드리지 말 것)

## 배경 (코디네이터가 이미 고친 것 — 되돌리지 말고 먼저 읽을 것)
Codex 적대 리뷰(`_planning/council-2026-08-22/review-codex-modularize.md` C1·C2)로 확인된 현행 버그:
G3 이후 `report.md`/`facts.jsonl` 을 변조해도 `render_pdf.py` 가 manifest 를 **통째로 재빌드**해 변조가 새 기준선으로 세탁되고 G5 가 PASS 했다. 또 manifest 는 `report.pdf` 파일명만 추적해 다른 이름 산출물은 영구 미추적이었다.

코디네이터가 수정한 코드(읽기 필수, 로직 변경 금지 — 버그를 발견하면 `ask` 로 물을 것):
- `scripts/gates.py` — `record_script_result(..., extra=dict)` 추가(예약 필드 덮어쓰기 금지).
- `scripts/manifest.py` — `_diff()`(저장 항목을 경로로 직접 재해시 → TRACKED 글롭 밖 산출물도 추적), `extend(wp, paths, label, expected_sha256)`(기존 항목 불변 확인 + G3 기준선 해시 대조 후 **추가만**), `verify()` 가 `_diff` 사용, CLI `verify` 가 [4b] 영수증의 `manifest_sha256` ↔ 현재 manifest.json 해시 대조. demo 에 C1·C2 회귀 포함.
- `scripts/verify_facts.py` — CLI PASS 경로가 `manifest.build()` 로 G3 기준선을 만들고 G3 영수증에 `extra={"manifest_sha256","manifest_entries"}` 결박.
- `scripts/render_pdf.py` — `render()` 가 `"artifacts": [pdf]` 도 반환(양식 모듈 공통 계약). CLI 가 G3 영수증의 `manifest_sha256` 를 `manifest.extend(expected_sha256=)` 에 넘겨 확장만 하고, [4b] 영수증에 `manifest_sha256`·`g3_result_summary_sha256`·`artifacts[{path,sha256}]` 결박.

4개 스크립트 `python scripts/<x>.py demo` 는 코디네이터 환경에서 전부 PASS 확인됨.

## 손대는 파일 (이 밖은 금지)
`tests/test_adversarial.py` · `tests/test_e2e.py` · `SKILL.md` · `references/verification-gates.md` · `../../README.md`(파이프라인 설명 줄만)

## 할 일
1. **`tests/test_adversarial.py` 기존 케이스 보정**: `g5_receipt_owned_by_manifest_verify` 는 [4b] 를 API 로 기록하는데 이제 G5 CLI 가 [4b] 영수증의 `manifest_sha256` 결박을 요구한다 → `manifest.build(wp)` 뒤 `gates.record_script_result(wp, "[4b]", 0, "reseal PASS", extra={"manifest_sha256": manifest.sha256_file(wp.manifest)})` 로 바꿔 통과시킬 것(소유 스크립트가 하는 일을 흉내). 다른 케이스는 실행해 보고 깨진 곳만 최소 보정.
2. **적대 케이스 추가** (`@case` 함수, 기존 스타일·한글 docstring·긍정형 짝 유지):
   - `reseal_rejects_post_g3_tamper`: 임시 work_dir 에 G0(audit/research-plan.md 필요)·G1·[2] 영수증을 API 로 기록(기존 `g5_receipt_owned_by_manifest_verify` 의 셋업을 참고), `report.md` 작성, `manifest.build` + G3 영수증을 `extra={"manifest_sha256": ...}` 로 기록(verify_facts 소유자 흉내). 그 뒤 `facts.jsonl` 을 변조하고 `render_pdf.py <report.md>` CLI 를 subprocess 로 실행 → **exit 1**, 원장에 [4b] 영수증 없음, manifest.json 해시 불변. 긍정형 짝: 변조 안 한 같은 셋업 → exit 0, [4b] 영수증에 `manifest_sha256`·`artifacts`(report.pdf 포함) 존재, manifest entries 에 `report.pdf` 추가되고 기존 항목 해시는 그대로.
   - `g5_rejects_rebuilt_manifest`: 정상 체인(… [4b] 까지) 후 `manifest.build(wp)` 를 다시 호출(세탁 시도) → G4 기록 → `manifest.py verify` CLI → **exit 1**, stderr 에 "[4b]" 결박 불일치 메시지, 원장 마지막 레코드는 G5 가 아니거나(전제조건 단계 실패이므로 기록 없음) 최소한 PASS 가 아님.
   - `manifest_extend_tracks_custom_artifact`: `extend` 로 `custom.pdf`(TRACKED 밖 이름) 봉인 → 변조 시 `verify()` 가 changed 로 잡고, 삭제 시 missing 으로 잡음. 작업폴더 밖 경로는 `ValueError`.
3. **`tests/test_e2e.py` 를 실제 CLI 체인으로**: 현재 4)~6.5) 단계가 `verify_facts.verify()`·`manifest.build()`·`render_pdf.render()` 를 함수로 직접 불러 CLI 경로(영수증·기준선·extend)를 검증하지 못한다(Codex C1 지적). 다음으로 바꿀 것: `audit/research-plan.md` 작성(`references/research-plan.md` 의 "승인 목차" 서식 `# 부 N. 제목` 으로 REPORT 목차와 정합되게 — 안 맞으면 `verify_facts.check_toc` 가 FAIL 하니 실제 돌려보며 맞출 것; 정 어려우면 `[목차미검증]` WARN 으로 떨어지는 조건을 이용하되 그 선택을 보고에 적을 것) → `gates.record_manual(G0)` → `record_script_result(G1)` → `record_manual("[2]")`(confirmed 전건 lead reread 는 이미 있음) → `verify_facts.py report.md <wd>` **CLI** exit 0, `manifest.json` 생성됨, G3 영수증에 `manifest_sha256` → `render_pdf.py report.md` **CLI** exit 0, [4b] 영수증 존재, manifest 에 report.pdf 추가 → `preview_pdf` → `record_manual(G4)` → `manifest.py verify <wd>` **CLI** exit 0, G5 영수증 PASS. 기존 단언(고객 PDF/audit 분리·해시 일치)은 유지. subprocess 는 `encoding="utf-8", errors="replace"` 와 `env={**os.environ, "PYTHONIOENCODING": "utf-8"}`.
4. **문서 정합**: 아래 문구를 새 동작에 맞게 고친다(테스트가 정규식으로 잡는 제목 `[4] render_pdf`·`## G4 preview` 등 헤딩은 유지):
   - `SKILL.md` [G3] 불릿: "`scripts/manifest.py build`: … 해시 고정" → verify_facts CLI PASS 가 기준 manifest 를 자동 생성하고 영수증에 해시를 결박한다는 문장으로. [4b] 불릿: "manifest.py build 재실행 … 기존 항목 보존" → **extend-only**(기존 항목 불변 확인 실패 시 거부 = G3 복귀, 렌더 산출물 artifacts 만 추가, G3 기준선 해시 대조). 영수증 줄: G5 가 [4b]↔manifest 결박을 검사한다는 문장 추가. `[G2]` 참고 문단의 "재봉인이 해법" 은 "재봉인(extend) 이 해법" 정도로만.
   - `references/verification-gates.md` G3 절 끝("→ `manifest.py build` …")·"G4 preview → G5" 절의 재봉인 문장·"영수증 커버리지" 절을 같은 취지로. `## G4 preview` 절에는 `intent-diff`·`축별`·`복귀` 단어가 남아야 한다(테스트).
   - `README.md`(저장소 루트) 파이프라인 블록의 `[G3]`·`[4b]` 줄과 "게이트 영수증" 표 아래 설명 한두 문장.
5. **실행 증거**: `PYTHONIOENCODING=utf-8 python tests/test_adversarial.py`(전건 검출OK, 마지막 줄 N/N) · `python tests/test_e2e.py`(E2E OK) · `python scripts/gates.py demo` · `manifest.py demo` · `verify_facts.py demo` · `render_pdf.py demo`. 결과 요약(각 마지막 줄)을 worker_done body 에 붙일 것.

## 제약
- Windows·cp949 콘솔: 파이썬 실행 시 `PYTHONIOENCODING=utf-8`. pandoc·Chrome 은 설치돼 있음.
- `git commit` 금지(코디네이터가 리뷰 후 커밋). `.fablize/goals.py` 실행 금지.
- 모르는 것은 추측 말고 `orca orchestration ask` 로 질문.
