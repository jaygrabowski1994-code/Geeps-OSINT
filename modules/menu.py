"""Main interactive menu for Geeps OSINT Hub -- built dynamically from installed plugins."""

from __future__ import annotations

from core.plugins import get_menu_plugins
from core.ui import Fore, Style, banner, clear
from core.version import __version__


def main_menu() -> str:
    """Render the main menu (auto-built from modules/ plugins) and return the user's choice."""
    clear()
    banner("GEEPS OSINT HUB")
    print(f"{Fore.CYAN}A modular, public-source OSINT toolkit{Style.RESET_ALL}  "
          f"{Style.DIM}v{__version__}{Style.RESET_ALL}\n")

    plugins = get_menu_plugins()

    # Right-align the key inside brackets so [1] and [10] line up their names.
    max_key_len = max((len(p.meta.key) for p in plugins), default=1)
    max_key_len = max(max_key_len, 1)

    for plugin in plugins:
        key = plugin.meta.key.rjust(max_key_len)
        print(f"  {Fore.GREEN}[{key}]{Style.RESET_ALL}  {plugin.meta.name}")

    exit_key = "0".rjust(max_key_len)
    print(f"  {Fore.RED}[{exit_key}]{Style.RESET_ALL}  Exit")

    print()
    choice = input(f"{Fore.CYAN}\u25b8{Style.RESET_ALL} Select an option: ").strip()
    return choice
