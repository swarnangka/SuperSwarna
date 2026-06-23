"""
SuperSwarna — data layer
Handles Angel One SmartAPI connection + yfinance fallback.
All credentials read from Streamlit secrets (never hardcoded).
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# ── Angel One SmartAPI (optional — app degrades gracefully if absent) ─────────
SMARTAPI_AVAILABLE = False
try:
    from SmartApi import SmartConnect
    import pyotp
    SMARTAPI_AVAILABLE = True
except Exception:
    SMARTAPI_AVAILABLE = False


# ── Instrument tokens (Angel One symbol tokens for indices) ───────────────────
# These are the NSE tokens used by SmartAPI for index spot values.
INDEX_TOKENS = {
    "NIFTY 50":   {"token": "99926000", "exchange": "NSE", "yf": "^NSEI"},
    "BANK NIFTY": {"token": "99926009", "exchange": "NSE", "yf": "^NSEBANK"},
    "S&P 500":    {"token": None,        "exchange": None,  "yf": "^GSPC"},
    "NASDAQ":     {"token": None,        "exchange": None,  "yf": "^IXIC"},
}


@st.cache_resource(show_spinner=False)
def get_smartapi_session():
    """Create an authenticated SmartAPI session. Cached for the server session."""
    if not SMARTAPI_AVAILABLE:
        return None
    try:
        creds = st.secrets["angelone"]
        api_key   = creds["api_key"]
        client_id = creds["client_code"]
        mpin      = creds["mpin"]
        totp_secret = creds["totp_secret"]

        obj = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_secret).now()
        data = obj.generateSession(client_id, mpin, totp)
        if data.get("status"):
            return obj
        return None
    except Exception:
        return None


def smartapi_connected() -> bool:
    return get_smartapi_session() is not None


# ── yfinance fallback fetch ───────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def fetch_yf(symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    import yfinance as yf
    for attempt in range(3):
        try:
            df = yf.download(symbol, period=period, interval=interval,
                             auto_adjust=True, progress=False, threads=False)
            if df is not None and not df.empty:
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                return df[keep].dropna()
        except Exception as e:
            if "Too Many Requests" in str(e) or "Rate limited" in str(e):
                time.sleep(1.5 * (attempt + 1))
                continue
        time.sleep(0.3)
    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_index_ltp(index_name: str) -> float:
    """Live LTP via SmartAPI if available; else last yfinance close."""
    info = INDEX_TOKENS.get(index_name, {})
    obj = get_smartapi_session()
    if obj and info.get("token"):
        try:
            r = obj.ltpData(info["exchange"], index_name, info["token"])
            if r.get("status") and r.get("data"):
                return float(r["data"]["ltp"])
        except Exception:
            pass
    df = fetch_yf(info.get("yf", ""), period="5d")
    if not df.empty:
        return float(df["Close"].iloc[-1])
    return float("nan")


# ── Technical indicators ──────────────────────────────────────────────────────
def add_mas(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["MA50"]  = df["Close"].rolling(50).mean()
    df["MA150"] = df["Close"].rolling(150).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["MA200_1M"] = df["MA200"].shift(22)
    df["52WH"] = df["Close"].rolling(252, min_periods=50).max()
    df["52WL"] = df["Close"].rolling(252, min_periods=50).min()
    return df


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """Classic Supertrend. Returns df with 'ST' line and 'ST_dir' (1 bull / -1 bear)."""
    if df.empty or len(df) < period + 1:
        df = df.copy()
        df["ST"] = np.nan
        df["ST_dir"] = 0
        return df
    df = df.copy()
    hl2 = (df["High"] + df["Low"]) / 2
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()

    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    close = df["Close"].values.copy()
    fu = upper.values.copy()
    fl = lower.values.copy()
    for i in range(1, len(df)):
        fu[i] = upper.iloc[i] if (upper.iloc[i] < fu[i-1] or close[i-1] > fu[i-1]) else fu[i-1]
        fl[i] = lower.iloc[i] if (lower.iloc[i] > fl[i-1] or close[i-1] < fl[i-1]) else fl[i-1]

    st_line = np.full(len(df), np.nan)
    direction = np.ones(len(df), dtype=int)
    for i in range(1, len(df)):
        if close[i] > fu[i-1]:
            direction[i] = 1
        elif close[i] < fl[i-1]:
            direction[i] = -1
        else:
            direction[i] = direction[i-1]
        st_line[i] = fl[i] if direction[i] == 1 else fu[i]

    df["ST"] = st_line
    df["ST_dir"] = direction
    return df


def rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return float("nan")
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return float(out.iloc[-1])
