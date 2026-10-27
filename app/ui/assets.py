"""Runtime asset generation (taskbar icon)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def ensure_icon() -> Path:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSETS_DIR / "optimusx.ico"
    if path.exists():
        return path
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, size - 8, size - 8), radius=56, fill=(7, 13, 24, 255), outline=(38, 58, 82, 255), width=4)
    # shield
    shield = [(128, 46), (196, 72), (190, 144), (128, 212), (66, 144), (60, 72)]
    draw.polygon(shield, outline=(52, 201, 244, 255), width=5)
    # X mark
    draw.line((98, 104, 158, 164), fill=(102, 226, 255, 255), width=12)
    draw.line((158, 104, 98, 164), fill=(102, 226, 255, 255), width=12)
    image.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return path
