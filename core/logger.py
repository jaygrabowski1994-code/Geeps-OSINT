"""
Centralized logging for Geeps OSINT Hub.

Writes rotating log files to logs/geeps-osint.log and mirrors warnings/errors
to the console, without cluttering the interactive menu with INFO spam.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from core.config import LOG_DIR, get as config_get

_LOGGER_NAME = "geeps_osint"
_configured = False


def setup_logging() -> logging.Logger:
    """Idempotently configure and return the shared application logger."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)

    if _configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_level_name = str(config_get("app.log_level", "INFO")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(lineno)d | %(message)s"
    )
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")

    file_handler = RotatingFileHandler(
        LOG_DIR / "geeps-osint.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.setLevel(min(log_level, logging.DEBUG))
    _configured = True
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a child logger under the shared app logger, configuring it if needed."""
    setup_logging()
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)
