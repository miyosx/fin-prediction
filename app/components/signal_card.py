"""Signal status card widgets (green/yellow/red)."""
import streamlit as st


ZONE_COLORS = {
    "bullish": "#26a69a",
    "neutral": "#ffa726",
    "bearish": "#ef5350",
    "active": "#ef5350",
    "inactive": "#26a69a",
    "unknown": "#9e9e9e",
}

ZONE_EMOJIS = {
    "bullish": "🟢",
    "neutral": "🟡",
    "bearish": "🔴",
    "active": "🔴",
    "inactive": "🟢",
    "unknown": "⚪",
}


def signal_card(
    title: str,
    value: str | float,
    zone: str = "neutral",
    subtitle: str = "",
):
    """Render a colored metric card for a single signal."""
    color = ZONE_COLORS.get(zone, ZONE_COLORS["unknown"])
    emoji = ZONE_EMOJIS.get(zone, "⚪")

    value_str = f"{value:.1f}" if isinstance(value, float) else str(value)

    st.markdown(
        f"""
        <div style="
            background-color: {color}22;
            border-left: 4px solid {color};
            border-radius: 4px;
            padding: 12px 16px;
            margin-bottom: 8px;
        ">
            <div style="font-size: 0.85em; color: #aaa; margin-bottom: 4px;">{title}</div>
            <div style="font-size: 1.4em; font-weight: bold; color: {color};">{emoji} {value_str}</div>
            {f'<div style="font-size: 0.8em; color: #888; margin-top: 4px;">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def signal_grid(signals: list[dict]):
    """Render a row of signal cards from a list of dicts.

    Each dict: {title, value, zone, subtitle (optional)}
    """
    cols = st.columns(len(signals))
    for col, sig in zip(cols, signals):
        with col:
            signal_card(
                title=sig["title"],
                value=sig["value"],
                zone=sig.get("zone", "neutral"),
                subtitle=sig.get("subtitle", ""),
            )
