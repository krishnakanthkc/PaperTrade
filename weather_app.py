import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pyxirr import xirr 

# Page Setup
st.set_page_config(page_title="Weather-Alpha Engine 2026", layout="wide")
st.title("🌦️ Weather-Regime Alpha Engine")
st.markdown("---")

# 1. SIDEBAR: Controls
st.sidebar.header("🕹️ Strategy Controls")
start_date = st.sidebar.date_input("Start Date", value=datetime(2026, 1, 1))
end_date = st.sidebar.date_input("End Date", value=datetime(2026, 5, 4))
lookback = st.sidebar.slider("Rolling Window (Days)", min_value=3, max_value=30, value=3)

# Added Portfolio Value Input for Order Calculation
portfolio_value = st.sidebar.number_input("Total Portfolio Value (INR)", value=1000000, step=100000)

p_list = st.sidebar.text_input("Power Basket", "NTPC.NS, POWERGRID.NS").split(", ")
d_list = st.sidebar.text_input("Defensive Basket", "NESTLEIND.NS, HINDUNILVR.NS, SUNPHARMA.NS").split(", ")
mkt = st.sidebar.selectbox("Market Benchmark", ["^NSEI"])

# 2. DATA ENGINE
@st.cache_data
def get_clean_data(tickers, start, end):
    df = yf.download(tickers, start=start - timedelta(days=40), end=end, progress=False)['Close']
    return df.ffill().dropna()

raw_data = get_clean_data(p_list + d_list + [mkt], start_date, end_date)
rets = raw_data.pct_change().dropna()

# 3. QUANT LOGIC
rets['Heat'] = rets[p_list].mean(axis=1).rolling(lookback).mean()
rets['Rain'] = rets[d_list].mean(axis=1).rolling(lookback).mean()
rets['Signal'] = np.where(rets['Heat'] > rets['Rain'], 1, 0)

rets['Base'] = np.where(rets['Signal'] == 1, rets[p_list].mean(axis=1), rets[d_list].mean(axis=1))
rets['Perf_Gate'] = rets['Base'].rolling(lookback).sum()
rets['Risk_Weight'] = np.where(rets['Perf_Gate'] < 0, 0.20, 0.80)

# Final Returns calculation (includes Risk-Free interest for the cash portion)
rf_daily = 0.06 / 252
rets['Strat'] = (rets['Base'] * rets['Risk_Weight'].shift(1)) + (rf_daily * (1 - rets['Risk_Weight'].shift(1)))
rets = rets.loc[start_date:] # Trim to user's requested date range

# 4. METRICS 
def calc_metrics(strat_ret, mkt_ret):
    cum = (1 + strat_ret).cumprod()
    mdd = (cum / cum.cummax() - 1).min()
    cf_dates = [strat_ret.index[0], strat_ret.index[-1]]
    cf_amounts = [-1.0, cum.iloc[-1]]
    try:
        x_val = xirr(cf_dates, cf_amounts)
    except:
        x_val = 0.0
    mkt_var = mkt_ret.var()
    beta = np.cov(strat_ret, mkt_ret)[0][1] / mkt_var if mkt_var != 0 else 0
    alpha = x_val - (0.06 + beta * (mkt_ret.mean()*252 - 0.06))
    return x_val, mdd, beta, alpha, cum

x_val, mdd, beta, alpha, cum_series = calc_metrics(rets['Strat'], rets[mkt])

# 5. UI DISPLAY - METRICS
m1, m2, m3, m4 = st.columns(4)
m1.metric(f"XIRR ({lookback}D Window)", f"{x_val*100:.2f}%")
m2.metric("Max Drawdown", f"{mdd*100:.2f}%", delta_color="inverse")
m3.metric("Strategy Beta", f"{beta:.2f}")
m4.metric("Jensen's Alpha", f"{alpha*100:.2f}%")

st.plotly_chart(go.Figure(data=[
    go.Scatter(x=cum_series.index, y=cum_series, name="Strategy", line=dict(color='#00FFAA')),
    go.Scatter(x=cum_series.index, y=(1+rets[mkt]).cumprod(), name="Market", line=dict(color='gray', dash='dot'))
]).update_layout(template="plotly_dark", height=400), use_container_width=True)

# 6. ENHANCED ORDER DETAILS (AS OF MAY 4, 2026)
st.subheader("📋 Exact Order Quantities (Manual Trade Sheet)")

# Get current prices for all tickers
last_prices = raw_data.iloc[-1]
last_regime = "RAIN PIVOT" if rets['Rain'].iloc[-1] > rets['Heat'].iloc[-1] else "HEATWAVE"
risk_w = rets['Risk_Weight'].iloc[-1]

# Dynamic Weights based on image_5707e4.png logic
target_power = 0.31 if last_regime == "RAIN PIVOT" else 0.80
target_def = 0.49 if last_regime == "RAIN PIVOT" else 0.20

# Allocation Values
val_power = portfolio_value * (target_power * risk_w)
val_def = portfolio_value * (target_def * risk_w)

def generate_order_table(tickers, total_basket_value):
    order_data = []
    # Distribute value equally among stocks in the basket
    per_stock_value = total_basket_value / len(tickers)
    for ticker in tickers:
        price = last_prices[ticker]
        qty = int(per_stock_value / price)
        order_data.append({
            "Ticker": ticker,
            "LTP (May 4)": f"₹{price:.2f}",
            "Action": "BUY/REBALANCE",
            "Quantity": qty,
            "Estimated Value": f"₹{qty * price:,.0f}"
        })
    return pd.DataFrame(order_data)

# Displaying Tables
tab1, tab2 = st.tabs(["Power Basket Orders", "Defensive Basket Orders"])

with tab1:
    st.write(f"**Total Capital to Deploy:** ₹{val_power:,.0f}")
    st.table(generate_order_table(p_list, val_power))

with tab2:
    st.write(f"**Total Capital to Deploy:** ₹{val_def:,.0f}")
    st.table(generate_order_table(d_list, val_def))

st.warning(f"**Cash Reserve:** Send **₹{portfolio_value * (1-risk_w):,.0f}** to Liquid Funds/Cash to maintain the -4.93% drawdown protection seen in your backtest.")