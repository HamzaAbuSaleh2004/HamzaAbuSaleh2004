"""Prep a portrait photo for ASCII conversion.

  1. cut the background out with rembg
  2. boost local contrast with CLAHE (ASCII ramps need punchy midtones)
  3. flatten onto pure white, so the background maps to blank characters

Run once per photo -- the result is committed, so CI never needs these deps.

    pip install -r scripts/requirements-portrait.txt
    python scripts/prep_photo.py source-photo.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "source-prepped.png"

# CLAHE: modest clip limit keeps skin tones from posterising.
CLIP_LIMIT = 2.4
TILE_GRID = (8, 8)


def cut_background(image: Image.Image) -> Image.Image:
    print("[prep] removing background (first run downloads the u2net model)...")
    return remove(image.convert("RGBA"))


def boost_contrast(image: Image.Image) -> Image.Image:
    """CLAHE on the L channel of LAB, leaving the alpha matte untouched."""
    rgba = np.array(image)
    rgb, alpha = rgba[:, :, :3], rgba[:, :, 3]

    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=CLIP_LIMIT, tileGridSize=TILE_GRID)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    return Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA")


def flatten_white(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
    canvas.alpha_composite(image)
    return canvas.convert("RGB")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        print("usage: python scripts/prep_photo.py <photo> [output.png]", file=sys.stderr)
        return 2

    src = Path(argv[1])
    if not src.exists():
        print(f"[prep] ERROR: no such file: {src}", file=sys.stderr)
        return 1
    out = Path(argv[2]) if len(argv) > 2 else DEFAULT_OUT

    image = Image.open(src)
    print(f"[prep] loaded {src.name} ({image.width}x{image.height})")

    image = flatten_white(boost_contrast(cut_background(image)))
    image.save(out)

    print(f"[prep] wrote {out.name} -- now run: python scripts/make_ascii_svg.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
