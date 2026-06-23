"""
SuperSwarna — Market Risk & Momentum Terminal (v2)
Dark navy fintech UI. Nifty/BankNifty risk ON-OFF + Supertrend ON-OFF,
F&O screener with 10AM momentum, 52-week high & low scanners.
Powered by Angel One SmartAPI.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from data_layer import INDEX_TOKENS, connected
from engine import (
    index_risk, scan_fno, scan_52w, get_scan_universe, FNO_STOCKS
)

st.set_page_config(page_title="SuperSwarna", page_icon="🪙",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Dark navy theme + dark dataframe styling ──────────────────────────────────
st.markdown("""
<style>
  :root {
    --bg:#0A1124; --panel:#111A33; --panel2:#16213F; --border:#1E2A4A;
    --txt:#E6ECF5; --txt2:#8A99B8; --green:#16C784; --red:#EA3943;
    --amber:#F0B90B; --accent:#3B82F6;
  }
  .stApp { background:var(--bg); color:var(--txt); }
  #MainMenu, footer, header { visibility:hidden; }
  .block-container { padding:1rem 1.5rem 3rem; max-width:1500px; }
  h1,h2,h3,h4 { color:var(--txt)!important; }

  .brand { display:flex; align-items:baseline; gap:12px; }
  .brand-name { font-size:30px; font-weight:800; letter-spacing:-0.5px;
                background:linear-gradient(90deg,#F0B90B,#3B82F6);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .brand-sub { font-size:12px; color:var(--txt2); letter-spacing:2px; text-transform:uppercase; }
  .conn-pill { font-size:11px; padding:3px 10px; border-radius:999px; font-weight:600; }
  .conn-live { background:rgba(22,199,132,0.15); color:var(--green); }
  .conn-delayed { background:rgba(240,185,11,0.15); color:var(--amber); }
  .section-eyebrow { font-size:11px; letter-spacing:3px; color:var(--txt2);
                     text-transform:uppercase; margin:26px 0 12px; font-weight:600; }

  .risk-card { background:var(--panel); border:1px solid var(--border);
               border-radius:16px; padding:20px 22px; }
  .risk-idx { font-size:15px; color:var(--txt2); font-weight:600;
              letter-spacing:1px; text-transform:uppercase; }
  .risk-ltp { font-size:32px; font-weight:800; margin:6px 0 2px; }
  .risk-chg { font-size:14px; font-weight:600; }
  .up { color:var(--green); } .down { color:var(--red); }
  .switch-row { display:flex; gap:12px; margin-top:16px; }
  .switch { flex:1; border-radius:12px; padding:12px 14px; text-align:center;
            border:1px solid var(--border); }
  .switch-label { font-size:10px; letter-spacing:1.5px; text-transform:uppercase;
                  color:var(--txt2); margin-bottom:6px; }
  .switch-val { font-size:18px; font-weight:800; letter-spacing:0.5px; }
  .on  { background:rgba(22,199,132,0.12); border-color:rgba(22,199,132,0.4); }
  .on .switch-val { color:var(--green); }
  .off { background:rgba(234,57,67,0.12); border-color:rgba(234,57,67,0.4); }
  .off .switch-val { color:var(--red); }

  /* Dark dataframe */
  [data-testid="stDataFrame"] { background:var(--panel); border:1px solid var(--border);
        border-radius:12px; padding:4px; }
  [data-testid="stDataFrame"] * { color:var(--txt)!important; }
  .stTabs [data-baseweb="tab-list"] { gap:4px; background:transparent; }
  .stTabs [data-baseweb="tab"] { background:var(--panel2); border-radius:8px 8px 0 0;
        color:var(--txt2); }
  .stTabs [aria-selected="true"] { background:var(--accent); color:#fff; }
  div[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--border);
        border-radius:12px; }
  .stSelectbox div[data-baseweb="select"] > div { background:var(--panel2);
        border-color:var(--border); color:var(--txt); }
  .stButton button { background:var(--accent); color:#fff; border:none;
        border-radius:8px; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
live = connected()
conn = ('<span class="conn-pill conn-live">● LIVE · Angel One</span>' if live
        else '<span class="conn-pill conn-delayed">● Connect Angel One in Secrets</span>')
st.markdown(f"""
<div class="brand"><span class="brand-name">SuperSwarna</span>
<span class="brand-sub">Market Risk & Momentum Terminal</span></div>
<div style="margin:4px 0 2px">{conn}
<span style="font-size:11px;color:#8A99B8;margin-left:10px">
{datetime.now().strftime('%d %b %Y · %H:%M')} IST</span></div>
""", unsafe_allow_html=True)

# ═══ SECTION 1 — RISK INDICATOR (Nifty & BankNifty) ════════════════════════════
st.markdown('<div class="section-eyebrow">01 · Risk Indicator — Minervini & Supertrend (10,3)</div>',
            unsafe_allow_html=True)

cols = st.columns(2)
risks = {}
for i, idx in enumerate(INDEX_TOKENS.keys()):
    with cols[i]:
        with st.spinner(f"Loading {idx}…"):
            rk = index_risk(idx)
        risks[idx] = rk
        if rk["minervini"] is None:
            st.markdown(f"""<div class="risk-card"><div class="risk-idx">{idx}</div>
            <div class="risk-ltp">—</div><div style="color:#8A99B8;font-size:13px">
            Awaiting data — check Angel One connection</div></div>""",
            unsafe_allow_html=True)
            continue
        ltp = rk["ltp"]; chg = rk["chg"]
        arrow = "▲" if chg >= 0 else "▼"
        chg_cls = "up" if chg >= 0 else "down"
        mv_cls = "on" if rk["minervini"] else "off"
        mv_txt = "RISK ON" if rk["minervini"] else "RISK OFF"
        st_cls = "on" if rk["supertrend"] else "off"
        st_txt = "BUY" if rk["supertrend"] else "SELL"
        st.markdown(f"""
        <div class="risk-card">
          <div class="risk-idx">{idx}</div>
          <div class="risk-ltp">{ltp:,.1f}</div>
          <div class="risk-chg {chg_cls}">{arrow} {abs(chg):.2f}%</div>
          <div class="switch-row">
            <div class="switch {mv_cls}">
              <div class="switch-label">Minervini</div>
              <div class="switch-val">{mv_txt}</div>
            </div>
            <div class="switch {st_cls}">
              <div class="switch-label">Supertrend</div>
              <div class="switch-val">{st_txt}</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

with st.expander("📋 Minervini condition detail"):
    for idx, rk in risks.items():
        if rk["minervini"] is not None:
            st.markdown(f"**{idx}** — {rk['conditions_met']}/{rk['total_conditions']} "
                        f"conditions met · Price ₹{rk['price']:,.1f} · 200DMA ₹{rk['ma200']:,.1f}")

# ═══ SECTION 2 — F&O SCREENER ══════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">02 · F&O Screener — Supertrend (10,2) + 10 AM Momentum</div>',
            unsafe_allow_html=True)
st.caption("RSI across daily/weekly/monthly · Supertrend BUY/SELL · % from 52W high & low · "
           "‘vs 10AM %’ = current price vs the 10:00 AM candle (intraday momentum). "
           "Click any header to sort; hover for filter.")

c1, c2 = st.columns([1, 4])
with c1:
    run_fno = st.button("🔄 Run F&O scan", use_container_width=True)
if run_fno or st.session_state.get("fno_done"):
    if run_fno:
        st.session_state["fno_done"] = True
    with st.spinner("Scanning F&O universe…"):
        fno = scan_fno(FNO_STOCKS, st_factor=2.0, with_10am=live)
    if not fno.empty:
        st.dataframe(fno, use_container_width=True, hide_index=True, height=520,
            column_config={
                "Chg %": st.column_config.NumberColumn(format="%.2f%%"),
                "% from 52WH": st.column_config.NumberColumn(format="%.1f%%"),
                "% from 52WL": st.column_config.NumberColumn(format="%.1f%%"),
                "vs 10AM %": st.column_config.NumberColumn(format="%.2f%%"),
            })
        st.caption(f"{len(fno)} stocks scanned. Cached 15 min.")
    else:
        st.info("No data returned. Ensure Angel One is connected (Secrets).")
else:
    st.info("Click **Run F&O scan** to load the screener (≈30-45s).")

# ═══ SECTION 3 — 52-WEEK HIGH ══════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">03 · 52-Week High Stocks</div>',
            unsafe_allow_html=True)
hc1, hc2, hc3 = st.columns([1, 1, 3])
with hc1:
    hi_uni = st.selectbox("Universe", ["F&O + Large/Mid", "All NSE cash"], key="hi_uni")
with hc2:
    run_hi = st.button("🔄 Scan highs", use_container_width=True)
if run_hi or st.session_state.get("hi_done"):
    if run_hi: st.session_state["hi_done"] = True
    uni = get_scan_universe("all" if hi_uni == "All NSE cash" else "fno_plus")
    with st.spinner("Scanning for 52-week highs…"):
        hi = scan_52w(uni, kind="high", threshold=3.0,
                      max_scan=750 if hi_uni == "All NSE cash" else 110)
    if not hi.empty:
        st.dataframe(hi, use_container_width=True, hide_index=True, height=400,
            column_config={
                "Chg %": st.column_config.NumberColumn(format="%.2f%%"),
                "% from 52WH": st.column_config.NumberColumn(format="%.1f%%"),
                "% from 52WL": st.column_config.NumberColumn(format="%.1f%%"),
            })
        st.caption(f"{len(hi)} stocks within 3% of 52-week high.")
    else:
        st.info("No stocks near 52-week highs found.")
else:
    st.info("Click **Scan highs** to find stocks near their 52-week high.")

# ═══ SECTION 4 — 52-WEEK LOW ═══════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">04 · 52-Week Low Stocks</div>',
            unsafe_allow_html=True)
lc1, lc2, lc3 = st.columns([1, 1, 3])
with lc1:
    lo_uni = st.selectbox("Universe", ["F&O + Large/Mid", "All NSE cash"], key="lo_uni")
with lc2:
    run_lo = st.button("🔄 Scan lows", use_container_width=True)
if run_lo or st.session_state.get("lo_done"):
    if run_lo: st.session_state["lo_done"] = True
    uni = get_scan_universe("all" if lo_uni == "All NSE cash" else "fno_plus")
    with st.spinner("Scanning for 52-week lows…"):
        lo = scan_52w(uni, kind="low", threshold=3.0,
                      max_scan=750 if lo_uni == "All NSE cash" else 110)
    if not lo.empty:
        st.dataframe(lo, use_container_width=True, hide_index=True, height=400,
            column_config={
                "Chg %": st.column_config.NumberColumn(format="%.2f%%"),
                "% from 52WH": st.column_config.NumberColumn(format="%.1f%%"),
                "% from 52WL": st.column_config.NumberColumn(format="%.1f%%"),
            })
        st.caption(f"{len(lo)} stocks within 3% of 52-week low.")
    else:
        st.info("No stocks near 52-week lows found.")
else:
    st.info("Click **Scan lows** to find stocks near their 52-week low.")

st.divider()
st.caption("SuperSwarna · Minervini SEPA + Supertrend · Powered by Angel One SmartAPI · "
           "Not investment advice.")
