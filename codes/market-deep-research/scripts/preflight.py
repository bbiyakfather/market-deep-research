"""preflight.py — G0 의존성/도구 점검. 미설치 계층은 "건너뜀+경고"로 진행(자체 스택이 보장 코어).

파이썬에서 감지 가능한 것만 본다(python 패키지 · CLI 바이너리 · insane-search 스킬 폴더).
playwright MCP · 무료 공공 MCP(opendart/KOSIS 등)는 런타임에서 오케스트레이터(Claude)가
도구 목록으로 확인한다 — 여기서는 "런타임 확인 필요"로만 표시.

HARD(없으면 exit 1): python>=3.10, fitz(PyMuPDF), pandoc, chrome.
SOFT(경고): curl_cffi, trafilatura, openpyxl, yt-dlp, insane-search 스킬.

CLI: python preflight.py          # 리포트 출력, HARD 누락 시 exit 1
     python preflight.py --json   # JSON
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

HARD_PY = ["fitz"]
SOFT_PY = ["curl_cffi", "trafilatura", "openpyxl", "yt_dlp"]

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


def _find_insane_search() -> str | None:
    base = Path.home() / ".claude" / "plugins"
    hits = list(base.glob("**/insane-search/**/SKILL.md")) if base.exists() else []
    return str(hits[0].parent) if hits else None


def check() -> dict:
    py_ok = sys.version_info >= (3, 10)
    report = {
        "hard": {
            "python>=3.10": {"ok": py_ok, "detail": sys.version.split()[0]},
            "fitz": {"ok": _has_py("fitz")},
            "pandoc": {"ok": shutil.which("pandoc") is not None, "detail": shutil.which("pandoc")},
            "chrome": {"ok": _find_chrome() is not None, "detail": _find_chrome()},
        },
        "soft": {
            **{m: {"ok": _has_py(m)} for m in SOFT_PY},
            "insane_search_skill": {"ok": _find_insane_search() is not None,
                                    "detail": _find_insane_search()},
        },
        "runtime_check_needed": [
            "playwright MCP (mcp__*playwright*)",
            "무료 공공 MCP: opendart · KOSIS · KakaoMap 등",
        ],
    }
    report["hard_ok"] = all(v["ok"] for v in report["hard"].values())
    return report


def _fmt(report: dict) -> str:
    lines = ["[G0 preflight]"]
    for grp in ("hard", "soft"):
        lines.append(f"  {grp.upper()}:")
        for k, v in report[grp].items():
            mark = "OK " if v["ok"] else "MISS"
            det = f"  ({v.get('detail')})" if v.get("detail") else ""
            lines.append(f"    [{mark}] {k}{det}")
    lines.append("  RUNTIME(오케스트레이터 확인): " + " · ".join(report["runtime_check_needed"]))
    if not report["hard_ok"]:
        lines.append("  ✗ HARD 의존성 누락 — 설치 후 재실행. (SOFT 누락은 해당 계층만 건너뜀)")
    else:
        soft_miss = [k for k, v in report["soft"].items() if not v["ok"]]
        if soft_miss:
            lines.append(f"  ⚠ SOFT 누락(해당 계층 건너뜀): {', '.join(soft_miss)}")
            lines.append("    설치: pip install curl_cffi trafilatura  (+선택 yt-dlp)")
    return "\n".join(lines)


if __name__ == "__main__":
    rep = check()
    if "--json" in sys.argv:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(_fmt(rep))
    sys.exit(0 if rep["hard_ok"] else 1)
