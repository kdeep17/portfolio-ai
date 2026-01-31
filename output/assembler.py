from datetime import datetime
import hashlib
import numpy as np
import pandas as pd

# --- SCORING WEIGHTS ---
W_FUNDAMENTAL = 0.40  # Thesis strength is paramount
W_EFFICIENCY  = 0.30  # Opportunity cost / ROE
W_VALUATION   = 0.20  # Margin of safety
W_RISK        = 0.10  # Volatility profile

def _hash_dataframe(df) -> str:
    """Creates a stable fingerprint of holdings for auditability."""
    try:
        csv_bytes = df.to_csv(index=False).encode()
        return hashlib.sha256(csv_bytes).hexdigest()
    except:
        return "hash_error"

def _sanitize(obj):
    """
    Recursively converts numpy/pandas types to native Python types.
    Ensures JSON serializability for the frontend/API.
    """
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    elif obj is None:
        return None
    return str(obj)

def calculate_premium_health_score(df, thesis_data, opportunity_data, valuation_data):
    """
    Computes a sophisticated 'Portfolio Quality Score' (0-100).
    """
    total_score = 0.0
    total_weight = 0.0

    for _, row in df.iterrows():
        sym = row.get("symbol")
        if row.get("instrument_type") != "Equity":
            continue
            
        w = row.get("weight_pct", 0)
        
        # 1. Fundamental Score (Thesis)
        # Intact=100, Weakening=50, Broken=0
        t_status = thesis_data.get(sym, {}).get("status", "Unknown")
        score_fund = 100 if t_status == "Intact" else (50 if t_status == "Weakening" else 0)

        # 2. Efficiency Score (Opportunity Cost)
        # Derived from Capital Drag (Lower drag = Higher efficiency)
        drag = opportunity_data.get(sym, {}).get("capital_drag_score", 50)
        score_eff = max(0, 100 - drag)

        # 3. Valuation Score
        # Derived from Stress Score (Lower stress = Higher comfort)
        stress = valuation_data.get(sym, {}).get("stress_score", 50)
        score_val = max(0, 100 - stress)

        # 4. Composite Holding Score
        holding_score = (
            (score_fund * W_FUNDAMENTAL) + 
            (score_eff * W_EFFICIENCY) + 
            (score_val * W_VALUATION) + 
            (50 * W_RISK) # Risk is neutral at holding level, managed at portfolio level
        )
        
        total_score += (holding_score * w)
        total_weight += w

    if total_weight == 0: return 0
    return int(round(total_score / total_weight))

def assemble_output(
    df,
    total_value,
    risk_data,
    valuation_data,
    thesis_data,
    opportunity_data,
    decision_data,
    event_data=None
) -> dict:
    """
    Assembles the 'Single Source of Truth' for the advisory interface.
    """

    # =========================
    # 1. METADATA & SCORING
    # =========================
    run_id = datetime.utcnow().isoformat()
    health_score = calculate_premium_health_score(df, thesis_data, opportunity_data, valuation_data)

    # =========================
    # 2. EXECUTIVE SUMMARY (RISK AWARE)
    # =========================
    try:
        r_metrics = risk_data.get("portfolio_metrics", {})
        conc = risk_data.get("concentration", {})
        
        # Calculate Cash Position
        equity_weight = df[df["instrument_type"] == "Equity"]["weight_pct"].sum()
        cash_pct = max(0.0, 100.0 - equity_weight)
        
        # Action Counts
        actions = decision_data.get("portfolio_actions", {}).get("actions", [])
        action_counts = {"EXIT": 0, "TRIM": 0, "REPLACE": 0}
        for a in actions:
            if a["action"] in action_counts:
                action_counts[a["action"]] += 1

        portfolio_summary = {
            "total_value": total_value,
            "health_score": health_score,
            "holdings_count": len(df),
            
            # The "Risk Dashboard"
            "risk_profile": {
                "label": r_metrics.get("risk_profile", "Unknown"),
                "beta": r_metrics.get("portfolio_beta", 1.0),
                "daily_var_95_amt": r_metrics.get("daily_var_95", 0), # Value at Risk
                "cash_position_pct": round(cash_pct, 1)
            },
            
            # The "Action Plan"
            "advisory_summary": {
                "total_actions": len(actions),
                "critical_actions": action_counts["EXIT"] + action_counts["REPLACE"],
                "breakdown": action_counts
            },
            
            # Alerts
            "critical_flags": conc.get("flags", []) + risk_data.get("sector_exposure", {}).get("flags", [])
        }
    except Exception as e:
        print(f"Assembly Error (Summary): {e}")
        portfolio_summary = {"error": "Failed to generate summary"}

    # =========================
    # 3. DETAILED HOLDINGS ANALYSIS
    # =========================
    holdings_analysis = []

    for _, row in df.iterrows():
        sym = row.get("symbol")
        
        # Support Non-Equity (SGB, ETFs) gently
        is_equity = row.get("instrument_type") == "Equity"
        
        try:
            # Null-Safe Extractors
            t_dat = thesis_data.get(sym, {})
            v_dat = valuation_data.get(sym, {})
            o_dat = opportunity_data.get(sym, {})
            r_dat = risk_data.get("holding_risk", {}).get(sym, {})
            d_dat = decision_data.get("holding_actions", {}).get(sym, {})

            holding_block = {
                "symbol": sym,
                "type": row.get("instrument_type"),
                "meta": {
                    "sector": t_dat.get("sector", "N/A"),
                    "weight_pct": round(row.get("weight_pct", 0), 2),
                    "current_price": row.get("ltp", 0),
                    "invested_val": row.get("current_value", 0)
                },
                # Only populate deep analytics for Equity
                "analytics": {
                    "thesis_status": t_dat.get("status", "N/A") if is_equity else "N/A",
                    "valuation_rating": v_dat.get("valuation_status", "N/A") if is_equity else "N/A",
                    "momentum_score": o_dat.get("momentum_health", 50) if is_equity else 0,
                    "risk_beta": r_dat.get("beta", 0) if is_equity else 0,
                    "var_contribution": r_dat.get("var_95_amt", 0)
                },
                "advisory": {
                    "action": d_dat.get("action", "HOLD"),
                    "rationale": d_dat.get("reason", ""),
                    "urgency": d_dat.get("urgency", "Low"),
                    "alternatives": o_dat.get("replacement_candidates")
                }
            }
            holdings_analysis.append(holding_block)

        except Exception as e:
            print(f"Skipping {sym}: {e}")
            continue

    # =========================
    # 4. FINAL PACKAGE
    # =========================
    output = {
        "metadata": {
            "run_id": run_id,
            "version": "Premium v2.0",
            "data_hash": _hash_dataframe(df)
        },
        "summary": portfolio_summary,
        "actions": decision_data.get("portfolio_actions", {}).get("actions", []),
        "holdings": holdings_analysis,
        "intelligence": event_data or []
    }

    return _sanitize(output)