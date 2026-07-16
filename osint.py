#!/usr/bin/env python3
"""
Geeps OSINT Hub -- a modular, publicly-sourced OSINT investigation toolkit.

Entry point: wires the interactive menu to whichever investigation
plugins are found under modules/ (see core/plugins.py), performs a
startup dependency check, and ensures unhandled errors in any single
plugin are logged and reported without crashing the whole app.

Adding a new investigation module is a one-file operation: drop a
modules/<name>.py file exposing MODULE_META and run(), and it appears
in the menu automatically -- no changes to this file or menu.py needed.
"""

from __future__ import annotations

import sys

from core.config import ensure_config_exists
from core.dependencies import check_dependencies
from core.logger import get_logger
from core.plugins import get_broken_plugins, get_menu_plugins
from core import report
from core.ui import clear, confirm, err, info, pause
from core.version import __version__

log = get_logger("main")


def _offer_report_save(session) -> None:
    """After a plugin finishes, offer to save its captured output as a report."""
    if session is None or not session.has_content():
        return
    if not confirm("Save a report of this investigation?", default=False):
        return
    try:
        paths = session.save()
    except OSError as exc:
        log.exception("Failed to save report")
        err(f"Could not save report: {exc}")
        return
    for path in paths:
        info(f"Saved: {path}")
    pause()


def _dispatch(choice: str) -> bool:
    """Run the plugin matching `choice`. Returns False if the app should exit."""
    if choice == "0":
        print("\nThanks for using Geeps OSINT Hub.")
        return False

    plugin = next((p for p in get_menu_plugins() if p.meta.key == choice), None)
    if plugin is None:
        print("\nInvalid option.")
        pause()
        return True

    session = report.start_session(plugin.meta.name)
    try:
        plugin.run()
    except KeyboardInterrupt:
        print("\nInterrupted -- returning to menu.")
    except Exception:
        log.exception("Unhandled error in plugin '%s' (menu choice '%s')", plugin.module_name, choice)
        err("Something went wrong in that module. Details were written to logs/geeps-osint.log.")
        pause()
    finally:
        finished = report.end_session()
        _offer_report_save(finished)

    return True


def _list_modules() -> int:
    """Print every discovered plugin (working and broken) and exit. Used by --list-modules."""
    print(f"Geeps OSINT Hub v{__version__}\n")
    print("Installed modules:\n")
    for plugin in get_menu_plugins():
        print(f"  [{plugin.meta.key}] {plugin.meta.name} ({plugin.module_name}.py)")
        if plugin.meta.description:
            print(f"      {plugin.meta.description}")

    broken = get_broken_plugins()
    if broken:
        print("\nFailed to load:\n")
        for plugin in broken:
            print(f"  {plugin.module_name}.py -- {plugin.load_error}")

    return 0


def main() -> int:
    if "--version" in sys.argv or "-v" in sys.argv:
        print(f"Geeps OSINT Hub v{__version__}")
        return 0

    ensure_config_exists()

    if "--list-modules" in sys.argv:
        return _list_modules()

    print("Starting Geeps OSINT Hub...")
    if not check_dependencies(auto_install=True):
        print("\nCannot start until required dependencies are installed. Exiting.")
        return 1

    from modules.menu import main_menu

    running = True
    while running:
        try:
            choice = main_menu()
        except KeyboardInterrupt:
            clear()
            print("\nThanks for using Geeps OSINT Hub.")
            break
        running = _dispatch(choice)

    return 0


if __name__ == "__main__":
    sys.exit(main())
