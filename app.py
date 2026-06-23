"""
SuperSwarna — Market Risk & Momentum Terminal (v4)
Premium dark global-terminal design.
Section 1: Nifty/BankNifty risk (Minervini + Supertrend), LTP, point & % change.
Section 2: Chartink screener results.
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

# ── Premium dark theme ────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:#070B16; --bg2:#0A1020; --panel:#0F1729; --panel-hi:#141E36;
    --border:#1C2942; --border-hi:#2A3B5C;
    --txt:#EDF1F8; --txt2:#7E8DAE; --txt3:#4D5B7C;
    --green:#1FD080; --green-dim:#0E7A4A; --red:#FF4D5E; --red-dim:#992E38;
    --amber:#FFB020; --gold:#E8B84B; --accent:#4D7CFE;
    --glow-g:rgba(31,208,128,0.25); --glow-r:rgba(255,77,94,0.22);
  }
  .stApp {
    background:
      radial-gradient(1200px 600px at 15% -10%, rgba(77,124,254,0.08), transparent 60%),
      radial-gradient(900px 500px at 100% 0%, rgba(232,184,75,0.05), transparent 55%),
      var(--bg);
    color:var(--txt);
    font-family:'Inter',-apple-system,sans-serif;
  }
  #MainMenu, footer, header { visibility:hidden; }
  .block-container { padding:1.4rem 2rem 4rem; max-width:1240px; }
  h1,h2,h3,h4 { color:var(--txt)!important; font-family:'Inter',sans-serif; }
  .mono { font-family:'JetBrains Mono',monospace; }

  /* Header */
  .topbar { display:flex; align-items:center; justify-content:space-between;
            padding-bottom:18px; border-bottom:1px solid var(--border);
            margin-bottom:8px; }
  .brand { display:flex; align-items:baseline; gap:14px; }
  .brand-mark { font-size:32px; font-weight:800; letter-spacing:-1px;
                background:linear-gradient(120deg,#E8B84B 0%,#FFD97A 30%,#4D7CFE 100%);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                font-family:'Inter',sans-serif; }
  .brand-tag { font-size:10.5px; color:var(--txt3); letter-spacing:3px;
               text-transform:uppercase; font-weight:600; }
  .status { display:flex; align-items:center; gap:14px; }
  .conn-pill { font-size:11px; padding:5px 13px; border-radius:999px; font-weight:600;
               display:inline-flex; align-items:center; gap:6px; }
  .conn-live { background:rgba(31,208,128,0.1); color:var(--green);
               border:1px solid rgba(31,208,128,0.25); }
  .conn-off { background:rgba(255,176,32,0.1); color:var(--amber);
              border:1px solid rgba(255,176,32,0.25); }
  .dot { width:7px; height:7px; border-radius:50%; background:currentColor;
         box-shadow:0 0 8px currentColor; animation:pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  .clock { font-size:12px; color:var(--txt2); font-family:'JetBrains Mono',monospace; }

  .eyebrow { display:flex; align-items:center; gap:12px; margin:30px 0 14px; }
  .eyebrow-num { font-family:'JetBrains Mono',monospace; font-size:12px;
                 color:var(--accent); font-weight:700; }
  .eyebrow-txt { font-size:11px; letter-spacing:2.5px; color:var(--txt2);
                 text-transform:uppercase; font-weight:600; }
  .eyebrow-line { flex:1; height:1px;
                  background:linear-gradient(90deg,var(--border),transparent); }

  /* Risk cards */
  .rcard { position:relative; background:linear-gradient(160deg,var(--panel-hi),var(--panel));
           border:1px solid var(--border); border-radius:18px; padding:22px 24px;
           overflow:hidden; transition:border-color .2s; }
  .rcard::before { content:''; position:absolute; top:0; left:0; right:0; height:2px;
                   opacity:0.7; }
  .rcard.pos::before { background:linear-gradient(90deg,transparent,var(--green),transparent); }
  .rcard.neg::before { background:linear-gradient(90deg,transparent,var(--red),transparent); }
  .rc-top { display:flex; align-items:flex-start; justify-content:space-between; }
  .rc-name { font-size:13px; color:var(--txt2); font-weight:600; letter-spacing:1.5px;
             text-transform:uppercase; }
  .rc-spark { font-size:10px; color:var(--txt3); font-family:'JetBrains Mono',monospace; }
  .rc-ltp { font-size:38px; font-weight:800; margin:10px 0 4px; letter-spacing:-1px;
            font-family:'JetBrains Mono',monospace; }
  .rc-chg { font-size:15px; font-weight:700; display:flex; align-items:center; gap:10px;
            font-family:'JetBrains Mono',monospace; }
  .chg-chip { padding:2px 9px; border-radius:7px; font-size:13px; }
  .pos .rc-chg, .chip-pos { color:var(--green); }
  .neg .rc-chg, .chip-neg { color:var(--red); }
  .chip-pos { background:rgba(31,208,128,0.12); }
  .chip-neg { background:rgba(255,77,94,0.12); }
  .switch-row { display:flex; gap:12px; margin-top:20px; }
  .switch { flex:1; border-radius:13px; padding:13px 14px; text-align:center;
            border:1px solid var(--border); position:relative; }
  .switch-label { font-size:9.5px; letter-spacing:1.5px; text-transform:uppercase;
                  color:var(--txt3); margin-bottom:7px; font-weight:600; }
  .switch-val { font-size:17px; font-weight:800; letter-spacing:0.5px;
                font-family:'JetBrains Mono',monospace; }
  .sw-on  { background:rgba(31,208,128,0.1); border-color:rgba(31,208,128,0.35);
            box-shadow:inset 0 0 20px rgba(31,208,128,0.06); }
  .sw-on .switch-val { color:var(--green); }
  .sw-off { background:rgba(255,77,94,0.1); border-color:rgba(255,77,94,0.35);
            box-shadow:inset 0 0 20px rgba(255,77,94,0.06); }
  .sw-off .switch-val { color:var(--red); }

  /* Widgets */
  [data-testid="stDataFrame"] { background:var(--panel); border:1px solid var(--border);
        border-radius:14px; padding:6px; }
  [data-testid="stDataFrame"] * { color:var(--txt)!important;
        font-family:'JetBrains Mono',monospace!important; font-size:13px!important; }
  div[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--border);
        border-radius:13px; }
  div[data-testid="stExpander"] summary { color:var(--txt2)!important; }
  .stSelectbox div[data-baseweb="select"] > div { background:var(--panel-hi);
        border-color:var(--border); color:var(--txt); border-radius:10px; }
  .stButton button { background:linear-gradient(135deg,var(--accent),#3A66E0);
        color:#fff; border:none; border-radius:10px; font-weight:700;
        letter-spacing:0.3px; transition:transform .1s, box-shadow .2s;
        box-shadow:0 4px 14px rgba(77,124,254,0.3); }
  .stButton button:hover { transform:translateY(-1px);
        box-shadow:0 6px 20px rgba(77,124,254,0.45); }
  .stTextArea textarea { background:var(--panel-hi); color:var(--txt);
        border-color:var(--border); border-radius:10px;
        font-family:'JetBrains Mono',monospace; }
  .caption-sub { color:var(--txt2); font-size:12.5px; margin:2px 0 10px; }
  hr { border-color:var(--border)!important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
live = connected()
conn = ('<span class="conn-pill conn-live"><span class="dot"></span>LIVE · Angel One</span>'
        if live else
        '<span class="conn-pill conn-off"><span class="dot"></span>Connect Angel One</span>')
st.markdown(f"""
<div class="topbar">
  <div class="brand">
    <span class="brand-mark">SuperSwarna</span>
    <span class="brand-tag">Market Risk &amp; Momentum Terminal</span>
  </div>
  <div class="status">
    {conn}
    <span class="clock">{datetime.now().strftime('%d %b %Y · %H:%M')} IST</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══ SECTION 1 — RISK INDICATOR ════════════════════════════════════════════════
st.markdown("""<div class="eyebrow"><span class="eyebrow-num">01</span>
<span class="eyebrow-txt">Risk Indicator — Minervini &amp; Supertrend (10,3)</span>
<span class="eyebrow-line"></span></div>""", unsafe_allow_html=True)

cols = st.columns(2)
risks = {}
for i, idx in enumerate(INDEX_TOKENS.keys()):
    with cols[i]:
        with st.spinner(f"Loading {idx}…"):
            rk = index_risk(idx)
        risks[idx] = rk
        if rk["minervini"] is None:
            st.markdown(f"""<div class="rcard"><div class="rc-name">{idx}</div>
            <div class="rc-ltp">—</div><div style="color:#7E8DAE;font-size:13px">
            Awaiting data — check Angel One connection</div></div>""",
            unsafe_allow_html=True)
            continue
        ltp = rk["ltp"]; chg = rk["chg"]; pts = rk.get("chg_pts", 0)
        pos = chg >= 0
        card_cls = "pos" if pos else "neg"
        arrow = "▲" if pos else "▼"
        chip_cls = "chip-pos" if pos else "chip-neg"
        sign = "+" if pos else "−"
        mv_cls = "sw-on" if rk["minervini"] else "sw-off"
        mv_txt = "RISK ON" if rk["minervini"] else "RISK OFF"
        st_cls = "sw-on" if rk["supertrend"] else "sw-off"
        st_txt = "BUY" if rk["supertrend"] else "SELL"
        st.markdown(f"""
        <div class="rcard {card_cls}">
          <div class="rc-top">
            <div class="rc-name">{idx}</div>
          </div>
          <div class="rc-ltp">{ltp:,.2f}</div>
          <div class="rc-chg">
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

with st.expander("Minervini condition detail"):
    for idx, rk in risks.items():
        if rk["minervini"] is not None:
            st.markdown(f"**{idx}** — {rk['conditions_met']}/{rk['total_conditions']} "
                        f"conditions met · Price ₹{rk['price']:,.1f} · 200 DMA ₹{rk['ma200']:,.1f}")

# ═══ SECTION 2 — CHARTINK SCREENER ═════════════════════════════════════════════
st.markdown("""<div class="eyebrow"><span class="eyebrow-num">02</span>
<span class="eyebrow-txt">Chartink Screener</span>
<span class="eyebrow-line"></span></div>""", unsafe_allow_html=True)
st.markdown('<div class="caption-sub">Live results from your Chartink scans · '
            'free Chartink data is delayed ~30-45 min</div>', unsafe_allow_html=True)

ck1, ck2 = st.columns([2, 1])
with ck1:
    screener_name = st.selectbox("Screener", list(DEFAULT_SCREENERS.keys()), key="ck_screener")
with ck2:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    run_ck = st.button("Run scan", use_container_width=True, key="ck_run")

with st.expander("Or paste a custom scan clause"):
    custom_clause = st.text_area(
        "scan_clause (Chartink → Network → process → Payload)",
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
        st.dataframe(ck_df, use_container_width=True, hide_index=True, height=480,
            column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
        st.markdown(f'<div class="caption-sub">{len(ck_df)} stocks matched · '
                    'click any column header to sort</div>', unsafe_allow_html=True)
else:
    st.info("Pick a screener and click Run scan.")

st.divider()
st.markdown('<div class="caption-sub" style="text-align:center">SuperSwarna · '
            'Minervini SEPA + Supertrend (Angel One) · Chartink (unofficial, delayed) · '
            'Not investment advice</div>', unsafe_allow_html=True)
