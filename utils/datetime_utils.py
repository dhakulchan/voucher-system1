from __future__ import annotations

"""Datetime utilities.

Provides a single place to obtain timezone-aware UTC datetimes so we avoid
scattered uses of datetime.utcnow() (naive) across the codebase which can
produce deprecation warnings in some frameworks and subtle bugs when mixed
with aware datetimes.
"""

from datetime import datetime, timezone, timedelta

def utc_now() -> datetime:
    """Return an aware UTC datetime (alias for datetime.now(timezone.utc))."""
    return datetime.now(timezone.utc)

def naive_utc_now() -> datetime:
    """Return a naive UTC datetime (wrapper for datetime.utcnow) for legacy DB columns.

    Prefer using utc_now() for new code; only use this where SQLAlchemy models
    still expect naive datetimes (no tzinfo) to avoid migration complexity.
    """
    return datetime.utcnow()

def utc_ts() -> int:
    """Return current UTC timestamp as int seconds."""
    return int(utc_now().timestamp())

def in_utc(dt: datetime) -> datetime:
    """Force a datetime into UTC (assumes naive datetimes are UTC already)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

__all__ = ["utc_now", "naive_utc_now", "utc_ts", "in_utc", "timezone", "timedelta"]
