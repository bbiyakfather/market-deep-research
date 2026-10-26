"""preflight.py — G0 의존성/도구 점검. 미설치 계층은 "건너뜀+경고"로 진행(자체 스택이 보장 코어).

파이썬에서 감지 가능한 것만 본다(python 패키지 · CLI 바이너리).
브라우저(agent-browser CLI → playwright MCP → claude-in-chrome) · 무료 공공 MCP(opendart/KOSIS 등)는
런타임에서 오케스트레이터(Claude)가 도구 목록으로 확인한다 — 여기서는 "런타임 확인 필요"로만 표시.

HARD(없으면 exit 1): python>=3.10, fitz(PyMuPDF), pandoc, chrome.
SOFT(경고): curl_cffi, trafilatura, openpyxl, yt-dlp.
※ curl_cffi 는 사실상 필수 — 내장 우회(모바일 iOS 지문 등)가 전부 이 위에 얹혀 있다.

CLI: python preflight.py          # 리포트 출력, HARD 누락 시 exit 1
     python preflight.py --json   # JSON
     python preflight.py --check-help   # scripts/*.py 의 --help 종료코드 0 여부(선택 경고)
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HARD_PY = ["fitz"]
SOFT_PY = ["curl_cffi", "trafilatura", "openpyxl", "yt_dlp", "ddgs", "vl_convert"]  # vl_convert: make_chart SVG 렌더(없으면 사이드카만)
# 배포 이름(import 이름과 다른 것 포함). preflight 가 설치본 버전을 출력한다.
_VERSION_DISTS = (
    ("curl_cffi", "curl_cffi"),
    ("trafilatura", "trafilatura"),
    ("fitz", "PyMuPDF"),
    ("openpyxl", "openpyxl"),
    ("yt_dlp", "yt-dlp"),
    ("certifi", "certifi"),
)

_CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]


def _has_py(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def _find_chrome() -> str | None:
    for name in ("chrome", "chrome.exe", "google-chrome", "chromium"):
        p = shutil.which(name)
        if p:
            return p
    for c in _CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    return None


def _dist_version(dist: str) -> str:
    try:
        from importlib.metadata import version
        return version(dist)
    except Exception:
        return "없음"


def _impersonate_gap() -> tuple[list[str], str | None]:
    """코드가 쓰는 impersonate 별칭이 설치본에 없으면 그 목록. 확인 불가면 사유."""
    try:
        import fetch
        from curl_cffi.requests.impersonate import REAL_TARGET_MAP, BrowserType
    except Exception as exc:
        return [], f"impersonate 별칭 확인 불가({exc.__class__.__name__})"
    supported = set(REAL_TARGET_MAP) | {item.value for item in BrowserType}
    aliases = list(dict.fromkeys([*fetch.IMPERSONATE_GRID, fetch.MOBILE_IMPERSONATE]))
    return [alias for alias in aliases if alias not in supported], None


def _browser_layer() -> dict:
    """브라우저 계층은 선택. patchright 가 있으면 그것을, 없으면 playwright, 둘 다 없으면 없음."""
    if _has_py("patchright"):
        label = "patchright"
    elif _has_py("playwright"):
        label = "playwright"
    else:
        label = "없음"
    return {"ok": label != "없음", "detail": f"브라우저 계층: {label}"}


def check() -> dict:
    py_ok = sys.version_info >= (3, 10)
    missing, note = _impersonate_gap()
    soft = {m: {"ok": _has_py(m)} for m in SOFT_PY}
    soft["browser"] = _browser_layer()
    soft["agent-browser(cli)"] = {"ok": shutil.which("agent-browser") is not None, "detail": shutil.which("agent-browser")}
    report = {
        "hard": {
            "python>=3.10": {"ok": py_ok, "detail": sys.version.split()[0]},
            "fitz": {"ok": _has_py("fitz")},
            "pandoc": {"ok": shutil.which("pandoc") is not None, "detail": shutil.which("pandoc")},
            "chrome": {"ok": _find_chrome() is not None, "detail": _find_chrome()},
        },
        # 강방어 우회는 fetch.py 에 내장됨 — insane-search 스킬 의존 없음(2026-07-31)
        "soft": soft,
        "runtime_check_needed": [
            "브라우저: agent-browser CLI → playwright MCP → claude-in-chrome",
            "무료 공공 MCP: opendart · KOSIS · KakaoMap 등",
        ],
        "versions": {name: _dist_version(dist) for name, dist in _VERSION_DISTS},
        "impersonate_unsupported": missing,
        "impersonate_note": note,
    }
    report["hard_ok"] = all(v["ok"] for v in report["hard"].values())
    return report


def check_help_contract(timeout: int = 30) -> dict:
    """scripts/*.py 가 `--help` 로 종료코드 0 인지 점검(하위 폴더 flint/ 제외). 실패만 {파일: 코드} 로 반환. 소스에 argparse·--help 가 없으면 실행하지 않고 "help 미지원".
    --help 를 모르는 스크립트는 본 동작을 실행할 수 있어, 빈 임시 폴더에서 MDR_WORK_DIR 없이 돌려 부작용을 가둔다."""
    env = {k: v for k, v in os.environ.items() if k != "MDR_WORK_DIR"}
    bad: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        for f in sorted(Path(__file__).parent.glob("*.py")):
            if f.name == Path(__file__).name:
                continue
            src = f.read_text(encoding="utf-8", errors="replace")
            if "argparse" not in src and "--help" not in src:   # --help 를 모르면 본동작이 실행될 수 있어 돌리지 않는다
                bad[f.name] = "help 미지원"
                continue
            try:
                rc = subprocess.run([sys.executable, str(f), "--help"], cwd=tmp, env=env, timeout=timeout,
                                    capture_output=True).returncode
            except subprocess.TimeoutExpired:
                rc = "timeout"
            if rc != 0:
                bad[f.name] = rc
    return bad


def _fmt(report: dict) -> str:
    lines = ["[G0 preflight]"]
    for grp in ("hard", "soft"):
        lines.append(f"  {grp.upper()}:")
        for k, v in report[grp].items():
            mark = "OK " if v["ok"] else "MISS"
            det = f"  ({v.get('detail')})" if v.get("detail") else ""
            lines.append(f"    [{mark}] {k}{det}")
    lines.append("  RUNTIME(오케스트레이터 확인): " + " · ".join(report["runtime_check_needed"]))
    lines.append("  VERSIONS:")
    for name, ver in report.get("versions", {}).items():
        lines.append(f"    {name} {ver}")
    unsupported = report.get("impersonate_unsupported") or []
    if unsupported:
        lines.append("  ⚠ SOFT impersonate 별칭 미지원: " + ", ".join(unsupported))
    if report.get("impersonate_note"):
        lines.append("  ⚠ SOFT " + report["impersonate_note"])
    if not report["hard_ok"]:
        lines.append("  ✗ HARD 의존성 누락 — 설치 후 재실행. (SOFT 누락은 해당 계층만 건너뜀)")
    else:
        soft_miss = [k for k, v in report["soft"].items() if not v["ok"]]
        if soft_miss:
            lines.append(f"  ⚠ SOFT 누락(해당 계층 건너뜀): {', '.join(soft_miss)}")
            lines.append("    설치: pip install curl_cffi trafilatura  (+선택 yt-dlp)")
            if "vl_convert" in soft_miss:
                lines.append("    차트 SVG 렌더: pip install vl-convert-python")
    if report.get("help_contract"):
        lines.append("  ⚠ --help 종료코드≠0 (선택 경고): " + ", ".join(f"{k}={v}" for k, v in report["help_contract"].items()))
    return "\n".join(lines)


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):          # cp949 콘솔/파이프 UnicodeEncodeError 방지
        _reconf = getattr(_stream, "reconfigure", None)
        if _reconf:
            _reconf(encoding="utf-8", errors="replace")
    rep = check()
    if "--check-help" in sys.argv:                     # 느리므로(스크립트 수만큼 프로세스) 옵션. exit 코드에는 영향 없음
        rep["help_contract"] = check_help_contract()
    if "--json" in sys.argv:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(_fmt(rep))
    sys.exit(0 if rep["hard_ok"] else 1)
