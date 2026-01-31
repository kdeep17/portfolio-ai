import pandas as pd
import numpy as np
from utils.constants import SECTOR_MAP, SECTOR_CAPTAINS

# --- CONFIGURATION ---
# Weights for Capital Drag Calculation
W_THESIS = 0.45      # Fundamental breakdown is the biggest red flag
W_MOMENTUM = 0.20    # "Don't catch a falling knife"
W_VALUATION = 0.20   # "Don't overpay"
W_RISK = 0.15        # "Don't bet the house"

THESIS_PENALTY = {"Intact": 0, "Weakening": 40, "Broken": 100}

# The "Switch Hurdle": A candidate must be X% better to justify tax/slippage costs
SWITCH_HURDLE_PCT = 1.15  # Candidate must offer 15% better metrics to trigger a switch

def get_momentum_score(price_history) -> float:
    """
    Calculates a 0-100 Momentum Score based on technical structure.
    0 = Crash Mode (Below all MAs), 100 = Bull Run (Above 200DMA).
    """
    if price_history is None or price_history.empty or len(price_history) < 200:
        return 50.0  # Neutral if no data

    try:
        closes = price_history['Close']
        current = closes.iloc[-1]
        ma_50 = closes.rolling(window=50).mean().iloc[-1]
        ma_200 = closes.rolling(window=200).mean().iloc[-1]
        
        score = 50.0
        
        # Long-term Trend (weight: 30)
        if current > ma_200: score += 15
        else: score -= 15
        
        # Medium-term Trend (weight: 20)
        if current > ma_50: score += 10
        else: score -= 10
        
        # Momentum Acceleration (weight: 10)
        if ma_50 > ma_200: score += 5  # Golden Cross territory
        
        return max(0.0, min(100.0, score))
        
    except Exception:
        return 50.0

def evaluate_premium_switch(holding_sym: str, candidate_sym: str, market_data, holding_risk: dict):
    # 1. Get Data
    h_info = market_data.info.get(holding_sym, {})
    c_info = market_data.info.get(candidate_sym, {})
    c_hist = market_data.price_history.get(candidate_sym)
    
    if not c_info or not h_info: return None

    # 2. Extract Metrics (THE FIX: Use 'or' to fallback if None)
    h_pe = h_info.get("trailingPE") or 100.0  # Assume expensive if missing
    c_pe = c_info.get("trailingPE") or 100.0
    
    h_roe = h_info.get("returnOnEquity") or 0.0
    c_roe = c_info.get("returnOnEquity") or 0.0
    
    h_peg = h_info.get("pegRatio") or 5.0
    c_peg = c_info.get("pegRatio") or 5.0
    
    # 3. Filter 1: The "Quality" Hurdle (ROE)
    # Candidate must have Better ROE OR similar ROE with much lower Beta
    quality_pass = False
    
    # If Candidate ROE is > 15% higher than Holding (The Switch Cost Hurdle)
    if c_roe > (h_roe * SWITCH_HURDLE_PCT):
        quality_pass = True
        
    if not quality_pass: return None # Fail fast

    # 4. Filter 2: The "Value" Check (PE / PEG)
    # Don't switch into an overvalued bubble
    value_pass = False
    if c_pe < h_pe: # Cheaper is good
        value_pass = True
    elif c_peg < 1.5: # If expensive, growth must justify it
        value_pass = True
        
    if not value_pass: return None
    
    # 5. Filter 3: The "Trend" Safety (Momentum)
    # Ensure we aren't suggesting a "Value Trap" (falling stock)
    c_mom_score = get_momentum_score(c_hist)
    if c_mom_score < 40: # Stock is in a downtrend
        return None 

    # 6. Construct The Verdict
    # If we reached here, it's a valid switch. Now we format the "Why".
    
    # Scenario A: Growth at a Reasonable Price (GARP) Upgrade
    if c_peg < h_peg and c_roe > h_roe:
        return (f"GARP Upgrade: {candidate_sym} offers higher capital efficiency "
                f"(ROE {round(c_roe*100,1)}%) and faster growth (PEG {c_peg}) "
                f"compared to your holding.")

    # Scenario B: Deep Value Switch
    if c_pe < (h_pe * 0.7):
        return (f"Valuation Arbitrage: {candidate_sym} trades at a 30%+ discount "
                f"(PE {round(c_pe,1)} vs {round(h_pe,1)}) while maintaining superior quality.")

    return (f"Quality Upgrade: {candidate_sym} is a sector leader with superior "
            f"fundamentals (ROE {round(c_roe*100,1)}%) and positive momentum.")


def run_opportunity_cost_engine(df, risk_data, valuation_data, thesis_data, market_data):
    """
    Identifies 'Dead Capital' using a Multi-Factor Capital Drag Model.
    Suggests swaps only if the 'Hurdle Rate' is met.
    """
    results = {}

    for _, row in df.iterrows():
        symbol = row["symbol"]
        
        if row.get("instrument_type", "Equity") != "Equity":
            continue

        # 1. Gather Inputs
        thesis = thesis_data.get(symbol, {})
        val = valuation_data.get(symbol, {})
        risk = risk_data["holding_risk"].get(symbol, {})
        price_hist = market_data.price_history.get(symbol)

        thesis_status = thesis.get("status", "Unknown")
        val_stress = val.get("stress_score", 50)
        risk_score = risk.get("risk_contribution_score", 0)
        
        # 2. Compute "Momentum Drag" (New Factor)
        # If stock is crashing (Momentum < 30), Drag increases significantly
        mom_score = get_momentum_score(price_hist)
        mom_drag = 100.0 - mom_score # Low momentum = High drag

        # 3. Compute Total "Capital Drag Score"
        if thesis_status == "Broken":
            drag_score = 100.0
        else:
            # Normalize inputs to 0-100 scale
            risk_norm = min(risk_score * 5, 100)
            
            # Weighted Multi-Factor Model
            drag_score = (
                (THESIS_PENALTY.get(thesis_status, 0) * W_THESIS) +
                (val_stress * W_VALUATION) +
                (risk_norm * W_RISK) +
                (mom_drag * W_MOMENTUM)
            )
            drag_score = round(min(drag_score, 100), 1)

        # 4. Determine Action Bucket
        if drag_score >= 85:
            bucket = "Replace"   # Critical inefficiency
        elif drag_score >= 60:
            bucket = "Monitor"   # Underperformance warning
        else:
            bucket = "Defend"    # Efficient capital

        # 5. Find Replacement Candidates (The "Alpha Search")
        replacement_candidates = None
        
        if bucket in ["Replace", "Monitor"]:
            sector = SECTOR_MAP.get(symbol, "Unknown")
            potential_candidates = SECTOR_CAPTAINS.get(sector, [])
            
            valid_switches = []
            
            for candidate in potential_candidates:
                # Avoid self-reference
                if candidate == symbol or candidate in df["symbol"].values:
                    continue
                
                # Run the Premium Filter
                rationale = evaluate_premium_switch(
                    symbol, candidate, market_data, risk
                )
                
                if rationale:
                    valid_switches.append({
                        "symbol": candidate,
                        "note": rationale
                    })

            if valid_switches:
                replacement_candidates = {
                    "sector": sector,
                    "candidates": valid_switches[:2], # Strict curation (Top 2 only)
                    "disclaimer": "Switch suggestions incorporate 'Hurdle Rate' logic (Cost of switching)."
                }

        results[symbol] = {
            "capital_drag_score": drag_score,
            "momentum_health": round(mom_score, 1),
            "bucket": bucket,
            "replacement_candidates": replacement_candidates
        }

    return results