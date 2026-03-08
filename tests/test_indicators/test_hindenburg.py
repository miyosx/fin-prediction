"""Tests for Hindenburg Omen conditions."""
import pandas as pd
import numpy as np
import pytest

from indicators.hindenburg import compute_conditions, detect_clusters


@pytest.fixture
def mock_inputs():
    dates = pd.date_range("2020-01-01", periods=300, freq="B")
    nya = pd.Series(np.linspace(10000, 12000, 300), index=dates, name="NYA")
    # Net NH/NL: make some days have large positive values (many highs only) —
    # for testing cluster logic, force both c2 and c3 by alternating
    nahl = pd.Series(np.random.choice([-100, 100], 300) * 80, index=dates)
    mco = pd.Series(np.random.randn(300) * 50, index=dates)
    return nya, nahl, mco


def test_conditions_columns(mock_inputs):
    nya, nahl, mco = mock_inputs
    result = compute_conditions(nya, nahl, mco)
    expected = {"c1_nya_sma_rising", "c2_new_highs_above_threshold",
                "c3_new_lows_above_threshold", "c4_mco_negative",
                "c5_highs_lt_2x_lows", "hindenburg_signal", "conditions_met"}
    assert expected.issubset(set(result.columns))


def test_conditions_met_bounds(mock_inputs):
    nya, nahl, mco = mock_inputs
    result = compute_conditions(nya, nahl, mco)
    assert result["conditions_met"].min() >= 0
    assert result["conditions_met"].max() <= 5


def test_detect_clusters():
    dates = pd.date_range("2020-01-01", periods=100, freq="B")
    signals = pd.Series(False, index=dates)
    # Place 2 signals within 36 days
    signals.iloc[10] = True
    signals.iloc[20] = True
    clusters = detect_clusters(signals)
    assert clusters.iloc[20] == True
    # No cluster at the start
    assert clusters.iloc[0] == False
