# Setup

## What's here

| File | What it does | Runs |
| --- | --- | --- |
| `scripts/fetch_contributions.py` | Scrapes the public contributions calendar → `data/contributions.json` | daily, in CI |
| `scripts/render_heatmap_svg.py` | `contributions.json` → `contrib-heatmap.svg` | daily, in CI |
| `scripts/make_info_card.py` | neofetch-style card → `info-card.svg` | locally, on demand |
| `scripts/prep_photo.py` | photo → background-free, contrast-boosted `source-prepped.png` | locally, once |
| `scripts/make_ascii_svg.py` | prepped photo → `portrait-ascii.svg` | locally, once |

No GitHub token is needed anywhere. The contributions endpoint is public HTML.

## Publish it

The repo name **must exactly equal your GitHub username** — that's what makes GitHub
show the README on your profile page.

```bash
git init -b main
git add .
git commit -m "feat: animated profile readme"
gh repo create HamzaAbuSaleh2004 --public --source . --push
```

No `gh`? Create `HamzaAbuSaleh2004` on github.com/new — public, and leave
"Add a README"/.gitignore/license **unticked**, or the push gets rejected for
having unrelated history. Then:

```bash
git remote add origin https://github.com/HamzaAbuSaleh2004/HamzaAbuSaleh2004.git
git push -u origin main
```

The name appears twice on purpose: owner, then repo.

## Regenerating the portrait

`portrait-ascii.svg` is built from `image.png`. To redo it, or to swap in a
different photo:

```bash
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r scripts/requirements-portrait.txt   # heavy: onnxruntime + a ~1GB matting model
python scripts/prep_photo.py image.png             # → source-prepped.png
python scripts/make_ascii_svg.py                   # → portrait-ascii.svg
```

Three settings control how it looks, and a new photo will usually need the first
one retuned:

- **`CROP` in `make_ascii_svg.py`** — relative `(x0, y0, x1, y1)`, currently
  `(0.16, 0.0, 0.70, 0.54)` to frame head-and-shoulders. The grid is only 78×47
  characters, so a full-body shot leaves the face ~12 characters wide and the
  features disappear. Try values with `--crop=x0,y0,x1,y1`, or `--no-crop` for
  the full frame, before editing the constant.
- **`SUBJECT_CEIL` in `prep_photo.py`** (225) — caps how bright the subject gets.
  The top of the ramp (`#`, `%`, `@`) is nearly uniform in perceived density, so
  letting a lit face reach 255 flattens it into a blob.
- **`SUBJECT_FLOOR`** (42) — keeps dark clothing from dropping out entirely.

### Why the photo gets composited onto black

The art is light glyphs on a dark panel, so a *denser* character reads as a
*brighter* pixel. That inverts the usual ASCII convention: the background has to
land on 0 (blank) and the subject sits above it. Composite onto white — as the
original article does, because it assumes dark-ink-on-light — and a dark suit
turns into a solid bright slab.

A head-and-shoulders shot with even lighting works best; the ramp only has 13
steps, so low-contrast or backlit photos turn to mush.

## Edit the info card

Everything you'd want to change lives in the `PROFILE` dict at the top of
`scripts/make_info_card.py`. Then:

```bash
python scripts/make_info_card.py
```

Set `STATIC=1` to render a frozen frame instead of the animated one (useful for
previewing in an image viewer that ignores CSS animation).

## Layout rules that actually matter

- `860 = 370 + 490`. The heatmap width must equal the sum of the two table
  columns or the block looks misaligned. Change one, change all three.
- GitHub strips `<script>` and inline `style` attributes from README HTML, so
  **every animation lives inside the SVG files** as CSS `@keyframes`.
- `<h3>` instead of `<h1>`/`<h2>` — the bigger headings get a full-width
  underline rule that breaks the centered terminal look.
- Vertical spacing comes from `<br>` tags; CSS margins get stripped.

## Verify the daily job

Actions tab → **Update profile art** → *Run workflow*. It should commit a fresh
`contrib-heatmap.svg`. The `[skip ci]` in the commit message stops the bot commit
from re-triggering the `push` build.
