"""IBD Follow-Through Day (FTD) state machine.

States:
    NORMAL          → No active rally attempt
    ATTEMPTED_RALLY → Market is in a rally attempt (day 1+ from low)
    FTD             → Follow-Through Day confirmed
    FAILED          → Rally failed (undercut the low)

Transitions:
    NORMAL → ATTEMPTED_RALLY  : index closes higher than correction low day
    ATTEMPTED_RALLY → FTD     : Day 4+, up ≥1.25%, volume > prev day AND > 50d avg
    ATTEMPTED_RALLY → FAILED  : Undercuts the correction low at any point
    FTD → NORMAL              : After FTD, monitor for new correction
"""
from enum import Enum

import pandas as pd
import numpy as np


class FTDState(str, Enum):
    NORMAL = "NORMAL"
    ATTEMPTED_RALLY = "ATTEMPTED_RALLY"
    FTD = "FTD"
    FAILED = "FAILED"


def compute_ftd(
    close: pd.Series,
    volume: pd.Series,
    min_gain_pct: float = 1.25,
    min_rally_day: int = 4,
    vol_avg_window: int = 50,
    correction_threshold_pct: float = -5.0,
) -> pd.DataFrame:
    """Run FTD state machine on a single index.

    Args:
        close: Close price series.
        volume: Volume series (aligned with close).
        min_gain_pct: Minimum day gain % to qualify as FTD (default 1.25%).
        min_rally_day: Minimum rally day count before FTD can occur (default 4).
        vol_avg_window: Window for average volume comparison (default 50).
        correction_threshold_pct: % drawdown from recent high to start looking
            for rally attempts (default -5%).

    Returns:
        DataFrame with columns:
            - state: FTDState string for each day
            - rally_day: Day count within current rally attempt (0 if not rallying)
            - ftd_signal: True on FTD days
            - correction_low: Tracked correction low price
    """
    n = len(close)
    dates = close.index
    closes = close.values
    volumes = volume.values if volume is not None else np.ones(n)

    avg_vol = pd.Series(volumes).rolling(vol_avg_window, min_periods=10).mean().values

    states = [FTDState.NORMAL] * n
    rally_days = np.zeros(n, dtype=int)
    ftd_signals = np.zeros(n, dtype=bool)
    correction_lows = np.full(n, np.nan)

    state = FTDState.NORMAL
    correction_low = np.nan
    rally_start_day = -1
    peak_price = closes[0] if n > 0 else np.nan

    for i in range(1, n):
        c = closes[i]
        c_prev = closes[i - 1]
        v = volumes[i]
        v_prev = volumes[i - 1]
        v_avg = avg_vol[i]

        if state == FTDState.NORMAL:
            # Track rolling peak for correction detection
            peak_price = max(peak_price, c_prev) if not np.isnan(peak_price) else c_prev
            pct_from_peak = (c - peak_price) / peak_price * 100

            if pct_from_peak <= correction_threshold_pct:
                # We're in a correction; wait for a up day to start rally attempt
                correction_low = c
            elif not np.isnan(correction_low) and c > correction_low:
                # First up day off the low → rally attempt day 1
                state = FTDState.ATTEMPTED_RALLY
                rally_start_day = i
                # correction_low stays as tracking reference

        elif state == FTDState.ATTEMPTED_RALLY:
            # Update correction low if price makes new low
            if c < correction_low:
                correction_low = c

            # Check for undercut (failed)
            if c < correction_low:
                state = FTDState.FAILED

            else:
                rally_day = i - rally_start_day + 1
                rally_days[i] = rally_day

                # Check FTD conditions
                pct_gain = (c - c_prev) / c_prev * 100
                vol_above_prev = v > v_prev
                vol_above_avg = (not np.isnan(v_avg)) and (v > v_avg)

                if (
                    rally_day >= min_rally_day
                    and pct_gain >= min_gain_pct
                    and vol_above_prev
                    and vol_above_avg
                ):
                    state = FTDState.FTD
                    ftd_signals[i] = True

        elif state in (FTDState.FTD, FTDState.FAILED):
            # After FTD or failure, reset to NORMAL after one bar to allow
            # fresh detection. Track new peak from here.
            state = FTDState.NORMAL
            correction_low = np.nan
            peak_price = c
            rally_start_day = -1

        states[i] = state
        correction_lows[i] = correction_low

    return pd.DataFrame(
        {
            "ftd_state": [s.value for s in states],
            "rally_day": rally_days,
            "ftd_signal": ftd_signals,
            "correction_low": correction_lows,
        },
        index=dates,
    )
