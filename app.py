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

# --- CACHING DECORATORS (Performance Optimization) ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
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
    st.caption("v3.0 | Premium Advisory")
    
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
        
    time_placeholder = st.empty()


# ==========================================
# === 1. ORCHESTRATION LAYER ===
# ==========================================
try:
    total_start = time.perf_counter()

    # A. Data Processing (Cached)
    with st.spinner("Establishing Secure Link to Market Data..."):
        t_start = time.perf_counter()
        
        # Using Cached Functions
        df, total_value = process_holdings(uploaded_file)
        market_data = get_market_data(df["symbol"].tolist())
        
        t_end = time.perf_counter()
        data_load_time = t_end - t_start

    # B. Analytical Processing (Real-time Engines)
    with st.status("Executing Neural Analytics...", expanded=True) as status:
        
        # 1. RISK (Quantitative)
        t0 = time.perf_counter()
        risk_data = run_risk_engine(df, market_data)
        st.write(f"✓ Risk Vectors & VaR Calculated ({time.perf_counter() - t0:.2f}s)")
        
        # 2. VALUATION (Sector Benchmarked)
        t0 = time.perf_counter()
        valuation_data = run_valuation_engine(df, market_data)
        st.write(f"✓ Valuation Models Calibrated ({time.perf_counter() - t0:.2f}s)")
        
        # 3. THESIS (3-Statement Analysis)
        t0 = time.perf_counter()
        thesis_data = run_thesis_engine(df, market_data)
        st.write(f"✓ Earnings Quality Scanned ({time.perf_counter() - t0:.2f}s)")
        
        # 4. OPPORTUNITY (Momentum + Drag)
        t0 = time.perf_counter()
        opportunity_data = run_opportunity_cost_engine(df, risk_data, valuation_data, thesis_data, market_data)
        st.write(f"✓ Switch Hurdles Analyzed ({time.perf_counter() - t0:.2f}s)")
        
        # 5. EVENTS (Semantic Search)
        t0 = time.perf_counter()
        events_data = run_events_engine(df, thesis_data, market_data)
        st.write(f"✓ News Sentiment Parsed ({time.perf_counter() - t0:.2f}s)")
        
        # 6. DECISION (Hierarchical Logic)
        t0 = time.perf_counter()
        decision_data = run_decision_engine(df, risk_data, valuation_data, thesis_data, opportunity_data, events_data)
        st.write(f"✓ Strategic Policies Generated ({time.perf_counter() - t0:.2f}s)")
        
        total_end = time.perf_counter()
        total_duration = total_end - total_start
        
        status.update(label=f"Analysis Completed in {total_duration:.2f}s", state="complete", expanded=False)

    time_placeholder.caption(f"⚡ Execution: {total_duration:.2f}s (Data Fetch: {data_load_time:.2f}s)")

    # C. Assembly
    final_output = assemble_output(df, total_value, risk_data, valuation_data, thesis_data, 
                                   opportunity_data, decision_data, events_data)

except Exception as e:
    st.error(f"⚠️ Critical System Failure: {str(e)}")
    st.stop()


# ==========================================
# === 2. DASHBOARD UI ===
# ==========================================

summ = final_output["summary"] # Updated Key
risk_prof = summ["risk_profile"]

# --- A. HEADS-UP DISPLAY (HUD) ---
st.markdown("### Executive Summary")
c1, c2, c3, c4 = st.columns(4)

# Premium Formatting
c1.metric("Net Worth", f"₹ {summ['total_value']/100000:.2f} L")
c2.metric("Portfolio Health", f"{summ['health_score']}/100", help="Multi-factor score based on Thesis, Valuation, and Efficiency.")
c3.metric("Daily VaR (95%)", f"₹ {risk_prof['daily_var_95_amt']:,.0f}", help="Estimated maximum loss in a single day with 95% confidence.")
c4.metric("Cash Position", f"{risk_prof['cash_position_pct']}%", delta="Liquidity", delta_color="off")

st.divider()

# --- B. VISUAL ANALYTICS ---
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
        text = base.mark_text(radius=120).encode(
            text=alt.Text("Weight", format=".1f"),
            order=alt.Order("Weight", sort="descending"),
            color=alt.value("gray")  
        )
        st.altair_chart(pie + text, width='stretch')

with col_charts_2:
    st.caption("CONCENTRATION RISK")
    top_holdings = df[df["instrument_type"] == "Equity"].sort_values("weight_pct", ascending=False).head(5)
    
    bar_chart = alt.Chart(top_holdings).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
        x=alt.X("weight_pct", title=None, axis=None),
        y=alt.Y("symbol", sort="-x", title=None),
        color=alt.Color("weight_pct", scale=alt.Scale(scheme="blues"), legend=None),
        tooltip=["symbol", "weight_pct"]
    ).properties(height=200)
    
    text_bar = bar_chart.mark_text(align='left', dx=5).encode(text=alt.Text('weight_pct', format='.1f'))
    st.altair_chart(bar_chart + text_bar, width='stretch')

st.markdown("---")


# --- C. INTELLIGENCE TABS ---
tab_actions, tab_details, tab_news = st.tabs(["🚀 Strategic Actions", "🔬 Deep Dive Analysis", "📡 Global Intelligence"])

# TAB 1: STRATEGIC ACTIONS
with tab_actions:
    actions = final_output["actions"] # Updated Key
    if not actions:
        st.success("✅ Portfolio is fully optimized. No critical interventions required.")
    else:
        # Sort by Urgency (Critical First)
        priority_map = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        actions.sort(key=lambda x: priority_map.get(x["urgency"], 99))
        
        for act in actions:
            if act["action"] == "EXIT":
                border_color, bg_color, icon = "#ef4444", "#fef2f2", "🚨"
            elif act["action"] == "REPLACE":
                border_color, bg_color, icon = "#f97316", "#fff7ed", "🔄"
            elif act["action"] == "TRIM":
                border_color, bg_color, icon = "#eab308", "#fefce8", "✂️"
            else:
                border_color, bg_color, icon = "#3b82f6", "#eff6ff", "🔍"

            st.markdown(f"""
            <div style="border-left: 5px solid {border_color}; background-color: {bg_color}; padding: 15px; border-radius: 4px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 1.2rem; font-weight: bold; color: #1f2937;">{icon} {act['symbol']}</span>
                        <span style="background-color: {border_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; margin-left: 10px;">{act['action']}</span>
                    </div>
                    <span style="font-size: 0.8rem; color: #6b7280; font-weight: 600;">URGENCY: {act['urgency'].upper()}</span>
                </div>
                <div style="margin-top: 8px; color: #4b5563; font-size: 0.95rem;">{act['reason']}</div>
            </div>
            """, unsafe_allow_html=True)


# TAB 2: DEEP DIVE TABLE (Updated for New Schema)
with tab_details:
    flat_data = []
    for h in final_output["holdings"]:
        if h["type"] != "Equity": continue # Skip Gold/Liquid for analytics table

        # Extract Alternatives correctly
        alts_data = h["advisory"]["alternatives"]
        alt_str = ", ".join([c["symbol"] for c in alts_data["candidates"]]) if alts_data else ""
        
        flat_data.append({
            "Symbol": h["symbol"],
            "Action": h["advisory"]["action"],
            "Weight %": h['meta']['weight_pct'],
            "Thesis": h["analytics"]["thesis_status"],
            "Valuation": h["analytics"]["valuation_rating"],
            "Momentum": int(h["analytics"]["momentum_score"]),
            "Beta": h["analytics"]["risk_beta"],
            "VaR (₹)": int(h["analytics"]["var_contribution"]),
            "Rationale": h["advisory"]["rationale"],
            "Alternatives": alt_str
        })
    
    df_disp = pd.DataFrame(flat_data)
    
    # Conditional Styling
    def highlight_cells(val):
        if val == 'EXIT': return 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'
        if val == 'REPLACE': return 'background-color: #ffedd5; color: #9a3412; font-weight: bold;'
        if val == 'TRIM': return 'background-color: #fef9c3; color: #854d0e;'
        if val == 'Broken': return 'color: #dc2626; font-weight: bold;'
        if isinstance(val, int) and val < 40: return 'color: #dc2626;' # Low Momentum
        return ''

    st.dataframe(
        df_disp.style.applymap(highlight_cells, subset=['Action', 'Thesis', 'Momentum']),
        width='stretch',
        height=600,
        column_config={
            "Weight %": st.column_config.NumberColumn(format="%.1f"),
            "Momentum": st.column_config.ProgressColumn("Trend Strength", min_value=0, max_value=100, format="%d"),
            "Beta": st.column_config.NumberColumn(format="%.2f"),
            "VaR (₹)": st.column_config.NumberColumn(format="%d"),
            "Rationale": st.column_config.TextColumn("Verdict", width="large"),
        },
        hide_index=True
    )


# TAB 3: INTELLIGENCE (Updated for New Schema)
with tab_news:
    events = final_output["intelligence"] # Updated Key
    if not events:
        st.info("No material catalyst events detected in the current scan window.")
    else:
        # Group by Symbol
        from collections import defaultdict
        grouped = defaultdict(list)
        for e in events: grouped[e["symbol"]].append(e)
            
        # Masonry Layout
        c_news_1, c_news_2 = st.columns(2)
        
        for i, (sym, items) in enumerate(grouped.items()):
            target = c_news_1 if i % 2 == 0 else c_news_2
            with target:
                with st.expander(f"**{sym}** • {len(items)} Events", expanded=True):
                    for item in items:
                        # Color coding based on Category
                        cat = item['impact']
                        if cat in ["Governance Risk", "Deterioration", "Earnings Miss"]:
                            badge_cls = "badge-red"
                        elif cat in ["Earnings Blowout", "Order Book", "Upgrade"]:
                            badge_cls = "badge-blue"
                        else:
                            badge_cls = "badge-orange"
                            
                        st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                                <span class="badge {badge_cls}">{cat}</span> 
                                <span style="font-size:0.8rem; color:#888;">{item['published']}</span>
                            </div>
                            <div style="font-weight:500; font-size:0.95rem; margin-bottom:4px;">{item['headline']}</div>
                            <div style="font-size:0.85rem; color:#555; font-style:italic;">{item['confidence_effect']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.divider()