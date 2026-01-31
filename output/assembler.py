from datetime import datetime
import hashlib
import numpy as np
import pandas as pd

def _hash_dataframe(df) -> str:
    """Creates a stable fingerprint of holdings for auditability."""
    csv_bytes = df.to_csv(index=False).encode()
    return hashlib.sha256(csv_bytes).hexdigest()

def _sanitize(obj):
    """
    Recursively converts numpy types to native Python types for JSON serialization.
    Essential for Streamlit/API compatibility.
    Updated for NumPy 2.0 compatibility (uses abstract base classes).
    """
    # Check for integer types (covers int8, int16, int32, int64, uint8, etc.)
    if isinstance(obj, np.integer):
        return int(obj)
    
    # Check for floating types (covers float16, float32, float64)
    elif isinstance(obj, np.floating):
        return float(obj)
        
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
        
    elif isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
        
    elif isinstance(obj, list):
        return [_sanitize(v) for v in obj]
        
    return obj

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
    Assembles the 'Source of Truth' response object.
    Aggregates disparate engine signals into a cohesive narrative.
    """

    # =========================
    # 1. RUN METADATA
    # =========================
    run_id = datetime.utcnow().isoformat()

    # =========================
    # 2. PORTFOLIO SCORING
    # =========================
    # Calculate a weighted "Health Score" for the portfolio
    total_weighted_score = 0.0
    total_weight = 0.0
    
    for _, row in df.iterrows():
        sym = row.get("symbol")
        if row.get("instrument_type") == "Equity":
            w = row.get("weight_pct", 0)
            
            # 100 - Opportunity Cost Score = Efficiency Score
            # (If Op Cost is 0, Efficiency is 100. If Op Cost is 100, Efficiency is 0)
            op_data = opportunity_data.get(sym, {})
            drag = op_data.get("capital_drag_score", 50) 
            efficiency = 100 - drag
            
            total_weighted_score += (efficiency * w)
            total_weight += w
            
    portfolio_health_score = round(total_weighted_score / total_weight) if total_weight > 0 else 0

    # =========================
    # 3. EXECUTIVE SUMMARY
    # =========================
    try:
        risk_metrics = risk_data.get("portfolio_metrics", {})
        sector_info = risk_data.get("sector_exposure", {})
        
        # Count Actions
        actions = decision_data.get("portfolio_actions", {}).get("actions", [])
        action_counts = {"EXIT": 0, "TRIM": 0, "REPLACE": 0, "HOLD": 0}
        for a in actions:
            action_counts[a["action"]] = action_counts.get(a["action"], 0) + 1

        portfolio_summary = {
            "total_value": total_value,
            "net_worth_health_score": portfolio_health_score,
            "number_of_holdings": int(len(df[df["instrument_type"] == "Equity"])),
            "risk_profile": {
                "beta": risk_metrics.get("portfolio_beta"),
                "label": risk_metrics.get("risk_profile"),
                "cash_drag_pct": round(100.0 - total_weight, 2) # Remaining weight is cash
            },
            "top_sector": next(iter(sector_info.get("weights", {}))) if sector_info.get("weights") else "N/A",
            "action_summary": f"{len(actions)} Actions Suggested ({action_counts['EXIT']} Exit, {action_counts['REPLACE']} Replace)",
            "critical_flags": (
                risk_data.get("concentration", {}).get("flags", []) + 
                risk_data.get("sector_exposure", {}).get("flags", [])
            )
        }
    except Exception as e:
        print(f"Summary Assembly Error: {e}")
        portfolio_summary = {"error": str(e)}

    # =========================
    # 4. DETAILED HOLDINGS ANALYSIS
    # =========================
    holdings_analysis = []

    for _, row in df.iterrows():
        symbol = row.get("symbol")
        if row.get("instrument_type") != "Equity":
            continue

        try:
            # Null-safe extraction
            thesis = thesis_data.get(symbol) or {}
            val = valuation_data.get(symbol) or {}
            opp = opportunity_data.get(symbol) or {}
            risk = risk_data.get("holding_risk", {}).get(symbol) or {}
            decision = decision_data.get("holding_actions", {}).get(symbol) or {}

            holding_block = {
                "symbol": symbol,
                "meta": {
                    "sector": thesis.get("sector", "Unknown"),
                    "weight_pct": round(row.get("weight_pct", 0.0), 2),
                    "current_price": row.get("ltp", 0.0)
                },
                "fundamental_health": {
                    "status": thesis.get("status", "Unknown"),
                    "drivers": thesis.get("drivers", [])
                },
                "valuation": {
                    "rating": val.get("valuation_status", "Unknown"),
                    "score": val.get("stress_score", 0),
                    "context": val.get("reason", ""),
                    "benchmark": f"{val.get('primary_metric')} vs {val.get('benchmark_source')}"
                },
                "risk_profile": {
                    "contribution": risk.get("risk_contribution_score", 0),
                    "beta": risk.get("beta", 1.0),
                    "liquidity": risk.get("size_category", "Unknown"),
                    "tag": risk.get("risk_tag", "Low")
                },
                "efficiency": {
                    "capital_drag": opp.get("capital_drag_score", 0),
                    "action_bucket": opp.get("bucket", "Hold"),
                    "better_alternatives": opp.get("replacement_candidates")
                },
                "final_verdict": {
                    "action": decision.get("action", "HOLD"),
                    "rationale": decision.get("reason", ""),
                    "urgency": decision.get("urgency", "Low")
                }
            }

            holdings_analysis.append(holding_block)

        except Exception as e:
            print(f"Skipping {symbol} due to assembly error: {e}")
            continue

    # =========================
    # 5. FINAL PACKAGING (Sanitized)
    # =========================
    raw_output = {
        "run_metadata": {
            "run_id": run_id,
            "data_hash": _hash_dataframe(df),
            "generated_at_utc": run_id,
            "engine_version": "2.1 (NumPy 2.0 Compatible)"
        },
        "portfolio_summary": portfolio_summary,
        "strategic_actions": decision_data.get("portfolio_actions", {}).get("actions", []),
        "holdings_analysis": holdings_analysis,
        "market_intelligence": event_data or []
    }

    return _sanitize(raw_output)