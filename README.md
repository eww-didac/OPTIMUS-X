[README(5).md](https://github.com/user-attachments/files/34152856/README.5.md)
<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/logo.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/logo-light.svg">
  <img src="docs/logo-light.svg" alt="Optimus X" width="420">
</picture>

<br>

**A Windows optimizer for gaming PCs, with backups, dry-run mode and a revert button for every setting it can restore.**

<br>

![Platform](https://img.shields.io/badge/Windows-10%20%7C%2011%20(64--bit)-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![Version](https://img.shields.io/badge/Version-2.0-34C9F4?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-2FE0A4?style=for-the-badge)

<br>

<img src="docs/screenshot-dashboard.png" alt="Optimus X dashboard" width="900">

</div>

<br>

## Read this first

Optimus X changes real Windows settings. Before you run it:

- **Not everything can be undone.** Registry values and service settings are backed up and can be restored from the app. Removing apps, uninstalling Edge or OneDrive, and cleaning files **cannot** be restored by the revert button. See [What can and cannot be reverted](#what-can-and-cannot-be-reverted).
- **Windows Update moves to manual mode.** You will no longer get updates automatically. Install security updates yourself on a regular basis.
- **The installer is not code-signed yet.** Windows SmartScreen will warn you. Verify the file hash (see [Installation](#installation)) and read the source before you click *Run anyway*.
- **Create a restore point or system image first.** The app can do it for you, but a full backup is safer.
- **Use dry-run mode on your first run.** It shows exactly what would change without touching your system.

<br>

## Overview

Windows ships with preinstalled apps, background services, telemetry and visual effects that use RAM, CPU and disk. Optimus X lets you turn them off from one dashboard and shows you what each change does before you apply it.

| Feature | Details |
| --- | --- |
| **Backup and revert** | The original value of each registry and service setting is saved before it is changed. One click restores it. |
| **Dry-run mode** | Preview every change without modifying your system. |
| **Confirmation window** | Lists every change with its risk level, reboot requirement and trade-off before anything runs. |
| **Activity log** | Every change is written to a readable log. |
| **Local only** | No account, no cloud. See [Privacy and network activity](#privacy-and-network-activity). |

<br>

## Features

### Dashboard
Live CPU, RAM and GPU gauges, temperature, network latency and an optimization score. Two profiles:

- **Normal optimization:** a recommended set of 14 tweaks that can all be reverted from the app.
- **Extreme optimization:** all 27 tweaks, including advanced ones and some that cannot be reverted. It asks you to create a restore point first.

### Tweaks & Privacy
Turn individual tweaks on or off, review them, then apply them in one batch. Each tweak shows its risk level and whether it needs a reboot.

### Deep Cleaner
Removes preinstalled apps, optionally uninstalls Microsoft Edge and OneDrive, disables Copilot and Recall, and cleans temporary files and caches.

### Game Boost
Switches on the gaming profile, changes the power plan and closes memory-hungry background apps.

### Toolbox
Creates a restore point, runs SFC and DISM, resets the network stack, restarts Explorer, checks disk health and exports a system report.

### Settings
Shows your administrator status, toggles dry-run mode, reverts all backed-up tweaks and opens the activity log.

<br>

## What it changes

Counts and defaults can change between versions. The confirmation window always shows the current list.

> The **Reverts from the app** column describes the type of change. Check it against the code or the in-app confirmation window before relying on it.

### Debloat and components

| Change | Reverts from the app | Trade-off |
| --- | --- | --- |
| Preinstalled UWP/AppX apps (only installed ones are listed; the Microsoft Store and system-critical packages are excluded) | No. Reinstall from the Microsoft Store | You lose those apps and their data |
| Microsoft Edge | No | Windows can reinstall it after a feature update. Some apps depend on Edge components such as WebView2 |
| OneDrive and its File Explorer sidebar entry | Sidebar entry: yes. Uninstall: no | Files synced to the cloud stop syncing |
| Windows Copilot | Yes | Feature unavailable |
| Recall | Yes | Windows 11 only |
| Windows Media Player Legacy and DirectPlay | No. Re-enable in *Windows Features* | Old games or media apps may need DirectPlay |

### Services

| Change | Reverts from the app | Trade-off |
| --- | --- | --- |
| SysMain (SuperFetch) off | Yes | Less app preloading and fewer SSD writes. Little effect on modern SSDs, and apps may open a bit slower on HDDs |
| Windows Search off | Yes | Start menu and File Explorer searches become slower |
| Windows Update in controlled mode | Yes | Manual start, asks before downloading or installing, and does not restart your PC while you are signed in. **You must install security updates yourself** |
| Telemetry (DiagTrack, push service, compatibility and CEIP tasks) | Yes | Less diagnostic data sent to Microsoft |
| Fax, Geolocation, Downloaded Maps, WMP network sharing | Yes | Matching features stop working |
| Print Spooler | Yes | **You cannot print** until it is re-enabled |
| Xbox Live services | Yes | Xbox app, Game Pass and games that use Xbox sign-in or cloud saves may stop working |

### Registry and kernel

| Change | Reverts from the app | Trade-off |
| --- | --- | --- |
| Keep kernel and drivers in RAM (`DisablePagingExecutive`) | Yes | Recommended only with 16 GB of RAM or more |
| Foreground game priority and multimedia scheduling | Yes | Background tasks get less CPU time while a game runs |
| Power Throttling off | Yes | Higher power use and heat, especially on laptops |
| Raw mouse input (no pointer acceleration) | Yes | Pointer feel changes |
| USB selective suspend off | Yes | Slightly higher power use on laptops |
| Hardware-accelerated GPU scheduling (HAGS) on or off | Yes | Results depend on GPU and driver. It can help or hurt |
| Hibernation off | Yes | Frees several GB, but also disables Fast Startup and hibernate |
| Game Bar and DVR off | Yes | Xbox Game Bar capture stops working |
| Fullscreen optimizations off | Yes | Some games perform worse without them |

### Network and latency

| Change | Reverts from the app | Trade-off |
| --- | --- | --- |
| Nagle's algorithm and delayed ACK off on active adapters | Yes | Benefit is small and depends on the game and network |
| Network throttling removed | Yes | Small effect on most setups |
| DNS cache tuning | Yes | Small effect |
| Reserved QoS bandwidth released | Yes | Small effect |

### Interface and visual effects

| Change | Reverts from the app | Trade-off |
| --- | --- | --- |
| Transparency, window animations, Aero Peek, drag full windows off | Yes | Plainer look |
| File Explorer performance mode (icons instead of thumbnails, no status bar) | Yes | Less visual information |

### Disk cleanup

| Change | Reverts from the app | Trade-off |
| --- | --- | --- |
| User and Windows temp files | No | Deleted files are gone |
| DirectX shader cache, crash dumps, thumbnail cache | No | Games rebuild the shader cache, so the first launch afterwards can stutter |
| Delivery Optimization and Windows Update caches | No | Updates may need to download again |
| Recycle Bin | No | Permanently deletes its contents |

The cleaner never follows links and refuses to touch protected folders.

<br>

## What can and cannot be reverted

| Type of change | How to undo it |
| --- | --- |
| Registry values and service settings | **Settings → Revert backed-up tweaks**, or revert a single tweak. Uses the value saved before the change |
| Apps removed | Reinstall from the Microsoft Store |
| Edge and OneDrive uninstalled | Reinstall manually from Microsoft |
| Optional Windows features (WMP Legacy, DirectPlay) | *Windows Features* control panel |
| Deleted temp files, caches and Recycle Bin | Cannot be restored |

If a tweak says **"No saved backup"** when you revert it, that value was already set before you used Optimus X, or its backup was deleted. The app cannot know the original value, so change it manually in Windows.

For anything the app cannot restore, use the **Windows restore point** it offers to create, or a system image.

<br>

## Performance expectations

There are no published benchmarks for Optimus X yet. Results depend heavily on your hardware, drivers and games. Several tweaks, such as Nagle/delayed ACK and SysMain, have small or debatable effects on modern hardware, and removing apps or services mainly frees memory and background activity rather than raising frame rates directly.

The **"Estimated performance gain"** shown on the dashboard is a rough guide, not a measurement. To check the real effect on your PC, measure frame times before and after with a tool such as [CapFrameX](https://www.capframex.com/) or [PresentMon](https://github.com/GameTechDev/PresentMon), using the same game and scene.

<br>

## Installation

**Requirements:** Windows 10 or Windows 11, 64-bit. Copilot and Recall options apply to Windows 11 only.

1. Open the [latest release](https://github.com/eww-didac/OPTIMUS-X/releases/latest) and download `OptimusX-Setup-x.x.x.exe`.
2. Verify the download. In PowerShell, run:

   ```powershell
   Get-FileHash .\OptimusX-Setup-x.x.x.exe -Algorithm SHA256
   ```

   The result must match the SHA-256 published in the release notes:

   ```text
   SHA-256: <add the hash here for each release>
   ```

3. Double-click the installer. If Windows shows *"Windows protected your PC"*, this is because the installer is not code-signed yet. Only continue with **More info → Run anyway** if the hash matches.
4. Click **Next → Install**, then **Finish**.
5. Open **Optimus X** and accept the Windows (UAC) prompt so every feature can work.

**To uninstall:** *Settings → Apps → Installed apps → Optimus X → Uninstall*. Your settings and backups stay in `%LOCALAPPDATA%\OptimusX`, so you can still revert tweaks if you reinstall later.

<details>
<summary><b>Run from source or build the installer</b></summary>

<br>

You need [Python 3.11+](https://www.python.org/downloads/) with **"Add Python to PATH"** ticked.

```powershell
git clone https://github.com/eww-didac/OPTIMUS-X.git
cd OPTIMUS-X
python -m pip install -r requirements.txt
python main.py
```

To build the installer, install [Inno Setup 6](https://jrsoftware.org/isdl.php) and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

</details>

<br>

## How to use it

1. Open the **Dashboard** and review your system status.
2. Turn on **Dry-run mode** in Settings and apply a profile once to see what would change.
3. Turn dry-run off. Click **Normal optimization**, or open **Tweaks & Privacy** and choose individual tweaks.
4. Read the confirmation window. It lists every change, its risk level and any warning.
5. Keep **"Create a restore point"** ticked and confirm.
6. Restart Windows if the app says a reboot is needed.

To undo backed-up changes, go to **Settings → Revert backed-up tweaks**.

<br>

## Privacy and network activity

- No account, no cloud, no telemetry sent by Optimus X.
- The dashboard measures network latency by pinging `1.1.1.1` (Cloudflare DNS). This is the only network activity the app is designed to perform.
- The app does not download or run code from the internet and does not bundle third-party installers.
- The full source is in this repository, so you can check these claims.

### Where your data is stored

Everything lives in `%LOCALAPPDATA%\OptimusX`:

| Folder | Contents |
| --- | --- |
| `data\` | Your preferences and the backups used to revert changes |
| `logs\` | A readable activity log and a technical log |
| `reports\` | System reports exported from the Toolbox |

> **Revert your tweaks from Settings before you delete this folder.** The backups in it are what make changes reversible.

<br>

## FAQ

<details>
<summary><b>Is it safe?</b></summary>

<br>

It is designed to reduce risk with confirmations, backups, dry-run mode and an optional restore point. It still changes real Windows settings and some changes cannot be reverted by the app. Read each confirmation window and keep a restore point or system image.

</details>

<details>
<summary><b>Do I need administrator rights?</b></summary>

<br>

For changes to services, the system registry and installed apps, yes. The app opens without them and offers to restart as administrator when needed.

</details>

<details>
<summary><b>Windows SmartScreen or my antivirus shows a warning.</b></summary>

<br>

The installer is not code-signed yet, and security tools are often cautious about software that edits system settings. Check the installer's SHA-256 against the release notes, and review the source in this repository before continuing.

</details>

<details>
<summary><b>The Edge uninstall failed.</b></summary>

<br>

Some Windows builds and regions block it. Windows can also reinstall Edge after a feature update.

</details>

<details>
<summary><b>I don't see a CPU temperature.</b></summary>

<br>

The reading needs administrator rights, and not every motherboard exposes it. The other gauges still work.

</details>

<details>
<summary><b>The window opened off-screen.</b></summary>

<br>

Delete `%LOCALAPPDATA%\OptimusX\data\settings.json` and start the app again.

</details>

<details>
<summary><b>I get <code>ModuleNotFoundError: customtkinter</code> (running from source).</b></summary>

<br>

Run `python -m pip install -r requirements.txt` again from the project folder. This does not happen with the installer.

</details>

<br>

## Reporting problems

Open an [issue](https://github.com/eww-didac/OPTIMUS-X/issues) and include your Windows version, the Optimus X version, what you applied and the relevant lines from `%LOCALAPPDATA%\OptimusX\logs`.

<br>

## Disclaimer

Optimus X is provided **as-is, without warranty of any kind**. It modifies Windows services, registry values, installed packages and files. Use it on a machine you can restore, keep a Windows restore point or system image, and review each dialog before confirming. The authors are not responsible for data loss, reduced functionality, loss of security updates or policy violations resulting from its use.

<br>

## License

Released under the [MIT License](LICENSE).
