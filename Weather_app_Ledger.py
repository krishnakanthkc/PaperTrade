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

# --- 2. SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ Strategy Controls")
start_date = st.sidebar.date_input("Backtest Start", value=datetime(2026, 1, 1))
as_of_date = st.sidebar.date_input("Analysis 'As Of' Date", value=datetime(2026, 5, 4))
lookback = st.sidebar.slider("Rolling Window (Days)", 3, 30, 3)
port_val = st.sidebar.number_input("Total Portfolio Value (INR)", min_value=1000, value=1000, step=1000)

p_list = st.sidebar.text_input("Power Basket", "NTPC.NS, POWERGRID.NS").split(", ")
d_list = st.sidebar.text_input("Defensive Basket", "NESTLEIND.NS, HINDUNILVR.NS, SUNPHARMA.NS").split(", ")
mkt = st.sidebar.selectbox("Market Benchmark", ["^NSEI"])

# --- 3. DATA ENGINE ---
@st.cache_data
def get_full_data(tickers, start, end):
    df = yf.download(tickers, start=start - timedelta(days=40), end=end + timedelta(days=1), progress=False)['Close']
    return df.ffill().dropna()

all_tix = list(set(p_list + d_list + [mkt]))
raw_data = get_full_data(all_tix, start_date, as_of_date)
rets = raw_data.pct_change().dropna()

# --- 4. STRATEGY LOGIC ---
rets['Heat'] = rets[p_list].mean(axis=1).rolling(lookback).mean()
rets['Rain'] = rets[d_list].mean(axis=1).rolling(lookback).mean()
rets['Signal'] = np.where(rets['Heat'] > rets['Rain'], 1, 0)
rets['Base'] = np.where(rets['Signal'] == 1, rets[p_list].mean(axis=1), rets[d_list].mean(axis=1))
rets['Perf_Gate'] = rets['Base'].rolling(lookback).sum()
rets['Risk_W'] = np.where(rets['Perf_Gate'] < 0, 0.20, 0.80)

rf_daily = 0.06 / 252
rets['Strat'] = (rets['Base'] * rets['Risk_W'].shift(1)) + (rf_daily * (1 - rets['Risk_W'].shift(1)))
strat_rets = rets.loc[start_date:as_of_date].dropna()

# --- 5. PERFORMANCE CALCULATIONS ---
def calc_final_metrics(s_ret, m_ret, signal_series, initial_cap):
    cum_gross = (1 + s_ret['Strat']).cumprod()
    mdd = (cum_gross / cum_gross.cummax() - 1).min()
    
    cf_dates = [s_ret.index[0], s_ret.index[-1]]
    try: xg = xirr(cf_dates, [-1.0, cum_gross.iloc[-1]])
    except: xg = 0.0
    
    abs_gross = cum_gross.iloc[-1] - 1.0
    flips = signal_series.diff().abs().sum()
    friction = flips * 0.0020
    net_pre_tax = abs_gross - friction
    tax = max(0, net_pre_tax * 0.15)
    
    abs_net = abs_gross - friction - tax
    cash_earned = initial_cap * abs_net
    try: xn = xirr(cf_dates, [-1.0, 1.0 + abs_net])
    except: xn = 0.0
    
    beta = np.cov(s_ret['Strat'], m_ret.loc[s_ret.index])[0][1] / m_ret.loc[s_ret.index].var()
    
    return xg, xn, abs_net, cash_earned, mdd, beta, cum_gross

xg, xn, an, cash, mdd, beta, cum_series = calc_final_metrics(strat_rets, rets[mkt], rets['Signal'], port_val)

# --- 6. UI: METRICS WITH TOOLTIPS ---
st.title("🌦️ Weather-Regime Alpha Engine")

m1, m2, m3, m4, m5 = st.columns(5)

# Helper function for pretty printing large numbers in the UI
def format_large(n):
    if n >= 1e6: return f"{n/1e6:.2f}M"
    if n >= 1e3: return f"{n/1e3:.2f}K"
    return f"{n:.2f}"

m1.metric("Gross XIRR", f"{xg*100:.2f}%", help=f"Full Value: {xg*100}%")
m2.metric("Net XIRR", f"{xn*100:.2f}%", delta=f"{- (xg-xn)*100:.2f}%", help=f"Full Value: {xn*100}%")
m3.metric("Net Abs Return", f"{format_large(an*100)}%", help=f"Exact Percentage: {an*100}%")
m4.metric("Cash Profit (Net)", f"₹{format_large(cash)}", help=f"Exact Profit: ₹{cash:,.2f}")
m5.metric("Max Drawdown", f"{mdd*100:.2f}%")

# Equity Curve
fig = go.Figure()
fig.add_trace(go.Scatter(x=cum_series.index, y=cum_series, name="Strategy", line=dict(color='#00FFAA')))
fig.add_trace(go.Scatter(x=cum_series.index, y=(1+rets[mkt].loc[strat_rets.index]).cumprod(), name="Market", line=dict(color='gray', dash='dot')))
fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# --- 7. ADVICE & LEDGER ---
st.markdown("---")
cur_regime = "RAIN PIVOT" if rets['Rain'].iloc[-1] > rets['Heat'].iloc[-1] else "HEATWAVE"
st.subheader(f"📅 Trade Advice: {cur_regime}")

c1, c2 = st.columns(2)
with c1:
    st.success("✅ BUY/HOLD")
    to_buy = d_list if cur_regime == "RAIN PIVOT" else p_list
    alloc = (port_val * rets['Risk_W'].iloc[-1]) / len(to_buy)
    buy_table = [{"Ticker": t, "Price": round(raw_data[t].iloc[-1], 2), "Qty": int(alloc/raw_data[t].iloc[-1])} for t in to_buy]
    st.table(pd.DataFrame(buy_table))

with c2:
    st.error("🛑 SELL/EXIT")
    exit_list = p_list if cur_regime == "RAIN PIVOT" else d_list
    active_in_ledger = st.session_state.trade_log[st.session_state.trade_log['Status'] == 'Open']['Ticker'].tolist()
    final_exits = [t for t in exit_list if t in active_in_ledger]
    if final_exits:
        st.table(pd.DataFrame([{"Ticker": t, "Price": round(raw_data[t].iloc[-1], 2), "Action": "EXIT"} for t in final_exits]))
    else:
        st.write("No open positions for exit.")

st.markdown("---")
st.subheader("📝 Manual Trade Ledger")
edited_df = st.data_editor(st.session_state.trade_log, num_rows="dynamic", use_container_width=True)
if st.button("💾 Save Ledger"):
    st.session_state.trade_log = edited_df
    edited_df.to_csv(LEDGER_FILE, index=False)
    st.success("Ledger Saved!")