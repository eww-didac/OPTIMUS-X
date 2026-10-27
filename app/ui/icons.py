"""Small line icons drawn directly on a Tk canvas.

Keeping the icons vector-drawn (instead of emoji or bitmaps) means they stay
crisp at every DPI and can be recolored instantly for hover/active states.
"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Iterable

Line = tuple[float, float, float, float]


def _tags(tags: Iterable[str] | None) -> tuple[str, ...]:
    return tuple(tags or ())


def draw_icon(
    canvas: tk.Canvas,
    name: str,
    cx: float,
    cy: float,
    size: float = 20,
    color: str = "#ffffff",
    width: float = 1.7,
    tags: Iterable[str] | None = None,
) -> None:
    """Draw a 24x24 line icon centered at cx/cy."""

    s = size / 24.0
    t = _tags(tags)

    def x(v: float) -> float:
        return cx + (v - 12.0) * s

    def y(v: float) -> float:
        return cy + (v - 12.0) * s

    def line(x1: float, y1: float, x2: float, y2: float, w: float = width) -> None:
        canvas.create_line(
            x(x1), y(y1), x(x2), y(y2),
            fill=color, width=max(1, w), capstyle=tk.ROUND, joinstyle=tk.ROUND,
            tags=t,
        )

    def poly(points: list[tuple[float, float]], closed: bool = True, fill: str = "") -> None:
        coords: list[float] = []
        for px, py in points:
            coords.extend((x(px), y(py)))
        if closed:
            canvas.create_polygon(
                coords, fill=fill, outline=color, width=max(1, width),
                joinstyle=tk.ROUND, smooth=False, tags=t,
            )
        else:
            canvas.create_line(
                coords, fill=color, width=max(1, width),
                capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=t,
            )

    def circle(px: float, py: float, r: float, fill: str = "") -> None:
        canvas.create_oval(
            x(px - r), y(py - r), x(px + r), y(py + r),
            outline=color, width=max(1, width), fill=fill, tags=t,
        )

    def arc(px: float, py: float, r: float, start: float, extent: float, w: float = width) -> None:
        canvas.create_arc(
            x(px - r), y(py - r), x(px + r), y(py + r),
            start=start, extent=extent, style=tk.ARC,
            outline=color, width=max(1, w), tags=t,
        )

    def dot(px: float, py: float, r: float = 1.5, fill: str | None = None) -> None:
        canvas.create_oval(
            x(px - r), y(py - r), x(px + r), y(py + r),
            outline="", fill=fill or color, tags=t,
        )

    if name == "home":
        poly([(3.5, 11), (12, 3.5), (20.5, 11)], closed=False)
        poly([(5.5, 9.5), (5.5, 20.5), (9.5, 20.5), (9.5, 15), (14.5, 15), (14.5, 20.5), (18.5, 20.5), (18.5, 9.5)], closed=False)
        line(9.5, 15, 14.5, 15)
        line(9.5, 15, 9.5, 20.5)
        line(14.5, 15, 14.5, 20.5)

    elif name == "bolt":
        poly([(13.2, 2.5), (4.5, 14), (11.2, 14), (9.6, 21.5), (19.5, 9.2), (12.8, 9.2)])

    elif name == "broom":
        line(4.2, 20.2, 13.2, 10.2)
        poly([(12.2, 9.4), (16.4, 5.2), (21.2, 10), (17.0, 14.2)])
        line(17.2, 7.2, 19.2, 9.2)
        line(3.4, 18.4, 5.8, 20.8)
        line(19.4, 3.2, 21.2, 2)
        line(21.2, 2, 21.2, 4)
        dot(5.1, 5.2, 0.9)
        dot(8.2, 2.9, 0.7)

    elif name == "gamepad":
        poly([
            (5.0, 9.2), (8.0, 7.8), (16.0, 7.8), (19.0, 9.2),
            (21.0, 13.8), (20.4, 18.2), (18.0, 20.2), (15.6, 18.5),
            (13.8, 16.2), (10.2, 16.2), (8.4, 18.5), (6.0, 20.2),
            (3.6, 18.2), (3.0, 13.8),
        ])
        line(7.0, 12.3, 10.0, 12.3)
        line(8.5, 10.8, 8.5, 13.8)
        dot(15.3, 11.2, 1.15)
        dot(17.7, 13.0, 1.15)

    elif name == "toolbox":
        line(3.2, 9.5, 20.8, 9.5)
        poly([(3.4, 9.2), (3.4, 20.2), (20.6, 20.2), (20.6, 9.2)], closed=False)
        poly([(8.0, 9.0), (8.0, 5.4), (16.0, 5.4), (16.0, 9.0)], closed=False)
        line(3.5, 14.0, 20.5, 14.0)
        poly([(10.6, 12.2), (13.4, 12.2), (13.4, 15.8), (10.6, 15.8)], closed=False)

    elif name == "gear":
        circle(12, 12, 3.4)
        for angle in range(0, 360, 45):
            radians = math.radians(angle)
            line(
                12 + 5.4 * math.cos(radians), 12 + 5.4 * math.sin(radians),
                12 + 7.4 * math.cos(radians), 12 + 7.4 * math.sin(radians),
                max(1, width * 1.1),
            )
        circle(12, 12, 7.4)

    elif name == "shield":
        poly([(12, 2.8), (20, 5.5), (19.2, 13.3), (12, 21.2), (4.8, 13.3), (4.0, 5.5)])
        poly([(8.3, 11.8), (11.0, 14.4), (15.9, 8.8)], closed=False)

    elif name == "search":
        circle(10.4, 10.4, 5.4)
        line(14.5, 14.5, 20.5, 20.5)

    elif name == "close":
        line(5.5, 5.5, 18.5, 18.5)
        line(18.5, 5.5, 5.5, 18.5)

    elif name == "minimize":
        line(5.5, 12, 18.5, 12)

    elif name == "maximize":
        poly([(5.5, 5.5), (18.5, 5.5), (18.5, 18.5), (5.5, 18.5)], closed=True, fill="")

    elif name == "restore":
        poly([(8, 5.5), (18.5, 5.5), (18.5, 16)], closed=False)
        poly([(5.5, 8), (15.5, 8), (15.5, 18.5), (5.5, 18.5)], closed=False)

    elif name == "refresh":
        arc(12, 12, 7.6, 35, 285)
        poly([(17.9, 3.9), (19.2, 8.3), (14.8, 9.4)], closed=False)

    elif name == "trash":
        line(4.5, 6.5, 19.5, 6.5)
        poly([(6.5, 6.5), (7.4, 21), (16.6, 21), (17.5, 6.5)], closed=False)
        line(9.4, 4.2, 14.6, 4.2)
        line(9.7, 10.3, 9.7, 17.4)
        line(14.3, 10.3, 14.3, 17.4)

    elif name == "disk":
        poly([(4.0, 18.4), (4.0, 6.2), (7.0, 3.8), (17.0, 3.8), (20.0, 6.2), (20.0, 18.4)], closed=False)
        line(6.2, 6.8, 17.8, 6.8)
        circle(12, 13.4, 3.0)
        dot(16.4, 20.0, 1.0)

    elif name == "cpu":
        poly([(6, 6), (18, 6), (18, 18), (6, 18)], closed=True, fill="")
        poly([(9, 9), (15, 9), (15, 15), (9, 15)], closed=True, fill="")
        for v in (8.5, 12, 15.5):
            line(v, 2.8, v, 5.5)
            line(v, 18.5, v, 21.2)
            line(2.8, v, 5.5, v)
            line(18.5, v, 21.2, v)

    elif name == "ram":
        poly([(3, 7.5), (21, 7.5), (21, 16.5), (3, 16.5)], closed=True, fill="")
        for v in (6.2, 9.3, 12.4, 15.5, 18.6):
            line(v, 16.5, v, 19.5)
        line(6.3, 10.5, 9.5, 10.5)
        line(11.3, 10.5, 14.5, 10.5)
        line(16.3, 10.5, 18.8, 10.5)

    elif name == "gpu":
        poly([(2.8, 7.5), (21.2, 7.5), (21.2, 17.5), (2.8, 17.5)], closed=True, fill="")
        circle(9.2, 12.5, 3.1)
        dot(9.2, 12.5, 0.9)
        line(15.0, 10.3, 18.7, 10.3)
        line(15.0, 13.0, 18.7, 13.0)
        line(15.0, 15.7, 18.7, 15.7)
        line(4.2, 19.4, 4.2, 21.0)
        line(19.8, 19.4, 19.8, 21.0)

    elif name == "network":
        dot(5, 19, 1.6)
        dot(19, 19, 1.6)
        dot(12, 5, 1.6)
        line(5, 19, 12, 7)
        line(19, 19, 12, 7)
        line(5, 19, 19, 19)

    elif name == "wifi":
        arc(12, 20.5, 3.6, 45, 90)
        arc(12, 20.5, 7.2, 45, 90)
        arc(12, 20.5, 10.8, 45, 90)
        dot(12, 20.5, 1.35)

    elif name == "clock":
        circle(12, 12, 8.2)
        line(12, 7.2, 12, 12)
        line(12, 12, 15.6, 14.0)

    elif name == "power":
        arc(12, 12, 7.8, -55, 290)
        line(12, 3.5, 12, 10.5)

    elif name == "check":
        poly([(4.5, 12.2), (9.8, 17.4), (19.5, 6.8)], closed=False)

    elif name == "alert":
        poly([(12, 3.5), (21, 20), (3, 20)])
        line(12, 8.5, 12, 14.2)
        dot(12, 17.0, 1.1)

    elif name == "external":
        poly([(13, 4), (20, 4), (20, 11)], closed=False)
        line(20, 4, 11.5, 12.5)
        poly([(9, 6), (4, 6), (4, 20), (18, 20), (18, 15)], closed=False)

    elif name == "sparkle":
        poly([(12, 2.5), (13.6, 9.3), (20.5, 12), (13.6, 14.7), (12, 21.5), (10.4, 14.7), (3.5, 12), (10.4, 9.3)])
        dot(19.5, 4.2, 1.0)

    elif name == "download":
        line(12, 3.5, 12, 15)
        poly([(7.4, 10.5), (12, 15), (16.6, 10.5)], closed=False)
        poly([(4.5, 17), (4.5, 20.5), (19.5, 20.5), (19.5, 17)], closed=False)

    elif name == "arrow_right":
        line(4, 12, 19, 12)
        poly([(13.5, 6.5), (19, 12), (13.5, 17.5)], closed=False)

    elif name == "play":
        poly([(8, 5.5), (19, 12), (8, 18.5)], closed=True, fill=color)

    elif name == "window":
        poly([(3.5, 5), (20.5, 5), (20.5, 19), (3.5, 19)], closed=True, fill="")
        line(3.5, 8.8, 20.5, 8.8)
        line(12, 8.8, 12, 19)

    elif name == "lock":
        circle(12, 10, 4)
        poly([(7.5, 10), (7.5, 18), (16.5, 18), (16.5, 10)], closed=False)
        dot(12, 13.6, 1.0)

    elif name == "info":
        circle(12, 12, 8.4)
        dot(12, 8, 1.0)
        line(12, 11, 12, 16.4)

    else:
        circle(12, 12, 7.5)
