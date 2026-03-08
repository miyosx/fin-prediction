"""Page 2: Advance-Decline Line, McClellan Oscillator & Summation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.state import init_session_state
from app.components.charts import line_chart, COLORS
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
    st.info("If refresh fails, check the sidebar for which symbols failed.")
    st.stop()

ad_line = nyad_df["Close"]
ad_df = compute_ad(ad_line)

# ------------------------------------------------------------------ #
# Signal cards
# ------------------------------------------------------------------ #
latest = ad_df.iloc[-1]
mco_val = latest.get("mcclellan_oscillator", float("nan"))
mcs_val = latest.get("mcclellan_summation", float("nan"))
net_val = latest.get("net_advances", float("nan"))

mco_zone = "bullish" if mco_val > 100 else "bearish" if mco_val < -100 else "neutral"
mcs_zone = "bullish" if mcs_val > 500 else "bearish" if mcs_val < -500 else "neutral"

signal_grid([
    {"title": "McClellan Oscillator", "value": round(mco_val, 0), "zone": mco_zone,
     "subtitle": "Signal: cross ±100"},
    {"title": "McClellan Summation", "value": round(mcs_val, 0), "zone": mcs_zone,
     "subtitle": "Signal: cross 0 / ±1000"},
    {"title": "Daily Net Advances", "value": round(net_val, 0), "zone": "neutral"},
])

st.markdown("---")

# ------------------------------------------------------------------ #
# Sidebar
# ------------------------------------------------------------------ #
years = st.sidebar.slider("Years of history", 1, 25, 5)
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
ad_plot = ad_df[ad_df.index >= cutoff]

# ------------------------------------------------------------------ #
# A/D Line
# ------------------------------------------------------------------ #
st.subheader("Cumulative Advance-Decline Line")
st.plotly_chart(
    line_chart({"Cumulative A/D Line": ad_plot["ad_line"]},
               title="NYSE Cumulative A/D Line — rising = broad participation, falling = narrowing",
               height=320),
    use_container_width=True,
)

# ------------------------------------------------------------------ #
# McClellan Oscillator
# ------------------------------------------------------------------ #
col_title, col_help = st.columns([6, 1])
with col_title:
    st.subheader("McClellan Oscillator")
with col_help:
    st.write("")  # vertical align
    with st.popover("What is this?"):
        st.markdown("""
**McClellan Oscillator** = EMA(19) − EMA(39) of daily net advances

**Net advances** = stocks closing up − stocks closing down, each day.

Think of it as **MACD applied to market breadth** instead of price.

---
**How to read it:**

| Reading | Meaning |
|---|---|
| **Above 0** | More stocks rising than falling — positive breadth momentum |
| **Below 0** | More stocks falling — negative breadth momentum |
| **Above +100** | 🟢 Strong buying surge; breadth is expanding fast |
| **Below −100** | 🔴 Selling pressure is broad; breadth collapsing |
| **Cross above 0** | Short-term buy signal |
| **Cross below 0** | Short-term sell signal |
| **Extreme ±150+** | Climactic move — often precedes a reversal |

---
**Divergence from price:**
If SPX makes a new high but the oscillator makes a lower high → breadth is narrowing → warning sign.
        """)

osc = ad_plot["mcclellan_oscillator"]
colors = [COLORS["up"] if v >= 0 else COLORS["down"] for v in osc.values]

fig_osc = go.Figure()
fig_osc.add_trace(go.Bar(
    x=osc.index, y=osc.values, marker_color=colors, name="McClellan Oscillator",
    opacity=0.85,
))

# Signal zones
fig_osc.add_hrect(y0=100, y1=osc.max() * 1.1 if osc.max() > 100 else 200,
                  fillcolor=COLORS["bullish"], opacity=0.06, line_width=0,
                  annotation_text="Overbought / Climactic surge", annotation_position="top left")
fig_osc.add_hrect(y0=osc.min() * 1.1 if osc.min() < -100 else -200, y1=-100,
                  fillcolor=COLORS["bearish"], opacity=0.06, line_width=0,
                  annotation_text="Oversold / Climactic selling", annotation_position="bottom left")

# Key reference lines
fig_osc.add_hline(y=0,    line=dict(color="rgba(200,200,200,0.5)", width=1.5))
fig_osc.add_hline(y=100,  line=dict(color=COLORS["bullish"], dash="dash", width=1),
                  annotation_text="+100", annotation_position="right")
fig_osc.add_hline(y=-100, line=dict(color=COLORS["bearish"], dash="dash", width=1),
                  annotation_text="−100", annotation_position="right")

# Mark zero-line crossings (onset only)
cross_up   = (osc > 0) & (osc.shift(1) <= 0)
cross_down = (osc < 0) & (osc.shift(1) >= 0)
if cross_up.any():
    fig_osc.add_trace(go.Scatter(
        x=osc[cross_up].index, y=osc[cross_up].values,
        mode="markers", name="Cross above 0",
        marker=dict(symbol="triangle-up", size=9, color=COLORS["bullish"],
                    line=dict(width=1, color="white")),
    ))
if cross_down.any():
    fig_osc.add_trace(go.Scatter(
        x=osc[cross_down].index, y=osc[cross_down].values,
        mode="markers", name="Cross below 0",
        marker=dict(symbol="triangle-down", size=9, color=COLORS["bearish"],
                    line=dict(width=1, color="white")),
    ))

fig_osc.update_layout(height=300, template="plotly_dark", bargap=0,
                       margin=dict(l=40, r=60, t=30, b=20),
                       title="McClellan Oscillator — markers show zero-line crossings (buy/sell signals)")
st.plotly_chart(fig_osc, use_container_width=True)

# ------------------------------------------------------------------ #
# McClellan Summation Index
# ------------------------------------------------------------------ #
col_title2, col_help2 = st.columns([6, 1])
with col_title2:
    st.subheader("McClellan Summation Index")
with col_help2:
    st.write("")
    with st.popover("What is this?"):
        st.markdown("""
**McClellan Summation Index** = running cumulative sum of the McClellan Oscillator

If the Oscillator is *momentum*, the Summation Index is *trend*.

---
**How to read it:**

| Reading | Meaning |
|---|---|
| **Above 0 and rising** | 🟢 Healthy bull market; broad participation |
| **Below 0 and falling** | 🔴 Bear market internals |
| **Cross above 0** | Major buy signal — breadth trend has turned positive |
| **Cross below 0** | Major sell signal — breadth trend has turned negative |
| **Above +1000** | Overbought; market is extended, watch for stall |
| **Below −1000** | Oversold; conditions ripe for a breadth thrust reversal |

---
**Breadth thrust signal:**
A rapid move from below −500 to above +500 within a few weeks
is a rare "breadth thrust" — historically very bullish.

---
**Divergence from price:**
Price making new highs while Summation Index is declining = narrowing
participation = distribution. One of the most reliable warning signals.
        """)

summ = ad_plot["mcclellan_summation"]

fig_summ = go.Figure()

# Shade above/below zero
fig_summ.add_hrect(y0=0, y1=max(summ.max() * 1.1, 500),
                   fillcolor=COLORS["bullish"], opacity=0.04, line_width=0)
fig_summ.add_hrect(y0=min(summ.min() * 1.1, -500), y1=0,
                   fillcolor=COLORS["bearish"], opacity=0.04, line_width=0)

# Overbought / oversold bands
fig_summ.add_hrect(y0=1000, y1=max(summ.max() * 1.1, 1200),
                   fillcolor=COLORS["bullish"], opacity=0.08, line_width=0,
                   annotation_text="Overbought (+1000)", annotation_position="top left")
fig_summ.add_hrect(y0=min(summ.min() * 1.1, -1200), y1=-1000,
                   fillcolor=COLORS["bearish"], opacity=0.08, line_width=0,
                   annotation_text="Oversold (−1000)", annotation_position="bottom left")

# Main line
fig_summ.add_trace(go.Scatter(
    x=summ.index, y=summ.values, name="Summation Index",
    mode="lines", line=dict(color=COLORS["price"], width=2),
    fill="tozeroy", fillcolor="rgba(66,165,245,0.06)",
))

# Reference lines
fig_summ.add_hline(y=0,     line=dict(color="rgba(200,200,200,0.6)", width=1.5))
fig_summ.add_hline(y=1000,  line=dict(color=COLORS["bullish"], dash="dash", width=1),
                   annotation_text="+1000", annotation_position="right")
fig_summ.add_hline(y=-1000, line=dict(color=COLORS["bearish"], dash="dash", width=1),
                   annotation_text="−1000", annotation_position="right")

# Zero-line crossings — the major buy/sell signals
s_cross_up   = (summ > 0) & (summ.shift(1) <= 0)
s_cross_down = (summ < 0) & (summ.shift(1) >= 0)
if s_cross_up.any():
    fig_summ.add_trace(go.Scatter(
        x=summ[s_cross_up].index, y=summ[s_cross_up].values,
        mode="markers", name="Cross above 0 (Buy)",
        marker=dict(symbol="star", size=12, color=COLORS["bullish"],
                    line=dict(width=1, color="white")),
    ))
if s_cross_down.any():
    fig_summ.add_trace(go.Scatter(
        x=summ[s_cross_down].index, y=summ[s_cross_down].values,
        mode="markers", name="Cross below 0 (Sell)",
        marker=dict(symbol="star", size=12, color=COLORS["bearish"],
                    line=dict(width=1, color="white")),
    ))

fig_summ.update_layout(height=320, template="plotly_dark",
                        margin=dict(l=40, r=60, t=30, b=20),
                        title="McClellan Summation Index — ★ marks major zero-line crossings")
st.plotly_chart(fig_summ, use_container_width=True)

# ------------------------------------------------------------------ #
# Raw data
# ------------------------------------------------------------------ #
with st.expander("Raw Data"):
    st.dataframe(ad_plot.tail(60).sort_index(ascending=False), use_container_width=True)
