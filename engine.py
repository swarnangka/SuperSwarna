"""
SuperSwarna — engine v2
Minervini ON/OFF + Supertrend ON/OFF for indices.
F&O screener with 10AM momentum. 52W high/low scans over NSE cash universe.
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
from data_layer import (
    add_mas, supertrend, rsi, get_candles, token_for, get_ltp,
    get_10am_price, fetch_yf, load_instruments, INDEX_TOKENS
)

# Liquid F&O universe (NSE symbols, no suffix)
FNO_STOCKS = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI","TITAN",
    "SUNPHARMA","BAJFINANCE","HCLTECH","WIPRO","ULTRACEMCO","NESTLEIND","NTPC",
    "POWERGRID","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS",
    "COALINDIA","ONGC","GRASIM","HINDALCO","CIPLA","DRREDDY","DIVISLAB",
    "BAJAJFINSV","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","BRITANNIA","TECHM",
    "INDUSINDBK","BPCL","IOC","SHREECEM","UPL","APOLLOHOSP","TATACONSUM",
    "PIDILITIND","DABUR","GODREJCP","HAVELLS","DLF","SIEMENS","PNB",
    "BANKBARODA","CANBK","FEDERALBNK","IDFCFIRSTB","BANDHANBNK","AUBANK",
    "ZOMATO","PAYTM","NYKAA","POLICYBZR","DMART","TRENT","NAUKRI","INDIGO",
    "VEDL","SAIL","NMDC","BEL","HAL","BHEL","IRCTC","GAIL","PETRONET",
    "TORNTPHARM","LUPIN","AUROPHARMA","BIOCON","COLPAL","MARICO","BERGEPAINT",
    "AMBUJACEM","ACC","MOTHERSON","BOSCHLTD","BALKRISIND","CUMMINSIND","ABB",
    "PFC","RECLTD","IRFC","JINDALSTEL","TVSMOTOR","CHOLAFIN","SHRIRAMFIN",
    "MUTHOOTFIN","ICICIGI","ICICIPRULI","SBILIFE","HDFCLIFE","INDUSTOWER",
    "LTIM","PERSISTENT","COFORGE","MPHASIS","TATAPOWER","ADANIGREEN",
]


def get_index_history(index_name: str) -> pd.DataFrame:
    """Daily candles for an index — SmartAPI first, yfinance fallback."""
    info = INDEX_TOKENS[index_name]
    df = get_candles(info["token"], info["exchange"], "ONE_DAY", days=400)
    if df.empty:
        df = fetch_yf(info["yf"], period="2y")
    return df


def index_risk(index_name: str) -> dict:
    """Minervini ON/OFF + Supertrend(10,3) ON/OFF. Binary, no high/med/low."""
    df = add_mas(get_index_history(index_name))
    if df.empty or len(df) < 200:
        return {"index": index_name, "minervini": None, "supertrend": None,
                "ltp": None, "chg": None}
    df = supertrend(df, 10, 3.0)
    r = df.iloc[-1]
    price = float(r["Close"])
    ma50, ma150, ma200 = float(r["MA50"]), float(r["MA150"]), float(r["MA200"])
    ma200_1m = float(r["MA200_1M"]) if not np.isnan(r["MA200_1M"]) else ma200
    lo52, hi52 = float(r["52WL"]), float(r["52WH"])

    # Minervini trend template — ON only if ALL core conditions met
    conditions = [
        price > ma150 and price > ma200,
        ma150 > ma200,
        ma200 > ma200_1m,
        ma50 > ma150 and ma50 > ma200,
        price > ma50,
        price >= lo52 * 1.30,
        price >= hi52 * 0.75,
    ]
    minervini_on = all(conditions)
    st_on = int(r["ST_dir"]) == 1

    info = INDEX_TOKENS[index_name]
    ltp = get_ltp(index_name, info["token"], info["exchange"])
    if ltp != ltp:  # nan
        ltp = price
    prev = float(df["Close"].iloc[-2])
    chg = (ltp - prev) / prev * 100

    return {"index": index_name, "minervini": minervini_on, "supertrend": st_on,
            "ltp": ltp, "chg": chg, "price": price, "ma200": ma200,
            "conditions_met": sum(conditions), "total_conditions": len(conditions)}


def _process_stock(sym: str, df: pd.DataFrame, st_factor: float,
                   ref_10am: float = None) -> dict:
    if df.empty or len(df) < 60:
        return None
    d = add_mas(df)
    d = supertrend(d, 10, st_factor)
    last = float(d["Close"].iloc[-1])
    prev = float(d["Close"].iloc[-2])
    hi52 = float(d["52WH"].iloc[-1])
    lo52 = float(d["52WL"].iloc[-1])
    chg = (last - prev) / prev * 100
    from_high = (last - hi52) / hi52 * 100
    from_low = (last - lo52) / lo52 * 100
    wk = d["Close"].resample("W").last().dropna()
    mo = d["Close"].resample("ME").last().dropna()
    dy = d["Close"]
    row = {
        "Symbol": sym,
        "LTP": round(last, 1),
        "Chg %": round(chg, 2),
        "Daily RSI": round(rsi(dy, 14), 1) if len(dy) > 15 else None,
        "Wkly RSI": round(rsi(wk, 14), 1) if len(wk) > 15 else None,
        "Mnly RSI": round(rsi(mo, 14), 1) if len(mo) > 15 else None,
        "% from 52WH": round(from_high, 1),
        "% from 52WL": round(from_low, 1),
        "Supertrend": "BUY" if int(d["ST_dir"].iloc[-1]) == 1 else "SELL",
    }
    if ref_10am is not None and ref_10am == ref_10am and ref_10am > 0:
        row["vs 10AM %"] = round((last - ref_10am) / ref_10am * 100, 2)
    return row


def scan_fno(stocks: list, st_factor: float = 2.0, with_10am: bool = True) -> pd.DataFrame:
    """F&O screener with daily/weekly/monthly RSI, supertrend, 10AM momentum."""
    rows = []
    progress = st.progress(0.0, text="Scanning F&O stocks…")
    n = len(stocks)
    for i, sym in enumerate(stocks):
        tok = token_for(sym)
        if tok is None:
            progress.progress((i+1)/n); continue
        df = get_candles(tok, "NSE", "ONE_DAY", days=400)
        ref = get_10am_price(tok, "NSE") if with_10am else None
        row = _process_stock(sym, df, st_factor, ref)
        if row:
            rows.append(row)
        progress.progress((i+1)/n, text=f"Scanning… {sym} ({i+1}/{n})")
        time.sleep(0.25)  # respect ~3 req/s rate limit
    progress.empty()
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def get_scan_universe(mode: str = "fno_plus") -> list:
    """Universe for 52W scans. 'all' = full NSE cash; 'fno_plus' = liquid subset."""
    if mode == "all":
        inst = load_instruments()
        if not inst.empty:
            return inst["clean"].tolist()
    return FNO_STOCKS


def scan_52w(stocks: list, kind: str = "high", threshold: float = 3.0,
             max_scan: int = 750) -> pd.DataFrame:
    """Stocks near 52-week high (kind='high') or low (kind='low')."""
    rows = []
    scan_list = stocks[:max_scan]
    n = len(scan_list)
    progress = st.progress(0.0, text=f"Scanning for 52-week {kind}s…")
    for i, sym in enumerate(scan_list):
        tok = token_for(sym)
        if tok is None:
            progress.progress((i+1)/n); continue
        df = get_candles(tok, "NSE", "ONE_DAY", days=400)
        if not df.empty and len(df) >= 60:
            d = add_mas(df)
            last = float(d["Close"].iloc[-1])
            prev = float(d["Close"].iloc[-2])
            hi52 = float(d["52WH"].iloc[-1])
            lo52 = float(d["52WL"].iloc[-1])
            from_high = (last - hi52) / hi52 * 100
            from_low = (last - lo52) / lo52 * 100
            include = (kind == "high" and from_high >= -threshold) or \
                      (kind == "low" and from_low <= threshold)
            if include:
                rows.append({
                    "Symbol": sym, "LTP": round(last, 1),
                    "Chg %": round((last-prev)/prev*100, 2),
                    "% from 52WH": round(from_high, 1),
                    "% from 52WL": round(from_low, 1),
                    "52W High": round(hi52, 1), "52W Low": round(lo52, 1),
                })
        progress.progress((i+1)/n, text=f"Scanning {kind}s… ({i+1}/{n})")
        time.sleep(0.25)
    progress.empty()
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("% from 52WH", ascending=(kind == "low"))
    return df
