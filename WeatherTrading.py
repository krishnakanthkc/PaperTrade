import yfinance as yf
import pandas as pd
import numpy as np

# 1. Load Data: Industrial Weather-Sensitive Stocks
# ABB and Siemens are the backbone of cooling/grid technology
tickers = ["ABB.NS", "SIEMENS.NS", "^NSEI"]
df = yf.download(tickers, start="2018-01-01", end="2026-05-01", progress=False)['Close'].ffill().dropna()

# 2. Strategy Logic
df['Basket_Ret'] = df[["ABB.NS", "SIEMENS.NS"]].pct_change().mean(axis=1)
df['Mkt_Ret'] = df["^NSEI"].pct_change()

# Moving Average for Momentum Validation
df['SMA_50'] = df["ABB.NS"].rolling(50).mean()

# Season: Expanding from February to mid-July (to capture late-summer upgrades)
df['Month'] = df.index.month
df['Day'] = df.index.day
df['Season'] = df.apply(lambda x: 1 if (x['Month'] in [2, 3, 4, 5, 6]) or (x['Month'] == 7 and x['Day'] <= 15) else 0, axis=1)

# Signal: In Season + Above 50-day SMA + Nifty not in a crash
df['Signal'] = 0
df.loc[(df['Season'] == 1) & (df['ABB.NS'] > df['SMA_50']) & (df['^NSEI'] > df['^NSEI'].rolling(200).mean()), 'Signal'] = 1

# 3. Execution with 1.5x Leverage (Futures Simulation)
leverage = 1.5
df['Strat_Ret'] = (df['Basket_Ret'] * leverage) * df['Signal'].shift(1)

# 4. Performance Calculation
def calculate_metrics(strat_ret, mkt_ret):
    combined = pd.DataFrame({'strat': strat_ret, 'mkt': mkt_ret}).dropna()
    cum_ret = (1 + combined['strat']).cumprod()
    
    total_years = (combined.index[-1] - combined.index[0]).days / 365.25
    xirr = (cum_ret.iloc[-1]**(1/total_years)) - 1
    
    # Beta during active periods
    beta = combined['strat'].cov(combined['mkt']) / combined['mkt'].var()
    mdd = (cum_ret / cum_ret.cummax() - 1).min()
    
    return xirr, beta, mdd, cum_ret

xirr, beta, mdd, cum_series = calculate_metrics(df['Strat_Ret'], df['Mkt_Ret'])

print(f"--- Leveraged Industrial Weather Strategy ---")
print(f"XIRR: {xirr*100:.2f}%")
print(f"Strategy Beta: {beta:.2f}")
print(f"Max Drawdown: {mdd*100:.2f}%")