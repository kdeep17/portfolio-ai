from collections import defaultdict
import pandas as pd
from utils.constants import SECTOR_MAP, RISK_THRESHOLDS


def run_risk_engine(df: pd.DataFrame) -> dict:
    """
    Computes portfolio-level and holding-level risk diagnostics.
    """

    risk_output = {}

    # --- Concentration ---
    sorted_df = df.sort_values("weight_pct", ascending=False)

    top1 = sorted_df.iloc[0]["weight_pct"]
    top3 = sorted_df.head(3)["weight_pct"].sum()
    top5 = sorted_df.head(5)["weight_pct"].sum()

    concentration_flags = []
    if top1 > RISK_THRESHOLDS["single_stock_high"]:
        concentration_flags.append(
            f"Single stock > {RISK_THRESHOLDS['single_stock_high']}%"
        )

    if top3 > RISK_THRESHOLDS["top3_high"]:
        concentration_flags.append(
            f"Top 3 holdings > {RISK_THRESHOLDS['top3_high']}%"
        )

    if top5 > RISK_THRESHOLDS["top5_high"]:
        concentration_flags.append(
            f"Top 5 holdings > {RISK_THRESHOLDS['top5_high']}%"
        )

    # --- Sector aggregation ---
    sector_weights = defaultdict(float)

    for _, row in df.iterrows():
        sector = SECTOR_MAP.get(row["symbol"], "Unknown")
        sector_weights[sector] += row["weight_pct"]

    # --- Risk contribution per holding ---
    holding_risk = {}

    for _, row in df.iterrows():
        risk_tag = "Low"
        if row["weight_pct"] > RISK_THRESHOLDS["single_stock_high"]:
            risk_tag = "High"
        elif row["weight_pct"] > 8:
            risk_tag = "Moderate"

        holding_risk[row["symbol"]] = risk_tag

    risk_output["concentration"] = {
        "top1_pct": round(top1, 2),
        "top3_pct": round(top3, 2),
        "top5_pct": round(top5, 2),
        "flags": concentration_flags
    }

    risk_output["sector_exposure"] = dict(
        sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)
    )

    risk_output["holding_risk"] = holding_risk

    return risk_output
