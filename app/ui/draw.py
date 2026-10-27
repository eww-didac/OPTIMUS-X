"""Small drawing primitives shared by the canvas widgets."""

from __future__ import annotations

import tkinter as tk
from typing import Iterable


def round_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    *,
    fill: str = "",
    outline: str = "",
    width: float = 1,
    tags: Iterable[str] | None = None,
    **kwargs,
) -> int:
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=32,
        fill=fill,
        outline=outline,
        width=width,
        tags=tuple(tags or ()),
        **kwargs,
    )


def mix(color_a: str, color_b: str, amount: float) -> str:
    amount = max(0.0, min(1.0, amount))
    a = color_a.lstrip("#")
    b = color_b.lstrip("#")
    if len(a) != 6 or len(b) != 6:
        return color_b
    result = []
    for index in (0, 2, 4):
        av = int(a[index:index + 2], 16)
        bv = int(b[index:index + 2], 16)
        result.append(round(av + (bv - av) * amount))
    return "#{:02x}{:02x}{:02x}".format(*result)


def fit_text(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"
