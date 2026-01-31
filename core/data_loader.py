import yfinance as yf
from core.schema import MarketData
from utils.constants import SECTOR_CAPTAINS

def fetch_market_data(user_symbols: list[str]) -> MarketData:
    """
    Fetches all required data for the portfolio + sector captains in ONE batch request.
    Handles symbol normalization (.NS suffix) ensuring robust mapping.
    """
    
    # 1. Gather Sector Captains (avoid duplicates)
    captain_symbols = set()
    for captains in SECTOR_CAPTAINS.values():
        captain_symbols.update(captains)
        
    # 2. Merge with User Symbols
    # We use a set to ensure uniqueness across both lists
    # Clean inputs: Strip whitespace and upper case
    unique_symbols = set([s.strip().upper() for s in user_symbols]) | captain_symbols
    
    # 3. Create Mapping: Internal Symbol -> Yahoo Ticker
    # This prevents the "zip" bug. We track exactly what to call API with.
    symbol_map = {}
    for sym in unique_symbols:
        if sym.endswith(".NS"):
            symbol_map[sym] = sym
        else:
            symbol_map[sym] = f"{sym}.NS"
            
    # 4. Batch Fetch
    api_tickers = list(symbol_map.values())
    print(f"🔌 Connecting to API for {len(api_tickers)} symbols...")
    
    # Use yfinance Tickers object
    tickers = yf.Tickers(" ".join(api_tickers))
    
    # 5. Populate Data Object
    data = MarketData()
    
    for internal_sym, api_sym in symbol_map.items():
        try:
            # Access the specific ticker object
            ticker = tickers.tickers[api_sym]
            
            # --- Fast Data (Metadata) ---
            # info usually triggers a request. If it fails, whole ticker is likely invalid.
            try:
                data.info[internal_sym] = ticker.info
            except Exception:
                # If info fetch fails, skip this ticker
                print(f"⚠️ Info fetch failed for {internal_sym}")
                continue
            
            # --- Heavy Data (Financials) ---
            # Wrap individually so one failure doesn't break the rest
            try:
                data.financials[internal_sym] = ticker.financials
            except Exception:
                data.financials[internal_sym] = None
            
            try:
                data.balance_sheet[internal_sym] = ticker.balance_sheet
            except Exception:
                data.balance_sheet[internal_sym] = None

            # --- News ---
            try:
                data.news[internal_sym] = ticker.news
            except Exception:
                data.news[internal_sym] = []
            
        except Exception as e:
            print(f"⚠️ Critical fetch error for {internal_sym}: {e}")
            
    return data