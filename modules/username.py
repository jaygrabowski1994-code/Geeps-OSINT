"""
Username Investigation module.

Checks whether a given username appears to be registered on a curated
list of major public platforms, using only publicly reachable profile
URLs (no login, no scraping behind auth walls, no ToS-violating bulk
scraping). Designed to degrade gracefully: a network hiccup on one
site never aborts the rest of the scan.

The built-in list below is intentionally a hand-curated, maintainable
set (~50 major platforms) rather than an attempt to hand-roll hundreds
of URL templates, which would be both error-prone and a maintenance
burden. For genuinely broad coverage (400+ sites), this module offers
to hand off to Sherlock (https://github.com/sherlock-project/sherlock)
if it's installed on the system -- see core/sherlock_runner.py.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List

from core import sherlock_runner
from core.logger import get_logger
from core.netutils import head, get
from core.plugins import PluginMeta
from core.ui import banner, clear, confirm, err, info, ok, pause, prompt, section, warn

log = get_logger("username")

MODULE_META = PluginMeta(
    key="1",
    name="Username Investigation",
    description="Check a username's presence across major public platforms, with optional Sherlock integration",
    order=10,
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,39}$")

# Each entry: platform name, profile URL template, method, and how to
# interpret the response. "head" (does the URL 200/404) is the most
# robust check and preferred wherever a platform supports it cleanly;
# "get_json" and "get_text_notfound" exist for platforms that always
# return HTTP 200 and need a body-content check instead.
PLATFORMS: List[dict] = [
    # -- Developer / tech --
    {"name": "GitHub", "url": "https://github.com/{u}", "mode": "head"},
    {"name": "GitLab", "url": "https://gitlab.com/{u}", "mode": "head"},
    {"name": "Bitbucket", "url": "https://bitbucket.org/{u}/", "mode": "head"},
    {"name": "SourceForge", "url": "https://sourceforge.net/u/{u}/profile/", "mode": "head"},
    {"name": "Docker Hub", "url": "https://hub.docker.com/u/{u}", "mode": "head"},
    {"name": "npm", "url": "https://www.npmjs.com/~{u}", "mode": "head"},
    {"name": "PyPI", "url": "https://pypi.org/user/{u}/", "mode": "head"},
    {"name": "Crates.io", "url": "https://crates.io/users/{u}", "mode": "head"},
    {"name": "Kaggle", "url": "https://www.kaggle.com/{u}", "mode": "head"},
    {"name": "Replit", "url": "https://replit.com/@{u}", "mode": "head"},
    {"name": "CodePen", "url": "https://codepen.io/{u}", "mode": "head"},
    {"name": "HackerOne", "url": "https://hackerone.com/{u}", "mode": "head"},
    {"name": "Keybase", "url": "https://keybase.io/{u}", "mode": "head"},
    {"name": "Product Hunt", "url": "https://www.producthunt.com/@{u}", "mode": "head"},
    {"name": "Dev.to", "url": "https://dev.to/{u}", "mode": "head"},
    {"name": "HackerNews", "url": "https://news.ycombinator.com/user?id={u}", "mode": "get_text_notfound",
     "notfound_marker": "No such user"},
    # -- Social / general --
    {"name": "X (Twitter)", "url": "https://x.com/{u}", "mode": "head"},
    {"name": "Instagram", "url": "https://www.instagram.com/{u}/", "mode": "head"},
    {"name": "Facebook", "url": "https://www.facebook.com/{u}", "mode": "head"},
    {"name": "LinkedIn", "url": "https://www.linkedin.com/in/{u}", "mode": "head"},
    {"name": "Threads", "url": "https://www.threads.net/@{u}", "mode": "head"},
    {"name": "TikTok", "url": "https://www.tiktok.com/@{u}", "mode": "head"},
    {"name": "Pinterest", "url": "https://www.pinterest.com/{u}/", "mode": "head"},
    {"name": "Reddit", "url": "https://www.reddit.com/user/{u}/about.json", "mode": "get_json"},
    {"name": "Telegram", "url": "https://t.me/{u}", "mode": "head"},
    {"name": "Medium", "url": "https://medium.com/@{u}", "mode": "head"},
    {"name": "Tumblr", "url": "https://{u}.tumblr.com", "mode": "head"},
    {"name": "Quora", "url": "https://www.quora.com/profile/{u}", "mode": "head"},
    {"name": "About.me", "url": "https://about.me/{u}", "mode": "head"},
    {"name": "Linktree", "url": "https://linktr.ee/{u}", "mode": "head"},
    # -- Gaming / streaming --
    {"name": "Twitch", "url": "https://www.twitch.tv/{u}", "mode": "head"},
    {"name": "Steam", "url": "https://steamcommunity.com/id/{u}", "mode": "get_text_notfound",
     "notfound_marker": "The specified profile could not be found"},
    {"name": "Chess.com", "url": "https://www.chess.com/member/{u}", "mode": "head"},
    {"name": "Lichess", "url": "https://lichess.org/@/{u}", "mode": "head"},
    {"name": "Itch.io", "url": "https://{u}.itch.io", "mode": "head"},
    # -- Creative / media --
    {"name": "YouTube (@handle)", "url": "https://www.youtube.com/@{u}", "mode": "head"},
    {"name": "Vimeo", "url": "https://vimeo.com/{u}", "mode": "head"},
    {"name": "SoundCloud", "url": "https://soundcloud.com/{u}", "mode": "head"},
    {"name": "Behance", "url": "https://www.behance.net/{u}", "mode": "head"},
    {"name": "Dribbble", "url": "https://dribbble.com/{u}", "mode": "head"},
    {"name": "DeviantArt", "url": "https://www.deviantart.com/{u}", "mode": "head"},
    {"name": "Flickr", "url": "https://www.flickr.com/people/{u}", "mode": "head"},
    {"name": "Letterboxd", "url": "https://letterboxd.com/{u}/", "mode": "head"},
    {"name": "Last.fm", "url": "https://www.last.fm/user/{u}", "mode": "head"},
    {"name": "Discogs", "url": "https://www.discogs.com/user/{u}", "mode": "head"},
    {"name": "Genius", "url": "https://genius.com/{u}", "mode": "head"},
    # -- Blogs --
    {"name": "Blogspot", "url": "https://{u}.blogspot.com", "mode": "head"},
    {"name": "WordPress.com", "url": "https://{u}.wordpress.com", "mode": "head"},
    # -- Commerce / monetization --
    {"name": "Etsy shop", "url": "https://www.etsy.com/shop/{u}", "mode": "head"},
    {"name": "eBay", "url": "https://www.ebay.com/usr/{u}", "mode": "head"},
    {"name": "Fiverr", "url": "https://www.fiverr.com/{u}", "mode": "head"},
    {"name": "Gumroad", "url": "https://{u}.gumroad.com", "mode": "head"},
    {"name": "Patreon", "url": "https://www.patreon.com/{u}", "mode": "head"},
    {"name": "Ko-fi", "url": "https://ko-fi.com/{u}", "mode": "head"},
    {"name": "PayPal.me", "url": "https://paypal.me/{u}", "mode": "head"},
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


def _run_sherlock(username: str) -> None:
    section("Sherlock (400+ sites)")
    info("Running Sherlock -- this can take a minute or two...")
    success, output = sherlock_runner.run(username)
    if not success:
        warn(output)
        return
    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        info("Sherlock found no additional matches.")
        return
    for line in lines:
        ok(line)


def run() -> None:
    clear()
    banner("USERNAME INVESTIGATION")
    print(f"Checks public profile URLs across {len(PLATFORMS)} major platforms.\n"
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
        with ThreadPoolExecutor(max_workers=16) as pool:
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

    if sherlock_runner.available():
        if confirm("Sherlock is installed -- also run it for coverage across 400+ sites?", default=False):
            try:
                _run_sherlock(username)
            except Exception:
                log.exception("Unexpected error running Sherlock")
                err("Unexpected error running Sherlock -- see logs for details.")
    else:
        info(f"Tip: install Sherlock for 400+ site coverage. {sherlock_runner.INSTALL_HINT}")

    pause()
