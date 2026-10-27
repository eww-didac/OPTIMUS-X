"""Non-blocking toast notifications anchored above the status bar."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import i18n, theme
from .icons import draw_icon

_KINDS = {
    "success": (theme.Color.GREEN, "check"),
    "warning": (theme.Color.AMBER, "alert"),
    "error": (theme.Color.RED, "alert"),
    "info": (theme.Color.CYAN, "info"),
}


class ToastManager:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.host = ctk.CTkFrame(
            root, fg_color=theme.Color.CONTENT, corner_radius=0, width=1, height=1
        )
        self._cards: list[ctk.CTkFrame] = []

    def show(self, message: str, kind: str = "info") -> None:
        message = i18n.tr(message)
        accent, icon_name = _KINDS.get(kind, _KINDS["info"])
        if not self._cards:
            self.host.place(relx=1.0, rely=1.0, x=-22, y=-42, anchor="se")
        card = ctk.CTkFrame(
            self.host,
            fg_color=theme.Color.CARD_SOFT,
            corner_radius=10,
            border_width=1,
            border_color=theme.Color.BORDER_STRONG,
        )
        card.pack(side="bottom", pady=(5, 0))
        self._cards.append(card)

        accent_bar = tk.Canvas(
            card, width=3, height=36, bg=accent,
            highlightthickness=0, bd=0,
        )
        accent_bar.pack(side="left", padx=(8, 0), pady=9)

        icon = tk.Canvas(
            card, width=24, height=24, bg=theme.Color.CARD_SOFT,
            highlightthickness=0, bd=0,
        )
        draw_icon(icon, icon_name, 12, 12, 15, accent, 1.5)
        icon.pack(side="left", padx=(7, 7), pady=10)

        label = ctk.CTkLabel(
            card,
            text=message,
            text_color=theme.Color.TEXT_SOFT,
            font=theme.font(9),
            anchor="w",
            justify="left",
            wraplength=300,
        )
        label.pack(side="left", padx=(0, 16), pady=9)

        for widget in (card, accent_bar, icon, label):
            widget.bind("<Button-1>", lambda _event, target=card: self._dismiss(target))

        self.host.lift()
        while len(self._cards) > 4:
            self._dismiss(self._cards[0])
        self.root.after(4600, lambda target=card: self._dismiss(target))

    def _dismiss(self, card: ctk.CTkFrame) -> None:
        if card in self._cards:
            self._cards.remove(card)
        try:
            card.destroy()
        except Exception:
            pass
        if not self._cards:
            try:
                self.host.place_forget()
            except Exception:
                pass
