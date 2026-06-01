import streamlit as st
import pandas as pd
import numpy as np

# 1. Page Configuration & UI Formatting
st.set_page_config(page_title="Dynamic Institutional Wealth Forecaster", layout="wide")
st.title("🛡️ Institutional Wealth & Dynamic SIF Forecast Engine")
st.markdown("SYSTEM STATUS: **DYNAMIC AIRSPACE MAPPER ONLINE** | HARDCODING: **DEACTIVATED**")

# 2. Sidebar Risk Parametrization
st.sidebar.header("⚡ Macro Stress Parameters")
st.sidebar.write("Model the structural AI shift over a 5-year continuum.")

st.sidebar.subheader("Near-Term: Systemic Shock (0-24 Months)")
market_correction = st.sidebar.slider("Broader Indian Equity Correction (%)", min_value=0, max_value=50, value=25, step=5)
tech_disruption = st.sidebar.slider("IT Services/Tech Drag Over-Index (%)", min_value=0, max_value=40, value=15, step=5)

st.sidebar.subheader("Far-Future: Cyclical Recovery (24-60 Months)")
recovery_rate = st.sidebar.slider("Post-Crash Market Recovery (CAGR %)", min_value=5, max_value=25, value=14, step=1)

st.sidebar.subheader("SIF Alpha Mechanics")
sif_short_efficiency = st.sidebar.slider("SIF Short-Hedge Downside Capture (%)", min_value=0, max_value=30, value=15, step=1)

# New Tranche Scaler
st.sidebar.subheader("Capital Allocation")
NEW_TRANCHE = st.sidebar.number_input("Fresh Deployable Capital (₹)", min_value=100000, max_value=100000000, value=1000000, step=100000, format="%d")

# 3. Dynamic Asset Acquisition Layer (CSV Upload / Manual Table Editor)
st.subheader("📋 Dynamic Asset Registry Matrix")
st.write("Upload your portfolio holdings CSV file below, or interactively modify/add assets directly in the spreadsheet grid.")

uploaded_file = st.file_uploader("Upload Portfolio CSV Template (Columns required: Fund_Name, Current_Value, Asset_Type)", type=["csv"])

# Default fallback structural template if no file uploaded yet
default_template = pd.DataFrame({
    "Fund_Name": ["Template Equity Asset 1", "Template Alternative Asset 1 (SIF)"],
    "Current_Value": [10000000, 1000000],
    "Asset_Type": ["Mutual Fund", "SIF"]
})

if uploaded_file is not None:
    try:
        raw_df = pd.read_csv(uploaded_file)
        # Ensure mandatory columns exist
        if all(col in raw_df.columns for col in ["Fund_Name", "Current_Value", "Asset_Type"]):
            working_df = raw_df
            st.success("Target asset file parsed successfully.")
        else:
            st.error("CSV Structure Error: Template must contain 'Fund_Name', 'Current_Value', and 'Asset_Type' columns.")
            working_df = default_template
    except Exception as e:
        st.error(f"File Read Failure: {str(e)}")
        working_df = default_template
else:
    working_df = default_template
    st.info("Operating under sandbox baseline. Upload your generated portfolio CSV file to view your precise assets.")

# Expose an editable grid to the user to manipulate records or add rows manually
edited_df = st.data_editor(
    working_df, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "Current_Value": st.column_config.NumberColumn("Current Valuation (₹)", format="%d"),
        "Asset_Type": st.column_config.SelectboxColumn("Asset Classification", options=["Mutual Fund", "SIF"])
    }
)

# 4. Runtime Aggregation
# Calculate live aggregates dynamically based on user manual changes or CSV payload
MUTUAL_FUND_VAL = edited_df[edited_df["Asset_Type"] == "Mutual Fund"]["Current_Value"].sum()
EXISTING_SIF_VAL = edited_df[edited_df["Asset_Type"] == "SIF"]["Current_Value"].sum()
TOTAL_EX_ANTE_WEALTH = MUTUAL_FUND_VAL + EXISTING_SIF_VAL

# 5. Stochastic Math Simulation Engine
def run_wealth_simulation(allocation_strategy, days=1260, simulations=300):
    if TOTAL_EX_ANTE_WEALTH <= 0:
        return np.zeros(days)
        
    np.random.seed(42) 
    shock_days = 504 
    recovery_days = days - shock_days
    
    mf_vol = 0.13
    sif_vol = 0.09
    
    all_wealth_paths = []
    
    for _ in range(simulations):
        # --- PHASE 1: THE NEAR-TERM CRASH (Days 0 to 504) ---
        mf_shock_mu = -((market_correction * 0.85) / 100) / 252
        sif_shock_mu = -(max(0, market_correction - sif_short_efficiency) / 100) / 252
        
        mf_shock_ret = np.random.normal(mf_shock_mu, mf_vol / np.sqrt(252), shock_days)
        sif_shock_ret = np.random.normal(sif_shock_mu, sif_vol / np.sqrt(252), shock_days)
        
        if allocation_strategy == "Deploy New Tranche in Flexi Cap":
            new_shock_mu = -((market_correction + tech_disruption) / 100) / 252
            new_shock_ret = np.random.normal(new_shock_mu, 0.16 / np.sqrt(252), shock_days)
        else: 
            new_shock_mu = sif_shock_mu
            new_shock_ret = np.random.normal(new_shock_mu, sif_vol / np.sqrt(252), shock_days)
            
        # --- PHASE 2: THE FAR-FUTURE REBOUND (Days 504 to 1260) ---
        mf_recov_mu = (recovery_rate / 100) / 252
        sif_recov_mu = ((recovery_rate - 1.5) / 100) / 252 
        
        mf_recov_ret = np.random.normal(mf_recov_mu, mf_vol / np.sqrt(252), recovery_days)
        sif_recov_ret = np.random.normal(sif_recov_mu, sif_vol / np.sqrt(252), recovery_days)
        
        if allocation_strategy == "Deploy New Tranche in Flexi Cap":
            new_recov_ret = np.random.normal(mf_recov_mu, 0.15 / np.sqrt(252), recovery_days)
        else:
            new_recov_ret = np.random.normal(sif_recov_mu, sif_vol / np.sqrt(252), recovery_days)
            
        # --- COMPILING THE TRACKS ---
        mf_total_ret = np.concatenate([mf_shock_ret, mf_recov_ret])
        sif_total_ret = np.concatenate([sif_shock_ret, sif_recov_ret])
        new_total_ret = np.concatenate([new_shock_ret, new_recov_ret])
        
        path_mf_core = MUTUAL_FUND_VAL * np.exp(np.cumsum(mf_total_ret))
        path_sif_core = EXISTING_SIF_VAL * np.exp(np.cumsum(sif_total_ret))
        path_new_tranche = NEW_TRANCHE * np.exp(np.cumsum(new_total_ret))
        
        total_consolidated_path = path_mf_core + path_sif_core + path_new_tranche
        all_wealth_paths.append(total_consolidated_path)
        
    matrix = np.array(all_wealth_paths)
    return np.percentile(matrix, 50, axis=0) 

# 6. Dashboard Render Panel
if TOTAL_EX_ANTE_WEALTH > 0:
    st.write("---")
    c_reg1, c_reg2 = st.columns(2)
    with c_reg1:
        st.metric("Total Mutual Fund Capital", f"₹{MUTUAL_FUND_VAL:,.2f}")
        st.metric("Total Alternative SIF Capital", f"₹{EXISTING_SIF_VAL:,.2f}")
    with c_reg2:
        st.metric("Consolidated Portfolio Valuation Balance", f"₹{TOTAL_EX_ANTE_WEALTH:,.2f}")
        st.metric("Target New Deployable Deployment Tranche", f"₹{NEW_TRANCHE:,.2f}")

    st.write("---")
    with st.spinner("Processing Matrix Simulations..."):
        timeline = pd.date_range(start=pd.Timestamp.today(), periods=1260, freq='B')
        
        path_flexi_overlay = run_wealth_simulation("Deploy New Tranche in Flexi Cap")
        path_sif_overlay = run_wealth_simulation("Deploy New Tranche in SIF (Double Down)")
        
        df_chart = pd.DataFrame({
            "Date": timeline,
            f"Total Wealth Matrix (New Tranche → Flexi Cap)": path_flexi_overlay,
            f"Total Wealth Matrix (New Tranche → SIF Growth)": path_sif_overlay
        }).set_index("Date")

    col_metrics1, col_metrics2 = st.columns(2)
    starting_capital = TOTAL_EX_ANTE_WEALTH + NEW_TRANCHE

    with col_metrics1:
        st.markdown("### 🔴 Allocation Scenario A: Route Tranche to Flexi Cap")
        bottom_f = path_flexi_overlay[504]
        final_f = path_flexi_overlay[-1]
        st.metric("Portfolio Drop Floor (Year 2 Bottom)", f"₹{bottom_f:,.2f}", f"Drawdown: {((bottom_f-starting_capital)/starting_capital)*100:.2f}%", delta_color="inverse")
        st.metric("5-Year Terminal Wealth Target", f"₹{final_f:,.2f}", f"Net Return: {((final_f-starting_capital)/starting_capital)*100:.2f}%")

    with col_metrics2:
        st.markdown("### 🟢 Allocation Scenario B: Route Tranche to SIF Expansion")
        bottom_s = path_sif_overlay[504]
        final_s = path_sif_overlay[-1]
        st.metric("Portfolio Drop Floor (Year 2 Bottom)", f"₹{bottom_s:,.2f}", f"Drawdown: {((bottom_s-starting_capital)/starting_capital)*100:.2f}%", delta_color="inverse")
        st.metric("5-Year Terminal Wealth Target", f"₹{final_s:,.2f}", f"Net Return: {((final_s-starting_capital)/starting_capital)*100:.2f}%")

    st.write("---")
    st.subheader("📉 Dynamic Wealth Trajectory Simulation Projection")
    st.line_chart(df_chart, color=["#FF4B4B", "#00FF33"])
else:
    st.warning("Awaiting configuration data inside registry. Add values or upload your template CSV above.")