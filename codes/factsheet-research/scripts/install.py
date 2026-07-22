"""install.py — 개발본을 설치본(~/.claude/skills/factsheet-research/)으로 해시검증 복사.

SKILL.md · references/ · scripts/ · assets/ 를 복사하고 각 파일 SHA-256 을 원본과 대조.
__pycache__ · *.pyc · 작업폴더(research_*) 는 제외.

CLI: python install.py            # 기본 대상 ~/.claude/skills/factsheet-research
     python install.py --target <dir>
     python install.py --dry-run
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

from skill_paths import SKILL_ROOT

DEFAULT_TARGET = Path.home() / ".claude" / "skills" / "factsheet-research"
INCLUDE = ["SKILL.md", "references", "scripts", "assets"]
EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIX = {".pyc", ".tmp"}


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _iter_files(root: Path):
    for item in INCLUDE:
        src = root / item
        if src.is_file():
            yield src
        elif src.is_dir():
            for p in src.rglob("*"):
                if p.is_file() and not (set(p.parts) & EXCLUDE_DIRS) and p.suffix not in EXCLUDE_SUFFIX:
                    yield p


def install(target: Path | str = DEFAULT_TARGET, dry_run: bool = False) -> dict:
    target = Path(target)
    copied, verified, failed = [], [], []
    for src in _iter_files(SKILL_ROOT):
        rel = src.relative_to(SKILL_ROOT)
        dst = target / rel
        if dry_run:
            copied.append(str(rel)); continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(rel))
        if _sha(src) == _sha(dst):
            verified.append(str(rel))
        else:
            failed.append(str(rel))
    return {"ok": not failed, "target": str(target), "count": len(copied),
            "verified": len(verified), "failed": failed, "dry_run": dry_run}


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r = install(Path(td) / "install-test")
        assert r["ok"], f"설치 실패: {r['failed']}"
        assert (Path(r["target"]) / "SKILL.md").exists()
        assert (Path(r["target"]) / "scripts" / "facts_db.py").exists()
        assert r["verified"] == r["count"] and r["count"] > 10, r
        # __pycache__ 는 제외됐는지
        assert not list((Path(r["target"])).rglob("__pycache__"))
    from datetime import datetime
    print(f"[{datetime.now().isoformat(timespec='seconds')}] install demo OK ({r['count']} 파일 해시검증)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "demo":
        demo()
    else:
        tgt = args[args.index("--target") + 1] if "--target" in args else DEFAULT_TARGET
        r = install(tgt, dry_run="--dry-run" in args)
        import json
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["ok"] else 1)
