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
from market_web import (
    gainers_losers, nifty50, advance_decline, nifty50_heatmap_yf
)
from events_news import (
    fno_ban, results_today, events_window, news_digest
)

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

with st.expander("📋 Minervini Trend Template — full criteria breakdown"):
    st.caption("Each criterion carries equal weight (1 of 7). RISK ON only when all 7 pass. "
               "Supertrend (10,3) is a separate confirmation signal.")
    for idx, rk in risks.items():
        if rk.get("checks"):
            met = rk["conditions_met"]; tot = rk["total_conditions"]
            score_pct = met / tot * 100
            bar_col = "#16C784" if met == tot else ("#F0B90B" if met >= 4 else "#EA3943")
            st.markdown(f"""<div style="margin:10px 0 6px">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-weight:700;font-size:15px">{idx}</span>
                <span style="font-family:monospace;color:{bar_col};font-weight:700">
                  {met}/{tot} criteria · {score_pct:.0f}%</span>
              </div>
              <div style="background:#16213F;border-radius:4px;height:6px;margin-top:6px">
                <div style="width:{score_pct}%;background:{bar_col};height:6px;
                     border-radius:4px"></div></div></div>""", unsafe_allow_html=True)
            for c in rk["checks"]:
                icon = "🟢" if c["pass"] else "🔴"
                wt = c["weight"]
                st.markdown(
                    f"<div style='padding:3px 0 3px 4px;font-size:13px'>{icon} "
                    f"<b>{c['label']}</b> "
                    f"<span style='color:#8A99B8'>· weight {wt}/7</span><br>"
                    f"<span style='color:#8A99B8;font-size:12px;margin-left:22px'>"
                    f"{c['detail']}</span></div>",
                    unsafe_allow_html=True)
            st.markdown("<hr style='border-color:#1E2A4A;margin:12px 0'>",
                        unsafe_allow_html=True)

# ═══ SECTION 2 — MARKET INTERNALS ══════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">02 · Market Internals</div>',
            unsafe_allow_html=True)
st.caption("Advance/decline, gainers/losers (NSE) & Nifty 50 heatmap (Yahoo). "
           "Zero Angel One load. Loads on demand, collapse anytime.")

bc1, bc2 = st.columns([1, 1])
with bc1:
    if st.button("🔄 Load / refresh", key="intern_run", width="stretch"):
        st.session_state["intern_done"] = True
with bc2:
    if st.session_state.get("intern_done"):
        if st.button("✕ Clear", key="intern_clear", width="stretch"):
            st.session_state["intern_done"] = False
            st.rerun()

if st.session_state.get("intern_done"):
    with st.spinner("Fetching market internals…"):
        n50 = nifty50()
        ad = advance_decline(n50)
        gl = gainers_losers()
        heat = nifty50_heatmap_yf()

    nse_ok = not (n50.empty and gl["gainers"].empty)
    with st.expander("Market internals", expanded=True):
        if not nse_ok and heat.empty:
            st.warning("No data returned. NSE can block cloud-server IPs (Streamlit's), "
                       "and Yahoo may be rate-limited. Try refresh in a moment.")
        else:
            # ── Advance/Decline meter ──
            if ad["total"] > 0:
                adv, dec = ad["adv"], ad["dec"]
                adv_pct = adv / ad["total"] * 100
                st.markdown(f"""
                <div style="background:#111A33;border:1px solid #1E2A4A;border-radius:12px;
                            padding:14px 18px;margin-bottom:14px">
                  <div style="display:flex;justify-content:space-between;font-size:13px;
                              color:#8A99B8;margin-bottom:8px">
                    <span>Nifty 50 Advance / Decline</span>
                    <span><span style="color:#16C784">{adv} adv</span> ·
                    <span style="color:#EA3943">{dec} dec</span></span>
                  </div>
                  <div style="display:flex;height:10px;border-radius:5px;overflow:hidden;
                              background:#16213F">
                    <div style="width:{adv_pct}%;background:#16C784"></div>
                    <div style="flex:1;background:#EA3943"></div>
                  </div>
                </div>""", unsafe_allow_html=True)
            elif not heat.empty:
                # Fallback A/D computed from Yahoo heatmap data
                adv = int((heat["Chg %"] > 0).sum())
                dec = int((heat["Chg %"] < 0).sum())
                tot = len(heat)
                adv_pct = adv / tot * 100 if tot else 0
                st.markdown(f"""
                <div style="background:#111A33;border:1px solid #1E2A4A;border-radius:12px;
                            padding:14px 18px;margin-bottom:14px">
                  <div style="display:flex;justify-content:space-between;font-size:13px;
                              color:#8A99B8;margin-bottom:8px">
                    <span>Nifty 50 Advance / Decline</span>
                    <span><span style="color:#16C784">{adv} adv</span> ·
                    <span style="color:#EA3943">{dec} dec</span></span>
                  </div>
                  <div style="display:flex;height:10px;border-radius:5px;overflow:hidden;
                              background:#16213F">
                    <div style="width:{adv_pct}%;background:#16C784"></div>
                    <div style="flex:1;background:#EA3943"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

            # ── Nifty 50 heatmap (Yahoo) ──
            st.markdown("**Nifty 50 heatmap**")
            if not heat.empty:
                cells = ""
                for _, row in heat.iterrows():
                    v = row["Chg %"]
                    if v > 1: bg = "#0E7A4A"
                    elif v > 0: bg = "#16C784"
                    elif v == 0: bg = "#16213F"
                    elif v > -1: bg = "#EA3943"
                    else: bg = "#992E38"
                    cells += (f'<div style="background:{bg};border-radius:6px;padding:6px 4px;'
                              f'text-align:center"><div style="font-size:9px;color:#fff;'
                              f'font-weight:600;overflow:hidden;text-overflow:ellipsis;'
                              f'white-space:nowrap">{row["Symbol"]}</div>'
                              f'<div style="font-size:10px;color:#fff">{v:+.1f}%</div></div>')
                st.markdown(f'<div style="display:grid;grid-template-columns:repeat(10,1fr);'
                            f'gap:4px;margin-bottom:16px">{cells}</div>', unsafe_allow_html=True)
            else:
                st.info("Heatmap data unavailable (Yahoo may be rate-limited — try refresh).")

            # ── Gainers / Losers (NSE) ──
            gc1, gc2 = st.columns(2)
            with gc1:
                st.markdown("**Top gainers**")
                if not gl["gainers"].empty:
                    st.dataframe(gl["gainers"], width="stretch", hide_index=True, height=300,
                        column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
                else:
                    st.caption("Gainers unavailable (NSE may block this server).")
            with gc2:
                st.markdown("**Top losers**")
                if not gl["losers"].empty:
                    st.dataframe(gl["losers"], width="stretch", hide_index=True, height=300,
                        column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
                else:
                    st.caption("Losers unavailable (NSE may block this server).")
else:
    st.info("Click **Load / refresh** to fetch breadth, movers & heatmap.")

# ═══ SECTION 3 — CHARTINK SCREENER ═════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">03 · Chartink Screener</div>',
            unsafe_allow_html=True)
st.caption("Live results from your Chartink scans. Free Chartink data is delayed ~30-45 min.")

ck1, ck2, ck3 = st.columns([2, 1, 1])
with ck1:
    screener_name = st.selectbox("Screener", list(DEFAULT_SCREENERS.keys()), key="ck_screener")
with ck2:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    run_ck = st.button("🔄 Run scan", width="stretch", key="ck_run")
with ck3:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.session_state.get("ck_done"):
        clear_ck = st.button("✕ Clear", width="stretch", key="ck_clear")
        if clear_ck:
            st.session_state["ck_done"] = False
            st.session_state.pop("ck_result", None)
            st.rerun()

if run_ck:
    clause = DEFAULT_SCREENERS[screener_name]
    with st.spinner("Fetching from Chartink…"):
        ck_df = run_chartink_scan(clause)
    st.session_state["ck_done"] = True
    st.session_state["ck_result"] = ck_df
    st.session_state["ck_name"] = screener_name

if st.session_state.get("ck_done"):
    ck_df = st.session_state.get("ck_result")
    if ck_df is None:
        st.info("No results.")
    elif "error" in ck_df.columns:
        st.error(ck_df["error"].iloc[0])
    elif ck_df.empty:
        st.info("No stocks matched this screener right now.")
    else:
        st.dataframe(ck_df, width="stretch", hide_index=True, height=480,
            column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
        st.caption(f"{len(ck_df)} stocks matched “{st.session_state.get('ck_name','')}” · "
                   "click any column header to sort.")
else:
    st.info("Pick a screener and click **Run scan**.")

# ═══ SECTION 4 — EVENTS, BAN LIST, RESULTS & NEWS ══════════════════════════════
st.markdown('<div class="section-eyebrow">04 · Events, Ban List, Results & News</div>',
            unsafe_allow_html=True)
st.caption("Today's market events, F&O ban list, results due & news headlines. "
           "Free sources (NSE + RSS). Loads on demand.")

ec1, ec2 = st.columns([1, 1])
with ec1:
    if st.button("🔄 Load / refresh", key="ev_run", width="stretch"):
        st.session_state["ev_done"] = True
with ec2:
    if st.session_state.get("ev_done"):
        if st.button("✕ Clear", key="ev_clear", width="stretch"):
            st.session_state["ev_done"] = False
            st.rerun()

if st.session_state.get("ev_done"):
    with st.spinner("Fetching events, ban list, results & news…"):
        evts = events_window(7)
        ban = fno_ban()
        results = results_today()
        news = news_digest(6)

    with st.expander("Events & market triggers", expanded=True):
        # ── Upcoming events (FOMC / MSCI) ──
        st.markdown("**Upcoming events (7 days)**")
        if not evts.empty:
            for _, e in evts.iterrows():
                badge = "#F0B90B" if e["When"] == "TODAY" else "#3B82F6"
                st.markdown(
                    f"<div style='padding:5px 0'><span style='background:{badge};"
                    f"color:#06101F;font-weight:700;font-size:10px;padding:2px 8px;"
                    f"border-radius:6px'>{e['When']}</span> "
                    f"<b>{e['Date']} · {e['Type']}</b> — "
                    f"<span style='color:#8A99B8'>{e['Event']}</span></div>",
                    unsafe_allow_html=True)
        else:
            st.caption("No FOMC/MSCI events in the next 7 days.")

        # ── F&O ban list ──
        st.markdown("<div style='height:10px'></div>**F&O ban list (today)**",
                    unsafe_allow_html=True)
        if not ban["banned"].empty:
            st.dataframe(ban["banned"], width="stretch", hide_index=True, height=220)
        else:
            st.caption("Ban list unavailable (NSE may block this server) or no stocks banned.")

        # ── Results today ──
        st.markdown("**Results / earnings due**")
        if not results.empty:
            st.dataframe(results, width="stretch", hide_index=True, height=240)
        else:
            st.caption("No results found for today, or NSE endpoint unavailable.")

    with st.expander("Market news headlines", expanded=True):
        if not news.empty:
            for src in news["Source"].unique():
                st.markdown(f"**{src}**")
                sub = news[news["Source"] == src]
                for _, n in sub.iterrows():
                    link = n["Link"]
                    if link:
                        st.markdown(f"- [{n['Headline']}]({link})")
                    else:
                        st.markdown(f"- {n['Headline']}")
        else:
            st.caption("News feeds unavailable right now.")
else:
    st.info("Click **Load / refresh** to fetch events, ban list, results & news.")

st.divider()
st.caption("SuperSwarna · Minervini SEPA + Supertrend (Angel One) · Chartink (unofficial, delayed) · "
           "NSE + RSS news · Not investment advice.")
