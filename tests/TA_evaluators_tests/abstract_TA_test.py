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

    def init(self, TA_evaluator_class, data_file=None, test_symbol="BTC"):
        self.evaluator = TA_evaluator_class()
        self.config = load_test_config()
        self.test_symbol = test_symbol
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

    # runs stress test and assert that neutral evaluation ratio is under required_not_neutral_evaluation_ratio and
    # resets eval_note between each run if reset_eval_to_none_before_each_eval set to True
    def run_stress_test_without_exceptions(self,
                                           required_not_neutral_evaluation_ratio=0.75,
                                           reset_eval_to_none_before_each_eval=True):

        time_framed_data_list = self._get_all_data_for_all_available_time_frames()
        for current_time_frame_data in time_framed_data_list:
            # start with 0 data dataframe and goes onwards the end of the data
            not_neutral_evaluation_count = 0
            for current_time_in_frame in range(len(current_time_frame_data)):

                self.evaluator.set_data(current_time_frame_data[0:current_time_in_frame])
                if reset_eval_to_none_before_each_eval:
                    # force None value if possible to make sure eval_note is set during eval_impl()
                    self.evaluator.eval_note = None
                self.evaluator.eval_impl()

                assert self.evaluator.eval_note is not None
                if self.evaluator.eval_note != START_PENDING_EVAL_NOTE:
                    not_neutral_evaluation_count += 1
            assert not_neutral_evaluation_count/len(current_time_frame_data) >= required_not_neutral_evaluation_ratio

    def _get_all_data_for_all_available_time_frames(self):
        return [self.exchange_inst.get_symbol_prices(
            self.test_symbol,
            time_frame,
            data_frame=True) for time_frame in TimeFrames if self.exchange_inst.has_data_for_time_frame(time_frame.value)]

    def _init_data(self, data_file):
        data_location = data_file if data_file else self.config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILE]
        self.full_data = DataCollectorParser.parse(data_location)
        self.one_hour_data = self.exchange_inst.get_symbol_prices(
            self.test_symbol,
            TimeFrames.ONE_HOUR,
            data_frame=True)

    def _assert_init(self):
        assert self.evaluator
        assert self.config
        assert self.full_data
        assert self.exchange_inst
        assert type(self.one_hour_data) is DataFrame
