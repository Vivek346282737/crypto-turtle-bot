import pandas as pd
import numpy as np

class BacktestEngine:
    def __init__(self, initial_capital: float = 10000.0, fee_pct: float = 0.001):
        self.initial_capital = initial_capital
        self.fee_pct = fee_pct

    def run_backtest(self, prices: pd.Series, signals: pd.Series) -> dict:
        capital = self.initial_capital
        position = 0
        trades = 0
        
        for i in range(1, len(prices)):
            if signals.iloc[i] == 1 and position == 0:
                # Buy signal
                entry_price = prices.iloc[i]
                capital -= capital * self.fee_pct
                position = capital / entry_price
                capital = 0
                trades += 1
            elif signals.iloc[i] == -1 and position > 0:
                # Sell signal
                exit_price = prices.iloc[i]
                capital = position * exit_price
                capital -= capital * self.fee_pct
                position = 0
                trades += 1

        final_value = capital if position == 0 else position * prices.iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital

        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return_pct': total_return * 100,
            'total_trades': trades

        }
