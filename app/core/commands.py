"""Streaming PowerShell execution used by long-running tasks and dialogs."""

from __future__ import annotations

import queue
import subprocess
import threading
import time
from typing import Callable

CREATE_NO_WINDOW = 0x08000000
Emit = Callable[[str], None]


def _kill_tree(pid: int) -> None:
    try:
        subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def run_streaming(
    script: str,
    emit: Emit,
    cancel: threading.Event | None = None,
    *,
    timeout: float | None = None,
    label: str = "PowerShell",
) -> int:
    """Run PowerShell, streaming output. Returns the process return code."""

    cancel = cancel or threading.Event()
    wrapped = "$OutputEncoding=[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + script
    emit(f"PS> {label}")
    try:
        process = subprocess.Popen(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                wrapped,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception as exc:
        emit(f"[!] Could not start PowerShell: {exc}")
        return 1

    lines: queue.Queue[str] = queue.Queue()

    def reader() -> None:
        try:
            assert process.stdout is not None
            for line in process.stdout:
                lines.put(line.rstrip())
        finally:
            lines.put("__EOF__")

    threading.Thread(target=reader, daemon=True).start()
    started = time.time()
    eof = False
    cancelled = False
    while not eof:
        if cancel.is_set() and process.poll() is None:
            emit("[!] Cancelling task…")
            _kill_tree(process.pid)
            cancelled = True
            break
        if timeout and time.time() - started > timeout and process.poll() is None:
            emit(f"[!] Timed out after {int(timeout)}s.")
            _kill_tree(process.pid)
            break
        try:
            line = lines.get(timeout=0.2)
        except queue.Empty:
            continue
        if line == "__EOF__":
            eof = True
            continue
        if line.startswith("__PS_") and line.endswith("__"):
            continue
        if line.strip():
            emit(line)
    try:
        process.wait(timeout=8)
    except Exception:
        pass
    if cancelled:
        return 130
    return int(process.returncode or 0)
