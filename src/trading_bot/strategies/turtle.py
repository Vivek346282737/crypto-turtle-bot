from trading_bot.strategies.base import BaseStrategy

class TurtleStrategy(BaseStrategy):
    def __init__(self, breakout_window: int = 20):
        self.breakout_window = breakout_window

    def generate_signal(self, symbol: str, highs, lows, closes):
        if len(highs) < self.breakout_window:
            return None
        upper_channel = highs.iloc[-self.breakout_window:-1].max()
        current_price = closes.iloc[-1]

        if current_price > upper_channel:
            return {
                'symbol': symbol,
                'side': 'BUY',
                'price': current_price,
                'reason': 'Donchian Breakout High'
            }
        return None
