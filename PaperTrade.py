import yfinance as yf
import pandas as pd

# 1. Download Data (Flattening the MultiIndex)
ticker = "NIFTYBEES.NS"
data = yf.download(ticker, start="2021-01-01", end="2026-03-05")

# This line fixes the 'KeyError' by simplifying the table structure
data.columns = data.columns.get_level_values(0)

# 2. Calculate the 20-Day Moving Average
data['MA20'] = data['Close'].rolling(window=20).mean()

# 3. Strategy Logic (Low Risk Mean Reversion)
data['Signal'] = 0
# Buy when price is 2% below the average
data.loc[data['Close'] < (data['MA20'] * 0.98), 'Signal'] = 1 
# Sell when price recovers to the average
data.loc[data['Close'] > data['MA20'], 'Signal'] = 0

# 4. Calculate Returns
data['Returns'] = data['Close'].pct_change()
data['Strategy_Returns'] = data['Signal'].shift(1) * data['Returns']

# 5. Calculate Performance Metrics
cumulative_profit = (1 + data['Strategy_Returns']).cumprod().iloc[-1]
total_return_pct = (cumulative_profit - 1) * 100
avg_monthly = ((cumulative_profit**(1/36)) - 1) * 100

# Calculate Max Drawdown (The "Risk" part)
cum_rets = (1 + data['Strategy_Returns']).cumprod()
peak = cum_rets.expanding(min_periods=1).max()
drawdown = (cum_rets/peak) - 1
max_drawdown = drawdown.min() * 100

print(f"--- Backtest Results ---")
print(f"Total Return (3 Years): {total_return_pct:.2f}%")
print(f"Average Monthly Return: {avg_monthly:.2f}%")
print(f"Max Drawdown (Worst Dip): {max_drawdown:.2f}%")