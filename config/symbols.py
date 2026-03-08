"""All ticker symbols used in the application."""

# Major indices
INDEX_SYMBOLS = {
    "SPX": "^GSPC",
    "NYA": "^NYA",
    "IXIC": "^IXIC",
    "RUT": "^RUT",
    "DJI": "^DJI",
}

# NYSE breadth data
BREADTH_SYMBOLS = {
    "NYAD": "^NYAD",    # Cumulative Advance-Decline Line
    "NAHL": "^NAHL",    # Net New Highs - New Lows
    "NYUPVOL": "^NYUPVOL",  # NYSE Up Volume
    "NYDNVOL": "^NYDNVOL",  # NYSE Down Volume
}

# MM breadth (if available directly via yfinance)
MM_BREADTH_SYMBOLS = {
    "MMFD": "$MMFD",    # % stocks above 200 MA (NYSE)
    "MMTW": "$MMTW",    # % stocks above 20 MA (NYSE)
    "MMFI": "$MMFI",    # % stocks above 50 MA (NYSE)
    "MMTH": "$MMTH",    # % stocks above 100 MA (NYSE)
}

# S&P 500 constituent fetch (used for computed MM breadth approximation)
SP500_INDEX = "^GSPC"

# Total NYSE issues (approximate, used for Hindenburg threshold)
TOTAL_NYSE_ISSUES = 3300

# All symbols needed for backfill
ALL_YFINANCE_SYMBOLS = (
    list(INDEX_SYMBOLS.values())
    + list(BREADTH_SYMBOLS.values())
)
