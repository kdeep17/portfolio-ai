REQUIRED_HOLDINGS_COLUMNS = {
    "symbol",
    "quantity",
    "avg_price"
}

ZERODHA_COLUMN_MAP = {
    "Instrument": "symbol",
    "Qty.": "quantity",
    "Avg. cost": "avg_price",
    "LTP": "ltp",
    "Invested": "invested",
    "Cur. val": "current_value",
    "P&L": "pnl",
}

REQUIRED_ZERODHA_COLUMNS = set(ZERODHA_COLUMN_MAP.keys())

MAX_PORTFOLIO_ACTIONS = 3