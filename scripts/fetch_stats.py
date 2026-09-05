"""Aggregate public repo + language stats into data/stats.json.

Reads only the public API, so no token is required. If GITHUB_TOKEN happens to be
set (the Action provides one) it is used purely to raise the rate limit from 60
to 5000 requests/hour -- it never widens what is collected. Private repos are
deliberately excluded: they stay private, and the numbers stay honest.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

USERNAME = os.environ.get("GITHUB_PROFILE_USER", "HamzaAbuSaleh2004")
API = "https://api.github.com"

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "stats.json"

# Repos that exist only as accidents/duplicates and would skew the language mix.
EXCLUDE = {"https---github.com-HamzaAbuSaleh2004-Baladiya_Qatar"}

# Languages reported by GitHub that aren't really "what you write".
IGNORE_LANGUAGES = {"Dockerfile", "Makefile", "Batchfile", "Shell", "Procfile"}

TOP_LANGUAGES = 5


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-readme-bot/1.0",
        }
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
        print("[stats] using GITHUB_TOKEN for rate limit headroom")
    return s


def fetch_repos(s: requests.Session) -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        r = s.get(f"{API}/users/{USERNAME}/repos",
                  params={"per_page": 100, "page": page, "type": "owner"}, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1

    keep = [
        repo for repo in repos
        if not repo.get("fork") and not repo.get("archived") and repo["name"] not in EXCLUDE
    ]
    print(f"[stats] {len(keep)} public repos counted ({len(repos) - len(keep)} skipped)")
    return keep


def fetch_languages(s: requests.Session, repos: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repos:
        r = s.get(f"{API}/repos/{USERNAME}/{repo['name']}/languages", timeout=30)
        if r.status_code != 200:
            print(f"[stats]   ! {repo['name']}: languages HTTP {r.status_code}", file=sys.stderr)
            continue
        for lang, size in r.json().items():
            if lang in IGNORE_LANGUAGES:
                continue
            totals[lang] = totals.get(lang, 0) + size
    return totals


def main() -> int:
    s = session()
    repos = fetch_repos(s)
    if not repos:
        print("[stats] ERROR: no repos returned", file=sys.stderr)
        return 1

    totals = fetch_languages(s, repos)
    grand = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)

    languages = [
        {"name": name, "bytes": size, "percent": round(size * 100 / grand, 1)}
        for name, size in ranked[:TOP_LANGUAGES]
    ]
    other = sum(size for _, size in ranked[TOP_LANGUAGES:])
    if other:
        languages.append({"name": "Other", "bytes": other,
                          "percent": round(other * 100 / grand, 1)})

    payload = {
        "username": USERNAME,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totals": {
            "repos": len(repos),
            "languages": len(totals),
            "stars": sum(r.get("stargazers_count", 0) for r in repos),
            "code_bytes": grand,
        },
        "languages": languages,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    top = ", ".join(f"{l['name']} {l['percent']}%" for l in languages[:3])
    print(f"[stats] {len(repos)} repos | {len(totals)} languages | {top} -> {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
