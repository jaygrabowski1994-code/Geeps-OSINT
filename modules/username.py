"""
Username Investigation module.

Checks whether a given username appears to be registered on a curated
list of major public platforms, using only publicly reachable profile
URLs (no login, no scraping behind auth walls, no ToS-violating bulk
scraping). Designed to degrade gracefully: a network hiccup on one
site never aborts the rest of the scan.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List

from core.logger import get_logger
from core.netutils import head, get
from core.ui import banner, clear, err, info, ok, pause, prompt, section, warn

log = get_logger("username")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,39}$")

# Each entry: platform name, profile URL template, method, and how to
# interpret the response ("head_status" = 200 means exists; some sites
# always return 200 and need a body-text check instead).
PLATFORMS: List[dict] = [
    {"name": "GitHub", "url": "https://github.com/{u}", "mode": "head"},
    {"name": "GitLab", "url": "https://gitlab.com/{u}", "mode": "head"},
    {"name": "Reddit", "url": "https://www.reddit.com/user/{u}/about.json", "mode": "get_json"},
    {"name": "X (Twitter)", "url": "https://x.com/{u}", "mode": "head"},
    {"name": "Instagram", "url": "https://www.instagram.com/{u}/", "mode": "head"},
    {"name": "Steam", "url": "https://steamcommunity.com/id/{u}", "mode": "get_text_notfound",
     "notfound_marker": "The specified profile could not be found"},
    {"name": "Twitch", "url": "https://www.twitch.tv/{u}", "mode": "head"},
    {"name": "YouTube (@handle)", "url": "https://www.youtube.com/@{u}", "mode": "head"},
    {"name": "TikTok", "url": "https://www.tiktok.com/@{u}", "mode": "head"},
    {"name": "Pinterest", "url": "https://www.pinterest.com/{u}/", "mode": "head"},
    {"name": "HackerNews", "url": "https://news.ycombinator.com/user?id={u}", "mode": "get_text_notfound",
     "notfound_marker": "No such user"},
    {"name": "Dev.to", "url": "https://dev.to/{u}", "mode": "head"},
    {"name": "Medium", "url": "https://medium.com/@{u}", "mode": "head"},
    {"name": "PyPI (author profile via projects)", "url": "https://pypi.org/user/{u}/", "mode": "head"},
]


@dataclass
class PlatformResult:
    platform: str
    url: str
    status: str  # "found" | "not_found" | "unknown"
    detail: str = ""


def _check_platform(entry: dict, username: str) -> PlatformResult:
    url = entry["url"].format(u=username)
    try:
        if entry["mode"] == "head":
            result = head(url)
            if not result.ok:
                return PlatformResult(entry["name"], url, "unknown", result.error or "request failed")
            if result.status_code == 200:
                return PlatformResult(entry["name"], url, "found")
            if result.status_code in (404, 410):
                return PlatformResult(entry["name"], url, "not_found")
            return PlatformResult(entry["name"], url, "unknown", f"HTTP {result.status_code}")

        if entry["mode"] == "get_json":
            result = get(url, expect_json=True)
            if result.status_code == 404:
                return PlatformResult(entry["name"], url, "not_found")
            if result.ok and result.json_data is not None:
                return PlatformResult(entry["name"], url, "found")
            return PlatformResult(entry["name"], url, "unknown", result.error or f"HTTP {result.status_code}")

        if entry["mode"] == "get_text_notfound":
            result = get(url)
            if not result.ok:
                return PlatformResult(entry["name"], url, "unknown", result.error or "request failed")
            marker = entry.get("notfound_marker", "")
            if marker and marker in result.text:
                return PlatformResult(entry["name"], url, "not_found")
            if result.status_code == 200:
                return PlatformResult(entry["name"], url, "found")
            return PlatformResult(entry["name"], url, "unknown", f"HTTP {result.status_code}")

    except Exception as exc:  # last-resort guard: one bad site must not kill the scan
        log.exception("Unexpected error checking %s for username %s", entry["name"], username)
        return PlatformResult(entry["name"], url, "unknown", f"error: {exc}")

    return PlatformResult(entry["name"], url, "unknown", "unhandled mode")


def run() -> None:
    clear()
    banner("USERNAME INVESTIGATION")
    print("Checks public profile URLs across major platforms.\n"
          "Uses only unauthenticated, publicly reachable pages.\n")

    username = prompt("Enter username to investigate")
    if not username:
        warn("No username entered. Returning to menu.")
        pause()
        return

    if not USERNAME_RE.match(username):
        warn("Username contains characters some platforms won't accept -- continuing anyway.")

    section(f"Scanning {len(PLATFORMS)} platforms for '{username}'")
    log.info("Username investigation started for '%s'", username)

    results: List[PlatformResult] = []
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_check_platform, entry, username): entry for entry in PLATFORMS}
            for future in as_completed(futures):
                res = future.result()
                results.append(res)
                if res.status == "found":
                    ok(f"{res.platform:28} {res.url}")
                elif res.status == "not_found":
                    print(f"    {res.platform:28} not found")
                else:
                    warn(f"{res.platform:28} inconclusive ({res.detail})")
    except Exception:
        log.exception("Username investigation crashed unexpectedly")
        err("An unexpected error interrupted the scan. Partial results shown above.")

    found = sum(1 for r in results if r.status == "found")
    not_found = sum(1 for r in results if r.status == "not_found")
    unknown = sum(1 for r in results if r.status == "unknown")

    section("Summary")
    info(f"Found: {found}  |  Not found: {not_found}  |  Inconclusive: {unknown}")
    log.info("Username investigation complete for '%s': found=%d not_found=%d unknown=%d",
              username, found, not_found, unknown)

    pause()
