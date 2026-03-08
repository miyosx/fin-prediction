"""Lowry Research indicators: Up/Down Volume ratio and 90% day flags."""
import pandas as pd
import numpy as np


def up_down_vol_ratio(
    upvol: pd.Series, dnvol: pd.Series, window: int = 90
) -> pd.DataFrame:
    """Compute Lowry Up/Down Volume indicators.

    Args:
        upvol: NYSE Up Volume series (^NYUPVOL Close).
        dnvol: NYSE Down Volume series (^NYDNVOL Close).
        window: Rolling window for trend ratio (default 90 days).

    Returns:
        DataFrame with columns:
            - upvol: raw up volume
            - dnvol: raw down volume
            - total_vol: upvol + dnvol
            - up_pct: upvol / total_vol * 100
            - dn_pct: dnvol / total_vol * 100
            - is_90pct_up_day: up_pct >= 90
            - is_90pct_dn_day: dn_pct >= 90
            - rolling_up_ratio_{window}d: rolling mean of up_pct
    """
    total = upvol + dnvol

    up_pct = (upvol / total * 100).rename("up_pct")
    dn_pct = (dnvol / total * 100).rename("dn_pct")

    is_90_up = (up_pct >= 90.0).rename("is_90pct_up_day")
    is_90_dn = (dn_pct >= 90.0).rename("is_90pct_dn_day")

    rolling_up = up_pct.rolling(window=window, min_periods=window // 2).mean().rename(
        f"rolling_up_ratio_{window}d"
    )

    df = pd.DataFrame({
        "upvol": upvol,
        "dnvol": dnvol,
        "total_vol": total,
        "up_pct": up_pct,
        "dn_pct": dn_pct,
        "is_90pct_up_day": is_90_up,
        "is_90pct_dn_day": is_90_dn,
        f"rolling_up_ratio_{window}d": rolling_up,
    })
    return df


def consecutive_90pct_days(df: pd.DataFrame, kind: str = "up", max_gap: int = 5) -> pd.Series:
    """Count consecutive or clustered 90% days of a given kind.

    Args:
        df: Output of up_down_vol_ratio().
        kind: "up" or "dn".
        max_gap: Maximum gap (days) between 90% days to be considered a cluster.

    Returns:
        Series counting how many 90% days occurred in the trailing max_gap window.
    """
    col = f"is_90pct_{kind}_day"
    if col not in df.columns:
        raise ValueError(f"Column {col} not found")
    return (
        df[col]
        .astype(int)
        .rolling(window=max_gap, min_periods=1)
        .sum()
        .rename(f"clustered_90pct_{kind}_days_{max_gap}d")
    )
