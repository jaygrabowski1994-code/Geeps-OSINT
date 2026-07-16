"""
Maigret integration for Username Investigation.

Maigret (https://github.com/soxoj/maigret) is a Sherlock fork that
checks a username across 3000+ sites and, unlike Sherlock, can extract
extra profile details. Like the Sherlock launcher, this shells out to
the user's own install if present and stays out of the way otherwise;
nothing is bundled here.

Its plain console output uses the same "[+] Site: url" convention as
Sherlock, so core.sherlock_runner.parse_found() parses both.

Same safety pattern as the other launchers: no shell=True, the
username is passed as its own argv element, never interpolated into a
shell string.
"""

from __future__ import annotations

import subprocess

from core.sherlock_runner import parse_found  # shared parser; re-exported for callers
from core.tools import is_installed, path

INSTALL_HINT = "Install with: pip install maigret"

__all__ = ["available", "run", "parse_found", "INSTALL_HINT"]


def available() -> bool:
    return is_installed("maigret")


def run(username: str, timeout_seconds: int = 300) -> tuple[bool, str]:
    """
    Run maigret against a username with a per-site timeout and no
    progress bar (so captured stdout is clean, parseable result lines).

    Returns (success, output). success is False if Maigret isn't
    installed, errored, or timed out -- output then holds a
    human-readable explanation instead of tool output.
    """
    if not available():
        return False, f"Maigret is not installed. {INSTALL_HINT}"

    cmd = [
        path("maigret"), username,
        "--timeout", "30",
        "--no-recursion",       # don't fan out into discovered usernames -- keeps it bounded
        "--no-progressbar",     # progress bar would pollute captured stdout
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"Maigret did not finish within {timeout_seconds}s (network may be slow)."
    except OSError as exc:
        return False, f"Could not launch Maigret: {exc}"

    output = (result.stdout or "").strip()
    if not output and result.stderr:
        output = result.stderr.strip()
    return True, output or "(no output)"
