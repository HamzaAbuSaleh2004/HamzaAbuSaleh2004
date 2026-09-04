"""Prep a portrait photo for ASCII conversion.

  1. cut the background out with rembg
  2. boost local contrast with CLAHE (ASCII ramps need punchy midtones)
  3. stretch the subject's tonal range, then flatten onto black

Step 3 matters more than it looks. The art is drawn as light glyphs on a dark
panel, so a dense '@' reads as *bright* -- meaning the background has to land on
black (a blank character) and the subject has to stay above it. Composite onto
white instead and the whole thing inverts into an unreadable blob.

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

# Floor the subject sits on, so dark clothing still registers as a faint glyph
# instead of dropping out into the background.
SUBJECT_FLOOR = 42

# Ceiling, deliberately short of 255. The top of the ramp (#, %, @) is nearly
# uniform in perceived density, so letting a lit face run all the way up flattens
# it into a featureless blob. Capping here keeps skin in the c/s/# range, where
# the ramp still separates, and reserves @ for genuine speculars.
SUBJECT_CEIL = 225


def cut_background(image: Image.Image) -> Image.Image:
    print("[prep] removing background (first run downloads the matting model, ~1GB)...")
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


def flatten_black(image: Image.Image) -> Image.Image:
    """Stretch the subject's tonal range, then alpha-composite onto black.

    Percentiles rather than min/max, so a single blown-out highlight or one
    crushed shadow pixel can't collapse the whole range.
    """
    rgba = np.array(image).astype(np.float32)
    rgb, alpha = rgba[:, :, :3], rgba[:, :, 3:4] / 255.0

    subject = alpha[:, :, 0] > 0.5
    if subject.any():
        lum = rgb.mean(axis=2)
        lo, hi = np.percentile(lum[subject], [2, 99])
        if hi > lo:
            normalised = np.clip((rgb - lo) / (hi - lo), 0.0, 1.0)
            rgb = normalised * (SUBJECT_CEIL - SUBJECT_FLOOR) + SUBJECT_FLOOR
            print(f"[prep] subject levels {lo:.0f}-{hi:.0f} -> {SUBJECT_FLOOR}-{SUBJECT_CEIL}")

    flattened = rgb * alpha          # background falls to 0 -> blank character
    return Image.fromarray(np.clip(flattened, 0, 255).astype(np.uint8), mode="RGB")


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

    image = flatten_black(boost_contrast(cut_background(image)))
    image.save(out)

    print(f"[prep] wrote {out.name} -- now run: python scripts/make_ascii_svg.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
