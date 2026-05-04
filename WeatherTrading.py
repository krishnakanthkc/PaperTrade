import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Load Data: Power (Growth) and Agri (The Hedge)
# We use UPL as the short candidate due to its high domestic monsoon sensitivity
tickers = ["ABB.NS", "SIEMENS.NS", "UPL.NS", "^NSEI"]
df = yf.download(tickers, start="2018-01-01", end="2026-05-01", progress=False)['Close'].ffill().dropna()

# 2. Strategy Logic
df['Long_Basket'] = df[["ABB.NS", "SIEMENS.NS"]].pct_change().mean(axis=1)
df['Short_Agri'] = df["UPL.NS"].pct_change()
df['Mkt_Ret'] = df["^NSEI"].pct_change()

# Season: Expanding from Feb to mid-July
df['Month'] = df.index.month
df['Season'] = df['Month'].apply(lambda x: 1 if x in [2, 3, 4, 5, 6, 7] else 0)

# Signals
df['Signal'] = 0
# We only play if Nifty is healthy (SMA 200) and it's the "Weather Window"
df.loc[(df['Season'] == 1) & (df['^NSEI'] > df['^NSEI'].rolling(200).mean()), 'Signal'] = 1

# 3. Arbitrage Execution
# We go 1.5x Long Power AND 0.5x Short Agri (Net 1.0x Exposure)
# This reduces the beta significantly while harvesting the weather delta
leverage_long = 1.5
hedge_short = 0.5

df['Strat_Ret'] = (df['Long_Basket'] * leverage_long - df['Short_Agri'] * hedge_short) * df['Signal'].shift(1)

# 4. Performance Calculation
def calculate_metrics(strat_ret, mkt_ret):
    combined = pd.DataFrame({'strat': strat_ret, 'mkt': mkt_ret}).dropna()
    cum_ret = (1 + combined['strat']).cumprod()
    total_years = (combined.index[-1] - combined.index[0]).days / 365.25
    xirr = (cum_ret.iloc[-1]**(1/total_years)) - 1
    beta = combined['strat'].cov(combined['mkt']) / combined['mkt'].var()
    mdd = (cum_ret / cum_ret.cummax() - 1).min()
    return xirr, beta, mdd, cum_ret

xirr, beta, mdd, cum_series = calculate_metrics(df['Strat_Ret'], df['Mkt_Ret'])

# 5. Output
print(f"--- Macro-Weather Arbitrage Strategy ---")
print(f"XIRR: {xirr*100:.2f}%")
print(f"Strategy Beta: {beta:.2f}")
print(f"Max Drawdown: {mdd*100:.2f}%")

# Plotting the result
plt.figure(figsize=(12,6))
plt.plot(cum_series, label=f'Weather Arbitrage (XIRR: {xirr*100:.1f}%)', color='darkgreen')
plt.plot((1+df['Mkt_Ret']).cumprod(), label='Nifty 50 (Benchmark)', color='gray', alpha=0.5)
plt.title("Final Strategy: Industrial Power Long vs. Agri Short")
plt.legend()
plt.grid(True)
plt.show()