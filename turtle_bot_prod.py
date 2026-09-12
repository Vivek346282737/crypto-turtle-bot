import time
import ccxt
import pandas as pd
import numpy as np
import os
import json
import csv
from datetime import datetime

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
INITIAL_CAPITAL = 1000.0
RISK_PER_TRADE = 0.01
MAX_DAILY_LOSS = 0.03

exchange = ccxt.binance({"enableRateLimit": True})

class InstitutionalTurtleProd:
    def __init__(self, capital=INITIAL_CAPITAL):
        self.capital = capital
        self.daily_start_capital = capital
        self.last_day = datetime.now().day
        self.position = None
        self.state_file = "bot_state.json"
        self.log_file = "turtle_trades_audit.csv"
        self._init_files()
        self._load_state()

    def _init_files(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Symbol", "Side", "Action", "Price", "Amount", "PnL", "Balance", "Reason"])

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump({
                "capital": self.capital,
                "daily_start": self.daily_start_capital,
                "position": self.position
            }, f, indent=4)

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.capital = data.get("capital", self.capital)
                    self.daily_start_capital = data.get("daily_start", self.daily_start_capital)
                    self.position = data.get("position", None)
                    if self.position:
                        sym = self.position.get("symbol", "")
                        side = self.position.get("side", "")
                        print(">>> [RECOVERED STATE] Resuming position: " + sym + " " + side)
            except Exception:
                pass

    def check_daily_reset(self):
        current_day = datetime.now().day
        if current_day != self.last_day:
            self.daily_start_capital = self.capital
            self.last_day = current_day
            self._save_state()

    def is_kill_switch_active(self):
        self.check_daily_reset()
        drawdown = (self.daily_start_capital - self.capital) / self.daily_start_capital
        if drawdown >= MAX_DAILY_LOSS:
            return True, round(drawdown * 100, 2)
        return False, 0.0

    def log(self, symbol, side, action, price, amount, pnl, reason):
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                symbol, side, action, price, amount, round(pnl, 2), round(self.capital, 2), reason
            ])
        self._save_state()

    def fetch_data(self, symbol, limit=50):
        bars = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=limit)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
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
        risk = pos["risk"]
        size = pos["size"]
        sym = pos["symbol"]
        closed = False
        pnl = 0
        reason = ""

        # Break-Even Lock at +1.5R
        if side == "BUY":
            if (current_price - entry) >= (1.5 * risk) and pos["sl"] < entry:
                pos["sl"] = entry
                print(">>> [PROTECTION ACTIVE] " + sym + " SL locked to BREAK-EVEN @ " + str(entry))
                self._save_state()

            if low <= pos["sl"]:
                closed = True
                pnl = (pos["sl"] - entry) * size
                reason = "BREAK_EVEN" if pos["sl"] == entry else "STOP_LOSS"
            elif low <= exit_low_10 and current_price > entry:
                closed = True
                pnl = (exit_low_10 - entry) * size
                reason = "10H_BARRIER_EXIT"

        elif side == "SELL":
            if (entry - current_price) >= (1.5 * risk) and pos["sl"] > entry:
                pos["sl"] = entry
                print(">>> [PROTECTION ACTIVE] " + sym + " SL locked to BREAK-EVEN @ " + str(entry))
                self._save_state()

            if high >= pos["sl"]:
                closed = True
                pnl = (entry - pos["sl"]) * size
                reason = "BREAK_EVEN" if pos["sl"] == entry else "STOP_LOSS"
            elif high >= exit_high_10 and current_price < entry:
                closed = True
                pnl = (entry - exit_high_10) * size
                reason = "10H_BARRIER_EXIT"

        if closed:
            fees = (entry * size * 0.0008) + (current_price * size * 0.0008)
            net_pnl = pnl - fees
            self.capital += net_pnl
            self.log(sym, side, "CLOSE", current_price, size, net_pnl, reason)
            print(">>> [POSITION CLOSED] " + sym + " " + side + " | Net: $" + str(round(net_pnl, 2)) + " | Reason: " + reason + " | Balance: $" + str(round(self.capital, 2)))
            self.position = None
            self._save_state()

print("==========================================================")
print("Turtle Engine v4.1 (Final Quant Edge) | BTC, ETH, SOL")
print("Donchian 20H + Break-Even Lock (+1.5R) + 3% Daily KillSwitch")
print("==========================================================")

engine = InstitutionalTurtleProd()

while True:
    try:
        t_now = time.strftime("%H:%M:%S")

        killed, dd_pct = engine.is_kill_switch_active()
        if killed:
            print("[" + t_now + "] [KILL-SWITCH ACTIVE] Daily loss exceeded " + str(dd_pct) + "%. Paused.")
            time.sleep(300)
            continue

        if engine.position:
            sym = engine.position["symbol"]
            df = engine.fetch_data(sym, limit=25)
            latest = df.iloc[-1]
            engine.manage_position(latest["close"], latest["high"], latest["low"], latest["Exit_Low_10"], latest["Exit_High_10"])
            if engine.position:
                p = engine.position
                print("[" + t_now + " | HOLD " + sym + "] " + p["side"] + " @ " + str(p["entry"]) + " | Live: $" + str(latest["close"]) + " | Current SL: " + str(round(p["sl"], 2)))

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
                    engine.position = {"symbol": sym, "side": "BUY", "entry": price, "sl": sl, "size": size, "risk": sl_dist}
                    engine.log(sym, "BUY", "OPEN", price, size, 0, "20H_HIGH_BREAKOUT")
                    print(">>> [ORDER FIRED: BUY] " + sym + " " + str(size) + " @ " + str(price) + " | SL: " + str(round(sl, 2)))
                    break

                elif low < l20:
                    sl_dist = atr * 2.0
                    sl = price + sl_dist
                    size = round((engine.capital * RISK_PER_TRADE) / sl_dist, 4)
                    engine.position = {"symbol": sym, "side": "SELL", "entry": price, "sl": sl, "size": size, "risk": sl_dist}
                    engine.log(sym, "SELL", "OPEN", price, size, 0, "20H_LOW_BREAKOUT")
                    print(">>> [ORDER FIRED: SELL] " + sym + " " + str(size) + " @ " + str(price) + " | SL: " + str(round(sl, 2)))
                    break

    except Exception as e:
        print("Loop Error:", e)

    time.sleep(60)
