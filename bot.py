!pip install alpaca-trade-api

from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import requests
import datetime
import time
import os

API_KEY = os.getenv("ALPACA_KEY")
API_SECRET = os.getenv("ALPACA_SECRET")
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, API_SECRET, BASE_URL)

# Liquid sector ETFs with strong trends
symbols = ["XLK", "XLE", "XLF", "XLV", "XLI"]

qty = 3  # per trade (adjust based on account size)
stop_loss_pct = 0.97  # -3%
take_profit_pct = 1.03  # +3%

def get_sma_data(symbol):
    bars = api.get_bars(symbol, TimeFrame.Minute, limit=100)
    df = pd.DataFrame([b.__dict__["_raw"] for b in bars])
    df["close"] = pd.to_numeric(df["c"])
    df["sma_fast"] = df["close"].rolling(5).mean()
    df["sma_slow"] = df["close"].rolling(20).mean()
    return df.dropna()

def in_position(symbol):
    return any(p.symbol == symbol for p in api.list_positions())

def get_position(symbol):
    for p in api.list_positions():
        if p.symbol == symbol:
            return float(p.avg_entry_price), float(p.current_price)
    return None, None

def run_strategy():
    clock = api.get_clock()
    if not clock.is_open:
        print("⏳ Market closed… waiting.")
        return

    for symbol in symbols:
        try:
            df = get_sma_data(symbol)
            fast, slow = df["sma_fast"].iloc[-1], df["sma_slow"].iloc[-1]
            pf, ps = df["sma_fast"].iloc[-2], df["sma_slow"].iloc[-2]

            holding = in_position(symbol)

            # Risk exits
            if holding:
                entry, current = get_position(symbol)

                if current <= entry * stop_loss_pct:
                    print(f"{symbol} ❌ Stop loss: SELL")
                    api.submit_order(symbol=symbol, qty=qty, side="sell", type="market")
                    continue

                if current >= entry * take_profit_pct:
                    print(f"{symbol} ✅ Take profit: SELL")
                    api.submit_order(symbol=symbol, qty=qty, side="sell", type="market")
                    continue

            # Buy signal
            if not holding and pf < ps and fast > slow:
                print(f"{symbol} 📈 Trend up: BUY")
                api.submit_order(symbol=symbol, qty=qty, side="buy", type="market")
                continue

            # Sell signal
            if holding and pf > ps and fast < slow:
                print(f"{symbol} 📉 Trend down: SELL")
                api.submit_order(symbol=symbol, qty=qty, side="sell", type="market")
                continue

            print(f"{symbol} — No signal")

        except Exception as e:
            print(f"⚠️ Error on {symbol}: {e}")

# Loop: checks every 2 minutes
while True:
    run_strategy()
    time.sleep(120)
