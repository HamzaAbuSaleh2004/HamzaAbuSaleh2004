"""Render data/contributions.json as an animated contribution heatmap SVG.

Everything animates with CSS @keyframes *inside* the SVG -- GitHub strips <script>
and inline README styles, but CSS animations inside an <img>-loaded SVG do run.

Output: contrib-heatmap.svg (860px wide, to match 370 + 490 in the README table).
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

# STATIC=1 emits a frozen final frame -- useful for previewing in an image viewer.
STATIC = os.environ.get("STATIC") == "1"

WIDTH = 860
CELL = 12
GAP = 3
PITCH = CELL + GAP
WEEKS = 53
ROWS = 7

PAD_L = 42          # room for the Mon/Wed/Fri labels
PAD_T = 84          # title bar + prompt line + month labels
MONTH_ROW_Y = 72
GRID_W = WEEKS * PITCH - GAP
HEIGHT = PAD_T + ROWS * PITCH - GAP + 62

# GitHub-ish greens, with one extra hot step at the top end.
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

BG = "#0d1117"
CHROME = "#161b22"
BORDER = "#30363d"
FG = "#c9d1d9"
DIM = "#7d8590"
ACCENT = "#39d353"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


def bucket(count: int, level: int) -> int:
    """Map a day to a palette index, promoting genuinely huge days to the hot step."""
    if count >= 20:
        return 5
    return max(0, min(4, level))


def build_month_labels(days: list[dict]) -> list[tuple[int, str]]:
    """Anchor each month at its first week, skipping months with no real footing.

    The calendar starts mid-month, so the leading partial month (often a single
    column) would otherwise get a label that collides with the next one. Only
    anchoring on a day in the first week of the month drops it cleanly.
    """
    labels: list[tuple[int, str]] = []
    seen: set[tuple[int, int]] = set()
    for day in days:
        date = dt.date.fromisoformat(day["date"])
        if date.day > 7:
            continue
        key = (date.year, date.month)
        if key in seen:
            continue
        seen.add(key)
        week = day["week"]
        if labels and week - labels[-1][0] < 3:
            continue
        labels.append((week, MONTHS[date.month - 1]))
    return labels


def render(payload: dict) -> str:
    days = payload["days"]
    stats = payload["stats"]
    user = payload["username"]

    # Right-align the calendar so the newest week sits at the far right edge.
    max_week = max((d["week"] for d in days), default=0)
    week_shift = (WEEKS - 1) - max_week

    parts: list[str] = []
    # Explicit declaration: the card uses ➜/·/─, and we don't want a server that
    # serves SVG without charset=utf-8 to mangle them.
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{escape(user)} GitHub contribution heatmap">'
    )

    style = f"<style>.t{{font-family:{MONO};dominant-baseline:middle}}"
    if not STATIC:
        style += (
            "@keyframes popIn{"
            "from{opacity:0;transform:translateY(-7px) scale(.55)}"
            "to{opacity:1;transform:translateY(0) scale(1)}}"
            "@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}"
            "to{opacity:1;transform:translateY(0)}}"
            "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
            ".cell{transform-box:fill-box;transform-origin:center;opacity:0;"
            "animation:popIn .45s cubic-bezier(.2,.8,.3,1) both}"
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
    parts.append(f'<path d="M0 10a10 10 0 0 1 10-10h{WIDTH - 20}a10 10 0 0 1 10 10v26H0z" fill="{CHROME}"/>')
    parts.append(f'<line x1="0" y1="36" x2="{WIDTH}" y2="36" stroke="{BORDER}"/>')
    for i, colour in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        parts.append(f'<circle cx="{20 + i * 18}" cy="18" r="5.5" fill="{colour}"/>')
    parts.append(
        f'<text class="t chrome" x="{WIDTH / 2}" y="19" fill="{DIM}" font-size="11.5" '
        f'text-anchor="middle">{escape(user)}@github: ~/contributions</text>'
    )

    prompt_y = 52
    parts.append(
        f'<text class="t chrome" x="18" y="{prompt_y}" font-size="12.5" '
        f'style="animation-delay:.1s">'
        f'<tspan fill="{ACCENT}">➜</tspan> '
        f'<tspan fill="#58a6ff">~</tspan> '
        f'<tspan fill="{FG}">./contributions.sh --year</tspan>'
        f'<tspan class="cursor" fill="{ACCENT}"> ▍</tspan>'
        f"</text>"
    )

    # --- month + weekday labels -----------------------------------------
    for week, name in build_month_labels(days):
        x = PAD_L + (week + week_shift) * PITCH
        parts.append(
            f'<text class="t chrome" x="{x}" y="{MONTH_ROW_Y}" fill="{DIM}" font-size="9.5" '
            f'style="animation-delay:.2s">{name}</text>'
        )

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = PAD_T + row * PITCH + CELL / 2
        parts.append(
            f'<text class="t chrome" x="{PAD_L - 8}" y="{y}" fill="{DIM}" font-size="9.5" '
            f'text-anchor="end" style="animation-delay:.2s">{label}</text>'
        )

    # --- the grid --------------------------------------------------------
    parts.append("<g>")
    for day in days:
        col = day["week"] + week_shift
        x = PAD_L + col * PITCH
        y = PAD_T + day["weekday"] * PITCH
        fill = PALETTE[bucket(day["count"], day["level"])]
        # Diagonal wave: delay grows with (column + row), so it sweeps down-right.
        delay = 0.30 + (col + day["weekday"]) * 0.014
        plural = "" if day["count"] == 1 else "s"
        parts.append(
            f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
            f'fill="{fill}" style="animation-delay:{delay:.3f}s">'
            f'<title>{day["count"]} contribution{plural} on {day["date"]}</title></rect>'
        )
    parts.append("</g>")

    # --- footer: legend left, stats right --------------------------------
    foot_y = PAD_T + ROWS * PITCH + 16
    legend_x = PAD_L
    parts.append(
        f'<text class="t chrome" x="{legend_x}" y="{foot_y + 6}" fill="{DIM}" font-size="10" '
        f'style="animation-delay:1.5s">Less</text>'
    )
    for i, colour in enumerate(PALETTE):
        parts.append(
            f'<rect class="cell" x="{legend_x + 30 + i * PITCH}" y="{foot_y}" '
            f'width="{CELL}" height="{CELL}" rx="2.5" fill="{colour}" '
            f'style="animation-delay:{1.55 + i * 0.05:.2f}s"/>'
        )
    parts.append(
        f'<text class="t chrome" x="{legend_x + 36 + len(PALETTE) * PITCH}" y="{foot_y + 6}" '
        f'fill="{DIM}" font-size="10" style="animation-delay:1.9s">More</text>'
    )

    busiest = stats.get("busiest_day") or {"count": 0}
    summary = (
        f'{stats["total"]} contributions  ·  '
        f'{stats["current_streak"]}d streak  ·  '
        f'{stats["longest_streak"]}d best  ·  '
        f'{stats["active_days"]} active days  ·  '
        f'peak {busiest["count"]}'
    )
    parts.append(
        f'<text class="t chrome" x="{WIDTH - 18}" y="{foot_y + 6}" fill="{FG}" font-size="11" '
        f'text-anchor="end" style="animation-delay:1.95s">{escape(summary)}</text>'
    )

    parts.append(
        f'<text class="t chrome" x="{WIDTH - 18}" y="{foot_y + 26}" fill="{DIM}" font-size="9" '
        f'text-anchor="end" style="animation-delay:2.05s">'
        f'last refresh {escape(payload["generated_at"])}</text>'
    )

    parts.append("</svg>")
    return "".join(parts)


def main() -> int:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.write_text(render(payload), encoding="utf-8")
    print(f"[heatmap] {len(payload['days'])} cells -> {OUT.name} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
