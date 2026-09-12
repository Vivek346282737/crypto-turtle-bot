import ccxt
import os
from typing import Dict, Any

class ExchangeAdapter:
    """
    Unified exchange abstraction interface using CCXT.
    Supports Binance, Bybit, OKX, and other CCXT-compatible exchanges.
    """
    def __init__(self, exchange_id: str = 'binance', sandbox: bool = True):
        self.exchange_id = exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        
        # Initialize exchange client with safety defaults
        self.client = exchange_class({
            'apiKey': os.getenv('BINANCE_API_KEY', ''),
            'secret': os.getenv('BINANCE_SECRET_KEY', ''),
            'enableRateLimit': True,
        })
        
        if sandbox and hasattr(self.client, 'set_sandbox_mode'):
            self.client.set_sandbox_mode(True)

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        try:
            return self.client.fetch_ticker(symbol)
        except Exception as e:
            raise ConnectionError(f""Failed to fetch ticker for {symbol}: {str(e)}"")

    def fetch_balance(self) -> Dict[str, Any]:
        try:
            return self.client.fetch_balance()
        except Exception as e:
            raise ConnectionError(f""Failed to fetch account balance: {str(e)}"")
