"""Data freshness banner and refresh button."""
import streamlit as st

from config.symbols import ALL_YFINANCE_SYMBOLS
from data.cache import cache_manager


def freshness_banner(force_key: str = "refresh_all"):
    """Display last-updated info and a refresh button in the sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Data Freshness**")

        for sym in ALL_YFINANCE_SYMBOLS[:8]:
            age_str = cache_manager.last_updated(sym)
            st.caption(f"`{sym}`: {age_str}")

        if st.button("Refresh All Data", key=force_key, use_container_width=True):
            progress = st.progress(0, text="Starting...")
            results = {}
            symbols = ALL_YFINANCE_SYMBOLS
            for i, sym in enumerate(symbols):
                progress.progress((i + 1) / len(symbols), text=f"Fetching {sym}…")
                try:
                    df = cache_manager.get_or_fetch(sym, force_refresh=True)
                    results[sym] = not df.empty
                except Exception as exc:
                    results[sym] = False
                    st.warning(f"{sym}: {exc}")

            progress.empty()
            failed = [s for s, ok in results.items() if not ok]
            ok_count = len(results) - len(failed)

            if failed:
                st.warning(f"✓ {ok_count}/{len(results)} succeeded. Failed: {', '.join(failed)}")
            else:
                st.success(f"✓ All {ok_count} symbols refreshed")

            st.rerun()
