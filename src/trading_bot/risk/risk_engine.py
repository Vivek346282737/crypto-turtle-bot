import logging

logger = logging.getLogger(__name__)

class RiskEngine:
    def __init__(self, max_risk_per_trade_pct: float = 0.01, max_daily_drawdown_pct: float = 0.03):
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.max_daily_drawdown_pct = max_daily_drawdown_pct

    def evaluate_signal(self, signal: dict, account_equity: float, current_daily_drawdown: float) -> bool:
        if current_daily_drawdown >= self.max_daily_drawdown_pct:
            logger.warning(f'RISK REJECTION: Daily drawdown ({current_daily_drawdown:.2%}) breached limit ({self.max_daily_drawdown_pct:.2%}).')
            return False

        side = signal.get('side')
        if side not in ['BUY', 'SELL']:
            logger.warning(f'RISK REJECTION: Invalid signal side {side}.')
            return False

        logger.info('RISK APPROVAL: Signal passed all safety checks.')
        return True
