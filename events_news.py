"""
Parabolic Trends — Events, Results, Calendar & News
News sources: Reuters, CNBC, Axios, Economic Times, Moneycontrol
Headlines only, newest first, with date/time stamp.
"""
import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

RSS_FEEDS = {
    "Reuters":       "https://feeds.reuters.com/reuters/businessNews",
    "CNBC":          "https://feeds.content.cnbc.com/applications/cnbc/rss?id=100003114",
    "Axios Markets": "https://api.axios.com/feed/",
    "Economic Times":"https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Moneycontrol":  "https://www.moneycontrol.com/rss/marketreports.xml",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 Chrome/122 Safari/537.36"}

EVENTS_2026 = [
    ("2026-01-28","FOMC","US Fed rate decision"),
    ("2026-03-18","FOMC","US Fed rate decision + SEP projections"),
    ("2026-04-29","FOMC","US Fed rate decision"),
    ("2026-06-17","FOMC","US Fed rate decision + SEP projections"),
    ("2026-07-29","FOMC","US Fed rate decision"),
    ("2026-09-16","FOMC","US Fed rate decision + SEP projections"),
    ("2026-11-04","FOMC","US Fed rate decision"),
    ("2026-12-16","FOMC","US Fed rate decision + SEP projections"),
    ("2026-02-28","MSCI","MSCI Quarterly Index Review effective"),
    ("2026-05-29","MSCI","MSCI Semi-Annual Index Review effective"),
    ("2026-08-28","MSCI","MSCI Quarterly Index Review effective"),
    ("2026-11-28","MSCI","MSCI Semi-Annual Index Review effective"),
    ("2026-04-07","RBI","RBI MPC Rate Decision"),
    ("2026-06-06","RBI","RBI MPC Rate Decision"),
    ("2026-08-07","RBI","RBI MPC Rate Decision"),
    ("2026-10-09","RBI","RBI MPC Rate Decision"),
    ("2026-12-05","RBI","RBI MPC Rate Decision"),
]


def events_window(days: int = 7) -> pd.DataFrame:
    today = date.today()
    rows = []
    for dstr, kind, desc in EVENTS_2026:
        try:
            d = datetime.strptime(dstr, "%Y-%m-%d").date()
            delta = (d - today).days
            if 0 <= delta <= days:
                when = "TODAY" if delta == 0 else f"in {delta}d"
                rows.append({"Date": d.strftime("%d %b"), "When": when,
                             "Type": kind, "Event": desc})
        except Exception:
            continue
    return pd.DataFrame(rows)


def results_today() -> pd.DataFrame:
    """Fetch results calendar from Investing.com RSS as alternate to NSE."""
    rows = []
    try:
        r = requests.get(
            "https://in.investing.com/rss/news_25.rss",
            headers=HEADERS, timeout=10)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for it in root.findall(".//item")[:30]:
                title = it.findtext("title","").lower()
                if "result" in title or "quarterly" in title or "earnings" in title:
                    rows.append({"Headline": it.findtext("title","").strip()})
    except Exception:
        pass
    return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner=False)
def news_digest(max_per_feed: int = 6) -> pd.DataFrame:
    """Headlines from all RSS sources, newest first, with IST timestamp."""
    from email.utils import parsedate_to_datetime
    rows = []
    for source, url in RSS_FEEDS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            for it in root.findall(".//item")[:max_per_feed]:
                title = it.findtext("title","").strip()
                link  = it.findtext("link","").strip()
                pub   = it.findtext("pubDate","").strip()
                dt    = None
                try:
                    dt = parsedate_to_datetime(pub)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(IST).replace(tzinfo=None)
                except Exception:
                    pass
                if title:
                    rows.append({"Source": source, "Headline": title,
                                 "Link": link, "dt": dt})
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("dt", ascending=False, na_position="last").reset_index(drop=True)
    return df
