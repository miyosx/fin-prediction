"""% distance above/below the 200-day SMA for each major index."""
import pandas as pd


def pct_above_200ma(close: pd.Series, window: int = 200) -> pd.Series:
    """Compute (close - SMA200) / SMA200 * 100 for a price series.

    Args:
        close: Price series indexed by Date.
        window: MA window (default 200).

    Returns:
        Series of % distance values, named '<series.name>_pct_dist_200ma'.
    """
    sma = close.rolling(window=window, min_periods=window // 2).mean()
    dist = (close - sma) / sma * 100
    name = f"{close.name}_pct_dist_{window}ma" if close.name else f"pct_dist_{window}ma"
    return dist.rename(name)


def ma_distance_all(indices: dict[str, pd.Series], window: int = 200) -> pd.DataFrame:
    """Compute % distance for all provided index series.

    Args:
        indices: dict of {name: close_series}
        window: MA window.

    Returns:
        DataFrame with one column per index.
    """
    parts = []
    for name, close in indices.items():
        close = close.rename(name)
        parts.append(pct_above_200ma(close, window))
    return pd.concat(parts, axis=1)
