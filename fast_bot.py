import time
import ccxt
import pandas as pd
import os
import csv
from datetime import datetime

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
INITIAL_CAPITAL = 1000.0
RISK_PER_TRADE = 0.01

exchange = ccxt.binance({"enableRateLimit": True})

class FastExecutionEngine:
    def __init__(self, capital=INITIAL_CAPITAL):
        self.capital = capital
        self.position = None
        self.log_file = "fast_trades_audit.csv"
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

    def fetch_fast_data(self, symbol):
        # 1-Minute timeframe with 5-candle breakout for instant action
        bars = exchange.fetch_ohlcv(symbol, timeframe="1m", limit=20)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        
        c = df["close"]
        df["High_Fast"] = df["high"].rolling(5).max().shift(1)
        df["Low_Fast"] = df["low"].rolling(5).min().shift(1)
        df["Exit_Low"] = df["low"].rolling(3).min().shift(1)
        df["Exit_High"] = df["high"].rolling(3).max().shift(1)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - c.shift()).abs(),
            (df["low"] - c.shift()).abs()
        ], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(5).mean()
        return df

    def manage_position(self, current_price, high, low, exit_low, exit_high):
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
            elif low <= exit_low and current_price > entry:
                closed = True
                pnl = (exit_low - entry) * size
                reason = "TRAILING_PROFIT_EXIT"
        elif side == "SELL":
            if high >= sl:
                closed = True
                pnl = (entry - sl) * size
                reason = "STOP_LOSS"
            elif high >= exit_high and current_price < entry:
                closed = True
                pnl = (entry - exit_high) * size
                reason = "TRAILING_PROFIT_EXIT"

        if closed:
            fees = (entry * size * 0.0008) + (current_price * size * 0.0008)
            net_pnl = pnl - fees
            self.capital += net_pnl
            self.log(sym, side, "CLOSE", current_price, size, net_pnl, reason)
            print(">>> [CLOSED] " + sym + " " + side + " | Net PnL: $" + str(round(net_pnl, 2)) + " | Reason: " + reason + " | Wallet: $" + str(round(self.capital, 2)))
            self.position = None

print("==========================================================")
print("Instant Fast-Execution Engine | 1-Minute Live Action Loop")
print("Scanning: BTC, ETH, SOL | 5-Period Breakout | 10s Fast Check")
print("==========================================================")

engine = FastExecutionEngine()

while True:
    try:
        t_now = time.strftime("%H:%M:%S")

        if engine.position:
            sym = engine.position["symbol"]
            df = engine.fetch_fast_data(sym)
            latest = df.iloc[-1]
            engine.manage_position(latest["close"], latest["high"], latest["low"], latest["Exit_Low"], latest["Exit_High"])
            if engine.position:
                p = engine.position
                print("[" + t_now + " | ACTIVE " + sym + "] " + p["side"] + " @ " + str(p["entry"]) + " | Live Price: $" + str(latest["close"]) + " | SL: " + str(round(p["sl"], 2)))

        else:
            for sym in SYMBOLS:
                df = engine.fetch_fast_data(sym)
                latest = df.iloc[-1]
                price = latest["close"]
                high = latest["high"]
                low = latest["low"]
                h_break = latest["High_Fast"]
                l_break = latest["Low_Fast"]
                atr = latest["ATR"]

                print("[" + t_now + " | " + sym + "] Price: $" + str(price) + " | Breakout High: " + str(round(h_break, 2)) + " | Breakout Low: " + str(round(l_break, 2)))

                if high > h_break:
                    sl_dist = max(atr * 1.5, price * 0.001)
                    sl = price - sl_dist
                    size = round((engine.capital * RISK_PER_TRADE) / sl_dist, 4)
                    engine.position = {"symbol": sym, "side": "BUY", "entry": price, "sl": sl, "size": size}
                    engine.log(sym, "BUY", "OPEN", price, size, 0, "FAST_HIGH_BREAKOUT")
                    print(">>> [FAST ORDER FIRED: BUY] " + sym + " " + str(size) + " @ " + str(price) + " | SL: " + str(round(sl, 2)))
                    break

                elif low < l_break:
                    sl_dist = max(atr * 1.5, price * 0.001)
                    sl = price + sl_dist
                    size = round((engine.capital * RISK_PER_TRADE) / sl_dist, 4)
                    engine.position = {"symbol": sym, "side": "SELL", "entry": price, "sl": sl, "size": size}
                    engine.log(sym, "SELL", "OPEN", price, size, 0, "FAST_LOW_BREAKOUT")
                    print(">>> [FAST ORDER FIRED: SELL] " + sym + " " + str(size) + " @ " + str(price) + " | SL: " + str(round(sl, 2)))
                    break

    except Exception as e:
        print("Fast Loop Error:", e)

    time.sleep(10)
