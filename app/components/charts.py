"""Reusable Plotly chart builders."""
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


COLORS = {
    "bullish": "#26a69a",
    "neutral": "#ffa726",
    "bearish": "#ef5350",
    "price": "#42a5f5",
    "signal": "#ab47bc",
    "up": "#26a69a",
    "down": "#ef5350",
    "zero_line": "rgba(128,128,128,0.4)",
}


def price_chart(
    df: pd.DataFrame,
    title: str = "",
    ma_windows: list[int] | None = None,
    height: int = 400,
) -> go.Figure:
    """OHLCV candlestick + optional MAs."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.02,
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df.get("Open", df.get("Close")),
            high=df.get("High", df.get("Close")),
            low=df.get("Low", df.get("Close")),
            close=df["Close"],
            name="Price",
            increasing_line_color=COLORS["up"],
            decreasing_line_color=COLORS["down"],
        ),
        row=1, col=1,
    )

    if ma_windows:
        for w in ma_windows:
            ma = df["Close"].rolling(w).mean()
            fig.add_trace(
                go.Scatter(x=df.index, y=ma, name=f"SMA {w}", mode="lines",
                           line=dict(width=1)),
                row=1, col=1,
            )

    if "Volume" in df.columns:
        colors = [COLORS["up"] if df["Close"].iloc[i] >= df["Close"].iloc[i - 1]
                  else COLORS["down"] for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df.index, y=df["Volume"], name="Volume",
                   marker_color=colors, opacity=0.6),
            row=2, col=1,
        )

    fig.update_layout(
        title=title,
        height=height,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def line_chart(
    series_dict: dict[str, pd.Series],
    title: str = "",
    height: int = 350,
    zero_line: bool = False,
    fill_zero: bool = False,
) -> go.Figure:
    """Multi-line chart for one or more named series."""
    fig = go.Figure()
    for name, s in series_dict.items():
        kwargs = dict(x=s.index, y=s.values, name=name, mode="lines")
        if fill_zero:
            kwargs["fill"] = "tozeroy"
        fig.add_trace(go.Scatter(**kwargs))

    if zero_line:
        fig.add_hline(y=0, line=dict(color=COLORS["zero_line"], dash="dash", width=1))

    fig.update_layout(
        title=title,
        height=height,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def zone_area_chart(
    series: pd.Series,
    symbol: str,
    thresholds: dict,
    title: str = "",
    height: int = 350,
) -> go.Figure:
    """Area chart with bearish/bullish/neutral threshold bands."""
    fig = go.Figure()

    bear_thresh = thresholds["bearish"]
    bull_thresh = thresholds["bullish"]

    # Shaded zones
    fig.add_hrect(y0=0, y1=bear_thresh, fillcolor=COLORS["bearish"],
                  opacity=0.08, line_width=0, annotation_text="Bearish")
    fig.add_hrect(y0=bear_thresh, y1=bull_thresh, fillcolor=COLORS["neutral"],
                  opacity=0.04, line_width=0, annotation_text="Neutral")
    fig.add_hrect(y0=bull_thresh, y1=100, fillcolor=COLORS["bullish"],
                  opacity=0.08, line_width=0, annotation_text="Bullish")

    # Threshold lines
    fig.add_hline(y=bear_thresh, line=dict(color=COLORS["bearish"], dash="dash", width=1))
    fig.add_hline(y=bull_thresh, line=dict(color=COLORS["bullish"], dash="dash", width=1))

    # Data line
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values, name=symbol,
        mode="lines", line=dict(color=COLORS["price"], width=2),
        fill="tozeroy", fillcolor="rgba(66,165,245,0.08)",
    ))

    fig.update_layout(
        title=title or symbol,
        height=height,
        yaxis=dict(range=[0, 100]),
        template="plotly_dark",
        margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def signal_scatter(
    price: pd.Series,
    signal_dates: pd.DatetimeIndex,
    title: str = "",
    signal_name: str = "Signal",
    height: int = 350,
) -> go.Figure:
    """Price line with signal markers overlaid."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=price.index, y=price.values, name="Price",
        mode="lines", line=dict(color=COLORS["price"], width=1.5),
    ))

    if len(signal_dates) > 0:
        signal_prices = price.reindex(signal_dates).dropna()
        fig.add_trace(go.Scatter(
            x=signal_prices.index, y=signal_prices.values, name=signal_name,
            mode="markers",
            marker=dict(symbol="triangle-down", size=12, color=COLORS["bearish"],
                        line=dict(width=1, color="white")),
        ))

    fig.update_layout(
        title=title,
        height=height,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def dual_signal_scatter(
    price: pd.Series,
    bearish_dates: pd.DatetimeIndex,
    bullish_dates: pd.DatetimeIndex,
    title: str = "",
    height: int = 350,
) -> go.Figure:
    """Price line with both bearish (red ▼) and bullish (green ▲) markers."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=price.index, y=price.values, name="Price",
        mode="lines", line=dict(color=COLORS["price"], width=1.5),
    ))

    if len(bearish_dates) > 0:
        bp = price.reindex(bearish_dates).dropna()
        fig.add_trace(go.Scatter(
            x=bp.index, y=bp.values, name="Bearish Divergence",
            mode="markers",
            marker=dict(symbol="triangle-down", size=11, color=COLORS["bearish"],
                        line=dict(width=1, color="white")),
        ))

    if len(bullish_dates) > 0:
        gp = price.reindex(bullish_dates).dropna()
        fig.add_trace(go.Scatter(
            x=gp.index, y=gp.values, name="Bullish Divergence",
            mode="markers",
            marker=dict(symbol="triangle-up", size=11, color=COLORS["bullish"],
                        line=dict(width=1, color="white")),
        ))

    fig.update_layout(
        title=title,
        height=height,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def oscillator_chart(
    series: pd.Series,
    title: str = "",
    height: int = 250,
    positive_color: str = COLORS["up"],
    negative_color: str = COLORS["down"],
) -> go.Figure:
    """Bar chart for oscillator-style indicators (colored by sign)."""
    colors = [positive_color if v >= 0 else negative_color for v in series.values]
    fig = go.Figure(go.Bar(
        x=series.index, y=series.values, marker_color=colors, name=series.name or "Value"
    ))
    fig.add_hline(y=0, line=dict(color=COLORS["zero_line"], dash="dash", width=1))
    fig.update_layout(
        title=title,
        height=height,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=40, b=20),
        bargap=0,
    )
    return fig
