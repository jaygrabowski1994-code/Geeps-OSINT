"""
Configuration management for Geeps OSINT Hub.

Loads settings from config/config.json (created automatically from
config/config.example.json on first run if missing). Supports optional
API keys for enrichment services -- every module degrades gracefully
and keeps working with zero keys configured.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "config.json"
CONFIG_EXAMPLE_PATH = CONFIG_DIR / "config.example.json"
LOG_DIR = BASE_DIR / "logs"

DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": "Geeps OSINT Hub",
        "log_level": "INFO",
        "request_timeout_seconds": 8,
        "max_retries": 2,
    },
    "api_keys": {
        "hibp_api_key": "",
        "hunter_io_api_key": "",
        "numverify_api_key": "",
    },
    "network": {
        "user_agent": "Geeps-OSINT-Hub/2.0 (+https://github.com/)",
        "verify_tls": True,
    },
}


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or is invalid."""


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge override into base, recursively, without mutating either input."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def ensure_config_exists() -> None:
    """Create config directory / files on first run if they don't exist yet."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_EXAMPLE_PATH.exists():
        CONFIG_EXAMPLE_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n")

    if not CONFIG_PATH.exists():
        shutil.copyfile(CONFIG_EXAMPLE_PATH, CONFIG_PATH)


def load_config() -> Dict[str, Any]:
    """Load config.json, merged over defaults so missing keys never crash callers."""
    ensure_config_exists()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            user_config = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"config/config.json is not valid JSON: {exc}. "
            "Delete or fix the file and restart, or copy config.example.json over it."
        ) from exc
    except OSError as exc:
        raise ConfigError(f"Could not read config/config.json: {exc}") from exc

    return _deep_merge(DEFAULT_CONFIG, user_config)


def get(path: str, default: Any = None) -> Any:
    """Fetch a dotted config path, e.g. get('api_keys.hibp_api_key')."""
    cfg = load_config()
    node: Any = cfg
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node


def env_override(config_value: str, env_var: str) -> str:
    """Environment variable takes priority over a config file value, if set."""
    return os.environ.get(env_var, config_value) or ""
