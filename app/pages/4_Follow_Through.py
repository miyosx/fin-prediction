"""Page 4: IBD Follow-Through Day detection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from app.state import init_session_state
from app.components.charts import signal_scatter, line_chart
from app.components.signal_card import signal_grid
from app.components.data_freshness import freshness_banner
from data.fetchers.index_fetcher import fetch_index
from indicators.follow_through_day import compute_ftd

st.set_page_config(page_title="Follow-Through Day", layout="wide")
init_session_state()
freshness_banner(force_key="refresh_ftd")

st.title("IBD Follow-Through Day Detector")

st.info("""
**Follow-Through Day (FTD)**: IBD methodology to identify potential market bottoms.
- Day 1: Market closes higher than the correction low.
- Day 4+: Index gains ≥1.25% on higher volume than prior day AND above 50-day average.
""")

with st.spinner("Loading SPX data..."):
    spx_df = fetch_index("SPX")

if spx_df.empty or "Close" not in spx_df.columns:
    st.error("SPX data unavailable. Click 'Refresh All Data'.")
    st.stop()

volume = spx_df["Volume"] if "Volume" in spx_df.columns else pd.Series(dtype=float)
ftd_df = compute_ftd(spx_df["Close"], volume)

# Current state
latest = ftd_df.iloc[-1]
state = latest["ftd_state"]
rally_day = int(latest["rally_day"])

state_zone = {"FTD": "bullish", "ATTEMPTED_RALLY": "neutral",
              "FAILED": "bearish", "NORMAL": "neutral"}.get(state, "neutral")

signal_grid([
    {"title": "Current State", "value": state, "zone": state_zone},
    {"title": "Rally Day #", "value": rally_day if rally_day > 0 else "—"},
    {"title": "FTD Signals (all time)", "value": int(ftd_df["ftd_signal"].sum())},
])

st.markdown("---")

years = st.sidebar.slider("Years of history", 1, 25, 5)
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)

ftd_plot = ftd_df[ftd_df.index >= cutoff]
spx_plot = spx_df[spx_df.index >= cutoff]["Close"]

ftd_dates = ftd_plot[ftd_plot["ftd_signal"] == True].index

st.plotly_chart(
    signal_scatter(spx_plot, ftd_dates, title="SPX with Follow-Through Day Signals",
                   signal_name="FTD Signal"),
    use_container_width=True,
)

# Rally day counter over time (when in rally attempt)
rally_days_series = ftd_plot["rally_day"].replace(0, None)
if rally_days_series.notna().any():
    st.plotly_chart(
        line_chart({"Rally Day #": rally_days_series},
                   title="Current Rally Attempt Day Count", height=200),
        use_container_width=True,
    )

with st.expander("All FTD Signal Dates"):
    all_ftds = ftd_df[ftd_df["ftd_signal"] == True][["ftd_state", "rally_day"]]
    st.dataframe(all_ftds.sort_index(ascending=False), use_container_width=True)
