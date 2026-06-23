"""
SuperSwarna — Market data from NSE India (free, zero Angel One load).
NSE requires a session-cookie handshake: hit the homepage first to get
cookies, then call the JSON data endpoints with browser-like headers.
All functions cached; called on button press only.
"""
import streamlit as st
import pandas as pd
import requests

NSE_HOME = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/122.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _nse_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get(NSE_HOME, timeout=10)  # seeds cookies
        s.get(NSE_HOME + "/market-data/live-equity-market", timeout=10)
    except Exception:
        pass
    return s


def _nse_get(path: str) -> dict:
    """GET a NSE JSON endpoint with cookie handshake + one retry."""
    for attempt in range(2):
        try:
            s = _nse_session()
            r = s.get(NSE_HOME + path, timeout=12)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return {}


# ── Gainers & Losers (from the NIFTY universe) ────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def gainers_losers() -> dict:
    """NSE live-analysis gainers/losers endpoints → JSON."""
    out = {"gainers": pd.DataFrame(), "losers": pd.DataFrame()}
    g = _nse_get("/api/live-analysis-variations?index=gainers")
    l = _nse_get("/api/live-analysis-variations?index=loosers")  # NSE's spelling

    def parse(payload):
        # payload structure: {"NIFTY": {"data": [...]}, "BANKNIFTY": {...}, ...}
        if not payload:
            return pd.DataFrame()
        block = payload.get("NIFTY") or next(
            (v for v in payload.values() if isinstance(v, dict) and "data" in v), None)
        if not block or "data" not in block:
            return pd.DataFrame()
        df = pd.DataFrame(block["data"])
        ren = {}
        if "symbol" in df: ren["symbol"] = "Symbol"
        if "ltp" in df: ren["ltp"] = "LTP"
        if "perChange" in df: ren["perChange"] = "Chg %"
        if "netPrice" in df: ren["netPrice"] = "Net %"
        if "tradedQuantity" in df: ren["tradedQuantity"] = "Volume"
        df = df.rename(columns=ren)
        keep = [c for c in ["Symbol","LTP","Chg %","Volume"] if c in df.columns]
        return df[keep].head(10) if keep else df.head(10)

    out["gainers"] = parse(g)
    out["losers"] = parse(l)
    return out


# ── Most active by volume & value ─────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def most_active() -> dict:
    out = {"volume": pd.DataFrame(), "value": pd.DataFrame()}
    vol = _nse_get("/api/live-analysis-most-active-securities?index=volume")
    val = _nse_get("/api/live-analysis-most-active-securities?index=value")

    def parse(payload):
        if not payload or "data" not in payload:
            return pd.DataFrame()
        df = pd.DataFrame(payload["data"])
        ren = {}
        if "symbol" in df: ren["symbol"] = "Symbol"
        if "lastPrice" in df: ren["lastPrice"] = "LTP"
        if "ltp" in df: ren["ltp"] = "LTP"
        if "pChange" in df: ren["pChange"] = "Chg %"
        if "perChange" in df: ren["perChange"] = "Chg %"
        if "tradedQuantity" in df: ren["tradedQuantity"] = "Volume"
        if "totalTradedVolume" in df: ren["totalTradedVolume"] = "Volume"
        if "turnover" in df: ren["turnover"] = "Turnover"
        if "totalTradedValue" in df: ren["totalTradedValue"] = "Turnover"
        df = df.rename(columns=ren)
        keep = [c for c in ["Symbol","LTP","Chg %","Volume","Turnover"] if c in df.columns]
        return df[keep].head(10) if keep else df.head(10)

    out["volume"] = parse(vol)
    out["value"] = parse(val)
    return out


# ── Advance / Decline (NIFTY 50) ──────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def nifty50() -> pd.DataFrame:
    """NIFTY 50 constituents with % change — powers A/D and heatmap."""
    payload = _nse_get("/api/equity-stockIndices?index=NIFTY%2050")
    if not payload or "data" not in payload:
        return pd.DataFrame()
    df = pd.DataFrame(payload["data"])
    # First row is the index itself; keep only constituents
    df = df[df["symbol"] != "NIFTY 50"] if "symbol" in df else df
    ren = {}
    if "symbol" in df: ren["symbol"] = "Symbol"
    if "lastPrice" in df: ren["lastPrice"] = "LTP"
    if "pChange" in df: ren["pChange"] = "Chg %"
    df = df.rename(columns=ren)
    keep = [c for c in ["Symbol","LTP","Chg %"] if c in df.columns]
    return df[keep] if keep else df


def advance_decline(n50: pd.DataFrame) -> dict:
    if n50.empty or "Chg %" not in n50:
        return {"adv": 0, "dec": 0, "unch": 0, "total": 0}
    adv = int((n50["Chg %"] > 0).sum())
    dec = int((n50["Chg %"] < 0).sum())
    unch = int((n50["Chg %"] == 0).sum())
    return {"adv": adv, "dec": dec, "unch": unch, "total": len(n50)}


# ── Nifty 50 heatmap via Yahoo Finance batch (NSE endpoint blocks cloud IPs) ──
NIFTY50_YF = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI","TITAN",
    "SUNPHARMA","BAJFINANCE","HCLTECH","WIPRO","ULTRACEMCO","NESTLEIND","NTPC",
    "POWERGRID","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS",
    "COALINDIA","ONGC","GRASIM","HINDALCO","CIPLA","DRREDDY","BAJAJFINSV",
    "BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","BRITANNIA","TECHM","INDUSINDBK",
    "BPCL","SHREECEM","APOLLOHOSP","TATACONSUM","DIVISLAB","SBILIFE","HDFCLIFE",
    "LTIM","TRENT",
]

@st.cache_data(ttl=300, show_spinner=False)
def nifty50_heatmap_yf() -> pd.DataFrame:
    """Nifty 50 % change via one batched Yahoo Finance download."""
    import yfinance as yf
    syms = [s + ".NS" for s in NIFTY50_YF]
    rows = []
    try:
        data = yf.download(syms, period="2d", auto_adjust=True,
                           progress=False, group_by="ticker", threads=True)
        for s in NIFTY50_YF:
            try:
                d = data[s + ".NS"]["Close"].dropna()
                if len(d) >= 2:
                    chg = (float(d.iloc[-1]) - float(d.iloc[-2])) / float(d.iloc[-2]) * 100
                    rows.append({"Symbol": s, "Chg %": round(chg, 2)})
            except Exception:
                continue
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame(rows)
