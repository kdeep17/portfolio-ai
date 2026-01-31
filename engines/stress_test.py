import numpy as np
import pandas as pd

SIMULATION_DAYS = 252 # 1 Year
NUM_SIMULATIONS = 1000

def run_monte_carlo_engine(df, market_data, total_value):
    """
    Runs Monte Carlo simulations on the aggregated portfolio history.
    """
    # 1. Construct Portfolio Historical Returns
    weighted_returns = pd.DataFrame()
    
    for _, row in df.iterrows():
        sym = row["symbol"]
        if row["instrument_type"] != "Equity": continue
        
        hist = market_data.price_history.get(sym)
        if hist is None or hist.empty: continue
        
        # Calculate daily log returns
        daily_ret = np.log(hist['Close'] / hist['Close'].shift(1))
        weighted_returns[sym] = daily_ret * (row["weight_pct"] / 100)

    if weighted_returns.empty:
        return None

    # Aggregate to get Portfolio Daily Return history
    portfolio_daily_ret = weighted_returns.sum(axis=1).dropna()
    
    # 2. Calculate Drift and Volatility
    u = portfolio_daily_ret.mean()
    var = portfolio_daily_ret.var()
    drift = u - (0.5 * var)
    stdev = portfolio_daily_ret.std()

    # 3. Run Simulations
    # Formula: Pt = Pt-1 * exp(drift + stdev * Z)
    daily_returns = np.exp(drift + stdev * np.random.normal(0, 1, (SIMULATION_DAYS, NUM_SIMULATIONS)))
    
    price_paths = np.zeros_like(daily_returns)
    price_paths[0] = total_value
    
    for t in range(1, SIMULATION_DAYS):
        price_paths[t] = price_paths[t-1] * daily_returns[t]

    # 4. Analyze Results
    ending_values = price_paths[-1]
    worst_case = np.percentile(ending_values, 5) # 5th percentile (95% confidence)
    best_case = np.percentile(ending_values, 95)
    median_case = np.median(ending_values)

    return {
        "simulation_data": price_paths, # Raw paths for plotting
        "metrics": {
            "worst_case_1y": worst_case,
            "best_case_1y": best_case,
            "median_1y": median_case,
            "loss_probability": np.mean(ending_values < total_value) # % chance of losing money
        }
    }