import pandas as pd
from trading_bot.strategies.turtle import TurtleStrategy

def test_turtle_strategy_breakout():
    strategy = TurtleStrategy(breakout_window=3)
    highs = pd.Series([10, 12, 15, 18])
    lows = pd.Series([8, 9, 10, 11])
    closes = pd.Series([10, 11, 14, 17])
    
    signal = strategy.generate_signal('BTC/USDT', highs, lows, closes)
    assert signal is not None
    assert signal['side'] == 'BUY'
    assert signal['symbol'] == 'BTC/USDT'
