import yfinance as yf
from utils.constants import SECTOR_MAP


def fetch_trailing_pe(symbol: str):
    """
    Fetch trailing P/E using Yahoo Finance.
    NSE symbols require .NS suffix.
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        pe = ticker.info.get("trailingPE")
        return pe
    except Exception:
        return None


def run_valuation_engine(df):
    """
    Computes valuation stretch indicators.
    """

    valuation_output = {}

    # --- Fetch trailing PEs ---
    pe_data = {}
    for _, row in df.iterrows():
        symbol = row["symbol"]
        if row["instrument_type"] != "Equity":
            pe_data[symbol] = None
        else:
            pe_data[symbol] = fetch_trailing_pe(symbol)
        # print("PE DATA:", pe_data)
    # --- Compute sector medians ---
    sector_pe = {}
    for symbol, pe in pe_data.items():
        if pe is None:
            continue
        sector = SECTOR_MAP.get(symbol)
        if sector:
            sector_pe.setdefault(sector, []).append(pe)

    sector_median_pe = {
        sector: sorted(pes)[len(pes) // 2]
        for sector, pes in sector_pe.items()
        if pes
    }

    # --- Assign valuation status ---
    for symbol in df["symbol"]:
        pe = pe_data.get(symbol)
        sector = SECTOR_MAP.get(symbol, "Other")
        sector_median = sector_median_pe.get(sector)

        # TEMP DEBUG — remove later
        # print("Sector medians:", sector_median_pe)

        # --- Robust valuation assignment ---
        if row["instrument_type"] != "Equity":
            valuation_status = "Not Applicable"
            stress_score = None

        elif pe is None or sector_median is None:
            valuation_status = "Insufficient data"
            stress_score = None

        else:
            ratio = pe / sector_median

            if ratio > 1.5:
                valuation_status = "Highly Stretched"
                stress_score = 80
            elif ratio > 1.2:
                valuation_status = "Stretched"
                stress_score = 60
            elif ratio < 0.7:
                valuation_status = "Below Sector"
                stress_score = 30
            else:
                valuation_status = "Within Range"
                stress_score = 45

        valuation_output[symbol] = {
            "trailing_pe": pe,
            "sector": sector,
            "sector_median_pe": sector_median,
            "valuation_status": valuation_status,
            "stress_score": stress_score
        }

    return valuation_output