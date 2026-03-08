"""Breadth-price divergence detection.

Algorithm: rolling z-score level comparison (no lookahead).

For each pair (price index vs ADL, or index vs index):
  1. Normalize both series to rolling z-scores over a long lookback (default 252d).
     z = (x - rolling_mean) / rolling_std
  2. Divergence = the z-score SPREAD between the two series.
     Positive spread → price is high relative to history while breadth is low → bearish.
  3. Boolean flags: bearish when price_z > +z_thresh AND breadth_z < -z_thresh
                   bullish when price_z < -z_thresh AND breadth_z > +z_thresh

Why z-score levels (not slopes):
  Slope-of-z detects *acceleration* and only fires when a series changes velocity,
  not when two series steadily diverge. Level-based detection fires whenever price
  is above its historical average while breadth is below — which is exactly the
  classic breadth-price split signal traders look for.

Pairs monitored:
  SPX vs ADL  — primary: cap-weighted price vs equal-weighted breadth
  RUT vs ADL  — small-cap vs breadth: leads major turns
  DJI vs ADL  — 30-stock Dow vs broad breadth: concentration risk
  SPX vs RUT  — inter-index: large vs small cap confirmation

A rolling slope of each z-score series is also computed (using fast OLS) and
included in the output for the visualization charts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ #
# Private helpers
# ------------------------------------------------------------------ #

def _rolling_zscore(s: pd.Series, lookback: int) -> pd.Series:
    """Normalize to z-scores over a rolling lookback window."""
    mu = s.rolling(lookback, min_periods=lookback // 2).mean()
    sigma = s.rolling(lookback, min_periods=lookback // 2).std()
    return ((s - mu) / sigma.replace(0, np.nan)).rename(s.name)


def _rolling_slope(z: pd.Series, window: int) -> pd.Series:
    """Rolling OLS slope using closed-form vectorized formula.

    Slope is in z-score units per day within the window.
    Used for visualization (how fast the z-score is moving), not detection.
    """
    n = window
    i = np.arange(n, dtype=float)
    sum_i = i.sum()
    sum_i2 = (i ** 2).sum()
    denom = n * sum_i2 - sum_i ** 2

    def _slope(arr: np.ndarray) -> float:
        if np.isnan(arr).sum() > n // 2:
            return np.nan
        valid = ~np.isnan(arr)
        if valid.sum() < 3:
            return np.nan
        return (n * np.nansum(i * arr) - sum_i * np.nansum(arr)) / denom

    return (
        z.rolling(window=window, min_periods=max(3, window // 2))
        .apply(_slope, raw=True)
        .rename(f"{z.name}_slope")
    )


def _div_flags(
    z_a: pd.Series,
    z_b: pd.Series,
    z_thresh: float,
    prefix: str,
) -> pd.DataFrame:
    """Return divergence spread and boolean flags for a pair.

    Args:
        z_a: Z-score of the price/reference series.
        z_b: Z-score of the breadth/comparison series.
        z_thresh: How many std devs each series must be offset to count.
        prefix: Column name prefix (e.g. 'spx_adl').

    Bearish divergence: z_a > +z_thresh AND z_b < -z_thresh
    Bullish divergence: z_a < -z_thresh AND z_b > +z_thresh
    """
    spread = (z_a - z_b).rename(f"{prefix}_div")
    bearish = ((z_a > z_thresh) & (z_b < -z_thresh)).rename(f"{prefix}_bearish")
    bullish = ((z_a < -z_thresh) & (z_b > z_thresh)).rename(f"{prefix}_bullish")
    return pd.DataFrame({
        f"{prefix}_div": spread,
        f"{prefix}_bearish": bearish,
        f"{prefix}_bullish": bullish,
    })


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

PAIR_WEIGHTS = {
    "spx_adl": 0.40,
    "rut_adl": 0.30,
    "dji_adl": 0.15,
    "spx_rut": 0.15,
}


def compute_all(
    adl: pd.Series,
    spx: pd.Series,
    rut: pd.Series,
    dji: pd.Series,
    window: int = 21,
    z_lookback: int = 252,
    z_thresh: float = 0.5,
) -> pd.DataFrame:
    """Compute divergence signals for all monitored pairs.

    Args:
        adl: Cumulative A/D line (from advance_decline.compute_all).
        spx: SPX Close prices.
        rut: RUT Close prices.
        dji: DJI Close prices.
        window: Rolling slope window in trading days for visualization (default 21).
        z_lookback: Z-score normalization lookback (default 252 ≈ 1 year).
        z_thresh: Z-score threshold to flag divergence (default 0.5 std devs).

    Returns:
        DataFrame with normalized z-scores, slopes, divergence spreads,
        boolean pair flags, active pair counts, and a weighted composite score.
    """
    combined = pd.concat(
        [adl.rename("adl"), spx.rename("spx"), rut.rename("rut"), dji.rename("dji")],
        axis=1,
        join="inner",
    ).sort_index()

    # --- Z-score normalize each series ---
    z = pd.DataFrame({
        "adl_z": _rolling_zscore(combined["adl"], z_lookback),
        "spx_z": _rolling_zscore(combined["spx"], z_lookback),
        "rut_z": _rolling_zscore(combined["rut"], z_lookback),
        "dji_z": _rolling_zscore(combined["dji"], z_lookback),
    })

    # --- Rolling slopes (for visualization charts) ---
    slopes = pd.DataFrame({
        "adl_slope": _rolling_slope(z["adl_z"], window),
        "spx_slope": _rolling_slope(z["spx_z"], window),
        "rut_slope": _rolling_slope(z["rut_z"], window),
        "dji_slope": _rolling_slope(z["dji_z"], window),
    })

    # --- Pair divergence flags (z-level based) ---
    pairs = [
        _div_flags(z["spx_z"], z["adl_z"], z_thresh, "spx_adl"),
        _div_flags(z["rut_z"], z["adl_z"], z_thresh, "rut_adl"),
        _div_flags(z["dji_z"], z["adl_z"], z_thresh, "dji_adl"),
        _div_flags(z["spx_z"], z["rut_z"], z_thresh, "spx_rut"),
    ]
    pair_df = pd.concat(pairs, axis=1)

    # --- Aggregate counts ---
    bearish_cols = [c for c in pair_df.columns if c.endswith("_bearish")]
    bullish_cols = [c for c in pair_df.columns if c.endswith("_bullish")]
    active_bearish = pair_df[bearish_cols].astype(int).sum(axis=1).rename("active_bearish_pairs")
    active_bullish = pair_df[bullish_cols].astype(int).sum(axis=1).rename("active_bullish_pairs")

    # --- Composite score (positive = bearish divergence, negative = bullish) ---
    composite = sum(
        pair_df[f"{p}_div"] * w
        for p, w in PAIR_WEIGHTS.items()
        if f"{p}_div" in pair_df.columns
    )
    composite = composite.rename("composite_div_score")

    return pd.concat([z, slopes, pair_df, active_bearish, active_bullish, composite], axis=1)


def divergence_zone(score: float) -> str:
    """Classify a composite divergence score.

    Positive = price outrunning breadth = bearish divergence warning.
    Negative = breadth outrunning price = bullish divergence / internal strength.
    """
    if score > 0.5:
        return "bearish"
    if score < -0.5:
        return "bullish"
    return "neutral"
