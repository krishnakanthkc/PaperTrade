import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. CONFIG & CSS ---
st.set_page_config(page_title="Weather-Alpha 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0E1117; }
    [data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 800; color: #E0E0E0; }
    [data-testid="stMetricLabel"] { font-size: 1rem; color: #888888; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; padding-bottom: 10px; }
    [data-testid="collapsedControl"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA LAYER ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1g6MPLJ71mex86k4EJW0XMfEt5oKXLMnh5x0C6toiSdE/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

if 'trade_log' not in st.session_state:
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Ledger", usecols=list(range(5)))
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
            st.session_state.trade_log = df.dropna(how="all")
        else:
            st.session_state.trade_log = pd.DataFrame(columns=["Date", "Ticker", "Type", "Qty", "Price"])
    except:
        st.session_state.trade_log = pd.DataFrame(columns=["Date", "Ticker", "Type", "Qty", "Price"])

def save_ledger():
    try:
        save_df = st.session_state.trade_log.copy()
        save_df['Date'] = save_df['Date'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))
        conn.update(spreadsheet=SHEET_URL, worksheet="Ledger", data=save_df)
        st.toast("✅ Cloud Ledger Updated!")
    except Exception as e: 
        st.error(f"Save failed: {e}")

def parse_holdings_xlsx(file):
    try:
        df_raw = pd.read_excel(file, sheet_name='Equity', header=None, engine='openpyxl')
        header_row = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ["Symbol", "Instrument", "Quantity", "Avg"]):
                header_row = i
                break
        df = pd.read_excel(file, sheet_name='Equity', skiprows=header_row, engine='openpyxl')
        t_col = next((c for c in df.columns if c in ['Symbol', 'Instrument']), None)
        q_col = next((c for c in df.columns if 'Quantity' in c or 'Qty' in c), None)
        p_col = next((c for c in df.columns if 'Average' in c or 'Avg' in c), None)
        return pd.DataFrame({
            "Date": datetime.now().date(),
            "Ticker": df[t_col].astype(str) + ".NS",
            "Type": "BUY",
            "Qty": df[q_col].astype(float),
            "Price": df[p_col].astype(float)
        }).dropna(subset=['Ticker'])
    except Exception as e:
        st.error(f"Excel Sync Error: {e}")
        return None

# Global Configuration
p_basket = ["NTPC.NS", "POWERGRID.NS"]
d_basket = ["NESTLEIND.NS", "HINDUNILVR.NS", "SUNPHARMA.NS"]
mkt_bench = "^NSEI"
all_tix = list(set(p_basket + d_basket + [mkt_bench]))

@st.cache_data(ttl=600)
def fetch_data(tickers):
    return yf.download(tickers, start="2018-01-01", end=datetime.now()+timedelta(days=1), progress=False)

raw_data_master = fetch_data(all_tix)

def run_strategy(df_prices, lookback_val, crash_val):
    # Adjusting crash_val logic to handle slider percentage input
    crash_decimal = crash_val / 100 if abs(crash_val) > 1 else crash_val
    
    rets = df_prices.pct_change().dropna()
    rets['Heat'] = rets[p_basket].mean(axis=1).rolling(lookback_val).mean()
    rets['Rain'] = rets[d_basket].mean(axis=1).rolling(lookback_val).mean()
    rets['Signal'] = np.where(rets['Heat'] > rets['Rain'], 1, 0)
    rets['Base'] = np.where(rets['Signal'] == 1, rets[p_basket].mean(axis=1), rets[d_basket].mean(axis=1))
    rets['Mkt_Roll'] = rets[mkt_bench].rolling(lookback_val).sum()
    rets['Risk_W'] = np.where(rets['Mkt_Roll'] <= crash_decimal, 0.0, np.where(rets['Base'].rolling(lookback_val).sum() < 0, 0.20, 0.80))
    rets['Strat'] = (rets['Base'] * rets['Risk_W'].shift(1)) + ((0.06/252) * (1 - rets['Risk_W'].shift(1)))
    return rets

# --- 3. APP TABS ---
tab_live, tab_sandbox, tab_tech, tab_ledger = st.tabs(["🏠 Live Operations", "🧪 Sandbox", "🔍 Technicals", "📓 Ledger"])

# --- TAB 1: LIVE OPERATIONS ---
with tab_live:
    with st.container(border=True):
        st.markdown("### 🏦 Capital Settings")
        port_val = st.number_input("Total Account Value (INR)", min_value=1000, value=10000, step=1000)
        
    if raw_data_master is not None:
        live_rets = run_strategy(raw_data_master['Close'].ffill(), 3, -0.04)
        curr_risk = float(live_rets['Risk_W'].iloc[-1])
        ledger = st.session_state.trade_log
        
        if not ledger.empty:
            current_prices = raw_data_master['Close'].ffill().iloc[-1]
            valid_ledger = ledger[ledger['Ticker'].isin(current_prices.index)].copy()
            valid_ledger['Current_Val'] = valid_ledger.apply(lambda x: x['Qty'] * current_prices[x['Ticker']], axis=1)
            valid_ledger['Invested_Val'] = valid_ledger['Qty'] * valid_ledger['Price']
            
            current_pos_val = valid_ledger['Current_Val'].sum()
            actual_pnl = current_pos_val - valid_ledger['Invested_Val'].sum()
            chart_start = pd.to_datetime(ledger['Date'].min()) - timedelta(days=2) 
        else:
            current_pos_val, actual_pnl, chart_start = 0.0, 0.0, datetime.now() - timedelta(days=30)

        target_val = port_val * curr_risk
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Regime", "☀️ POWER" if live_rets['Signal'].iloc[-1] == 1 else "🛡️ DEFENSIVE")
        m2.metric("Exposure", f"₹{target_val:,.0f}", f"{curr_risk*100:.0f}%")
        m3.metric("Deployed", f"₹{current_pos_val:,.0f}", f"Gap ₹{target_val-current_pos_val:,.0f}")
        m4.metric("Net P&L", f"₹{actual_pnl:,.2f}", f"{(actual_pnl/port_val)*100:.2f}%" if port_val else "0%")

        chart_slice = live_rets.loc[pd.to_datetime(chart_start):]
        if not chart_slice.empty:
            cum_ret_live = (1 + chart_slice['Strat']).cumprod()
            fig_live = go.Figure(go.Scatter(x=cum_ret_live.index, y=cum_ret_live, fill='tozeroy', fillcolor='rgba(0, 255, 170, 0.1)', line=dict(color='#00FFAA', width=2)))
            fig_live.update_layout(template="plotly_dark", height=300, title="Operational Alpha Path", margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_live, use_container_width=True)

        st.markdown("### 🎯 Targets (Action Center)")
        active_basket = p_basket if live_rets['Signal'].iloc[-1] == 1 else d_basket
        holdings_dict = ledger.groupby("Ticker")["Qty"].sum().to_dict() if not ledger.empty else {}
        t_cols = st.columns(len(active_basket))
        for i, t in enumerate(active_basket):
            p = raw_data_master['Close'][t].iloc[-1]
            target_qty = int((target_val / len(active_basket)) // p)
            current_qty = holdings_dict.get(t, 0)
            with t_cols[i]:
                with st.container(border=True):
                    st.write(f"**{t}**")
                    st.write(f"Price: ₹{p:,.2f}")
                    if current_qty >= target_qty and target_qty > 0: st.success(f"Filled ({current_qty})")
                    elif target_qty > 0: st.warning(f"Action: BUY {target_qty - current_qty}")
                    else: st.info("Exit / No Allocation")

# --- TAB 2: SANDBOX (Fixed to image_7837c6.png) ---
with tab_sandbox:
    st.markdown("### 🧬 Strategy Backtest")
    
    # 3-column layout as seen in the screenshot
    col_start, col_window, col_crash = st.columns([2, 2, 4])
    
    with col_start:
        backtest_start = st.date_input("Start", value=datetime(2026, 5, 4))
        
    with col_window:
        # Renamed to "Window" per screenshot
        s_look = st.number_input("Window", min_value=1, max_value=30, value=3)
        
    with col_crash:
        # Matching "Crash Threshold %" label and -4.00 default
        s_crash = st.slider("Crash Threshold %", -10.0, -1.0, -4.0, step=0.1)
    
    if raw_data_master is not None:
        sim_rets = run_strategy(raw_data_master['Close'].ffill(), s_look, s_crash)
        
        # Filter data based on backtest_start
        sim_rets_filtered = sim_rets[sim_rets.index >= pd.to_datetime(backtest_start)]
        
        if not sim_rets_filtered.empty:
            sim_cum = (1 + sim_rets_filtered['Strat']).cumprod()
            
            fig_sim = go.Figure()
            fig_sim.add_trace(go.Scatter(
                x=sim_cum.index, 
                y=sim_cum, 
                line=dict(color='#00FFAA', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 170, 0.05)'
            ))
            
            fig_sim.update_layout(
                template="plotly_dark", 
                height=450, 
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(gridcolor='#333', zerolinecolor='#444'),
                xaxis=dict(gridcolor='#333')
            )
            st.plotly_chart(fig_sim, use_container_width=True)

# --- TAB 3: TECHNICALS ---
with tab_tech:
    st.markdown("### 🔍 Momentum Analysis")
    m_prices = raw_data_master['Close'].ffill()
    st.write("**Recent Performance**")
    st.dataframe(m_prices.tail(10).style.format("₹{:.2f}"), use_container_width=True)
    
    ca, cb = st.columns(2)
    with ca:
        st.write("Power Basket Momentum")
        st.line_chart(m_prices[p_basket].pct_change().rolling(3).mean())
    with cb:
        st.write("Defensive Basket Momentum")
        st.line_chart(m_prices[d_basket].pct_change().rolling(3).mean())

# --- TAB 4: LEDGER ---
with tab_ledger:
    st.markdown("### 📓 Smart Ledger")
    with st.expander("📊 Sync from Excel"):
        uploaded_file = st.file_uploader("Upload Zerodha holdings", type="xlsx")
        if uploaded_file and st.button("Sync Now"):
            new_data = parse_holdings_xlsx(uploaded_file)
            if new_data is not None:
                st.session_state.trade_log = pd.concat([st.session_state.trade_log, new_data]).drop_duplicates(subset=["Ticker"], keep='last')
                save_ledger(); st.rerun()

    st.session_state.trade_log['Date'] = pd.to_datetime(st.session_state.trade_log['Date'], errors='coerce').dt.date
    edited_df = st.data_editor(st.session_state.trade_log, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Finalize & Save", type="primary"):
        st.session_state.trade_log = edited_df
        save_ledger(); st.rerun()