"""manifest.py — run manifest + SHA-256 증거 체인 고정/검증(G3·G5).

작업폴더를 스캔해 증거 파일들의 SHA-256을 manifest.json에 기록하고(update),
나중에 재해시로 대조해 변경을 탐지한다(verify). 변경이 있으면 exit 1 —
G3 재실행 트리거 신호다(파일이 게이트 이후 교체되면 검증을 다시 돌려야 한다).

스캔 대상: _sources/(source) _captures/(capture) _reconstructed/(reconstructed)
          facts.jsonl(facts) report.md(report) report.pdf(pdf)
(audit/ 는 내부 번들이라 증거 체인에서 제외.)

CLI:
    python manifest.py update <work_dir>   # 스캔 → manifest.json 기록
    python manifest.py verify <work_dir>   # 재해시 대조, 변경 있으면 exit 1
    python manifest.py --selfcheck
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_paths  # noqa: E402  (import 시 UTF-8 콘솔 부트스트랩 1회)

import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from datetime import datetime, timezone  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# 스캔 규칙: (하위폴더, category) — 폴더 내 모든 파일 재귀 / (파일명, category) — 단일 파일
_SCAN_DIRS = [("_sources", "source"), ("_captures", "capture"), ("_reconstructed", "reconstructed")]
_SCAN_FILES = [("facts.jsonl", "facts"), ("report.md", "report"), ("report.pdf", "pdf")]


def sha256_file(p, _buf: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(_buf), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_files(work) -> list[tuple[Path, str]]:
    work = Path(work)
    out: list[tuple[Path, str]] = []
    for d, cat in _SCAN_DIRS:
        base = work / d
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    out.append((p, cat))
    for fn, cat in _SCAN_FILES:
        p = work / fn
        if p.is_file():
            out.append((p, cat))
    return out


def _entry(work: Path, p: Path, cat: str) -> dict:
    return {
        "path": p.relative_to(work).as_posix(),  # 작업폴더 상대, / 구분자
        "sha256": sha256_file(p),
        "bytes": p.stat().st_size,
        "category": cat,
        "recorded_at": _now_iso(),
    }


def _fitz_version():
    try:
        import fitz  # PyMuPDF
        return getattr(fitz, "__version__", None) or getattr(fitz, "VersionBind", None)
    except Exception:
        return None


def _atomic_write_json(path: Path, obj: dict) -> None:
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def manifest_path(work) -> Path:
    return Path(work) / "manifest.json"


def update(work) -> dict:
    """작업폴더 스캔 → manifest.json 기록. run_id·created_at·gate_state는 기존값 보존."""
    work = Path(work)
    mpath = manifest_path(work)
    prev = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    man = {
        "run_id": prev.get("run_id") or work.name,
        "created_at": prev.get("created_at") or _now_iso(),
        "tool_versions": {"python": sys.version.split()[0], "fitz": _fitz_version()},
        "files": [_entry(work, p, cat) for p, cat in scan_files(work)],
        "gate_state": prev.get("gate_state") or {},
    }
    _atomic_write_json(mpath, man)
    return man


def verify(work) -> tuple[dict | None, list[dict]]:
    """기록된 해시와 현재 파일을 재해시 대조. 변경 목록 반환(modified|missing|added)."""
    work = Path(work)
    mpath = manifest_path(work)
    if not mpath.exists():
        return None, [{"path": "manifest.json", "status": "missing"}]
    man = json.loads(mpath.read_text(encoding="utf-8"))
    recorded = {e["path"]: e for e in man.get("files", [])}
    changes: list[dict] = []
    for rel, e in recorded.items():
        p = work / rel
        if not p.is_file():
            changes.append({"path": rel, "status": "missing"})
        elif sha256_file(p) != e["sha256"]:
            changes.append({"path": rel, "status": "modified"})
    current = {p.relative_to(work).as_posix() for p, _ in scan_files(work)}
    for rel in sorted(current - set(recorded)):
        changes.append({"path": rel, "status": "added"})
    return man, changes


# --- selfcheck ------------------------------------------------------------
def _selfcheck() -> int:
    import tempfile

    # ⑦ update → 파일 1개 변조 → verify가 정확히 그 파일만 변경 보고 + exit 1
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        (work / "_sources").mkdir()
        (work / "_captures").mkdir()
        (work / "_sources" / "a.pdf").write_bytes(b"source-A")
        (work / "_sources" / "b.pdf").write_bytes(b"source-B")
        (work / "_captures" / "E001.png").write_bytes(b"capture-1")
        (work / "facts.jsonl").write_text('{"kind":"fact"}\n', encoding="utf-8")

        man = update(work)
        paths = {e["path"] for e in man["files"]}
        assert paths == {"_sources/a.pdf", "_sources/b.pdf",
                         "_captures/E001.png", "facts.jsonl"}, paths
        assert manifest_path(work).exists()
        # 갓 만든 직후엔 변경 0
        _, changes = verify(work)
        assert changes == [], changes

        # 파일 1개만 변조
        (work / "_sources" / "b.pdf").write_bytes(b"source-B-TAMPERED")
        _, changes = verify(work)
        assert changes == [{"path": "_sources/b.pdf", "status": "modified"}], changes

        # run_id·created_at·gate_state 보존 확인
        man["gate_state"] = {"G3": "pass"}
        _atomic_write_json(manifest_path(work), man)
        man2 = update(work)
        assert man2["run_id"] == man["run_id"], (man2["run_id"], man["run_id"])
        assert man2["created_at"] == man["created_at"], man2["created_at"]
        assert man2["gate_state"] == {"G3": "pass"}, man2["gate_state"]

        # 파일 추가 탐지
        (work / "_captures" / "E002.png").write_bytes(b"capture-2")
        _, changes = verify(work)
        assert {"path": "_captures/E002.png", "status": "added"} in changes, changes

    print("SELFCHECK OK")
    return 0


# --- CLI ------------------------------------------------------------------
def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="manifest", description="run manifest + SHA-256 증거 체인")
    p.add_argument("--selfcheck", action="store_true", help="내부 자기검증")
    sub = p.add_subparsers(dest="cmd")
    sp = sub.add_parser("update", help="스캔 → manifest.json 기록")
    sp.add_argument("work_dir")
    sp = sub.add_parser("verify", help="재해시 대조(변경 있으면 exit 1)")
    sp.add_argument("work_dir")

    args = p.parse_args(argv)
    if args.selfcheck:
        return _selfcheck()

    if args.cmd == "update":
        man = update(args.work_dir)
        print(f"manifest 기록: {len(man['files'])}개 파일, run_id={man['run_id']}")
        return 0
    if args.cmd == "verify":
        man, changes = verify(args.work_dir)
        if changes:
            print(f"VERIFY: 변경 {len(changes)}건 (G3 재실행 필요)")
            for c in changes:
                print(f"  [{c['status']}] {c['path']}")
            return 1
        print("VERIFY: OK (변경 없음)")
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
