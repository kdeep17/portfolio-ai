import pandas as pd
from utils.constants import SECTOR_MAP, SECTOR_CAPTAINS

# Weights for Capital Drag Calculation
W_THESIS = 0.50
W_VALUATION = 0.30
W_RISK = 0.20

THESIS_PENALTY = {"Intact": 0, "Weakening": 40, "Broken": 100}

def evaluate_switch_candidate(holding_symbol: str, candidate_symbol: str, market_data):
    """
    Performs a 'Head-to-Head' analysis between the current holding and a potential replacement.
    Returns a reason if the switch is mathematically superior.
    """
    # 1. Get Data for Both
    h_info = market_data.get_info(holding_symbol)
    c_info = market_data.get_info(candidate_symbol)
    
    if not c_info or not h_info:
        return None

    # 2. Extract Key Stats (Defensive)
    h_pe = h_info.get("trailingPE", 1000)
    c_pe = c_info.get("trailingPE", 1000)
    
    h_roe = h_info.get("returnOnEquity", 0)
    c_roe = c_info.get("returnOnEquity", 0)
    
    # 3. Logic: Is the Candidate "Objectively Better"?
    # Criteria A: "Quality Upgrade" -> Higher ROE at similar/lower PE
    if c_roe > (h_roe * 1.2) and c_pe < (h_pe * 1.1):
        return f"Quality Upgrade: {candidate_symbol} offers higher ROE ({round(c_roe*100,1)}% vs {round(h_roe*100,1)}%) at better/similar valuation."

    # Criteria B: "Valuation Relief" -> Massive discount for similar quality
    if c_pe < (h_pe * 0.6) and c_roe > (h_roe * 0.8):
        return f"Value Buy: {candidate_symbol} is significantly cheaper (PE {round(c_pe,1)} vs {round(h_pe,1)}) with comparable quality."

    return None


def run_opportunity_cost_engine(df, risk_data, valuation_data, thesis_data, market_data):
    """
    Identifies 'Dead Capital' (High Drag) and suggests 'Sector Captains' 
    as potential replacements if they offer superior risk-reward.
    """
    results = {}

    for _, row in df.iterrows():
        symbol = row["symbol"]
        
        # Skip non-equity
        if row.get("instrument_type", "Equity") != "Equity":
            continue

        # 1. Gather Inputs
        thesis = thesis_data.get(symbol, {})
        val = valuation_data.get(symbol, {})
        risk = risk_data["holding_risk"].get(symbol, {})

        thesis_status = thesis.get("status", "Unknown")
        val_stress = val.get("stress_score", 0)
        risk_score = risk.get("risk_contribution_score", 0)

        # 2. Compute "Capital Drag Score" (0 = Efficient, 100 = Dead Money)
        # If Thesis is Broken, Drag is automatically maxed out (100).
        if thesis_status == "Broken":
            drag_score = 100.0
        else:
            # Normalize inputs
            # Risk Score (0-20 typical) -> Scale to 0-100 approx
            risk_norm = min(risk_score * 5, 100) 
            
            drag_score = (
                (THESIS_PENALTY.get(thesis_status, 0) * W_THESIS) +
                (val_stress * W_VALUATION) +
                (risk_norm * W_RISK)
            )
            drag_score = round(min(drag_score, 100), 1)

        # 3. Determine Portfolio Action Bucket
        if drag_score >= 80:
            bucket = "Replace"  # Urgent attention
        elif drag_score >= 50:
            bucket = "Monitor"   # Watchlist
        else:
            bucket = "Defend"    # Keep holding

        # 4. Find Replacement Candidates (Only for 'Replace' or high 'Monitor' buckets)
        replacement_candidates = None
        
        if bucket == "Replace":
            sector = SECTOR_MAP.get(symbol, "Unknown")
            # We look at the SECTOR CAPTAINS (Market Leaders) as safe harbors
            potential_candidates = SECTOR_CAPTAINS.get(sector, [])
            
            valid_switches = []
            
            for candidate in potential_candidates:
                # Don't suggest buying what we already own (unless we want to add more, but let's keep it simple)
                if candidate == symbol or candidate in df["symbol"].values:
                    continue
                
                # Perform Head-to-Head Comparison
                rationale = evaluate_switch_candidate(symbol, candidate, market_data)
                
                if rationale:
                    valid_switches.append({
                        "symbol": candidate,
                        "note": rationale
                    })

            if valid_switches:
                replacement_candidates = {
                    "sector": sector,
                    "candidates": valid_switches[:2], # Top 2 options only
                    "disclaimer": "Switch suggestions based on fundamental comparison. Consult tax advisor regarding capital gains."
                }

        results[symbol] = {
            "capital_drag_score": drag_score,
            "bucket": bucket,
            "replacement_candidates": replacement_candidates
        }

    return results