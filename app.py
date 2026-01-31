import streamlit as st
import pandas as pd
import altair as alt
import time

# --- IMPORT CORE MODULES ---
from core.parser import load_and_validate_holdings, enrich_portfolio_metrics
from core.data_loader import fetch_market_data

# --- IMPORT ENGINES ---
from engines.risk import run_risk_engine
from engines.valuation import run_valuation_engine
from engines.thesis import run_thesis_engine
from engines.opportunity_cost import run_opportunity_cost_engine
from engines.events import run_events_engine
from engines.optimization import run_optimization_engine
from engines.stress_test import run_monte_carlo_engine
# NEW: Import Bedrock Explainer
from engines.explainer import batch_explain_holdings, explain_quant_metrics

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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    div.css-1r6slb0 { background-color: #ffffff; border: 1px solid #f0f0f0; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 600; color: #1e293b; }
    
    /* AI Insight Box Styling - STRICT CSS */
    .ai-box { 
        background-color: #f0f9ff; 
        border-left: 4px solid #0ea5e9; 
        padding: 12px; 
        border-radius: 4px; 
        margin-bottom: 12px; 
        font-family: 'Inter', sans-serif;
    }
    .ai-text { 
        color: #0c4a6e; 
        font-size: 0.9rem; 
        font-style: italic; 
        line-height: 1.4; 
    }
    .ai-label { 
        font-weight: 700; 
        color: #0ea5e9; 
        font-size: 0.7rem; 
        text-transform: uppercase; 
        margin-bottom: 4px; 
        letter-spacing: 0.05em; 
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- CACHING DECORATORS ---
@st.cache_data(ttl=3600)
def get_market_data(symbols):
    return fetch_market_data(symbols)

@st.cache_data
def process_holdings(file):
    df = load_and_validate_holdings(file)
    df, total_value = enrich_portfolio_metrics(df)
    return df, total_value

# --- SIDEBAR ---
with st.sidebar:
    st.title("🦅 Portfolio AI")
    st.caption("v3.3 | AWS Bedrock Integrated")
    
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
        st.caption("✅ Quant Lab: Active")
        st.caption("✅ AWS Bedrock: Connected")
        
    time_placeholder = st.empty()


# ==========================================
# === 1. ORCHESTRATION LAYER ===
# ==========================================
try:
    total_start = time.perf_counter()

    with st.spinner("Establishing Secure Link to Market Data..."):
        t_start = time.perf_counter()
        df, total_value = process_holdings(uploaded_file)
        market_data = get_market_data(df["symbol"].tolist())
        data_load_time = time.perf_counter() - t_start

    with st.status("Executing Neural Analytics...", expanded=True) as status:
        # 1. RUN ENGINES
        risk_data = run_risk_engine(df, market_data)
        st.write("✓ Risk Vectors Calculated")
        valuation_data = run_valuation_engine(df, market_data)
        st.write("✓ Valuation Models Calibrated")
        thesis_data = run_thesis_engine(df, market_data)
        st.write("✓ Earnings Quality Scanned")
        opportunity_data = run_opportunity_cost_engine(df, risk_data, valuation_data, thesis_data, market_data)
        st.write("✓ Opportunity Cost Analyzed")
        events_data = run_events_engine(df, thesis_data, market_data)
        st.write("✓ News Parsed")
        decision_data = run_decision_engine(df, risk_data, valuation_data, thesis_data, opportunity_data, events_data)
        st.write("✓ Strategic Decisions Generated")
        opt_data = run_optimization_engine(df, market_data, total_value)
        mc_data = run_monte_carlo_engine(df, market_data, total_value)
        st.write("✓ Quant Lab Simulations Completed")
        
        status.update(label="Core Analysis Complete. Engaging AI...", state="running", expanded=True)
        
        # 2. ASSEMBLE DATA
        final_output = assemble_output(df, total_value, risk_data, valuation_data, thesis_data, 
                                       opportunity_data, decision_data, events_data)
        final_output["optimization"] = opt_data
        final_output["stress_test"] = mc_data

        # 3. AI LAYER (Parallelized)
        t_ai = time.perf_counter()
        ai_holding_explanations = batch_explain_holdings(df, final_output)
        
        ai_quant_explanations = {}
        if final_output.get("optimization") and final_output.get("stress_test"):
            ai_quant_explanations = explain_quant_metrics(
                final_output["optimization"], 
                final_output["stress_test"]
            )
            
        st.write(f"✓ AI Insights Generated ({time.perf_counter() - t_ai:.2f}s)")
        status.update(label="System Ready", state="complete", expanded=False)

    time_placeholder.caption(f"⚡ Total Execution: {time.perf_counter() - total_start:.2f}s")

except Exception as e:
    st.error(f"⚠️ Critical System Failure: {str(e)}")
    st.stop()


# ==========================================
# === 2. DASHBOARD UI ===
# ==========================================

summ = final_output["summary"] 
risk_prof = summ["risk_profile"]

# --- A. HEADS-UP DISPLAY (HUD) ---
st.markdown("### Executive Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Net Worth", f"₹ {summ['total_value']/100000:.2f} L")
c2.metric("Portfolio Health", f"{summ['health_score']}/100", help="Multi-factor score.")
c3.metric("Daily VaR (95%)", f"₹ {risk_prof['daily_var_95_amt']:,.0f}")
c4.metric("Cash Position", f"{risk_prof['cash_position_pct']}%", delta="Liquidity", delta_color="off")
st.divider()

# --- B. CHARTS ---
col_charts_1, col_charts_2 = st.columns(2)
with col_charts_1:
    st.caption("SECTOR EXPOSURE")
    sector_data = risk_data.get("sector_exposure", {}).get("weights", {})
    if sector_data:
        chart_df = pd.DataFrame(list(sector_data.items()), columns=["Sector", "Weight"])
        base = alt.Chart(chart_df).encode(theta=alt.Theta("Weight", stack=True))
        pie = base.mark_arc(innerRadius=60, outerRadius=100).encode(
            color=alt.Color("Sector", scale=alt.Scale(scheme="tableau10"), legend=None),
            order=alt.Order("Weight", sort="descending"),
            tooltip=["Sector", alt.Tooltip("Weight", format=".1f")]
        )
        st.altair_chart(pie, use_container_width=True)

with col_charts_2:
    st.caption("CONCENTRATION RISK")
    top_holdings = df[df["instrument_type"] == "Equity"].sort_values("weight_pct", ascending=False).head(5)
    bar_chart = alt.Chart(top_holdings).mark_bar(cornerRadiusTopRight=5).encode(
        x=alt.X("weight_pct", axis=None),
        y=alt.Y("symbol", sort="-x", title=None),
        color=alt.Color("weight_pct", scale=alt.Scale(scheme="blues"), legend=None),
        tooltip=["symbol", "weight_pct"]
    ).properties(height=200)
    text_bar = bar_chart.mark_text(align='left', dx=5).encode(text=alt.Text('weight_pct', format='.1f'))
    st.altair_chart(bar_chart + text_bar, use_container_width=True)

st.markdown("---")

# --- C. TABS ---
tab_actions, tab_details, tab_news, tab_premium = st.tabs([
    "🚀 Strategic Actions", "🔬 Deep Dive Analysis", "📡 Global Intelligence", "🔮 Quant Lab"
])

# TAB 1: STRATEGIC ACTIONS
with tab_actions:
    actions = final_output["actions"] 
    if not actions:
        st.success("✅ Portfolio is fully optimized.")
    else:
        priority_map = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        actions.sort(key=lambda x: priority_map.get(x["urgency"], 99))
        
        for act in actions:
            ai_text = ai_holding_explanations.get(act['symbol'], "Processing insight...")
            
            if act["action"] == "EXIT": border, bg, icon = "#ef4444", "#fef2f2", "🚨"
            elif act["action"] == "REPLACE": border, bg, icon = "#f97316", "#fff7ed", "🔄"
            elif act["action"] == "TRIM": border, bg, icon = "#eab308", "#fefce8", "✂️"
            else: border, bg, icon = "#3b82f6", "#eff6ff", "🔍"

            # FIXED HTML FORMATTING (No Indentation Issues)
            html_block = f"""
            <div style="border-left: 5px solid {border}; background-color: {bg}; padding: 15px; border-radius: 4px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div>
                        <span style="font-size: 1.2rem; font-weight: bold; color: #1f2937;">{icon} {act['symbol']}</span>
                        <span style="background-color: {border}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; margin-left: 10px;">{act['action']}</span>
                    </div>
                </div>
                <div class="ai-box">
                    <div class="ai-label">✨ AWS Bedrock Insight</div>
                    <div class="ai-text">{ai_text}</div>
                </div>
                <div style="margin-top: 8px; color: #4b5563; font-size: 0.85rem; border-top: 1px dashed #ccc; padding-top: 8px;">
                    <strong>Technical Trigger:</strong> {act['reason']}
                </div>
            </div>
            """
            st.markdown(html_block, unsafe_allow_html=True)


# TAB 2: DEEP DIVE TABLE
with tab_details:
    flat_data = []
    for h in final_output["holdings"]:
        if h["type"] != "Equity": continue 

        alts_data = h["advisory"]["alternatives"]
        alt_str = "\n".join([f"👉 {c['symbol']}: {c['note']}" for c in alts_data["candidates"]]) if alts_data else ""
        
        flat_data.append({
            "Symbol": h["symbol"],
            "AI Insight": ai_holding_explanations.get(h["symbol"], ""), # Empty string if no data
            "Action": h["advisory"]["action"],
            "Weight %": h['meta']['weight_pct'],
            "Thesis": h["analytics"]["thesis_status"],
            "Valuation": h["analytics"]["valuation_rating"],
            "Momentum": int(h["analytics"]["momentum_score"]),
            "Beta": h["analytics"]["risk_beta"],
            "Rationale": h["advisory"]["rationale"],
            "Alternatives": alt_str
        })
    
    df_disp = pd.DataFrame(flat_data)
    
    st.dataframe(
        df_disp,
        use_container_width=True,
        height=600,
        column_config={
            "AI Insight": st.column_config.TextColumn("🤖 AI Analysis", width="large"),
            "Weight %": st.column_config.NumberColumn(format="%.1f"),
            "Momentum": st.column_config.ProgressColumn("Trend", min_value=0, max_value=100, format="%d"),
            "Beta": st.column_config.NumberColumn(format="%.2f"),
        },
        hide_index=True,
        column_order=["Symbol", "AI Insight", "Action", "Weight %", "Thesis", "Valuation", "Momentum", "Rationale", "Alternatives"] 
    )


# TAB 3: INTELLIGENCE
with tab_news:
    events = final_output["intelligence"] 
    if not events:
        st.info("No material catalyst events detected.")
    else:
        from collections import defaultdict
        grouped = defaultdict(list)
        for e in events: grouped[e["symbol"]].append(e)
            
        c_news_1, c_news_2 = st.columns(2)
        for i, (sym, items) in enumerate(grouped.items()):
            target = c_news_1 if i % 2 == 0 else c_news_2
            with target:
                with st.expander(f"**{sym}** • {len(items)} Events", expanded=True):
                    for item in items:
                        cat = item['impact']
                        if cat in ["Governance Risk", "Deterioration"]: badge_cls = "badge-red"
                        elif cat in ["Earnings Blowout", "Upgrade"]: badge_cls = "badge-blue"
                        else: badge_cls = "badge-orange"
                        st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                                <span class="badge {badge_cls}">{cat}</span> 
                                <span style="font-size:0.8rem; color:#888;">{item['published']}</span>
                            </div>
                            <div style="font-weight:500; font-size:0.95rem; margin-bottom:4px;">{item['headline']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.divider()

# TAB 4: QUANT LAB
with tab_premium:
    st.markdown("### 🧬 Portfolio DNA & Simulation")
    
    exp_opt = ai_quant_explanations.get("optimization", "Generating insight...")
    exp_stress = ai_quant_explanations.get("stress_test", "Generating insight...")
    
    # 1. OPTIMIZATION
    opt = final_output.get("optimization")
    if opt and opt["status"] == "Success":
        html_opt = f"""
        <div class="ai-box">
            <div class="ai-label">✨ Optimization Explained</div>
            <div class="ai-text">{exp_opt}</div>
        </div>
        """
        st.markdown(html_opt, unsafe_allow_html=True)

        c1, c2 = st.columns([1, 2])
        with c1:
            st.info("Mathematical Optimization (Max Sharpe)")
            metrics = opt["metrics"]
            st.metric("Potential Sharpe", f"{metrics['sharpe_ratio']:.2f}")
            st.metric("Expected Volatility", f"{metrics['volatility']*100:.1f}%")
        with c2:
            st.caption("Suggested Rebalancing")
            alloc_df = pd.DataFrame({
                "Symbol": list(opt["optimal_weights"].keys()),
                "Optimal Weight": list(opt["optimal_weights"].values())
            })
            chart = alt.Chart(alloc_df).mark_bar().encode(
                x='Symbol', y='Optimal Weight', color=alt.value("#10b981")
            )
            st.altair_chart(chart, use_container_width=True)
            
    # 2. MONTE CARLO
    st.divider()
    mc = final_output.get("stress_test")
    if mc:
        st.markdown("### 🎲 Monte Carlo Stress Test")
        
        html_stress = f"""
        <div class="ai-box">
            <div class="ai-label">✨ Risk Scenarios Explained</div>
            <div class="ai-text">{exp_stress}</div>
        </div>
        """
        st.markdown(html_stress, unsafe_allow_html=True)

        met = mc["metrics"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Worst Case (95%)", f"₹ {met['worst_case_1y']/100000:.2f} L")
        m2.metric("Median Outcome", f"₹ {met['median_1y']/100000:.2f} L")
        m3.metric("Loss Probability", f"{met['loss_probability']*100:.1f}%")
        
        paths = mc["simulation_data"]
        plot_paths = paths[:, :50]
        chart_data = pd.DataFrame(plot_paths).reset_index().melt('index')
        chart_data.columns = ['Day', 'Simulation', 'Value']
        
        line_chart = alt.Chart(chart_data).mark_line(opacity=0.3, size=1).encode(
            x='Day', y=alt.Y('Value', title='Portfolio Value'), detail='Simulation', color=alt.value("#6366f1")
        ).properties(height=300)
        st.altair_chart(line_chart, use_container_width=True)