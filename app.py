"""
SuperSwarna — Market Risk & Momentum Terminal (v5)
Dark professional theme · purple #7C5CFC + seagreen #2EC4A0 + white text.
Minimal: risk indicator always visible; everything else in collapsible sections.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from data_layer import INDEX_TOKENS, connected
from engine import index_risk
from chartink import run_chartink_scan, DEFAULT_SCREENERS
from market_web import gainers_losers, nifty50, advance_decline, nifty50_heatmap_yf
from events_news import results_today, events_window, news_digest
from banlist import fno_ban_mwpl

st.set_page_config(page_title="SuperSwarna", page_icon="🪙",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Dark professional theme: purple + seagreen + white ────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
  :root {
    --bg:#0B0E14; --panel:#12161F; --panel2:#1A1F2B; --border:#232A38;
    --txt:#FFFFFF; --txt2:#9BA6B8; --txt3:#5C6678;
    --purple:#7C5CFC; --purple-dim:#5B3FD6; --green:#2EC4A0; --green-dim:#1E8E74;
    --red:#FF5C6C; --amber:#F5B23D;
  }
  .stApp { background:var(--bg); color:var(--txt);
           font-family:'Inter',-apple-system,sans-serif; }
  #MainMenu, footer, header { visibility:hidden; }
  .block-container { padding:1.2rem 1.6rem 3rem; max-width:1280px; }
  h1,h2,h3,h4 { color:var(--txt)!important; }
  .mono { font-family:'JetBrains Mono',monospace; }

  .topbar { display:flex; align-items:center; justify-content:space-between;
            padding-bottom:16px; border-bottom:1px solid var(--border); margin-bottom:6px; }
  .brand-name { font-size:30px; font-weight:800; letter-spacing:-0.5px; color:#FFFFFF; }
  .brand-name .accent { color:var(--purple); }
  .conn-pill { font-size:11px; padding:4px 12px; border-radius:999px; font-weight:600;
               display:inline-flex; align-items:center; gap:6px; }
  .conn-live { background:rgba(46,196,160,0.14); color:var(--green); }
  .conn-off  { background:rgba(245,178,61,0.14); color:var(--amber); }
  .dot { width:7px; height:7px; border-radius:50%; background:currentColor; }
  .clock { font-size:12px; color:var(--txt2); font-family:'JetBrains Mono',monospace;
           margin-left:12px; }

  .risk-card { background:var(--panel); border:1px solid var(--border);
               border-radius:16px; padding:22px 24px; position:relative; overflow:hidden; }
  .risk-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; }
  .risk-card.pos::before { background:var(--green); }
  .risk-card.neg::before { background:var(--red); }
  .risk-idx { font-size:13px; color:var(--purple); font-weight:700;
              letter-spacing:1.5px; text-transform:uppercase; }
  .risk-ltp { font-size:36px; font-weight:800; margin:8px 0 2px; color:#FFFFFF;
              font-family:'JetBrains Mono',monospace; letter-spacing:-1px; }
  .risk-chg { font-size:15px; font-weight:700; display:flex; align-items:center; gap:10px;
              font-family:'JetBrains Mono',monospace; }
  .chg-chip { padding:2px 9px; border-radius:7px; font-size:13px; }
  .up { color:var(--green); } .down { color:var(--red); }
  .chip-up { background:rgba(46,196,160,0.14); color:var(--green); }
  .chip-down { background:rgba(255,92,108,0.14); color:var(--red); }
  .switch-row { display:flex; gap:12px; margin-top:20px; }
  .switch { flex:1; border-radius:12px; padding:13px 14px; text-align:center;
            border:1px solid var(--border); }
  .switch-label { font-size:10px; letter-spacing:1.5px; text-transform:uppercase;
                  color:var(--txt3); margin-bottom:7px; font-weight:600; }
  .switch-val { font-size:17px; font-weight:800; letter-spacing:0.5px;
                font-family:'JetBrains Mono',monospace; }
  .on  { background:rgba(46,196,160,0.1); border-color:rgba(46,196,160,0.4); }
  .on .switch-val { color:var(--green); }
  .off { background:rgba(255,92,108,0.1); border-color:rgba(255,92,108,0.4); }
  .off .switch-val { color:var(--red); }

  /* Collapsible sections — bold, prominent, click to expand/collapse */
  div[data-testid="stExpander"] { background:var(--panel); border:1px solid var(--border);
        border-radius:14px; margin-bottom:12px; }
  div[data-testid="stExpander"] summary { padding:6px 4px; }
  div[data-testid="stExpander"] summary p {
        font-size:16px!important; font-weight:700!important; color:#FFFFFF!important;
        letter-spacing:0.3px; }
  div[data-testid="stExpander"] summary:hover p { color:var(--purple)!important; }
  div[data-testid="stExpander"] svg { fill:var(--purple); }

  [data-testid="stDataFrame"] { background:var(--panel2); border:1px solid var(--border);
        border-radius:10px; padding:4px; }
  [data-testid="stDataFrame"] * { color:var(--txt)!important;
        font-family:'JetBrains Mono',monospace!important; font-size:13px!important; }
  .stSelectbox div[data-baseweb="select"] > div { background:var(--panel2);
        border-color:var(--border); color:var(--txt); border-radius:10px; }
  .stButton button { background:var(--purple); color:#fff; border:none;
        border-radius:9px; font-weight:700; transition:background .15s; }
  .stButton button:hover { background:var(--purple-dim); color:#fff; }
  .sec-head { font-size:11px; letter-spacing:3px; color:var(--txt3);
              text-transform:uppercase; font-weight:700; margin:24px 0 12px; }
  .news-meta { font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--txt3); }
  hr { border-color:var(--border)!important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
live = connected()
conn = ('<span class="conn-pill conn-live"><span class="dot"></span>LIVE</span>' if live
        else '<span class="conn-pill conn-off"><span class="dot"></span>OFFLINE</span>')
st.markdown(
f'<div class="topbar">'
f'<span class="brand-name">Super<span class="accent">Swarna</span></span>'
f'<div>{conn}<span class="clock">{datetime.now().strftime("%d %b · %H:%M")} IST</span></div>'
f'</div>', unsafe_allow_html=True)

# ═══ RISK INDICATOR — always visible ═══════════════════════════════════════════
cols = st.columns(2)
risks = {}
for i, idx in enumerate(INDEX_TOKENS.keys()):
    with cols[i]:
        with st.spinner(""):
            rk = index_risk(idx)
        risks[idx] = rk
        if rk["minervini"] is None:
            st.markdown(
f'<div class="risk-card"><div class="risk-idx">{idx}</div>'
f'<div class="risk-ltp">—</div></div>', unsafe_allow_html=True)
            continue
        ltp = rk["ltp"]; chg = rk["chg"]; pts = rk.get("chg_pts", 0)
        pos = chg >= 0
        card_cls = "pos" if pos else "neg"
        arrow = "▲" if pos else "▼"
        chip_cls = "chip-up" if pos else "chip-down"
        sign = "+" if pos else "−"
        mv_cls = "on" if rk["minervini"] else "off"
        mv_txt = "RISK ON" if rk["minervini"] else "RISK OFF"
        st_cls = "on" if rk["supertrend"] else "off"
        st_txt = "BUY" if rk["supertrend"] else "SELL"
        st.markdown(
f'<div class="risk-card {card_cls}">'
f'<div class="risk-idx">{idx}</div>'
f'<div class="risk-ltp">{ltp:,.2f}</div>'
f'<div class="risk-chg {("up" if pos else "down")}">'
f'<span>{arrow} {sign}{abs(pts):,.2f}</span>'
f'<span class="chg-chip {chip_cls}">{sign}{abs(chg):.2f}%</span></div>'
f'<div class="switch-row">'
f'<div class="switch {mv_cls}"><div class="switch-label">Swarna</div>'
f'<div class="switch-val">{mv_txt}</div></div>'
f'<div class="switch {st_cls}"><div class="switch-label">Supertrend</div>'
f'<div class="switch-val">{st_txt}</div></div>'
f'</div></div>', unsafe_allow_html=True)

st.markdown('<div class="sec-head">Sections</div>', unsafe_allow_html=True)

# ═══ MINERVINI DETAIL (collapsible) ════════════════════════════════════════════
with st.expander("Swarna Criteria"):
    for idx, rk in risks.items():
        if rk.get("checks"):
            met = rk["conditions_met"]; tot = rk["total_conditions"]
            pct = met / tot * 100
            col = "#2EC4A0" if met == tot else ("#F5B23D" if met >= 4 else "#FF5C6C")
            st.markdown(
f'<div style="margin:8px 0 6px">'
f'<div style="display:flex;justify-content:space-between">'
f'<span style="font-weight:700;font-size:15px">{idx}</span>'
f'<span style="font-family:monospace;color:{col};font-weight:700">{met}/{tot} · {pct:.0f}%</span></div>'
f'<div style="background:#232A38;border-radius:4px;height:6px;margin-top:6px">'
f'<div style="width:{pct}%;background:{col};height:6px;border-radius:4px"></div></div></div>',
                unsafe_allow_html=True)
            for c in rk["checks"]:
                icon = "🟢" if c["pass"] else "🔴"
                st.markdown(f"<div style='padding:3px 0 3px 4px;font-size:13px'>{icon} "
                    f"<b>{c['label']}</b> <span style='color:#5C6678'>· {c['weight']}/7</span><br>"
                    f"<span style='color:#9BA6B8;font-size:12px;margin-left:22px'>{c['detail']}</span></div>",
                    unsafe_allow_html=True)
            st.markdown("<hr style='border-color:#232A38;margin:10px 0'>", unsafe_allow_html=True)

# ═══ MARKET INTERNALS (collapsible) ════════════════════════════════════════════
with st.expander("Market Internals"):
    if st.button("Load", key="intern_run"):
        st.session_state["intern_done"] = True
    if st.session_state.get("intern_done"):
        with st.spinner(""):
            n50 = nifty50(); ad = advance_decline(n50)
            gl = gainers_losers(); heat = nifty50_heatmap_yf()
        if ad["total"] == 0 and not heat.empty:
            adv = int((heat["Chg %"] > 0).sum()); dec = int((heat["Chg %"] < 0).sum())
            ad = {"adv": adv, "dec": dec, "total": len(heat)}
        if ad["total"] > 0:
            adv_pct = ad["adv"] / ad["total"] * 100
            st.markdown(
f'<div style="background:#1A1F2B;border:1px solid #232A38;border-radius:12px;padding:14px 18px;margin-bottom:14px">'
f'<div style="display:flex;justify-content:space-between;font-size:13px;color:#9BA6B8;margin-bottom:8px">'
f'<span>Advance / Decline</span>'
f'<span><span style="color:#2EC4A0">{ad["adv"]} adv</span> · '
f'<span style="color:#FF5C6C">{ad["dec"]} dec</span></span></div>'
f'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;background:#232A38">'
f'<div style="width:{adv_pct}%;background:#2EC4A0"></div>'
f'<div style="flex:1;background:#FF5C6C"></div></div></div>',
                unsafe_allow_html=True)
        if not heat.empty:
            cells = ""
            for _, row in heat.iterrows():
                v = row["Chg %"]
                bg = "#1E8E74" if v > 1 else "#2EC4A0" if v > 0 else "#888780" if v == 0 else "#FF5C6C" if v > -1 else "#A33741"
                cells += (f'<div style="background:{bg};border-radius:6px;padding:6px 4px;text-align:center">'
                          f'<div style="font-size:9px;color:#fff;font-weight:600;overflow:hidden;'
                          f'text-overflow:ellipsis;white-space:nowrap">{row["Symbol"]}</div>'
                          f'<div style="font-size:10px;color:#fff">{v:+.1f}%</div></div>')
            st.markdown(f'<div style="display:grid;grid-template-columns:repeat(10,1fr);'
                        f'gap:4px;margin-bottom:14px">{cells}</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("<b style='color:#2EC4A0'>Top gainers</b>", unsafe_allow_html=True)
            if not gl["gainers"].empty:
                st.dataframe(gl["gainers"], width="stretch", hide_index=True, height=300,
                    column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
        with g2:
            st.markdown("<b style='color:#FF5C6C'>Top losers</b>", unsafe_allow_html=True)
            if not gl["losers"].empty:
                st.dataframe(gl["losers"], width="stretch", hide_index=True, height=300,
                    column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})

# ═══ CHARTINK SCREENER (collapsible) ═══════════════════════════════════════════
with st.expander("Screeners"):
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        screener_name = st.selectbox("Screener", list(DEFAULT_SCREENERS.keys()),
                                     key="ck_screener", label_visibility="collapsed")
    with sc2:
        run_ck = st.button("Run", key="ck_run", width="stretch")
    if run_ck:
        with st.spinner(""):
            st.session_state["ck_result"] = run_chartink_scan(DEFAULT_SCREENERS[screener_name])
            st.session_state["ck_name"] = screener_name
    ck_df = st.session_state.get("ck_result")
    if ck_df is not None:
        if "error" in ck_df.columns:
            st.error(ck_df["error"].iloc[0])
        elif ck_df.empty:
            st.caption("No matches.")
        else:
            st.dataframe(ck_df, width="stretch", hide_index=True, height=460,
                column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
            st.caption(f"{len(ck_df)} matched · {st.session_state.get('ck_name','')}")

# ═══ EVENTS & BAN LIST (collapsible) ═══════════════════════════════════════════
with st.expander("Events & Ban List"):
    if st.button("Load", key="ev_run"):
        st.session_state["ev_done"] = True
    if st.session_state.get("ev_done"):
        with st.spinner(""):
            evts = events_window(7); ban = fno_ban_mwpl(); results = results_today()
        if not evts.empty:
            for _, e in evts.iterrows():
                badge = "#F5B23D" if e["When"] == "TODAY" else "#7C5CFC"
                st.markdown(f"<div style='padding:5px 0'><span style='background:{badge};"
                    f"color:#0B0E14;font-weight:700;font-size:10px;padding:2px 8px;"
                    f"border-radius:6px'>{e['When']}</span> <b>{e['Date']} · {e['Type']}</b> "
                    f"<span style='color:#9BA6B8'>— {e['Event']}</span></div>", unsafe_allow_html=True)
        asof = ban.get("asof", "")
        b1, b2 = st.columns(2)
        with b1:
            st.markdown("<b style='color:#FF5C6C'>In ban (≥95%)</b>", unsafe_allow_html=True)
            if not ban["banned"].empty:
                st.dataframe(ban["banned"], width="stretch", hide_index=True, height=240,
                    column_config={"MWPL %": st.column_config.NumberColumn(format="%.1f%%")})
            else:
                st.caption("None / source unavailable.")
        with b2:
            st.markdown("<b style='color:#F5B23D'>Possible entrants (80–95%)</b>", unsafe_allow_html=True)
            if not ban["entrants"].empty:
                st.dataframe(ban["entrants"], width="stretch", hide_index=True, height=240,
                    column_config={"MWPL %": st.column_config.NumberColumn(format="%.1f%%")})
            else:
                st.caption("None / source unavailable.")
        st.markdown("<b style='color:#7C5CFC'>Results due</b>", unsafe_allow_html=True)
        if not results.empty:
            st.dataframe(results, width="stretch", hide_index=True, height=220)
        else:
            st.caption("None today / source unavailable.")

# ═══ NEWS (collapsible) ════════════════════════════════════════════════════════
with st.expander("Market News"):
    if st.button("Load", key="news_run"):
        st.session_state["news_done"] = True
    if st.session_state.get("news_done"):
        with st.spinner(""):
            news = news_digest(8)
        if not news.empty:
            for _, n in news.iterrows():
                dt = n["dt"]
                stamp = dt.strftime("%d %b · %H:%M") if pd.notna(dt) else ""
                link = n["Link"]
                head = f"<a href='{link}' style='color:#FFFFFF;text-decoration:none'>{n['Headline']}</a>" if link else n["Headline"]
                st.markdown(f"<div style='padding:7px 0;border-bottom:1px solid #232A38'>"
                    f"<span class='news-meta'>{stamp} · {n['Source']}</span><br>{head}</div>",
                    unsafe_allow_html=True)
        else:
            st.caption("News unavailable.")
