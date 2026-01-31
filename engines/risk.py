import pandas as pd
import numpy as np
from collections import defaultdict
from utils.constants import SECTOR_MAP, RISK_THRESHOLDS

# --- CONSTANTS ---
BENCHMARK_SYMBOL = "^NSEI"  # Nifty 50
TRADING_DAYS = 252
CONFIDENCE_LEVEL = 1.65     # 95% Confidence (Z-score)

def calculate_dynamic_metrics(stock_hist: pd.DataFrame, benchmark_hist: pd.DataFrame):
    """
    Calculates Realized Beta and Volatility using 1-year daily returns.
    Returns: (Beta, Annualized Volatility)
    """
    if stock_hist is None or benchmark_hist is None or stock_hist.empty or benchmark_hist.empty:
        return 1.0, 0.20 # Fallbacks: Beta 1.0, Vol 20%

    # 1. Align Data (Intersection of dates)
    # We use 'Close' prices. Ensure indexes are datetime.
    try:
        df = pd.DataFrame({
            'stock': stock_hist['Close'],
            'market': benchmark_hist['Close']
        }).dropna()

        if len(df) < 60: # Need at least 2-3 months of data for valid beta
            return 1.0, 0.20

        # 2. Calculate Log Returns
        # Log returns are additive and better for statistical analysis
        log_rets = np.log(df / df.shift(1)).dropna()

        # 3. Calculate Beta (Covariance / Variance)
        # Cov(Stock, Market) / Var(Market)
        cov_matrix = np.cov(log_rets['stock'], log_rets['market'])
        beta = cov_matrix[0, 1] / cov_matrix[1, 1]

        # 4. Calculate Annualized Volatility
        volatility = log_rets['stock'].std() * np.sqrt(TRADING_DAYS)
        
        return round(beta, 2), round(volatility, 2)

    except Exception as e:
        print(f"Risk Calc Error: {e}")
        return 1.0, 0.20


def run_risk_engine(df: pd.DataFrame, market_data) -> dict:
    """
    Quantitative Risk Engine.
    Uses raw price history to calculate VaR and Beta.
    """
    risk_output = {}
    
    # --- 1. PREP BENCHMARK ---
    # Try to find Nifty 50 in the fetched history
    # (Ensure your Data Loader fetches '^NSEI' or 'NIFTY 50.NS')
    nifty_hist = market_data.price_history.get(BENCHMARK_SYMBOL) 
    if nifty_hist is None:
        # Try finding it via alternative names if mapped differently
        nifty_hist = market_data.price_history.get("NIFTY 50.NS")

    # --- 2. HOLDING-LEVEL METRICS ---
    holdings_risk = {}
    total_weighted_beta = 0.0
    total_var_95 = 0.0
    
    # Aggregators
    sector_exposure = defaultdict(float)
    size_exposure = defaultdict(float)

    for _, row in df.iterrows():
        symbol = row["symbol"]
        weight_pct = row["weight_pct"]
        invested_val = row["current_value"]
        
        # A. Get Asset Class Specifics
        if row.get("instrument_type") == "Equity":
            # 1. Fetch History
            stock_hist = market_data.price_history.get(symbol)
            
            # 2. Calculate Real Metrics
            beta, vol = calculate_dynamic_metrics(stock_hist, nifty_hist)
            
            # 3. Calculate Value at Risk (VaR)
            # "How much could I lose in 1 day with 95% confidence?"
            # Formula: Value * Volatility (Daily) * Z-Score (1.65)
            daily_vol = vol / np.sqrt(TRADING_DAYS)
            var_value = invested_val * daily_vol * CONFIDENCE_LEVEL
            
            # 4. Market Cap Logic (Fallback to fast_info/info if needed)
            info = market_data.info.get(symbol, {})
            mcap = info.get("marketCap") or 0
            
            if mcap > 20000 * 10**7: size_cat = "Large Cap"
            elif mcap > 5000 * 10**7: size_cat = "Mid Cap"
            elif mcap > 0: size_cat = "Small Cap"
            else: size_cat = "Unknown" # Likely missing data
            
        else:
            # Non-Equity (Gold/Liquid/Cash)
            beta = 0.05 if "GB" in symbol else 0.0 # Gold has low beta, Cash 0
            vol = 0.10 if "GB" in symbol else 0.0
            var_value = invested_val * (vol/np.sqrt(TRADING_DAYS)) * 1.65
            size_cat = "Cash/Equiv"

        # B. Accumulate Portfolio Stats
        # Beta contribution = Weight * Beta
        total_weighted_beta += (weight_pct / 100) * beta
        
        # VaR Summation (Conservative approach: assuming perfect correlation 1.0)
        # In reality, diversification reduces this, but for risk alerts, better to overestimate.
        total_var_95 += var_value
        
        sector_exposure[SECTOR_MAP.get(symbol, "Other")] += weight_pct
        size_exposure[size_cat] += weight_pct

        # C. Generate Holding Risk Tag
        # Combine Volatility + Size + Weight
        risk_tag = "Low"
        
        # Logic: Small Cap with High Weight OR Extreme Volatility
        if size_cat == "Small Cap" and weight_pct > 7.0:
            risk_tag = "Critical (Liquidity)"
        elif vol > 0.40: # >40% annualized volatility
            risk_tag = "High Volatility"
        elif beta > 1.5 and weight_pct > 5.0:
            risk_tag = "Aggressive Exposure"
        elif size_cat == "Small Cap":
            risk_tag = "Moderate (Small Cap)"

        holdings_risk[symbol] = {
            "beta": beta,
            "volatility_annual": vol,
            "var_95_amt": round(var_value, 2),
            "size_category": size_cat,
            "risk_tag": risk_tag,
            "risk_contribution_score": round(beta * weight_pct, 2)
        }

    # --- 3. CONCENTRATION CHECKS ---
    # Sort for Top N analysis
    sorted_weights = sorted(df["weight_pct"].tolist(), reverse=True)
    top1 = sorted_weights[0] if sorted_weights else 0
    top3 = sum(sorted_weights[:3])

    flags = []
    
    # Check 1: Single Stock
    if top1 > RISK_THRESHOLDS.get("single_stock_high", 15):
        flags.append(f"Concentration Alert: Single stock is {round(top1,1)}% of portfolio")
        
    # Check 2: Small Cap Overload
    if size_exposure["Small Cap"] > 35.0:
        flags.append(f"Liquidity Risk: {round(size_exposure['Small Cap'],1)}% allocated to Small Caps")

    # Check 3: Sector Overload
    for sec, w in sector_exposure.items():
        if w > 35.0 and sec != "ETF": # Ignore ETFs in sector concentration
            flags.append(f"Sector Bias: {sec} is {round(w,1)}% of portfolio")


    # --- 4. FINAL ASSEMBLY ---
    
    # Determine Label
    if total_weighted_beta < 0.8: p_label = "Conservative"
    elif total_weighted_beta < 1.15: p_label = "Moderate"
    elif total_weighted_beta < 1.4: p_label = "Aggressive"
    else: p_label = "High Risk"

    risk_output["portfolio_metrics"] = {
        "portfolio_beta": round(total_weighted_beta, 2),
        "risk_profile": p_label,
        "daily_var_95": round(total_var_95, 2),
        "size_allocation": dict(size_exposure)
    }

    risk_output["concentration"] = {
        "top1_pct": top1,
        "top3_pct": top3,
        "flags": flags
    }
    
    risk_output["sector_exposure"] = {
        "weights": dict(sector_exposure),
        "flags": [] # Handled in concentration flags
    }

    risk_output["holding_risk"] = holdings_risk

    return risk_output