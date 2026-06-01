import streamlit as st
import pandas as pd
import numpy as np

# 1. Page Configuration
st.set_page_config(page_title="Multi-Statement Wealth Forecaster", layout="wide")
st.title("🛡️ Institutional Wealth & Multi-Statement Forecast Engine")
st.markdown("SYSTEM STATUS: **MULTIPLE FILE INGESTION LAYER ACTIVE** | HARDCODING: **DEACTIVATED**")

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

# 3. Multi-CSV Ingestion Layer
st.subheader("📥 Aggregated Asset Registry Matrix")
st.write("Upload one or multiple portfolio CSV files (e.g., separate files for Mutual Funds and SIFs). The engine will automatically merge them.")

# Enabling multiple file uploads
uploaded_files = st.file_uploader(
    "Upload Portfolio CSV Templates (Columns required: Fund_Name, Current_Value, Asset_Type)", 
    type=["csv"], 
    accept_multiple_files=True
)

# Baseline placeholder frame if no files are present
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
            # Standardize column naming rules to prevent key misses
            raw_df.columns = raw_df.columns.str.strip()
            
            # Verify required structural headers match
            required_cols = ["Fund_Name", "Current_Value", "Asset_Type"]
            if all(col in raw_df.columns for col in required_cols):
                parsed_dataframes.append(raw_df[required_cols])
                st.toast(f"Successfully processed: {uploaded_file.name}", icon="✅")
            else:
                st.error(f"Structure Mismatch in '{uploaded_file.name}': Missing one of {required_cols}")
        except Exception as e:
            st.error(f"Failed to read '{uploaded_file.name}': {str(e)}")

    if parsed_dataframes:
        # Concatenate all valid sheets into an integrated master list
        combined_df = pd.concat(parsed_dataframes, ignore_index=True)
        # Drop identical rows to clear duplicate entries across statements
        working_df = combined_df.drop_duplicates().reset_index(drop=True)
    else:
        working_df = default_template
else:
    working_df = default_template
    st.info("Operating under baseline sandbox. Upload your portfolio CSV files to view combined actual holdings.")

# Expose an editable aggregate grid to manually tweak entries on the fly
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
        st.metric("Total Consolidated Mutual Funds", f"₹{MUTUAL_FUND_VAL:,.2f}")
        st.metric("Total Consolidated SIF Assets", f"₹{EXISTING_SIF_VAL:,.2f}")
    with c_reg2:
        st.metric("Aggregate Combined Net Worth", f"₹{TOTAL_EX_ANTE_WEALTH:,.2f}")
        st.metric("Fresh Target Allocation Tranche", f"₹{NEW_TRANCHE:,.2f}")

    st.write("---")
    with st.spinner("Processing Multi-Statement Matrix Simulations..."):
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
    st.subheader("📉 Consolidated Wealth Trajectory Simulation Projection")
    st.line_chart(df_chart, color=["#FF4B4B", "#00FF33"])
else:
    st.warning("Awaiting statement uploads. Drag and drop your portfolio CSVs above.")