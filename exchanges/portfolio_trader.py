import logging


class PortfolioTrader:
    def __init__(self, config, exchange):
        self.exchange = exchange
        self.config = config
        self.risk = self.config["trader"]["risk"]
        self.logger = logging.getLogger("PortfolioTrader")

        # Debug
        if self.enabled():
            self.logger.debug("Enabled on " + self.exchange.get_name())
        else:
            self.logger.debug("Disabled on " + self.exchange.get_name())

    def enabled(self):
        if self.config["trader"]["enabled"]:
            return True
        else:
            return False

    def get_risk(self):
        return self.risk

    def create_order(self, order_type):
        pass
