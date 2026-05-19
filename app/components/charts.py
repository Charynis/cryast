import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Optional

PLOTLY_THEME = {
    "paper_bgcolor": "#0D1117",
    "plot_bgcolor": "#161B22",
    "font_color": "#E6EDF3",
    "gridcolor": "#21262D",
}


def equity_curve_chart(predictions: List[Dict]) -> go.Figure:
    if not predictions:
        return _empty_chart("No completed trades yet")

    profits = [p.get("actual_profit_pct", 0) or 0 for p in predictions]
    dates = [p.get("closed_at", "") for p in predictions]
    cumulative = pd.Series(profits).cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(cumulative))),
        y=cumulative.tolist(),
        mode="lines+markers",
        line=dict(color="#58A6FF", width=2),
        marker=dict(size=6, color=["#3FB950" if p >= 0 else "#F85149" for p in profits]),
        fill="tozeroy",
        fillcolor="rgba(88, 166, 255, 0.1)",
        name="Cumulative P&L",
        hovertemplate="Trade %{x}<br>Cumulative P&L: %{y:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Trade #",
        yaxis_title="Cumulative P&L (%)",
        **PLOTLY_THEME,
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    fig.update_xaxes(gridcolor=PLOTLY_THEME["gridcolor"])
    fig.update_yaxes(gridcolor=PLOTLY_THEME["gridcolor"])
    return fig


def win_loss_pie(wins: int, losses: int, invalidations: int) -> go.Figure:
    fig = go.Figure(data=[go.Pie(
        labels=["Wins", "Losses", "Invalidated"],
        values=[max(wins, 0.01), max(losses, 0.01), max(invalidations, 0.01)],
        hole=0.6,
        marker=dict(colors=["#3FB950", "#F85149", "#E3B341"]),
        textinfo="label+percent",
        textfont=dict(color="#E6EDF3"),
    )])
    fig.update_layout(
        title="Trade Outcomes",
        **PLOTLY_THEME,
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
    )
    return fig


def regime_history_chart(regime_rows: List[Dict]) -> go.Figure:
    if not regime_rows:
        return _empty_chart("No regime history")

    regime_color_map = {"bull": "#3FB950", "bear": "#F85149", "sideways": "#E3B341", "dangerous": "#F0883E"}
    dates = [r.get("detected_at", "") for r in regime_rows[-30:]]
    regimes = [r.get("regime", "sideways") for r in regime_rows[-30:]]
    confidences = [r.get("confidence", 0.5) for r in regime_rows[-30:]]
    colors = [regime_color_map.get(r, "#8B949E") for r in regimes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates,
        y=confidences,
        marker_color=colors,
        name="Regime Confidence",
        hovertemplate="%{x}<br>Regime: " + "<br>".join(regimes) + "<br>Confidence: %{y:.1%}<extra></extra>",
    ))
    fig.update_layout(
        title="Market Regime History",
        **PLOTLY_THEME,
        height=220,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def setup_type_performance_chart(predictions: List[Dict]) -> go.Figure:
    if not predictions:
        return _empty_chart("No data")

    setup_data: Dict[str, List[float]] = {}
    for p in predictions:
        st = p.get("setup_type", "unknown")
        profit = p.get("actual_profit_pct", 0) or 0
        setup_data.setdefault(st, []).append(profit)

    labels = list(setup_data.keys())
    avg_profits = [sum(v) / len(v) for v in setup_data.values()]
    counts = [len(v) for v in setup_data.values()]
    colors = ["#3FB950" if p > 0 else "#F85149" for p in avg_profits]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=avg_profits,
        marker_color=colors,
        text=[f"n={c}" for c in counts],
        textposition="outside",
        name="Avg Profit by Setup",
    ))
    fig.update_layout(
        title="Performance by Setup Type",
        **PLOTLY_THEME,
        height=260,
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis_ticksuffix="%",
    )
    return fig


def confidence_calibration_chart(predictions: List[Dict]) -> go.Figure:
    if len(predictions) < 5:
        return _empty_chart("Need more trades for calibration")

    bins = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
    actual_rates = []
    bin_labels = []
    counts = []

    for low, high in bins:
        bucket = [p for p in predictions if low <= (p.get("confidence_score", 0) or 0) < high]
        if bucket:
            wins = sum(1 for p in bucket if (p.get("actual_profit_pct", 0) or 0) > 0)
            actual_rates.append(wins / len(bucket))
            counts.append(len(bucket))
        else:
            actual_rates.append(0)
            counts.append(0)
        bin_labels.append(f"{low*100:.0f}–{high*100:.0f}%")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=bin_labels, y=actual_rates,
        marker_color="#58A6FF", name="Actual Win Rate",
        text=[f"n={c}" for c in counts], textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=bin_labels, y=[(low + high) / 2 for low, high in bins],
        mode="lines+markers", line=dict(color="#E3B341", dash="dash"),
        name="Expected (model)",
    ))
    fig.update_layout(
        title="Confidence Calibration",
        **PLOTLY_THEME,
        height=260,
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis_tickformat=".0%",
    )
    return fig


def _empty_chart(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                       font=dict(color="#8B949E", size=14))
    fig.update_layout(**PLOTLY_THEME, height=200, margin=dict(l=0, r=0, t=20, b=0))
    return fig
