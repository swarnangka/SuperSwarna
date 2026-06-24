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
    "Midcap":     "^NSEMDCP150",
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
def generate_synthesis(global_pulse: dict, recap: dict,
                       levels: dict, news: list) -> str:
    """Call Claude API once per 6AM cache window to write the morning note."""
    try:
        import anthropic
        # Build a tight data summary for the prompt
        dxy = global_pulse.get("DXY", {})
        crude = global_pulse.get("Crude", {})
        gold = global_pulse.get("Gold", {})
        dow = global_pulse.get("Dow", {})
        nifty = recap.get("Nifty 50", {})
        bnk = recap.get("Bank Nifty", {})
        nifty_lvl = levels.get("Nifty 50", {})

        data_block = f"""
DXY: {dxy.get('last','N/A')} ({dxy.get('chg','N/A'):+.2f}% vs prev)
Crude: ${crude.get('last','N/A')} ({crude.get('chg','N/A'):+.2f}%)
Gold: ${gold.get('last','N/A')} ({gold.get('chg','N/A'):+.2f}%)
Dow: {dow.get('chg','N/A'):+.2f}%
Nifty yesterday: O={nifty.get('open','N/A')} H={nifty.get('high','N/A')} L={nifty.get('low','N/A')} C={nifty.get('close','N/A')} ({nifty.get('chg','N/A'):+.2f}%)
Bank Nifty yesterday: C={bnk.get('close','N/A')} ({bnk.get('chg','N/A'):+.2f}%)
Nifty key levels: S2={nifty_lvl.get('S2')} S1/Bias={nifty_lvl.get('S1')} R1={nifty_lvl.get('R1')} R2={nifty_lvl.get('R2')}
Top headlines: {'; '.join(news) if news else 'None'}
"""
        system = """You write a morning market brief for Indian equity traders.
Style rules — follow strictly:
- 3 short paragraphs, 50-60 words each, no more
- First paragraph: global cues and their implication for India
- Second paragraph: Nifty/BankNifty structure, key level to watch today
- Third paragraph: playbook — what to do, what to avoid, where to focus
- Tone: direct, declarative, confident. Like a senior trader wrote it at 5:45 AM
- No bullet points. No emoji. No hedging language. No "it appears" or "it seems"
- Do not mention that you are an AI. Write as a human desk note
- Specific levels must appear as numbers, not words
- Start directly with the content — no title, no date header"""

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=system,
            messages=[{"role": "user",
                       "content": f"Write today's morning brief using this data:\n{data_block}"}]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        return f"Morning brief unavailable — {str(e)[:60]}"
