from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from tools.data_util import DataUtil


class Backtester:

    def __init__(self, octobot):
        self.octobot = octobot

    def get_is_computing(self):
        simulator = self._get_exchange_simulator()
        if simulator:
            return not simulator.get_backtesting().get_is_finished()
        return False

    def get_progress(self):
        simulator = self._get_exchange_simulator()
        if simulator:
            return simulator.get_progress()
        return 0

    def get_report(self):
        simulator = self._get_exchange_simulator()
        if simulator:
            return simulator.get_backtesting().get_dict_formatted_report(self.octobot)
        return {}

    def _get_exchange_simulator(self):
        for exchange in self.octobot.get_exchanges_list().values():
            if isinstance(exchange.get_exchange(), ExchangeSimulator):
                return exchange.get_exchange()