import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page Setup
st.set_page_config(page_title="Weather-Alpha Engine 2026", layout="wide")
st.title("🌦️ Weather-Regime Alpha Engine")
st.markdown("---")

# 1. SIDEBAR: Controls
st.sidebar.header("🕹️ Strategy Controls")
start_date = st.sidebar.date_input("Start Date", value=datetime.now() - timedelta(days=730))
end_date = st.sidebar.date_input("End Date", value=datetime(2026, 5, 4))

p_list = st.sidebar.text_input("Power Basket (split by comma)", "NTPC.NS, POWERGRID.NS").split(", ")
d_list = st.sidebar.text_input("Defensive Basket (split by comma)", "NESTLEIND.NS, HINDUNILVR.NS, SUNPHARMA.NS").split(", ")
mkt = st.sidebar.selectbox("Market Benchmark", ["^NSEI", "^BSESN"])

# 2. DATA ENGINE
@st.cache_data
def get_clean_data(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, progress=False)['Close']
    return df.ffill().dropna()

raw_data = get_clean_data(p_list + d_list + [mkt], start_date, end_date)
rets = raw_data.pct_change().dropna()

# 3. QUANT LOGIC (Regime Switching)
rets['Heat'] = rets[p_list].mean(axis=1).rolling(10).mean()
rets['Rain'] = rets[d_list].mean(axis=1).rolling(10).mean()
rets['Signal'] = np.where(rets['Heat'] > rets['Rain'], 1, 0)

rets['Base'] = np.where(rets['Signal'] == 1, rets[p_list].mean(axis=1), rets[d_list].mean(axis=1))
rets['Perf_Gate'] = rets['Base'].rolling(10).sum()
rets['Risk_Weight'] = np.where(rets['Perf_Gate'] < 0, 0.20, 0.80)

# Final Returns Calculation
rf_daily = 0.06 / 252
rets['Strat'] = (rets['Base'] * rets['Risk_Weight'].shift(1)) + (rf_daily * (1 - rets['Risk_Weight'].shift(1)))
rets = rets.dropna()

# 4. METRICS (The Fix for NaN)
def calc_metrics(strat_ret, mkt_ret):
    cum = (1 + strat_ret).cumprod()
    days = (strat_ret.index[-1] - strat_ret.index[0]).days
    xirr = (cum.iloc[-1]**(365/days)) - 1 if days > 0 else 0
    mdd = (cum / cum.cummax() - 1).min()
    
    # Secure Beta Calculation
    mkt_var = mkt_ret.var()
    if mkt_var == 0 or np.isnan(mkt_var):
        beta = 0.0
    else:
        beta = np.cov(strat_ret, mkt_ret)[0][1] / mkt_var
    
    # Jensen's Alpha
    mkt_annual = mkt_ret.mean() * 252
    alpha = xirr - (0.06 + beta * (mkt_annual - 0.06))
    
    return xirr, mdd, beta, alpha, cum

xirr, mdd, beta, alpha, cum_series = calc_metrics(rets['Strat'], rets[mkt])

# 5. UI DISPLAY
m1, m2, m3, m4 = st.columns(4)
m1.metric("XIRR (Annualized)", f"{xirr*100:.2f}%")
m2.metric("Max Drawdown", f"{mdd*100:.2f}%", delta_color="inverse")
m3.metric("Strategy Beta", f"{beta:.2f}")
m4.metric("Jensen's Alpha", f"{alpha*100:.2f}%")

# Charting
fig = go.Figure()
fig.add_trace(go.Scatter(x=cum_series.index, y=cum_series, name="Strategy", line=dict(color='#00FFAA')))
fig.add_trace(go.Scatter(x=cum_series.index, y=(1+rets[mkt]).cumprod(), name="Market", line=dict(color='gray', dash='dot')))
st.plotly_chart(fig, use_container_width=True)

# 6. LIVE STATUS AGENT
last_regime = "RAIN PIVOT" if rets['Rain'].iloc[-1] > rets['Heat'].iloc[-1] else "HEATWAVE"
top_asset = rets[d_list if last_regime == "RAIN PIVOT" else p_list].iloc[-1].idxmax()
surge = rets[top_asset].iloc[-1] * 100

st.subheader(f"🛡️ Active Agent Status: {last_regime}")
st.info(f"**Deployment Strategy:** Overweight **{top_asset}** based on {surge:.2f}% intraday surge. | **Risk Weight:** {rets['Risk_Weight'].iloc[-1]*100}%")