"""Parquet-based local cache for time series data."""
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from config.settings import settings

logger = logging.getLogger(__name__)


def _cache_path(name: str) -> Path:
    """Return the parquet file path for a given cache key."""
    safe = name.replace("^", "").replace("$", "").replace("/", "_")
    return settings.cache_dir / f"{safe}.parquet"


def cache_exists(name: str) -> bool:
    return _cache_path(name).exists()


def cache_age_hours(name: str) -> float:
    """Return age of cache file in hours, or inf if not cached."""
    path = _cache_path(name)
    if not path.exists():
        return float("inf")
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.now() - mtime).total_seconds() / 3600


def is_stale(name: str, max_age_hours: int | None = None) -> bool:
    """Return True if cache is missing or older than max_age_hours."""
    age = max_age_hours or settings.cache_max_age_hours
    return cache_age_hours(name) > age


def load(name: str) -> pd.DataFrame:
    """Load a DataFrame from cache. Returns empty DataFrame if not found."""
    path = _cache_path(name)
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as exc:
        logger.error("Failed to load cache %s: %s", name, exc)
        return pd.DataFrame()


def save(name: str, df: pd.DataFrame) -> None:
    """Save a DataFrame to cache."""
    if df.empty:
        logger.warning("Not caching empty DataFrame for %s", name)
        return
    path = _cache_path(name)
    try:
        df.to_parquet(path, engine="pyarrow", compression="snappy")
        logger.debug("Cached %s (%d rows)", name, len(df))
    except Exception as exc:
        logger.error("Failed to save cache %s: %s", name, exc)


def update(name: str, new_df: pd.DataFrame) -> pd.DataFrame:
    """Merge new data with existing cache and save. Returns merged DataFrame."""
    existing = load(name)
    if existing.empty:
        combined = new_df
    else:
        combined = pd.concat([existing, new_df])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()
    save(name, combined)
    return combined


def invalidate(name: str) -> None:
    """Delete a cache file."""
    path = _cache_path(name)
    if path.exists():
        path.unlink()
        logger.info("Invalidated cache: %s", name)
