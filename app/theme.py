"""Visual language for Optimus X.

The UI is intentionally dark, with cyan instrumentation accents and a small
amount of green used only for success / protection states.
"""

from __future__ import annotations

import customtkinter as ctk

from .i18n import tr


class Color:
    # Surfaces
    BG = "#060a11"
    SHELL = "#080d16"
    SIDEBAR = "#070c15"
    TITLEBAR = "#080d16"
    CONTENT = "#080d16"
    CARD = "#0c1421"
    CARD_ALT = "#0a111c"
    CARD_SOFT = "#0e1826"
    CARD_HOVER = "#101b2b"
    INPUT = "#0a111d"

    # Borders
    BORDER = "#1a2638"
    BORDER_SOFT = "#131e2e"
    BORDER_STRONG = "#293b55"

    # Type
    TEXT = "#eaf1fa"
    TEXT_SOFT = "#bdc9da"
    MUTED = "#8493a9"
    DIM = "#56657b"

    # Accents
    CYAN = "#34c9f4"
    CYAN_BRIGHT = "#66e2ff"
    CYAN_DIM = "#1e8aa8"
    CYAN_FAINT = "#0b2d3b"
    CYAN_GLOW = "#0d3a4d"
    GREEN = "#2fe0a4"
    GREEN_BRIGHT = "#66f2c5"
    GREEN_DIM = "#0d3a31"
    AMBER = "#f1b84b"
    AMBER_DIM = "#3d2e13"
    RED = "#ff6473"
    RED_DIM = "#3e1821"
    PURPLE = "#8b5cf6"
    WHITE = "#ffffff"


RISK_COLORS = {
    "safe": (Color.GREEN, "#0b2b27"),
    "advanced": (Color.AMBER, "#32270f"),
    "extreme": (Color.RED, "#35141b"),
}

CATEGORY_LABELS = {
    "Services": "WINDOWS SERVICES",
    "Kernel & Registry": "REGISTRY & KERNEL",
    "Network & Latency": "NETWORK & LATENCY",
    "Visual & DWM": "VISUAL & DWM",
    "Privacy": "PRIVACY & TELEMETRY",
    "Components": "SYSTEM COMPONENTS",
}

CATEGORY_ORDER = [
    "Services",
    "Kernel & Registry",
    "Network & Latency",
    "Visual & DWM",
    "Privacy",
]


def font(size: int = 13, weight: str = "normal", family: str = "Segoe UI") -> ctk.CTkFont:
    return ctk.CTkFont(family=family, size=size, weight=weight)


def display(size: int, weight: str = "bold") -> ctk.CTkFont:
    return ctk.CTkFont(family="Segoe UI Variable Display", size=size, weight=weight)


def risk_palette(risk: str) -> tuple[str, str]:
    return RISK_COLORS.get(risk.lower(), (Color.MUTED, Color.CARD_SOFT))


def risk_label(risk: str) -> str:
    return tr(
        {"safe": "SAFE", "advanced": "ADVANCED", "extreme": "EXTREME"}.get(
            risk.lower(), risk.upper()
        )
    )
