
"""
Sherlock integration helpers.

Optional helper used by Username Investigation.
If Sherlock is not installed, callers simply skip it.
"""

from __future__ import annotations

import subprocess

from core.tools import is_installed

def available() -> bool:
    return is_installed("sherlock")

def run(username: str) -> tuple[bool, str]:
    if not available():
        return False, "Sherlock not installed"

    try:
        result = subprocess.run(
            ["sherlock", username, "--print-found"],
            capture_output=True,
            text=True,
            timeout=180,
        )

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        return True, output.strip()

    except Exception as exc:
        return False, str(exc)
