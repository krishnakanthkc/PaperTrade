import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Load Data with Robust Check
def get_data(tickers, start, end):
    try:
        data = yf.download(tickers, start=start, end=end, progress=False)['Close']
        if data.empty:
            raise ValueError("No data downloaded. Check tickers or internet.")
        return data.ffill().dropna()
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

# Tickers: Blue Star (Growth/Weather) and Power Grid (Low Beta Anchor)
tickers = ["BLUESTARCO.NS", "POWERGRID.NS", "^NSEI"]
df = get_data(tickers, "2018-01-01", "2026-05-01")

if not df.empty:
    # 2. Strategy Logic
    df['Basket_Ret'] = df[["BLUESTARCO.NS", "POWERGRID.NS"]].pct_change().mean(axis=1)
    df['Mkt_Ret'] = df["^NSEI"].pct_change()
    
    # Technical Indicators
    df['SMA_20'] = df["BLUESTARCO.NS"].rolling(20).mean()
    df['Mkt_SMA_200'] = df["^NSEI"].rolling(200).mean()
    
    # Rules: Feb-June, Stock > SMA20, and Market is Healthy
    df['Month'] = df.index.month
    df['Season'] = df['Month'].apply(lambda x: 1 if x in [2, 3, 4, 5, 6] else 0)
    
    df['Signal'] = 0
    df.loc[(df['Season'] == 1) & 
           (df['BLUESTARCO.NS'] > df['SMA_20']) & 
           (df['^NSEI'] > df['Mkt_SMA_200']), 'Signal'] = 1

    # 3. Execution (Shift to avoid look-ahead bias)
    df['Strat_Ret'] = df['Basket_Ret'] * df['Signal'].shift(1)
    
    # 4. Robust Metrics Function (Fixed for Empty Data)
    def calculate_metrics(strat_ret, mkt_ret):
        combined = pd.DataFrame({'strat': strat_ret, 'mkt': mkt_ret}).dropna()
        if combined.empty or len(combined) < 2:
            return 0, 0, 0, pd.Series([1])
            
        cum_ret = (1 + combined['strat']).cumprod()
        total_years = (combined.index[-1] - combined.index[0]).days / 365.25
        xirr = (cum_ret.iloc[-1]**(1/total_years)) - 1
        
        # Beta
        beta = combined['strat'].cov(combined['mkt']) / combined['mkt'].var()
        mdd = (cum_ret / cum_ret.cummax() - 1).min()
        
        return xirr, beta, mdd, cum_ret

    xirr, beta, mdd, cum_series = calculate_metrics(df['Strat_Ret'], df['Mkt_Ret'])

    print(f"--- Cooling Momentum Strategy ---")
    print(f"XIRR: {xirr*100:.2f}%")
    print(f"Beta: {beta:.2f}")
    print(f"Max Drawdown: {mdd*100:.2f}%")

    cum_series.plot(title="Growth of Investment (Weather Momentum)")
    plt.show()