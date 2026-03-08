"""yfinance-backed data provider."""
import logging

import pandas as pd
import yfinance as yf

from .base import DataProvider

logger = logging.getLogger(__name__)


class YFinanceProvider(DataProvider):
    """Fetches data from Yahoo Finance via yfinance."""

    def is_available(self) -> bool:
        return True  # Always available (free, no key needed)

    def fetch(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end, auto_adjust=True)
            if df.empty:
                logger.warning("No data returned for %s", symbol)
                return pd.DataFrame()
            # Normalize index to timezone-naive dates
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df.index.name = "Date"
            # Keep standard OHLCV columns
            cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            return df[cols]
        except Exception as exc:
            logger.error("yfinance fetch failed for %s: %s", symbol, exc)
            return pd.DataFrame()

    def fetch_multiple(
        self, symbols: list[str], start: str, end: str
    ) -> dict[str, pd.DataFrame]:
        """Batch download for efficiency."""
        if not symbols:
            return {}
        try:
            raw = yf.download(
                symbols,
                start=start,
                end=end,
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
            )
            result: dict[str, pd.DataFrame] = {}
            if len(symbols) == 1:
                sym = symbols[0]
                df = raw.copy()
                df.index = pd.to_datetime(df.index).tz_localize(None)
                df.index.name = "Date"
                cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                result[sym] = df[cols] if cols else pd.DataFrame()
            else:
                for sym in symbols:
                    try:
                        df = raw[sym].dropna(how="all").copy()
                        df.index = pd.to_datetime(df.index).tz_localize(None)
                        df.index.name = "Date"
                        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                        result[sym] = df[cols] if cols else pd.DataFrame()
                    except KeyError:
                        logger.warning("Symbol %s not found in batch download", sym)
                        result[sym] = pd.DataFrame()
            return result
        except Exception as exc:
            logger.error("Batch download failed: %s. Falling back to individual.", exc)
            return super().fetch_multiple(symbols, start, end)
