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

NON_EQUITY_SUFFIXES = ("-GB",)     # Sovereign Gold Bonds
NON_EQUITY_SERIES = ("-BE",)       # BE category stocks

def classify_instrument(symbol: str) -> str:
    if symbol.endswith(NON_EQUITY_SUFFIXES):
        return "SGB"
    if symbol.endswith(NON_EQUITY_SERIES):
        return "Restricted Equity"
    return "Equity"

# utils/constants.py

# Live benchmarks: We fetch these to gauge "Sector Sentiment"
SECTOR_CAPTAINS = {
    "Financials": ["HDFCBANK.NS", "ICICIBANK.NS"], # The heavyweights
    "IT": ["TCS.NS", "INFY.NS"],                   # The standard bearers
    "FMCG": ["HINDUNILVR.NS"],                     # The defensive anchor
    "Auto": ["MARUTI.NS"],                         # The cyclical leader
    "Energy": ["RELIANCE.NS"],                     # The conglomerate proxy
    "Defence": ["HAL.NS"],
    "Power": ["NTPC.NS"]
}

# Fallback values (Safety net only)
FALLBACK_SECTOR_PE = {
    "Financials": 18.0, 
    "IT": 26.0, 
    "FMCG": 55.0, 
    "Auto": 24.0, 
    "Energy": 20.0, 
    "Defence": 35.0,
    "Unknown": 20.0
}

SECTOR_MAP = {
    # Financials
    "360ONE": "Financials",
    "ABCAPITAL": "Financials",
    "BAJAJHFL": "Financials",
    "BAJFINANCE": "Financials",
    "HDFCBANK": "Financials",
    "HDFCLIFE": "Financials",
    "IEX": "Financials",
    "JIOFIN": "Financials",
    "KOTAKBANK": "Financials",
    "SBICARD": "Financials",
    "SBIN": "Financials",

    # IT / Telecom
    "HFCL": "Telecom",
    "KPITTECH": "IT",
    "MPHASIS": "IT",
    "NETWEB": "IT",
    "OPTIEMUS": "IT",  # Electronics / Hardware
    "PERSISTENT": "IT",
    "RAILTEL": "Telecom",
    "STLTECH": "Telecom",

    # Energy / Power / Oil
    "ATL": "Power",  # Adani Energy Solutions
    "IOC": "Energy",
    "NHPC": "Power",
    "OIL": "Energy",
    "RELIANCE": "Energy",
    "TATAPOWER": "Power",

    # Auto Components
    "MMFL": "Auto Components",
    "MOTHERSON": "Auto Components",
    "MSUMI": "Auto Components",
    "RANEHOLDIN": "Auto Components",
    "SONACOMS": "Auto Components",

    # FMCG / Consumer Staples
    "AVTNPL": "FMCG",
    "EIDPARRY": "FMCG",
    "GODREJAGRO": "FMCG",
    "ITC": "FMCG",
    "KRBL": "FMCG",
    "LTFOODS": "FMCG",
    "VBL": "FMCG",

    # Chemicals / Fertilizers
    "CHAMBLFERT": "Chemicals",
    "DEEPAKFERT": "Chemicals",
    "JUBLINGREA": "Chemicals",
    "LXCHEM": "Chemicals",
    "RCF": "Chemicals",
    "SHARDACROP": "Chemicals",
    "SUMICHEM": "Chemicals",

    # Capital Goods / Defence / Engineering
    "HAL": "Defence",
    "JASH": "Capital Goods",
    "KPIL": "Infrastructure",
    "RAYMOND": "Capital Goods",  # Core Engineering/Realty entity
    "SHAKTIPUMP": "Capital Goods",
    "TITAGARH": "Capital Goods",
    "WALCHANNAG": "Capital Goods",

    # Consumer Discretionary / Retail
    "CHALET": "Hotels",
    "RAYMONDLSL": "Retail",  # Lifestyle/Textiles
    "TRENT": "Retail",

    # Metals & Mining
    "HINDALCO": "Metals",
    "NATIONALUM": "Metals",

    # Materials / Packaging / Cement
    "EPL": "Materials",
    "ORIENTCEM": "Materials",
    "TIMETECHNO": "Materials",

    # Services / Logistics / Ports
    "ADANIENT": "Services",
    "ADANIPORTS": "Services",
    "ESSARSHPNG-BE": "Services",
    "IRCTC": "Services",
    "NAVKARCORP": "Services",

    # Realty
    "ANANTRAJ": "Realty",
    "RAYMONDREL": "Realty",

    # Healthcare
    "MANKIND": "Healthcare",

    # ETFs & Sovereign Gold Bonds (Commodities)
    "GOLDBEES": "ETF",
    "GOLDCASE": "ETF",
    "NIFTYBEES": "ETF",
    "SGBJUN31I-GB": "Commodities",
    "SGBMAY29I-GB": "Commodities",
    "SGBMR29XII-GB": "Commodities",
    "SGBSEP28VI-GB": "Commodities"
}

RISK_THRESHOLDS = {
    "single_stock_high": 15.0,   # %
    "top3_high": 45.0,
    "top5_high": 65.0
}


MAX_PORTFOLIO_ACTIONS = 10