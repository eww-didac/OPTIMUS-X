[README.md](https://github.com/user-attachments/files/34002354/README.md)
# OPTIMUS X

A Windows 10/11 optimizer for gaming and performance, built with Python and CustomTkinter.

Optimus X combines live hardware telemetry, reversible tweaks, careful bloatware removal, a gaming profile and maintenance tools in one dark neon interface. Everything runs locally: nothing is uploaded. Every change is confirmed, backed up and logged.

![Dashboard](docs/screenshot-dashboard.png)

> **Warning:** Optimus X modifies Windows services, registry values, policies and installed packages. Use it at your own risk, on a machine you can restore, and review every dialog before confirming. See the [Disclaimer](#disclaimer).

---

## Features

| Page | What it does |
| --- | --- |
| **Dashboard** | Live CPU / RAM / GPU gauges, temperature, network latency, optimization score and two profiles: **Normal** (recommended tweaks) and **Extreme** (every reversible tweak). |
| **Tweaks & Privacy** | Stage tweaks by category, review pending changes and apply them in one batch. Shows risk level and reboot requirements, and lets you revert each tweak. |
| **Deep Cleaner** | Removes preinstalled apps (AppX), manages components (Copilot, Recall, Edge, OneDrive, Windows Media Player Legacy, DirectPlay) and cleans temporary files. |
| **Game Boost** | Applies the competitive profile, switches the power plan and ends memory-heavy background processes. |
| **Toolbox** | Restore point, SFC, DISM, network reset, Explorer restart, disk health scan and a system report. |
| **Settings** | Administrator status, dry-run mode, backups, revert-all and an activity log viewer. |

### What it optimizes

**1. Debloat and components**
- Uninstall UWP/AppX apps (Xbox, Mail & Calendar, Maps, Movies & TV, Weather, Phone Link, Cortana, Teams, Clipchamp and more). Only packages that are actually installed are listed.
- Optional removal of **Microsoft Edge** and **OneDrive**, including OneDrive's entry in the File Explorer navigation pane.
- Disable **Windows Copilot** and **Recall**.
- Disable **Windows Media Player Legacy** and **DirectPlay**.

**2. Services**
- SysMain (SuperFetch), Windows Search, Telemetry (DiagTrack, dmwappushservice and the compatibility/CEIP scheduled tasks).
- Windows Update in **controlled mode**: manual start, asks before downloading or installing, and blocks automatic restarts while you are signed in.
- Fax, Geolocation, Print Spooler, Downloaded Maps Manager, Xbox Live services and WMP network sharing.

**3. Registry and kernel**
- `DisablePagingExecutive`, `Win32PrioritySeparation`, `SystemResponsiveness`, the *Games* task priority and Power Throttling.
- Direct mouse input (no pointer acceleration) and USB selective suspend disabled.
- Hardware-accelerated GPU scheduling (HAGS): enable or disable, with the two options mutually exclusive.
- Hibernation, Game Bar/DVR and fullscreen optimizations.

**4. Network and latency**
- Nagle's algorithm (`TCPNoDelay`, `TcpAckFrequency`) on active adapters.
- `NetworkThrottlingIndex`, DNS cache tuning and the QoS reserved-bandwidth limit.

**5. Interface and visual effects**
- Transparency, window animations, Aero Peek and drag-full-windows.
- File Explorer performance mode (icons instead of thumbnails, no status bar).

**6. Disk cleanup**
- User and Windows temp files, DirectX shader cache, crash dumps, thumbnail cache, Delivery Optimization and Windows Update caches, and the Recycle Bin.

---

## Requirements

- Windows 10 or Windows 11, 64-bit.
- Python 3.11 or newer.
- Administrator rights for system-wide changes. The interface opens without them and asks for elevation when needed.

Dependencies are pinned in `requirements.txt`:

```text
customtkinter==6.0.0
psutil==7.2.2
pillow==13.0.0
```

## Install and run

```powershell
git clone https://github.com/eww-didac/OPTIMUS-X.git
cd OPTIMUS-X
python -m pip install -r requirements.txt
python main.py
```

For full functionality, open the terminal as administrator or use **Settings → Restart as admin** (Windows shows a UAC prompt).

The window opens at 1280×720, can be moved, resized and maximized, and remembers its position and size.

---

## Safety model

1. **Confirmation first:** every action lists the changes, warnings and risk level before it runs. Removals require an acknowledgement checkbox.
2. **Dry-run mode:** enable it in Settings to simulate everything. Commands are logged without touching the system, and no administrator rights are needed.
3. **Restore point:** optional before applying a profile. Windows normally allows only one every 24 hours; Optimus X handles that and tells you if it could not create one.
4. **Original-value backups:** the previous value of every registry key and the start type of every service are saved before anything is written. When two tweaks share a key, the true original value is kept.
5. **Revert:** each tweak can be reverted individually, or all at once from Settings. Edge and OneDrive are reinstalled with `winget`; AppX apps can be recovered from the Microsoft Store.
6. **Audit trail:** every apply, revert, cleanup and export is written to `logs\actions.log`.
7. **Cleanup protections:** links and NTFS junctions are never followed, and dangerous root folders are refused (for example, if `TEMP` points at a whole drive or your profile).
8. **No hidden access:** the app never downloads code, sends telemetry or bundles third-party installers.

### Reboots

Some changes (kernel, network, some services) only take full effect after a restart. Each affected tweak carries a **REBOOT** badge.

---

## Data locations

Everything is stored under `%LOCALAPPDATA%\OptimusX`:

```text
OptimusX\
├─ data\
│  ├─ settings.json     # preferences, window geometry, last optimization
│  └─ backups.json      # reversible registry/service backups
├─ logs\
│  ├─ actions.log       # human-readable audit trail
│  └─ optimusx.log      # rotating technical log
└─ reports\
   └─ OptimusX_Report_YYYYMMDD_HHMMSS.md
```

Deleting this folder resets the app. **Revert your tweaks from Settings first**, because `backups.json` is what makes them reversible.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| A button shows "Administrator rights required" | Use **Settings → Restart as admin** and accept the UAC prompt. |
| "Dry-run" messages appear | Turn off **Dry-run mode** in Settings. |
| No CPU temperature | The reading needs administrator rights and not every motherboard exposes it. The other gauges still work. |
| Reverting a tweak says "No saved backup" | The value was already set before using Optimus X, or the backup was deleted. Change it manually in Windows. |
| Edge uninstall fails | Some Windows builds and regions block it. Windows may also reinstall Edge after a feature update. |
| An AppX package fails to remove | It may be protected by policy or in use. Sign out, sign back in and retry as administrator. |
| SmartScreen or antivirus warns about the app | It is an unsigned local utility. Review the source code or allow it locally. |
| The window opens off-screen | Delete `%LOCALAPPDATA%\OptimusX\data\settings.json`. |
| `ModuleNotFoundError: customtkinter` | Run `python -m pip install -r requirements.txt`. |

---

## Project layout

```text
main.py                     Entry point
requirements.txt            Pinned dependencies
app\
├─ application.py           Window shell, navigation, quick optimize, elevation
├─ theme.py                 Colors, fonts and categories
├─ core\
│  ├─ admin.py              Elevation and privilege checks
│  ├─ catalog.py            Declarative tweak, AppX and component definitions
│  ├─ cleaner.py            File cleanup and AppX removal
│  ├─ commands.py           Streaming PowerShell runner with cancellation
│  ├─ executor.py           Backup / apply / revert engine
│  ├─ metrics.py            Background telemetry sampler
│  ├─ report.py             Markdown system report
│  ├─ store.py              Settings, backups and logs
│  └─ system.py             Registry, services, power plans and hardware probes
└─ ui\                      Title bar, cards, dialogs and pages
```

---

## Notes

- Some tweaks trade functionality for latency or memory (for example, disabling Search indexing slows down Start-menu searches). Each card states the trade-off before you apply it.
- Kernel tweaks such as `DisablePagingExecutive` are only recommended with 16 GB of RAM or more.
- The AppX list is curated: it never includes the Microsoft Store, system-critical packages or frameworks.
- The "estimated FPS gain" on the Dashboard is a rough heuristic, not a measurement.

## Disclaimer

Optimus X is provided as-is, without warranty of any kind. It modifies Windows services, registry values, installed packages and temporary files. Use it on a machine you can restore, keep a Windows restore point or full system image, and review each dialog before confirming. The authors are not responsible for data loss, reduced functionality or policy violations resulting from its use.

## License

[MIT](LICENSE)
