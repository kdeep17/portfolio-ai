import streamlit as st
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

        st.success("Holdings file validated successfully")

        st.metric("Total Portfolio Value", f"₹ {total_value:,.0f}")

        st.subheader("Normalized Holdings")
        st.dataframe(df)

    except Exception as e:
        st.error(str(e))
