"""Cache manager: orchestrates staleness checks and refresh logic."""
import logging
from datetime import date

import pandas as pd

from config.settings import settings
from config.symbols import ALL_YFINANCE_SYMBOLS
from data.providers.yfinance_provider import YFinanceProvider
from . import parquet_cache as cache

logger = logging.getLogger(__name__)

_provider = YFinanceProvider()


def get_or_fetch(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Return cached data, fetching from provider if stale or missing.

    Args:
        symbol: Ticker symbol (e.g. "^GSPC")
        start: Start date string "YYYY-MM-DD" (defaults to settings.data_start_date)
        end: End date string (defaults to today)
        force_refresh: Bypass cache staleness check
    """
    start = start or settings.data_start_date
    end = end or date.today().isoformat()

    if not force_refresh and not cache.is_stale(symbol):
        cached = cache.load(symbol)
        if not cached.empty:
            return cached

    logger.info("Fetching fresh data for %s", symbol)
    df = _provider.fetch(symbol, start, end)
    if not df.empty:
        cache.update(symbol, df)
    return df


def refresh_all(force: bool = False) -> dict[str, bool]:
    """Refresh all standard symbols. Returns {symbol: success}."""
    results = {}
    for sym in ALL_YFINANCE_SYMBOLS:
        try:
            df = get_or_fetch(sym, force_refresh=force)
            results[sym] = not df.empty
        except Exception as exc:
            logger.error("Refresh failed for %s: %s", sym, exc)
            results[sym] = False
    return results


def last_updated(symbol: str) -> str:
    """Return human-readable last update time for a symbol."""
    age = cache.cache_age_hours(symbol)
    if age == float("inf"):
        return "Never"
    if age < 1:
        return f"{int(age * 60)} min ago"
    if age < 24:
        return f"{age:.1f} hours ago"
    return f"{age / 24:.1f} days ago"
