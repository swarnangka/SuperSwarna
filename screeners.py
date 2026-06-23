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
    "52-Week High": "( {33489} ( daily close >= daily max( 240 , daily close ) ) )",
    # "Your next scan": "( {33489} ( ... ) )",
    # "Another scan":   "( {cash} ( ... ) )",
}
