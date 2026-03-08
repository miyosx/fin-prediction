"""Tests for divergence indicator."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from indicators.divergence import compute_all, divergence_zone, _rolling_zscore, _rolling_slope


@pytest.fixture
def dates():
    return pd.date_range("2018-01-01", periods=600, freq="B")


@pytest.fixture
def noisy_trend(dates):
    """Upward-trending series with noise — realistic for z-score testing."""
    np.random.seed(7)
    trend = np.linspace(0, 5, 600)
    noise = np.random.randn(600)
    return pd.Series(trend + noise, index=dates, name="price")


@pytest.fixture
def phased_pair(dates):
    """Two series that move together then diverge.

    Phase 1 (0-200): both rise together — no divergence.
    Phase 2 (200-400): SPX continues rising, ADL reverses down — bearish divergence.
    Phase 3 (400-600): both fall together — no divergence.
    """
    np.random.seed(42)
    n = 600
    t = np.arange(n, dtype=float)

    # SPX: rises throughout
    spx_vals = np.concatenate([
        np.linspace(100, 130, 200),   # Phase 1: up
        np.linspace(130, 170, 200),   # Phase 2: continues up
        np.linspace(170, 150, 200),   # Phase 3: slight pullback
    ]) + np.random.randn(n) * 0.5

    # ADL: rises then falls sharply
    adl_vals = np.concatenate([
        np.linspace(5000, 5500, 200),  # Phase 1: up
        np.linspace(5500, 4000, 200),  # Phase 2: falls (diverges from SPX)
        np.linspace(4000, 3800, 200),  # Phase 3: continues down
    ]) + np.random.randn(n) * 10

    # RUT and DJI move with SPX (no inter-index divergence in this fixture)
    rut_vals = spx_vals * 0.5 + np.random.randn(n) * 0.3
    dji_vals = spx_vals * 350 + np.random.randn(n) * 100

    return (
        pd.Series(spx_vals, index=dates, name="spx"),
        pd.Series(adl_vals, index=dates, name="adl"),
        pd.Series(rut_vals, index=dates, name="rut"),
        pd.Series(dji_vals, index=dates, name="dji"),
    )


@pytest.fixture
def bullish_pair(dates):
    """SPX falling phase while ADL stabilizes/rises — bullish divergence."""
    np.random.seed(99)
    n = 600

    spx_vals = np.concatenate([
        np.linspace(150, 150, 200),   # Phase 1: flat
        np.linspace(150, 110, 200),   # Phase 2: SPX falls
        np.linspace(110, 110, 200),   # Phase 3: flat
    ]) + np.random.randn(n) * 0.5

    adl_vals = np.concatenate([
        np.linspace(5000, 5000, 200),  # Phase 1: flat
        np.linspace(5000, 5300, 200),  # Phase 2: ADL rises (diverges from SPX)
        np.linspace(5300, 5300, 200),  # Phase 3: flat
    ]) + np.random.randn(n) * 10

    rut_vals = spx_vals * 0.5
    dji_vals = spx_vals * 350

    return (
        pd.Series(spx_vals, index=dates, name="spx"),
        pd.Series(adl_vals, index=dates, name="adl"),
        pd.Series(rut_vals, index=dates, name="rut"),
        pd.Series(dji_vals, index=dates, name="dji"),
    )


# ------------------------------------------------------------------ #
# Helper tests
# ------------------------------------------------------------------ #

def test_rolling_zscore_returns_series(noisy_trend):
    z = _rolling_zscore(noisy_trend, 100)
    assert isinstance(z, pd.Series)
    assert len(z) == len(noisy_trend)


def test_rolling_zscore_has_warmup_nans(noisy_trend):
    z = _rolling_zscore(noisy_trend, 100)
    # First ~50 values (min_periods = lookback//2) should be NaN
    assert z.iloc[:40].isna().all()


def test_rolling_zscore_finite_after_warmup(noisy_trend):
    z = _rolling_zscore(noisy_trend, 100)
    assert z.iloc[150:].notna().all()
    # Z-scores for a noisy trend should be bounded
    assert z.iloc[150:].abs().max() < 10


def test_rolling_slope_positive_for_trend_up(noisy_trend):
    z = _rolling_zscore(noisy_trend, 100)
    slope = _rolling_slope(z, 21)
    # Noisy upward trend → mean slope should be positive after warmup
    assert slope.iloc[200:].mean() > 0


def test_rolling_slope_returns_series(noisy_trend):
    z = _rolling_zscore(noisy_trend, 100)
    slope = _rolling_slope(z, 21)
    assert isinstance(slope, pd.Series)
    assert len(slope) == len(noisy_trend)


# ------------------------------------------------------------------ #
# compute_all output structure
# ------------------------------------------------------------------ #

def test_output_columns(phased_pair):
    spx, adl, rut, dji = phased_pair
    result = compute_all(adl, spx, rut, dji)
    required = {
        "adl_z", "spx_z", "rut_z", "dji_z",
        "adl_slope", "spx_slope", "rut_slope", "dji_slope",
        "spx_adl_div", "spx_adl_bearish", "spx_adl_bullish",
        "rut_adl_div", "dji_adl_div", "spx_rut_div",
        "active_bearish_pairs", "active_bullish_pairs",
        "composite_div_score",
    }
    assert required.issubset(set(result.columns))


def test_output_length(phased_pair):
    spx, adl, rut, dji = phased_pair
    result = compute_all(adl, spx, rut, dji)
    assert len(result) == 600


def test_bearish_divergence_detected(phased_pair):
    spx, adl, rut, dji = phased_pair
    # Phase 2 (index 200-400): SPX rising while ADL falling → bearish
    result = compute_all(adl, spx, rut, dji, window=21, z_lookback=100, z_thresh=0.3)
    # Check bearish flag fires somewhere in Phase 2
    phase2 = result["spx_adl_bearish"].iloc[250:380]
    assert phase2.any(), "Bearish divergence not detected in Phase 2"


def test_bullish_divergence_detected(bullish_pair):
    spx, adl, rut, dji = bullish_pair
    result = compute_all(adl, spx, rut, dji, window=21, z_lookback=100, z_thresh=0.3)
    phase2 = result["spx_adl_bullish"].iloc[250:380]
    assert phase2.any(), "Bullish divergence not detected in Phase 2"


def test_composite_score_positive_in_bearish_phase(phased_pair):
    spx, adl, rut, dji = phased_pair
    result = compute_all(adl, spx, rut, dji, window=21, z_lookback=100, z_thresh=0.3)
    # Mean composite score in divergence phase should be positive (bearish)
    assert result["composite_div_score"].iloc[260:380].mean() > 0


def test_composite_score_negative_in_bullish_phase(bullish_pair):
    spx, adl, rut, dji = bullish_pair
    result = compute_all(adl, spx, rut, dji, window=21, z_lookback=100, z_thresh=0.3)
    assert result["composite_div_score"].iloc[260:380].mean() < 0


def test_active_pair_counts_bounded(phased_pair):
    spx, adl, rut, dji = phased_pair
    result = compute_all(adl, spx, rut, dji)
    assert result["active_bearish_pairs"].between(0, 4).all()
    assert result["active_bullish_pairs"].between(0, 4).all()


def test_no_divergence_when_perfectly_correlated(dates):
    """When all series move identically, no divergence should fire."""
    base = pd.Series(np.random.randn(600).cumsum() + 100, index=dates)
    result = compute_all(base, base * 10, base * 0.5, base * 300,
                         window=21, z_lookback=100, z_thresh=0.5)
    # Perfectly correlated → slopes are equal → div ~= 0 → no flags
    assert result["spx_adl_bearish"].iloc[200:].sum() == 0
    assert result["spx_adl_bullish"].iloc[200:].sum() == 0


# ------------------------------------------------------------------ #
# divergence_zone
# ------------------------------------------------------------------ #

def test_zone_bearish():
    assert divergence_zone(0.8) == "bearish"

def test_zone_bullish():
    assert divergence_zone(-0.8) == "bullish"

def test_zone_neutral_positive():
    assert divergence_zone(0.1) == "neutral"

def test_zone_neutral_negative():
    assert divergence_zone(-0.1) == "neutral"

def test_zone_neutral_zero():
    assert divergence_zone(0.0) == "neutral"
