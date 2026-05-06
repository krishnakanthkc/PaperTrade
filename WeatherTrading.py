import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# --- 1. CONFIG & CSS INJECTIONS ---
st.set_page_config(page_title="Weather-Alpha 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    [data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 800; color: #E0E0E0; }
    [data-testid="stMetricLabel"] { font-size: 1rem; color: #888888; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: 600; }
    [data-testid="collapsedControl"] { display: none; }
    @media (max-width: 640px) {
        [data-testid="stMetricValue"] { font-size: 1.5rem; }
        .main .block-container { padding-top: 2rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CLOUD DATABASE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1g6MPLJ71mex86k4EJW0XMfEt5oKXLMnh5x0C6toiSdE/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

if 'trade_log' not in st.session_state:
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Ledger", usecols=list(range(5)))
        # Pre-process dates to objects for the editor
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
            st.session_state.trade_log = df.dropna(how="all")
        else:
            st.session_state.trade_log = pd.DataFrame(columns=["Date", "Ticker", "Type", "Qty", "Price"])
    except:
        st.session_state.trade_log = pd.DataFrame(columns=["Date", "Ticker", "Type", "Qty", "Price"])

def save_ledger():
    try:
        # Convert objects back to strings for GSheets stability
        save_df = st.session_state.trade_log.copy()
        save_df['Date'] = save_df['Date'].astype(str)
        conn.update(spreadsheet=SHEET_URL, worksheet="Ledger", data=save_df)
        st.toast("✅ Cloud Ledger Updated!")
    except: st.error("Save failed. Verify GSheets access.")

def parse_bulk_kite(raw_text):
    try:
        df = pd.read_csv(io.StringIO(raw_text.strip()))
        return pd.DataFrame({
            "Date": datetime.now().date(),
            "Ticker": df["Instrument"].astype(str) + ".NS",
            "Type": "BUY", "Qty": df["Qty."], "Price": df["Avg."]
        })
    except: return None

# --- 3. GLOBAL ASSET CONFIG ---
p_basket = ["NTPC.NS", "POWERGRID.NS"]
d_basket = ["NESTLEIND.NS", "HINDUNILVR.NS", "SUNPHARMA.NS"]
mkt_bench = "^NSEI"
all_tix = list(set(p_basket + d_basket + [mkt_bench]))

@st.cache_data(ttl=600)
def fetch_data(tickers, start):
    try: return yf.download(tickers, start=start-timedelta(days=100), end=datetime.now()+timedelta(days=1), progress=False)
    except: return None

raw_data_master = fetch_data(all_tix, datetime(2016, 5, 5))

def run_strategy(df_prices, lookback_val, crash_val):
    rets = df_prices.pct_change().dropna()
    rets['Heat'] = rets[p_basket].mean(axis=1).rolling(lookback_val).mean()
    rets['Rain'] = rets[d_basket].mean(axis=1).rolling(lookback_val).mean()
    rets['Signal'] = np.where(rets['Heat'] > rets['Rain'], 1, 0)
    rets['Base'] = np.where(rets['Signal'] == 1, rets[p_basket].mean(axis=1), rets[d_basket].mean(axis=1))
    rets['Mkt_Roll'] = rets[mkt_bench].rolling(lookback_val).sum()
    rets['Risk_W'] = np.where(rets['Mkt_Roll'] <= crash_val, 0.0, np.where(rets['Base'].rolling(lookback_val).sum() < 0, 0.20, 0.80))
    rets['Strat'] = (rets['Base'] * rets['Risk_W'].shift(1)) + ((0.06/252) * (1 - rets['Risk_W'].shift(1)))
    return rets

# --- 4. APP LAYOUT ---
st.title("🌦️ Weather-Alpha Engine")
tab_live, tab_backtest, tab_tech, tab_ledger = st.tabs(["🏠 Live Operations", "🧪 Sandbox", "🔍 Technicals", "📓 Ledger"])

# --- TAB 1: LIVE OPERATIONS ---
with tab_live:
    with st.container(border=True):
        st.markdown("### 🏦 Capital Settings")
        port_val = st.number_input("Total Account Value (INR)", min_value=1000, value=10000, step=1000)
        
    if raw_data_master is not None:
        live_rets = run_strategy(raw_data_master['Close'].ffill(), 3, -0.04)
        curr_risk = float(live_rets['Risk_W'].iloc[-1])
        
        # Portfolio Math
        ledger = st.session_state.trade_log
        if not ledger.empty:
            current_prices = raw_data_master['Close'].ffill().iloc[-1]
            ledger_with_val = ledger.copy()
            ledger_with_val['Current_Val'] = ledger_with_val.apply(lambda x: x['Qty'] * current_prices[x['Ticker']] if x['Ticker'] in current_prices else 0, axis=1)
            current_pos_val = ledger_with_val['Current_Val'].sum()
            actual_pnl = current_pos_val - (ledger_with_val['Qty'] * ledger_with_val['Price']).sum()
        else:
            current_pos_val, actual_pnl = 0.0, 0.0

        target_val = port_val * curr_risk

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Regime", "☀️ POWER" if live_rets['Signal'].iloc[-1] == 1 else "🛡️ DEFENSIVE")
        m2.metric("Exposure", f"₹{target_val:,.0f}", f"{curr_risk*100:.0f}%")
        m3.metric("Deployed", f"₹{current_pos_val:,.0f}", f"Gap ₹{target_val-current_pos_val:,.0f}")
        m4.metric("Net P&L", f"₹{actual_pnl:,.0f}", f"{(actual_pnl/port_val)*100:.2f}%" if port_val else "0%")

        cum_ret_live = (1 + live_rets['Strat']).cumprod()
        fig_live = go.Figure(go.Scatter(x=cum_ret_live.index, y=cum_ret_live, fill='tozeroy', fillcolor='rgba(0, 255, 170, 0.1)', line=dict(color='#00FFAA', width=2)))
        fig_live.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=20,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_live, use_container_width=True)

        st.markdown("### 🎯 Targets")
        active_basket = p_basket if live_rets['Signal'].iloc[-1] == 1 else d_basket
        holdings = ledger.groupby("Ticker")["Qty"].sum().to_dict() if not ledger.empty else {}
        t_cols = st.columns(len(active_basket))
        for i, t in enumerate(active_basket):
            p = raw_data_master['Close'][t].iloc[-1]
            target_qty = int((target_val / len(active_basket)) // p)
            with t_cols[i]:
                with st.container(border=True):
                    st.write(f"**{t}**")
                    if holdings.get(t, 0) >= target_qty and target_qty > 0: st.success("Filled")
                    elif target_qty > 0: st.warning(f"Buy {target_qty - holdings.get(t, 0)}")
                    else: st.error("No Allocation")

# --- TAB 2: SANDBOX ---
with tab_backtest:
    st.markdown("### 🔬 Strategy Backtest")
    with st.container(border=True):
        bc1, bc2, bc3 = st.columns(3)
        bt_start = bc1.date_input("Start", value=datetime.now() - timedelta(days=365))
        bt_lookback = bc2.number_input("Window", min_value=3, value=5)
        bt_crash = bc3.slider("Crash Threshold %", -15.0, -1.0, -4.0) / 100.0

    if raw_data_master is not None:
        bt_data = raw_data_master['Close'].ffill().loc[pd.to_datetime(bt_start):]
        bt_rets = run_strategy(bt_data, bt_lookback, bt_crash)
        cum_ret_bt = (1 + bt_rets['Strat']).cumprod()
        fig_bt = go.Figure(go.Scatter(x=cum_ret_bt.index, y=cum_ret_bt, fill='tozeroy', fillcolor='rgba(255, 179, 0, 0.1)', line=dict(color='#FFB300')))
        fig_bt.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=20,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bt, use_container_width=True)

# --- TAB 3: TECHNICALS ---
with tab_tech:
    inspect_stock = st.selectbox("Asset Scanner", all_tix)
    if raw_data_master is not None:
        try:
            df_t = raw_data_master.xs(inspect_stock, axis=1, level=1).copy() if isinstance(raw_data_master.columns, pd.MultiIndex) else raw_data_master.copy()
            df_t['TR'] = pd.concat([df_t['High']-df_t['Low'], abs(df_t['High']-df_t['Close'].shift(1)), abs(df_t['Low']-df_t['Close'].shift(1))], axis=1).max(axis=1)
            df_t['ATR'] = df_t['TR'].rolling(14).mean()
            df_t['Mid'] = df_t['Close'].rolling(14).mean()
            df_p = df_t.tail(120)
            fig_tech = go.Figure(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close']))
            fig_tech.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_tech, use_container_width=True)
        except: st.error("Incomplete OHLC data for this asset.")

# --- TAB 4: LEDGER ---
with tab_ledger:
    st.markdown("### 📓 Trade History")
    with st.expander("📥 Kite Bulk Sync"):
        kite_input = st.text_area("Paste CSV:", height=80)
        if st.button("Sync"):
            new_data = parse_bulk_kite(kite_input)
            if new_data is not None:
                st.session_state.trade_log = pd.concat([st.session_state.trade_log, new_data]).drop_duplicates(subset=["Date", "Ticker"], keep='last')
                save_ledger(); st.rerun()

    # Safe conversion for editor compatibility
    st.session_state.trade_log['Date'] = pd.to_datetime(st.session_state.trade_log['Date'], errors='coerce').dt.date
    
    edited_df = st.data_editor(
        st.session_state.trade_log, 
        num_rows="dynamic", use_container_width=True,
        column_config={
            "Date": st.column_config.DateColumn("Date"),
            "Ticker": st.column_config.SelectboxColumn("Asset", options=all_tix),
            "Type": st.column_config.SelectboxColumn("Type", options=["BUY", "SELL"])
        }
    )
    if st.button("💾 Save to GSheets", type="primary"):
        st.session_state.trade_log = edited_df
        save_ledger()