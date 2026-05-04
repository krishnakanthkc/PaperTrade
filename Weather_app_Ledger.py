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
port_val = st.sidebar.number_input("Total Portfolio Value (INR)", 1000000)

p_list = st.sidebar.text_input("Power Basket", "NTPC.NS, POWERGRID.NS").split(", ")
d_list = st.sidebar.text_input("Defensive Basket", "NESTLEIND.NS, HINDUNILVR.NS, SUNPHARMA.NS").split(", ")
mkt = st.sidebar.selectbox("Market Benchmark", ["^NSEI"])

# --- 3. DATA ENGINE ---
@st.cache_data
def get_full_data(tickers, start, end):
    # Buffer for rolling window calculation
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

# --- 5. TOP METRICS BAR ---
def calc_stats(s_ret, m_ret):
    cum = (1 + s_ret['Strat']).cumprod()
    mdd = (cum / cum.cummax() - 1).min()
    # XIRR calculation
    cf_dates = [s_ret.index[0], s_ret.index[-1]]
    cf_amounts = [-1.0, cum.iloc[-1]]
    try: x_val = xirr(cf_dates, cf_amounts)
    except: x_val = 0.0
    # Beta
    m_var = m_ret.loc[s_ret.index].var()
    beta = np.cov(s_ret['Strat'], m_ret.loc[s_ret.index])[0][1] / m_var if m_var != 0 else 0
    alpha = x_val - (0.06 + beta * (m_ret.mean()*252 - 0.06))
    return x_val, mdd, beta, alpha, cum

x_val, mdd, beta, alpha, cum_series = calc_stats(strat_rets, rets[mkt])

st.title("🌦️ Weather-Regime Alpha Engine")
m1, m2, m3, m4 = st.columns(4)
m1.metric(f"XIRR ({lookback}D)", f"{x_val*100:.2f}%")
m2.metric("Max Drawdown", f"{mdd*100:.2f}%")
m3.metric("Strategy Beta", f"{beta:.2f}")
m4.metric("Jensen's Alpha", f"{alpha*100:.2f}%")

# --- 6. EQUITY CURVE ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=cum_series.index, y=cum_series, name="Strategy", line=dict(color='#00FFAA')))
fig.add_trace(go.Scatter(x=cum_series.index, y=(1+rets[mkt].loc[strat_rets.index]).cumprod(), name="Market", line=dict(color='gray', dash='dot')))
fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# --- 7. ACTIONABLE ORDERS ---
st.markdown("---")
cur_regime = "RAIN PIVOT" if rets['Rain'].iloc[-1] > rets['Heat'].iloc[-1] else "HEATWAVE"
st.subheader(f"📅 Active Advice: {cur_regime} (as of {as_of_date.strftime('%Y-%m-%d')})")

to_buy = d_list if cur_regime == "RAIN PIVOT" else p_list
risk_w = rets['Risk_W'].iloc[-1]

c1, c2 = st.columns(2)
with c1:
    st.success("✅ BUY/HOLD BASKET")
    buy_df = []
    alloc = (port_val * risk_w) / len(to_buy)
    for t in to_buy:
        p = raw_data[t].iloc[-1]
        buy_df.append({"Ticker": t, "Price": round(p, 2), "Qty": int(alloc/p)})
    st.table(pd.DataFrame(buy_df))

with c2:
    st.error("🛑 SELL/EXIT PREVIOUS REGIME")
    exit_list = p_list if cur_regime == "RAIN PIVOT" else d_list
    # Filter only what's currently marked as 'Open' in our ledger
    active_in_ledger = st.session_state.trade_log[st.session_state.trade_log['Status'] == 'Open']['Ticker'].tolist()
    final_exits = [t for t in exit_list if t in active_in_ledger]
    if final_exits:
        st.table(pd.DataFrame([{"Ticker": t, "LTP": round(raw_data[t].iloc[-1], 2)} for t in final_exits]))
    else:
        st.write("No active positions from old regime found in ledger.")

# --- 8. THE LEDGER ---
st.markdown("---")
st.subheader("📝 Manual Trade Ledger")
edited_df = st.data_editor(st.session_state.trade_log, num_rows="dynamic", use_container_width=True)

if st.button("💾 Save & Sync Ledger"):
    st.session_state.trade_log = edited_df
    edited_df.to_csv(LEDGER_FILE, index=False)
    st.success("Ledger synced to disk!")