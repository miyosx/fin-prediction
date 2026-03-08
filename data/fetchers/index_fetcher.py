"""Fetches OHLCV data for major index symbols."""
import pandas as pd

from config.settings import settings
from config.symbols import INDEX_SYMBOLS
from data.cache import cache_manager


def fetch_index(symbol_key: str, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch data for a single index by its short name (e.g. 'SPX').

    Returns OHLCV DataFrame indexed by Date.
    """
    ticker = INDEX_SYMBOLS.get(symbol_key, symbol_key)
    return cache_manager.get_or_fetch(ticker, force_refresh=force_refresh)


def fetch_all_indices(force_refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Fetch all configured index symbols.

    Returns dict keyed by short name (e.g. {'SPX': df, 'NYA': df, ...}).
    """
    return {
        name: cache_manager.get_or_fetch(ticker, force_refresh=force_refresh)
        for name, ticker in INDEX_SYMBOLS.items()
    }


def get_close(symbol_key: str, force_refresh: bool = False) -> pd.Series:
    """Convenience: return just the Close series for an index."""
    df = fetch_index(symbol_key, force_refresh=force_refresh)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float, name=symbol_key)
    return df["Close"].rename(symbol_key)
