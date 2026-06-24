"""
Parabolic Trends — HHLL Commodity Signal Engine
Pine Script translated to Python exactly:
  HH = SMA(high, 29), LL = SMA(low, 29)
  offset = (HH - LL) / 2
  upper = HH + offset, lower = LL - offset
  reverse = True (as per original script)
  BUY  = price crossed below lower (reverse flips: cross above upper = LONG)
  SELL = price crossed above upper (reverse flips: cross below lower = SHORT)
Symbols: GC=F (Gold), SI=F (Silver), HG=F (Copper) — USD, authentic CME futures
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

COMMODITIES = {
    "Gold":   {"sym": "GC=F", "unit": "USD/oz"},
    "Silver": {"sym": "SI=F", "unit": "USD/oz"},
    "Copper": {"sym": "HG=F", "unit": "USD/lb"},
}


def _download_ohlcv(symbol: str, interval: str, period: str = "60d") -> pd.DataFrame:
    try:
        df = yf.download(symbol, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        return df[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def _resample_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    if df_1h.empty:
        return pd.DataFrame()
    try:
        df = df_1h.resample("4h").agg({
            "Open":  "first", "High": "max",
            "Low":   "min",   "Close": "last", "Volume": "sum"
        }).dropna()
        return df
    except Exception:
        return pd.DataFrame()


def _hhll_signal(df: pd.DataFrame, period: int = 29) -> dict:
    """Compute HHLL signal. reverse=True as in Pine Script."""
    if df.empty or len(df) < period + 2:
        return {"signal": "NO DATA", "price": None, "upper": None, "lower": None, "crossed": ""}
    df = df.copy()
    df["HH"] = df["High"].rolling(period).mean()
    df["LL"] = df["Low"].rolling(period).mean()
    df["offset"] = (df["HH"] - df["LL"]) / 2
    df["upper"] = df["HH"] + df["offset"]
    df["lower"] = df["LL"] - df["offset"]
    df = df.dropna()
    if len(df) < 2:
        return {"signal": "NO DATA", "price": None, "upper": None, "lower": None, "crossed": ""}

    curr = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(curr["Close"])
    upper = float(curr["upper"])
    lower = float(curr["lower"])
    prev_upper = float(prev["upper"])
    prev_lower = float(prev["lower"])

    # Pine: pos=1 if low < LLM[1] (bullish), pos=-1 if high > HHM[1] (bearish)
    # reverse=True flips: possig=-1 when pos=1, possig=1 when pos=-1
    # Net effect: LONG when high > upper[1], SHORT when low < lower[1]
    raw_signal = "NEUTRAL"
    crossed = "Inside bands"
    if curr["High"] > prev_upper:
        raw_signal = "LONG"
        crossed = f"High crossed upper ▲"
    elif curr["Low"] < prev_lower:
        raw_signal = "SHORT"
        crossed = f"Low crossed lower ▼"

    return {
        "signal": raw_signal, "price": price,
        "upper": upper, "lower": lower, "crossed": crossed
    }


@st.cache_data(ttl=1800, show_spinner=False)
def get_hhll_signals() -> dict:
    """Returns signals for all commodities across 1H and 4H."""
    results = {}
    for name, info in COMMODITIES.items():
        df_1h = _download_ohlcv(info["sym"], "1h", "60d")
        df_4h = _resample_4h(df_1h)
        results[name] = {
            "unit":   info["sym"],
            "display_unit": info["unit"],
            "1H": _hhll_signal(df_1h, 29),
            "4H": _hhll_signal(df_4h, 29),
        }
    return results
