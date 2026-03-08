"""Assembles all indicator outputs into a single feature_matrix parquet file."""
import logging
from pathlib import Path

import pandas as pd

from config.settings import settings
from data.fetchers.index_fetcher import fetch_all_indices
from data.fetchers.breadth_fetcher import fetch_all_breadth
from data.fetchers.mm_breadth_fetcher import fetch_all_mm
from indicators import (
    ma_distance,
    advance_decline,
    net_new_highs,
    hindenburg,
    follow_through_day,
    lowry,
    mm_breadth,
)

logger = logging.getLogger(__name__)

FEATURE_MATRIX_PATH = settings.root_dir / "data" / "feature_matrix.parquet"


def build_feature_matrix(force_refresh: bool = False) -> pd.DataFrame:
    """Compute and persist the full feature matrix.

    Returns:
        Combined DataFrame with all indicator columns, indexed by Date.
    """
    if not force_refresh and FEATURE_MATRIX_PATH.exists():
        logger.info("Loading cached feature matrix from %s", FEATURE_MATRIX_PATH)
        return pd.read_parquet(FEATURE_MATRIX_PATH)

    logger.info("Building feature matrix from scratch...")

    # --- Fetch raw data ---
    indices = fetch_all_indices()
    breadth = fetch_all_breadth()
    mm_data = fetch_all_mm()

    parts: list[pd.DataFrame] = []

    # --- MA Distance ---
    index_closes = {}
    for name, df in indices.items():
        if not df.empty and "Close" in df.columns:
            index_closes[name] = df["Close"]
    if index_closes:
        ma_df = ma_distance.ma_distance_all(index_closes)
        parts.append(ma_df)

    # --- SPX close (used for FTD and targets) ---
    if "SPX" in indices and not indices["SPX"].empty:
        spx = indices["SPX"]
        parts.append(spx[["Close"]].rename(columns={"Close": "spx_close"}))
        if "Volume" in spx.columns:
            parts.append(spx[["Volume"]].rename(columns={"Volume": "spx_volume"}))

    # --- A/D and McClellan ---
    if "NYAD" in breadth and not breadth["NYAD"].empty:
        ad_line = breadth["NYAD"]["Close"]
        ad_df = advance_decline.compute_all(ad_line)
        parts.append(ad_df)
        mco = ad_df["mcclellan_oscillator"]
    else:
        mco = pd.Series(dtype=float)

    # --- Net New Highs/Lows ---
    if "NAHL" in breadth and not breadth["NAHL"].empty:
        nahl = breadth["NAHL"]["Close"]
        nhnl_df = net_new_highs.compute_all(nahl)
        parts.append(nhnl_df)
    else:
        nahl = pd.Series(dtype=float)

    # --- Hindenburg Omen ---
    if (
        "NYA" in indices
        and not indices["NYA"].empty
        and not nahl.empty
        and not mco.empty
    ):
        hind_df = hindenburg.compute_all(
            nya_close=indices["NYA"]["Close"],
            nahl_net=nahl,
            mcclellan_osc=mco,
        )
        parts.append(hind_df)

    # --- Follow-Through Day (SPX) ---
    if "SPX" in indices and not indices["SPX"].empty:
        spx = indices["SPX"]
        if "Close" in spx.columns and "Volume" in spx.columns:
            ftd_df = follow_through_day.compute_ftd(spx["Close"], spx["Volume"])
            parts.append(ftd_df)

    # --- Lowry Up/Down Volume ---
    if (
        "NYUPVOL" in breadth
        and not breadth["NYUPVOL"].empty
        and "NYDNVOL" in breadth
        and not breadth["NYDNVOL"].empty
    ):
        upvol = breadth["NYUPVOL"]["Close"]
        dnvol = breadth["NYDNVOL"]["Close"]
        lowry_df = lowry.up_down_vol_ratio(upvol, dnvol)
        parts.append(lowry_df)

    # --- MM Breadth ---
    if mm_data:
        mm_df = mm_breadth.compute_all(mm_data)
        if not mm_df.empty:
            parts.append(mm_df)

    # --- Combine ---
    if not parts:
        logger.warning("No data to assemble in feature matrix")
        return pd.DataFrame()

    combined = pd.concat(parts, axis=1, join="outer")
    combined = combined.sort_index()
    combined.index.name = "Date"

    # Persist
    FEATURE_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(FEATURE_MATRIX_PATH, engine="pyarrow", compression="snappy")
    logger.info("Feature matrix saved: %s (%d rows × %d cols)", FEATURE_MATRIX_PATH, *combined.shape)

    return combined
