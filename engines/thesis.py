import pandas as pd
import numpy as np
from utils.constants import SECTOR_MAP

def get_safe_metric(df: pd.DataFrame, possible_names: list) -> pd.Series:
    """
    Robust extractor: Tries multiple column aliases (e.g., 'Total Revenue', 'Revenue')
    to handle YFinance's inconsistent naming across tickers.
    """
    if df is None or df.empty:
        return None
    
    for name in possible_names:
        if name in df.index:
            series = df.loc[name]
            # Ensure it's numeric and drop NaNs
            return pd.to_numeric(series, errors='coerce').dropna()
    return None


def evaluate_robust_trend(series: pd.Series) -> str:
    """
    Premium Trend Logic:
    1. Ignores minor noise (< 5% fluctuation).
    2. Flags 'Deteriorating' only on significant shocks (> 10% drop) 
       or consistent multi-year structural decline.
    """
    if series is None or len(series) < 2:
        return "Unknown"
    
    # yfinance financials are typically sorted [Latest, Previous, YearBefore...]
    latest = series.iloc[0]
    prev = series.iloc[1]
    
    # 1. Check for Multi-year structural decline (if 3 years data exists)
    if len(series) >= 3:
        prev_2 = series.iloc[2]
        # If Latest < Previous < 2YearsAgo -> Valid Downtrend
        if latest < prev and prev < prev_2:
             return "Deteriorating" 

    # 2. Check for Significant Recent Shock (>10% drop)
    # We allow a 10% buffer for cyclical volatility
    if latest < (prev * 0.90):
        return "Deteriorating"

    # 3. Check for Growth
    if latest > prev:
        return "Improving"
        
    return "Stable"


def run_thesis_engine(df, market_data):
    """
    Evaluates 'Business Momentum' using a 3-Statement Analysis.
    Uses Centralized MarketData (No internal API calls).
    """
    thesis_output = {}

    for _, row in df.iterrows():
        symbol = row["symbol"]
        
        # 1. Skip Non-Equity
        if row.get("instrument_type", "Equity") != "Equity":
            thesis_output[symbol] = {"status": "Not Applicable", "drivers": []}
            continue

        # 2. Retrieve Data from Central Store
        # (This assumes fetch_market_data has already run)
        financials = market_data.get_financials(symbol)
        balance_sheet = market_data.get_balance_sheet(symbol)
        
        if financials is None or balance_sheet is None:
            thesis_output[symbol] = {"status": "Insufficient Data", "drivers": []}
            continue

        # 3. Extract Key Metrics (Using Safe Aliases)
        rev = get_safe_metric(financials, ["Total Revenue", "Operating Revenue", "Revenue"])
        net_inc = get_safe_metric(financials, ["Net Income", "Net Income Common Stockholders"])
        op_inc = get_safe_metric(financials, ["Operating Income", "EBIT"])
        
        # Interest is often negative in data, we need absolute value later
        int_exp = get_safe_metric(financials, ["Interest Expense", "Interest Expense Non Operating"])
        
        debt = get_safe_metric(balance_sheet, ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"])
        equity = get_safe_metric(balance_sheet, ["Stockholders Equity", "Total Stockholder Equity"])

        # 4. Analysis Logic
        drivers = []
        deterioration_score = 0.0
        sector = SECTOR_MAP.get(symbol, "Unknown")
        
        # --- TEST A: TOP-LINE MOMENTUM (Revenue) ---
        if evaluate_robust_trend(rev) == "Deteriorating":
            drivers.append("Revenue momentum stalling (>10% drop or multi-year decline)")
            deterioration_score += 1.0
            
        # --- TEST B: BOTTOM-LINE QUALITY (Profit) ---
        if evaluate_robust_trend(net_inc) == "Deteriorating":
            drivers.append("Profitability under pressure")
            deterioration_score += 1.0

        # --- TEST C: OPERATIONAL EFFICIENCY (Margins) ---
        # Skip for Financials (Banks don't use 'Operating Margin' standardly)
        if sector != "Financials" and op_inc is not None and rev is not None:
             try:
                 # Align indices (intersection of dates)
                 common = op_inc.index.intersection(rev.index)
                 if len(common) >= 2:
                     curr_margin = op_inc[common[0]] / rev[common[0]]
                     prev_margin = op_inc[common[1]] / rev[common[1]]
                     
                     # Check for Margin Compression (>10% relative drop)
                     if curr_margin < (prev_margin * 0.9): 
                         drivers.append(f"Margin Compression ({round(curr_margin*100,1)}% vs {round(prev_margin*100,1)}%)")
                         deterioration_score += 1.0
             except: pass

        # --- TEST D: SOLVENCY & SAFETY (The "Blowup" Risk) ---
        
        if sector != "Financials":
            # 1. Interest Coverage Ratio (EBIT / Interest)
            if op_inc is not None and int_exp is not None:
                curr_op = op_inc.iloc[0]
                curr_int = abs(int_exp.iloc[0])
                
                if curr_int > 0:
                    cov = curr_op / curr_int
                    if cov < 1.5:
                        drivers.append(f"Critical Solvency Risk (Int. Cov {round(cov,1)}x < 1.5x)")
                        deterioration_score += 2.0 # HIGH SEVERITY (Potential Bankruptcy Risk)
                    elif cov < 3.0:
                        drivers.append(f"Balance Sheet Stress (Int. Cov {round(cov,1)}x < 3.0x)")
                        deterioration_score += 0.5

            # 2. Leverage (Debt/Equity)
            if debt is not None and equity is not None:
                curr_debt = debt.iloc[0]
                curr_eq = equity.iloc[0]
                if curr_eq > 0 and (curr_debt / curr_eq) > 2.0:
                     drivers.append("High Leverage (Debt > 2x Equity)")
                     deterioration_score += 0.5
        
        else: # Financials Specific Logic
            # For Banks, Capital Adequacy/Book Value is king
            if evaluate_robust_trend(equity) == "Deteriorating":
                drivers.append("Capital Erosion (Book Value declining)")
                deterioration_score += 2.0 # Critical for banks

        # --- FINAL VERDICT ---
        # Thresholds adjusted for the "Robust" logic
        # Since we filter noise, any flags are now more meaningful.
        
        if deterioration_score >= 2.5:
            status = "Broken"
        elif deterioration_score >= 1.0:
            status = "Weakening"
        else:
            status = "Intact"
            
        thesis_output[symbol] = {
            "status": status,
            "drivers": drivers,
            "sector": sector
        }

    return thesis_output