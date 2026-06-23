"""
SuperSwarna — Market Risk & Momentum Terminal
Dark-navy fintech UI. Minervini risk + Supertrend across indices,
participant data, breadth, sector heatmap, 52W highs, F&O screener.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from data_layer import (
    INDEX_TOKENS, get_index_ltp, smartapi_connected, fetch_yf
)
from engine import (
    build_index_card, scan_fno_table, scan_52w_high, sector_strength,
    FNO_STOCKS, minervini_score
)

st.set_page_config(page_title="SuperSwarna", page_icon="🪙",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Theme: dark navy fintech ──────────────────────────────────────────────────
st.markdown("""
<style>
  :root {
    --bg: #0A1124; --panel: #111A33; --panel2: #16213F;
    --border: #1E2A4A; --txt: #E6ECF5; --txt2: #8A99B8;
    --green: #16C784; --red: #EA3943; --amber: #F0B90B;
    --accent: #3B82F6;
  }
  .stApp { background: var(--bg); color: var(--txt); }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 1rem 1.5rem 3rem; max-width: 1400px; }
  h1,h2,h3,h4 { color: var(--txt) !important; font-family: 'Inter',sans-serif; }

  .brand { display:flex; align-items:baseline; gap:12px; margin-bottom:2px; }
  .brand-name { font-size:30px; font-weight:800; letter-spacing:-0.5px;
                background:linear-gradient(90deg,#F0B90B,#3B82F6);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .brand-sub { font-size:12px; color:var(--txt2); letter-spacing:2px; text-transform:uppercase; }
  .conn-pill { font-size:11px; padding:3px 10px; border-radius:999px; font-weight:600; }
  .conn-live { background:rgba(22,199,132,0.15); color:var(--green); }
  .conn-delayed { background:rgba(240,185,11,0.15); color:var(--amber); }

  .section-eyebrow { font-size:11px; letter-spacing:3px; color:var(--txt2);
                     text-transform:uppercase; margin:24px 0 10px; font-weight:600; }

  .idx-card { background:var(--panel); border:1px solid var(--border);
              border-radius:14px; padding:16px 18px; height:100%; }
  .idx-name { font-size:13px; color:var(--txt2); font-weight:600;
              letter-spacing:1px; text-transform:uppercase; }
  .idx-ltp { font-size:26px; font-weight:700; margin:4px 0 2px; }
  .idx-chg { font-size:13px; font-weight:600; }
  .up { color:var(--green); } .down { color:var(--red); }
  .risk-tag { display:inline-block; font-size:12px; font-weight:700;
              padding:4px 14px; border-radius:8px; margin-top:10px; letter-spacing:0.5px; }
  .risk-LOW { background:rgba(22,199,132,0.15); color:var(--green); }
  .risk-MODERATE { background:rgba(240,185,11,0.15); color:var(--amber); }
  .risk-HIGH { background:rgba(234,57,67,0.15); color:var(--red); }
  .risk-NODATA { background:rgba(138,153,184,0.15); color:var(--txt2); }
  .st-btn { display:inline-block; font-size:11px; font-weight:700; padding:4px 12px;
            border-radius:8px; margin-top:10px; margin-left:6px; letter-spacing:0.5px; }
  .st-buy { background:var(--green); color:#04140C; }
  .st-sell { background:var(--red); color:#1A0406; }
  .score-mini { font-size:11px; color:var(--txt2); margin-top:8px; }

  .panel { background:var(--panel); border:1px solid var(--border);
           border-radius:14px; padding:18px; }
  .stDataFrame { border-radius:10px; overflow:hidden; }

  div[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--border);
           border-radius:12px; }
  .stTabs [data-baseweb="tab-list"] { gap:4px; }
  .stTabs [data-baseweb="tab"] { background:var(--panel2); border-radius:8px 8px 0 0;
           color:var(--txt2); padding:6px 16px; }
  .stTabs [aria-selected="true"] { background:var(--accent); color:white; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
live = smartapi_connected()
conn_html = ('<span class="conn-pill conn-live">● LIVE · Angel One</span>' if live
             else '<span class="conn-pill conn-delayed">● DELAYED · Yahoo (15m)</span>')
st.markdown(f"""
<div class="brand">
  <span class="brand-name">SuperSwarna</span>
  <span class="brand-sub">Market Risk & Momentum Terminal</span>
</div>
<div style="margin-bottom:6px">{conn_html}
<span style="font-size:11px;color:var(--txt2);margin-left:10px">Updated {datetime.now().strftime('%d %b %Y · %H:%M')} IST</span>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — RISK INDICATOR (4 indices at a glance)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">01 · Risk Indicator — Minervini Template + Supertrend (10,3)</div>', unsafe_allow_html=True)

cols = st.columns(4)
cards = {}
for i, (idx_name, info) in enumerate(INDEX_TOKENS.items()):
    with cols[i]:
        with st.spinner(f"Loading {idx_name}…"):
            card = build_index_card(idx_name, info["yf"])
            ltp = get_index_ltp(idx_name)
        cards[idx_name] = card
        risk = card.get("risk", "NO DATA")
        risk_cls = "risk-" + risk.replace(" ", "").replace("NODATA", "NODATA")
        if risk == "NO DATA":
            risk_cls = "risk-NODATA"
        chg = card.get("chg_pct")
        chg_html = ""
        if chg is not None:
            arrow = "▲" if chg >= 0 else "▼"
            chg_html = f'<span class="idx-chg {"up" if chg>=0 else "down"}">{arrow} {abs(chg):.2f}%</span>'
        st_dir = card.get("st_dir", 0)
        st_html = (f'<span class="st-btn st-buy">ST · BUY</span>' if st_dir == 1
                   else f'<span class="st-btn st-sell">ST · SELL</span>' if st_dir == -1
                   else "")
        ltp_str = f"{ltp:,.1f}" if ltp == ltp else "—"
        score = card.get("score")
        score_str = f"{score}/8" if score is not None else "—"
        pct200 = card.get("pct_200")
        pct200_str = f"{pct200:+.1f}% vs 200DMA" if pct200 is not None else ""
        st.markdown(f"""
        <div class="idx-card">
          <div class="idx-name">{idx_name}</div>
          <div class="idx-ltp">{ltp_str}</div>
          <div>{chg_html}</div>
          <div>
            <span class="risk-tag {risk_cls}">{risk} RISK</span>
            {st_html}
          </div>
          <div class="score-mini">Minervini {score_str} · {pct200_str}</div>
        </div>
        """, unsafe_allow_html=True)

# Pillars / checklist — on demand
with st.expander("📋 Minervini pillars & signal checklist (expand for full analysis)"):
    tabs = st.tabs(list(INDEX_TOKENS.keys()))
    for tab, idx_name in zip(tabs, INDEX_TOKENS.keys()):
        with tab:
            card = cards[idx_name]
            checks = card.get("checks", {})
            if not checks:
                st.info("Insufficient data for this index.")
                continue
            cc = st.columns(2)
            items = list(checks.items())
            for j, (label, passed) in enumerate(items):
                with cc[j % 2]:
                    icon = "🟢" if passed else "🔴"
                    st.markdown(f"{icon} {label}")
            st.caption(f"Score: {card.get('score')}/8 · "
                       f"Price ₹{card.get('price',0):,.1f} · "
                       f"200 DMA ₹{card.get('ma200',0):,.1f} · "
                       f"52W High ₹{card.get('hi52',0):,.1f}")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Participant flows (left) + Breadth & Sectors (right)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">02 · Flows & Market Internals</div>', unsafe_allow_html=True)

left, right = st.columns([1, 1])

with left:
    st.markdown("**FII & Client — cumulative F&O positioning (3-week trend)**")
    if live:
        st.info("Participant OI data wiring is ready. Connect NSE participant feed "
                "to populate. (SmartAPI does not expose participant-wise OI; "
                "this pulls from NSE's daily participant report — see setup guide.)")
    else:
        # Placeholder illustrative trend so layout is visible before data wiring
        import plotly.graph_objects as go
        days = pd.date_range(end=datetime.now(), periods=15, freq="B")
        demo = pd.DataFrame({
            "FII": np.cumsum(np.random.randn(15) * 8000),
            "Client": np.cumsum(np.random.randn(15) * 6000),
        }, index=days)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=demo.index, y=demo["FII"], name="FII net",
                                 line=dict(color="#3B82F6", width=2)))
        fig.add_trace(go.Scatter(x=demo.index, y=demo["Client"], name="Client net",
                                 line=dict(color="#F0B90B", width=2)))
        fig.update_layout(height=300, template="plotly_dark",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=10, r=10, t=10, b=10),
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("⚠️ Illustrative placeholder. Real participant data requires NSE feed (see guide).")

with right:
    st.markdown("**Advance / Decline & Sector strength**")
    period_map = {"Daily": 1, "Weekly": 5, "Monthly": 22}
    period_label = st.selectbox("Lookback", list(period_map.keys()), key="sector_period")
    with st.spinner("Computing sector strength…"):
        sec = sector_strength(period_map[period_label])
    if not sec.empty:
        import plotly.express as px
        sec_sorted = sec.sort_values("Return %")
        colors = ["#16C784" if v >= 0 else "#EA3943" for v in sec_sorted["Return %"]]
        fig2 = go.Figure(go.Bar(
            x=sec_sorted["Return %"], y=sec_sorted["Sector"],
            orientation="h", marker_color=colors,
            text=sec_sorted["Return %"].map(lambda x: f"{x:+.1f}%"),
            textposition="outside"))
        fig2.update_layout(height=320, template="plotly_dark",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           margin=dict(l=10, r=10, t=10, b=10),
                           xaxis_title=f"{period_label} return %")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sector data unavailable right now.")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — 52-week high stocks
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">03 · 52-Week High Stocks</div>', unsafe_allow_html=True)
seg = st.selectbox("Universe", ["F&O", "Cash"], key="universe_52w")
with st.spinner("Scanning for stocks near 52-week highs…"):
    hi_df = scan_52w_high(FNO_STOCKS, threshold_pct=5.0)
if not hi_df.empty:
    st.dataframe(hi_df, use_container_width=True, hide_index=True,
                 column_config={
                     "Chg %": st.column_config.NumberColumn(format="%.2f%%"),
                     "% from 52WH": st.column_config.NumberColumn(format="%.1f%%"),
                 })
    st.caption(f"{len(hi_df)} stocks within 5% of their 52-week high.")
else:
    st.info("No stocks near 52-week highs, or data unavailable.")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Live F&O screener
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">04 · F&O Stock Screener — Supertrend (10,2)</div>', unsafe_allow_html=True)
st.caption("Sort any column by clicking its header. Use the filter icon on hover. "
           "10 AM vs current % requires SmartAPI live feed (shown once connected).")
with st.spinner("Building F&O screener (first load ~30-60s)…"):
    fno_df = scan_fno_table(FNO_STOCKS, st_factor=2.0)
if not fno_df.empty:
    st.dataframe(
        fno_df, use_container_width=True, hide_index=True, height=560,
        column_config={
            "Chg %": st.column_config.NumberColumn(format="%.2f%%"),
            "% from 52WH": st.column_config.NumberColumn(format="%.1f%%"),
            "Wkly RSI": st.column_config.NumberColumn(format="%.1f"),
            "Mnly RSI": st.column_config.NumberColumn(format="%.1f"),
        })
    st.caption(f"{len(fno_df)} F&O stocks scanned.")
else:
    st.info("Screener data unavailable right now. Try refreshing.")

st.divider()
st.caption("SuperSwarna · Methodology based on Mark Minervini's SEPA / Trend Template. "
           "Not investment advice. Data delayed unless Angel One SmartAPI is connected.")
