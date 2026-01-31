import pandas as pd
from collections import defaultdict
from utils.constants import SECTOR_MAP, RISK_THRESHOLDS

# Constants for Market Cap Classification (in INR Crores)
MCAP_LARGE = 20000 * 10**7  # > 20k Cr
MCAP_MID = 5000 * 10**7     # > 5k Cr

def get_risk_profile(beta: float) -> str:
    if beta < 0.8: return "Conservative"
    if beta < 1.1: return "Moderate"
    if beta < 1.5: return "Aggressive"
    return "High Volatility"

def run_risk_engine(df: pd.DataFrame, market_data) -> dict:
    """
    Computes sophisticated risk diagnostics:
    1. Beta-Adjusted Portfolio Risk (Systemic Risk)
    2. Concentration Risk (Single Stock & Sector)
    3. Liquidity/Size Risk (Small Cap Over-exposure)
    """
    
    risk_output = {}
    
    # --- PRE-COMPUTATION: Enrich Data with Market Info ---
    # We map symbol -> {beta, mcap_category, risk_score}
    
    holdings_metrics = {}
    total_portfolio_beta = 0.0
    
    # Buckets for Size Analysis
    allocation_by_size = defaultdict(float)

    for _, row in df.iterrows():
        symbol = row["symbol"]
        weight_pct = row["weight_pct"]
        weight_dec = weight_pct / 100.0
        
        # 1. Determine Beta & Market Cap
        if row.get("instrument_type") == "Equity":
            info = market_data.get_info(symbol)
            
            # Beta Logic: Default to 1.0 (Market) if missing to avoid underestimating risk
            beta = info.get("beta")
            if beta is None: beta = 1.0
            
            # Market Cap Logic (info['marketCap'] is usually in base currency)
            mcap = info.get("marketCap", 0)
            if mcap >= MCAP_LARGE:
                size_cat = "Large Cap"
            elif mcap >= MCAP_MID:
                size_cat = "Mid Cap"
            else:
                size_cat = "Small Cap"
                
        else:
            # Non-Equity (Gold, Liquid Bees, etc.) -> Zero Beta, Cash Equivalent
            beta = 0.0
            size_cat = "Cash/Liquid"

        # 2. Risk Contribution Calculation
        # How much "pain" does this stock add? (Weight * Beta)
        risk_contribution = weight_pct * beta
        
        # 3. Portfolio Beta Accumulation
        total_portfolio_beta += (weight_dec * beta)
        
        # 4. Size Bucket Accumulation
        allocation_by_size[size_cat] += weight_pct

        holdings_metrics[symbol] = {
            "beta": round(beta, 2),
            "size_category": size_cat,
            "risk_contribution": risk_contribution
        }

    # --- ANALYSIS 1: CONCENTRATION RISKS ---
    sorted_df = df.sort_values("weight_pct", ascending=False)
    
    top1 = sorted_df.iloc[0]["weight_pct"] if not sorted_df.empty else 0
    top3 = sorted_df.head(3)["weight_pct"].sum()
    top5 = sorted_df.head(5)["weight_pct"].sum()

    concentration_flags = []
    
    # Hard Limits
    limit_single = RISK_THRESHOLDS.get("single_stock_high", 10.0)
    limit_top3 = RISK_THRESHOLDS.get("top3_high", 30.0)
    
    if top1 > limit_single:
        concentration_flags.append(f"Critical: Single stock exposure ({round(top1,1)}%) exceeds limit ({limit_single}%)")
    elif top1 > (limit_single * 0.8):
        concentration_flags.append(f"Warning: Single stock concentration high ({round(top1,1)}%)")

    if top3 > limit_top3:
        concentration_flags.append(f"Portfolio Top-Heavy: Top 3 holdings constitute {round(top3,0)}%")

    # --- ANALYSIS 2: SECTOR EXPOSURE ---
    sector_weights = defaultdict(float)
    for _, row in df.iterrows():
        sym = row["symbol"]
        sec = SECTOR_MAP.get(sym, "Unknown")
        sector_weights[sec] += row["weight_pct"]

    sector_flags = []
    for sec, w in sector_weights.items():
        if w > 35.0:
             sector_flags.append(f"Critical Overweight: {sec} ({round(w,1)}%)")
        elif w > 25.0:
             sector_flags.append(f"Concentrated: {sec} ({round(w,1)}%)")

    # --- ANALYSIS 3: SMALL CAP / LIQUIDITY RISK (Premium Feature) ---
    # High allocation to Small Caps is a distinct risk factor
    small_cap_exposure = allocation_by_size["Small Cap"]
    if small_cap_exposure > 30.0:
        concentration_flags.append(f"High Volatility Risk: {round(small_cap_exposure,1)}% in Small Caps")
    
    # Identify specific dangerous positions (High Weight + Small Cap)
    holding_risk_output = {}
    for sym, metrics in holdings_metrics.items():
        risk_tag = "Low"
        weight = df[df["symbol"] == sym]["weight_pct"].values[0]
        
        # Risk Tag Logic
        # Critical = Small Cap > 5% OR High Beta (>1.5) & High Weight (>5%)
        if metrics["size_category"] == "Small Cap" and weight > 5.0:
            risk_tag = "Critical (Liquidity)"
        elif metrics["risk_contribution"] > 12.0:
            risk_tag = "Critical (Volatility)" # e.g. 10% weight in 1.2 beta
        elif metrics["risk_contribution"] > 8.0:
            risk_tag = "High"
        elif metrics["risk_contribution"] > 4.0:
            risk_tag = "Moderate"

        holding_risk_output[sym] = {
            "risk_tag": risk_tag,
            "beta": metrics["beta"],
            "size_category": metrics["size_category"],
            "risk_contribution_score": round(metrics["risk_contribution"], 2)
        }

    # --- FINAL ASSEMBLY ---
    risk_output["concentration"] = {
        "top1_pct": round(top1, 2),
        "top3_pct": round(top3, 2),
        "flags": concentration_flags
    }

    risk_output["sector_exposure"] = {
        "weights": dict(sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)),
        "flags": sector_flags
    }
    
    risk_output["portfolio_metrics"] = {
        "portfolio_beta": round(total_portfolio_beta, 2),
        "risk_profile": get_risk_profile(total_portfolio_beta),
        "size_allocation": dict(allocation_by_size)
    }

    risk_output["holding_risk"] = holding_risk_output

    return risk_output