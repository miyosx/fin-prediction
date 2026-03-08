"""EODHD API provider (Tier 3, optional paid data)."""
import logging

import pandas as pd
import requests

from config.settings import settings
from .base import DataProvider

logger = logging.getLogger(__name__)

EODHD_BASE_URL = "https://eodhd.com/api"

# Map our internal names to EODHD symbols
EODHD_SYMBOL_MAP = {
    "MMFD": "MMFD.INDIC",
    "MMTW": "MMTW.INDIC",
    "MMFI": "MMFI.INDIC",
    "MMTH": "MMTH.INDIC",
}


class EODHDProvider(DataProvider):
    """Fetches MM breadth data from EODHD API."""

    def is_available(self) -> bool:
        return bool(settings.eodhd_api_key)

    def fetch(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        if not self.is_available():
            return pd.DataFrame()

        eodhd_sym = EODHD_SYMBOL_MAP.get(symbol, symbol)
        exchange = eodhd_sym.split(".")[-1] if "." in eodhd_sym else "US"
        ticker = eodhd_sym.split(".")[0]

        url = f"{EODHD_BASE_URL}/eod/{ticker}.{exchange}"
        params = {
            "api_token": settings.eodhd_api_key,
            "from": start,
            "to": end,
            "fmt": "json",
            "period": "d",
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data)
            df["Date"] = pd.to_datetime(df["date"])
            df = df.set_index("Date")
            df = df.rename(columns={"close": "Close", "open": "Open",
                                     "high": "High", "low": "Low", "volume": "Volume"})
            cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            return df[cols]
        except Exception as exc:
            logger.error("EODHD fetch failed for %s: %s", symbol, exc)
            return pd.DataFrame()
