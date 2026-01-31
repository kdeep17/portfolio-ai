import pandas as pd
import numpy as np
from pypfopt import risk_models, expected_returns
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices

def _prepare_price_matrix(df, market_data):
    """
    Converts individual stock histories into a single Price Matrix (Date x Ticker).
    """
    price_frames = []
    valid_symbols = []

    for _, row in df.iterrows():
        sym = row["symbol"]
        if row["instrument_type"] != "Equity":
            continue
            
        hist = market_data.price_history.get(sym)
        if hist is not None and not hist.empty:
            # Extract Close prices and rename column to symbol
            series = hist["Close"].rename(sym)
            price_frames.append(series)
            valid_symbols.append(sym)

    if not price_frames:
        return None, []

    # Combine into one DataFrame and handle missing data
    price_matrix = pd.concat(price_frames, axis=1).dropna()
    return price_matrix, valid_symbols

def run_optimization_engine(df, market_data, current_portfolio_value):
    """
    Calculates the Efficient Frontier to find optimal weights.
    """
    prices, symbols = _prepare_price_matrix(df, market_data)
    
    if prices is None or len(symbols) < 2:
        return {"status": "Skipped", "message": "Need at least 2 stocks with history"}

    try:
        # 1. Calculate Expected Returns (mu) and Sample Covariance (S)
        mu = expected_returns.mean_historical_return(prices)
        S = risk_models.sample_cov(prices)

        # 2. Optimize for Maximum Sharpe Ratio
        ef = EfficientFrontier(mu, S)
        raw_weights = ef.max_sharpe()
        cleaned_weights = ef.clean_weights()

        # 3. Calculate Expected Performance
        perf = ef.portfolio_performance(verbose=False)
        
        # 4. Generate Discrete Allocation (How many shares to buy?)
        latest_prices = get_latest_prices(prices)
        da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=current_portfolio_value)
        allocation, leftover = da.greedy_portfolio()

        return {
            "status": "Success",
            "optimal_weights": cleaned_weights,
            "metrics": {
                "expected_return": perf[0],
                "volatility": perf[1],
                "sharpe_ratio": perf[2]
            },
            "suggested_allocation": allocation
        }

    except Exception as e:
        return {"status": "Error", "message": str(e)}