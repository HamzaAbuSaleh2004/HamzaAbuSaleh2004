"""Hand-author a neofetch-style info card as an animated SVG.

Output: info-card.svg (490x420 viewBox -- same height ratio as portrait-ascii.svg
so the two line up in the README table).

Set STATIC=1 to emit a frozen frame (handy for previewing in an image viewer).
"""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape

# ---------------------------------------------------------------------------
# EDIT ME -- this is the only block you need to touch.
# ---------------------------------------------------------------------------
PROFILE = {
    "user": "hamza",
    "host": "github",
    "rows": [
        ("Now", "Building AI agents @ LiverX"),
        ("Prev", "Data Science & AI @ Al Hussein Technical University"),
        ("Stack", "Python · Google ADK · Vertex AI · GCP · PyTorch · FastAPI"),
        ("Focus", "Multi-agent systems, MLOps, applied ML"),
        ("Highlights", "Cancer-risk prediction · CNN image classification · transit analytics"),
        ("Web", "hamza-portfolio-rk8n.onrender.com"),
        ("Email", "hamzaabusaleh04@gmail.com"),
    ],
}
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "info-card.svg"

WIDTH = 490
HEIGHT = 420
STATIC = os.environ.get("STATIC") == "1"

BG = "#0d1117"
CHROME = "#161b22"
BORDER = "#30363d"
FG = "#c9d1d9"
DIM = "#7d8590"
KEY = "#39d353"
ACCENT = "#58a6ff"

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

CHROME_H = 36
PAD_X = 18
FONT = 11.5
CHAR_W = FONT * 0.6           # monospace advance
LINE_H = 17.5
KEY_W = 78                    # left column width in px


def wrap(text: str, max_chars: int) -> list[str]:
    """Greedy word wrap; falls back to hard-splitting any oversized token."""
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        while len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[: max_chars - 1] + "-")
            word = word[max_chars - 1 :]
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def anim(delay: float, base: str = "") -> str:
    """Attribute string for a staggered element, merging `base` into the class list."""
    classes = f"{base} row".strip() if not STATIC else base
    attrs = f' class="{classes}"' if classes else ""
    if not STATIC:
        attrs += f' style="animation-delay:{delay:.2f}s"'
    return attrs


def render() -> str:
    user, host = PROFILE["user"], PROFILE["host"]
    value_chars = int((WIDTH - PAD_X * 2 - KEY_W) / CHAR_W)

    parts: list[str] = []
    # Explicit declaration: the card uses ➜/·/─, and we don't want a server that
    # serves SVG without charset=utf-8 to mangle them.
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Profile info card">'
    )

    style = (
        "<style>"
        "@keyframes slideIn{from{opacity:0;transform:translateX(-10px)}"
        "to{opacity:1;transform:translateX(0)}}"
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        f".t{{font-family:{MONO};dominant-baseline:middle;white-space:pre}}"
    )
    if not STATIC:
        style += (
            ".row{opacity:0;animation:slideIn .5s cubic-bezier(.2,.8,.3,1) both}"
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
        f'<text class="t" x="{WIDTH / 2}" y="19" fill="{DIM}" font-size="11" '
        f'text-anchor="middle">neofetch</text>'
    )

    y = CHROME_H + 26
    delay = 0.15

    # --- prompt ----------------------------------------------------------
    cursor = "" if STATIC else f'<tspan class="cursor" fill="{KEY}"> ▍</tspan>'
    parts.append(
        f'<text{anim(delay, "t")} x="{PAD_X}" y="{y}" font-size="{FONT}">'
        f'<tspan fill="{KEY}">➜</tspan> <tspan fill="{ACCENT}">~</tspan> '
        f'<tspan fill="{FG}">neofetch --profile</tspan>{cursor}</text>'
    )
    y += LINE_H * 1.7
    delay += 0.18

    # --- user@host + rule ------------------------------------------------
    parts.append(
        f'<text{anim(delay, "t")} x="{PAD_X}" y="{y}" font-size="{FONT + 1.5}" '
        f'font-weight="700">'
        f'<tspan fill="{KEY}">{escape(user)}</tspan>'
        f'<tspan fill="{DIM}">@</tspan>'
        f'<tspan fill="{ACCENT}">{escape(host)}</tspan></text>'
    )
    y += LINE_H
    delay += 0.1

    rule = "─" * int((WIDTH - PAD_X * 2) / CHAR_W)
    parts.append(
        f'<text{anim(delay, "t")} x="{PAD_X}" y="{y}" fill="{BORDER}" '
        f'font-size="{FONT}">{rule}</text>'
    )
    y += LINE_H * 1.3
    delay += 0.1

    # --- key/value rows --------------------------------------------------
    for label, value in PROFILE["rows"]:
        for i, line in enumerate(wrap(value, value_chars)):
            parts.append(f'<g{anim(delay)}>')
            if i == 0:
                parts.append(
                    f'<text class="t" x="{PAD_X}" y="{y}" fill="{KEY}" font-size="{FONT}" '
                    f'font-weight="700">{escape(label)}</text>'
                )
            parts.append(
                f'<text class="t" x="{PAD_X + KEY_W}" y="{y}" fill="{FG}" '
                f'font-size="{FONT}">{escape(line)}</text>'
            )
            parts.append("</g>")
            y += LINE_H
            delay += 0.09
        y += 5

    # --- neofetch colour swatches ---------------------------------------
    swatch_y = HEIGHT - 30
    swatches = ["#ff5f56", "#ffbd2e", "#27c93f", "#39d353",
                "#58a6ff", "#bc8cff", "#39c5cf", "#c9d1d9"]
    for i, colour in enumerate(swatches):
        parts.append(
            f'<rect{anim(delay + i * 0.05)} x="{PAD_X + i * 20}" y="{swatch_y}" '
            f'width="16" height="10" rx="2" fill="{colour}"/>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main() -> int:
    OUT.write_text(render(), encoding="utf-8")
    mode = "static" if STATIC else "animated"
    print(f"[info-card] {mode} -> {OUT.name} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
