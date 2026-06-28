"""PARABOLIC DASHBOARD — Trade Entry"""

import streamlit as st
import pandas as pd
import gspread
import csv
import io
import pytz
from datetime import datetime, date, timedelta
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="ParabolicTrends · Entry", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

IST    = pytz.timezone("Asia/Kolkata")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
TAB_TRADES      = "TRADES"
TAB_CLOSED      = "CLOSED_TRADES"
TAB_INSTRUMENTS = "INSTRUMENTS"
TAB_STRATEGIES  = "STRATEGIES"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;background:#0a0a0f;color:#e2e8f0;}
.stApp{background:#0a0a0f;}
.block-container{padding:1.5rem 2rem 3rem 2rem;max-width:1400px;}
.pb-header{display:flex;align-items:baseline;gap:12px;padding:0 0 1.2rem 0;border-bottom:1px solid #1e1e2e;margin-bottom:1.5rem;}
.pb-logo{font-size:1.1rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#f97316;}
.pb-sub{font-size:0.75rem;color:#475569;letter-spacing:0.08em;text-transform:uppercase;}
.section-title{font-size:0.7rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:#94a3b8;margin-bottom:1rem;padding-bottom:0.6rem;border-bottom:1px solid #1e1e2e;}
.stSelectbox label,.stNumberInput label,.stTextInput label,.stDateInput label,.stTimeInput label,.stTextArea label,.stCheckbox label{font-size:0.68rem!important;font-weight:500!important;letter-spacing:0.08em!important;text-transform:uppercase!important;color:#64748b!important;}
.stSelectbox>div>div,.stTextInput>div>div>input,.stNumberInput>div>div>input,.stDateInput>div>div>input{background:#141420!important;border:1px solid #252538!important;border-radius:6px!important;color:#e2e8f0!important;font-size:0.875rem!important;}
textarea{background:#141420!important;border:1px solid #252538!important;border-radius:6px!important;color:#e2e8f0!important;}
.stButton>button{background:transparent;border:1px solid #252538;border-radius:6px;color:#94a3b8;font-size:0.75rem;font-weight:500;padding:0.4rem 0.85rem;transition:all 0.15s;letter-spacing:0.04em;white-space:nowrap;}
.stButton>button:hover{border-color:#f97316;color:#f97316;background:rgba(249,115,22,0.06);}
.stForm [data-testid="stFormSubmitButton"]>button{background:#f97316;border:none;border-radius:6px;color:#fff;font-size:0.8rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;padding:0.55rem 1.5rem;width:100%;}
.badge-buy{background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);color:#22c55e;border-radius:4px;padding:2px 8px;font-size:0.65rem;font-weight:600;}
.badge-sell{background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);color:#ef4444;border-radius:4px;padding:2px 8px;font-size:0.65rem;font-weight:600;}
.badge-new{background:rgba(249,115,22,0.15);border:1px solid rgba(249,115,22,0.35);color:#f97316;border-radius:4px;padding:1px 6px;font-size:0.6rem;font-weight:700;margin-left:4px;}
.qty-box{background:#0f0f1a;border:1px solid #1e1e2e;border-radius:6px;padding:10px 14px;margin-top:8px;}
.qty-label{font-size:0.6rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;}
.qty-value{font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;}
.stat-box{background:#0f0f1a;border:1px solid #1e1e2e;border-radius:7px;padding:14px 16px;height:90px;display:flex;flex-direction:column;justify-content:space-between;}
.stat-label{font-size:0.58rem;color:#475569;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:0;}
.stat-value{font-size:1.1rem;font-weight:700;font-family:'JetBrains Mono',monospace;line-height:1.2;margin:0;}
.stat-value-sm{font-size:0.95rem;font-weight:700;font-family:'JetBrains Mono',monospace;line-height:1.2;margin:0;}
.stat-sub{font-size:0.6rem;color:#475569;margin-top:0;}
.trade-symbol{font-size:0.88rem;font-weight:600;color:#e2e8f0;margin-bottom:3px;line-height:1.3;}
.trade-meta{font-size:0.71rem;color:#475569;font-family:'JetBrains Mono',monospace;line-height:1.5;}
.edit-panel{background:#0a0a14;border:1px solid #2e2e48;border-radius:8px;padding:1rem 1.2rem;margin:4px 0 10px 0;}
.warn-box{background:rgba(234,179,8,0.08);border-left:3px solid #eab308;border-radius:0 6px 6px 0;padding:8px 12px;font-size:0.78rem;color:#ca8a04;margin:6px 0;}
.info-box{background:rgba(59,130,246,0.08);border-left:3px solid #3b82f6;border-radius:0 6px 6px 0;padding:8px 12px;font-size:0.78rem;color:#60a5fa;margin:6px 0;}
.success-box{background:rgba(34,197,94,0.08);border-left:3px solid #22c55e;border-radius:0 6px 6px 0;padding:8px 12px;font-size:0.78rem;color:#22c55e;margin:6px 0;}
.divider{border:none;border-top:1px solid #1e1e2e;margin:0.8rem 0;}
#MainMenu,footer,header{visibility:hidden;}
.stDeployButton{display:none;}
</style>
""", unsafe_allow_html=True)


# ── SHEETS AUTH ───────────────────────────────────────────────────────────────
@st.cache_resource(ttl=3600)
def get_client():
    raw = dict(st.secrets["gcp_service_account"])
    pk  = str(raw.get("private_key","")).replace("\\n","\n")
    if not pk.endswith("\n"): pk += "\n"
    raw["private_key"] = pk
    return gspread.authorize(Credentials.from_service_account_info(raw, scopes=SCOPES))

@st.cache_resource(ttl=3600)
def get_spreadsheet():
    """Cache the spreadsheet object — avoids repeated open_by_key calls."""
    return get_client().open_by_key(st.secrets["app"]["sheet_id"])

@st.cache_resource(ttl=3600)
def get_ws_cached(tab: str):
    """Cache individual worksheet objects — avoids repeated .worksheet() calls."""
    return get_spreadsheet().worksheet(tab)

def get_ws(tab):
    """Get worksheet — use cached version for read-heavy tabs."""
    return get_ws_cached(tab)


# ── DATA READS ────────────────────────────────────────────────────────────────
# KEY: instruments cached in session_state (not st.cache_data) so it persists
# across reruns but can be manually invalidated after CSV upload.
# This avoids hitting Google API quota on every widget interaction.

def load_instruments_to_session():
    """Read instruments from sheet once and store in session_state."""
    try:
        data = get_ws(TAB_INSTRUMENTS).get_all_records()
        st.session_state["_instruments_df"] = pd.DataFrame(data) if data else pd.DataFrame()
        st.session_state["_instruments_loaded"] = True
    except Exception as e:
        st.session_state["_instruments_df"] = pd.DataFrame()
        st.session_state["_instruments_loaded"] = False
        st.session_state["_instruments_error"] = str(e)

def get_instruments() -> pd.DataFrame:
    """Return instruments DataFrame from session cache."""
    if "_instruments_df" not in st.session_state:
        load_instruments_to_session()
    return st.session_state.get("_instruments_df", pd.DataFrame())

@st.cache_data(ttl=60)
def read_trades():
    try:
        data = get_ws(TAB_TRADES).get_all_records()
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        if "is_deleted" in df.columns:
            df = df[df["is_deleted"].astype(str).str.upper() != "TRUE"]
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def read_strategies():
    try:
        data = get_ws(TAB_STRATEGIES).get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def read_cash_stocks():
    """Read user-maintained cash stock list from CASH sheet tab."""
    try:
        data = get_ws("CASH").get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def read_etf_list():
    """Read ETF list from ETF sheet tab (eq_etfseclist.csv columns: Symbol, Underlying, SecurityName...)."""
    try:
        data = get_ws("ETF").get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_etf_symbols():
    """Return sorted ETF symbol list from ETF tab."""
    df = read_etf_list()
    if df.empty: return []
    sym_col = next((c for c in df.columns if c.strip().upper() == "SYMBOL"), None)
    if not sym_col: return []
    return sorted(df[sym_col].str.upper().str.strip().tolist())

def get_etf_name(symbol: str) -> str:
    """Return ETF full name for display."""
    df = read_etf_list()
    if df.empty: return ""
    sym_col  = next((c for c in df.columns if c.strip().upper() == "SYMBOL"), None)
    name_col = next((c for c in df.columns if c.strip().upper() in ("SECURITYNAME","UNDERLYING","SECURITY NAME")), None)
    if not sym_col or not name_col: return ""
    m = df[df[sym_col].str.upper().str.strip() == symbol.upper().strip()]
    return str(m.iloc[0][name_col]).strip() if not m.empty else ""

def get_cash_symbols():
    """Return list of cash stock symbols from CASH tab (NSE equity list)."""
    df = read_cash_stocks()
    if df.empty:
        return []
    # Handle both "SYMBOL" (NSE CSV) and "symbol" (lowercase) column names
    sym_col = next((c for c in df.columns if c.strip().upper() == "SYMBOL"), None)
    if not sym_col:
        return []
    return sorted(df[sym_col].str.upper().str.strip().tolist())

def get_cash_stock_name(symbol: str) -> str:
    """Return company name for a given symbol from CASH tab."""
    df = read_cash_stocks()
    if df.empty: return ""
    sym_col  = next((c for c in df.columns if c.strip().upper() == "SYMBOL"), None)
    name_col = next((c for c in df.columns if "NAME" in c.strip().upper()), None)
    if not sym_col or not name_col: return ""
    match = df[df[sym_col].str.upper().str.strip() == symbol.upper().strip()]
    if match.empty: return ""
    return str(match.iloc[0][name_col]).strip()


# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_strategy_list():
    df = read_strategies()
    if df.empty or "strategy_name" not in df.columns: return []
    if "active" in df.columns:
        df = df[df["active"].astype(str).str.upper() == "Y"]
    return df["strategy_name"].tolist()

def get_fno_symbols():
    df = get_instruments()
    if df.empty or "symbol" not in df.columns: return []
    return sorted(df["symbol"].str.strip().tolist())

def get_lot_size(symbol: str) -> int:
    """Look up lot size from session-cached instruments DataFrame."""
    if not symbol: return 1
    df = get_instruments()
    if df.empty or "symbol" not in df.columns or "lot_size" not in df.columns: return 1
    m = df[df["symbol"].str.upper().str.strip() == symbol.upper().strip()]
    if m.empty: return 1
    try:
        v = int(str(m.iloc[0]["lot_size"]).strip())
        return v if v > 0 else 1
    except: return 1

def now_ist():
    return datetime.now(IST)

def generate_trade_id():
    return now_ist().strftime("TRD-%Y%m%d-%H%M%S")

def build_expiry_months(n=6):
    months = []
    base = now_ist()
    for i in range(n):
        month = (base.month-1+i)%12+1
        year  = base.year+(base.month-1+i)//12
        months.append(datetime(year,month,1).strftime("%b-%y").upper())
    return months

def badge(a):
    c = "badge-buy" if a=="BUY" else "badge-sell"
    return f'<span class="{c}">{a}</span>'

def fmt_px(v):
    try: return f"₹{float(v):,.2f}"
    except: return str(v)


# ── WRITES ────────────────────────────────────────────────────────────────────
def append_trade(row_data):
    try:
        ws = get_ws(TAB_TRADES)
        headers = ws.row_values(1)
        ws.append_row([str(row_data.get(h,"")) for h in headers], value_input_option="USER_ENTERED")
        read_trades.clear()
        return True
    except Exception as e:
        st.error(f"Write error: {e}"); return False

def soft_delete(trade_id):
    try:
        ws = get_ws(TAB_TRADES)
        h  = ws.row_values(1)
        ti,di = h.index("trade_id")+1, h.index("is_deleted")+1
        for i,v in enumerate(ws.col_values(ti)):
            if v==str(trade_id):
                ws.update_cell(i+1,di,"TRUE"); read_trades.clear(); return True
        return False
    except Exception as e:
        st.error(f"Delete error: {e}"); return False

def close_trade_fast(trade_data: dict, close_price: float, close_date: str) -> bool:
    """
    Fast close: append a matching SELL row to TRADES tab.
    One API call. Dashboard nets BUY+SELL to show position as closed.
    """
    try:
        ws      = get_ws(TAB_TRADES)
        headers = ws.row_values(1)

        action    = str(trade_data.get("action","BUY")).upper()
        close_act = "SELL" if action == "BUY" else "BUY"  # opposite action
        sym       = str(trade_data.get("symbol",""))
        lots      = str(trade_data.get("lots_qty","1"))
        instr     = str(trade_data.get("instrument","FUT"))
        cur_ls    = get_lot_size(sym)
        try:
            lots_int = int(float(lots))
        except:
            lots_int = 1
        qty = lots_int * cur_ls if cur_ls > 1 else int(float(trade_data.get("quantity",lots_int)))

        row = {
            "trade_id":        generate_trade_id(),
            "timestamp_entry": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
            "trade_date":      close_date,
            "trade_time":      now_ist().strftime("%H:%M:%S"),
            "strategy":        str(trade_data.get("strategy","")),
            "exchange":        str(trade_data.get("exchange","NSE")),
            "instrument":      instr,
            "symbol":          sym,
            "expiry":          str(trade_data.get("expiry","")),
            "strike":          str(trade_data.get("strike","")),
            "option_type":     str(trade_data.get("option_type","")),
            "action":          close_act,
            "lots_qty":        lots_int,
            "quantity":        qty,
            "price":           close_price,
            "price_source":    "MANUAL_CLOSE",
            "lot_size":        cur_ls,
            "notes":           f"CLOSE of {trade_data.get('trade_id','')}",
            "is_deleted":      "FALSE",
            "punched_by":      "SELF",
        }
        ws.append_row(
            [str(row.get(h,"")) for h in headers],
            value_input_option="USER_ENTERED"
        )
        read_trades.clear()
        return True
    except Exception as e:
        st.error(f"Close error: {e}")
        return False

def process_closure_trade(close_action: str, symbol: str, exchange: str,
                          instrument: str, expiry: str, strike: str, opt_type: str,
                          lots_to_close: int, close_price: float, close_date: str,
                          strategy: str, lot_size: int) -> tuple:
    """
    Process a closure trade — modifies Google Sheet directly.
    FIFO: closes oldest matching open trade first.
    Writes P&L record to CLOSED_TRADES tab.
    """
    try:
        ws      = get_ws(TAB_TRADES)
        headers = ws.row_values(1)
        col     = {h: i+1 for i, h in enumerate(headers)}  # 1-indexed col numbers

        # Read all rows fresh (bypass cache)
        all_data = ws.get_all_values()
        if len(all_data) < 2:
            return False, "No open trades found in sheet."

        # Opposite action = what we're closing
        orig_action = "BUY" if close_action.upper() == "SELL" else "SELL"

        # Find matching open trades (not deleted)
        matching = []
        for i, row in enumerate(all_data[1:], start=2):
            if len(row) < 5: continue
            d = dict(zip(headers, row))
            if d.get("is_deleted","").upper() == "TRUE": continue
            if d.get("symbol","").upper().strip() != symbol.upper().strip(): continue
            if d.get("action","").upper() != orig_action: continue
            if instrument and d.get("instrument","").upper() != instrument.upper(): continue
            if expiry and d.get("expiry","").upper() != expiry.upper(): continue
            # Only match strike for options
            if opt_type and d.get("option_type","").upper() != opt_type.upper(): continue
            if strike and strike not in ("","0") and d.get("strike","") not in ("","0"):
                if str(d.get("strike","")).strip() != str(strike).strip(): continue
            try:
                open_lots = float(d.get("lots_qty",0) or 0)
            except: open_lots = 0
            if open_lots <= 0: continue
            matching.append((i, d, open_lots))

        if not matching:
            return False, f"No open {orig_action} position found for {symbol} {expiry}. Check symbol/expiry match."

        # FIFO — oldest first
        matching.sort(key=lambda x: x[1].get("timestamp_entry",""))

        remaining     = lots_to_close
        total_pnl     = 0.0
        ws_closed     = get_ws(TAB_CLOSED)
        c_headers     = ws_closed.row_values(1)
        closed_records = []

        for row_idx, trade, open_lots in matching:
            if remaining <= 0: break

            lots_this = min(remaining, open_lots)
            qty_this  = lots_this * lot_size
            entry_px  = float(trade.get("price",0) or 0)
            pnl       = (close_price - entry_px)*qty_this if orig_action=="BUY" else (entry_px - close_price)*qty_this
            total_pnl += pnl

            # Hold days calculation
            try:
                from datetime import date as _date
                entry_dt = trade.get("trade_date","")
                if entry_dt:
                    ed = datetime.strptime(entry_dt, "%Y-%m-%d").date()
                    cd = datetime.strptime(close_date, "%Y-%m-%d").date()
                    hold_days = (cd - ed).days
                else:
                    hold_days = 0
            except:
                hold_days = 0

            # ROI
            roi_pct = round((pnl / (entry_px * qty_this) * 100), 2) if entry_px > 0 and qty_this > 0 else 0

            # Write P&L record to CLOSED_TRADES — column order matches setup_sheet.py CLOSED_HEADERS
            closed = {
                "trade_id":         trade.get("trade_id",""),
                "strategy":         strategy,
                "symbol":           symbol,
                "exchange":         exchange,
                "instrument":       instrument,
                "expiry":           expiry,
                "strike":           strike,
                "option_type":      opt_type,
                "direction":        orig_action,
                "entry_date":       trade.get("trade_date",""),
                "exit_date":        close_date,
                "lots_qty":         lots_this,
                "quantity":         qty_this,
                "avg_entry_price":  entry_px,
                "exit_price":       close_price,
                "gross_pnl":        round(pnl, 2),
                "brokerage":        40.0,   # ₹20 per leg × 2
                "stt":              round(close_price * qty_this * 0.0001, 2),
                "exchange_charges": round(close_price * qty_this * 0.00002, 2),
                "sebi_charges":     round(close_price * qty_this * 0.000001, 2),
                "gst":              round(40.0 * 0.18, 2),
                "stamp_duty":       round(entry_px * qty_this * 0.00003, 2),
                "total_charges":    round(40 + close_price*qty_this*0.0001 + 40*0.18, 2),
                "net_pnl":          round(pnl - (40 + close_price*qty_this*0.0001 + 40*0.18), 2),
                "roi_pct":          roi_pct,
                "hold_days":        hold_days,
                "exit_type":        "MANUAL",
                "is_edited":        "FALSE",
                "edit_timestamp":   "",
                "edit_notes":       "",
            }
            # Build row matching EXACT sheet column order
            # Using get() with fallbacks for both possible header name variants
            def _cv(key, alt=None):
                v = closed.get(key, closed.get(alt,"") if alt else "")
                return str(v) if v not in (None,"") else ""
            
            row_for_sheet = []
            for h in c_headers:
                # Map header variants
                mapping = {
                    "open_date":       closed.get("entry_date",""),
                    "entry_date":      closed.get("entry_date",""),
                    "close_date":      closed.get("exit_date",""),
                    "exit_date":       closed.get("exit_date",""),
                    "avg_exit_price":  closed.get("exit_price",""),
                    "exit_price":      closed.get("exit_price",""),
                    "lots":            closed.get("lots_qty",""),
                    "lots_qty":        closed.get("lots_qty",""),
                    "close_id":        closed.get("trade_id",""),
                    "linked_trade_ids":closed.get("trade_id",""),
                    "close_type":      closed.get("exit_type","MANUAL"),
                    "exit_type":       closed.get("exit_type","MANUAL"),
                }
                row_for_sheet.append(str(mapping.get(h, closed.get(h, ""))))
            closed_records.append(row_for_sheet)

            # Update TRADES tab — reduce qty or mark deleted
            di = col.get("is_deleted", 0)
            lq = col.get("lots_qty", 0)
            qq = col.get("quantity", 0)

            if lots_this >= open_lots - 0.001:
                # Fully closed — mark deleted
                if di: ws.update_cell(row_idx, di, "TRUE")
            else:
                # Partially closed — reduce qty
                rem_lots = open_lots - lots_this
                rem_qty  = rem_lots * lot_size
                if lq: ws.update_cell(row_idx, lq, str(rem_lots))
                if qq: ws.update_cell(row_idx, qq, str(int(rem_qty)))

            remaining -= lots_this

        # Batch write CLOSED_TRADES
        if closed_records:
            ws_closed.append_rows(closed_records, value_input_option="USER_ENTERED")

        # Write closure audit to TRADES (is_deleted=TRUE — won't show in open)
        close_audit = {
            "trade_id":        generate_trade_id(),
            "timestamp_entry": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
            "trade_date":      close_date,
            "trade_time":      now_ist().strftime("%H:%M:%S"),
            "strategy":        strategy,
            "exchange":        exchange,
            "instrument":      instrument,
            "symbol":          symbol,
            "expiry":          expiry,
            "strike":          strike,
            "option_type":     opt_type,
            "action":          close_action,
            "lots_qty":        lots_to_close - remaining,
            "quantity":        (lots_to_close - remaining) * lot_size,
            "price":           close_price,
            "price_source":    "CLOSURE",
            "lot_size":        lot_size,
            "notes":           f"CLOSURE | P&L ₹{total_pnl:,.0f}",
            "is_deleted":      "TRUE",
            "punched_by":      "SELF",
        }
        ws.append_row(
            [str(close_audit.get(h,"")) for h in headers],
            value_input_option="USER_ENTERED"
        )

        read_trades.clear()
        sign = "+" if total_pnl >= 0 else ""
        return True, f"✅ Closed {lots_to_close - remaining}L {symbol} @ ₹{close_price:,.2f} · P&L {sign}₹{abs(total_pnl):,.0f}"

    except Exception as e:
        return False, f"❌ Close error: {e}"


def update_field(trade_id, field, value):
    try:
        ws = get_ws(TAB_TRADES)
        h  = ws.row_values(1)
        ti,fi = h.index("trade_id")+1, h.index(field)+1
        for i,v in enumerate(ws.col_values(ti)):
            if v==str(trade_id):
                ws.update_cell(i+1,fi,str(value)); read_trades.clear(); return True
        return False
    except Exception as e:
        st.error(f"Update error: {e}"); return False

def last_thursday(year: int, month: int) -> date:
    """Return last Thursday of given month (NSE F&O expiry day)."""
    from calendar import monthrange  # stdlib, always available
    last_day = monthrange(year, month)[1]
    d = date(year, month, last_day)
    # Thursday = weekday 3
    offset = (d.weekday() - 3) % 7
    return d - timedelta(days=offset)

def current_expiry_month() -> tuple:
    """
    Return (month, year) of the CURRENT active F&O expiry.
    After last Thursday 3:30 PM IST → roll to next month.
    """
    now = now_ist()
    lt  = last_thursday(now.year, now.month)
    cutoff = IST.localize(datetime(now.year, now.month, lt.day, 15, 30))
    if now > cutoff:
        # Roll to next month
        nm = now.month % 12 + 1
        ny = now.year + (1 if now.month == 12 else 0)
        return (nm, ny)
    return (now.month, now.year)

def get_expiry_col_index(headers: list) -> int:
    """
    Auto-detect which column in fo_mktlots.csv has current expiry lots.
    fo_mktlots.csv headers: Symbol, JAN, FEB, MAR... or col1=symbol, col2=expiry_month, col3=lot_size
    Returns column index (0-based) for lot size of current expiry.
    """
    month, year = current_expiry_month()
    month_abbr  = datetime(year, month, 1).strftime("%b").upper()  # e.g. "JUN"
    # Try to find month name in headers
    for i, h in enumerate(headers):
        if h.strip().upper().startswith(month_abbr):
            return i
    # Fallback: column index 2 (standard SEBI format col C = current month)
    return 2

def parse_fo_csv(text: str) -> list:
    """
    Parse fo_mktlots.csv auto-detecting the lot size column for current expiry.
    Returns list of {symbol, lot_size, underlying, exchange, instrument_type, last_updated}
    Also validates and returns audit info via parse_fo_csv.warnings (attached to function).
    """
    import csv, io
    parse_fo_csv.warnings = []   # reset each call
    parse_fo_csv.audit    = []

    rows_raw   = list(csv.reader(io.StringIO(text)))
    if not rows_raw:
        return []

    # Detect header row
    header_row = 0
    headers    = []
    for i, row in enumerate(rows_raw[:5]):
        joined = " ".join(row).upper()
        if "SYMBOL" in joined or "UNDERLYING" in joined:
            header_row = i
            headers    = [c.strip().upper() for c in row]
            break

    # Find symbol column
    sym_col = next((i for i,h in enumerate(headers) if "SYMBOL" in h or "UNDERLYING" in h), 0)

    # Auto-detect lot size column for current expiry
    lot_col = get_expiry_col_index(headers)
    month, year = current_expiry_month()
    month_name  = datetime(year, month, 1).strftime("%b %Y")
    parse_fo_csv.active_month = month_name

    data_rows = rows_raw[header_row+1:]
    results   = []

    for row in data_rows:
        if len(row) <= max(sym_col, lot_col): continue
        sym = row[sym_col].strip().upper()
        if not sym or sym in ("SYMBOL","UNDERLYING",""): continue

        raw_lot = row[lot_col].strip().replace(",","")

        # Feature 6: graceful missing lot size
        if not raw_lot or not raw_lot.isdigit():
            parse_fo_csv.warnings.append(
                f"⚠️ {sym}: lot size blank/invalid in {month_name} column — skipped"
            )
            continue

        lot = int(raw_lot)

        # Feature 4: warn if lot size is zero
        if lot == 0:
            parse_fo_csv.warnings.append(f"⚠️ {sym}: lot size is 0 in {month_name} — skipped")
            continue

        results.append({
            "symbol":          sym,
            "lot_size":        lot,
            "underlying":      sym,
            "exchange":        "NFO",
            "instrument_type": "FUT",
            "last_updated":    month_name,
        })

    return results


def write_instruments(rows):
    try:
        ws  = get_ws(TAB_INSTRUMENTS)
        av  = ws.get_all_values()

        # ── Feature 4+5: compare with existing lot sizes before overwriting ──
        size_warnings = []
        audit_log     = []
        if len(av) > 1:
            existing = {}
            headers  = [h.strip().lower() for h in av[0]]
            try:
                si = headers.index("symbol")
                li = headers.index("lot_size")
                for row in av[1:]:
                    if len(row) > max(si, li) and row[si]:
                        try: existing[row[si].upper()] = int(row[li])
                        except: pass
            except: pass

            # Feature 4: warn if lot size changed by >50%
            # Feature 5: build audit trail
            now_str = now_ist().strftime("%d %b %Y")
            for r in rows:
                sym     = r["symbol"].upper()
                new_lot = int(r["lot_size"])
                if sym in existing:
                    old_lot = existing[sym]
                    if old_lot > 0 and abs(new_lot - old_lot) / old_lot > 0.50:
                        size_warnings.append(
                            f"⚠️ {sym}: lot size changed {old_lot} → {new_lot} "
                            f"({round((new_lot-old_lot)/old_lot*100,0):+.0f}%) — verify before saving"
                        )
                    if old_lot != new_lot:
                        audit_log.append(
                            f"As of {now_str}, {sym} lot size changed from {old_lot} to {new_lot}"
                        )

            ws.batch_clear([f"A2:Z{len(av)}"])

        # Column order MUST match setup_sheet.py INSTRUMENTS_HEADERS:
        # symbol | exchange | instrument_type | lot_size | as_of_month | underlying_name
        data = [[r["symbol"], r["exchange"], r["instrument_type"],
                 r["lot_size"], r["last_updated"], r["underlying"]] for r in rows]
        ws.append_rows(data, value_input_option="USER_ENTERED")
        # Immediately update session cache — no extra API call needed
        st.session_state["_instruments_df"] = pd.DataFrame(rows)
        st.session_state["_instruments_loaded"] = True
        return True, f"✅ {len(data)} symbols loaded — {now_ist().strftime('%d-%m-%Y %H:%M')}"
    except Exception as e:
        return False, f"❌ {e}"


# ── SESSION STATE INIT ────────────────────────────────────────────────────────
if "edit_id" not in st.session_state: st.session_state.edit_id = None

# Load instruments into session — reload if empty (handles post-upload case)
if "_instruments_loaded" not in st.session_state:
    load_instruments_to_session()

df_inst = get_instruments()
# If loaded but empty, try once more (sheet may have been updated)
if df_inst.empty and st.session_state.get("_instruments_loaded"):
    load_instruments_to_session()
    df_inst = get_instruments()
inst_count = len(df_inst) if not df_inst.empty else 0
inst_last  = df_inst["last_updated"].iloc[0] if (not df_inst.empty and "last_updated" in df_inst.columns) else ""


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="pb-header">'
    '<span style="font-size:1.3rem;font-weight:700;letter-spacing:0.02em;">'
    '<span style="color:#ffffff;">Parabolic</span>'
    '<span style="color:#7c6fcd;">Trends</span>'
    '</span>'
    '<span class="pb-sub" style="margin-left:16px;">Trade Entry</span>'
    '</div>',
    unsafe_allow_html=True
)


# ══════════════════════════════════════════════════════════════════════════════
# INSTRUMENTS PANEL
# ══════════════════════════════════════════════════════════════════════════════
col_status = "#f97316" if inst_count > 0 else "#ef4444"
st.markdown(
    f'<div style="font-size:0.72rem;color:{col_status};margin-bottom:6px;">'
    f'📋 {inst_count} F&O symbols loaded{" · " + inst_last if inst_last else " — upload fo_mktlots.csv below"}</div>',
    unsafe_allow_html=True
)

# Feature 3: Show which expiry column will be used
_exp_month, _exp_year = current_expiry_month()
_exp_label = datetime(_exp_year, _exp_month, 1).strftime("%b %Y").upper()
_lt        = last_thursday(_exp_year, _exp_month)
_cutoff    = IST.localize(datetime(_exp_year, _exp_month, _lt.day, 15, 30))
_roll_note = " · ⚡ Rolling to next month after 3:30 PM today" if now_ist().date() == _lt else ""

with st.expander(f"🔧 Update F&O Lot Sizes — {_exp_label}{_roll_note}", expanded=(inst_count == 0)):
    st.markdown(
        f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:8px;">'
        f'Select <b>fo_mktlots.csv</b> → click Update. '
        f'Lot sizes will be read from the <b>{_exp_label}</b> column automatically.</div>',
        unsafe_allow_html=True
    )
    uploaded = st.file_uploader("fo_mktlots.csv", type=["csv"], label_visibility="collapsed")
    if st.button("⬆ Update Instruments"):
        if uploaded:
            parsed = parse_fo_csv(uploaded.read().decode("utf-8", errors="replace"))
            if parsed:
                ok, msg, size_warnings, audit_changes = write_instruments(parsed)
                st.markdown(f'<div class="{"success-box" if ok else "warn-box"}">{msg}</div>', unsafe_allow_html=True)
                if ok: st.rerun()
            else:
                st.markdown('<div class="warn-box">⚠️ Could not parse — check file is NSE fo_mktlots.csv</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warn-box">⚠️ Select file first</div>', unsafe_allow_html=True)

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
col_form, col_trades = st.columns([1, 1.4], gap="large")


# ══════════════════════════════════════════════════════
# LEFT — ENTRY
# Selectors are OUTSIDE the form so every symbol change
# triggers an immediate rerun and lot size updates live.
# ══════════════════════════════════════════════════════
with col_form:
    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;'
        'color:#94a3b8;margin-bottom:1rem;padding-bottom:0.6rem;border-bottom:1px solid #1e1e2e;">'
        '✦ New Trade</div>',
        unsafe_allow_html=True
    )

    strategies  = get_strategy_list()
    fno_symbols = get_fno_symbols()

    if not strategies:
        st.markdown('<div class="warn-box">No strategies — check STRATEGIES tab in Google Sheet.</div>', unsafe_allow_html=True)
    else:
        # ── ALL SELECTORS OUTSIDE FORM ──
        strategy = st.selectbox("Strategy", strategies, key="sel_strategy")

        sc1, sc2 = st.columns(2)
        exchange   = sc1.selectbox("Exchange",   ["NSE","BSE","MCX"], key="sel_exchange")
        instrument = sc2.selectbox("Instrument", ["FUT","OPT","CASH","ETF"], key="sel_instrument")

        if instrument in ("CASH", "ETF"):
            if instrument == "ETF":
                sym_list = get_etf_symbols()
                name_fn  = get_etf_name
                sym_key  = "sel_symbol_etf"
                man_key  = "sel_etf_manual"
                lbl      = "ETF Symbol (type to search)"
                fallback = "e.g. NIFTYBEES"
            else:
                sym_list = get_cash_symbols()
                name_fn  = get_cash_stock_name
                sym_key  = "sel_symbol_cash"
                man_key  = "sel_cash_manual"
                lbl      = "Symbol (type to search)"
                fallback = "e.g. RELIANCE"
            if sym_list:
                opts   = sym_list + ["✏ Type manually..."]
                choice = st.selectbox(lbl, opts, key=sym_key)
                if choice == "✏ Type manually...":
                    symbol = st.text_input("Symbol", placeholder=fallback, key=man_key).upper().strip()
                else:
                    symbol = choice
                    dname  = name_fn(symbol)
                    if dname:
                        st.markdown(f'<div style="font-size:0.72rem;color:#475569;margin:-2px 0 6px 0;">{dname}</div>', unsafe_allow_html=True)
            else:
                symbol = st.text_input(lbl, placeholder=fallback, key=sym_key).upper().strip()
            expiry, strike, opt_type = "", 0, ""
            if fno_symbols:
                symbol = st.selectbox("Symbol", fno_symbols, key="sel_symbol_fno")
            else:
                symbol = st.text_input("Symbol (upload F&O list above)", key="sel_symbol_manual").upper().strip()

            ec1, ec2, ec3 = st.columns(3)
            expiry = ec1.selectbox("Expiry", build_expiry_months(6), key="sel_expiry")
            if instrument == "OPT":
                strike   = ec2.number_input("Strike", min_value=0, step=50, value=0, key="sel_strike")
                opt_type = ec3.selectbox("CE / PE", ["CE","PE"], key="sel_opttype")
            else:
                strike, opt_type = 0, ""

        # ── LOT SIZE from session cache — zero API calls ──
        lot_size = 1
        if instrument not in ("CASH","ETF") and symbol:
            lot_size = get_lot_size(symbol)

        ac1, ac2 = st.columns(2)
        action = ac1.selectbox("Action", ["BUY","SELL"], key="sel_action")

        if instrument in ("CASH", "ETF"):
            quantity = ac2.number_input("Quantity (shares)", min_value=1, step=1, value=1, key="sel_qty")
            lots     = 0
        else:
            lots     = ac2.number_input("Lots", min_value=1, step=1, value=1, key="sel_lots")
            quantity = lots * lot_size

        # ── QTY DISPLAY ──
        if instrument != "CASH":
            qc1, qc2, qc3 = st.columns(3)
            ls_color = "#f97316" if lot_size > 1 else "#ef4444"
            ls_disp  = str(lot_size) if lot_size > 1 else "NOT FOUND"
            qc1.markdown(f'<div class="qty-box"><div class="qty-label">Lot Size</div><div class="qty-value" style="color:{ls_color};">{ls_disp}</div></div>', unsafe_allow_html=True)
            qc2.markdown(f'<div class="qty-box"><div class="qty-label">Lots × Size</div><div class="qty-value" style="color:#94a3b8;">{lots} × {lot_size}</div></div>', unsafe_allow_html=True)
            qt_color = "#22c55e" if lot_size > 1 else "#ef4444"
            qc3.markdown(f'<div class="qty-box"><div class="qty-label">Total Qty</div><div class="qty-value" style="color:{qt_color};">{quantity:,} shares</div></div>', unsafe_allow_html=True)
            if lot_size == 1 and symbol:
                df_check = get_instruments()
                loaded_count = len(df_check)
                if loaded_count == 0:
                    st.markdown(f'<div class="warn-box">⚠️ No instruments loaded yet. Upload fo_mktlots.csv above → click Update.</div>', unsafe_allow_html=True)
                else:
                    # Symbol genuinely not found — show first 5 loaded symbols for debug
                    sample = df_check["symbol"].head(3).tolist() if "symbol" in df_check.columns else []
                    st.markdown(f'<div class="warn-box">⚠️ <b>{symbol}</b> — lot size unavailable, update CSV or enter quantity manually.</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── FORM — date/price/notes/submit only ──
        with st.form("entry_form", clear_on_submit=True):
            now = now_ist()
            fc1, fc2   = st.columns(2)
            trade_date = fc1.date_input("Trade Date", value=now.date())
            trade_time = fc2.time_input("Trade Time", value=now.time().replace(second=0,microsecond=0))

            is_back = trade_date < now.date()
            if is_back:
                st.markdown('<div class="info-box">↩ Backdated entry — enter price manually.</div>', unsafe_allow_html=True)

            fp1, fp2 = st.columns([1.5,1])
            manual   = fp2.checkbox("Manual price", value=True)
            price    = fp1.number_input("Price ₹", min_value=0.0, step=0.05, format="%.2f", value=0.0)
            price_source = "MANUAL"

            if not manual and not is_back and instrument != "CASH":
                try:
                    from core.angelone import get_angel_obj, get_symbol_token, fetch_current_ltp
                    obj = get_angel_obj()
                    if obj:
                        token = get_symbol_token(symbol, exchange, instrument)
                        if token:
                            ltp, _ = fetch_current_ltp(symbol, exchange, token)
                            if ltp and ltp > 0:
                                price = ltp; price_source = "ANGELONE_LTP"
                                st.markdown(f'<div class="success-box">LTP fetched: {fmt_px(ltp)}</div>', unsafe_allow_html=True)
                            else:
                                st.markdown('<div class="warn-box">No price returned — enter manually.</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="warn-box">Symbol token not found for {symbol}.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="warn-box">AngelOne login failed — enter manually.</div>', unsafe_allow_html=True)
                except Exception as ex:
                    st.markdown(f'<div class="warn-box">AngelOne error: {ex}</div>', unsafe_allow_html=True)

            notes     = st.text_area("Notes", height=56, placeholder="Setup, SL, reason...")

            # ── CLOSURE TRADE TOGGLE ──
            is_closure = st.checkbox("🔴 Closure trade", value=False)

            submitted = st.form_submit_button("LOG TRADE →")

        if submitted:
            if not symbol:
                st.markdown('<div class="warn-box">⚠️ Symbol required.</div>', unsafe_allow_html=True)
            elif price <= 0:
                st.markdown('<div class="warn-box">⚠️ Enter a valid price > 0.</div>', unsafe_allow_html=True)
            elif is_closure:
                # ── CLOSURE TRADE PATH ──
                ok_c, msg_c = process_closure_trade(
                    close_action  = action,
                    symbol        = symbol,
                    exchange      = exchange,
                    instrument    = instrument,
                    expiry        = expiry,
                    strike        = str(strike) if strike else "",
                    opt_type      = opt_type,
                    lots_to_close = int(lots) if instrument != "CASH" else 0,
                    close_price   = price,
                    close_date    = str(trade_date),
                    strategy      = strategy,
                    lot_size      = lot_size,
                )
                box_class = "success-box" if ok_c else "warn-box"
                st.markdown(f'<div class="{box_class}">{msg_c}</div>', unsafe_allow_html=True)
            else:
                # ── REGULAR TRADE PATH ──
                ok = append_trade({
                    "trade_id":        generate_trade_id(),
                    "timestamp_entry": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
                    "trade_date":      str(trade_date),
                    "trade_time":      str(trade_time),
                    "strategy":        strategy,
                    "exchange":        exchange,
                    "instrument":      instrument,
                    "symbol":          symbol,
                    "expiry":          expiry,
                    "strike":          strike if strike else "",
                    "option_type":     opt_type,
                    "action":          action,
                    "lots_qty":        lots if instrument not in ("CASH","ETF") else 0,
                    "quantity":        int(quantity),
                    "price":           price,
                    "price_source":    price_source,
                    "lot_size":        lot_size,
                    "notes":           notes,
                    "is_deleted":      "FALSE",
                    "punched_by":      "SELF",
                })
                if ok:
                    qty_desc = f"{lots} lots ({quantity:,} sh)" if instrument!="CASH" else f"{int(quantity):,} shares"
                    st.markdown(
                        f'<div class="success-box">✅ {action} {symbol} — {qty_desc} @ {fmt_px(price)}</div>',
                        unsafe_allow_html=True
                    )


# ══════════════════════════════════════════════════════
# RIGHT — OPEN TRADES (grouped by strategy)
# ══════════════════════════════════════════════════════
with col_trades:
    st.markdown(
        '<div style="font-size:0.72rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;'
        'color:#94a3b8;margin-bottom:1rem;padding-bottom:0.6rem;border-bottom:1px solid #1e1e2e;">'
        '✦ Open Trades</div>',
        unsafe_allow_html=True
    )

    # Refresh left, Clear Data far right aligned with Margin Remaining box
    _c1, _c2, _c3, _c4 = st.columns([1, 1, 1, 1])
    if _c1.button("↻ Refresh"):
        read_trades.clear()
        st.rerun()
    if _c4.button("🗑 Clear Data", help="Marks ALL open trades as deleted. Use to reset test data."):
        st.session_state["confirm_clear"] = True

    if st.session_state.get("confirm_clear", False):
        st.markdown('<div class="warn-box">⚠️ This will mark ALL open trades as deleted. Are you sure?</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        if cc1.button("✓ Yes, Clear All"):
            try:
                ws      = get_ws(TAB_TRADES)
                headers = ws.row_values(1)
                if "is_deleted" in headers:
                    di       = headers.index("is_deleted") + 1
                    all_vals = ws.get_all_values()
                    updates  = []
                    for i, row in enumerate(all_vals[1:], start=2):
                        if len(row) >= di and row[di-1].upper() != "TRUE":
                            updates.append({"range": f"{chr(64+di)}{i}", "values": [["TRUE"]]})
                    if updates:
                        ws.batch_update(updates)
                    read_trades.clear()
                    st.session_state.pop("confirm_clear", None)
                    st.rerun()
            except Exception as e:
                st.error(f"Clear error: {e}")
        if cc2.button("Cancel"):
            st.session_state.pop("confirm_clear", None)
            st.rerun()

    df        = read_trades()
    today_str = now_ist().strftime("%Y-%m-%d")

    if df.empty:
        st.markdown('<div style="color:#475569;font-size:0.82rem;padding:2rem 0;text-align:center;">No trades logged yet.</div>', unsafe_allow_html=True)
    else:
        if "timestamp_entry" in df.columns:
            df = df.sort_values("timestamp_entry", ascending=False)

        # Ensure instruments loaded before rendering lot sizes
        df_inst_check = get_instruments()
        if df_inst_check.empty:
            load_instruments_to_session()

        # df_display = df filtered by is_deleted=FALSE (already done in read_trades)
        df_display = df

        # ── FETCH LTP + MARGIN FOR ALL POSITIONS (one batch) ──
        ltp_map           = {}
        margin_map        = {}   # {trade_id: margin_estimate}
        total_margin_used = 0.0

        try:
            from core.angelone import get_angel_obj, get_symbol_token, fetch_current_ltp, fetch_margin_for_positions
            obj = get_angel_obj()
            if obj:
                token_map = {}  # {sym: token} — reuse tokens for both LTP and margin
                positions_for_margin = []

                for _, row in df.iterrows():
                    sym   = str(row.get("symbol",""))
                    exch  = str(row.get("exchange","NSE"))
                    instr = str(row.get("instrument","FUT"))
                    exp_v = str(row.get("expiry",""))
                    stk_v = float(row.get("strike",0) or 0)
                    opt_v = str(row.get("option_type",""))
                    qty   = float(row.get("quantity",0) or 0)
                    px    = float(row.get("price",0) or 0)

                    if sym and sym not in ltp_map:
                        token = get_symbol_token(sym, exch, instr, exp_v, stk_v, opt_v)
                        token_map[sym] = token
                        ltp, _ = fetch_current_ltp(sym, exch, token, instr)
                        if ltp and ltp > 0:
                            ltp_map[sym] = ltp

                    # Build margin positions with token
                    if instr.upper() != "CASH" and sym:
                        positions_for_margin.append({
                            "symbol":          sym,
                            "exchange":        exch,
                            "instrument":      instr,
                            "token":           token_map.get(sym,""),
                            "quantity":        qty,
                            "avg_entry_price": px,
                            "strategy":        str(row.get("strategy","")),
                        })

                # Try SPAN margin API first
                if positions_for_margin:
                    mdata = fetch_margin_for_positions(positions_for_margin)
                    total_margin_used = float(mdata.get("_total_required", 0))

                # Build per-position margin map (symbol → margin estimate)
                # Using LTP × qty × SEBI min margin %
                margin_map = {}   # {sym: margin_for_this_position}
                for _, row in df.iterrows():
                    sym   = str(row.get("symbol",""))
                    instr = str(row.get("instrument","FUT"))
                    lots  = float(row.get("lots_qty", row.get("quantity",0)) or 0)
                    tid_r = str(row.get("trade_id",""))
                    if sym in ltp_map:
                        ltp  = ltp_map[sym]
                        if instr.upper() == "CASH":
                            cash_qty   = float(row.get("quantity", 0) or 0)
                            pos_margin = ltp * cash_qty * 0.20
                        else:
                            # Feature 2: prefer stored lot_size over live lookup
                            s_ls   = row.get("lot_size", 0)
                            try:   s_ls = int(float(str(s_ls))) if s_ls else 0
                            except: s_ls = 0
                            ls_use = s_ls if s_ls > 1 else get_lot_size(sym)
                            lots_r = float(row.get("lots_qty", row.get("quantity",0)) or 0)
                            qty_r  = lots_r * ls_use if ls_use > 1 else float(row.get("quantity",0) or 0)
                            pct    = 0.12 if instr.upper() == "OPT" else 0.15
                            pos_margin = ltp * qty_r * pct
                        margin_map[tid_r] = pos_margin
                total_margin_used = sum(margin_map.values())

        except Exception:
            pass

        # ── TOTAL ALLOCATED CAPITAL ──
        total_capital = 0
        try:
            df_strat = read_strategies()
            if not df_strat.empty and "allocated_capital" in df_strat.columns:
                for _, sr in df_strat.iterrows():
                    try:
                        cap = str(sr["allocated_capital"]).replace("L","").replace("l","").strip()
                        cv  = float(cap)
                        if cv < 10000: cv *= 100000
                        total_capital += cv
                    except: pass
        except: pass

        # ── TOTAL MTM ──
        total_mtm = 0.0
        for _, row in df.iterrows():
            sym = str(row.get("symbol",""))
            if sym in ltp_map:
                ep  = float(row.get("price",0) or 0)
                qty = float(row.get("quantity",0) or 0)
                act = str(row.get("action","BUY")).upper()
                total_mtm += ((ltp_map[sym]-ep)*qty) if act=="BUY" else ((ep-ltp_map[sym])*qty)

        # ── SUMMARY METRICS ROW ──
        tm_c = "#22c55e" if total_mtm>=0 else "#ef4444"
        tm_s = ("+" if total_mtm>=0 else "")+f"₹{abs(total_mtm):,.0f}" if ltp_map else "—"
        mg_s = f"₹{total_margin_used/100000:.1f}L" if total_margin_used > 0 else "—"
        mg_p = f"{total_margin_used/total_capital*100:.1f}%" if (total_capital>0 and total_margin_used>0) else ""
        mg_c = "#22c55e" if (total_margin_used/total_capital < 0.5 if total_capital>0 and total_margin_used>0 else True) else "#eab308"
        cr_s = f"₹{(total_capital-total_margin_used)/100000:.1f}L" if (total_capital>0 and total_margin_used>0) else "—"

        m1,m2,m3,m4 = st.columns(4)
        m1.markdown(f'<div class="stat-box"><div class="stat-label">Positions</div><div class="stat-value" style="color:#e2e8f0">{len(df)}</div><div class="stat-sub">{len(df[df["action"].str.upper()=="BUY"])}L · {len(df[df["action"].str.upper()=="SELL"])}S</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="stat-box"><div class="stat-label">Total MTM</div><div class="stat-value" style="color:{tm_c}">{tm_s}</div><div class="stat-sub">{"live" if ltp_map else "needs AngelOne"}</div></div>', unsafe_allow_html=True)
        m3.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-label">Margin Utilised</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:2px;">'
            f'<span style="font-size:1.1rem;font-weight:700;font-family:JetBrains Mono,monospace;color:{mg_c};">{mg_s}</span>'
            f'<span style="font-size:0.82rem;font-weight:600;color:{mg_c};">{mg_p}</span>'
            f'</div>'
            f'<div class="stat-sub">{"of ₹"+str(int(total_capital//100000))+"L capital" if total_capital>0 else "SPAN estimated"}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        m4.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-label">Margin Remaining</div>'
            f'<div class="stat-value" style="color:#e2e8f0">{cr_s}</div>'
            f'<div class="stat-sub">{"of ₹"+str(int(total_capital//100000))+"L total" if cr_s != "—" else "add AngelOne"}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # ── GROUP BY STRATEGY — fixed order ──
        STRATEGY_ORDER = ["TREND", "COMMODITIES", "MOMENTUM"]
        all_strats = df_display["strategy"].unique().tolist() if (not df_display.empty and "strategy" in df_display.columns) else []
        ordered = [s for s in STRATEGY_ORDER if s in all_strats]
        others  = sorted([s for s in all_strats if s not in STRATEGY_ORDER])
        strategies_in_trades = ordered + others

        for strategy_name in strategies_in_trades:
            strategy_df = df_display[df_display["strategy"] == strategy_name].copy()

            # Strategy MTM
            strat_mtm = 0.0
            for _, row in strategy_df.iterrows():
                sym = str(row.get("symbol",""))
                if sym in ltp_map:
                    ep  = float(row.get("price",0) or 0)
                    qty = float(row.get("quantity",0) or 0)
                    act = str(row.get("action","BUY")).upper()
                    strat_mtm += ((ltp_map[sym]-ep)*qty) if act=="BUY" else ((ep-ltp_map[sym])*qty)

            strat_mtm_c = "#22c55e" if strat_mtm>=0 else "#ef4444"
            strat_mtm_s = ("+" if strat_mtm>=0 else "")+f"₹{abs(strat_mtm):,.0f}" if ltp_map else "—"
            strat_today = len(strategy_df[strategy_df["trade_date"].astype(str)==today_str]) if "trade_date" in strategy_df.columns else 0

            # Strategy header row
            sc1, sc2, sc3, sc4, sc5 = st.columns([1.2, 0.8, 1.2, 1.8, 0.8])
            sc1.markdown(
                f'<div style="background:rgba(249,115,22,0.12);border:1px solid rgba(249,115,22,0.3);'
                f'border-radius:5px;padding:5px 12px;display:inline-block;font-size:0.75rem;'
                f'font-weight:700;letter-spacing:0.1em;color:#f97316;text-transform:uppercase;white-space:nowrap;">{strategy_name}</div>',
                unsafe_allow_html=True
            )
            sc2.markdown(f'<div style="font-size:0.6rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;">Positions</div><div style="font-size:0.95rem;font-weight:700;color:#e2e8f0;">{len(strategy_df)}</div>', unsafe_allow_html=True)
            sc3.markdown(f'<div style="font-size:0.6rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;">MTM P&L</div><div style="font-size:0.95rem;font-weight:700;color:{strat_mtm_c};">{strat_mtm_s}</div>', unsafe_allow_html=True)
            strat_margin = sum(
                margin_map.get(str(r.get("trade_id","")), 0)
                for _, r in strategy_df.iterrows()
            )
            # Get allocated capital for this strategy
            strat_alloc = 0
            try:
                df_st = read_strategies()
                if not df_st.empty and "strategy_name" in df_st.columns and "allocated_capital" in df_st.columns:
                    st_row = df_st[df_st["strategy_name"] == strategy_name]
                    if not st_row.empty:
                        cap_str = str(st_row.iloc[0]["allocated_capital"]).replace("L","").replace("l","").strip()
                        cv = float(cap_str)
                        strat_alloc = cv * 100000 if cv < 10000 else cv
            except: pass
            
            strat_mg_s   = f"₹{strat_margin/100000:.1f}L" if strat_margin > 0 else "—"
            strat_rem    = strat_alloc - strat_margin if strat_alloc > 0 and strat_margin > 0 else None
            strat_rem_s  = f"₹{strat_rem/100000:.1f}L free" if strat_rem is not None else ""
            strat_mg_c   = "#22c55e" if (strat_rem is not None and strat_rem > 0) else ("#eab308" if strat_margin > 0 else "#475569")
            sc4.markdown(
                f'<div style="font-size:0.65rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin-top:2px;">Utilised · Remaining</div>'
                f'<div style="font-size:0.85rem;font-weight:600;color:{strat_mg_c};">'
                f'{strat_mg_s}{" · <span style=\"color:#22c55e\">" + strat_rem_s + "</span>" if strat_rem_s else ""}'
                f'</div>',
                unsafe_allow_html=True
            )
            sc5.markdown(f'<div style="font-size:0.65rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin-top:2px;">Today</div><div style="font-size:0.9rem;font-weight:600;color:#f97316;">{strat_today}</div>', unsafe_allow_html=True)

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            # ── AGGREGATE same symbol+expiry+strike+action into one display row ──
            agg_rows = []
            grp_cols = ["symbol","instrument","expiry","strike","option_type","action"]
            avail_gc = [c for c in grp_cols if c in strategy_df.columns]
            for grp_key, grp in strategy_df.groupby(avail_gc, dropna=False, sort=False):
                base = grp.sort_values("timestamp_entry").iloc[0].copy() if "timestamp_entry" in grp.columns else grp.iloc[0].copy()
                total_lots = 0.0
                total_qty  = 0.0
                wprice_sum = 0.0
                earliest_date = None
                for _, r in grp.iterrows():
                    lots_r  = float(r.get("lots_qty", 0) or 0)
                    px_r    = float(r.get("price",0) or 0)
                    instr_r = str(r.get("instrument","FUT")).upper()
                    if instr_r in ("CASH","ETF"):
                        qty_r = float(r.get("quantity",0) or 0)
                        total_lots += qty_r
                    else:
                        s_ls  = int(float(str(r.get("lot_size",0) or 0)))
                        ls_r  = s_ls if s_ls > 1 else get_lot_size(str(r.get("symbol","")))
                        qty_r = lots_r * ls_r if ls_r > 1 else float(r.get("quantity",0) or 0)
                        total_lots += lots_r
                    total_qty  += qty_r
                    wprice_sum += px_r * qty_r
                    dt_r = str(r.get("trade_date",""))
                    if dt_r and (earliest_date is None or dt_r < earliest_date):
                        earliest_date = dt_r
                avg_px = wprice_sum / total_qty if total_qty > 0 else 0
                instr_base = str(base.get("instrument","FUT")).upper()
                if instr_base in ("CASH","ETF"):
                    base["quantity"] = int(total_qty)
                    base["lots_qty"] = 0
                else:
                    base["lots_qty"]   = total_lots
                    base["quantity"]   = int(total_qty)
                base["trade_date"] = earliest_date or str(base.get("trade_date",""))
                # Use first trade_id for key but mark as aggregated
                base["_agg_count"] = len(grp)
                agg_rows.append(base)

            render_df = pd.DataFrame(agg_rows) if agg_rows else strategy_df

            # Trade rows under this strategy
            for _ri, (_, row) in enumerate(render_df.iterrows()):
                tid   = str(row.get("trade_id","")).strip()
                sym   = str(row.get("symbol","")).strip()
                act   = str(row.get("action","")).strip()
                instr = str(row.get("instrument","")).strip()
                exp_v = str(row.get("expiry","")).strip()
                stk_v = str(row.get("strike","")).strip()
                opt_v = str(row.get("option_type","")).strip()

                # Skip corrupted/empty rows
                if not tid or not sym or not act:
                    continue
                # Make key unique even if tid is duplicated (safety)
                _key = f"{strategy_name}_{tid}_{_ri}"
                lv    = str(row.get("lots_qty",""))
                qv    = str(row.get("quantity",""))
                pv    = row.get("price",0)
                dt_v  = str(row.get("trade_date",""))

                # Descriptor
                agg_count = int(row.get("_agg_count", 1))
                desc  = sym
                if exp_v: desc += f" {exp_v}"
                if stk_v and stk_v not in ("","0"): desc += f" {stk_v}{opt_v}"
                new_b = '<span class="badge-new">NEW</span>' if dt_v==today_str else ""
                # Show aggregation indicator if multiple trades combined
                agg_b = f'<span style="font-size:0.6rem;color:#7c6fcd;margin-left:4px;">[{agg_count} trades]</span>' if agg_count > 1 else ""

                # Days open
                try:
                    days_open = (now_ist().date() - datetime.strptime(dt_v,"%Y-%m-%d").date()).days
                    days_str  = "today" if days_open==0 else f"{days_open}d"
                except: days_str = "—"

                # Qty
                # Feature 2: use stored entry lot_size first, never recompute from CSV
                stored_ls = row.get("lot_size", 0)
                try:    stored_ls = int(float(str(stored_ls))) if stored_ls else 0
                except: stored_ls = 0
                cur_ls  = stored_ls if stored_ls > 1 else get_lot_size(sym)
                if instr in ("CASH","ETF"):
                    qty_info = f"{qv}sh"
                else:
                    cur_qty  = int(float(lv))*cur_ls if (str(lv).replace(".","").isdigit() and cur_ls>1) else qv
                    qty_info = f"{float(lv):.0f}L×{cur_ls}={cur_qty}sh"

                # LTP + MTM per trade
                ltp_str = ""
                mtm_str = ""
                if sym in ltp_map:
                    lp = ltp_map[sym]
                    ltp_str = fmt_px(lp)
                    try:
                        ep  = float(pv)
                        qty = float(qv)
                        pnl = (lp-ep)*qty if act.upper()=="BUY" else (ep-lp)*qty
                        pc  = "#22c55e" if pnl>=0 else "#ef4444"
                        mtm_str = f'<span style="color:{pc};font-weight:600">{"+" if pnl>=0 else ""}₹{abs(pnl):,.0f}</span>'
                    except: mtm_str = ""

                is_editing = (st.session_state.edit_id == tid)
                ci, cb2   = st.columns([4, 0.6])

                # Per-position margin
                pos_margin     = margin_map.get(tid, 0)
                pos_margin_str = f"Mrgn ₹{pos_margin/100000:.2f}L" if pos_margin > 0 else ""

                with ci:
                    st.markdown(
                        f'<div style="background:#0f0f1a;border:1px solid #1e1e2e;border-radius:6px;padding:8px 12px;margin-bottom:4px;">'
                        f'<div class="trade-symbol">{badge(act)} &nbsp;{desc}{new_b}{agg_b}</div>'
                        f'<div class="trade-meta">{qty_info} · {fmt_px(pv)} entry'
                        f'{"  ·  LTP " + ltp_str if ltp_str else ""}'
                        f'{"  " + mtm_str if mtm_str else ""}'
                        f'</div>'
                        f'<div class="trade-meta">{dt_v} · {days_str} open'
                        f'{"  ·  <span style=\'color:#7c6fcd;\'>" + pos_margin_str + "</span>" if pos_margin_str else ""}'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                with cb2:
                    b1, b2 = st.columns(2)
                    if b1.button("✏", key=f"e_{_key}", help="Edit"):
                        st.session_state.edit_id = None if is_editing else tid
                        st.rerun()
                    if b2.button("✕", key=f"d_{_key}", help="Delete"):
                        # Delete ALL trades in this aggregated group
                        grp_tids = [
                            str(r.get("trade_id",""))
                            for _, r in strategy_df.iterrows()
                            if str(r.get("symbol","")) == sym
                            and str(r.get("instrument","")) == instr
                            and str(r.get("expiry","")) == exp_v
                            and str(r.get("action","")) == act
                            and str(r.get("strike","")) == stk_v
                            and str(r.get("option_type","")) == opt_v
                        ]
                        for _tid in grp_tids:
                            if _tid:
                                soft_delete(_tid)
                        st.session_state.edit_id = None
                        st.rerun()

                if is_editing:
                    st.markdown('<div class="edit-panel">', unsafe_allow_html=True)
                    ea,eb,ec = st.columns(3)
                    try:    dv = datetime.strptime(dt_v,"%Y-%m-%d").date()
                    except: dv = now_ist().date()
                    nd = ea.date_input("Date", value=dv, key=f"ed_{_key}")
                    np = eb.number_input("Price ₹", min_value=0.0, step=0.05,
                                         format="%.2f", value=float(pv) if pv else 0.0, key=f"ep_{_key}")
                    # CASH/ETF: edit shares directly; FUT/OPT: edit lots
                    if instr in ("CASH","ETF"):
                        cur_qty_val = int(float(qv)) if str(qv).replace(".","").isdigit() else 1
                        nq = ec.number_input("Qty (shares)", min_value=1, step=1,
                                             value=cur_qty_val, key=f"el_{_key}")
                    else:
                        nl = ec.number_input("Lots", min_value=1, step=1,
                                             value=int(float(lv)) if str(lv).replace(".","").isdigit() else 1,
                                             key=f"el_{_key}")
                    s1,s2 = st.columns(2)
                    if s1.button("Save", key=f"sv_{_key}"):
                        update_field(tid,"trade_date",str(nd))
                        update_field(tid,"price",np)
                        if instr in ("CASH","ETF"):
                            update_field(tid,"quantity", nq)
                            update_field(tid,"lots_qty", 0)
                        else:
                            ls = get_lot_size(sym)
                            update_field(tid,"lots_qty", nl)
                            update_field(tid,"quantity", nl*ls)
                        st.session_state.edit_id=None; st.rerun()
                    if s2.button("Cancel", key=f"cx_{_key}"):
                        st.session_state.edit_id=None; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)



            # Spacing between strategy groups
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
