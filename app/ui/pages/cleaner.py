"""Deep Cleaner: AppX bloatware, system components and junk cleanup."""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Callable

import customtkinter as ctk

from ... import i18n, theme
from ...core import catalog, cleaner, system
from ...core.executor import executor
from ...core.store import store
from ...ui.controls import IconButton, PageHeader, RiskPill, SectionTitle
from ...ui.dialogs import ConfirmDialog, TaskDialog
from ...ui.icons import draw_icon
from ...ui.widgets import PageBase, SmoothScrollFrame


class ComponentCard(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        item: catalog.Tweak,
        icon: str,
        action: Callable[[catalog.Tweak], None],
        revert: Callable[[catalog.Tweak], None],
    ) -> None:
        super().__init__(
            master, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        self.item = item
        self._action = action
        self._revert = revert
        self._applied = False
        self._can_revert = item.id not in {"edge", "onedrive"}
        self.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=14, pady=(13, 0))
        head.grid_columnconfigure(1, weight=1)
        self.icon_canvas = tk.Canvas(
            head, width=28, height=28, bg=theme.Color.CARD, highlightthickness=0,
        )
        self.icon_canvas.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 8))
        draw_icon(self.icon_canvas, icon, 14, 14, 21, theme.Color.CYAN, 1.55)
        ctk.CTkLabel(
            head, text=i18n.tr(item.title), text_color=theme.Color.TEXT,
            font=theme.font(11, "bold"), anchor="w",
        ).grid(row=0, column=1, sticky="w")
        self.status = ctk.CTkLabel(
            head, text=i18n.tr("CHECKING…"), text_color=theme.Color.DIM,
            font=theme.font(8, "bold"), anchor="w",
        )
        self.status.grid(row=1, column=1, sticky="w", pady=(1, 0))
        self.status_dot = tk.Canvas(
            head, width=8, height=8, bg=theme.Color.CARD, highlightthickness=0,
        )
        self.status_dot.grid(row=0, column=2, rowspan=2, sticky="ne", padx=(6, 0))
        self.status_dot.create_oval(1, 1, 7, 7, fill=theme.Color.DIM, outline="")

        ctk.CTkLabel(
            self, text=i18n.tr(item.description), text_color=theme.Color.MUTED,
            font=theme.font(9), anchor="w", justify="left", wraplength=410,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(7, 7))
        fg, bg = theme.risk_palette(item.risk)
        RiskPill(self, theme.risk_label(item.risk), fg, bg).grid(
            row=2, column=0, sticky="w", padx=14, pady=(0, 10)
        )
        self.button = IconButton(
            self, text="Remove", command=self._clicked, width=105, height=30,
        )
        self.button.grid(row=2, column=0, sticky="e", padx=14, pady=(0, 10))

    def set_state(self, applied: bool | None, feature_state: str | None = None) -> None:
        self._applied = bool(applied)
        label = "CHECKING…"
        color = theme.Color.DIM
        action_text = "Remove"
        style = "danger" if self.item.risk == "extreme" else "accent"
        if feature_state:
            if feature_state.lower() == "disabled":
                applied = True
            elif feature_state.lower() == "enabled":
                applied = False
            self._applied = bool(applied)
        if applied:
            if self.item.id in {"copilot", "recall"}:
                label = "DISABLED"
                action_text = "Re-enable"
                style = "normal"
            elif self.item.id in {"edge", "onedrive"}:
                label = "REMOVED"
                action_text = "Removed"
                style = "disabled"
            else:
                label = "DISABLED"
                action_text = "Re-enable" if self._can_revert else "Removed"
                style = "normal" if self._can_revert else "disabled"
            color = theme.Color.GREEN
        elif applied is False:
            label = "PRESENT"
            color = theme.Color.CYAN
            if self.item.id == "edge":
                action_text = "Uninstall"
            elif self.item.id == "onedrive":
                action_text = "Uninstall"
            elif self.item.id in {"copilot", "recall", "wmp_legacy", "directplay"}:
                action_text = "Disable"
        else:
            label = "OPTIONAL"
            color = theme.Color.AMBER
            action_text = "Disable"
        self.status.configure(text=i18n.tr(label), text_color=color)
        self.status_dot.delete("all")
        self.status_dot.create_oval(1, 1, 7, 7, fill=color, outline="")
        self.button.configure(text=i18n.tr(action_text))
        if style == "disabled":
            self.button.configure(state="disabled")
        else:
            self.button.configure(state="normal")
            if style == "danger":
                self.button.configure(
                    fg_color=theme.Color.RED_DIM, hover_color="#55212b",
                    text_color="#ff9ba5", border_color="#5d2732",
                )
            elif style == "accent":
                self.button.configure(
                    fg_color=theme.Color.CYAN_FAINT, hover_color="#124254",
                    text_color=theme.Color.CYAN_BRIGHT, border_color=theme.Color.CYAN_DIM,
                )
            else:
                self.button.configure(
                    fg_color=theme.Color.CARD_SOFT, hover_color=theme.Color.CARD_HOVER,
                    text_color=theme.Color.TEXT_SOFT, border_color=theme.Color.BORDER,
                )

    def _clicked(self) -> None:
        if self._applied and self._can_revert:
            self._revert(self.item)
        elif not self._applied:
            self._action(self.item)


class DeepCleanerPage(PageBase):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._scanning = False
        self._scan_done = False
        self._scan_packages: list[dict] = []
        self._scan_error: str | None = None
        self._features: dict[str, str] = {}
        self._selected: set[str] = set()
        self._filter = ""
        self._junk_rows: list[dict] = []
        self._junk_total = 0
        self._junk_scanning = False
        self._junk_rendered = False
        self._junk_parent: tk.Misc | None = None
        self._scan_generation = 0
        self._component_cards: dict[str, ComponentCard] = {}

        header = PageHeader(
            self,
            "Deep Cleaner",
            "Remove preinstalled bloat, disable legacy components and reclaim disk space.",
            eyebrow="Bloatware control",
        )
        header.grid(row=0, column=0, sticky="ew")
        self.rescan_btn = IconButton(
            header.actions, text="Rescan system", command=self.rescan, accent=True,
            width=124, height=31,
        )
        self.rescan_btn.pack(side="right")

        self.body = SmoothScrollFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=theme.Color.BORDER_STRONG,
            scrollbar_button_hover_color=theme.Color.CYAN_DIM,
        )
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

        self._build_storage_card()
        self._build_components()
        self._build_apps_card()
        self._build_junk_card()

        self.after(150, self._poll_scan)
        self.after(150, self._poll_junk)

    # ------------------------------------------------------------------- layout
    def _build_storage_card(self) -> None:
        card = ctk.CTkFrame(
            self.body, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid(row=0, column=0, sticky="ew", pady=(2, 12))
        card.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.grid(row=0, column=0, sticky="ew", padx=18, pady=15)
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            left, text=i18n.tr("SYSTEM DRIVE"), text_color=theme.Color.DIM,
            font=theme.font(8, "bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self.disk_title = ctk.CTkLabel(
            left, text=i18n.tr("C:\\  —"), text_color=theme.Color.TEXT,
            font=theme.display(21, "bold"), anchor="w",
        )
        self.disk_title.grid(row=1, column=0, sticky="w", pady=(1, 0))
        self.disk_detail = ctk.CTkLabel(
            left, text=i18n.tr("Reading disk usage…"), text_color=theme.Color.MUTED,
            font=theme.font(10), anchor="w",
        )
        self.disk_detail.grid(row=2, column=0, sticky="w", pady=(2, 8))
        self.disk_bar = ctk.CTkProgressBar(
            left, height=7, corner_radius=4, fg_color="#172333",
            progress_color=theme.Color.CYAN,
        )
        self.disk_bar.grid(row=3, column=0, sticky="ew")
        self.disk_bar.set(0)
        self.transient_free = ctk.CTkLabel(
            left, text="", text_color=theme.Color.DIM, font=theme.font(8), anchor="w",
        )
        self.transient_free.grid(row=4, column=0, sticky="w", pady=(5, 0))

        right = ctk.CTkFrame(card, fg_color=theme.Color.CARD_ALT, corner_radius=10)
        right.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=14)
        ctk.CTkLabel(
            right, text=i18n.tr("RECLAIMABLE"), text_color=theme.Color.DIM,
            font=theme.font(8, "bold"), anchor="w",
        ).pack(anchor="w", padx=14, pady=(10, 0))
        self.junk_total_label = ctk.CTkLabel(
            right, text=i18n.tr("Scanning…"), text_color=theme.Color.CYAN,
            font=theme.display(18, "bold"), anchor="w",
        )
        self.junk_total_label.pack(anchor="w", padx=14, pady=(0, 7))
        self.clean_btn = IconButton(
            right, text="Deep clean", command=self.clean_junk, accent=True,
            width=108, height=30,
        )
        self.clean_btn.pack(anchor="w", padx=14, pady=(0, 10))

    def _build_components(self) -> None:
        section = SectionTitle(
            self.body, "SYSTEM COMPONENTS",
            "Edge, OneDrive, Copilot, Recall and legacy runtimes",
            right_text="6 COMPONENTS",
        )
        section.grid(row=1, column=0, sticky="ew", padx=2, pady=(4, 8))
        grid = ctk.CTkFrame(self.body, fg_color="transparent")
        grid.grid(row=2, column=0, sticky="ew")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        icons = {
            "copilot": "sparkle",
            "recall": "clock",
            "edge": "window",
            "onedrive": "download",
            "wmp_legacy": "play",
            "directplay": "gamepad",
        }
        for index, item in enumerate(catalog.cleaner_components()):
            card = ComponentCard(grid, item, icons.get(item.id, "gear"), self.apply_component, self.revert_component)
            card.grid(
                row=index // 2, column=index % 2, sticky="nsew",
                padx=(0, 6) if index % 2 == 0 else (6, 0),
                pady=(0, 7),
            )
            self._component_cards[item.id] = card
        self.refresh_component_states()

    def _build_apps_card(self) -> None:
        section = SectionTitle(
            self.body, "PREINSTALLED APPS",
            "Packages installed for the current Windows user",
            right_text="",
        )
        section.grid(row=3, column=0, sticky="ew", padx=2, pady=(16, 8))
        card = ctk.CTkFrame(
            self.body, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid(row=4, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(card, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        toolbar.grid_columnconfigure(1, weight=1)
        self.apps_count = ctk.CTkLabel(
            toolbar, text=i18n.tr("Scanning installed packages…"), text_color=theme.Color.MUTED,
            font=theme.font(9), anchor="w",
        )
        self.apps_count.grid(row=0, column=0, sticky="w")
        self.search_entry = ctk.CTkEntry(
            toolbar, width=180, height=28, placeholder_text=i18n.tr("Filter apps…"),
            fg_color=theme.Color.INPUT, border_color=theme.Color.BORDER,
            text_color=theme.Color.TEXT, font=theme.font(9), corner_radius=8,
        )
        self.search_entry.grid(row=0, column=1, sticky="e", padx=(8, 8))
        self.search_entry.bind("<KeyRelease>", self._on_filter)
        self.select_recommended = IconButton(
            toolbar, text="Select recommended", command=self.select_recommended_apps,
            width=140, height=28,
        )
        self.select_recommended.grid(row=0, column=2, sticky="e", padx=(0, 6))
        self.remove_apps_btn = IconButton(
            toolbar, text="Remove selected", command=self.remove_selected_apps,
            danger=True, width=132, height=28,
        )
        self.remove_apps_btn.grid(row=0, column=3, sticky="e")
        self.remove_apps_btn.configure(state="disabled")

        self.apps_status = ctk.CTkLabel(
            card,
            text=i18n.tr(
                "Scanning the installed AppX package list. This can take a few seconds…"
            ),
            text_color=theme.Color.DIM, font=theme.font(9), anchor="w",
        )
        self.apps_status.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        self.apps_list = ctk.CTkFrame(card, fg_color="transparent")
        self.apps_list.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.apps_list.grid_columnconfigure(0, weight=1)

    def _build_junk_card(self) -> None:
        section = SectionTitle(
            self.body, "DEEP CLEAN TARGETS",
            "Temporary files, shader cache, update cache and Recycle Bin",
            right_text="",
        )
        section.grid(row=5, column=0, sticky="ew", padx=2, pady=(16, 8))
        card = ctk.CTkFrame(
            self.body, fg_color=theme.Color.CARD, corner_radius=12,
            border_width=1, border_color=theme.Color.BORDER,
        )
        card.grid(row=6, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        self.junk_list = ctk.CTkFrame(card, fg_color="transparent")
        self.junk_list.grid(row=0, column=0, sticky="ew", padx=16, pady=12)
        self.junk_list.grid_columnconfigure(0, weight=1)
        self._junk_parent = card
        ctk.CTkLabel(
            self.junk_list, text=i18n.tr("Scanning cleanup targets…"),
            text_color=theme.Color.DIM, font=theme.font(9),
        ).grid(row=0, column=0, sticky="w")
        spacer = ctk.CTkFrame(self.body, fg_color="transparent", height=14)
        spacer.grid(row=7, column=0)

    # ------------------------------------------------------------------- scanning
    def _start_scan(self) -> None:
        self._scan_generation += 1
        generation = self._scan_generation
        self._scanning = True
        self._scan_done = False
        self._scan_error = None
        self._scan_packages = []
        self.apps_count.configure(
            text=i18n.tr("Scanning installed packages…"), text_color=theme.Color.MUTED
        )
        self.apps_status.configure(
            text=i18n.tr("Querying Get-AppxPackage and Windows optional features…"),
            text_color=theme.Color.DIM,
        )
        for child in self.apps_list.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.apps_list, text=i18n.tr("  Scanning…  "), text_color=theme.Color.CYAN,
            font=theme.font(9),
        ).grid(row=0, column=0, sticky="w", pady=8)

        def worker() -> None:
            packages, error = system.scan_appx(catalog.scan_names())
            rows = []
            for package in packages:
                meta = catalog.appx_metadata(package["name"])
                rows.append(
                    {
                        **package,
                        "title": meta["title"],
                        "note": meta["note"],
                        "recommended": meta["recommended"],
                    }
                )
            rows.sort(key=lambda item: (not item["recommended"], item["title"].lower()))
            features = system.feature_states()
            if generation != self._scan_generation:
                return
            self._scan_packages = rows
            self._scan_error = error
            self._features = features
            self._scan_done = True

        threading.Thread(target=worker, name="appx-scan", daemon=True).start()

    def _poll_scan(self) -> None:
        if not self.winfo_exists():
            return
        if self._scan_done and self._scanning:
            self._scanning = False
            self._render_apps()
            self.refresh_component_states()
            if self._scan_error:
                self.apps_status.configure(
                    text=i18n.tr("Scan warning: {error}", error=self._scan_error),
                    text_color=theme.Color.AMBER,
                )
                self.apps_count.configure(
                    text=i18n.tr("Package list incomplete"), text_color=theme.Color.AMBER
                )
            else:
                self.apps_status.configure(
                    text=i18n.tr(
                        "Select packages to remove. Removal applies to the current user and provisioned image."
                    ),
                    text_color=theme.Color.DIM,
                )
        self.after(200, self._poll_scan)

    def _on_filter(self, _event=None) -> None:
        self._filter = self.search_entry.get().strip().lower()
        self._render_apps()

    def _render_apps(self) -> None:
        for child in self.apps_list.winfo_children():
            child.destroy()
        packages = self._scan_packages
        if self._filter:
            packages = [
                item for item in packages
                if self._filter in item["title"].lower() or self._filter in item["name"].lower()
            ]
        if not packages:
            message = i18n.tr(
                "No curated bloatware packages found for this user."
                if not self._filter
                else "No matching packages."
            )
            ctk.CTkLabel(
                self.apps_list, text=message, text_color=theme.Color.DIM,
                font=theme.font(9), anchor="w",
            ).grid(row=0, column=0, sticky="w", pady=10)
        else:
            for index, package in enumerate(packages):
                row = ctk.CTkFrame(self.apps_list, fg_color="transparent")
                row.grid(row=index, column=0, sticky="ew", pady=1)
                row.grid_columnconfigure(1, weight=1)
                key = package["full_name"]
                var = ctk.BooleanVar(value=key in self._selected)
                checkbox = ctk.CTkCheckBox(
                    row, text="", variable=var, width=20, height=20,
                    checkbox_width=17, checkbox_height=17, corner_radius=4,
                    fg_color=theme.Color.CYAN, hover_color=theme.Color.CYAN_DIM,
                    border_color=theme.Color.BORDER_STRONG,
                    command=lambda k=key, v=var: self._toggle_app(k, v.get()),
                )
                checkbox.grid(row=0, column=0, padx=(2, 10), pady=5)
                title_row = ctk.CTkFrame(row, fg_color="transparent")
                title_row.grid(row=0, column=1, sticky="w")
                ctk.CTkLabel(
                    title_row, text=i18n.tr(package["title"]), text_color=theme.Color.TEXT_SOFT,
                    font=theme.font(9, "bold"),
                ).pack(side="left")
                if package["recommended"]:
                    RiskPill(title_row, "RECOMMENDED", theme.Color.CYAN, "#092b38").pack(
                        side="left", padx=(7, 0)
                    )
                ctk.CTkLabel(
                    row, text=package["name"], text_color=theme.Color.DIM,
                    font=theme.font(9), anchor="e",
                ).grid(row=0, column=2, sticky="e", padx=(8, 4))
        self._update_apps_toolbar(len(packages))

    def _toggle_app(self, key: str, selected: bool) -> None:
        if selected:
            self._selected.add(key)
        else:
            self._selected.discard(key)
        self._update_apps_toolbar(len(self._scan_packages))

    def _update_apps_toolbar(self, visible_count: int) -> None:
        total = len(self._scan_packages)
        selected = len(self._selected)
        if self._scanning:
            self.apps_count.configure(text=i18n.tr("Scanning installed packages…"))
            return
        total_key = "package found" if total == 1 else "packages found"
        self.apps_count.configure(
            text=i18n.tr(
                "{total} " + total_key + "  •  {selected} selected",
                total=total,
                selected=selected,
            ),
            text_color=theme.Color.MUTED,
        )
        self.remove_apps_btn.configure(state="normal" if selected else "disabled")
        self.select_recommended.configure(state="normal" if total else "disabled")

    def select_recommended_apps(self) -> None:
        self._selected = {
            item["full_name"] for item in self._scan_packages if item.get("recommended")
        }
        self._render_apps()

    # -------------------------------------------------------------------- actions
    def remove_selected_apps(self) -> None:
        if not self._selected:
            return
        if not self.app.is_admin:
            self.app.prompt_admin(
                i18n.tr("Removing AppX packages requires administrator rights.")
            )
            return
        selected = [
            item for item in self._scan_packages if item["full_name"] in self._selected
        ]
        if not selected:
            return
        titles = [item["title"] for item in selected]

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                return

            def worker(emit, cancel) -> dict:
                emit(i18n.tr("Removing {count} package(s)…", count=len(selected)))
                result = cleaner.remove_appx(selected, emit, cancel)
                return {
                    "success": result["ok"] == 1,
                    "failed": result["failed"],
                    "message": i18n.tr("Packages removed."),
                }

            def done(result: dict) -> None:
                self._selected.clear()
                self.rescan()
                self.app.refresh_dashboard()
                self.app.notify(
                    i18n.tr(
                        "Selected packages were removed."
                        if result.get("success")
                        else "Package removal reported issues."
                    ),
                    "success" if result.get("success") else "warning",
                )

            TaskDialog(
                self.app,
                title=i18n.tr("Removing preinstalled apps"),
                subtitle=i18n.tr(
                    "{count} AppX package(s) · current user + provisioned image",
                    count=len(selected),
                ),
                worker=worker,
                on_done=done,
                accent=theme.Color.RED,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Remove selected apps?"),
            message=i18n.tr(
                "These UWP packages will be uninstalled for your user and removed from the provisioned image. "
                "Microsoft Store and system-critical packages are never included."
            ),
            confirm_text=i18n.tr("Remove {count} apps", count=len(selected)),
            items=[i18n.tr(title) for title in titles],
            warnings=[
                i18n.tr(
                    "Removing Xbox components can break Game Pass sign-in and Game Bar captures."
                )
            ],
            risk="extreme",
            checkbox_text=i18n.tr("I understand this is not easily reversible"),
            checkbox_default=False,
            require_checkbox=True,
            height=500,
            on_result=confirmed,
        )

    def apply_component(self, item: catalog.Tweak) -> None:
        if item.admin and not self.app.is_admin:
            self.app.prompt_admin(
                i18n.tr("{name} requires administrator rights.", name=i18n.tr(item.title))
            )
            return

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                return

            def worker(emit, cancel) -> dict:
                result = executor.apply(item, emit=emit)
                return {"success": result.success, "failed": 0 if result.success else 1}

            def done(_result: dict) -> None:
                self.refresh_component_states()
                self._start_feature_refresh()
                self.app.refresh_dashboard()
                self.app.notify(
                    i18n.tr("{name}: action completed.", name=i18n.tr(item.title)),
                    "success",
                )

            TaskDialog(
                self.app,
                title=i18n.tr(item.title),
                subtitle=i18n.tr("Applying a system component change"),
                worker=worker,
                on_done=done,
                accent=theme.Color.RED if item.risk == "extreme" else theme.Color.CYAN,
            )

        is_destructive = item.id in {"edge", "onedrive"}
        ConfirmDialog(
            self.app,
            title=i18n.tr(item.title),
            message=i18n.tr(item.description),
            confirm_text=i18n.tr("Uninstall" if is_destructive else "Disable"),
            warnings=[i18n.tr(item.warning)] if item.warning else [],
            risk=item.risk,
            checkbox_text=(
                i18n.tr("I understand this is not easily reversible")
                if is_destructive
                else None
            ),
            checkbox_default=False,
            require_checkbox=is_destructive,
            on_result=confirmed,
        )

    def revert_component(self, item: catalog.Tweak) -> None:
        if item.admin and not self.app.is_admin:
            self.app.prompt_admin(
                i18n.tr(
                    "Restoring {name} requires administrator rights.",
                    name=i18n.tr(item.title),
                )
            )
            return

        def confirmed(accepted: bool, _checked: bool) -> None:
            if not accepted:
                return

            def worker(emit, cancel) -> dict:
                result = executor.revert(item, emit=emit)
                return {"success": result.success, "failed": 0 if result.success else 1}

            def done(_result: dict) -> None:
                self.refresh_component_states()
                self._start_feature_refresh()
                self.app.notify(
                    i18n.tr("{name}: previous state restored.", name=i18n.tr(item.title)),
                    "success",
                )

            TaskDialog(
                self.app,
                title=i18n.tr("Restore {name}", name=i18n.tr(item.title)),
                subtitle=i18n.tr("Restoring the saved backed-up state"),
                worker=worker,
                on_done=done,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Re-enable {name}?", name=i18n.tr(item.title)),
            message=i18n.tr(
                "The previous registry and service state will be restored from the local backup."
            ),
            confirm_text=i18n.tr("Re-enable"),
            risk="safe",
            on_result=confirmed,
        )

    def refresh_component_states(self) -> None:
        for item in catalog.cleaner_components():
            card = self._component_cards.get(item.id)
            if not card:
                continue
            state = executor.is_applied(item)
            feature = None
            if item.id == "directplay":
                feature = self._features.get("DirectPlay")
            elif item.id == "wmp_legacy" and self._features.get("WindowsMediaPlayer"):
                feature = self._features.get("WindowsMediaPlayer")
            card.set_state(state, feature)

    def _start_feature_refresh(self) -> None:
        def worker() -> None:
            self._features = system.feature_states()

        threading.Thread(target=worker, name="feature-scan", daemon=True).start()
        self.after(1200, self.refresh_component_states)

    # ----------------------------------------------------------------------- junk
    def _update_disk(self) -> None:
        disk = system.disk_usage()
        self.disk_title.configure(text=f"{disk['path']}  {system.format_bytes(disk['total'])}")
        self.disk_detail.configure(
            text=i18n.tr(
                "{free} free  •  {percent}% used",
                free=system.format_bytes(disk["free"]),
                percent=disk["percent"],
            )
        )
        self.disk_bar.set(disk["percent"] / 100.0)
        self.transient_free.configure(
            text=i18n.tr(
                "Used {used} of {total}",
                used=system.format_bytes(disk["used"]),
                total=system.format_bytes(disk["total"]),
            )
        )

    def _start_junk_scan(self) -> None:
        if self._junk_scanning:
            return
        self._junk_scanning = True
        self._junk_rendered = False
        self.junk_total_label.configure(text=i18n.tr("Scanning…"))
        self.clean_btn.configure(state="disabled")
        self._update_disk()

        def worker() -> None:
            rows = cleaner.scan_junk()
            total = sum(row["size"] for row in rows if row["size"] > 0)
            self._junk_rows = rows
            self._junk_total = total
            self._junk_scanning = False

        threading.Thread(target=worker, name="junk-scan", daemon=True).start()

    def _poll_junk(self) -> None:
        if not self.winfo_exists():
            return
        if not self._junk_scanning and self._junk_rows and not self._junk_rendered:
            self._junk_rendered = True
            self._render_junk()
        if (
            not self._junk_scanning
            and self.junk_total_label.cget("text") == i18n.tr("Scanning…")
        ):
            self.junk_total_label.configure(text=system.format_bytes(self._junk_total))
            self.clean_btn.configure(state="normal")
        self.after(400, self._poll_junk)

    def _render_junk(self) -> None:
        for child in self.junk_list.winfo_children():
            child.destroy()
        self.junk_total_label.configure(text=system.format_bytes(self._junk_total))
        self.clean_btn.configure(state="normal")
        for index, row in enumerate(self._junk_rows):
            target = row["target"]
            if not row["exists"]:
                continue
            item = ctk.CTkFrame(self.junk_list, fg_color="transparent")
            item.grid(row=index, column=0, sticky="ew", pady=2)
            item.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                item, text=i18n.tr(target.title), text_color=theme.Color.TEXT_SOFT,
                font=theme.font(9, "bold"), anchor="w",
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                item, text=i18n.tr(target.description), text_color=theme.Color.DIM,
                font=theme.font(9), anchor="w",
            ).grid(row=1, column=0, sticky="w")
            size_text = i18n.tr("Ready") if row["size"] < 0 else system.format_bytes(row["size"])
            ctk.CTkLabel(
                item, text=size_text, text_color=theme.Color.MUTED,
                font=theme.font(9, "bold"), anchor="e",
            ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 0))
            if target.admin:
                RiskPill(item, "ADMIN", theme.Color.AMBER, theme.Color.AMBER_DIM).grid(
                    row=0, column=2, rowspan=2, sticky="e", padx=(8, 0)
                )
        if not self.junk_list.winfo_children():
            ctk.CTkLabel(
                self.junk_list, text=i18n.tr("Nothing to clean right now."),
                text_color=theme.Color.GREEN, font=theme.font(9),
            ).grid(row=0, column=0, sticky="w")

    def clean_junk(self) -> None:
        if not self._junk_rows:
            return
        ids = [row["target"].id for row in self._junk_rows if row["exists"]]
        titles = [row["target"].title for row in self._junk_rows if row["exists"]]
        if not ids:
            self.app.notify(i18n.tr("No cleanup targets are available."), "info")
            return
        needs_admin = any(row["target"].admin for row in self._junk_rows if row["exists"])

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
                self._update_disk()
                self._junk_rows = []
                self._junk_total = 0
                self.junk_total_label.configure(text=i18n.tr("Rescanning…"))
                self._start_junk_scan()
                self.app.refresh_dashboard()
                if result.get("removed"):
                    self.app.notify(
                        i18n.tr(
                            "{size} reclaimed.",
                            size=system.format_bytes(result["removed"]),
                        ),
                        "success",
                    )

            TaskDialog(
                self.app,
                title=i18n.tr("Deep clean system files"),
                subtitle=i18n.tr(
                    "Temporary files, caches, update payloads and Recycle Bin"
                ),
                worker=worker,
                on_done=done,
                accent=theme.Color.CYAN,
            )

        ConfirmDialog(
            self.app,
            title=i18n.tr("Start deep clean?"),
            message=i18n.tr(
                "Only temporary and cache locations are touched. Windows Update downloads and the "
                "Recycle Bin are included, so review the list before continuing."
            ),
            confirm_text=i18n.tr("Clean now"),
            items=[i18n.tr(title) for title in titles],
            warnings=(
                [
                    i18n.tr(
                        "Administrator-only targets are skipped when the app is not elevated."
                    )
                ]
                if needs_admin and not self.app.is_admin
                else []
            ),
            risk="advanced",
            on_result=confirmed,
            height=470,
        )

    # ----------------------------------------------------------------------- API
    def rescan(self) -> None:
        self._selected.clear()
        self._features = {}
        self._start_scan()
        for child in self.junk_list.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.junk_list, text=i18n.tr("Scanning cleanup targets…"),
            text_color=theme.Color.DIM, font=theme.font(9),
        ).grid(row=0, column=0, sticky="w")
        self._junk_rows = []
        self._junk_total = 0
        self._junk_scanning = False
        self._start_junk_scan()

    def on_show(self) -> None:
        if not self._scan_done and not self._scanning:
            self._start_scan()
            self._start_junk_scan()
        self._update_disk()
