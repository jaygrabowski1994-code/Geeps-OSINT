"""
Automatic dependency checking for Geeps OSINT Hub.

On startup, verifies every third-party package the toolkit needs is
importable. If something is missing, offers to install it via pip
(using the *same* interpreter that's currently running, so it works
correctly inside venvs, Termux, and system Python alike) instead of
just crashing with an ImportError deep inside a module.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import dataclass
from typing import List

from core.logger import get_logger

log = get_logger("dependencies")

# (import name, pip package name, human description)
REQUIRED_PACKAGES: List["Dependency"] = []


@dataclass
class Dependency:
    import_name: str
    pip_name: str
    purpose: str
    required: bool = True


REQUIRED_PACKAGES = [
    Dependency("requests", "requests", "HTTP requests for all lookup modules"),
    Dependency("dns.resolver", "dnspython", "DNS record lookups (domain/email modules)"),
    Dependency("whois", "python-whois", "WHOIS registration lookups (domain module)"),
    Dependency("phonenumbers", "phonenumbers", "phone number parsing/validation"),
    Dependency("bs4", "beautifulsoup4", "HTML parsing for public page checks"),
    Dependency("colorama", "colorama", "cross-platform colored terminal output", required=False),
]


def _is_importable(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except Exception:  # pragma: no cover - import errors vary by package
        return False


def check_dependencies(auto_install: bool = True) -> bool:
    """
    Verify all required packages are importable.

    If auto_install is True, missing *required* packages are installed
    automatically via `pip install --user`. Optional packages are skipped
    with a warning if missing. Returns True if the app is safe to proceed.
    """
    missing_required: List[Dependency] = []
    missing_optional: List[Dependency] = []

    for dep in REQUIRED_PACKAGES:
        if not _is_importable(dep.import_name):
            (missing_required if dep.required else missing_optional).append(dep)

    if missing_optional:
        names = ", ".join(d.pip_name for d in missing_optional)
        print(f"[!] Optional packages not installed (reduced experience): {names}")
        log.warning("Missing optional dependencies: %s", names)

    if not missing_required:
        return True

    print("\n[!] Missing required dependencies:")
    for dep in missing_required:
        print(f"    - {dep.pip_name}  ({dep.purpose})")

    if not auto_install:
        print("\nInstall them with:")
        print(f"    {sys.executable} -m pip install " + " ".join(d.pip_name for d in missing_required))
        return False

    answer = input("\nInstall missing dependencies now via pip? [Y/n]: ").strip().lower()
    if answer not in ("", "y", "yes"):
        print("Cannot continue without required dependencies.")
        log.error("User declined dependency install; missing: %s",
                   [d.pip_name for d in missing_required])
        return False

    ok = True
    for dep in missing_required:
        print(f"[*] Installing {dep.pip_name} ...")
        if not _pip_install(dep.pip_name):
            print(f"[x] Failed to install {dep.pip_name}. Try manually: "
                  f"{sys.executable} -m pip install {dep.pip_name}")
            log.error("Failed to auto-install %s", dep.pip_name)
            ok = False
        elif not _is_importable(dep.import_name):
            print(f"[x] Installed {dep.pip_name} but it still fails to import.")
            log.error("Post-install import check failed for %s", dep.import_name)
            ok = False
        else:
            print(f"[OK] {dep.pip_name} installed.")
            log.info("Installed dependency %s", dep.pip_name)

    return ok


def _pip_install(pip_name: str) -> bool:
    """Try a normal user install first, then fall back to --break-system-packages
    (needed on some Debian/Ubuntu and Termux setups with PEP 668-protected Python)."""
    attempts = [
        [sys.executable, "-m", "pip", "install", "--user", pip_name],
        [sys.executable, "-m", "pip", "install", "--user", "--break-system-packages", pip_name],
        [sys.executable, "-m", "pip", "install", pip_name],
    ]
    for cmd in attempts:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                return True
            log.debug("pip attempt failed (%s): %s", " ".join(cmd), result.stderr[-500:])
        except (subprocess.SubprocessError, OSError) as exc:
            log.debug("pip attempt raised for %s: %s", pip_name, exc)
    return False


def dependency_report() -> str:
    """Return a human-readable status report of every dependency, for Health Check."""
    lines = []
    for dep in REQUIRED_PACKAGES:
        status = "OK" if _is_importable(dep.import_name) else "MISSING"
        tag = "required" if dep.required else "optional"
        lines.append(f"  [{status:7}] {dep.pip_name:20} ({tag}) - {dep.purpose}")
    return "\n".join(lines)
