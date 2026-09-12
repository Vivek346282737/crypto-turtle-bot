import logging

logger = logging.getLogger(__name__)

class ExecutionEngine:
    def __init__(self, exchange_adapter, dry_run: bool = True):
        self.exchange = exchange_adapter
        self.dry_run = dry_run
        self.processed_signals = set()

    def execute_order(self, signal: dict) -> dict:
        sym = signal.get('symbol', 'UNKNOWN')
        side = signal.get('side', 'BUY')
        ts = signal.get('timestamp', 0)
        signal_id = f'{sym}-{side}-{ts}'

        if signal_id in self.processed_signals:
            logger.warning(f'DUPLICATE PREVENTION: Signal {signal_id} already executed.')
            return {'status': 'REJECTED', 'reason': 'Duplicate signal'}

        if self.dry_run:
            logger.info(f'PAPER/DRY RUN EXECUTION: {side} {sym}')
            self.processed_signals.add(signal_id)
            return {'status': 'FILLED', 'mode': 'PAPER', 'signal_id': signal_id}

        self.processed_signals.add(signal_id)
        return {'status': 'FILLED', 'mode': 'LIVE', 'signal_id': signal_id}
