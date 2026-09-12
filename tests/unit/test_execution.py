import pytest
from trading_bot.execution.engine import ExecutionEngine

class DummyExchange:
    pass

def test_execution_idempotency_and_duplicate_prevention():
    adapter = DummyExchange()
    engine = ExecutionEngine(exchange_adapter=adapter, dry_run=True)
    
    signal = {'symbol': 'BTC/USDT', 'side': 'BUY', 'timestamp': 1700000000}
    
    # First execution should succeed
    result1 = engine.execute_order(signal)
    assert result1['status'] == 'FILLED'

    # Second identical execution should be rejected to prevent double orders
    result2 = engine.execute_order(signal)
    assert result2['status'] == 'REJECTED'
    assert result2['reason'] == 'Duplicate signal'
