#!/usr/bin/env python3
"""One-time historical data download from 2000 to present.

Usage:
    python scripts/backfill_data.py [--start 2000-01-01] [--force]
"""
import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.symbols import ALL_YFINANCE_SYMBOLS
from data.cache import cache_manager
from data.fetchers.mm_breadth_fetcher import fetch_all_mm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Backfill market data")
    parser.add_argument("--start", default="2000-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Force re-download even if cached")
    args = parser.parse_args()

    logger.info("Starting backfill from %s", args.start)

    # Standard symbols (indices + NYSE breadth)
    success = 0
    for sym in ALL_YFINANCE_SYMBOLS:
        logger.info("Fetching %s...", sym)
        df = cache_manager.get_or_fetch(sym, start=args.start, force_refresh=args.force)
        if not df.empty:
            logger.info("  → %d rows", len(df))
            success += 1
        else:
            logger.warning("  → No data returned for %s", sym)

    logger.info("Standard symbols: %d/%d successful", success, len(ALL_YFINANCE_SYMBOLS))

    # MM Breadth (may be slow — downloads all S&P 500 constituents)
    logger.info("Computing MM breadth from S&P 500 constituents...")
    mm_data = fetch_all_mm(start=args.start, force_refresh=args.force)
    mm_ok = sum(1 for df in mm_data.values() if not df.empty)
    logger.info("MM breadth: %d/4 series computed", mm_ok)

    logger.info("Backfill complete.")


if __name__ == "__main__":
    main()
