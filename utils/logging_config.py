"""Central logging configuration.

Provides a get_logger(name) helper that configures a root application logger
only once. Subsequent calls reuse the existing configuration. Uses an
environment variable LOG_LEVEL to allow dynamic verbosity control.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

_CONFIGURED = False

def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(level=level, format=fmt)
    _CONFIGURED = True

def get_logger(name: Optional[str] = None) -> logging.Logger:
    _configure_root()
    return logging.getLogger(name or "app")
