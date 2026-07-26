"""install.py — 개발본을 설치본(~/.claude/skills/market-deep-research/)으로 해시검증 복사.

SKILL.md · references/ · scripts/ · assets/ 를 복사하고 각 파일 SHA-256 을 원본과 대조.
__pycache__ · *.pyc · 작업폴더(research_*) 는 제외.

CLI: python install.py            # 기본 대상 ~/.claude/skills/market-deep-research
     python install.py --target <dir>
     python install.py --dry-run
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

from skill_paths import SKILL_ROOT

DEFAULT_TARGET = Path.home() / ".claude" / "skills" / "market-deep-research"
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
    target = Path(target).resolve()
    src_root = SKILL_ROOT.resolve()
    if target == src_root or src_root in target.parents:
        raise SystemExit(f"설치 대상이 소스 루트와 같거나 그 하위 경로입니다: {target}")

    # 기존 설치본(SKILL.md 존재)일 때만 나중에 stale 파일을 정리한다 — 임의 폴더 오폭 방지.
    was_existing_install = not dry_run and (target / "SKILL.md").exists()

    copied, verified, failed, src_rel_set = [], [], [], set()
    for src in _iter_files(SKILL_ROOT):
        rel = src.relative_to(SKILL_ROOT)
        src_rel_set.add(str(rel))
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

    removed = []
    if was_existing_install:
        for existing in _iter_files(target):                # 기존 EXCLUDE 규칙 재사용(스캔 오폭 방지)
            rel = str(existing.relative_to(target))
            if rel not in src_rel_set:
                existing.unlink()
                removed.append(rel)

    return {"ok": not failed, "target": str(target), "count": len(copied),
            "verified": len(verified), "failed": failed, "dry_run": dry_run, "removed": removed}


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "install-test"
        r = install(target)
        assert r["ok"], f"설치 실패: {r['failed']}"
        assert (Path(r["target"]) / "SKILL.md").exists()
        assert (Path(r["target"]) / "scripts" / "facts_db.py").exists()
        assert r["verified"] == r["count"] and r["count"] > 10, r
        # __pycache__ 는 제외됐는지
        assert not list((Path(r["target"])).rglob("__pycache__"))
        assert r["removed"] == [], r["removed"]

        # stale 파일 시드 + EXCLUDE 대상(__pycache__) 시드 후 재설치 → stale 만 정리
        stale = target / "scripts" / "zzz_stale.py"
        stale.write_text("stale", encoding="utf-8")
        keep = target / "scripts" / "__pycache__" / "keep.pyc"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_text("keep", encoding="utf-8")

        r2 = install(target)
        assert r2["ok"], f"재설치 실패: {r2['failed']}"
        assert not stale.exists(), "stale 파일이 정리되지 않음"
        assert any(Path(x) == Path("scripts/zzz_stale.py") for x in r2["removed"]), r2["removed"]
        assert keep.exists(), "EXCLUDE 대상(__pycache__)이 오폭 삭제됨"

        # 자기복사 가드: 소스==타깃이면 SystemExit
        try:
            install(SKILL_ROOT)
            assert False, "자기복사 가드 미작동"
        except SystemExit:
            pass
    from datetime import datetime
    print(f"[{datetime.now().isoformat(timespec='seconds')}] install demo OK ({r['count']} 파일 해시검증, stale 정리 포함)")


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
