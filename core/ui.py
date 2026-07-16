"""Small shared terminal UI helpers so every module looks/behaves consistently."""

from __future__ import annotations

import os

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    _HAS_COLOR = True
except ImportError:  # optional dependency
    _HAS_COLOR = False

    class _NoColor:
        def __getattr__(self, _name):
            return ""

    Fore = _NoColor()
    Style = _NoColor()


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def banner(title: str) -> None:
    width = 60
    print(Fore.CYAN + "=" * width)
    print(Fore.CYAN + title.center(width))
    print(Fore.CYAN + "=" * width + Style.RESET_ALL)


def section(title: str) -> None:
    print(f"\n{Fore.YELLOW}-- {title} --{Style.RESET_ALL}")


def ok(msg: str) -> None:
    print(f"{Fore.GREEN}[+]{Style.RESET_ALL} {msg}")


def warn(msg: str) -> None:
    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {msg}")


def err(msg: str) -> None:
    print(f"{Fore.RED}[x]{Style.RESET_ALL} {msg}")


def info(msg: str) -> None:
    print(f"{Fore.CYAN}[*]{Style.RESET_ALL} {msg}")


def pause() -> None:
    input("\nPress Enter to return to the menu...")


def prompt(msg: str, required: bool = True) -> str:
    """Prompt for input, re-asking if required and left blank. Ctrl+C returns ''."""
    while True:
        try:
            value = input(f"{msg}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return ""
        if value or not required:
            return value
        warn("This field is required.")
