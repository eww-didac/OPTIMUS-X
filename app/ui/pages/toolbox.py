"""Toolbox: maintenance, repair and diagnostics actions."""

from __future__ import annotations

import os
import threading
import tkinter as tk

import customtkinter as ctk

from ... import i18n, theme
from ...core import cleaner, report, system
from ...core.commands import run_streaming
from ...core.store import store
from ...ui.controls import IconButton, PageHeader, RiskPill, SectionTitle
from ...ui.dialogs import ConfirmDialog, InfoDialog, TaskDialog
from ...ui.icons import draw_icon
from ...ui.widgets import PageBase, SmoothScrollFrame


class ToolCard(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        title: str,
        description: str,
        icon: str,
        risk: str,
        button_text: str,
        command,
        accent: str = theme.Color.CYAN,
    ) -> None:
        super().__init__(
            master, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        self.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=15, pady=(13, 0))
        head.grid_columnconfigure(1, weight=1)
        tile = tk.Canvas(head, width=32, height=32, bg=theme.Color.CARD, highlightthickness=0)
        tile.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 9))
        tile.create_oval(1, 1, 31, 31, fill="#0c202a", outline="#173343")
        draw_icon(tile, icon, 16, 16, 17, accent, 1.5)
        ctk.CTkLabel(
            head, text=i18n.tr(title), text_color=theme.Color.TEXT,
            font=theme.font(11, "bold"), anchor="w",
        ).grid(row=0, column=1, sticky="w")
        fg, bg = theme.risk_palette(risk)
        RiskPill(head, theme.risk_label(risk), fg, bg).grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(
            head, text=i18n.tr(description), text_color=theme.Color.MUTED, font=theme.font(9),
            anchor="w", justify="left", wraplength=390,
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(2, 0))
        self.button = IconButton(
            self, text=button_text, command=command, width=120, height=29,
            accent=risk == "safe", danger=risk == "extreme",
        )
        self.button.grid(row=1, column=0, sticky="w", padx=15, pady=(9, 12))


class ToolboxPage(PageBase):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = PageHeader(
            self,
            "Toolbox",
            "Repair Windows, reset networking and export a complete diagnostic snapshot.",
            eyebrow="Maintenance & repair",
        )
        header.grid(row=0, column=0, sticky="ew")
        self.host_chip = ctk.CTkLabel(
            header.actions,
            text=system.os_info()["hostname"].upper()
            + "  •  "
            + i18n.tr(system.admin_state().upper()),
            text_color=theme.Color.MUTED, font=theme.font(8, "bold"),
        )
        self.host_chip.pack(side="right")

        body = SmoothScrollFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=theme.Color.BORDER_STRONG,
            scrollbar_button_hover_color=theme.Color.CYAN_DIM,
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        section = SectionTitle(
            body, "SYSTEM REPAIR", "Signed Microsoft tools only",
            right_text="ADMIN RECOMMENDED",
        )
        section.grid(row=0, column=0, columnspan=2, sticky="ew", padx=2, pady=(2, 8))

        tools = [
            {
                "title": "Create restore point",
                "description": "Checkpoint the current registry and system state before making changes.",
                "icon": "shield",
                "risk": "safe",
                "button": "Create point",
                "command": self.create_restore_point,
                "accent": theme.Color.GREEN,
            },
            {
                "title": "System File Checker",
                "description": "Run sfc /scannow to repair corrupt protected Windows files.",
                "icon": "window",
                "risk": "safe",
                "button": "Run SFC",
                "command": lambda: self.run_command(
                    "System File Checker", "Scans and repairs protected Windows files.",
                    "sfc.exe /scannow", needs_admin=True, risk="safe", timeout=3600,
                ),
            },
            {
                "title": "DISM component repair",
                "description": "Restore the component store with DISM /RestoreHealth.",
                "icon": "cpu",
                "risk": "safe",
                "button": "Run DISM",
                "command": lambda: self.run_command(
                    "DISM component repair", "Repairs the Windows component store. This can take a while.",
                    "DISM.exe /Online /Cleanup-Image /RestoreHealth", needs_admin=True,
                    risk="advanced", timeout=3600,
                ),
            },
            {
                "title": "Flush DNS cache",
                "description": "Clear stale resolver entries after changing DNS or network settings.",
                "icon": "network",
                "risk": "safe",
                "button": "Flush DNS",
                "command": lambda: self.run_command(
                    "Flush DNS cache", "Clears the local DNS resolver cache.",
                    "ipconfig.exe /flushdns", needs_admin=False, risk="safe", timeout=30,
                ),
            },
            {
                "title": "Reset network stack",
                "description": "Reset Winsock and TCP/IP, then flush DNS. Requires a restart.",
                "icon": "refresh",
                "risk": "advanced",
                "button": "Reset network",
                "command": lambda: self.run_command(
                    "Reset network stack",
                    "Resets Winsock and TCP/IP configuration. Network adapters may briefly disconnect.",
                    "netsh.exe winsock reset; netsh.exe int ip reset; ipconfig.exe /flushdns",
                    needs_admin=True, risk="advanced", timeout=180,
                    warning="A reboot is required after the reset.",
                ),
            },
            {
                "title": "Restart Explorer",
                "description": "Restart the shell to apply Explorer and visual changes immediately.",
                "icon": "window",
                "risk": "safe",
                "button": "Restart",
                "command": lambda: self.run_command(
                    "Restart Explorer", "Stops explorer.exe; Windows starts it again automatically.",
                    "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue",
                    needs_admin=False, risk="safe", timeout=20,
                ),
            },
            {
                "title": "Clean temporary files",
                "description": "Remove user temp, shader cache, crash dumps and the Recycle Bin.",
                "icon": "broom",
                "risk": "advanced",
                "button": "Clean now",
                "command": self.clean_temp,
            },
            {
                "title": "High performance plan",
                "description": "Switch the active Windows power plan for maximum clock responsiveness.",
                "icon": "bolt",
                "risk": "safe",
                "button": "Activate",
                "command": self.high_performance,
                "accent": theme.Color.GREEN,
            },
            {
                "title": "Check disk health",
                "description": "Run a read-only chkdsk scan on the system volume.",
                "icon": "disk",
                "risk": "advanced",
                "button": "Scan disk",
                "command": lambda: self.run_command(
                    "Check disk health", "Runs a read-only NTFS health scan on the system drive.",
                    "chkdsk.exe $env:SystemDrive /scan", needs_admin=True, risk="advanced", timeout=1800,
                ),
            },
            {
                "title": "System report",
                "description": "Export OS, hardware, applied tweaks and safety state as a Markdown report.",
                "icon": "info",
                "risk": "safe",
                "button": "Export report",
                "command": self.export_report,
                "accent": theme.Color.GREEN,
            },
            {
                "title": "Open report folder",
                "description": "Open the local Optimus X report and backup folder.",
                "icon": "external",
                "risk": "safe",
                "button": "Open folder",
                "command": self.open_data_folder,
            },
            {
                "title": "Activity log",
                "description": "Review every applied or reverted change in the local audit trail.",
                "icon": "clock",
                "risk": "safe",
                "button": "Open logs",
                "command": lambda: self.app.show_page("Settings"),
            },
        ]

        for index, tool in enumerate(tools):
            card = ToolCard(
                body,
                title=tool["title"],
                description=tool["description"],
                icon=tool["icon"],
                risk=tool["risk"],
                button_text=tool["button"],
                command=tool["command"],
                accent=tool.get("accent", theme.Color.CYAN),
            )
            card.grid(
                row=1 + index // 2, column=index % 2, sticky="nsew",
                padx=(0, 5) if index % 2 == 0 else (5, 0),
                pady=(0, 7),
            )

        spacer = ctk.CTkFrame(body, fg_color="transparent", height=14)
        spacer.grid(row=1 + (len(tools) + 1) // 2, column=0, columnspan=2)

    # ----------------------------------------------------------------- commands
    def run_command(
        self,
        title: str,
        description: str,
        script: str,
        *,
        needs_admin: bool,
        risk: str,
        timeout: float = 600,
        warning: str = "",
    ) -> None:
        display_title = i18n.tr(title)
        display_description = i18n.tr(description)
        if needs_admin and not self.app.is_admin:
            self.app.prompt_admin(
                i18n.tr("{name} requires administrator rights.", name=display_title)
            )
            return

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                return
            accent = theme.Color.RED if risk == "extreme" else theme.Color.CYAN

            def worker(emit, cancel) -> dict:
                code = run_streaming(script, emit, cancel, timeout=timeout, label=title)
                return {"success": code == 0, "failed": 0 if code == 0 else 1, "returncode": code}

            def done(result: dict) -> None:
                self.app.notify(
                    i18n.tr(
                        "{name}: completed."
                        if result.get("success")
                        else "{name}: completed with errors.",
                        name=display_title,
                    ),
                    "success" if result.get("success") else "warning",
                )
                self.host_chip.configure(
                    text=system.os_info()["hostname"].upper()
                    + "  •  "
                    + i18n.tr(system.admin_state().upper())
                )

            TaskDialog(
                self.app,
                title=display_title,
                subtitle=display_description,
                worker=worker,
                on_done=done,
                accent=accent,
            )

        ConfirmDialog(
            self.app,
            title=display_title,
            message=display_description,
            confirm_text=i18n.tr("Run task"),
            items=[script],
            warnings=[i18n.tr(warning)] if warning else [],
            risk=risk,
            checkbox_text=(
                i18n.tr("I understand this may change system configuration")
                if needs_admin
                else None
            ),
            checkbox_default=False,
            require_checkbox=bool(needs_admin) and risk != "safe",
            height=390,
            on_result=confirmed,
        )

    def create_restore_point(self) -> None:
        if not self.app.is_admin:
            self.app.prompt_admin(
                i18n.tr("Creating a restore point requires administrator rights.")
            )
            return

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                return

            def worker(emit, cancel) -> dict:
                emit(i18n.tr("Requesting a Windows restore point…"))
                ok, message = system.create_restore_point("Optimus X - manual checkpoint")
                emit(message)
                return {"success": ok, "failed": 0 if ok else 1}

            def done(result: dict) -> None:
                self.app.notify(
                    i18n.tr(
                        "Restore point created."
                        if result.get("success")
                        else "Restore point could not be created."
                    ),
                    "success" if result.get("success") else "warning",
                )

            TaskDialog(
                self.app,
                title=i18n.tr("Create restore point"),
                subtitle=i18n.tr("System Protection checkpoint"),
                worker=worker,
                on_done=done,
                accent=theme.Color.GREEN,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Create a restore point?"),
            message=i18n.tr(
                "Windows System Protection may need to be enabled. This can take a minute."
            ),
            confirm_text=i18n.tr("Create"),
            risk="safe",
            on_result=confirmed,
        )

    def high_performance(self) -> None:
        ok, message = system.set_power_plan("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")
        if ok:
            self.app.notify(
                i18n.tr("High performance power plan activated."), "success"
            )
        else:
            self.app.notify(
                i18n.tr("Could not change power plan: {error}", error=message), "warning"
            )

    def export_report(self) -> None:
        try:
            path = report.export_report()
        except Exception as exc:
            self.app.notify(
                i18n.tr("Could not export report: {error}", error=exc), "warning"
            )
            return
        self.app.notify(
            i18n.tr("Report saved to {name}", name=path.name), "success"
        )
        InfoDialog(
            self.app,
            title=i18n.tr("System report exported"),
            message=i18n.tr(
                "The report was saved locally:\n\n{path}\n\nNo data was uploaded.",
                path=path,
            ),
            accent=theme.Color.GREEN,
        )

    def open_data_folder(self) -> None:
        try:
            os.startfile(str(store.root))
        except Exception as exc:
            self.app.notify(
                i18n.tr("Could not open folder: {error}", error=exc), "warning"
            )

    def clean_temp(self) -> None:
        ids = ["user_temp", "shader_cache", "crash_dumps", "thumb_cache", "recycle_bin"]
        titles = [
            i18n.tr(title)
            for title in (
                "User temporary files",
                "DirectX shader cache",
                "Crash dumps",
                "Thumbnail cache",
                "Recycle Bin",
            )
        ]

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                return

            def worker(emit, cancel) -> dict:
                result = cleaner.clean_junk(ids, emit, cancel)
                return {
                    "success": True,
                    "failed": result.get("errors", 0),
                    "removed": result.get("removed", 0),
                }

            def done(result: dict) -> None:
                removed = result.get("removed", 0)
                self.app.notify(
                    i18n.tr(
                        "{size} reclaimed.",
                        size=system.format_bytes(removed),
                    )
                    if removed
                    else i18n.tr("Temporary locations cleaned."),
                    "success",
                )
                self.app.refresh_dashboard()

            TaskDialog(
                self.app,
                title=i18n.tr("Clean temporary files"),
                subtitle=i18n.tr(
                    "User temp, shader cache, crash dumps, thumbnails and Recycle Bin"
                ),
                worker=worker,
                on_done=done,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Clean temporary files?"),
            message=i18n.tr(
                "Only cache and temporary locations are touched. The Recycle Bin will be emptied."
            ),
            confirm_text=i18n.tr("Clean now"),
            items=titles,
            risk="advanced",
            on_result=confirmed,
        )

    def on_show(self) -> None:
        self.host_chip.configure(
            text=system.os_info()["hostname"].upper()
            + "  •  "
            + i18n.tr(system.admin_state().upper())
        )
