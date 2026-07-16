"""
Tool Manager plugin for Geeps OSINT Hub.

Detects which external OSINT tools are installed on this system (read
only -- it never installs or launches anything itself). Two of the
detected tools, Sherlock and PhoneInfoga, are also wired as optional
add-on steps directly inside Username Investigation and Phone
Investigation respectively, so you don't need to come back here to use
them -- this page is just for an at-a-glance inventory.
"""

from __future__ import annotations

import platform

from core import tools
from core.plugins import PluginMeta
from core.ui import banner, clear, info, ok, pause, section, warn

MODULE_META = PluginMeta(
    key="9",
    name="Tool Manager",
    description="Detect installed external OSINT tools (Sherlock, PhoneInfoga, etc.)",
    order=90,
)

# (display name, core.tools key, note)
DISPLAY_TOOLS = [
    ("Python 3", "python3", ""),
    ("Git", "git", ""),
    ("GitHub CLI", "gh", ""),
    ("Sherlock", "sherlock", "used automatically by Username Investigation if installed"),
    ("PhoneInfoga", "phoneinfoga", "used automatically by Phone Investigation if installed"),
    ("Holehe", "holehe", "email-to-registered-accounts checker"),
    ("Maigret", "maigret", "used automatically by Username Investigation if installed"),
    ("theHarvester", "theHarvester", "email/subdomain/name harvesting"),
    ("Amass", "amass", "subdomain enumeration"),
    ("Subfinder", "subfinder", "subdomain enumeration"),
    ("ExifTool", "exiftool", "media metadata extraction"),
]


def run() -> None:
    clear()
    banner("TOOL MANAGER")
    info(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")

    section("External tools")
    installed = 0
    for name, key, note in DISPLAY_TOOLS:
        found = tools.path(key)
        if found:
            installed += 1
            ok(f"{name:<14} {tools.version(key)}")
            print(f"      {found}")
        else:
            warn(f"{name:<14} not found on PATH")
        if note:
            print(f"      ({note})")

    section("Summary")
    info(f"{installed} of {len(DISPLAY_TOOLS)} tools detected.")
    pause()
