"""
Parabolic Trends — HHLL Commodity Signal Engine
Exact Pine Script translation. reverse=True.
Returns signal timestamp (when signal ACTUALLY triggered), price at signal, elapsed time.
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

COMMODITIES = {
    "Gold":   {"sym": "GC=F", "unit": "USD/oz"},
    "Silver": {"sym": "SI=F", "unit": "USD/oz"},
    "Copper": {"sym": "HG=F", "unit": "USD/lb"},
}


def _download_ohlcv(symbol: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, period="60d", interval=interval,
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df[["Open","High","Low","Close","Volume"]].dropna()
        # Remove duplicate index entries (known yfinance issue with CME futures)
        df = df[~df.index.duplicated(keep="last")]
        return df.sort_index()
    except Exception:
        return pd.DataFrame()


def _resample_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    if df_1h.empty:
        return pd.DataFrame()
    try:
        return df_1h.resample("4h").agg({
            "Open":"first","High":"max","Low":"min",
            "Close":"last","Volume":"sum"
        }).dropna()
    except Exception:
        return pd.DataFrame()


def _hhll_signal(df: pd.DataFrame, period: int = 29) -> dict:
    """
    Compute HHLL signal with exact trigger bar info.
    Returns: signal, price, upper, lower, crossed,
             signal_time (IST str), signal_price, elapsed_str
    """
    empty = {"signal":"NO DATA","price":None,"upper":None,"lower":None,
             "crossed":"","signal_time":"—","signal_price":None,"elapsed":"—"}
    if df.empty or len(df) < period + 2:
        return empty

    df = df.copy()
    df["HH"] = df["High"].rolling(period).mean()
    df["LL"] = df["Low"].rolling(period).mean()
    df["offset"] = (df["HH"] - df["LL"]) / 2
    df["upper"] = df["HH"] + df["offset"]
    df["lower"] = df["LL"] - df["offset"]
    df = df.dropna()
    if len(df) < 2:
        return empty

    # Compute signal for each bar
    signals = ["NEUTRAL"] * len(df)
    for i in range(1, len(df)):
        if df["High"].iloc[i] > df["upper"].iloc[i-1]:
            signals[i] = "LONG"
        elif df["Low"].iloc[i] < df["lower"].iloc[i-1]:
            signals[i] = "SHORT"
        else:
            signals[i] = signals[i-1]  # carry forward

    curr_sig = signals[-1]
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    # Find when current signal started (scan backwards)
    flip_idx = len(signals) - 1
    for i in range(len(signals) - 2, -1, -1):
        if signals[i] != curr_sig:
            flip_idx = i + 1
            break
        if i == 0:
            flip_idx = 0

    # Signal bar info
    flip_bar = df.iloc[flip_idx]
    sig_price = float(flip_bar["Close"])
    sig_dt_raw = df.index[flip_idx]

    # Convert to IST
    try:
        if hasattr(sig_dt_raw, "tzinfo") and sig_dt_raw.tzinfo is not None:
            sig_dt_ist = sig_dt_raw.astimezone(IST)
        else:
            sig_dt_ist = sig_dt_raw.replace(tzinfo=timezone.utc).astimezone(IST)
        sig_time_str = sig_dt_ist.strftime("%d %b · %H:%M IST")
        # Elapsed
        now_ist = datetime.now(IST)
        delta = now_ist - sig_dt_ist
        total_h = int(delta.total_seconds() // 3600)
        days = total_h // 24
        hrs  = total_h % 24
        if days > 0:
            elapsed = f"{days}d {hrs}h ago"
        else:
            elapsed = f"{hrs}h ago"
    except Exception:
        sig_time_str = str(sig_dt_raw)[:16]
        elapsed = "—"

    # Current bar data
    price  = float(curr["Close"])
    upper  = float(curr["upper"])
    lower  = float(curr["lower"])
    p_upper = float(prev["upper"])
    p_lower = float(prev["lower"])

    crossed = ""
    if curr_sig == "LONG":
        crossed = f"High > upper ▲"
    elif curr_sig == "SHORT":
        crossed = f"Low < lower ▼"

    return {
        "signal": curr_sig,
        "price": price,
        "upper": upper,
        "lower": lower,
        "crossed": crossed,
        "signal_time": sig_time_str,
        "signal_price": sig_price,
        "elapsed": elapsed,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def get_hhll_signals() -> dict:
    results = {}
    for name, info in COMMODITIES.items():
        df_1h = _download_ohlcv(info["sym"], "1h")
        df_4h = _resample_4h(df_1h)
        results[name] = {
            "unit": info["sym"],
            "display_unit": info["unit"],
            "1H": _hhll_signal(df_1h, 29),
            "4H": _hhll_signal(df_4h, 29),
        }
    return results
