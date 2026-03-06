import yfinance as yf
import pandas as pd
import os
from datetime import datetime
import time

# --- Configuration ---
TICKER = "NIFTYBEES.NS"
LOG_FILE = "PaperTrade_Log.csv"
INITIAL_CAPITAL = 300000

def log_trade(action, price, balance, timestamp):
    """Saves trade data to a CSV file."""
    df = pd.DataFrame([{
        "Timestamp": timestamp,
        "Action": action,
        "Price": round(price, 2),
        "Virtual_Balance": round(balance, 2)
    }])
    # Append to CSV or create new if not exists
    df.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))

def get_last_state():
    """Checks the CSV to see if we are currently holding or in cash."""
    if not os.path.exists(LOG_FILE):
        return 0, INITIAL_CAPITAL # Position (0=none), Current Cash
    df = pd.read_csv(LOG_FILE)
    if df.empty:
        return 0, INITIAL_CAPITAL
    last_row = df.iloc[-1]
    pos = 1 if last_row['Action'] == "BUY" else 0
    return pos, last_row['Virtual_Balance']

# --- Live Execution Loop ---
position, current_balance = get_last_state()
print(f"Bot Active. Current Balance: ₹{current_balance} | Holding: {'Yes' if position else 'No'}")

while True:
    now = datetime.now()
    # NSE Trading Hours (9:15 AM - 3:30 PM)
    if (now.hour == 9 and now.minute >= 15) or (10 <= now.hour <= 14) or (now.hour == 15 and now.minute <= 30):
        try:
            data = yf.download(TICKER, period="30d", interval="1d", progress=False)
            data.columns = data.columns.get_level_values(0)
            
            cp = data['Close'].iloc[-1]   # Current Price
            ma20 = data['Close'].rolling(window=20).mean().iloc[-1]
            
            # Strategy: 2% dip buy, exit at Mean
            if cp < (ma20 * 0.98) and position == 0:
                position = 1
                log_trade("BUY", cp, current_balance, now)
                print(f"[{now}] Alert: VIRTUAL BUY at {cp}")
                
            elif cp > ma20 and position == 1:
                # Calculate return on the trade
                # Note: In a real bot, we'd track the specific buy price
                # For this simple log, we assume full capital reinvestment
                position = 0
                # Assuming simple profit update for the log
                log_trade("SELL", cp, current_balance, now)
                print(f"[{now}] Alert: VIRTUAL SELL at {cp}")

        except Exception as e:
            print(f"Connection Error: {e}")
    
    # Check every 15 minutes
    time.sleep(900)