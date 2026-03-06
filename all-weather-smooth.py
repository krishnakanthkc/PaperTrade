import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ====================== CONFIG ======================
tickers = ["NIFTYBEES.NS", "BANKBEES.NS", "GOLDBEES.NS", "SILVERBEES.NS", "LIQUIDBEES.NS"]
start_date = "2018-01-01"
end_date = datetime.today().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 100000
TARGET_VOL = 0.10          # 10% annualized target volatility (adjust lower for even smoother)
MIN_MOM_THRESHOLD = 0.05   # Require at least +5% momentum to consider
BASE_CASH_FLOOR = 0.20     # Always hold at least 20% in LIQUIDBEES as ballast

# Download data
print("Downloading data...")
data = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close']
monthly = data.resample('ME').last().dropna(how='all')

# Momentum (12-month for smoothness)
momentum = monthly.pct_change(periods=12)

# Long-term trend filter (price > 12-month SMA)
sma12 = monthly.rolling(12).mean()

# Daily returns for vol calculation
returns_daily = data.pct_change()
vol_annual = returns_daily.rolling(126).std() * np.sqrt(252)   # ~6 months rolling vol
vol_monthly = vol_annual.resample('ME').last()

# ====================== SIGNAL & POSITION GENERATION ======================
positions = pd.DataFrame(0.0, index=monthly.index, columns=tickers)

for date in monthly.index[12:]:  # need 12+ months history
    mom_row = momentum.loc[date]
    price_row = monthly.loc[date]
    sma_row = sma12.loc[date]
    vol_row = vol_monthly.loc[date]
    
    # Eligible: positive strong momentum + above long-term trend
    eligible_mask = (mom_row > MIN_MOM_THRESHOLD) & (price_row > sma_row)
    eligible = mom_row[eligible_mask].index
    
    if len(eligible) == 0:
        # Full cash in bad regime
        positions.loc[date, "LIQUIDBEES.NS"] = 1.0
        continue
    
    # Inverse vol weighting among eligible
    vols = vol_row[eligible].replace(0, np.nan).dropna()
    if len(vols) == 0:
        weights = pd.Series(1.0 / len(eligible), index=eligible)
    else:
        inv_vol = 1 / vols
        weights = inv_vol / inv_vol.sum()
    
    # Apply weights, but enforce cash floor
    total_risky_weight = weights.sum()
    scale_factor = min(1.0, TARGET_VOL / vol_row.mean())  # volatility targeting
    
    for asset in eligible:
        positions.loc[date, asset] = weights[asset] * scale_factor * (1 - BASE_CASH_FLOOR)
    
    # Remaining to LIQUIDBEES (floor + leftover)
    positions.loc[date, "LIQUIDBEES.NS"] = BASE_CASH_FLOOR + (1 - total_risky_weight * scale_factor)

# ====================== BACKTEST ======================
asset_returns = monthly.pct_change()
strategy_returns = (positions.shift(1) * asset_returns).sum(axis=1).dropna()

cum_rets = (1 + strategy_returns).cumprod()
final_value = cum_rets.iloc[-1] * INITIAL_CAPITAL
total_return = (final_value / INITIAL_CAPITAL - 1) * 100

# Metrics
years = (monthly.index[-1] - monthly.index[0]).days / 365.25
cagr = ((final_value / INITIAL_CAPITAL) ** (1 / years) - 1) * 100 if years > 0 else 0
avg_monthly = strategy_returns.mean() * 100
monthly_std = strategy_returns.std() * 100

peak = cum_rets.expanding().max()
drawdown = (cum_rets / peak - 1) * 100
max_dd = drawdown.min()

print(f"\n=== SMOOTHER DYNAMIC ALL-WEATHER ROTATION (12M Momentum + Vol Target + Cash Floor) ===")
print(f"Period             : {start_date[:4]} – {end_date[:4]} (~{years:.1f} years)")
print(f"Final Capital      : ₹{final_value:,.0f}")
print(f"Total Return       : {total_return:.2f}%")
print(f"CAGR               : {cagr:.2f}%")
print(f"Average Monthly    : {avg_monthly:.2f}%")
print(f"Monthly Volatility : {monthly_std:.2f}%")
print(f"Max Drawdown       : {max_dd:.2f}%   ← should be noticeably lower than before")
print(f"Months with 0% exposure to risky assets: {(positions[tickers[:-1]].sum(axis=1) == 0).sum()}")
print("==================================================================")
print("This version prioritizes smoothness → expect fewer/big switches, smaller dips, slightly lower upside in roaring bulls.")
print("Real-world: add ~0.1-0.3% per rebalance cost, taxes, slippage. Paper trade first!")