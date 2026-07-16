"""
Sherlock integration for Username Investigation.

Sherlock (https://github.com/sherlock-project/sherlock) checks a
username against 400+ sites -- far more than this toolkit's own
built-in platform list is realistic to hand-maintain. Rather than
duplicate that work, this module launches the user's own Sherlock
install as a subprocess if present, and stays out of the way (with a
clear "how to install" pointer) if it isn't. Nothing is bundled or
vendored here.

Never runs with shell=True and never interpolates the username into a
shell string -- it's passed as a separate argv element to subprocess,
so shell metacharacters in a username can't do anything unexpected.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import List

from core.tools import is_installed, path

INSTALL_HINT = (
    "Install with: pipx install sherlock-project  (or: pip install sherlock-project)"
)

# Sherlock --print-found lines look like:  [+] Instagram: https://instagram.com/user
# (with --no-color there are no escape codes to strip). Maigret's plain
# output is similar: [+] Instagram: https://instagram.com/user
_FOUND_RE = re.compile(r"^\s*\[\+\]\s*(?P<site>[^:]+):\s*(?P<url>https?://\S+)\s*$")


@dataclass
class FoundAccount:
    site: str
    url: str


def parse_found(output: str) -> List[FoundAccount]:
    """
    Extract (site, url) pairs from Sherlock/Maigret '[+] Site: url' output.

    Lines that don't match the found-account pattern (progress text,
    banners, summaries) are ignored, so this is safe to run over raw
    stdout. Deduplicated, preserving first-seen order.
    """
    seen = set()
    results: List[FoundAccount] = []
    for line in output.splitlines():
        m = _FOUND_RE.match(line)
        if not m:
            continue
        site = m.group("site").strip()
        url = m.group("url").strip()
        key = (site.lower(), url.lower())
        if key in seen:
            continue
        seen.add(key)
        results.append(FoundAccount(site=site, url=url))
    return results


def available() -> bool:
    return is_installed("sherlock")


def run(username: str, timeout_seconds: int = 240) -> tuple[bool, str]:
    """
    Run `sherlock --print-found --no-color --timeout 30 <username>`.

    Returns (success, output). success is False if Sherlock isn't
    installed, the process errored, or it timed out -- output then
    holds a human-readable explanation instead of tool output.
    """
    if not available():
        return False, f"Sherlock is not installed. {INSTALL_HINT}"

    cmd = [path("sherlock"), "--print-found", "--no-color", "--timeout", "30", username]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"Sherlock did not finish within {timeout_seconds}s (network may be slow)."
    except OSError as exc:
        return False, f"Could not launch Sherlock: {exc}"

    output = (result.stdout or "").strip()
    if not output and result.stderr:
        output = result.stderr.strip()
    return True, output or "(no output)"
