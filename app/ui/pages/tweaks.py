"""Tweaks & Privacy: staged, reversible Windows optimizations."""

from __future__ import annotations

import time
import tkinter as tk
from typing import Callable

import customtkinter as ctk

from ... import i18n, theme
from ...core import catalog
from ...core.executor import executor
from ...core.store import store
from ...ui.controls import IconButton, PageHeader, RiskPill, SectionTitle, ToggleSwitch
from ...ui.flows import apply_tweak_batch, risk_for
from ...ui.widgets import PageBase, SmoothScrollFrame


class TweakRow(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        tweak: catalog.Tweak,
        applied: bool,
        on_toggle: Callable[[str, bool], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.Color.CARD,
            corner_radius=11,
            border_width=1,
            border_color=theme.Color.BORDER,
        )
        self.tweak = tweak
        self.on_toggle = on_toggle
        self._applied = bool(applied)
        self.grid_columnconfigure(0, weight=1)

        # Plain Tk containers are much cheaper to create than CTk frames with
        # rounded canvas backdrops.  They are only layout wrappers, so use the
        # card colour directly and keep the list build fast.
        left = tk.Frame(self, bg=theme.Color.CARD)
        left.grid(row=0, column=0, sticky="ew", padx=(16, 10), pady=11)
        left.grid_columnconfigure(0, weight=1)

        title_row = tk.Frame(left, bg=theme.Color.CARD)
        title_row.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_row, text=i18n.tr(tweak.title), text_color=theme.Color.TEXT,
            font=theme.font(11, "bold"), anchor="w",
        ).pack(side="left")
        fg, bg = theme.risk_palette(tweak.risk)
        RiskPill(title_row, theme.risk_label(tweak.risk), fg, bg).pack(side="left", padx=(8, 0))
        if tweak.reboot:
            RiskPill(title_row, "REBOOT", theme.Color.CYAN, "#092b38").pack(side="left", padx=(5, 0))

        ctk.CTkLabel(
            left, text=i18n.tr(tweak.description), text_color=theme.Color.MUTED,
            font=theme.font(10), anchor="w", justify="left", wraplength=700,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        if tweak.warning:
            ctk.CTkLabel(
                left, text=i18n.tr(tweak.warning), text_color="#b99a59",
                font=theme.font(9), anchor="w", justify="left", wraplength=700,
            ).grid(row=2, column=0, sticky="w", pady=(3, 0))

        right = tk.Frame(self, bg=theme.Color.CARD)
        right.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=11)
        self.state_label = ctk.CTkLabel(
            right, text=i18n.tr("APPLIED" if applied else "OFF"),
            text_color=theme.Color.GREEN if applied else theme.Color.DIM,
            font=theme.font(8, "bold"),
        )
        self.state_label.pack(anchor="e", pady=(0, 5))
        self.switch = ToggleSwitch(
            right, value=applied,
            command=lambda value: self._changed(value),
            bg=theme.Color.CARD, accent=theme.Color.CYAN,
        )
        self.switch.pack(anchor="e")

    def _changed(self, value: bool) -> None:
        if value == self._applied:
            text = "APPLIED" if value else "OFF"
            color = theme.Color.GREEN if value else theme.Color.DIM
        elif value:
            text, color = "STAGED ON", theme.Color.CYAN
        else:
            text, color = "STAGED OFF", theme.Color.AMBER
        self.state_label.configure(text=i18n.tr(text), text_color=color)
        self.configure(
            border_color=theme.Color.CYAN_DIM if value != self._applied else theme.Color.BORDER
        )
        self.on_toggle(self.tweak.id, value)

    def sync(self, applied: bool, desired: bool | None = None) -> None:
        """Refresh the persisted state without rebuilding the row.

        A background refresh must not undo a change the user has already
        staged, so ``desired`` keeps the switch where the user left it while
        ``applied`` only updates the baseline used to label the row.
        """

        self._applied = bool(applied)
        value = self._applied if desired is None else bool(desired)
        if value == self._applied:
            text = "APPLIED" if value else "OFF"
            color = theme.Color.GREEN if value else theme.Color.DIM
        elif value:
            text, color = "STAGED ON", theme.Color.CYAN
        else:
            text, color = "STAGED OFF", theme.Color.AMBER
        self.state_label.configure(text=i18n.tr(text), text_color=color)
        if self.switch.value != value:
            self.switch.set(value)
        self.configure(
            border_color=theme.Color.CYAN_DIM if value != self._applied else theme.Color.BORDER
        )


class TweaksPage(PageBase):
    def __init__(self, master: tk.Misc, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._initial: dict[str, bool] = {}
        self._desired: dict[str, bool] = {}
        self._switches: dict[str, TweakRow] = {}
        self._filter = "All"
        self._items_by_id: dict[str, catalog.Tweak] = {}
        self._state_loading = False
        self._has_loaded_state = False
        self._state_stamp = 0.0
        self._refresh_again = False
        self._refresh_reset = False
        self._render_generation = 0
        self._rendering = False
        self._loading_label: ctk.CTkLabel | None = None

        header = PageHeader(
            self,
            "Tweaks & Privacy",
            "Stage system changes, review them, then apply with a single restore point.",
            eyebrow="Windows control center",
        )
        header.grid(row=0, column=0, sticky="ew")
        self.header_widget = header

        self.segmented = ctk.CTkSegmentedButton(
            header.actions,
            values=[i18n.tr(value) for value in ("All", "Services", "Kernel", "Network", "Visual", "Privacy")],
            command=self._filter_changed,
            font=theme.font(9, "bold"),
            height=30,
            fg_color=theme.Color.CARD_ALT,
            selected_color=theme.Color.CYAN_FAINT,
            selected_hover_color="#124254",
            unselected_color=theme.Color.CARD_ALT,
            unselected_hover_color=theme.Color.CARD_HOVER,
            text_color=theme.Color.TEXT_SOFT,
        )
        self.segmented.pack(side="left")
        self.applied_badge = ctk.CTkLabel(
            header.actions, text=i18n.tr("{count} APPLIED", count=0), text_color=theme.Color.GREEN,
            font=theme.font(8, "bold"),
        )
        self.applied_badge.pack(side="left", padx=(12, 0))

        self.body = SmoothScrollFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=theme.Color.BORDER_STRONG,
            scrollbar_button_hover_color=theme.Color.CYAN_DIM,
        )
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

        self.footer = ctk.CTkFrame(
            self, fg_color=theme.Color.CARD_ALT, corner_radius=11,
            border_width=1, border_color=theme.Color.BORDER,
        )
        self.footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.footer.grid_columnconfigure(0, weight=1)
        self.pending_title = ctk.CTkLabel(
            self.footer, text=i18n.tr("All selected tweaks are up to date"),
            text_color=theme.Color.TEXT_SOFT, font=theme.font(10, "bold"), anchor="w",
        )
        self.pending_title.grid(row=0, column=0, sticky="w", padx=(14, 0), pady=(8, 0))
        self.pending_sub = ctk.CTkLabel(
            self.footer, text=i18n.tr("Toggle a row to stage a change, or run a quick profile."),
            text_color=theme.Color.DIM, font=theme.font(9), anchor="w",
        )
        self.pending_sub.grid(row=1, column=0, sticky="w", padx=(14, 0), pady=(0, 8))
        self.normal_btn = IconButton(
            self.footer, text="Recommended",
            command=lambda: self.apply_profile("normal"),
            accent=True, width=116, height=32,
        )
        self.normal_btn.grid(row=0, column=1, rowspan=2, padx=(8, 0))
        self.extreme_btn = IconButton(
            self.footer, text="Extreme · all",
            command=lambda: self.apply_profile("extreme"),
            width=110, height=32,
        )
        self.extreme_btn.configure(
            fg_color=theme.Color.AMBER_DIM,
            hover_color="#4a3714",
            text_color="#f3cc7c",
            border_color="#5b4518",
        )
        self.extreme_btn.grid(row=0, column=2, rowspan=2, padx=(6, 0))
        self.reset_btn = IconButton(
            self.footer, text="Discard", command=self.refresh_states, width=84, height=32,
        )
        self.reset_btn.grid(row=0, column=3, rowspan=2, padx=(14, 0))
        self.apply_btn = IconButton(
            self.footer, text="Apply changes", command=self.apply_changes,
            accent=True, width=132, height=32,
        )
        self.apply_btn.grid(row=0, column=4, rowspan=2, padx=(8, 14))
        self.apply_btn.configure(state="disabled")

        self.refresh_states(reset_desired=True)

    # ----------------------------------------------------------------- rendering
    def refresh_states(
        self,
        *,
        reset_desired: bool = True,
        show_loading: bool | None = None,
    ) -> None:
        """Read the persisted tweak states without blocking the UI thread.

        The first load runs behind a loading placeholder.  Later refreshes are
        silent: rows are updated in place so returning to this page never
        flashes a half-built list.
        """

        if self._state_loading:
            # Coalesce requests made while a scan is already in flight.
            self._refresh_again = True
            self._refresh_reset = self._refresh_reset or reset_desired
            return
        self._state_loading = True
        self.apply_btn.configure(state="disabled")
        if show_loading is None:
            show_loading = not self._has_loaded_state
        if show_loading:
            self._show_loading("Checking tweak states…")

        def collect_states() -> tuple[tuple[catalog.Tweak, ...], dict[str, bool]]:
            items = catalog.tweaks()
            states = {item.id: bool(executor.is_applied(item)) for item in items}
            return items, states

        def update_states(result: tuple[tuple[catalog.Tweak, ...], dict[str, bool]]) -> None:
            self._state_loading = False
            if not self.winfo_exists():
                return
            items, states = result
            self._items_by_id = {item.id: item for item in items}
            self._initial = states
            if reset_desired:
                self._desired = dict(states)
            else:
                # Keep anything the user staged while the scan was running.
                self._desired = {
                    tweak_id: self._desired.get(tweak_id, applied)
                    for tweak_id, applied in states.items()
                }
            self.applied_badge.configure(
                text=i18n.tr(
                    "{count} APPLIED",
                    count=sum(1 for value in states.values() if value),
                )
            )
            self._has_loaded_state = True
            self._state_stamp = time.monotonic()

            visible_ids = {item.id for item in self._visible_tweaks()}
            can_patch = (
                not self._rendering
                and bool(visible_ids)
                and visible_ids.issubset(self._switches.keys())
            )
            if can_patch:
                for tweak_id in visible_ids:
                    row = self._switches.get(tweak_id)
                    if row is not None and row.winfo_exists():
                        applied = states.get(tweak_id, False)
                        row.sync(applied, self._desired.get(tweak_id, applied))
                self._update_footer()
            else:
                self._render_rows()

            if self._refresh_again:
                self._refresh_again = False
                reset_again = self._refresh_reset
                self._refresh_reset = False
                self.after_idle(
                    lambda: self.refresh_states(
                        reset_desired=reset_again, show_loading=False
                    )
                )

        def states_failed(error: Exception) -> None:
            self._state_loading = False
            if not self.winfo_exists():
                return
            if self._has_loaded_state:
                # Keep the usable list on screen; only report the failure.
                self.app.notify(
                    i18n.tr("Could not refresh tweak states: {error}", error=error),
                    "error",
                )
            else:
                self._show_loading("Could not load tweak states.")
                self.app.notify(
                    i18n.tr("Could not load tweak states: {error}", error=error),
                    "error",
                )

        self.app.run_background(collect_states, update_states, states_failed)

    def _show_loading(self, message: str) -> None:
        self.body.grid_remove()
        message = i18n.tr(message)
        if self._loading_label is None or not self._loading_label.winfo_exists():
            self._loading_label = ctk.CTkLabel(
                self,
                text=message,
                text_color=theme.Color.DIM,
                font=theme.font(11),
            )
            self._loading_label.grid(row=1, column=0, sticky="nsew")
        else:
            self._loading_label.configure(text=message)

    def _filter_changed(self, value: str) -> None:
        # The segmented button shows translated labels but the page logic and
        # catalog categories remain keyed by the English values.
        for key in ("All", "Services", "Kernel", "Network", "Visual", "Privacy"):
            if value == i18n.tr(key):
                self._filter = key
                break
        else:
            self._filter = value
        if not self._state_loading and self._has_loaded_state:
            self._render_rows()
            self.body.scroll_to_top()

    def _visible_tweaks(self) -> list[catalog.Tweak]:
        mapping = {
            "Kernel": "Kernel & Registry",
            "Network": "Network & Latency",
            "Visual": "Visual & DWM",
        }
        category = mapping.get(self._filter, self._filter)
        if category == "All":
            items = list(self._items_by_id.values())
        else:
            items = [
                item for item in self._items_by_id.values()
                if item.category == category
            ]
        order = {name: index for index, name in enumerate(theme.CATEGORY_ORDER)}
        return sorted(items, key=lambda item: order.get(item.category, 99))

    def _render_rows(self) -> None:
        self._render_generation += 1
        generation = self._render_generation
        self._rendering = True
        # Build the new list out of sight.  Showing the scroll area while rows
        # are still being created is what made the page appear piece by piece.
        if self._loading_label is None or not self._loading_label.winfo_exists():
            self._show_loading("Loading tweaks…")
        else:
            self.body.grid_remove()
        for child in self.body.winfo_children():
            child.destroy()
        self._switches = {}
        visible = self._visible_tweaks()
        if not visible:
            ctk.CTkLabel(
                self.body, text=i18n.tr("No tweaks in this category."),
                text_color=theme.Color.DIM, font=theme.font(11),
            ).grid(row=0, column=0, pady=40)
            self._finish_render()
            return

        entries: list[tuple[str, catalog.Tweak | str]] = []
        current_category = None
        category_counts: dict[str, int] = {}
        for tweak in visible:
            category_counts[tweak.category] = category_counts.get(tweak.category, 0) + 1
        for tweak in visible:
            if tweak.category != current_category:
                current_category = tweak.category
                entries.append(("section", current_category))
            entries.append(("tweak", tweak))

        def render_batch(start: int = 0, row_index: int = 0) -> None:
            if generation != self._render_generation:
                return
            if not self.winfo_exists():
                self._rendering = False
                return
            end = min(start + 10, len(entries))
            for kind, value in entries[start:end]:
                if kind == "section":
                    category_name = str(value)
                    section = SectionTitle(
                        self.body,
                        theme.CATEGORY_LABELS.get(
                            category_name, category_name.upper()
                        ),
                        right_text=i18n.tr(
                            "{count} OPTIONS", count=category_counts[category_name]
                        ),
                    )
                    section.grid(
                        row=row_index, column=0, sticky="ew", padx=2,
                        pady=(16 if row_index else 2, 7),
                    )
                else:
                    tweak = value
                    if not isinstance(tweak, catalog.Tweak):
                        raise TypeError("Tweak row data is invalid")
                    row = TweakRow(
                        self.body, tweak,
                        applied=self._desired.get(tweak.id, False),
                        on_toggle=self._toggle,
                    )
                    row.grid(row=row_index, column=0, sticky="ew", pady=3)
                    self._switches[tweak.id] = row
                row_index += 1
            if end < len(entries):
                self.after(1, lambda: render_batch(end, row_index))
            else:
                spacer = tk.Frame(self.body, bg=theme.Color.CONTENT, height=12)
                spacer.grid(row=row_index, column=0)
                self._finish_render()

        render_batch()

    def _finish_render(self) -> None:
        self._rendering = False
        if self._loading_label is not None and self._loading_label.winfo_exists():
            self._loading_label.destroy()
        self._loading_label = None
        self.body.grid()
        self.body.scroll_to_top()
        try:
            # Let Tk lay the rebuilt list out before the event loop paints it,
            # so the page is presented as one complete frame.
            self.body.update_idletasks()
        except Exception:
            pass
        self._layout_revision = int(getattr(self, "_layout_revision", 0)) + 1
        if not self.winfo_ismapped():
            try:
                self.after_idle(lambda: self.app.warm_page(self))
            except Exception:
                pass

    def _toggle(self, tweak_id: str, value: bool) -> None:
        self._desired[tweak_id] = value
        self._update_footer()

    def _pending(self) -> tuple[list[catalog.Tweak], list[catalog.Tweak]]:
        apply_items: list[catalog.Tweak] = []
        revert_items: list[catalog.Tweak] = []
        for tweak in self._items_by_id.values():
            initial = self._initial.get(tweak.id, False)
            desired = self._desired.get(tweak.id, initial)
            if desired and not initial:
                apply_items.append(tweak)
            elif not desired and initial:
                revert_items.append(tweak)
        return apply_items, revert_items

    def _update_footer(self) -> None:
        apply_items, revert_items = self._pending()
        total = len(apply_items) + len(revert_items)
        if not total:
            self.pending_title.configure(
                text=i18n.tr("All selected tweaks are up to date"),
                text_color=theme.Color.TEXT_SOFT,
            )
            self.pending_sub.configure(
                text=i18n.tr("Toggle a row to stage a change, or run a quick profile."),
                text_color=theme.Color.DIM,
            )
            self.apply_btn.configure(state="disabled", text=i18n.tr("Apply changes"))
            return
        parts = []
        if apply_items:
            parts.append(i18n.tr("{count} to apply", count=len(apply_items)))
        if revert_items:
            parts.append(i18n.tr("{count} to restore", count=len(revert_items)))
        dry_run = bool(store.get("dry_run"))
        self.pending_title.configure(
            text="  •  ".join(parts),
            text_color=theme.Color.CYAN,
        )
        sub = i18n.tr(
            "Review before applying. A restore point is created when possible."
        )
        if dry_run:
            sub = i18n.tr(
                "Dry-run is enabled: commands will be logged but not executed."
            )
        self.pending_sub.configure(text=sub, text_color=theme.Color.AMBER if dry_run else theme.Color.DIM)
        self.apply_btn.configure(
            state="normal",
            text=i18n.tr(
                "Apply {count} change" if total == 1 else "Apply {count} changes",
                count=total,
            ),
        )

    # -------------------------------------------------------------------- apply
    def apply_changes(self) -> None:
        apply_items, revert_items = self._pending()
        if not apply_items and not revert_items:
            return
        reboot = any(item.reboot for item in apply_items + revert_items)
        extra: list[str] = []
        if reboot:
            extra.append(i18n.tr("One or more changes take full effect after a reboot."))
        apply_tweak_batch(
            self.app,
            apply_items,
            revert_items,
            title=i18n.tr("Apply staged changes?"),
            message=i18n.tr(
                "Optimus X will write the selected registry values and service states. "
                "Previous values are saved to a local backup and can be restored from Settings."
            ),
            confirm_text=i18n.tr("Apply now"),
            admin_message=i18n.tr(
                "Applying these tweaks requires administrator rights."
            ),
            task_title=i18n.tr("Applying system changes"),
            profile_name=i18n.tr("Staged changes"),
            extra_warnings=extra,
            risk=risk_for(apply_items + revert_items),
            on_done=lambda _result: self.refresh_states(),
        )

    def apply_profile(self, mode: str) -> None:
        """Apply the recommended or extreme preset in one confirmed batch."""

        items = catalog.profile_tweaks(mode)
        if self._has_loaded_state:
            # Use the states already scanned for this page instead of blocking
            # the click on another round of registry/service probes.
            pending = [item for item in items if not self._initial.get(item.id, False)]
        else:
            pending = [item for item in items if not executor.is_applied(item)]
        if not pending:
            self.app.notify(
                i18n.tr(
                    "The normal profile is already applied."
                    if mode == "normal"
                    else "The extreme profile is already applied."
                ),
                "success",
            )
            return

        if mode == "normal":
            title = i18n.tr("Apply the recommended profile?")
            message = i18n.tr(
                "Optimus X will enable the recommended, reversible performance profile: "
                "background services, telemetry, kernel responsiveness, input latency, "
                "network throttling and privacy. Existing values are backed up first."
            )
            confirm_text = i18n.tr("Apply recommended")
            task_title = i18n.tr("Applying recommended profile")
            profile_name = i18n.tr("Recommended profile")
            extra: list[str] = []
        else:
            title = i18n.tr("Apply the extreme profile?")
            message = i18n.tr(
                "Extreme mode enables every reversible tweak in the catalog, including "
                "advanced changes such as Windows Update manual mode, print spooler, "
                "Xbox services, visual effects and hardware GPU scheduling. Review the "
                "list before continuing."
            )
            confirm_text = i18n.tr("Apply extreme")
            task_title = i18n.tr("Applying extreme profile")
            profile_name = i18n.tr("Extreme profile")
            extra = [
                i18n.tr(
                    "Extreme mode disables automatic Windows updates and printing until reverted."
                ),
                i18n.tr(
                    "Conflicting hardware-scheduling alternatives are skipped; the modern option is used."
                ),
            ]

        apply_tweak_batch(
            self.app,
            pending,
            [],
            title=title,
            message=message,
            confirm_text=confirm_text,
            admin_message=i18n.tr(
                "The normal profile changes Windows services and system registry values."
                if mode == "normal"
                else "The extreme profile changes Windows services, registry values and system policies."
            ),
            task_title=task_title,
            profile_name=profile_name,
            extra_warnings=extra,
            risk="extreme" if mode == "extreme" else risk_for(pending),
            on_done=lambda _result: self.refresh_states(),
        )

    def on_show(self) -> None:
        if self._state_loading:
            return
        if not self._has_loaded_state:
            self.refresh_states(reset_desired=True, show_loading=True)
        elif time.monotonic() - self._state_stamp > 2.0:
            # Silent refresh: the current rows stay on screen and are patched
            # in place when the background scan returns.
            self.refresh_states(reset_desired=False, show_loading=False)
