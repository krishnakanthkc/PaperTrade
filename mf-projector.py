import streamlit as st
import pandas as pd
import numpy as np

# 1. Page Configuration
st.set_page_config(page_title="Regime-Aware Wealth Forecaster", layout="wide")
st.title("🛡️ Institutional Wealth & Regime Forecast Engine")
st.markdown("SYSTEM STATUS: **REGIME MAPPER ACTIVE** | MULTI-FILE INGESTION: **ONLINE**")

# 2. Sidebar Risk Parametrization & Regime Control
st.sidebar.header("🌍 Market Regime Selector")
st.sidebar.write("Select a macroeconomic environment to auto-configure the math, or use Custom to build your own.")

regime = st.sidebar.radio(
    "Select Macro Environment Preset:",
    ("Custom (Manual Setup)", "Bull Run (Expansion)", "Bear Run (AI Tech Shock)", "Balanced Run (Sideways)")
)

st.sidebar.markdown("---")

# Pre-configured Regime Logic
if regime == "Bull Run (Expansion)":
    market_correction = 0
    tech_disruption = 0
    recovery_rate = 18
    sif_short_efficiency = 5
    st.sidebar.success("**Bull Run Active:** Zero market shock. High mean-reversion drift. SIF will lag Flexi Cap due to unnecessary hedging costs.")
    
elif regime == "Bear Run (AI Tech Shock)":
    market_correction = 35
    tech_disruption = 20
    recovery_rate = 12
    sif_short_efficiency = 22
    st.sidebar.error("**Bear Run Active:** Severe initial drop with heavily penalized IT sector. SIF short-alpha acts as a major capital shield.")

elif regime == "Balanced Run (Sideways)":
    market_correction = 10
    tech_disruption = 5
    recovery_rate = 8
    sif_short_efficiency = 15
    st.sidebar.info("**Balanced Run Active:** Churning, range-bound market. Low broader recovery. SIF generates steady alpha via long/short pair trading.")

else:
    st.sidebar.subheader("⚙️ Custom Parameters")
    market_correction = st.sidebar.slider("Broader Indian Equity Correction (%)", min_value=0, max_value=50, value=25, step=5)
    tech_disruption = st.sidebar.slider("IT Services/Tech Drag Over-Index (%)", min_value=0, max_value=40, value=15, step=5)
    recovery_rate = st.sidebar.slider("Post-Crash Market Recovery (CAGR %)", min_value=5, max_value=25, value=14, step=1)
    sif_short_efficiency = st.sidebar.slider("SIF Short-Hedge Downside Capture (%)", min_value=0, max_value=30, value=15, step=1)

st.sidebar.markdown("---")
# New Tranche Scaler
st.sidebar.subheader("Capital Allocation")
NEW_TRANCHE = st.sidebar.number_input("Fresh Deployable Capital (₹)", min_value=100000, max_value=100000000, value=1000000, step=100000, format="%d")

# 3. Multi-CSV Ingestion Layer
st.subheader("📥 Aggregated Asset Registry Matrix")
uploaded_files = st.file_uploader(
    "Upload Portfolio CSV Templates (Columns required: Fund_Name, Current_Value, Asset_Type)", 
    type=["csv"], 
    accept_multiple_files=True
)

default_template = pd.DataFrame({
    "Fund_Name": ["Template Equity Asset 1", "Template Alternative Asset 1 (SIF)"],
    "Current_Value": [10000000, 1000000],
    "Asset_Type": ["Mutual Fund", "SIF"]
})

parsed_dataframes = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            raw_df = pd.read_csv(uploaded_file)
            raw_df.columns = raw_df.columns.str.strip()
            required_cols = ["Fund_Name", "Current_Value", "Asset_Type"]
            if all(col in raw_df.columns for col in required_cols):
                parsed_dataframes.append(raw_df[required_cols])
            else:
                st.error(f"Structure Mismatch in '{uploaded_file.name}'")
        except Exception as e:
            st.error(f"Failed to read '{uploaded_file.name}': {str(e)}")

    if parsed_dataframes:
        combined_df = pd.concat(parsed_dataframes, ignore_index=True)
        working_df = combined_df.drop_duplicates().reset_index(drop=True)
    else:
        working_df = default_template
else:
    working_df = default_template

edited_df = st.data_editor(
    working_df, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "Current_Value": st.column_config.NumberColumn("Current Valuation (₹)", format="%d"),
        "Asset_Type": st.column_config.SelectboxColumn("Asset Classification", options=["Mutual Fund", "SIF"])
    }
)

# 4. In-Memory Runtime Aggregation
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
        # PHASE 1: SHOCK REGIME
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
            
        # PHASE 2: RECOVERY REGIME
        mf_recov_mu = (recovery_rate / 100) / 252
        # SIF deduction accounts for hedge drag during pure upside moves
        sif_recov_mu = ((recovery_rate - 2.0) / 100) / 252 
        
        mf_recov_ret = np.random.normal(mf_recov_mu, mf_vol / np.sqrt(252), recovery_days)
        sif_recov_ret = np.random.normal(sif_recov_mu, sif_vol / np.sqrt(252), recovery_days)
        
        if allocation_strategy == "Deploy New Tranche in Flexi Cap":
            new_recov_ret = np.random.normal(mf_recov_mu, 0.15 / np.sqrt(252), recovery_days)
        else:
            new_recov_ret = np.random.normal(sif_recov_mu, sif_vol / np.sqrt(252), recovery_days)
            
        # COMPILE PATHS
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
    with st.spinner(f"Processing Matrix Simulations for {regime}..."):
        timeline = pd.date_range(start=pd.Timestamp.today(), periods=1260, freq='B')
        
        path_flexi_overlay = run_wealth_simulation("Deploy New Tranche in Flexi Cap")
        path_sif_overlay = run_wealth_simulation("Deploy New Tranche in SIF (Double Down)")
        
        df_chart = pd.DataFrame({
            "Date": timeline,
            "Total Net Worth (New Tranche → Flexi Cap)": path_flexi_overlay,
            "Total Net Worth (New Tranche → SIF Expansion)": path_sif_overlay
        }).set_index("Date")

    col_metrics1, col_metrics2 = st.columns(2)
    starting_capital = TOTAL_EX_ANTE_WEALTH + NEW_TRANCHE

    with col_metrics1:
        st.markdown("### 🔴 Scenario A: Route New Tranche to Flexi Cap")
        bottom_f = path_flexi_overlay[504]
        final_f = path_flexi_overlay[-1]
        st.metric("Combined Floor Value (Year 2 Bottom)", f"₹{bottom_f:,.2f}", f"Drawdown: {((bottom_f-starting_capital)/starting_capital)*100:.2f}%", delta_color="inverse")
        st.metric("5-Year Terminal Asset Target", f"₹{final_f:,.2f}", f"Net Return: {((final_f-starting_capital)/starting_capital)*100:.2f}%")

    with col_metrics2:
        st.markdown("### 🟢 Scenario B: Route New Tranche to SIF Expansion")
        bottom_s = path_sif_overlay[504]
        final_s = path_sif_overlay[-1]
        st.metric("Combined Floor Value (Year 2 Bottom)", f"₹{bottom_s:,.2f}", f"Drawdown: {((bottom_s-starting_capital)/starting_capital)*100:.2f}%", delta_color="inverse")
        st.metric("5-Year Terminal Asset Target", f"₹{final_s:,.2f}", f"Net Return: {((final_s-starting_capital)/starting_capital)*100:.2f}%")

    st.write("---")
    st.subheader(f"📉 Consolidated Wealth Trajectory: {regime}")
    st.line_chart(df_chart, color=["#FF4B4B", "#00FF33"])
else:
    st.warning("Awaiting statement uploads. Drag and drop your portfolio CSVs above.")