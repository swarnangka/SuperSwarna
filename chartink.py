"""
Parabolic Trends — Chartink integration
Unofficial CSRF + POST endpoint for scan results.
"""
import streamlit as st
import pandas as pd
import requests
import re

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36")

# Screener dropdown options (existing)
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

# Ticker tape scans — fetched by slug, shown as scrolling tapes
TAPE_SCANS = {
    "52W":     "one-year-high-cross-2",
    "MM":      "mm-rsi-89",
    "DWM RSI": "dwm-rsi-656556",
    "ATR":     "swarna-atr",
}


def _get_csrf(sess: requests.Session) -> str:
    try:
        r = sess.get("https://chartink.com/screener/", timeout=10)
        m = re.search(r'meta name="csrf-token" content="([^"]+)"', r.text)
        return m.group(1) if m else ""
    except Exception:
        return ""


def _get_scan_clause_from_slug(sess: requests.Session, slug: str) -> str:
    """Fetch scan clause from a public Chartink screener slug."""
    try:
        r = sess.get(f"https://chartink.com/screener/{slug}", timeout=12)
        # Look for scan_clause in textarea
        m = re.search(
            r'<textarea[^>]*name=["\']scan_clause["\'][^>]*>(.*?)</textarea>',
            r.text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Fallback: look for JS variable
        m = re.search(r'scan_clause["\s:=]+["\']([^"\']{10,})["\']', r.text)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


def run_chartink_scan(scan_clause: str) -> pd.DataFrame:
    """Run any scan clause via Chartink API."""
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://chartink.com/"})
    csrf = _get_csrf(sess)
    if not csrf:
        return pd.DataFrame([{"error": "Could not connect to Chartink"}])
    try:
        r = sess.post(
            "https://chartink.com/screener/process",
            data={"scan_clause": scan_clause},
            headers={"X-Csrf-Token": csrf,
                     "Content-Type": "application/x-www-form-urlencoded",
                     "X-Requested-With": "XMLHttpRequest"},
            timeout=20)
        j = r.json()
        data = j.get("data", [])
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        rename = {"nsecode":"Symbol","close":"LTP","per_chg":"Chg %",
                  "volume":"Volume","mcap":"MCap"}
        df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
        for col in ["LTP","Chg %"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        keep = [c for c in ["Symbol","LTP","Chg %","Volume"] if c in df.columns]
        return df[keep]
    except Exception as e:
        return pd.DataFrame([{"error": str(e)[:80]}])


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_tape_scan(label: str, slug: str) -> list:
    """
    Fetch a public Chartink screener by slug.
    Returns list of dicts: {symbol, chg}
    Cached 30 min.
    """
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://chartink.com/"})
    csrf = _get_csrf(sess)
    if not csrf:
        return []
    clause = _get_scan_clause_from_slug(sess, slug)
    if not clause:
        # Fallback clauses for known slugs
        fallbacks = {
            "one-year-high-cross-2":
                "( {33489} ( daily close >= daily max( 240 , daily close ) ) )",
            "mm-rsi-89":
                "( {33489} ( daily rsi( 14 ) > 60 and weekly rsi( 14 ) > 60 ) )",
            "dwm-rsi-656556":
                "( {33489} ( daily rsi( 14 ) > 70 and weekly rsi( 14 ) > 70 and monthly rsi( 14 ) > 70 ) )",
            "swarna-atr":
                "( {33489} ( daily close >= daily max( 240 , daily close ) and daily volume > daily sma( volume,20 ) * 1.5 ) )",
        }
        clause = fallbacks.get(slug, "")
    if not clause:
        return []
    try:
        r = sess.post(
            "https://chartink.com/screener/process",
            data={"scan_clause": clause},
            headers={"X-Csrf-Token": csrf,
                     "Content-Type": "application/x-www-form-urlencoded",
                     "X-Requested-With": "XMLHttpRequest"},
            timeout=20)
        j = r.json()
        data = j.get("data", [])
        results = []
        for item in data:
            sym = item.get("nsecode","")
            chg = float(item.get("per_chg", 0) or 0)
            if sym:
                results.append({"symbol": sym, "chg": chg})
        return results[:60]  # cap at 60 symbols per tape
    except Exception:
        return []
