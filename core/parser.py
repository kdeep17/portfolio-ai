import pandas as pd
from utils.constants import REQUIRED_ZERODHA_COLUMNS, ZERODHA_COLUMN_MAP
from utils.constants import classify_instrument


class HoldingsParseError(Exception):
    pass


def load_and_validate_holdings(csv_file) -> pd.DataFrame:
    """
    Loads Zerodha holdings CSV and converts it into
    canonical internal format.
    """

    df = pd.read_csv(csv_file)

    # --- Column validation ---
    missing = REQUIRED_ZERODHA_COLUMNS - set(df.columns)
    if missing:
        raise HoldingsParseError(
            f"Missing required columns: {missing}"
        )

    # --- Rename to internal schema ---
    df = df.rename(columns=ZERODHA_COLUMN_MAP)

    # --- Keep only required internal columns ---
    df = df[list(ZERODHA_COLUMN_MAP.values())]

    # --- Basic sanity checks ---
    if (df["quantity"] <= 0).any():
        raise HoldingsParseError("Quantity must be > 0")

    if (df["avg_price"] <= 0).any():
        raise HoldingsParseError("Avg price must be > 0")

    # --- Normalize symbol format ---
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df["instrument_type"] = df["symbol"].apply(classify_instrument)

    return df

def enrich_portfolio_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds derived portfolio metrics.
    """

    total_value = df["current_value"].sum()

    if total_value <= 0:
        raise HoldingsParseError("Total portfolio value must be positive")

    df["weight_pct"] = (df["current_value"] / total_value) * 100

    return df, total_value
