"""
Parabolic Trends — Morning Brief
Fetches global/Indian market data, computes key levels, generates AI synthesis.
Cached at 6 AM IST daily — first load after 6 AM triggers generation.
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timezone, timedelta, date
import xml.etree.ElementTree as ET

IST = timezone(timedelta(hours=5, minutes=30))

GLOBAL_SYMBOLS = {
    "DXY":      "DX-Y.NYB",
    "Crude":    "CL=F",
    "Gold":     "GC=F",
    "Silver":   "SI=F",
    "US10Y":    "^TNX",
    "Dow":      "^DJI",
    "Nasdaq":   "^IXIC",
    "GiftNifty":"^NSEI",
    "Nikkei":   "^N225",
    "HangSeng": "^HSI",
    "DAX":      "^GDAXI",
    "USDINR":   "USDINR=X",
}

INDEX_SYMBOLS = {
    "Nifty 50":   "^NSEI",
    "Bank Nifty": "^NSEBANK",
    "Midcap":     "NIFTY_MIDCAP_100.NS",
}


def _ist_now() -> datetime:
    return datetime.now(IST)


def _cache_key() -> str:
    """Key changes at 6 AM IST each day — forces daily refresh."""
    n = _ist_now()
    if n.hour < 6:
        d = (n - timedelta(days=1)).date()
    else:
        d = n.date()
    return f"morning_brief_{d}"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_global_pulse() -> dict:
    syms = list(GLOBAL_SYMBOLS.values())
    out = {}
    try:
        data = yf.download(syms, period="2d", auto_adjust=True,
                           progress=False, group_by="ticker")
        for name, sym in GLOBAL_SYMBOLS.items():
            try:
                if len(syms) == 1:
                    d = data
                else:
                    d = data[sym]
                d = d.dropna()
                if len(d) >= 2:
                    last = float(d["Close"].iloc[-1])
                    prev = float(d["Close"].iloc[-2])
                    chg  = (last - prev) / prev * 100
                    out[name] = {"last": round(last, 2), "chg": round(chg, 2)}
            except Exception:
                out[name] = {"last": None, "chg": None}
    except Exception:
        pass
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_indian_recap() -> dict:
    out = {}
    for name, sym in INDEX_SYMBOLS.items():
        try:
            df = yf.download(sym, period="5d", auto_adjust=True, progress=False)
            if df is not None and not df.empty:
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                df = df.dropna()
                if len(df) >= 2:
                    r = df.iloc[-1]; p = df.iloc[-2]
                    out[name] = {
                        "open":  round(float(r["Open"]),  1),
                        "high":  round(float(r["High"]),  1),
                        "low":   round(float(r["Low"]),   1),
                        "close": round(float(r["Close"]), 1),
                        "prev":  round(float(p["Close"]), 1),
                        "chg":   round((float(r["Close"]) - float(p["Close"])) / float(p["Close"]) * 100, 2),
                        "ma50":  round(float(df["Close"].rolling(50).mean().iloc[-1]), 1) if len(df) >= 50 else None,
                        "ma200": round(float(df["Close"].rolling(200).mean().iloc[-1]), 1) if len(df) >= 200 else None,
                    }
        except Exception:
            continue
    return out


def compute_key_levels(recap: dict) -> dict:
    """S1/S2 and R1/R2 from pivot point method using yesterday's OHLC."""
    levels = {}
    for name, d in recap.items():
        try:
            h = d["high"]; l = d["low"]; c = d["close"]
            pivot = (h + l + c) / 3
            r1 = round(2 * pivot - l, 1)
            s1 = round(2 * pivot - h, 1)
            r2 = round(pivot + (h - l), 1)
            s2 = round(pivot - (h - l), 1)
            # bias line = S1 (holding above = bullish, closing below = key risk)
            levels[name] = {"S2": s2, "S1": s1, "Bias": s1, "R1": r1, "R2": r2}
        except Exception:
            continue
    return levels


@st.cache_data(ttl=600, show_spinner=False)
def fetch_top_news(max_items: int = 3) -> list:
    feeds = {
        "Reuters":  "https://feeds.reuters.com/reuters/businessNews",
        "CNBC":     "https://feeds.content.cnbc.com/applications/cnbc/rss?id=100003114",
    }
    items = []
    for source, url in feeds.items():
        try:
            r = requests.get(url, timeout=8,
                headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200: continue
            root = ET.fromstring(r.content)
            for it in root.findall(".//item")[:2]:
                title = it.findtext("title","").strip()
                if title:
                    items.append(f"{source}: {title}")
        except Exception:
            continue
    return items[:max_items]


@st.cache_data(ttl=43200, show_spinner=False)
def generate_synthesis(global_pulse: dict, recap: dict, levels: dict,
                       news: list, sectors: dict = None,
                       events: list = None, results: list = None,
                       movers: dict = None) -> str:
    """Call Claude API once at 6AM IST. Cached all day. Never re-called."""
    try:
        import anthropic, os
        api_key = None
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception:
            pass
        if not api_key:
            try:
                api_key = st.secrets["anthropic_api_key"]
            except Exception:
                pass
        if not api_key:
            try:
                api_key = st.secrets["anthropic"]["api_key"]
            except Exception:
                pass
        if not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return ("Morning brief unavailable — ANTHROPIC_API_KEY not found. "
                    "In Streamlit: Settings → Secrets → add exactly:\n"
                    "ANTHROPIC_API_KEY = \"sk-ant-api03-...\"")
        if not str(api_key).startswith("sk-"):
            return (f"Morning brief unavailable — API key looks wrong "
                    f"(starts with '{str(api_key)[:8]}...'). Check Streamlit Secrets.")

        def fv(v, fmt=".2f"):
            if v is None: return "N/A"
            try: return f"{v:{fmt}}"
            except: return str(v)

        dxy   = global_pulse.get("DXY", {})
        crude = global_pulse.get("Crude", {})
        gold  = global_pulse.get("Gold", {})
        dow   = global_pulse.get("Dow", {})
        nifty = recap.get("Nifty 50", {})
        bnk   = recap.get("Bank Nifty", {})
        nifty_lvl = levels.get("Nifty 50", {})

        # Sector strength/weakness
        sector_str = "Not available"
        if sectors:
            strong = [f"{k} ({v:+.1f}%)" for k,v in sectors.items() if v > 0][:3]
            weak   = [f"{k} ({v:+.1f}%)" for k,v in sectors.items() if v < 0][:3]
            sector_str = (f"Strong: {', '.join(strong) if strong else 'none'}. "
                         f"Weak: {', '.join(weak) if weak else 'none'}.")

        # Top movers
        movers_str = "Not available"
        if movers:
            gainers = movers.get("gainers", [])[:3]
            losers  = movers.get("losers", [])[:3]
            movers_str = (f"Top gainers: {', '.join(gainers) if gainers else 'none'}. "
                         f"Top losers: {', '.join(losers) if losers else 'none'}.")

        # Events today
        events_str = "No major events today."
        if events:
            events_str = "; ".join(events)

        # Results today
        results_str = "No results due today."
        if results:
            results_str = "; ".join(results[:5])

        data_block = f"""
GLOBAL CUES:
DXY: {fv(dxy.get('last'))} ({fv(dxy.get('chg'),'+.2f')}%)
Crude: ${fv(crude.get('last'))} ({fv(crude.get('chg'),'+.2f')}%)
Gold: ${fv(gold.get('last'))} ({fv(gold.get('chg'),'+.2f')}%)
Dow Jones: {fv(dow.get('chg'),'+.2f')}%
Headlines: {'; '.join(news) if news else 'None'}

INDIAN MARKET (yesterday):
Nifty: O={fv(nifty.get('open'))} H={fv(nifty.get('high'))} L={fv(nifty.get('low'))} C={fv(nifty.get('close'))} ({fv(nifty.get('chg'),'+.2f')}%)
Bank Nifty: C={fv(bnk.get('close'))} ({fv(bnk.get('chg'),'+.2f')}%)
Key levels: S2={nifty_lvl.get('S2','N/A')} S1={nifty_lvl.get('S1','N/A')} R1={nifty_lvl.get('R1','N/A')} R2={nifty_lvl.get('R2','N/A')}

SECTORS (yesterday):
{sector_str}

MOVERS (yesterday):
{movers_str}

TODAY'S EVENTS: {events_str}
TODAY'S RESULTS: {results_str}
"""

        system = """You write a morning market brief for Indian equity traders. 4 tight paragraphs.

Para 1 — Global cues: DXY/crude/gold direction and what it means for India today. 40-50 words.
Para 2 — Index structure: Nifty/BankNifty key level to hold or break today. Be specific with numbers. 40-50 words.
Para 3 — Sectors and movers: which sectors showing strength or weakness, any stocks to watch. If results are due, name them. If no events or results, explicitly say so. 40-50 words.
Para 4 — Playbook: one clear action bias for the session. What to do, what to avoid. 30-40 words.

Rules:
- Direct, declarative, confident. Like a senior trader wrote this at 5:45 AM.
- No bullets. No emoji. No hedging. No "it appears" or "it seems" or "it is worth noting".
- Do not mention being an AI.
- Specific numbers must appear as digits, not words.
- Start directly — no title, no date, no greeting."""

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system,
            messages=[{"role": "user",
                       "content": f"Write today's morning brief:\n{data_block}"}])
        return msg.content[0].text.strip()
    except Exception as e:
        return f"Morning brief error — {str(e)[:80]}"
