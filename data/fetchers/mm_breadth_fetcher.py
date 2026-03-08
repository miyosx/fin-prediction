"""MM breadth fetcher with 3-tier priority chain.

Priority:
  1. EODHD API (if key set)
  2. Manual CSV imports (data/manual_imports/*.csv)
  3. Computed from S&P 500 constituents (always available)
"""
import logging
from pathlib import Path

import pandas as pd

from config.settings import settings
from config.symbols import MM_BREADTH_SYMBOLS
from data.providers.eodhd_provider import EODHDProvider
from data.providers.computed_provider import ComputedMMProvider
from data.cache import parquet_cache as cache

logger = logging.getLogger(__name__)

_eodhd = EODHDProvider()
_computed = ComputedMMProvider()

MM_SYMBOLS = list(MM_BREADTH_SYMBOLS.keys())  # ['MMFD','MMTW','MMFI','MMTH']

# CSV column name aliases accepted in manual imports
_CSV_ALIASES = {
    "MMFD": ["MMFD", "mmfd", "pct_above_200", "close", "Close"],
    "MMTW": ["MMTW", "mmtw", "pct_above_20", "close", "Close"],
    "MMFI": ["MMFI", "mmfi", "pct_above_50", "close", "Close"],
    "MMTH": ["MMTH", "mmth", "pct_above_100", "close", "Close"],
}


def _load_manual_csv(symbol: str) -> pd.DataFrame:
    """Try to load a manual CSV for the given symbol from the imports directory."""
    imports_dir = settings.manual_imports_dir
    candidates = list(imports_dir.glob(f"{symbol}*.csv")) + list(imports_dir.glob(f"{symbol.lower()}*.csv"))
    if not candidates:
        return pd.DataFrame()

    path = sorted(candidates)[-1]  # most recent by name
    try:
        df = pd.read_csv(path)
        # Flexible date column detection
        date_col = next((c for c in df.columns if "date" in c.lower()), None)
        if date_col is None:
            logger.warning("No date column in %s", path)
            return pd.DataFrame()
        df["Date"] = pd.to_datetime(df[date_col])
        df = df.set_index("Date")

        # Flexible value column detection
        aliases = _CSV_ALIASES.get(symbol, ["Close", "close"])
        val_col = next((c for c in aliases if c in df.columns), None)
        if val_col is None:
            logger.warning("No value column in %s (tried %s)", path, aliases)
            return pd.DataFrame()

        result = df[[val_col]].rename(columns={val_col: "Close"})
        logger.info("Loaded manual CSV for %s from %s (%d rows)", symbol, path.name, len(result))
        return result
    except Exception as exc:
        logger.error("Failed to parse manual CSV %s: %s", path, exc)
        return pd.DataFrame()


def fetch_mm_symbol(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch a single MM breadth series using priority chain.

    Returns DataFrame with 'Close' column (breadth % value).
    """
    start = start or settings.data_start_date
    from datetime import date
    end = end or date.today().isoformat()

    cache_key = f"mm_{symbol}"

    if not force_refresh and not cache.is_stale(cache_key):
        cached = cache.load(cache_key)
        if not cached.empty:
            return cached

    # Tier 1: EODHD
    if _eodhd.is_available():
        df = _eodhd.fetch(symbol, start, end)
        if not df.empty:
            cache.update(cache_key, df)
            return cache.load(cache_key)

    # Tier 2: Manual CSV
    df = _load_manual_csv(symbol)
    if not df.empty:
        cache.update(cache_key, df)
        return cache.load(cache_key)

    # Tier 3: Computed from S&P 500 constituents
    logger.info("Computing %s from S&P 500 constituents (Tier 3)", symbol)
    df = _computed.fetch(symbol, start, end)
    if not df.empty:
        cache.update(cache_key, df)
    return cache.load(cache_key)


def fetch_all_mm(
    start: str | None = None,
    end: str | None = None,
    force_refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """Fetch all four MM breadth series efficiently."""
    start = start or settings.data_start_date
    from datetime import date
    end = end or date.today().isoformat()

    # Check if any are stale
    any_stale = force_refresh or any(
        cache.is_stale(f"mm_{sym}") for sym in MM_SYMBOLS
    )

    if not any_stale:
        result = {}
        all_cached = True
        for sym in MM_SYMBOLS:
            df = cache.load(f"mm_{sym}")
            if df.empty:
                all_cached = False
                break
            result[sym] = df
        if all_cached:
            return result

    # Tier 1: EODHD (individual fetches)
    if _eodhd.is_available():
        return {sym: fetch_mm_symbol(sym, start, end, force_refresh=True) for sym in MM_SYMBOLS}

    # Tier 2: Manual CSVs
    manual_result = {sym: _load_manual_csv(sym) for sym in MM_SYMBOLS}
    if all(not df.empty for df in manual_result.values()):
        for sym, df in manual_result.items():
            cache.update(f"mm_{sym}", df)
        return {sym: cache.load(f"mm_{sym}") for sym in MM_SYMBOLS}

    # Tier 3: Batch compute (single constituent download for efficiency)
    # Reuse already-cached constituent data from breadth_fetcher if available
    logger.info("Batch computing MM breadth from S&P 500 constituents...")
    all_computed = _computed.fetch_all(start, end)
    computed = {sym: all_computed.get(sym, pd.DataFrame()) for sym in MM_SYMBOLS}

    # Merge manual CSV data where available (partial override)
    for sym in MM_SYMBOLS:
        manual = _load_manual_csv(sym)
        if not manual.empty and not computed.get(sym, pd.DataFrame()).empty:
            # Prefer manual where available, fill gaps with computed
            combined = computed[sym].combine_first(manual)
            computed[sym] = combined

    for sym, df in computed.items():
        if not df.empty:
            cache.update(f"mm_{sym}", df)

    return {sym: cache.load(f"mm_{sym}") for sym in MM_SYMBOLS}
