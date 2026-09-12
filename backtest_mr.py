import ccxt
import pandas as pd
import numpy as np

def run_mean_reversion_backtest(symbol="BTC/USDT", timeframe="1h", limit=1000):
    exchange = ccxt.binance({"enableRateLimit": True})
    print("==================================================")
    print("Running Institutional Mean-Reversion Backtest: " + symbol)
    print("==================================================")
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    c = df["close"]
    
    # Bollinger Bands (20, 2.0)
    sma_20 = c.rolling(20).mean()
    std_20 = c.rolling(20).std()
    df["BB_Upper"] = sma_20 + (std_20 * 2.0)
    df["BB_Lower"] = sma_20 - (std_20 * 2.0)
    df["SMA_20"] = sma_20

    # RSI (14)
    delta = c.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    # ATR (14)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - c.shift()).abs(),
        (df["low"] - c.shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    capital = 1000.0
    trades = []
    position = None

    for i in range(30, len(df)):
        price = df["close"].iloc[i]
        high = df["high"].iloc[i]
        low = df["low"].iloc[i]
        atr = df["ATR"].iloc[i]
        rsi = df["RSI"].iloc[i]
        bb_u = df["BB_Upper"].iloc[i]
        bb_l = df["BB_Lower"].iloc[i]
        mid = df["SMA_20"].iloc[i]

        if position:
            side = position["side"]
            entry = position["entry"]
            sl = position["sl"]
            tp = position["tp"]
            size = position["size"]
            closed = False
            pnl = 0

            if side == "BUY":
                if low <= sl:
                    closed = True
                    pnl = (sl - entry) * size
                elif high >= tp:
                    closed = True
                    pnl = (tp - entry) * size
            elif side == "SELL":
                if high >= sl:
                    closed = True
                    pnl = (entry - sl) * size
                elif low <= tp:
                    closed = True
                    pnl = (entry - tp) * size

            if closed:
                fees = (entry * size * 0.0008) + (price * size * 0.0008)
                net_pnl = pnl - fees
                capital += net_pnl
                trades.append(net_pnl)
                position = None

        else:
            # Mean-Reversion Entries: Extreme RSI + Outer Band Touch
            # Target = Mean (SMA 20) | Stop = 1.2 x ATR
            if price <= bb_l and rsi < 32:
                side = "BUY"
                sl_dist = atr * 1.2
                tp = mid
                sl = price - sl_dist
                risk_dollars = capital * 0.01
                size = round(risk_dollars / sl_dist, 4)
                if tp > price:
                    position = {"side": side, "entry": price, "sl": sl, "tp": tp, "size": size}

            elif price >= bb_u and rsi > 68:
                side = "SELL"
                sl_dist = atr * 1.2
                tp = mid
                sl = price + sl_dist
                risk_dollars = capital * 0.01
                size = round(risk_dollars / sl_dist, 4)
                if tp < price:
                    position = {"side": side, "entry": price, "sl": sl, "tp": tp, "size": size}

    if len(trades) > 0:
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(trades)
        profit_factor = abs(sum(wins) / (sum(losses) + 1e-9))
        print("Mean-Reversion Backtest (" + str(len(trades)) + " Trades)")
        print("Final Capital: $" + str(round(capital, 2)) + " | Net PnL: $" + str(round(total_pnl, 2)))
        print("Win Rate: " + str(round(win_rate, 2)) + "% | Profit Factor: " + str(round(profit_factor, 2)))
    else:
        print("No trades generated under mean-reversion rules.")

if __name__ == "__main__":
    run_mean_reversion_backtest("BTC/USDT")
