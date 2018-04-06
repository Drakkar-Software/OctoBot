from exchanges.trader import Trader


class TraderSimulator(Trader):
    def __init__(self, config, exchange):
        super().__init__(config, exchange)
