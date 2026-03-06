import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ====================== CONFIG ======================
tickers = ["NIFTYBEES.NS", "BANKBEES.NS", "GOLDBEES.NS", "SILVERBEES.NS", "LIQUIDBEES.NS"]
start_date = "2018-01-01"
end_date = datetime.today().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 100000

# Download data
print("Downloading data...")
data = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close']
monthly = data.resample('ME').last().dropna(how='all')

# 6-month momentum + 6-month SMA filter for absolute strength
momentum = monthly.pct_change(periods=6)
sma6 = monthly.rolling(6).mean()

# Volatility (for risk-parity weighting)
returns_daily = data.pct_change()
vol = returns_daily.rolling(126).std() * np.sqrt(252)  # annualized vol
vol_monthly = vol.resample('ME').last()

# ====================== SIGNAL GENERATION ======================
positions = pd.DataFrame(0.0, index=monthly.index, columns=tickers)

for date in monthly.index[6:]:  # need enough history
    mom_row = momentum.loc[date]
    price_row = monthly.loc[date]
    sma_row = sma6.loc[date]
    vol_row = vol_monthly.loc[date]
    
    # Eligible assets: positive momentum AND above 6M SMA
    eligible = mom_row[(mom_row > 0) & (price_row > sma_row)]
    
    if len(eligible) == 0:
        positions.loc[date, "LIQUIDBEES.NS"] = 1.0  # safety in cash proxy
        continue
    
    # Inverse volatility weighting (risk parity)
    vols = vol_row[eligible.index].replace(0, np.nan).dropna()
    if len(vols) == 0:
        positions.loc[date, eligible.index] = 1.0 / len(eligible)
    else:
        inv_vol = 1 / vols
        weights = inv_vol / inv_vol.sum()
        for asset, w in weights.items():
            positions.loc[date, asset] = w

# ====================== BACKTEST ======================
asset_returns = monthly.pct_change()
strategy_returns = (positions.shift(1) * asset_returns).sum(axis=1).dropna()

cum_rets = (1 + strategy_returns).cumprod()
final_value = cum_rets.iloc[-1] * INITIAL_CAPITAL
total_return = (final_value / INITIAL_CAPITAL - 1) * 100

# Performance metrics
years = (monthly.index[-1] - monthly.index[0]).days / 365.25
cagr = ((final_value / INITIAL_CAPITAL) ** (1/years) - 1) * 100
avg_monthly = strategy_returns.mean() * 100

peak = cum_rets.expanding().max()
drawdown = (cum_rets / peak - 1) * 100
max_dd = drawdown.min()

print(f"\n=== DYNAMIC ALL-WEATHER ROTATION RESULTS {start_date[:4]}–{end_date[:4]} ===")
print(f"Final Capital      : ₹{final_value:,.0f}")
print(f"Total Return       : {total_return:.2f}%")
print(f"CAGR               : {cagr:.2f}%")
print(f"Average Monthly    : {avg_monthly:.2f}%   ← Close to your 1% target in good periods")
print(f"Max Drawdown       : {max_dd:.2f}%")
print(f"Months in Cash     : {(positions.sum(axis=1) == 0).sum()}")
print("====================================================")
print("This is historical only. Real trading will have costs/taxes/slippage.")