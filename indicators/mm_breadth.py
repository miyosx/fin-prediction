"""MM Breadth indicators: MMFD, MMTW, MMFI, MMTH with threshold signals."""
import pandas as pd

# Thresholds per symbol: (bearish_upper, bullish_lower)
# Below bearish_upper → bearish, above bullish_lower → bullish, else neutral
THRESHOLDS = {
    "MMFD": {"bearish": 20, "bullish": 60},
    "MMTW": {"bearish": 20, "bullish": 80},
    "MMFI": {"bearish": 30, "bullish": 70},
    "MMTH": {"bearish": 25, "bullish": 65},
}


def zone(value: float, symbol: str) -> str:
    """Return 'bearish', 'neutral', or 'bullish' for a given value."""
    t = THRESHOLDS.get(symbol, {"bearish": 30, "bullish": 70})
    if value < t["bearish"]:
        return "bearish"
    if value > t["bullish"]:
        return "bullish"
    return "neutral"


def zone_series(series: pd.Series, symbol: str) -> pd.Series:
    """Apply zone() to every value in a series."""
    t = THRESHOLDS.get(symbol, {"bearish": 30, "bullish": 70})
    conditions = [
        series < t["bearish"],
        series > t["bullish"],
    ]
    choices = ["bearish", "bullish"]
    import numpy as np
    return pd.Series(
        np.select(conditions, choices, default="neutral"),
        index=series.index,
        name=f"{symbol}_zone",
    )


def compute_all(mm_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build a combined MM breadth DataFrame with values and zone labels.

    Args:
        mm_data: Dict from mm_breadth_fetcher.fetch_all_mm(), keys are
                 MMFD, MMTW, MMFI, MMTH. Each value is a DataFrame with
                 a 'Close' column.

    Returns:
        DataFrame with columns: MMFD, MMTW, MMFI, MMTH,
        MMFD_zone, MMTW_zone, MMFI_zone, MMTH_zone.
    """
    cols = {}
    for sym, df in mm_data.items():
        if df.empty or "Close" not in df.columns:
            continue
        cols[sym] = df["Close"]
        cols[f"{sym}_zone"] = zone_series(df["Close"], sym)

    if not cols:
        return pd.DataFrame()

    return pd.DataFrame(cols)
