import time
import ccxt
import pandas as pd
import numpy as np
import os
import csv
from datetime import datetime

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
INITIAL_CAPITAL = 1000.0
RISK_PER_TRADE = 0.01

exchange = ccxt.binance({"enableRateLimit": True})

class TurtleExecutionEngine:
    def __init__(self, capital=INITIAL_CAPITAL):
        self.capital = capital
        self.position = None
        self.log_file = "turtle_trades_audit.csv"
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Symbol", "Side", "Action", "Price", "Amount", "PnL", "Balance", "Reason"])

    def log(self, symbol, side, action, price, amount, pnl, reason):
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                symbol, side, action, price, amount, round(pnl, 2), round(self.capital, 2), reason
            ])

    def fetch_data(self, symbol, limit=50):
        bars = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=limit)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        
        c = df["close"]
        df["High_20"] = df["high"].rolling(20).max().shift(1)
        df["Low_20"] = df["low"].rolling(20).min().shift(1)
        df["Exit_Low_10"] = df["low"].rolling(10).min().shift(1)
        df["Exit_High_10"] = df["high"].rolling(10).max().shift(1)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - c.shift()).abs(),
            (df["low"] - c.shift()).abs()
        ], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(20).mean()
        return df

    def manage_position(self, current_price, high, low, exit_low_10, exit_high_10):
        pos = self.position
        side = pos["side"]
        entry = pos["entry"]
        sl = pos["sl"]
        size = pos["size"]
        sym = pos["symbol"]
        closed = False
        pnl = 0
        reason = ""

        if side == "BUY":
            if low <= sl:
                closed = True
                pnl = (sl - entry) * size
                reason = "STOP_LOSS"
            elif low <= exit_low_10 and current_price > entry:
                closed = True
                pnl = (exit_low_10 - entry) * size
                reason = "10H_TRAILING_EXIT"
        elif side == "SELL":
            if high >= sl:
                closed = True
                pnl = (entry - sl) * size
                reason = "STOP_LOSS"
            elif high >= exit_high_10 and current_price < entry:
                closed = True
                pnl = (entry - exit_high_10) * size
                reason = "10H_TRAILING_EXIT"

        if closed:
            fees = (entry * size * 0.0008) + (current_price * size * 0.0008)
            net_pnl = pnl - fees
            self.capital += net_pnl
            self.log(sym, side, "CLOSE", current_price, size, net_pnl, reason)
            print(">>> [POSITION CLOSED] " + sym + " " + side + " | Net PnL: $" + str(round(net_pnl, 2)) + " | Reason: " + reason + " | Wallet: $" + str(round(self.capital, 2)))
            self.position = None

print("==========================================================")
print("Institutional Turtle Engine v3.5 | Multi-Asset Live Loop")
print("Assets: BTC, ETH, SOL | Pure Asymmetric Edge | Risk: 1%")
print("==========================================================")

engine = TurtleExecutionEngine()

while True:
    try:
        t_now = time.strftime("%H:%M:%S")

        # 1. Active Position Check
        if engine.position:
            sym = engine.position["symbol"]
            df = engine.fetch_data(sym, limit=25)
            latest = df.iloc[-1]
            engine.manage_position(latest["close"], latest["high"], latest["low"], latest["Exit_Low_10"], latest["Exit_High_10"])
            if engine.position:
                p = engine.position
                print("[" + t_now + " | HOLD " + sym + "] " + p["side"] + " @ " + str(p["entry"]) + " | Hard SL: " + str(round(p["sl"], 2)))

        # 2. Multi-Asset Scan
        else:
            for sym in SYMBOLS:
                df = engine.fetch_data(sym, limit=35)
                latest = df.iloc[-1]
                price = latest["close"]
                high = latest["high"]
                low = latest["low"]
                h20 = latest["High_20"]
                l20 = latest["Low_20"]
                atr = latest["ATR"]

                print("[" + t_now + " | " + sym + "] Price: $" + str(price) + " | 20H High: " + str(round(h20, 2)) + " | 20H Low: " + str(round(l20, 2)))

                if high > h20:
                    sl_dist = atr * 2.0
                    sl = price - sl_dist
                    size = round((engine.capital * RISK_PER_TRADE) / sl_dist, 4)
                    engine.position = {"symbol": sym, "side": "BUY", "entry": price, "sl": sl, "size": size}
                    engine.log(sym, "BUY", "OPEN", price, size, 0, "20H_HIGH_BREAKOUT")
                    print(">>> [EXECUTION: BUY BREAKOUT] " + sym + " " + str(size) + " @ " + str(price) + " | SL: " + str(round(sl, 2)))
                    break

                elif low < l20:
                    sl_dist = atr * 2.0
                    sl = price + sl_dist
                    size = round((engine.capital * RISK_PER_TRADE) / sl_dist, 4)
                    engine.position = {"symbol": sym, "side": "SELL", "entry": price, "sl": sl, "size": size}
                    engine.log(sym, "SELL", "OPEN", price, size, 0, "20H_LOW_BREAKOUT")
                    print(">>> [EXECUTION: SELL BREAKOUT] " + sym + " " + str(size) + " @ " + str(price) + " | SL: " + str(round(sl, 2)))
                    break

    except Exception as e:
        print("Engine Exception:", e)

    time.sleep(60)
