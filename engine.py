"""
SuperSwarna — scoring engine & stock universes
"""
import pandas as pd
import numpy as np
from data_layer import add_mas, supertrend, fetch_yf, rsi

# ── F&O / Nifty universe (NSE tickers for yfinance) ───────────────────────────
# A practical liquid F&O set. Extend freely.
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
    "TORNTPHARM","LUPIN","AUROPHARMA","BIOCON","MCDOWELL-N","COLPAL",
    "MARICO","BERGEPAINT","AMBUJACEM","ACC","MOTHERSON","BOSCHLTD","BALKRISIND",
]

SECTOR_INDICES = {
    "Nifty IT":        "^CNXIT",
    "Nifty Bank":      "^NSEBANK",
    "Nifty Pharma":    "^CNXPHARMA",
    "Nifty FMCG":      "^CNXFMCG",
    "Nifty Metal":     "^CNXMETAL",
    "Nifty Energy":    "^CNXENERGY",
    "Nifty Realty":    "^CNXREALTY",
    "Nifty Media":     "^CNXMEDIA",
    "Nifty PSU Bank":  "^CNXPSUBANK",
    "Nifty Infra":     "^CNXINFRA",
    "Nifty Auto":      "^CNXAUTO",
    "Nifty Fin Svc":   "NIFTY_FIN_SERVICE.NS",
}


import streamlit as st
import time

@st.cache_data(ttl=900, show_spinner=False)
def batch_download(symbols: tuple, period: str = "2y") -> dict:
    """Download many tickers in ONE yfinance call to avoid rate limits.
    Returns dict {symbol: DataFrame}."""
    import yfinance as yf
    out = {}
    syms = list(symbols)
    # chunk into groups of 30 to keep each request reasonable
    for i in range(0, len(syms), 30):
        chunk = syms[i:i+30]
        for attempt in range(3):
            try:
                data = yf.download(chunk, period=period, auto_adjust=True,
                                   progress=False, group_by="ticker", threads=True)
                if data is not None and not data.empty:
                    for s in chunk:
                        try:
                            if len(chunk) == 1:
                                d = data
                            else:
                                d = data[s]
                            d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
                            if not d.empty:
                                out[s] = d
                        except Exception:
                            continue
                    break
            except Exception as e:
                if "Too Many Requests" in str(e) or "Rate limited" in str(e):
                    time.sleep(2 * (attempt + 1))
                    continue
            time.sleep(0.5)
        time.sleep(0.5)  # gap between chunks
    return out


def minervini_score(df: pd.DataFrame, st_dir: int) -> dict:
    """Compute Minervini trend-template risk score (0..max) plus risk band."""
    if df.empty or len(df) < 200:
        return {"score": None, "risk": "NO DATA", "checks": {}, "pct_200": None}
    r = df.iloc[-1]
    price = float(r["Close"])
    ma50, ma150, ma200 = float(r["MA50"]), float(r["MA150"]), float(r["MA200"])
    ma200_1m = float(r["MA200_1M"]) if not np.isnan(r["MA200_1M"]) else ma200
    hi52, lo52 = float(r["52WH"]), float(r["52WL"])

    checks = {}
    score = 0

    # 8 classic Minervini trend template conditions
    c1 = price > ma150 and price > ma200
    checks["Price > 150 & 200 DMA"] = c1; score += 1 if c1 else 0
    c2 = ma150 > ma200
    checks["150 DMA > 200 DMA"] = c2; score += 1 if c2 else 0
    c3 = ma200 > ma200_1m
    checks["200 DMA trending up"] = c3; score += 1 if c3 else 0
    c4 = ma50 > ma150 > ma200
    checks["50 > 150 > 200 (stacked)"] = c4; score += 1 if c4 else 0
    c5 = price > ma50
    checks["Price > 50 DMA"] = c5; score += 1 if c5 else 0
    c6 = price >= lo52 * 1.30
    checks["≥30% above 52W low"] = c6; score += 1 if c6 else 0
    c7 = price >= hi52 * 0.75
    checks["Within 25% of 52W high"] = c7; score += 1 if c7 else 0
    c8 = st_dir == 1
    checks["Supertrend bullish"] = c8; score += 1 if c8 else 0

    pct_200 = (price - ma200) / ma200 * 100

    # Risk banding on 8-point scale
    if score >= 7:
        risk = "LOW"
    elif score >= 4:
        risk = "MODERATE"
    else:
        risk = "HIGH"

    return {"score": score, "max": 8, "risk": risk, "checks": checks,
            "pct_200": pct_200, "price": price,
            "ma50": ma50, "ma200": ma200, "hi52": hi52}


def build_index_card(index_name: str, yf_symbol: str, df=None) -> dict:
    if df is None:
        df = fetch_yf(yf_symbol, period="2y")
    df = add_mas(df)
    df = supertrend(df, 10, 3.0)
    st_dir = int(df["ST_dir"].iloc[-1]) if not df.empty else 0
    mv = minervini_score(df, st_dir)
    mv["st_dir"] = st_dir
    mv["index"] = index_name
    if not df.empty and len(df) >= 2:
        prev = float(df["Close"].iloc[-2])
        last = float(df["Close"].iloc[-1])
        mv["chg_pct"] = (last - prev) / prev * 100
    else:
        mv["chg_pct"] = None
    return mv


def build_all_index_cards() -> dict:
    """Batch-fetch all 4 indices in one call to avoid rate limits."""
    from data_layer import INDEX_TOKENS
    syms = tuple(info["yf"] for info in INDEX_TOKENS.values())
    data = batch_download(syms, period="2y")
    cards = {}
    for idx_name, info in INDEX_TOKENS.items():
        d = data.get(info["yf"], pd.DataFrame())
        cards[idx_name] = build_index_card(idx_name, info["yf"], df=d)
    return cards


def scan_fno_table(stocks: list, st_factor: float = 2.0) -> pd.DataFrame:
    """Build the F&O screener table. st_factor configurable (default 10,2)."""
    symbols = tuple(s + ".NS" for s in stocks)
    data = batch_download(symbols, period="2y")
    rows = []
    for sym in stocks:
        d = data.get(sym + ".NS")
        if d is None or len(d) < 60:
            continue
        try:
            d = add_mas(d)
            d = supertrend(d, 10, st_factor)
            last = float(d["Close"].iloc[-1])
            prev = float(d["Close"].iloc[-2])
            hi52 = float(d["52WH"].iloc[-1])
            chg = (last - prev) / prev * 100
            from_high = (last - hi52) / hi52 * 100
            wk = d["Close"].resample("W").last().dropna()
            mo = d["Close"].resample("ME").last().dropna()
            rsi_w = rsi(wk, 14)
            rsi_m = rsi(mo, 14)
            st_dir = int(d["ST_dir"].iloc[-1])
            rows.append({
                "Symbol": sym,
                "LTP": round(last, 1),
                "Chg %": round(chg, 2),
                "% from 52WH": round(from_high, 1),
                "Wkly RSI": round(rsi_w, 1) if not np.isnan(rsi_w) else None,
                "Mnly RSI": round(rsi_m, 1) if not np.isnan(rsi_m) else None,
                "Supertrend": "BUY" if st_dir == 1 else "SELL",
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


def scan_52w_high(stocks: list, threshold_pct: float = 5.0) -> pd.DataFrame:
    """Stocks within threshold_pct of their 52-week high."""
    symbols = tuple(s + ".NS" for s in stocks)
    data = batch_download(symbols, period="2y")
    rows = []
    for sym in stocks:
        d = data.get(sym + ".NS")
        if d is None or len(d) < 60:
            continue
        try:
            d = add_mas(d)
            last = float(d["Close"].iloc[-1])
            hi52 = float(d["52WH"].iloc[-1])
            from_high = (last - hi52) / hi52 * 100
            if from_high >= -threshold_pct:
                prev = float(d["Close"].iloc[-2])
                rows.append({
                    "Symbol": sym,
                    "LTP": round(last, 1),
                    "Chg %": round((last - prev) / prev * 100, 2),
                    "% from 52WH": round(from_high, 1),
                    "52W High": round(hi52, 1),
                })
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("% from 52WH", ascending=False)
    return df


def sector_strength(period_days: int = 1) -> pd.DataFrame:
    """Relative strength of sector indices over a lookback window."""
    symbols = tuple(SECTOR_INDICES.values())
    data = batch_download(symbols, period="6mo")
    rows = []
    for name, sym in SECTOR_INDICES.items():
        d = data.get(sym)
        if d is None or len(d) < period_days + 1:
            continue
        try:
            last = float(d["Close"].iloc[-1])
            past = float(d["Close"].iloc[-(period_days + 1)])
            ret = (last - past) / past * 100
            rows.append({"Sector": name, "Return %": round(ret, 2)})
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Return %", ascending=False)
    return df
