"""Bloatware and disk cleanup operations."""

from __future__ import annotations

import os
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import system
from .admin import is_admin, run_ps
from .commands import run_streaming

Emit = Callable[[str], None]


@dataclass(frozen=True)
class JunkTarget:
    id: str
    title: str
    description: str
    paths: tuple[str, ...]
    admin: bool = False
    recycle_bin: bool = False
    pattern: str = "*"


def _env_path(var: str, default: str = "") -> str:
    return os.path.expandvars(os.environ.get(var, default))


def junk_targets() -> list[JunkTarget]:
    local = _env_path("LOCALAPPDATA")
    system_root = _env_path("SystemRoot", r"C:\Windows")
    return [
        JunkTarget(
            "user_temp",
            "User temporary files",
            "Leftover installers, caches and crash artefacts in your profile.",
            tuple(x for x in (_env_path("TEMP"), _env_path("TMP")) if x),
        ),
        JunkTarget(
            "windows_temp",
            "Windows temporary files",
            "System-wide temp files in C:\\Windows\\Temp.",
            (str(Path(system_root) / "Temp"),),
            admin=True,
        ),
        JunkTarget(
            "shader_cache",
            "DirectX shader cache",
            "Compiled shaders that Windows can rebuild automatically.",
            (str(Path(local) / "D3DSCache"),),
        ),
        JunkTarget(
            "crash_dumps",
            "Crash dumps",
            "Application crash reports and minidumps.",
            (str(Path(local) / "CrashDumps"),),
        ),
        JunkTarget(
            "thumb_cache",
            "Explorer thumbnail cache",
            "Cached thumbnails used by File Explorer.",
            (str(Path(local) / "Microsoft" / "Windows" / "Explorer"),),
            pattern="thumbcache_*.db",
        ),
        JunkTarget(
            "delivery_opt",
            "Delivery Optimization cache",
            "Windows update delivery cache shared on your network.",
            (str(Path(system_root) / "SoftwareDistribution" / "DeliveryOptimization"),),
            admin=True,
        ),
        JunkTarget(
            "update_cache",
            "Windows Update download cache",
            "Already-installed update payloads in SoftwareDistribution.",
            (str(Path(system_root) / "SoftwareDistribution" / "Download"),),
            admin=True,
        ),
        JunkTarget(
            "recycle_bin",
            "Recycle Bin",
            "Files waiting in the Recycle Bin on the system drive.",
            (),
            recycle_bin=True,
        ),
    ]


def _path_size(path: str, pattern: str = "*", deadline: float = 7.0) -> int:
    root = Path(path)
    if not root.exists():
        return 0
    if root.is_file():
        try:
            return root.stat().st_size
        except OSError:
            return 0
    total = 0
    started = time.time()
    stack = [str(root)]
    seen = 0
    while stack:
        if time.time() - started > deadline:
            break
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    seen += 1
                    if seen > 120_000:
                        return total
                    try:
                        if entry.is_file(follow_symlinks=False):
                            if pattern != "*" and not Path(entry.name).match(pattern):
                                continue
                            total += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def scan_junk() -> list[dict]:
    rows: list[dict] = []
    for target in junk_targets():
        exists = True
        size = 0
        if target.recycle_bin:
            size = -1  # unknown, represented as "Ready"
        else:
            exists = any(Path(path).exists() for path in target.paths)
            for path in target.paths:
                size += _path_size(path, target.pattern)
        rows.append(
            {
                "target": target,
                "exists": exists,
                "size": size,
            }
        )
    return rows


def _delete_contents(target: JunkTarget, emit: Emit, cancel: threading.Event) -> tuple[int, int]:
    removed = 0
    errors = 0
    for path in target.paths:
        root = Path(path)
        if not root.exists():
            continue
        if not is_admin() and target.admin:
            emit(f"[!] Administrator rights required for {target.title}")
            return removed, errors + 1
        try:
            children = list(root.iterdir())
        except OSError as exc:
            emit(f"[!] Could not open {root}: {exc}")
            errors += 1
            continue
        for child in children:
            if cancel.is_set():
                return removed, errors
            try:
                if child.is_dir() and not child.is_symlink():
                    if target.pattern != "*":
                        # Never delete whole folders when a file pattern is set.
                        continue
                    size = _path_size(str(child), "*", deadline=3)
                    shutil.rmtree(child, ignore_errors=True)
                    if not child.exists():
                        removed += size
                else:
                    if target.pattern != "*" and not child.match(target.pattern):
                        continue
                    size = child.stat().st_size
                    child.unlink()
                    removed += size
            except OSError:
                errors += 1
    return removed, errors


def clean_junk(
    ids: list[str],
    emit: Emit,
    cancel: threading.Event | None = None,
) -> dict:
    cancel = cancel or threading.Event()
    targets = {target.id: target for target in junk_targets()}
    removed = 0
    errors = 0
    cleaned = 0
    for target_id in ids:
        if cancel.is_set():
            emit("[!] Cleaning cancelled.")
            break
        target = targets.get(target_id)
        if not target:
            continue
        emit(f"Cleaning {target.title}…")
        if target.recycle_bin:
            code = run_streaming(
                "Clear-RecycleBin -DriveLetter $env:SystemDrive[0] -Force -ErrorAction SilentlyContinue",
                emit,
                cancel,
                timeout=60,
                label="Empty Recycle Bin",
            )
            if code == 0:
                cleaned += 1
                emit("[ok] Recycle Bin emptied.")
            else:
                errors += 1
            continue
        if target.admin and not is_admin():
            emit(f"[!] Skipped {target.title}: administrator rights required.")
            errors += 1
            continue

        service_was_running = False
        if target_id == "update_cache":
            service_was_running = system.service_running("wuauserv")
            if service_was_running:
                run_ps("Stop-Service wuauserv -Force -ErrorAction SilentlyContinue", timeout=30)

        size, errs = _delete_contents(target, emit, cancel)
        removed += size
        errors += errs
        cleaned += 1
        emit(f"[ok] {target.title}: freed {system.format_bytes(size)}")

        if target_id == "update_cache" and service_was_running:
            run_ps("Start-Service wuauserv -ErrorAction SilentlyContinue", timeout=30)
            emit("Windows Update service restarted.")

    emit(f"\nCleanup finished: {system.format_bytes(removed)} freed" + (f", {errors} issue(s)" if errors else ""))
    return {"removed": removed, "errors": errors, "cleaned": cleaned}


def remove_appx(packages: list[dict], emit: Emit, cancel: threading.Event | None = None) -> dict:
    cancel = cancel or threading.Event()
    if not packages:
        return {"ok": 0, "failed": 0, "removed": 0}
    lines = [
        "$ErrorActionPreference='Continue';",
        "$removed=0;",
        "$failed=0;",
    ]
    for package in packages:
        full = str(package.get("full_name") or "").replace("'", "''")
        name = str(package.get("name") or "").replace("'", "''")
        title = str(package.get("title") or name).replace("'", "''")
        if not full:
            continue
        lines.append(
            f"$pkgs=@(Get-AppxPackage -AllUsers -ErrorAction SilentlyContinue | "
            f"Where-Object {{$_.PackageFullName -eq '{full}'}});"
            "if($pkgs.Count -gt 0){"
            "foreach($p in $pkgs){"
            "try{"
            "Remove-AppxPackage -Package $p.PackageFullName -AllUsers -ErrorAction Stop;"
            f"Write-Output 'Removed {title}';$removed++"
            "}catch{"
            "try{"
            "Remove-AppxPackage -Package $p.PackageFullName -ErrorAction Stop;"
            f"Write-Output 'Removed {title} (current user)';$removed++"
            "}catch{"
            f"Write-Output ('Failed {title}: '+$_.Exception.Message);$failed++"
            "}}}"
            "}else{"
            f"Write-Output 'Not installed: {title}'"
            "};"
            "try{"
            f"$prov=Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -eq '{name}'}};"
            "if($prov){$prov|Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue}"
            "}catch{}"
        )
    lines.append("Write-Output \"RESULT removed=$removed failed=$failed\"; exit $failed")
    code = run_streaming(
        "".join(lines),
        emit,
        cancel,
        timeout=600,
        label="Remove selected AppX packages",
    )
    ok = code == 0
    return {
        "ok": 1 if ok else 0,
        "failed": 0 if ok else 1,
        "removed": len(packages) if ok else 0,
    }


def purge_edge_webview_only() -> None:
    """Kept for future use; intentionally does not touch WebView2."""
    return None
