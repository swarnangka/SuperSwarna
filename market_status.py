"""
Parabolic Trends — Market Status Module
NSE Equity and MCX Commodity market open/closed status with holiday awareness.
"""
from datetime import datetime, timezone, timedelta, date

IST = timezone(timedelta(hours=5, minutes=30))

# NSE Equity holidays 2026 (confirmed from NSE circular)
NSE_HOLIDAYS_2026 = {
    date(2026,1,15),   # Makar Sankranti / Municipal Elections Maharashtra
    date(2026,1,26),   # Republic Day
    date(2026,2,19),   # Chhatrapati Shivaji Maharaj Jayanti
    date(2026,3,25),   # Holi
    date(2026,4,6),    # Ram Navami
    date(2026,4,10),   # Good Friday
    date(2026,4,14),   # Dr. Ambedkar Jayanti
    date(2026,5,1),    # Maharashtra Day
    date(2026,6,26),   # Muharram
    date(2026,8,15),   # Independence Day
    date(2026,10,2),   # Gandhi Jayanti
    date(2026,10,26),  # Dussehra
    date(2026,11,26),  # Gurunanak Jayanti
    date(2026,12,25),  # Christmas
}

# MCX morning session closed on same days as NSE
# Evening session stays open on most holidays (global commodity markets don't pause)
MCX_EVENING_CLOSED_2026 = {
    date(2026,1,26),   # Republic Day — both sessions closed
    date(2026,8,15),   # Independence Day — both sessions closed
    date(2026,10,2),   # Gandhi Jayanti — both sessions closed
}

# US Daylight Saving: clocks spring forward Mar 8, fall back Nov 1
# During DST (Mar-Oct approx): MCX closes at 11:30 PM
# During non-DST (Nov-Mar): MCX closes at 11:55 PM
def _mcx_evening_close() -> tuple:
    """Returns (hour, minute) for MCX evening close based on DST."""
    today = datetime.now(IST).date()
    m = today.month
    # DST roughly March to October
    if 3 <= m <= 10:
        return (23, 30)   # 11:30 PM IST
    return (23, 55)       # 11:55 PM IST


def nse_equity_status() -> dict:
    """Returns {open: bool, label: str, detail: str}"""
    n = datetime.now(IST)
    today = n.date()

    # Weekend
    if n.weekday() >= 5:
        return {"open": False, "label": "CLOSED",
                "detail": "Weekend", "color": "#484F58"}

    # Holiday
    if today in NSE_HOLIDAYS_2026:
        return {"open": False, "label": "HOLIDAY",
                "detail": "Market holiday today", "color": "#D29922"}

    # Trading hours: 9:15 AM – 3:30 PM
    t = n.hour * 60 + n.minute
    if t < 555:   # before 9:15
        return {"open": False, "label": "PRE-OPEN",
                "detail": f"Opens at 09:15 IST", "color": "#D29922"}
    if t <= 930:  # 9:15 to 15:30
        return {"open": True, "label": "LIVE",
                "detail": "Equity · 09:15–15:30", "color": "#2EC4A0"}
    return {"open": False, "label": "CLOSED",
            "detail": "Closed · Opens 09:15 tomorrow", "color": "#484F58"}


def mcx_status() -> dict:
    """Returns {open: bool, label: str, detail: str}"""
    n = datetime.now(IST)
    today = n.date()

    # Weekend
    if n.weekday() >= 5:
        return {"open": False, "label": "CLOSED",
                "detail": "Weekend", "color": "#484F58"}

    # Check if both sessions closed
    if today in MCX_EVENING_CLOSED_2026:
        return {"open": False, "label": "HOLIDAY",
                "detail": "MCX closed today", "color": "#D29922"}

    # Morning session closed on NSE holidays but evening open
    morning_closed = today in NSE_HOLIDAYS_2026

    eh, em = _mcx_evening_close()
    t = n.hour * 60 + n.minute
    evening_close = eh * 60 + em

    if t < 540:   # before 9:00 AM
        return {"open": False, "label": "PRE-OPEN",
                "detail": "MCX opens 09:00", "color": "#D29922"}
    if t < 555 and not morning_closed:   # 9:00–9:15 pre-open
        return {"open": True, "label": "PRE-OPEN",
                "detail": "Pre-open session", "color": "#D29922"}
    if morning_closed and t < 1020:  # holiday morning closed, before 5 PM
        return {"open": False, "label": "HOLIDAY AM",
                "detail": "Evening opens 17:00", "color": "#D29922"}
    if t <= evening_close:
        session = "Morning" if t < 1020 else "Evening"
        return {"open": True, "label": "LIVE",
                "detail": f"MCX {session} · closes {eh:02d}:{em:02d}",
                "color": "#2EC4A0"}
    return {"open": False, "label": "CLOSED",
            "detail": "MCX closed · Opens 09:00", "color": "#484F58"}
