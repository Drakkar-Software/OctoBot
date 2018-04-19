class TradesManager:
    def __init__(self, trader):
        self.trader = trader
        self.portfolio = trader.get_portfolio()
        self.exchange = trader.get_exchange()
        self.trades = []

    def add_new_trade(self, trade):
        if trade not in self.trades:
            self.trades.append(trade)

    def get_profitability(self):
        pass
