import streamlit as st
import pandas as pd
import altair as alt

# --- IMPORT CORE MODULES ---
from core.parser import load_and_validate_holdings, enrich_portfolio_metrics
from core.data_loader import fetch_market_data

# --- IMPORT ENGINES ---
from engines.risk import run_risk_engine
from engines.valuation import run_valuation_engine
from engines.thesis import run_thesis_engine
from engines.opportunity_cost import run_opportunity_cost_engine
from engines.events import run_events_engine

from synthesis.decision_engine import run_decision_engine
from output.assembler import assemble_output

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Portfolio AI",
    layout="wide",
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

# --- FUTURISTIC MINIMALIST STYLING ---
st.markdown("""
<style>
    /* Global Font & Reset */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Clean Cards (Glassmorphism Lite) */
    div.css-1r6slb0 { background-color: #ffffff; border: 1px solid #f0f0f0; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 600; color: #1e293b; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #64748b; }
    
    /* Custom Status Badges in Text */
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; }
    .badge-red { background-color: #fee2e2; color: #991b1b; }
    .badge-orange { background-color: #ffedd5; color: #9a3412; }
    .badge-blue { background-color: #e0f2fe; color: #075985; }
    
    /* Hide Streamlit Clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🦅 Portfolio AI")
    st.caption("v1.0 | Premium Advisory")
    
    uploaded_file = st.file_uploader("Upload Holdings (Zerodha CSV)", type=["csv"])
    
    st.markdown("---")
    
    if uploaded_file:
        st.success("System Online")
    else:
        st.info("Awaiting Data Upload...")
        st.stop()
        
    st.markdown("---")
    
    with st.expander("System Health", expanded=True):
        st.caption("✅ Core Engine: Ready")
        st.caption("✅ Market Data: Live")
        st.caption("✅ Risk Models: Active")


# ==========================================
# === 1. ORCHESTRATION LAYER ===
# ==========================================
try:
    # A. Batch Data Fetching
    with st.spinner("Establishing Secure Link to Market Data..."):
        df = load_and_validate_holdings(uploaded_file)
        df, total_value = enrich_portfolio_metrics(df)
        market_data = fetch_market_data(df["symbol"].tolist())

    # B. Analytical Processing
    with st.status("Executing Neural Analytics...", expanded=False) as status:
        risk_data = run_risk_engine(df, market_data)
        st.write("✓ Risk Vectors Calculated")
        
        valuation_data = run_valuation_engine(df, market_data)
        st.write("✓ Valuation Benchmarks Calibrated")
        
        thesis_data = run_thesis_engine(df, market_data)
        st.write("✓ Fundamental Health Scanned")
        
        opportunity_data = run_opportunity_cost_engine(df, risk_data, valuation_data, thesis_data, market_data)
        st.write("✓ Capital Efficiency Modeled")
        
        events_data = run_events_engine(df, thesis_data, market_data)
        st.write("✓ Sentiment Analysis Complete")
        
        decision_data = run_decision_engine(df, risk_data, valuation_data, thesis_data, opportunity_data, events_data)
        st.write("✓ Decision Synthesis Finalized")
        
        status.update(label="Analysis Successfully Completed", state="complete", expanded=False)

    final_output = assemble_output(df, total_value, risk_data, valuation_data, thesis_data, 
                                   opportunity_data, decision_data, events_data)

except Exception as e:
    st.error(f"⚠️ Critical System Failure: {str(e)}")
    st.stop()


# ==========================================
# === 2. DASHBOARD UI ===
# ==========================================

summ = final_output["portfolio_summary"]
risk_prof = summ["risk_profile"]

# --- A. HEADS-UP DISPLAY (HUD) ---
st.markdown("### Executive Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Net Worth", f"₹ {summ['total_value']/100000:.2f} L")
c2.metric("Health Score", f"{summ['net_worth_health_score']}/100")
c3.metric("Portfolio Beta", f"{risk_prof['beta']}", delta=risk_prof['label'], delta_color="inverse")
c4.metric("Cash Drag", f"{risk_prof['cash_drag_pct']}%")

st.divider()

# --- B. VISUAL ANALYTICS ---
col_charts_1, col_charts_2 = st.columns(2)

with col_charts_1:
    st.caption("SECTOR ALLOCATION")
    sector_data = risk_data.get("sector_exposure", {}).get("weights", {})
    if sector_data:
        chart_df = pd.DataFrame(list(sector_data.items()), columns=["Sector", "Weight"])
        
        # Elegant Donut Chart
        base = alt.Chart(chart_df).encode(
            theta=alt.Theta("Weight", stack=True)
        )
        pie = base.mark_arc(innerRadius=60, outerRadius=100).encode(
            color=alt.Color("Sector", scale=alt.Scale(scheme="tableau10"), legend=None),
            order=alt.Order("Weight", sort="descending"),
            tooltip=["Sector", alt.Tooltip("Weight", format=".1f")]
        )
        # Center Text
        text = base.mark_text(radius=120).encode(
            text=alt.Text("Weight", format=".1f"),
            order=alt.Order("Weight", sort="descending"),
            color=alt.value("gray")  
        )
        st.altair_chart(pie + text, use_container_width=True)

with col_charts_2:
    st.caption("CONCENTRATION RISK (TOP 5)")
    top_holdings = df[df["instrument_type"] == "Equity"].sort_values("weight_pct", ascending=False).head(5)
    
    # Minimalist Bar Chart
    bar_chart = alt.Chart(top_holdings).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
        x=alt.X("weight_pct", title=None, axis=None),
        y=alt.Y("symbol", sort="-x", title=None),
        color=alt.Color("weight_pct", scale=alt.Scale(scheme="blues"), legend=None),
        tooltip=["symbol", "weight_pct"]
    ).properties(height=200)
    
    text_bar = bar_chart.mark_text(align='left', dx=5).encode(
        text=alt.Text('weight_pct', format='.1f')
    )
    
    st.altair_chart(bar_chart + text_bar, use_container_width=True)

st.markdown("---")


# --- C. INTELLIGENCE TABS ---
tab_actions, tab_details, tab_news = st.tabs(["🚀 Strategic Actions", "🔬 Deep Dive Analysis", "📡 Global Intelligence"])

# TAB 1: STRATEGIC ACTIONS
with tab_actions:
    actions = final_output["strategic_actions"]
    if not actions:
        st.success("✅ Portfolio is fully optimized. No critical interventions required.")
    else:
        # Priority Sort
        priority_map = {"EXIT": 0, "REPLACE": 1, "TRIM": 2, "WATCH": 3}
        actions.sort(key=lambda x: priority_map.get(x["action"], 99))
        
        # Responsive Grid Layout for Actions
        for act in actions:
            # Dynamic Styling based on Action
            if act["action"] == "EXIT":
                border_color = "#ef4444"
                bg_color = "#fef2f2"
                icon = "🚨"
            elif act["action"] == "REPLACE":
                border_color = "#f97316"
                bg_color = "#fff7ed"
                icon = "🔄"
            else:
                border_color = "#3b82f6"
                bg_color = "#eff6ff"
                icon = "🔍"

            # Action Card HTML
            st.markdown(f"""
            <div style="
                border-left: 5px solid {border_color};
                background-color: {bg_color};
                padding: 15px;
                border-radius: 4px;
                margin-bottom: 10px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 1.2rem; font-weight: bold; color: #1f2937;">{icon} {act['symbol']}</span>
                        <span style="background-color: {border_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; margin-left: 10px;">{act['action']}</span>
                    </div>
                    <span style="font-size: 0.8rem; color: #6b7280; font-weight: 600;">URGENCY: {act['urgency'].upper()}</span>
                </div>
                <div style="margin-top: 8px; color: #4b5563; font-size: 0.95rem;">
                    {act['reason']}
                </div>
            </div>
            """, unsafe_allow_html=True)


# TAB 2: DEEP DIVE TABLE
with tab_details:
    flat_data = []
    for h in final_output["holdings_analysis"]:
        alts = h["efficiency"]["better_alternatives"]
        alt_str = ", ".join([c["symbol"] for c in alts["candidates"]]) if alts else ""
        
        flat_data.append({
            "Symbol": h["symbol"],
            "Action": h["final_verdict"]["action"],
            "Weight": h['meta']['weight_pct'],
            "Thesis": h["fundamental_health"]["status"],
            "Valuation": h["valuation"]["rating"],
            "Risk": h["risk_profile"]["tag"],
            "Drag": int(h["efficiency"]["capital_drag"]),
            "Rationale": h["final_verdict"]["rationale"],
            "Alts": alt_str
        })
    
    df_disp = pd.DataFrame(flat_data)
    
    # Sort by Risk Severity
    risk_map = {"Critical (Liquidity)": 5, "Critical (Volatility)": 4, "High": 3, "Moderate": 2, "Low": 1}
    if not df_disp.empty:
        df_disp["_sort"] = df_disp["Risk"].map(lambda x: risk_map.get(x, 0))
        df_disp = df_disp.sort_values("_sort", ascending=False).drop(columns=["_sort"])

    # Conditional Formatting Map
    def highlight_cells(val):
        if val == 'EXIT': return 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'
        if val == 'REPLACE': return 'background-color: #ffedd5; color: #9a3412; font-weight: bold;'
        if val == 'TRIM': return 'background-color: #e0f2fe; color: #075985;'
        if val == 'Broken': return 'color: #dc2626; font-weight: bold;'
        if val == 'Critical (Liquidity)': return 'color: #dc2626; font-weight: bold;'
        return ''

    st.dataframe(
        df_disp.style.applymap(highlight_cells, subset=['Action', 'Thesis', 'Risk']),
        use_container_width=True,
        height=600,
        column_config={
            "Weight": st.column_config.NumberColumn("Wt %", format="%.2f"),
            "Drag": st.column_config.ProgressColumn("Efficiency Drag", min_value=0, max_value=100, format="%d"),
            "Alts": st.column_config.TextColumn("Better Alternatives", width="medium"),
            "Rationale": st.column_config.TextColumn("Verdict", width="large"),
        },
        hide_index=True
    )


# TAB 3: INTELLIGENCE
with tab_news:
    events = final_output["market_intelligence"]
    if not events:
        st.info("No material catalyst events detected in the current scan window.")
    else:
        from collections import defaultdict
        grouped = defaultdict(list)
        for e in events: grouped[e["symbol"]].append(e)
            
        # Masonry Layout (2 Columns)
        c_news_1, c_news_2 = st.columns(2)
        
        for i, (sym, items) in enumerate(grouped.items()):
            target = c_news_1 if i % 2 == 0 else c_news_2
            with target:
                with st.expander(f"**{sym}** • {len(items)} Events", expanded=True):
                    for item in items:
                        if item["score"] < 0:
                            badge = f'<span class="badge badge-red">NEGATIVE</span>'
                        else:
                            badge = f'<span class="badge badge-blue">POSITIVE</span>'
                            
                        st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                                {badge} <span style="font-size:0.8rem; color:#888;">{item['published']}</span>
                            </div>
                            <div style="font-weight:500; font-size:0.95rem; margin-bottom:4px;">{item['headline']}</div>
                            <div style="font-size:0.85rem; color:#555; font-style:italic;">Impact: {item['confidence_effect']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.divider()