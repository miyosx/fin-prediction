#!/usr/bin/env python3
"""Validate indicator outputs against known historical signal dates.

Known reference dates:
- Hindenburg Omen cluster: August 2010
- Major bear markets: 2000-03, 2007-10, 2020-03

Usage:
    python scripts/validate_indicators.py
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from data.fetchers.index_fetcher import fetch_index
from data.fetchers.breadth_fetcher import fetch_breadth
from indicators.advance_decline import compute_all as compute_ad
from indicators.hindenburg import compute_all as compute_hind

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def validate_hindenburg():
    """Check that Hindenburg Omen fires around August 2010 (known cluster)."""
    logger.info("=== Hindenburg Omen Validation ===")

    nya = fetch_index("NYA")
    nahl = fetch_breadth("NAHL")
    nyad = fetch_breadth("NYAD")

    if any(df.empty for df in [nya, nahl, nyad]):
        logger.error("Missing data — run backfill_data.py first")
        return

    ad_df = compute_ad(nyad["Close"])
    hind_df = compute_hind(nya["Close"], nahl["Close"], ad_df["mcclellan_oscillator"])

    # Check August–October 2010 window
    window = hind_df["2010-07":"2010-11"]
    signals_in_window = window[window["hindenburg_signal"] == True]
    clusters_in_window = window[window["hindenburg_cluster"] == True]

    logger.info("Signals in Aug–Nov 2010: %d", len(signals_in_window))
    logger.info("Cluster days in Aug–Nov 2010: %d", len(clusters_in_window))

    if len(signals_in_window) >= 2:
        logger.info("PASS: Hindenburg cluster detected in expected window")
    else:
        logger.warning("WARN: Fewer signals than expected. Data quality may be limited (^NAHL is net only)")

    if not signals_in_window.empty:
        logger.info("Signal dates:\n%s", signals_in_window.index.tolist())


def validate_ma_distance():
    """Check SPX % distance from 200MA at known extreme dates."""
    logger.info("=== MA Distance Validation ===")

    from indicators.ma_distance import pct_above_200ma
    spx = fetch_index("SPX")

    if spx.empty:
        logger.error("No SPX data")
        return

    dist = pct_above_200ma(spx["Close"])

    # March 2009 low should be deeply negative (SPX was ~40% below 200MA)
    mar2009 = dist.get("2009-03-09", None)
    if mar2009 is not None:
        logger.info("SPX %% dist 200MA on 2009-03-09: %.1f%%", mar2009)
        if mar2009 < -30:
            logger.info("PASS: Deep negative distance at 2009 low")
        else:
            logger.warning("WARN: Expected <-30%%, got %.1f%%", mar2009)

    # Jan 2022 peak should be moderately positive
    jan2022 = dist.get("2022-01-03", None)
    if jan2022 is not None:
        logger.info("SPX %% dist 200MA on 2022-01-03: %.1f%%", jan2022)


if __name__ == "__main__":
    validate_hindenburg()
    validate_ma_distance()
    logger.info("Validation complete.")
