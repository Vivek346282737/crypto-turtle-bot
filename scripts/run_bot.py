import os
from dotenv import load_dotenv
from trading_bot.monitoring.logger import setup_logger
from trading_bot.exchange.adapter import ExchangeAdapter

load_dotenv()
logger = setup_logger('production_bot')

def main():
    mode = os.getenv('TRADING_MODE', 'paper')
    logger.info(f'Starting Crypto Turtle Bot in {mode.upper()} mode...')
    exchange = ExchangeAdapter(exchange_id='binance', sandbox=True)
    logger.info('Exchange adapter initialized successfully.')

if __name__ == '__main__':
    main()
