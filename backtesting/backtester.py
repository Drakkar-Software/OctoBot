from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from backtesting.backtesting_util import start_backtesting_bot, get_standalone_backtesting_bot


class Backtester:

    def __init__(self, config, files=None):
        if files is None:
            files = []
        self.octobot, self.ignored_files = get_standalone_backtesting_bot(config, files)
        self.error = None

    def get_ignored_files(self):
        return self.ignored_files

    def get_is_computing(self):
        if self.error is not None:
            return False
        simulator = self._get_exchange_simulator()
        if simulator:
            return simulator.get_is_initializing() or not simulator.get_backtesting().get_is_finished()
        return False

    def get_progress(self):
        simulator = self._get_exchange_simulator()
        if simulator:
            return simulator.get_progress()
        return 0

    def get_report(self):
        simulator = self._get_exchange_simulator()
        if simulator:
            report = simulator.get_backtesting().get_dict_formatted_report()
            if self.error is not None:
                report["error"] = str(self.error)
            return report
        return {}

    def _get_exchange_simulator(self):
        for exchange in self.octobot.get_exchanges_list().values():
            if isinstance(exchange.get_exchange(), ExchangeSimulator):
                return exchange.get_exchange()

    def start_backtesting(self, in_thread=False):
        self.error = None
        return start_backtesting_bot(self.octobot, in_thread=in_thread, watcher=self)

    def get_bot(self):
        return self.octobot

    def set_error(self, error):
        self.error = error
