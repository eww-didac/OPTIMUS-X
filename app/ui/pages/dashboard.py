"""Dashboard: live telemetry, one-click optimization and system status."""

from __future__ import annotations

import time
import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from ... import i18n, theme
from ...core import catalog, system
from ...core.executor import executor
from ...core.metrics import metrics
from ...core.store import store
from ...ui.cards import MetricCard, MiniCard
from ...ui.controls import GlowButton, IconButton
from ...ui.icons import draw_icon
from ...ui.widgets import PageBase

if TYPE_CHECKING:
    from ...application import OptimusXApp


class DashboardPage(PageBase):
    def __init__(self, master: tk.Misc, app: "OptimusXApp") -> None:
        super().__init__(master, app)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_row, text=i18n.tr("System Status"), text_color=theme.Color.TEXT,
            font=theme.display(25, "bold"), anchor="w",
        ).pack(side="left")
        self.gaming_label = ctk.CTkLabel(
            title_row, text=i18n.tr("(Gaming Mode: STANDBY)"), text_color=theme.Color.AMBER,
            font=theme.font(12, "bold"), anchor="w",
        )
        self.gaming_label.pack(side="left", padx=(10, 0), pady=(5, 0))
        ctk.CTkLabel(
            header, text=i18n.tr("Live telemetry, latency and two reversible optimization profiles."),
            text_color=theme.Color.MUTED, font=theme.font(10), anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, rowspan=2, sticky="e")
        self.system_chip = ctk.CTkFrame(
            right, fg_color=theme.Color.CARD_ALT, corner_radius=9,
            border_width=1, border_color=theme.Color.BORDER,
        )
        self.system_chip.pack(side="left")
        shield = tk.Canvas(self.system_chip, width=18, height=18, bg=theme.Color.CARD_ALT, highlightthickness=0)
        shield.pack(side="left", padx=(9, 4), pady=6)
        draw_icon(shield, "shield", 9, 9, 13, theme.Color.GREEN, 1.4)
        os_data = system.os_info()
        self.system_label = ctk.CTkLabel(
            self.system_chip,
            text=f"{os_data['name'].replace('Microsoft ', '')}  •  {i18n.tr(system.admin_state().upper())}",
            text_color=theme.Color.MUTED, font=theme.font(8, "bold"),
        )
        self.system_label.pack(side="left", padx=(0, 10), pady=6)
        self.refresh_btn = IconButton(
            right, text="Refresh", command=self.app.refresh_dashboard, width=76, height=30,
        )
        self.refresh_btn.pack(side="left", padx=(8, 0))

        cards = ctk.CTkFrame(self, fg_color="transparent", height=258)
        cards.grid(row=1, column=0, sticky="ew")
        for index in range(3):
            cards.grid_columnconfigure(index, weight=1, uniform="metrics")
        self.cpu_card = MetricCard(cards, "cpu", theme.Color.CYAN)
        self.cpu_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.ram_card = MetricCard(cards, "ram", theme.Color.CYAN)
        self.ram_card.grid(row=0, column=1, sticky="nsew", padx=8)
        self.gpu_card = MetricCard(cards, "gpu", theme.Color.CYAN)
        self.gpu_card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        for card in (self.cpu_card, self.ram_card, self.gpu_card):
            card.configure(height=258)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=2, column=0, sticky="nsew")
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=1)
        center.grid_rowconfigure(3, weight=1)

        actions = ctk.CTkFrame(center, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=8)
        actions.grid_columnconfigure(0, weight=1, uniform="optimize")
        actions.grid_columnconfigure(1, weight=1, uniform="optimize")
        self.optimize_btn = GlowButton(
            actions, "Normal optimization", self.app.quick_optimize,
            width=340, height=70, bg=theme.Color.CONTENT, accent=theme.Color.CYAN,
        )
        self.optimize_btn.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        self.extreme_btn = GlowButton(
            actions, "Extreme optimization", self.app.quick_optimize_extreme,
            width=340, height=70, bg=theme.Color.CONTENT, accent=theme.Color.AMBER,
        )
        self.extreme_btn.grid(row=0, column=1, sticky="ew", padx=(7, 0))

        captions = ctk.CTkFrame(center, fg_color="transparent")
        captions.grid(row=2, column=0, sticky="ew", padx=8, pady=(5, 0))
        captions.grid_columnconfigure(0, weight=1, uniform="optimize")
        captions.grid_columnconfigure(1, weight=1, uniform="optimize")
        self.normal_caption = ctk.CTkLabel(
            captions,
            text=i18n.tr("RECOMMENDED PROFILE  ·  ANALYZING…"),
            text_color=theme.Color.DIM, font=theme.font(8), anchor="center",
        )
        self.normal_caption.grid(row=0, column=0)
        self.extreme_caption = ctk.CTkLabel(
            captions,
            text=i18n.tr("ALL TWEAKS  ·  ADVANCED CHANGES  ·  RESTORE POINT"),
            text_color="#b99a59", font=theme.font(8), anchor="center",
        )
        self.extreme_caption.grid(row=0, column=1)

        status = ctk.CTkFrame(
            center, fg_color=theme.Color.CARD_ALT, corner_radius=10,
            border_width=1, border_color=theme.Color.BORDER,
        )
        status.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        status.grid_columnconfigure(4, weight=1)
        self.status_dot = tk.Canvas(status, width=18, height=18, bg=theme.Color.CARD_ALT, highlightthickness=0)
        self.status_dot.grid(row=0, column=0, padx=(10, 0), pady=9)
        self._draw_status_dot(theme.Color.DIM)
        self.status_text = ctk.CTkLabel(
            status,
            text=i18n.tr(
                "Last optimization: {value}", value=store.last_optimization_text()
            ),
            text_color=theme.Color.MUTED, font=theme.font(9), anchor="w",
        )
        self.status_text.grid(row=0, column=1, sticky="w", padx=(4, 0), pady=9)
        ctk.CTkLabel(
            status, text="|", text_color=theme.Color.BORDER_STRONG, font=theme.font(12),
        ).grid(row=0, column=2, padx=10, pady=9)
        self.gain_label = ctk.CTkLabel(
            status, text=i18n.tr("Estimated performance gain: +{gain}% FPS", gain=0),
            text_color=theme.Color.GREEN, font=theme.font(9, "bold"), anchor="w",
        )
        self.gain_label.grid(row=0, column=3, sticky="w", pady=9)
        self.activity_btn = IconButton(
            status, text="Activity log", command=lambda: self.app.show_page("Settings"),
            width=96, height=26,
        )
        self.activity_btn.grid(row=0, column=5, sticky="e", padx=8, pady=4)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        self.latency_card = MiniCard(
            bottom, "NETWORK LATENCY", "—", "Measuring 1.1.1.1…",
            accent=theme.Color.CYAN, icon="wifi", percent=0,
        )
        self.latency_card.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.score_card = MiniCard(
            bottom, "OPTIMIZATION SCORE", "0 / 100", "Analyzing tweaks…",
            accent=theme.Color.GREEN, icon="shield", percent=0,
        )
        self.score_card.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self._score_stamp = 0.0
        self._refreshing_profile = False
        self.after(300, self._tick)
        self.refresh_profile()

    # ------------------------------------------------------------------ rendering
    def _draw_status_dot(self, color: str) -> None:
        self.status_dot.delete("all")
        self.status_dot.create_oval(3, 3, 15, 15, fill=color, outline="")
        self.status_dot.create_oval(7, 7, 11, 11, fill=theme.Color.CARD_ALT, outline="")

    def _is_visible(self) -> bool:
        try:
            return bool(self.winfo_exists() and self.winfo_ismapped())
        except Exception:
            return False

    def _render_live(self) -> None:
        data = metrics.latest
        cpu = system.cpu_info()
        self.cpu_card.update_cpu(
            data.get("cpu", 0),
            data.get("cpu_freq"),
            cpu["cores"],
            cpu["threads"],
            data.get("cpu_temp"),
            cpu["name"],
        )
        self.ram_card.update_ram(
            data.get("ram_used", 0) / 1024**3,
            data.get("ram_total", 1) / 1024**3,
            data.get("ram_percent", 0),
        )
        # Never fall back to a blocking GPU probe on the UI thread.  The
        # telemetry worker owns that sampler and publishes its latest result.
        gpu = data.get("gpu") or {
            "available": False,
            "name": "GPU",
            "percent": None,
            "temp": None,
            "source": "none",
        }
        self.gpu_card.update_gpu(gpu, data.get("gpu_history", []))
        self._update_mini(data)

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        visible = self._is_visible()
        if visible:
            self._render_live()
            delay = 1150
        else:
            # A hidden page does not need to animate canvases or touch psutil;
            # keep a slow wake-up so it is current when it comes back.
            delay = 2200
        self.after(delay, self._tick)

    def _update_mini(self, data: dict) -> None:
        latency = data.get("latency")
        if latency is None:
            self.latency_card.update_values(
                value="—", detail=i18n.tr("Latency probe unavailable"), percent=0,
            )
        else:
            if latency <= 20:
                color, quality = theme.Color.GREEN, i18n.tr("Excellent route to 1.1.1.1")
            elif latency <= 45:
                color, quality = theme.Color.CYAN, i18n.tr("Good route to 1.1.1.1")
            else:
                color, quality = theme.Color.AMBER, i18n.tr("Elevated route latency")
            self.latency_card.update_values(
                value=f"{latency:.0f} ms",
                detail=quality,
                percent=max(4.0, min(100.0, 100.0 - latency * 1.6)),
            )
            self.latency_card.accent = color

        if (
            time.time() - self._score_stamp > 30
            and not self._refreshing_profile
            and self._is_visible()
        ):
            self.refresh_profile()

    def _apply_score(self, applied: int, total: int) -> None:
        score = round(35 + (applied / max(1, total)) * 65)
        if score >= 78:
            color = theme.Color.GREEN
        elif score >= 55:
            color = theme.Color.CYAN
        else:
            color = theme.Color.AMBER
        self.score_card.accent = color
        self.score_card.update_values(
            value=f"{score} / 100",
            detail=i18n.tr("{applied} of {total} tweaks active", applied=applied, total=total),
            percent=score,
        )

    # ----------------------------------------------------------------------- API
    def refresh_profile(self) -> None:
        if self._refreshing_profile:
            return
        self._refreshing_profile = True

        gaming = bool(store.get("gaming_mode", False))
        if gaming:
            self.gaming_label.configure(
                text=i18n.tr("(Gaming Mode: ACTIVATED)"), text_color=theme.Color.GREEN
            )
        else:
            self.gaming_label.configure(
                text=i18n.tr("(Gaming Mode: STANDBY)"), text_color=theme.Color.AMBER
            )
        self.status_text.configure(
            text=i18n.tr(
                "Last optimization: {value}", value=store.last_optimization_text()
            )
        )

        def collect_profile() -> tuple[int, int, int, int, int]:
            all_tweaks = catalog.tweaks()
            applied_ids = [
                tweak.id for tweak in all_tweaks if executor.is_applied(tweak)
            ]
            return (
                len(applied_ids),
                len(all_tweaks),
                catalog.estimated_gain(applied_ids),
                len(catalog.profile_tweaks("normal")),
                len(catalog.profile_tweaks("extreme")),
            )

        def update_profile(result: tuple[int, int, int, int, int]) -> None:
            self._refreshing_profile = False
            if not self.winfo_exists():
                return
            applied, total, gain, normal_count, extreme_count = result
            self.gain_label.configure(
                text=i18n.tr("Estimated performance gain: +{gain}% FPS", gain=gain)
            )
            self._draw_status_dot(theme.Color.GREEN if applied else theme.Color.DIM)
            self._apply_score(applied, total)
            self.normal_caption.configure(
                text=i18n.tr(
                    "RECOMMENDED PROFILE  ·  {normal_count} REVERSIBLE TWEAKS",
                    normal_count=normal_count,
                )
            )
            self.extreme_caption.configure(
                text=i18n.tr(
                    "ALL {extreme_count} TWEAKS  ·  ADVANCED CHANGES  ·  RESTORE POINT",
                    extreme_count=extreme_count,
                )
            )
            self._score_stamp = time.time()

        def profile_failed(error: Exception) -> None:
            self._refreshing_profile = False
            self._score_stamp = time.time()
            if self.winfo_exists():
                self.app.notify(
                    i18n.tr("Could not refresh system profile: {error}", error=error),
                    "error",
                )

        self.app.run_background(collect_profile, update_profile, profile_failed)

    def on_show(self) -> None:
        # Returning to the dashboard should paint the live values immediately
        # instead of waiting for the next scheduled telemetry tick.
        self._render_live()
        if not self._refreshing_profile and time.time() - self._score_stamp > 10:
            self.refresh_profile()

    def set_optimize_state(self, state: str, label: str | None = None, profile: str = "normal") -> None:
        button = self.extreme_btn if profile == "extreme" else self.optimize_btn
        default = i18n.tr(
            "Extreme optimization" if profile == "extreme" else "Normal optimization"
        )
        button.set_state(state, label or default)

    def select_profile_badge(self) -> None:
        self.refresh_profile()
