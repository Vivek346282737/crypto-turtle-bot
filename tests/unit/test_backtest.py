import pandas as pd
from trading_bot.backtesting.engine import BacktestEngine

def test_backtest_execution():
    engine = BacktestEngine(initial_capital=10000.0, fee_pct=0.0)
    prices = pd.Series([100, 105, 110, 105, 120])
    signals = pd.Series([0, 1, 0, 0, -1])  # Buy at index 1, Sell at index 4
    
    result = engine.run_backtest(prices, signals)
    assert result['initial_capital'] == 10000.0
    assert result['total_trades'] == 2
    assert result['final_value'] > 10000.0
