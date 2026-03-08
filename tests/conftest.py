"""Shared test fixtures."""
import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def price_series():
    """Synthetic price series (200 days, trending up)."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    prices = 100 * (1 + np.random.randn(400) * 0.01).cumprod()
    return pd.Series(prices, index=dates, name="SPX")


@pytest.fixture
def volume_series():
    """Synthetic volume series aligned to price_series."""
    np.random.seed(0)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    vol = np.random.randint(1_000_000, 5_000_000, size=400).astype(float)
    return pd.Series(vol, index=dates, name="Volume")


@pytest.fixture
def breadth_series():
    """Synthetic cumulative A/D line."""
    np.random.seed(1)
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    steps = np.random.choice([-500, 500], size=400, p=[0.45, 0.55])
    ad = steps.cumsum()
    return pd.Series(ad.astype(float), index=dates, name="NYAD")
