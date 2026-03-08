"""Page 8: Breadth-Price Divergence Scanner."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import streamlit as st

from app.state import init_session_state
from app.components.charts import (
    dual_signal_scatter,
    line_chart,
    oscillator_chart,
)
from app.components.signal_card import signal_grid
from app.components.data_freshness import freshness_banner
from data.fetchers.index_fetcher import fetch_index
from data.fetchers.breadth_fetcher import fetch_breadth
from indicators.advance_decline import compute_all as compute_ad
from indicators import divergence as div_mod

st.set_page_config(page_title="Divergence", layout="wide")
init_session_state()
freshness_banner(force_key="refresh_div")

st.title("Breadth-Price Divergence Scanner")
st.markdown("""
Detects when price indices and the A/D line move in opposite directions —
a classic warning of deteriorating market internals or an upcoming reversal.

> **Bearish divergence**: price rising, breadth falling — narrow rally, distribution risk
> **Bullish divergence**: price falling, breadth rising — selling is narrowing, potential reversal
""")

# ------------------------------------------------------------------ #
# Sidebar controls
# ------------------------------------------------------------------ #
st.sidebar.markdown("### Chart Options")
years = st.sidebar.slider("Years of history", 1, 25, 3)
window = st.sidebar.slider("Slope window (trading days)", 10, 63, 21)
thresh = st.sidebar.slider("Z-score threshold", 0.2, 1.5, 0.5, step=0.1,
                            help="How many std devs each series must be offset to flag divergence")
pair_options = {
    "SPX vs A/D Line": ("spx_adl", "spx_z", "adl_z", "SPX", "ADL"),
    "RUT vs A/D Line": ("rut_adl", "rut_z", "adl_z", "RUT", "ADL"),
    "DJI vs A/D Line": ("dji_adl", "dji_z", "adl_z", "DJI", "ADL"),
    "SPX vs RUT":      ("spx_rut", "spx_z", "rut_z", "SPX", "RUT"),
}
pair_label = st.sidebar.selectbox("Pair to inspect (normalized overlay)", list(pair_options.keys()))

# ------------------------------------------------------------------ #
# Data loading
# ------------------------------------------------------------------ #
with st.spinner("Loading data…"):
    spx_df = fetch_index("SPX")
    rut_df = fetch_index("RUT")
    dji_df = fetch_index("DJI")
    nyad_df = fetch_breadth("NYAD")

missing = [n for n, d in [("SPX", spx_df), ("RUT", rut_df), ("DJI", dji_df), ("NYAD", nyad_df)]
           if d.empty or "Close" not in d.columns]
if missing:
    st.error(f"Missing data for: {', '.join(missing)}. Click **Refresh All Data** in the sidebar.")
    st.stop()

ad_df = compute_ad(nyad_df["Close"])
adl = ad_df["ad_line"]

div_df = div_mod.compute_all(
    adl=adl,
    spx=spx_df["Close"],
    rut=rut_df["Close"],
    dji=dji_df["Close"],
    window=window,
    z_thresh=thresh,
)

# Date filter
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
div_plot = div_df[div_df.index >= cutoff]
spx_plot = spx_df["Close"][spx_df.index >= cutoff]

# ------------------------------------------------------------------ #
# Signal cards
# ------------------------------------------------------------------ #
latest = div_df.iloc[-1]
comp_score = latest.get("composite_div_score", 0.0)
n_bearish = int(latest.get("active_bearish_pairs", 0))
n_bullish = int(latest.get("active_bullish_pairs", 0))

comp_zone = div_mod.divergence_zone(comp_score)
bear_zone = "bearish" if n_bearish >= 2 else "neutral" if n_bearish == 1 else "bullish"
bull_zone = "bullish" if n_bullish >= 2 else "neutral" if n_bullish == 1 else "bearish"

pair_scores = {
    "SPX / ADL": ("spx_adl_div", "spx_adl"),
    "RUT / ADL": ("rut_adl_div", "rut_adl"),
    "DJI / ADL": ("dji_adl_div", "dji_adl"),
    "SPX / RUT": ("spx_rut_div", "spx_rut"),
}

signal_grid([
    {"title": "Composite Score", "value": round(comp_score, 2), "zone": comp_zone,
     "subtitle": "+ve = bearish divergence"},
    {"title": "Bearish Pairs", "value": f"{n_bearish} / 4", "zone": bear_zone},
    {"title": "Bullish Pairs", "value": f"{n_bullish} / 4", "zone": bull_zone},
    *[
        {
            "title": label,
            "value": round(latest.get(div_col, 0.0), 2),
            "zone": div_mod.divergence_zone(latest.get(div_col, 0.0)),
        }
        for label, (div_col, _prefix) in pair_scores.items()
    ],
])

st.markdown("---")

# ------------------------------------------------------------------ #
# Chart 1: SPX with bearish/bullish divergence markers
# ------------------------------------------------------------------ #
st.subheader("SPX Price — Divergence Signals")

bearish_any = div_plot[[c for c in div_plot.columns if c.endswith("_bearish")]].any(axis=1)
bullish_any = div_plot[[c for c in div_plot.columns if c.endswith("_bullish")]].any(axis=1)

# Only mark the first day of each consecutive divergence run
def _onset_dates(mask: pd.Series) -> pd.DatetimeIndex:
    started = mask & ~mask.shift(1).fillna(False)
    return started[started].index

bearish_onsets = _onset_dates(bearish_any)
bullish_onsets = _onset_dates(bullish_any)

st.plotly_chart(
    dual_signal_scatter(
        spx_plot,
        bearish_dates=bearish_onsets,
        bullish_dates=bullish_onsets,
        title="SPX with Divergence Onset Markers",
        height=400,
    ),
    use_container_width=True,
)

# ------------------------------------------------------------------ #
# Chart 2: Composite divergence score (oscillator)
# ------------------------------------------------------------------ #
st.subheader("Composite Divergence Score")
st.caption("Positive = price outpacing breadth (bearish). Negative = breadth outpacing price (bullish).")
st.plotly_chart(
    oscillator_chart(
        div_plot["composite_div_score"],
        title=f"Composite Divergence Score (slope window={window}d)",
        height=260,
    ),
    use_container_width=True,
)

# ------------------------------------------------------------------ #
# Chart 3: All pair divergence strengths
# ------------------------------------------------------------------ #
st.subheader("Individual Pair Divergence Strength")
div_cols = {c.replace("_div", "").replace("_", " ").upper(): div_plot[c]
            for c in div_plot.columns if c.endswith("_div") and "composite" not in c}

st.plotly_chart(
    line_chart(div_cols, title="Slope Difference per Pair (+ = price leading, − = breadth leading)",
               zero_line=True, height=300),
    use_container_width=True,
)

# ------------------------------------------------------------------ #
# Chart 4: Normalized pair overlay (user-selected)
# ------------------------------------------------------------------ #
prefix, col_a, col_b, label_a, label_b = pair_options[pair_label]
st.subheader(f"Normalized Overlay — {pair_label}")
st.caption("Both series z-score normalized to the same scale for visual comparison.")

if col_a in div_plot.columns and col_b in div_plot.columns:
    st.plotly_chart(
        line_chart(
            {label_a: div_plot[col_a], label_b: div_plot[col_b]},
            title=f"{label_a} vs {label_b} (z-score, {years}y)",
            zero_line=True,
            height=300,
        ),
        use_container_width=True,
    )
else:
    st.info("Insufficient data to display normalized overlay.")

# ------------------------------------------------------------------ #
# Chart 5: Slope breakdown
# ------------------------------------------------------------------ #
with st.expander("Individual Slopes"):
    slope_cols = {c.replace("_slope", "").upper(): div_plot[c]
                  for c in div_plot.columns if c.endswith("_slope")}
    st.plotly_chart(
        line_chart(slope_cols, title="Rolling Slopes (z-score units per day)", zero_line=True, height=280),
        use_container_width=True,
    )

# ------------------------------------------------------------------ #
# Raw data
# ------------------------------------------------------------------ #
with st.expander("Raw Divergence Data"):
    display_cols = (
        [c for c in div_plot.columns if "_div" in c or "_bearish" in c or "_bullish" in c
         or c in ("active_bearish_pairs", "active_bullish_pairs")]
    )
    st.dataframe(
        div_plot[display_cols].tail(60).sort_index(ascending=False),
        use_container_width=True,
    )
