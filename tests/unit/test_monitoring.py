import logging
from trading_bot.monitoring.logger import setup_logger

def test_logger_setup():
    logger = setup_logger('test_bot')
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO
