"""
Parabolic Trends v8
Section order: Morning Brief → Risk → Swarna → Commodity → rest.
Commodity Signals always visible (no expander).
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone, timedelta

from data_layer import INDEX_TOKENS, connected
from market_status import nse_equity_status, mcx_status
from engine import index_risk, us_index_risk, US_INDICES
from chartink import run_chartink_scan, DEFAULT_SCREENERS, fetch_tape_scan
from market_web import gainers_losers, nifty50_heatmap_yf, sector_heatmap_yf
from events_news import results_today, events_window, news_digest
from banlist import fno_ban_mwpl
from hhll import get_hhll_signals
from morning_brief import (fetch_global_pulse, fetch_indian_recap,
                           compute_key_levels, fetch_top_news, generate_synthesis)
from fii_sectors import get_fii_sectors, render_fii_heatmap
from concurrent.futures import ThreadPoolExecutor, as_completed

IST = timezone(timedelta(hours=5, minutes=30))

def ist_now():
    return datetime.now(IST)

def fetch_yf_parallel(symbols: dict, period: str = "2d",
                      max_workers: int = 8, timeout_s: float = 12.0) -> dict:
    def _fetch_one(name, sym):
        try:
            df = yf.download(sym, period=period, auto_adjust=True,
                             progress=False, timeout=8)
            if df is None or df.empty: return name, None
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df.dropna()
            if len(df) < 2: return name, None
            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            return name, {"last": round(last,4), "chg": round((last-prev)/prev*100,4)}
        except Exception:
            return name, None
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_one, n, s): n for n, s in symbols.items()}
        for fut in as_completed(futures, timeout=timeout_s):
            try:
                name, val = fut.result()
                results[name] = val
            except Exception:
                results[futures[fut]] = None
    for name in symbols:
        if name not in results: results[name] = None
    return results

st.set_page_config(page_title="Parabolic Trends", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt_chg(v, decimals=2):
    if v is None: return "—"
    s = "+" if v >= 0 else "−"
    return f"{s}{abs(v):.{decimals}f}%"

def sentiment_tag(h):
    h = h.lower()
    if any(w in h for w in ["surge","rally","gain","rise","jump","bull","record","beat","high"]):
        return "BULL"
    if any(w in h for w in ["fall","drop","crash","decline","slide","bear","cut","miss","fear","weak"]):
        return "BEAR"
    return "NEUT"

# ── Theme ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
:root{--bg:#0D1117;--panel:#161B22;--panel2:#1C2128;--border:#30363D;
  --txt:#E6EDF3;--txt2:#8B949E;--txt3:#484F58;
  --purple:#7C5CFC;--green:#2EC4A0;--red:#F85149;--amber:#D29922;
  --fn:'JetBrains Mono',monospace;--fs:'Inter',sans-serif;}
.stApp{background:var(--bg);color:var(--txt);font-family:var(--fs);}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:0 1rem 3rem;max-width:1320px;}
h1,h2,h3,h4{color:var(--txt)!important;font-family:var(--fs)!important;}

/* ── Tape ── */
.tape-wrap{overflow:hidden;width:100%;border-bottom:1px solid var(--border);}
/* Force each tape to be exactly one horizontal line — no wrapping ever */
.tape-row{display:flex;align-items:center;width:100%;overflow:hidden;
  border-bottom:1px solid var(--border);background:var(--bg);padding:2px 0;}
.tape-scroll{overflow:hidden;flex:1;white-space:nowrap;}
.tape-inner{display:inline-flex;white-space:nowrap;will-change:transform;}
.tape-inner.fast{animation:ticker 80s linear infinite;}
.tape-inner.med{animation:ticker 35s linear infinite;}
.tape-inner:hover{animation-play-state:paused;}
/* 3 copies — animation moves through exactly 1/3 of total width for seamless loop */
@keyframes ticker{0%{transform:translateX(0)}100%{transform:translateX(-33.333%)}}
.t-item{display:inline-flex;align-items:center;gap:5px;padding:0 14px;
  font-family:var(--fn);font-size:12px;border-right:1px solid var(--border);
  white-space:nowrap;flex-shrink:0;}
.t-name{color:var(--txt2);font-size:11px;}
.t-val{color:var(--txt);font-weight:500;}
.t-up{color:var(--green);}.t-dn{color:var(--red);}
/* Badge pinned left, never scrolls */
.tape-badge-pin{flex-shrink:0;padding:2px 8px;border-radius:4px;
  font-size:10px;font-weight:700;letter-spacing:1px;font-family:var(--fn);
  margin:0 6px;}

/* ── Header ── */
.topbar{display:flex;align-items:center;justify-content:space-between;
  padding:10px 0 8px;border-bottom:1px solid var(--border);margin-bottom:2px;}
.brand{font-size:22px;font-weight:700;color:var(--txt);}
.brand em{color:var(--purple);font-style:normal;}
.hdr-right{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}
.conn-live{font-size:11px;padding:3px 8px;border-radius:999px;font-weight:600;
  background:rgba(46,196,160,.12);color:var(--green);}
.conn-off{font-size:11px;padding:3px 8px;border-radius:999px;font-weight:600;
  background:rgba(210,153,34,.12);color:var(--amber);}
.clock{font-size:12px;color:var(--txt2);font-family:var(--fn);}
/* Market status pills */
.mkt-pill{font-size:10px;padding:3px 8px;border-radius:6px;font-weight:700;
  display:inline-flex;align-items:center;gap:4px;white-space:nowrap;
  font-family:var(--fn);letter-spacing:0.5px;}
.mkt-pill-label{font-size:9px;color:var(--txt3);margin-right:2px;font-weight:400;}
.mkt-open{background:rgba(46,196,160,.12);border:1px solid rgba(46,196,160,.4);color:var(--green);}
.mkt-closed-pill{background:rgba(72,79,88,.15);border:1px solid var(--border);color:var(--txt3);}
.mkt-holiday-pill{background:rgba(210,153,34,.1);border:1px solid rgba(210,153,34,.4);color:var(--amber);}
.mkt-dot{width:5px;height:5px;border-radius:50%;background:currentColor;
  display:inline-block;margin-right:2px;}

/* ── Section dividers ── */
.sec{display:flex;align-items:center;gap:10px;margin:16px 0 10px;}
.sec-title{font-size:11px;font-weight:600;letter-spacing:2.5px;
  text-transform:uppercase;color:var(--txt3);white-space:nowrap;}
.sec-line{flex:1;height:1px;background:var(--border);}

/* ── Risk cards ── */
.rcard{background:var(--panel);border:1px solid var(--border);
  border-radius:10px;padding:14px 16px;position:relative;overflow:hidden;}
.rcard::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.pos::before{background:var(--green);}.neg::before{background:var(--red);}
.rc-name{font-size:11px;font-weight:600;letter-spacing:2px;
  text-transform:uppercase;color:var(--purple);margin-bottom:5px;}
.rc-ltp{font-size:28px;font-weight:700;color:var(--txt);
  font-family:var(--fn);letter-spacing:-1px;line-height:1.1;}
.rc-chg{font-size:13px;font-weight:600;font-family:var(--fn);
  display:flex;align-items:center;gap:7px;margin-top:3px;}
.chip{padding:2px 7px;border-radius:5px;font-size:12px;font-weight:600;}
.cup{background:rgba(46,196,160,.14);color:var(--green);}
.cdn{background:rgba(248,81,73,.14);color:var(--red);}
.up{color:var(--green);}.dn{color:var(--red);}
.risk-block{display:flex;align-items:center;gap:10px;margin-top:12px;}
.risk-badge{font-size:13px;font-weight:800;padding:5px 14px;
  border-radius:7px;font-family:var(--fn);letter-spacing:1px;}
.risk-score{font-size:12px;color:var(--txt2);font-family:var(--fn);}
.st-row{display:flex;gap:7px;margin-top:9px;}
.st-pill{flex:1;border-radius:8px;padding:8px 10px;text-align:center;
  border:1px solid var(--border);}
.st-lbl{font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--txt3);margin-bottom:4px;font-weight:600;}
.st-val{font-size:13px;font-weight:800;font-family:var(--fn);}
.on{background:rgba(46,196,160,.1);border-color:rgba(46,196,160,.35);}
.on .st-val{color:var(--green);}
.off{background:rgba(248,81,73,.1);border-color:rgba(248,81,73,.35);}
.off .st-val{color:var(--red);}
.rc-sub{font-size:11px;color:var(--txt3);font-family:var(--fn);margin-top:7px;}
.score-bar-bg{background:var(--border);border-radius:3px;height:4px;margin-top:5px;}
.score-bar{height:4px;border-radius:3px;}

/* ── HHLL cards ── */
.hl-card{background:var(--panel);border:1px solid var(--border);
  border-radius:10px;padding:12px 14px;position:relative;overflow:hidden;}
.hl-top{position:absolute;top:0;left:0;right:0;height:2px;}
.hl-com{font-size:11px;font-weight:600;letter-spacing:2px;
  text-transform:uppercase;color:var(--txt2);margin:3px 0 2px;}
.hl-unit{font-size:10px;color:var(--txt3);margin-bottom:3px;}
.hl-price-row{display:flex;align-items:baseline;gap:8px;}
.hl-price{font-size:20px;font-weight:700;color:var(--txt);font-family:var(--fn);}
.hl-pchg{font-size:13px;font-weight:600;font-family:var(--fn);}
.hl-pill{display:inline-block;font-size:11px;font-weight:700;padding:2px 10px;
  border-radius:5px;margin:5px 0 4px;font-family:var(--fn);}
.lp{background:rgba(46,196,160,.14);color:var(--green);}
.sp{background:rgba(248,81,73,.14);color:var(--red);}
.np{background:rgba(72,79,88,.3);color:var(--txt2);}
.hl-bands{font-size:11px;color:var(--txt3);font-family:var(--fn);}
.hl-bands span{display:block;line-height:1.7;}
.hl-sig-ts{font-size:10px;color:var(--purple);margin-top:3px;font-family:var(--fn);}
.hdiv{border:none;border-top:1px solid var(--border);margin:10px 0;}

/* ── Brief ── */
.brief-wrap{background:var(--panel);border:1px solid var(--border);
  border-radius:10px;padding:16px 18px;}
.brief-text{font-size:13.5px;color:var(--txt);line-height:1.78;font-family:var(--fs);}
.brief-text p{margin:0 0 11px;}
.brief-text p:last-child{margin:0;}

/* ── Expanders ── */
div[data-testid="stExpander"]{background:var(--panel)!important;
  border:1px solid var(--border)!important;border-radius:10px!important;
  margin-bottom:8px!important;}
div[data-testid="stExpander"]>div:first-child{background:var(--panel)!important;}
div[data-testid="stExpander"] summary{background:var(--panel)!important;
  padding:9px 16px!important;}
div[data-testid="stExpander"] summary p{font-size:14px!important;
  font-weight:600!important;color:var(--txt)!important;}
div[data-testid="stExpander"] summary:hover p{color:var(--purple)!important;}
div[data-testid="stExpander"] svg{fill:var(--txt3);}
div[data-testid="stExpander"]>div>div{background:var(--panel)!important;}

/* ── Dataframes ── */
[data-testid="stDataFrame"]{background:var(--panel2)!important;
  border:1px solid var(--border)!important;border-radius:8px!important;}
[data-testid="stDataFrame"] iframe{background:var(--panel2)!important;}
[data-testid="stDataFrame"] *{color:var(--txt)!important;
  font-family:var(--fn)!important;font-size:12px!important;}

/* ── Buttons ── */
.stButton button{background:var(--purple)!important;color:#fff!important;
  border:none!important;border-radius:7px!important;font-weight:600!important;
  font-size:13px!important;padding:5px 14px!important;}
.stButton button:hover{background:#6044D8!important;}
.dash-btn .stButton button{background:transparent!important;
  border:1px solid var(--border)!important;color:var(--txt2)!important;
  font-size:12px!important;padding:4px 12px!important;}
.dash-btn .stButton button:hover{border-color:var(--purple)!important;
  color:var(--purple)!important;}

/* ── Stale badge ── */
.stale-badge{font-size:10px;color:var(--txt3);font-family:var(--fn);
  padding:2px 8px;border-radius:4px;background:var(--panel2);
  border:1px solid var(--border);}
.stale-live{color:var(--green);border-color:rgba(46,196,160,.3);
  background:rgba(46,196,160,.08);}

/* ── Market closed banner ── */
.mkt-closed-banner{background:var(--panel2);border:1px solid var(--border);
  border-radius:8px;padding:8px 14px;margin:8px 0;font-size:12px;
  color:var(--txt3);font-family:var(--fn);text-align:center;}

/* ── Mobile responsive ── */
@media(max-width:768px){
  .block-container{padding:0 0.5rem 2rem!important;}
  .rc-ltp{font-size:22px!important;}
  .hl-price{font-size:16px!important;}
  .t-item{padding:0 10px!important;}
  .risk-badge{font-size:11px!important;padding:3px 10px!important;}
}

.stSelectbox div[data-baseweb="select"]>div{background:var(--panel2)!important;
  border-color:var(--border)!important;color:var(--txt)!important;border-radius:7px!important;}
.stRadio>div{gap:6px!important;}
.ad-wrap{background:var(--panel2);border:1px solid var(--border);
  border-radius:8px;padding:11px 14px;margin-bottom:11px;}
.ad-hdr{display:flex;justify-content:space-between;font-size:12px;
  color:var(--txt2);margin-bottom:6px;}
.ad-bar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--border);}
.news-item{padding:7px 0;border-bottom:1px solid var(--border);}
.news-meta{font-size:11px;color:var(--txt3);font-family:var(--fn);margin-bottom:2px;}
.news-hl{font-size:13px;color:var(--txt);line-height:1.5;}
.news-hl a{color:var(--txt);text-decoration:none;}
.news-hl a:hover{color:var(--purple);}
.bull{color:var(--green);font-size:10px;font-weight:700;}
.bear{color:var(--red);font-size:10px;font-weight:700;}
.neut{color:var(--txt3);font-size:10px;}
hr{border-color:var(--border)!important;margin:4px 0!important;}
</style>
""", unsafe_allow_html=True)

# ── Tape helpers ───────────────────────────────────────────────────────────────
def _tape_items_html(items: list) -> str:
    """Build one set of tape items as inline HTML."""
    seg = ""
    for it in items:
        chg = it.get("chg", 0)
        arrow = "▲" if chg >= 0 else "▼"
        cls   = "t-up" if chg >= 0 else "t-dn"
        seg  += (f'<span class="t-item">'
                 f'<span class="t-name">{it["name"]}</span>'
                 f'<span class="t-val">{it["last"]:,.2f}</span>'
                 f'<span class="{cls}">{arrow}{abs(chg):.2f}%</span>'
                 f'</span>')
    return seg


def _scan_items_html(items: list) -> str:
    """Build scan tape items as inline HTML."""
    seg = ""
    for it in items:
        chg = it.get("chg", 0)
        cls = "t-up" if chg >= 0 else "t-dn"
        seg += (f'<span class="t-item">'
                f'<span class="t-val">{it["symbol"]}</span>'
                f'<span class="{cls}">{chg:+.1f}%</span>'
                f'</span>')
    return seg


def render_tape(items_html: str, speed: str = "fast",
                badge: str = "", badge_bg: str = "", badge_fg: str = "") -> None:
    """Render a single tape row. 3 copies of content for seamless loop."""
    if not items_html:
        return
    # 3 copies — animation moves -33.33% which is exactly 1 copy width
    content = items_html * 3
    badge_html = ""
    if badge:
        badge_html = (f'<span class="tape-badge-pin" '
                      f'style="background:{badge_bg};color:{badge_fg}">'
                      f'{badge}</span>')
    st.markdown(
        f'<div class="tape-row">'
        f'{badge_html}'
        f'<div class="tape-scroll">'
        f'<div class="tape-inner {speed}">{content}</div>'
        f'</div></div>',
        unsafe_allow_html=True)

# ── Global ticker (parallel) ───────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def global_ticker_data():
    syms = {"S&P":"^GSPC","Dow":"^DJI","Nasdaq":"^IXIC","FTSE":"^FTSE",
            "Nikkei":"^N225","DAX":"^GDAXI","DXY":"DX-Y.NYB",
            "Gold":"GC=F","Silver":"SI=F","Crude":"CL=F",
            "USD/INR":"USDINR=X","Nifty":"^NSEI","BankNifty":"^NSEBANK"}
    results = fetch_yf_parallel(syms, period="2d", max_workers=8)
    out = []
    for name in syms:
        val = results.get(name)
        if val:
            out.append({"name": name, "last": val["last"], "chg": val["chg"]})
    return out

# ══ HEADER ════════════════════════════════════════════════════════════════════
live    = connected()
nse_st  = nse_equity_status()
mcx_st  = mcx_status()

def _mkt_pill(label: str, status: dict) -> str:
    cls = ("mkt-open" if status["open"]
           else "mkt-holiday-pill" if status["label"] in ("HOLIDAY","HOLIDAY AM")
           else "mkt-closed-pill")
    dot = '<span class="mkt-dot"></span>' if status["open"] else ""
    return (f'<span class="mkt-pill {cls}" title="{status["detail"]}">'
            f'{dot}<span class="mkt-pill-label">{label}</span>'
            f'{status["label"]}</span>')

conn_html = ('<span class="conn-live">● LIVE</span>' if live
             else '<span class="conn-off">● DELAYED</span>')

h1, h2 = st.columns([7, 1])
with h1:
    st.markdown(
        f'<div class="topbar">'
        f'<span class="brand">Parabolic<em>Trends</em></span>'
        f'<div class="hdr-right">'
        f'{_mkt_pill("EQ",nse_st)}'
        f'{_mkt_pill("MCX",mcx_st)}'
        f'{conn_html}'
        f'<span class="clock">{ist_now().strftime("%d %b %Y · %H:%M")} IST</span>'
        f'</div></div>', unsafe_allow_html=True)
with h2:
    # Plain styled link — no Streamlit button, just HTML anchor matching dark theme
    st.markdown(
        '<div style="padding-top:10px;text-align:right">'
        '<a href="https://trading-journal-ryxzgf6acavnzc6mv6vdzn.streamlit.app/" '
        'target="_blank" style="display:inline-block;padding:5px 12px;'
        'border-radius:7px;background:#1C2128;border:1px solid #30363D;'
        'color:#7C5CFC;font-size:12px;font-weight:600;text-decoration:none;'
        'font-family:Inter,sans-serif">Dashboard</a></div>',
        unsafe_allow_html=True)

# Market closed/holiday banner
if not nse_st["open"]:
    banner_color = "#D29922" if nse_st["label"] == "HOLIDAY" else "#484F58"
    st.markdown(
        f'<div style="background:var(--panel2);border:1px solid {banner_color}44;'
        f'border-radius:8px;padding:7px 14px;margin:6px 0;font-size:12px;'
        f'color:{banner_color};font-family:var(--fn);text-align:center">'
        f'NSE Equity: {nse_st["detail"]} · '
        f'MCX: {mcx_st["detail"]} · Showing last session data</div>',
        unsafe_allow_html=True)

# ══ TAPES — 3 stacked rows, all on one line each ════════════════════════════
# Row 1: Global markets
g_items = global_ticker_data()
render_tape(_tape_items_html(g_items), speed="fast")

# Row 2: 52WH scan
wh_items = fetch_tape_scan("52WH")
wh_html = _scan_items_html(wh_items) if wh_items else ""
render_tape(wh_html or '<span class="t-item" style="color:var(--txt3)">Scan unavailable</span>',
            speed="med", badge="52WH", badge_bg="#7C5CFC", badge_fg="#fff")

# Row 3: MM scan
mm_items = fetch_tape_scan("MM")
mm_html = _scan_items_html(mm_items) if mm_items else ""
render_tape(mm_html or '<span class="t-item" style="color:var(--txt3)">Scan unavailable</span>',
            speed="med", badge="MM", badge_bg="#2EC4A0", badge_fg="#0D1117")

# ══ SECTION 1 — MORNING BRIEF ══════════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">Morning Brief</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)

with st.expander("Morning Brief", expanded=True):
    def _brief_day_key():
        n = ist_now()
        from datetime import timedelta
        d = (n - timedelta(days=1)).date() if n.hour < 6 else n.date()
        return f"brief_{d}"

    today_key = _brief_day_key()
    if st.session_state.get("brief_day_key") != today_key:
        for k in ["brief_result","brief_ts","brief_done"]:
            st.session_state.pop(k, None)
        st.session_state["brief_day_key"] = today_key

    mb1, mb2 = st.columns([2,5])
    with mb1:
        already_done = "brief_result" in st.session_state
        btn_label = "Regenerate" if already_done else "Generate"
        run_brief = st.button(btn_label, key="brief_run")
    with mb2:
        if st.session_state.get("brief_ts"):
            st.markdown(
                f'<span style="font-size:11px;color:#484F58">'
                f'Generated {st.session_state["brief_ts"]}'
                f' — refreshes after 06:00 IST tomorrow</span>',
                unsafe_allow_html=True)

    if run_brief:
        st.session_state.pop("brief_result", None)
        st.session_state["brief_done"] = True

    if st.session_state.get("brief_done"):
        if "brief_result" not in st.session_state:
            with st.spinner("Fetching data…"):
                gp    = fetch_global_pulse()
                recap = fetch_indian_recap()
                lvls  = compute_key_levels(recap)
                news3 = fetch_top_news(3)
                evts  = events_window(1)
                res_df = results_today()
                sectors_dict = {}
                try:
                    sec_syms = {"IT":"^CNXIT","Bank":"^NSEBANK","Pharma":"^CNXPHARMA",
                                "FMCG":"CNXFMCG.NS","Metal":"CNXMETAL.NS","Auto":"CNXAUTO.NS"}
                    results_p = fetch_yf_parallel(sec_syms, period="2d", max_workers=6)
                    for nm, val in results_p.items():
                        if val:
                            sectors_dict[nm] = round(val["chg"], 2)
                except Exception:
                    pass
                movers_dict = {}
                try:
                    gl = gainers_losers()
                    if not gl["gainers"].empty and "Symbol" in gl["gainers"].columns:
                        movers_dict["gainers"] = gl["gainers"]["Symbol"].head(3).tolist()
                    if not gl["losers"].empty and "Symbol" in gl["losers"].columns:
                        movers_dict["losers"]  = gl["losers"]["Symbol"].head(3).tolist()
                except Exception:
                    pass
                ev_list  = [f"{e['Type']}: {e['Event']}" for _,e in evts.iterrows()] if not evts.empty else None
                res_list = res_df["Headline"].head(5).tolist() if not res_df.empty and "Headline" in res_df.columns else None
            gen_ts = ist_now().strftime("%d %b %Y · %H:%M IST")
            with st.spinner("Writing brief…"):
                synthesis = generate_synthesis(
                    gp, recap, lvls, news3,
                    sectors=sectors_dict or None,
                    events=ev_list, results=res_list,
                    movers=movers_dict or None,
                    gen_ts=gen_ts)
            st.session_state["brief_result"] = synthesis
            st.session_state["brief_ts"]     = gen_ts
        else:
            synthesis = st.session_state["brief_result"]

        para_html = "".join(f"<p>{p.strip()}</p>"
                            for p in synthesis.split("\n\n") if p.strip())
        st.markdown(
            f'<div class="brief-wrap"><div class="brief-text">{para_html}</div></div>',
            unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#484F58;font-size:13px">'
                    'Click Generate for today\'s morning brief.</span>',
                    unsafe_allow_html=True)

# ══ SECTION 2a — US MARKET RISK ══════════════════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">US Market Risk · S&amp;P 500 &amp; Nasdaq</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)

us_risk_cols = st.columns(2)
us_risks = {}
for i, us_idx in enumerate(US_INDICES.keys()):
    with us_risk_cols[i]:
        with st.spinner(""):
            urk = us_index_risk(us_idx)
        us_risks[us_idx] = urk
        if urk.get("ltp") is None:
            st.markdown(f'<div class="rcard"><div class="rc-name">{us_idx}</div>'
                        f'<div class="rc-ltp">—</div></div>', unsafe_allow_html=True)
            continue
        ltp   = urk["ltp"]; chg = urk.get("chg") or 0
        pts   = urk.get("chg_pts") or 0; pos = chg >= 0
        ccard = "pos" if pos else "neg"
        arrow = "▲" if pos else "▼"; sign = "+" if pos else "−"
        cchip = "cup" if pos else "cdn"; ctxt = "up" if pos else "dn"
        rl    = urk["risk_level"]; rc = urk["risk_color"]
        score = urk["score"]; maxs = urk.get("max_score", 11)
        score_pct = score / maxs * 100
        st_on = urk["supertrend"]
        st_c  = "on" if st_on else "off"; st_t = "BUY" if st_on else "SELL"
        st_date   = urk.get("st_date", "—"); st_cal = urk.get("st_bars", 0)
        st_price  = urk.get("st_price", None)
        elapsed_str = f"{st_cal}d ago" if st_cal > 0 else ""
        st_since_str = (f"{st_t} since {st_date}"
                        + (f" · {elapsed_str}" if elapsed_str else "")
                        + (f" @ {st_price:,.2f}" if st_price else ""))
        met    = urk.get("conditions_met", 0); tot = urk.get("total_conditions", 7)
        pct200 = urk.get("pct_200", 0) or 0
        last_bar = urk.get("last_bar", "—")
        st.markdown(
f'<div class="rcard {ccard}">'
f'<div class="rc-name">{us_idx}</div>'
f'<div class="rc-ltp">{ltp:,.2f}</div>'
f'<div class="rc-chg {ctxt}"><span>{arrow} {sign}{abs(pts):,.2f}</span>'
f'<span class="chip {cchip}">{sign}{abs(chg):.2f}%</span></div>'
f'<div class="risk-block">'
f'<span class="risk-badge" style="background:{rc}22;color:{rc};border:1px solid {rc}55">'
f'{rl} RISK</span>'
f'<div><div class="risk-score">{score:.1f}/{maxs} weighted score</div>'
f'<div class="score-bar-bg"><div class="score-bar" style="width:{score_pct:.0f}%;background:{rc}"></div></div></div>'
f'</div>'
f'<div class="st-row">'
f'<div class="st-pill {st_c}"><div class="st-lbl">Supertrend</div>'
f'<div class="st-val">{st_t}</div></div>'
f'<div class="st-pill" style="background:var(--panel2);flex:2">'
f'<div class="st-lbl">Signal history</div>'
f'<div style="font-size:11px;color:var(--txt2);font-family:var(--fn)">{st_since_str}</div>'
f'</div></div>'
f'<div class="rc-sub">{met}/{tot} criteria · {pct200:+.1f}% vs 200DMA</div>'
f'<div style="font-size:10px;color:var(--txt3);font-family:var(--fn);margin-top:4px">'
f'● Yahoo Finance · Data as of {last_bar}</div>'
f'</div>', unsafe_allow_html=True)

# US Swarna Criteria expander
with st.expander("US Market — Swarna Criteria"):
    for us_idx, urk in us_risks.items():
        if urk.get("checks"):
            score = urk["score"]; maxs = urk.get("max_score", 11)
            pct = score / maxs * 100; col = urk["risk_color"]
            st.markdown(
f'<div style="margin:8px 0 6px"><div style="display:flex;justify-content:space-between">'
f'<span style="font-weight:600;font-size:14px;color:#E6EDF3">{us_idx}</span>'
f'<span style="font-family:monospace;color:{col};font-weight:700">'
f'{score:.1f}/{maxs} · {pct:.0f}% · '
f'<span style="padding:1px 6px;border-radius:4px;background:{col}22;font-size:11px">'
f'{urk["risk_level"]} RISK</span></span></div>'
f'<div style="background:#30363D;border-radius:3px;height:4px;margin-top:4px">'
f'<div style="width:{pct:.0f}%;background:{col};height:4px;border-radius:3px"></div>'
f'</div></div>', unsafe_allow_html=True)
            for c in urk["checks"]:
                icon = "🟢" if c["pass"] else "🔴"
                st.markdown(
f'<div style="padding:3px 0;font-size:13px;color:#E6EDF3">'
f'{icon} <b>{c["label"]}</b> <span style="color:#484F58">· weight {c["weight"]}</span><br>'
f'<span style="color:#8B949E;font-size:11px;margin-left:20px">{c["detail"]}</span></div>',
                    unsafe_allow_html=True)
            st.markdown('<hr style="border-color:#30363D;margin:10px 0">',
                        unsafe_allow_html=True)

# ══ SECTION 2b — INDIAN MARKET RISK INDICATOR ════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">India Risk Indicator · Nifty &amp; Bank Nifty</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)

risk_cols = st.columns(2)
risks = {}
for i, idx in enumerate(INDEX_TOKENS.keys()):
    with risk_cols[i]:
        with st.spinner(""):
            rk = index_risk(idx)
        risks[idx] = rk
        if rk["ltp"] is None:
            st.markdown(f'<div class="rcard"><div class="rc-name">{idx}</div>'
                        f'<div class="rc-ltp">—</div></div>', unsafe_allow_html=True)
            continue
        ltp=rk["ltp"]; chg=rk.get("chg") or 0; pts=rk.get("chg_pts") or 0; pos=chg>=0
        ccard="pos" if pos else "neg"
        arrow="▲" if pos else "▼"; sign="+" if pos else "−"
        cchip="cup" if pos else "cdn"; ctxt="up" if pos else "dn"
        rl=rk["risk_level"]; rc=rk["risk_color"]
        score=rk["score"]; maxs=rk.get("max_score",11)
        score_pct=score/maxs*100
        st_on=rk["supertrend"]
        st_c="on" if st_on else "off"; st_t="BUY" if st_on else "SELL"
        st_date=rk.get("st_date","—"); st_cal=rk.get("st_bars",0)
        st_price=rk.get("st_price",None)
        # Show calendar days elapsed, not bar count
        if st_cal > 0:
            elapsed_str = f"{st_cal}d ago"
        else:
            elapsed_str = ""
        st_since_str=(f"{st_t} since {st_date}"
                      +(f" · {elapsed_str}" if elapsed_str else "")
                      +(f" @ {st_price:,.0f}" if st_price else ""))
        met=rk.get("conditions_met",0); tot=rk.get("total_conditions",7)
        pct200=rk.get("pct_200",0) or 0
        data_src=rk.get("data_src","—"); last_bar=rk.get("last_bar","—")
        src_color = "#2EC4A0" if data_src=="Angel One" else "#D29922"
        st.markdown(
f'<div class="rcard {ccard}">'
f'<div class="rc-name">{idx}</div>'
f'<div class="rc-ltp">{ltp:,.2f}</div>'
f'<div class="rc-chg {ctxt}"><span>{arrow} {sign}{abs(pts):,.2f}</span>'
f'<span class="chip {cchip}">{sign}{abs(chg):.2f}%</span></div>'
f'<div class="risk-block">'
f'<span class="risk-badge" style="background:{rc}22;color:{rc};border:1px solid {rc}55">'
f'{rl} RISK</span>'
f'<div><div class="risk-score">{score:.1f}/{maxs} weighted score</div>'
f'<div class="score-bar-bg"><div class="score-bar" style="width:{score_pct:.0f}%;background:{rc}"></div></div></div>'
f'</div>'
f'<div class="st-row">'
f'<div class="st-pill {st_c}"><div class="st-lbl">Supertrend</div>'
f'<div class="st-val">{st_t}</div></div>'
f'<div class="st-pill" style="background:var(--panel2);flex:2">'
f'<div class="st-lbl">Signal history</div>'
f'<div style="font-size:11px;color:var(--txt2);font-family:var(--fn)">{st_since_str}</div>'
f'</div></div>'
f'<div class="rc-sub">{met}/{tot} criteria · {pct200:+.1f}% vs 200DMA</div>'
f'<div style="font-size:10px;color:{src_color};font-family:var(--fn);margin-top:4px">'
f'● {data_src} · Data as of {last_bar}</div>'
f'</div>', unsafe_allow_html=True)


# ══ SECTION 3 — SWARNA CRITERIA (collapsible) ═══════════════════════
with st.expander("Swarna Criteria"):
    for idx, rk in risks.items():
        if rk.get("checks"):
            score=rk["score"]; maxs=rk.get("max_score",11)
            pct=score/maxs*100; col=rk["risk_color"]
            st.markdown(
f'<div style="margin:8px 0 6px"><div style="display:flex;justify-content:space-between">'
f'<span style="font-weight:600;font-size:14px;color:#E6EDF3">{idx}</span>'
f'<span style="font-family:monospace;color:{col};font-weight:700">'
f'{score:.1f}/{maxs} · {pct:.0f}% · '
f'<span style="padding:1px 6px;border-radius:4px;background:{col}22;font-size:11px">'
f'{rk["risk_level"]} RISK</span></span></div>'
f'<div style="background:#30363D;border-radius:3px;height:4px;margin-top:4px">'
f'<div style="width:{pct:.0f}%;background:{col};height:4px;border-radius:3px"></div>'
f'</div></div>', unsafe_allow_html=True)
            for c in rk["checks"]:
                icon="🟢" if c["pass"] else "🔴"
                st.markdown(
f'<div style="padding:3px 0;font-size:13px;color:#E6EDF3">'
f'{icon} <b>{c["label"]}</b> <span style="color:#484F58">· weight {c["weight"]}</span><br>'
f'<span style="color:#8B949E;font-size:11px;margin-left:20px">{c["detail"]}</span></div>',
                    unsafe_allow_html=True)
            st.markdown('<hr style="border-color:#30363D;margin:10px 0">',
                        unsafe_allow_html=True)

# ══ SECTION 4 — COMMODITY SIGNALS (always visible) ════════════════
st.markdown('<div class="sec"><span class="sec-title">Commodity Signals · HHLL(29) · USD</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)

with st.container():
    # Auto-fetch on every page load — @cache_data(ttl=1800) handles the 30-min refresh
    with st.spinner(""):
        sigs = get_hhll_signals()

    # Show timestamp
    fetch_ts = ist_now().strftime("%d %b · %H:%M IST")
    st.markdown(
        f'<span style="font-size:10px;color:var(--txt3);font-family:var(--fn)">'
        f'Refreshes every 30 min · Last fetch {fetch_ts}</span>',
        unsafe_allow_html=True)

    # 1H cards
    st.markdown('<div style="font-size:10px;font-weight:600;letter-spacing:2px;'
                'text-transform:uppercase;color:var(--txt3);margin:8px 0 7px">'
                '1-Hour Signal</div>', unsafe_allow_html=True)
    hcols = st.columns(3)
    for ci, (name, data) in enumerate(sigs.items()):
        with hcols[ci]:
            s = data["1H"]; sig = s["signal"]
            price = s["price"]; upper = s["upper"]; lower = s["lower"]
            crossed = s["crossed"]
            sig_time  = s.get("signal_time","—")
            sig_price = s.get("signal_price",None)
            elapsed   = s.get("elapsed","—")
            # % change from signal price (shows move since signal triggered)
            pchg = None
            if price and sig_price and sig_price != 0:
                pchg = (price - sig_price) / sig_price * 100
            # Also fetch prev day % change from yfinance cache
            prev_chg = None
            try:
                sym = data["unit"]  # e.g. "GC=F"
                _df = yf.download(sym, period="2d", auto_adjust=True,
                                  progress=False, timeout=5)
                if _df is not None and len(_df) >= 2:
                    _df.columns = [c[0] if isinstance(c,tuple) else c for c in _df.columns]
                    prev_chg = (float(_df["Close"].iloc[-1]) - float(_df["Close"].iloc[-2])) \
                               / float(_df["Close"].iloc[-2]) * 100
            except Exception:
                pass
            top_col  = "#2EC4A0" if sig=="LONG" else "#F85149" if sig=="SHORT" else "#484F58"
            pill_cls = "lp" if sig=="LONG" else "sp" if sig=="SHORT" else "np"
            pstr = f"{price:,.3f}" if price else "—"
            ustr = f"{upper:,.3f}" if upper else "—"
            lstr = f"{lower:,.3f}" if lower else "—"
            # Prev day % change badge
            prev_html = ""
            if prev_chg is not None:
                pcls = "t-up" if prev_chg >= 0 else "t-dn"
                arr  = "▲" if prev_chg >= 0 else "▼"
                prev_html = f'<span class="hl-pchg {pcls}">{arr}{abs(prev_chg):.2f}%</span>'
            # Since-signal % change
            since_html = ""
            if pchg is not None:
                scls = "t-up" if pchg >= 0 else "t-dn"
                since_html = f'<span style="font-size:10px;color:var(--txt3)"> · {pchg:+.2f}% since signal</span>'
            # CME closed / no data note
            if sig == "NO DATA" or not price:
                cme_note = (f'<div style="font-size:11px;color:var(--txt3);'
                            f'margin-top:10px;padding:6px 8px;background:var(--panel2);'
                            f'border-radius:5px">CME futures closed or data unavailable'
                            f'<br>Last fetch: {fetch_ts}</div>')
                bands_html = ""
                sig_ts_html = ""
            else:
                cme_note = ""
                bands_html = (f'<div class="hl-bands">'
                              f'<span>Upper {ustr}</span>'
                              f'<span>Lower {lstr}</span>'
                              f'<span style="color:#484F58">{crossed}</span>'
                              f'</div>')
                sig_ts_html = (f'<div class="hl-sig-ts">Signal since: {sig_time} · {elapsed}'
                               f'{(" @ "+f"{sig_price:,.3f}") if sig_price else ""}</div>')
            st.markdown(
f'<div class="hl-card">'
f'<div class="hl-top" style="background:{top_col}"></div>'
f'<div class="hl-com">{name}</div>'
f'<div class="hl-unit">{data["display_unit"]}</div>'
f'<div class="hl-price-row">'
f'<div class="hl-price">{pstr}</div>{prev_html}'
f'</div>'
f'<span class="hl-pill {pill_cls}">{sig}</span>{since_html}'
f'{bands_html}{sig_ts_html}{cme_note}'
f'</div>', unsafe_allow_html=True)

# ══ COLLAPSIBLE SECTIONS ══════════════════════════════════════════════════════
with st.expander("Market Internals"):
    hmap_mode = st.radio("View", ["Nifty 50 Stocks","Sector Indices"],
                         horizontal=True, key="hmap_mode",
                         label_visibility="collapsed")
    i1, i2 = st.columns([1,1])
    with i1:
        run_int = st.button("Load", key="int_run")
    with i2:
        if st.session_state.get("int_done"):
            if st.button("Clear", key="int_clr"):
                st.session_state["int_done"] = False; st.rerun()
    if run_int: st.session_state["int_done"] = True
    if st.session_state.get("int_done"):
        data_ts = ist_now().strftime("%H:%M IST")
        with st.spinner("Loading… (parallel fetch)"):
            heat, heat_src     = nifty50_heatmap_yf()
            sec_heat, sec_src  = sector_heatmap_yf()
            gl                 = gainers_losers()

        src = heat_src if hmap_mode == "Nifty 50 Stocks" else sec_src
        src_color = "#2EC4A0" if "Live" in src else "#D29922"
        st.markdown(
            f'<span style="font-size:11px;color:{src_color};font-family:var(--fn);'
            f'display:inline-block;margin-bottom:8px">● {src}</span>',
            unsafe_allow_html=True)

        # A/D computed directly from heatmap
        if not heat.empty:
            adv = int((heat["Chg %"] > 0).sum()); dec = int((heat["Chg %"] < 0).sum())
            apct = adv / (adv + dec) * 100 if (adv+dec) > 0 else 50
            st.markdown(
f'<div class="ad-wrap"><div class="ad-hdr">'
f'<span>Advance / Decline · Nifty 50</span>'
f'<span><span style="color:#2EC4A0">{adv} adv</span> · '
f'<span style="color:#F85149">{dec} dec</span></span></div>'
f'<div class="ad-bar">'
f'<div style="width:{apct:.0f}%;background:#2EC4A0"></div>'
f'<div style="flex:1;background:#F85149"></div></div></div>',
                unsafe_allow_html=True)

        def render_hmap(df, cols=10):
            if df is None or df.empty: return
            cells = ""
            for _, row in df.iterrows():
                v = row["Chg %"]
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    bg = "#2D333B"; vstr = "N/A"
                else:
                    bg = ("#1E8E74" if v>1 else "#2EC4A0" if v>0
                          else "#484F58" if v==0 else "#F85149" if v>-1 else "#A32D2D")
                    vstr = f"{v:+.1f}%"
                cells += (f'<div style="background:{bg};border-radius:5px;'
                          f'padding:5px 3px;text-align:center">'
                          f'<div style="font-size:9px;color:#fff;font-weight:600;'
                          f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
                          f'{row["Symbol"]}</div>'
                          f'<div style="font-size:10px;color:#fff;font-family:monospace">'
                          f'{vstr}</div></div>')
            st.markdown(
                f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);'
                f'gap:3px;margin-bottom:12px">{cells}</div>',
                unsafe_allow_html=True)

        st.markdown(
            f'<div style="font-size:11px;color:#484F58;margin-bottom:4px">'
            f'{"Nifty 50 stocks" if hmap_mode=="Nifty 50 Stocks" else "Sector indices"}'
            f' · % change</div>', unsafe_allow_html=True)
        if hmap_mode == "Nifty 50 Stocks":
            render_hmap(heat, 10)
        else:
            render_hmap(sec_heat, 6)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown('<b style="color:#2EC4A0;font-size:13px">Top Gainers</b>',
                        unsafe_allow_html=True)
            if not gl["gainers"].empty:
                st.dataframe(gl["gainers"], width="stretch", hide_index=True, height=280,
                    column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
        with g2:
            st.markdown('<b style="color:#F85149;font-size:13px">Top Losers</b>',
                        unsafe_allow_html=True)
            if not gl["losers"].empty:
                st.dataframe(gl["losers"], width="stretch", hide_index=True, height=280,
                    column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})

with st.expander("Screeners"):
    sc1, sc2 = st.columns([3,1])
    with sc1:
        sname = st.selectbox("Screener", list(DEFAULT_SCREENERS.keys()),
                             key="ck_s", label_visibility="collapsed")
    with sc2:
        run_ck = st.button("Run", key="ck_run")
    if run_ck:
        with st.spinner(""):
            st.session_state["ck_result"] = run_chartink_scan(DEFAULT_SCREENERS[sname])
            st.session_state["ck_name"]   = sname
    ck_df = st.session_state.get("ck_result")
    if ck_df is not None:
        if "error" in ck_df.columns: st.error(ck_df["error"].iloc[0])
        elif ck_df.empty: st.caption("No matches.")
        else:
            st.dataframe(ck_df, width="stretch", hide_index=True, height=460,
                column_config={"Chg %": st.column_config.NumberColumn(format="%.2f%%")})
            st.caption(f"{len(ck_df)} stocks · {st.session_state.get('ck_name','')}")

with st.expander("Events & Ban List"):
    e1, e2 = st.columns([1,1])
    with e1:
        run_ev = st.button("Load", key="ev_run")
    with e2:
        if st.session_state.get("ev_done"):
            if st.button("Clear", key="ev_clr"):
                st.session_state["ev_done"] = False; st.rerun()
    if run_ev: st.session_state["ev_done"] = True
    if st.session_state.get("ev_done"):
        with st.spinner(""):
            evts = events_window(7); ban = fno_ban_mwpl(); results = results_today()
        # Today's date header
        today_str = ist_now().strftime("%A, %d %b %Y")
        st.markdown(
            f'<div style="font-size:12px;color:var(--txt3);font-family:var(--fn);'
            f'margin-bottom:10px;padding:6px 10px;background:var(--panel2);'
            f'border-radius:6px;border-left:3px solid var(--purple)">'
            f'Today: {today_str}</div>',
            unsafe_allow_html=True)
        if not evts.empty:
            for _, e in evts.iterrows():
                bc = "#D29922" if e["When"] == "TODAY" else "#7C5CFC"
                st.markdown(
f'<div style="padding:5px 0;font-size:13px">'
f'<span style="background:{bc};color:#0D1117;font-weight:700;font-size:10px;'
f'padding:2px 7px;border-radius:4px">{e["When"]}</span>'
f' <b style="color:#E6EDF3">{e["Date"]} · {e["Type"]}</b>'
f' <span style="color:#8B949E">— {e["Event"]}</span></div>',
                    unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            st.markdown('<b style="color:#F85149;font-size:12px">IN BAN (≥95%)</b>',
                        unsafe_allow_html=True)
            if not ban["banned"].empty:
                st.dataframe(ban["banned"], width="stretch", hide_index=True, height=200)
            else:
                st.caption("None today / unavailable.")
        with b2:
            st.markdown('<b style="color:#D29922;font-size:12px">APPROACHING (80–95%)</b>',
                        unsafe_allow_html=True)
            if not ban["entrants"].empty:
                st.dataframe(ban["entrants"], width="stretch", hide_index=True, height=200,
                    column_config={"MWPL %": st.column_config.NumberColumn(format="%.1f%%")})
            else:
                st.caption("None / unavailable.")
        if not results.empty:
            st.markdown('<b style="color:#7C5CFC;font-size:12px">RESULTS DUE</b>',
                        unsafe_allow_html=True)
            st.dataframe(results, width="stretch", hide_index=True, height=180)

with st.expander("FII Sector Flows"):
    f1, f2 = st.columns([1,1])
    with f1:
        run_fii = st.button("Load", key="fii_run")
    with f2:
        if st.session_state.get("fii_done"):
            if st.button("Clear", key="fii_clr"):
                st.session_state["fii_done"] = False; st.rerun()
    if run_fii: st.session_state["fii_done"] = True
    if st.session_state.get("fii_done"):
        with st.spinner(""):
            fii_data, fii_source = get_fii_sectors()
        # Show fortnight period label
        from datetime import timedelta as _td
        today = ist_now().date()
        # FII data is published fortnightly — show period ending last Friday
        days_since_fri = (today.weekday() - 4) % 7
        last_fri = today - _td(days=days_since_fri)
        fortnight_start = last_fri - _td(days=13)
        period_str = f"{fortnight_start.strftime('%d %b')} – {last_fri.strftime('%d %b %Y')}"
        st.markdown(
            f'<div style="font-size:11px;color:var(--txt3);font-family:var(--fn);'
            f'margin-bottom:8px">FII Sector Flows · Fortnight ending {last_fri.strftime("%d %b %Y")}'
            f' · Source: {fii_source}</div>',
            unsafe_allow_html=True)
        render_fii_heatmap(fii_data, fii_source)

with st.expander("Market News"):
    n1, n2 = st.columns([1,1])
    with n1:
        run_news = st.button("Load", key="news_run")
    with n2:
        if st.session_state.get("news_done"):
            if st.button("Clear", key="news_clr"):
                st.session_state["news_done"] = False; st.rerun()
    if run_news: st.session_state["news_done"] = True
    if st.session_state.get("news_done"):
        with st.spinner(""):
            news = news_digest(6)
        if not news.empty:
            for _, n in news.iterrows():
                dt = n["dt"]
                stamp = dt.strftime("%d %b · %H:%M IST") if pd.notna(dt) and dt else ""
                tag = sentiment_tag(n["Headline"])
                tag_html = (f'<span class="bull">↑ BULL</span>' if tag=="BULL"
                            else f'<span class="bear">↓ BEAR</span>' if tag=="BEAR"
                            else f'<span class="neut">· NEUT</span>')
                link = n["Link"]
                head = (f'<a href="{link}" target="_blank">{n["Headline"]}</a>'
                        if link else n["Headline"])
                st.markdown(
f'<div class="news-item">'
f'<div class="news-meta">{stamp} · {n["Source"]} {tag_html}</div>'
f'<div class="news-hl">{head}</div></div>', unsafe_allow_html=True)
        else:
            st.caption("News unavailable.")

st.markdown(
    f'<div style="height:14px"></div>'
    f'<div style="font-size:11px;color:#484F58;text-align:center">'
    f'Parabolic Trends · Swarna risk criteria · Angel One · Yahoo Finance · Chartink · '
    f'{ist_now().strftime("%d %b %Y")} · Not investment advice</div>',
    unsafe_allow_html=True)
