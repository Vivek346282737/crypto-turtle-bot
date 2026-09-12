import ccxt
import pandas as pd
import numpy as np

def run_alpha_backtest(symbol="BTC/USDT", timeframe="1h", limit=1000):
    exchange = ccxt.binance({"enableRateLimit": True})
    print("==================================================")
    print("Running Institutional Alpha Engine: " + symbol)
    print("Volume Confirmation (RVOL) + Volatility Trailing")
    print("==================================================")
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    c = df["close"]
    df["High_20"] = df["high"].rolling(20).max().shift(1)
    df["Low_20"] = df["low"].rolling(20).min().shift(1)

    # ATR (14)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - c.shift()).abs(),
        (df["low"] - c.shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    # RVOL (Volume Confirmation)
    vol_sma = df["volume"].rolling(20).mean()
    df["RVOL"] = df["volume"] / (vol_sma + 1e-9)

    capital = 1000.0
    trades = []
    position = None

    for i in range(25, len(df)):
        price = df["close"].iloc[i]
        high = df["high"].iloc[i]
        low = df["low"].iloc[i]
        atr = df["ATR"].iloc[i]
        rvol = df["RVOL"].iloc[i]

        if position:
            side = position["side"]
            entry = position["entry"]
            sl = position["sl"]
            size = position["size"]
            closed = False
            pnl = 0

            # Dynamic Chandelier Trailing Exit
            if side == "BUY":
                if high > position["peak_price"]:
                    position["peak_price"] = high
                    new_sl = high - (atr * 2.5)
                    if new_sl > position["sl"]:
                        position["sl"] = new_sl

                if low <= position["sl"]:
                    closed = True
                    pnl = (position["sl"] - entry) * size

            elif side == "SELL":
                if low < position["peak_price"]:
                    position["peak_price"] = low
                    new_sl = low + (atr * 2.5)
                    if new_sl < position["sl"]:
                        position["sl"] = new_sl

                if high >= position["sl"]:
                    closed = True
                    pnl = (entry - position["sl"]) * size

            if closed:
                fees = (entry * size * 0.0008) + (price * size * 0.0008)
                net_pnl = pnl - fees
                capital += net_pnl
                trades.append(net_pnl)
                position = None

        else:
            # ALPHA ENTRY: Breakout ONLY with Volume Surge (RVOL > 1.3)
            if high > df["High_20"].iloc[i] and rvol > 1.3:
                sl_dist = atr * 2.0
                sl = price - sl_dist
                risk_dollars = capital * 0.01
                size = round(risk_dollars / sl_dist, 4)
                position = {"side": "BUY", "entry": price, "sl": sl, "size": size, "peak_price": price}

            elif low < df["Low_20"].iloc[i] and rvol > 1.3:
                sl_dist = atr * 2.0
                sl = price + sl_dist
                risk_dollars = capital * 0.01
                size = round(risk_dollars / sl_dist, 4)
                position = {"side": "SELL", "entry": price, "sl": sl, "size": size, "peak_price": price}

    if len(trades) > 0:
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(trades)
        profit_factor = abs(sum(wins) / (sum(losses) + 1e-9))
        print("Alpha Engine Backtest (" + str(len(trades)) + " Filtered Trades)")
        print("Final Capital: $" + str(round(capital, 2)) + " | Net PnL: $" + str(round(total_pnl, 2)))
        print("Win Rate: " + str(round(win_rate, 2)) + "% | Profit Factor: " + str(round(profit_factor, 2)))
    else:
        print("No qualified setups.")

if __name__ == "__main__":
    run_alpha_backtest("BTC/USDT")
