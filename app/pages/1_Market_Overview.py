"""Page 1: Market Overview — index prices and % above/below 200 MA."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from app.state import init_session_state
from app.components.charts import price_chart, line_chart, render
from app.components.signal_card import signal_grid
from app.components.data_freshness import freshness_banner
from data.fetchers.index_fetcher import fetch_all_indices
from indicators.ma_distance import ma_distance_all

st.set_page_config(page_title="Market Overview", layout="wide")
init_session_state()
freshness_banner(force_key="refresh_overview")

st.title("Market Overview — % Above/Below 200-Day MA")

with st.spinner("Loading index data..."):
    indices = fetch_all_indices()

if not indices:
    st.error("No index data available. Click 'Refresh All Data' in the sidebar.")
    st.stop()

# Compute MA distances
index_closes = {
    name: df["Close"]
    for name, df in indices.items()
    if not df.empty and "Close" in df.columns
}
ma_df = ma_distance_all(index_closes) if index_closes else pd.DataFrame()

# Signal cards: current % distance
if not ma_df.empty:
    latest = ma_df.iloc[-1]
    cards = []
    for col in ma_df.columns:
        val = latest.get(col, float("nan"))
        if pd.isna(val):
            zone = "unknown"
        elif val > 10:
            zone = "bullish"
        elif val < -5:
            zone = "bearish"
        else:
            zone = "neutral"
        name = col.replace("_pct_dist_200ma", "")
        cards.append({"title": f"{name} vs 200MA", "value": round(val, 1), "zone": zone, "subtitle": "%"})
    signal_grid(cards)
    st.markdown("---")

# Date range selector
st.sidebar.markdown("### Chart Options")
years = st.sidebar.slider("Years of history", min_value=1, max_value=25, value=5)
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)

# Select index to chart
selected = st.selectbox("Select Index", list(indices.keys()))
if selected and selected in indices:
    df = indices[selected]
    if not df.empty:
        df_plot = df[df.index >= cutoff]
        render(price_chart(df_plot, title=f"{selected} Price", ma_windows=[50, 200], height=450))

# MA Distance chart (all indices)
if not ma_df.empty:
    ma_plot = ma_df[ma_df.index >= cutoff]
    series_dict = {
        col.replace("_pct_dist_200ma", ""): ma_plot[col].dropna()
        for col in ma_plot.columns
    }
    st.plotly_chart(
        line_chart(series_dict, title="% Distance from 200-Day MA (all indices)",
                   zero_line=True, height=350),
        use_container_width=True,
    )

# Raw data expander
with st.expander("Raw MA Distance Data"):
    if not ma_df.empty:
        st.dataframe(ma_df.tail(60).sort_index(ascending=False), use_container_width=True)
