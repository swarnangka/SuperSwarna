"""
Parabolic Trends — Chartink integration
3 tape scans: 52WH, MM, ATR
"""
import streamlit as st
import pandas as pd
import requests
import re

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36")

DEFAULT_SCREENERS = {
    "52-Week High":
        "( {33489} ( daily close >= daily max( 240 , daily close ) ) )",
    "Multi-TF RSI > 70 (D/W/M)":
        "( {33489} ( daily rsi( 14 ) > 70 and weekly rsi( 14 ) > 70 and "
        "monthly rsi( 14 ) > 70 ) )",
    "Minervini Trend + Monthly RSI > 75":
        "( {33489} ( daily ema( close,50 ) > daily ema( close,150 ) and "
        "daily ema( close,150 ) > daily ema( close,200 ) and "
        "daily close > daily ema( close,50 ) and daily volume > 100000 and "
        "monthly rsi( 14 ) > 75 ) )",
}

# 3 tape scans — slug + reliable fallback clause
TAPE_SCANS = {
    "52WH": {
        "slug": "one-year-high-cross-2",
        "fallback": "( {33489} ( daily close >= daily max( 240 , daily close ) ) )",
    },
    "MM": {
        "slug": "mm-rsi-89",
        # MM ema crossovers and RSI monthly 75
        "fallback": (
            "( {33489} ( daily ema( close,20 ) > daily ema( close,50 ) and "
            "daily ema( close,50 ) > daily ema( close,150 ) and "
            "monthly rsi( 14 ) > 75 ) )"
        ),
    },
    "ATR": {
        "slug": "swarna-atr",
        # ATR breakout — price crosses 52W high with volume surge
        "fallback": (
            "( {33489} ( daily close >= daily max( 240 , daily close ) and "
            "daily volume >= daily sma( volume , 20 ) * 1.5 ) )"
        ),
    },
}


def _get_csrf(sess: requests.Session) -> str:
    try:
        r = sess.get("https://chartink.com/screener/", timeout=10)
        m = re.search(r'meta name="csrf-token" content="([^"]+)"', r.text)
        return m.group(1) if m else ""
    except Exception:
        return ""


def _get_clause_from_slug(sess: requests.Session, slug: str) -> str:
    """Try to extract scan clause from public Chartink screener page."""
    try:
        r = sess.get(f"https://chartink.com/screener/{slug}", timeout=12)
        m = re.search(
            r'<textarea[^>]*name=["\']scan_clause["\'][^>]*>(.*?)</textarea>',
            r.text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        m = re.search(r'"scan_clause"\s*:\s*"([^"]{10,})"', r.text)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


def _run_clause(sess: requests.Session, csrf: str, clause: str) -> list:
    """POST a clause to Chartink and return list of {symbol, chg} dicts."""
    try:
        r = sess.post(
            "https://chartink.com/screener/process",
            data={"scan_clause": clause},
            headers={
                "X-Csrf-Token": csrf,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=20)
        data = r.json().get("data", [])
        out = []
        for item in data:
            sym = item.get("nsecode", "")
            chg = float(item.get("per_chg", 0) or 0)
            if sym:
                out.append({"symbol": sym, "chg": chg})
        return out[:80]
    except Exception:
        return []


def run_chartink_scan(scan_clause: str) -> pd.DataFrame:
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://chartink.com/"})
    csrf = _get_csrf(sess)
    if not csrf:
        return pd.DataFrame([{"error": "Could not connect to Chartink"}])
    items = _run_clause(sess, csrf, scan_clause)
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items).rename(columns={"symbol":"Symbol","chg":"Chg %"})
    df["Chg %"] = pd.to_numeric(df["Chg %"], errors="coerce")
    return df


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_tape_scan(label: str) -> list:
    """
    Fetch a tape scan by label. Tries live slug first, falls back to
    hardcoded clause. Returns [] if Chartink unreachable.
    """
    info = TAPE_SCANS.get(label)
    if not info:
        return []
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://chartink.com/"})
    csrf = _get_csrf(sess)
    if not csrf:
        return []
    # Try live slug first
    clause = _get_clause_from_slug(sess, info["slug"])
    # Fall back to hardcoded clause if live extraction failed
    if not clause:
        clause = info["fallback"]
    return _run_clause(sess, csrf, clause)
