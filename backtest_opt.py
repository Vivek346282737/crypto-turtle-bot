import ccxt
import pandas as pd
import numpy as np

def run_optimized_turtle(symbol="BTC/USDT", timeframe="1h", limit=1000):
    exchange = ccxt.binance({"enableRateLimit": True})
    print("==================================================")
    print("Running Optimized Institutional Engine: " + symbol)
    print("Pure Donchian + Break-Even Lock + 10H Barrier")
    print("==================================================")
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
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

    capital = 1000.0
    trades = []
    position = None

    for i in range(25, len(df)):
        price = df["close"].iloc[i]
        high = df["high"].iloc[i]
        low = df["low"].iloc[i]
        atr = df["ATR"].iloc[i]

        if position:
            side = position["side"]
            entry = position["entry"]
            sl = position["sl"]
            risk = position["risk"]
            exit_barrier = df["Exit_Low_10"].iloc[i] if side == "BUY" else df["Exit_High_10"].iloc[i]
            size = position["size"]
            closed = False
            pnl = 0

            # 1. Break-Even Shield: +1.5R profit aate hi Stop ko entry par lock karo
            if side == "BUY":
                if (price - entry) >= (1.5 * risk) and position["sl"] < entry:
                    position["sl"] = entry

                if low <= position["sl"]:
                    closed = True
                    pnl = (position["sl"] - entry) * size
                elif low <= exit_barrier and price > entry:
                    closed = True
                    pnl = (exit_barrier - entry) * size

            elif side == "SELL":
                if (entry - price) >= (1.5 * risk) and position["sl"] > entry:
                    position["sl"] = entry

                if high >= position["sl"]:
                    closed = True
                    pnl = (entry - position["sl"]) * size
                elif high >= exit_barrier and price < entry:
                    closed = True
                    pnl = (entry - exit_barrier) * size

            if closed:
                fees = (entry * size * 0.0008) + (price * size * 0.0008)
                net_pnl = pnl - fees
                capital += net_pnl
                trades.append(net_pnl)
                position = None

        else:
            # Turtle Entry
            if high > df["High_20"].iloc[i]:
                sl_dist = atr * 2.0
                sl = price - sl_dist
                risk_dollars = capital * 0.01
                size = round(risk_dollars / sl_dist, 4)
                position = {"side": "BUY", "entry": price, "sl": sl, "size": size, "risk": sl_dist}

            elif low < df["Low_20"].iloc[i]:
                sl_dist = atr * 2.0
                sl = price + sl_dist
                risk_dollars = capital * 0.01
                size = round(risk_dollars / sl_dist, 4)
                position = {"side": "SELL", "entry": price, "sl": sl, "size": size, "risk": sl_dist}

    if len(trades) > 0:
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(trades)
        profit_factor = abs(sum(wins) / (sum(losses) + 1e-9))
        print("Optimized Engine Results (" + str(len(trades)) + " Trades)")
        print("Final Capital: $" + str(round(capital, 2)) + " | Net PnL: $" + str(round(total_pnl, 2)))
        print("Win Rate: " + str(round(win_rate, 2)) + "% | Profit Factor: " + str(round(profit_factor, 2)))
    else:
        print("No trades triggered.")

if __name__ == "__main__":
    run_optimized_turtle("BTC/USDT")
