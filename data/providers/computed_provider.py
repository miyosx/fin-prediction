"""Computes all breadth indicators from S&P 500 constituent OHLCV data.

Used as fallback when Yahoo Finance breadth tickers (^NYAD etc.) are unavailable.
Downloads constituent data once and derives:
  - Advance/Decline line (cumulative net advances)
  - Net New Highs/Lows (52-week)
  - Up/Down Volume
  - MM breadth: % stocks above 20/50/100/200 MA
"""
from __future__ import annotations

import logging

import pandas as pd
import numpy as np
import yfinance as yf

from .base import DataProvider

logger = logging.getLogger(__name__)

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NH_NL_WINDOW = 252  # trading days for 52-week new highs/lows


def _get_sp500_tickers() -> list[str]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
        tables = pd.read_html(SP500_WIKI_URL, storage_options={"User-Agent": headers["User-Agent"]})
        tickers = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
        return tickers
    except Exception as exc:
        logger.error("Failed to fetch S&P 500 list: %s", exc)
        return []


def _extract_field(raw: pd.DataFrame, field: str) -> pd.DataFrame:
    """Extract a single field from a multi-ticker yfinance download."""
    if isinstance(raw.columns, pd.MultiIndex):
        # yfinance >= 0.2: columns are (Field, Ticker) or (Ticker, Field)
        # Try both level orderings
        try:
            result = raw[field]
        except KeyError:
            result = raw.xs(field, axis=1, level=1)
    else:
        result = raw[[field]] if field in raw.columns else pd.DataFrame()
    result.index = pd.to_datetime(result.index).tz_localize(None)
    result.index.name = "Date"
    return result


class ComputedBreadthProvider(DataProvider):
    """Derives NYSE-style breadth from S&P 500 constituents via yfinance.

    Note: Results are S&P 500 approximations, not full NYSE breadth.
    """

    def is_available(self) -> bool:
        return True

    def fetch(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch a single breadth series by internal symbol name."""
        data = self.fetch_all(start, end)
        return data.get(symbol, pd.DataFrame())

    def fetch_all(self, start: str, end: str) -> dict[str, pd.DataFrame]:
        """Download constituents once and compute all breadth series.

        Automatically extends the download start date by the largest MA window
        (200 days + NH/NL window of 252 days) so indicators have enough warmup.
        Results are then trimmed back to the requested start date.
        """
        tickers = _get_sp500_tickers()
        if not tickers:
            return {}

        # Extend start for warmup (252 calendar days ≈ 180 trading days, use 400 to be safe)
        extended_start = (
            pd.Timestamp(start) - pd.tseries.offsets.BDay(400)
        ).strftime("%Y-%m-%d")

        logger.info("Downloading %d S&P 500 constituents (OHLCV, from %s)...", len(tickers), extended_start)
        raw = self._download(tickers, extended_start, end)
        if raw.empty:
            return {}

        closes = _extract_field(raw, "Close")
        volumes = _extract_field(raw, "Volume")

        # Drop tickers with <50% data coverage (across full window including warmup)
        min_obs = max(1, int(len(closes) * 0.5))
        closes = closes.dropna(axis=1, thresh=min_obs)
        volumes = volumes.reindex(columns=closes.columns).reindex(closes.index)

        result: dict[str, pd.DataFrame] = {}
        _start_ts = pd.Timestamp(start)

        # --- A/D Line ---
        result["NYAD"] = self._compute_ad_line(closes).loc[_start_ts:]

        # --- Net New Highs/Lows ---
        result["NAHL"] = self._compute_nhnl(closes).loc[_start_ts:]

        # --- Up/Down Volume ---
        upvol, dnvol = self._compute_updn_volume(closes, volumes)
        result["NYUPVOL"] = upvol.loc[_start_ts:]
        result["NYDNVOL"] = dnvol.loc[_start_ts:]

        # --- MM Breadth ---
        for sym, window in {"MMFD": 200, "MMTW": 20, "MMFI": 50, "MMTH": 100}.items():
            pct = self._pct_above_ma(closes, window)
            result[sym] = pct.to_frame(name="Close").loc[_start_ts:]

        return result

    # ------------------------------------------------------------------ #
    # Computation helpers
    # ------------------------------------------------------------------ #

    def _compute_ad_line(self, closes: pd.DataFrame) -> pd.DataFrame:
        """Cumulative (advances - declines) from daily price changes."""
        daily_change = closes.diff()
        advances = (daily_change > 0).sum(axis=1)
        declines = (daily_change < 0).sum(axis=1)
        net = (advances - declines).astype(float)
        ad_line = net.cumsum()
        ad_line.name = "Close"
        return ad_line.to_frame()

    def _compute_nhnl(self, closes: pd.DataFrame) -> pd.DataFrame:
        """Net new 52-week highs minus lows (as Close column)."""
        rolling_high = closes.rolling(NH_NL_WINDOW, min_periods=NH_NL_WINDOW // 2).max()
        rolling_low = closes.rolling(NH_NL_WINDOW, min_periods=NH_NL_WINDOW // 2).min()
        new_highs = (closes >= rolling_high).sum(axis=1)
        new_lows = (closes <= rolling_low).sum(axis=1)
        net = (new_highs - new_lows).astype(float)
        net.name = "Close"
        return net.to_frame()

    def _compute_updn_volume(
        self, closes: pd.DataFrame, volumes: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Sum volume of advancing vs declining stocks."""
        daily_change = closes.diff()
        up_mask = daily_change > 0
        dn_mask = daily_change < 0
        upvol = volumes.where(up_mask, 0).sum(axis=1).astype(float)
        dnvol = volumes.where(dn_mask, 0).sum(axis=1).astype(float)
        return upvol.rename("Close").to_frame(), dnvol.rename("Close").to_frame()

    def _pct_above_ma(self, closes: pd.DataFrame, window: int) -> pd.Series:
        ma = closes.rolling(window=window, min_periods=window // 2).mean()
        above = (closes > ma).astype(float)
        pct = above.mean(axis=1) * 100
        pct.name = f"pct_above_{window}ma"
        return pct

    def _download(self, tickers: list[str], start: str, end: str) -> pd.DataFrame:
        try:
            raw = yf.download(
                tickers,
                start=start,
                end=end,
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
            )
            return raw
        except Exception as exc:
            logger.error("Constituent download failed: %s", exc)
            return pd.DataFrame()


# Keep old name as alias so existing imports don't break
ComputedMMProvider = ComputedBreadthProvider
