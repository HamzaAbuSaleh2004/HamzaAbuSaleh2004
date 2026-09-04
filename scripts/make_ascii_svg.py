"""Turn the prepped portrait into a self-typing ASCII-art SVG.

    python scripts/make_ascii_svg.py                    # uses source-prepped.png
    python scripts/make_ascii_svg.py some-photo.png     # any image
    python scripts/make_ascii_svg.py --placeholder      # no photo, no Pillow needed

The whole grid sits inside one <clipPath> whose per-row rects scale from 0 -> 1
with a staggered delay, which reads as the art typing itself in line by line.

Output: portrait-ascii.svg (370x420 viewBox, matching info-card.svg's height).
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "portrait-ascii.svg"
DEFAULT_SRC = ROOT / "source-prepped.png"

WIDTH = 370
HEIGHT = 420
STATIC = os.environ.get("STATIC") == "1"

BG = "#0d1117"
CHROME = "#161b22"
BORDER = "#30363d"
INK = "#b8c2cc"          # monochrome light-grey, per the article
DIM = "#7d8590"
ACCENT = "#39d353"

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# Sparse -> dense. The glyphs are light on a dark panel, so a denser character
# reads as a *brighter* pixel: 0 (the black background) -> ' ', 255 -> '@'.
RAMP = " .`:-=+*cs#%@"

CHROME_H = 36
PAD_X = 8
PAD_TOP = 10
PAD_BOT = 10
# 78 cols lands the glyphs at ~7.5px. Pushing to 100 (as the article does) works
# at full width, but at 370px the font drops under 6px and subpixel antialiasing
# starts fringing the monochrome art with colour.
COLS = 78

# Relative (x0, y0, x1, y1) crop applied before anything else, tuned for the
# current source photo: a full-body shot leaves the face only ~12 characters
# wide, which is well under what the 13-step ramp needs to show a feature.
# Set to None to use the whole frame; override per-run with --crop=x0,y0,x1,y1.
CROP = (0.16, 0.00, 0.70, 0.54)

ART_W = WIDTH - PAD_X * 2
ART_TOP = CHROME_H + PAD_TOP
ART_H = HEIGHT - ART_TOP - PAD_BOT

CHAR_W = ART_W / COLS
FONT = CHAR_W / 0.6
LINE_H = FONT * 1.02
ROWS = int(ART_H // LINE_H)


def sample_image(path: Path, crop: tuple[float, float, float, float] | None) -> list[list[int]]:
    """Crop to frame the subject, fit the character-grid aspect, downsample."""
    from PIL import Image  # imported lazily so --placeholder needs no deps

    image = Image.open(path).convert("L")

    if crop:
        w, h = image.size
        x0, y0, x1, y1 = crop
        image = image.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
        print(f"[ascii] cropped to {image.width}x{image.height}")

    target = (COLS * CHAR_W) / (ROWS * LINE_H)
    w, h = image.size

    if w / h > target:                       # too wide -> trim the sides
        new_w = int(h * target)
        left = (w - new_w) // 2
        image = image.crop((left, 0, left + new_w, h))
    else:                                    # too tall -> trim top/bottom
        new_h = int(w / target)
        top = int((h - new_h) * 0.35)        # bias upward: keep the face, drop the chest
        image = image.crop((0, top, w, top + new_h))

    image = image.resize((COLS, ROWS), Image.LANCZOS)
    px = image.load()
    return [[px[x, y] for x in range(COLS)] for y in range(ROWS)]


def placeholder_grid() -> list[list[int]]:
    """A procedural bust silhouette, so the README renders before a photo exists."""
    grid: list[list[int]] = []
    for row in range(ROWS):
        line: list[int] = []
        v = row / (ROWS - 1)
        for col in range(COLS):
            u = col / (COLS - 1)
            dx, dy = (u - 0.5) * 1.9, (v - 0.34) * 2.05
            head = 1.0 - math.hypot(dx, dy) / 0.62
            sx, sy = (u - 0.5) * 1.25, (v - 1.18) * 1.3
            shoulders = 1.0 - math.hypot(sx, sy) / 0.72
            mass = max(head, shoulders)
            if mass <= 0:
                line.append(0)            # background -> blank character
                continue
            edge = min(1.0, mass / 0.30)                              # soft rim falloff
            lit = max(0.0, min(1.0, 0.55 - 0.45 * dx - 0.30 * dy))    # key light, upper-left
            bright = 0.10 + 0.72 * lit * (0.30 + 0.70 * edge)
            line.append(int(255 * max(0.0, min(0.90, bright))))
        grid.append(line)
    return grid


def to_ascii(grid: list[list[int]]) -> list[str]:
    span = len(RAMP) - 1
    return [
        "".join(RAMP[min(span, int(v * len(RAMP) / 256))] for v in row)
        for row in grid
    ]


def render(rows: list[str], label: str) -> str:
    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="ASCII-art portrait">'
    )

    style = (
        "<style>"
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        f".t{{font-family:{MONO};dominant-baseline:middle;white-space:pre}}"
    )
    if not STATIC:
        style += (
            "@keyframes wipe{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
            "@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}"
            "to{opacity:1;transform:translateY(0)}}"
            ".w{transform-box:fill-box;transform-origin:left center;"
            "animation:wipe .22s linear both}"
            ".chrome{opacity:0;animation:fadeUp .5s ease-out both}"
            ".cursor{animation:blink 1.05s step-end infinite}"
        )
    style += "</style>"
    parts.append(style)

    # --- terminal chrome -------------------------------------------------
    parts.append(
        f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>'
    )
    parts.append(
        f'<path d="M0 10a10 10 0 0 1 10-10h{WIDTH - 20}a10 10 0 0 1 10 10v26H0z" fill="{CHROME}"/>'
    )
    parts.append(f'<line x1="0" y1="{CHROME_H}" x2="{WIDTH}" y2="{CHROME_H}" stroke="{BORDER}"/>')
    for i, colour in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        parts.append(f'<circle cx="{20 + i * 18}" cy="18" r="5.5" fill="{colour}"/>')
    parts.append(
        f'<text class="t chrome" x="{WIDTH / 2}" y="19" fill="{DIM}" font-size="11" '
        f'text-anchor="middle">{escape(label)}</text>'
    )

    # --- typewriter clip: one rect per row, staggered --------------------
    if not STATIC:
        parts.append('<clipPath id="typewriter">')
        for i in range(len(rows)):
            y = ART_TOP + i * LINE_H
            parts.append(
                f'<rect class="w" x="{PAD_X}" y="{y:.2f}" width="{ART_W}" '
                f'height="{LINE_H + 1:.2f}" style="animation-delay:{0.25 + i * 0.026:.3f}s"/>'
            )
        parts.append("</clipPath>")
        parts.append('<g clip-path="url(#typewriter)">')
    else:
        parts.append("<g>")

    for i, line in enumerate(rows):
        y = ART_TOP + i * LINE_H + LINE_H / 2
        parts.append(
            f'<text class="t" x="{PAD_X}" y="{y:.2f}" fill="{INK}" font-size="{FONT:.3f}" '
            f'textLength="{ART_W}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve">{escape(line)}</text>'
        )
    parts.append("</g>")

    parts.append("</svg>")
    return "".join(parts)


def parse_crop(argv: list[str]) -> tuple[float, float, float, float] | None:
    for arg in argv:
        if arg == "--no-crop":
            return None
        if arg.startswith("--crop="):
            parts = tuple(float(p) for p in arg.split("=", 1)[1].split(","))
            if len(parts) != 4:
                raise SystemExit("--crop needs four comma-separated values: x0,y0,x1,y1")
            return parts  # type: ignore[return-value]
    return CROP


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("-")]
    force_placeholder = "--placeholder" in argv[1:]

    src = Path(args[0]) if args else DEFAULT_SRC

    if force_placeholder:
        grid, label = placeholder_grid(), "portrait.ascii [placeholder]"
        print("[ascii] rendering procedural placeholder (no photo used)")
    elif src.exists():
        grid, label = sample_image(src, parse_crop(argv[1:])), "portrait.ascii"
        print(f"[ascii] sampled {src.name} -> {COLS}x{ROWS} grid")
    else:
        print(
            f"[ascii] ERROR: {src.name} not found.\n"
            f"        Run prep_photo.py first, or pass --placeholder.",
            file=sys.stderr,
        )
        return 1

    OUT.write_text(render(to_ascii(grid), label), encoding="utf-8")
    mode = "static" if STATIC else "animated"
    print(f"[ascii] {mode} -> {OUT.name} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
