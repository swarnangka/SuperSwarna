"""
Parabolic Trends — FII Sector Flows Heatmap
Source: NSDL fortnightly FPI sector HTML pages (predictable URL pattern)
Cached 24h. Falls back to last good cache if NSDL blocks server.
"""
import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _fortnightly_dates(n: int = 12) -> list:
    """Generate last N fortnightly dates (15th and last day of each month)."""
    dates = []
    today = date.today()
    y, m = today.year, today.month
    for _ in range(n * 3):
        for day in [15, _last_day(y, m)]:
            d = date(y, m, day)
            if d <= today:
                dates.append(d)
        m -= 1
        if m == 0:
            m = 12; y -= 1
    dates.sort(reverse=True)
    return dates[:n]


def _last_day(y: int, m: int) -> int:
    import calendar
    return calendar.monthrange(y, m)[1]


def _nsdl_url(d: date) -> str:
    mon = d.strftime("%b")
    return (f"https://www.fpi.nsdl.co.in/StaticReports/"
            f"Fortnightly_Sector_wise_FII_Investment_Data/"
            f"FIIInvestSector_{mon}{d.day:02d}{d.year}.html")


def _parse_nsdl_table(html: str, date_label: str) -> pd.DataFrame:
    try:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for tbl in tables:
            rows = tbl.find_all("tr")
            if len(rows) < 5:
                continue
            data = []
            for row in rows[1:]:
                cols = [c.get_text(strip=True) for c in row.find_all(["td","th"])]
                if len(cols) >= 3:
                    data.append(cols)
            if data:
                df = pd.DataFrame(data)
                df.columns = range(len(df.columns))
                df = df.rename(columns={0: "Sector"})
                # find net investment column — usually 3rd or 4th
                for col_idx in [3, 4, 2]:
                    if col_idx < len(df.columns):
                        df["Flow"] = pd.to_numeric(
                            df[col_idx].str.replace(",","").str.replace("(","−").str.replace(")",""),
                            errors="coerce")
                        if df["Flow"].notna().sum() > 3:
                            return df[["Sector","Flow"]].rename(columns={"Flow": date_label})
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def get_fii_sector_heatmap() -> pd.DataFrame:
    """Build the sector × fortnight matrix. Returns wide DataFrame."""
    dates = _fortnightly_dates(12)
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://www.nseindia.com/"})
    try:
        sess.get("https://www.nseindia.com", timeout=8)
    except Exception:
        pass

    frames = []
    for d in dates:
        label = d.strftime("%b %d")
        url   = _nsdl_url(d)
        try:
            r = sess.get(url, timeout=12)
            if r.status_code == 200 and len(r.text) > 500:
                df = _parse_nsdl_table(r.text, label)
                if not df.empty:
                    frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    result = frames[0]
    for f in frames[1:]:
        result = result.merge(f, on="Sector", how="outer")
    num_cols = [c for c in result.columns if c != "Sector"]
    result["YTD"] = result[num_cols].sum(axis=1, numeric_only=True)
    result = result.sort_values("YTD", ascending=False).reset_index(drop=True)
    return result
