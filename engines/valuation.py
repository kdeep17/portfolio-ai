import numpy as np
import pandas as pd
from utils.constants import SECTOR_MAP, SECTOR_CAPTAINS, FALLBACK_SECTOR_PE

def run_valuation_engine(df, market_data):
    """
    Computes valuation stretch using Dynamic Sector Benchmarking.
    OPTIMIZED: Pre-calculates sector benchmarks to avoid redundant lookups.
    """

    valuation_output = {}

    # --- PHASE 1: PRE-CALCULATE SECTOR BENCHMARKS ---
    # Identify all unique sectors in the user's portfolio first
    unique_sectors = set()
    for sym in df["symbol"]:
        unique_sectors.add(SECTOR_MAP.get(sym, "Unknown"))

    # Cache benchmarks for these sectors to avoid re-calculating inside the main loop
    sector_benchmarks_cache = {}

    for sector in unique_sectors:
        # 1. Identify Captains
        captains = SECTOR_CAPTAINS.get(sector, [])
        pe_values = []
        pb_values = []

        # 2. Fetch Captain Data (Once per sector)
        for cap_symbol in captains:
            # Handle suffix safety (try both raw and .NS)
            info = market_data.get_info(cap_symbol)
            if not info:
                # Fallback to appending .NS if the raw symbol didn't return info
                info = market_data.get_info(f"{cap_symbol}.NS")
            
            if info:
                pe = info.get("trailingPE")
                pb = info.get("priceToBook")
                # Filter out None and negative values (unprofitable companies shouldn't set the PE bar)
                if pe and pe > 0: pe_values.append(pe)
                if pb and pb > 0: pb_values.append(pb)
        
        # 3. Compute Medians or Fallbacks
        # PE Benchmark Calculation
        if pe_values:
            bench_pe = np.median(pe_values)
            source_pe = "Live Sector Captains"
        else:
            bench_pe = FALLBACK_SECTOR_PE.get(sector, 20.0)
            source_pe = "Static Market Baseline"

        # PB Benchmark Calculation (Default fallback 3.0 if no captains)
        if pb_values:
            bench_pb = np.median(pb_values)
            source_pb = "Live Sector Captains"
        else:
            bench_pb = 3.0
            source_pb = "Static Market Baseline"

        sector_benchmarks_cache[sector] = {
            "pe": (bench_pe, source_pe),
            "pb": (bench_pb, source_pb)
        }

    # --- PHASE 2: EVALUATE HOLDINGS ---
    # Now we iterate through the portfolio. Since benchmarks are cached, this is fast.
    
    for _, row in df.iterrows():
        symbol = row["symbol"]
        
        # 1. Skip Non-Equity
        if row.get("instrument_type", "Equity") != "Equity":
            valuation_output[symbol] = {
                "valuation_status": "Not Applicable",
                "stress_score": 0,
                "reason": "Non-equity instrument"
            }
            continue

        # 2. Get Stock Data
        info = market_data.get_info(symbol)
        sector = SECTOR_MAP.get(symbol, "Unknown")
        
        # Defensively get metrics
        pe = info.get("trailingPE")
        pb = info.get("priceToBook")
        peg = info.get("pegRatio")
        
        # 3. Determine Primary Metric (Financials vs Others)
        is_financial = (sector == "Financials")
        
        if is_financial:
            primary_val = pb
            metric_name = "P/B"
            # Retrieve cached benchmark
            benchmark_val, benchmark_source = sector_benchmarks_cache.get(sector, {}).get("pb", (3.0, "Fallback"))
        else:
            primary_val = pe
            metric_name = "P/E"
            # Retrieve cached benchmark
            benchmark_val, benchmark_source = sector_benchmarks_cache.get(sector, {}).get("pe", (20.0, "Fallback"))

        # 4. Logic Gates
        status = "Unknown"
        stress_score = 50
        reason = ""

        # A. Missing Data Check
        if primary_val is None:
            status = "Insufficient Data"
            stress_score = 0
            reason = f"Missing {metric_name} data"
        
        # B. Valid Data Analysis
        else:
            # Calculate Premium/Discount
            ratio = primary_val / benchmark_val if benchmark_val else 1.0
            
            # --- TIER 1: Undervalued ---
            if ratio < 0.75: # >25% discount
                status = "Undervalued"
                stress_score = 30
                reason = f"Trading at discount to {benchmark_source} ({metric_name} {round(primary_val,1)} vs {round(benchmark_val,1)})"

            # --- TIER 2: Fair Value ---
            elif 0.75 <= ratio <= 1.25:
                status = "Fair Value"
                stress_score = 50
                reason = f"Aligned with {benchmark_source}"

            # --- TIER 3: Expensive (Requires Growth Defense) ---
            else:
                # Check PEG Ratio (The "Growth Defense")
                # PEG < 1.5 is generally acceptable for high growth
                is_growth_justified = (peg is not None and 0 < peg < 1.5)
                
                if is_growth_justified:
                    status = "Justified Premium"
                    stress_score = 60 # Elevated but not critical
                    reason = f"Premium valuations supported by growth (PEG {peg})"
                else:
                    if ratio > 2.5: # Extreme disconnect
                        status = "Highly Stretched"
                        stress_score = 90
                        reason = f"Significantly detached from {benchmark_source} without PEG support"
                    elif ratio > 1.5:
                        status = "Overvalued"
                        stress_score = 75
                        reason = f"Expensive relative to {benchmark_source}"
                    else:
                        status = "Premium"
                        stress_score = 65
                        reason = f"Trading at premium to peers"

        # 5. Final Output Construction
        valuation_output[symbol] = {
            "valuation_status": status,
            "stress_score": stress_score,
            "primary_metric": metric_name,
            "primary_value": primary_val,
            "benchmark_value": round(benchmark_val, 2) if benchmark_val else None,
            "benchmark_source": benchmark_source,
            "peg_ratio": peg,
            "reason": reason
        }

    return valuation_output