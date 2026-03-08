"""Tests for advance-decline indicators."""
import pandas as pd
import numpy as np
import pytest

from indicators.advance_decline import compute_all, net_advances, mcclellan_oscillator


def test_net_advances(breadth_series):
    net = net_advances(breadth_series)
    assert isinstance(net, pd.Series)
    assert net.iloc[0] is np.nan or pd.isna(net.iloc[0])
    # Net should be roughly ±500 based on fixture
    assert net.dropna().abs().mean() < 1000


def test_mcclellan_oscillator(breadth_series):
    net = net_advances(breadth_series)
    osc = mcclellan_oscillator(net)
    assert isinstance(osc, pd.Series)
    assert len(osc) == len(breadth_series)
    # After warmup, should have values
    assert osc.iloc[50:].notna().any()


def test_compute_all_columns(breadth_series):
    result = compute_all(breadth_series)
    assert isinstance(result, pd.DataFrame)
    expected_cols = {"ad_line", "net_advances", "mcclellan_oscillator", "mcclellan_summation"}
    assert expected_cols.issubset(set(result.columns))


def test_summation_cumulative(breadth_series):
    result = compute_all(breadth_series)
    # Summation should be cumsum of oscillator (after the first non-NaN)
    osc = result["mcclellan_oscillator"].fillna(0)
    expected_summ = osc.cumsum()
    # Allow for floating point tolerance
    diff = (result["mcclellan_summation"] - expected_summ).abs().max()
    assert diff < 1e-6
