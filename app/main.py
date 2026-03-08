"""Streamlit entry point: streamlit run app/main.py"""
import sys
from pathlib import Path

# Ensure project root is on sys.path when running via `streamlit run app/main.py`
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from app.state import init_session_state
from app.components.data_freshness import freshness_banner

st.set_page_config(
    page_title="Market Breadth Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

# Sidebar navigation note
st.sidebar.title("Market Breadth Dashboard")
st.sidebar.markdown("Use the pages in the sidebar to navigate.")

freshness_banner()

# Landing content
st.title("📊 Market Breadth & Prediction Dashboard")
st.markdown("""
Welcome to the market breadth visualization tool. Navigate using the sidebar:

| Page | Content |
|---|---|
| **1 Market Overview** | Index prices + % above/below 200-day MA |
| **2 Breadth** | A/D Line, McClellan Oscillator & Summation |
| **3 Hindenburg** | Omen conditions + cluster history |
| **4 Follow Through** | IBD Follow-Through Day detection |
| **5 Lowry** | Up/Down volume + 90% day flags |
| **6 MM Breadth** | MMFD / MMTW / MMFI / MMTH panels |
| **7 Prediction** | ML model output + historical precedents |

---

### Quick Start
1. Click **Refresh All Data** in the sidebar to download historical data.
2. Navigate to any page to view charts.

> **Note on MM Breadth data**: MMFD/MMTW/MMFI/MMTH are approximated from
> S&P 500 constituents by default (Tier 1). Drop CSV exports into
> `data/manual_imports/` to use more accurate data (Tier 2). Set
> `EODHD_API_KEY` in `.env` for full NYSE breadth (Tier 3).
""")
