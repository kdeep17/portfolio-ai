import pandas as pd
import time
import sys

# --- IMPORT ENGINES ---
from core.data_loader import fetch_market_data
from engines.risk import run_risk_engine
from engines.valuation import run_valuation_engine
from engines.thesis import run_thesis_engine
from engines.opportunity_cost import run_opportunity_cost_engine

# --- MOCK DATA ---
# We create a fake portfolio with a known "Bad Stock" to force a suggestion.
# Stock: IOC.NS (Often has low PE/High Div, but let's assume we want to swap it for testing)
# Or better: VEDL.NS (High Dividend, volatile) vs a stable compounder.
print("1. Creating Mock Portfolio...")
mock_df = pd.DataFrame([
    {
        "symbol": "IOC", 
        "instrument_type": "Equity", 
        "quantity": 100, 
        "avg_price": 100, 
        "ltp": 120, 
        "current_value": 12000, 
        "weight_pct": 100.0
    }
])

# --- DEBUGGING STEP 1: DATA FETCH ---
print("\n2. Fetching Market Data...")
symbols = mock_df["symbol"].tolist()
market_data = fetch_market_data(symbols)

# Check if we actually got fundamental data (The common point of failure)
info = market_data.info.get("IOC", {})
print(f"   [DEBUG] IOC Info Keys Found: {list(info.keys())[:5]}...") 
print(f"   [DEBUG] IOC ROE: {info.get('returnOnEquity')}")
print(f"   [DEBUG] IOC PE: {info.get('trailingPE')}")

if info.get('returnOnEquity') is None:
    print("   [CRITICAL WARNING] ROE is None. Yahoo Finance failed to fetch fundamentals.")
    print("   -> This is why swaps are blank. The engine assumes ROE=0 and fails the 'Quality Upgrade' check.")

# --- DEBUGGING STEP 2: PREREQUISITE ENGINES ---
print("\n3. Running Prerequisite Engines...")
risk_data = run_risk_engine(mock_df, market_data)
# Force a high stress score to trigger "Replace" bucket
valuation_data = {"IOC": {"stress_score": 90, "valuation_status": "Overvalued"}} 
# Force a broken thesis
thesis_data = {"IOC": {"status": "Weakening"}} 

# --- DEBUGGING STEP 3: OPPORTUNITY ENGINE ---
print("\n4. Running Opportunity Cost Engine (The Suspect)...")

# We modify the function call slightly to trace inside if possible, 
# but here we will inspect the output deeply.
opportunity_data = run_opportunity_cost_engine(
    mock_df, risk_data, valuation_data, thesis_data, market_data
)

result = opportunity_data.get("IOC", {})
print(f"\n   [RESULT] IOC Data:")
print(f"   -> Bucket: {result.get('bucket')} (Must be 'Replace' or 'Monitor')")
print(f"   -> Drag Score: {result.get('capital_drag_score')} (Must be > 60)")

candidates = result.get("replacement_candidates")
if candidates:
    print(f"   -> Sector Identified: {candidates.get('sector')}")
    print(f"   -> Candidates Found: {len(candidates.get('candidates', []))}")
    for cand in candidates.get("candidates", []):
        print(f"      * Symbol: {cand['symbol']}")
        print(f"      * Reason: {cand['note']}")
else:
    print("   [FAILURE] No replacement candidates generated.")
    
    # Trace WHY it failed
    from utils.constants import SECTOR_CAPTAINS, SECTOR_MAP
    from engines.opportunity_cost import map_yahoo_to_internal
    
    # 1. Sector Mapping Check
    y_info = market_data.info.get("IOC", {})
    mapped_sector = map_yahoo_to_internal(y_info)
    print(f"\n   [TRACE] Sector Mapping Logic:")
    print(f"   -> Yahoo Sector: {y_info.get('sector')}")
    print(f"   -> Yahoo Industry: {y_info.get('industry')}")
    print(f"   -> Mapped Internal Sector: {mapped_sector}")
    
    # 2. Captains Check
    captains = SECTOR_CAPTAINS.get(mapped_sector, [])
    print(f"   -> Captains for {mapped_sector}: {captains}")
    
    # 3. Evaluation Logic Check
    print(f"\n   [TRACE] switch_logic check:")
    if not captains:
        print("   -> No captains found for this sector. Engine defaults to empty.")
    else:
        print("   -> Captains exist. Problem is in 'evaluate_premium_switch'.")
        print("   -> Likely Cause: Candidate data (PE/ROE) is missing, or hurdles are too high.")