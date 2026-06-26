"""
Parabolic Trends — market web data
Nifty50 heatmap, sector heatmap, gainers/losers.
File-based persistence for last session data — survives app restarts.
"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

IST = timezone(timedelta(hours=5, minutes=30))
CACHE_DIR = "/tmp/parabolic_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

NIFTY50_SYMS = {
    "RELIANCE":"RELIANCE.NS","TCS":"TCS.NS","HDFCBANK":"HDFCBANK.NS",
    "INFY":"INFY.NS","ICICIBANK":"ICICIBANK.NS","HINDUNILVR":"HINDUNILVR.NS",
    "ITC":"ITC.NS","SBIN":"SBIN.NS","BHARTIARTL":"BHARTIARTL.NS",
    "KOTAKBANK":"KOTAKBANK.NS","LT":"LT.NS","AXISBANK":"AXISBANK.NS",
    "ASIANPAINT":"ASIANPAINT.NS","MARUTI":"MARUTI.NS","TITAN":"TITAN.NS",
    "SUNPHARMA":"SUNPHARMA.NS","BAJFINANCE":"BAJFINANCE.NS",
    "HCLTECH":"HCLTECH.NS","WIPRO":"WIPRO.NS","ULTRACEMCO":"ULTRACEMCO.NS",
    "NESTLEIND":"NESTLEIND.NS","NTPC":"NTPC.NS","POWERGRID":"POWERGRID.NS",
    "TATASTEEL":"TATASTEEL.NS","JSWSTEEL":"JSWSTEEL.NS","ADANIENT":"ADANIENT.NS",
    "ADANIPORTS":"ADANIPORTS.NS","COALINDIA":"COALINDIA.NS","ONGC":"ONGC.NS",
    "GRASIM":"GRASIM.NS","HINDALCO":"HINDALCO.NS","CIPLA":"CIPLA.NS",
    "DRREDDY":"DRREDDY.NS","DIVISLAB":"DIVISLAB.NS","BAJAJFINSV":"BAJAJFINSV.NS",
    "HEROMOTOCO":"HEROMOTOCO.NS","EICHERMOT":"EICHERMOT.NS",
    "BRITANNIA":"BRITANNIA.NS","TECHM":"TECHM.NS","INDUSINDBK":"INDUSINDBK.NS",
    "BPCL":"BPCL.NS","IOC":"IOC.NS","APOLLOHOSP":"APOLLOHOSP.NS",
    "TATACONSUM":"TATACONSUM.NS","TRENT":"TRENT.NS",
    "BAJAJ-AUTO":"BAJAJ-AUTO.NS","ZOMATO":"ZOMATO.BO",
    "SHREECEM":"SHREECEM.NS","UPL":"UPL.NS",
}

SECTOR_SYMS = {
    "IT":          "^CNXIT",
    "Bank":        "^NSEBANK",
    "Pharma":      "^CNXPHARMA",
    "FMCG":        "^CNXFMCG",
    "Metal":       "^CNXMETAL",
    "Auto":        "^CNXAUTO",
    "Energy":      "^CNXENERGY",
    "Realty":      "^CNXREALTY",
    "Media":       "^CNXMEDIA",
    "PSU Bank":    "^CNXPSUBANK",
    "Infra":       "^CNXINFRA",
    "Fin Service": "^CNXFINANCE",
    "Healthcare":  "^CNXHEALTH",
    "Cons Durbl":  "^CNXCONSDUR",
    "MidCap":      "NIFTY_MIDCAP_100.NS",
    "MidSmCap":    "NIFTY_MIDSMCAP_400.NS",
}


def _fetch_parallel(symbols: dict, period: str = "2d", max_workers: int = 10) -> dict:
    def _one(name, sym):
        try:
            df = yf.download(sym, period=period, auto_adjust=True,
                             progress=False, timeout=8)
            if df is None or df.empty: return name, None
            df.columns = [c[0] if isinstance(c,tuple) else c for c in df.columns]
            df = df.dropna()
            if len(df) < 2: return name, None
            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            return name, {"last": round(last,4), "chg": round((last-prev)/prev*100,4)}
        except Exception:
            return name, None
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_one, n, s): n for n,s in symbols.items()}
        for fut in as_completed(futs, timeout=20):
            try:
                n, v = fut.result(); results[n] = v
            except Exception:
                results[futs[fut]] = None
    for n in symbols:
        if n not in results: results[n] = None
    return results


# ── File persistence helpers ───────────────────────────────────────────────────
def _save_cache(key: str, data: list, label: str):
    """Save data list to disk with metadata."""
    try:
        payload = {
            "data": data,
            "label": label,
            "saved_at": datetime.now(IST).strftime("%d %b · %H:%M IST"),
        }
        with open(f"{CACHE_DIR}/{key}.json", "w") as f:
            json.dump(payload, f)
    except Exception:
        pass


def _load_cache(key: str) -> tuple:
    """Load cached data. Returns (data_list, label, saved_at) or (None, None, None)."""
    try:
        path = f"{CACHE_DIR}/{key}.json"
        if not os.path.exists(path):
            return None, None, None
        with open(path) as f:
            payload = json.load(f)
        return payload["data"], payload.get("label",""), payload.get("saved_at","")
    except Exception:
        return None, None, None


def _has_meaningful_data(rows: list) -> bool:
    """True if at least half the rows have a non-None chg value."""
    if not rows: return False
    valid = sum(1 for r in rows if r.get("Chg %") is not None)
    return valid >= len(rows) * 0.5


# ── Public functions ────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def nifty50_heatmap_yf() -> tuple:
    """
    Returns (DataFrame, source_label).
    Tries live fetch first. Falls back to file cache if live returns empty.
    """
    results = _fetch_parallel(NIFTY50_SYMS, period="2d", max_workers=12)
    rows = []
    for name in NIFTY50_SYMS:
        val = results.get(name)
        rows.append({"Symbol": name, "Chg %": round(val["chg"],2) if val else None})

    if _has_meaningful_data(rows):
        df = pd.DataFrame(rows)
        _save_cache("nifty50_heat", rows, "Live")
        return df, "Live"

    # Fallback to file cache
    cached, lbl, saved_at = _load_cache("nifty50_heat")
    if cached:
        return pd.DataFrame(cached), f"Last session · {saved_at}"

    return pd.DataFrame(rows), "No data"


@st.cache_data(ttl=900, show_spinner=False)
def sector_heatmap_yf() -> tuple:
    """Returns (DataFrame, source_label). Same persistence pattern."""
    results = _fetch_parallel(SECTOR_SYMS, period="2d", max_workers=8)
    rows = []
    for name in SECTOR_SYMS:
        val = results.get(name)
        rows.append({"Symbol": name, "Chg %": round(val["chg"],2) if val else None})

    if _has_meaningful_data(rows):
        df = pd.DataFrame(rows)
        _save_cache("sector_heat", rows, "Live")
        return df, "Live"

    cached, lbl, saved_at = _load_cache("sector_heat")
    if cached:
        return pd.DataFrame(cached), f"Last session · {saved_at}"

    return pd.DataFrame(rows), "No data"


@st.cache_data(ttl=900, show_spinner=False)
def gainers_losers(top_n: int = 10) -> dict:
    """Top gainers and losers. Uses heatmap data (already cached)."""
    df, _ = nifty50_heatmap_yf()
    if df.empty:
        return {"gainers": pd.DataFrame(), "losers": pd.DataFrame()}
    df_sorted = df.dropna(subset=["Chg %"]).sort_values("Chg %", ascending=False)
    return {
        "gainers": df_sorted.head(top_n).reset_index(drop=True),
        "losers":  df_sorted.tail(top_n).iloc[::-1].reset_index(drop=True),
    }
