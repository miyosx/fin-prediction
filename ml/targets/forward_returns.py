"""Compute forward return targets for model training."""
import pandas as pd
import numpy as np


def compute_targets(spx_close: pd.Series) -> pd.DataFrame:
    """Compute forward return targets aligned to each date.

    Args:
        spx_close: SPX daily close prices.

    Returns:
        DataFrame with columns:
            - spx_fwd_21d: 1-month (21-day) forward return %
            - spx_fwd_63d: 3-month (63-day) forward return %
            - bear_flag_126d: 1 if SPX drops >20% within next 126 trading days
    """
    close = spx_close.sort_index()
    n = len(close)

    fwd_21 = close.shift(-21) / close - 1
    fwd_63 = close.shift(-63) / close - 1

    # Bear flag: any drawdown >20% within next 126 days
    bear_flags = pd.Series(False, index=close.index)
    vals = close.values
    for i in range(n):
        end = min(i + 127, n)
        future = vals[i + 1 : end]
        if len(future) == 0:
            continue
        max_drawdown = (future.min() - vals[i]) / vals[i]
        bear_flags.iloc[i] = max_drawdown < -0.20

    return pd.DataFrame({
        "spx_fwd_21d": fwd_21 * 100,
        "spx_fwd_63d": fwd_63 * 100,
        "bear_flag_126d": bear_flags.astype(int),
    })
