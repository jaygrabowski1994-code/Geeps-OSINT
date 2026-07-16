"""
Small shared terminal UI helpers so every module looks/behaves consistently.

Two extra capabilities live here beyond plain print wrappers:

  - capture(): a context manager that redirects ok/warn/err/info/section
    calls made *on the current thread* into a buffer instead of stdout.
    This is what lets modules run several independent checks in parallel
    (ThreadPoolExecutor) without their output interleaving into a mess --
    each thread's lines are collected in order and flushed by the caller
    once that check completes.

  - Every ok/warn/err/info/section/prompt call is also mirrored into
    core.report's active session (if one is running). Modules don't need
    to know or care about this -- it's what makes "generate a report of
    this investigation" work for every module for free, with zero
    per-module code.
"""

from __future__ import annotations

import os
import shutil
import textwrap
import threading

from core import report as _report

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

_local = threading.local()

# Minimum width we'll ever wrap to -- narrower than this and wrapping does
# more harm than good, so we just let the terminal do its own thing.
_MIN_WRAP_WIDTH = 30
# Cap: on a very wide desktop terminal, ultra-long lines are still hard to
# read, but we don't want to force-wrap someone's roomy screen either.
_MAX_WRAP_WIDTH = 100


def _terminal_width() -> int:
    """Best-effort current terminal width, with a sane fallback for pipes/Termux."""
    try:
        cols = shutil.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        cols = 80
    return max(_MIN_WRAP_WIDTH, min(cols, _MAX_WRAP_WIDTH))


def _wrap_message(msg: str, prefix_width: int) -> str:
    """
    Wrap a plain message to the terminal width, indenting continuation
    lines by prefix_width so they line up under the first line's text
    (past the "[+] " tag). Existing newlines in msg are preserved and
    each resulting line wrapped independently.
    """
    width = _terminal_width()
    body_width = max(_MIN_WRAP_WIDTH - prefix_width, width - prefix_width)
    indent = " " * prefix_width

    out_lines = []
    for raw_line in msg.split("\n"):
        if not raw_line:
            out_lines.append("")
            continue
        wrapped = textwrap.wrap(
            raw_line,
            width=body_width,
            break_long_words=True,   # a single 400-char token still has to break
            break_on_hyphens=False,  # don't split domains/URLs on their hyphens
        )
        if not wrapped:
            out_lines.append("")
            continue
        out_lines.append(wrapped[0])
        out_lines.extend(indent + line for line in wrapped[1:])
    return "\n".join(out_lines)


def _emit(line_template: str, level: str, plain_msg: str, tag: str = "") -> None:
    """
    Send a formatted, width-wrapped line to this thread's capture buffer
    or stdout. line_template contains a single {} where the (possibly
    multi-line, indented) message goes; tag is the visible prefix like
    "[+] " used to compute the continuation indent.
    """
    _report.record(level, plain_msg)
    wrapped = _wrap_message(plain_msg, len(tag))
    line = line_template.format(wrapped)
    sink = getattr(_local, "sink", None)
    if sink is not None:
        sink.append(line)
    else:
        print(line)


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def banner(title: str) -> None:
    """A boxed title banner using Unicode box-drawing characters."""
    width = min(_terminal_width(), 60)
    inner = width - 2
    print(Fore.CYAN + "\u256d" + "\u2500" * inner + "\u256e")
    print(Fore.CYAN + "\u2502" + title.center(inner) + "\u2502")
    print(Fore.CYAN + "\u2570" + "\u2500" * inner + "\u256f" + Style.RESET_ALL)


def section(title: str) -> None:
    # Section headers are short; no wrapping needed, and we don't want the
    # leading blank line to get an indent computed for it.
    _report.record("section", title)
    underline = "\u2500" * (len(title) + 2)
    line = "\n{y}\u25b8 {t}{r}\n{y}{u}{r}".format(
        y=Fore.YELLOW, t=title, r=Style.RESET_ALL, u=underline
    )
    sink = getattr(_local, "sink", None)
    if sink is not None:
        sink.append(line)
    else:
        print(line)


def ok(msg: str) -> None:
    _emit(f"{Fore.GREEN}[+]{Style.RESET_ALL} {{}}", "ok", msg, tag="[+] ")


def warn(msg: str) -> None:
    _emit(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {{}}", "warn", msg, tag="[!] ")


def err(msg: str) -> None:
    _emit(f"{Fore.RED}[x]{Style.RESET_ALL} {{}}", "err", msg, tag="[x] ")


def info(msg: str) -> None:
    _emit(f"{Fore.CYAN}[*]{Style.RESET_ALL} {{}}", "info", msg, tag="[*] ")


def pause() -> None:
    input("\nPress Enter to return to the menu...")


class capture:
    """
    Redirect ok/warn/err/info/section output on this thread into a list
    instead of printing immediately. Use around one independent unit of
    work inside a ThreadPoolExecutor so parallel checks don't interleave
    their output; flush the returned list with the caller's own print()
    once the check is done, in whatever order you want them displayed.

        def _check():
            with capture() as buf:
                ok("found something")
            return buf

        future = pool.submit(_check)
        ...
        for line in future.result():
            print(line)
    """

    def __enter__(self) -> list:
        self.buffer: list = []
        self._previous = getattr(_local, "sink", None)
        _local.sink = self.buffer
        return self.buffer

    def __exit__(self, *_exc) -> None:
        _local.sink = self._previous


def prompt(msg: str, required: bool = True) -> str:
    """Prompt for input, re-asking if required and left blank. Ctrl+C returns ''."""
    while True:
        try:
            value = input(f"{msg}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return ""
        if value or not required:
            if value:
                _report.record("target", f"{msg}: {value}")
            return value
        warn("This field is required.")


def confirm(msg: str, default: bool = False) -> bool:
    """Yes/no prompt. Ctrl+C returns the default."""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        value = input(f"{msg} {suffix}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not value:
        return default
    return value in ("y", "yes")


def run_parallel(tasks: "dict[str, callable]", max_workers: int = 4) -> None:
    """
    Run several independent, zero-argument checks concurrently, printing
    each one's section header and output in the order given -- not
    completion order -- so results stay readable even though the
    underlying network calls all happen at once.

    Each task should be self-contained (its own try/except + logging);
    this only adds a last-resort catch so one broken task can't crash
    the others or leave its section silently blank.

        tasks = {
            "DNS records": lambda: _dns_lookup(domain),
            "WHOIS": lambda: _whois_lookup(domain),
        }
        run_parallel(tasks)
    """
    import concurrent.futures

    def _run_one(title, fn):
        with capture() as buf:
            section(title)
            try:
                fn()
            except Exception as exc:  # last-resort: task should normally handle its own errors
                err(f"Unexpected error: {exc}")
        return buf

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {name: pool.submit(_run_one, name, fn) for name, fn in tasks.items()}
        for name in tasks:
            for line in futures[name].result():
                print(line)
