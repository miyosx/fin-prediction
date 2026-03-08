"""Net New Highs/Lows indicator from ^NAHL (net = highs - lows)."""
import pandas as pd


def net_new_highs_lows(nahl: pd.Series) -> pd.Series:
    """Return the net NH/NL series (already net from ^NAHL).

    ^NAHL from yfinance is the net (new 52-week highs minus lows).
    """
    return nahl.rename("net_new_highs_lows")


def smoothed_nhnl(nahl: pd.Series, window: int = 10) -> pd.Series:
    """Rolling N-day average of net NH/NL."""
    return nahl.rolling(window=window, min_periods=1).mean().rename(f"nhnl_sma{window}")


def compute_all(nahl: pd.Series) -> pd.DataFrame:
    """Compute net NH/NL indicators.

    Args:
        nahl: ^NAHL Close series (net new highs - new lows).

    Returns:
        DataFrame with columns:
            - net_new_highs_lows
            - nhnl_sma10
    """
    return pd.DataFrame({
        "net_new_highs_lows": net_new_highs_lows(nahl),
        "nhnl_sma10": smoothed_nhnl(nahl, 10),
    })
