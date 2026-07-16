"""Main interactive menu for Geeps OSINT Hub."""

from __future__ import annotations

from core.ui import clear, banner, Fore, Style

MENU_OPTIONS = {
    "1": "Username Investigation",
    "2": "Email Investigation",
    "3": "Phone Investigation",
    "4": "Domain Investigation",
    "5": "Employment Investigation",
    "6": "Health Check",
    "0": "Exit",
}


def main_menu() -> str:
    """Render the main menu and return the user's raw choice string."""
    clear()
    banner("GEEPS OSINT HUB")
    print(f"{Fore.CYAN}A modular, public-source OSINT toolkit{Style.RESET_ALL}\n")

    for key in ("1", "2", "3", "4", "5", "6"):
        print(f"  [{key}] {MENU_OPTIONS[key]}")
    print(f"  [0] {MENU_OPTIONS['0']}")

    print()
    choice = input("Select an option: ").strip()
    return choice
