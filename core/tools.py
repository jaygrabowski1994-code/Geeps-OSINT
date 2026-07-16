
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

    for arg in ("--version", "-V", "version"):
        try:
            r = subprocess.run(
                [exe, arg],
                capture_output=True,
                text=True,
                timeout=3,
            )
            out = (r.stdout or r.stderr).splitlines()
            if out:
                return out[0].strip()
        except Exception:
            pass

    return "Unknown version"
