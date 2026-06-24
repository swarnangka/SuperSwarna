"""
Parabolic Trends — Chartink screeners.
Add more by pasting the scan_clause from Chartink Network → process → Payload.
"""

SCREENERS = {
    "52-Week High":
        "( {33489} ( daily close >= daily max( 240 , daily close ) ) )",

    "Multi-TF RSI > 70 (D/W/M)":
        "( {33489} ( daily rsi( 14 ) > 70 and weekly rsi( 14 ) > 70 and "
        "monthly rsi( 14 ) > 70 ) )",

    "Minervini Trend + Monthly RSI > 75":
        "( {33489} ( daily ema( close,50 ) > daily ema( close,150 ) and "
        "daily ema( close,150 ) > daily ema( close,200 ) and "
        "( daily close / ( daily max( 250 , daily high ) ) ) > 0.85 and "
        "( daily close / ( daily min( 250 , daily low ) ) ) > 1.3 and "
        "daily close > daily ema( close,50 ) and daily close > 30 and "
        "daily volume > 100000 and "
        "daily volume < daily sma( volume,20 ) * 1.1 and "
        "monthly rsi( 14 ) > 75 ) )",
}
