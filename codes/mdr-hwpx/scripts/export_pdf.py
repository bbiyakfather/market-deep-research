"""한글 COM 으로 HWPX 를 PDF 로보낸다.

Hwp.exe 가 안 떠 있으면 CoCreateInstance 가 '서버 실행에 실패' 로 죽는다.
그 경우 Hwp.exe -Automation 을 띄우고 최대 20초 재시도한다.
RegisterModule('FilePathCheckDLL','FilePathCheckerModule') 이 없으면
보안 대화상자에서 멈춘다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HWP_EXE = Path(r"C:/Program Files (x86)/Hnc/Office 2024/HOffice130/Bin/Hwp.exe")
# CO_E_SERVER_EXEC_FAILURE
_SERVER_FAIL_HR = -2146959355
_CLASS_NOT_REG_HR = -2147221164


class HangulMissing(RuntimeError):
    """한글이 이 PC 에 없다."""


def _is_server_fail(exc: BaseException) -> bool:
    msg = str(exc)
    if "서버 실행에 실패" in msg:
        return True
    args = getattr(exc, "args", ())
    if args and args[0] == _SERVER_FAIL_HR:
        return True
    return "CO_E_SERVER_EXEC_FAILURE" in msg or "-2146959355" in msg


def _is_not_registered(exc: BaseException) -> bool:
    msg = str(exc)
    args = getattr(exc, "args", ())
    if args and args[0] == _CLASS_NOT_REG_HR:
        return True
    return "Class not registered" in msg or "클래스가 등록되지" in msg


def _dispatch():
    import win32com.client as w
    return w.gencache.EnsureDispatch("HWPFrame.HwpObject")


def _ensure_hwp():
    """HWPFrame.HwpObject 를 얻고, 서버 실행 실패면 Hwp.exe -Automation 후 재시도.

    반환 (hwp, proc). proc 은 이번에 Popen 한 프로세스이고, 이미 떠 있던
    한글에 붙었으면 None 이다 — 그 PID 는 절대 terminate 하지 않는다.
    """
    try:
        return _dispatch(), None
    except Exception as e:
        if _is_not_registered(e) and not HWP_EXE.exists():
            raise HangulMissing("한글 없음") from e
        if not _is_server_fail(e) and not HWP_EXE.exists():
            raise HangulMissing("한글 없음") from e
        if not HWP_EXE.exists():
            raise HangulMissing("한글 없음") from e
        proc = subprocess.Popen(
            [str(HWP_EXE), "-Automation"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        last: BaseException | None = e
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            time.sleep(0.5)
            try:
                return _dispatch(), proc
            except Exception as e2:
                last = e2
        _stop_spawned(proc)
        raise RuntimeError(f"Hwp Automation 재시도 실패: {last}") from last


def _hwp_pids() -> set[int]:
    """현재 Hwp.exe PID 집합. 메모리 열에 쉼표가 있어 CSV split 하지 않는다."""
    r = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Hwp.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, encoding="oem", errors="replace",
    )
    pids: set[int] = set()
    for line in r.stdout.splitlines():
        m = re.match(r'"Hwp\.exe","(\d+)"', line, re.I)
        if m:
            pids.add(int(m.group(1)))
    return pids


def _stop_spawned(proc: subprocess.Popen, wait_s: float = 5.0) -> bool:
    """우리가 띄운 Popen 만 최대 wait_s 초 기다렸다가 살아 있으면 terminate/kill.

    True 면 우리가 강제로 끊었다. 미리 떠 있던 한글 PID 는 여기로 안 넘어온다.
    """
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        time.sleep(0.2)
    if proc.poll() is not None:
        return False
    try:
        proc.terminate()
    except Exception:
        pass
    kill_deadline = time.monotonic() + 2
    while time.monotonic() < kill_deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.1)
    try:
        proc.kill()
    except Exception:
        pass
    return True


def _kill_pid(pid: int) -> bool:
    """taskkill 로 해당 PID 만 강제 종료. 성공하면 True."""
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F"],
        capture_output=True, text=True, encoding="oem", errors="replace",
    )
    time.sleep(0.2)
    return pid not in _hwp_pids()


def _reap_new_hwps(before: set[int], wait_s: float = 5.0) -> bool:
    """시작 전에 없던 Hwp.exe 만 정리한다. 기존 PID(사용자 한글)는 건드리지 않는다."""
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        leftover = _hwp_pids() - before
        if not leftover:
            return False
        time.sleep(0.2)
    leftover = _hwp_pids() - before
    killed = False
    for pid in leftover:
        if _kill_pid(pid):
            killed = True
    return killed


def _close_hwp(h) -> None:
    """Quit 전에 문서를 비운다. Clear 가 없는 빌드는 그냥 Quit 로 넘어간다."""
    try:
        h.Clear(1)
    except Exception:
        try:
            h.Run("FileClose")
        except Exception:
            pass
    try:
        h.Quit()
    except Exception:
        pass


def export(src, out=None) -> dict:
    """src hwpx 를 PDF 로 저장한다. 경로는 절대경로로 변환한다."""
    src_path = Path(src).resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"없음: {src_path}")
    out_path = Path(out).resolve() if out else src_path.with_suffix(".pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        out_path.unlink()
    except FileNotFoundError:
        pass
    except PermissionError as e:
        raise RuntimeError(f"기존 PDF 잠김 — 뷰어 닫고 재시도: {out_path} ({e})") from e

    h = None
    proc = None
    spawned = False
    terminated = False
    size = 0
    before_pids = _hwp_pids()
    try:
        h, proc = _ensure_hwp()
        spawned = proc is not None or bool(_hwp_pids() - before_pids)
        h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        h.Open(str(src_path), "HWPX", "forceopen:true")
        h.HAction.GetDefault("FileSaveAsPdf", h.HParameterSet.HFileOpenSave.HSet)
        h.HParameterSet.HFileOpenSave.filename = str(out_path)
        h.HParameterSet.HFileOpenSave.Format = "PDF"
        h.HAction.Execute("FileSaveAsPdf", h.HParameterSet.HFileOpenSave.HSet)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if out_path.exists() and out_path.stat().st_size > 0:
                break
            time.sleep(0.4)
        if not out_path.exists() or out_path.stat().st_size == 0:
            raise RuntimeError(f"PDF 생성 안 됨: {out_path}")
        size = out_path.stat().st_size
    finally:
        if h is not None:
            _close_hwp(h)
        if proc is not None:
            terminated = _stop_spawned(proc)
        # Dispatch 가 Popen 없이 새 Hwp.exe 를 띄운 경우도, 시작 전 PID 만 남긴다
        if _reap_new_hwps(before_pids):
            terminated = True
            spawned = True
    return {"ok": True, "pdf": str(out_path), "size": size,
            "spawned": spawned, "terminated": terminated}


def demo() -> None:
    """COM 없이 경로·오류 판정과, 우리가 띄운 Popen 만 거두는지를 점검한다."""
    assert "HOffice130" in str(HWP_EXE) and HWP_EXE.name == "Hwp.exe"
    assert _is_server_fail(Exception("서버 실행에 실패했습니다."))
    assert not _is_server_fail(Exception("다른 오류"))

    class _E(Exception):
        pass

    e = _E("x")
    e.args = (_SERVER_FAIL_HR, "서버 실행에 실패했습니다.", None, None)
    assert _is_server_fail(e)
    try:
        export("__no_such_export_src__.hwpx")
        raise AssertionError("없는 파일이 통과됨")
    except FileNotFoundError:
        pass

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert proc.poll() is None
    killed = _stop_spawned(proc, wait_s=0.4)
    assert killed is True and proc.poll() is not None, (killed, proc.poll())


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--demo" in args:
        demo()
        print("demo ok")
        return 0
    if not args:
        print("usage: export_pdf.py <in.hwpx> [<out.pdf>]", file=sys.stderr)
        return 1
    src = args[0]
    out = args[1] if len(args) > 1 else None
    try:
        result = export(src, out)
    except HangulMissing:
        print("한글 없음", file=sys.stderr)
        return 2
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
