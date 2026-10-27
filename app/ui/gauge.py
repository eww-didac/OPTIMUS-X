"""Anti-aliased gauge sprites rendered with Pillow.

Tk's canvas arcs are drawn without anti-aliasing, which makes the dashboard
telemetry rings look chunky.  This module draws each gauge at 4x resolution,
composites it over the card colour and downsamples with Lanczos, so the ring
and its soft glow stay smooth at every size.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageTk

from .. import theme

SUPERSAMPLE = 4


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _rgba(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    red, green, blue = _rgb(color)
    return red, green, blue, max(0, min(255, alpha))


def _lighten(color: str, amount: float) -> str:
    red, green, blue = _rgb(color)
    red = round(red + (255 - red) * amount)
    green = round(green + (255 - green) * amount)
    blue = round(blue + (255 - blue) * amount)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _arc(
    draw: ImageDraw.ImageDraw,
    centre: float,
    radius: float,
    start: float,
    end: float,
    fill: tuple[int, int, int, int],
    width: float,
    scale: int,
) -> None:
    box = (
        (centre - radius) * scale,
        (centre - radius) * scale,
        (centre + radius) * scale,
        (centre + radius) * scale,
    )
    if end - start >= 359.5:
        draw.ellipse(box, outline=fill, width=max(1, round(width * scale)))
    else:
        draw.arc(box, start=start, end=end, fill=fill, width=max(1, round(width * scale)))


@lru_cache(maxsize=320)
def gauge_sprite(
    accent: str = theme.Color.CYAN,
    radius: int = 49,
    thickness: int = 9,
    step: int = 0,
    background: str = theme.Color.CARD,
) -> Any:
    """Return a cached ``PhotoImage`` for one gauge frame.

    ``step`` is the percentage in half-points (0-200), which keeps the
    animation smooth without creating a new bitmap for every float value.
    """

    percent = max(0.0, min(100.0, step / 2.0))
    scale = SUPERSAMPLE
    padding = thickness + 7
    size = (radius + padding) * 2
    big = size * scale
    centre = size / 2.0

    base = Image.new("RGBA", (big, big), _rgba(background))

    # --- ambient glow -----------------------------------------------------
    if percent >= 2.0:
        extent = 360.0 * percent / 100.0
        start = -90.0
        end = start + extent
        glow = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        _arc(glow_draw, centre, radius, start, end, _rgba(accent, 60), thickness + 11, scale)
        _arc(glow_draw, centre, radius, start, end, _rgba(accent, 95), thickness + 4, scale)
        # Blurring the halo removes the hard radial edges of wide canvas arcs
        # and gives the ring a soft light bloom instead of a filled wedge.
        blur = max(2, round(thickness * 0.7 * scale))
        glow = glow.filter(ImageFilter.GaussianBlur(blur))
        base = Image.alpha_composite(base, glow)

    # --- track and foreground ring ---------------------------------------
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    _arc(draw, centre, radius, 0, 360, _rgba("#22334c"), thickness, scale)

    if percent > 0.2:
        start = -90.0
        extent = 360.0 * percent / 100.0
        end = start + extent
        _arc(draw, centre, radius, start, end, _rgba(accent), thickness, scale)
        if percent >= 15.0:
            inner = radius - thickness / 2 - 3.5
            _arc(
                draw, centre, inner,
                start + 10.0, start + extent * 0.62,
                _rgba(_lighten(accent, 0.55), 150), 1.4, scale,
            )

    base = Image.alpha_composite(base, layer)
    small = base.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(small)


def clear_gauge_cache() -> None:
    """Release cached bitmaps (used when the Tk root is recreated)."""

    gauge_sprite.cache_clear()
