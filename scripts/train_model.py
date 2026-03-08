#!/usr/bin/env python3
"""Stage 2: Train the LightGBM prediction model.

Placeholder — implements the training pipeline scaffold.
Full implementation in ml/ directory (Stage 2).

Usage:
    python scripts/train_model.py [--rebuild-features]
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("Stage 2 ML training pipeline — not yet implemented.")
    logger.info("Run backfill_data.py first to ensure sufficient historical data.")
    logger.info("Then implement ml/ directory (see plan Stage 4).")


if __name__ == "__main__":
    main()
