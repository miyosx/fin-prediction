"""Page 2: Advance-Decline Line, McClellan Oscillator & Summation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from app.state import init_session_state
from app.components.charts import line_chart, oscillator_chart
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
st.plotly_chart(
    line_chart({"Cumulative A/D Line": ad_plot["ad_line"]},
               title="NYSE Cumulative Advance-Decline Line", height=350),
    use_container_width=True,
)

# McClellan Oscillator
st.plotly_chart(
    oscillator_chart(ad_plot["mcclellan_oscillator"],
                     title="McClellan Oscillator (EMA19 - EMA39 of Net Advances)",
                     height=280),
    use_container_width=True,
)

# McClellan Summation
st.plotly_chart(
    line_chart(
        {"McClellan Summation": ad_plot["mcclellan_summation"]},
        title="McClellan Summation Index",
        zero_line=True,
        height=280,
    ),
    use_container_width=True,
)

with st.expander("Raw Data"):
    st.dataframe(ad_plot.tail(60).sort_index(ascending=False), use_container_width=True)
