import time
import ccxt
import pandas as pd
from regime import MarketRegime
from risk_engine import InstitutionalRisk

exchange = ccxt.binance({"enableRateLimit": True})
risk_mgr = InstitutionalRisk(initial_capital=998.96, max_risk_pct=0.01)
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

def fetch_df(symbol, timeframe, limit=80):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

print("==========================================================")
print("Institutional Quant Bot v3.0 | Multi-Asset (BTC, ETH, SOL)")
print("Capital:", risk_mgr.balance, "| Max Risk: 1% | Min R:R: 1:3")
print("==========================================================")

while True:
    try:
        # 1. Check Active Trade first
        if risk_mgr.position:
            sym = risk_mgr.position.get("symbol", "BTC/USDT")
            df_sym = fetch_df(sym, "1h", limit=5)
            latest_bar = df_sym.iloc[-1]
            status = risk_mgr.update_position_state(latest_bar["close"], latest_bar["high"], latest_bar["low"])
            if status == "HOLD":
                pos = risk_mgr.position
                print("--- [MONITORING " + sym + "] " + pos["side"] + " @ " + str(pos["entry"]) + " | Current SL: " + str(round(pos["sl"], 2)) + " | TP: " + str(round(pos["tp"], 2)))

        # 2. Multi-Asset Market Scan
        else:
            for sym in SYMBOLS:
                df_1h = fetch_df(sym, "1h", limit=80)
                df_4h = fetch_df(sym, "4h", limit=80)
                regime = MarketRegime.detect(df_1h, df_4h)
                latest_bar = df_1h.iloc[-1]
                current_price = latest_bar["close"]

                tr = pd.concat([
                    df_1h["high"] - df_1h["low"],
                    (df_1h["high"] - df_1h["close"].shift()).abs(),
                    (df_1h["low"] - df_1h["close"].shift()).abs()
                ], axis=1).max(axis=1)
                atr_1h = tr.rolling(14).mean().iloc[-1]

                t_now = time.strftime("%H:%M:%S")
                print("[" + t_now + " | " + sym + "] Price: $" + str(current_price) + " | Regime: " + regime)

                side = None
                if regime == "STRONG_BULL_TREND":
                    side = "BUY"
                    sl_price = current_price - (atr_1h * 1.5)
                    tp_price = current_price + (atr_1h * 4.5)
                elif regime == "STRONG_BEAR_TREND":
                    side = "SELL"
                    sl_price = current_price + (atr_1h * 1.5)
                    tp_price = current_price - (atr_1h * 4.5)

                if side:
                    assessment = risk_mgr.evaluate_entry(current_price, sl_price, regime, win_rate=0.38, reward_ratio=3.0)
                    if assessment["allow"]:
                        order_size = assessment["size"]
                        ev_val = assessment["ev"]
                        risk_mgr.position = {
                            "symbol": sym,
                            "side": side,
                            "entry": current_price,
                            "orig_sl": sl_price,
                            "sl": sl_price,
                            "tp": tp_price,
                            "size": order_size,
                            "ev": ev_val
                        }
                        risk_mgr.log_trade(sym, side, "OPEN", current_price, order_size, 0, ev_val, "REGIME_ENTRY")
                        print(">>> [ORDER EXECUTED] " + sym + " " + side + " " + str(order_size) + " @ " + str(current_price) + " | SL: " + str(round(sl_price, 2)) + " | TP: " + str(round(tp_price, 2)))
                        break
                    else:
                        print("--- [" + sym + " NO TRADE] Reason: " + assessment["reason"])

    except Exception as e:
        print("Engine Error:", e)

    time.sleep(60)
