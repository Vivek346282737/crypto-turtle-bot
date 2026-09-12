import os
import csv
from datetime import datetime

class InstitutionalRisk:
    def __init__(self, initial_capital=998.96, max_risk_pct=0.01, max_drawdown_pct=0.05):
        self.balance = initial_capital
        self.peak_balance = initial_capital
        self.max_risk_pct = max_risk_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.position = None
        self.log_file = "trades_audit.csv"
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Symbol", "Side", "Action", "Price", "Amount", "PnL", "Balance", "EV", "Reason"])

    def log_trade(self, symbol, side, action, price, amount, pnl, ev, reason):
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                symbol, side, action, price, amount, round(pnl, 2), round(self.balance, 2), round(ev, 2), reason
            ])

    def evaluate_edge(self, win_rate, reward_ratio, taker_fee_bps=8, slippage_bps=5):
        friction_pct = (taker_fee_bps * 2 + slippage_bps) / 10000.0
        gross_ev = (win_rate * reward_ratio) - ((1.0 - win_rate) * 1.0)
        return gross_ev - friction_pct

    def evaluate_entry(self, entry_price, sl_price, regime, win_rate=0.38, reward_ratio=3.0):
        drawdown = (self.peak_balance - self.balance) / self.peak_balance
        if drawdown >= self.max_drawdown_pct:
            return {"allow": False, "reason": "KILL_SWITCH: Max Drawdown hit (" + str(round(drawdown*100, 2)) + "%)", "size": 0}

        if regime in ["HIGH_VOL_CRISIS", "CHOPPY_RANGE"]:
            return {"allow": False, "reason": "REGIME_FILTER: " + regime + " is unfavorable", "size": 0}

        net_ev = self.evaluate_edge(win_rate, reward_ratio)
        if net_ev <= 0.10:
            return {"allow": False, "reason": "INSUFFICIENT_EDGE: EV is " + str(round(net_ev, 3)), "size": 0}

        sl_dist = abs(entry_price - sl_price)
        if sl_dist <= 0:
            return {"allow": False, "reason": "INVALID_STOP_DISTANCE", "size": 0}

        risk_dollars = self.balance * self.max_risk_pct
        size = round(risk_dollars / sl_dist, 4)
        return {"allow": True, "reason": "TRADE_APPROVED", "size": size, "risk_dollars": risk_dollars, "ev": net_ev}

    def update_position_state(self, current_price, high, low):
        if not self.position:
            return None

        pos = self.position
        side = pos["side"]
        entry = pos["entry"]
        orig_sl = pos["orig_sl"]
        sl = pos["sl"]
        tp = pos["tp"]
        risk_dist = abs(entry - orig_sl)
        close_trade = False
        reason = ""
        pnl = 0

        if side == "SELL":
            unrealized_dist = entry - current_price
            if unrealized_dist >= (2.0 * risk_dist):
                new_sl = entry - (1.0 * risk_dist)
                if new_sl < pos["sl"]:
                    pos["sl"] = new_sl
                    print(">>> [TRAILING SL ACTIVATED] New SL locked at: " + str(round(new_sl, 2)))
            elif unrealized_dist >= (1.0 * risk_dist) and pos["sl"] > entry:
                pos["sl"] = entry
                print(">>> [BREAK-EVEN HIT] SL shifted to Entry: " + str(entry) + " (Risk-Free Trade)")

            if high >= pos["sl"]:
                close_trade = True
                reason = "STOP_LOSS_OR_TRAIL"
                pnl = (entry - pos["sl"]) * pos["size"]
            elif low <= tp:
                close_trade = True
                reason = "TAKE_PROFIT_1:3"
                pnl = (entry - tp) * pos["size"]

        elif side == "BUY":
            unrealized_dist = current_price - entry
            if unrealized_dist >= (2.0 * risk_dist):
                new_sl = entry + (1.0 * risk_dist)
                if new_sl > pos["sl"]:
                    pos["sl"] = new_sl
                    print(">>> [TRAILING SL ACTIVATED] New SL locked at: " + str(round(new_sl, 2)))
            elif unrealized_dist >= (1.0 * risk_dist) and pos["sl"] < entry:
                pos["sl"] = entry
                print(">>> [BREAK-EVEN HIT] SL shifted to Entry: " + str(entry) + " (Risk-Free Trade)")

            if low <= pos["sl"]:
                close_trade = True
                reason = "STOP_LOSS_OR_TRAIL"
                pnl = (pos["sl"] - entry) * pos["size"]
            elif high >= tp:
                close_trade = True
                reason = "TAKE_PROFIT_1:3"
                pnl = (tp - entry) * pos["size"]

        if close_trade:
            self.balance += pnl
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            self.log_trade("BTC/USDT", side, "CLOSE", current_price, pos["size"], pnl, pos["ev"], reason)
            print(">>> [POSITION CLOSED] " + side + " | Exit: " + str(current_price) + " | PnL: $" + str(round(pnl, 2)) + " | Reason: " + reason + " | Balance: $" + str(round(self.balance, 2)))
            self.position = None
            return "CLOSED"

        return "HOLD"
