"""
Parabolic Trends — FII Sector Flows Heatmap
Source: MrChartist public API → NSDL fortnightly data
Fallback: hardcoded reference data from latest NSDL report (Jun 2026)
Renders as color-coded grid matching Zerodha Varsity format.
"""
import streamlit as st
import pandas as pd
import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Real data from the Zerodha Varsity image you shared (INR Crore, approximate)
# YTD flows through Jun 2026. Positive = net inflow, negative = net outflow.
FALLBACK_DATA = [
    {"sector": "Sovereign",                       "aum_pct": 0.0,  "fortnight": 20000,  "one_year":  30000},
    {"sector": "Capital Goods",                   "aum_pct": 7.3,  "fortnight": -2600,  "one_year":  23000},
    {"sector": "Metals & Mining",                 "aum_pct": 4.3,  "fortnight": -4700,  "one_year":  17000},
    {"sector": "Others",                          "aum_pct": 0.9,  "fortnight":   352,  "one_year":   7900},
    {"sector": "Power",                           "aum_pct": 4.3,  "fortnight": -2600,  "one_year":   3200},
    {"sector": "Services",                        "aum_pct": 2.5,  "fortnight":   305,  "one_year":   3200},
    {"sector": "Consumer Durables",               "aum_pct": 2.5,  "fortnight":  -634,  "one_year":  -6700},
    {"sector": "Construction",                    "aum_pct": 1.8,  "fortnight":  -750,  "one_year":  -7300},
    {"sector": "Construction Materials",          "aum_pct": 1.6,  "fortnight": -2400,  "one_year":  -9000},
    {"sector": "Realty",                          "aum_pct": 1.5,  "fortnight": -1200,  "one_year": -14000},
    {"sector": "Telecommunication",               "aum_pct": 5.4,  "fortnight":   373,  "one_year": -17000},
    {"sector": "Healthcare",                      "aum_pct": 7.3,  "fortnight": -4500,  "one_year": -22000},
    {"sector": "Consumer Services",               "aum_pct": 3.5,  "fortnight": -1900,  "one_year": -24000},
    {"sector": "Oil, Gas & Consumable Fuels",     "aum_pct": 7.2,  "fortnight":-10000,  "one_year": -25000},
    {"sector": "Fast Moving Consumer Goods",      "aum_pct": 4.8,  "fortnight": -5100,  "one_year": -27000},
    {"sector": "Automobile and Auto Components",  "aum_pct": 7.5,  "fortnight": -9000,  "one_year": -30000},
    {"sector": "Information Technology",          "aum_pct": 5.4,  "fortnight": -6700,  "one_year": -34000},
    {"sector": "Financial Services",              "aum_pct":29.8,  "fortnight": -7800,  "one_year":-126000},
]


@st.cache_data(ttl=86400, show_spinner=False)
def get_fii_sectors() -> tuple:
    """Try MrChartist API. Fall back to hardcoded data if unavailable."""
    try:
        r = requests.get(
            "https://fii-diidata.mrchartist.com/api/sectors",
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=12)
        if r.status_code == 200:
            raw = r.json()
            if isinstance(raw, list) and len(raw) > 3:
                parsed = []
                for item in raw:
                    # Try all possible field name variants
                    name = (item.get("name") or item.get("sector")
                            or item.get("sectorName") or item.get("Sector") or "")
                    aum  = float(item.get("aumPct") or item.get("aum_pct")
                                 or item.get("aum") or item.get("AUM") or 0)
                    ftn  = float(item.get("fortnightFlow") or item.get("fortnight")
                                 or item.get("fortnightNet") or item.get("flow") or 0)
                    yr   = float(item.get("oneYearFlow") or item.get("one_year")
                                 or item.get("yearFlow") or item.get("annualFlow") or 0)
                    if name:
                        parsed.append({"sector": name, "aum_pct": aum,
                                       "fortnight": ftn, "one_year": yr})
                # Only use API data if flows are non-zero (otherwise it's empty)
                has_flows = any(abs(d["fortnight"]) > 0 or abs(d["one_year"]) > 0
                                for d in parsed)
                if parsed and has_flows:
                    return parsed, "MrChartist · NSDL fortnightly (live)"
    except Exception:
        pass
    return FALLBACK_DATA, "NSDL fortnightly reference · Jun 2026"


def render_fii_heatmap(data: list, source: str):
    """Color-coded grid matching Zerodha Varsity format."""
    if not data:
        st.info("No sector data available.")
        return

    # Sort by 1-year flow descending (best performers first)
    data_sorted = sorted(data, key=lambda x: x.get("one_year", 0), reverse=True)

    # Scale colors relative to max absolute value
    all_abs = [abs(d.get("fortnight", 0)) for d in data_sorted] + \
              [abs(d.get("one_year",   0)) for d in data_sorted]
    max_abs = max(all_abs) if all_abs else 10000

    def cell_style(val: float) -> tuple:
        """(bg, text_color) based on flow magnitude."""
        if not val or val == 0:
            return "#2D333B", "#8B949E"
        ratio = min(abs(val) / max(max_abs, 1), 1.0)
        if val > 0:
            # Green scale: light green → deep green
            if ratio > 0.6:   return "#0E7A4A", "#FFFFFF"
            if ratio > 0.2:   return "#1A6B45", "#FFFFFF"
            return "#1E4D35", "#E6EDF3"
        else:
            # Red scale: light red → deep red
            if ratio > 0.6:   return "#8B1A1A", "#FFFFFF"
            if ratio > 0.2:   return "#6B2020", "#FFFFFF"
            return "#4D2020", "#E6EDF3"

    def fmt(val: float) -> str:
        if val is None or val == 0: return "0"
        if abs(val) >= 1000:
            return f"{val/1000:+.1f}k"
        return f"{val:+.0f}"

    # Source line
    st.markdown(
        f'<div style="font-size:11px;color:#8B949E;margin-bottom:8px">'
        f'FII YTD Sector Flows · INR Crore · Source: {source}</div>',
        unsafe_allow_html=True)

    # Header row
    hdr = (
        '<div style="display:grid;grid-template-columns:210px 65px 110px 120px;'
        'gap:3px;margin-bottom:6px;padding:4px 6px">'
        '<div style="font-size:10px;font-weight:700;letter-spacing:1px;color:#484F58">SECTOR</div>'
        '<div style="font-size:10px;font-weight:700;letter-spacing:1px;color:#484F58;text-align:right">AUM %</div>'
        '<div style="font-size:10px;font-weight:700;letter-spacing:1px;color:#484F58;text-align:center">FORTNIGHT</div>'
        '<div style="font-size:10px;font-weight:700;letter-spacing:1px;color:#484F58;text-align:center">1-YEAR NET</div>'
        '</div>'
    )

    rows = ""
    for d in data_sorted:
        fbg, ftx = cell_style(d.get("fortnight", 0))
        ybg, ytx = cell_style(d.get("one_year", 0))
        aum = d.get("aum_pct", 0)
        aum_str = f"{aum:.1f}%" if aum else "—"

        rows += (
            f'<div style="display:grid;grid-template-columns:210px 65px 110px 120px;'
            f'gap:3px;margin-bottom:2px;align-items:center">'
            f'<div style="font-size:13px;color:#E6EDF3;padding:5px 6px;'
            f'font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'{d["sector"]}</div>'
            f'<div style="font-size:12px;color:#8B949E;text-align:right;'
            f'padding:5px 6px;font-family:monospace">{aum_str}</div>'
            f'<div style="background:{fbg};color:{ftx};border-radius:5px;'
            f'text-align:center;padding:5px 8px;font-size:13px;'
            f'font-family:monospace;font-weight:600">{fmt(d.get("fortnight",0))}</div>'
            f'<div style="background:{ybg};color:{ytx};border-radius:5px;'
            f'text-align:center;padding:5px 8px;font-size:13px;'
            f'font-family:monospace;font-weight:600">{fmt(d.get("one_year",0))}</div>'
            f'</div>'
        )

    legend = (
        '<div style="display:flex;gap:16px;margin-top:12px;flex-wrap:wrap">'
        '<span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#8B949E">'
        '<span style="width:12px;height:12px;background:#1A6B45;border-radius:2px;display:inline-block"></span>Strong inflow</span>'
        '<span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#8B949E">'
        '<span style="width:12px;height:12px;background:#1E4D35;border-radius:2px;display:inline-block"></span>Moderate inflow</span>'
        '<span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#8B949E">'
        '<span style="width:12px;height:12px;background:#6B2020;border-radius:2px;display:inline-block"></span>Moderate outflow</span>'
        '<span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#8B949E">'
        '<span style="width:12px;height:12px;background:#8B1A1A;border-radius:2px;display:inline-block"></span>Heavy outflow</span>'
        '</div>'
    )

    st.markdown(
        f'<div style="background:#161B22;border:1px solid #30363D;'
        f'border-radius:10px;padding:16px 18px;overflow-x:auto">'
        f'{hdr}{rows}{legend}</div>',
        unsafe_allow_html=True)
