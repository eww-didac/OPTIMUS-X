"""Windows privilege and process helpers."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Start a new elevated copy of Optimus X. Returns True when launched."""

    try:
        executable = sys.executable
        if getattr(sys, "frozen", False):
            params = subprocess.list2cmdline(sys.argv[1:])
        else:
            script = os.path.abspath(sys.argv[0])
            params = subprocess.list2cmdline([script, *sys.argv[1:]])
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, os.path.dirname(os.path.abspath(sys.argv[0])), 1
        )
        return result > 32
    except Exception:
        return False


def run_process(
    args: list[str] | str,
    *,
    timeout: float = 45,
    shell: bool = False,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a hidden process and capture text output."""

    kwargs: dict = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout,
        "creationflags": CREATE_NO_WINDOW,
    }
    if cwd:
        kwargs["cwd"] = cwd
    return subprocess.run(args, shell=shell, **kwargs)


def run_ps(script: str, *, timeout: float = 45) -> subprocess.CompletedProcess[str]:
    """Run PowerShell without a console window."""

    wrapped = "$OutputEncoding=[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + script
    return run_process(
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
        timeout=timeout,
    )
