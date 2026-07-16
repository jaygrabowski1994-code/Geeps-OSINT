"""
Health Check module.

Gives a single-glance status of everything the toolkit depends on:
Python version, required packages, config file validity, log
writability, and basic outbound network/DNS connectivity. Offers to
auto-install any missing required dependency.
"""

from __future__ import annotations

import platform
import socket
import sys

from core.config import CONFIG_PATH, LOG_DIR, ConfigError, load_config
from core.dependencies import check_dependencies, dependency_report
from core.logger import get_logger
from core.plugins import PluginMeta
from core.ui import banner, clear, err, info, ok, pause, section, warn

log = get_logger("health")

MODULE_META = PluginMeta(
    key="6",
    name="Health Check",
    description="Verify Python version, dependencies, config, logging, network, and installed plugins",
    order=90,
)

MIN_PYTHON = (3, 8)


def _check_python_version() -> None:
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    if version[:2] >= MIN_PYTHON:
        ok(f"Python {version_str} (minimum {'.'.join(map(str, MIN_PYTHON))} required)")
    else:
        err(f"Python {version_str} is below the minimum supported version "
            f"{'.'.join(map(str, MIN_PYTHON))}.")


def _check_config() -> None:
    try:
        load_config()
        ok(f"Config loaded OK: {CONFIG_PATH}")
    except ConfigError as exc:
        err(str(exc))


def _check_logging() -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        test_file = LOG_DIR / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        ok(f"Log directory writable: {LOG_DIR}")
    except OSError as exc:
        err(f"Cannot write to log directory {LOG_DIR}: {exc}")


def _check_network() -> None:
    try:
        socket.setdefaulttimeout(5)
        socket.gethostbyname("one.one.one.one")
        ok("DNS resolution works.")
    except OSError as exc:
        err(f"DNS resolution failed: {exc}")
        warn("Most modules need internet access -- check your connection.")
        return

    try:
        with socket.create_connection(("one.one.one.one", 443), timeout=5):
            pass
        ok("Outbound HTTPS (port 443) connectivity works.")
    except OSError as exc:
        err(f"Could not establish outbound HTTPS connection: {exc}")
        warn("You may be behind a firewall/proxy blocking outbound HTTPS.")


def _check_plugins() -> None:
    from core.plugins import discover_plugins

    plugins = discover_plugins()
    working = [p for p in plugins if p.load_error is None]
    broken = [p for p in plugins if p.load_error is not None]

    for plugin in working:
        ok(f"[{plugin.meta.key}] {plugin.meta.name}  ({plugin.module_name}.py)")

    for plugin in broken:
        err(f"{plugin.module_name}.py failed to load: {plugin.load_error}")

    if broken:
        warn(f"{len(broken)} plugin(s) will not appear in the menu until fixed.")
    else:
        ok(f"All {len(working)} plugins loaded cleanly.")


def run() -> None:
    clear()
    banner("HEALTH CHECK")
    print(f"Platform: {platform.system()} {platform.release()}  |  Python: {sys.version.split()[0]}\n")

    section("Python version")
    _check_python_version()

    section("Dependencies")
    print(dependency_report())
    print()
    try:
        deps_ok = check_dependencies(auto_install=True)
        if deps_ok:
            ok("All required dependencies are installed.")
        else:
            err("Some required dependencies are still missing.")
    except Exception:
        log.exception("Unexpected error during dependency check")
        err("Unexpected error while checking dependencies.")

    section("Configuration")
    _check_config()

    section("Logging")
    _check_logging()

    section("Network connectivity")
    _check_network()

    section("Plugins")
    try:
        _check_plugins()
    except Exception:
        log.exception("Unexpected error during plugin discovery")
        err("Unexpected error while discovering plugins.")

    log.info("Health check complete")
    pause()
