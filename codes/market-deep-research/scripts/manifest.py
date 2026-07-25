"""manifest.py — 증거체인 SHA-256 매니페스트 기록·검증(plan-v2 핵심설계6 / G3·G5).

목적: source/capture/report/PDF/대장 파일의 해시를 고정해, G3 통과 이후 파일이 바뀌면
검출한다(변경 시 G3 재실행 트리거). 최종 PDF 무결성 재검사(G5)도 이 모듈로.

CLI:
  python manifest.py build  <work_dir>   # 현재 상태 해시 기록 → manifest.json
  python manifest.py verify <work_dir>   # 저장본과 대조 → 변경/유실/신규 리포트(변경 시 exit 1)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from skill_paths import WorkPaths

# 해시 대상: (라벨, 상대경로 glob). 조사 산출물의 증거체인.
# audit/** 는 절대 추가하지 말 것 — G5c·G4 가 G3 이후에도 정상적으로 audit/ 에 쓰므로
# 추가하면 정상 경로가 매번 changed 로 잡혀 G3 무한 복귀가 된다(실측 확인됨).
TRACKED = [
    ("source", "_sources/**/*"),
    ("capture", "_captures/**/*"),
    ("assets", "assets/**/*"),        # report.pdf 에 --embed-resources 로 내장되는 생성 차트
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


def verify(work: WorkPaths | Path | str) -> dict:
    """저장된 manifest.json 과 현재 파일 해시를 대조. changed/missing/new 를 반환."""
    wp = work if isinstance(work, WorkPaths) else WorkPaths(work)
    if not wp.manifest.exists():
        return {"ok": False, "reason": "manifest.json 없음", "changed": [], "missing": [], "new": []}
    stored = json.loads(wp.manifest.read_text(encoding="utf-8"))["entries"]
    current = _scan(wp.root)
    changed = [r for r in stored if r in current and stored[r]["sha256"] != current[r]["sha256"]]
    missing = [r for r in stored if r not in current]
    new = [r for r in current if r not in stored]
    ok = not (changed or missing)          # 신규 추가만 있으면 무결성은 유지(경고만)
    return {"ok": ok, "changed": changed, "missing": missing, "new": new}


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

        (wp.captures / "E001.png").write_bytes(b"\x89PNG")                # 신규만
        build(wp)
        assert verify(wp)["ok"]
    print(f"[{datetime.now().isoformat(timespec='seconds')}] manifest demo OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "demo":
        demo()
    elif args[0] == "build" and len(args) == 2:
        m = build(args[1]); print(f"기록: {len(m['entries'])} 항목 → manifest.json")
    elif args[0] == "verify" and len(args) == 2:
        v = verify(args[1])
        print(json.dumps(v, ensure_ascii=False, indent=2))
        sys.exit(0 if v["ok"] else 1)
    else:
        print(__doc__); sys.exit(2)
