"""
SuperSwarna — your Chartink screeners.
═══════════════════════════════════════════════════════════════════
TO ADD A SCREENER:
  1. Open your screener on chartink.com
  2. Press ⌥⌘I → Network tab → click "Run Scan" → click the 'process' row
  3. Open the Payload tab → copy the full scan_clause value
  4. Add a line below: "Your name": "( paste clause here )",
  5. Save, push to GitHub. It appears in the dropdown automatically.
═══════════════════════════════════════════════════════════════════
"""

SCREENERS = {
    "52-Week High":
        "( {33489} ( daily close >= daily max( 240 , daily close ) ) )",

    "Multi-TF RSI > 60 (D/W/M)":
        "( {33489} ( daily rsi( 14 ) > 60 and weekly rsi( 14 ) > 60 and "
        "monthly rsi( 14 ) > 60 ) )",

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
