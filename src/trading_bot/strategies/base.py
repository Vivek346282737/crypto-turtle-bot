class BaseStrategy:
    def generate_signal(self, *args, **kwargs):
        raise NotImplementedError('Strategy must implement generate_signal')
