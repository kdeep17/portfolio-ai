from utils.constants import MAX_PORTFOLIO_ACTIONS

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
    Synthesizes signals from 4 specialist engines into concrete, prioritized actions.
    """

    # -------------------------
    # 1. Defensive Input Validation
    # -------------------------
    if not isinstance(risk_data, dict): raise ValueError("risk_data must be dict")
    if not isinstance(valuation_data, dict): raise ValueError("valuation_data must be dict")
    if not isinstance(thesis_data, dict): raise ValueError("thesis_data must be dict")
    if not isinstance(opportunity_data, dict): raise ValueError("opportunity_data must be dict")

    holding_actions = {}
    portfolio_actions = []

    # -------------------------
    # 2. Decision Logic Constants
    # -------------------------
    # Valuation Stress Thresholds
    STRESS_HIGH = 75
    STRESS_EXTREME = 90
    
    # Capital Efficiency Thresholds
    DRAG_CRITICAL = 80  # Dead money territory
    
    # Urgency Mapping
    URGENCY_MAP = {
        "EXIT": "Immediate", 
        "REPLACE": "High", 
        "TRIM": "Medium", 
        "WATCH": "Low",
        "HOLD": "Low"
    }

    # -------------------------
    # 3. Holding-Level Evaluation Loop
    # -------------------------
    for _, row in df.iterrows():
        symbol = row.get("symbol")
        if not symbol: continue

        # A. Default State
        action = "HOLD"
        reason = "Fundamentals intact, valuation reasonable."
        urgency = "Low"

        # B. Skip Non-Equity
        if row.get("instrument_type") != "Equity":
            holding_actions[symbol] = {"action": "HOLD", "reason": "Non-equity", "urgency": "Low"}
            continue

        # C. Gather Intelligence (Null-Safe)
        thesis = thesis_data.get(symbol, {})
        val = valuation_data.get(symbol, {})
        opp = opportunity_data.get(symbol, {})
        risk = risk_data.get("holding_risk", {}).get(symbol, {})

        # Extract Core Signals
        thesis_status = thesis.get("status", "Unknown")           # Broken, Weakening, Intact
        val_stress = val.get("stress_score", 50)                  # 0-100
        drag_score = opp.get("capital_drag_score", 0)             # 0-100
        risk_tag = risk.get("risk_tag", "Low")                    # Critical, High, Moderate
        
        # D. The Decision Matrix (Priority Order: Survival > Value > Efficiency)

        # --- LEVEL 1: SURVIVAL (Thesis Breakdown) ---
        if thesis_status == "Broken":
            action = "EXIT"
            reason = "Thesis Broken: Fundamental drivers have deteriorated significantly."
        
        # --- LEVEL 2: RISK MANAGEMENT (Liquidity/Concentration) ---
        elif risk_tag == "Critical (Liquidity)":
            action = "TRIM"
            reason = "Liquidity Risk: Position size too large for Small-Cap stock."
        elif risk_tag == "Critical (Volatility)":
            action = "TRIM"
            reason = "Volatility Risk: High Beta exposure exceeds risk limits."

        # --- LEVEL 3: CAPITAL EFFICIENCY (Dead Money) ---
        elif drag_score >= DRAG_CRITICAL:
            action = "REPLACE"
            reason = "Dead Capital: Stock is inefficient (High Valuation + Weakening Thesis)."
            
        # --- LEVEL 4: VALUATION DISCIPLINE ---
        elif val_stress >= STRESS_EXTREME:
            action = "TRIM"
            reason = "Extreme Valuation: Price has decoupled from fundamentals (Growth unsupported)."
        elif thesis_status == "Weakening" and val_stress >= STRESS_HIGH:
            action = "REPLACE"
            reason = "Double Whammy: Weakening fundamentals meet expensive valuation."

        # --- LEVEL 5: WATCHLIST (Yellow Flags) ---
        elif thesis_status == "Weakening":
            action = "WATCH"
            reason = "Monitor: Fundamentals softening, but valuation offers safety margin."
        elif val_stress >= STRESS_HIGH:
            action = "WATCH"
            reason = "Monitor: Valuation stretched, but growth/momentum is strong."

        # E. Store Decision
        holding_actions[symbol] = {
            "action": action,
            "reason": reason,
            "urgency": URGENCY_MAP.get(action, "Low"),
            "metrics": {
                "thesis": thesis_status,
                "val_stress": val_stress,
                "drag": drag_score
            }
        }

    # -------------------------
    # 4. Portfolio-Level Aggregation
    # -------------------------
    # Filter for actionable items (Ignore HOLD and WATCH for the "Top Actions" list)
    actionable_items = [
        (sym, data) for sym, data in holding_actions.items() 
        if data["action"] in ("EXIT", "REPLACE", "TRIM")
    ]

    # Sort by Severity (EXIT > REPLACE > TRIM)
    severity_rank = {"EXIT": 3, "REPLACE": 2, "TRIM": 1}
    
    actionable_items.sort(
        key=lambda x: severity_rank.get(x[1]["action"], 0), 
        reverse=True
    )

    # Populate Top Actions List
    for sym, data in actionable_items[:MAX_PORTFOLIO_ACTIONS]:
        portfolio_actions.append({
            "symbol": sym,
            "action": data["action"],
            "reason": data["reason"],
            "urgency": data["urgency"]
        })

    # -------------------------
    # 5. Final Return
    # -------------------------
    return {
        "portfolio_actions": {
            "do_nothing": len(portfolio_actions) == 0,
            "net_action_bias": "Optimize" if len(portfolio_actions) > 0 else "Hold",
            "actions": portfolio_actions
        },
        "holding_actions": holding_actions
    }