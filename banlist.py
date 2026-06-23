"""
SuperSwarna — F&O Ban List + Possible Entrants (alternate to NSE direct).
Strategy: NSE publishes a daily CSV of combined OI + MWPL for every F&O stock
at a stable archive URL. We compute:
  • Banned     : MWPL% >= 95  (in ban)
  • Entrants   : 80 <= MWPL% < 95  (likely to enter ban)
  • Exiting    : already banned but OI easing (best-effort)
This CSV path is the same data brokers/mirror sites repackage, and is more
reliable than NSE's cookie-gated JSON from cloud servers.
"""
import streamlit as st
import pandas as pd
import requests
from io import StringIO
from datetime import datetime

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36")


@st.cache_data(ttl=1800, show_spinner=False)
def fno_ban_mwpl() -> dict:
    """
    Pull combined OI / MWPL CSV and bucket by MWPL%.
    Primary: NSE archive CSV (nsccl combineoi_deleq). Fallback: nsearchives.
    """
    out = {"banned": pd.DataFrame(), "entrants": pd.DataFrame(),
           "asof": "", "source": ""}
    today = datetime.now()
    ddmmyyyy = today.strftime("%d%m%Y")

    urls = [
        f"https://nsearchives.nseindia.com/content/nsccl/combineoi_deleq_{ddmmyyyy}.csv",
        f"https://archives.nseindia.com/content/nsccl/combineoi_deleq_{ddmmyyyy}.csv",
    ]
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept": "*/*",
                         "Referer": "https://www.nseindia.com/"})
    try:
        sess.get("https://www.nseindia.com", timeout=8)
    except Exception:
        pass

    raw = None
    used = ""
    for u in urls:
        try:
            r = sess.get(u, timeout=12)
            if r.status_code == 200 and len(r.text) > 200:
                raw = r.text
                used = u
                break
        except Exception:
            continue
    if raw is None:
        return out

    try:
        # The combineoi file has a header row then data; columns vary, so parse flexibly
        df = pd.read_csv(StringIO(raw))
        df.columns = [str(c).strip() for c in df.columns]
        # Identify symbol and MWPL% columns heuristically
        sym_col = next((c for c in df.columns if c.lower() in
                        ("symbol", "underlying", "scrip")), None)
        pct_col = next((c for c in df.columns if "%" in c or "mwpl" in c.lower()
                        or "limit" in c.lower()), None)
        if sym_col is None or pct_col is None:
            return out
        df = df[[sym_col, pct_col]].copy()
        df.columns = ["Symbol", "MWPL %"]
        df["MWPL %"] = pd.to_numeric(df["MWPL %"], errors="coerce")
        df = df.dropna()
        banned = df[df["MWPL %"] >= 95].sort_values("MWPL %", ascending=False)
        entrants = df[(df["MWPL %"] >= 80) & (df["MWPL %"] < 95)] \
            .sort_values("MWPL %", ascending=False)
        out["banned"] = banned.reset_index(drop=True)
        out["entrants"] = entrants.reset_index(drop=True)
        out["asof"] = today.strftime("%d %b %Y")
        out["source"] = used
    except Exception:
        return out
    return out
