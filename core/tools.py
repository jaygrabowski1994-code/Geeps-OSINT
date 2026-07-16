
"""
Shared tool detection helpers.
"""

from __future__ import annotations

import shutil
import subprocess

TOOLS = {
    "python": "python",
    "python3": "python3",
    "git": "git",
    "gh": "gh",
    "sherlock": "sherlock",
    "phoneinfoga": "phoneinfoga",
    "holehe": "holehe",
    "maigret": "maigret",
    "theHarvester": "theHarvester",
    "amass": "amass",
    "subfinder": "subfinder",
    "nmap": "nmap",
    "exiftool": "exiftool",
    "go": "go",
    "rustc": "rustc",
}

# Tools whose version flag doesn't match the common --version/-V/version
# convention tried below. exiftool in particular doesn't recognize
# --version at all and instead prints its own manual page (starting
# with "NAME"), which would otherwise get mistaken for real output.
_VERSION_ARG_OVERRIDES = {
    "exiftool": ["-ver"],
}

def is_installed(name: str) -> bool:
    exe = TOOLS.get(name, name)
    return shutil.which(exe) is not None

def path(name: str) -> str | None:
    exe = TOOLS.get(name, name)
    return shutil.which(exe)

def version(name: str) -> str:
    exe = TOOLS.get(name, name)
    if shutil.which(exe) is None:
        return "Not installed"

    args_to_try = _VERSION_ARG_OVERRIDES.get(name, ["--version", "-V", "version"])
    fallback = ""
    for arg in args_to_try:
        try:
            r = subprocess.run(
                [exe, arg],
                capture_output=True,
                text=True,
                timeout=3,
            )
            lines = (r.stdout or r.stderr).splitlines()
            if not lines:
                continue
            first_line = lines[0].strip()
            # Only trust output from an attempt that actually succeeded --
            # a nonzero exit (e.g. an unrecognized flag) often still
            # prints *something* to stderr, which isn't the version.
            if r.returncode == 0 and first_line:
                return first_line
            if first_line and not fallback:
                fallback = first_line
        except Exception:
            pass

    return fallback or "Unknown version"
