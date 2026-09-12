import ccxt
import pandas as pd
import numpy as np

def run_backtest(symbol="BTC/USDT", timeframe="1h", limit=1000):
    exchange = ccxt.binance({"enableRateLimit": True})
    print("==================================================")
    print("Running Institutional Regime Backtest: " + symbol)
    print("==================================================")
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    c = df["close"]
    df["EMA_20"] = c.ewm(span=20, adjust=False).mean()
    df["EMA_50"] = c.ewm(span=50, adjust=False).mean()
    df["EMA_200"] = c.ewm(span=200, adjust=False).mean()

    # ATR
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - c.shift()).abs(),
        (df["low"] - c.shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()

    # Trend Strength Filter (ADX Proxy via Directional Movement)
    up_move = df["high"] - df["high"].shift()
    down_move = df["low"].shift() - df["low"]
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / (df["ATR"] + 1e-9))
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / (df["ATR"] + 1e-9))
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    df["ADX"] = dx.rolling(14).mean()

    capital = 1000.0
    trades = []
    position = None

    for i in range(200, len(df)):
        current_price = df["close"].iloc[i]
        high = df["high"].iloc[i]
        low = df["low"].iloc[i]
        current_atr = df["ATR"].iloc[i]

        if position:
            side = position["side"]
            entry = position["entry"]
            sl = position["sl"]
            tp = position["tp"]
            size = position["size"]
            closed = False
            pnl = 0

            # Dynamic Break-Even (+1R pe SL shift)
            if side == "SELL":
                if (entry - current_price) >= position["risk"]:
                    position["sl"] = min(position["sl"], entry)
                if high >= position["sl"]:
                    closed = True
                    pnl = (entry - position["sl"]) * size
                elif low <= tp:
                    closed = True
                    pnl = (entry - tp) * size
            elif side == "BUY":
                if (current_price - entry) >= position["risk"]:
                    position["sl"] = max(position["sl"], entry)
                if low <= position["sl"]:
                    closed = True
                    pnl = (position["sl"] - entry) * size
                elif high >= tp:
                    closed = True
                    pnl = (tp - entry) * size

            if closed:
                fees = (entry * size * 0.0008) + (current_price * size * 0.0008)
                net_pnl = pnl - fees
                capital += net_pnl
                trades.append(net_pnl)
                position = None

        else:
            # Regime Confirmation: Trend alignment + Macro Trend + ADX > 22
            is_strong_trend = df["ADX"].iloc[i] > 22
            is_bull = (
                is_strong_trend and 
                c.iloc[i] > df["EMA_200"].iloc[i] and 
                df["EMA_20"].iloc[i] > df["EMA_50"].iloc[i] and
                c.iloc[i] > df["EMA_20"].iloc[i]
            )
            is_bear = (
                is_strong_trend and 
                c.iloc[i] < df["EMA_200"].iloc[i] and 
                df["EMA_20"].iloc[i] < df["EMA_50"].iloc[i] and
                c.iloc[i] < df["EMA_20"].iloc[i]
            )

            if is_bull or is_bear:
                side = "BUY" if is_bull else "SELL"
                sl_dist = current_atr * 1.5
                tp_dist = current_atr * 3.5  # Realistic 1:2.33 target for trend capture
                risk_dollars = capital * 0.01
                size = round(risk_dollars / sl_dist, 4)

                sl = current_price - sl_dist if side == "BUY" else current_price + sl_dist
                tp = current_price + tp_dist if side == "BUY" else current_price - tp_dist

                position = {"side": side, "entry": current_price, "sl": sl, "tp": tp, "size": size, "risk": sl_dist}

    if len(trades) > 0:
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(trades)
        profit_factor = abs(sum(wins) / (sum(losses) + 1e-9))
        print("Regime Filtered Backtest (" + str(len(trades)) + " Trades)")
        print("Final Capital: $" + str(round(capital, 2)) + " | Net PnL: $" + str(round(total_pnl, 2)))
        print("Win Rate: " + str(round(win_rate, 2)) + "% | Profit Factor: " + str(round(profit_factor, 2)))
    else:
        print("No trades qualified under strict regime rules.")

if __name__ == "__main__":
    run_backtest("BTC/USDT")
