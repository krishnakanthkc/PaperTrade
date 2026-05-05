import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pyxirr import xirr
import os

# --- 1. CONFIG & LEDGER ---
st.set_page_config(page_title="Weather-Alpha Engine 2026", layout="wide")
LEDGER_FILE = "trade_ledger.csv"

if 'trade_log' not in st.session_state:
    if os.path.exists(LEDGER_FILE):
        st.session_state.trade_log = pd.read_csv(LEDGER_FILE)
    else:
        st.session_state.trade_log = pd.DataFrame(columns=["Date", "Ticker", "Type", "Qty", "Price"])

# --- 2. SIDEBAR CONTROLS ---
st.sidebar.header("🔌 Connectivity")
use_synthetic = st.sidebar.toggle("Use Synthetic Data (API Bypass)", value=True)

st.sidebar.header("🕹️ Strategy Controls")
port_val = st.sidebar.number_input("Total Portfolio Value (INR)", min_value=1000, value=1000000)
p_list = [x.strip() for x in st.sidebar.text_input("Power Basket", "NTPC.NS, POWERGRID.NS").split(",")]
d_list = [x.strip() for x in st.sidebar.text_input("Defensive Basket", "NESTLEIND.NS, HINDUNILVR.NS, SUNPHARMA.NS").split(",")]
mkt_bench = st.sidebar.selectbox("Market Benchmark", ["^NSEI"])

start_dt = st.sidebar.date_input("Backtest Start", value=datetime(2026, 4, 6))
as_of_dt = st.sidebar.date_input("Analysis 'As Of' Date", value=datetime(2026, 5, 5))
lookback = st.sidebar.slider("Rolling Window", 3, 30, 3)
# NEW: Black Swan Threshold
crash_limit = st.sidebar.slider("Black Swan Threshold (%)", -10.0, -1.0, -4.0, 0.5) / 100.0

# --- 3. DATA ENGINE ---
def get_synthetic_data(tickers, start, end):
    dates = pd.date_range(start=start - timedelta(days=60), end=end, freq='D')
    df = pd.DataFrame(index=dates)
    for t in tickers:
        df[t] = 100 * (1 + np.random.randn(len(dates)) * 0.015).cumprod()
    return df

@st.cache_data(ttl=600)
def fetch_data(tickers, start, end):
    try:
        data = yf.download(tickers, start=start-timedelta(days=60), end=end+timedelta(days=1), progress=False)
        if not data.empty:
            df = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data[['Close']]
            if not isinstance(data.columns, pd.MultiIndex): df.columns = tickers
            return df.ffill().dropna()
    except: return pd.DataFrame()
    return pd.DataFrame()

all_tix = list(set(p_list + d_list + [mkt_bench]))
raw_data = get_synthetic_data(all_tix, start_dt, as_of_dt) if use_synthetic else fetch_data(all_tix, start_dt, as_of_dt)

if raw_data.empty:
    st.error("🛑 Data Unavailable. Toggle 'Synthetic Mode' in sidebar.")
    st.stop()

# --- 4. CALCULATIONS (BLACK SWAN LOGIC ADDED) ---
rets = raw_data.pct_change().dropna()
rets['Heat'] = rets[p_list].mean(axis=1).rolling(lookback).mean()
rets['Rain'] = rets[d_list].mean(axis=1).rolling(lookback).mean()
rets['Signal'] = np.where(rets['Heat'] > rets['Rain'], 1, 0)
rets['Base'] = np.where(rets['Signal'] == 1, rets[p_list].mean(axis=1), rets[d_list].mean(axis=1))

# Risk Gating & Black Swan Override
rets['Perf_Gate'] = rets['Base'].rolling(lookback).sum()
rets['Mkt_Roll'] = rets[mkt_bench].rolling(lookback).sum() # Benchmark momentum

# Logic: If market drops past threshold -> 0% Risk. If basket is negative -> 20% Risk. Else -> 80%.
rets['Risk_W'] = np.where(rets['Mkt_Roll'] <= crash_limit, 0.0, 
                 np.where(rets['Perf_Gate'] < 0, 0.20, 0.80))

rets['Strat'] = (rets['Base'] * rets['Risk_W'].shift(1)) + ((0.06/252) * (1 - rets['Risk_W'].shift(1)))
strat_rets = rets.loc[start_dt:as_of_dt].dropna()

# --- 5. UI: KEY METRICS ---
st.title("🌦️ Weather-Alpha Engine")
if use_synthetic: st.warning("🛠️ DATA BYPASS ACTIVE: Showing Synthetic Results")

if not strat_rets.empty:
    cum_ret = (1 + strat_rets['Strat']).cumprod()
    abs_profit = port_val * (cum_ret.iloc[-1] - 1)
    
    dates = [strat_rets.index[0], strat_rets.index[-1]]
    cash_flows = [-port_val, port_val * cum_ret.iloc[-1]]
    try:
        net_xirr = xirr(pd.DataFrame({"date": dates, "amount": cash_flows})) * 100
    except: net_xirr = 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Net XIRR", f"{net_xirr:.2f}%")
    m2.metric("Total Profit", f"₹{abs_profit:,.2f}")
    m3.metric("Current Regime", "🔥 POWER" if rets['Signal'].iloc[-1] == 1 else "🛡️ DEFENSIVE")
    
    # Color-code Risk Metric
    curr_risk = rets['Risk_W'].iloc[-1]
    risk_color = "🔴" if curr_risk == 0 else ("🟡" if curr_risk == 0.2 else "🟢")
    m4.metric("Capital Deployed", f"{risk_color} {curr_risk*100:.0f}%")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cum_ret.index, y=cum_ret, name="Strategy", line=dict(color='#00FFAA', width=3)))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

# --- 6. ACTIONABLE EXECUTION ---
st.markdown("---")
curr_sig = rets['Signal'].iloc[-1]
active_basket = p_list if curr_sig == 1 else d_list

c1, c2 = st.columns([1.2, 1])
with c1:
    deployed_capital = port_val * curr_risk
    st.subheader(f"🎯 Actionable Targets (Deploying: ₹{deployed_capital:,.2f})")
    
    if curr_risk == 0.0:
        st.error("🚨 **BLACK SWAN GATE ACTIVE** 🚨\n\nThe broader market has breached your crash threshold. Move 100% of strategy capital to Liquid Funds. Do not execute equity buys.")
    else:
        # Calculate exactly how many shares to buy
        capital_per_asset = deployed_capital / len(active_basket)
        t_cols = st.columns(len(active_basket))
        
        for i, t in enumerate(active_basket):
            price = raw_data[t].iloc[-1]
            target_qty = int(capital_per_asset // price) # Floor division for whole shares
            alloc_val = target_qty * price
            
            with t_cols[i]:
                st.info(f"**{t}**")
                st.metric("Buy Qty", f"{target_qty} shares")
                st.caption(f"Price: ₹{price:,.2f}")
                st.caption(f"Alloc: ₹{alloc_val:,.2f}")

with c2:
    st.subheader("📝 Trade Logger")
    with st.form("trade_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        t_tix = f1.selectbox("Ticker", all_tix)
        t_qty = f2.number_input("Qty", min_value=1)
        t_prc = f3.number_input("Price", value=float(raw_data[all_tix[0]].iloc[-1]) if not raw_data.empty else 0.0)
        if st.form_submit_button("Log Trade"):
            new_trade = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Ticker": t_tix, "Type": "BUY", "Qty": t_qty, "Price": t_prc}])
            st.session_state.trade_log = pd.concat([st.session_state.trade_log, new_trade], ignore_index=True)
            st.session_state.trade_log.to_csv(LEDGER_FILE, index=False)

if not st.session_state.trade_log.empty:
    st.dataframe(st.session_state.trade_log.tail(5), use_container_width=True)