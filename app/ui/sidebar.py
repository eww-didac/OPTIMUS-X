"""Custom-drawn navigation rail with a subtle neon glass backdrop."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Callable

from PIL import Image, ImageDraw, ImageFilter, ImageTk

from .. import i18n, theme
from .icons import draw_icon


NAV_ITEMS = [
    ("Dashboard", "home"),
    ("Tweaks & Privacy", "bolt"),
    ("Deep Cleaner", "broom"),
    ("Game Boost", "gamepad"),
    ("Toolbox", "toolbox"),
]


class Sidebar(tk.Canvas):
    WIDTH = 238

    def __init__(
        self,
        master: tk.Misc,
        on_select: Callable[[str], None],
        on_prefetch: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=self.WIDTH,
            bg=theme.Color.SIDEBAR,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.on_select = on_select
        self.on_prefetch = on_prefetch
        self.active = "Dashboard"
        self._hover: str | None = None
        self._bg_image: ImageTk.PhotoImage | None = None
        self._bg_size = (0, 0)
        self._admin = False
        self._dry_run = False
        self._items: list[tuple[str, int, int]] = []
        self._fonts = {
            "logo": ("Segoe UI Variable Display", 22, "bold"),
            "label": ("Segoe UI", 8, "bold"),
            "nav": ("Segoe UI", 12),
            "nav_active": ("Segoe UI", 12, "bold"),
            "tiny": ("Segoe UI", 8),
        }
        self._logo_measure = tkfont.Font(family="Segoe UI Variable Display", size=22, weight="bold")
        self.bind("<Configure>", self._on_configure)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    # ------------------------------------------------------------------ painting
    def _on_configure(self, event: tk.Event) -> None:
        width = max(1, event.width)
        height = max(1, event.height)
        if (width, height) == self._bg_size:
            return
        self._bg_size = (width, height)
        self._render_background(width, height)
        self.after_idle(self._draw)

    def _render_background(self, width: int, height: int) -> None:
        base = Image.new("RGB", (width, height), theme.Color.SIDEBAR)
        draw = ImageDraw.Draw(base)
        for y in range(height):
            factor = y / max(1, height)
            # gentle vertical lift from near-black to navy
            r = int(7 + 2 * (1 - factor))
            g = int(12 + 4 * (1 - factor))
            b = int(21 + 8 * (1 - factor))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gdraw.ellipse(
            (-width * 0.55, height * 0.03, width * 0.85, height * 0.36),
            fill=(18, 126, 166, 52),
        )
        gdraw.ellipse(
            (-width * 0.55, height * 0.70, width * 0.75, height * 1.04),
            fill=(102, 59, 190, 38),
        )
        gdraw.ellipse(
            (width * 0.55, height * 0.10, width * 1.15, height * 0.24),
            fill=(25, 226, 196, 18),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(42))
        base = Image.alpha_composite(base.convert("RGBA"), glow)
        draw = ImageDraw.Draw(base)
        draw.line([(width - 1, 0), (width - 1, height)], fill=(24, 37, 55, 255))
        self._bg_image = ImageTk.PhotoImage(base)
        self.delete("bg")
        self.create_image(0, 0, image=self._bg_image, anchor="nw", tags="bg")
        self.tag_lower("bg")

    def _draw(self) -> None:
        self.delete("ui")
        w = max(self.winfo_width(), self.WIDTH)
        h = max(self.winfo_height(), 600)

        # Brand
        self.create_text(
            24, 38, text="OPTIMUS", anchor="w",
            fill=theme.Color.TEXT, font=self._fonts["logo"], tags="ui",
        )
        self.create_text(
            24, 64, text=i18n.tr("S Y S T E M   O P T I M I Z E R"), anchor="w",
            fill=theme.Color.DIM, font=self._fonts["tiny"], tags="ui",
        )
        # The X is drawn separately so it can carry the brand cyan.
        self.create_text(
            24 + self._logo_measure.measure("OPTIMUS") + 3, 38, text="X", anchor="w",
            fill=theme.Color.CYAN, font=self._fonts["logo"], tags="ui",
        )
        self.create_line(24, 80, 66, 80, fill=theme.Color.CYAN_DIM, width=1, tags="ui")

        self.create_text(
            24, 112, text=i18n.tr("W O R K S P A C E"), anchor="w",
            fill=theme.Color.DIM, font=self._fonts["label"], tags="ui",
        )

        self._items = []
        y = 130
        for name, icon in NAV_ITEMS:
            self._draw_item(name, icon, y, w, h)
            self._items.append((name, y, y + 46))
            y += 52

        # Divider above settings
        self.create_line(20, h - 128, w - 20, h - 128, fill=theme.Color.BORDER_SOFT, width=1, tags="ui")
        settings_y = h - 116
        self._draw_item("Settings", "gear", settings_y, w, h)
        self._items.append(("Settings", settings_y, settings_y + 46))

        # Admin / dry-run state
        dot_color = theme.Color.AMBER if not self._admin else theme.Color.GREEN
        state_text = "STANDARD USER" if not self._admin else "ADMINISTRATOR"
        if self._dry_run:
            dot_color = theme.Color.CYAN
            state_text = "DRY RUN MODE"
        self.create_oval(25, h - 50, 31, h - 44, fill=dot_color, outline="", tags="ui")
        self.create_text(
            39, h - 47, text=i18n.tr(state_text), anchor="w",
            fill=theme.Color.MUTED, font=self._fonts["label"], tags="ui",
        )
        self.create_text(
            24, h - 27, text="OPTIMUS X  •  v2.0", anchor="w",
            fill=theme.Color.DIM, font=self._fonts["tiny"], tags="ui",
        )

    def _draw_item(self, name: str, icon: str, y: int, width: int, height: int) -> None:
        active = name == self.active
        hovered = name == self._hover
        if active:
            self.create_round_rect(
                14, y, width - 14, y + 46, 11,
                fill="#0d2733", outline="#164357", width=1, tags="ui",
            )
            self.create_line(18, y + 13, 18, y + 33, fill=theme.Color.CYAN, width=2, tags="ui")
        elif hovered:
            self.create_round_rect(
                14, y, width - 14, y + 46, 11,
                fill="#0c1826", outline="#152538", width=1, tags="ui",
            )
        color = theme.Color.CYAN if active else ("#dbe7f5" if hovered else "#a6b4c8")
        draw_icon(self, icon, 38, y + 23, 18, color, 1.55, tags=("ui", f"nav_{name}"))
        self.create_text(
            58, y + 23, text=i18n.tr(name), anchor="w",
            fill=color,
            font=self._fonts["nav_active"] if active else self._fonts["nav"],
            tags=("ui", f"nav_{name}"),
        )

    def create_round_rect(self, x1: float, y1: float, x2: float, y2: float, r: float, **kwargs):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    # -------------------------------------------------------------------- events
    def _item_at(self, y: int) -> str | None:
        for name, top, bottom in self._items:
            if top <= y <= bottom:
                return name
        return None

    def _on_motion(self, event: tk.Event) -> None:
        name = self._item_at(event.y)
        if name != self._hover:
            self._hover = name
            self.configure(cursor="hand2" if name else "")
            if name and name != self.active and self.on_prefetch is not None:
                try:
                    self.on_prefetch(name)
                except Exception:
                    pass
            self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._hover is not None:
            self._hover = None
            self.configure(cursor="")
            self._draw()

    def _on_click(self, event: tk.Event) -> None:
        name = self._item_at(event.y)
        if name:
            self.on_select(name)

    # ---------------------------------------------------------------------- API
    def refresh_language(self) -> None:
        """Repaint every canvas label after a language change."""

        self._draw()

    def set_active(self, name: str) -> None:
        if name != self.active:
            self.active = name
            self._draw()

    def set_identity(self, *, admin: bool, dry_run: bool) -> None:
        self._admin = admin
        self._dry_run = dry_run
        self._draw()
