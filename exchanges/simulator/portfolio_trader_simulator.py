from exchanges.portfolio_trader import PortfolioTrader


class PortfolioTraderSimulator(PortfolioTrader):
    def __init__(self, config, exchange):
        super().__init__(config, exchange)
