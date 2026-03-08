"""Page 3: Hindenburg Omen — conditions and historical occurrences."""
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
from data.fetchers.breadth_fetcher import fetch_breadth
from indicators.advance_decline import compute_all as compute_ad
from indicators.hindenburg import compute_all as compute_hind

st.set_page_config(page_title="Hindenburg Omen", layout="wide")
init_session_state()
freshness_banner(force_key="refresh_hind")

st.title("Hindenburg Omen — Conditions & Cluster Detection")

with st.spinner("Loading data..."):
    nya_df = fetch_index("NYA")
    nahl_df = fetch_breadth("NAHL")
    nyad_df = fetch_breadth("NYAD")

if any(df.empty for df in [nya_df, nahl_df, nyad_df]):
    st.warning("Some data is missing. Results may be incomplete.")

mco = pd.Series(dtype=float)
if not nyad_df.empty and "Close" in nyad_df.columns:
    ad_df = compute_ad(nyad_df["Close"])
    mco = ad_df["mcclellan_oscillator"]

if nya_df.empty or "Close" not in nya_df.columns:
    st.error("NYA data unavailable.")
    st.stop()

nahl = nahl_df["Close"] if not nahl_df.empty and "Close" in nahl_df.columns else pd.Series(dtype=float)

if nahl.empty or mco.empty:
    st.warning("NH/NL or McClellan data missing — Hindenburg analysis is limited.")
    st.stop()

hind_df = compute_hind(nya_df["Close"], nahl, mco)

# Signal cards
latest = hind_df.iloc[-1]
cluster_active = bool(latest.get("hindenburg_cluster", False))
conditions_met = int(latest.get("conditions_met", 0))
signal_active = bool(latest.get("hindenburg_signal", False))

signal_grid([
    {"title": "Signal Today", "value": "YES" if signal_active else "NO",
     "zone": "bearish" if signal_active else "inactive"},
    {"title": "Cluster Active (36d)", "value": "YES" if cluster_active else "NO",
     "zone": "bearish" if cluster_active else "inactive"},
    {"title": "Conditions Met", "value": conditions_met,
     "zone": "bearish" if conditions_met >= 4 else "neutral" if conditions_met >= 2 else "bullish"},
])

# Condition breakdown table
st.markdown("### Current Conditions")
cond_cols = [c for c in hind_df.columns if c.startswith("c") and "_" in c]
if cond_cols and not hind_df.empty:
    latest_conds = hind_df[cond_cols].iloc[-1]
    cond_df = pd.DataFrame({
        "Condition": latest_conds.index,
        "Met": latest_conds.values,
    })
    cond_df["Status"] = cond_df["Met"].map({True: "✅", False: "❌"})
    st.dataframe(cond_df[["Condition", "Status"]], use_container_width=True, hide_index=True)

st.markdown("---")

# Date range
years = st.sidebar.slider("Years of history", 1, 25, 10)
cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)

# Historical signals on NYA price
signal_dates = hind_df[hind_df["hindenburg_signal"] == True].index
signal_dates = signal_dates[signal_dates >= cutoff]
nya_close = nya_df["Close"][nya_df.index >= cutoff]

st.plotly_chart(
    signal_scatter(nya_close, signal_dates, title="NYA with Hindenburg Omen Signals",
                   signal_name="Hindenburg Signal"),
    use_container_width=True,
)

# Conditions met count over time
hind_plot = hind_df[hind_df.index >= cutoff]
st.plotly_chart(
    line_chart({"Conditions Met": hind_plot["conditions_met"]},
               title="Hindenburg Conditions Met per Day", height=250),
    use_container_width=True,
)

with st.expander("Signal History (all confirmed signals)"):
    all_signals = hind_df[hind_df["hindenburg_signal"] == True][["conditions_met", "hindenburg_cluster"]]
    st.dataframe(all_signals.sort_index(ascending=False), use_container_width=True)
