
"""
Tool Manager plugin for Geeps OSINT Hub.
"""

from __future__ import annotations

import platform
import shutil
import subprocess

from core.plugins import PluginMeta
from core.ui import banner, clear, ok, warn, info, pause, section

MODULE_META = PluginMeta(
    key="7",
    name="Tool Manager",
    description="Detect installed external OSINT tools",
    order=70,
)

TOOLS = [
    ("Python", "python"),
    ("Python3", "python3"),
    ("Git", "git"),
    ("GitHub CLI", "gh"),
    ("Sherlock", "sherlock"),
    ("PhoneInfoga", "phoneinfoga"),
    ("Holehe", "holehe"),
    ("Maigret", "maigret"),
    ("theHarvester", "theHarvester"),
    ("Amass", "amass"),
    ("Subfinder", "subfinder"),
    ("Nmap", "nmap"),
    ("ExifTool", "exiftool"),
    ("Go", "go"),
    ("Rust", "rustc"),
]

def get_version(command: str) -> str:
    for arg in ("--version", "-V", "version"):
        try:
            result = subprocess.run(
                [command, arg],
                capture_output=True,
                text=True,
                timeout=3,
            )
            output = (result.stdout or result.stderr).splitlines()
            if output:
                return output[0].strip()
        except Exception:
            pass
    return "Version unknown"

def run() -> None:
    clear()
    banner("TOOL MANAGER")

    info(f"Platform : {platform.system()} {platform.release()}")
    info(f"Machine  : {platform.machine()}")

    section("Installed tools")

    installed = 0
    missing = 0

    for name, exe in TOOLS:
        path = shutil.which(exe)
        if path:
            installed += 1
            ok(f"{name:<15} {path}")
            print(f"      {get_version(exe)}")
        else:
            missing += 1
            warn(f"{name:<15} Not installed")

    section("Summary")
    print(f"Installed : {installed}")
    print(f"Missing   : {missing}")

    pause()
