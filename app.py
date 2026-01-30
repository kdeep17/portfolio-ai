import streamlit as st
import pandas as pd
from core.parser import load_and_validate_holdings, enrich_portfolio_metrics
from engines.risk import run_risk_engine
from engines.valuation import run_valuation_engine
from engines.thesis import run_thesis_engine

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Portfolio AI | Premium Advisory", layout="wide", page_icon="📈")

# Custom CSS for minimalist badges and metrics
st.markdown("""
<style>
    .stMetric {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    div[data-testid="stExpander"] {
        border: none;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("📊 Portfolio AI")
st.markdown("*Premium Automated Investment Advisory Diagnostics*")

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Zerodha holdings.csv", type=["csv"])

if uploaded_file:
    try:
        # 1. LOAD & PARSE
        with st.spinner("Parsing Portfolio..."):
            df = load_and_validate_holdings(uploaded_file)
            df, total_value = enrich_portfolio_metrics(df)

        # 2. RUN ENGINES
        with st.spinner("Running Risk, Valuation & Thesis Engines..."):
            risk_data = run_risk_engine(df)
            val_data = run_valuation_engine(df)
            thesis_data = run_thesis_engine(df)

        # --- DASHBOARD ---
        
        # A. PORTFOLIO SNAPSHOT
        st.subheader("Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        # Safe beta display
        p_beta = risk_data["portfolio_metrics"]["portfolio_beta"]
        p_profile = risk_data["portfolio_metrics"]["risk_profile"]
        
        # Safe sector display
        if risk_data["sector_exposure"]["weights"]:
            top_sector_name = list(risk_data["sector_exposure"]["weights"].keys())[0]
            top_sector_val = list(risk_data["sector_exposure"]["weights"].values())[0]
        else:
            top_sector_name = "N/A"
            top_sector_val = 0.0

        col1.metric("Total Value", f"₹ {total_value/100000:.2f} L")
        col2.metric("Portfolio Beta", p_beta, delta=p_profile, delta_color="inverse")
        col3.metric("Top Sector", top_sector_name, f"{top_sector_val:.1f}%")
        col4.metric("Active Holdings", len(df[df['instrument_type'] == 'Equity']))

        st.divider()

        # B. RISK DIAGNOSTICS
        st.subheader("📉 Risk Architecture")
        
        # 1. Concentration Flags
        flags = risk_data["concentration"]["flags"] + risk_data["sector_exposure"]["flags"]
        if flags:
            for flag in flags:
                st.error(f"⚠️ {flag}")
        else:
            st.success("✅ No structural concentration risks detected.")

        # 2. Holdings Heatmap (Beta vs Weight)
        with st.expander("View Holding Risk Details", expanded=False):
            risk_rows = []
            for sym, details in risk_data["holding_risk"].items():
                risk_rows.append({
                    "Symbol": sym,
                    "Risk Tag": details["risk_tag"],
                    "Beta": details["beta"],
                    "Risk Contribution": details["risk_contribution_score"]
                })
            if risk_rows:
                st.dataframe(pd.DataFrame(risk_rows).set_index("Symbol").sort_values("Risk Contribution", ascending=False), width='stretch')


        st.divider()

        # C. DEEP DIVE: THESIS & VALUATION
        st.subheader("🧠 Thesis & Valuation Health")
        
        rows = []
        for _, row in df.iterrows():
            sym = row["symbol"]
            if row["instrument_type"] != "Equity": continue
            
            t = thesis_data.get(sym, {})
            v = val_data.get(sym, {})
            
            # Status Icons
            t_status = t.get("status", "Unknown")
            t_icon = "🔴" if t_status == "Broken" else "🟠" if t_status == "Weakening" else "🟢"
            
            v_status = v.get("valuation_status", "Unknown")
            v_icon = "🟢" if "Undervalued" in v_status else "🔴" if "Stretched" in v_status else "⚪"

            # --- SAFE FORMATTING FIX ---
            # Handle cases where primary_value or sector_median is None
            prim_val = v.get('primary_value')
            sec_med = v.get('sector_median')
            metric_name = v.get('primary_metric', '-')

            if prim_val is not None:
                prim_val_str = f"{prim_val:.1f}"
            else:
                prim_val_str = "N/A"

            if sec_med is not None:
                sec_med_str = f"{sec_med:.1f}"
            else:
                sec_med_str = "N/A"
                
            metric_display = f"{metric_name}: {prim_val_str} vs {sec_med_str}"
            # ---------------------------

            rows.append({
                "Symbol": sym,
                "Sector": t.get("sector", "Unknown"),
                "Thesis": f"{t_icon} {t_status}",
                "Thesis Drivers": ", ".join(t.get("drivers", [])) if t.get("drivers") else "None",
                "Valuation": f"{v_icon} {v_status}",
                "Metric": metric_display,
                "Stress Score": v.get("stress_score", 0) if v.get("stress_score") is not None else 0
            })

        # Display as a clean interactive table
        if rows:
            results_df = pd.DataFrame(rows)
            
            # Simple highlighter for broken rows
            def highlight_broken(row):
                # Check if "Broken" text exists in the Thesis column
                if "Broken" in str(row["Thesis"]):
                    return ['background-color: #ffebee'] * len(row)
                return [''] * len(row)

            st.dataframe(
                results_df.style.apply(highlight_broken, axis=1),
                column_config={
                    "Thesis Drivers": st.column_config.TextColumn("Risk Drivers", width="large"),
                    "Stress Score": st.column_config.ProgressColumn("Valuation Heat", min_value=0, max_value=100, format="%d"),
                },
                width='stretch',
                height=600
            )
            
            # Download Report Option
            st.download_button(
                label="📥 Download Full Analysis CSV",
                data=results_df.to_csv().encode('utf-8'),
                file_name='portfolio_analysis_premium.csv',
                mime='text/csv',
            )
        else:
            st.info("No Equity holdings found to analyze.")

    except Exception as e:
        st.error(f"Analysis Failed: {str(e)}")
        # st.write(e) # Uncomment to see full traceback if needed