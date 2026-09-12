import pytest
import pandas as pd
import numpy as np
from trading_bot.risk.risk_engine import RiskEngine
from trading_bot.execution.engine import ExecutionEngine
from trading_bot.exchange.adapter import ExchangeAdapter
from trading_bot.regime.detector import RegimeDetector

def test_risk_engine_max_drawdown_breach():
    engine = RiskEngine(max_risk_per_trade_pct=0.01, max_daily_drawdown_pct=0.03)
    signal = {'side': 'BUY', 'symbol': 'BTC/USDT'}
    # Drawdown 3.5% exceeds 3.0% limit -> must reject
    approved = engine.evaluate_signal(signal, account_equity=10000.0, current_daily_drawdown=0.035)
    assert approved is False

def test_invalid_ohlcv_and_stale_data():
    detector = RegimeDetector(window=20)
    # Insufficient data length should return 'UNKNOWN' instead of crashing
    short_closes = pd.Series([100, 101, 102])
    assert detector.detect(short_closes) == 'UNKNOWN'

def test_execution_idempotency_retry():
    class DummyClient:
        pass
    engine = ExecutionEngine(exchange_adapter=DummyClient(), dry_run=True)
    signal = {'symbol': 'ETH/USDT', 'side': 'BUY', 'timestamp': 1700000000}
    
    res1 = engine.execute_order(signal)
    assert res1['status'] == 'FILLED'
    
    # Duplicate signal submission should be rejected
    res2 = engine.execute_order(signal)
    assert res2['status'] == 'REJECTED'
    assert res2['reason'] == 'Duplicate signal'

def test_invalid_configuration_handling():
    with pytest.raises(Exception):
        _ = ExchangeAdapter(exchange_id='non_existent_exchange_id_12345', sandbox=True)
