"""Tests for Lowry up/down volume indicators."""
import pandas as pd
import numpy as np
import pytest

from indicators.lowry import up_down_vol_ratio, consecutive_90pct_days


@pytest.fixture
def vol_pair():
    dates = pd.date_range("2020-01-01", periods=200, freq="B")
    upvol = pd.Series(np.random.randint(500_000, 3_000_000, size=200).astype(float), index=dates)
    dnvol = pd.Series(np.random.randint(500_000, 3_000_000, size=200).astype(float), index=dates)
    return upvol, dnvol


def test_up_down_ratio_columns(vol_pair):
    upvol, dnvol = vol_pair
    result = up_down_vol_ratio(upvol, dnvol)
    expected = {"upvol", "dnvol", "total_vol", "up_pct", "dn_pct", "is_90pct_up_day", "is_90pct_dn_day"}
    assert expected.issubset(set(result.columns))


def test_up_pct_plus_dn_pct_equals_100(vol_pair):
    upvol, dnvol = vol_pair
    result = up_down_vol_ratio(upvol, dnvol)
    total = result["up_pct"] + result["dn_pct"]
    assert (total - 100).abs().max() < 1e-6


def test_90pct_day_detection():
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    upvol = pd.Series([90.0, 10, 10, 10, 10, 10, 10, 10, 10, 10], index=dates)
    dnvol = pd.Series([10.0, 90, 10, 10, 10, 10, 10, 10, 10, 10], index=dates)
    result = up_down_vol_ratio(upvol, dnvol)
    assert result["is_90pct_up_day"].iloc[0] == True
    assert result["is_90pct_dn_day"].iloc[1] == True
    assert result["is_90pct_up_day"].iloc[2] == False
