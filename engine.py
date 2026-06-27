"""
Parabolic Trends — engine v3
Swarna Risk: weighted score out of 11 → LOW / MODERATE / HIGH
Supertrend signal date: scans candle history for last flip
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
from data_layer import (
    add_mas, supertrend, rsi, get_candles, token_for, get_ltp,
    get_10am_price, fetch_yf, load_instruments, INDEX_TOKENS
)

FNO_STOCKS = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC","SBIN",
    "BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI","TITAN",
    "SUNPHARMA","BAJFINANCE","HCLTECH","WIPRO","ULTRACEMCO","NESTLEIND","NTPC",
    "POWERGRID","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS",
    "COALINDIA","ONGC","GRASIM","HINDALCO","CIPLA","DRREDDY","DIVISLAB",
    "BAJAJFINSV","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","BRITANNIA","TECHM",
    "INDUSINDBK","BPCL","IOC","SHREECEM","UPL","APOLLOHOSP","TATACONSUM",
    "PIDILITIND","DABUR","GODREJCP","HAVELLS","DLF","SIEMENS","PNB",
    "BANKBARODA","CANBK","FEDERALBNK","IDFCFIRSTB","BANDHANBNK","AUBANK",
    "ZOMATO","DMART","TRENT","NAUKRI","INDIGO","VEDL","SAIL","NMDC",
    "BEL","HAL","BHEL","IRCTC","GAIL","PETRONET","TORNTPHARM","LUPIN",
    "AUROPHARMA","BIOCON","COLPAL","MARICO","BERGEPAINT","AMBUJACEM","ACC",
    "MOTHERSON","BOSCHLTD","BALKRISIND","CUMMINSIND","ABB","PFC","RECLTD",
    "IRFC","JINDALSTEL","TVSMOTOR","CHOLAFIN","SHRIRAMFIN","MUTHOOTFIN",
    "ICICIGI","ICICIPRULI","SBILIFE","HDFCLIFE","INDUSTOWER",
    "PERSISTENT","COFORGE","MPHASIS","TATAPOWER","ADANIGREEN",
]

# ── Weighted criteria definition ───────────────────────────────────────────────
# Weight rationale (total = 11):
#   200DMA trending up  = 2  (bedrock of Stage 2 — most critical)
#   Price > 150 & 200   = 2  (confirms Stage 2 entry)
#   Within 25% of 52WH  = 2  (relative strength proxy — institutional demand)
#   50DMA > 150 & 200   = 1.5 (MA alignment across timeframes)
#   Price > 50DMA       = 1.5 (short-term trend confirmation)
#   ≥30% above 52WL     = 1  (momentum, but passes easily in bull markets)
#   150DMA > 200DMA     = 1  (structural but derivative of above)

CRITERIA_WEIGHTS = [2, 2, 2, 1.5, 1.5, 1, 1]
MAX_SCORE = sum(CRITERIA_WEIGHTS)  # 11


def _risk_level(score: float) -> tuple:
    """Returns (level, color) for a weighted score out of 11."""
    pct = score / MAX_SCORE
    if pct >= 0.72:   return "LOW",      "#2EC4A0"   # green
    if pct >= 0.45:   return "MODERATE", "#D29922"   # amber
    return             "HIGH",     "#F85149"   # red


def _supertrend_since(df: pd.DataFrame) -> tuple:
    """
    Scan backwards to find when current Supertrend direction started.
    Returns (direction_str, date_str, calendar_days_ago, price_at_signal)
    
    Uses CALENDAR DAYS via datetime arithmetic on the SAME flip_date object.
    Handles tz-naive pandas Timestamps safely.
    """
    if df.empty or "ST_dir" not in df.columns or len(df) < 3:
        return "—", "—", 0, None

    dirs   = df["ST_dir"].values
    closes = df["Close"].values
    dates  = df.index

    current_dir = int(dirs[-1])

    # Walk backwards to find the last flip
    flip_idx = 0
    for i in range(len(dirs) - 2, -1, -1):
        if int(dirs[i]) != current_dir:
            flip_idx = i + 1
            break

    direction  = "BUY" if current_dir == 1 else "SELL"
    flip_ts    = dates[flip_idx]   # pandas Timestamp
    flip_price = float(closes[flip_idx])

    try:
        # Normalize to a plain date — works for both tz-naive and tz-aware
        if hasattr(flip_ts, "date"):
            flip_date = flip_ts.date()
        else:
            flip_date = pd.Timestamp(flip_ts).date()

        date_str = flip_date.strftime("%d %b %Y")

        # Calendar days: both sides must be plain date objects
        from datetime import timezone as _tz, timedelta as _td, datetime as _dt
        _IST = _tz(_td(hours=5, minutes=30))
        today_date = _dt.now(_IST).date()
        cal_days   = (today_date - flip_date).days
        # Guard against negative (data in future) or absurd values
        if cal_days < 0 or cal_days > 3000:
            cal_days = 0
    except Exception:
        date_str = str(flip_ts)[:10]
        cal_days = 0

    return direction, date_str, cal_days, flip_price


US_INDICES = {
    "S&P 500":  {"yf": "^GSPC", "display": "S&P 500"},
    "Nasdaq":   {"yf": "^IXIC",  "display": "Nasdaq"},
}


def us_index_risk(index_name: str) -> dict:
    """
    Same Swarna weighted risk (out of 11) + Supertrend (10,2) for US indices.
    Pure Yahoo Finance — no Angel One dependency.
    Price format in USD (2 decimal places).
    """
    info = US_INDICES.get(index_name, {})
    if not info:
        return {"index": index_name, "ltp": None}

    df_raw = fetch_yf(info["yf"], period="1y")
    df = add_mas(df_raw)
    if df.empty or len(df) < 50:
        return {"index": index_name, "ltp": None, "chg": None,
                "score": 0, "risk_level": "HIGH", "risk_color": "#F85149",
                "checks": [], "conditions_met": 0, "total_conditions": 7,
                "st_date": "—", "st_bars": 0, "st_price": None,
                "pct_200": 0, "data_src": "Yahoo Finance", "last_bar": "—"}

    df = supertrend(df, 10, 2.0)

    r      = df.iloc[-1]
    price  = float(r["Close"])
    ma50   = float(r["MA50"])
    ma150  = float(r["MA150"])
    ma200  = float(r["MA200"])
    ma200_1m = float(r["MA200_1M"]) if not np.isnan(r.get("MA200_1M", float("nan"))) else ma200
    lo52   = float(r["52WL"])
    hi52   = float(r["52WH"])

    raw = [
        (ma200 > ma200_1m,
         "200 DMA trending up (1M)", 2,
         f"200DMA {ma200:,.2f} vs 1M ago {ma200_1m:,.2f} ({(ma200-ma200_1m)/ma200_1m*100:+.1f}%)"),
        (price > ma150 and price > ma200,
         "Price above 150 & 200 DMA", 2,
         f"Price {price:,.2f} | 150DMA {ma150:,.2f} | 200DMA {ma200:,.2f}"),
        (price >= hi52 * 0.75,
         "Within 25% of 52-week high", 2,
         f"Price {price:,.2f} | 52W High {hi52:,.2f} ({(price-hi52)/hi52*100:+.1f}%)"),
        (ma50 > ma150 and ma50 > ma200,
         "50 DMA above 150 & 200 DMA", 1.5,
         f"50DMA {ma50:,.2f} | 150DMA {ma150:,.2f} | 200DMA {ma200:,.2f}"),
        (price > ma50,
         "Price above 50 DMA", 1.5,
         f"Price {price:,.2f} | 50DMA {ma50:,.2f}"),
        (price >= lo52 * 1.30,
         "≥30% above 52-week low", 1,
         f"Price {price:,.2f} | 52W Low {lo52:,.2f} ({(price-lo52)/lo52*100:+.0f}%)"),
        (ma150 > ma200,
         "150 DMA above 200 DMA", 1,
         f"150DMA {ma150:,.2f} | 200DMA {ma200:,.2f}"),
    ]

    checks = []
    score  = 0.0
    for passed, label, weight, detail in raw:
        checks.append({"pass": passed, "label": label,
                       "weight": weight, "detail": detail})
        if passed:
            score += weight

    conditions_met = sum(1 for c in checks if c["pass"])
    risk_level, risk_color = _risk_level(score)
    st_on = int(r["ST_dir"]) == 1

    st_since, st_date, st_bars, st_price = _supertrend_since(df)

    prev     = float(df["Close"].iloc[-2])
    chg      = (price - prev) / prev * 100
    chg_pts  = price - prev
    pct_200  = (price - ma200) / ma200 * 100

    try:
        last_bar_str = pd.Timestamp(df.index[-1]).strftime("%d %b %Y")
    except Exception:
        last_bar_str = "—"

    return {
        "index":          index_name,
        "display":        info["display"],
        "supertrend":     st_on,
        "ltp":            price,
        "chg":            chg,
        "chg_pts":        chg_pts,
        "price":          price,
        "ma200":          ma200,
        "pct_200":        pct_200,
        "score":          score,
        "max_score":      MAX_SCORE,
        "risk_level":     risk_level,
        "risk_color":     risk_color,
        "checks":         checks,
        "conditions_met": conditions_met,
        "total_conditions": 7,
        "st_since":       st_since,
        "st_date":        st_date,
        "st_bars":        st_bars,
        "st_price":       st_price,
        "data_src":       "Yahoo Finance",
        "last_bar":       last_bar_str,
    }


    """
    Fetch daily OHLCV for an index.
    Returns (DataFrame, data_source_str).
    Angel One preferred; yfinance fallback with 1y period.
    """
    info = INDEX_TOKENS[index_name]
    df = get_candles(info["token"], info["exchange"], "ONE_DAY", days=400)
    if not df.empty and len(df) > 50:
        # Validate data is recent (last bar within 5 days)
        import pandas as pd
        last_date = df.index[-1]
        from datetime import timezone, timedelta, datetime
        IST = timezone(timedelta(hours=5, minutes=30))
        days_old = (datetime.now(IST).date() - pd.Timestamp(last_date).date()).days
        if days_old <= 5:
            return df, "Angel One"
    # Fallback to Yahoo Finance — use 1y to match TV's default lookback
    df_yf = fetch_yf(info["yf"], period="1y")
    if not df_yf.empty:
        return df_yf, "Yahoo Finance"
    return df if not df.empty else df_yf, "Unknown"


def get_index_history(index_name: str) -> tuple:
    """
    Fetch daily OHLCV for an Indian index.
    Returns (DataFrame, data_source_str).
    Angel One preferred; yfinance 1y fallback.
    """
    info = INDEX_TOKENS[index_name]
    df = get_candles(info["token"], info["exchange"], "ONE_DAY", days=400)
    if not df.empty and len(df) > 50:
        from datetime import timezone, timedelta, datetime as _dt
        _IST = timezone(timedelta(hours=5, minutes=30))
        days_old = (_dt.now(_IST).date() - pd.Timestamp(df.index[-1]).date()).days
        if days_old <= 5:
            return df, "Angel One"
    df_yf = fetch_yf(info["yf"], period="1y")
    if not df_yf.empty:
        return df_yf, "Yahoo Finance"
    return df if not df.empty else df_yf, "Unknown"


def index_risk(index_name: str) -> dict:
    """
    Swarna weighted risk score (out of 11) + Supertrend direction + signal date.
    Risk levels: LOW (≥8), MODERATE (5-7), HIGH (0-4).
    Supertrend: period=10, factor=2.0 — matches TradingView 'Supertrend 10 hl2 2'.
    """
    df_raw, data_src = get_index_history(index_name)
    df = add_mas(df_raw)
    if df.empty or len(df) < 50:
        return {"index": index_name, "minervini": None, "supertrend": None,
                "ltp": None, "chg": None, "chg_pts": None, "checks": [],
                "score": 0, "risk_level": "HIGH", "risk_color": "#F85149",
                "st_since": "—", "st_date": "—", "st_bars": 0, "st_price": None,
                "conditions_met": 0, "total_conditions": 7, "pct_200": 0,
                "data_src": data_src}

    df = supertrend(df, 10, 2.0)   # factor=2.0 — TradingView 'Supertrend 10 hl2 2'

    r = df.iloc[-1]
    price  = float(r["Close"])
    ma50   = float(r["MA50"])
    ma150  = float(r["MA150"])
    ma200  = float(r["MA200"])
    ma200_1m = float(r["MA200_1M"]) if not np.isnan(r.get("MA200_1M", float("nan"))) else ma200
    lo52   = float(r["52WL"])
    hi52   = float(r["52WH"])

    # 7 criteria with weights
    raw = [
        # (pass, label, weight, detail)
        (ma200 > ma200_1m,
         "200 DMA trending up (1M)",  2,
         f"200DMA {ma200:,.0f} vs 1M ago {ma200_1m:,.0f} ({(ma200-ma200_1m)/ma200_1m*100:+.1f}%)"),
        (price > ma150 and price > ma200,
         "Price above 150 & 200 DMA", 2,
         f"Price {price:,.0f} | 150DMA {ma150:,.0f} | 200DMA {ma200:,.0f}"),
        (price >= hi52 * 0.75,
         "Within 25% of 52-week high", 2,
         f"Price {price:,.0f} | 52W High {hi52:,.0f} ({(price-hi52)/hi52*100:+.1f}%)"),
        (ma50 > ma150 and ma50 > ma200,
         "50 DMA above 150 & 200 DMA", 1.5,
         f"50DMA {ma50:,.0f} | 150DMA {ma150:,.0f} | 200DMA {ma200:,.0f}"),
        (price > ma50,
         "Price above 50 DMA", 1.5,
         f"Price {price:,.0f} | 50DMA {ma50:,.0f}"),
        (price >= lo52 * 1.30,
         "≥30% above 52-week low", 1,
         f"Price {price:,.0f} | 52W Low {lo52:,.0f} ({(price-lo52)/lo52*100:+.0f}%)"),
        (ma150 > ma200,
         "150 DMA above 200 DMA", 1,
         f"150DMA {ma150:,.0f} | 200DMA {ma200:,.0f}"),
    ]

    checks = []
    score = 0.0
    for passed, label, weight, detail in raw:
        checks.append({"pass": passed, "label": label,
                       "weight": weight, "detail": detail})
        if passed:
            score += weight

    conditions_met = sum(1 for c in checks if c["pass"])
    risk_level, risk_color = _risk_level(score)
    st_on = int(r["ST_dir"]) == 1

    # Supertrend signal date
    st_since, st_date, st_bars, st_price = _supertrend_since(df)

    # LTP
    info = INDEX_TOKENS[index_name]
    ltp = get_ltp(index_name, info["token"], info["exchange"])
    if ltp != ltp:
        ltp = price
    prev = float(df["Close"].iloc[-2])
    chg = (ltp - prev) / prev * 100
    chg_pts = ltp - prev
    pct_200 = (price - ma200) / ma200 * 100

    # Data freshness info
    try:
        last_bar_str = pd.Timestamp(df.index[-1]).strftime("%d %b %Y")
    except Exception:
        last_bar_str = str(df.index[-1])[:10]

    return {
        "index": index_name,
        "minervini": conditions_met == 7,
        "supertrend": st_on,
        "ltp": ltp, "chg": chg, "chg_pts": chg_pts,
        "price": price, "ma200": ma200, "pct_200": pct_200,
        "score": score, "max_score": MAX_SCORE,
        "risk_level": risk_level, "risk_color": risk_color,
        "checks": checks,
        "conditions_met": conditions_met, "total_conditions": 7,
        "st_since": st_since, "st_date": st_date,
        "st_bars": st_bars, "st_price": st_price,
        "data_src": data_src, "last_bar": last_bar_str,
    }


def _process_stock(sym, df, st_factor, ref_10am=None):
    if df.empty or len(df) < 60:
        return None
    d = add_mas(df)
    d = supertrend(d, 10, st_factor)
    last = float(d["Close"].iloc[-1])
    prev = float(d["Close"].iloc[-2])
    hi52 = float(d["52WH"].iloc[-1])
    lo52 = float(d["52WL"].iloc[-1])
    chg = (last - prev) / prev * 100
    wk = d["Close"].resample("W").last().dropna()
    mo = d["Close"].resample("ME").last().dropna()
    row = {
        "Symbol": sym, "LTP": round(last, 1), "Chg %": round(chg, 2),
        "Daily RSI": round(rsi(d["Close"], 14), 1) if len(d) > 15 else None,
        "Wkly RSI": round(rsi(wk, 14), 1) if len(wk) > 15 else None,
        "Mnly RSI": round(rsi(mo, 14), 1) if len(mo) > 15 else None,
        "% from 52WH": round((last-hi52)/hi52*100, 1),
        "% from 52WL": round((last-lo52)/lo52*100, 1),
        "Supertrend": "BUY" if int(d["ST_dir"].iloc[-1]) == 1 else "SELL",
    }
    if ref_10am is not None and ref_10am == ref_10am and ref_10am > 0:
        row["vs 10AM %"] = round((last - ref_10am) / ref_10am * 100, 2)
    return row


def scan_fno(stocks, st_factor=2.0, with_10am=True):
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
        time.sleep(0.25)
    progress.empty()
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def get_scan_universe(mode="fno_plus"):
    if mode == "all":
        inst = load_instruments()
        if not inst.empty:
            return inst["clean"].tolist()
    return FNO_STOCKS
