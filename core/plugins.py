"""
Plugin registry for Geeps OSINT Hub.

Any file dropped into modules/ becomes a menu option automatically, as
long as it exposes a MODULE_META object and a run() function -- no
editing of menu.py or osint.py required. This is what makes "adding a
new module" a one-file operation instead of a multi-file wiring job.

Expected contract for a plugin module:

    from core.plugins import PluginMeta

    MODULE_META = PluginMeta(
        key="7",                        # menu key; "0" is reserved for Exit
        name="My New Module",
        description="One-line summary shown in the menu / --list-modules",
        order=70,                       # sort position in the menu (lower = higher)
    )

    def run() -> None:
        ...

Convention that keeps discovery safe: modules must only do lightweight
work at import time (defining functions/constants). Anything that
needs a third-party package (requests, dnspython, phonenumbers, ...)
must import it *inside* run() or a helper function, not at module
scope. That way a missing dependency in one plugin surfaces as a clean
"failed to load" line for that single menu entry, instead of crashing
discovery for every other plugin.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import modules as modules_pkg
from core.logger import get_logger

log = get_logger("plugins")

# Modules that exist in the package but are NOT selectable investigation
# plugins (shared infra, not a menu entry).
_NON_PLUGIN_MODULES = {"menu", "plugins"}

RESERVED_KEYS = {"0"}  # "0" is always Exit, no plugin may claim it


@dataclass
class PluginMeta:
    key: str
    name: str
    description: str = ""
    order: int = 100


@dataclass
class Plugin:
    meta: PluginMeta
    module_name: str
    run: Optional[Callable[[], None]] = None
    load_error: Optional[str] = None


def _iter_module_names() -> List[str]:
    names = []
    for _finder, name, is_pkg in pkgutil.iter_modules(modules_pkg.__path__):
        if is_pkg or name in _NON_PLUGIN_MODULES or name.startswith("_"):
            continue
        names.append(name)
    return names


def load_plugin(module_name: str) -> Optional[Plugin]:
    """
    Import a single plugin module and return its Plugin wrapper.

    Never raises. If the module fails to import (e.g. a syntax error,
    or a top-level import of a package that isn't installed -- which
    plugins shouldn't do, see module docstring), a Plugin with
    load_error set is returned so the caller can show one clean line
    instead of crashing the whole menu.
    """
    full_name = f"modules.{module_name}"
    try:
        mod = importlib.import_module(full_name)
    except Exception as exc:  # missing dependency, syntax error, etc.
        log.warning("Plugin '%s' failed to import: %s", module_name, exc)
        return Plugin(
            meta=PluginMeta(key=f"!{module_name}", name=module_name,
                             description="(failed to load)", order=999),
            module_name=module_name,
            load_error=str(exc),
        )

    meta = getattr(mod, "MODULE_META", None)
    run_fn = getattr(mod, "run", None)

    if meta is None or run_fn is None:
        log.debug("Module '%s' has no MODULE_META/run() -- not a plugin, skipping.", module_name)
        return None

    if meta.key in RESERVED_KEYS:
        log.error("Plugin '%s' uses reserved menu key '%s' -- skipping.", module_name, meta.key)
        return Plugin(
            meta=PluginMeta(key=f"!{module_name}", name=meta.name,
                             description="(reserved menu key, skipped)", order=999),
            module_name=module_name,
            load_error=f"menu key '{meta.key}' is reserved for Exit",
        )

    return Plugin(meta=meta, module_name=module_name, run=run_fn)


def discover_plugins() -> List[Plugin]:
    """Import every module under modules/ and return the valid plugins, sorted for menu display."""
    plugins: List[Plugin] = []
    by_key: Dict[str, List[Plugin]] = {}

    for name in _iter_module_names():
        plugin = load_plugin(name)
        if plugin is None:
            continue
        plugins.append(plugin)
        if plugin.load_error is None:
            by_key.setdefault(plugin.meta.key, []).append(plugin)

    # A key collision is a config error, not a "first one wins" situation --
    # silently picking a winner based on filesystem iteration order could
    # make a previously-working module vanish from the menu with no clear
    # signal why. Instead, disable every plugin sharing the key and report
    # the conflict on each, so it's obvious in Health Check and impossible
    # to miss.
    for key, owners in by_key.items():
        if len(owners) <= 1:
            continue
        names = ", ".join(p.module_name for p in owners)
        log.error("Menu key '%s' claimed by multiple plugins (%s) -- disabling all of them "
                   "until the conflict is resolved.", key, names)
        for plugin in owners:
            plugin.load_error = f"menu key '{key}' conflicts with: {names}"
            plugin.meta = PluginMeta(key=f"!{plugin.module_name}", name=plugin.meta.name,
                                      description="(menu key conflict, skipped)", order=999)

    return sorted(plugins, key=lambda p: (p.meta.order, p.meta.name))


def get_menu_plugins() -> List[Plugin]:
    """Plugins that loaded successfully and are safe to show as a working menu entry."""
    return [p for p in discover_plugins() if p.load_error is None]


def get_broken_plugins() -> List[Plugin]:
    """Plugins that failed to load -- shown in Health Check, not the main menu."""
    return [p for p in discover_plugins() if p.load_error is not None]
