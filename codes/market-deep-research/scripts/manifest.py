"""manifest.py — 증거체인 SHA-256 매니페스트 기록·검증(plan-v2 핵심설계6 / G3·G5).

목적: source/capture/report/PDF/대장 파일의 해시를 고정해, G3 통과 이후 파일이 바뀌면
검출한다(변경 시 G3 재실행 트리거). 최종 PDF 무결성 재검사(G5)도 이 모듈로.

봉인 순서(G3 → [4b] → G5):
  build()  = G3 기준선. verify_facts.py CLI PASS 가 호출하고 G3 영수증에 manifest 해시를 결박한다.
  extend() = [4b] 재봉인. 기존 항목이 한 바이트도 안 바뀌었음을 먼저 확인한 뒤 렌더 산출물만
             **추가**한다(덮어쓰기 금지 — 덮어쓰면 G3 이후 변조가 새 기준선으로 세탁된다).
  verify() = 저장 항목을 경로로 직접 재해시(TRACKED 글롭 밖의 산출물도 추적) + 미봉인 신규 탐지.

CLI:
  python manifest.py build  <work_dir>   # 현재 상태 해시 기록 → manifest.json (G3 외 수동 호출은 비권장)
  python manifest.py verify <work_dir>   # [4b]·G4 영수증 확인 + [4b]↔manifest 결박 대조 후 저장본 대조,
                                         # 결과를 G5 로 자기기록(변경 시 exit 1)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import gates
from skill_paths import WorkPaths

# 해시 대상: (라벨, 상대경로 glob). 조사 산출물의 증거체인.
# audit/** 는 절대 추가하지 말 것 — G5c·G4 가 G3 이후에도 정상적으로 audit/ 에 쓰므로
# 추가하면 정상 경로가 매번 changed 로 잡혀 G3 무한 복귀가 된다(실측 확인됨).
TRACKED = [
    ("source", "_sources/**/*"),
    ("capture", "_captures/**/*"),
    ("assets", "assets/**/*"),        # report.pdf 에 --embed-resources 로 내장되는 생성 차트
    ("images", "_images/**/*"),       # 수확 도판 + IMAGES.md + harvest index.json — 본문 도판도 PDF 에 내장된다
    ("facts", "facts.jsonl"),
    ("evidence", "evidence.jsonl"),
    ("report_md", "report.md"),
    ("report_pdf", "report.pdf"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan(root: Path) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for label, pattern in TRACKED:
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                entries[rel] = {"label": label, "sha256": sha256_file(p), "size": p.stat().st_size}
    return entries


def build(work: WorkPaths | Path | str) -> dict:
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    manifest = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "root": wp.root.name,
        "entries": _scan(wp.root),
    }
    wp.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _load(wp: WorkPaths) -> dict:
    return json.loads(wp.manifest.read_text(encoding="utf-8"))


def _write(wp: WorkPaths, manifest: dict) -> None:
    wp.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _diff(wp: WorkPaths, stored: dict) -> dict:
    """저장 항목은 경로로 직접 재해시한다 — TRACKED 글롭에 안 잡히는 산출물(report.hwpx·custom.pdf)도
    일단 봉인됐으면 변조·삭제를 잡는다. 신규는 글롭 스캔으로만 본다."""
    changed, missing = [], []
    for rel, meta in stored.items():
        p = wp.root / rel
        if not p.is_file():
            missing.append(rel)
        elif sha256_file(p) != meta["sha256"]:
            changed.append(rel)
    new = [r for r in _scan(wp.root) if r not in stored]
    return {"changed": changed, "missing": missing, "new": new}


def extend(work: WorkPaths | Path | str, paths: list[Path | str], label: str = "render",
           expected_sha256: str | None = None) -> dict:
    """[4b] 재봉인: 기존 항목 불변 확인 후 ``paths`` 만 추가한다.

    ``expected_sha256`` 는 G3 영수증이 결박한 manifest.json 해시 — 다르면 G3 이후 누군가 기준선을
    다시 만든 것이므로 거부한다. 기존 항목이 하나라도 changed/missing 이면 거부한다(= G3 복귀).
    추가 경로는 작업폴더 내부의 실재 파일이어야 한다.
    """
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    if not wp.manifest.exists():
        raise ValueError("manifest.json 없음 — G3 기준선(build) 먼저")
    if expected_sha256 and sha256_file(wp.manifest).lower() != expected_sha256.lower():
        raise ValueError("manifest.json 이 G3 영수증의 기준선과 다름 — G3 이후 재빌드됨, G3 복귀")
    manifest = _load(wp)
    d = _diff(wp, manifest["entries"])
    if d["changed"] or d["missing"]:
        raise ValueError(f"기존 봉인 항목 변조/소실 — 재봉인 거부(G3 복귀): {d}")
    root = wp.root.resolve()
    added = []
    for raw in paths:
        p = Path(raw).resolve()
        if not p.is_file():
            raise ValueError(f"추가 대상 없음: {raw}")
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            raise ValueError(f"추가 대상이 작업폴더 밖: {raw}")
        manifest["entries"][rel] = {"label": label, "sha256": sha256_file(p), "size": p.stat().st_size}
        added.append(rel)
    manifest.setdefault("extended", []).append({"at": datetime.now().isoformat(timespec="seconds"),
                                                "added": added})
    _write(wp, manifest)
    return manifest


def verify(work: WorkPaths | Path | str) -> dict:
    """저장된 manifest.json 과 현재 파일 해시를 대조. changed/missing/new 를 반환."""
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    if not wp.manifest.exists():
        return {"ok": False, "reason": "manifest.json 없음", "changed": [], "missing": [], "new": []}
    d = _diff(wp, _load(wp)["entries"])
    ok = not (d["changed"] or d["missing"] or d["new"])   # 신규(미봉인) 파일도 실패 — render 산출물은 재봉인 필수
    return {"ok": ok, **d}


def demo() -> None:
    import tempfile
    from skill_paths import resolve_work_dir
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("매니페스트 데모", base=td)
        wp = WorkPaths(wd)
        (wp.sources / "a.txt").write_text("hello", encoding="utf-8")
        wp.facts.write_text('{"id":"F001"}\n', encoding="utf-8")
        m = build(wp)
        assert m["entries"], "스캔 결과 비어있음"
        assert verify(wp)["ok"], "빌드 직후 verify 는 ok 여야 함"

        (wp.sources / "a.txt").write_text("tampered", encoding="utf-8")   # 변조
        v = verify(wp)
        assert not v["ok"] and v["changed"], f"변조 미검출: {v}"
        (wp.sources / "a.txt").write_text("hello", encoding="utf-8")      # 원복(다음 단언 격리)

        # G3 build 이후 render_pdf 가 report.pdf 를 새로 만드는 상황 재현 — 재봉인 전엔 미봉인 신규
        # 파일로 잡혀 실패해야 한다(V06 회귀 가드).
        wp.report_pdf.write_bytes(b"%PDF-1.4 fake")
        v2 = verify(wp)
        assert not v2["ok"] and "report.pdf" in v2["new"], f"미봉인 신규 파일이 통과됨: {v2}"

        baseline_sha = sha256_file(wp.manifest)
        extend(wp, [wp.report_pdf], expected_sha256=baseline_sha)          # [4b] 재봉인 = 추가만
        assert verify(wp)["ok"], "재봉인 후에도 실패"
        assert _load(wp)["entries"]["_sources/a.txt"]["sha256"] == m["entries"]["_sources/a.txt"]["sha256"], \
            "extend 가 기존 항목을 건드림"

        # C1 회귀: G3 이후 대장을 변조하고 재봉인하면 거부돼야 한다(세탁 차단)
        wp.facts.write_text('{"id":"F001","tampered":1}\n', encoding="utf-8")
        (wp.root / "custom.pdf").write_bytes(b"%PDF custom")
        try:
            extend(wp, [wp.root / "custom.pdf"]); raise AssertionError("변조 후 재봉인이 통과됨")
        except ValueError as e:
            assert "변조" in str(e), e
        wp.facts.write_text('{"id":"F001"}\n', encoding="utf-8")           # 원복

        # 기준선이 재빌드됐으면(G3 영수증 해시와 불일치) 거부
        try:
            extend(wp, [wp.root / "custom.pdf"], expected_sha256="0" * 64); raise AssertionError("기준선 불일치 통과")
        except ValueError as e:
            assert "기준선" in str(e), e

        # C2 회귀: TRACKED 글롭 밖 산출물(custom.pdf)도 extend 로 봉인되면 변조를 잡는다
        extend(wp, [wp.root / "custom.pdf"])
        assert verify(wp)["ok"]
        (wp.root / "custom.pdf").write_bytes(b"%PDF custom tampered")
        v3 = verify(wp)
        assert not v3["ok"] and "custom.pdf" in v3["changed"], f"글롭 밖 산출물 변조 미검출: {v3}"
        (wp.root / "custom.pdf").unlink()
        assert "custom.pdf" in verify(wp)["missing"]

        # 작업폴더 밖 경로는 거부
        outside = Path(td) / "outside.pdf"; outside.write_bytes(b"x")
        try:
            extend(wp, [outside]); raise AssertionError("폴더 밖 산출물 봉인 통과")
        except ValueError:
            pass
    print(f"[{datetime.now().isoformat(timespec='seconds')}] manifest demo OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif args[0] == "build" and len(args) == 2:
        m = build(args[1]); print(f"기록: {len(m['entries'])} 항목 → manifest.json")
    elif args[0] == "verify" and len(args) == 2:
        wp = WorkPaths(args[1])
        try:
            reseal = gates.require_receipt(wp, "[4b]")
            checked = gates.check_gate(wp, "G5")          # G5 선행 = G4(팀리드 육안검증)
            if not checked["ok"]:
                raise gates.GateError("; ".join(checked["issues"]))
            # [4b] 가 봉인한 manifest 그대로인지 — 영수증 이후 manifest 를 다시 build 해 변조를
            # 새 기준선으로 세탁하는 경로를 막는다(C1).
            bound = reseal.get("manifest_sha256")
            if not bound:
                raise gates.GateError("[4b] 영수증에 manifest_sha256 결박 없음(구버전) — render_pdf.py 재실행")
            if not wp.manifest.is_file() or sha256_file(wp.manifest).lower() != str(bound).lower():
                raise gates.GateError("manifest.json 이 [4b] 영수증 결박과 다름 — [4b] 이후 재봉인/변조")
        except gates.GateError as exc:
            print(f"[G5] 전제조건 미충족: {exc}", file=sys.stderr)
            sys.exit(1)
        v = verify(wp)
        # 검증 결과 자체를 G5 영수증으로 남긴다 — PASS 만 기록하면 실패 이력이 원장에서 사라진다
        gates.record_script_result(wp, "G5", 0 if v["ok"] else 1,
                                   json.dumps(v, ensure_ascii=False, sort_keys=True), wp.facts)
        print(json.dumps(v, ensure_ascii=False, indent=2))
        sys.exit(0 if v["ok"] else 1)
    else:
        print(__doc__); sys.exit(2)
