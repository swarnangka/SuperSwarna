"""
Parabolic Trends — market web data
NSE gainers/losers, Nifty50 heatmap.
Uses parallel fetch from data_layer.
"""
import streamlit as st
import pandas as pd
import yfinance as yf
from data_layer import fetch_yf_parallel

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
    "BAJAJ-AUTO":"BAJAJ-AUTO.NS","SHREECEM":"SHREECEM.NS",
    "UPL":"UPL.NS","WIPRO":"WIPRO.NS","ZOMATO":"ZOMATO.NS",
}

SECTOR_SYMS = {
    "IT":          "^CNXIT",
    "Bank":        "^NSEBANK",
    "Pharma":      "^CNXPHARMA",
    "FMCG":        "CNXFMCG.NS",
    "Metal":       "CNXMETAL.NS",
    "Auto":        "CNXAUTO.NS",
    "Energy":      "CNXENERGY.NS",
    "Realty":      "CNXREALTY.NS",
    "Media":       "CNXMEDIA.NS",
    "PSU Bank":    "CNXPSUBANK.NS",
    "Infra":       "CNXINFRA.NS",
    "Fin Service": "CNXFINANCE.NS",
    "Healthcare":  "CNXHEALTH.NS",
    "Cons Durbl":  "CNXCONSDUR.NS",
    "MidCap":      "NIFTY_MIDCAP_100.NS",
    "Mid+Sml":     "NIFTY_MIDSML_400.NS",
}


def nifty50() -> pd.DataFrame:
    return pd.DataFrame()  # placeholder


def advance_decline(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"adv": 0, "dec": 0, "total": 0}
    adv = int((df["Chg %"] > 0).sum()) if "Chg %" in df.columns else 0
    dec = int((df["Chg %"] < 0).sum()) if "Chg %" in df.columns else 0
    return {"adv": adv, "dec": dec, "total": adv + dec}


@st.cache_data(ttl=900, show_spinner=False)
def nifty50_heatmap_yf() -> pd.DataFrame:
    """Fetch Nifty 50 stocks in parallel — 900s cache."""
    results = fetch_yf_parallel(NIFTY50_SYMS, period="2d", max_workers=12)
    rows = []
    for name, val in results.items():
        if val:
            rows.append({"Symbol": name, "Chg %": round(val["chg"], 2)})
    return pd.DataFrame(rows)


@st.cache_data(ttl=900, show_spinner=False)
def sector_heatmap_yf() -> pd.DataFrame:
    """Fetch sector indices in parallel — 900s cache."""
    results = fetch_yf_parallel(SECTOR_SYMS, period="2d", max_workers=8)
    rows = []
    for name in SECTOR_SYMS:  # preserve order
        val = results.get(name)
        rows.append({"Symbol": name,
                     "Chg %": round(val["chg"], 2) if val else None})
    return pd.DataFrame(rows)


@st.cache_data(ttl=900, show_spinner=False)
def gainers_losers(top_n: int = 10) -> dict:
    """Top gainers and losers from Nifty 50 heatmap."""
    df = nifty50_heatmap_yf()
    if df.empty:
        return {"gainers": pd.DataFrame(), "losers": pd.DataFrame()}
    df_sorted = df.dropna().sort_values("Chg %", ascending=False)
    return {
        "gainers": df_sorted.head(top_n).reset_index(drop=True),
        "losers":  df_sorted.tail(top_n).iloc[::-1].reset_index(drop=True),
    }
