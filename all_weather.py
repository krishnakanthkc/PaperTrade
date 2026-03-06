import yfinance as yf
import pandas as pd
import numpy as np

# 1. Download Data for our All-Weather Basket
tickers = ["NIFTYBEES.NS", "GOLDBEES.NS"]
start_date = "2018-01-01"
end_date = "2026-03-05"
data = yf.download(tickers, start=start_date, end=end_date)['Close']
data = data.dropna() # Clear missing early data

# Extract and print years
start_year = int(start_date.split("-")[0])
end_year = int(end_date.split("-")[0])

# 2. Resample data to Monthly (End of Month) to avoid overtrading
monthly_data = data.resample('ME').last()

# 3. Calculate 3-Month Momentum (Return over 3 months)
momentum = monthly_data.pct_change(periods=3)

# 4. Strategy Logic: Rank the assets
# Shift momentum by 1 month so we don't cheat by looking at the future
signal = momentum.shift(1)

# Pick the Winner (Asset with highest positive return)
positions = pd.DataFrame(index=signal.index, columns=tickers).fillna(0)

for date, row in signal.iterrows():
    # Skip if all values are NaN
    if row.isna().all():
        continue
    
    # If both are negative, hold CASH (0 allocation)
    if row.max() <= 0:
        continue
    
    # If there is a positive winner, put 100% (1.0) into it
    winner = row.idxmax()
    positions.loc[date, winner] = 1.0

# 5. Calculate Returns
# Calculate the next month's return for each asset
asset_returns = monthly_data.pct_change()

# Our portfolio return is the return of the asset we were holding that month
strategy_returns = (positions.shift(1) * asset_returns).sum(axis=1)

# 6. Show Results
cumulative_profit = (1 + strategy_returns).cumprod().iloc[-1]
total_return_pct = (cumulative_profit - 1) * 100
avg_annual = ((cumulative_profit**(1/7)) - 1) * 100 # 7 years of data
avg_monthly = avg_annual / 12

cum_rets = (1 + strategy_returns).cumprod()
peak = cum_rets.expanding(min_periods=1).max()
drawdown = (cum_rets/peak) - 1
max_drawdown = drawdown.min() * 100

print(f"--- All-Weather Rotation Results {start_year} to {end_year} ---")
print(f"Total Return: {total_return_pct:.2f}%")
print(f"Average Monthly Return: {avg_monthly:.2f}%")
print(f"Max Drawdown (Worst Dip): {max_drawdown:.2f}%")