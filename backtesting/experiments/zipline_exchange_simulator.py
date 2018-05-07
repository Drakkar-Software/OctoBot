from backtesting.exchange_simulator import ExchangeSimulator


class ZiplineExchangeSimulator(ExchangeSimulator):
    def __init__(self, config, exchange_type):
        super().__init__(config, exchange_type)
