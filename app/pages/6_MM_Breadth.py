"""Page 6: MM Breadth — MMFD, MMTW, MMFI, MMTH panels."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from app.state import init_session_state
from app.components.charts import zone_area_chart, render
from app.components.signal_card import signal_grid
from app.components.data_freshness import freshness_banner
from data.fetchers.mm_breadth_fetcher import fetch_all_mm
from indicators.mm_breadth import THRESHOLDS, compute_all as compute_mm

st.set_page_config(page_title="MM Breadth", layout="wide")
init_session_state()
freshness_banner(force_key="refresh_mm")

st.title("MM Breadth — % Stocks Above Key Moving Averages")

st.info("""
**Data source**: Approximated from S&P 500 constituents via yfinance (Tier 1).
For full NYSE breadth, drop CSV exports into `data/manual_imports/` or set `EODHD_API_KEY`.
""")

with st.spinner("Loading MM breadth data (may take a moment on first load)..."):
    mm_data = fetch_all_mm()

if not mm_data or all(df.empty for df in mm_data.values()):
    st.error("MM breadth data unavailable. This may take a moment to compute from S&P 500 constituents.")
    st.stop()

mm_df = compute_mm(mm_data)

# Signal cards
symbols = ["MMFD", "MMTW", "MMFI", "MMTH"]
labels = {
    "MMFD": "% Above 200MA",
    "MMTW": "% Above 20MA",
    "MMFI": "% Above 50MA",
    "MMTH": "% Above 100MA",
}
cards = []
for sym in symbols:
    if sym in mm_df.columns:
        val = mm_df[sym].iloc[-1]
        zone = mm_df[f"{sym}_zone"].iloc[-1] if f"{sym}_zone" in mm_df.columns else "neutral"
        cards.append({"title": labels[sym], "value": round(val, 1), "zone": zone, "subtitle": f"{sym}"})

if cards:
    signal_grid(cards)
    st.markdown("---")

years = st.sidebar.slider("Years of history", 1, 10, 3)
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)

# One chart per symbol in a 2×2 grid
col1, col2 = st.columns(2)
pairs = [("MMFD", col1), ("MMTW", col2), ("MMFI", col1), ("MMTH", col2)]

for sym, col in pairs:
    if sym not in mm_df.columns:
        continue
    series = mm_df[sym][mm_df.index >= cutoff]
    if series.empty:
        continue
    with col:
        st.plotly_chart(
            zone_area_chart(
                series,
                sym,
                THRESHOLDS[sym],
                title=f"{sym} — {labels[sym]}",
                height=320,
            ),
            use_container_width=True,
        )

with st.expander("Raw MM Breadth Data"):
    if not mm_df.empty:
        val_cols = [c for c in mm_df.columns if not c.endswith("_zone")]
        st.dataframe(mm_df[val_cols].tail(60).sort_index(ascending=False), use_container_width=True)
