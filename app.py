"""
Noon Search Analytics Dashboard
================================
Compare Google vs Close4 search engine performance using LLM-evaluated rankings.

Run locally  : streamlit run app.py
Deploy       : Push to GitHub → connect on share.streamlit.io
"""

import json
import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ─── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Noon · Search Analytics",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Imports after page config ────────────────────────────────────────────────
from utils import (
    run_query,
    QUERY_ANALYSIS_SQL, SUMMARY_SQL, DELIVERY_BREAKDOWN_SQL, SCORE_OVER_RANK_SQL,
    parse_products, parse_summary_json,
    winner_badge, delivery_badge, score_delta,
    win_rate_donut, score_distribution, score_scatter,
    avg_score_bar, popularity_by_rank, delivery_breakdown_chart,
    ENGINE_COLORS, DELIVERY_COLORS, DELIVERY_ICON,
    NOON_ORANGE, GOOGLE_BLUE, CLOSE4_TEAL,
    BG_DARK, SURFACE, CARD_BG, BORDER_COLOR,
    TEXT_PRIMARY, TEXT_MUTED, SUCCESS_GREEN, DANGER_RED,
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=Syne:wght@400;600;700;800&display=swap');

/* Reset & base */
html, body, [data-testid="stAppViewContainer"] {
    background: #0B0C10 !important;
    font-family: 'DM Mono', monospace;
}
[data-testid="stSidebar"] {
    background: #0F1016 !important;
    border-right: 1px solid #1E1F2A;
}
h1,h2,h3,h4,h5 { font-family: 'Syne', sans-serif !important; }

/* Header bar */
.dash-header {
    display: flex; align-items: center; gap: 16px;
    padding: 20px 0 8px;
    border-bottom: 1px solid #1E1F2A;
    margin-bottom: 24px;
}
.dash-header .logo {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem; font-weight: 800;
    background: linear-gradient(135deg, #F5A623, #FFBE57);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
}
.dash-header .subtitle {
    font-size: 0.8rem; color: #7A7B8A; letter-spacing: 2px; text-transform: uppercase;
}

/* KPI cards */
.kpi-row { display: flex; gap: 14px; margin-bottom: 20px; flex-wrap: wrap; }
.kpi-card {
    flex: 1; min-width: 160px;
    background: #13141A;
    border: 1px solid #1E1F2A;
    border-radius: 10px;
    padding: 18px 20px;
    position: relative; overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: var(--accent, #F5A623);
}
.kpi-label { font-size: 0.7rem; color: #7A7B8A; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
.kpi-value { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 700; color: #E8E9F0; line-height: 1; }
.kpi-sub   { font-size: 0.72rem; color: #7A7B8A; margin-top: 5px; }

/* Section titles */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    color: #7A7B8A;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    margin: 28px 0 14px;
    display: flex; align-items: center; gap: 10px;
}
.section-title::after {
    content: ''; flex: 1; height: 1px; background: #1E1F2A;
}

/* Engine pill */
.engine-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.engine-google { background: #4A90D922; color: #4A90D9; border: 1px solid #4A90D940; }
.engine-close4 { background: #2EC4B622; color: #2EC4B6; border: 1px solid #2EC4B640; }
.engine-winner { background: #F5A62322; color: #F5A623; border: 1px solid #F5A62340; }

/* Query detail panel */
.query-header {
    background: #13141A; border: 1px solid #1E1F2A;
    border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
}
.query-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.3rem; font-weight: 700; margin-bottom: 10px;
    color: #F5A623;
}

/* Product cards */
.product-card {
    background: #13141A;
    border: 1px solid #1E1F2A;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 8px;
    display: flex; align-items: flex-start; gap: 12px;
    transition: border-color 0.15s;
}
.product-card:hover { border-color: #2C2D38; }
.rank-badge {
    width: 26px; height: 26px; min-width: 26px;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
    background: #1E1F2A; color: #7A7B8A;
}
.rank-badge.top3 { background: #F5A62320; color: #F5A623; }
.product-title { font-size: 0.82rem; color: #E8E9F0; line-height: 1.4; margin-bottom: 4px; }
.product-meta  { font-size: 0.72rem; color: #7A7B8A; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.pop-bar-wrap  { height: 4px; background: #1E1F2A; border-radius: 2px; width: 80px; display: inline-block; vertical-align: middle; margin-left: 4px; }
.pop-bar       { height: 4px; border-radius: 2px; }

/* Reason bullets */
.reason-block {
    background: #13141A; border: 1px solid #1E1F2A;
    border-left: 3px solid #F5A623;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px; margin-bottom: 8px;
    font-size: 0.82rem; line-height: 1.6; color: #C8C9D0;
}

/* Insight cards (summary page) */
.insight-box {
    background: #13141A; border: 1px solid #1E1F2A;
    border-radius: 10px; padding: 18px 20px; height: 100%;
}
.insight-box.google { border-top: 3px solid #4A90D9; }
.insight-box.close4 { border-top: 3px solid #2EC4B6; }
.insight-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.85rem; font-weight: 700; margin-bottom: 12px;
    text-transform: uppercase; letter-spacing: 1px;
}
.insight-item {
    font-size: 0.8rem; color: #B0B1C0;
    padding: 6px 0; border-bottom: 1px solid #1E1F2A;
    line-height: 1.5;
}
.insight-item:last-child { border-bottom: none; }
.insight-item::before { content: '→ '; color: #F5A623; }

/* Verdict box */
.verdict-box {
    background: linear-gradient(135deg, #13141A 0%, #1A1B2A 100%);
    border: 1px solid #2C2D38;
    border-radius: 12px; padding: 22px 26px;
    font-size: 0.88rem; line-height: 1.7; color: #C8C9D0;
    position: relative;
}
.verdict-box::before {
    content: '⚖️ FINAL VERDICT';
    display: block;
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem; font-weight: 700;
    letter-spacing: 2px; color: #F5A623;
    margin-bottom: 10px;
}

/* URL buttons */
.url-btn {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    text-decoration: none;
    margin-right: 8px;
    letter-spacing: 0.3px;
}
.url-btn.google { background: #4A90D915; color: #4A90D9; border: 1px solid #4A90D940; }
.url-btn.close4 { background: #2EC4B615; color: #2EC4B6; border: 1px solid #2EC4B640; }
.url-btn:hover  { opacity: 0.8; }

/* Score diff highlight */
.diff-positive { color: #4A90D9; font-weight: 600; }
.diff-negative { color: #2EC4B6; font-weight: 600; }
.diff-neutral  { color: #7A7B8A; }

/* Streamlit overrides */
div[data-testid="stPlotlyChart"] { border: 1px solid #1E1F2A; border-radius: 10px; overflow: hidden; }
.stSelectbox label, .stMultiSelect label { color: #7A7B8A !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 1px; }
[data-testid="stMetric"] { background: #13141A; border: 1px solid #1E1F2A; border-radius: 8px; padding: 12px 16px; }
div.stTabs [data-baseweb="tab-list"] { gap: 4px; background: transparent; }
div.stTabs [data-baseweb="tab"] { background: #13141A; border: 1px solid #1E1F2A; border-radius: 6px; padding: 8px 18px; font-size: 0.8rem; }
div.stTabs [aria-selected="true"] { background: #F5A62320 !important; border-color: #F5A623 !important; color: #F5A623 !important; }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 20px;">
      <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;
                  background:linear-gradient(135deg,#F5A623,#FFBE57);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        🔍 Search Analytics
      </div>
      <div style="font-size:0.68rem;color:#7A7B8A;letter-spacing:2px;text-transform:uppercase;margin-top:2px;">
        Noon · Engine Evaluator
      </div>
    </div>
    """, unsafe_allow_html=True)

    country_filter = st.selectbox("Country", ["SA", "AE", "EG"], index=0)

    st.markdown("---")
    st.markdown("<div style='font-size:0.68rem;color:#7A7B8A;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>Engines</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <span class="engine-pill engine-google">Google</span>
      <span class="engine-pill engine-close4">Close4</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div style='font-size:0.68rem;color:#7A7B8A;'>Last refreshed<br><b style='color:#E8E9F0;'>{datetime.now().strftime('%b %d, %H:%M')}</b></div>", unsafe_allow_html=True)

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ─── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data(country: str):
    """Load and cache all required data from BigQuery."""
    with st.spinner("Fetching data from BigQuery…"):
        df_queries  = run_query(QUERY_ANALYSIS_SQL)
        df_summary  = run_query(SUMMARY_SQL)
        df_delivery = run_query(DELIVERY_BREAKDOWN_SQL)
        df_rank     = run_query(SCORE_OVER_RANK_SQL)
    return df_queries, df_summary, df_delivery, df_rank


df_queries, df_summary, df_delivery, df_rank = load_all_data(country_filter)

# Filter by country
df = df_queries[df_queries["country"] == country_filter].copy()
df_sum_row = df_summary[df_summary["country"] == country_filter]

# Clean scores
df["google_score"] = pd.to_numeric(df["google_score"], errors="coerce")
df["close4_score"] = pd.to_numeric(df["close4_score"], errors="coerce")
df_clean = df.dropna(subset=["google_score", "close4_score"])


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="dash-header">
  <div>
    <div class="logo">noon · search intelligence</div>
    <div class="subtitle">Google vs Close4 · LLM-evaluated ranking performance · {country_filter}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_overview, tab_queries, tab_products, tab_insights = st.tabs([
    "📊  Overview",
    "🔍  Query Explorer",
    "📦  Product Comparison",
    "💡  Systemic Insights",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab_overview:

    # — KPI cards —
    total_q      = len(df_clean)
    google_wins  = (df_clean["winner"] == "google").sum()
    close4_wins  = (df_clean["winner"] == "close4").sum()
    avg_google   = df_clean["google_score"].mean()
    avg_close4   = df_clean["close4_score"].mean()
    avg_delta    = avg_google - avg_close4

    def kpi(label, value, sub, accent=NOON_ORANGE):
        return f"""
        <div class="kpi-card" style="--accent:{accent}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{sub}</div>
        </div>"""

    st.markdown(f"""
    <div class="kpi-row">
      {kpi("Total Queries", total_q, "evaluated queries")}
      {kpi("Google Wins", google_wins, f"{google_wins/total_q*100:.0f}% win rate", GOOGLE_BLUE)}
      {kpi("Close4 Wins", close4_wins, f"{close4_wins/total_q*100:.0f}% win rate", CLOSE4_TEAL)}
      {kpi("Avg Google Score", f"{avg_google:.2f}", "out of 10", GOOGLE_BLUE)}
      {kpi("Avg Close4 Score", f"{avg_close4:.2f}", "out of 10", CLOSE4_TEAL)}
      {kpi("Score Delta", f"{abs(avg_delta):.2f}", ("Google leads" if avg_delta > 0 else "Close4 leads"), NOON_ORANGE)}
    </div>
    """, unsafe_allow_html=True)

    # — Charts row 1 —
    col1, col2, col3 = st.columns([1.2, 1.5, 1.5])

    with col1:
        st.markdown("<div class='section-title'>Win Rate</div>", unsafe_allow_html=True)
        st.plotly_chart(win_rate_donut(df_clean), use_container_width=True, config={"displayModeBar": False})

    with col2:
        st.markdown("<div class='section-title'>Score Distribution</div>", unsafe_allow_html=True)
        st.plotly_chart(score_distribution(df_clean), use_container_width=True, config={"displayModeBar": False})

    with col3:
        st.markdown("<div class='section-title'>Score Scatter</div>", unsafe_allow_html=True)
        st.plotly_chart(score_scatter(df_clean), use_container_width=True, config={"displayModeBar": False})

    # — Charts row 2 —
    col4, col5 = st.columns(2)

    with col4:
        st.markdown("<div class='section-title'>Popularity by Rank Position</div>", unsafe_allow_html=True)
        if not df_rank.empty:
            st.plotly_chart(popularity_by_rank(df_rank), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No rank data available.")

    with col5:
        st.markdown("<div class='section-title'>Delivery Type Distribution</div>", unsafe_allow_html=True)
        if not df_delivery.empty:
            st.plotly_chart(delivery_breakdown_chart(df_delivery), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No delivery data available.")

    # — Score over time table (top/bottom performers) —
    st.markdown("<div class='section-title'>Top 5 · Google Wins</div>", unsafe_allow_html=True)
    top_google = df_clean[df_clean["winner"] == "google"].nlargest(5, "google_score")[
        ["query", "google_score", "close4_score", "winner"]
    ].reset_index(drop=True)
    st.dataframe(
        top_google.style.format({"google_score": "{:.1f}", "close4_score": "{:.1f}"}),
        use_container_width=True, hide_index=True
    )

    st.markdown("<div class='section-title'>Top 5 · Close4 Wins</div>", unsafe_allow_html=True)
    top_close4 = df_clean[df_clean["winner"] == "close4"].nlargest(5, "close4_score")[
        ["query", "google_score", "close4_score", "winner"]
    ].reset_index(drop=True)
    st.dataframe(
        top_close4.style.format({"google_score": "{:.1f}", "close4_score": "{:.1f}"}),
        use_container_width=True, hide_index=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — QUERY EXPLORER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_queries:

    col_list, col_detail = st.columns([1, 1.8])

    with col_list:
        st.markdown("<div class='section-title'>Browse Queries</div>", unsafe_allow_html=True)

        # Search box
        search_term = st.text_input("🔎 Search queries", placeholder="e.g. nike shoes…", label_visibility="collapsed")
        winner_pick = st.selectbox("Filter by winner", ["All", "google", "close4"], label_visibility="visible")

        filtered = df_clean.copy()
        if search_term:
            filtered = filtered[filtered["query"].str.contains(search_term, case=False, na=False)]
        if winner_pick != "All":
            filtered = filtered[filtered["winner"] == winner_pick]

        filtered = filtered.sort_values("google_score", ascending=False).reset_index(drop=True)

        # Render scrollable list
        query_rows_html = ""
        for _, row in filtered.iterrows():
            w_color = GOOGLE_BLUE if row["winner"] == "google" else CLOSE4_TEAL
            delta = row["google_score"] - row["close4_score"]
            d_text = f"+{delta:.1f} G" if delta > 0 else f"+{abs(delta):.1f} C4"
            d_color = GOOGLE_BLUE if delta > 0 else CLOSE4_TEAL
            query_rows_html += f"""
            <div style="background:#13141A;border:1px solid #1E1F2A;border-radius:8px;
                        padding:10px 14px;margin-bottom:6px;cursor:pointer;
                        border-left:3px solid {w_color};">
              <div style="font-size:0.82rem;color:#E8E9F0;margin-bottom:4px;">{row['query']}</div>
              <div style="display:flex;gap:10px;font-size:0.7rem;color:#7A7B8A;align-items:center;">
                <span>G: <b style="color:{GOOGLE_BLUE};">{row['google_score']:.1f}</b></span>
                <span>C4: <b style="color:{CLOSE4_TEAL};">{row['close4_score']:.1f}</b></span>
                <span style="color:{d_color};font-weight:600;">{d_text}</span>
              </div>
            </div>"""

        st.markdown(f"""
        <div style="max-height:560px;overflow-y:auto;padding-right:4px;">
          {query_rows_html}
        </div>
        """, unsafe_allow_html=True)

    with col_detail:
        st.markdown("<div class='section-title'>Query Detail</div>", unsafe_allow_html=True)

        if filtered.empty:
            st.info("No queries match your filter.")
        else:
            query_options = filtered["query"].tolist()
            selected_query = st.selectbox("Select a query", query_options, label_visibility="collapsed")
            row = df_clean[df_clean["query"] == selected_query].iloc[0]

            # Header
            delta = row["google_score"] - row["close4_score"]
            d_color = GOOGLE_BLUE if delta > 0 else CLOSE4_TEAL
            w_color = ENGINE_COLORS.get(row["winner"], NOON_ORANGE)

            st.markdown(f"""
            <div class="query-header">
              <div class="query-title">"{selected_query}"</div>
              <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;">
                <span>
                  <span class="engine-pill engine-google">Google {row['google_score']:.1f}</span>
                </span>
                <span>
                  <span class="engine-pill engine-close4">Close4 {row['close4_score']:.1f}</span>
                </span>
                <span style="font-size:0.78rem;color:{d_color};font-weight:700;">
                  Δ {abs(delta):.1f} → {row['winner'].upper()} wins
                </span>
              </div>
              <div style="margin-top:12px;display:flex;gap:10px;">
                <a href="{row.get('google_url','#')}" target="_blank" class="url-btn google">🔗 View on noon (Google)</a>
                <a href="{row.get('close4_url','#')}" target="_blank" class="url-btn close4">🔗 View on noon (Close4)</a>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Scores mini-chart
            fig_score = go.Figure()
            for engine, color, score in [("Google", GOOGLE_BLUE, row["google_score"]),
                                          ("Close4", CLOSE4_TEAL, row["close4_score"])]:
                fig_score.add_trace(go.Bar(
                    x=[engine], y=[score],
                    marker=dict(color=color + ("" if score == max(row["google_score"], row["close4_score"]) else "60")),
                    text=[f"{score:.1f}"], textposition="outside",
                    width=0.4,
                    hoverinfo="skip",
                ))
            fig_score.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="DM Mono, monospace", color=TEXT_PRIMARY),
                margin=dict(l=0, r=0, t=10, b=0), height=130,
                yaxis=dict(range=[0, 10.5], showgrid=False, visible=False),
                xaxis=dict(showgrid=False),
                showlegend=False, bargap=0.5,
            )
            st.plotly_chart(fig_score, use_container_width=True, config={"displayModeBar": False})

            # Reasons
            if pd.notna(row.get("reason")) and row["reason"]:
                st.markdown("<div class='section-title'>LLM Evaluation Reasons</div>", unsafe_allow_html=True)
                for bullet in str(row["reason"]).split("\n\n"):
                    bullet = bullet.strip("•- \n")
                    if bullet:
                        st.markdown(f"<div class='reason-block'>• {bullet}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRODUCT COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
with tab_products:

    st.markdown("<div class='section-title'>Side-by-Side Product Comparison</div>", unsafe_allow_html=True)

    if df_clean.empty:
        st.info("No data available.")
    else:
        query_pick = st.selectbox(
            "Choose a query",
            df_clean.sort_values("query")["query"].unique(),
            key="prod_query_select"
        )
        row2 = df_clean[df_clean["query"] == query_pick].iloc[0]

        google_prods = parse_products(row2.get("google_products"))
        close4_prods = parse_products(row2.get("close4_products"))

        def render_product_list(products: list, engine_name: str, engine_color: str):
            if not products:
                st.markdown("<div style='color:#7A7B8A;font-size:0.82rem;padding:20px;'>No products found.</div>", unsafe_allow_html=True)
                return

            html = ""
            for item in products:
                rank  = item.get("rank", "—")
                title = item.get("title") or "—"
                brand = item.get("brand") or "—"
                dtype = (item.get("delivery_type_tag") or "market").lower()
                pop   = float(item.get("units_l30d_norm") or 0)

                rank_class = "rank-badge top3" if isinstance(rank, int) and rank <= 3 else "rank-badge"
                dtype_icon  = DELIVERY_ICON.get(dtype, "📦")
                dtype_color = DELIVERY_COLORS.get(dtype, TEXT_MUTED)

                bar_width = int(pop * 80)
                bar_color = engine_color

                html += f"""
                <div class="product-card">
                  <div class="{rank_class}">#{rank}</div>
                  <div style="flex:1;min-width:0;">
                    <div class="product-title">{title[:90]}{'…' if len(str(title))>90 else ''}</div>
                    <div class="product-meta">
                      <span style="color:#7A7B8A;">🏷️ {brand}</span>
                      <span style="color:{dtype_color};">{dtype_icon} {dtype}</span>
                      <span>
                        📈 {pop:.2f}
                        <span class="pop-bar-wrap"><span class="pop-bar" style="width:{bar_width}px;background:{bar_color};"></span></span>
                      </span>
                    </div>
                  </div>
                </div>"""

            st.markdown(html, unsafe_allow_html=True)

        col_g, col_c = st.columns(2)

        with col_g:
            g_score = row2.get("google_score", 0)
            is_winner_g = row2.get("winner") == "google"
            st.markdown(f"""
            <div style="background:#13141A;border:1px solid #1E1F2A;border-top:3px solid {GOOGLE_BLUE};
                        border-radius:10px;padding:14px 16px;margin-bottom:12px;display:flex;
                        justify-content:space-between;align-items:center;">
              <div>
                <span style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:{GOOGLE_BLUE};">Google</span>
                {"<span style='margin-left:8px;font-size:0.7rem;background:#F5A62320;color:#F5A623;padding:2px 8px;border-radius:4px;'>🏆 WINNER</span>" if is_winner_g else ""}
              </div>
              <div style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:700;color:{GOOGLE_BLUE};">{g_score:.1f}</div>
            </div>
            """, unsafe_allow_html=True)
            render_product_list(google_prods, "google", GOOGLE_BLUE)

        with col_c:
            c_score = row2.get("close4_score", 0)
            is_winner_c = row2.get("winner") == "close4"
            st.markdown(f"""
            <div style="background:#13141A;border:1px solid #1E1F2A;border-top:3px solid {CLOSE4_TEAL};
                        border-radius:10px;padding:14px 16px;margin-bottom:12px;display:flex;
                        justify-content:space-between;align-items:center;">
              <div>
                <span style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:{CLOSE4_TEAL};">Close4</span>
                {"<span style='margin-left:8px;font-size:0.7rem;background:#F5A62320;color:#F5A623;padding:2px 8px;border-radius:4px;'>🏆 WINNER</span>" if is_winner_c else ""}
              </div>
              <div style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:700;color:{CLOSE4_TEAL};">{c_score:.1f}</div>
            </div>
            """, unsafe_allow_html=True)
            render_product_list(close4_prods, "close4", CLOSE4_TEAL)

        # Reasons for this query
        if pd.notna(row2.get("reason")) and row2["reason"]:
            st.markdown("<div class='section-title'>Why this result?</div>", unsafe_allow_html=True)
            for bullet in str(row2["reason"]).split("\n\n"):
                bullet = bullet.strip("•- \n")
                if bullet:
                    st.markdown(f"<div class='reason-block'>• {bullet}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SYSTEMIC INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_insights:

    st.markdown("<div class='section-title'>LLM-Generated Macro Analysis</div>", unsafe_allow_html=True)

    if df_sum_row.empty:
        st.info("No summary data available for this country.")
    else:
        raw_json = df_sum_row.iloc[0]["clean_json"]
        summary = parse_summary_json(raw_json)

        if not summary:
            st.warning("Could not parse summary JSON from LLM response.")
            with st.expander("Raw response"):
                st.text(raw_json)
        else:
            # — Strengths & Weaknesses —
            col_gs, col_gw, col_cs, col_cw = st.columns(4)

            def insight_box(title, items, css_class, icon):
                inner = "".join(f"<div class='insight-item'>{i}</div>" for i in items)
                return f"""
                <div class="insight-box {css_class}">
                  <div class="insight-title" style="color:{'#4A90D9' if 'google' in css_class else '#2EC4B6'};">{icon} {title}</div>
                  {inner}
                </div>"""

            with col_gs:
                st.markdown(insight_box("Google Strengths", summary.get("google_strengths", []), "google", "✅"), unsafe_allow_html=True)
            with col_gw:
                st.markdown(insight_box("Google Weaknesses", summary.get("google_weaknesses", []), "google", "❌"), unsafe_allow_html=True)
            with col_cs:
                st.markdown(insight_box("Close4 Strengths", summary.get("close4_strengths", []), "close4", "✅"), unsafe_allow_html=True)
            with col_cw:
                st.markdown(insight_box("Close4 Weaknesses", summary.get("close4_weaknesses", []), "close4", "❌"), unsafe_allow_html=True)

            # — Key differences —
            st.markdown("<div class='section-title' style='margin-top:28px;'>Key Differences</div>", unsafe_allow_html=True)
            diffs = summary.get("key_differences", [])
            for i, diff in enumerate(diffs):
                col_num, col_text = st.columns([0.06, 1])
                with col_num:
                    st.markdown(f"<div style='font-family:Syne,sans-serif;font-size:1.2rem;font-weight:800;color:#F5A623;padding-top:4px;'>{i+1:02d}</div>", unsafe_allow_html=True)
                with col_text:
                    st.markdown(f"<div style='background:#13141A;border:1px solid #1E1F2A;border-radius:8px;padding:12px 16px;font-size:0.83rem;color:#C8C9D0;line-height:1.6;'>{diff}</div>", unsafe_allow_html=True)

            # — Final verdict —
            st.markdown("<div class='section-title' style='margin-top:28px;'>Overall Verdict</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='verdict-box'>{summary.get('final_verdict', 'No verdict available.')}</div>", unsafe_allow_html=True)

    # — Score distribution summary charts —
    st.markdown("<div class='section-title' style='margin-top:32px;'>Score Summary</div>", unsafe_allow_html=True)
    col_avg, col_dist = st.columns(2)

    with col_avg:
        st.plotly_chart(avg_score_bar(df_clean), use_container_width=True, config={"displayModeBar": False})

    with col_dist:
        # Score delta histogram
        df_clean2 = df_clean.copy()
        df_clean2["delta"] = df_clean2["google_score"] - df_clean2["close4_score"]

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=df_clean2["delta"],
            nbinsx=20,
            marker=dict(color=[GOOGLE_BLUE if d > 0 else CLOSE4_TEAL for d in df_clean2["delta"]],
                        line=dict(color=BG_DARK, width=1)),
            hovertemplate="Delta: %{x:.1f}<br>Count: %{y}<extra></extra>",
        ))
        fig_hist.add_vline(x=0, line_dash="dash", line_color=NOON_ORANGE, line_width=1.5)
        fig_hist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Mono, monospace", color=TEXT_PRIMARY),
            margin=dict(l=12, r=12, t=36, b=12),
            title=dict(text="Score Delta Distribution (Google − Close4)", font=dict(size=14)),
            xaxis=dict(title="Google − Close4 Score", gridcolor=BORDER_COLOR),
            yaxis=dict(title="# Queries", gridcolor=BORDER_COLOR),
        )
        st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})

    # — Full data table —
    with st.expander("📋 Full query-level results table"):
        display_cols = ["query", "google_score", "close4_score", "winner"]
        st.dataframe(
            df_clean[display_cols].sort_values("google_score", ascending=False)
            .style.format({"google_score": "{:.1f}", "close4_score": "{:.1f}"}),
            use_container_width=True,
            hide_index=True,
        )
