"""
SuperSwarna — Market Risk & Momentum Terminal (v3 restored)
Section 1: Nifty/BankNifty risk ON-OFF (Minervini) + Supertrend ON-OFF
Section 2: Chartink screener results
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from data_layer import INDEX_TOKENS, connected
from engine import index_risk
from chartink import run_chartink_scan, DEFAULT_SCREENERS

st.set_page_config(page_title="SuperSwarna", page_icon="🪙",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Dark navy theme ───────────────────────────────────────────────────────────
st.markdown("""
<style>
  :root {
    --bg:#0A1124; --panel:#111A33; --panel2:#16213F; --border:#1E2A4A;
    --txt:#E6ECF5; --txt2:#8A99B8; --green:#16C784; --red:#EA3943;
    --amber:#F0B90B; --accent:#3B82F6;
  }
  .stApp { background:var(--bg); color:var(--txt); }
  #MainMenu, footer, header { visibility:hidden; }
  .block-container { padding:1rem 1.5rem 3rem; max-width:1300px; }
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
  .risk-chg { font-size:14px; font-weight:600; display:flex; align-items:center; gap:10px; }
  .chg-chip { padding:2px 8px; border-radius:6px; font-size:13px; }
  .up { color:var(--green); } .down { color:var(--red); }
  .chip-up { background:rgba(22,199,132,0.14); color:var(--green); }
  .chip-down { background:rgba(234,57,67,0.14); color:var(--red); }
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

  [data-testid="stDataFrame"] { background:var(--panel); border:1px solid var(--border);
        border-radius:12px; padding:4px; }
  [data-testid="stDataFrame"] * { color:var(--txt)!important; }
  div[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--border);
        border-radius:12px; }
  .stSelectbox div[data-baseweb="select"] > div { background:var(--panel2);
        border-color:var(--border); color:var(--txt); }
  .stButton button { background:var(--accent); color:#fff; border:none;
        border-radius:8px; font-weight:600; }
  .stTextArea textarea { background:var(--panel2); color:var(--txt); border-color:var(--border); }
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

# ═══ SECTION 1 — RISK INDICATOR ════════════════════════════════════════════════
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
        ltp = rk["ltp"]; chg = rk["chg"]; pts = rk.get("chg_pts", 0)
        pos = chg >= 0
        arrow = "▲" if pos else "▼"
        chg_cls = "up" if pos else "down"
        chip_cls = "chip-up" if pos else "chip-down"
        sign = "+" if pos else "−"
        mv_cls = "on" if rk["minervini"] else "off"
        mv_txt = "RISK ON" if rk["minervini"] else "RISK OFF"
        st_cls = "on" if rk["supertrend"] else "off"
        st_txt = "BUY" if rk["supertrend"] else "SELL"
        st.markdown(f"""
        <div class="risk-card">
          <div class="risk-idx">{idx}</div>
          <div class="risk-ltp">{ltp:,.2f}</div>
          <div class="risk-chg {chg_cls}">
            <span>{arrow} {sign}{abs(pts):,.2f}</span>
            <span class="chg-chip {chip_cls}">{sign}{abs(chg):.2f}%</span>
          </div>
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

# ═══ SECTION 2 — CHARTINK SCREENER ═════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">02 · Chartink Screener</div>',
            unsafe_allow_html=True)
st.caption("Live results from your Chartink scans. Free Chartink data is delayed ~30-45 min.")

ck1, ck2 = st.columns([2, 1])
with ck1:
    screener_name = st.selectbox("Screener", list(DEFAULT_SCREENERS.keys()), key="ck_screener")
with ck2:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    run_ck = st.button("🔄 Run scan", width="stretch", key="ck_run")

with st.expander("✏️ Or paste a custom scan clause"):
    custom_clause = st.text_area(
        "scan_clause (from Chartink → F12 Network → process → Payload)",
        value="", height=80, key="ck_custom",
        placeholder="( {33489} ( daily close >= daily max( 240 , daily close ) ) )")
    run_custom = st.button("Run custom scan", key="ck_run_custom")

clause = None
if run_custom and custom_clause.strip():
    clause = custom_clause.strip()
elif run_ck:
    clause = DEFAULT_SCREENERS[screener_name]

if clause:
    with st.spinner("Fetching from Chartink…"):
        ck_df = run_chartink_scan(clause)
    if "error" in ck_df.columns:
        st.error(ck_df["error"].iloc[0])
    elif ck_df.empty:
        st.info("No stocks matched this screener right now.")
    else:
        st.dataframe(ck_df, width="stretch", hide_index=True, height=480,
            column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
        st.caption(f"{len(ck_df)} stocks matched. Click any column header to sort.")
else:
    st.info("Pick a screener and click **Run scan**.")

st.divider()
st.caption("SuperSwarna · Minervini SEPA + Supertrend (Angel One) · Chartink (unofficial, delayed) · "
           "Not investment advice.")
