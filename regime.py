import numpy as np
import pandas as pd

class MarketRegime:
    @staticmethod
    def detect(df_1h, df_4h):
        if len(df_1h) < 50 or len(df_4h) < 50:
            return "INSUFFICIENT_DATA"

        c_1h = df_1h["close"]
        c_4h = df_4h["close"]

        ema_50_4h = c_4h.ewm(span=50, adjust=False).mean().iloc[-1]
        ema_200_4h = c_4h.ewm(span=200, adjust=False).mean().iloc[-1]
        macro_bull = ema_50_4h > ema_200_4h
        macro_bear = ema_50_4h < ema_200_4h

        tr = pd.concat([
            df_1h["high"] - df_1h["low"],
            (df_1h["high"] - c_1h.shift()).abs(),
            (df_1h["low"] - c_1h.shift()).abs()
        ], axis=1).max(axis=1)
        natr = (tr.rolling(14).mean() / c_1h) * 100
        current_natr = natr.iloc[-1]
        natr_80th = natr.quantile(0.80)

        ema_20_1h = c_1h.ewm(span=20, adjust=False).mean().iloc[-1]
        ema_50_1h = c_1h.ewm(span=50, adjust=False).mean().iloc[-1]

        if current_natr > natr_80th and abs(c_1h.pct_change(3).iloc[-1]) > 0.04:
            return "HIGH_VOL_CRISIS"
        elif macro_bull and ema_20_1h > ema_50_1h and c_1h.iloc[-1] > ema_20_1h:
            return "STRONG_BULL_TREND"
        elif macro_bear and ema_20_1h < ema_50_1h and c_1h.iloc[-1] < ema_20_1h:
            return "STRONG_BEAR_TREND"
        else:
            return "CHOPPY_RANGE"
