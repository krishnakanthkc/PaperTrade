import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# --- 1. CONFIG & CLOUD LEDGER ---
st.set_page_config(page_title="Weather-Alpha Engine 2026", layout="wide")

# The public URL you provided
SHEET_URL = "https://docs.google.com/spreadsheets/d/1g6MPLJ71mex86k4EJW0XMfEt5oKXLMnh5x0C6toiSdE/edit#gid=0"

# Establish connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Initialize Session State from Cloud Database
if 'trade_log' not in st.session_state:
    try:
        # Use the public URL to read. 
        # Note: If "Ledger" is the first sheet, worksheet="Ledger" works.
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Ledger", usecols=list(range(5)))
        df = df.dropna(how="all") 
        
        if not df.empty:
            st.session_state.trade_log = df
        else:
            st.session_state.trade_log = pd.DataFrame(columns=["Date", "Ticker", "Type", "Qty", "Price"])
    except Exception as e:
        st.warning(f"Could not connect to Sheet. Starting fresh. Error: {e}")
        st.session_state.trade_log = pd.DataFrame(columns=["Date", "Ticker", "Type", "Qty", "Price"])

def save_ledger():
    try:
        # NOTE: This will only work if you have a valid Service Account in secrets.toml
        conn.update(spreadsheet=SHEET_URL, worksheet="Ledger", data=st.session_state.trade_log)
        st.success("Cloud Ledger Updated!")
    except Exception as e:
        st.error(f"Save failed. Public links are 'Read-Only'. To save, you need the Service Account JSON. Error: {e}")

def parse_bulk_kite_data(raw_text):
    try:
        df = pd.read_csv(io.StringIO(raw_text.strip()))
        upload_df = pd.DataFrame({
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Ticker": df["Instrument"].astype(str) + ".NS",
            "Type": "BUY",
            "Qty": df["Qty."],
            "Price": df["Avg."]
        })
        return upload_df
    except Exception as e:
        st.error(f"Format Error: {e}")
        return None

# --- 2. SIDEBAR ---
st.sidebar.header("🔌 Connectivity")
use_synthetic = st.sidebar.toggle("Use Synthetic Data (API Bypass)", value=True)

st.sidebar.header("🌌 Asset Universe")
potential_universe = [
    "NTPC.NS", "POWERGRID.NS", "NESTLEIND.NS", "HINDUNILVR.NS", 
    "SUNPHARMA.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", 
    "NIPPON_INDIA_SMALL_CAP.NS", "HDFCBANK.NS", "ICICIBANK.NS", "^NSEI"
]

selected_p = st.sidebar.multiselect("Power Basket", potential_universe, default=["NTPC.NS", "POWERGRID.NS"])
selected_d = st.sidebar.multiselect("Defensive Basket", potential_universe, default=["NESTLEIND.NS", "HINDUNILVR.NS", "SUNPHARMA.NS"])

st.sidebar.header("🕹️ Strategy Controls")
port_val = st.sidebar.number_input("Portfolio Value (INR)", min_value=1000, value=1000000)
mkt_bench = st.sidebar.selectbox("Market Benchmark", ["^NSEI"])
start_dt = st.sidebar.date_input("Backtest Start", value=datetime(2026, 4, 6))
as_of_dt = st.sidebar.date_input("Analysis 'As Of' Date", value=datetime(2026, 5, 5))
lookback = st.sidebar.slider("Rolling Window", 3, 30, 3)
crash_limit = st.sidebar.slider("Black Swan Threshold (%)", -10.0, -1.0, -4.0, 0.5) / 100.0

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_data(tickers, start, end):
    try:
        data = yf.download(tickers, start=start-timedelta(days=100), end=end+timedelta(days=1), progress=False)
        return data if not data.empty else None
    except: return None

all_tix = list(set(selected_p + selected_d + [mkt_bench]))
raw_data_full = fetch_data(all_tix, start_dt, as_of_dt)

# --- 4. CALCULATIONS ---
curr_risk = 0.0 
rets = pd.DataFrame()
strat_rets = pd.DataFrame()

if raw_data_full is not None and not raw_data_full.empty:
    prices = raw_data_full['Close'].ffill()
    rets = prices.pct_change().dropna()
    
    if not rets.empty:
        rets['Heat'] = rets[selected_p].mean(axis=1).rolling(lookback).mean()
        rets['Rain'] = rets[selected_d].mean(axis=1).rolling(lookback).mean()
        rets['Signal'] = np.where(rets['Heat'] > rets['Rain'], 1, 0)
        rets['Base'] = np.where(rets['Signal'] == 1, rets[selected_p].mean(axis=1), rets[selected_d].mean(axis=1))
        rets['Mkt_Roll'] = rets[mkt_bench].rolling(lookback).sum()
        rets['Risk_W'] = np.where(rets['Mkt_Roll'] <= crash_limit, 0.0, np.where(rets['Base'].rolling(lookback).sum() < 0, 0.20, 0.80))
        
        curr_risk = float(rets['Risk_W'].iloc[-1])
        rets['Strat'] = (rets['Base'] * rets['Risk_W'].shift(1)) + ((0.06/252) * (1 - rets['Risk_W'].shift(1)))
        strat_rets = rets.loc[start_dt:as_of_dt]

# --- 5. UI: TOP METRICS & GROWTH CHART ---
st.title("🌦️ Weather-Alpha Engine")
if not strat_rets.empty:
    cum_ret = (1 + strat_rets['Strat']).cumprod()
    abs_profit = port_val * (cum_ret.iloc[-1] - 1)
    
    m1, m2 = st.columns(2)
    m3, m4 = st.columns(2)
    
    m1.metric("Estimated XIRR", f"{((cum_ret.iloc[-1]**(365/max(1, (as_of_dt-start_dt).days))) - 1) * 100:.2f}%")
    m2.metric("Total Profit", f"₹{abs_profit:,.2f}")
    m3.metric("Regime", "🔥 POWER" if rets['Signal'].iloc[-1] == 1 else "🛡️ DEFENSIVE")
    m4.metric("Risk Weight", f"{curr_risk*100:.0f}%")

    fig_growth = go.Figure()
    fig_growth.add_trace(go.Scatter(x=cum_ret.index, y=cum_ret, name="Strategy Path", line=dict(color='#00FFAA', width=3)))
    fig_growth.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=30, b=10), title="Strategy Growth Path")
    st.plotly_chart(fig_growth, use_container_width=True)

# --- 6. PORTFOLIO ACTION & LEDGER ---
st.markdown("---")
c1, c2 = st.columns([1.2, 1])

with c1:
    deployed_cap = port_val * curr_risk
    st.subheader(f"🎯 Actionable Targets (Total ₹{deployed_cap:,.2f})")
    
    if curr_risk == 0:
        st.error("🚨 BLACK SWAN GATE ACTIVE: Stay in Cash.")
    elif not rets.empty:
        active_basket = selected_p if rets['Signal'].iloc[-1] == 1 else selected_d
        cap_per = deployed_cap / len(active_basket)
        
        holding_summary = st.session_state.trade_log.groupby("Ticker")["Qty"].sum().to_dict()

        t_cols = st.columns(len(active_basket))
        for i, t in enumerate(active_basket):
            p = prices[t].iloc[-1]
            target_qty = int(cap_per // p)
            actual_qty = holding_summary.get(t, 0)
            
            with t_cols[i]:
                if actual_qty >= target_qty and target_qty > 0:
                    st.success(f"**{t}**")
                    st.metric("✅ Owned", f"{actual_qty}")
                elif target_qty > 0:
                    st.warning(f"**{t}**")
                    st.metric("⚠️ Buy", f"{target_qty - actual_qty}")
                st.caption(f"LTP: ₹{p:,.2f}")

with c2:
    st.subheader("📝 Trade Ledger")
    # Bulk Sync
    with st.expander("📥 Bulk Sync from Kite"):
        kite_input = st.text_area("Paste CSV columns here:", height=100)
        if st.button("Process & Sync", use_container_width=True):
            new_data = parse_bulk_kite_data(kite_input)
            if new_data is not None:
                st.session_state.trade_log = pd.concat([st.session_state.trade_log, new_data]).drop_duplicates(subset=["Date", "Ticker"], keep='last')
                save_ledger()
                st.rerun()

    # Manual Log
    with st.expander("➕ Manual Log"):
        with st.form("add_t", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            ticker = f1.selectbox("Ticker", all_tix)
            qty = f2.number_input("Qty", min_value=1)
            price = f3.number_input("Price", value=float(prices[ticker].iloc[-1]) if not rets.empty else 0.0)
            if st.form_submit_button("Log", use_container_width=True):
                new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Ticker": ticker, "Type": "BUY", "Qty": qty, "Price": price}])
                st.session_state.trade_log = pd.concat([st.session_state.trade_log, new_row], ignore_index=True)
                save_ledger()
                st.rerun()
    
    if not st.session_state.trade_log.empty:
        edited_df = st.data_editor(st.session_state.trade_log, num_rows="dynamic", use_container_width=True, key="ledger_editor")
        if st.button("💾 Save Table Changes", use_container_width=True):
            st.session_state.trade_log = edited_df
            save_ledger()

# --- 7. TECHNICAL CHART ---
st.markdown("---")
st.subheader("📊 Technical Deep Dive")
inspect_stock = st.selectbox("Inspect Asset", all_tix)

if raw_data_full is not None and not raw_data_full.empty:
    df_t = raw_data_full['Close'][inspect_stock].to_frame(name='Close')
    df_t['High'] = raw_data_full['High'][inspect_stock]
    df_t['Low'] = raw_data_full['Low'][inspect_stock]
    df_t['Open'] = raw_data_full['Open'][inspect_stock]
    
    df_t['TR'] = pd.concat([df_t['High']-df_t['Low'], abs(df_t['High']-df_t['Close'].shift(1)), abs(df_t['Low']-df_t['Close'].shift(1))], axis=1).max(axis=1)
    df_t['ATR'] = df_t['TR'].rolling(5).mean()
    df_t['Mid'] = df_t['Close'].rolling(5).mean()
    df_t['Upper'] = df_t['Mid'] + (df_t['ATR'] * 3)
    df_t['Lower'] = df_t['Mid'] - (df_t['ATR'] * 3)
    df_p = df_t.loc[start_dt:as_of_dt]

    fig_tech = go.Figure()
    fig_tech.add_trace(go.Scatter(x=df_p.index, y=df_p['Upper'], line=dict(color='rgba(0,0,0,0)'), showlegend=False))
    fig_tech.add_trace(go.Scatter(x=df_p.index, y=df_p['Lower'], line=dict(color='rgba(0,0,0,0)'), fill='tonexty', fillcolor='rgba(100,100,100,0.2)', name="ATR Bands"))
    fig_tech.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price"))
    fig_tech.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_tech, use_container_width=True)