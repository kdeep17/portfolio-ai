import streamlit as st
from engines.risk import run_risk_engine
from core.parser import load_and_validate_holdings, enrich_portfolio_metrics

st.set_page_config(page_title="Portfolio AI", layout="wide")
st.title("📊 Portfolio AI")

uploaded_file = st.file_uploader(
    "Upload Zerodha holdings.csv",
    type=["csv"]
)

if uploaded_file:
    try:
        df = load_and_validate_holdings(uploaded_file)
        df, total_value = enrich_portfolio_metrics(df)
        st.metric("Total Portfolio Value", f"₹ {total_value:,.0f}")
        st.subheader("Normalized Holdings")

        risk_output = run_risk_engine(df)

        st.divider()
        st.subheader("📉 Risk Diagnostics")

        col1, col2, col3 = st.columns(3)
        col1.metric("Top 1 Weight (%)", risk_output["concentration"]["top1_pct"])
        col2.metric("Top 3 Weight (%)", risk_output["concentration"]["top3_pct"])
        col3.metric("Top 5 Weight (%)", risk_output["concentration"]["top5_pct"])

        if risk_output["concentration"]["flags"]:
            for flag in risk_output["concentration"]["flags"]:
                st.warning(flag)

        st.subheader("Sector Exposure (%)")
        st.json(risk_output["sector_exposure"])

        st.subheader("Holding Risk Contribution")
        st.json(risk_output["holding_risk"])

        st.success("Holdings file validated successfully")

        st.dataframe(df)

    except Exception as e:
        st.error(str(e))
