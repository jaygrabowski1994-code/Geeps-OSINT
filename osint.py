#!/usr/bin/env python3
"""
Geeps OSINT Hub -- a modular, publicly-sourced OSINT investigation toolkit.

Entry point: wires the interactive menu to each investigation module,
performs a startup dependency check, and ensures unhandled errors in
any module are logged and reported without crashing the whole app.
"""

from __future__ import annotations

import sys

from core.config import ensure_config_exists
from core.dependencies import check_dependencies
from core.logger import get_logger
from core.ui import clear, err, pause

log = get_logger("main")


def _dispatch(choice: str) -> bool:
    """Run the module for `choice`. Returns False if the app should exit."""
    if choice == "0":
        print("\nThanks for using Geeps OSINT Hub.")
        return False

    # Imported lazily so a broken/missing dependency in one module
    # (e.g. phonenumbers not installed) can't prevent the whole app,
    # including Health Check, from starting up.
    try:
        if choice == "1":
            from modules import username
            username.run()
        elif choice == "2":
            from modules import email_lookup
            email_lookup.run()
        elif choice == "3":
            from modules import phone
            phone.run()
        elif choice == "4":
            from modules import domain
            domain.run()
        elif choice == "5":
            from modules import employment
            employment.run()
        elif choice == "6":
            from modules import health
            health.run()
        else:
            print("\nInvalid option.")
            pause()
    except KeyboardInterrupt:
        print("\nInterrupted -- returning to menu.")
    except Exception:
        log.exception("Unhandled error in module for menu choice '%s'", choice)
        err("Something went wrong in that module. Details were written to logs/geeps-osint.log.")
        pause()

    return True


def main() -> int:
    ensure_config_exists()

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
