"""Game Boost: one-click competitive profile, process cleanup and power plans."""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Callable

import customtkinter as ctk
import psutil

from ... import i18n, theme
from ...core import catalog, system
from ...core.executor import executor
from ...core.store import store
from ...ui.controls import IconButton, PageHeader, RiskPill, SectionTitle, ToggleSwitch
from ...ui.dialogs import ConfirmDialog, TaskDialog
from ...ui.draw import round_rect
from ...ui.icons import draw_icon
from ...ui.widgets import PageBase, SmoothScrollFrame


class GameBoostPage(PageBase):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._busy = False
        self._process_vars: dict[int, ctk.BooleanVar] = {}
        self._process_rows: dict[int, dict] = {}
        self._refresh_job: str | None = None

        header = PageHeader(
            self,
            "Game Boost",
            "A competitive profile for latency, frame-time consistency and background noise.",
            eyebrow="Performance profile",
        )
        header.grid(row=0, column=0, sticky="ew")
        self.power_chip = ctk.CTkLabel(
            header.actions, text=i18n.tr("POWER PLAN  •  —"), text_color=theme.Color.MUTED,
            font=theme.font(8, "bold"),
        )
        self.power_chip.pack(side="right", padx=(0, 4))

        body = SmoothScrollFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=theme.Color.BORDER_STRONG,
            scrollbar_button_hover_color=theme.Color.CYAN_DIM,
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        self._build_hero(body)
        self._build_profile(body)
        self._build_processes(body)
        self._build_power(body)
        self.refresh()

    # --------------------------------------------------------------------- layout
    def _build_hero(self, body: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            body, fg_color=theme.Color.CARD, corner_radius=14,
            border_width=1, border_color="#1b4b5a",
        )
        card.grid(row=0, column=0, sticky="ew", pady=(2, 12))
        card.grid_columnconfigure(0, weight=1)
        accent = tk.Canvas(card, width=4, height=132, bg=theme.Color.CARD, highlightthickness=0)
        accent.grid(row=0, column=0, rowspan=2, sticky="w", padx=(1, 0))
        accent.create_rectangle(0, 18, 3, 114, fill=theme.Color.CYAN, outline="")

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(24, 10), pady=(18, 0))
        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(
            title_row, text=i18n.tr("GAME BOOST"), text_color=theme.Color.TEXT,
            font=theme.display(24, "bold"),
        ).pack(side="left")
        RiskPill(title_row, "COMPETITIVE", theme.Color.CYAN, "#092b38").pack(
            side="left", padx=(9, 0), pady=(4, 0)
        )
        ctk.CTkLabel(
            left,
            text=i18n.tr(
                "Applies the reversible gaming profile: kernel priority, input latency, "
                "network throttling, telemetry, search and visual effects."
            ),
            text_color=theme.Color.MUTED, font=theme.font(10), justify="left", wraplength=560,
        ).pack(anchor="w", pady=(4, 6))
        self.profile_status = ctk.CTkLabel(
            left, text=i18n.tr("STAND BY"), text_color=theme.Color.AMBER,
            font=theme.font(9, "bold"),
        )
        self.profile_status.pack(anchor="w")
        self.profile_hint = ctk.CTkLabel(
            left,
            text=i18n.tr("Tweak count: 13  •  Reboot recommended  •  Backup enabled"),
            text_color=theme.Color.DIM, font=theme.font(9),
        )
        self.profile_hint.pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=(10, 26), pady=(16, 0))
        self.big_toggle = ToggleSwitch(
            right, value=False, command=self._toggle_gaming,
            width=74, height=38, bg=theme.Color.CARD, accent=theme.Color.GREEN,
        )
        self.big_toggle.pack(anchor="e")
        ctk.CTkLabel(
            right, text=i18n.tr("GAMING MODE"), text_color=theme.Color.DIM,
            font=theme.font(8, "bold"),
        ).pack(anchor="e", pady=(6, 0))
        self.hero_action = IconButton(
            right, text="Activate profile", command=self._toggle_from_button,
            accent=True, width=142, height=30,
        )
        self.hero_action.pack(anchor="e", pady=(10, 0))

        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.grid(row=1, column=0, columnspan=2, sticky="ew", padx=24, pady=(9, 15))
        for column in range(3):
            stats.grid_columnconfigure(column, weight=1)
        self._stat_values: dict[str, ctk.CTkLabel] = {}
        for column, (title, detail, initial) in enumerate(
            (
                ("APPLIED TWEAKS", "Counted from the gaming profile", "0 / 0"),
                ("REBOOT STATUS", "Kernel changes need one restart", "—"),
                ("SAFETY", "Restore point + local backup", "READY"),
            )
        ):
            box = ctk.CTkFrame(stats, fg_color="transparent")
            box.grid(row=0, column=column, sticky="w")
            ctk.CTkLabel(
                box, text=i18n.tr(title), text_color=theme.Color.DIM,
                font=theme.font(8, "bold"),
            ).pack(anchor="w")
            value = ctk.CTkLabel(
                box, text=i18n.tr(initial), text_color=theme.Color.TEXT_SOFT,
                font=theme.display(13, "bold"),
            )
            value.pack(anchor="w", pady=(2, 0))
            self._stat_values[title] = value
            ctk.CTkLabel(
                box, text=i18n.tr(detail), text_color=theme.Color.MUTED,
                font=theme.font(9),
            ).pack(anchor="w", pady=(1, 0))

    def _build_profile(self, body: ctk.CTkFrame) -> None:
        section = SectionTitle(
            body, "PROFILE CHECKLIST", "Changes included in Game Boost",
            right_text=i18n.tr("{count} CHECKS", count=len(catalog.gaming_tweaks())),
        )
        section.grid(row=1, column=0, sticky="ew", padx=2, pady=(4, 8))
        card = ctk.CTkFrame(
            body, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid(row=2, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)
        self._profile_grid = card
        self._profile_rows: dict[str, tuple[tk.Canvas, ctk.CTkLabel]] = {}
        for index, tweak in enumerate(catalog.gaming_tweaks()):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.grid(
                row=index // 2, column=index % 2, sticky="ew",
                padx=(16, 8) if index % 2 == 0 else (8, 16),
                pady=7,
            )
            row.grid_columnconfigure(1, weight=1)
            dot = tk.Canvas(row, width=10, height=10, bg=theme.Color.CARD, highlightthickness=0)
            dot.grid(row=0, column=0, padx=(0, 7))
            circle = dot.create_oval(1, 1, 9, 9, fill=theme.Color.DIM, outline="")
            text = ctk.CTkLabel(
                row, text=i18n.tr(tweak.title), text_color=theme.Color.TEXT_SOFT,
                font=theme.font(9), anchor="w",
            )
            text.grid(row=0, column=1, sticky="w")
            self._profile_rows[tweak.id] = (dot, text)

    def _build_processes(self, body: ctk.CTkFrame) -> None:
        section = SectionTitle(
            body, "BACKGROUND PROCESSES", "High-memory apps that can steal frame time",
            right_text="",
        )
        section.grid(row=3, column=0, sticky="ew", padx=2, pady=(16, 8))
        card = ctk.CTkFrame(
            body, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid(row=4, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        toolbar = ctk.CTkFrame(card, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 7))
        toolbar.grid_columnconfigure(0, weight=1)
        self.process_hint = ctk.CTkLabel(
            toolbar, text=i18n.tr("Reading process list…"), text_color=theme.Color.MUTED,
            font=theme.font(9), anchor="w",
        )
        self.process_hint.grid(row=0, column=0, sticky="w")
        self.refresh_processes_btn = IconButton(
            toolbar, text="Refresh", command=self.refresh_processes, width=76, height=28,
        )
        self.refresh_processes_btn.grid(row=0, column=1, padx=(8, 6))
        self.end_processes_btn = IconButton(
            toolbar, text="End selected", command=self.end_selected_processes,
            danger=True, width=110, height=28,
        )
        self.end_processes_btn.grid(row=0, column=2)
        self.end_processes_btn.configure(state="disabled")
        self.process_list = ctk.CTkFrame(card, fg_color="transparent")
        self.process_list.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.process_list.grid_columnconfigure(0, weight=1)

    def _build_power(self, body: ctk.CTkFrame) -> None:
        section = SectionTitle(
            body, "POWER PLAN", "Windows processor scheduling for the current session",
            right_text="",
        )
        section.grid(row=5, column=0, sticky="ew", padx=2, pady=(16, 8))
        card = ctk.CTkFrame(
            body, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid(row=6, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        self.power_label = ctk.CTkLabel(
            card, text=i18n.tr("Reading active power plan…"), text_color=theme.Color.TEXT,
            font=theme.font(12, "bold"), anchor="w",
        )
        self.power_label.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        self.power_detail = ctk.CTkLabel(
            card, text="", text_color=theme.Color.MUTED, font=theme.font(9), anchor="w",
        )
        self.power_detail.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=0, column=1, rowspan=2, sticky="e", padx=16)
        self.balanced_btn = IconButton(
            buttons, text="Balanced", command=lambda: self.set_power_plan(
                "381b4222-f694-41f0-9685-ff5bb260df2e", "Balanced"
            ), width=100, height=30,
        )
        self.balanced_btn.pack(side="left", padx=(0, 6))
        self.high_btn = IconButton(
            buttons, text="High performance", command=lambda: self.set_power_plan(
                "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", "High performance"
            ), accent=True, width=140, height=30,
        )
        self.high_btn.pack(side="left")
        spacer = ctk.CTkFrame(body, fg_color="transparent", height=16)
        spacer.grid(row=7, column=0)

    # -------------------------------------------------------------------- profile
    def refresh(self) -> None:
        gaming = bool(store.get("gaming_mode", False))
        self.big_toggle.set(gaming)
        self.profile_status.configure(
            text=i18n.tr("ACTIVATED" if gaming else "STAND BY"),
            text_color=theme.Color.GREEN if gaming else theme.Color.AMBER,
        )
        self.hero_action.configure(
            text=i18n.tr("Deactivate profile" if gaming else "Activate profile")
        )
        self.profile_hint.configure(
            text=i18n.tr(
                "{count} tweaks in profile  •  Reboot recommended  •  Fully reversible"
                if gaming
                else "{count} tweaks in profile  •  Backup enabled  •  Fully reversible",
                count=len(catalog.gaming_tweaks()),
            )
        )
        for tweak in catalog.gaming_tweaks():
            applied = bool(executor.is_applied(tweak))
            dot, label = self._profile_rows[tweak.id]
            dot.delete("all")
            dot.create_oval(
                1, 1, 9, 9,
                fill=theme.Color.GREEN if applied else "#273548",
                outline="",
            )
            label.configure(text_color=theme.Color.TEXT_SOFT if applied else theme.Color.MUTED)
        total = len(catalog.gaming_tweaks())
        applied_total = sum(
            1 for tweak in catalog.gaming_tweaks() if executor.is_applied(tweak)
        )
        self._stat_values["APPLIED TWEAKS"].configure(text=f"{applied_total} / {total}")
        self._stat_values["REBOOT STATUS"].configure(
            text=i18n.tr("RECOMMENDED" if gaming else "NOT ACTIVE"),
            text_color=theme.Color.AMBER if gaming else theme.Color.MUTED,
        )
        self._stat_values["SAFETY"].configure(
            text=i18n.tr("PROTECTED" if gaming else "READY"),
            text_color=theme.Color.GREEN if gaming else theme.Color.TEXT_SOFT,
        )
        plan = system.power_plan()
        self.power_label.configure(
            text=i18n.tr(plan["name"] or "Unknown power plan")
        )
        self.power_detail.configure(
            text=i18n.tr(
                "{guid}  •  switch to High performance before a long session",
                guid=plan["guid"] or "—",
            )
        )
        self.power_chip.configure(
            text=i18n.tr("POWER PLAN  •  {name}", name=(plan["name"] or "—").upper())
        )
        self.refresh_processes()

    def _toggle_from_button(self) -> None:
        target = not bool(store.get("gaming_mode", False))
        self.big_toggle.set(target)
        self._toggle_gaming(target)

    def _toggle_gaming(self, activate: bool) -> None:
        if self._busy:
            self.big_toggle.set(bool(store.get("gaming_mode", False)))
            return
        current = bool(store.get("gaming_mode", False))
        if activate == current:
            return
        if activate:
            items = [tweak for tweak in catalog.gaming_tweaks() if not executor.is_applied(tweak)]
            if not items:
                store.set("gaming_mode", True)
                self.refresh()
                self.app.refresh_dashboard()
                self.app.notify(i18n.tr("Gaming profile is already active."), "info")
                return
            self._confirm_activate(items)
        else:
            stored = store.get("gaming_profile_applied", [])
            items = [tweak for tweak in catalog.tweaks() if tweak.id in stored]
            if not items:
                store.set("gaming_mode", False)
                self.refresh()
                self.app.refresh_dashboard()
                return
            self._confirm_deactivate(items)

    def _confirm_activate(self, items: list[catalog.Tweak]) -> None:
        if not self.app.is_admin:
            self.big_toggle.set(False)
            self.app.prompt_admin(
                i18n.tr("Activating Game Boost requires administrator rights.")
            )
            return

        def confirmed(accepted: bool, checked: bool) -> None:
            if not accepted:
                self.big_toggle.set(bool(store.get("gaming_mode", False)))
                return
            store.set("create_restore_point", checked)
            self._busy = True

            def worker(emit, cancel: threading.Event) -> dict:
                return executor.apply_many(
                    items, create_restore_point=checked, emit=emit, cancel=cancel
                )

            def done(result: dict) -> None:
                self._busy = False
                failed = int(result.get("failed") or 0)
                dry = bool(result.get("dry_run"))
                if failed == 0 and not dry:
                    store.update(
                        {
                            "gaming_mode": True,
                            "gaming_profile_applied": [item.id for item in items],
                        }
                    )
                self.refresh()
                self.app.refresh_dashboard()
                if dry:
                    self.app.notify(
                        i18n.tr("Dry-run complete — Game Boost was not applied."), "info"
                    )
                elif failed:
                    self.app.notify(i18n.tr("Game Boost applied with issues."), "warning")
                else:
                    self.app.notify(i18n.tr("Game Boost activated."), "success")
                if result.get("reboot") and not dry:
                    self.app.notify(
                        i18n.tr("Reboot to finish applying kernel and network tweaks."),
                        "info",
                    )

            TaskDialog(
                self.app,
                title=i18n.tr("Activating Game Boost"),
                subtitle=i18n.tr(
                    "{count} reversible changes · competitive profile", count=len(items)
                ),
                worker=worker,
                on_done=done,
                accent=theme.Color.GREEN,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Activate Game Boost?"),
            message=i18n.tr(
                "Optimus X will apply the competitive profile. Existing values are backed up first, "
                "so Deactivate can restore them later."
            ),
            confirm_text=i18n.tr("Activate profile"),
            items=[i18n.tr("ENABLE  ·  {name}", name=i18n.tr(item.title)) for item in items],
            warnings=[
                i18n.tr("Kernel and network changes take full effect after a reboot.")
            ],
            risk="advanced",
            checkbox_text=i18n.tr("Create a Windows restore point first"),
            checkbox_default=bool(store.get("create_restore_point", True)),
            height=480 if len(items) < 10 else 550,
            on_result=confirmed,
        )

    def _confirm_deactivate(self, items: list[catalog.Tweak]) -> None:
        if not self.app.is_admin:
            self.big_toggle.set(True)
            self.app.prompt_admin(
                i18n.tr("Restoring the gaming profile requires administrator rights.")
            )
            return

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                self.big_toggle.set(True)
                return
            self._busy = True

            def worker(emit, cancel: threading.Event) -> dict:
                return executor.revert_many(items, emit=emit, cancel=cancel)

            def done(result: dict) -> None:
                self._busy = False
                dry = bool(result.get("dry_run"))
                if not dry:
                    store.update({"gaming_mode": False, "gaming_profile_applied": []})
                self.refresh()
                self.app.refresh_dashboard()
                if dry:
                    self.app.notify(
                        i18n.tr(
                            "Dry-run complete — the gaming profile was not reverted."
                        ),
                        "info",
                    )
                else:
                    self.app.notify(
                        i18n.tr("Game Boost deactivated. Previous values restored."),
                        "success" if not result.get("failed") else "warning",
                    )

            TaskDialog(
                self.app,
                title=i18n.tr("Deactivating Game Boost"),
                subtitle=i18n.tr(
                    "Restoring {count} backed-up values", count=len(items)
                ),
                worker=worker,
                on_done=done,
                accent=theme.Color.CYAN,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Deactivate Game Boost?"),
            message=i18n.tr(
                "The values saved when Game Boost was activated will be restored."
            ),
            confirm_text=i18n.tr("Deactivate"),
            items=[i18n.tr("RESTORE  ·  {name}", name=i18n.tr(item.title)) for item in items],
            risk="safe",
            height=460,
            on_result=confirmed,
        )

    # ------------------------------------------------------------------- processes
    def refresh_processes(self) -> None:
        for child in self.process_list.winfo_children():
            child.destroy()
        self._process_vars = {}
        self._process_rows = {}
        processes = system.top_processes(8)
        if not processes:
            ctk.CTkLabel(
                self.process_list, text=i18n.tr("No heavy background apps detected."),
                text_color=theme.Color.GREEN, font=theme.font(9),
            ).grid(row=0, column=0, sticky="w", pady=8)
            self.process_hint.configure(
                text=i18n.tr("No memory-heavy background apps found.")
            )
            self.end_processes_btn.configure(state="disabled")
            return
        self.process_hint.configure(
            text=i18n.tr(
                "Top {count} by working set  •  select to end", count=len(processes)
            )
        )
        for index, process in enumerate(processes):
            row = ctk.CTkFrame(self.process_list, fg_color="transparent")
            row.grid(row=index, column=0, sticky="ew", pady=1)
            row.grid_columnconfigure(1, weight=1)
            var = ctk.BooleanVar(value=False)
            self._process_vars[process["pid"]] = var
            self._process_rows[process["pid"]] = process
            ctk.CTkCheckBox(
                row, text="", variable=var, width=18, height=18,
                checkbox_width=16, checkbox_height=16, corner_radius=4,
                fg_color=theme.Color.RED, hover_color="#c94a57",
                border_color=theme.Color.BORDER_STRONG,
                command=self._update_process_button,
            ).grid(row=0, column=0, padx=(0, 9), pady=4)
            ctk.CTkLabel(
                row, text=process["name"], text_color=theme.Color.TEXT_SOFT,
                font=theme.font(9), anchor="w",
            ).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(
                row, text=f"{system.format_bytes(process['memory'])}  •  PID {process['pid']}",
                text_color=theme.Color.DIM, font=theme.font(8), anchor="e",
            ).grid(row=0, column=2, sticky="e", padx=(8, 2))

    def _update_process_button(self) -> None:
        selected = any(var.get() for var in self._process_vars.values())
        self.end_processes_btn.configure(state="normal" if selected else "disabled")

    def end_selected_processes(self) -> None:
        selected = [pid for pid, var in self._process_vars.items() if var.get()]
        if not selected:
            return
        processes = [self._process_rows[pid] for pid in selected if pid in self._process_rows]
        names = [f"{proc['name']} (PID {proc['pid']})" for proc in processes]

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                return
            ended = 0
            errors = 0
            for process in processes:
                if system.is_process_protected(process["name"]):
                    continue
                try:
                    proc = psutil.Process(process["pid"])
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.2)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    ended += 1
                except Exception:
                    errors += 1
            self.refresh_processes()
            message = i18n.tr("Ended {count} process(es).", count=ended)
            if errors:
                message += " " + i18n.tr("{count} could not be closed.", count=errors)
            self.app.notify(message, "success" if not errors else "warning")

        ConfirmDialog(
            self.app,
            title=i18n.tr("End selected processes?"),
            message=i18n.tr("Unsaved work in these applications may be lost."),
            confirm_text=i18n.tr("End processes"),
            items=names,
            risk="advanced",
            on_result=confirmed,
            height=390,
        )

    # ------------------------------------------------------------------ power plan
    def set_power_plan(self, guid: str, name: str) -> None:
        ok, message = system.set_power_plan(guid)
        if ok:
            self.app.notify(i18n.tr("Power plan set to {name}.", name=i18n.tr(name)), "success")
            self.refresh()
        else:
            self.app.notify(
                i18n.tr("Could not change power plan: {error}", error=message), "warning"
            )

    def on_show(self) -> None:
        # The page is prebuilt and already shows its last snapshot. Reading the
        # power plan and process list here would delay the swap by ~100 ms, so
        # let the cached frame paint first and patch it a moment later.
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
        self._refresh_job = self.after(40, self._refresh_visible)

    def _refresh_visible(self) -> None:
        self._refresh_job = None
        if not self.winfo_exists():
            return
        try:
            self.refresh()
        except Exception:
            pass
