import pandas as pd
import numpy as np
from utils.constants import SECTOR_MAP, SECTOR_CAPTAINS

# --- CONFIGURATION ---
W_THESIS = 0.45      
W_MOMENTUM = 0.20    
W_VALUATION = 0.20   
W_RISK = 0.15        

THESIS_PENALTY = {"Intact": 0, "Weakening": 40, "Broken": 100}

# LOWERED THRESHOLD: Make it easier to suggest swaps (10% improvement is enough)
SWITCH_HURDLE_PCT = 1.10

def map_yahoo_to_internal(yahoo_info: dict) -> str:
    """
    Intelligent mapping that uses Industry specificity to find the best peer.
    """
    sector = yahoo_info.get("sector", "")
    industry = yahoo_info.get("industry", "")
    
    # --- LEVEL 1: KEYWORD SCALPEL (High Specificity) ---
    if "Aerospace" in industry or "Defense" in industry: return "Defence"
    if "Marine" in industry or "Transport" in industry or "Logistics" in industry: return "Services"
    if "Construction" in industry or "Engineering" in industry: return "Infrastructure"
    if "Machinery" in industry or "Electrical Equipment" in industry or "Tools" in industry: return "Capital Goods"
    
    if "Hotel" in industry or "Resort" in industry or "Lodging" in industry: return "Hotels"
    if "Retail" in industry or "Apparel" in industry or "Luxury" in industry or "Department" in industry: return "Retail"
    if "Auto Parts" in industry: return "Auto Components"
    if any(x in industry for x in ["Auto", "Truck", "Vehicle"]): return "Auto"
    if "Electronics" in industry or "Components" in industry or "Appliances" in industry: return "Consumer Durables"

    if "Bank" in industry or "Credit" in industry or "Asset" in industry or "Insurance" in industry: return "Financials"

    if "Software" in industry or "Information" in industry or "Data" in industry or "Semiconductor" in industry: return "IT"
    if "Telecom" in industry: return "Telecom"

    if any(x in industry for x in ["Drug", "Biotech", "Health", "Pharma"]): return "Healthcare"
    if any(x in industry for x in ["Steel", "Copper", "Aluminum", "Metal", "Mining"]): return "Metals"
    if "Chemical" in industry: return "Chemicals"
    if "Building" in industry or "Cement" in industry: return "Materials"

    if "Oil" in industry or "Gas" in industry or "Coal" in industry: return "Energy"
    if "Utilities" in sector or "Power" in industry: return "Power"

    # --- LEVEL 2: BROAD SECTOR BACKSTOP ---
    if sector == "Financial Services": return "Financials"
    if sector == "Technology": return "IT"
    if sector == "Healthcare": return "Healthcare"
    if sector == "Energy": return "Energy"
    if sector == "Utilities": return "Power"
    if sector == "Consumer Defensive": return "FMCG"
    if sector == "Basic Materials": return "Metals" 
    if sector == "Real Estate": return "Realty"

    # --- LEVEL 3: INTELLIGENT FALLBACKS ---
    if sector == "Consumer Cyclical": return "Universal"
    if sector == "Industrials": return "Universal"

    return "Universal"

def get_momentum_score(price_history) -> float:
    """
    Calculates a 0-100 Momentum Score based on technical structure.
    """
    if price_history is None or price_history.empty or len(price_history) < 200:
        return 50.0

    try:
        closes = price_history['Close']
        current = closes.iloc[-1]
        ma_50 = closes.rolling(window=50).mean().iloc[-1]
        ma_200 = closes.rolling(window=200).mean().iloc[-1]
        
        score = 50.0
        if current > ma_200: score += 15
        else: score -= 15
        if current > ma_50: score += 10
        else: score -= 10
        if ma_50 > ma_200: score += 5 
        
        return max(0.0, min(100.0, score))
    except Exception:
        return 50.0

def evaluate_premium_switch(holding_sym: str, candidate_sym: str, market_data, holding_risk: dict, is_emergency: bool = False):
    """
    Generates 'Advisory Grade' rationales for switching stocks.
    """
    # 1. Get Data
    h_info = market_data.info.get(holding_sym, {})
    c_info = market_data.info.get(candidate_sym, {})
    c_hist = market_data.price_history.get(candidate_sym)
    
    if not c_info or not h_info: return None

    # 2. Extract Metrics (With Safety Defaults)
    h_roe = h_info.get("returnOnEquity") or 0.10
    c_roe = c_info.get("returnOnEquity") or 0.10
    
    h_pe = h_info.get("trailingPE") or 100.0
    c_pe = c_info.get("trailingPE") or 100.0
    
    h_peg = h_info.get("pegRatio") or 5.0
    c_peg = c_info.get("pegRatio") or 5.0

    # 3. EMERGENCY MODE (Broken Stock)
    if is_emergency:
        # If the holding is broken, we just need a stable ship (ROE > 12%).
        if c_roe > 0.12:
             return (f"🛡️ **Safety Switch**: {holding_sym} fundamentals are broken. Switch to **{candidate_sym}** "
                     f"to preserve capital in a sector leader (ROE {round(c_roe*100,1)}%).")

    # 4. Standard "Premium Upgrade" Logic
    quality_pass = False
    
    # Check A: ROE Upgrade
    if c_roe > (h_roe * SWITCH_HURDLE_PCT):
        quality_pass = True
        
    # Check B: Momentum Upgrade (Stop catching falling knives)
    c_mom = get_momentum_score(c_hist)
    h_mom = get_momentum_score(market_data.price_history.get(holding_sym))
    
    if h_mom < 30 and c_mom > 60: # Holding crashing, Candidate flying
        quality_pass = True
        
    if not quality_pass: return None 

    # 5. Value Check
    value_pass = False
    if c_pe < h_pe: value_pass = True
    elif c_peg < 1.5: value_pass = True
    elif is_emergency: value_pass = True
        
    if not value_pass: return None
    
    # 6. Momentum Check (Safety)
    if c_mom < 40: return None 

    # 7. THE VERDICT (Premium Strings)
    
    # Scenario A: GARP (Growth at Reasonable Price)
    if c_peg < h_peg and c_roe > h_roe:
        return (f"💎 **Strategic Upgrade**: **{candidate_sym}** is a superior compounder. "
                f"It offers higher capital efficiency (ROE {round(c_roe*100,1)}%) "
                f"at a better growth-adjusted price (PEG {c_peg}) than {holding_sym}.")

    # Scenario B: Deep Value
    if c_pe < (h_pe * 0.8):
        return (f"💰 **Valuation Arbitrage**: You are overpaying for {holding_sym} (PE {round(h_pe,1)}). "
                f"Switch to **{candidate_sym}** (PE {round(c_pe,1)}) to own similar quality at a 20%+ discount.")
                
    # Scenario C: Momentum Flip
    if h_mom < 30 and c_mom > 60:
         return (f"🚀 **Momentum Flip**: {holding_sym} is in a confirmed downtrend. "
                 f"Capital is rotating into **{candidate_sym}**, which shows strong institutional accumulation.")

    return (f"✅ **Quality Upgrade**: {candidate_sym} is the sector leader with superior fundamentals (ROE {round(c_roe*100,1)}%).")


def run_opportunity_cost_engine(df, risk_data, valuation_data, thesis_data, market_data):
    results = {}

    for _, row in df.iterrows():
        symbol = row["symbol"]
        if row.get("instrument_type", "Equity") != "Equity": continue

        # Gather Inputs
        thesis = thesis_data.get(symbol, {})
        val = valuation_data.get(symbol, {})
        risk = risk_data["holding_risk"].get(symbol, {})
        price_hist = market_data.price_history.get(symbol)

        thesis_status = thesis.get("status", "Unknown")
        val_stress = val.get("stress_score", 50)
        risk_score = risk.get("risk_contribution_score", 0)
        
        mom_score = get_momentum_score(price_hist)
        mom_drag = 100.0 - mom_score 

        # Compute Drag Score
        if thesis_status == "Broken":
            drag_score = 100.0
        else:
            risk_norm = min(risk_score * 5, 100)
            drag_score = (
                (THESIS_PENALTY.get(thesis_status, 0) * W_THESIS) +
                (val_stress * W_VALUATION) +
                (risk_norm * W_RISK) +
                (mom_drag * W_MOMENTUM)
            )
            drag_score = round(min(drag_score, 100), 1)

        # UPDATED THRESHOLDS [Lowered to catch more opportunities]
        if drag_score >= 80: bucket = "Replace"
        elif drag_score >= 50: bucket = "Monitor" 
        else: bucket = "Defend"

        replacement_candidates = None
        
        if bucket in ["Replace", "Monitor"]:
            sector = SECTOR_MAP.get(symbol, "Unknown")
            if sector == "Unknown":
                y_info = market_data.info.get(symbol, {})
                sector = map_yahoo_to_internal(y_info)
            
            potential_candidates = SECTOR_CAPTAINS.get(sector, [])
            if not potential_candidates:
                 potential_candidates = SECTOR_CAPTAINS.get("Universal", ["NIFTYBEES.NS"])

            valid_switches = []
            
            # Pass 'is_emergency' flag if bucket is Replace
            is_emergency = (bucket == "Replace")
            
            for candidate in potential_candidates:
                if candidate == symbol or candidate in df["symbol"].values: continue
                
                rationale = evaluate_premium_switch(
                    symbol, candidate, market_data, risk, is_emergency=is_emergency
                )
                
                if rationale:
                    valid_switches.append({"symbol": candidate, "note": rationale})

            if valid_switches:
                replacement_candidates = {
                    "sector": sector,
                    "candidates": valid_switches[:2],
                    "disclaimer": "Switch suggestions based on relative efficiency."
                }

        results[symbol] = {
            "capital_drag_score": drag_score,
            "momentum_health": round(mom_score, 1),
            "bucket": bucket,
            "replacement_candidates": replacement_candidates
        }

    return results