import streamlit as st
import pandas as pd
import numpy as np

# 1. System Config
st.set_page_config(page_title="Consolidated Portfolio Forecaster", layout="wide")
st.title("🧮 Live Portfolio & SIF Forecasting Engine")
st.markdown("SYSTEM STATUS: **ACTIVE** | MODE: **STOCHASTIC BROWNIAN MOTION (BLENDED BETA)**")

# 2. Hardcoded Actual Portfolio State (From User Radar)
# Consolidating the massive 2.25 Cr portfolio to calculate blended baseline volatility
ACTUAL_HOLDINGS = {
    "SBI ELSS Tax Saver Fund": {"Current_Value": 6770000},
    "ICICI Pru Dynamic Asset FOF": {"Current_Value": 3813000},
    "Parag Parikh Flexi Cap": {"Current_Value": 3096000},
    "HDFC Flexi Cap": {"Current_Value": 2016000},
    "Edelweiss Nifty Next 50": {"Current_Value": 1564000},
    "HDFC Balanced Advantage": {"Current_Value": 1000000},
    "Others (Arbitrage, Liquid, Small Caps)": {"Current_Value": 4280965}
}

TOTAL_BASELINE_VALUE = sum(item["Current_Value"] for item in ACTUAL_HOLDINGS.values())
BLENDED_VOLATILITY = 0.14  # Much lower than small-caps due to heavy FOF/BAF/Arbitrage presence

# 3. Parameter Control
st.sidebar.header("⚙️ MACRO PARAMETERS")

st.sidebar.subheader("Near-Term: The Disruption (0-24 Months)")
market_correction = st.sidebar.slider("Broader Market Correction Severity (%)", min_value=0, max_value=50, value=25, step=5)
tech_disruption = st.sidebar.slider("IT/Tech Sector Drag (%)", min_value=0, max_value=40, value=15, step=5)

st.sidebar.subheader("Far-Future: Mean Reversion (24-60 Months)")
recovery_rate = st.sidebar.slider("Market Recovery Velocity (CAGR %)", min_value=5, max_value=25, value=14, step=1)

st.sidebar.subheader("Structural Mechanics")
sif_efficiency = st.sidebar.slider("SIF Short-Hedge Capture (%)", min_value=0, max_value=30, value=15, step=1)

# 4. The Predictive Engine
def simulate_actual_portfolio(combination_mode, days=1260, simulations=500):
    np.random.seed(42)
    shock_days = 504 
    recovery_days = days - shock_days
    
    all_combined_paths = []
    
    for _ in range(simulations):
        # 1. Simulate the ₹2.25 Cr Baseline Portfolio
        # It drops less than the market due to BAFs/Arbitrage components
        baseline_shock_mu = -((market_correction * 0.8) / 100) / 252 
        baseline_shock_returns = np.random.normal(baseline_shock_mu, BLENDED_VOLATILITY / np.sqrt(252), shock_days)
        
        baseline_recov_mu = ((recovery_rate * 0.9) / 100) / 252 # Trails pure equity slightly in a bull run
        baseline_recov_returns = np.random.normal(baseline_recov_mu, BLENDED_VOLATILITY / np.sqrt(252), recovery_days)
        
        baseline_total_returns = np.concatenate([baseline_shock_returns, baseline_recov_returns])
        baseline_path = TOTAL_BASELINE_VALUE * np.exp(np.cumsum(baseline_total_returns))
        
        # 2. Simulate the New ₹10 Lakh Tranche
        new_tranche_initial = 1000000
        
        if combination_mode == "Overlay Flexi Cap":
            tranche_shock_mu = -((market_correction + tech_disruption) / 100) / 252
            tranche_shock_vol = 0.16 / np.sqrt(252)
            tranche_recov_mu = (recovery_rate / 100) / 252
            tranche_recov_vol = 0.14 / np.sqrt(252)
            
        elif combination_mode == "Overlay SIF":
            net_drop = max(0, market_correction - sif_efficiency)
            tranche_shock_mu = -(net_drop / 100) / 252
            tranche_shock_vol = 0.11 / np.sqrt(252) 
            tranche_recov_mu = ((recovery_rate - 1) / 100) / 252 
            tranche_recov_vol = 0.12 / np.sqrt(252)

        tranche_shock_returns = np.random.normal(tranche_shock_mu, tranche_shock_vol, shock_days)
        tranche_recov_returns = np.random.normal(tranche_recov_mu, tranche_recov_vol, recovery_days)
        tranche_total_returns = np.concatenate([tranche_shock_returns, tranche_recov_returns])
        tranche_path = new_tranche_initial * np.exp(np.cumsum(tranche_total_returns))
        
        # 3. Combine Wealth
        combined_path = baseline_path + tranche_path
        all_combined_paths.append(combined_path)
        
    matrix = np.array(all_combined_paths)
    return np.percentile(matrix, 50, axis=0) 

# 5. Execute Simulation
with st.spinner("CALCULATING CONSOLIDATED VECTORS..."):
    path_flexi = simulate_actual_portfolio("Overlay Flexi Cap")
    path_sif = simulate_actual_portfolio("Overlay SIF")
    
    date_index = pd.date_range(start=pd.Timestamp.today(), periods=1260, freq='B')
    
    df_chart = pd.DataFrame({
        "Date": date_index,
        "Total Net Worth (+Flexi Cap)": path_flexi,
        "Total Net Worth (+SIF)": path_sif
    }).set_index("Date")

# 6. Dashboard Render
st.subheader("📋 Verified Portfolio Architecture")
col_a, col_b = st.columns(2)
with col_a:
    for fund, data in list(ACTUAL_HOLDINGS.items())[:4]:
        st.write(f"**{fund}:** ₹{data['Current_Value']/100000:,.2f} Lakhs")
with col_b:
    for fund, data in list(ACTUAL_HOLDINGS.items())[4:]:
        st.write(f"**{fund}:** ₹{data['Current_Value']/100000:,.2f} Lakhs")

st.info(f"**Aggregate Baseline Value Tracked:** ₹{TOTAL_BASELINE_VALUE/10000000:,.2f} Crores | **New Deployment:** ₹10 Lakhs")
st.write("---")

c1, c2 = st.columns(2)
initial_combined = TOTAL_BASELINE_VALUE + 1000000

with c1:
    st.markdown("### 🔴 Path A: Baseline + Flexi Cap")
    bottom_f = path_flexi[504]
    final_f = path_flexi[-1]
    st.metric("Total Value at Crash Bottom", f"₹{bottom_f/10000000:,.2f} Cr", f"{((bottom_f-initial_combined)/initial_combined)*100:.1f}%", delta_color="inverse")
    st.metric("Final Projected Value (Year 5)", f"₹{final_f/10000000:,.2f} Cr", f"{((final_f-initial_combined)/initial_combined)*100:.1f}%")

with c2:
    st.markdown("### 🟢 Path B: Baseline + Hedged SIF")
    bottom_s = path_sif[504]
    final_s = path_sif[-1]
    st.metric("Total Value at Crash Bottom", f"₹{bottom_s/10000000:,.2f} Cr", f"{((bottom_s-initial_combined)/initial_combined)*100:.1f}%", delta_color="inverse")
    st.metric("Final Projected Value (Year 5)", f"₹{final_s/10000000:,.2f} Cr", f"{((final_s-initial_combined)/initial_combined)*100:.1f}%")

st.write("---")
st.subheader("📉 Consolidated Net Worth Trajectory (5 Years)")
st.line_chart(df_chart, color=["#FF4B4B", "#00FF33"])