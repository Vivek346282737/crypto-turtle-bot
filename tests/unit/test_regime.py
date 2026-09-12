import pandas as pd
from trading_bot.regime.detector import RegimeDetector

def test_regime_detection():
    detector = RegimeDetector(window=3)
    closes = pd.Series([100, 102, 105, 110])  # Rising trend
    regime = detector.detect(closes)
    assert regime == 'TREND_UP'
