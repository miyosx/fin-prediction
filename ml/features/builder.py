"""Build feature matrix from composite indicator output."""
import pandas as pd
import numpy as np

from indicators.composite import build_feature_matrix


LAG_WINDOWS = [5, 10, 21]
ROLLING_WINDOWS = [21, 63]

# Columns to exclude from feature engineering (non-numeric / target-like)
_EXCLUDE_COLS = {"ftd_state", "hindenburg_cluster"}


def build_features(force_rebuild: bool = False) -> pd.DataFrame:
    """Load composite matrix and engineer lag/rolling features.

    Returns:
        Feature DataFrame ready for model training.
    """
    base = build_feature_matrix(force_refresh=force_rebuild)
    if base.empty:
        return pd.DataFrame()

    # Select numeric columns only
    num_cols = [
        c for c in base.columns
        if c not in _EXCLUDE_COLS and pd.api.types.is_numeric_dtype(base[c])
    ]
    df = base[num_cols].copy()

    parts = [df]

    # Lag features
    for lag in LAG_WINDOWS:
        lagged = df.shift(lag).add_suffix(f"_lag{lag}")
        parts.append(lagged)

    # Rolling mean and std
    for w in ROLLING_WINDOWS:
        rolled_mean = df.rolling(w, min_periods=w // 2).mean().add_suffix(f"_roll{w}m")
        rolled_std = df.rolling(w, min_periods=w // 2).std().add_suffix(f"_roll{w}s")
        parts.append(rolled_mean)
        parts.append(rolled_std)

    # Boolean interaction flags
    if "hindenburg_signal" in base.columns:
        hind_last20 = (
            base["hindenburg_signal"]
            .astype(int)
            .rolling(20, min_periods=1)
            .sum()
            .gt(0)
            .astype(int)
            .rename("hindenburg_last20d")
        )
        parts.append(hind_last20.to_frame())

    if "ftd_signal" in base.columns:
        ftd_last20 = (
            base["ftd_signal"]
            .astype(int)
            .rolling(20, min_periods=1)
            .sum()
            .gt(0)
            .astype(int)
            .rename("ftd_last20d")
        )
        parts.append(ftd_last20.to_frame())

    combined = pd.concat(parts, axis=1)
    combined = combined.sort_index()
    return combined
