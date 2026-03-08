"""Advance-Decline indicators: cumulative A/D, McClellan Oscillator, Summation."""
import pandas as pd


def net_advances(ad_cumulative: pd.Series) -> pd.Series:
    """Recover daily net advances from the cumulative A/D line (^NYAD)."""
    return ad_cumulative.diff().rename("net_advances")


def mcclellan_oscillator(net_adv: pd.Series) -> pd.Series:
    """EMA(19) - EMA(39) of daily net advances.

    Args:
        net_adv: Daily net advances series.

    Returns:
        McClellan Oscillator series.
    """
    ema19 = net_adv.ewm(span=19, adjust=False, min_periods=10).mean()
    ema39 = net_adv.ewm(span=39, adjust=False, min_periods=20).mean()
    osc = (ema19 - ema39).rename("mcclellan_oscillator")
    return osc


def mcclellan_summation(oscillator: pd.Series) -> pd.Series:
    """Cumulative sum of McClellan Oscillator."""
    return oscillator.cumsum().rename("mcclellan_summation")


def compute_all(ad_line: pd.Series) -> pd.DataFrame:
    """Compute all A/D-derived indicators from the ^NYAD cumulative line.

    Returns DataFrame with columns:
        - ad_line: original cumulative A/D
        - net_advances: daily net
        - mcclellan_oscillator
        - mcclellan_summation
    """
    net = net_advances(ad_line)
    osc = mcclellan_oscillator(net)
    summ = mcclellan_summation(osc)
    return pd.DataFrame({
        "ad_line": ad_line,
        "net_advances": net,
        "mcclellan_oscillator": osc,
        "mcclellan_summation": summ,
    })
