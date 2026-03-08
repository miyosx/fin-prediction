"""Page 5: Lowry Up/Down Volume and 90% Day Analysis."""
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
from indicators.lowry import up_down_vol_ratio, consecutive_90pct_days

st.set_page_config(page_title="Lowry Analysis", layout="wide")
init_session_state()
freshness_banner(force_key="refresh_lowry")

st.title("Lowry Research — Up/Down Volume Analysis")

with st.spinner("Loading volume breadth data..."):
    upvol_df = fetch_breadth("NYUPVOL")
    dnvol_df = fetch_breadth("NYDNVOL")

if upvol_df.empty or dnvol_df.empty:
    st.error("Up/Down volume data unavailable. Click 'Refresh All Data'.")
    st.stop()

upvol = upvol_df["Close"]
dnvol = dnvol_df["Close"]

lowry_df = up_down_vol_ratio(upvol, dnvol)

# Signal cards
latest = lowry_df.iloc[-1]
up_pct = latest.get("up_pct", float("nan"))
dn_pct = latest.get("dn_pct", float("nan"))
roll_col = "rolling_up_ratio_90d"
roll_up = latest.get(roll_col, float("nan"))

up_zone = "bullish" if up_pct >= 90 else "bearish" if up_pct <= 30 else "neutral"
dn_zone = "bearish" if dn_pct >= 90 else "neutral"
trend_zone = "bullish" if roll_up > 55 else "bearish" if roll_up < 45 else "neutral"

signal_grid([
    {"title": "Today Up Vol %", "value": round(up_pct, 1), "zone": up_zone, "subtitle": "≥90% = 90% Day"},
    {"title": "Today Down Vol %", "value": round(dn_pct, 1), "zone": dn_zone},
    {"title": "90-Day Avg Up %", "value": round(roll_up, 1), "zone": trend_zone},
    {"title": "90% Up Days (30d)", "value": int(consecutive_90pct_days(lowry_df, "up", 30).iloc[-1])},
    {"title": "90% Down Days (30d)", "value": int(consecutive_90pct_days(lowry_df, "dn", 30).iloc[-1])},
])

st.markdown("---")

years = st.sidebar.slider("Years of history", 1, 25, 5)
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
df_plot = lowry_df[lowry_df.index >= cutoff]

# Up/Down % line
st.plotly_chart(
    line_chart(
        {"Up Vol %": df_plot["up_pct"], "Down Vol %": df_plot["dn_pct"]},
        title="Daily Up/Down Volume %",
        height=300,
    ),
    use_container_width=True,
)

# 90-day rolling ratio
st.plotly_chart(
    line_chart(
        {f"Rolling {90}d Up %": df_plot[roll_col]},
        title=f"90-Day Rolling Up Volume % (trend: >55% bullish, <45% bearish)",
        height=250,
    ),
    use_container_width=True,
)

# 90% day markers
up90 = df_plot[df_plot["is_90pct_up_day"]]["up_pct"]
dn90 = df_plot[df_plot["is_90pct_dn_day"]]["dn_pct"]

col1, col2 = st.columns(2)
with col1:
    st.markdown("#### 90% Up Days")
    st.dataframe(
        up90.reset_index().rename(columns={"Date": "Date", "up_pct": "Up %"}).sort_values("Date", ascending=False),
        use_container_width=True, hide_index=True,
    )
with col2:
    st.markdown("#### 90% Down Days")
    st.dataframe(
        dn90.reset_index().rename(columns={"Date": "Date", "dn_pct": "Down %"}).sort_values("Date", ascending=False),
        use_container_width=True, hide_index=True,
    )
