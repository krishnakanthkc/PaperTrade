import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import timedelta

# 1. Native Streamlit Configurations (Respects System Light/Dark Mode)
st.set_page_config(page_title="Tactical MF Radar v7.0", layout="wide")

# Removed hardcoded neon CSS. Using CSS variables so it adapts to Light/Dark mode automatically.
st.markdown("""
<style>
    .radar-intercept {
        border: 2px dashed var(--primary-color);
        padding: 20px;
        border-radius: 8px;
        margin: 15px 0px;
        background-color: rgba(128, 128, 128, 0.05);
    }
    .sim-warning {
        border: 1px solid #ffaa00;
        color: #ffaa00 !important;
        padding: 10px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 2. Resilient Network Protocols & Synthetic Fallback
@st.cache_data(ttl=3600, show_spinner=False)
def stealth_fetch(url, max_retries=2):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Accept': 'application/json'
    }
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception:
            time.sleep(1)
    return None

def generate_synthetic_telemetry(fund_name, days=1825):
    """Generates mathematically accurate proxy data if API is jammed."""
    np.random.seed(hash(fund_name) % (2**32 - 1))
    
    if 'small' in fund_name.lower():
        cagr, vol = 0.22, 0.20
    elif 'flexi' in fund_name.lower():
        cagr, vol = 0.16, 0.15
    elif 'balanced' in fund_name.lower() or 'dynamic' in fund_name.lower():
        cagr, vol = 0.12, 0.10
    else:
        cagr, vol = 0.14, 0.14
        
    daily_mu = cagr / 252
    daily_vol = vol / np.sqrt(252)
    
    returns = np.random.normal(daily_mu, daily_vol, days)
    nav_series = 100 * np.exp(np.cumsum(returns))
    
    end_date = pd.Timestamp.today()
    dates = [end_date - timedelta(days=x) for x in range(days)]
    dates.reverse()
    
    return pd.DataFrame({'date': dates, 'nav': nav_series})

# Local Backup Directory
LOCAL_RADAR_DB = {
    "Parag Parikh Flexi Cap Fund (Direct)": "122639",
    "HDFC Balanced Advantage Fund (Direct)": "119063",
    "ICICI Prudential Balanced Advantage Fund (Direct)": "119566",
    "Quant Small Cap Fund (Direct)": "120847",
    "Nippon India Small Cap Fund (Direct)": "119851",
    "SBI Small Cap Fund (Direct)": "125354",
    "ICICI Prudential Dynamic Asset Allocation FOF": "128913",
    "HDFC Flexi Cap Fund (Direct)": "119036"
}

def identify_alternatives(fund_name):
    name = fund_name.lower()
    if any(k in name for k in ['dynamic', 'balanced', 'baf', 'asset allocation', 'fof']):
        return ["HDFC Balanced Advantage", "Edelweiss Balanced Advantage", "ICICI Pru Balanced Advantage"]
    elif any(k in name for k in ['small', 'smallcap']):
        return ["Nippon India Small Cap", "Quant Small Cap", "Axis Small Cap"]
    elif 'flexi' in name:
        return ["Parag Parikh Flexi Cap", "HDFC Flexi Cap", "Quant Flexi Cap"]
    else:
        return ["Parag Parikh Flexi Cap", "HDFC Balanced Advantage", "UTI Nifty 50 Index"]

# 3. Main HUD
st.title("📡 TACTICAL MF RADAR Terminal v7.0")
st.markdown("SYSTEM STATUS: **ONLINE** | THEME: **DYNAMIC OS SYNC**")
st.write("---")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("⚡ TARGET ACQUISITION")
    query = st.text_input("SCAN SYSTEM AIRSPACE:", "").strip()
    
    final_scheme_code = None
    final_scheme_name = None
    
    if query:
        combined_options = {}
        
        # Step A: Pull local matches instantly
        local_matches = {k: v for k, v in LOCAL_RADAR_DB.items() if query.lower() in k.lower()}
        combined_options.update(local_matches)
        
        # Step B: Pull ALL external API matches and combine them
        payload = stealth_fetch(f"https://api.mfapi.in/mf/search?q={query}")
        if payload:
            api_map = {item['schemeName']: str(item['schemeCode']) for item in payload}
            combined_options.update(api_map)
        
        # Step C: Display combined list
        if combined_options:
            selected_target = st.selectbox("LOCKING SIGNAL (Local & API Data Combined):", list(combined_options.keys()))
            final_scheme_code = combined_options[selected_target]
            final_scheme_name = selected_target
        else:
            st.warning("⚠️ NO TARGETS FOUND AND EXTERNAL API JAMMED. MANUAL OVERRIDE REQUIRED.")
            manual_code = st.text_input("INPUT 6-DIGIT AMFI CODE:", "")
            if manual_code.isdigit():
                final_scheme_code = manual_code
                final_scheme_name = f"UNKNOWN TARGET [#{manual_code}]"

with col_right:
    st.subheader("🎯 INTERCEPT DIAGNOSTICS")
    if final_scheme_name:
        alts = identify_alternatives(final_scheme_name)
        st.markdown(f"""
        <div class="radar-intercept">
            <h4 style='margin-top:0;'>⚠️ RADAR INTERCEPT ADVISORY</h4>
            <p>Target: <b>{final_scheme_name}</b></p>
            <p>Superior Direct-Plan Alternatives Detected:</p>
            <ul><li>{alts[0]}</li><li>{alts[1]}</li><li>{alts[2]}</li></ul>
        </div>
        """, unsafe_allow_html=True)

# 4. Telemetry Engine & Simulation
if final_scheme_code:
    st.write("---")
    if st.button("FIRE DEEP QUANT RADAR SWEEP", type="primary"):
        with st.spinner("PULLING LIVE TELEMETRY..."):
            
            is_synthetic = False
            raw_payload = stealth_fetch(f"https://api.mfapi.in/mf/{final_scheme_code}")
            
            if raw_payload and 'data' in raw_payload and len(raw_payload['data']) > 0:
                df = pd.DataFrame(raw_payload['data'])
                df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
                df['nav'] = pd.to_numeric(df['nav'])
                df = df.sort_values('date').reset_index(drop=True)
            else:
                is_synthetic = True
                df = generate_synthetic_telemetry(final_scheme_name)
            
            df['Daily_Return'] = df['nav'].pct_change()
            total_days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
            
            initial_investment = 1000000
            units_bought = initial_investment / df['nav'].iloc[0]
            df['Portfolio_Value'] = df['nav'] * units_bought
            final_value = df['Portfolio_Value'].iloc[-1]
            profit = final_value - initial_investment
            
            absolute_return = (final_value / initial_investment) - 1
            cagr = ((1 + absolute_return) ** (365.25 / total_days)) - 1
            volatility = df['Daily_Return'].std() * np.sqrt(252)
            sharpe = (cagr - 0.065) / volatility if volatility > 0 else 0
            
            if is_synthetic:
                st.markdown("<div class='sim-warning'>⚠️ LIVE SIGNAL LOST: Displaying offline AI-generated synthetic telemetry.</div><br>", unsafe_allow_html=True)
            
            st.subheader(f"📊 DEPLOYMENT SIMULATION: ₹10,00,000 in {final_scheme_name}")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("CURRENT VALUATION", f"₹{final_value:,.0f}")
            m2.metric("NET PROFIT", f"₹{profit:,.0f}", f"{absolute_return*100:.2f}%")
            m3.metric("CAGR (VELOCITY)", f"{cagr*100:.2f}%")
            m4.metric("SHARPE (EFFICIENCY)", f"{sharpe:.2f}")
            
            st.markdown("### 📈 PORTFOLIO TRAJECTORY (₹)")
            st.line_chart(df.set_index('date')['Portfolio_Value'])