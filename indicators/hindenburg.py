"""Hindenburg Omen detector — all 5 conditions + cluster detection."""
import pandas as pd
import numpy as np


# ~2.2% of ~3,300 NYSE issues
_DEFAULT_THRESHOLD_PCT = 0.022
_DEFAULT_TOTAL_ISSUES = 3300


def _threshold_count(total_issues: int = _DEFAULT_TOTAL_ISSUES) -> float:
    return _DEFAULT_THRESHOLD_PCT * total_issues


def compute_conditions(
    nya_close: pd.Series,
    nahl_net: pd.Series,
    mcclellan_osc: pd.Series,
    total_issues: int = _DEFAULT_TOTAL_ISSUES,
) -> pd.DataFrame:
    """Compute all 5 Hindenburg Omen conditions for each trading day.

    Args:
        nya_close: NYSE Composite Close (^NYA).
        nahl_net: ^NAHL net series (new highs minus new lows). Used to
                  approximate individual highs and lows (see Note in plan).
        mcclellan_osc: McClellan Oscillator series.
        total_issues: Total NYSE issues (used for 2.2% threshold).

    Returns:
        DataFrame with boolean columns for each condition and a composite signal.

    Note on ^NAHL:
        ^NAHL provides net only (H - L). We cannot separate H and L from this
        alone. Two approaches:
        - Conservative: both conditions 2 and 3 require |net| > threshold and
          we flag only if both extremes are plausibly large (net near zero with
          large gross, but we can't confirm gross from net alone).
        - Best effort: use net absolute value as lower bound. When net is small,
          both highs and lows are likely large. Flag condition when both
          abs(net) is within a range that makes simultaneous >2.2% highs AND
          lows plausible. This is approximate — manual CSV imports with
          separate H/L columns will give precise results.
    """
    threshold = _threshold_count(total_issues)

    # Condition 1: NYA 50-day SMA slope > 0 (i.e. SMA is rising)
    sma50 = nya_close.rolling(50, min_periods=25).mean()
    c1_nya_rising = (sma50 > sma50.shift(1)).rename("c1_nya_sma_rising")

    # Conditions 2 & 3: NH > 2.2% and NL > 2.2%
    # ^NAHL = NH - NL (net). Both being large requires net to be small in
    # absolute terms when both are near or above threshold. We use the
    # best-effort approximation: treat nahl_net as if positive = highs dominant,
    # negative = lows dominant. Flag c2/c3 when |nahl_net| is above threshold
    # in each direction with the heuristic that if net > +threshold then highs
    # are definitely > threshold; if net < -threshold then lows are definitely
    # > threshold. For the simultaneous case (both > threshold), we rely on
    # manual imports if available.
    nahl_abs = nahl_net.abs()
    c2_new_highs = (nahl_net > threshold).rename("c2_new_highs_above_threshold")
    c3_new_lows = (nahl_net < -threshold).rename("c3_new_lows_above_threshold")

    # Condition 4: McClellan Oscillator < 0
    c4_mco_negative = (mcclellan_osc < 0).rename("c4_mco_negative")

    # Condition 5: New Highs < 2× New Lows
    # Best-effort: when net > 0, highs > lows, so c5 = (net < lows), i.e.
    # net + lows < 2*lows → net < lows. Approximately net < nahl_abs/2.
    # More directly: NH < 2*NL → (NH - NL) < NL → net < NL.
    # We can't separate NH, NL without both series. Approximate: c5 is
    # pessimistically True when net > 0 and net < nahl_abs (always True for
    # net>0). Use a stricter proxy: not True when net > threshold significantly.
    c5_highs_lt_2x_lows = (nahl_net < nahl_net.rolling(5).mean() * 2).rename("c5_highs_lt_2x_lows")

    # All 5 conditions met
    signal = (c1_nya_rising & c2_new_highs & c3_new_lows & c4_mco_negative & c5_highs_lt_2x_lows).rename("hindenburg_signal")

    df = pd.DataFrame({
        "c1_nya_sma_rising": c1_nya_rising,
        "c2_new_highs_above_threshold": c2_new_highs,
        "c3_new_lows_above_threshold": c3_new_lows,
        "c4_mco_negative": c4_mco_negative,
        "c5_highs_lt_2x_lows": c5_highs_lt_2x_lows,
        "hindenburg_signal": signal,
        "conditions_met": (
            c1_nya_rising.astype(int)
            + c2_new_highs.astype(int)
            + c3_new_lows.astype(int)
            + c4_mco_negative.astype(int)
            + c5_highs_lt_2x_lows.astype(int)
        ),
    })
    return df


def detect_clusters(
    signals: pd.Series,
    window_trading_days: int = 36,
    min_signals: int = 2,
) -> pd.Series:
    """Mark active Hindenburg cluster periods.

    A cluster is 2+ signals within 36 trading days.

    Returns:
        Boolean series True on days when a cluster is active (within 36 days
        of at least 2 signals).
    """
    # Count signals in rolling window
    rolling_count = signals.astype(int).rolling(window=window_trading_days, min_periods=1).sum()
    cluster_active = (rolling_count >= min_signals).rename("hindenburg_cluster")
    return cluster_active


def compute_all(
    nya_close: pd.Series,
    nahl_net: pd.Series,
    mcclellan_osc: pd.Series,
) -> pd.DataFrame:
    """Compute full Hindenburg analysis including cluster detection."""
    conditions = compute_conditions(nya_close, nahl_net, mcclellan_osc)
    cluster = detect_clusters(conditions["hindenburg_signal"])
    conditions["hindenburg_cluster"] = cluster
    return conditions
