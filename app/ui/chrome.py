"""Custom window chrome: draggable title bar and the bottom telemetry strip."""

from __future__ import annotations

import re
import time
import tkinter as tk
import tkinter.font as tkfont
from typing import Callable

import customtkinter as ctk

from .. import i18n, theme
from .icons import draw_icon
from .win32 import begin_drag, left_button_down, work_area


class TitleBar(tk.Canvas):
    """Borderless title bar with brand, breadcrumb and window controls."""

    HEIGHT = 46
    BTN = 44

    def __init__(self, master: tk.Misc, *, on_close: Callable[[], None]) -> None:
        super().__init__(
            master,
            height=self.HEIGHT,
            bg=theme.Color.TITLEBAR,
            highlightthickness=0,
            bd=0,
        )
        self.window = master.winfo_toplevel()
        self.on_close = on_close
        self._page = "Dashboard"
        self._hover: str | None = None
        self._buttons: list[tuple[str, float, float]] = []
        self._last_press = 0.0
        self._dragging = False
        self._native_drag = False
        self._drag_dx = 0
        self._drag_dy = 0
        self._press_x = 0
        self._press_y = 0
        self._maximized = False
        self._restore_geometry = ""
        self._brand_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self._page_font = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.bind("<Configure>", lambda _event: self._render())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ----------------------------------------------------------------- painting
    def set_page(self, name: str) -> None:
        self._page = name
        self._render()

    def _render(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 600)
        height = self.HEIGHT
        self.create_rectangle(0, 0, width, height, fill=theme.Color.TITLEBAR, outline="")
        self.create_line(0, 1, width, 1, fill="#0c1521")
        self.create_line(0, height - 1, width, height - 1, fill=theme.Color.BORDER_SOFT)

        draw_icon(self, "shield", 23, height / 2, 16, theme.Color.CYAN, 1.4)
        self.create_text(
            38, height / 2 - 0.5, text="OPTIMUS X", anchor="w",
            fill=theme.Color.TEXT_SOFT, font=self._brand_font,
        )
        separator = 38 + self._brand_font.measure("OPTIMUS X") + 11
        self.create_line(separator, height / 2 - 7, separator, height / 2 + 7, fill=theme.Color.BORDER_STRONG)
        self.create_text(
            separator + 11, height / 2, text=i18n.tr(self._page).upper(), anchor="w",
            fill=theme.Color.CYAN_DIM, font=self._page_font,
        )

        self._buttons = []
        controls_x = width - self.BTN * 3
        for index, name in enumerate(("minimize", "maximize", "close")):
            x1 = controls_x + index * self.BTN
            x2 = x1 + self.BTN
            hovered = self._hover == name
            if hovered:
                fill = theme.Color.RED_DIM if name == "close" else theme.Color.CARD_HOVER
                self.create_rectangle(x1 + 6, height / 2 - 12, x2 - 6, height / 2 + 12, fill=fill, outline="")
            if name == "close":
                color = theme.Color.RED if hovered else theme.Color.MUTED
            else:
                color = theme.Color.TEXT if hovered else theme.Color.MUTED
            icon = name
            if name == "maximize" and self._maximized:
                icon = "restore"
            draw_icon(self, icon, (x1 + x2) / 2, height / 2, 12.5, color, 1.45)
            self._buttons.append((name, x1, x2))

        chip_right = controls_x - 16
        self.create_oval(
            chip_right - 58, height / 2 - 2.5, chip_right - 53, height / 2 + 2.5,
            fill=theme.Color.GREEN, outline="",
        )
        self.create_text(
            chip_right - 47, height / 2, text=i18n.tr("LOCAL"), anchor="w",
            fill=theme.Color.DIM, font=("Segoe UI", 7, "bold"),
        )

    # -------------------------------------------------------------------- events
    def _button_at(self, x: float, y: float) -> str | None:
        if not (0 <= y <= self.HEIGHT):
            return None
        for name, x1, x2 in self._buttons:
            if x1 <= x <= x2:
                return name
        return None

    def _on_motion(self, event: tk.Event) -> None:
        name = self._button_at(event.x, event.y)
        if name != self._hover:
            self._hover = name
            self.configure(cursor="hand2" if name else "")
            self._render()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._hover is not None:
            self._hover = None
            self.configure(cursor="")
            self._render()

    def _on_click(self, event: tk.Event) -> None:
        name = self._button_at(event.x, event.y)
        if name:
            self._last_press = 0.0
            self._press(name)
            return
        now = time.monotonic()
        if now - self._last_press < 0.38:
            self._last_press = 0.0
            self._toggle_maximize()
            return
        self._last_press = now
        self._start_drag(event)

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_dx = event.x_root - self.window.winfo_x()
        self._drag_dy = event.y_root - self.window.winfo_y()
        self._press_x = event.x_root
        self._press_y = event.y_root
        self._dragging = True
        self._native_drag = False

    def _apply_restore_geometry(self, *, under_pointer: tk.Event | None = None, ratio: float = 0.5) -> None:
        saved = self._restore_geometry or ""
        match = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", saved.strip())
        if match:
            width, height = int(match.group(1)), int(match.group(2))
            x, y = int(match.group(3)), int(match.group(4))
            if under_pointer is not None:
                x = int(under_pointer.x_root - width * ratio)
                y = max(0, int(under_pointer.y_root - under_pointer.y))
            try:
                self.window.geometry(f"{width}x{height}+{x}+{y}")
            except Exception:
                pass
        else:
            try:
                self.window.state("normal")
            except Exception:
                pass

    def _on_drag(self, event: tk.Event) -> None:
        if not self._dragging or self._native_drag:
            return
        # Wait for a real movement before handing the drag to Windows so a
        # plain click or double-click never enters the native move loop.
        if abs(event.x_root - self._press_x) + abs(event.y_root - self._press_y) < 3:
            return
        if self._maximized:
            ratio = event.x / max(1, self.winfo_width())
            self._maximized = False
            self._apply_restore_geometry(under_pointer=event, ratio=ratio)
        self._native_drag = True
        if begin_drag(self.window):
            self._watch_native_drag()
            return
        self._native_drag = False
        # Non-Windows fallback: move the window ourselves.
        x = event.x_root - self._drag_dx
        y = event.y_root - self._drag_dy
        self.window.geometry(f"+{x}+{y}")

    def _watch_native_drag(self) -> None:
        # The native move loop owns the mouse while it runs.  Poll the physical
        # button state so the drag flag clears even if Tk never receives the
        # release event.
        if not self._dragging or not self._native_drag:
            return
        if not left_button_down():
            self._on_release(None)
            return
        self.after(80, self._watch_native_drag)

    def _on_release(self, _event: tk.Event | None) -> None:
        self._dragging = False
        self._native_drag = False

    def _press(self, name: str) -> None:
        if name == "minimize":
            try:
                self.window.iconify()
            except Exception:
                pass
        elif name == "close":
            self.on_close()
        else:
            self._toggle_maximize()
        self.after(140, self._render)

    def _toggle_maximize(self) -> None:
        try:
            if self._maximized:
                self._maximized = False
                self._apply_restore_geometry()
            else:
                current = self.window.geometry()
                # Reuse the previous normal geometry when the only difference is
                # DPI rounding; otherwise repeated maximize/restore cycles creep.
                if not self._same_geometry(current, self._restore_geometry):
                    self._restore_geometry = current
                area = work_area(self.window)
                if area:
                    width, height, x, y = area
                    self.window.geometry(f"{width}x{height}+{x}+{y}")
                    self._maximized = True
                else:
                    self.window.state("zoomed")
                    self._maximized = True
        except Exception:
            pass
        self.after(140, self._render)
        self.after(360, self._render)

    @staticmethod
    def _same_geometry(first: str, second: str, tolerance: int = 3) -> bool:
        if not second:
            return False
        pattern = r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$"
        left = re.match(pattern, (first or "").strip())
        right = re.match(pattern, (second or "").strip())
        if not left or not right:
            return False
        return all(
            abs(int(left.group(index)) - int(right.group(index))) <= tolerance
            for index in range(1, 5)
        )

    @property
    def maximized(self) -> bool:
        return self._maximized

    @property
    def restore_geometry(self) -> str:
        return self._restore_geometry


class StatusBar(ctk.CTkFrame):
    """Thin bottom strip with live telemetry and session identity."""

    HEIGHT = 28

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(
            master,
            fg_color=theme.Color.SHELL,
            corner_radius=0,
            height=self.HEIGHT,
        )
        self.grid_propagate(False)
        top = ctk.CTkFrame(self, fg_color=theme.Color.BORDER_SOFT, height=1, corner_radius=0)
        top.place(relx=0, rely=0, relwidth=1)

        self.dot = tk.Canvas(
            self, width=10, height=10, bg=theme.Color.SHELL,
            highlightthickness=0, bd=0,
        )
        self.dot.place(x=18, rely=0.5, anchor="w")
        self._dot = self.dot.create_oval(1, 1, 9, 9, fill=theme.Color.GREEN, outline="")

        self.left = ctk.CTkLabel(
            self, text="", text_color=theme.Color.MUTED,
            font=theme.font(8, "bold"), height=self.HEIGHT,
        )
        self.left.place(x=34, rely=0.5, anchor="w")

        self.middle = ctk.CTkLabel(
            self, text="", text_color=theme.Color.DIM,
            font=theme.font(8), height=self.HEIGHT,
        )
        self.middle.place(relx=0.5, rely=0.5, anchor="center")

        self.right = ctk.CTkLabel(
            self, text=i18n.tr("OPTIMUS X  •  v2.0  •  LOCAL ONLY"),
            text_color=theme.Color.DIM, font=theme.font(8), height=self.HEIGHT,
        )
        self.right.place(relx=1.0, x=-18, rely=0.5, anchor="e")
        self._last_data: dict = {}
        self._last_admin = False

    def refresh_language(self) -> None:
        """Repaint the localized status labels after a language switch."""

        self.right.configure(text=i18n.tr("OPTIMUS X  •  v2.0  •  LOCAL ONLY"))
        if self._last_data:
            self.update_state(self._last_data, self._last_admin)

    def update_state(self, data: dict, admin: bool) -> None:
        self._last_data = dict(data or {})
        self._last_admin = bool(admin)
        self.dot.itemconfigure(
            self._dot, fill=theme.Color.GREEN if admin else theme.Color.AMBER
        )
        self.left.configure(
            text=(
                i18n.tr("ADMINISTRATOR" if admin else "STANDARD USER")
                + "     ·     "
                + i18n.tr("SYSTEM READY")
            )
        )
        cpu = float(data.get("cpu") or 0)
        ram = float(data.get("ram_percent") or 0)
        gpu = data.get("gpu") or {}
        gpu_percent = gpu.get("percent")
        latency = data.get("latency")
        parts = [
            f"CPU {cpu:.0f}%",
            f"RAM {ram:.0f}%",
            f"GPU {gpu_percent:.0f}%" if gpu_percent is not None else "GPU —",
            (
                f"{i18n.tr('LATENCY')} {latency:.0f} ms"
                if latency
                else f"{i18n.tr('LATENCY')} —"
            ),
        ]
        self.middle.configure(text="     ·     ".join(parts))
