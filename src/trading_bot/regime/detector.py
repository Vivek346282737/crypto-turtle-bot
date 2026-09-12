import pandas as pd

class RegimeDetector:
    def __init__(self, window: int = 20):
        self.window = window

    def detect(self, closes: pd.Series) -> str:
        if len(closes) < self.window:
            return 'UNKNOWN'
        sma = closes.rolling(window=self.window).mean().iloc[-1]
        current_price = closes.iloc[-1]

        if current_price > sma * 1.02:
            return 'TREND_UP'
        elif current_price < sma * 0.98:
            return 'TREND_DOWN'
        return 'RANGE'
