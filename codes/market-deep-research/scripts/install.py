"""install.py — 개발본을 설치본(~/.claude/skills/market-deep-research/)으로 해시검증 복사.

SKILL.md · references/ · scripts/ · assets/ 를 복사하고 각 파일 SHA-256 을 원본과 대조.
__pycache__ · *.pyc · 작업폴더(research_*) 는 제외.

CLI: python install.py            # 기본 대상 ~/.claude/skills/market-deep-research
     python install.py --target <dir>
     python install.py --dry-run
     python install.py --check     # 설치 없이 드리프트만 대조(불일치 시 exit 1)
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


def _content_sha(p: Path) -> str:
    """줄바꿈 정규화 해시. git 이 체크아웃 때 CRLF 로 바꿔놓는 탓에 바이트 해시로 대조하면
    내용이 같은 파일이 전부 '변경'으로 뜬다 — 거짓 경보가 나는 가드는 곧 무시되는 가드다."""
    b = p.read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def check(target: Path | str = DEFAULT_TARGET) -> dict:
    """저장소↔설치본 드리프트 대조(읽기전용). 설치본이 정본보다 뒤처지면 새 방어가
    '넣었다'고 기록되는데 라이브에는 없는 상태가 된다 — 그 침묵을 깨는 가드."""
    target = Path(target).resolve()
    if not (target / "SKILL.md").exists():
        return {"ok": False, "target": str(target), "installed": False,
                "changed": [], "missing": [], "extra": []}
    src_rel = {str(p.relative_to(SKILL_ROOT)): _content_sha(p) for p in _iter_files(SKILL_ROOT)}
    dst_rel = {str(p.relative_to(target)): _content_sha(p) for p in _iter_files(target)}
    changed = sorted(r for r, h in src_rel.items() if r in dst_rel and dst_rel[r] != h)
    missing = sorted(r for r in src_rel if r not in dst_rel)          # 설치본에 없음
    extra = sorted(r for r in dst_rel if r not in src_rel)            # 설치본에만 있음
    return {"ok": not (changed or missing or extra), "target": str(target),
            "installed": True, "changed": changed, "missing": missing, "extra": extra}


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

        # --check: 방금 설치했으니 동기 상태여야 하고, 변조하면 그 경로가 잡혀야 한다
        c0 = check(target)
        assert c0["ok"] and c0["installed"], c0
        # 줄바꿈만 다른 파일은 드리프트가 아니다(git 체크아웃이 CRLF 로 바꾸는 것 때문에
        # 거짓 경보가 나면 가드 자체가 무시된다)
        tgt_md = target / "SKILL.md"
        tgt_md.write_bytes(tgt_md.read_bytes().replace(b"\r\n", b"\n"))
        assert check(target)["ok"], "줄바꿈 차이가 드리프트로 오보됨"
        (target / "scripts" / "facts_db.py").write_text("tampered", encoding="utf-8")
        c1 = check(target)
        assert not c1["ok"] and "scripts/facts_db.py" in [p.replace("\\", "/") for p in c1["changed"]], c1
        (target / "SKILL.md").unlink()
        c2 = check(target)
        assert not c2["installed"], "SKILL.md 부재인데 설치본으로 인식"
    from datetime import datetime
    print(f"[{datetime.now().isoformat(timespec='seconds')}] install demo OK ({r['count']} 파일 해시검증, stale 정리 포함)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "demo":
        demo()
    else:
        import json
        tgt = args[args.index("--target") + 1] if "--target" in args else DEFAULT_TARGET
        if "--check" in args:
            r = check(tgt)
            print(json.dumps(r, ensure_ascii=False, indent=2))
            if not r["installed"]:
                print("설치본 없음 — python install.py 로 먼저 설치하십시오.", file=sys.stderr)
            elif not r["ok"]:
                print(f"드리프트: 변경 {len(r['changed'])} · 설치본 누락 {len(r['missing'])} "
                      f"· 설치본 잉여 {len(r['extra'])} → python install.py 로 재동기화",
                      file=sys.stderr)
            sys.exit(0 if r["ok"] else 1)
        r = install(tgt, dry_run="--dry-run" in args)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["ok"] else 1)
