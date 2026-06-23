"""
SuperSwarna — Chartink screener integration
Uses Chartink's public scan endpoint (unofficial). Free accounts return
data delayed ~30-45 min. Returns the matching stock list only.
"""
import streamlit as st
import pandas as pd
import requests
import re

PROCESS_URL = "https://chartink.com/screener/process"
SCREENER_URL = "https://chartink.com/screener/"

# Your saved screeners. Edit these — paste the scan_clause from Chartink's
# Network → process → Payload (or rebuild via their visual builder).
# Find scan_clause: open your screener on chartink.com, F12 → Network →
# run scan → click 'process' → Payload tab → copy the scan_clause value.
try:
    from screeners import SCREENERS as DEFAULT_SCREENERS
except Exception:
    DEFAULT_SCREENERS = {
        "52-Week High": "( {33489} ( daily close >= daily max( 240 , daily close ) ) )",
    }


@st.cache_data(ttl=300, show_spinner=False)
def run_chartink_scan(scan_clause: str) -> pd.DataFrame:
    """Run a Chartink scan and return matching stocks as a DataFrame."""
    try:
        with requests.Session() as s:
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0 Safari/537.36",
                "Referer": SCREENER_URL,
            })
            page = s.get(SCREENER_URL, timeout=20)
            m = re.search(r'name="csrf-token"\s+content="([^"]+)"', page.text)
            if not m:
                return pd.DataFrame({"error": ["Could not get CSRF token from Chartink"]})
            s.headers["x-csrf-token"] = m.group(1)
            s.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            r = s.post(PROCESS_URL, data={"scan_clause": scan_clause}, timeout=30)
            if r.status_code != 200:
                return pd.DataFrame({"error": [f"Chartink returned status {r.status_code}"]})
            j = r.json()
            data = j.get("data", [])
            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data)
            # Standard Chartink columns: nsecode, name, close, per_chg, volume
            cols = {}
            if "nsecode" in df: cols["nsecode"] = "Symbol"
            if "name" in df: cols["name"] = "Name"
            if "close" in df: cols["close"] = "Close"
            if "per_chg" in df: cols["per_chg"] = "Chg %"
            if "volume" in df: cols["volume"] = "Volume"
            df = df.rename(columns=cols)
            keep = [c for c in ["Symbol","Name","Close","Chg %","Volume"] if c in df.columns]
            return df[keep] if keep else df
    except Exception as e:
        return pd.DataFrame({"error": [f"Chartink fetch failed: {str(e)[:120]}"]})
