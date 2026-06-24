"""
Parabolic Trends — v6
All 9 tasks: weighted risk, ST signal date, HHLL timestamps,
scan tapes, sector heatmap fix, UX overhaul, global refresh.
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone, timedelta

from data_layer import INDEX_TOKENS, connected
from engine import index_risk
from chartink import run_chartink_scan, DEFAULT_SCREENERS, fetch_tape_scan, TAPE_SCANS
from market_web import gainers_losers, nifty50, advance_decline, nifty50_heatmap_yf
from events_news import results_today, events_window, news_digest
from banlist import fno_ban_mwpl
from hhll import get_hhll_signals
from morning_brief import (fetch_global_pulse, fetch_indian_recap,
                           compute_key_levels, fetch_top_news, generate_synthesis)
from fii_sectors import get_fii_sectors, render_fii_heatmap

IST = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="Parabolic Trends", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Global Refresh ─────────────────────────────────────────────────────────────

# ── Helpers ────────────────────────────────────────────────────────────────────
def ist_now():
    return datetime.now(IST)

def fmt_chg(v, decimals=2):
    if v is None: return "—"
    s = "+" if v >= 0 else "−"
    return f"{s}{abs(v):.{decimals}f}%"

def sentiment_tag(h):
    h = h.lower()
    if any(w in h for w in ["surge","rally","gain","rise","jump","high","bull","record","beat"]):
        return "BULL"
    if any(w in h for w in ["fall","drop","crash","decline","slide","bear","cut","miss","fear"]):
        return "BEAR"
    return "NEUT"

# ── Theme ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
:root {
  --bg:#0D1117; --panel:#161B22; --panel2:#1C2128; --border:#30363D;
  --txt:#E6EDF3; --txt2:#8B949E; --txt3:#484F58;
  --purple:#7C5CFC; --green:#2EC4A0; --red:#F85149; --amber:#D29922;
  --fn:'JetBrains Mono',monospace; --fs:'Inter',sans-serif;
}
.stApp{background:var(--bg);color:var(--txt);font-family:var(--fs);}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:0 1.4rem 3rem;max-width:1320px;}
h1,h2,h3,h4{color:var(--txt)!important;font-family:var(--fs)!important;}

/* ── Ticker tapes ── */
.tape-wrap{overflow:hidden;width:100%;border-bottom:1px solid var(--border);}
.tape-global{background:#0A0F16;padding:6px 0;}
.tape-row{padding:4px 0;display:flex;align-items:center;}
.tape-badge{font-size:10px;font-weight:700;letter-spacing:1px;
  padding:2px 8px;border-radius:4px;margin-right:8px;
  white-space:nowrap;font-family:var(--fn);}
.tape-inner{display:flex;white-space:nowrap;}
.tape-inner.fast{animation:scroll 60s linear infinite;}
.tape-inner.med{animation:scroll 20s linear infinite;}
.tape-inner:hover{animation-play-state:paused;}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.t-item{display:inline-flex;align-items:center;gap:5px;padding:0 18px;
  font-family:var(--fn);font-size:12px;border-right:1px solid var(--border);}
.t-name{color:var(--txt2);font-size:11px;}
.t-val{color:var(--txt);font-weight:500;}
.t-up{color:var(--green);} .t-dn{color:var(--red);}
.t-neut{color:var(--txt2);}

/* ── Header ── */
.topbar{display:flex;align-items:center;justify-content:space-between;
  padding:10px 0 8px;border-bottom:1px solid var(--border);margin-bottom:2px;}
.brand{font-size:24px;font-weight:700;color:var(--txt);}
.brand em{color:var(--purple);font-style:normal;}
.hdr-right{display:flex;align-items:center;gap:10px;}
.conn-live{font-size:11px;padding:3px 10px;border-radius:999px;font-weight:600;
  background:rgba(46,196,160,.12);color:var(--green);}
.conn-off{font-size:11px;padding:3px 10px;border-radius:999px;font-weight:600;
  background:rgba(210,153,34,.12);color:var(--amber);}
.clock{font-size:12px;color:var(--txt2);font-family:var(--fn);}

/* ── Section dividers ── */
.sec{display:flex;align-items:center;gap:10px;margin:18px 0 10px;}
.sec-title{font-size:11px;font-weight:600;letter-spacing:2.5px;
  text-transform:uppercase;color:var(--txt3);white-space:nowrap;}
.sec-line{flex:1;height:1px;background:var(--border);}

/* ── Risk cards v2 (LOW/MODERATE/HIGH) ── */
.rcard{background:var(--panel);border:1px solid var(--border);
  border-radius:10px;padding:16px 18px;position:relative;overflow:hidden;}
.rcard::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;}
.pos::before{background:var(--green);} .neg::before{background:var(--red);}
.rc-name{font-size:11px;font-weight:600;letter-spacing:2px;
  text-transform:uppercase;color:var(--purple);margin-bottom:6px;}
.rc-ltp{font-size:30px;font-weight:700;color:var(--txt);
  font-family:var(--fn);letter-spacing:-1px;line-height:1.1;}
.rc-chg{font-size:13px;font-weight:600;font-family:var(--fn);
  display:flex;align-items:center;gap:8px;margin-top:3px;}
.chip{padding:2px 8px;border-radius:5px;font-size:12px;font-weight:600;}
.cup{background:rgba(46,196,160,.14);color:var(--green);}
.cdn{background:rgba(248,81,73,.14);color:var(--red);}
.up{color:var(--green);} .dn{color:var(--red);}
.risk-block{display:flex;align-items:center;gap:12px;margin-top:14px;}
.risk-badge{font-size:14px;font-weight:800;padding:6px 16px;
  border-radius:8px;font-family:var(--fn);letter-spacing:1px;}
.risk-score{font-size:12px;color:var(--txt2);font-family:var(--fn);}
.st-row{display:flex;gap:8px;margin-top:10px;}
.st-pill{flex:1;border-radius:8px;padding:8px 10px;text-align:center;
  border:1px solid var(--border);}
.st-lbl{font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--txt3);margin-bottom:4px;font-weight:600;}
.st-val{font-size:14px;font-weight:800;font-family:var(--fn);}
.on{background:rgba(46,196,160,.1);border-color:rgba(46,196,160,.35);}
.on .st-val{color:var(--green);}
.off{background:rgba(248,81,73,.1);border-color:rgba(248,81,73,.35);}
.off .st-val{color:var(--red);}
.rc-sub{font-size:11px;color:var(--txt3);font-family:var(--fn);margin-top:8px;}
.score-bar-bg{background:var(--border);border-radius:3px;height:5px;margin-top:6px;}
.score-bar{height:5px;border-radius:3px;}

/* ── HHLL cards ── */
.hl-card{background:var(--panel);border:1px solid var(--border);
  border-radius:10px;padding:13px 15px;position:relative;overflow:hidden;}
.hl-top{position:absolute;top:0;left:0;right:0;height:2px;}
.hl-com{font-size:11px;font-weight:600;letter-spacing:2px;
  text-transform:uppercase;color:var(--txt2);margin:4px 0 2px;}
.hl-unit{font-size:10px;color:var(--txt3);margin-bottom:4px;}
.hl-price{font-size:20px;font-weight:700;color:var(--txt);font-family:var(--fn);}
.hl-pill{display:inline-block;font-size:11px;font-weight:700;padding:2px 10px;
  border-radius:5px;margin:6px 0 5px;font-family:var(--fn);}
.lp{background:rgba(46,196,160,.14);color:var(--green);}
.sp{background:rgba(248,81,73,.14);color:var(--red);}
.np{background:rgba(72,79,88,.3);color:var(--txt2);}
.hl-bands{font-size:11px;color:var(--txt3);font-family:var(--fn);}
.hl-bands span{display:block;line-height:1.75;}
.hl-sig-ts{font-size:10px;color:var(--purple);margin-top:4px;font-family:var(--fn);}
.tf-hdr{font-size:10px;font-weight:600;letter-spacing:2px;
  text-transform:uppercase;color:var(--txt3);margin:12px 0 7px;}
.hdiv{border:none;border-top:1px solid var(--border);margin:12px 0;}

/* ── Brief ── */
.brief-wrap{background:var(--panel);border:1px solid var(--border);
  border-radius:10px;padding:16px 18px;}
.brief-text{font-size:13.5px;color:var(--txt);line-height:1.78;font-family:var(--fs);}
.brief-text p{margin:0 0 11px;}
.brief-text p:last-child{margin:0;}
.brief-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px;}
.brief-table{background:var(--panel2);border-radius:8px;padding:10px 12px;}
.bt-title{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--txt3);margin-bottom:7px;font-weight:600;}
.bt-row{display:flex;justify-content:space-between;padding:3px 0;
  border-bottom:1px solid var(--border);font-size:12px;}
.bt-row:last-child{border:none;}
.bt-label{color:var(--txt2);}
.bt-val{font-family:var(--fn);color:var(--txt);font-weight:500;}

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
  font-size:13px!important;padding:5px 14px!important;transition:background .15s!important;}
.stButton button:hover{background:#6044D8!important;}

/* ── Radio ── */
.stRadio>div{gap:6px!important;}
.stRadio label{color:var(--txt2)!important;font-size:13px!important;}

/* ── Selectbox ── */
.stSelectbox div[data-baseweb="select"]>div{background:var(--panel2)!important;
  border-color:var(--border)!important;color:var(--txt)!important;border-radius:7px!important;}

/* ── News ── */
.news-item{padding:7px 0;border-bottom:1px solid var(--border);}
.news-meta{font-size:11px;color:var(--txt3);font-family:var(--fn);margin-bottom:2px;}
.news-hl{font-size:13px;color:var(--txt);line-height:1.5;}
.news-hl a{color:var(--txt);text-decoration:none;}
.news-hl a:hover{color:var(--purple);}
.bull{color:var(--green);font-size:10px;font-weight:700;}
.bear{color:var(--red);font-size:10px;font-weight:700;}
.neut{color:var(--txt3);font-size:10px;}

/* ── AD meter ── */
.ad-wrap{background:var(--panel2);border:1px solid var(--border);
  border-radius:8px;padding:11px 14px;margin-bottom:11px;}
.ad-hdr{display:flex;justify-content:space-between;font-size:12px;
  color:var(--txt2);margin-bottom:6px;}
.ad-bar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--border);}
hr{border-color:var(--border)!important;margin:4px 0!important;}
</style>
""", unsafe_allow_html=True)

# ══ TICKER TAPE DATA ══════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def global_ticker_data():
    syms = {"S&P":"^GSPC","Dow":"^DJI","Nasdaq":"^IXIC","FTSE":"^FTSE",
            "Nikkei":"^N225","DAX":"^GDAXI","DXY":"DX-Y.NYB",
            "Gold":"GC=F","Crude":"CL=F","USD/INR":"USDINR=X",
            "Nifty":"^NSEI","BankNifty":"^NSEBANK"}
    out = []
    for name, sym in syms.items():
        try:
            d = yf.download(sym, period="2d", auto_adjust=True,
                           progress=False, timeout=8)
            if d is not None and not d.empty:
                d.columns = [c[0] if isinstance(c,tuple) else c for c in d.columns]
                d = d.dropna()
                if len(d) >= 2:
                    last = float(d["Close"].iloc[-1])
                    chg  = (last - float(d["Close"].iloc[-2])) / float(d["Close"].iloc[-2]) * 100
                    out.append({"name": name, "last": last, "chg": chg})
        except Exception:
            continue
    return out


def build_tape_html(items: list, speed_class: str = "fast") -> str:
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
    if not seg:
        return ""
    return f'<div class="tape-inner {speed_class}">{seg}{seg}</div>'


def build_scan_tape_html(items: list, speed_class: str = "med") -> str:
    if not items:
        return '<span style="color:var(--txt3);font-size:12px;padding:0 12px">Scan unavailable — market may be closed or Chartink unreachable</span>'
    seg = ""
    for it in items:
        chg = it.get("chg", 0)
        cls = "t-up" if chg >= 0 else "t-dn"
        seg += (f'<span class="t-item">'
                f'<span class="t-val" style="color:var(--txt)">{it["symbol"]}</span>'
                f'<span class="{cls}">{chg:+.1f}%</span>'
                f'</span>')
    if not seg:
        return ""
    return f'<div class="tape-inner {speed_class}">{seg}{seg}</div>'


# ══ HEADER (brand name first, then tickers) ══════════════════════════════════
live = connected()
conn = ('<span class="conn-live">● LIVE</span>' if live
        else '<span class="conn-off">● DELAYED</span>')
st.markdown(
    f'<div class="topbar">'
    f'<span class="brand">Parabolic<em>Trends</em></span>'
    f'<div class="hdr-right">{conn}'
    f'<span class="clock">{ist_now().strftime("%d %b %Y · %H:%M")} IST</span>'
    f'</div></div>',
    unsafe_allow_html=True)

# ══ TICKERS (after header) ════════════════════════════════════════════════════
# Global markets tape
g_items = global_ticker_data()
g_html  = build_tape_html(g_items, "fast")
st.markdown(
    f'<div class="tape-wrap tape-global">{g_html}</div>',
    unsafe_allow_html=True)

# Scan tapes — 52WH, MM, ATR only (badge sits outside scroll area)
BADGE_COLORS = {
    "52WH": ("#7C5CFC", "#fff"),
    "MM":   ("#2EC4A0", "#0D1117"),
    "ATR":  ("#F85149", "#fff"),
}
for tape_label, info in TAPE_SCANS.items():
    tape_items = fetch_tape_scan(tape_label)
    tape_html  = build_scan_tape_html(tape_items, "med")
    bg, fg = BADGE_COLORS.get(tape_label, ("#484F58","#fff"))
    # Badge is OUTSIDE the overflow:hidden div so it never gets covered
    st.markdown(
        f'<div style="display:flex;align-items:center;'
        f'border-bottom:1px solid var(--border);background:var(--bg);'
        f'padding:3px 0">'
        f'<span class="tape-badge" style="background:{bg};color:{fg};'
        f'flex-shrink:0;margin:0 8px">{tape_label}</span>'
        f'<div style="overflow:hidden;flex:1">'
        f'<div style="display:flex">{tape_html}</div>'
        f'</div></div>',
        unsafe_allow_html=True)

# ══ SECTION 1 — RISK INDICATOR ════════════════════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">Risk Indicator</span>'
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
                        f'<div class="rc-ltp">—</div></div>',
                        unsafe_allow_html=True)
            continue
        ltp=rk["ltp"]; chg=rk["chg"]; pts=rk.get("chg_pts",0)
        pos=chg>=0
        ccard="pos" if pos else "neg"
        arrow="▲" if pos else "▼"; sign="+" if pos else "−"
        cchip="cup" if pos else "cdn"; ctxt="up" if pos else "dn"

        # Risk level badge
        rl=rk["risk_level"]; rc=rk["risk_color"]
        score=rk["score"]; maxs=rk.get("max_score",11)
        score_pct = score/maxs*100

        # Supertrend pill
        st_on=rk["supertrend"]
        st_c="on" if st_on else "off"; st_t="BUY" if st_on else "SELL"
        st_date=rk.get("st_date","—"); st_bars=rk.get("st_bars",0)
        st_price=rk.get("st_price",None)
        st_since_str = (f"{st_t} since {st_date}"
                        + (f" · {st_bars}d ago" if st_bars>0 else "")
                        + (f" @ {st_price:,.0f}" if st_price else ""))

        met=rk.get("conditions_met",0); tot=rk.get("total_conditions",7)
        pct200=rk.get("pct_200",0) or 0

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
f'<div class="score-bar-bg"><div class="score-bar" '
f'style="width:{score_pct:.0f}%;background:{rc}"></div></div></div>'
f'</div>'
f'<div class="st-row">'
f'<div class="st-pill {st_c}"><div class="st-lbl">Supertrend</div>'
f'<div class="st-val">{st_t}</div></div>'
f'<div class="st-pill" style="background:var(--panel2);flex:2">'
f'<div class="st-lbl">Signal history</div>'
f'<div style="font-size:11px;color:var(--txt2);font-family:var(--fn)">{st_since_str}</div>'
f'</div></div>'
f'<div class="rc-sub">{met}/{tot} criteria · {pct200:+.1f}% vs 200DMA</div>'
f'</div>', unsafe_allow_html=True)

# Swarna Criteria expander
with st.expander("Swarna Criteria"):
    for idx, rk in risks.items():
        if rk.get("checks"):
            score=rk["score"]; maxs=rk.get("max_score",11)
            pct=score/maxs*100
            col=rk["risk_color"]
            st.markdown(
f'<div style="margin:8px 0 6px">'
f'<div style="display:flex;justify-content:space-between">'
f'<span style="font-weight:600;font-size:14px;color:#E6EDF3">{idx}</span>'
f'<span style="font-family:monospace;color:{col};font-weight:700">'
f'{score:.1f}/{maxs} · {pct:.0f}% · <span style="padding:1px 6px;border-radius:4px;'
f'background:{col}22;font-size:11px">{rk["risk_level"]} RISK</span></span></div>'
f'<div style="background:#30363D;border-radius:3px;height:5px;margin-top:5px">'
f'<div style="width:{pct:.0f}%;background:{col};height:5px;border-radius:3px"></div>'
f'</div></div>', unsafe_allow_html=True)
            for c in rk["checks"]:
                icon="🟢" if c["pass"] else "🔴"
                w=c["weight"]
                st.markdown(
f'<div style="padding:3px 0;font-size:13px;color:#E6EDF3">'
f'{icon} <b>{c["label"]}</b> '
f'<span style="color:#484F58">· weight {w}</span><br>'
f'<span style="color:#8B949E;font-size:11px;margin-left:20px">{c["detail"]}</span></div>',
                    unsafe_allow_html=True)
            st.markdown('<hr style="border-color:#30363D;margin:10px 0">',
                        unsafe_allow_html=True)

# ══ SECTION 2 — MORNING BRIEF ════════════════════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">Morning Brief</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)

with st.expander("Morning Brief", expanded=True):
    mb1, mb2 = st.columns([2,5])
    with mb1:
        run_brief = st.button("Generate", key="brief_run")
    with mb2:
        if st.session_state.get("brief_done"):
            st.markdown(
                f'<span style="font-size:11px;color:#484F58">'
                f'Generated {st.session_state.get("brief_ts","today")}'
                f' — cached for the day</span>', unsafe_allow_html=True)

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
                                "FMCG":"^CNXFMCG","Metal":"^CNXMETAL","Auto":"^CNXAUTO"}
                    for nm,sym in sec_syms.items():
                        d=yf.download(sym,period="2d",auto_adjust=True,progress=False)
                        if d is not None and len(d)>=2:
                            d.columns=[c[0] if isinstance(c,tuple) else c for c in d.columns]
                            c2=float(d["Close"].iloc[-1]); p=float(d["Close"].iloc[-2])
                            sectors_dict[nm]=round((c2-p)/p*100,2)
                except Exception:
                    pass
                movers_dict = {}
                try:
                    gl=gainers_losers()
                    if not gl["gainers"].empty and "Symbol" in gl["gainers"].columns:
                        movers_dict["gainers"]=gl["gainers"]["Symbol"].head(3).tolist()
                    if not gl["losers"].empty and "Symbol" in gl["losers"].columns:
                        movers_dict["losers"]=gl["losers"]["Symbol"].head(3).tolist()
                except Exception:
                    pass
                ev_list=[f"{e['Type']}: {e['Event']}" for _,e in evts.iterrows()] if not evts.empty else None
                res_list=res_df["Headline"].head(5).tolist() if not res_df.empty and "Headline" in res_df.columns else None
            with st.spinner("Writing brief…"):
                synthesis = generate_synthesis(
                    gp, recap, lvls, news3,
                    sectors=sectors_dict or None,
                    events=ev_list, results=res_list,
                    movers=movers_dict or None)
            st.session_state["brief_result"] = synthesis
            st.session_state["brief_gp"]     = gp
            st.session_state["brief_lvls"]   = lvls
            st.session_state["brief_ts"]     = ist_now().strftime("%d %b · %H:%M IST")
        else:
            synthesis = st.session_state["brief_result"]
            gp   = st.session_state.get("brief_gp", {})
            lvls = st.session_state.get("brief_lvls", {})

        para_html = "".join(f"<p>{p.strip()}</p>"
                            for p in synthesis.split("\n\n") if p.strip())
        gp_rows = ""
        for label,key,fmt in [("DXY","DXY",",.2f"),("Crude","Crude",",.2f"),
                               ("Gold","Gold",",.2f"),("Dow","Dow","+,.2f"),
                               ("Nasdaq","Nasdaq","+,.2f")]:
            d=gp.get(key,{}); v=d.get("last"); c=d.get("chg")
            vstr=f"{v:{fmt}}" if v else "—"
            cstr=(f'<span class="{"t-up" if c and c>=0 else "t-dn"}">{fmt_chg(c)}</span>'
                  if c is not None else "—")
            gp_rows+=f'<div class="bt-row"><span class="bt-label">{label}</span><span class="bt-val">{vstr} {cstr}</span></div>'
        nf=lvls.get("Nifty 50",{})
        lvl_rows=""
        for lbl,k in [("S2","S2"),("S1 / Bias","S1"),("R1","R1"),("R2","R2")]:
            lvl_rows+=f'<div class="bt-row"><span class="bt-label">{lbl}</span><span class="bt-val">{nf.get(k,"—")}</span></div>'
        st.markdown(
f'<div class="brief-wrap"><div class="brief-text">{para_html}</div>'
f'<div class="brief-grid">'
f'<div class="brief-table"><div class="bt-title">Global Pulse</div>{gp_rows}</div>'
f'<div class="brief-table"><div class="bt-title">Nifty Key Levels</div>{lvl_rows}</div>'
f'</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#484F58;font-size:13px">'
                    'Click Generate for today\'s morning brief.</span>',
                    unsafe_allow_html=True)

# ══ SECTION 3 — HHLL COMMODITY SIGNALS ═══════════════════════════════════════
st.markdown('<div class="sec"><span class="sec-title">Commodity Signals · HHLL(29) · USD</span>'
            '<span class="sec-line"></span></div>', unsafe_allow_html=True)

with st.expander("Commodity Signals", expanded=True):
    with st.spinner(""):
        sigs = get_hhll_signals()
    for tf_label,tf_key in [("1-Hour — short term","1H"),("4-Hour — medium term","4H")]:
        st.markdown(f'<div class="tf-hdr">{tf_label}</div>', unsafe_allow_html=True)
        hcols = st.columns(3)
        for ci,(name,data) in enumerate(sigs.items()):
            with hcols[ci]:
                s=data[tf_key]; sig=s["signal"]
                price=s["price"]; upper=s["upper"]; lower=s["lower"]
                crossed=s["crossed"]
                sig_time=s.get("signal_time","—")
                sig_price=s.get("signal_price",None)
                elapsed=s.get("elapsed","—")
                top_col=("#2EC4A0" if sig=="LONG" else
                         "#F85149" if sig=="SHORT" else "#484F58")
                pill_cls=("lp" if sig=="LONG" else
                          "sp" if sig=="SHORT" else "np")
                pstr=f"{price:,.3f}" if price else "—"
                ustr=f"{upper:,.3f}" if upper else "—"
                lstr=f"{lower:,.3f}" if lower else "—"
                spstr=f"@ {sig_price:,.3f}" if sig_price else ""
                ts_line=(f"{sig_time} · {elapsed} {spstr}"
                         if sig_time != "—" else "—")
                st.markdown(
f'<div class="hl-card">'
f'<div class="hl-top" style="background:{top_col}"></div>'
f'<div class="hl-com">{name}</div>'
f'<div class="hl-unit">{data["display_unit"]}</div>'
f'<div class="hl-price">{pstr}</div>'
f'<span class="hl-pill {pill_cls}">{sig}</span>'
f'<div class="hl-bands">'
f'<span>Upper {ustr}</span>'
f'<span>Lower {lstr}</span>'
f'<span style="color:#484F58">{crossed}</span>'
f'</div>'
f'<div class="hl-sig-ts">Signal since: {ts_line}</div>'
f'</div>', unsafe_allow_html=True)
        if tf_key=="1H":
            st.markdown('<div class="hdiv"></div>', unsafe_allow_html=True)

# ══ COLLAPSIBLE SECTIONS ══════════════════════════════════════════════════════
with st.expander("Market Internals"):
    hmap_mode = st.radio("View",["Nifty 50 Stocks","Sector Indices"],
                         horizontal=True, key="hmap_mode",
                         label_visibility="collapsed")
    c1,c2 = st.columns([1,1])
    with c1:
        run_int=st.button("Load",key="int_run")
    with c2:
        if st.session_state.get("int_done"):
            if st.button("Clear",key="int_clr"):
                st.session_state["int_done"]=False; st.rerun()
    if run_int: st.session_state["int_done"]=True
    if st.session_state.get("int_done"):
        with st.spinner(""):
            n50=nifty50(); ad=advance_decline(n50)
            gl=gainers_losers(); heat=nifty50_heatmap_yf()
            # Fetch sector indices individually (fixes missing sectors)
            SECTOR_SYMS = [
                ("IT","^CNXIT"),("Bank","^NSEBANK"),("Pharma","^CNXPHARMA"),
                ("FMCG","^CNXFMCG"),("Metal","^CNXMETAL"),("Auto","^CNXAUTO"),
                ("Energy","^CNXENERGY"),("Realty","^CNXREALTY"),
                ("Media","^CNXMEDIA"),("PSU Bank","^CNXPSUBANK"),
                ("Infra","^CNXINFRA"),("MidCap","NIFTY_MIDCAP_100.NS"),
            ]
            sec_rows=[]
            for nm,sym in SECTOR_SYMS:
                try:
                    d=yf.download(sym,period="2d",auto_adjust=True,
                                  progress=False,timeout=8)
                    if d is not None and not d.empty:
                        d.columns=[c[0] if isinstance(c,tuple) else c
                                   for c in d.columns]
                        d=d.dropna()
                        if len(d)>=2:
                            c2v=float(d["Close"].iloc[-1])
                            p=float(d["Close"].iloc[-2])
                            sec_rows.append({"Symbol":nm,
                                            "Chg %":round((c2v-p)/p*100,2)})
                except Exception:
                    sec_rows.append({"Symbol":nm,"Chg %":0.0})
            sec_heat=pd.DataFrame(sec_rows)

        if ad["total"]==0 and not heat.empty:
            adv=int((heat["Chg %"]>0).sum()); dec=int((heat["Chg %"]<0).sum())
            ad={"adv":adv,"dec":dec,"total":len(heat)}
        if ad["total"]>0:
            apct=ad["adv"]/ad["total"]*100
            st.markdown(
f'<div class="ad-wrap"><div class="ad-hdr">'
f'<span>Advance / Decline · Nifty 50</span>'
f'<span><span style="color:#2EC4A0">{ad["adv"]} adv</span> · '
f'<span style="color:#F85149">{ad["dec"]} dec</span></span></div>'
f'<div class="ad-bar">'
f'<div style="width:{apct:.0f}%;background:#2EC4A0"></div>'
f'<div style="flex:1;background:#F85149"></div></div></div>',
                unsafe_allow_html=True)

        def render_hmap(df,cols=10):
            if df.empty: return
            cells=""
            for _,row in df.iterrows():
                v=row["Chg %"]
                bg=("#1E8E74" if v>1 else "#2EC4A0" if v>0
                    else "#484F58" if v==0 else "#F85149" if v>-1 else "#A32D2D")
                cells+=(f'<div style="background:{bg};border-radius:5px;'
                        f'padding:5px 3px;text-align:center">'
                        f'<div style="font-size:9px;color:#fff;font-weight:600;'
                        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
                        f'{row["Symbol"]}</div>'
                        f'<div style="font-size:10px;color:#fff;font-family:monospace">'
                        f'{v:+.1f}%</div></div>')
            st.markdown(
                f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);'
                f'gap:3px;margin-bottom:12px">{cells}</div>',
                unsafe_allow_html=True)

        st.markdown(
            f'<div style="font-size:11px;color:#484F58;margin-bottom:4px">'
            f'{"Nifty 50 constituent stocks" if hmap_mode=="Nifty 50 Stocks" else "Broad sector indices"} · % change</div>',
            unsafe_allow_html=True)
        if hmap_mode=="Nifty 50 Stocks":
            render_hmap(heat,10)
        else:
            render_hmap(sec_heat,7)

        g1,g2=st.columns(2)
        with g1:
            st.markdown('<b style="color:#2EC4A0;font-size:13px">Top Gainers</b>',
                        unsafe_allow_html=True)
            if not gl["gainers"].empty:
                st.dataframe(gl["gainers"],width="stretch",hide_index=True,height=280,
                    column_config={"Chg %":st.column_config.NumberColumn(format="%.2f%%")})
        with g2:
            st.markdown('<b style="color:#F85149;font-size:13px">Top Losers</b>',
                        unsafe_allow_html=True)
            if not gl["losers"].empty:
                st.dataframe(gl["losers"],width="stretch",hide_index=True,height=280,
                    column_config={"Chg %":st.column_config.NumberColumn(format="%.2f%%")})

with st.expander("Screeners"):
    sc1,sc2=st.columns([3,1])
    with sc1:
        sname=st.selectbox("Screener",list(DEFAULT_SCREENERS.keys()),
                           key="ck_s",label_visibility="collapsed")
    with sc2:
        run_ck=st.button("Run",key="ck_run")
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
            st.caption(f"{len(ck_df)} stocks · {st.session_state.get('ck_name','')}")

with st.expander("Events & Ban List"):
    e1,e2=st.columns([1,1])
    with e1:
        run_ev=st.button("Load",key="ev_run")
    with e2:
        if st.session_state.get("ev_done"):
            if st.button("Clear",key="ev_clr"):
                st.session_state["ev_done"]=False; st.rerun()
    if run_ev: st.session_state["ev_done"]=True
    if st.session_state.get("ev_done"):
        with st.spinner(""):
            evts=events_window(7); ban=fno_ban_mwpl(); results=results_today()
        if not evts.empty:
            for _,e in evts.iterrows():
                bc="#D29922" if e["When"]=="TODAY" else "#7C5CFC"
                st.markdown(
f'<div style="padding:5px 0;font-size:13px">'
f'<span style="background:{bc};color:#0D1117;font-weight:700;font-size:10px;'
f'padding:2px 7px;border-radius:4px">{e["When"]}</span>'
f' <b style="color:#E6EDF3">{e["Date"]} · {e["Type"]}</b>'
f' <span style="color:#8B949E">— {e["Event"]}</span></div>',
                    unsafe_allow_html=True)
        b1,b2=st.columns(2)
        with b1:
            st.markdown('<b style="color:#F85149;font-size:12px">IN BAN (≥95%)</b>',
                        unsafe_allow_html=True)
            if not ban["banned"].empty:
                st.dataframe(ban["banned"],width="stretch",hide_index=True,height=200)
            else:
                st.caption("None today / unavailable.")
        with b2:
            st.markdown('<b style="color:#D29922;font-size:12px">APPROACHING (80–95%)</b>',
                        unsafe_allow_html=True)
            if not ban["entrants"].empty:
                st.dataframe(ban["entrants"],width="stretch",hide_index=True,height=200,
                    column_config={"MWPL %":st.column_config.NumberColumn(format="%.1f%%")})
            else:
                st.caption("None / unavailable.")
        if not results.empty:
            st.markdown('<b style="color:#7C5CFC;font-size:12px">RESULTS DUE</b>',
                        unsafe_allow_html=True)
            st.dataframe(results,width="stretch",hide_index=True,height=180)

with st.expander("FII Sector Flows"):
    f1,f2=st.columns([1,1])
    with f1:
        run_fii=st.button("Load",key="fii_run")
    with f2:
        if st.session_state.get("fii_done"):
            if st.button("Clear",key="fii_clr"):
                st.session_state["fii_done"]=False; st.rerun()
    if run_fii: st.session_state["fii_done"]=True
    if st.session_state.get("fii_done"):
        with st.spinner("Fetching FII sector data…"):
            fii_data,fii_source=get_fii_sectors()
        render_fii_heatmap(fii_data,fii_source)

with st.expander("Market News"):
    n1,n2=st.columns([1,1])
    with n1:
        run_news=st.button("Load",key="news_run")
    with n2:
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
                stamp=dt.strftime("%d %b · %H:%M IST") if pd.notna(dt) and dt else ""
                tag=sentiment_tag(n["Headline"])
                tag_html=(f'<span class="bull">↑ BULL</span>' if tag=="BULL"
                          else f'<span class="bear">↓ BEAR</span>' if tag=="BEAR"
                          else f'<span class="neut">· NEUT</span>')
                link=n["Link"]
                head=(f'<a href="{link}" target="_blank">{n["Headline"]}</a>'
                      if link else n["Headline"])
                st.markdown(
f'<div class="news-item">'
f'<div class="news-meta">{stamp} · {n["Source"]} {tag_html}</div>'
f'<div class="news-hl">{head}</div></div>', unsafe_allow_html=True)
        else:
            st.caption("News unavailable.")

st.markdown(
    f'<div style="height:16px"></div>'
    f'<div style="font-size:11px;color:#484F58;text-align:center">'
    f'Parabolic Trends · Swarna criteria · Angel One SmartAPI · Yahoo Finance · '
    f'Chartink · NSDL · {ist_now().strftime("%d %b %Y")} · Not investment advice</div>',
    unsafe_allow_html=True)
