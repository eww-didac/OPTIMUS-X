"""Settings: safety, privileges, audit trail and about."""

from __future__ import annotations

import os
import threading
import tkinter as tk

import customtkinter as ctk

from ... import i18n, theme
from ...core import system
from ...core.executor import executor
from ...core.store import APP_VERSION, store
from ...ui.controls import IconButton, PageHeader, SectionTitle
from ...ui.dialogs import ConfirmDialog, TaskDialog
from ...ui.icons import draw_icon
from ...ui.widgets import PageBase, SmoothScrollFrame


class SettingsPage(PageBase):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = PageHeader(
            self,
            "Settings",
            "Safety controls, privilege state, backups and the local audit trail.",
            eyebrow="Optimus X",
        )
        header.grid(row=0, column=0, sticky="ew")
        self.version_chip = ctk.CTkLabel(
            header.actions, text=i18n.tr("VERSION {version}", version=APP_VERSION).upper(),
            text_color=theme.Color.DIM, font=theme.font(8, "bold"),
        )
        self.version_chip.pack(side="right")

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

        self._build_privilege(body)
        self._build_behavior(body)
        self._build_safety(body)
        self._build_language(body)
        self._build_logs(body)
        self._build_about(body)
        self.refresh()

    # --------------------------------------------------------------------- cards
    def _card(self, parent: tk.Misc, *, padded: bool = True) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid_columnconfigure(0, weight=1)
        if padded:
            card.configure()
        return card

    def _build_privilege(self, body: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            body, fg_color=theme.Color.CARD_ALT, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(2, 10))
        card.grid_columnconfigure(1, weight=1)
        self.priv_icon = tk.Canvas(card, width=42, height=42, bg=theme.Color.CARD_ALT, highlightthickness=0)
        self.priv_icon.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=13)
        draw_icon(self.priv_icon, "shield", 21, 21, 27, theme.Color.GREEN, 1.7)
        self.priv_title = ctk.CTkLabel(
            card, text=i18n.tr("Administrator session"), text_color=theme.Color.TEXT,
            font=theme.font(12, "bold"), anchor="w",
        )
        self.priv_title.grid(row=0, column=1, sticky="w", pady=(13, 0))
        self.priv_detail = ctk.CTkLabel(
            card, text=i18n.tr("System-wide changes are available."), text_color=theme.Color.MUTED,
            font=theme.font(10), anchor="w",
        )
        self.priv_detail.grid(row=1, column=1, sticky="w", pady=(1, 13))
        self.elevate_btn = IconButton(
            card, text="Restart as admin", command=self.request_elevation,
            accent=True, width=138, height=31,
        )
        self.elevate_btn.grid(row=0, column=2, rowspan=2, padx=16)

    def _build_behavior(self, body: ctk.CTkFrame) -> None:
        section = SectionTitle(body, "BEHAVIOR", right_text="")
        section.grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=(2, 7))
        card = self._card(body)
        card.grid(row=2, column=0, sticky="nsew", padx=(0, 5), pady=(0, 8))
        ctk.CTkLabel(
            card, text=i18n.tr("Safety defaults"), text_color=theme.Color.TEXT,
            font=theme.font(11, "bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(13, 2))
        ctk.CTkLabel(
            card, text=i18n.tr("Controls how every staged change is executed."),
            text_color=theme.Color.MUTED, font=theme.font(9), anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        self.dry_switch = self._switch_row(
            card, row=2,
            title="Dry-run mode",
            detail="Log commands without writing registry, services or files.",
            command=self._toggle_dry_run,
        )
        self.restore_switch = self._switch_row(
            card, row=3,
            title="Restore point by default",
            detail="Preselect the Windows checkpoint before applying changes.",
            command=self._toggle_restore,
        )

    def _build_safety(self, body: ctk.CTkFrame) -> None:
        section = SectionTitle(body, "BACKUP & RESTORE", right_text="")
        section.grid(row=1, column=1, sticky="ew", padx=2, pady=(2, 7))
        card = self._card(body)
        card.grid(row=2, column=1, sticky="nsew", padx=(5, 0), pady=(0, 8))
        ctk.CTkLabel(
            card, text=i18n.tr("Reversible by design"), text_color=theme.Color.TEXT,
            font=theme.font(11, "bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(13, 2))
        self.backup_detail = ctk.CTkLabel(
            card, text=i18n.tr("Reading backups…"), text_color=theme.Color.MUTED,
            font=theme.font(9), anchor="w",
        )
        self.backup_detail.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))
        self.restore_btn = IconButton(
            row, text="Create restore point", command=self.create_restore_point,
            accent=True, width=146, height=30,
        )
        self.restore_btn.pack(side="left")
        self.open_btn = IconButton(
            row, text="Open data folder", command=self.open_data_folder,
            width=122, height=30,
        )
        self.open_btn.pack(side="left", padx=(6, 0))
        self.revert_btn = IconButton(
            card, text="Revert backed-up tweaks", command=self.revert_all,
            danger=True, width=186, height=30,
        )
        self.revert_btn.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 13))

    def _switch_row(
        self,
        parent: ctk.CTkFrame,
        *,
        row: int,
        title: str,
        detail: str,
        command,
    ) -> ctk.CTkSwitch:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 12))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame, text=i18n.tr(title), text_color=theme.Color.TEXT_SOFT,
            font=theme.font(9, "bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            frame, text=i18n.tr(detail), text_color=theme.Color.DIM,
            font=theme.font(9), anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(1, 0))
        switch = ctk.CTkSwitch(
            frame, text="", width=46, height=23, switch_width=40, switch_height=20,
            fg_color=theme.Color.BORDER, progress_color=theme.Color.CYAN,
            button_color=theme.Color.TEXT_SOFT, button_hover_color=theme.Color.WHITE,
            command=command,
        )
        switch.grid(row=0, column=1, rowspan=2, sticky="e")
        return switch

    def _build_language(self, body: ctk.CTkFrame) -> None:
        section = SectionTitle(body, "LANGUAGE", right_text="")
        section.grid(row=3, column=0, columnspan=2, sticky="ew", padx=2, pady=(10, 7))
        card = self._card(body)
        card.grid(row=4, column=0, columnspan=2, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(
            card, text=i18n.tr("Application language"), text_color=theme.Color.TEXT,
            font=theme.font(11, "bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(13, 2))
        ctk.CTkLabel(
            card, text=i18n.tr("Choose the interface language. Changes apply immediately."),
            text_color=theme.Color.MUTED, font=theme.font(9), anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 13))
        self.language_selector = ctk.CTkSegmentedButton(
            card,
            values=list(i18n.LANGUAGES.values()),
            command=self._language_changed,
            font=theme.font(9, "bold"), height=32,
            fg_color=theme.Color.CARD_ALT,
            selected_color=theme.Color.CYAN_FAINT,
            selected_hover_color="#124254",
            unselected_color=theme.Color.CARD_ALT,
            unselected_hover_color=theme.Color.CARD_HOVER,
            text_color=theme.Color.TEXT_SOFT,
        )
        self.language_selector.set(i18n.LANGUAGES[i18n.get_language()])
        self.language_selector.grid(row=0, column=1, rowspan=2, sticky="e", padx=16)

    def _language_changed(self, label: str) -> None:
        code = i18n.LANGUAGE_CODES.get(label, "en")
        if code == i18n.get_language():
            return
        self.app.set_language(code)
        self.app.notify(
            i18n.tr(
                "Language changed to Spanish."
                if code == "es"
                else "Language changed to English."
            ),
            "success",
        )

    def _build_logs(self, body: ctk.CTkFrame) -> None:
        section = SectionTitle(
            body, "LOCAL ACTIVITY", "Every change is written to disk",
            right_text="",
        )
        section.grid(row=5, column=0, columnspan=2, sticky="ew", padx=2, pady=(10, 7))
        card = self._card(body)
        card.grid(row=6, column=0, columnspan=2, sticky="ew")
        toolbar = ctk.CTkFrame(card, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 5))
        toolbar.grid_columnconfigure(0, weight=1)
        self.log_source = ctk.CTkSegmentedButton(
            toolbar,
            values=[i18n.tr("Action audit"), i18n.tr("Technical log")],
            command=lambda _value: self.refresh_log(),
            font=theme.font(9, "bold"), height=27,
            fg_color=theme.Color.CARD_ALT,
            selected_color=theme.Color.CYAN_FAINT,
            selected_hover_color="#124254",
            unselected_color=theme.Color.CARD_ALT,
            unselected_hover_color=theme.Color.CARD_HOVER,
            text_color=theme.Color.TEXT_SOFT,
        )
        self.log_source.set(i18n.tr("Action audit"))
        self.log_source.grid(row=0, column=0, sticky="w")
        self.log_refresh = IconButton(
            toolbar, text="Refresh", command=self.refresh_log, width=76, height=27,
        )
        self.log_refresh.grid(row=0, column=1, sticky="e")
        self.log_text = ctk.CTkTextbox(
            card, height=170, fg_color=theme.Color.CARD_ALT,
            text_color="#a8c6d4", font=("Consolas", 8),
            border_width=1, border_color=theme.Color.BORDER,
            corner_radius=9, wrap="none",
            scrollbar_button_color=theme.Color.BORDER_STRONG,
            scrollbar_button_hover_color=theme.Color.CYAN_DIM,
        )
        self.log_text.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.log_text.configure(state="disabled")

    def _build_about(self, body: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            body, fg_color=theme.Color.CARD_ALT, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 16))
        card.grid_columnconfigure(1, weight=1)
        logo = tk.Canvas(card, width=54, height=54, bg=theme.Color.CARD_ALT, highlightthickness=0)
        logo.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=13)
        logo.create_oval(2, 2, 52, 52, fill="#0c202a", outline="#173343")
        draw_icon(logo, "shield", 27, 27, 27, theme.Color.CYAN, 1.6)
        ctk.CTkLabel(
            card, text="OPTIMUS X", text_color=theme.Color.TEXT,
            font=theme.display(14, "bold"), anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(13, 0))
        ctk.CTkLabel(
            card,
            text=i18n.tr(
                "Version {version}  •  local-only utility  •  no telemetry, no cloud, no bundled installers. Registry and service backups stay on this machine.",
                version=APP_VERSION,
            ),
            text_color=theme.Color.MUTED, font=theme.font(9),
            anchor="w", justify="left", wraplength=760,
        ).grid(row=1, column=1, sticky="w", padx=(0, 16), pady=(2, 13))

    # ------------------------------------------------------------------- actions
    def refresh(self) -> None:
        admin = self.app.is_admin
        self.priv_title.configure(
            text=i18n.tr("Administrator session" if admin else "Standard user session")
        )
        self.priv_detail.configure(
            text=i18n.tr(
                "System-wide changes are available."
                if admin
                else "Registry, service, AppX and repair tasks need elevation."
            ),
            text_color=theme.Color.MUTED if admin else theme.Color.AMBER,
        )
        self.priv_icon.delete("all")
        draw_icon(
            self.priv_icon, "shield", 21, 21, 27,
            theme.Color.GREEN if admin else theme.Color.AMBER, 1.7,
        )
        self.elevate_btn.configure(
            text=i18n.tr("Elevated" if admin else "Restart as admin")
        )
        self.elevate_btn.configure(state="disabled" if admin else "normal")
        self.dry_switch.select() if store.get("dry_run") else self.dry_switch.deselect()
        self.restore_switch.select() if store.get("create_restore_point") else self.restore_switch.deselect()
        backups = store.backup_count()
        self.revert_btn.configure(state="normal" if backups else "disabled")
        key = (
            "{count} reversible change stored  •  {value}"
            if backups == 1
            else "{count} reversible changes stored  •  {value}"
        )
        self.backup_detail.configure(
            text=i18n.tr(key, count=backups, value=store.last_optimization_text())
        )
        self.refresh_log()

    def refresh_log(self) -> None:
        source = self.log_source.get()
        technical = source == i18n.tr("Technical log")
        text = store.read_runtime_log() if technical else store.read_actions_log()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _toggle_dry_run(self) -> None:
        value = bool(self.dry_switch.get())
        store.set("dry_run", value)
        self.app.refresh_sidebar_identity()
        self.app.notify(
            i18n.tr(
                "Dry-run enabled: commands will be logged only."
                if value
                else "Dry-run disabled."
            ),
            "info" if value else "success",
        )
        self.app.refresh_dashboard()

    def _toggle_restore(self) -> None:
        store.set("create_restore_point", bool(self.restore_switch.get()))

    def request_elevation(self) -> None:
        if self.app.is_admin:
            self.app.notify(i18n.tr("Already running with administrator rights."), "info")
            return

        def confirmed(accepted: bool, _checked: bool) -> None:
            if accepted:
                self.app.relaunch_elevated()

        ConfirmDialog(
            self.app,
            title=i18n.tr("Restart as administrator?"),
            message=i18n.tr(
                "Windows will show a UAC prompt. Optimus X will close and reopen elevated; "
                "your settings and backups are kept."
            ),
            confirm_text=i18n.tr("Restart elevated"),
            risk="safe",
            on_result=confirmed,
        )

    def open_data_folder(self) -> None:
        try:
            os.startfile(str(store.root))
        except Exception as exc:
            self.app.notify(i18n.tr("Could not open folder: {error}", error=exc), "warning")

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
                ok, message = system.create_restore_point(
                    "Optimus X - settings checkpoint"
                )
                emit(message)
                return {"success": ok, "failed": 0 if ok else 1}

            def done(result: dict) -> None:
                self.app.notify(
                    i18n.tr(
                        "Restore point created."
                        if result.get("success")
                        else "Restore point failed."
                    ),
                    "success" if result.get("success") else "warning",
                )

            TaskDialog(
                self.app,
                title=i18n.tr("Create restore point"),
                subtitle=i18n.tr("Windows System Protection checkpoint"),
                worker=worker,
                on_done=done,
                accent=theme.Color.GREEN,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Create restore point?"),
            message=i18n.tr(
                "Windows may need System Protection enabled. This can take a minute."
            ),
            confirm_text=i18n.tr("Create"),
            risk="safe",
            on_result=confirmed,
        )

    def revert_all(self) -> None:
        backups = store.backup_count()
        if backups == 0:
            self.app.notify(i18n.tr("There are no stored tweaks to revert."), "info")
            return
        if not self.app.is_admin:
            self.app.prompt_admin(
                i18n.tr("Restoring backed-up system values requires administrator rights.")
            )
            return

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                return

            def worker(emit, cancel) -> dict:
                return executor.revert_all(emit=emit, cancel=cancel)

            def done(result: dict) -> None:
                store.update({"gaming_mode": False, "gaming_profile_applied": []})
                self.app.refresh_dashboard()
                self.app.refresh_sidebar_identity()
                self.refresh()
                if result.get("dry_run"):
                    self.app.notify(
                        i18n.tr("Dry-run complete — no values were restored."), "info"
                    )
                else:
                    self.app.notify(
                        i18n.tr(
                            "{count} tweak(s) restored to their previous values.",
                            count=result.get("ok", 0),
                        ),
                        "success" if not result.get("failed") else "warning",
                    )

            TaskDialog(
                self.app,
                title=i18n.tr("Reverting all applied tweaks"),
                subtitle=i18n.tr(
                    "Restoring {count} backed-up system state(s)", count=backups
                ),
                worker=worker,
                on_done=done,
                accent=theme.Color.CYAN,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Revert every applied tweak?"),
            message=i18n.tr(
                "Optimus X will restore the registry values and service start types saved in the local backup. "
                "Changes that had no backup (such as Edge removal) cannot be undone."
            ),
            confirm_text=i18n.tr("Revert everything"),
            warnings=[
                i18n.tr("This restores all tweaks recorded in the backup store."),
                i18n.tr("A reboot may be required for kernel and network changes."),
            ],
            risk="advanced",
            checkbox_text=i18n.tr("I want to restore all backed-up values"),
            checkbox_default=False,
            require_checkbox=True,
            on_result=confirmed,
        )

    def on_show(self) -> None:
        self.refresh()
