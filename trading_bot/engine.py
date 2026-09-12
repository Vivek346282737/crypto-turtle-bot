import os
import csv
from datetime import datetime
import config

class BestExecutionEngine:
    def __init__(self):
        self.balance = config.INITIAL_BALANCE
        self.position = None
        self.log_file = "trades_log.csv"
        self.last_trade_time = None
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Action", "Side", "Price", "Amount", "PnL", "Balance", "Reason"])

    def _log(self, action, side, price, amount, pnl, reason):
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, side, price, amount, round(pnl, 2), round(self.balance, 2), reason])

    def check_exit(self, current_price, high, low):
        if not self.position:
            return
        entry = self.position["price"]
        side = self.position["side"]
        amount = self.position["amount"]
        sl = self.position["sl"]
        tp = self.position["tp"]
        close, reason, pnl = False, "", 0

        if side == "BUY":
            if low <= sl:
                close, reason = True, "STOP-LOSS"
                pnl = -config.FIXED_RISK_USD
            elif high >= tp:
                close, reason = True, "TAKE-PROFIT"
                pnl = config.FIXED_RISK_USD * config.REWARD_RATIO
        elif side == "SELL":
            if high >= sl:
                close, reason = True, "STOP-LOSS"
                pnl = -config.FIXED_RISK_USD
            elif low <= tp:
                close, reason = True, "TAKE-PROFIT"
                pnl = config.FIXED_RISK_USD * config.REWARD_RATIO

        if close:
            self.balance += pnl
            self._log("CLOSE", side, current_price, amount, pnl, reason)
            print(f">>> [CLOSED] {side} @ {current_price} | {reason} | PnL: ${round(pnl, 2)} | Wallet: ${round(self.balance, 2)}")
            self.position = None
            self.last_trade_time = datetime.now()

    def enter_position(self, side, price, atr):
        if self.position:
            return
        if self.last_trade_time:
            elapsed = (datetime.now() - self.last_trade_time).total_seconds() / 3600
            if elapsed < 1: # 1-hour cooldown between trades for clean execution
                return

        sl_dist = atr * config.ATR_MULTIPLIER_SL
        tp_dist = sl_dist * config.REWARD_RATIO
        amount = round(config.FIXED_RISK_USD / sl_dist, 4)

        if amount <= 0:
            return

        if side == "BUY":
            sl = price - sl_dist
            tp = price + tp_dist
        else:
            sl = price + sl_dist
            tp = price - tp_dist

        self.position = {"side": side, "price": price, "amount": amount, "sl": sl, "tp": tp}
        self._log("OPEN", side, price, amount, 0, "SIGNAL")
        print(f">>> [OPENED] {side} {amount} BTC @ {price} | Strict SL: {round(sl, 2)} | Massive TP (1:4): {round(tp, 2)}")
