"""
Data processing and formatting helpers for the Noon Search Analytics dashboard.
"""

import json
import re
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional

# ─── Brand / theme constants ──────────────────────────────────────────────────

NOON_ORANGE   = "#F5A623"
NOON_ORANGE_L = "#FFBE57"
GOOGLE_BLUE   = "#4A90D9"
CLOSE4_TEAL   = "#2EC4B6"
BG_DARK       = "#0B0C10"
SURFACE       = "#13141A"
CARD_BG       = "#1A1B23"
BORDER_COLOR  = "#2C2D38"
TEXT_PRIMARY  = "#E8E9F0"
TEXT_MUTED    = "#7A7B8A"
SUCCESS_GREEN = "#00C896"
DANGER_RED    = "#E94560"

ENGINE_COLORS = {
    "google": GOOGLE_BLUE,
    "close4": CLOSE4_TEAL,
}

DELIVERY_COLORS = {
    "rocket":  "#F5A623",
    "express": "#4A90D9",
    "market":  "#8B8FA8",
    "global":  "#6C5CE7",
}

DELIVERY_ICON = {
    "rocket":  "🚀",
    "express": "⚡",
    "market":  "🏪",
    "global":  "🌍",
}

# ─── Data parsing ─────────────────────────────────────────────────────────────

def parse_products(products_raw) -> list[dict]:
    """Parse the nested JSON products field from BigQuery into a list of dicts."""
    if products_raw is None or (isinstance(products_raw, float) and np.isnan(products_raw)):
        return []
    if isinstance(products_raw, str):
        try:
            products_raw = json.loads(products_raw)
        except Exception:
            return []
    if isinstance(products_raw, list):
        return products_raw
    return []


def parse_summary_json(raw: str) -> Optional[dict]:
    """Parse the LLM summary JSON safely."""
    if not raw:
        return None
    try:
        cleaned = re.sub(r"```json|```", "", raw).strip()
        return json.loads(cleaned)
    except Exception:
        return None


def score_delta(google_score: float, close4_score: float) -> str:
    delta = google_score - close4_score
    arrow = "▲" if delta > 0 else "▼" if delta < 0 else "●"
    color = GOOGLE_BLUE if delta > 0 else CLOSE4_TEAL if delta < 0 else TEXT_MUTED
    return f"<span style='color:{color}'>{arrow} {abs(delta):.1f}</span>"


def winner_badge(winner: str) -> str:
    color = ENGINE_COLORS.get(winner, TEXT_MUTED)
    icon = "🔵" if winner == "google" else "🟢" if winner == "close4" else "⚪"
    return f"<span style='background:{color}22;color:{color};padding:2px 8px;border-radius:4px;font-size:0.8rem;font-weight:700;'>{icon} {winner.upper()}</span>"


def delivery_badge(dtype: str) -> str:
    icon = DELIVERY_ICON.get(dtype, "📦")
    color = DELIVERY_COLORS.get(dtype, TEXT_MUTED)
    return f"<span style='background:{color}22;color:{color};padding:1px 6px;border-radius:3px;font-size:0.75rem;'>{icon} {dtype}</span>"


# ─── Chart builders ───────────────────────────────────────────────────────────

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono, monospace", color=TEXT_PRIMARY, size=12),
    margin=dict(l=12, r=12, t=36, b=12),
)


def win_rate_donut(df: pd.DataFrame) -> go.Figure:
    counts = df["winner"].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    colors = [ENGINE_COLORS.get(l, TEXT_MUTED) for l in labels]

    fig = go.Figure(go.Pie(
        labels=[l.upper() for l in labels],
        values=values,
        hole=0.68,
        marker=dict(colors=colors, line=dict(color=BG_DARK, width=3)),
        textfont=dict(size=13, family="DM Mono, monospace"),
        hovertemplate="<b>%{label}</b><br>%{value} queries (%{percent})<extra></extra>",
    ))

    total = len(df)
    top_engine = counts.idxmax() if len(counts) else "—"
    top_pct = f"{counts.max() / total * 100:.0f}%" if total else "—"

    fig.add_annotation(
        text=f"<b>{top_pct}</b>",
        x=0.5, y=0.55, showarrow=False,
        font=dict(size=26, color=ENGINE_COLORS.get(top_engine, TEXT_PRIMARY), family="DM Mono, monospace"),
    )
    fig.add_annotation(
        text=f"{top_engine.upper()} wins",
        x=0.5, y=0.38, showarrow=False,
        font=dict(size=12, color=TEXT_MUTED, family="DM Mono, monospace"),
    )

    fig.update_layout(**PLOTLY_BASE, showlegend=True,
                      legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5))
    return fig


def score_distribution(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    for engine, color in ENGINE_COLORS.items():
        col = f"{engine}_score"
        if col not in df.columns:
            continue
        scores = df[col].dropna()
        fig.add_trace(go.Violin(
            y=scores,
            name=engine.upper(),
            side="positive",
            line_color=color,
            fillcolor=color + "30",
            box_visible=True,
            meanline_visible=True,
            points="outliers",
            hovertemplate=f"<b>{engine.upper()}</b><br>Score: %{{y:.1f}}<extra></extra>",
        ))

    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text="Score Distribution per Engine", font=dict(size=14)),
        yaxis=dict(gridcolor=BORDER_COLOR, title="LLM Score (1–10)"),
        xaxis=dict(gridcolor=BORDER_COLOR),
        violingap=0.3,
    )
    return fig


def score_scatter(df: pd.DataFrame) -> go.Figure:
    df2 = df.dropna(subset=["google_score", "close4_score"]).copy()
    df2["delta"] = df2["google_score"] - df2["close4_score"]
    df2["color"] = df2["winner"].map(ENGINE_COLORS).fillna(TEXT_MUTED)

    fig = go.Figure()

    # Reference diagonal
    lims = [0, 10]
    fig.add_trace(go.Scatter(
        x=lims, y=lims,
        mode="lines",
        line=dict(color=BORDER_COLOR, dash="dash", width=1),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Winner region labels
    fig.add_annotation(text="close4 wins ▲", x=2.5, y=8.5, showarrow=False,
                       font=dict(color=CLOSE4_TEAL + "80", size=11))
    fig.add_annotation(text="google wins ▼", x=7.5, y=1.5, showarrow=False,
                       font=dict(color=GOOGLE_BLUE + "80", size=11))

    for winner_val, color in ENGINE_COLORS.items():
        subset = df2[df2["winner"] == winner_val]
        fig.add_trace(go.Scatter(
            x=subset["google_score"],
            y=subset["close4_score"],
            mode="markers",
            name=f"{winner_val.upper()} wins",
            marker=dict(color=color, size=8, opacity=0.8, line=dict(width=1, color=BG_DARK)),
            customdata=subset[["query", "google_score", "close4_score"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>Google: %{customdata[1]:.1f} | Close4: %{customdata[2]:.1f}<extra></extra>",
        ))

    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text="Google Score vs Close4 Score (per query)", font=dict(size=14)),
        xaxis=dict(title="Google Score", range=[0, 10], gridcolor=BORDER_COLOR),
        yaxis=dict(title="Close4 Score", range=[0, 10], gridcolor=BORDER_COLOR),
    )
    return fig


def avg_score_bar(df: pd.DataFrame) -> go.Figure:
    avgs = {
        "Google": df["google_score"].mean(),
        "Close4": df["close4_score"].mean(),
    }
    colors = [GOOGLE_BLUE, CLOSE4_TEAL]

    fig = go.Figure(go.Bar(
        x=list(avgs.keys()),
        y=list(avgs.values()),
        marker=dict(color=colors, line=dict(color=BG_DARK, width=2)),
        text=[f"{v:.2f}" for v in avgs.values()],
        textposition="outside",
        textfont=dict(size=16, color=TEXT_PRIMARY),
        hovertemplate="<b>%{x}</b><br>Avg Score: %{y:.2f}<extra></extra>",
        width=0.4,
    ))

    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text="Average LLM Score", font=dict(size=14)),
        yaxis=dict(range=[0, 10.5], gridcolor=BORDER_COLOR),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    return fig


def popularity_by_rank(df_rank: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for engine, color in ENGINE_COLORS.items():
        subset = df_rank[df_rank["engine"] == engine]
        fig.add_trace(go.Scatter(
            x=subset["index_position"],
            y=subset["avg_popularity"],
            name=engine.upper(),
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=7, color=color),
            hovertemplate=f"<b>{engine.upper()}</b> Rank %{{x}}<br>Avg Popularity: %{{y:.3f}}<extra></extra>",
        ))
    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text="Avg Product Popularity by Rank Position", font=dict(size=14)),
        xaxis=dict(title="Rank", gridcolor=BORDER_COLOR, dtick=1),
        yaxis=dict(title="Avg units_l30d_norm", gridcolor=BORDER_COLOR),
    )
    return fig


def delivery_breakdown_chart(df_delivery: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for dtype in ["rocket", "express", "market", "global"]:
        sub = df_delivery[df_delivery["delivery_type_tag"] == dtype]
        if sub.empty:
            continue
        for engine in ["google", "close4"]:
            row = sub[sub["engine"] == engine]
            if row.empty:
                continue
            fig.add_trace(go.Bar(
                name=f"{engine.upper()} / {dtype}",
                x=[engine.upper()],
                y=row["product_count"].values,
                marker_color=DELIVERY_COLORS.get(dtype, TEXT_MUTED),
                opacity=0.9 if engine == "google" else 0.6,
                hovertemplate=f"<b>{engine.upper()}</b> – {dtype}<br>Count: %{{y}}<extra></extra>",
            ))
    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text="Delivery Type Distribution", font=dict(size=14)),
        barmode="stack",
        yaxis=dict(gridcolor=BORDER_COLOR),
        showlegend=True,
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
    )
    return fig
