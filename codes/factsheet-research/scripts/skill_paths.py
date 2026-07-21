"""skill_paths.py — factsheet-research 스킬 공통 경로/부트스트랩 모듈.

모든 스크립트는 이 모듈을 **최상단**에서 import 한다. import 시점에 UTF-8 콘솔
부트스트랩이 1회 실행되므로(단일 지점), 한글 출력이 깨지지 않는다.

CLI:
    python skill_paths.py --preflight [--json]   # G0 의존성 점검
    python skill_paths.py --selfcheck            # 내부 자기검증
"""
from __future__ import annotations

import builtins
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date as _date, datetime
from pathlib import Path


# --- UTF-8 부트스트랩 (import 시 1회) -------------------------------------
def _bootstrap_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # py3.7+ TextIOWrapper
        except Exception:
            pass  # 재구성 불가한 스트림(일부 파이프/리다이렉트)은 무시


_bootstrap_utf8()


# --- 경로 해석 ------------------------------------------------------------
def skill_root() -> Path:
    """스킬 루트(factsheet-research/) 절대경로. 이 파일은 scripts/ 아래에 있어
    어느 작업폴더에서 실행하든 안정적으로 루트를 가리킨다."""
    return Path(__file__).resolve().parent.parent


def slugify(topic: str, maxlen: int = 40) -> str:
    """주제 → 폴더 슬러그.

    규칙(확정): NFC 정규화 → 공백·특수문자를 `_`로 → maxlen(40)자 컷(한글 유지).
    `\\w`는 유니코드 문자(한글 포함)를 유지하고, 그 외 기호/공백만 `_`로 접는다.
    결과가 비면 'topic'으로 대체한다.
    """
    s = unicodedata.normalize("NFC", topic or "")
    s = re.sub(r"[^\w가-힣]+", "_", s, flags=re.UNICODE)
    s = s.strip("_")[:maxlen].rstrip("_")
    return s or "topic"


def _date_stamp(date=None) -> str:
    if date is None:
        return datetime.now().strftime("%Y%m%d")
    if isinstance(date, (_date, datetime)):
        return date.strftime("%Y%m%d")
    return str(date)  # "YYYYMMDD" 문자열 그대로 수용


def work_dir(topic: str, date=None, base=None, create: bool = False) -> Path:
    """research_<슬러그>_<YYYYMMDD>/ 경로를 만든다.

    기존 폴더와 충돌하면 `_2`, `_3` … 접미로 회피한다. create=True면 실제 생성.
    base 미지정 시 현재 작업 디렉터리(조사 실행 위치) 기준.
    """
    base = Path(base) if base else Path.cwd()
    stem = f"research_{slugify(topic)}_{_date_stamp(date)}"
    work = base / stem
    n = 2
    while work.exists():
        work = base / f"{stem}_{n}"
        n += 1
    if create:
        work.mkdir(parents=True, exist_ok=True)
    return work


_SUBDIRS = {
    "sources": "_sources",           # 원본 스냅샷 + 해시
    "research": "_research",          # 에이전트 원자료 보존
    "captures": "_captures",          # source_capture (증빙 인정)
    "reconstructed": "_reconstructed",  # 내부 재구성 발췌 (증빙 불인정)
    "audit": "audit",                 # 내부 audit 번들
}


def subdirs(work, create: bool = False) -> dict:
    """작업폴더 하위 표준 디렉터리 경로 dict. create=True면 work 포함 실제 생성."""
    work = Path(work)
    paths = {key: work / name for key, name in _SUBDIRS.items()}
    if create:
        work.mkdir(parents=True, exist_ok=True)
        for p in paths.values():
            p.mkdir(parents=True, exist_ok=True)
    return paths


# --- subprocess 헬퍼 (UTF-8 환경 상속) ------------------------------------
def run(cmd, **kw):
    """subprocess.run 래퍼. encoding=utf-8 + env에 PYTHONUTF8=1 상속.

    자식 프로세스(파이썬 스크립트·pandoc·chrome 등)의 한글 입출력을 보장한다.
    """
    env = dict(kw.pop("env", None) or os.environ)
    env.setdefault("PYTHONUTF8", "1")
    kw.setdefault("encoding", "utf-8")
    kw["env"] = env
    return subprocess.run(cmd, **kw)


# --- preflight (G0 의존성 점검) ------------------------------------------
def _module_present(name: str):
    """모듈 존재 여부. __import__를 직접 호출해 builtins.__import__ 패치를 존중
    한다(selfcheck에서 특정 모듈을 가려 absent 동작을 검증하기 위함)."""
    try:
        mod = __import__(name)
        ver = getattr(mod, "__version__", None)
        return True, (str(ver) if ver else "importable")
    except Exception as e:  # ImportError 외 로드 실패도 absent로 취급
        return False, f"{type(e).__name__}: {e}"


def _find_chrome():
    """Chrome 실행파일 탐색: PATH → Windows 표준 설치경로 후보."""
    p = shutil.which("chrome")
    if p:
        return p
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    localapp = os.environ.get("LOCALAPPDATA")
    if localapp:
        candidates.append(os.path.join(localapp, r"Google\Chrome\Application\chrome.exe"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def check_dependencies() -> dict:
    """의존성별 present/detail/required 매핑.

    required=True 중 하나라도 absent면 preflight 실패(exit 1).
    yt_dlp는 선택(required=False) — 경고만.
    """
    result = {}
    result["python"] = {"present": True, "required": True,
                        "detail": sys.version.split()[0]}
    for name in ("fitz", "curl_cffi", "trafilatura", "playwright"):
        ok, detail = _module_present(name)
        result[name] = {"present": ok, "required": True, "detail": detail}
    pandoc = shutil.which("pandoc")
    result["pandoc"] = {"present": bool(pandoc), "required": True,
                        "detail": pandoc or "not found"}
    chrome = _find_chrome()
    result["chrome"] = {"present": bool(chrome), "required": True,
                        "detail": chrome or "not found"}
    ok, detail = _module_present("yt_dlp")
    result["yt_dlp"] = {"present": ok, "required": False, "detail": detail}
    return result


def _preflight(as_json: bool) -> int:
    deps = check_dependencies()
    missing = [n for n, d in deps.items() if d["required"] and not d["present"]]
    if as_json:
        print(json.dumps({"deps": deps, "missing_required": missing,
                          "ok": not missing}, ensure_ascii=False, indent=2))
    else:
        print(f"{'TOOL':<14}{'STATUS':<9}DETAIL")
        for n, d in deps.items():
            status = "present" if d["present"] else ("ABSENT" if d["required"] else "absent")
            tag = "" if d["required"] else "  (optional)"
            print(f"{n:<14}{status:<9}{d['detail']}{tag}")
        if missing:
            print(f"\nPREFLIGHT: FAIL ({len(missing)} required missing: {', '.join(missing)})")
        else:
            print("\nPREFLIGHT: OK")
    return 1 if missing else 0


def _selfcheck() -> int:
    # (a) 슬러그 규칙: 한글 유지 / 공백·특수문자 → _ / 40자 컷
    assert slugify("삼성전자 반도체 시장!") == "삼성전자_반도체_시장", slugify("삼성전자 반도체 시장!")
    assert slugify("A/B  test??") == "A_B_test", slugify("A/B  test??")
    assert slugify("한글English123") == "한글English123", slugify("한글English123")
    assert len(slugify("가" * 50)) == 40, len(slugify("가" * 50))
    assert slugify("!!!") == "topic", slugify("!!!")

    # (b) fitz를 __import__ 패치로 가린 뒤 check_dependencies가 absent 보고하는지
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fitz" or name.split(".")[0] == "fitz":
            raise ImportError("hidden for selfcheck")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = fake_import
    try:
        deps = check_dependencies()
    finally:
        builtins.__import__ = real_import
    assert deps["fitz"]["present"] is False, deps["fitz"]

    print("SELFCHECK OK")
    return 0


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="skill_paths",
                                description="factsheet-research 공통 경로/preflight")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--preflight", action="store_true",
                   help="의존성 점검(필수 하나라도 누락 시 exit 1)")
    g.add_argument("--selfcheck", action="store_true", help="내부 자기검증")
    p.add_argument("--json", action="store_true", help="preflight 결과를 JSON으로 출력")
    args = p.parse_args(argv)
    if args.selfcheck:
        return _selfcheck()
    if args.preflight:
        return _preflight(args.json)
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
