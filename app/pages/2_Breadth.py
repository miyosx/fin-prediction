"""Page 2: Advance-Decline Line, McClellan Oscillator & Summation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from app.state import init_session_state
from app.components.charts import line_chart, oscillator_chart, render
from app.components.signal_card import signal_grid
from app.components.data_freshness import freshness_banner
from data.fetchers.breadth_fetcher import fetch_breadth
from indicators.advance_decline import compute_all as compute_ad

st.set_page_config(page_title="Breadth", layout="wide")
init_session_state()
freshness_banner(force_key="refresh_breadth")

st.title("Market Breadth — A/D Line & McClellan")

with st.spinner("Loading breadth data..."):
    nyad_df = fetch_breadth("NYAD")

if nyad_df.empty or "Close" not in nyad_df.columns:
    st.error("No A/D data available. Click **Refresh All Data** in the sidebar.")
    st.info("If refresh fails, yfinance may not support `^NYAD` in your region, or the symbol is temporarily unavailable. Check the sidebar for which symbols failed.")
    st.stop()

ad_line = nyad_df["Close"]
ad_df = compute_ad(ad_line)

# Signal cards
latest = ad_df.iloc[-1]
mco_val = latest.get("mcclellan_oscillator", float("nan"))
mcs_val = latest.get("mcclellan_summation", float("nan"))
net_val = latest.get("net_advances", float("nan"))

mco_zone = "bullish" if mco_val > 50 else "bearish" if mco_val < -50 else "neutral"
mcs_zone = "bullish" if mcs_val > 0 else "bearish"

signal_grid([
    {"title": "McClellan Oscillator", "value": round(mco_val, 0), "zone": mco_zone},
    {"title": "McClellan Summation", "value": round(mcs_val, 0), "zone": mcs_zone},
    {"title": "Daily Net Advances", "value": round(net_val, 0), "zone": "neutral"},
])

st.markdown("---")

# Date range
years = st.sidebar.slider("Years of history", 1, 25, 5)
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
ad_plot = ad_df[ad_df.index >= cutoff]

# A/D Line
render(line_chart({"Cumulative A/D Line": ad_plot["ad_line"]},
                  title="NYSE Cumulative Advance-Decline Line", height=350))

# McClellan Oscillator
col_osc, col_osc_help = st.columns([8, 1])
with col_osc:
    st.subheader("McClellan Oscillator")
with col_osc_help:
    with st.popover("?"):
        st.markdown("""
**McClellan Oscillator** = EMA(19) − EMA(39) of daily net advances

**Net advances** = number of stocks closing up minus stocks closing down each day.
Think of it as MACD applied to market breadth instead of price.

| Reading | Meaning |
|---|---|
| Above 0 | More stocks rising — positive breadth momentum |
| Below 0 | More stocks falling — negative breadth momentum |
| Above +100 | Strong buying surge; breadth expanding fast |
| Below −100 | Selling pressure is broad; breadth collapsing |
| Cross above 0 | Short-term buy signal |
| Cross below 0 | Short-term sell signal |
| Extreme ±150+ | Climactic move — often precedes a reversal |

**Divergence tip:** If SPX makes a new high but this oscillator makes a lower high, breadth is narrowing — a warning sign.
        """)
render(oscillator_chart(ad_plot["mcclellan_oscillator"],
                        title="McClellan Oscillator (EMA19 - EMA39 of Net Advances)",
                        height=280))

# McClellan Summation
col_summ, col_summ_help = st.columns([8, 1])
with col_summ:
    st.subheader("McClellan Summation Index")
with col_summ_help:
    with st.popover("?"):
        st.markdown("""
**McClellan Summation Index** = running cumulative sum of the McClellan Oscillator

If the Oscillator is momentum, the Summation Index is trend.

| Reading | Meaning |
|---|---|
| Above 0 and rising | Healthy bull market; broad participation |
| Below 0 and falling | Bear market internals |
| Cross above 0 | Major buy signal — breadth trend turned positive |
| Cross below 0 | Major sell signal — breadth trend turned negative |
| Above +1000 | Overbought; market extended, watch for stall |
| Below −1000 | Oversold; conditions ripe for a breadth thrust reversal |

**Breadth thrust:** A rapid move from below −500 to above +500 within a few weeks is historically very bullish.
        """)
render(line_chart(
    {"McClellan Summation": ad_plot["mcclellan_summation"]},
    title="McClellan Summation Index",
    zero_line=True,
    height=280,
))

with st.expander("Raw Data"):
    st.dataframe(ad_plot.tail(60).sort_index(ascending=False), use_container_width=True)
