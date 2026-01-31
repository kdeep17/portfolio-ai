import pandas as pd
from pprint import pprint

from events import run_events_engine


# -----------------------------
# MOCK PORTFOLIO (minimal)
# -----------------------------
df = pd.DataFrame([
    {"symbol": "HDFCBANK", "instrument_type": "Equity"},
    {"symbol": "ITC", "instrument_type": "Equity"},
    {"symbol": "RELIANCE", "instrument_type": "Equity"},
    {"symbol": "SGBJUN31I-GB", "instrument_type": "SGB"},  # should be ignored
])

# -----------------------------
# MOCK THESIS DATA
# -----------------------------
thesis_data = {
    "HDFCBANK": {"status": "Weakening"},
    "ITC": {"status": "Intact"},
    "RELIANCE": {"status": "Intact"},
}

# -----------------------------
# RUN EVENTS ENGINE
# -----------------------------
results = run_events_engine(df, thesis_data)

# -----------------------------
# INSPECT OUTPUT
# -----------------------------
# print("\n=== EVENTS OUTPUT ===")
# pprint(results)
# print(f"\nTotal events detected: {len(results)}")
