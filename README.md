# OPTIMUS X

A local-only Windows optimization dashboard built with Python and CustomTkinter.

Optimus X combines live hardware telemetry, reversible performance tweaks, careful
bloatware removal, a gaming profile and maintenance tools in one dark neon interface.
Every change is confirmed, backed up and written to a local audit log — nothing is
uploaded and no bundlers or installers are included.

![Dashboard](docs/screenshot-dashboard.png)

---

## Highlights

| Page | What it does |
| --- | --- |
| **Dashboard** | Live CPU / RAM / GPU gauges, sparklines, temperature readout, network latency, optimization score and two confirmed profiles: **Normal optimization** (recommended tweaks) and **Extreme optimization** (every reversible tweak). |
| **Tweaks & Privacy** | Stage, review and apply reversible service, registry, kernel, network and visual tweaks. Filters by category, shows per-tweak risk and reboot requirements, and offers one-click **Recommended** and **Extreme · all** profiles. |
| **Deep Cleaner** | Finds installed UWP/AppX bloat, removes selected packages for the current user and the provisioned image, toggles legacy components (Copilot and Recall policies, Edge and OneDrive removal, Windows Media Player Legacy, DirectPlay) and reclaims disk space from temporary locations. |
| **Game Boost** | Applies the competitive gaming profile, offers power plans, lists top processes by CPU/RAM and can end selected processes after confirmation. |
| **Toolbox** | Restore point, network stack reset, Explorer restart, disk health scan, temporary-file cleanup, Markdown system report and log access. |
| **Settings** | Administrator state, dry-run mode, restore-point default, backup counter, revert-all action, audit log viewer and local data folder. |

### What is covered

- **Services** — SysMain/SuperFetch, Windows Search indexing, Windows Update manual
  mode, telemetry/DiagTrack, Fax, Geolocation, Print Spooler, Maps manager, Xbox Live,
  Windows Media Player Network Sharing.
- **Kernel & registry** — DisablePagingExecutive, Win32PrioritySeparation, processor
  responsiveness, games task priority, power throttling, raw input latency, HAGS
  enable/disable, hibernation, Game DVR, fullscreen optimizations.
- **Network & latency** — NetworkThrottlingIndex, TCPNoDelay and TcpAckFrequency on
  active adapters, DNS cache sizing and resolver flush, QoS reserved bandwidth.
- **Visual & DWM** — transparency, window animations, Aero Peek, drag-full-windows,
  taskbar animations, and Explorer performance mode (icon-only folders, hidden status bar).
- **Privacy** — Copilot and Recall disablement, telemetry service handling.
- **UWP bloat** — Xbox suite, Mail & Calendar, Maps, Movies & TV, Weather, Phone Link,
  Get Help, Tips, Solitaire, People, Office Hub, Skype, Feedback Hub, News, Clipchamp,
  Microsoft To Do, Power Automate and more (27 known packages; only installed ones are
  listed).
- **Junk cleanup** — user temp, Windows temp, DirectX shader cache, crash dumps,
  Explorer thumbnails, Delivery Optimization cache, Windows Update download cache and
  the Recycle Bin.

---

## Requirements

- Windows 10 or Windows 11, 64-bit.
- Python 3.11 or newer (tested with Python 3.15, 64-bit).
- Administrator rights are required for system-wide changes. The interface still opens
  as a standard user and prompts for elevation when needed.

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

Run from a normal terminal. For full functionality, start with **Settings → Restart as
admin** (Windows shows a UAC prompt), or launch the terminal as administrator.

The app opens at a 1280×720 starting size and can be resized, minimized, maximized and
dragged from its custom title bar. Window position and size are remembered.

---

## Safety model

Optimus X is reversible by design.

1. **Confirmation first** — destructive or advanced actions open a dialog listing every
   change, with warnings, a risk badge and (for removals) a required acknowledgement.
   This includes the Normal and Extreme profiles and per-row staged changes.
2. **Dry-run mode** — enable it in Settings to log commands without touching the registry,
   services or files. Game Boost, Tweaks and quick optimize all report dry-run results.
3. **Restore point** — optional Windows checkpoint before applying a profile. The setting
   is preselected by default and can be disabled, but is ignored when not elevated.
4. **Backups** — original registry values and service start types are stored in
   `backups.json` before the first write. Settings → **Revert backed-up tweaks** restores
   them; Deep Cleaner component cards restore their own saved state.
5. **Audit trail** — every apply, revert, removal, cleanup and report export is appended
   to `logs\actions.log`; technical events go to `logs\optimusx.log` (rotated).
6. **No silent system access** — the app never downloads code, sends telemetry or bundles
   third-party installers.

### Administrator handling

- Standard-user sessions can browse every page, stage tweaks and preview profiles.
- Actions that need elevation show an **Administrator rights required** dialog; accepting
  relaunches the app elevated through a UAC prompt.
- AppX removal, service changes, system registry writes, restore points and repair tools
  are gated behind that prompt.
- Pure per-user registry tweaks do not require elevation.

### Reboots

Kernel, network and some service changes only take full effect after a restart. The app
marks these tweaks and reminds you when a reboot is recommended.

---

## Data locations

Everything is stored under `%LOCALAPPDATA%\OptimusX`:

```text
OptimusX\
├─ data\
│  ├─ settings.json     # preferences, window geometry, last optimization
│  └─ backups.json      # reversible registry/service snapshots
├─ logs\
│  ├─ actions.log       # human-readable audit trail
│  └─ optimusx.log      # rotating technical log
└─ reports\
   └─ OptimusX_Report_YYYYMMDD_HHMMSS.md
```

Settings → **Open data folder** opens this directory. Deleting it resets the app to its
defaults.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Buttons for system changes show an admin prompt | Run **Settings → Restart as admin** and accept the UAC prompt. |
| “Dry-run” messages appear after an action | Disable **Dry-run mode** in Settings. |
| A tweak shows `—` for latency or no temperature | The sensor or network probe is unavailable on this hardware; gauges still work. |
| Windows Defender or SmartScreen warns about the app | It is an unsigned local Python utility. Review the source or allow it locally. |
| AppX removal fails for a package | The package may be provisioned by policy or in use. Sign out/in and retry as administrator. |
| A change should be undone | Use **Settings → Revert backed-up tweaks** or the restore button on the affected Deep Cleaner card. |
| Window opens off-screen after a monitor change | Delete `%LOCALAPPDATA%\OptimusX\data\settings.json`; the window re-centers at 1280×720. |
| `ModuleNotFoundError: customtkinter` | Install dependencies with `python -m pip install -r requirements.txt`. |

---

## Project layout

```text
main.py                     Entry point
requirements.txt            Pinned dependencies
app\
├─ application.py           Window shell, navigation, quick optimize, elevation
├─ theme.py                 Colors, fonts, category metadata
├─ assets\                  Application icon
├─ core\
│  ├─ admin.py              Elevation and privilege checks
│  ├─ catalog.py            Declarative tweak, AppX and component definitions
│  ├─ cleaner.py            AppX removal, junk scanning and cleaning
│  ├─ commands.py           Streaming PowerShell runner with cancellation
│  ├─ executor.py           Backup / apply / revert engine
│  ├─ metrics.py            Background telemetry sampler
│  ├─ report.py             Markdown system report
│  ├─ store.py              Settings, backups, audit logs and paths
│  └─ system.py             Registry, services, power plans, hardware probes
└─ ui\
   ├─ chrome.py             Custom title bar, status bar, maximize, drag
   ├─ cards.py              Pillow-anti-aliased metric cards with sparklines
   ├─ controls.py           Toggle switches, glow buttons, pills, headers
   ├─ dialogs.py            Confirm / task / info dialogs
   ├─ draw.py               Color and text helpers
   ├─ flows.py              Shared confirm / restore-point / task batch flow
   ├─ gauge.py              Supersampled telemetry gauge sprites
   ├─ icons.py              Canvas icon drawing
   ├─ sidebar.py            Navigation and identity block
   ├─ toasts.py             Non-blocking notifications
   ├─ widgets.py            Page bases and resilient smooth scrolling
   └─ pages\                Dashboard, Tweaks, Cleaner, Game Boost, Toolbox, Settings
```

---

## Notes

- UI text is English; the interface uses a dark navy glass theme with cyan and green
  accents.
- The layout is tuned for 1280×720 and larger; the window enforces a minimum size so
  pages stay readable.
- AppX removal is intentionally curated. System-critical packages, the Store itself and
  frameworks are never listed.
- Some tweaks trade functionality for latency or memory (for example, disabling Search
  indexing slows Start-menu searches). Each card states the trade-off before you apply it.

## Disclaimer

Optimus X modifies Windows services, registry values, installed packages and temporary
files. It is provided as-is, without warranty. Use it on a machine you can restore, keep
a Windows restore point or image backup, and review each dialog before confirming. The
authors are not responsible for data loss, reduced functionality or policy violations
resulting from misuse.
