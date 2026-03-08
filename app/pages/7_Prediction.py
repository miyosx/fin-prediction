"""Page 7: Prediction — Stage 2 placeholder."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from app.state import init_session_state
from app.components.data_freshness import freshness_banner

st.set_page_config(page_title="Prediction", layout="wide")
init_session_state()
freshness_banner(force_key="refresh_pred")

st.title("Prediction Model — Stage 2")

st.info("""
**Stage 2 — Coming Soon**

This page will display:
- Bear market probability (classification, LightGBM)
- Forward return forecasts (1-month, 3-month regression)
- SHAP feature importance explaining the current prediction
- Top-10 most similar historical periods with actual outcomes

**To train the model**: Run `python scripts/train_model.py` after collecting
sufficient historical data via the backfill script.
""")

st.markdown("""
### Stage 2 Architecture

| Component | Details |
|---|---|
| **Features** | ~80-120 indicators + 5/10/21d lags + rolling 21/63d stats |
| **Models** | Ridge baseline + LightGBM primary + ensemble |
| **CV** | Walk-forward: 5-year train, 1-year step |
| **Similarity** | Cosine similarity on normalized feature vector |
| **Targets** | `spx_fwd_21d`, `spx_fwd_63d`, `bear_flag_126d` |

Build the feature matrix first:
```bash
python scripts/backfill_data.py
```

Then train:
```bash
python scripts/train_model.py
```
""")
