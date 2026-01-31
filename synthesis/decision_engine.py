from utils.constants import MAX_PORTFOLIO_ACTIONS
from collections import defaultdict

# --- CONFIGURATION ---
# Urgency Levels
URGENCY_CRITICAL = "Critical"  # Immediate Action (Fraud, Thesis Break)
URGENCY_HIGH     = "High"      # Strategic Reallocation (Dead Money)
URGENCY_MEDIUM   = "Medium"    # Risk Control (Trimming)
URGENCY_LOW      = "Low"       # Maintenance

def _index_events(event_list: list) -> dict:
    """
    Indexes events by symbol for O(1) lookup during the decision loop.
    Prioritizes the most negative event if multiple exist.
    """
    if not event_list: return {}
    
    event_map = {}
    for e in event_list:
        sym = e["symbol"]
        # If we already have a Critical event for this symbol, don't overwrite with a minor one
        if sym in event_map and event_map[sym]["impact"] == "Governance Risk":
            continue
        event_map[sym] = e
    return event_map

def run_decision_engine(
    df,
    risk_data: dict,
    valuation_data: dict,
    thesis_data: dict,
    opportunity_data: dict,
    event_data: list | None = None
) -> dict:
    """
    The 'Central Nervous System'. 
    Synthesizes signals from 5 specialist engines into concrete, prioritized actions.
    Uses a 'Veto' system where Critical Risks override Value/Momentum signals.
    """

    # 1. Validation
    if not isinstance(risk_data, dict): raise ValueError("risk_data must be dict")
    
    holding_actions = {}
    portfolio_actions = []
    
    # 2. Index Events for fast lookup
    events_map = _index_events(event_data)

    # 3. Evaluation Loop
    for _, row in df.iterrows():
        symbol = row.get("symbol")
        if not symbol: continue
        
        # A. Default State
        action = "HOLD"
        reason = "Thesis intact, metrics within tolerance."
        urgency = URGENCY_LOW
        
        # B. Skip Non-Equity
        if row.get("instrument_type") != "Equity":
            holding_actions[symbol] = {"action": "HOLD", "reason": "Asset Class: Non-Equity", "urgency": "Low"}
            continue

        # C. Gather Intelligence
        thesis = thesis_data.get(symbol, {})
        val = valuation_data.get(symbol, {})
        opp = opportunity_data.get(symbol, {})
        risk = risk_data.get("holding_risk", {}).get(symbol, {})
        event = events_map.get(symbol)

        # Extract Signals
        thesis_status = thesis.get("status", "Unknown")           
        val_stress = val.get("stress_score", 50)                  
        drag_score = opp.get("capital_drag_score", 0)             
        mom_score = opp.get("momentum_health", 50) # New from Opportunity Engine
        risk_tag = risk.get("risk_tag", "Low")
        
        # D. THE DECISION HIERARCHY (The "Brain")
        
        # --- PRIORITY 1: EVENT RISKS (The Veto Layer) ---
        # Governance Fraud / Regulatory Bans trigger immediate exit regardless of price.
        if event and event["impact"] in ["Governance Risk", "Regulatory Hit"]:
            action = "EXIT"
            reason = f"CRITICAL EVENT: {event['headline']} ({event['impact']})"
            urgency = URGENCY_CRITICAL

        # --- PRIORITY 2: THESIS FAILURE ---
        elif thesis_status == "Broken":
            action = "EXIT"
            reason = "Thesis Broken: Structural deterioration in fundamentals."
            urgency = URGENCY_CRITICAL

        # --- PRIORITY 3: RISK BREACHES ---
        elif risk_tag == "Critical (Liquidity)":
            action = "TRIM"
            reason = "Liquidity Trap: Position size dangerous for Small Cap volume."
            urgency = URGENCY_HIGH
            
        elif risk_tag == "Critical (Volatility)":
            # Nuance: If Momentum is Strong, we Trim. If Weak, we Exit.
            if mom_score > 60:
                action = "TRIM"
                reason = "Risk Control: Trimming overweight position in volatile stock."
                urgency = URGENCY_MEDIUM
            else:
                action = "EXIT"
                reason = "Volatility Risk: High Beta without momentum support."
                urgency = URGENCY_HIGH

        # --- PRIORITY 4: CAPITAL EFFICIENCY (Dead Money) ---
        elif drag_score >= 85:
            # Check if we have a replacement ready
            candidates = opp.get("replacement_candidates")
            if candidates:
                action = "REPLACE"
                alt_sym = candidates["candidates"][0]["symbol"]
                reason = f"Dead Capital: Switch to {alt_sym} for better ROE/Efficiency."
                urgency = URGENCY_HIGH
            else:
                action = "EXIT"
                reason = "Dead Capital: Stock is efficiently dragging portfolio performance."
                urgency = URGENCY_MEDIUM

        # --- PRIORITY 5: VALUATION & MOMENTUM (The "Trade" Layer) ---
        elif val_stress >= 90: # Extreme Overvaluation
            if mom_score > 75:
                # "Ride the Bubble" but take chips off table
                action = "TRIM"
                reason = "Profit Booking: Valuation stretched, but momentum is strong. Trim to lock gains."
                urgency = URGENCY_MEDIUM
            else:
                # Bubble Bursting
                action = "EXIT"
                reason = "Valuation Bubble: Price disconnected from reality with fading momentum."
                urgency = URGENCY_HIGH

        elif thesis_status == "Weakening" and mom_score < 40:
            action = "EXIT"
            reason = "Falling Knife: Weakening fundamentals + Downtrend."
            urgency = URGENCY_HIGH
            
        elif val_stress >= 75 and thesis_status == "Intact":
             action = "WATCH"
             reason = "Monitor: Premium valuation, but quality is intact."

        # E. Store Decision
        holding_actions[symbol] = {
            "action": action,
            "reason": reason,
            "urgency": urgency,
            "meta": {
                "momentum": mom_score,
                "thesis": thesis_status
            }
        }

    # 4. Portfolio-Level Prioritization
    # We score actions to ensure the "Top 3" displayed are actually the most important
    
    action_score_map = {
        "EXIT": 100,
        "REPLACE": 80,
        "TRIM": 60,
        "WATCH": 10,
        "HOLD": 0
    }
    
    urgency_multiplier = {
        URGENCY_CRITICAL: 2.0,
        URGENCY_HIGH: 1.5,
        URGENCY_MEDIUM: 1.0,
        URGENCY_LOW: 0.5
    }

    scored_actions = []
    for sym, data in holding_actions.items():
        if data["action"] in ["HOLD", "WATCH"]: continue
        
        base_score = action_score_map.get(data["action"], 0)
        mult = urgency_multiplier.get(data["urgency"], 1.0)
        final_score = base_score * mult
        
        scored_actions.append((sym, data, final_score))

    # Sort by Score Descending
    scored_actions.sort(key=lambda x: x[2], reverse=True)

    for sym, data, score in scored_actions[:MAX_PORTFOLIO_ACTIONS]:
        portfolio_actions.append({
            "symbol": sym,
            "action": data["action"],
            "reason": data["reason"],
            "urgency": data["urgency"]
        })

    return {
        "portfolio_actions": {
            "do_nothing": len(portfolio_actions) == 0,
            "net_action_bias": "De-Risk" if any(a["action"]=="EXIT" for a in portfolio_actions) else "Optimize",
            "actions": portfolio_actions
        },
        "holding_actions": holding_actions
    }