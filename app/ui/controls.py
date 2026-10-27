"""Reusable interactive controls: glow button, toggle, pills, page headers."""

from __future__ import annotations

import math
import tkinter as tk
from typing import Callable

import customtkinter as ctk

from .. import i18n, theme
from .draw import mix, round_rect
from .icons import draw_icon


class GlowButton(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        width: int = 540,
        height: int = 74,
        bg: str = theme.Color.CONTENT,
        accent: str = theme.Color.CYAN,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            **kwargs,
        )
        self.label = i18n.tr(text)
        self.command = command
        self.accent = accent
        self.base_accent = accent
        self.state = "idle"
        self._pulse = 0.0
        self._hover = False
        self._enabled = True
        self._animating = True
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", lambda _event: self._render())
        self.after(10, self._tick)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hover = True
        self._render()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hover = False
        self._render()

    def _on_click(self, _event: tk.Event) -> None:
        if self._enabled and self.state != "running":
            self.command()

    def _tick(self) -> None:
        if not self._animating:
            return
        if not self.winfo_exists():
            return
        self._pulse = (self._pulse + 0.055) % (math.pi * 2)
        if self.winfo_viewable():
            self._render()
        self.after(65, self._tick)

    def set_state(self, state: str, label: str | None = None) -> None:
        self.state = state
        if label:
            self.label = i18n.tr(label)
        if state == "success":
            self.accent = theme.Color.GREEN
        elif state == "running":
            self.accent = mix(self.base_accent, theme.Color.WHITE, 0.28)
        else:
            self.accent = self.base_accent
        self._enabled = state != "disabled"
        self.configure(cursor="hand2" if self._enabled else "arrow")
        self._render()

    def set_label(self, label: str) -> None:
        self.label = i18n.tr(label)
        self._render()

    def _render(self) -> None:
        if not self.winfo_exists():
            return
        self.delete("all")
        w = max(self.winfo_width(), 300)
        h = max(self.winfo_height(), 64)
        pad = 10
        intensity = 0.34 + 0.22 * (0.5 + 0.5 * math.sin(self._pulse))
        if self.state == "running":
            intensity = 0.48 + 0.3 * (0.5 + 0.5 * math.sin(self._pulse * 2.1))
        if self._hover:
            intensity = min(1.0, intensity + 0.16)

        # Outer halo, built from faint nested outlines.
        for index in range(8, 0, -1):
            inset = index * 1.35
            color = mix("#071019", self.accent, intensity * (1 - index / 11))
            round_rect(
                self, pad - inset, pad - inset, w - pad + inset, h - pad + inset,
                18 + inset, fill="", outline=color, width=1.4,
            )
        # Button body
        round_rect(
            self, pad, pad, w - pad, h - pad, 17,
            fill="#06121b" if self.state != "success" else "#071812",
            outline=mix("#155067", self.accent, intensity), width=2,
        )
        round_rect(
            self, pad + 4, pad + 4, w - pad - 4, h - pad - 4, 14,
            fill="", outline=mix("#0a2734", self.accent, intensity * 0.35), width=1,
        )
        text_color = mix("#aeeaff", self.accent, 0.8) if self.state != "disabled" else theme.Color.DIM
        font = ("Segoe UI Variable Display", 15, "bold")
        self.create_text(w / 2, h / 2 - 1, text=self.label.upper(), fill=text_color, font=font)
        if self.state == "running":
            # Animated scanning underline
            line_w = (w - 180) * (0.4 + 0.35 * (0.5 + 0.5 * math.sin(self._pulse * 1.6)))
            x1 = (w - line_w) / 2
            self.create_line(x1, h - 22, x1 + line_w, h - 22, fill=mix("#0b3040", self.accent, intensity), width=2)


class ToggleSwitch(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        value: bool = False,
        command: Callable[[bool], None] | None = None,
        *,
        width: int = 54,
        height: int = 28,
        bg: str = theme.Color.CARD,
        accent: str = theme.Color.CYAN,
        **kwargs,
    ) -> None:
        super().__init__(
            master, width=width, height=height, bg=bg,
            highlightthickness=0, bd=0, cursor="hand2", **kwargs,
        )
        self._value = bool(value)
        self._display = 1.0 if value else 0.0
        self.command = command
        self.accent = accent
        self._tw = width
        self._th = height
        self.bind("<Button-1>", self._toggle)
        self._render()

    @property
    def value(self) -> bool:
        return self._value

    def set(self, value: bool, *, notify: bool = False) -> None:
        self._value = bool(value)
        self._animate()
        if notify and self.command:
            self.command(self._value)

    def _toggle(self, _event: tk.Event) -> None:
        self._value = not self._value
        self._animate()
        if self.command:
            self.command(self._value)

    def _animate(self) -> None:
        target = 1.0 if self._value else 0.0
        delta = target - self._display
        if abs(delta) < 0.04:
            self._display = target
            self._render()
            return
        self._display += delta * 0.35
        self._render()
        self.after(16, self._animate)

    def _render(self) -> None:
        self.delete("all")
        w, h = self._tw, self._th
        radius = h / 2
        track = mix("#243244", self.accent, self._display)
        round_rect(self, 1, 1, w - 1, h - 1, radius, fill=track, outline="")
        knob_r = h / 2 - 4
        x = 4 + knob_r + (w - 8 - 2 * knob_r) * self._display
        y = h / 2
        self.create_oval(x - knob_r - 1, y - knob_r - 1, x + knob_r + 1, y + knob_r + 1, fill="#041018", outline="")
        self.create_oval(x - knob_r, y - knob_r, x + knob_r, y + knob_r, fill="#eaf8ff" if self._value else "#9aabbf", outline="")


class RiskPill(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, text: str, fg: str, bg: str, **kwargs) -> None:
        super().__init__(master, fg_color=bg, corner_radius=7, height=19, **kwargs)
        self.label = ctk.CTkLabel(
            self, text=i18n.tr(text), text_color=fg,
            font=theme.font(7, "bold"), height=19,
        )
        self.label.pack(padx=7, pady=1)
        self.grid_propagate(False)


class PageHeader(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        title: str,
        subtitle: str,
        *,
        eyebrow: str | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        top = 0
        if eyebrow:
            ctk.CTkLabel(
                self, text=i18n.tr(eyebrow).upper(), text_color=theme.Color.CYAN_DIM,
                font=theme.font(9, "bold"), anchor="w",
            ).grid(row=0, column=0, sticky="w", pady=(0, 1))
            top = 1
        self.title_label = ctk.CTkLabel(
            self, text=i18n.tr(title), text_color=theme.Color.TEXT,
            font=theme.display(25, "bold"), anchor="w",
        )
        self.title_label.grid(row=top, column=0, sticky="w")
        self.subtitle_label = ctk.CTkLabel(
            self, text=i18n.tr(subtitle), text_color=theme.Color.MUTED,
            font=theme.font(10), anchor="w", justify="left",
        )
        self.subtitle_label.grid(row=top + 1, column=0, sticky="w", pady=(1, 0))
        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.grid(row=0, column=1, rowspan=top + 2, sticky="e", padx=(20, 0))

    def set_title(self, title: str, subtitle: str | None = None) -> None:
        self.title_label.configure(text=i18n.tr(title))
        if subtitle is not None:
            self.subtitle_label.configure(text=i18n.tr(subtitle))


class SectionTitle(ctk.CTkFrame):
    def __init__(
        self,
        master: tk.Misc,
        title: str,
        subtitle: str = "",
        *,
        right_text: str = "",
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left, text=i18n.tr(title), text_color=theme.Color.TEXT_SOFT,
            font=theme.font(11, "bold"), anchor="w",
        ).pack(side="left")
        if subtitle:
            ctk.CTkLabel(
                left, text=f"   {i18n.tr(subtitle)}", text_color=theme.Color.DIM,
                font=theme.font(10), anchor="w",
            ).pack(side="left", padx=(4, 0))
        self.right = ctk.CTkLabel(
            self, text=i18n.tr(right_text), text_color=theme.Color.DIM,
            font=theme.font(9, "bold"), anchor="e",
        )
        self.right.grid(row=0, column=1, sticky="e")

    def set_right(self, text: str, color: str | None = None) -> None:
        self.right.configure(text=i18n.tr(text), text_color=color or theme.Color.DIM)


class IconButton(ctk.CTkButton):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        icon: str | None = None,
        accent: bool = False,
        danger: bool = False,
        **kwargs,
    ) -> None:
        fg = theme.Color.CYAN_FAINT if accent else theme.Color.CARD_SOFT
        hover = "#124254" if accent else theme.Color.CARD_HOVER
        text_color = theme.Color.CYAN_BRIGHT if accent else theme.Color.TEXT_SOFT
        border = theme.Color.CYAN_DIM if accent else theme.Color.BORDER
        if danger:
            fg = theme.Color.RED_DIM
            hover = "#55212b"
            text_color = "#ff9ba5"
            border = "#5d2732"
        height = kwargs.pop("height", 32)
        super().__init__(
            master,
            text=i18n.tr(text),
            command=command,
            fg_color=fg,
            hover_color=hover,
            text_color=text_color,
            border_color=border,
            border_width=1,
            corner_radius=9,
            height=height,
            font=theme.font(10, "bold"),
            **kwargs,
        )
