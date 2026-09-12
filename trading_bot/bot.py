import time
import ccxt
import pandas as pd
import config
from indicators import add_indicators
from engine import BestExecutionEngine

def run():
    exchange = ccxt.binance({"enableRateLimit": True})
    engine = BestExecutionEngine()
    print("==================================================")
    print("Best Institutional Setup | 1h Timeframe | 1:4 R:R")
    print("Capital:", config.INITIAL_BALANCE, "| Fixed Risk: $1.0 per trade")
    print("==================================================")

    while True:
        try:
            bars = exchange.fetch_ohlcv(config.SYMBOL, timeframe=config.TIMEFRAME, limit=config.LIMIT)
            df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = add_indicators(df)

            latest = df.iloc[-1]
            prev = df.iloc[-2]
            current_price = latest["close"]
            atr_val = latest["ATR"]

            engine.check_exit(current_price, latest["high"], latest["low"])

            t_str = str(latest["timestamp"])
            print("[" + t_str + "] Price: " + str(current_price) + " | RSI: " + str(round(latest["RSI"], 2)) + " | ATR: " + str(round(atr_val, 2)))

            if not engine.position:
                trend_bullish = current_price > latest["EMA_200"]
                trend_bearish = current_price < latest["EMA_200"]

                buy_cond = (
                    trend_bullish and
                    prev["EMA_9"] <= prev["EMA_21"] and 
                    latest["EMA_9"] > latest["EMA_21"] and 
                    latest["RSI"] < 62 and 
                    latest["MACD"] > latest["Signal_Line"]
                )
                sell_cond = (
                    trend_bearish and
                    prev["EMA_9"] >= prev["EMA_21"] and 
                    latest["EMA_9"] < latest["EMA_21"] and 
                    latest["RSI"] > 38 and 
                    latest["MACD"] < latest["Signal_Line"]
                )

                if buy_cond:
                    engine.enter_position("BUY", current_price, atr_val)
                elif sell_cond:
                    engine.enter_position("SELL", current_price, atr_val)
                else:
                    print("--- Status: Waiting for clean 1-hour institutional setup...")
            else:
                pos = engine.position
                print("--- Active Position:", pos["side"], "| Entry:", pos["price"], "| SL:", round(pos["sl"], 2), "| TP:", round(pos["tp"], 2))

        except Exception as e:
            print("Engine Loop Error:", e)

        time.sleep(60)

if __name__ == "__main__":
    run()
