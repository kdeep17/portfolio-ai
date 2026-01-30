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

SECTOR_MAP = {
    "360ONE": "Financials",
    "ABCAPITAL": "Financials",
    "ADANIENT": "Services",
    "ADANIPORTS": "Services",
    "ANANTRAJ": "Realty",
    "ATL": "Energy",
    "AVTNPL": "Consumer Staples",
    "BAJAJHFL": "Financials",
    "BAJFINANCE": "Financials",
    "CHALET": "Consumer Discretionary",
    "CHAMBLFERT": "Chemicals",
    "DEEPAKFERT": "Chemicals",
    "EIDPARRY": "Consumer Staples",
    "EPL": "Materials",
    "ESSARSHPNG-BE": "Services",
    "GODREJAGRO": "Consumer Staples",
    "GOLDBEES": "ETF",
    "GOLDCASE": "ETF",
    "HAL": "Defence",
    "HDFCBANK": "Financials",
    "HDFCLIFE": "Financials",
    "HFCL": "Telecommunication",
    "HINDALCO": "Metals & Mining",
    "IEX": "Financials",
    "IOC": "Energy",
    "IRCTC": "Services",
    "ITC": "Consumer Staples",
    "JASH": "Capital Goods",
    "JIOFIN": "Financials",
    "JUBLINGREA": "Chemicals",
    "KOTAKBANK": "Financials",
    "KPIL": "Capital Goods",
    "KPITTECH": "IT",
    "KRBL": "Consumer Staples",
    "LTFOODS": "Consumer Staples",
    "LXCHEM": "Chemicals",
    "MANKIND": "Healthcare",
    "MMFL": "Auto Components",
    "MOTHERSON": "Auto Components",
    "MPHASIS": "IT",
    "MSUMI": "Auto Components",
    "NATIONALUM": "Metals & Mining",
    "NAVKARCORP": "Services",
    "NETWEB": "IT",
    "NHPC": "Energy",
    "NIFTYBEES": "ETF",
    "OIL": "Energy",
    "OPTIEMUS": "IT",
    "ORIENTCEM": "Materials",
    "PERSISTENT": "IT",
    "RAILTEL": "Telecommunication",
    "RANEHOLDIN": "Auto Components",
    "RAYMOND": "Capital Goods",
    "RAYMONDLSL": "Consumer Discretionary",
    "RAYMONDREL": "Realty",
    "RCF": "Chemicals",
    "RELIANCE": "Energy",
    "SBICARD": "Financials",
    "SBIN": "Financials",
    "SGBJUN31I-GB": "Commodities",
    "SGBMAY29I-GB": "Commodities",
    "SGBMR29XII-GB": "Commodities",
    "SGBSEP28VI-GB": "Commodities",
    "SHAKTIPUMP": "Capital Goods",
    "SHARDACROP": "Chemicals",
    "SONACOMS": "Auto Components",
    "STLTECH": "Telecommunication",
    "SUMICHEM": "Chemicals",
    "TATAPOWER": "Energy",
    "TIMETECHNO": "Materials",
    "TITAGARH": "Capital Goods",
    "TRENT": "Consumer Discretionary",
    "VBL": "Consumer Staples",
    "WALCHANNAG": "Capital Goods"
}

RISK_THRESHOLDS = {
    "single_stock_high": 15.0,   # %
    "top3_high": 45.0,
    "top5_high": 65.0
}


MAX_PORTFOLIO_ACTIONS = 3