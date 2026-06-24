"""
Parabolic Trends — F&O Ban List + Possible Entrants
Source: NSE Clearing daily CSV (nsearchives.nseindia.com/content/fo/fo_secban.csv)
This is the exact same authoritative source used by all brokers and StockeZee.
MWPL data from NSE combineoi CSV for possible entrants.
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from io import StringIO

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
HEADERS = {"User-Agent": UA, "Referer": "https://www.nseindia.com/"}

BAN_CSV_URL     = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"
MWPL_BASE_URL   = "https://nsearchives.nseindia.com/content/nsccl/combineoi_deleq_{}.csv"


def _get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get("https://www.nseindia.com", timeout=8)
    except Exception:
        pass
    return s


@st.cache_data(ttl=3600, show_spinner=False)
def fno_ban_mwpl() -> dict:
    out = {"banned": pd.DataFrame(), "entrants": pd.DataFrame(), "asof": ""}
    s = _get_session()

    # ── Ban list from NSE Clearing CSV ────────────────────────────────────────
    try:
        r = s.get(BAN_CSV_URL, timeout=12)
        if r.status_code == 200 and len(r.text) > 10:
            lines = [l.strip() for l in r.text.strip().split("\n") if l.strip()]
            # Format: "Securities in Ban For Trade Date DD-MON-YYYY: 1,SYM1\n2,SYM2..."
            # Or just: "SYM1\nSYM2" or comma-separated
            banned_syms = []
            trade_date  = ""
            for line in lines:
                if "ban" in line.lower() and "date" in line.lower():
                    # Extract date
                    import re
                    m = re.search(r'\d{2}-[A-Z]{3}-\d{4}', line)
                    if m:
                        trade_date = m.group()
                    continue
                # Remove numbering like "1," or "2,"
                parts = line.split(",")
                for p in parts:
                    sym = p.strip()
                    if sym and not sym.isdigit() and len(sym) > 1:
                        banned_syms.append(sym)
            if banned_syms:
                out["banned"] = pd.DataFrame({"Symbol": banned_syms, "Status": "IN BAN"})
                out["asof"] = trade_date or date.today().strftime("%d %b %Y")
    except Exception:
        pass

    # ── MWPL data for possible entrants ───────────────────────────────────────
    try:
        ddmmyyyy = date.today().strftime("%d%m%Y")
        url = MWPL_BASE_URL.format(ddmmyyyy)
        r = s.get(url, timeout=12)
        if r.status_code == 200 and len(r.text) > 200:
            df = pd.read_csv(StringIO(r.text))
            df.columns = [c.strip() for c in df.columns]
            # Find symbol and MWPL% columns flexibly
            sym_col = next((c for c in df.columns if c.lower() in
                           ("symbol","underlying","scrip","security")), None)
            pct_col = next((c for c in df.columns if
                           "%" in c or "mwpl" in c.lower() or "limit" in c.lower()), None)
            if sym_col and pct_col:
                df = df[[sym_col, pct_col]].copy()
                df.columns = ["Symbol", "MWPL %"]
                df["MWPL %"] = pd.to_numeric(df["MWPL %"], errors="coerce")
                df = df.dropna()
                entrants = df[(df["MWPL %"] >= 80) & (df["MWPL %"] < 95)]\
                    .sort_values("MWPL %", ascending=False).reset_index(drop=True)
                out["entrants"] = entrants
                if not out["asof"]:
                    out["asof"] = date.today().strftime("%d %b %Y")
    except Exception:
        pass

    # If ban list is empty, check if it's a trading day
    if out["banned"].empty and not out["asof"]:
        today = date.today()
        if today.weekday() >= 5:  # Saturday/Sunday
            out["asof"] = "Weekend — no trading"
        else:
            out["asof"] = date.today().strftime("%d %b %Y")

    return out
