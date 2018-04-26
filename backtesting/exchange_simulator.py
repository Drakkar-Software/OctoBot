from trading import Exchange


class ExchangeSimulator(Exchange):
    def __init__(self, config, exchange_type):
        super().__init__(config, exchange_type)

