"""install.py — market-research-assistant 스킬 해시검증 설치기.

개발본(이 파일이 있는 폴더) → 설치본 `~/.claude/skills/market-research-assistant/`
로 복사하되, 각 단계에서 SHA-256을 대조해 변조·부분복사를 차단한다.

절차(install):
  ① 개발본 파일별 SHA-256 계산
  ② 설치 위치와 같은 볼륨의 임시 스테이징 폴더에 복사
  ③ 스테이징 재해시로 원본과 대조 — 불일치 시 중단·정리·exit 1
  ④ 통과 시 원자적 교체(기존 설치본은 .bak 백업 후 os.replace 스왑)
  ⑤ 설치본 재해시 최종 대조 + install-manifest.json(파일·해시 목록) 기록

대상: SKILL.md · references/** · scripts/**/*.py · assets/**
제외: tests/ · __pycache__ · .pytest_cache · install.py 자신 · *.pyc

CLI:
    python install.py                  # 실설치
    python install.py --dry-run        # 복사 없이 대상 파일·해시 목록만 출력
    python install.py --verify         # 기존 설치본 vs 개발본 해시 대조만
    python install.py --selfcheck      # 가짜 설치 대상으로 내부 자기검증
"""
from __future__ import annotations

import sys
from pathlib import Path

# scripts/ 를 경로에 넣어 skill_paths(UTF-8 부트스트랩)·manifest(sha256_file) 재사용
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
import skill_paths  # noqa: E402,F401  (import 시 UTF-8 콘솔 부트스트랩 1회)
from manifest import sha256_file  # noqa: E402  (검증된 SHA-256 헬퍼 재사용)

import json  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
from datetime import datetime, timezone  # noqa: E402


SKILL_NAME = "market-research-assistant"
MANIFEST_NAME = "install-manifest.json"
_EXCLUDE_DIR_PARTS = {"__pycache__", ".pytest_cache"}


class InstallError(RuntimeError):
    """설치 중단 사유(해시 불일치·부분복사·개발본 손상 등)."""


def dev_root() -> Path:
    """개발본 루트 = 이 install.py 가 있는 폴더(스킬 루트)."""
    return Path(__file__).resolve().parent


def install_root() -> Path:
    return Path.home() / ".claude" / "skills" / SKILL_NAME


def _walk(base: Path) -> list[Path]:
    """base 하위 전 파일(재귀). __pycache__/.pytest_cache/*.pyc 제외."""
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        if _EXCLUDE_DIR_PARTS & set(p.parts) or p.suffix == ".pyc":
            continue
        out.append(p)
    return out


def source_files(dev: Path) -> list[str]:
    """설치 대상 파일들의 개발본 상대경로(POSIX) 정렬 목록."""
    files: list[Path] = []
    skill_md = dev / "SKILL.md"
    if skill_md.is_file():
        files.append(skill_md)
    files += _walk(dev / "references")
    files += _walk(dev / "assets")
    for p in sorted((dev / "scripts").rglob("*.py")):
        if not (_EXCLUDE_DIR_PARTS & set(p.parts)):
            files.append(p)
    rels = sorted({p.relative_to(dev).as_posix() for p in files})
    if "SKILL.md" not in rels:
        raise InstallError(f"개발본 손상: SKILL.md 없음 ({dev})")
    return rels


def hash_tree(root: Path, rels: list[str]) -> dict[str, str]:
    """root 기준 rels 각 파일의 SHA-256. 없는 파일은 sentinel 로 표기."""
    return {rel: (sha256_file(root / rel) if (root / rel).is_file() else "<MISSING>")
            for rel in rels}


def compare(expected: dict[str, str], root: Path) -> list[dict]:
    """expected(rel→hash) 대비 root 실제 파일의 변경 목록(missing|modified)."""
    changes = []
    for rel, want in expected.items():
        p = root / rel
        if not p.is_file():
            changes.append({"path": rel, "status": "missing"})
        elif sha256_file(p) != want:
            changes.append({"path": rel, "status": "modified"})
    return changes


def _copy_into(dev: Path, staging: Path, rels: list[str]) -> None:
    for rel in rels:
        dst = staging / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dev / rel, dst)  # 메타데이터(mtime) 보존


def _manifest(dev: Path, rels: list[str], hashes: dict[str, str]) -> dict:
    return {
        "skill": SKILL_NAME,
        "installed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": str(dev),
        "python": sys.version.split()[0],
        "files": [{"path": rel, "sha256": hashes[rel], "bytes": (dev / rel).stat().st_size}
                  for rel in rels],
    }


def do_install(dev: Path, target: Path, *, _tamper=None) -> dict:
    """dev → target 해시검증 설치. 실패 시 InstallError(스테이징 정리, target 무손상).

    _tamper(staging): selfcheck 전용 seam — 복사 후·재해시 전에 스테이징을 변조.
    """
    rels = source_files(dev)
    dev_hashes = hash_tree(dev, rels)

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".install-staging-{target.name}-{os.getpid()}"
    bak = target.parent / f"{target.name}.bak"
    if staging.exists():
        shutil.rmtree(staging)
    try:
        # ② 스테이징 복사
        _copy_into(dev, staging, rels)
        if _tamper is not None:
            _tamper(staging)
        # ③ 스테이징 재해시 대조 (변조·부분복사 차단)
        changes = compare(dev_hashes, staging)
        if changes:
            raise InstallError(f"스테이징 해시 불일치 {len(changes)}건: {changes}")
        # ⑤(선) install-manifest.json 을 스테이징에 기록 → 원자 스왑에 포함
        (staging / MANIFEST_NAME).write_text(
            json.dumps(_manifest(dev, rels, dev_hashes), ensure_ascii=False, indent=2),
            encoding="utf-8")
        # ④ 원자적 교체: 기존 설치본 .bak 백업 후 스왑(같은 볼륨 → os.replace 원자)
        if target.exists():
            if bak.exists():
                shutil.rmtree(bak)
            os.replace(target, bak)
        os.replace(staging, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    # ⑤ 설치본 최종 재해시 대조
    final = compare(dev_hashes, target)
    if final:
        raise InstallError(f"설치본 최종 대조 실패 {len(final)}건: {final}")
    return {"target": target, "files": rels, "backup": bak if bak.exists() else None}


# --- CLI 동작 -------------------------------------------------------------
def _run_dry(dev: Path) -> int:
    rels = source_files(dev)
    hashes = hash_tree(dev, rels)
    print(f"[dry-run] 개발본: {dev}")
    print(f"[dry-run] 설치 대상 {len(rels)}개 파일 (복사 안 함):")
    for rel in rels:
        print(f"  {hashes[rel][:12]}  {rel}")
    return 0


def _run_verify(dev: Path, target: Path) -> int:
    if not target.exists():
        print(f"VERIFY: 설치본 없음 ({target})")
        return 1
    rels = source_files(dev)
    dev_hashes = hash_tree(dev, rels)
    changes = compare(dev_hashes, target)
    installed = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    extra = sorted(installed - set(rels) - {MANIFEST_NAME})
    if changes or extra:
        print(f"VERIFY: 불일치 (변경 {len(changes)}, 추가 {len(extra)})")
        for c in changes:
            print(f"  [{c['status']}] {c['path']}")
        for e in extra:
            print(f"  [extra] {e}")
        return 1
    print(f"VERIFY: OK ({len(rels)}개 파일 해시 일치)")
    return 0


def _run_install(dev: Path, target: Path) -> int:
    res = do_install(dev, target)
    print(f"설치 완료: {target}")
    print(f"  파일 {len(res['files'])}개 + {MANIFEST_NAME}")
    if res["backup"]:
        print(f"  기존 설치본 백업: {res['backup']}")
    return 0


def _selfcheck() -> int:
    import tempfile

    dev = dev_root()
    rels = source_files(dev)
    assert "SKILL.md" in rels and any(r.startswith("scripts/") for r in rels), rels

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # ① 정상 설치 성공 + 해시 일치
        target = base / "skills" / SKILL_NAME
        do_install(dev, target)
        assert (target / "SKILL.md").is_file(), "SKILL.md 미설치"
        assert (target / MANIFEST_NAME).is_file(), "manifest 미기록"
        assert compare(hash_tree(dev, rels), target) == [], "설치본 해시 불일치"
        # install.py 자신은 설치본에 없어야(제외 규칙)
        assert not (target / "install.py").exists(), "install.py 가 복사됨"
        # tests/ 도 제외
        assert not (target / "tests").exists(), "tests/ 가 복사됨"

        # ② 스테이징 1개 파일 변조 시 중단 + 원본 설치본 무손상
        sentinel = sha256_file(target / "SKILL.md")

        def tamper(staging: Path) -> None:
            (staging / "SKILL.md").write_bytes(b"TAMPERED")

        raised = False
        try:
            do_install(dev, target, _tamper=tamper)
        except InstallError:
            raised = True
        assert raised, "변조를 탐지하지 못함"
        assert sha256_file(target / "SKILL.md") == sentinel, "변조 시 기존 설치본 손상됨"
        # 스테이징 잔재 없음
        leftovers = list(target.parent.glob(".install-staging-*"))
        assert leftovers == [], f"스테이징 잔재: {leftovers}"

        # ③ --dry-run 이 파일시스템 무변경
        fresh = base / "skills2" / SKILL_NAME
        before = fresh.exists()
        _run_dry(dev)
        assert fresh.exists() == before, "--dry-run 이 파일시스템을 변경함"
        assert not fresh.exists(), "--dry-run 이 대상을 생성함"

    print("SELFCHECK OK")
    return 0


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="install", description="market-research-assistant 해시검증 설치기")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="복사 없이 대상 파일·해시 목록만 출력")
    g.add_argument("--verify", action="store_true", help="기존 설치본 vs 개발본 해시 대조만")
    g.add_argument("--selfcheck", action="store_true", help="가짜 설치 대상으로 내부 자기검증")
    p.add_argument("--target", default=None, help="설치 위치 override(기본=~/.claude/skills/...)")
    args = p.parse_args(argv)

    dev = dev_root()
    target = Path(args.target).expanduser().resolve() if args.target else install_root()
    try:
        if args.selfcheck:
            return _selfcheck()
        if args.dry_run:
            return _run_dry(dev)
        if args.verify:
            return _run_verify(dev, target)
        return _run_install(dev, target)
    except InstallError as e:
        print(f"설치 중단: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
