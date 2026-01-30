from core import schema
import streamlit as st

st.set_page_config(
    page_title="Portfolio AI",
    layout="wide"
)

st.title("📊 Portfolio AI Dashboard")

st.markdown("""
This system analyzes your equity portfolio and provides
**risk-aware, thesis-driven decision support**.

> Manual trigger. No auto-trading. No noise.
""")

st.success("System environment loaded successfully.")
