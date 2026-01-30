import yfinance as yf
import pandas as pd
import numpy as np
from utils.constants import SECTOR_MAP

def fetch_financial_trends(symbol: str):
    """
    Fetches comprehensive financial data for premium thesis evaluation.
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        financials = ticker.financials
        balance_sheet = ticker.balance_sheet

        # Defensive checks
        if financials is None or balance_sheet is None:
            return None
        
        if financials.empty or balance_sheet.empty:
            return None

        def safe_get_row(df, possible_labels):
            for label in possible_labels:
                if label in df.index:
                    series = df.loc[label].dropna()
                    if not series.empty:
                        return series
            return None

        # 1. CORE GROWTH METRICS
        revenue = safe_get_row(financials, ["Total Revenue", "Operating Revenue", "Revenue"])
        
        net_income = safe_get_row(financials, [
            "Net Income", "Net Income Common Stockholders", 
            "Net Income From Continuing And Discontinued Operation"
        ])

        # 2. OPERATIONAL EFFICIENCY METRICS
        # operating_income is crucial for margins and interest coverage
        operating_income = safe_get_row(financials, ["Operating Income", "EBIT"])

        # 3. SOLVENCY METRICS
        # Get Interest Expense (Absolute value often needed as YF reports negative)
        interest_expense = safe_get_row(financials, ["Interest Expense", "Interest Expense Non Operating"])

        total_debt = safe_get_row(balance_sheet, [
            "Total Debt", "Long Term Debt And Capital Lease Obligation"
        ])

        total_equity = safe_get_row(balance_sheet, [
            "Stockholders Equity", "Total Stockholder Equity", "Total Equity Gross Minority Interest"
        ])

        return {
            "revenue": revenue,
            "net_income": net_income,
            "operating_income": operating_income,
            "interest_expense": interest_expense,
            "total_debt": total_debt,
            "total_equity": total_equity
        }

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None


def evaluate_trend(series):
    """
    Direction check. Returns: Improving / Stable / Deteriorating
    """
    if series is None or len(series) < 2:
        return "Unknown"

    latest = series.iloc[0]
    previous = series.iloc[1]

    if latest > previous:
        return "Improving"
    elif latest < previous:
        return "Deteriorating"
    else:
        return "Stable"

def calculate_ratio_trend(numerator_series, denominator_series):
    """
    Helper to calculate a ratio (e.g., Margin = OpIncome / Revenue) 
    and evaluate its trend.
    """
    if (numerator_series is None or denominator_series is None or 
        len(numerator_series) < 2 or len(denominator_series) < 2):
        return "Unknown", 0.0

    # Align dates (intersection of indices)
    common_dates = numerator_series.index.intersection(denominator_series.index)
    if len(common_dates) < 2:
        return "Unknown", 0.0

    num = numerator_series.loc[common_dates]
    den = denominator_series.loc[common_dates]

    # Calculate Ratios
    # Avoid division by zero
    ratios = num / den.replace(0, np.nan)
    
    latest_ratio = ratios.iloc[0]
    prev_ratio = ratios.iloc[1]

    trend = "Stable"
    if latest_ratio > prev_ratio:
        trend = "Improving"
    elif latest_ratio < prev_ratio:
        trend = "Deteriorating"
        
    return trend, latest_ratio


def run_thesis_engine(df):
    thesis_output = {}

    for _, row in df.iterrows():
        symbol = row["symbol"]
        
        # 1. Skip non-equity
        if row.get("instrument_type", "Equity") != "Equity":
            thesis_output[symbol] = {"status": "Not Applicable", "drivers": []}
            continue

        # 2. Get Data
        data = fetch_financial_trends(symbol)
        if data is None:
            thesis_output[symbol] = {"status": "Insufficient Data", "drivers": []}
            continue

        drivers = []
        deterioration_count = 0
        sector = SECTOR_MAP.get(symbol, "Unknown")

        # --- TEST 1: REVENUE MOMENTUM ---
        revenue_trend = evaluate_trend(data["revenue"])
        if revenue_trend == "Deteriorating":
            drivers.append("Revenue growth weakening")
            deterioration_count += 1

        # --- TEST 2: PROFITABILITY MOMENTUM ---
        income_trend = evaluate_trend(data["net_income"])
        if income_trend == "Deteriorating":
            drivers.append("Net Profit decline")
            deterioration_count += 1

        # --- TEST 3: MARGIN PRESSURE (Premium Check) ---
        # (Operating Income / Revenue)
        # Skip for Financials (Margins calculated differently)
        if sector != "Financials":
            margin_trend, latest_margin = calculate_ratio_trend(data["operating_income"], data["revenue"])
            if margin_trend == "Deteriorating":
                drivers.append("Operating Margins contracting")
                deterioration_count += 1

        # --- TEST 4: RETURN ON EQUITY (ROE) (Quality Check) ---
        # (Net Income / Total Equity)
        roe_trend, latest_roe = calculate_ratio_trend(data["net_income"], data["total_equity"])
        
        # Logic: Declining ROE is bad, but extremely low ROE is also bad.
        if roe_trend == "Deteriorating":
            drivers.append("ROE (Return on Equity) declining")
            deterioration_count += 1
        
        # --- TEST 5: FINANCIAL SOLVENCY & STABILITY ---
        
        debt_series = data["total_debt"]
        equity_series = data["total_equity"]
        equity_trend = evaluate_trend(equity_series)
        
        # Get scalars safely
        latest_debt = debt_series.iloc[0] if debt_series is not None and not debt_series.empty else 0
        latest_equity = equity_series.iloc[0] if equity_series is not None and not equity_series.empty else 0

        # A. FINANCIAL SECTOR LOGIC
        if sector == "Financials":
            # Critical Test: Capital Erosion
            if equity_trend == "Deteriorating":
                drivers.append("Book Value/Capital eroding")
                deterioration_count += 2  # Weighted heavily for banks
            
            # Note: We skip Debt/Equity and Interest Coverage for Banks as they are not standard metrics

        # B. NON-FINANCIAL SECTOR LOGIC
        else:
            # Test: High Leverage (Debt > Equity)
            if latest_debt > 0 and latest_equity > 0:
                if latest_debt > latest_equity:
                    drivers.append(f"High Leverage (D/E > 1)")
                    deterioration_count += 1
            
            # Test: Interest Coverage Ratio (EBIT / Interest)
            # This detects 'Zombie Companies' that can't pay interest
            if data["operating_income"] is not None and data["interest_expense"] is not None:
                # Get scalar values for latest period
                op_inc = data["operating_income"].iloc[0]
                int_exp = abs(data["interest_expense"].iloc[0]) # Absolute value
                
                if int_exp > 0:
                    coverage_ratio = op_inc / int_exp
                    if coverage_ratio < 1.5:
                        drivers.append(f"Critical Solvency Risk (Int. Cov < 1.5x)")
                        deterioration_count += 2 # Major Red Flag
                    elif coverage_ratio < 3.0:
                        drivers.append(f"Weak Solvency (Int. Cov < 3x)")
                        deterioration_count += 0.5 # Warning sign

        # --- FINAL SCORING LOGIC ---
        # Adjusted thresholds for higher number of tests
        if deterioration_count >= 3:
            status = "Broken"
        elif deterioration_count >= 1: # Even 1-2 flags indicate weakening now
            status = "Weakening"
        else:
            status = "Intact"

        thesis_output[symbol] = {
            "status": status,
            "drivers": drivers,
            "sector": sector
        }

    return thesis_output