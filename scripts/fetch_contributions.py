"""Scrape the public GitHub contributions calendar into data/contributions.json.

Uses the public HTML fragment at https://github.com/users/<user>/contributions --
no token, no GraphQL, no auth of any kind.

Set GITHUB_PROFILE_USER to override the username (the Action passes the repo owner).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GITHUB_PROFILE_USER", "HamzaAbuSaleh2004")
URL = f"https://github.com/users/{USERNAME}/contributions"

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"

# Tooltip text looks like "No contributions on August 31st." /
# "1 contribution on September 3rd." / "12 contributions on ...".
COUNT_RE = re.compile(r"^\s*(No|[\d,]+)\s+contributions?\b", re.IGNORECASE)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; profile-readme-bot/1.0)",
    "Accept": "text/html",
    "X-Requested-With": "XMLHttpRequest",
}


def fetch_html() -> str:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # Counts live in <tool-tip for="contribution-day-component-R-C">, not on the cell.
    tooltips = {
        tip.get("for"): tip.get_text(" ", strip=True)
        for tip in soup.find_all("tool-tip")
        if tip.get("for")
    }

    today = dt.date.today()
    days: list[dict] = []

    for cell in soup.select("td.ContributionCalendar-day"):
        iso = cell.get("data-date")
        if not iso:
            continue
        try:
            date = dt.date.fromisoformat(iso)
        except ValueError:
            continue
        if date > today:  # trailing cells of the current week
            continue

        count = 0
        match = COUNT_RE.match(tooltips.get(cell.get("id") or "", ""))
        if match:
            token = match.group(1)
            count = 0 if token.lower() == "no" else int(token.replace(",", ""))

        days.append(
            {
                "date": iso,
                "count": count,
                # data-level is GitHub's own 0-4 intensity bucket.
                "level": int(cell.get("data-level") or 0),
                "week": int(cell.get("data-ix") or 0),
                # GitHub rows run Sunday(0) -> Saturday(6).
                "weekday": date.isoweekday() % 7,
            }
        )

    days.sort(key=lambda d: d["date"])
    return days


def compute_stats(days: list[dict]) -> dict:
    counts = [d["count"] for d in days]
    total = sum(counts)
    active = sum(1 for c in counts if c > 0)

    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)

    # Current streak: walk backwards. A blank *today* doesn't break a live streak,
    # which matches how GitHub itself presents it.
    tail = list(counts)
    if tail and tail[-1] == 0:
        tail.pop()
    current = 0
    for c in reversed(tail):
        if c == 0:
            break
        current += 1

    best = max(days, key=lambda d: d["count"], default=None)

    return {
        "total": total,
        "active_days": active,
        "tracked_days": len(days),
        "current_streak": current,
        "longest_streak": longest,
        "busiest_day": {"date": best["date"], "count": best["count"]} if best else None,
        "average_per_day": round(total / len(days), 2) if days else 0,
        "first_date": days[0]["date"] if days else None,
        "last_date": days[-1]["date"] if days else None,
    }


def main() -> int:
    print(f"[fetch] {URL}")
    days = parse_days(fetch_html())
    if not days:
        print("[fetch] ERROR: no day cells parsed -- GitHub markup may have changed.", file=sys.stderr)
        return 1

    stats = compute_stats(days)
    payload = {
        "username": USERNAME,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": URL,
        "stats": stats,
        "days": days,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(
        f"[fetch] {len(days)} days | {stats['total']} contributions | "
        f"streak {stats['current_streak']} (best {stats['longest_streak']}) -> {OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
