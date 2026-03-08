"""Tests for forward return target computation."""
import pandas as pd
import numpy as np
import pytest

from ml.targets.forward_returns import compute_targets


@pytest.fixture
def flat_prices():
    dates = pd.date_range("2020-01-01", periods=300, freq="B")
    return pd.Series(100.0, index=dates, name="SPX")


@pytest.fixture
def crashing_prices():
    """Prices that drop 50% starting at day 100."""
    dates = pd.date_range("2020-01-01", periods=300, freq="B")
    prices = [100.0] * 100 + [50.0] * 200
    return pd.Series(prices, index=dates, name="SPX")


def test_target_columns(flat_prices):
    result = compute_targets(flat_prices)
    assert "spx_fwd_21d" in result.columns
    assert "spx_fwd_63d" in result.columns
    assert "bear_flag_126d" in result.columns


def test_flat_prices_zero_return(flat_prices):
    result = compute_targets(flat_prices)
    # Flat price → forward returns ~0
    valid = result["spx_fwd_21d"].dropna()
    assert valid.abs().max() < 0.01


def test_bear_flag_detected(crashing_prices):
    result = compute_targets(crashing_prices)
    # Rows before the crash should have bear_flag=1 (crash happens within 126d)
    assert result["bear_flag_126d"].iloc[0] == 1


def test_bear_flag_not_set_after_crash(crashing_prices):
    result = compute_targets(crashing_prices)
    # Rows well after the crash bottom: no further 20%+ drop
    last_rows = result["bear_flag_126d"].iloc[230:250]
    assert last_rows.max() == 0
