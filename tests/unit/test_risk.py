import pytest

def test_daily_kill_switch_logic():
    starting_balance = 10000.0
    current_balance = 9650.0  # 3.5% loss (exceeds 3% limit)
    max_allowed_drawdown_pct = 0.03
    
    drawdown = (starting_balance - current_balance) / starting_balance
    kill_switch_triggered = drawdown >= max_allowed_drawdown_pct
    
    assert kill_switch_triggered == True
