import numpy as np
from utils.constants import SECTOR_MAP, SECTOR_CAPTAINS, FALLBACK_SECTOR_PE

def run_valuation_engine(df, market_data):
    """
    Computes valuation stretch using Dynamic Sector Benchmarking.
    
    Logic:
    1. Compares stock against 'Sector Captains' (Market Leaders) first.
    2. If Captains data is missing, falls back to hardcoded Sector Baselines.
    3. Applies 'Growth Defense': High P/E is forgiven if PEG Ratio is low (<1.5).
    4. Distinguishes Financials (P/B focus) from non-Financials (P/E focus).
    """

    valuation_output = {}

    # --- HELPER: Get Dynamic Sector Benchmark ---
    def get_sector_benchmark(sector_name, metric_type="pe"):
        """
        Returns (benchmark_value, source_string)
        metric_type: 'pe' or 'pb'
        """
        captains = SECTOR_CAPTAINS.get(sector_name, [])
        captain_values = []
        
        # 1. Try fetching live data from Captains
        for cap_symbol in captains:
            # Handle potential suffix mismatch (e.g., 'TCS' vs 'TCS.NS')
            # We check both to be safe, preferring the exact match in market_data
            info = market_data.get_info(cap_symbol)
            if not info:
                # Try appending .NS if missing
                info = market_data.get_info(f"{cap_symbol}.NS")
            
            if info:
                val = info.get("trailingPE") if metric_type == "pe" else info.get("priceToBook")
                if val is not None and val > 0: # Filter out invalid/negative benchmarks
                    captain_values.append(val)
        
        # 2. If we have live captains, use their median
        if len(captain_values) > 0:
            return np.median(captain_values), "Live Sector Captains"

        # 3. Fallback to Hardcoded Baseline (Safety Net)
        # Note: We currently only have P/E fallbacks. For P/B, we assume a standard 3.0x fallback if needed.
        if metric_type == "pe":
            return FALLBACK_SECTOR_PE.get(sector_name, 20.0), "Static Market Baseline"
        else:
            return 3.0, "Static Market Baseline" # Default P/B fallback for financials


    # --- MAIN EVALUATION LOOP ---
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
            metric_key = "pb"
        else:
            primary_val = pe
            metric_name = "P/E"
            metric_key = "pe"

        # 4. Get Benchmark
        benchmark_val, benchmark_source = get_sector_benchmark(sector, metric_key)

        # 5. Logic Gates
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

        # 6. Final Output Construction
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