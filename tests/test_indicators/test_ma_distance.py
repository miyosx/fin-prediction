"""Tests for MA distance indicator."""
import pandas as pd
import numpy as np
import pytest

from indicators.ma_distance import pct_above_200ma, ma_distance_all


def test_pct_above_200ma_trending_up(price_series):
    result = pct_above_200ma(price_series)
    assert isinstance(result, pd.Series)
    # After 200 days, values should not all be NaN
    assert result.iloc[210:].notna().any()


def test_pct_above_200ma_known_value():
    """Flat price series should give ~0% distance."""
    dates = pd.date_range("2020-01-01", periods=300, freq="B")
    price = pd.Series(100.0, index=dates, name="TEST")
    result = pct_above_200ma(price)
    # Flat price: distance should be ~0 after warmup
    assert abs(result.iloc[-1]) < 0.1


def test_pct_above_200ma_below():
    """Price consistently below SMA should be negative."""
    dates = pd.date_range("2020-01-01", periods=300, freq="B")
    # Start high, crash
    prices = [100.0] * 200 + [50.0] * 100
    price = pd.Series(prices, index=dates, name="TEST")
    result = pct_above_200ma(price)
    # After crash settles in SMA, distance should be negative
    assert result.iloc[-1] < 0


def test_ma_distance_all(price_series):
    indices = {"SPX": price_series, "NYA": price_series * 0.9}
    result = ma_distance_all(indices)
    assert isinstance(result, pd.DataFrame)
    assert "SPX_pct_dist_200ma" in result.columns
    assert "NYA_pct_dist_200ma" in result.columns
