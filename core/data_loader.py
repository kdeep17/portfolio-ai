import yfinance as yf
import pandas as pd
from core.schema import MarketData
# UPDATED IMPORT: Added suffix constants to filter them out
from utils.constants import SECTOR_CAPTAINS, NON_EQUITY_SUFFIXES, NON_EQUITY_SERIES

def fetch_market_data(user_symbols: list[str]) -> MarketData:
    """
    Robust Data Loader [v3.2]
    - Restores fetching of critical fundamental data (PE, ROE).
    - Filters out SGBs (-GB) and Restricted (-BE) stocks to prevent 404 errors.
    """
    
    # 1. Prepare Symbols
    captain_symbols = set()
    for captains in SECTOR_CAPTAINS.values():
        captain_symbols.update(captains)
        
    unique_symbols = list(set([s.strip().upper() for s in user_symbols]) | captain_symbols)
    
    # Map Internal -> API Symbol
    symbol_map = {}
    api_tickers_list = []
    
    for sym in unique_symbols:
        # --- NEW FILTERING LOGIC ---
        # Skip Sovereign Gold Bonds (-GB) and Restricted Series (-BE)
        if sym.endswith(NON_EQUITY_SUFFIXES) or sym.endswith(NON_EQUITY_SERIES):
            continue
        # ---------------------------

        api_sym = sym if sym.endswith(".NS") or sym == "^NSEI" else f"{sym}.NS"
        symbol_map[api_sym] = sym
        api_tickers_list.append(api_sym)
            
    # Add Nifty for Beta Calculation
    if "^NSEI" not in api_tickers_list:
        api_tickers_list.append("^NSEI")
        symbol_map["^NSEI"] = "^NSEI"

    # Initialize Container
    data = MarketData()
    print(f"🔌 Connecting for {len(api_tickers_list)} symbols (Excluded SGB/BE)...")
    
    if not api_tickers_list:
        return data

    tickers = yf.Tickers(" ".join(api_tickers_list))

    # --- 2. BULK HISTORY FETCH (Risk Engine Data) ---
    try:
        print("   ↳ Fetching Price History...")
        history_bulk = tickers.history(period="1y", group_by='ticker')
        
        for api_sym in api_tickers_list:
            internal_sym = symbol_map.get(api_sym)
            if not internal_sym: continue
            
            try:
                # Handle Single Ticker vs Multi-Ticker return structure
                if len(api_tickers_list) == 1:
                    df_hist = history_bulk
                else:
                    df_hist = history_bulk.xs(api_sym, level=0, axis=1)
                
                if not df_hist.empty:
                    data.price_history[internal_sym] = df_hist
            except Exception:
                pass
    except Exception as e:
        print(f"   ⚠️ History fetch warning: {e}")

    # --- 3. DETAILED FUNDAMENTALS (Valuation/Thesis Data) ---
    print("   ↳ Fetching Deep Fundamentals (This may take a moment)...")
    
    for api_sym in api_tickers_list:
        internal_sym = symbol_map.get(api_sym)
        if not internal_sym: continue
        
        try:
            ticker = tickers.tickers[api_sym]
            
            # A. METADATA (CRITICAL RESTORATION)
            try:
                full_info = ticker.info
                # Fallback to fast_info if info fails (common YF bug)
                if not full_info:
                    fi = ticker.fast_info
                    full_info = {
                        "previousClose": fi.previous_close,
                        "marketCap": fi.market_cap,
                        "currency": fi.currency
                    }
                data.info[internal_sym] = full_info
            except Exception:
                data.info[internal_sym] = {}

            # B. FINANCIALS
            try:
                data.financials[internal_sym] = ticker.financials
            except:
                data.financials[internal_sym] = None

            try:
                data.balance_sheet[internal_sym] = ticker.balance_sheet
            except:
                data.balance_sheet[internal_sym] = None
                
            # C. NEWS
            try:
                data.news[internal_sym] = ticker.news
            except:
                data.news[internal_sym] = []

        except Exception as e:
            print(f"❌ Error processing {internal_sym}: {str(e)}")
            
    return data