import streamlit as st
import pandas as pd
import numpy as np
import requests

# Page layout configuration
st.set_page_config(page_title="Live MF Quant Analyzer", layout="wide")

st.title("Automated Mutual Fund Quantitative Analyzer")
st.write("Zero CSV uploads required. This engine live-streams historical data straight from the official AMFI database pipeline.")

# 1. Real-Time Fund Search Input
search_query = st.text_input("Type your fund name here (e.g., 'Parag Parikh Flexi', 'HDFC Balanced Advantage'):", "")

if search_query:
    with st.spinner("Searching AMFI database..."):
        # Query the open-source AMFI directory
        search_url = f"https://api.mfapi.in/mf/search?q={search_query}"
        search_results = requests.get(search_url).json()
    
    if search_results:
        # Build a clean key-value mapping of Fund Name -> Fund Code
        fund_map = {item['schemeName']: item['schemeCode'] for item in search_results}
        selected_fund = st.selectbox("Select the exact matching scheme from the database:", list(fund_map.keys()))
        scheme_code = fund_map[selected_fund]
        
        # Trigger calculation engine
        if st.button("Run Quantitative Analysis"):
            with st.spinner("Streaming live historical NAV data and processing metrics..."):
                # Fetch full historical NAV timelines
                data_url = f"https://api.mfapi.in/mf/{scheme_code}"
                raw_payload = requests.get(data_url).json()
                
                if 'data' in raw_payload and len(raw_payload['data']) > 0:
                    # Convert json payload to structured pandas DataFrame
                    df = pd.DataFrame(raw_payload['data'])
                    df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
                    df['nav'] = pd.to_numeric(df['nav'])
                    df = df.sort_values('date').reset_index(drop=True)
                    
                    # 2. Performance Calculations
                    df['Daily_Return'] = df['nav'].pct_change()
                    total_days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
                    
                    if total_days > 365:
                        absolute_return = (df['nav'].iloc[-1] / df['nav'].iloc[0]) - 1
                        cagr = ((1 + absolute_return) ** (365.25 / total_days)) - 1
                        
                        # 3. Advanced Risk Adjustments (Assuming standard 6.5% Risk-Free Rate for India)
                        risk_free_rate = 0.065
                        annual_volatility = df['Daily_Return'].std() * np.sqrt(252)
                        
                        # Isolate purely negative downside movements for Sortino Calculation
                        downside_returns = df[df['Daily_Return'] < 0]['Daily_Return']
                        downside_volatility = downside_returns.std() * np.sqrt(252)
                        
                        sharpe = (cagr - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
                        sortino = (cagr - risk_free_rate) / downside_volatility if downside_volatility > 0 else 0
                        
                        # 4. Interactive UI Presentation
                        st.markdown("---")
                        st.subheader(f"Analysis Profile: {selected_fund}")
                        st.caption(f"AMFI Scheme ID: {scheme_code} | Continuous Historical Range: {df['date'].iloc[0].strftime('%d %b %Y')} to {df['date'].iloc[-1].strftime('%d %b %Y')}")
                        
                        # Metric Display Rows
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Inception-to-Date CAGR", f"{cagr*100:.2f}%")
                        m2.metric("Sharpe Ratio (Risk vs Reward)", f"{sharpe:.2f}")
                        m3.metric("Sortino Ratio (Downside Shield)", f"{sortino:.2f}")
                        
                        # Interactive Performance Charts
                        st.subheader("Historical NAV Growth Chart")
                        st.line_chart(df.set_index('date')['nav'])
                    else:
                        st.warning("The historical data timeline found for this specific scheme code is under 1 year. Risk metrics require longer cycles to calculate accurately.")
                else:
                    st.error("The data server returned an empty payload for this scheme selection.")
    else:
        st.error("No active funds matching that specific name query were found in the AMFI registry. Try adjusting keywords.")