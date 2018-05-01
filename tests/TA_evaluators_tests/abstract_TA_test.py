from abc import *
from pandas import DataFrame
import ccxt

from config.cst import *
from backtesting.exchange_simulator import ExchangeSimulator
from backtesting.collector.data_collector import DataCollectorParser
from tests.test_utils.config import load_test_config


"""
Reference class for technical analysis black box testing. Defines tests to implement to test a TA analyser.
"""


class AbstractTATest:
    __metaclass__ = ABCMeta

    def init(self, TA_evaluator_class, data_file=None):
        self.evaluator = TA_evaluator_class()
        self.config = load_test_config()
        self.exchange_inst = ExchangeSimulator(self.config, ccxt.binance)
        self._init_data(data_file)
        self._assert_init()

    # replays a whole dataframe set and assert no exceptions are raised
    @abstractmethod
    def test_stress_test(self):
        raise NotImplementedError("stress_test not implemented")

    @staticmethod
    def get_full_data(self):
        return self.full_data

    def run_stress_test_without_exceptions(self):
        i=0

    def _init_data(self, data_file):
        data_location = data_file if data_file else self.config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILE]
        self.full_data = DataCollectorParser.parse(data_location)
        self.one_hour_data = self.exchange_inst.get_symbol_prices(
            "BTC",
            TimeFrames.ONE_HOUR,
            data_frame=True)

    def _assert_init(self):
        assert self.evaluator
        assert self.config
        assert self.full_data
        assert self.exchange_inst
        assert type(self.one_hour_data) is DataFrame