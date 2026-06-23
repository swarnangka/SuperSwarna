"""
SuperSwarna — Angel One SmartAPI data layer (v2)
Live LTP, historical candles, intraday 10AM capture.
Falls back to yfinance only for index history if SmartAPI unavailable.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

SMARTAPI_AVAILABLE = False
try:
    from SmartApi import SmartConnect
    import pyotp
    SMARTAPI_AVAILABLE = True
except Exception:
    SMARTAPI_AVAILABLE = False

INDEX_TOKENS = {
    "NIFTY 50":   {"token": "99926000", "exchange": "NSE", "yf": "^NSEI"},
    "BANK NIFTY": {"token": "99926009", "exchange": "NSE", "yf": "^NSEBANK"},
}


@st.cache_resource(show_spinner=False)
def get_session():
    if not SMARTAPI_AVAILABLE:
        return None
    try:
        creds = st.secrets["angelone"]
        obj = SmartConnect(api_key=creds["api_key"])
        totp = pyotp.TOTP(creds["totp_secret"]).now()
        data = obj.generateSession(creds["client_code"], creds["mpin"], totp)
        if data.get("status"):
            return obj
        return None
    except Exception:
        return None


def connected() -> bool:
    return get_session() is not None


@st.cache_data(ttl=86400, show_spinner=False)
def load_instruments() -> pd.DataFrame:
    import requests
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    try:
        r = requests.get(url, timeout=30)
        df = pd.DataFrame(r.json())
        eq = df[(df["exch_seg"] == "NSE") & (df["symbol"].str.endswith("-EQ"))].copy()
        eq["clean"] = eq["symbol"].str.replace("-EQ", "", regex=False)
        return eq[["token", "symbol", "name", "clean"]]
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def token_for(symbol: str) -> str:
    inst = load_instruments()
    if inst.empty:
        return None
    m = inst[inst["clean"] == symbol]
    if not m.empty:
        return str(m.iloc[0]["token"])
    return None


@st.cache_data(ttl=900, show_spinner=False)
def get_candles(token: str, exchange: str = "NSE",
                interval: str = "ONE_DAY", days: int = 400) -> pd.DataFrame:
    obj = get_session()
    if obj is None or token is None:
        return pd.DataFrame()
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(days=days)
    params = {
        "exchange": exchange, "symboltoken": token, "interval": interval,
        "fromdate": from_dt.strftime("%Y-%m-%d %H:%M"),
        "todate": to_dt.strftime("%Y-%m-%d %H:%M"),
    }
    for attempt in range(3):
        try:
            r = obj.getCandleData(params)
            if r.get("status") and r.get("data"):
                df = pd.DataFrame(r["data"],
                    columns=["ts","Open","High","Low","Close","Volume"])
                df["ts"] = pd.to_datetime(df["ts"])
                df = df.set_index("ts")
                for c in ["Open","High","Low","Close","Volume"]:
                    df[c] = pd.to_numeric(df[c])
                return df
            return pd.DataFrame()
        except Exception as e:
            if "rate" in str(e).lower():
                time.sleep(0.5 * (attempt + 1)); continue
            return pd.DataFrame()
    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_ltp(symbol: str, token: str, exchange: str = "NSE") -> float:
    obj = get_session()
    if obj is None or token is None:
        return float("nan")
    try:
        r = obj.ltpData(exchange, symbol, token)
        if r.get("status") and r.get("data"):
            return float(r["data"]["ltp"])
    except Exception:
        pass
    return float("nan")


@st.cache_data(ttl=300, show_spinner=False)
def get_10am_price(token: str, exchange: str = "NSE") -> float:
    obj = get_session()
    if obj is None or token is None:
        return float("nan")
    today = datetime.now().strftime("%Y-%m-%d")
    params = {
        "exchange": exchange, "symboltoken": token,
        "interval": "FIFTEEN_MINUTE",
        "fromdate": f"{today} 10:00", "todate": f"{today} 10:15",
    }
    try:
        r = obj.getCandleData(params)
        if r.get("status") and r.get("data") and len(r["data"]) > 0:
            return float(r["data"][0][4])
    except Exception:
        pass
    return float("nan")


@st.cache_data(ttl=900, show_spinner=False)
def fetch_yf(symbol: str, period: str = "2y") -> pd.DataFrame:
    import yfinance as yf
    for attempt in range(3):
        try:
            df = yf.download(symbol, period=period, auto_adjust=True,
                             progress=False, threads=False)
            if df is not None and not df.empty:
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                keep = [c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
                return df[keep].dropna()
        except Exception as e:
            if "Too Many Requests" in str(e):
                time.sleep(1.5 * (attempt + 1)); continue
        time.sleep(0.3)
    return pd.DataFrame()


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
    if df.empty or len(df) < period + 1:
        df = df.copy(); df["ST"] = np.nan; df["ST_dir"] = 0; return df
    df = df.copy()
    hl2 = (df["High"] + df["Low"]) / 2
    prev_close = df["Close"].shift(1)
    tr = pd.concat([df["High"]-df["Low"],
                    (df["High"]-prev_close).abs(),
                    (df["Low"]-prev_close).abs()], axis=1).max(axis=1)
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
    return float((100 - (100/(1+rs))).iloc[-1])
