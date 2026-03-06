import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ====================== CONFIGURATION ======================
SYMBOL = "NIFTYBEES.NS"          # Change to any stock/crypto (e.g. "^NSEI" for Nifty50)
START_DATE = "2025-01-01"
END_DATE = datetime.today().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 100000  # ₹1 lakh example
MONTHLY_TARGET = 0.01     # 1% — we will check if we hit it
MAX_DRAWDOWN_TARGET = 0.05

# Simple conservative strategy: 200-day SMA + position sizing
# (This is just an example — real strategies are much more complex)
# ========================================================

# Download data
print(f"Downloading {SYMBOL} data...")
downloaded_data = yf.download(SYMBOL, start=START_DATE, end=END_DATE, progress=False)
close = downloaded_data['Close'].copy()
sma200 = close.rolling(window=200).mean()
data = pd.DataFrame()
data['Close'] = close
data['SMA200'] = sma200

# Signals
data['Signal'] = 0
data.loc[data['SMA200'].notna() & (data['Close'] > data['SMA200']), 'Signal'] = 1   # Long only when above SMA

# Backtest
data['Position'] = data['Signal'].shift(1)  # lag to avoid look-ahead
data['Returns'] = data['Close'].pct_change()
data['Strategy_Returns'] = data['Position'] * data['Returns']

# Equity curve
data['Equity'] = INITIAL_CAPITAL * (1 + data['Strategy_Returns']).cumprod()
data['Peak'] = data['Equity'].cummax()
data['Drawdown'] = (data['Equity'] - data['Peak']) / data['Peak']

# Monthly performance
data['Month'] = data.index.to_period('M')
monthly = data.groupby('Month').agg({
    'Equity': 'last',
    'Drawdown': 'min'
}).reset_index()
monthly['Monthly_Return'] = monthly['Equity'].pct_change()

# Results
final_equity = data['Equity'].iloc[-1]
total_return = (final_equity / INITIAL_CAPITAL) - 1
cagr = ((final_equity / INITIAL_CAPITAL) ** (1 / (len(data)/252))) - 1
max_dd = data['Drawdown'].min()
win_months = (monthly['Monthly_Return'] > 0).mean() * 100

print("\n" + "="*60)
print("BACKTEST RESULTS (EDUCATIONAL ONLY — NOT REAL TRADING)")
print("="*60)
print(f"Period               : {START_DATE} to {END_DATE}")
print(f"Final Capital        : ₹{final_equity:,.2f}")
print(f"Total Return         : {total_return*100:+.2f}%")
print(f"CAGR                 : {cagr*100:+.2f}%")
print(f"Max Drawdown         : {max_dd*100:.2f}%  ← You wanted <5%")
print(f"Months above target  : {(monthly['Monthly_Return'] >= MONTHLY_TARGET).sum()}/{len(monthly)}")
print(f"Win rate             : {win_months:.1f}%")
print(f"Average monthly return: {monthly['Monthly_Return'].mean()*100:.2f}%")
print("="*60)
print("⚠️ This is HISTORICAL DATA only. Real markets will be worse.")
print("   Past performance is NOT indicative of future results.")
print("="*60)

# Plot (optional — requires matplotlib)
try:
    import matplotlib.pyplot as plt
    data[['Equity', 'Peak']].plot(figsize=(12,6), title=f"{SYMBOL} Strategy Equity Curve")
    plt.ylabel("Portfolio Value (₹)")
    plt.grid()
    plt.show()
except:
    pass