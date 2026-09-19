# 발견 1 표적 재리뷰

판정: **REQUEST_CHANGES**

발견 1은 **부분 개선됐으나 미해소**다. 기존 `_record_owned_result`를 이용한 재현 A·B는 차단됐지만, 그 아래의 `gates._record_script_result`를 직접 호출하면 동일한 최종 출고 우회가 남는다. 실제 G3 실패 영수증이 기록된 원고도 성공으로 덮어 승인할 수 있으며, 정상 G3 뒤 렌더만 생략하는 우회도 독립적으로 재현됐다.

## 범위와 가정

- 대상: `p0-final2.diff`. SHA-256: `dc97b66a2890a30c43b276bf3dde942a7413342549d7cd85ef57b9a30a108f76`.
- diff의 14개 파일 모두 새 Git blob 식별자가 워킹트리와 일치함을 확인했다. 2차 변경 범위는 `fixup2.diff`와 대조했다.
- 아래 파일:라인은 `F:/Claude/skills/market-deep-research/codes/market-deep-research/` 기준이다.
- 지시 파일 옆에는 입력 문서가 없으므로, 입력 문서들이 함께 있는 scratchpad를 “같은 폴더”로 해석했다.
- pytest 123개 및 데모 3종 통과는 제공된 사실로 받아들였으며 재실행하지 않았다. 이미 해소된 ②③④ 및 기타 통과 항목은 독립 재리뷰하지 않았다.
- 소스 수정·monkeypatch·원장 파일 직접 편집 없이, 기존 합성 픽스처로 만든 임시 작업폴더에서 함수 호출만으로 두 변종을 실행했다. 저장소 구현·테스트는 수정하지 않았다. 실행 결과는 같은 폴더의 `astra-rereview-probes.json`에 기록했다.

## 기존 재현 A·B와 정상 진입점

| 항목 | 판정과 구현 근거 |
|---|---|
| A의 기존 전용 기록 호출 | `scripts/gates.py:499`에서 G3와 [4b] 호출을 즉시 거부한다. `scripts/verify_facts.py:927`에서 정규 report.md에 실제 verify를 실행하고, FAIL이면 `:929`에서 실패 영수증만 남기고 반환하므로 이 진입점으로는 실패 원고가 봉인되지 않는다. |
| B의 기존 전용 기록 호출 | 같은 거부 분기로 [4b] 직접 성공 기록이 막힌다. `scripts/render_pdf.py:92`에서 G3 manifest 기준선을 대조하므로 가짜 PDF를 먼저 extend한 뒤 새 진입점을 호출해도 실패한다. |
| 새 G3 정상 경로 | `scripts/verify_facts.py:932`의 선행조건 검사 뒤 `:935`에서 봉인하고 `:936`에서 기록한다. 호출자가 결과 요약이나 검증 원고를 인자로 제공하지 않으며 CLI도 `:1040`에서 이 함수를 재사용한다. |
| 새 [4b] 정상 경로 | `scripts/render_pdf.py:94`의 실제 render 반환값만 `:97`에서 extend하고 파일 대조 후 `:102`에서 기록한다. pdf_out은 실제 렌더 출력 경로로 전달되며, 결과·artifacts 주입 인자는 없다. CLI도 `:147`에서 이 경로를 재사용한다. |

따라서 새 진입점 자체는 스펙의 실행 순서를 구현했다. 다만 이 진입점 사용이 성공 기록의 필수조건으로 강제되지 않는다.

## 발견 1 잔존 — [치명] 하위 기록 함수 직접 호출로 소유 작업 생략 후 최종 승인 가능

**위치:** `scripts/gates.py:517`, `:540`, `:563`, `:576`, `:581`. 새 정상 경로가 이 함수를 직접 사용하는 지점은 `scripts/verify_facts.py:936`, `scripts/render_pdf.py:102`.

`_record_script_result`는 선행 영수증만 확인하고, 호출자가 준 exit=0·결과 요약·extra 결박값으로 성공 영수증을 발급한다. 이 함수에는 `record_script_result`의 소유 게이트 거부(`scripts/gates.py:482`)도, `_record_owned_result`의 G3/[4b] 거부(`:499`)도 없다. verify/render 실행 여부를 확인하지 않는다. extra의 예약 필드 덮어쓰기는 막지만, manifest_sha256·manifest_entries·g3_receipt_id·artifacts 등 정상 소유 경로가 전달하는 값은 그대로 받는다.

`manifest.build`와 `manifest.extend`는 검증·렌더 없이 파일을 봉인할 수 있다(`scripts/manifest.py:61`, `:107`). 이어서 위 하위 기록 함수를 쓰면 실제 파일과 정확히 일치하는 결박값을 가진 성공 영수증을 만들 수 있다. `manifest._check_final_report`는 이 영수증들과 해시를 신뢰하므로(`:165`, `:170`, `:175`), `finalize_report`는 이를 정상 최종 출고로 승인한다(`:184`, `:187`, `:197`).

### 재현 절차

저장소 디렉터리에서 Python을 실행하고 아래 코드를 사용한다. 기존 테스트의 합성 work 픽스처만 재사용하며, 각 시나리오는 별도 임시 폴더에서 실행된다. 원장에 직접 쓰거나 소스·함수를 변경하지 않는다.

```python
import json
import sys
import tempfile
from pathlib import Path

repo = Path.cwd()
sys.path[:0] = [str(repo / "scripts"), str(repo / "tests")]
import gates
import manifest
import verify_facts
import test_p0_regressions as fixtures

for scenario in ("failed_g3", "skipped_render"):
    with tempfile.TemporaryDirectory(prefix="astra-rereview-") as td:
        wp = fixtures.work.__wrapped__(Path(td))
        fixtures.start_chain(wp)  # 정상 G0 → G1 → [2]

        if scenario == "failed_g3":
            wp.report_md.write_text(
                fixtures.EXPANDED + "\n\n![](_captures/E001.png)\n",
                encoding="utf-8",
            )
            checked = verify_facts.verify_and_record(wp)
            assert not checked["verification"]["ok"]
            assert checked["receipt"]["exit"] == 1

            sealed = manifest.build(wp, for_g3=True)
            g3 = gates._record_script_result(
                wp, "G3", 0, "without PASS",
                extra={
                    "manifest_sha256": gates.sha256_file(wp.manifest),
                    "manifest_entries": len(sealed["entries"]),
                },
            )
        else:
            checked = verify_facts.verify_and_record(wp)
            assert checked["verification"]["ok"]
            g3 = checked["receipt"]

        wp.report_pdf.write_bytes(b"%PDF-1.4 fabricated")
        sealed = manifest.extend(
            wp, [wp.report_pdf], expected_sha256=g3["manifest_sha256"],
        )
        gates._record_script_result(
            wp, "[4b]", 0, "without render",
            extra={
                "manifest_sha256": gates.sha256_file(wp.manifest),
                "g3_receipt_id": gates._receipt_id(g3),
                "g3_result_summary_sha256": g3["result_summary_sha256"],
                "artifacts": [
                    {"path": rel, "sha256": gates.sha256_file(wp.root / rel)}
                    for rel in sealed["extended"][-1]["added"]
                ],
            },
        )
        gates.record_manual(
            wp, "G4", "review declaration", refs=["report.pdf"],
        )
        final = manifest.finalize_report(wp)
        print(json.dumps({
            "scenario": scenario,
            "actual_g3_ok": checked["verification"]["ok"],
            "render_executed": False,
            "pdf_size": wp.report_pdf.stat().st_size,
            "final_ok": final["ok"],
            "publication_state": final["publication_state"],
            "g5_current": bool(gates.successful_receipt(wp, "G5")),
        }, ensure_ascii=False))
```

실제 실행 결과:

```json
{"scenario":"failed_g3","actual_g3_ok":false,"render_executed":false,"pdf_size":19,"final_ok":true,"publication_state":"최종","g5_current":true}
{"scenario":"skipped_render","actual_g3_ok":true,"render_executed":false,"pdf_size":19,"final_ok":true,"publication_state":"최종","g5_current":true}
```

A의 실제 검증 실패 사유는 “현재 본문에 sentence_text 없음 — 문장 변경 후 재검토 필요”와 “검토 누락(1건)”이었다. 실패 이력까지 남긴 뒤 하위 API가 새 성공 영수증을 발급했으므로, 실패 영수증 보존만으로는 이 우회가 차단되지 않는다. B는 G3를 실제 통과시켰으며 render/render_and_record를 전혀 실행하지 않았다.

추가된 부정 테스트는 `scripts/gates.py`의 하위 함수가 아니라 거부 처리된 `_record_owned_result`만 공격한다(`tests/test_p0_regressions.py:549`, `:556`, `:577`). 따라서 해당 테스트의 통과는 이 변종 차단을 입증하지 않는다.

## 필요한 수정과 2차 변경 회귀 판정

- 소유 작업 없이 성공을 발급하는 하위 기록 진입점까지 닫아야 한다. 정상 API와 언더스코어 함수 조합도 검토 범위이므로, 함수명 변경이나 내부용 선언으로 해결됐다고 볼 수 없다. G3/[4b] 성공 발급이 실제 소유 작업의 PASS 없이 진행되지 않도록 기록 구조를 묶고, G5도 최종 검사 생략 경로를 남기지 않아야 한다.
- 위 두 변종을 부정 회귀로 추가해, 하위 기록 함수 직접 호출 이후에도 유효한 성공 영수증과 최종 승인이 생기지 않는지 검증해야 한다.
- 2차 diff에서 위 미해소 문제 외에 별도의 정상 경로 회귀나 기존 해소 항목의 새로운 퇴행은 확인하지 못했다. 새 정상 진입점은 기존 verify/render 구현을 재사용하고 실패 기록을 남긴다. 이 판단은 제공된 테스트 결과와 2차 변경 범위의 코드 검토에 한정하며, 이미 해소된 항목을 다시 전면 검증한 결과는 아니다.

ASTRA_REREVIEW_DONE verdict=REQUEST_CHANGES
