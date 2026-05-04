import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# UI Configuration
st.set_page_config(page_title="Weather-Alpha Dashboard", layout="wide")
st.title("🌦️ Weather-Regime Alpha Engine")

# 1. Sidebar - Dynamic Inputs
st.sidebar.header("Strategy Configuration")
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2026-05-04"))

power_list = st.sidebar.multiselect("Power Basket", ['NTPC.NS', 'TATAPOWER.NS', 'POWERGRID.NS'], default=['NTPC.NS', 'POWERGRID.NS'])
def_list = st.sidebar.multiselect("Defensive Basket", ['NESTLEIND.NS', 'HINDUNILVR.NS', 'BRITANNIA.NS', 'SUNPHARMA.NS', 'CIPLA.NS'], default=['HINDUNILVR.NS', 'SUNPHARMA.NS'])
benchmark = st.sidebar.selectbox("Benchmark Index", ['^NSEI', '^BSESN'], index=0)

# 2. Data Fetching
@st.cache_data
def load_data(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, progress=False)['Close']
    return df.ffill()

data = load_data(power_list + def_list + [benchmark], start_date, end_date)
returns = data.pct_change().dropna()

# 3. Dynamic Strategy Logic
returns['Heat_Score'] = returns[power_list].mean(axis=1).rolling(10).mean()
returns['Rain_Score'] = returns[def_list].mean(axis=1).rolling(10).mean()
returns['Signal'] = np.where(returns['Heat_Score'] > returns['Rain_Score'], 1, 0)

# Performance Logic
returns['Base_Strat'] = np.where(returns['Signal'] == 1, returns[power_list].mean(axis=1), returns[def_list].mean(axis=1))
returns['Recent_Perf'] = returns['Base_Strat'].rolling(10).sum()
returns['Risk_Weight'] = np.where(returns['Recent_Perf'] < 0, 0.20, 0.80)
returns['Final_Ret'] = (returns['Base_Strat'] * returns['Risk_Weight'].shift(1)) + (0.06/252 * (1 - returns['Risk_Weight'].shift(1)))

# 4. Metrics Calculation
def get_metrics(strat_ret, mkt_ret):
    cum_ret = (1 + strat_ret).cumprod()
    days = (strat_ret.index[-1] - strat_ret.index[0]).days
    xirr = (cum_ret.iloc[-1]**(365/days)) - 1
    mdd = (cum_ret / cum_ret.cummax() - 1).min()
    
    # Beta & Alpha
    covariance = np.cov(strat_ret, mkt_ret)[0][1]
    variance = np.var(mkt_ret)
    beta = covariance / variance
    alpha = xirr - (0.06 + beta * (mkt_ret.mean()*252 - 0.06)) # Jensen's Alpha
    
    return xirr, mdd, beta, alpha, cum_ret

xirr, mdd, beta, alpha, cum_series = get_metrics(returns['Final_Ret'], returns[benchmark])

# 5. Dashboard UI Layout
col1, col2, col3, col4 = st.columns(4)
col1.metric("XIRR (Annualized)", f"{xirr*100:.2f}%")
col2.metric("Max Drawdown", f"{mdd*100:.2f}%", delta_color="inverse")
col3.metric("Strategy Beta", f"{beta:.2f}")
col4.metric("Jensen's Alpha", f"{alpha*100:.2f}%")

# Equity Curve Plot
fig = go.Figure()
fig.add_trace(go.Scatter(x=cum_series.index, y=cum_series, name="Strategy Equity", line=dict(color='orange', width=2)))
fig.add_trace(go.Scatter(x=cum_series.index, y=(1+returns[benchmark]).cumprod(), name="Market Benchmark", line=dict(color='gray', dash='dash')))
st.plotly_chart(fig, use_container_width=True)

# Status Output
last_signal = "RAIN PIVOT" if returns['Rain_Score'].iloc[-1] > returns['Heat_Score'].iloc[-1] else "HEATWAVE"
st.success(f"**Current Status:** {last_signal} | **Risk Weight:** {returns['Risk_Weight'].iloc[-1]*100}%")