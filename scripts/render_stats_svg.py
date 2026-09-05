"""Render data/stats.json as an animated stats panel SVG.

Design notes, so future edits don't undo deliberate choices:

* One green for every bar, not a ramp. This is a single series sorted by
  magnitude -- length already encodes the value and each bar carries its own
  name and percentage, so a per-bar hue would encode nothing. Six greens close
  enough to look like a set also measure ~5 delta-E apart, which is below what
  normal colour vision resolves, so the shades would have been unreadable as
  meaning even if they had carried any.
* Every bar is directly labelled. GitHub renders this through <img>, where no
  tooltip or hover can fire, so nothing may hide behind interaction.

Output: stats-card.svg (860 wide, matching the README column sum).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "stats.json"
OUT = ROOT / "stats-card.svg"

STATIC = os.environ.get("STATIC") == "1"

WIDTH = 860
HEIGHT = 344
PAD = 24
CHROME_H = 36

BG = "#0d1117"
CHROME = "#161b22"
BORDER = "#30363d"
TRACK = "#21262d"
FG = "#c9d1d9"
DIM = "#7d8590"
BRIGHT = "#f0f6fc"
BAR = "#39d353"      # contrast vs BG well above 3:1
ACCENT = "#58a6ff"

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

TILE_Y = 74
TILE_H = 56
TILE_GAP = 14

BARS_TOP = 172
ROW_PITCH = 24       # 10px bar + 14px gap, comfortably over the 2px minimum
BAR_H = 10
NAME_W = 150
TRACK_X = PAD + NAME_W + 12
TRACK_W = 560


def human_bytes(n: int) -> str:
    mb = n / (1024 * 1024)
    return f"{mb:.1f} MB" if mb < 1024 else f"{mb / 1024:.1f} GB"


def anim(delay: float, base: str = "") -> str:
    classes = f"{base} in".strip() if not STATIC else base
    attrs = f' class="{classes}"' if classes else ""
    if not STATIC:
        attrs += f' style="animation-delay:{delay:.2f}s"'
    return attrs


def render(payload: dict) -> str:
    totals = payload["totals"]
    languages = payload["languages"]
    user = payload["username"]

    parts: list[str] = ['<?xml version="1.0" encoding="UTF-8"?>']
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{escape(user)} language and repository statistics">'
    )

    style = (
        "<style>"
        f".t{{font-family:{MONO};dominant-baseline:middle}}"
        ".lbl{letter-spacing:.09em}"
    )
    if not STATIC:
        style += (
            "@keyframes fadeUp{from{opacity:0;transform:translateY(7px)}"
            "to{opacity:1;transform:translateY(0)}}"
            "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
            "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
            ".in{opacity:0;animation:fadeUp .5s cubic-bezier(.2,.8,.3,1) both}"
            ".bar{transform-box:fill-box;transform-origin:left center;"
            "animation:grow .7s cubic-bezier(.2,.8,.3,1) both}"
            ".cursor{animation:blink 1.05s step-end infinite}"
        )
    style += "</style>"
    parts.append(style)

    # --- chrome ----------------------------------------------------------
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
        f'<text class="t" x="{WIDTH / 2}" y="19" fill="{DIM}" font-size="11.5" '
        f'text-anchor="middle">{escape(user)}@github: ~/stats</text>'
    )

    cursor = "" if STATIC else f'<tspan class="cursor" fill="{BAR}"> ▍</tspan>'
    parts.append(
        f'<text{anim(0.08, "t")} x="{PAD}" y="56" font-size="12.5">'
        f'<tspan fill="{BAR}">➜</tspan> <tspan fill="{ACCENT}">~</tspan> '
        f'<tspan fill="{FG}">./stats.sh</tspan>{cursor}</text>'
    )

    # --- KPI tiles -------------------------------------------------------
    tiles = [
        ("REPOSITORIES", str(totals["repos"]), "public"),
        ("LANGUAGES", str(totals["languages"]), "across all repos"),
        ("CODE", human_bytes(totals["code_bytes"]), "tracked by GitHub"),
    ]
    tile_w = (WIDTH - PAD * 2 - TILE_GAP * 2) / 3
    for i, (label, value, sub) in enumerate(tiles):
        x = PAD + i * (tile_w + TILE_GAP)
        parts.append(f'<g{anim(0.18 + i * 0.09)}>')
        parts.append(
            f'<rect x="{x:.1f}" y="{TILE_Y}" width="{tile_w:.1f}" height="{TILE_H}" '
            f'rx="7" fill="{CHROME}" stroke="{BORDER}"/>'
        )
        parts.append(
            f'<text class="t lbl" x="{x + 14:.1f}" y="{TILE_Y + 17}" fill="{DIM}" '
            f'font-size="9">{label}</text>'
        )
        parts.append(
            f'<text class="t" x="{x + 14:.1f}" y="{TILE_Y + 38}" fill="{BRIGHT}" '
            f'font-size="21" font-weight="700">{escape(value)}</text>'
        )
        parts.append(
            f'<text class="t" x="{x + tile_w - 14:.1f}" y="{TILE_Y + 39}" fill="{DIM}" '
            f'font-size="9.5" text-anchor="end">{escape(sub)}</text>'
        )
        parts.append("</g>")

    # --- language bars ---------------------------------------------------
    parts.append(
        f'<text{anim(0.46, "t lbl")} x="{PAD}" y="152" fill="{DIM}" font-size="9">'
        f'CODE BY LANGUAGE</text>'
    )

    widest = max((l["percent"] for l in languages), default=1) or 1
    for i, lang in enumerate(languages):
        y = BARS_TOP + i * ROW_PITCH
        # Scale to the largest share so the row reads as a comparison, not a
        # sliver -- the exact number sits at the end of every bar regardless.
        fill_w = max(3.0, TRACK_W * lang["percent"] / widest)
        delay = 0.52 + i * 0.08

        parts.append(f'<g{anim(delay)}>')
        parts.append(
            f'<text class="t" x="{PAD}" y="{y}" fill="{FG}" font-size="11.5">'
            f'{escape(lang["name"])}</text>'
        )
        parts.append(
            f'<rect x="{TRACK_X}" y="{y - BAR_H / 2}" width="{TRACK_W}" height="{BAR_H}" '
            f'rx="4" fill="{TRACK}"/>'
        )
        bar_style = "" if STATIC else f' style="animation-delay:{delay + 0.1:.2f}s"'
        bar_class = "" if STATIC else ' class="bar"'
        parts.append(
            f'<rect{bar_class}{bar_style} x="{TRACK_X}" y="{y - BAR_H / 2}" '
            f'width="{fill_w:.1f}" height="{BAR_H}" rx="4" fill="{BAR}">'
            f'<title>{escape(lang["name"])}: {lang["percent"]}% '
            f'({human_bytes(lang["bytes"])})</title></rect>'
        )
        parts.append(
            f'<text class="t" x="{WIDTH - PAD}" y="{y}" fill="{BRIGHT}" font-size="11.5" '
            f'text-anchor="end">{lang["percent"]}%</text>'
        )
        parts.append("</g>")

    # --- footer ----------------------------------------------------------
    foot = (
        f'{totals["repos"]} public repos  ·  private repos excluded  ·  '
        f'refreshed {payload["generated_at"]}'
    )
    parts.append(
        f'<text{anim(1.15, "t")} x="{WIDTH - PAD}" y="{HEIGHT - 16}" fill="{DIM}" '
        f'font-size="9" text-anchor="end">{escape(foot)}</text>'
    )

    parts.append("</svg>")
    return "".join(parts)


def main() -> int:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.write_text(render(payload), encoding="utf-8")
    mode = "static" if STATIC else "animated"
    print(f"[stats-card] {mode} -> {OUT.name} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
