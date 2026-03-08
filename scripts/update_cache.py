#!/usr/bin/env python3
"""Daily cache update — suitable for cron/launchd.

Usage:
    python scripts/update_cache.py

Add to crontab (runs at 6pm on weekdays):
    0 18 * * 1-5 cd /Users/miyos/00_C/Fin/Prediction && python scripts/update_cache.py
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.cache import cache_manager
from data.fetchers.mm_breadth_fetcher import fetch_all_mm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Running daily cache update...")
    results = cache_manager.refresh_all(force=True)
    ok = sum(v for v in results.values())
    total = len(results)
    logger.info("Standard symbols: %d/%d refreshed", ok, total)

    logger.info("Refreshing MM breadth...")
    mm_data = fetch_all_mm(force_refresh=True)
    mm_ok = sum(1 for df in mm_data.values() if not df.empty)
    logger.info("MM breadth: %d/4 series updated", mm_ok)

    logger.info("Update complete.")


if __name__ == "__main__":
    main()
