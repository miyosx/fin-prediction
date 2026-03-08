"""Abstract base class for all data providers."""
from abc import ABC, abstractmethod

import pandas as pd


class DataProvider(ABC):
    """Base class that all data providers must implement."""

    @abstractmethod
    def fetch(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol.

        Returns a DataFrame with columns: Open, High, Low, Close, Volume
        indexed by Date (DatetimeIndex, timezone-naive).
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider can be used (API keys present, etc.)."""

    def fetch_multiple(
        self, symbols: list[str], start: str, end: str
    ) -> dict[str, pd.DataFrame]:
        """Fetch multiple symbols. Default: calls fetch() in a loop."""
        return {sym: self.fetch(sym, start, end) for sym in symbols}
