"""Fetches NYSE breadth data: A/D line, NH/NL, Up/Down volume.

Tries yfinance first; falls back to computed S&P 500 approximation
if Yahoo Finance breadth tickers are unavailable (they were removed ~2024).
"""
from __future__ import annotations

import logging

import pandas as pd

from config.settings import settings
from config.symbols import BREADTH_SYMBOLS
from data.cache import parquet_cache as cache
from data.cache import cache_manager
from data.providers.computed_provider import ComputedBreadthProvider

logger = logging.getLogger(__name__)

_computed = ComputedBreadthProvider()

# Internal symbol name → yfinance ticker
_YF_TICKERS = BREADTH_SYMBOLS  # e.g. {"NYAD": "^NYAD", ...}


def _cache_key(symbol: str) -> str:
    return f"breadth_{symbol}"


def fetch_breadth(symbol: str, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch a breadth series by short name (e.g. 'NYAD', 'NAHL').

    Priority:
      1. Parquet cache (if fresh)
      2. yfinance (if ticker available)
      3. Computed from S&P 500 constituents
    """
    key = _cache_key(symbol)

    if not force_refresh and not cache.is_stale(key):
        cached = cache.load(key)
        if not cached.empty:
            return cached

    # Try yfinance
    ticker = _YF_TICKERS.get(symbol)
    if ticker:
        df = cache_manager.get_or_fetch(ticker, force_refresh=force_refresh)
        if not df.empty:
            result = df[["Close"]] if "Close" in df.columns else df
            cache.update(key, result)
            return cache.load(key)

    # Fallback: computed from constituents
    logger.info(
        "yfinance has no data for %s — computing from S&P 500 constituents", symbol
    )
    all_computed = _fetch_all_computed(force_refresh=force_refresh)
    df = all_computed.get(symbol, pd.DataFrame())
    if not df.empty:
        cache.update(key, df)
    return cache.load(key)


def fetch_all_breadth(force_refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Fetch all NYSE breadth symbols efficiently.

    Tries yfinance for each; if any fail, runs a single batch constituent
    computation to fill gaps.
    """
    symbols = list(_YF_TICKERS.keys())  # NYAD, NAHL, NYUPVOL, NYDNVOL
    result: dict[str, pd.DataFrame] = {}
    missing: list[str] = []

    for sym in symbols:
        key = _cache_key(sym)
        if not force_refresh and not cache.is_stale(key):
            cached = cache.load(key)
            if not cached.empty:
                result[sym] = cached
                continue

        ticker = _YF_TICKERS.get(sym)
        df = pd.DataFrame()
        if ticker:
            df = cache_manager.get_or_fetch(ticker, force_refresh=force_refresh)
            if not df.empty and "Close" in df.columns:
                df = df[["Close"]]
                cache.update(key, df)
                result[sym] = cache.load(key)
                continue

        missing.append(sym)

    if missing:
        logger.info("Computing breadth for %s from S&P 500 constituents...", missing)
        computed = _fetch_all_computed(force_refresh=force_refresh)
        for sym in missing:
            df = computed.get(sym, pd.DataFrame())
            if not df.empty:
                cache.update(_cache_key(sym), df)
            result[sym] = cache.load(_cache_key(sym))

    return result


def get_close(symbol: str, force_refresh: bool = False) -> pd.Series:
    """Return just the Close series for a breadth symbol."""
    df = fetch_breadth(symbol, force_refresh=force_refresh)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float, name=symbol)
    return df["Close"].rename(symbol)


# ------------------------------------------------------------------ #
# Internal: batch constituent computation with caching
# ------------------------------------------------------------------ #

_COMPUTED_BATCH_KEY = "computed_breadth_batch_ts"  # timestamp sentinel


def _fetch_all_computed(force_refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Run the constituent computation once and cache all outputs."""
    from datetime import date
    start = settings.data_start_date
    end = date.today().isoformat()

    # Check if any computed breadth is already fresh
    computed_symbols = ["NYAD", "NAHL", "NYUPVOL", "NYDNVOL"]
    if not force_refresh:
        all_fresh = all(
            not cache.is_stale(_cache_key(s)) and not cache.load(_cache_key(s)).empty
            for s in computed_symbols
        )
        if all_fresh:
            return {s: cache.load(_cache_key(s)) for s in computed_symbols}

    all_data = _computed.fetch_all(start, end)
    # Cache everything returned (breadth + MM breadth)
    for sym, df in all_data.items():
        if not df.empty:
            key = _cache_key(sym) if sym in computed_symbols else f"mm_{sym}"
            cache.update(key, df)

    return {s: all_data.get(s, pd.DataFrame()) for s in computed_symbols}
