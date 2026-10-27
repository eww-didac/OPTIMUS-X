"""Read-only Windows inspection helpers used across the application."""

from __future__ import annotations

import csv
import functools
import io
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import winreg
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from .admin import is_admin, run_process, run_ps
from .store import store

HIVES = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
}

START_TYPES = {0: "boot", 1: "system", 2: "auto", 3: "manual", 4: "disabled"}
START_VALUES = {v: k for k, v in START_TYPES.items()}


# --------------------------------------------------------------------------- registry
def read_reg(hive: str, path: str, name: str) -> tuple[Any, int | None]:
    try:
        with winreg.OpenKey(HIVES[hive], path, 0, winreg.KEY_READ) as key:
            value, value_type = winreg.QueryValueEx(key, name)
            return value, value_type
    except (FileNotFoundError, OSError, KeyError):
        return None, None


def registry_key_counts(hive: str, path: str) -> int:
    try:
        with winreg.OpenKey(HIVES[hive], path, 0, winreg.KEY_READ) as key:
            return winreg.QueryInfoKey(key)[1]
    except OSError:
        return 0


def reg_matches(hive: str, path: str, name: str, expected: Any) -> bool:
    value, _ = read_reg(hive, path, name)
    if value is None:
        return False
    if isinstance(expected, str):
        return str(value).lower() == expected.lower()
    return value == expected


# ---------------------------------------------------------------------------- services
def service_start(name: str) -> str | None:
    value, _ = read_reg("HKLM", rf"SYSTEM\CurrentControlSet\Services\{name}", "Start")
    if isinstance(value, int):
        return START_TYPES.get(value)
    return None


def service_running(name: str) -> bool:
    try:
        return psutil.win_service_get(name).status() == "running"
    except Exception:
        return False


def service_exists(name: str) -> bool:
    try:
        psutil.win_service_get(name)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------------------ system
@functools.lru_cache(maxsize=1)
def os_info() -> dict[str, str]:
    product = platform.system()
    build = platform.version()
    display = f"{product} {platform.release()}"
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        ) as key:
            product_name = winreg.QueryValueEx(key, "ProductName")[0]
            build_number = str(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
            ubr = winreg.QueryValueEx(key, "UBR")[0]
            display_name = winreg.QueryValueEx(key, "DisplayVersion")[0]
            edition = winreg.QueryValueEx(key, "EditionID")[0]
            if int(build_number) >= 22000:
                product_name = product_name.replace("Windows 10", "Windows 11")
            display = f"{product_name} {display_name}"
            build = f"{build_number}.{ubr}"
            product = edition
    except Exception:
        pass
    return {
        "name": display,
        "build": build,
        "edition": product,
        "architecture": platform.machine(),
        "hostname": socket.gethostname(),
        "user": os.environ.get("USERNAME", ""),
    }


@functools.lru_cache(maxsize=1)
def cpu_info() -> dict[str, Any]:
    name = platform.processor() or "Unknown CPU"
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        ) as key:
            name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    except Exception:
        pass
    return {
        "name": name,
        "cores": psutil.cpu_count(logical=False) or 0,
        "threads": psutil.cpu_count(logical=True) or 0,
    }


@functools.lru_cache(maxsize=1)
def gpu_names() -> list[str]:
    names: list[str] = []
    try:
        result = run_ps(
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress",
            timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if isinstance(data, str):
                data = [data]
            names = [str(item) for item in data if item]
    except Exception:
        pass
    if not names:
        try:
            nvidia = shutil.which("nvidia-smi")
            if nvidia:
                out = run_process(
                    [nvidia, "--query-gpu=name", "--format=csv,noheader"], timeout=5
                )
                names = [line.strip() for line in out.stdout.splitlines() if line.strip()]
        except Exception:
            pass
    return names or ["Display adapter"]


def gpu_name() -> str:
    names = gpu_names()
    if not names:
        return "GPU"
    for name in names:
        if "nvidia" in name.lower() or "radeon" in name.lower():
            return name
    return names[0]


@functools.lru_cache(maxsize=1)
def total_ram_gb() -> float:
    return psutil.virtual_memory().total / (1024**3)


def system_drive() -> str:
    return os.environ.get("SystemDrive", "C:") + "\\"


def disk_usage(path: str | None = None) -> dict[str, Any]:
    target = path or system_drive()
    try:
        usage = psutil.disk_usage(target)
        return {
            "path": target,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent,
        }
    except Exception:
        return {"path": target, "total": 0, "used": 0, "free": 0, "percent": 0}


def all_disks() -> list[dict[str, Any]]:
    result = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            result.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            )
        except Exception:
            continue
    return result


def format_bytes(value: float | int) -> str:
    value = float(value or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def uptime_text() -> str:
    try:
        seconds = int(datetime.now().timestamp() - psutil.boot_time())
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        if days:
            return f"{days}d {hours}h"
        return f"{hours}h {minutes}m"
    except Exception:
        return "—"


# --------------------------------------------------------------------------------- GPU
@functools.lru_cache(maxsize=1)
def nvidia_smi_path() -> str | None:
    return shutil.which("nvidia-smi")


def gpu_stats() -> dict[str, Any]:
    smi = nvidia_smi_path()
    if smi:
        try:
            result = run_process(
                [
                    smi,
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,clocks.current.graphics",
                    "--format=csv,noheader,nounits",
                ],
                timeout=4,
            )
            if result.returncode == 0 and result.stdout.strip():
                row = next(csv.reader(io.StringIO(result.stdout.strip())))
                if len(row) >= 6:
                    return {
                        "available": True,
                        "name": row[0].strip(),
                        "percent": _safe_float(row[1]),
                        "memory_used": _safe_float(row[2]) * 1024**2,
                        "memory_total": _safe_float(row[3]) * 1024**2,
                        "temp": _safe_float(row[4]),
                        "clock": _safe_float(row[5]),
                        "source": "nvidia",
                    }
        except Exception:
            pass

    # Windows' own 3D engine counter works for AMD and Intel adapters too.
    try:
        result = run_ps(
            "(Get-Counter '\\GPU Engine(*engtype_3D)\\Utilization Percentage' -ErrorAction SilentlyContinue)"
            ".CounterSamples | Measure-Object -Property CookedValue -Sum | Select-Object -ExpandProperty Sum",
            timeout=8,
        )
        if result.returncode == 0 and result.stdout.strip():
            percent = min(100.0, _safe_float(result.stdout.strip().splitlines()[-1]))
            return {
                "available": True,
                "name": gpu_name(),
                "percent": percent,
                "memory_used": None,
                "memory_total": None,
                "temp": None,
                "clock": None,
                "source": "counter",
            }
    except Exception:
        pass

    return {
        "available": False,
        "name": gpu_name(),
        "percent": None,
        "memory_used": None,
        "memory_total": None,
        "temp": None,
        "clock": None,
        "source": "none",
    }


def _safe_float(value: Any) -> float | None:
    try:
        text = str(value).strip().replace(",", ".")
        if not text or text.upper() in {"N/A", "[N/A]", "NAN"}:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def network_latency(host: str = "1.1.1.1") -> float | None:
    try:
        result = run_process(
            ["ping", "-n", "1", "-w", "900", host],
            timeout=2.5,
        )
        output = result.stdout or ""
        match = re.search(r"(?:time|tiempo|temps)[=<]\s*(\d+(?:[.,]\d+)?)\s*ms", output, re.I)
        if match:
            return float(match.group(1).replace(",", "."))
        if re.search(r"(?:time|tiempo)[<]\s*1\s*ms", output, re.I):
            return 1.0
    except Exception:
        pass
    return None


# --------------------------------------------------------------------------- appx scan
def scan_appx(names: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    if not names:
        return [], None
    escaped = ",".join("'" + name.replace("'", "''") + "'" for name in names)
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        f"$names=@({escaped});"
        "Get-AppxPackage | Where-Object { $names -contains $_.Name } | "
        "Select-Object Name,PackageFullName,Version,NonRemovable | ConvertTo-Json -Compress"
    )
    try:
        result = run_ps(script, timeout=65)
    except subprocess.TimeoutExpired:
        return [], "The AppX scan timed out. Try again."
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "PowerShell scan failed").strip()
        return [], message.splitlines()[-1][:220]
    raw = (result.stdout or "").strip()
    if not raw:
        return [], None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [], "Could not parse the installed package list."
    if isinstance(data, dict):
        data = [data]
    packages: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        packages.append(
            {
                "name": str(item.get("Name") or ""),
                "full_name": str(item.get("PackageFullName") or ""),
                "version": str(item.get("Version") or ""),
                "non_removable": bool(item.get("NonRemovable")),
            }
        )
    return packages, None


def feature_states() -> dict[str, str]:
    script = (
        "$ErrorActionPreference='SilentlyContinue';$out=@();"
        "foreach($f in @('DirectPlay','WindowsMediaPlayer')){"
        "$s=Get-WindowsOptionalFeature -Online -FeatureName $f;"
        "if($s){$out += [pscustomobject]@{Name=$f;State=[string]$s.State}}};"
        "$out|ConvertTo-Json -Compress"
    )
    try:
        result = run_ps(script, timeout=45)
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            return {str(item.get("Name")): str(item.get("State")) for item in data if isinstance(item, dict)}
    except Exception:
        pass
    return {}


def edge_installed() -> bool:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Microsoft/Edge/Application/msedge.exe",
    ]
    return any(path.exists() for path in candidates)


def onedrive_installed() -> bool:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/OneDrive/OneDrive.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft OneDrive/OneDrive.exe",
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/OneDriveSetup.exe",
    ]
    return any(str(path) and path.exists() for path in candidates)


def wmp_legacy_installed() -> bool:
    candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Windows Media Player/wmplayer.exe"
    value, _ = read_reg(
        "HKLM",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\wmplayer.exe",
        "",
    )
    return candidate.exists() or bool(value)


def power_plan() -> dict[str, str]:
    known = {
        "381b4222-f694-41f0-9685-ff5bb260df2e": "Balanced",
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "High performance",
        "a1841308-3541-4fab-bc81-f71556f20b4a": "Power saver",
        "e9a42b02-d5df-448d-aa00-03f14749eb61": "Ultimate performance",
    }
    guid = ""
    name = "Unknown"
    try:
        result = run_process(["powercfg", "/getactivescheme"], timeout=5)
        text = (result.stdout or "").strip()
        match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", text)
        if match:
            guid = match.group(1).lower()
        alias = re.search(r"\(([^)]+)\)", text)
        if alias:
            name = alias.group(1).strip()
        name = known.get(guid, name)
    except Exception:
        pass
    return {"guid": guid, "name": name}


def set_power_plan(guid: str) -> tuple[bool, str]:
    try:
        result = run_process(["powercfg", "/setactive", guid], timeout=10)
        if result.returncode == 0:
            return True, "Power plan changed."
        return False, (result.stderr or result.stdout or "powercfg failed").strip()
    except Exception as exc:
        return False, str(exc)


def top_processes(limit: int = 8) -> list[dict[str, Any]]:
    protected = {
        "system", "registry", "memory compression", "explorer.exe", "dwm.exe",
        "wininit.exe", "winlogon.exe", "csrss.exe", "smss.exe", "services.exe",
        "lsass.exe", "svchost.exe", "fontdrvhost.exe", "sihost.exe", "taskhostw.exe",
        "ctfmon.exe", "runtimebroker.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
        "searchhost.exe", "textinputhost.exe", "python.exe", "pythonw.exe",
    }
    own_pid = os.getpid()
    rows: list[dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "memory_info", "username"]):
        try:
            info = proc.info
            name = info.get("name") or ""
            if not name or info.get("pid") == own_pid:
                continue
            if name.lower() in protected:
                continue
            memory = info.get("memory_info")
            if not memory:
                continue
            rss = int(memory.rss)
            if rss < 35 * 1024**2:
                continue
            rows.append(
                {
                    "pid": int(info["pid"]),
                    "name": name,
                    "memory": rss,
                    "username": str(info.get("username") or ""),
                    "exe": _process_exe(proc),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    rows.sort(key=lambda row: row["memory"], reverse=True)
    return rows[:limit]


def _process_exe(proc: psutil.Process) -> str:
    try:
        return proc.exe()
    except Exception:
        return ""


def is_process_protected(name: str) -> bool:
    lowered = name.lower()
    critical = (
        "csrss", "wininit", "winlogon", "services", "lsass", "smss", "svchost",
        "explorer", "dwm", "system", "registry", "memory compression",
    )
    return lowered in critical or lowered.endswith(("csrss.exe", "winlogon.exe", "wininit.exe"))


def create_restore_point(description: str = "Optimus X - before optimization") -> tuple[bool, str]:
    script = (
        "Enable-ComputerRestore -Drive $env:SystemDrive -ErrorAction SilentlyContinue;"
        f"Checkpoint-Computer -Description '{description.replace(chr(39), chr(39) * 2)}' "
        "-RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop"
    )
    try:
        result = run_ps(script, timeout=120)
        if result.returncode == 0:
            return True, "Restore point created."
        message = (result.stderr or result.stdout or "").strip().splitlines()
        return False, message[-1] if message else "Restore point could not be created."
    except Exception as exc:
        return False, str(exc)


def admin_state() -> str:
    return "Administrator" if is_admin() else "Standard user"


def summary() -> dict[str, Any]:
    cpu = cpu_info()
    mem = psutil.virtual_memory()
    disk = disk_usage()
    return {
        "os": os_info(),
        "cpu": {**cpu, "freq": _cpu_freq_mhz()},
        "ram_gb": mem.total / 1024**3,
        "gpu": gpu_names(),
        "disk": disk,
        "power_plan": power_plan(),
        "uptime": uptime_text(),
        "admin": admin_state(),
        "generated": datetime.now().isoformat(timespec="seconds"),
    }


def _cpu_freq_mhz() -> float | None:
    try:
        freq = psutil.cpu_freq()
        return round(freq.current, 0) if freq else None
    except Exception:
        return None


def logs_summary() -> dict[str, Any]:
    return {
        "data_dir": str(store.root),
        "backup_count": store.backup_count(),
    }
