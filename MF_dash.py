import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. Advanced Radar Interface Configurations
st.set_page_config(page_title="Tactical MF Radar v4.0", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-color: #030803;
        color: #00ff33;
        font-family: 'Courier New', Courier, monospace;
    }
    h1, h2, h3, h4, p, span, div, label, li {
        color: #00ff33 !important;
        font-family: 'Courier New', Courier, monospace !important;
    }
    hr { border-color: #004411; }
    
    /* Input Form Field Aesthetics */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #001100 !important;
        color: #00ff33 !important;
        border: 1px solid #00ff33 !important;
        box-shadow: 0 0 8px #004411;
    }
    
    /* Terminal HUD Data blocks */
    [data-testid="stMetricValue"] {
        color: #00ff33 !important;
        text-shadow: 0 0 10px #00ff33;
        font-size: 2rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: #00aa22 !important;
    }
    
    /* Radar Scan Action Button */
    .stButton>button {
        background-color: #002200;
        color: #00ff33;
        border: 2px solid #00ff33;
        box-shadow: 0 0 12px #002200;
        font-weight: bold;
        letter-spacing: 2px;
        transition: all 0.4s ease;
    }
    .stButton>button:hover {
        background-color: #00ff33;
        color: #030803 !important;
        box-shadow: 0 0 20px #00ff33;
    }
    
    /* Intercept Diagnostic Panel */
    .radar-intercept {
        background-color: #001100;
        border: 2px dashed #00ff33;
        padding: 20px;
        border-radius: 4px;
        margin: 15px 0px;
        box-shadow: inset 0 0 15px rgba(0, 255, 51, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# 2. Local Strategic Backup Directory (Prevents 502 Server Crashes)
LOCAL_RADAR_DB = {
    "Parag Parikh Flexi Cap Fund (Direct - Growth)": "122639",
    "HDFC Balanced Advantage Fund (Direct - Growth)": "119063",
    "ICICI Prudential Balanced Advantage Fund (Direct - Growth)": "119566",
    "Quant Small Cap Fund (Direct - Growth)": "120847",
    "Nippon India Small Cap Fund (Direct - Growth)": "119851",
    "SBI Small Cap Fund (Direct - Growth)": "125354",
    "ICICI Prudential Dynamic Asset Allocation Active FOF (Direct)": "128913",
    "HDFC Flexi Cap Fund (Direct - Growth)": "119036"
}

def identify_alternatives(fund_name):
    """Instant Category Matchmaking Matrix"""
    name = fund_name.lower()
    if any(k in name for k in ['dynamic', 'balanced', 'baf', 'asset allocation', 'fof']):
        return [
            "🟢 HDFC Balanced Advantage Fund (Direct) | Category Alpha Dominator",
            "🟢 Edelweiss Balanced Advantage Fund (Direct) | Rule-Based Systematic Shield",
            "🟢 ICICI Prudential Balanced Advantage Fund (Direct) | Value Asset Allocator"
        ]
    elif any(k in name for k in ['small', 'smallcap']):
        return [
            "🟢 Nippon India Small Cap Fund (Direct) | Scaled Liquidity Engine",
            "🟢 Quant Small Cap Fund (Direct) | Ultra-High Kinetic Momentum",
            "🟢 Axis Small Cap Fund (Direct) | Deep Downside Protection"
        ]
    elif 'flexi' in name:
        return [
            "🟢 Parag Parikh Flexi Cap Fund (Direct) | Global Vanguard Core",
            "🟢 HDFC Flexi Cap Fund (Direct) | High Conviction Value Allocation",
            "🟢 Quant Flexi Cap Fund (Direct) | Macro Dynamic Tactical Swings"
        ]
    else:
        return [
            "🟢 Parag Parikh Flexi Cap Fund (Direct) | Standard Core Equity Choice",
            "🟢 HDFC Balanced Advantage Fund (Direct) | Standard Defensive Hybrid Choice",
            "🟢 UTI Nifty 50 Index Fund (Direct) | Clean Systematic Cost Minimizer"
        ]

# 3. Main HUD Interface Layout
st.title("📡 TACTICAL MF RADAR Terminal v4.0")
st.markdown("SYSTEM STATUS: **ONLINE** | ENCRYPTED ANTI-JAMMING PROTOCOLS RE-ENGAGED")
st.write("---")

# Split control grid into parallel frequencies
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("⚡ TARGET ACQUISITION")
    query = st.text_input("SCAN SYSTEM AIRSPACE (Type keywords like 'icici fof', 'parag', 'small cap'):", "").strip()
    
    final_scheme_code = None
    final_scheme_name = None
    
    if query:
        # Step A: Filter local database targets instantly for Zero-Latency responsiveness
        local_matches = {k: v for k, v in LOCAL_RADAR_DB.items() if query.lower() in k.lower()}
        
        search_results = []
        server_status = "ONLINE"
        
        # Step B: Attempt network telemetry query only if local cache yields nothing
        if not local_matches:
            try:
                response = requests.get(f"https://api.mfapi.in/mf/search?q={query}", timeout=5)
                if response.status_code == 200:
                    search_results = response.json()
                else:
                    server_status = f"JAMMED (HTTP {response.status_code})"
            except Exception:
                server_status = "HARD OFFLINE"
        
        # Step C: Consolidate target selection pathways
        if local_matches:
            selected_target = st.selectbox("LOCKING LOCAL SIGNAL VECTOR:", list(local_matches.keys()))
            final_scheme_code = local_matches[selected_target]
            final_scheme_name = selected_target
        elif search_results:
            api_map = {item['schemeName']: item['schemeCode'] for item in search_results}
            selected_target = st.selectbox("LOCKING EXTERNAL SATELLITE SIGNAL:", list(api_map.keys()))
            final_scheme_code = api_map[selected_target]
            final_scheme_name = selected_target
        else:
            st.warning(f"⚠️ AMFI MAIN ARRAY IS {server_status}. ENGAGING EMERGENCY MANUAL SCAN MODE.")
            manual_code = st.text_input("INPUT 6-DIGIT AMFI DESIGNATION CODE DIRECTLY:", "")
            if manual_code.isdigit():
                final_scheme_code = manual_code
                final_scheme_name = f"MANUAL TARGET DESIGNATION [#{manual_code}]"

with col_right:
    st.subheader("🎯 INTERCEPT DIAGNOSTICS")
    if final_scheme_name:
        recommendations = identify_alternatives(final_scheme_name)
        st.markdown(f"""
        <div class="radar-intercept">
            <h4 style='margin-top:0;'>⚠️ RADAR INTERCEPT ADVISORY</h4>
            <p>Target Tracked: <b>{final_scheme_name}</b></p>
            <p><b>CRITICAL RECON:</b> The intercept grid strongly advises substituting or combining this selection with these top 3 high-performance direct alternatives:</p>
            <ul style='padding-left:20px; margin-bottom:0;'>
                <li>{recommendations[0]}</li>
                <li>{recommendations[1]}</li>
                <li>{recommendations[2]}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("AWAITING ACQUISITION SYSTEM LOGINS... RADAR SCOPE IS CLEAR.")

# 4. Heavy Telemetry Processing Engine
if final_scheme_code:
    st.write("---")
    if st.button("🔴 FIRE DEEP QUANT RADAR SWEEP"):
        with st.spinner("TRANSMITTING KINETIC RISK PROBES..."):
            try:
                raw_response = requests.get(f"https://api.mfapi.in/mf/{final_scheme_code}", timeout=7)
                if raw_response.status_code == 200:
                    payload = raw_response.json()
                    
                    if 'data' in payload and len(payload['data']) > 0:
                        df = pd.DataFrame(payload['data'])
                        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
                        df['nav'] = pd.to_numeric(df['nav'])
                        df = df.sort_values('date').reset_index(drop=True)
                        
                        # Mathematical Metrics Processing
                        df['Daily_Return'] = df['nav'].pct_change()
                        total_days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
                        
                        if total_days > 365:
                            absolute_return = (df['nav'].iloc[-1] / df['nav'].iloc[0]) - 1
                            cagr = ((1 + absolute_return) ** (365.25 / total_days)) - 1
                            
                            rfr = 0.065
                            volatility = df['Daily_Return'].std() * np.sqrt(252)
                            downside_vol = df[df['Daily_Return'] < 0]['Daily_Return'].std() * np.sqrt(252)
                            
                            sharpe = (cagr - rfr) / volatility if volatility > 0 else 0
                            sortino = (cagr - rfr) / downside_vol if downside_vol > 0 else 0
                            
                            st.subheader(f"📊 HISTORICAL METRICS PROFILE: {final_scheme_name}")
                            m1, m2, m3 = st.columns(3)
                            m1.metric("CAGR (ANNUAL VELOCITY)", f"{cagr*100:.2f}%")
                            m2.metric("SHARPE (EFFICIENCY COEFFICIENT)", f"{sharpe:.2f}")
                            m3.metric("SORTINO (DOWNSIDE DEFENSE FORCE)", f"{sortino:.2f}")
                            
                            st.markdown("### 📈 TRAJECTORY MONITOR")
                            st.line_chart(df.set_index('date')['nav'], color="#00ff33")
                        else:
                            st.error("TELEMETRY ERROR: Under 365 days of chronological data. Metrics cannot compile.")
                    else:
                        st.error("TELEMETRY FAILURE: Scheme envelope matched but historical data payload is empty.")
                else:
                    st.error(f"COMBAT ALERT: Remote server rejected history request with error code {raw_response.status_code}")
            except Exception as e:
                st.error(f"SIGNAL TIMEOUT: The AMFI data pipeline failed to respond. Try manually running code tracking later.")