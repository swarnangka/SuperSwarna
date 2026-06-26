"""
Parabolic Trends — data layer v4
Angel One SmartAPI + Yahoo Finance fallback.
Parallel fetch support via ThreadPoolExecutor.
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
import pyotp
import time
import yfinance as yf
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

IST = timezone(timedelta(hours=5, minutes=30))

INDEX_TOKENS = {
    "Nifty 50":   {"token": "99926000", "exchange": "NSE", "yf": "^NSEI"},
    "Bank Nifty": {"token": "99926009", "exchange": "NSE", "yf": "^NSEBANK"},
}

def ist_now() -> datetime:
    return datetime.now(IST)

def is_market_hours() -> bool:
    """True if current IST time is within NSE trading hours Mon-Fri."""
    n = ist_now()
    if n.weekday() >= 5:   # Saturday/Sunday
        return False
    t = n.hour * 60 + n.minute
    return 555 <= t <= 930  # 9:15 AM to 3:30 PM

def market_status() -> str:
    n = ist_now()
    if n.weekday() >= 5:
        return "Weekend"
    t = n.hour * 60 + n.minute
    if t < 555:
        return "Pre-market"
    if t <= 930:
        return "Live"
    return "Closed"

@st.cache_resource(ttl=3000, show_spinner=False)
def get_session():
    """Angel One SmartAPI session. Re-auths every 50 min."""
    try:
        secrets = st.secrets.get("angelone", {})
        api_key     = secrets.get("api_key", "")
        client_code = secrets.get("client_code", "")
        mpin        = secrets.get("mpin", "")
        totp_secret = secrets.get("totp_secret", "")
        if not all([api_key, client_code, mpin, totp_secret]):
            return None
        from SmartApi import SmartConnect
        obj = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_secret).now()
        obj.generateSession(client_code, mpin, totp)
        return obj
    except Exception:
        return None

def connected() -> bool:
    try:
        s = get_session()
        return s is not None
    except Exception:
        return False

def get_ltp(index_name: str, token: str, exchange: str) -> float:
    try:
        s = get_session()
        if s is None:
            return float("nan")
        sym_map = {"Nifty 50": "NIFTY 50", "Bank Nifty": "BANK NIFTY"}
        r = s.ltpData(exchange, sym_map.get(index_name, index_name), token)
        if r and r.get("status"):
            return float(r["data"]["ltp"])
    except Exception:
        pass
    return float("nan")

def get_candles(token: str, exchange: str, interval: str, days: int = 400) -> pd.DataFrame:
    try:
        s = get_session()
        if s is None:
            return pd.DataFrame()
        now = ist_now()
        frm = (now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        to  = now.strftime("%Y-%m-%d %H:%M")
        r = s.getCandleData({"exchange": exchange, "symboltoken": token,
                             "interval": interval, "fromdate": frm, "todate": to})
        if not r or not r.get("status"):
            return pd.DataFrame()
        df = pd.DataFrame(r["data"],
                          columns=["Date","Open","High","Low","Close","Volume"])
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        for c in ["Open","High","Low","Close","Volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def fetch_yf(symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Fetch from Yahoo Finance with clean column handling."""
    try:
        df = yf.download(symbol, period=period, interval=interval,
                         auto_adjust=True, progress=False, timeout=10)
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        return df[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()

def fetch_yf_parallel(symbols: dict, period: str = "2d",
                      max_workers: int = 8, timeout_s: float = 12.0) -> dict:
    """
    Fetch multiple Yahoo Finance symbols in parallel.
    symbols: {name: yahoo_symbol}
    Returns: {name: {"last": float, "chg": float}} or {name: None} on failure
    """
    def _fetch_one(name: str, sym: str) -> tuple:
        try:
            df = yf.download(sym, period=period, auto_adjust=True,
                             progress=False, timeout=8)
            if df is None or df.empty:
                return name, None
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df.dropna()
            if len(df) < 2:
                return name, None
            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            chg  = (last - prev) / prev * 100
            return name, {"last": round(last, 4), "chg": round(chg, 4)}
        except Exception:
            return name, None

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_one, name, sym): name
                   for name, sym in symbols.items()}
        for fut in as_completed(futures, timeout=timeout_s):
            try:
                name, val = fut.result()
                results[name] = val
            except Exception:
                results[futures[fut]] = None
    # Fill missing
    for name in symbols:
        if name not in results:
            results[name] = None
    return results

def add_mas(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 50:
        return df
    df = df.copy()
    df["MA50"]    = df["Close"].rolling(50).mean()
    df["MA150"]   = df["Close"].rolling(150).mean()
    df["MA200"]   = df["Close"].rolling(200).mean()
    df["52WH"]    = df["High"].rolling(252).max()
    df["52WL"]    = df["Low"].rolling(252).min()
    if len(df) >= 220:
        df["MA200_1M"] = df["MA200"].shift(20)
    else:
        df["MA200_1M"] = df["MA200"]
    return df

def supertrend(df: pd.DataFrame, period: int = 10,
               factor: float = 2.0) -> pd.DataFrame:
    """
    TradingView-accurate Supertrend.
    ATR = Wilder RMA of True Range (not simple H-L mean).
    True Range = max(H-L, |H-prevC|, |L-prevC|)
    Wilder RMA = EWM with alpha=1/period, adjust=False.
    Default factor=2.0 matches TradingView 'Supertrend 10 hl2 2' setting.
    """
    if df.empty or len(df) < period + 1:
        return df
    df = df.copy()

    # True Range — correctly includes gap component
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Wilder's RMA (same as TradingView's ta.rma)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    hl2 = (df["High"] + df["Low"]) / 2

    # Basic upper (support) and lower (resistance) bands
    basic_upper = hl2 - factor * atr
    basic_lower = hl2 + factor * atr

    final_upper = pd.Series(np.nan, index=df.index, dtype=float)
    final_lower = pd.Series(np.nan, index=df.index, dtype=float)
    direction   = pd.Series(np.nan, index=df.index, dtype=float)

    closes = df["Close"].values.copy()
    bu = basic_upper.values.copy()
    bl = basic_lower.values.copy()
    fu = np.full(len(df), np.nan)
    fl = np.full(len(df), np.nan)
    di = np.full(len(df), np.nan)

    for i in range(len(df)):
        if np.isnan(atr.iloc[i]) or i == 0:
            fu[i] = bu[i] if not np.isnan(bu[i]) else 0.0
            fl[i] = bl[i] if not np.isnan(bl[i]) else 0.0
            di[i] = 1.0
            continue

        # Final upper band: only raise (tighten) if prev close was above it
        fu[i] = bu[i] if (bu[i] > fu[i-1] or closes[i-1] < fu[i-1]) else fu[i-1]
        # Final lower band: only lower (tighten) if prev close was below it
        fl[i] = bl[i] if (bl[i] < fl[i-1] or closes[i-1] > fl[i-1]) else fl[i-1]

        # Direction
        if di[i-1] == -1:
            di[i] = 1.0 if closes[i] > fl[i] else -1.0
        else:
            di[i] = -1.0 if closes[i] < fu[i] else 1.0

    final_upper[:] = fu
    final_lower[:] = fl
    direction[:]   = di

    # ST value = support when bullish, resistance when bearish
    st = pd.Series(np.where(direction == 1, final_upper, final_lower),
                   index=df.index)

    df["ST"]     = st
    df["ST_dir"] = direction.astype(int)
    return df

def rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return float("nan")
    delta = series.diff().dropna()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, float("nan"))
    r     = 100 - (100 / (1 + rs))
    return float(r.iloc[-1]) if not r.empty else float("nan")

def get_10am_price(token: str, exchange: str) -> float:
    try:
        s = get_session()
        if s is None: return float("nan")
        n   = ist_now()
        frm = n.strftime("%Y-%m-%d 09:45")
        to  = n.strftime("%Y-%m-%d 10:15")
        r   = s.getCandleData({"exchange": exchange, "symboltoken": token,
                               "interval": "FIVE_MINUTE",
                               "fromdate": frm, "todate": to})
        if r and r.get("status") and r["data"]:
            return float(r["data"][0][4])
    except Exception:
        pass
    return float("nan")

def token_for(symbol: str) -> str | None:
    try:
        inst = load_instruments()
        if inst.empty: return None
        row = inst[inst["clean"] == symbol.upper()]
        return str(row["token"].iloc[0]) if not row.empty else None
    except Exception:
        return None

@st.cache_data(ttl=86400, show_spinner=False)
def load_instruments() -> pd.DataFrame:
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        r = requests.get(url, timeout=15)
        df = pd.DataFrame(r.json())
        df = df[df["exch_seg"] == "NSE"]
        df["clean"] = df["name"].str.upper().str.strip()
        return df[["token","symbol","name","clean","lotsize"]]
    except Exception:
        return pd.DataFrame()
