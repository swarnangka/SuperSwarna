"""
Parabolic Trends — FII Sector Flows
Source: MrChartist public API (fii-diidata.mrchartist.com/api/sectors)
This is a public API — no auth required, served from their Express backend.
Falls back to hardcoded last-known data if server unreachable.
Renders as a color-coded HTML heatmap matching the Zerodha Varsity format.
"""
import streamlit as st
import pandas as pd
import requests
import json

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Hardcoded fallback data (approximate YTD flows from the image you shared)
# Used when live API is unreachable — shows "cached" label
FALLBACK_DATA = [
    {"sector": "Sovereign",              "aum_pct": 6.8,  "fortnight": 20000, "one_year": 30000},
    {"sector": "Capital Goods",          "aum_pct": 4.2,  "fortnight": -2600, "one_year": 23000},
    {"sector": "Metals & Mining",        "aum_pct": 3.8,  "fortnight": -4700, "one_year": 17000},
    {"sector": "Power",                  "aum_pct": 3.1,  "fortnight": -2600, "one_year":  3200},
    {"sector": "Services",               "aum_pct": 2.9,  "fortnight":   305, "one_year":  3200},
    {"sector": "Consumer Durables",      "aum_pct": 2.4,  "fortnight":  -634, "one_year": -6700},
    {"sector": "Construction",           "aum_pct": 2.2,  "fortnight":  -750, "one_year": -7300},
    {"sector": "Realty",                 "aum_pct": 1.8,  "fortnight": -1200, "one_year":-14000},
    {"sector": "Telecom",                "aum_pct": 3.4,  "fortnight":   373, "one_year":-17000},
    {"sector": "Healthcare",             "aum_pct": 4.1,  "fortnight": -4500, "one_year":-22000},
    {"sector": "Consumer Services",      "aum_pct": 2.6,  "fortnight": -1900, "one_year":-24000},
    {"sector": "Oil Gas & Fuels",        "aum_pct": 5.2,  "fortnight":-10000, "one_year":-25000},
    {"sector": "FMCG",                   "aum_pct": 4.8,  "fortnight": -5100, "one_year":-27000},
    {"sector": "Auto & Components",      "aum_pct": 4.6,  "fortnight": -9000, "one_year":-30000},
    {"sector": "Information Technology", "aum_pct":12.4,  "fortnight": -6700, "one_year":-34000},
    {"sector": "Financial Services",     "aum_pct":30.2,  "fortnight": -7800, "one_year":-126000},
]


@st.cache_data(ttl=86400, show_spinner=False)
def get_fii_sectors() -> tuple:
    """
    Returns (data_list, source_label).
    data_list: list of dicts with sector, aum_pct, fortnight, one_year keys.
    """
    try:
        r = requests.get(
            "https://fii-diidata.mrchartist.com/api/sectors",
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=12)
        if r.status_code == 200:
            raw = r.json()
            # Their format: array of sector objects
            if isinstance(raw, list) and len(raw) > 0:
                parsed = []
                for item in raw:
                    parsed.append({
                        "sector":   item.get("name") or item.get("sector",""),
                        "aum_pct":  float(item.get("aumPct") or item.get("aum_pct") or 0),
                        "fortnight":float(item.get("fortnightFlow") or item.get("fortnight") or 0),
                        "one_year": float(item.get("oneYearFlow") or item.get("one_year") or 0),
                    })
                if parsed:
                    return parsed, "MrChartist · NSDL fortnightly"
    except Exception:
        pass
    # Fallback
    return FALLBACK_DATA, "Cached reference data (live source unavailable)"


def render_fii_heatmap(data: list, source: str):
    """Render color-coded heatmap matching Zerodha Varsity style."""
    if not data:
        st.info("No sector data available.")
        return

    def flow_color(val: float, max_abs: float = 10000) -> tuple:
        """Returns (bg_color, text_color) based on flow value."""
        if val is None or val == 0:
            return "#30363D", "#8B949E"
        ratio = min(abs(val) / max(max_abs, 1), 1.0)
        if val > 0:
            # Green intensity
            g = int(46 + ratio * (142 - 46))
            r = int(46 - ratio * 30)
            b = int(100 - ratio * 50)
            return f"rgb({r},{g},{b})", "#0D1117" if ratio > 0.5 else "#E6EDF3"
        else:
            # Red intensity
            r = int(248 - ratio * 50)
            g = int(81 - ratio * 60)
            b = int(73 - ratio * 50)
            return f"rgb({r},{g},{b})", "#0D1117" if ratio > 0.5 else "#E6EDF3"

    def fmt_flow(val: float) -> str:
        if val is None: return "—"
        if abs(val) >= 1000:
            return f"{val/1000:+.1f}k"
        return f"{val:+.0f}"

    # Sort by 1-year flow descending (like Zerodha image)
    data_sorted = sorted(data, key=lambda x: x.get("one_year",0), reverse=True)

    # Compute max abs for color scaling
    all_vals = [abs(d.get("fortnight",0)) for d in data_sorted] + \
               [abs(d.get("one_year",0)) for d in data_sorted]
    max_abs = max(all_vals) if all_vals else 10000

    # Header
    st.markdown(
        f'<div style="font-size:11px;color:#8B949E;margin-bottom:10px">'
        f'FII YTD Sector Flows · INR Crore · Source: {source}</div>',
        unsafe_allow_html=True)

    # Table header
    header = (
        '<div style="display:grid;grid-template-columns:180px 70px 100px 120px;'
        'gap:2px;margin-bottom:4px;padding:0 2px">'
        '<div style="font-size:10px;color:#484F58;font-weight:600;letter-spacing:1px">SECTOR</div>'
        '<div style="font-size:10px;color:#484F58;font-weight:600;letter-spacing:1px;text-align:right">AUM %</div>'
        '<div style="font-size:10px;color:#484F58;font-weight:600;letter-spacing:1px;text-align:center">FORTNIGHT</div>'
        '<div style="font-size:10px;color:#484F58;font-weight:600;letter-spacing:1px;text-align:center">1-YEAR NET</div>'
        '</div>'
    )

    rows = ""
    for d in data_sorted:
        sector   = d.get("sector","")
        aum      = d.get("aum_pct", 0)
        ftn      = d.get("fortnight", 0)
        yr       = d.get("one_year", 0)
        fbg, ftx = flow_color(ftn, max_abs * 0.3)
        ybg, ytx = flow_color(yr, max_abs)

        rows += (
            f'<div style="display:grid;grid-template-columns:180px 70px 100px 120px;'
            f'gap:2px;margin-bottom:2px;align-items:center">'
            f'<div style="font-size:12px;color:#E6EDF3;padding:4px 4px;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{sector}</div>'
            f'<div style="font-size:12px;color:#8B949E;text-align:right;'
            f'font-family:monospace;padding:4px 4px">{aum:.1f}%</div>'
            f'<div style="background:{fbg};color:{ftx};border-radius:4px;'
            f'text-align:center;padding:4px 8px;font-size:12px;'
            f'font-family:monospace;font-weight:600">{fmt_flow(ftn)}</div>'
            f'<div style="background:{ybg};color:{ytx};border-radius:4px;'
            f'text-align:center;padding:4px 8px;font-size:12px;'
            f'font-family:monospace;font-weight:600">{fmt_flow(yr)}</div>'
            f'</div>'
        )

    # Legend
    legend = (
        '<div style="display:flex;gap:16px;margin-top:10px;flex-wrap:wrap">'
        '<div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#8B949E">'
        '<div style="width:12px;height:12px;background:#2EC4A0;border-radius:2px"></div>Strong inflow</div>'
        '<div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#8B949E">'
        '<div style="width:12px;height:12px;background:#1E8E74;border-radius:2px"></div>Moderate inflow</div>'
        '<div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#8B949E">'
        '<div style="width:12px;height:12px;background:#F85149;border-radius:2px"></div>Moderate outflow</div>'
        '<div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#8B949E">'
        '<div style="width:12px;height:12px;background:#A32D2D;border-radius:2px"></div>Heavy outflow</div>'
        '</div>'
    )

    st.markdown(
        f'<div style="background:#161B22;border:1px solid #30363D;'
        f'border-radius:10px;padding:14px 16px;overflow-x:auto">'
        f'{header}{rows}{legend}</div>',
        unsafe_allow_html=True)
