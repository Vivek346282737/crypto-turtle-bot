import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
secret_key = os.getenv("BINANCE_SECRET_KEY")

exchange = ccxt.binance({
    "apiKey": api_key,
    "secret": secret_key,
    "enableRateLimit": True,
    "options": {"defaultType": "spot"}
})

try:
    balance = exchange.fetch_balance()
    usdt_free = balance['free'].get('USDT', 0)
    print("==================================================")
    print(">>> BINANCE API HANDSHAKE SUCCESSFUL!")
    print(f">>> Available Spot USDT Balance: ${usdt_free}")
    print("==================================================")
except Exception as e:
    print("Connection Failed:", e)
