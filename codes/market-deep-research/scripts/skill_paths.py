"""skill_paths.py — 스킬 루트 및 조사 작업폴더 경로 해석 공통 모듈.

모든 스크립트가 이 모듈을 import 해서 경로를 얻는다(경로 하드코딩 금지).
스킬 루트는 이 파일(scripts/skill_paths.py)의 부모의 부모로 해석하므로,
작업 디렉터리가 어디든(조사 실행 폴더 등) 스킬 자원(references/·assets/)을 찾는다.

작업폴더 구조(조사 실행 시 생성):
  research_<slug>_<YYYYMMDD>/
    _sources/        원본 스냅샷 + 정제본 + sha256
    _research/       에이전트별 raw 산출물 보존(읽기전용 취급)
    _captures/       source_capture(증빙 인정)
    _reconstructed/  재구성 발췌(내부용, 증빙 불인정)
    assets/          차트·이미지 등 생성 자산
    audit/           내부 감사 번들 + 세션 저널
    facts.jsonl      사실 대장
    evidence.jsonl   증거 대장
    manifest.json    증거체인 해시
"""
from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

# --- 스킬 루트 ---------------------------------------------------------------
SKILL_ROOT = Path(__file__).resolve().parent.parent          # .../market-deep-research/
REFERENCES = SKILL_ROOT / "references"
ASSETS = SKILL_ROOT / "assets"
SCRIPTS = SKILL_ROOT / "scripts"

# 작업폴더 하위 디렉터리 이름(단일 진실원)
WORK_SUBDIRS = ("_sources", "_research", "_captures", "_reconstructed", "assets", "audit")


def slugify(topic: str, maxlen: int = 40) -> str:
    """주제 문자열을 폴더명 안전 slug로. 한글은 보존(Windows 허용), 금지문자만 제거."""
    s = topic.strip()
    s = re.sub(r'[\\/:*?"<>|]', "", s)      # Windows 금지문자
    s = re.sub(r"\s+", "_", s)
    return s[:maxlen].strip("_") or "untitled"


def work_dir_name(topic: str, on: date | None = None) -> str:
    on = on or date.today()
    return f"research_{slugify(topic)}_{on:%Y%m%d}"


def resolve_work_dir(topic: str, base: Path | str | None = None,
                     on: date | None = None, create: bool = True) -> Path:
    """조사 작업폴더 경로를 해석(기본: 현재 작업 디렉터리 아래). create=True면 하위 폴더까지 생성."""
    base = Path(base) if base else Path.cwd()
    wd = base / work_dir_name(topic, on)
    if create:
        for sub in WORK_SUBDIRS:
            (wd / sub).mkdir(parents=True, exist_ok=True)
    return wd


class WorkPaths:
    """작업폴더 내부 산출물 경로 모음. 스크립트들은 이 객체로 파일 위치를 공유한다."""

    def __init__(self, work_dir: Path | str):
        self.root = Path(work_dir)

    # 대장/매니페스트
    @property
    def facts(self) -> Path: return self.root / "facts.jsonl"
    @property
    def evidence(self) -> Path: return self.root / "evidence.jsonl"
    @property
    def manifest(self) -> Path: return self.root / "manifest.json"

    # 하위 폴더
    @property
    def sources(self) -> Path: return self.root / "_sources"
    @property
    def research(self) -> Path: return self.root / "_research"
    @property
    def captures(self) -> Path: return self.root / "_captures"
    @property
    def reconstructed(self) -> Path: return self.root / "_reconstructed"
    @property
    def gen_assets(self) -> Path: return self.root / "assets"
    @property
    def audit(self) -> Path: return self.root / "audit"

    # 세션 저널(audit 하위) — v3 감사저널 세트
    def journal(self, name: str) -> Path:
        """intent-diff.md / expansion-log.md / verification-economics.md / cause-disappearance.md 등."""
        return self.audit / name

    # 산출물
    @property
    def report_md(self) -> Path: return self.root / "report.md"
    @property
    def report_pdf(self) -> Path: return self.root / "report.pdf"


def _stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def demo() -> None:
    """self-check: 경로 해석이 스킬 루트를 정확히 가리키고, 작업폴더 구조가 생성되는지."""
    assert SKILL_ROOT.name == "market-deep-research", SKILL_ROOT
    assert (SKILL_ROOT / "scripts" / "skill_paths.py").exists()

    assert slugify("삼성전자 2024 매출 / 시장:규모?") == "삼성전자_2024_매출_시장규모"
    assert work_dir_name("PEM 수전해", date(2026, 7, 22)) == "research_PEM_수전해_20260722"

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wd = resolve_work_dir("테스트 주제", base=td, on=date(2026, 7, 22))
        for sub in WORK_SUBDIRS:
            assert (wd / sub).is_dir(), sub
        wp = WorkPaths(wd)
        assert wp.facts.name == "facts.jsonl"
        assert wp.journal("intent-diff.md").parent.name == "audit"
    print(f"[{_stamp()}] skill_paths demo OK  (SKILL_ROOT={SKILL_ROOT})")


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "demo":
        demo()
    else:
        print(resolve_work_dir(sys.argv[1], create=False))
