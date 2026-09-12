import pytest
from trading_bot.risk.risk_engine import RiskEngine

def test_risk_engine_approval():
    engine = RiskEngine(max_risk_per_trade_pct=0.01, max_daily_drawdown_pct=0.03)
    signal = {'side': 'BUY', 'symbol': 'BTC/USDT'}
    
    # 1% drawdown is well below 3% limit -> should be approved
    approved = engine.evaluate_signal(signal, account_equity=10000.0, current_daily_drawdown=0.01)
    assert approved == True

def test_risk_engine_rejection_due_to_drawdown():
    engine = RiskEngine(max_risk_per_trade_pct=0.01, max_daily_drawdown_pct=0.03)
    signal = {'side': 'BUY', 'symbol': 'BTC/USDT'}
    
    # 4% drawdown exceeds 3% limit -> should be rejected
    approved = engine.evaluate_signal(signal, account_equity=10000.0, current_daily_drawdown=0.04)
    assert approved == False
