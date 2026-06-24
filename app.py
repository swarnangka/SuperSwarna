"""
Parabolic Trends — Market Risk & Momentum Terminal
All 43 tasks implemented in one clean build.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from data_layer import INDEX_TOKENS, connected
from engine import index_risk
from chartink import run_chartink_scan, DEFAULT_SCREENERS
from market_web import gainers_losers, nifty50, advance_decline, nifty50_heatmap_yf
from events_news import results_today, events_window, news_digest
from banlist import fno_ban_mwpl
from hhll import get_hhll_signals
from morning_brief import (fetch_global_pulse, fetch_indian_recap,
                           compute_key_levels, fetch_top_news, generate_synthesis)
from fii_sectors import get_fii_sector_heatmap

IST = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="Parabolic Trends", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Professional dark theme ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
:root {
  --bg:#0D1117; --panel:#161B22; --panel2:#1C2128; --border:#30363D;
  --txt:#E6EDF3; --txt2:#8B949E; --txt3:#484F58;
  --purple:#7C5CFC; --green:#2EC4A0; --red:#F85149; --amber:#D29922;
  --font-num:'JetBrains Mono',monospace; --font-ui:'Inter',sans-serif;
}
.stApp { background:var(--bg); color:var(--txt); font-family:var(--font-ui); }
#MainMenu,footer,header { visibility:hidden; }
.block-container { padding:0 1.4rem 3rem; max-width:1320px; }
h1,h2,h3,h4 { color:var(--txt)!important; font-family:var(--font-ui)!important; }

/* Ticker tape */
.ticker-wrap { background:#0A0F16; border-bottom:1px solid var(--border);
  padding:6px 0; overflow:hidden; width:100%; }
.ticker-inner { display:flex; animation:ticker 60s linear infinite; white-space:nowrap; }
.ticker-inner:hover { animation-play-state:paused; }
@keyframes ticker { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.t-item { display:inline-flex; align-items:center; gap:6px; padding:0 22px;
  font-family:var(--font-num); font-size:12px; border-right:1px solid var(--border); }
.t-name { color:var(--txt2); font-size:11px; }
.t-val { color:var(--txt); font-weight:500; }
.t-up { color:var(--green); } .t-dn { color:var(--red); }

/* Header */
.topbar { display:flex; align-items:center; justify-content:space-between;
  padding:12px 0 10px; border-bottom:1px solid var(--border); margin-bottom:2px; }
.brand { font-size:26px; font-weight:700; color:var(--txt); font-family:var(--font-ui); }
.brand-accent { color:var(--purple); }
.status { display:flex; align-items:center; gap:10px; }
.conn-live { font-size:11px; padding:3px 10px; border-radius:999px; font-weight:600;
  background:rgba(46,196,160,.12); color:var(--green); }
.conn-off  { font-size:11px; padding:3px 10px; border-radius:999px; font-weight:600;
  background:rgba(210,153,34,.12); color:var(--amber); }
.clock { font-size:12px; color:var(--txt2); font-family:var(--font-num); }

/* Section dividers */
.sec { display:flex; align-items:center; gap:10px; margin:20px 0 12px; }
.sec-title { font-size:11px; font-weight:600; letter-spacing:2.5px; text-transform:uppercase;
  color:var(--txt3); white-space:nowrap; }
.sec-line { flex:1; height:1px; background:var(--border); }

/* Risk cards */
.rcard { background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:16px 18px; position:relative; overflow:hidden; }
.rcard::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; }
.pos::before { background:var(--green); } .neg::before { background:var(--red); }
.rc-name { font-size:11px; font-weight:600; letter-spacing:2px; text-transform:uppercase;
  color:var(--purple); margin-bottom:6px; }
.rc-ltp { font-size:30px; font-weight:700; color:var(--txt); font-family:var(--font-num);
  letter-spacing:-1px; line-height:1.1; }
.rc-chg { font-size:13px; font-weight:600; font-family:var(--font-num);
  display:flex; align-items:center; gap:8px; margin-top:3px; }
.chip { padding:2px 8px; border-radius:5px; font-size:12px; font-weight:600; }
.cup { background:rgba(46,196,160,.14); color:var(--green); }
.cdn { background:rgba(248,81,73,.14); color:var(--red); }
.up { color:var(--green); } .dn { color:var(--red); }
.sw-row { display:flex; gap:8px; margin-top:12px; }
.sw { flex:1; border-radius:8px; padding:9px 10px; text-align:center; border:1px solid var(--border); }
.sw-lbl { font-size:9px; letter-spacing:1.5px; text-transform:uppercase; color:var(--txt3); margin-bottom:5px; }
.sw-val { font-size:15px; font-weight:700; font-family:var(--font-num); }
.on  { background:rgba(46,196,160,.1); border-color:rgba(46,196,160,.35); }
.on .sw-val { color:var(--green); }
.off { background:rgba(248,81,73,.1); border-color:rgba(248,81,73,.35); }
.off .sw-val { color:var(--red); }
.rc-sub { font-size:11px; color:var(--txt3); font-family:var(--font-num); margin-top:8px; }

/* Morning brief */
.brief-wrap { background:var(--panel); border:1px solid var(--border);
  border-radius:10px; padding:16px 18px; }
.brief-text { font-size:13.5px; color:var(--txt); line-height:1.75;
  font-family:var(--font-ui); }
.brief-text p { margin:0 0 12px; }
.brief-text p:last-child { margin:0; }
.brief-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px; }
.brief-table { background:var(--panel2); border-radius:8px; padding:10px 12px; }
.bt-title { font-size:10px; letter-spacing:1.5px; text-transform:uppercase;
  color:var(--txt3); margin-bottom:8px; font-weight:600; }
.bt-row { display:flex; justify-content:space-between; padding:3px 0;
  border-bottom:1px solid var(--border); font-size:12px; }
.bt-row:last-child { border:none; }
.bt-label { color:var(--txt2); }
.bt-val { font-family:var(--font-num); color:var(--txt); font-weight:500; }

/* HHLL commodity */
.hl-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.hl-card { background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:14px 16px; position:relative; overflow:hidden; }
.hl-top { position:absolute; top:0; left:0; right:0; height:2px; }
.hl-com { font-size:11px; font-weight:600; letter-spacing:2px; text-transform:uppercase;
  color:var(--txt2); margin:4px 0 2px; }
.hl-unit { font-size:10px; color:var(--txt3); margin-bottom:4px; }
.hl-price { font-size:20px; font-weight:700; color:var(--txt); font-family:var(--font-num); }
.hl-pill { display:inline-block; font-size:11px; font-weight:700; padding:2px 10px;
  border-radius:5px; margin:7px 0 6px; font-family:var(--font-num); }
.lp { background:rgba(46,196,160,.14); color:var(--green); }
.sp { background:rgba(248,81,73,.14); color:var(--red); }
.np { background:rgba(72,79,88,.3); color:var(--txt2); }
.hl-bands { font-size:11px; color:var(--txt3); font-family:var(--font-num); }
.hl-bands span { display:block; line-height:1.7; }
.tf-hdr { font-size:10px; font-weight:600; letter-spacing:2px; text-transform:uppercase;
  color:var(--txt3); margin:14px 0 8px; }
.hdiv { border:none; border-top:1px solid var(--border); margin:14px 0; }

/* Expanders — dark, no white boxes */
div[data-testid="stExpander"] {
  background:var(--panel) !important;
  border:1px solid var(--border) !important;
  border-radius:10px !important;
  margin-bottom:8px !important;
}
div[data-testid="stExpander"] > div:first-child {
  background:var(--panel) !important;
  border-radius:10px !important;
}
div[data-testid="stExpander"] summary {
  background:var(--panel) !important;
  padding:10px 16px !important;
}
div[data-testid="stExpander"] summary p {
  font-size:15px !important; font-weight:600 !important;
  color:var(--txt) !important; font-family:var(--font-ui) !important;
}
div[data-testid="stExpander"] summary:hover p { color:var(--purple) !important; }
div[data-testid="stExpander"] svg { fill:var(--txt3); }
div[data-testid="stExpander"] > div > div {
  background:var(--panel) !important;
  border-radius:0 0 10px 10px !important;
}

/* Dataframes — dark */
[data-testid="stDataFrame"] { background:var(--panel2) !important;
  border:1px solid var(--border) !important; border-radius:8px !important; }
[data-testid="stDataFrame"] iframe { background:var(--panel2) !important; }
[data-testid="stDataFrame"] * { color:var(--txt) !important;
  font-family:var(--font-num) !important; font-size:12px !important; }
.dvs-header-row { background:var(--panel) !important; }

/* Buttons */
.stButton button { background:var(--purple) !important; color:#fff !important;
  border:none !important; border-radius:7px !important; font-weight:600 !important;
  font-size:13px !important; padding:6px 16px !important; }
.stButton button:hover { background:#6A4AE0 !important; }

/* Selectbox */
.stSelectbox div[data-baseweb="select"] > div {
  background:var(--panel2) !important; border-color:var(--border) !important;
  color:var(--txt) !important; border-radius:7px !important; }

/* AD meter */
.ad-wrap { background:var(--panel2); border:1px solid var(--border);
  border-radius:8px; padding:12px 14px; margin-bottom:12px; }
.ad-hdr { display:flex; justify-content:space-between; font-size:12px;
  color:var(--txt2); margin-bottom:7px; }
.ad-bar { display:flex; height:8px; border-radius:4px; overflow:hidden; background:var(--border); }

/* News */
.news-item { padding:8px 0; border-bottom:1px solid var(--border); }
.news-meta { font-size:11px; color:var(--txt3); font-family:var(--font-num); margin-bottom:2px; }
.news-title { font-size:13px; color:var(--txt); line-height:1.5; }
.news-title a { color:var(--txt); text-decoration:none; }
.news-title a:hover { color:var(--purple); }
.stag-bull { color:var(--green); font-size:10px; font-weight:700; }
.stag-bear { color:var(--red); font-size:10px; font-weight:700; }
.stag-neut { color:var(--txt3); font-size:10px; font-weight:700; }

hr { border-color:var(--border) !important; margin:4px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def ist_now():
    return datetime.now(IST)

def fmt_chg(v, decimals=2):
    if v is None: return "—"
    s = "+" if v >= 0 else "−"
    return f"{s}{abs(v):.{decimals}f}%"

def sentiment_tag(headline: str) -> str:
    h = headline.lower()
    bull = ["surge","rally","gain","rise","jump","high","up","bull","strong","record","beat"]
    bear = ["fall","drop","crash","decline","slide","low","down","bear","weak","cut","miss","fear"]
    if any(w in h for w in bull): return "BULL"
    if any(w in h for w in bear): return "BEAR"
    return "NEUT"

# ── Ticker tape data ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def ticker_data():
    import yfinance as yf
    syms = {"S&P 500":"^GSPC","Dow":"^DJI","Nasdaq":"^IXIC","FTSE":"^FTSE",
            "Nikkei":"^N225","DAX":"^GDAXI","DXY":"DX-Y.NYB",
            "Gold":"GC=F","Crude":"CL=F","USD/INR":"USDINR=X",
            "Nifty":"^NSEI","BankNifty":"^NSEBANK"}
    out = []
    try:
        df = yf.download(list(syms.values()), period="2d",
                         auto_adjust=True, progress=False, group_by="ticker")
        for name, sym in syms.items():
            try:
                d = df[sym].dropna() if len(syms) > 1 else df.dropna()
                if len(d) >= 2:
                    last = float(d["Close"].iloc[-1])
                    chg  = (last - float(d["Close"].iloc[-2])) / float(d["Close"].iloc[-2]) * 100
                    out.append({"name": name, "last": last, "chg": chg})
            except Exception:
                continue
    except Exception:
        pass
    return out

# ── Ticker tape HTML ──────────────────────────────────────────────────────────
def render_ticker():
    items = ticker_data()
    if not items: return
    html = '<div class="ticker-wrap"><div class="ticker-inner">'
    segment = ""
    for it in items:
        arrow = "▲" if it["chg"] >= 0 else "▼"
        cls   = "t-up" if it["chg"] >= 0 else "t-dn"
        segment += (f'<span class="t-item">'
                    f'<span class="t-name">{it["name"]}</span>'
                    f'<span class="t-val">{it["last"]:,.2f}</span>'
                    f'<span class="{cls}">{arrow}{abs(it["chg"]):.2f}%</span>'
                    f'</span>')
    html += segment + segment + "</div></div>"
    st.markdown(html, unsafe_allow_html=True)

# ═══ RENDER ════════════════════════════════════════════════════════════════════

render_ticker()

# Header
live = connected()
conn = ('<span class="conn-live">● LIVE</span>' if live
        else '<span class="conn-off">● DELAYED</span>')
st.markdown(
f'<div class="topbar">'
f'<span class="brand">Parabolic<span class="brand-accent">Trends</span></span>'
f'<div class="status">{conn}'
f'<span class="clock">{ist_now().strftime("%d %b %Y · %H:%M")} IST</span>'
f'</div></div>', unsafe_allow_html=True)

# ═══ SECTION 1 — RISK INDICATOR ════════════════════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">Risk Indicator</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)
cols = st.columns(2)
risks = {}
for i, idx in enumerate(INDEX_TOKENS.keys()):
    with cols[i]:
        with st.spinner(""):
            rk = index_risk(idx)
        risks[idx] = rk
        if rk["minervini"] is None:
            st.markdown(f'<div class="rcard"><div class="rc-name">{idx}</div>'
                        f'<div class="rc-ltp">—</div></div>', unsafe_allow_html=True)
            continue
        ltp=rk["ltp"]; chg=rk["chg"]; pts=rk.get("chg_pts",0); pos=chg>=0
        arrow="▲" if pos else "▼"; sign="+" if pos else "−"
        ccard="pos" if pos else "neg"
        cchip="cup" if pos else "cdn"; ctxt="up" if pos else "dn"
        mv_c="on" if rk["minervini"] else "off"
        mv_t="RISK ON" if rk["minervini"] else "RISK OFF"
        st_c="on" if rk["supertrend"] else "off"
        st_t="BUY" if rk["supertrend"] else "SELL"
        pct200 = rk.get("pct_200",0) or 0
        met=rk.get("conditions_met",0); tot=rk.get("total_conditions",7)
        st.markdown(
f'<div class="rcard {ccard}">'
f'<div class="rc-name">{idx}</div>'
f'<div class="rc-ltp">{ltp:,.2f}</div>'
f'<div class="rc-chg {ctxt}"><span>{arrow} {sign}{abs(pts):,.2f}</span>'
f'<span class="chip {cchip}">{sign}{abs(chg):.2f}%</span></div>'
f'<div class="sw-row">'
f'<div class="sw {mv_c}"><div class="sw-lbl">Swarna</div><div class="sw-val">{mv_t}</div></div>'
f'<div class="sw {st_c}"><div class="sw-lbl">Supertrend</div><div class="sw-val">{st_t}</div></div>'
f'</div>'
f'<div class="rc-sub">{met}/{tot} criteria · {pct200:+.1f}% vs 200DMA</div>'
f'</div>', unsafe_allow_html=True)

# Swarna criteria expander
with st.expander("Swarna Criteria — full breakdown"):
    for idx, rk in risks.items():
        if rk.get("checks"):
            met=rk["conditions_met"]; tot=rk["total_conditions"]
            pct=met/tot*100; col="#2EC4A0" if met==tot else ("#D29922" if met>=4 else "#F85149")
            st.markdown(
f'<div style="margin:8px 0 6px">'
f'<div style="display:flex;justify-content:space-between">'
f'<span style="font-weight:600;font-size:14px;color:#E6EDF3">{idx}</span>'
f'<span style="font-family:monospace;color:{col};font-weight:700">{met}/{tot} · {pct:.0f}%</span></div>'
f'<div style="background:#30363D;border-radius:3px;height:5px;margin-top:5px">'
f'<div style="width:{pct}%;background:{col};height:5px;border-radius:3px"></div></div></div>',
                unsafe_allow_html=True)
            for c in rk["checks"]:
                icon="🟢" if c["pass"] else "🔴"
                st.markdown(
f'<div style="padding:3px 0;font-size:13px;color:#E6EDF3">{icon} <b>{c["label"]}</b> '
f'<span style="color:#484F58">· {c["weight"]}/7</span><br>'
f'<span style="color:#8B949E;font-size:11px;margin-left:20px">{c["detail"]}</span></div>',
                    unsafe_allow_html=True)
            st.markdown('<hr style="border-color:#30363D;margin:10px 0">',
                        unsafe_allow_html=True)

# ═══ SECTION 2 — MORNING BRIEF ═════════════════════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">Morning Brief</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)
mb1, mb2 = st.columns([1,4])
with mb1:
    run_brief = st.button("Generate", key="brief_run")
    if st.session_state.get("brief_done"):
        if st.button("Clear", key="brief_clear"):
            st.session_state["brief_done"] = False
            st.rerun()
if run_brief:
    st.session_state["brief_done"] = True
if st.session_state.get("brief_done"):
    with st.spinner("Fetching market data…"):
        gp    = fetch_global_pulse()
        recap = fetch_indian_recap()
        lvls  = compute_key_levels(recap)
        news3 = fetch_top_news(3)
    with st.spinner("Writing brief…"):
        synthesis = generate_synthesis(gp, recap, lvls, news3)
    # Render compact brief
    para_html = "".join(f"<p>{p.strip()}</p>" for p in synthesis.split("\n\n") if p.strip())
    # Global pulse mini table
    gp_rows = ""
    for label, key, fmt in [
        ("DXY","DXY",",.2f"),("Crude","Crude",",.2f"),
        ("Gold","Gold",",.2f"),("Dow","Dow","+,.2f"),("Nasdaq","Nasdaq","+,.2f")]:
        d=gp.get(key,{}); v=d.get("last"); c=d.get("chg")
        vstr=f"{v:{fmt}}" if v else "—"
        cstr=f'<span class="{"t-up" if c and c>=0 else "t-dn"}">{fmt_chg(c)}</span>' if c else "—"
        gp_rows+=f'<div class="bt-row"><span class="bt-label">{label}</span><span class="bt-val">{vstr} {cstr}</span></div>'
    # Nifty levels mini table
    nf=lvls.get("Nifty 50",{})
    lvl_rows=""
    for lbl,k in [("S2","S2"),("S1 / Bias","S1"),("R1","R1"),("R2","R2")]:
        v=nf.get(k,"—")
        lvl_rows+=f'<div class="bt-row"><span class="bt-label">{lbl}</span><span class="bt-val">{v}</span></div>'
    st.markdown(
f'<div class="brief-wrap">'
f'<div class="brief-text">{para_html}</div>'
f'<div class="brief-grid">'
f'<div class="brief-table"><div class="bt-title">Global Pulse</div>{gp_rows}</div>'
f'<div class="brief-table"><div class="bt-title">Nifty Key Levels</div>{lvl_rows}</div>'
f'</div></div>', unsafe_allow_html=True)
else:
    st.markdown('<span style="color:#484F58;font-size:13px">Click Generate for today\'s morning brief.</span>',
                unsafe_allow_html=True)

# ═══ SECTION 3 — HHLL COMMODITY SIGNALS ════════════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">Commodity Signals · HHLL (29) · USD</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)
with st.spinner(""):
    sigs = get_hhll_signals()

for tf_label, tf_key in [("1-Hour — short term", "1H"), ("4-Hour — medium term", "4H")]:
    st.markdown(f'<div class="tf-hdr">{tf_label}</div>', unsafe_allow_html=True)
    hcols = st.columns(3)
    for ci, (name, data) in enumerate(sigs.items()):
        with hcols[ci]:
            s = data[tf_key]; sig = s["signal"]
            price = s["price"]; upper = s["upper"]; lower = s["lower"]; crossed = s["crossed"]
            top_col = "#2EC4A0" if sig=="LONG" else "#F85149" if sig=="SHORT" else "#484F58"
            pill_cls = "lp" if sig=="LONG" else "sp" if sig=="SHORT" else "np"
            price_str = f"{price:,.3f}" if price else "—"
            upper_str = f"{upper:,.3f}" if upper else "—"
            lower_str = f"{lower:,.3f}" if lower else "—"
            st.markdown(
f'<div class="hl-card">'
f'<div class="hl-top" style="background:{top_col}"></div>'
f'<div class="hl-com">{name}</div>'
f'<div class="hl-unit">{data["display_unit"]}</div>'
f'<div class="hl-price">{price_str}</div>'
f'<span class="hl-pill {pill_cls}">{sig}</span>'
f'<div class="hl-bands">'
f'<span>Upper {upper_str}</span>'
f'<span>Lower {lower_str}</span>'
f'<span style="color:#484F58">{crossed}</span>'
f'</div></div>', unsafe_allow_html=True)
    if tf_key == "1H":
        st.markdown('<div class="hdiv"></div>', unsafe_allow_html=True)

# ═══ COLLAPSIBLE SECTIONS ═══════════════════════════════════════════════════════
with st.expander("Market Internals"):
    ic1, ic2 = st.columns([1,1])
    with ic1:
        run_int = st.button("Load", key="int_run")
    with ic2:
        if st.session_state.get("int_done"):
            if st.button("Clear", key="int_clr"):
                st.session_state["int_done"] = False
                st.rerun()
    if run_int: st.session_state["int_done"] = True
    if st.session_state.get("int_done"):
        with st.spinner(""):
            n50=nifty50(); ad=advance_decline(n50)
            gl=gainers_losers(); heat=nifty50_heatmap_yf()
        if ad["total"]==0 and not heat.empty:
            adv=int((heat["Chg %"]>0).sum()); dec=int((heat["Chg %"]<0).sum())
            ad={"adv":adv,"dec":dec,"total":len(heat)}
        if ad["total"]>0:
            adv_pct=ad["adv"]/ad["total"]*100
            st.markdown(
f'<div class="ad-wrap"><div class="ad-hdr"><span>Advance / Decline · Nifty 50</span>'
f'<span><span style="color:#2EC4A0">{ad["adv"]} adv</span> · <span style="color:#F85149">{ad["dec"]} dec</span></span></div>'
f'<div class="ad-bar"><div style="width:{adv_pct}%;background:#2EC4A0"></div>'
f'<div style="flex:1;background:#F85149"></div></div></div>', unsafe_allow_html=True)
        if not heat.empty:
            cells=""
            for _,row in heat.iterrows():
                v=row["Chg %"]
                bg="#1E8E74" if v>1 else "#2EC4A0" if v>0 else "#484F58" if v==0 else "#F85149" if v>-1 else "#A32D2D"
                cells+=(f'<div style="background:{bg};border-radius:5px;padding:5px 3px;text-align:center">'
                        f'<div style="font-size:9px;color:#fff;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{row["Symbol"]}</div>'
                        f'<div style="font-size:10px;color:#fff;font-family:monospace">{v:+.1f}%</div></div>')
            st.markdown(f'<div style="display:grid;grid-template-columns:repeat(10,1fr);gap:3px;margin-bottom:12px">{cells}</div>', unsafe_allow_html=True)
        gc1,gc2=st.columns(2)
        with gc1:
            st.markdown('<b style="color:#2EC4A0;font-size:13px">Top Gainers</b>', unsafe_allow_html=True)
            if not gl["gainers"].empty:
                st.dataframe(gl["gainers"], width="stretch", hide_index=True, height=280,
                    column_config={"Chg %":st.column_config.NumberColumn(format="%.2f%%")})
        with gc2:
            st.markdown('<b style="color:#F85149;font-size:13px">Top Losers</b>', unsafe_allow_html=True)
            if not gl["losers"].empty:
                st.dataframe(gl["losers"], width="stretch", hide_index=True, height=280,
                    column_config={"Chg %":st.column_config.NumberColumn(format="%.2f%%")})

with st.expander("Screeners"):
    sc1,sc2=st.columns([3,1])
    with sc1:
        sname=st.selectbox("Screener",list(DEFAULT_SCREENERS.keys()),
                           key="ck_s",label_visibility="collapsed")
    with sc2:
        run_ck=st.button("Run",key="ck_run",width="stretch")
    if run_ck:
        with st.spinner(""):
            st.session_state["ck_result"]=run_chartink_scan(DEFAULT_SCREENERS[sname])
            st.session_state["ck_name"]=sname
    ck_df=st.session_state.get("ck_result")
    if ck_df is not None:
        if "error" in ck_df.columns: st.error(ck_df["error"].iloc[0])
        elif ck_df.empty: st.caption("No matches.")
        else:
            st.dataframe(ck_df,width="stretch",hide_index=True,height=460,
                column_config={"Chg %":st.column_config.NumberColumn(format="%.2f%%")})
            st.caption(f"{len(ck_df)} matched · {st.session_state.get('ck_name','')}")

with st.expander("Events & Ban List"):
    ec1,ec2=st.columns([1,1])
    with ec1:
        run_ev=st.button("Load",key="ev_run")
    with ec2:
        if st.session_state.get("ev_done"):
            if st.button("Clear",key="ev_clr"):
                st.session_state["ev_done"]=False; st.rerun()
    if run_ev: st.session_state["ev_done"]=True
    if st.session_state.get("ev_done"):
        with st.spinner(""):
            evts=events_window(7); ban=fno_ban_mwpl(); results=results_today()
        if not evts.empty:
            st.markdown('<b style="color:#8B949E;font-size:12px">UPCOMING EVENTS</b>', unsafe_allow_html=True)
            for _,e in evts.iterrows():
                bc="#D29922" if e["When"]=="TODAY" else "#7C5CFC"
                st.markdown(
f'<div style="padding:5px 0;font-size:13px">'
f'<span style="background:{bc};color:#0D1117;font-weight:700;font-size:10px;padding:2px 7px;border-radius:4px">{e["When"]}</span>'
f' <b style="color:#E6EDF3">{e["Date"]} · {e["Type"]}</b>'
f' <span style="color:#8B949E">— {e["Event"]}</span></div>', unsafe_allow_html=True)
        b1,b2=st.columns(2)
        with b1:
            st.markdown('<b style="color:#F85149;font-size:12px">IN BAN (MWPL ≥ 95%)</b>', unsafe_allow_html=True)
            if not ban["banned"].empty:
                st.dataframe(ban["banned"],width="stretch",hide_index=True,height=220,
                    column_config={"MWPL %":st.column_config.NumberColumn(format="%.1f%%")})
            else: st.caption("None / unavailable.")
        with b2:
            st.markdown('<b style="color:#D29922;font-size:12px">APPROACHING (80–95%)</b>', unsafe_allow_html=True)
            if not ban["entrants"].empty:
                st.dataframe(ban["entrants"],width="stretch",hide_index=True,height=220,
                    column_config={"MWPL %":st.column_config.NumberColumn(format="%.1f%%")})
            else: st.caption("None / unavailable.")

with st.expander("FII Sector Flows"):
    fc1,fc2=st.columns([1,1])
    with fc1:
        run_fii=st.button("Load",key="fii_run")
    with fc2:
        if st.session_state.get("fii_done"):
            if st.button("Clear",key="fii_clr"):
                st.session_state["fii_done"]=False; st.rerun()
    if run_fii: st.session_state["fii_done"]=True
    if st.session_state.get("fii_done"):
        with st.spinner("Fetching NSDL sector data…"):
            fii_df=get_fii_sector_heatmap()
        if not fii_df.empty:
            num_cols=[c for c in fii_df.columns if c not in ["Sector","YTD"]]
            def color_flow(val):
                if pd.isna(val): return ""
                if val>5000: return "background:#1E8E74;color:#fff"
                if val>0: return "background:#2EC4A0;color:#0D1117"
                if val>-5000: return "background:#F85149;color:#fff"
                return "background:#A32D2D;color:#fff"
            st.dataframe(fii_df,width="stretch",hide_index=True,height=500)
            st.caption("Source: NSDL fortnightly FPI sector reports · INR Crore")
        else:
            st.info("NSDL data unavailable. Try again — server may have blocked this request.")

with st.expander("Market News"):
    nc1,nc2=st.columns([1,1])
    with nc1:
        run_news=st.button("Load",key="news_run")
    with nc2:
        if st.session_state.get("news_done"):
            if st.button("Clear",key="news_clr"):
                st.session_state["news_done"]=False; st.rerun()
    if run_news: st.session_state["news_done"]=True
    if st.session_state.get("news_done"):
        with st.spinner(""):
            news=news_digest(6)
        if not news.empty:
            for _,n in news.iterrows():
                dt=n["dt"]
                stamp=dt.strftime("%d %b · %H:%M")+" IST" if pd.notna(dt) and dt else ""
                tag=sentiment_tag(n["Headline"])
                tag_html=(f'<span class="stag-bull">↑ BULL</span>' if tag=="BULL"
                          else f'<span class="stag-bear">↓ BEAR</span>' if tag=="BEAR"
                          else f'<span class="stag-neut">· NEUT</span>')
                link=n["Link"]
                head=(f'<a href="{link}" target="_blank">{n["Headline"]}</a>' if link else n["Headline"])
                st.markdown(
f'<div class="news-item">'
f'<div class="news-meta">{stamp} · {n["Source"]} {tag_html}</div>'
f'<div class="news-title">{head}</div>'
f'</div>', unsafe_allow_html=True)
        else:
            st.caption("News feeds unavailable.")

st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
st.markdown(f'<div style="font-size:11px;color:#484F58;text-align:center">'
            f'Parabolic Trends · Swarna criteria + Supertrend · Angel One SmartAPI · '
            f'Yahoo Finance · Chartink · NSDL · RSS · '
            f'{ist_now().strftime("%d %b %Y")} · Not investment advice</div>',
            unsafe_allow_html=True)
