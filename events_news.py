"""
SuperSwarna — Events, F&O Ban, Results & News (free / scrapeable sources)
  • F&O ban list + possible entrants → NSE
  • Results due today → NSE corporate results calendar
  • Events calendar → built-in FOMC/MSCI dates + macro (reliable, pre-published)
  • Market news digest → RSS (Economic Times, Moneycontrol, Investing.com)
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import xml.etree.ElementTree as ET

NSE_HOME = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/122.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _nse_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get(NSE_HOME, timeout=10)
    except Exception:
        pass
    return s


def _nse_get(path: str) -> dict:
    for _ in range(2):
        try:
            s = _nse_session()
            r = s.get(NSE_HOME + path, timeout=12)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return {}


# ── F&O Ban list + possible entrants ──────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fno_ban() -> dict:
    """NSE F&O securities ban + MWPL-based possible entrants."""
    out = {"banned": pd.DataFrame(), "entrants": pd.DataFrame()}
    # Ban list (CSV-like JSON from NSE)
    j = _nse_get("/api/reportsExpirty?index=fos_sec_ban")  # current ban list
    try:
        if j and "data" in j:
            df = pd.DataFrame(j["data"])
            out["banned"] = df
    except Exception:
        pass
    return out


# ── Results / earnings due today ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def results_today() -> pd.DataFrame:
    """Companies reporting results today (NSE results calendar)."""
    j = _nse_get("/api/event-calendar")
    rows = []
    today = date.today().strftime("%d-%b-%Y")
    try:
        data = j if isinstance(j, list) else j.get("data", [])
        for e in data:
            purpose = (e.get("purpose") or "").lower()
            edate = e.get("date", "")
            if "result" in purpose or "financial" in purpose:
                rows.append({
                    "Symbol": e.get("symbol", ""),
                    "Company": e.get("company", ""),
                    "Date": edate,
                    "Purpose": e.get("purpose", ""),
                })
    except Exception:
        pass
    df = pd.DataFrame(rows)
    return df


# ── Events calendar (FOMC / MSCI / macro) — pre-published, hardcoded ──────────
# FOMC 2026 meeting dates (decision day) + MSCI 2026 rebalance effective dates.
EVENTS_2026 = [
    ("2026-01-28", "FOMC", "US Fed rate decision"),
    ("2026-03-18", "FOMC", "US Fed rate decision + projections"),
    ("2026-04-29", "FOMC", "US Fed rate decision"),
    ("2026-06-17", "FOMC", "US Fed rate decision + projections"),
    ("2026-07-29", "FOMC", "US Fed rate decision"),
    ("2026-09-16", "FOMC", "US Fed rate decision + projections"),
    ("2026-11-04", "FOMC", "US Fed rate decision"),
    ("2026-12-16", "FOMC", "US Fed rate decision + projections"),
    ("2026-02-28", "MSCI", "MSCI Quarterly Index Review (effective)"),
    ("2026-05-29", "MSCI", "MSCI Semi-Annual Index Review (effective)"),
    ("2026-08-28", "MSCI", "MSCI Quarterly Index Review (effective)"),
    ("2026-11-28", "MSCI", "MSCI Semi-Annual Index Review (effective)"),
]


def events_window(days_ahead: int = 7) -> pd.DataFrame:
    """Upcoming FOMC/MSCI/macro events within N days (incl. today)."""
    today = date.today()
    rows = []
    for dstr, kind, desc in EVENTS_2026:
        try:
            d = datetime.strptime(dstr, "%Y-%m-%d").date()
            delta = (d - today).days
            if 0 <= delta <= days_ahead:
                when = "TODAY" if delta == 0 else (f"in {delta}d")
                rows.append({"Date": d.strftime("%d %b"), "When": when,
                             "Type": kind, "Event": desc})
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("When")
    return df


# ── Market news digest (RSS) ──────────────────────────────────────────────────
RSS_FEEDS = {
    "Economic Times":
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Moneycontrol":
        "https://www.moneycontrol.com/rss/marketreports.xml",
    "Investing.com India":
        "https://in.investing.com/rss/news_25.rss",
}


@st.cache_data(ttl=600, show_spinner=False)
def news_digest(max_per_feed: int = 6) -> pd.DataFrame:
    """Pull headlines from market RSS feeds. Plain, fast, reliable."""
    rows = []
    for source, url in RSS_FEEDS.items():
        try:
            r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=10)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            items = root.findall(".//item")[:max_per_feed]
            for it in items:
                title = it.findtext("title", "").strip()
                link = it.findtext("link", "").strip()
                pub = it.findtext("pubDate", "").strip()
                if title:
                    rows.append({"Source": source, "Headline": title,
                                 "Link": link, "Published": pub})
        except Exception:
            continue
    return pd.DataFrame(rows)
