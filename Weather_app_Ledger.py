import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pyxirr import xirr
import os

# --- 1. CONFIG & PERSISTENCE ---
st.set_page_config(page_title="Weather-Alpha Engine 2026", layout="wide")
LEDGER_FILE = "trade_ledger.csv"

if 'trade_log' not in st.session_state:
    if os.path.exists(LEDGER_FILE):
        st.session_state.trade_log = pd.read_csv(LEDGER_FILE)
    else:
        st.session_state.trade_log = pd.DataFrame(columns=["Date", "Ticker", "Type", "Qty", "Price", "Status"])

# --- 2. SIDEBAR: DYNAMIC CONTROLS ---
st.sidebar.header("⚡ Execution Mode")
mode = st.sidebar.radio("Strategy Type", ["Cash (Swing)", "Intraday (Day-Trade)"])

st.sidebar.header("🕹️ Strategy Controls")
if mode == "Intraday (Day-Trade)":
    trading_day = st.sidebar.date_input("Select Trading Day", value=datetime(2026, 5, 4))
    start_date, as_of_date = trading_day, trading_day
    lookback = st.sidebar.slider("Rolling Window (Hourly Bars)", 1, 10, 3)
else:
    start_date = st.sidebar.date_input("Backtest Start", value=datetime(2026, 4, 6))
    as_of_date = st.sidebar.date_input("Analysis 'As Of' Date", value=datetime(2026, 5, 4))
    lookback = st.sidebar.slider("Rolling Window (Days)", 3, 30, 3)

port_val = st.sidebar.number_input("Total Portfolio Value (INR)", min_value=1000, value=1000000, step=1000)
p_list = st.sidebar.text_input("Power Basket", "NTPC.NS, POWERGRID.NS").split(", ")
d_list = st.sidebar.text_input("Defensive Basket", "NESTLEIND.NS, HINDUNILVR.NS, SUNPHARMA.NS").split(", ")
mkt = st.sidebar.selectbox("Market Benchmark", ["^NSEI"])

# --- 3. DATA ENGINE ---
@st.cache_data
def get_hybrid_data(tickers, start, end, mode):
    if mode == "Intraday (Day-Trade)":
        fetch_start = start - timedelta(days=7) # Buffer for hourly lookback
        df = yf.download(tickers, start=fetch_start, end=end + timedelta(days=1), interval="1h", progress=False)['Close']
    else:
        fetch_start = start - timedelta(days=45) # Buffer for daily lookback
        df = yf.download(tickers, start=fetch_start, end=end + timedelta(days=1), progress=False)['Close']
    
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df.ffill().dropna()

all_tix = list(set(p_list + d_list + [mkt]))
raw_data = get_hybrid_data(all_tix, start_date, as_of_date, mode)
rets = raw_data.pct_change().dropna()

# --- 4. STRATEGY LOGIC ---
rets['Heat'] = rets[p_list].mean(axis=1).rolling(lookback).mean()
rets['Rain'] = rets[d_list].mean(axis=1).rolling(lookback).mean()
rets['Signal'] = np.where(rets['Heat'] > rets['Rain'], 1, 0)
rets['Base'] = np.where(rets['Signal'] == 1, rets[p_list].mean(axis=1), rets[d_list].mean(axis=1))

if mode == "Intraday (Day-Trade)":
    day_str = trading_day.strftime('%Y-%m-%d')
    strat_rets = rets[rets.index.strftime('%Y-%m-%d') == day_str]
else:
    rets['Perf_Gate'] = rets['Base'].rolling(lookback).sum()
    rets['Risk_W'] = np.where(rets['Perf_Gate'] < 0, 0.20, 0.80)
    rf_daily = 0.06 / 252
    rets['Strat'] = (rets['Base'] * rets['Risk_W'].shift(1)) + (rf_daily * (1 - rets['Risk_W'].shift(1)))
    strat_rets = rets.loc[start_date:as_of_date].dropna()

# --- 5. COMPREHENSIVE PERFORMANCE CALC ---
def calc_all_metrics(s_ret, initial_cap, mode):
    if s_ret.empty: return None
    
    col_name = 'Base' if mode == "Intraday (Day-Trade)" else 'Strat'
    cum_gross = (1 + s_ret[col_name]).cumprod()
    abs_gross = cum_gross.iloc[-1] - 1.0
    
    flips = s_ret['Signal'].diff().abs().sum() if mode == "Cash (Swing)" else 1
    friction = flips * (0.0010 if mode == "Intraday (Day-Trade)" else 0.0020)
    
    net_pre_tax = abs_gross - friction
    tax = max(0, net_pre_tax * 0.15)
    abs_net = net_pre_tax - tax
    cash_profit = initial_cap * abs_net
    
    xg, xn = 0.0, 0.0
    if mode == "Cash (Swing)":
        cf_dates = [s_ret.index[0], s_ret.index[-1]]
        try:
            xg = xirr(cf_dates, [-1.0, 1.0 + abs_gross])
            xn = xirr(cf_dates, [-1.0, 1.0 + abs_net])
        except: pass
        
    return {"xg": xg, "xn": xn, "an": abs_net, "cash": cash_profit, "cum": cum_gross}

res = calc_all_metrics(strat_rets, port_val, mode)

# --- 6. UI RENDERING ---
st.title(f"🌦️ {mode} Dashboard")
if res is None:
    st.warning("⚠️ No data for this selection. Market was likely closed.")
    st.stop()

m1, m2, m3, m4 = st.columns(4)
if mode == "Cash (Swing)":
    m1.metric("Gross XIRR", f"{res['xg']*100:.2f}%")
    m2.metric("Net XIRR", f"{res['xn']*100:.2f}%", delta=f"{- (res['xg']-res['xn'])*100:.2f}% Leakage")
    m3.metric("Net Abs Return", f"{res['an']*100:.2f}%")
    m4.metric("Cash Profit (Net)", f"₹{res['cash']:,.2f}")
else:
    m1.metric("Daily Gross", f"{(res['cum'].iloc[-1]-1)*100:.2f}%")
    m2.metric("Daily Net", f"{res['an']*100:.2f}%")
    m3.metric("Daily Cash Profit", f"₹{res['cash']:,.2f}")
    m4.metric("Intervals Trace", f"{len(strat_rets)} Bars")

fig = go.Figure()
fig.add_trace(go.Scatter(x=res['cum'].index, y=res['cum'], name="Strategy", line=dict(color='#00FFAA')))
fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=30, b=10))
st.plotly_chart(fig, use_container_width=True)

# --- 7. LEDGER ---
st.markdown("---")
st.subheader("📝 Manual Trade Ledger")
st.data_editor(st.session_state.trade_log, num_rows="dynamic", use_container_width=True)