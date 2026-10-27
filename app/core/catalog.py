"""Declarative catalog of every reversible Windows tweak.

Each tweak is data first: the UI renders it, the executor backs it up, and the
same record can later restore the previous state. No hidden one-way changes.
"""

from __future__ import annotations

import os
import winreg
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from . import system


# ------------------------------------------------------------------------------ ops
@dataclass(frozen=True)
class RegOp:
    hive: str
    path: str
    name: str
    value: Any
    value_type: int = winreg.REG_DWORD


@dataclass(frozen=True)
class SvcOp:
    name: str
    start: str = "disabled"
    stop: bool = True


@dataclass(frozen=True)
class CmdOp:
    script: str
    undo_script: str = ""
    label: str = ""


Op = RegOp | SvcOp | CmdOp


@dataclass
class Tweak:
    id: str
    title: str
    description: str
    category: str
    risk: str = "safe"
    reboot: bool = False
    admin: bool = True
    ops: tuple[Op, ...] = field(default_factory=tuple)
    warning: str = ""
    probe: Callable[[], bool | None] | None = None
    recommended: bool = False
    gaming: bool = False

    @property
    def shows_reboot(self) -> bool:
        return self.reboot


def dword(hive: str, path: str, name: str, value: int) -> RegOp:
    return RegOp(hive, path, name, value, winreg.REG_DWORD)


def sz(hive: str, path: str, name: str, value: str) -> RegOp:
    return RegOp(hive, path, name, value, winreg.REG_SZ)


def svc(name: str, start: str = "disabled", stop: bool = True) -> SvcOp:
    return SvcOp(name, start, stop)


def ps(script: str, undo: str = "", label: str = "") -> CmdOp:
    return CmdOp(script, undo, label)


# --------------------------------------------------------------------------- probes
def _hibernation_off() -> bool:
    return not (Path(os.environ.get("SystemRoot", r"C:\Windows")) / "hiberfil.sys").exists()


def _edge_removed() -> bool:
    return not system.edge_installed()


def _onedrive_removed() -> bool:
    return not system.onedrive_installed()


def _wmp_removed() -> bool:
    return not system.wmp_legacy_installed()


# ---------------------------------------------------------------------- network ops
@lru_cache(maxsize=1)
def network_interface_ops() -> tuple[RegOp, ...]:
    base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    ops: list[RegOp] = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    guid = winreg.EnumKey(key, index)
                except OSError:
                    break
                index += 1
                path = f"{base}\\{guid}"
                # Only adapters Windows is actually using.
                ip, _ = system.read_reg("HKLM", path, "DhcpIPAddress")
                static, _ = system.read_reg("HKLM", path, "IPAddress")
                dhcp, _ = system.read_reg("HKLM", path, "EnableDHCP")
                if not ip and not static and dhcp is None:
                    continue
                ops.extend(
                    (
                        dword("HKLM", path, "TCPNoDelay", 1),
                        dword("HKLM", path, "TcpAckFrequency", 1),
                        dword("HKLM", path, "TcpDelAckTicks", 0),
                    )
                )
    except OSError:
        pass
    return tuple(ops)


# --------------------------------------------------------------------- appx catalog
APPX_CATALOG: dict[str, dict[str, Any]] = {
    "Microsoft.XboxApp": {
        "title": "Xbox Console Companion",
        "recommended": False,
        "note": "Legacy Xbox companion app.",
    },
    "Microsoft.GamingApp": {
        "title": "Xbox",
        "recommended": False,
        "note": "Xbox app and Game Pass sign-in.",
    },
    "Microsoft.XboxGamingOverlay": {
        "title": "Xbox Game Bar",
        "recommended": False,
        "note": "Overlay, captures and Game Bar shortcuts.",
    },
    "Microsoft.XboxIdentityProvider": {
        "title": "Xbox Identity Provider",
        "recommended": False,
        "note": "Required by Xbox / Game Pass titles.",
    },
    "Microsoft.XboxSpeechToTextOverlay": {
        "title": "Xbox Speech To Text",
        "recommended": False,
        "note": "Accessibility overlay for the Game Bar.",
    },
    "Microsoft.Xbox.TCUI": {
        "title": "Xbox TCUI",
        "recommended": False,
        "note": "Xbox user interface components.",
    },
    "microsoft.windowscommunicationsapps": {
        "title": "Mail & Calendar",
        "recommended": True,
        "note": "Replaced by Outlook web or your mail client.",
    },
    "Microsoft.WindowsMaps": {
        "title": "Maps",
        "recommended": True,
        "note": "Offline maps and location search.",
    },
    "Microsoft.ZuneVideo": {
        "title": "Movies & TV",
        "recommended": True,
        "note": "Microsoft's video store and player.",
    },
    "Microsoft.ZuneMusic": {
        "title": "Media Player",
        "recommended": False,
        "note": "Modern Media Player / Groove package.",
    },
    "Microsoft.Media.Player": {
        "title": "Media Player",
        "recommended": False,
        "note": "Modern Media Player package.",
    },
    "Microsoft.BingWeather": {
        "title": "Weather",
        "recommended": True,
        "note": "Microsoft Weather app.",
    },
    "Microsoft.YourPhone": {
        "title": "Phone Link (Your Phone)",
        "recommended": True,
        "note": "Android phone mirroring and notifications.",
    },
    "Microsoft.GetHelp": {
        "title": "Get Help",
        "recommended": True,
        "note": "Microsoft support app.",
    },
    "Microsoft.Getstarted": {
        "title": "Tips",
        "recommended": True,
        "note": "Windows tips and suggestions.",
    },
    "Microsoft.MicrosoftSolitaireCollection": {
        "title": "Solitaire Collection",
        "recommended": True,
        "note": "Preinstalled card games.",
    },
    "Microsoft.People": {
        "title": "People",
        "recommended": True,
        "note": "Contacts app.",
    },
    "Microsoft.MicrosoftOfficeHub": {
        "title": "Microsoft 365 (Office Hub)",
        "recommended": True,
        "note": "Office promotional hub; not Office itself.",
    },
    "Microsoft.SkypeApp": {
        "title": "Skype",
        "recommended": True,
        "note": "Skype UWP client.",
    },
    "Microsoft.WindowsFeedbackHub": {
        "title": "Feedback Hub",
        "recommended": True,
        "note": "Microsoft feedback submission app.",
    },
    "Microsoft.BingNews": {
        "title": "News",
        "recommended": True,
        "note": "Microsoft News feed.",
    },
    "Clipchamp.Clipchamp": {
        "title": "Clipchamp",
        "recommended": True,
        "note": "Video editor with online export.",
    },
    "Microsoft.Todos": {
        "title": "Microsoft To Do",
        "recommended": True,
        "note": "Task list app.",
    },
    "Microsoft.PowerAutomateDesktop": {
        "title": "Power Automate",
        "recommended": True,
        "note": "Desktop automation app.",
    },
    "MicrosoftTeams": {
        "title": "Microsoft Teams (personal)",
        "recommended": True,
        "note": "Personal Teams client.",
    },
    "Microsoft.WindowsSoundRecorder": {
        "title": "Sound Recorder",
        "recommended": False,
        "note": "Simple voice recorder.",
    },
    "Microsoft.WindowsAlarms": {
        "title": "Alarms & Clock",
        "recommended": False,
        "note": "Alarms, timers and stopwatch.",
    },
}


# ------------------------------------------------------------------------ catalog
@lru_cache(maxsize=1)
def tweaks() -> tuple[Tweak, ...]:
    net_ops = network_interface_ops()
    items: list[Tweak] = [
        # ------------------------------------------------------------- services
        Tweak(
            "svc_sysmain",
            "Disable SysMain (SuperFetch)",
            "Stops background app precaching. Saves RAM and reduces unnecessary SSD writes.",
            "Services",
            "safe",
            ops=(svc("SysMain"),),
            warning="Apps may open a little slower right after a reboot.",
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "svc_search",
            "Disable Windows Search Indexing",
            "Stops the file indexer from scanning drives in the background while you play.",
            "Services",
            "advanced",
            ops=(svc("WSearch"),),
            warning="Start-menu and File Explorer searches become slower.",
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "svc_telemetry",
            "Disable Telemetry & Diagnostics",
            "Stops DiagTrack and the WAP push service, and applies the diagnostic data policy.",
            "Privacy",
            "safe",
            ops=(
                svc("DiagTrack"),
                svc("dmwappushservice"),
                dword("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
            ),
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "svc_updates",
            "Windows Update — Manual Mode",
            "Sets Windows Update to manual and stops it now. Updates can still be installed when you choose.",
            "Services",
            "advanced",
            ops=(svc("wuauserv", "manual"),),
            warning="Security updates will not download automatically while this is applied.",
            recommended=False,
        ),
        Tweak(
            "svc_fax",
            "Disable Fax Service",
            "Turns off the legacy fax service. It is unused on almost every modern PC.",
            "Services",
            "safe",
            ops=(svc("Fax"),),
            recommended=False,
        ),
        Tweak(
            "svc_geolocation",
            "Disable Geolocation",
            "Stops the location service and its background tracking of your position.",
            "Services",
            "safe",
            ops=(svc("lfsvc"),),
            recommended=False,
        ),
        Tweak(
            "svc_spooler",
            "Disable Print Spooler",
            "Turns off the printing subsystem. Recommended only on PCs without a printer.",
            "Services",
            "advanced",
            ops=(svc("Spooler"),),
            warning="Printing and some PDF printers will stop working.",
            recommended=False,
        ),
        Tweak(
            "svc_maps",
            "Disable Downloaded Maps Manager",
            "Stops the offline map download service.",
            "Services",
            "safe",
            ops=(svc("MapsBroker"),),
            recommended=False,
        ),
        Tweak(
            "svc_xbox",
            "Disable Xbox Live Services",
            "Stops Xbox authentication, cloud saves and networking services.",
            "Services",
            "advanced",
            ops=(svc("XblAuthManager"), svc("XblGameSave"), svc("XboxNetApiSvc")),
            warning="Microsoft Store / Game Pass games may not sign in.",
            recommended=False,
        ),
        Tweak(
            "svc_wmp_network",
            "Disable WMP Network Sharing",
            "Stops the legacy Windows Media Player media-sharing service.",
            "Services",
            "safe",
            ops=(svc("WMPNetworkSvc"),),
            recommended=False,
        ),
        # -------------------------------------------------- kernel & registry
        Tweak(
            "kernel_paging",
            "Keep Kernel & Drivers in RAM",
            "Sets DisablePagingExecutive=1 so kernel code stays in physical memory instead of the page file.",
            "Kernel & Registry",
            "advanced",
            reboot=True,
            ops=(
                dword(
                    "HKLM",
                    r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management",
                    "DisablePagingExecutive",
                    1,
                ),
            ),
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "kernel_priority",
            "Prioritize Foreground Games",
            "Uses a short, fixed processor quantum (Win32PrioritySeparation=38) for faster foreground response.",
            "Kernel & Registry",
            "advanced",
            reboot=True,
            ops=(dword("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", 38),),
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "kernel_responsiveness",
            "Lower Multimedia System Responsiveness",
            "Sets SystemResponsiveness=0 so background multimedia work reserves less CPU for games.",
            "Kernel & Registry",
            "safe",
            ops=(
                dword(
                    "HKLM",
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                    "SystemResponsiveness",
                    0,
                ),
            ),
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "game_task_priority",
            "Boost Games Task Priority",
            "Raises the GPU and CPU scheduling priority Windows gives to the Games task profile.",
            "Kernel & Registry",
            "safe",
            ops=(
                dword("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", 8),
                dword("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", 6),
                sz("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", "High"),
                sz("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "SFIO Priority", "High"),
            ),
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "power_throttling",
            "Disable Power Throttling",
            "Prevents Windows from capping background CPU clocks for efficiency.",
            "Kernel & Registry",
            "advanced",
            reboot=True,
            ops=(dword("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "PowerThrottlingOff", 1),),
            recommended=True,
        ),
        Tweak(
            "input_latency",
            "Raw Input / Low-Latency Peripherals",
            "Removes mouse acceleration, disables pointer smoothing and tightens USB mouse/keyboard queues.",
            "Kernel & Registry",
            "advanced",
            reboot=True,
            ops=(
                sz("HKCU", r"Control Panel\Mouse", "MouseSpeed", "0"),
                sz("HKCU", r"Control Panel\Mouse", "MouseThreshold1", "0"),
                sz("HKCU", r"Control Panel\Mouse", "MouseThreshold2", "0"),
                sz("HKCU", r"Control Panel\Mouse", "MouseSensitivity", "10"),
                dword("HKLM", r"SYSTEM\CurrentControlSet\Services\mouclass\Parameters", "MouseDataQueueSize", 20),
                dword("HKLM", r"SYSTEM\CurrentControlSet\Services\kbdclass\Parameters", "KeyboardDataQueueSize", 20),
            ),
            warning="Queue-size changes are advanced; revert them if you notice dropped inputs.",
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "disable_hags",
            "Disable Hardware GPU Scheduling",
            "Sets HwSchMode=1 to let the driver manage GPU scheduling itself. Reboot required.",
            "Kernel & Registry",
            "advanced",
            reboot=True,
            ops=(dword("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", 1),),
            warning="Some modern titles run better with HAGS enabled. Toggle and benchmark both.",
            recommended=False,
        ),
        Tweak(
            "enable_hags",
            "Enable Hardware GPU Scheduling",
            "Sets HwSchMode=2 so the GPU driver schedules work directly with lower latency. Reboot required.",
            "Kernel & Registry",
            "advanced",
            reboot=True,
            ops=(dword("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", 2),),
            warning="HAGS improves latency on many modern GPUs but can reduce stability in a few titles.",
            recommended=False,
        ),
        Tweak(
            "disable_hibernation",
            "Disable Hibernation",
            "Runs powercfg -h off, deleting hiberfil.sys and freeing several GB on the system drive.",
            "Kernel & Registry",
            "safe",
            ops=(ps("powercfg.exe /hibernate off", "powercfg.exe /hibernate on", "Disable hibernation"),),
            probe=_hibernation_off,
            warning="Fast Startup and hibernate will be unavailable until reverted.",
            recommended=False,
            gaming=True,
        ),
        Tweak(
            "game_dvr",
            "Disable Game Bar & DVR Capture",
            "Turns off background gameplay recording and the Game Bar capture pipeline.",
            "Visual & DWM",
            "safe",
            ops=(
                dword("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0),
                dword("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0),
            ),
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "fullscreen_optimizations",
            "Disable Fullscreen Optimizations",
            "Forces legacy exclusive fullscreen behavior for games that ignore the Windows compositor.",
            "Kernel & Registry",
            "advanced",
            admin=False,
            ops=(
                dword("HKCU", r"System\GameConfigStore", "GameDVR_FSEBehaviorMode", 2),
                dword("HKCU", r"System\GameConfigStore", "GameDVR_HonorUserFSEBehaviorMode", 1),
                dword("HKCU", r"System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", 1),
                dword("HKCU", r"System\GameConfigStore", "GameDVR_EFSEFeatureFlags", 0),
            ),
            recommended=False,
        ),
        # ---------------------------------------------------------- network
        Tweak(
            "network_throttling",
            "Disable Network Throttling",
            "Removes Windows' 10-packet multimedia throttle (NetworkThrottlingIndex=0xFFFFFFFF).",
            "Network & Latency",
            "safe",
            ops=(
                dword(
                    "HKLM",
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                    "NetworkThrottlingIndex",
                    0xFFFFFFFF,
                ),
            ),
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "tcp_nodelay",
            "Disable Nagle & Delayed ACK",
            "Sets TCPNoDelay and TcpAckFrequency=1 on active adapters so small game packets leave immediately.",
            "Network & Latency",
            "advanced",
            reboot=True,
            ops=net_ops,
            warning="Applied to active IPv4 adapters. New adapters need the tweak re-applied.",
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "dns_cache",
            "Optimize DNS Cache",
            "Extends the positive DNS cache and flushes the resolver so lookups stop repeating.",
            "Network & Latency",
            "safe",
            ops=(
                dword("HKLM", r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters", "MaxCacheTtl", 86400),
                dword("HKLM", r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters", "MaxNegativeCacheTtl", 300),
                ps("ipconfig.exe /flushdns", label="Flush DNS cache"),
            ),
            recommended=True,
            gaming=True,
        ),
        Tweak(
            "qos_reserve",
            "Release Reserved QoS Bandwidth",
            "Sets the reserved bandwidth policy to 0 instead of the legacy 20% ceiling.",
            "Network & Latency",
            "advanced",
            ops=(dword("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched", "NonBestEffortLimit", 0),),
            warning="Most networks are unaffected; this is a legacy policy.",
            recommended=False,
        ),
        # ------------------------------------------------------------ visual
        Tweak(
            "visual_effects",
            "Disable Aero, Transparency & Animations",
            "Turns off window animations, acrylic transparency, Aero Peek and drag-full-windows effects.",
            "Visual & DWM",
            "safe",
            admin=False,
            ops=(
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 2),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 0),
                sz("HKCU", r"Control Panel\Desktop\WindowMetrics", "MinAnimate", "0"),
                sz("HKCU", r"Control Panel\Desktop", "DragFullWindows", "0"),
                dword("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek", 0),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAnimations", 0),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ListviewAlphaSelect", 0),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ListviewShadow", 0),
            ),
            recommended=False,
            gaming=True,
        ),
        Tweak(
            "explorer_perf",
            "Explorer Performance Mode",
            "Disables thumbnail generation and the floating status bar in File Explorer.",
            "Visual & DWM",
            "safe",
            admin=False,
            ops=(
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "IconsOnly", 1),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowStatusBar", 0),
            ),
            warning="Folders will show icons instead of image previews.",
            recommended=False,
        ),
        # ----------------------------------------------------------- privacy
        Tweak(
            "privacy_ads",
            "Disable Ads & Suggested Content",
            "Turns off the advertising ID, suggested apps, and silent content installs.",
            "Privacy",
            "safe",
            admin=False,
            ops=(
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SilentInstalledAppsEnabled", 0),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338388Enabled", 0),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338389Enabled", 0),
            ),
            recommended=True,
            gaming=True,
        ),
    ]
    return tuple(items)


def tweak_by_id(tweak_id: str) -> Tweak | None:
    for item in tweaks():
        if item.id == tweak_id:
            return item
    return None


def recommended_tweaks() -> list[Tweak]:
    return [item for item in tweaks() if item.recommended]


def gaming_tweaks() -> list[Tweak]:
    return [item for item in tweaks() if item.gaming]


# Hardware GPU Scheduling has two opposite variants in the catalog.  An
# "apply everything" profile can only choose one, so the legacy off-switch is
# skipped in favour of the modern enable switch.
PROFILE_CONFLICTS = {"disable_hags": "enable_hags"}


def profile_tweaks(mode: str) -> list[Tweak]:
    """Return the tweak set for a quick optimization profile."""

    if mode == "normal":
        return recommended_tweaks()
    if mode == "extreme":
        return [item for item in tweaks() if item.id not in PROFILE_CONFLICTS]
    raise ValueError(f"Unknown optimization profile: {mode!r}")



def cleaner_components() -> tuple[Tweak, ...]:
    return (
        Tweak(
            "copilot",
            "Windows Copilot",
            "Disables the Copilot button and AI data analysis through policy, including background model access.",
            "Components",
            "safe",
            admin=True,
            ops=(
                dword("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowCopilotButton", 0),
                dword("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1),
                dword("HKCU", r"Software\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", 1),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\WindowsAI", "DisableAIDataAnalysis", 1),
                dword("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", 1),
            ),
            warning="Copilot disappears from the taskbar and Edge sidebar on next sign-in.",
        ),
        Tweak(
            "recall",
            "Windows Recall",
            "Disables Recall's local screenshot history and the AI data analysis pipeline.",
            "Components",
            "safe",
            ops=(
                dword("HKCU", r"Software\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", 1),
                dword("HKCU", r"Software\Microsoft\Windows\CurrentVersion\WindowsAI", "DisableAIDataAnalysis", 1),
                dword("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", 1),
                dword("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI", "AllowRecallEnablement", 0),
            ),
            warning="Existing Recall snapshots may remain until removed in Windows Settings.",
        ),
        Tweak(
            "edge",
            "Microsoft Edge",
            "Force-uninstalls Edge through its own installer. Chromium engines used by other apps are kept.",
            "Components",
            "extreme",
            ops=(
                ps(
                    "$paths=@(\"${env:ProgramFiles(x86)}\\Microsoft\\Edge\\Application\","
                    "\"$env:ProgramFiles\\Microsoft\\Edge\\Application\");"
                    "$setup=Get-ChildItem $paths -Filter setup.exe -Recurse -ErrorAction SilentlyContinue |"
                    " Select-Object -First 1;"
                    "if(!$setup){throw 'Edge installer not found'};"
                    "Start-Process -FilePath $setup.FullName -ArgumentList "
                    "'--uninstall','--system-level','--verbose-logging','--force-uninstall' -Wait",
                    label="Uninstall Microsoft Edge",
                ),
            ),
            warning="Windows may reinstall Edge after a feature update. Some apps rely on WebView2, not Edge.",
            probe=_edge_removed,
        ),
        Tweak(
            "onedrive",
            "Microsoft OneDrive",
            "Uninstalls the OneDrive sync client and stops its background process. Your cloud files are not deleted.",
            "Components",
            "extreme",
            ops=(
                ps(
                    "Stop-Process -Name OneDrive -Force -ErrorAction SilentlyContinue;"
                    "$setup=\"$env:SystemRoot\\SysWOW64\\OneDriveSetup.exe\";"
                    "if(!(Test-Path $setup)){$setup=\"$env:SystemRoot\\System32\\OneDriveSetup.exe\"};"
                    "if(!(Test-Path $setup)){throw 'OneDrive setup not found'};"
                    "Start-Process -FilePath $setup -ArgumentList '/uninstall' -Wait",
                    label="Uninstall OneDrive",
                ),
            ),
            warning="File Explorer OneDrive shortcuts are removed. Local files stay untouched.",
            probe=_onedrive_removed,
        ),
        Tweak(
            "wmp_legacy",
            "Windows Media Player (Legacy)",
            "Removes the old Media Player feature through DISM. Modern Media Player is separate.",
            "Components",
            "advanced",
            ops=(
                ps(
                    "DISM.exe /Online /Disable-Feature /FeatureName:WindowsMediaPlayer /NoRestart",
                    "DISM.exe /Online /Enable-Feature /FeatureName:WindowsMediaPlayer /NoRestart",
                    label="Disable Windows Media Player legacy",
                ),
            ),
            probe=_wmp_removed,
        ),
        Tweak(
            "directplay",
            "DirectPlay",
            "Disables the legacy DirectX 3/5/6 compatibility layer that modern games do not use.",
            "Components",
            "advanced",
            ops=(
                ps(
                    "DISM.exe /Online /Disable-Feature /FeatureName:DirectPlay /NoRestart",
                    "DISM.exe /Online /Enable-Feature /FeatureName:DirectPlay /NoRestart",
                    label="Disable DirectPlay",
                ),
            ),
            warning="Very old games from the 1990s/2000s may need it.",
        ),
    )


def estimated_gain(tweak_ids: list[str] | set[str]) -> int:
    known = {item.id: item for item in tweaks()}
    score = 0.0
    for tweak_id in tweak_ids:
        item = known.get(tweak_id)
        if not item:
            continue
        score += 1.35 if item.risk == "advanced" else 0.9
    return max(0, min(18, round(score)))


def scan_names() -> list[str]:
    return list(APPX_CATALOG.keys())


def appx_metadata(name: str) -> dict[str, Any]:
    return APPX_CATALOG.get(name, {"title": name, "recommended": False, "note": "Installed package."})
