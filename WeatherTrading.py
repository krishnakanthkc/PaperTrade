import yfinance as yf
import pandas as pd
import numpy as np

# 1. Load Natural Gas (NG=F) and a baseline like Crude Oil (CL=F)
tickers = ["NG=F", "CL=F"]
data = yf.download(tickers, start="2015-01-01", end="2026-01-01")['Close']

# 2. Strategy: Seasonal Weather Play
# We go long Natural Gas ONLY during the 'Heating Season' (Nov - Feb)
data['Month'] = data.index.month
data['Is_Winter'] = data['Month'].apply(lambda x: 1 if x in [11, 12, 1, 2] else 0)

# 3. Calculate Daily Returns
data['NG_Returns'] = data['NG=F'].pct_change()

# 4. Apply Weather Logic: 
# If it's winter, we hold NG. If not, we stay in Cash (0 return).
data['Weather_Strategy'] = data['NG_Returns'] * data['Is_Winter'].shift(1)

# 5. Performance Metrics
data.dropna(inplace=True)
cum_return = (1 + data['Weather_Strategy']).cumprod()
cagr = (cum_return.iloc[-1]**(252/len(data))) - 1
volatility = data['Weather_Strategy'].std() * np.sqrt(252)
sharpe = cagr / volatility

print(f"Weather Seasonal Strategy Results:")
print(f"XIRR (Approx): {cagr*100:.2f}%")
print(f"Annual Volatility: {volatility*100:.2f}%")
print(f"Sharpe Ratio: {sharpe:.2f}")

# Plotting the 'Winter Effect'
import matplotlib.pyplot as plt
cum_return.plot(title="Cumulative Returns of Winter-Only NG Strategy")
plt.show()