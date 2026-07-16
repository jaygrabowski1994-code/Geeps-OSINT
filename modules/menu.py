"""Main interactive menu for Geeps OSINT Hub -- built dynamically from installed plugins."""

from __future__ import annotations

from core.plugins import get_menu_plugins
from core.ui import Fore, Style, banner, clear


def main_menu() -> str:
    """Render the main menu (auto-built from modules/ plugins) and return the user's choice."""
    clear()
    banner("GEEPS OSINT HUB")
    print(f"{Fore.CYAN}A modular, public-source OSINT toolkit{Style.RESET_ALL}\n")

    plugins = get_menu_plugins()
    for plugin in plugins:
        print(f"  [{plugin.meta.key}] {plugin.meta.name}")
    print("  [0] Exit")

    print()
    choice = input("Select an option: ").strip()
    return choice
