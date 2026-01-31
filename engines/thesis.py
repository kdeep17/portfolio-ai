import pandas as pd
import numpy as np
from utils.constants import SECTOR_MAP

# --- CONFIGURATION ---
# Severity Weights (Higher = More Critical)
W_SOLVENCY = 3.0       # Bankruptcy risk
W_QUALITY = 2.0        # Earnings manipulation / Moat erosion
W_MOMENTUM = 1.0       # Standard growth slowdown
W_DILUTION = 0.5       # Shareholders getting diluted

def get_safe_metric(df: pd.DataFrame, possible_names: list) -> pd.Series:
    """
    Robust extractor: Tries multiple column aliases to handle YFinance inconsistencies.
    """
    if df is None or df.empty:
        return None
    
    for name in possible_names:
        if name in df.index:
            series = df.loc[name]
            return pd.to_numeric(series, errors='coerce').dropna()
    return None

def calculate_cagr(series: pd.Series, years: int = 3) -> float:
    """Calculates Compound Annual Growth Rate over N years."""
    if series is None or len(series) < years:
        return 0.0
    
    try:
        start_val = series.iloc[years-1] # Oldest
        end_val = series.iloc[0]         # Newest
        
        if start_val <= 0 or end_val <= 0: return 0.0
        
        return (end_val / start_val)**(1/(years-1)) - 1
    except:
        return 0.0

def evaluate_trend_structure(series: pd.Series) -> str:
    """
    Analyzes the structural direction of a metric.
    Returns: 'Improving', 'Stable', 'Deteriorating'
    """
    if series is None or len(series) < 2:
        return "Unknown"
    
    latest = series.iloc[0]
    prev = series.iloc[1]
    
    # Check for immediate shock (>15% drop)
    if latest < (prev * 0.85):
        return "Deteriorating"

    # Check for 3-year structural decline
    if len(series) >= 3:
        prev_2 = series.iloc[2]
        if latest < prev and prev < prev_2:
            return "Deteriorating"
            
    if latest > (prev * 1.05):
        return "Improving"
        
    return "Stable"

def run_thesis_engine(df, market_data):
    """
    Premium Thesis Engine:
    Evaluates Solvency, Earnings Quality, Capital Efficiency, and Growth.
    """
    thesis_output = {}

    for _, row in df.iterrows():
        symbol = row["symbol"]
        
        # 1. Skip Non-Equity
        if row.get("instrument_type", "Equity") != "Equity":
            thesis_output[symbol] = {"status": "Not Applicable", "drivers": []}
            continue

        # 2. Retrieve Data
        financials = market_data.get_financials(symbol)
        balance_sheet = market_data.get_balance_sheet(symbol)
        
        if financials is None or balance_sheet is None:
            thesis_output[symbol] = {"status": "Insufficient Data", "drivers": []}
            continue

        # 3. Extract Metrics (Expanded for Premium Analysis)
        # Income Statement
        rev = get_safe_metric(financials, ["Total Revenue", "Operating Revenue", "Revenue"])
        net_inc = get_safe_metric(financials, ["Net Income", "Net Income Common Stockholders"])
        op_inc = get_safe_metric(financials, ["Operating Income", "EBIT"])
        int_exp = get_safe_metric(financials, ["Interest Expense", "Interest Expense Non Operating"])
        
        # Balance Sheet
        debt = get_safe_metric(balance_sheet, ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"])
        equity = get_safe_metric(balance_sheet, ["Stockholders Equity", "Total Stockholder Equity"])
        receivables = get_safe_metric(balance_sheet, ["Net Receivables", "Accounts Receivable"])
        shares = get_safe_metric(balance_sheet, ["Share Issued", "Ordinary Shares Number"])

        # 4. Analysis Logic
        drivers = []
        deterioration_score = 0.0
        sector = SECTOR_MAP.get(symbol, "Unknown")
        is_financial = (sector == "Financials")
        
        # --- PILLAR 1: GROWTH & MOMENTUM ---
        rev_trend = evaluate_trend_structure(rev)
        inc_trend = evaluate_trend_structure(net_inc)
        
        if rev_trend == "Deteriorating":
            drivers.append("Top-line Stagnation: Revenue in structural decline")
            deterioration_score += W_MOMENTUM
            
        if inc_trend == "Deteriorating" and rev_trend != "Deteriorating":
            drivers.append("Profitless Growth: Revenue up but Profits down")
            deterioration_score += W_MOMENTUM

        # --- PILLAR 2: EARNINGS QUALITY (The "Cooking Books" Check) ---
        # If Receivables grow significantly faster than Revenue, sales might be artificial.
        if not is_financial and receivables is not None and rev is not None and len(rev) > 1:
            rev_growth = calculate_cagr(rev)
            rec_growth = calculate_cagr(receivables)
            
            if rev_growth > 0 and rec_growth > (rev_growth * 1.5):
                drivers.append(f"Earnings Quality Alert: Receivables growing 1.5x faster than Sales")
                deterioration_score += W_QUALITY

        # --- PILLAR 3: CAPITAL EFFICIENCY (ROE / ROIC) ---
        # Are they losing their competitive advantage?
        if net_inc is not None and equity is not None:
            try:
                # Align dates
                common = net_inc.index.intersection(equity.index)
                if len(common) >= 3:
                    roe_latest = net_inc[common[0]] / equity[common[0]]
                    roe_prev = net_inc[common[1]] / equity[common[1]]
                    roe_old = net_inc[common[2]] / equity[common[2]]
                    
                    if roe_latest < roe_prev and roe_prev < roe_old:
                        drivers.append("Moat Erosion: ROE has declined for 3 consecutive years")
                        deterioration_score += W_QUALITY
            except: pass

        # --- PILLAR 4: SOLVENCY & SAFETY ---
        if not is_financial:
            # Interest Coverage
            if op_inc is not None and int_exp is not None:
                curr_op = op_inc.iloc[0]
                curr_int = abs(int_exp.iloc[0])
                if curr_int > 0:
                    cov = curr_op / curr_int
                    if cov < 1.5:
                        drivers.append(f"Critical Solvency Risk: Interest Coverage {round(cov,1)}x")
                        deterioration_score += W_SOLVENCY
            
            # Dilution Check (Are they selling shares to survive?)
            if shares is not None and len(shares) >= 2:
                if shares.iloc[0] > (shares.iloc[1] * 1.05): # >5% dilution
                    drivers.append("Shareholder Dilution: Share count increased >5%")
                    deterioration_score += W_DILUTION
        else:
            # Financials: Check Book Value Erosion
            if evaluate_trend_structure(equity) == "Deteriorating":
                drivers.append("Capital Erosion: Book Value declining")
                deterioration_score += W_SOLVENCY

        # --- FINAL VERDICT ---
        if deterioration_score >= 3.0:
            status = "Broken"
        elif deterioration_score >= 1.0:
            status = "Weakening"
        else:
            status = "Intact"
            
        thesis_output[symbol] = {
            "status": status,
            "drivers": drivers,
            "sector": sector,
            "score": round(deterioration_score, 1)
        }

    return thesis_output