"""Dashboard metric cards and supporting mini widgets."""

from __future__ import annotations

import tkinter as tk

from .. import i18n, theme
from .draw import fit_text, round_rect
from .gauge import gauge_sprite
from .icons import draw_icon

CARD_HEIGHT = 258


def short_cpu(name: str) -> str:
    """Condense a marketing processor name to its model identifier."""

    text = name or ""
    for token in (
        "(R)", "(TM)", "CPU", "Processor", "-Core", "Edition",
        "12th Gen", "11th Gen", "13th Gen", "14th Gen",
        "Intel", "Core", "AMD", "Ryzen",
    ):
        text = text.replace(token, "")
    return " ".join(text.split())


class MetricCard(tk.Canvas):
    def __init__(self, master: tk.Misc, kind: str, accent: str = theme.Color.CYAN, **kwargs) -> None:
        super().__init__(
            master,
            height=CARD_HEIGHT,
            bg=theme.Color.CONTENT,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.kind = kind
        self.title = {"cpu": "CPU", "ram": "RAM", "gpu": "GPU"}.get(kind, kind.upper())
        self.accent = accent
        self._percent = 0.0
        self._target = 0.0
        self._side_top = "—"
        self._side_label = ""
        self._side_bottom = ""
        self._bottom_left = ""
        self._bottom_right = ""
        self._center_value = "0%"
        self._center_label = "UTILIZATION"
        self._history: list[float] = []
        self._available = True
        self._temp: float | None = None
        self._cpu_model = ""
        self._extra = ""
        self._hover = False
        self._animating = False
        self._gauge_image = None
        self.bind("<Configure>", lambda _event: self._render())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    # --------------------------------------------------------------------- API
    def update_cpu(
        self,
        percent: float,
        freq: float | None,
        cores: int,
        threads: int,
        temp: float | None,
        model: str = "",
    ) -> None:
        self._target = max(0.0, min(100.0, float(percent or 0)))
        self._center_value = f"{self._target:.0f}%"
        self._center_label = "UTILIZATION"
        self._side_top = f"{freq:.1f} GHz" if freq else "—"
        self._side_label = "CURRENT CLOCK"
        self._side_bottom = f"{cores}C / {threads}T"
        self._cpu_model = model
        self._bottom_left = "PROCESSOR LOAD"
        self._bottom_right = f"{self._target:.0f}%"
        self._temp = temp
        self._start_animation()

    def update_ram(self, used_gb: float, total_gb: float, percent: float) -> None:
        self._target = max(0.0, min(100.0, float(percent or 0)))
        self._center_value = f"{used_gb:.1f}"
        self._center_label = i18n.tr("GB USED / {total}", total=f"{total_gb:.0f}")
        self._side_top = f"{total_gb:.0f} GB"
        self._side_label = "TOTAL MEMORY"
        self._side_bottom = i18n.tr(
            "{free} GB free", free=f"{max(0.0, total_gb - used_gb):.1f}"
        )
        self._bottom_left = "PHYSICAL MEMORY"
        self._bottom_right = f"{self._target:.0f}%"
        self._start_animation()

    def update_gpu(self, stats: dict, history: list[float] | None = None) -> None:
        self._available = bool(stats.get("available"))
        percent = stats.get("percent")
        self._target = max(0.0, min(100.0, float(percent or 0)))
        self._center_value = f"{self._target:.0f}%" if self._available else "—"
        self._center_label = "UTILIZATION" if self._available else "NO TELEMETRY"
        name = str(stats.get("name") or "GPU")
        short = name.replace("NVIDIA ", "").replace("GeForce ", "").replace("AMD ", "").replace("Radeon ", "")
        self._side_top = fit_text(short, 26)
        self._side_label = "RENDER DEVICE"
        self._side_bottom = ""
        self._bottom_left = "3D ENGINE LOAD"
        self._history = list(history or [])
        self._temp = stats.get("temp")
        self._extra = stats.get("source", "")
        self._start_animation()

    # ----------------------------------------------------------------- rendering
    def _on_enter(self, _event: tk.Event) -> None:
        self._hover = True
        self._render()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hover = False
        self._render()

    def _start_animation(self) -> None:
        if not self._animating:
            self._animating = True
            self.after(16, self._animate)

    def _animate(self) -> None:
        delta = self._target - self._percent
        if abs(delta) < 0.15:
            self._percent = self._target
            self._animating = False
            self._render()
            return
        self._percent += delta * 0.24
        self._render()
        self.after(24, self._animate)

    def _render(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 250)
        height = self.winfo_height() or CARD_HEIGHT
        border = theme.Color.BORDER_STRONG if self._hover else theme.Color.BORDER
        round_rect(self, 1, 1, width - 1, height - 1, 17, fill=theme.Color.CARD, outline=border, width=1)
        # top glass highlight
        self.create_line(18, 2, width - 18, 2, fill="#1c2b3d", width=1)

        self.create_text(
            22, 22, text=self.title, anchor="nw",
            fill=theme.Color.TEXT, font=("Segoe UI Variable Display", 17, "bold"),
        )
        live_color = theme.Color.GREEN if self._available else theme.Color.DIM
        live_item = self.create_text(
            width - 22, 32, text=i18n.tr("LIVE" if self._available else "IDLE"), anchor="e",
            fill=theme.Color.DIM, font=("Segoe UI", 9, "bold"),
        )
        # Keep the status dot immediately left of the label: the Spanish
        # translations ("EN VIVO" / "INACTIVO") are wider than the English
        # ones, so a fixed offset would make the two collide.
        dot_x = width - 57.0
        dot_y = 32.0
        try:
            box = self.bbox(live_item)
            if box:
                dot_x = box[0] - 9
                dot_y = (box[1] + box[3]) / 2
        except Exception:
            pass
        self.create_oval(
            dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3,
            fill=live_color, outline="",
        )

        cx = 88
        cy = 118
        radius = 50
        thickness = 9
        self._draw_gauge(cx, cy, radius, thickness)
        # The state label sits just below the ring: keeping it inside made the
        # longer Spanish labels ("GB USADOS", "SIN TELEMETRÍA") crowd the arc.
        self._draw_center(cx, cy, cy + radius + 12)
        self._draw_side(width)

        if self.kind == "gpu":
            self._draw_sparkline(18, 201, width - 18, 225)
            if self._temp is not None:
                self.create_text(
                    width - 22, 241, text=f"{self._temp:.0f} °C", anchor="se",
                    fill=theme.Color.CYAN, font=("Segoe UI", 10, "bold"),
                )
            self.create_text(
                22, 241, text=i18n.tr(self._bottom_left), anchor="sw",
                fill=theme.Color.DIM, font=("Segoe UI", 9, "bold"),
            )
        else:
            self._draw_bar(width)
            self.create_text(
                22, 241, text=i18n.tr(self._bottom_left), anchor="sw",
                fill=theme.Color.DIM, font=("Segoe UI", 9, "bold"),
            )
            self.create_text(
                width - 22, 241, text=self._bottom_right, anchor="se",
                fill=theme.Color.TEXT_SOFT, font=("Segoe UI", 10, "bold"),
            )

    def _draw_gauge(self, cx: float, cy: float, radius: float, thickness: float) -> None:
        percent = max(0.0, min(100.0, self._percent))
        try:
            image = gauge_sprite(
                self.accent,
                round(radius),
                round(thickness),
                round(percent * 2),
                theme.Color.CARD,
            )
        except Exception:
            image = None
        if image is not None:
            self._gauge_image = image
            self.create_image(cx, cy, image=image, anchor="center")
            return

        # Pillow fallback: original Tk arcs, only used if the sprite cannot be
        # created (for example on a Tk build without RGBA image support).
        box = (cx - radius, cy - radius, cx + radius, cy + radius)
        self.create_oval(*box, outline="#22334c", width=thickness)
        if percent <= 0.2:
            return
        extent = -(percent / 100.0) * 359.9
        # Glow rings would balloon into a blob on very short arcs, so they
        # only appear once the arc has enough length to read as a gauge.
        if percent >= 8:
            self.create_arc(*box, start=90, extent=extent, style=tk.ARC, outline="#0e3a4b", width=thickness + 6)
            self.create_arc(*box, start=90, extent=extent, style=tk.ARC, outline="#116f8a", width=thickness + 3)
        self.create_arc(*box, start=90, extent=extent, style=tk.ARC, outline=self.accent, width=thickness)
        if percent >= 15:
            # inner ambient reflection
            self.create_arc(
                cx - radius + 8, cy - radius + 8, cx + radius - 8, cy + radius - 8,
                start=105, extent=max(-300, extent * 0.55), style=tk.ARC,
                outline="#5bdcff", width=1,
            )

    def _draw_center(self, cx: float, cy: float, label_y: float) -> None:
        primary_font = ("Segoe UI Variable Display", 24, "bold") if self.kind != "ram" else ("Segoe UI Variable Display", 23, "bold")
        self.create_text(cx, cy - 2, text=self._center_value, fill=theme.Color.TEXT, font=primary_font)
        self.create_text(
            cx, label_y, text=i18n.tr(self._center_label).upper(), anchor="n",
            fill=theme.Color.MUTED, font=("Segoe UI", 10, "bold"),
        )

    def _draw_side(self, width: float) -> None:
        x = 157
        self.create_text(
            x, 96, text=self._side_top, anchor="nw",
            fill=theme.Color.TEXT, font=("Segoe UI", 14, "bold"),
        )
        self.create_text(
            x, 118, text=i18n.tr(self._side_label).upper(), anchor="nw",
            fill=theme.Color.DIM, font=("Segoe UI", 9, "bold"),
        )
        if self._side_bottom:
            self.create_text(
                x, 141, text=self._side_bottom, anchor="nw",
                fill=theme.Color.MUTED, font=("Segoe UI", 10),
            )
        if self.kind == "cpu":
            if self._temp:
                self.create_text(
                    x, 168, text=f"{self._temp:.0f} °C", anchor="nw",
                    fill=theme.Color.CYAN, font=("Segoe UI", 10, "bold"),
                )
            elif self._cpu_model:
                self.create_text(
                    x, 170, text=fit_text(short_cpu(self._cpu_model), 24), anchor="nw",
                    fill=theme.Color.MUTED, font=("Segoe UI", 9),
                )
        elif self.kind == "gpu":
            self.create_text(
                x, 168, text=i18n.tr("ACTIVE" if self._available else "UNAVAILABLE"), anchor="nw",
                fill=theme.Color.GREEN if self._available else theme.Color.DIM,
                font=("Segoe UI", 10, "bold"),
            )

    def _draw_bar(self, width: float) -> None:
        x1 = 22
        x2 = width - 22
        y = 219
        round_rect(self, x1, y, x2, y + 6, 3, fill="#1a2636", outline="")
        fill_w = max(0, (x2 - x1) * (max(0.0, min(100.0, self._percent)) / 100.0))
        if fill_w > 2:
            round_rect(self, x1, y, x1 + fill_w, y + 6, 3, fill=self.accent, outline="")

    def _draw_sparkline(self, x1: float, y1: float, x2: float, y2: float) -> None:
        if not self._available:
            self.create_line(
                x1, (y1 + y2) / 2, x2, (y1 + y2) / 2,
                fill=theme.Color.BORDER, width=1, dash=(3, 4),
            )
            self.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2 - 8,
                text=i18n.tr("3D engine telemetry unavailable"),
                fill=theme.Color.DIM, font=("Segoe UI", 10),
            )
            return
        values = self._history[-36:]
        if len(values) < 2:
            values = [0.0, 0.0]
        for fraction in (0.25, 0.5, 0.75):
            gy = y2 - fraction * (y2 - y1)
            self.create_line(x1, gy, x2, gy, fill="#11202e", width=1, dash=(2, 7))
        points: list[float] = []
        count = len(values)
        for index, value in enumerate(values):
            px = x1 + (x2 - x1) * index / max(1, count - 1)
            py = y2 - (max(0.0, min(100.0, value)) / 100.0) * (y2 - y1)
            points.extend((px, py))
        # soft filled area (solid approximation of a gradient)
        area = [x1, y2, *points, x2, y2]
        self.create_polygon(area, fill="#0b2a38", outline="")
        self.create_line(*points, fill="#0f5267", width=4, smooth=True, splinesteps=18)
        self.create_line(*points, fill=self.accent, width=1.8, smooth=True, splinesteps=18)
        if points:
            self.create_oval(points[-2] - 2.2, points[-1] - 2.2, points[-2] + 2.2, points[-1] + 2.2, fill=self.accent, outline="")


class MiniCard(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        title: str,
        value: str,
        detail: str,
        *,
        accent: str = theme.Color.CYAN,
        icon: str = "network",
        percent: float | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            height=98,
            bg=theme.Color.CONTENT,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.title = title
        self.value = value
        self.detail = detail
        self.accent = accent
        self.icon = icon
        self.percent = percent
        self.bind("<Configure>", lambda _event: self._render())

    def update_values(self, *, value: str, detail: str, percent: float | None = None) -> None:
        self.value = value
        self.detail = detail
        self.percent = percent
        self._render()

    def _render(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 220)
        height = self.winfo_height() or 98
        round_rect(self, 1, 1, width - 1, height - 1, 14, fill=theme.Color.CARD_ALT, outline=theme.Color.BORDER, width=1)
        self.create_text(
            18, 16, text=i18n.tr(self.title).upper(), anchor="nw",
            fill=theme.Color.DIM, font=("Segoe UI", 9, "bold"),
        )
        self.create_text(
            18, 34, text=self.value, anchor="nw",
            fill=theme.Color.TEXT, font=("Segoe UI Variable Display", 20, "bold"),
        )
        self.create_text(
            18, 64, text=i18n.tr(self.detail), anchor="nw",
            fill=theme.Color.MUTED, font=("Segoe UI", 10),
        )
        # icon tile
        icon_size = 34
        round_rect(self, width - 54, 16, width - 20, 16 + icon_size, 10, fill="#0d202c", outline="#173343")
        draw_icon(self, self.icon, width - 37, 33, 16, self.accent, 1.5)
        if self.percent is not None:
            x1, x2, y = 18, width - 20, 86
            round_rect(self, x1, y, x2, y + 4, 2, fill="#192536", outline="")
            fill_w = (x2 - x1) * max(0.0, min(100.0, self.percent)) / 100.0
            if fill_w > 1:
                round_rect(self, x1, y, x1 + fill_w, y + 4, 2, fill=self.accent, outline="")
