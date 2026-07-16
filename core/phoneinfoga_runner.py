"""
PhoneInfoga integration for Phone Investigation.

PhoneInfoga (https://github.com/sundowndev/phoneinfoga) runs several
public-data scanners (carrier/line lookups, OVH VoIP detection, Google
dork link generation for footprint discovery) beyond what this
toolkit's offline libphonenumber-based check covers. Note: the
upstream project describes itself as stable but unmaintained, so
results/behavior may drift over time -- this launcher just shells out
to whatever the user has installed and stays out of the way if it
isn't present.

Same safety pattern as the Sherlock launcher: no shell=True, the
number is passed as its own argv element, never interpolated into a
shell string.
"""

from __future__ import annotations

import subprocess

from core.tools import is_installed, path

INSTALL_HINT = (
    "See install instructions at https://github.com/sundowndev/phoneinfoga "
    "(prebuilt binaries, Docker image, or install script)."
)


def available() -> bool:
    return is_installed("phoneinfoga")


def run(e164_number: str, timeout_seconds: int = 60) -> tuple[bool, str]:
    """
    Run `phoneinfoga scan -n <number>`.

    Returns (success, output). success is False if PhoneInfoga isn't
    installed, the process errored, or it timed out -- output then
    holds a human-readable explanation instead of tool output.
    """
    if not available():
        return False, f"PhoneInfoga is not installed. {INSTALL_HINT}"

    cmd = [path("phoneinfoga"), "scan", "-n", e164_number]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"PhoneInfoga did not finish within {timeout_seconds}s."
    except OSError as exc:
        return False, f"Could not launch PhoneInfoga: {exc}"

    output = (result.stdout or "").strip()
    if not output and result.stderr:
        output = result.stderr.strip()
    return True, output or "(no output)"
