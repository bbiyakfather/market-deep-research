"""install.py — 개발본을 설치본(~/.claude/skills/<name>/)으로 해시검증 복사.

allowlist SKILLS 만 설치한다. 소스 루트는 SKILL_ROOT.parent(개발본 codes/) 아래
각 이름 폴더이고, 설치 대상은 <skills_parent>/<name>/. --target 은 스킬 폴더가
아니라 **스킬 부모 디렉터리**(기본 ~/.claude/skills)다. 구 호출처럼 단일 스킬
경로(그 안에 SKILL.md 가 바로 있는 경로)를 넘기면 에러.

SKILL.md · references/ · scripts/ · assets/ 를 복사하고 각 파일 SHA-256 을 원본과 대조.
없는 INCLUDE 항목은 건너뛴다(mdr-search 처럼 SKILL.md 만 있는 스킬, mdr-hwpx 처럼 SKILL.md+references 도 설치됨).
__pycache__ · *.pyc · 작업폴더(research_*) 는 제외. allowlist 밖 ~/.claude/skills/*
는 사용자 스킬이므로 건드리지 않는다.

CLI: python install.py                 # 기본 부모 ~/.claude/skills
     python install.py --target <dir>  # 스킬 부모 디렉터리
     python install.py --dry-run
     python install.py --check         # 쓰지 않고 대조만(드리프트 감시, 불일치 시 exit 1)
     python install.py --help
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

from skill_paths import SKILL_ROOT

SKILLS = ("market-deep-research", "mdr-search", "mdr-hwpx")
SOURCE_PARENT = SKILL_ROOT.parent
DEFAULT_TARGET = Path.home() / ".claude" / "skills"
INCLUDE = ["SKILL.md", "references", "scripts", "assets", "profiles"]   # profiles: mdr-hwpx 양식 프로필
EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIX = {".pyc", ".tmp"}


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _sha_text(p: Path) -> str:
    """줄바꿈 정규화 해시 — 드리프트 대조 전용.

    install() 은 복사 직후 원본과 사본을 비교하므로 원바이트 해시가 맞다. 반면 --check 는
    시점이 다른 두 트리를 비교하는데, Windows 에서 git 이 체크아웃하며 LF→CRLF 로 바꾸면
    내용이 같은데도 전 파일이 불일치로 뜬다(실측: SKILL.md 내용 동일, CRLF 184 vs 178).
    매번 전건 불일치를 외치는 감시는 아무도 안 보게 되므로 줄바꿈은 차이로 세지 않는다.
    """
    h = hashlib.sha256()
    h.update(p.read_bytes().replace(b"\r\n", b"\n"))
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


def _skills_parent(target: Path | str) -> Path:
    """--target 은 스킬 부모 디렉터리. 그 안에 SKILL.md 가 바로 있으면 구 의미로 보고 거부."""
    parent = Path(target).resolve()
    if (parent / "SKILL.md").is_file():
        raise SystemExit(
            f"--target 은 스킬 부모 디렉터리를 넘기세요(예: {DEFAULT_TARGET}). "
            f"단일 스킬 경로입니다: {parent}"
        )
    return parent


def _source_of(name: str) -> Path:
    src = (SOURCE_PARENT / name).resolve()
    if not (src / "SKILL.md").is_file():
        raise SystemExit(f"allowlist 스킬 '{name}' 소스에 SKILL.md 가 없습니다: {src}")
    return src


def _install_one(src_root: Path, dest: Path, dry_run: bool) -> dict:
    src_root = src_root.resolve()
    dest = dest.resolve()
    if dest == src_root or src_root in dest.parents:
        raise SystemExit(f"설치 대상이 소스 루트와 같거나 그 하위 경로입니다: {dest}")

    # 기존 설치본(SKILL.md 존재)일 때만 나중에 stale 파일을 정리한다 — 임의 폴더 오폭 방지.
    was_existing_install = not dry_run and (dest / "SKILL.md").exists()

    copied, verified, failed, src_rel_set = [], [], [], set()
    for src in _iter_files(src_root):
        rel = src.relative_to(src_root)
        src_rel_set.add(str(rel))
        dst = dest / rel
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
        for existing in _iter_files(dest):                # 기존 EXCLUDE 규칙 재사용(스캔 오폭 방지)
            rel = str(existing.relative_to(dest))
            if rel not in src_rel_set:
                existing.unlink()
                removed.append(rel)

    return {"ok": not failed, "target": str(dest), "count": len(copied),
            "verified": len(verified), "failed": failed, "dry_run": dry_run, "removed": removed}


def _check_one(src_root: Path, dest: Path) -> dict:
    src_root = src_root.resolve()
    dest = dest.resolve()
    src = {str(p.relative_to(src_root)): p for p in _iter_files(src_root)}
    dst = {str(p.relative_to(dest)): p for p in _iter_files(dest)} if dest.exists() else {}
    missing = sorted(k for k in src if k not in dst)          # 설치본에 없음
    stale = sorted(k for k in dst if k not in src)            # 개발본에서 사라졌는데 남아있음
    differs = sorted(k for k in src if k in dst and _sha_text(src[k]) != _sha_text(dst[k]))
    return {"ok": not (missing or stale or differs), "target": str(dest),
            "count": len(src), "missing": missing, "stale": stale, "differs": differs}


def install(target: Path | str = DEFAULT_TARGET, dry_run: bool = False) -> dict:
    parent = _skills_parent(target)
    skills = {}
    for name in SKILLS:
        skills[name] = _install_one(_source_of(name), parent / name, dry_run=dry_run)
    return {"ok": all(v["ok"] for v in skills.values()), "skills": skills}


def check(target: Path | str = DEFAULT_TARGET) -> dict:
    """설치본이 개발본과 같은지 **쓰지 않고** 대조한다(드리프트 감시).

    install() 은 대조 전에 복사부터 하므로 "설치본이 최신인가"를 물을 수단이 못 된다 —
    물어보는 행위가 답을 바꿔버린다. 조사 직전에 이 명령으로 확인하면, 옛 코드로 조사가
    돌아가는 사고를 미리 잡는다. allowlist 에 있으나 설치본(SKILL.md)이 없으면
    missing_skills 로 보고한다. allowlist 밖 폴더는 스캔하지 않는다.
    """
    parent = _skills_parent(target)
    skills = {}
    missing_skills = []
    for name in SKILLS:
        dest = parent / name
        if not (dest / "SKILL.md").is_file():
            missing_skills.append(name)
        skills[name] = _check_one(_source_of(name), dest)
    return {"ok": (not missing_skills) and all(v["ok"] for v in skills.values()),
            "skills": skills, "missing_skills": missing_skills}


def demo() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        parent = Path(td)
        r = install(parent)
        assert r["ok"], f"설치 실패: {r}"
        core = r["skills"]["market-deep-research"]
        thin = r["skills"]["mdr-search"]
        hwpx = r["skills"]["mdr-hwpx"]
        core_tgt = Path(core["target"])
        thin_tgt = Path(thin["target"])
        hwpx_tgt = Path(hwpx["target"])

        assert (parent / "market-deep-research" / "SKILL.md").exists()
        assert (parent / "mdr-search" / "SKILL.md").exists()
        assert (parent / "mdr-hwpx" / "SKILL.md").exists()
        assert core_tgt / "SKILL.md" == parent / "market-deep-research" / "SKILL.md"
        assert hwpx_tgt / "SKILL.md" == parent / "mdr-hwpx" / "SKILL.md"
        assert (core_tgt / "scripts" / "facts_db.py").exists()
        assert core["verified"] == core["count"] and core["count"] > 10, core
        # __pycache__ 는 제외됐는지
        assert not list(core_tgt.rglob("__pycache__"))
        assert core["removed"] == [], core["removed"]

        # mdr-search 는 SKILL.md 1개로 설치
        assert thin["ok"] and thin["count"] == 1 and thin["verified"] == 1, thin
        thin_files = [p for p in thin_tgt.rglob("*") if p.is_file()]
        assert thin_files == [thin_tgt / "SKILL.md"], thin_files

        # mdr-hwpx 는 SKILL.md + references/ 가 설치됨(스크립트는 다른 워커가 채움)
        assert hwpx["ok"] and hwpx["verified"] == hwpx["count"] and hwpx["count"] >= 1, hwpx
        assert (hwpx_tgt / "SKILL.md").exists()

        # allowlist 밖 사용자 스킬 폴더는 건드리지 않는다
        outsider = parent / "user-skill" / "SKILL.md"
        outsider.parent.mkdir()
        outsider.write_text("keep", encoding="utf-8")

        # stale 파일 시드 + EXCLUDE 대상(__pycache__) 시드 후 재설치 → stale 만 정리
        stale = core_tgt / "scripts" / "zzz_stale.py"
        stale.write_text("stale", encoding="utf-8")
        keep = core_tgt / "scripts" / "__pycache__" / "keep.pyc"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_text("keep", encoding="utf-8")

        r2 = install(parent)
        assert r2["ok"], f"재설치 실패: {r2}"
        core2 = r2["skills"]["market-deep-research"]
        assert not stale.exists(), "stale 파일이 정리되지 않음"
        assert any(Path(x) == Path("scripts/zzz_stale.py") for x in core2["removed"]), core2["removed"]
        assert keep.exists(), "EXCLUDE 대상(__pycache__)이 오폭 삭제됨"
        assert outsider.exists(), "allowlist 밖 스킬 폴더가 삭제됨"

        # --check: 방금 설치한 직후는 일치, 파일을 건드리면 즉시 differs 로 잡혀야 한다
        c = check(parent)
        assert c["ok"] and not c["missing_skills"], c
        assert not (c["skills"]["market-deep-research"]["missing"]
                    or c["skills"]["market-deep-research"]["stale"]
                    or c["skills"]["market-deep-research"]["differs"]), c
        (core_tgt / "SKILL.md").write_text("변조", encoding="utf-8")
        c2 = check(parent)
        assert not c2["ok"] and "SKILL.md" in c2["skills"]["market-deep-research"]["differs"], c2
        (core_tgt / "scripts" / "facts_db.py").unlink()
        c3 = check(parent)
        assert any(Path(x) == Path("scripts/facts_db.py")
                   for x in c3["skills"]["market-deep-research"]["missing"]), c3

        # --check: allowlist 에 있으나 설치본 없음 → missing_skills
        empty = parent / "empty-parent"
        empty.mkdir()
        c_miss = check(empty)
        assert not c_miss["ok"] and list(c_miss["missing_skills"]) == list(SKILLS), c_miss

        # 구 --target 의미(SKILL.md 가 바로 있는 경로)는 부모를 넘기라는 에러
        try:
            install(SKILL_ROOT)
            assert False, "SKILL.md 직접 경로 거부 미작동"
        except SystemExit as e:
            assert "부모" in str(e), e

        # 자기복사 가드: 소스 부모(codes/)를 --target 으로 넘기면 dest==src
        try:
            install(SOURCE_PARENT)
            assert False, "자기복사 가드 미작동"
        except SystemExit:
            pass
    from datetime import datetime
    print(f"[{datetime.now().isoformat(timespec='seconds')}] install demo OK "
          f"(core {core['count']} + mdr-search {thin['count']} + mdr-hwpx {hwpx['count']} 파일 해시검증, stale 정리 포함)")


def _cli_target(args: list[str]) -> Path | str:
    return args[args.index("--target") + 1] if "--target" in args else DEFAULT_TARGET


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "demo":
        demo()
    elif "-h" in args or "--help" in args:
        print(__doc__.strip())
        sys.exit(0)
    elif "--check" in args:
        r = check(_cli_target(args))
        import json
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["ok"] else 1)
    else:
        r = install(_cli_target(args), dry_run="--dry-run" in args)
        import json
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["ok"] else 1)
