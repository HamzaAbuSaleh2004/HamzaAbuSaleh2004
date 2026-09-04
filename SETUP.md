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

No `gh`? Create `HamzaAbuSaleh2004` on github.com/new (public, no README), then:

```bash
git remote add origin https://github.com/HamzaAbuSaleh2004.git
git push -u origin main
```

## Add your real portrait

The committed `portrait-ascii.svg` is a **procedural placeholder**. To use your face:

```bash
python -m venv .venv && .venv\Scripts\activate     # PowerShell: .venv\Scripts\Activate.ps1
pip install -r scripts/requirements-portrait.txt   # heavy: rembg pulls onnxruntime
python scripts/prep_photo.py source-photo.jpg      # → source-prepped.png
python scripts/make_ascii_svg.py                   # → portrait-ascii.svg
git add portrait-ascii.svg && git commit -m "feat: real portrait" && git push
```

A head-and-shoulders shot with even lighting and a clean background works best —
ASCII has ~13 brightness levels, so busy backdrops turn to mush.

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
