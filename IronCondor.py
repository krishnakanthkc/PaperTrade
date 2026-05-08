import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# ====================== Normal CDF ======================
def norm_cdf(x):
    t = 1 / (1 + 0.2316419 * np.abs(x))
    d = 0.3989422804 * np.exp(-x * x / 2)
    p = d * t * (0.31938153 + t * (-0.356563782 + t * (1.781477937 +
                t * (-1.821255978 + t * 1.330274429))))
    return np.where(x >= 0, 1 - p, p)

def black_scholes_call(S, K, T, r, sigma):
    if T <= 0: return max(S - K, 0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm_cdf(d1) - K * np.exp(-r * T) * norm_cdf(d2)

def black_scholes_put(S, K, T, r, sigma):
    if T <= 0: return max(K - S, 0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return K * np.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

# ====================== Streamlit App ======================
st.set_page_config(page_title="Nifty Options Backtester", layout="wide")
st.title("📈 Nifty Short Strangle / Iron Condor Backtester with Real Data")

st.sidebar.header("Strategy Parameters")

if st.sidebar.button("🔄 Load Recommended Balanced Settings"):
    st.session_state.otm = 6
    st.session_state.profit_target = 60
    st.session_state.sl = 2.0
    st.session_state.position = 22
    st.session_state.iv_threshold = 24
    st.rerun()

start_year = st.sidebar.slider("Start Year", 2015, 2026, 2018)
capital = st.sidebar.number_input("Starting Capital (₹)", value=500000, min_value=100000, step=50000)

strategy_type = st.sidebar.selectbox("Strategy", ["Short Strangle", "Iron Condor"])
otm_percent = st.sidebar.slider("OTM Distance (%)", 3, 12, 6, key="otm")
profit_target = st.sidebar.slider("Profit Target (% of premium)", 40, 80, 60, key="profit_target")
stop_loss_mult = st.sidebar.slider("Stop Loss (x premium)", 1.5, 3.0, 2.0, key="sl")
position_size_pct = st.sidebar.slider("Position Size (% of Capital)", 10, 40, 22, key="position")
use_iv_filter = st.sidebar.checkbox("Enable IV Filter", value=True)
iv_threshold = st.sidebar.slider("IV Threshold (%)", 15, 40, 24, key="iv_threshold")

st.sidebar.markdown("### Costs & Taxes")
brokerage_per_trade = st.sidebar.number_input("Brokerage per trade (₹)", value=40.0)
stt_pct = st.sidebar.number_input("STT (%)", value=0.125)
other_charges_pct = st.sidebar.number_input("Other charges (%)", value=0.05)

# ====================== Data Source ======================
st.subheader("📡 Real Data Source")

try:
    import yfinance as yf
    yf_available = True
except:
    yf_available = False

if yf_available:
    if st.button("🔄 Download Nifty 50 + India VIX Data", type="primary"):
        with st.spinner("Downloading real data..."):
            try:
                nifty = yf.download("^NSEI", start=f"{start_year}-01-01", progress=False)
                vix = yf.download("^INDIAVIX", start=f"{start_year}-01-01", progress=False)
                
                # Fixed: Align dates properly
                df = pd.DataFrame()
                df['Close'] = nifty['Close']
                df['Volatility'] = vix['Close'] / 100.0
                df = df.dropna().reset_index()   # This line was causing the scalar error
                
                st.session_state.df = df
                st.success(f"✅ Downloaded {len(df)} trading days")
                st.dataframe(df.tail(10), use_container_width=True)
                
            except Exception as e:
                st.error(f"Download error: {e}")
else:
    st.warning("yfinance not available.")

# CSV Upload Fallback
uploaded_file = st.file_uploader("Or Upload CSV (Date, Close, Volatility)", type=["csv"])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df['Date'] = pd.to_datetime(df['Date'])
    st.session_state.df = df
    st.success(f"Loaded {len(df)} rows from CSV")

if 'df' not in st.session_state:
    st.warning("Please download data or upload CSV first.")
    st.stop()

df = st.session_state.df

# Weekly Data
df['Week'] = df['Date'].dt.to_period('W').apply(lambda x: x.start_time)
weekly = df.groupby('Week').agg({'Close': 'first', 'Volatility': 'mean'}).reset_index()
weekly = weekly.rename(columns={'Week': 'Date'})

# ====================== Backtest ======================
if st.button("🚀 Run Full Backtest with Costs & Taxes", type="primary"):
    with st.spinner("Running backtest..."):
        equity = float(capital)
        equity_curve = [equity]
        trade_log = []
        r = 0.065

        for i in range(len(weekly) - 1):
            row = weekly.iloc[i]
            S = float(row['Close'])
            sigma = float(row['Volatility'])
            T = 7 / 365.0

            call_strike = round(S * (1 + otm_percent/100) / 50) * 50
            put_strike = round(S * (1 - otm_percent/100) / 50) * 50

            credit = black_scholes_call(S, call_strike, T, r, sigma) + black_scholes_put(S, put_strike, T, r, sigma)

            if strategy_type == "Iron Condor":
                wing = otm_percent + 8
                cw = round(S * (1 + wing/100) / 50) * 50
                pw = round(S * (1 - wing/100) / 50) * 50
                credit -= black_scholes_call(S, cw, T, r, sigma) + black_scholes_put(S, pw, T, r, sigma)

            if credit <= 0.5 or (use_iv_filter and sigma < iv_threshold/100):
                equity_curve.append(equity)
                continue

            position_value = equity * (position_size_pct / 100.0)
            lots = max(1, int(position_value / (credit * 50)))

            max_profit = lots * credit * 50 * (profit_target / 100)
            max_loss = lots * credit * 50 * stop_loss_mult

            next_S = float(weekly.iloc[i+1]['Close'])
            payoff = max(next_S - call_strike, 0) + max(put_strike - next_S, 0)
            if strategy_type == "Iron Condor":
                payoff = max(0, payoff - max(next_S - cw, 0) - max(pw - next_S, 0))

            trade_pnl = lots * (credit - payoff) * 50
            if trade_pnl > max_profit: trade_pnl = max_profit
            elif trade_pnl < -max_loss: trade_pnl = -max_loss

            turnover = lots * credit * 50 * 2
            total_costs = (turnover * stt_pct / 100) + (brokerage_per_trade * 2) + (turnover * other_charges_pct / 100)

            net_pnl = trade_pnl - total_costs
            equity += net_pnl
            equity_curve.append(equity)

            trade_log.append({
                'Date': row['Date'].date(),
                'Spot': round(S, 2),
                'IV(%)': round(sigma*100, 1),
                'Credit': round(credit, 2),
                'Net PnL': round(net_pnl, 0),
                'Win': net_pnl > 0
            })

        # Results
        trade_df = pd.DataFrame(trade_log)
        days = (weekly['Date'].iloc[-1] - weekly['Date'].iloc[0]).days
        years = days / 365.25 if days > 0 else 1
        xirr = ((equity / capital) ** (1 / years) - 1) * 100

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Final Equity", f"₹{equity:,.0f}")
        col2.metric("Net XIRR", f"{xirr:.2f}%")
        col3.metric("Win Rate", f"{trade_df['Win'].mean()*100:.1f}%" if not trade_df.empty else "0%")
        col4.metric("Total Trades", len(trade_df))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=weekly['Date'], y=equity_curve, mode='lines'))
        fig.update_layout(title="Equity Curve (Net of Costs)", height=650)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Trade Log")
        st.dataframe(trade_df, use_container_width=True)

st.caption("**Click 'Load Recommended Balanced Settings'** for better results (aiming for 15-25% XIRR)")