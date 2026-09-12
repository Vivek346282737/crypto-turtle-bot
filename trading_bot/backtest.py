import ccxt
import pandas as pd
import config
from indicators import add_indicators

def run_backtest():
    print("==================================================")
    print("Running 30-Day Historical Backtest (1-Hour Timeframe)")
    print("==================================================")
    
    exchange = ccxt.binance({"enableRateLimit": True})
    bars = exchange.fetch_ohlcv(config.SYMBOL, timeframe="1h", limit=720)
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = add_indicators(df)
    df = df.dropna().reset_index(drop=True)

    balance = config.INITIAL_BALANCE
    trades_count = 0
    wins = 0
    losses = 0

    position = None

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        price = row["close"]
        atr = row["ATR"]

        if position:
            side = position["side"]
            entry = position["price"]
            sl = position["sl"]
            tp = position["tp"]
            amount = position["amount"]

            if side == "BUY":
                if row["low"] <= sl:
                    balance -= config.FIXED_RISK_USD
                    losses += 1
                    position = None
                elif row["high"] >= tp:
                    profit = config.FIXED_RISK_USD * config.REWARD_RATIO
                    balance += profit
                    wins += 1
                    position = None
            elif side == "SELL":
                if row["high"] >= sl:
                    balance -= config.FIXED_RISK_USD
                    losses += 1
                    position = None
                elif row["low"] <= tp:
                    profit = config.FIXED_RISK_USD * config.REWARD_RATIO
                    balance += profit
                    wins += 1
                    position = None
        
        if not position:
            trend_bullish = price > row["EMA_200"]
            trend_bearish = price < row["EMA_200"]

            buy_cond = (
                trend_bullish and
                prev["EMA_9"] <= prev["EMA_21"] and 
                row["EMA_9"] > row["EMA_21"] and 
                row["RSI"] < 62 and 
                row["MACD"] > row["Signal_Line"]
            )
            sell_cond = (
                trend_bearish and
                prev["EMA_9"] >= prev["EMA_21"] and 
                row["EMA_9"] < row["EMA_21"] and 
                row["RSI"] > 38 and 
                row["MACD"] < row["Signal_Line"]
            )

            sl_dist = atr * config.ATR_MULTIPLIER_SL
            tp_dist = sl_dist * config.REWARD_RATIO
            amount = round(config.FIXED_RISK_USD / sl_dist, 4)

            if buy_cond:
                position = {"side": "BUY", "price": price, "amount": amount, "sl": price - sl_dist, "tp": price + tp_dist}
                trades_count += 1
            elif sell_cond:
                position = {"side": "SELL", "price": price, "amount": amount, "sl": price + sl_dist, "tp": price - tp_dist}
                trades_count += 1

    print(f"Total Trades Taken: {trades_count}")
    print(f"Winning Trades: {wins}")
    print(f"Losing Trades: {losses}")
    if trades_count > 0:
        print(f"Win Rate: {round((wins/trades_count)*100, 2)}%")
    print(f"Final Simulated Wallet Balance: ${round(balance, 2)} (Starting: ${config.INITIAL_BALANCE})")
    print("==================================================")

if __name__ == "__main__":
    run_backtest()

