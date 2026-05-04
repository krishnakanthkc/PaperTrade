import yfinance as yf
import pandas as pd
import numpy as np

# 1. Broad Universe for Dynamic Picking
power = ['NTPC.NS', 'POWERGRID.NS']
fmcg = ['NESTLEIND.NS', 'HINDUNILVR.NS', 'BRITANNIA.NS']
pharma = ['SUNPHARMA.NS', 'CIPLA.NS']
benchmark = '^NSEI'

# 2. Load Data (Focusing on 2026 Volatility)
data = yf.download(power + fmcg + pharma + [benchmark], 
                   start="2010-01-01", end="2026-05-04", progress=False)['Close'].ffill()
returns = data.pct_change().dropna()

# 3. Dynamic Signal: The "Monsoon Mood" Index
# We compare Power (Heat) vs Pharma/FMCG (Rain/Defensive)
returns['Heat_Score'] = returns[power].mean(axis=1).rolling(10).mean()
returns['Rain_Score'] = returns[fmcg + pharma].mean(axis=1).rolling(10).mean()

# 4. Conservative Strategy Logic
# We only go 'High Heat' if Heat_Score > Rain_Score AND Nifty is above 20-day SMA
returns['Mkt_Trend'] = data[benchmark] > data[benchmark].rolling(20).mean()
returns['Signal'] = np.where((returns['Heat_Score'] > returns['Rain_Score']) & returns['Mkt_Trend'], 1, 0)

# 5. The "Drawdown Guard" (Dynamic Exposure)
# If 10-day strategy return is negative, we drop exposure to 20%
returns['Base_Strat'] = np.where(returns['Signal'] == 1, 
                                 returns[power].mean(axis=1), 
                                 returns[fmcg + pharma].mean(axis=1))

returns['Recent_Perf'] = returns['Base_Strat'].rolling(10).sum()
returns['Risk_Weight'] = np.where(returns['Recent_Perf'] < 0, 0.20, 0.80)

# Final Portfolio: (Risk_Weight * Base_Strat) + (Remaining * 6% Liquid)
cash_rate = 0.06 / 252
returns['Final_Ret'] = (returns['Base_Strat'] * returns['Risk_Weight'].shift(1)) + \
                        (cash_rate * (1 - returns['Risk_Weight'].shift(1)))

# 6. Performance Calculation
cum_ret = (1 + returns['Final_Ret']).cumprod()
years = (returns.index[-1] - returns.index[0]).days / 365.25
xirr = (cum_ret.iloc[-1]**(1/years)) - 1
mdd = (cum_ret / cum_ret.cummax() - 1).min()
beta = returns['Final_Ret'].cov(returns[benchmark]) / returns[benchmark].var()

print(f"--- Weather-Regime Pair Strategy ---")
print(f"XIRR: {xirr*100:.2f}%")
print(f"Max Drawdown: {mdd*100:.2f}%")
print(f"Beta: {beta:.2f}")