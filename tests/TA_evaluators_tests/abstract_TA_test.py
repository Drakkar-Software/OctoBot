from abc import *
import math

from config.cst import *
from tests.test_utils.config import load_test_config
from tests.test_utils.data_bank import DataBank

"""
Reference class for technical analysis black box testing. Defines tests to implement to test a TA analyser.
"""


class AbstractTATest:
    __metaclass__ = ABCMeta

    def init(self, TA_evaluator_class, data_file=None, test_symbols=["BTC"]):
        self.evaluator = TA_evaluator_class()
        self.config = load_test_config()
        self.test_symbols = test_symbols
        self.data_bank = DataBank(self.config, data_file, test_symbols)
        self._assert_init()

    @abstractmethod
    def init_test_with_evaluator_to_test(self):
        raise NotImplementedError("init_test_with_evaluator_to_test not implemented")

    # replays a whole dataframe set and assert no exceptions are raised
    @abstractmethod
    def test_stress_test(self):
        raise NotImplementedError("stress_test not implemented")

    # checks evaluations when a dump is happening
    @abstractmethod
    def test_reactions_to_dump(self):
        raise NotImplementedError("test_reactions_to_dump not implemented")

    # checks evaluations when a pump is happening
    @abstractmethod
    def test_reactions_to_pump(self):
        raise NotImplementedError("test_reactions_to_pump not implemented")

    # checks evaluations when an asset is over-sold
    @abstractmethod
    def test_reaction_to_rise_after_over_sold(self):
        raise NotImplementedError("test_reaction_to_oversold not implemented")

    # checks evaluations when an asset is over-sold
    @abstractmethod
    def test_reaction_to_over_bought_then_dip(self):
        raise NotImplementedError("test_reaction_to_over_bought_then_dip not implemented")

    # runs stress test and assert that neutral evaluation ratio is under required_not_neutral_evaluation_ratio and
    # resets eval_note between each run if reset_eval_to_none_before_each_eval set to True
    def run_stress_test_without_exceptions(self,
                                           required_not_neutral_evaluation_ratio=0.75,
                                           reset_eval_to_none_before_each_eval=True):

        for symbol in self.test_symbols:
            time_framed_data_list = self.data_bank.get_all_data_for_all_available_time_frames_for_symbol(symbol)
            for key, current_time_frame_data in time_framed_data_list.items():
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
                        assert not math.isnan(self.evaluator.eval_note)
                    if self.evaluator.eval_note != START_PENDING_EVAL_NOTE:
                        not_neutral_evaluation_count += 1
                assert not_neutral_evaluation_count/len(current_time_frame_data) \
                    >= required_not_neutral_evaluation_ratio

    # test reaction to dump
    def run_test_reactions_to_dump(self, pre_dump_eval,
                                   slight_dump_started_eval,
                                   heavy_dump_started_eval,
                                   end_dump_eval,
                                   after_dump_eval):

        dump_data, pre_dump, start_dump, heavy_dump, end_dump = self.data_bank.get_sudden_dump()

        # not dumped yet
        self._set_data_and_check_eval(dump_data[0:pre_dump], pre_dump_eval, False)

        # starts dumping
        self._set_data_and_check_eval(dump_data[0:start_dump], slight_dump_started_eval, True)

        # real dumping
        self._set_data_and_check_eval(dump_data[0:heavy_dump], heavy_dump_started_eval, True)

        # end dumping
        self._set_data_and_check_eval(dump_data[0:end_dump], end_dump_eval, True)

        # stopped dumping
        self._set_data_and_check_eval(dump_data, after_dump_eval, True)

    # test reaction to pump
    def run_test_reactions_to_pump(self, pre_pump_eval,
                                   start_pump_started_eval,
                                   heavy_pump_started_eval,
                                   max_pump_eval,
                                   stop_pump_eval,
                                   start_dip_eval,
                                   dipped_eval):

        # not started, started, heavy pump, max pump, change trend, dipping, max: dipped:
        pump_data, pre_pump, start_dump, heavy_pump, max_pump, change_trend, dipping = self.data_bank.get_sudden_pump()

        # not pumped yet
        self._set_data_and_check_eval(pump_data[0:pre_pump], pre_pump_eval, False)

        # starts pumping
        self._set_data_and_check_eval(pump_data[0:start_dump], start_pump_started_eval, False)

        # real pumping
        self._set_data_and_check_eval(pump_data[0:heavy_pump], heavy_pump_started_eval, False)

        # max pumping
        self._set_data_and_check_eval(pump_data[0:max_pump], max_pump_eval, False)

        # trend reversing
        self._set_data_and_check_eval(pump_data[0:change_trend], stop_pump_eval, True)

        # starts dipping
        self._set_data_and_check_eval(pump_data[0:dipping], start_dip_eval, True)

        # dipped
        self._set_data_and_check_eval(pump_data, dipped_eval, True)

    # test reaction to over-sold
    def run_test_reactions_to_rise_after_over_sold(self, pre_sell_eval,
                                                   started_sell_eval,
                                                   max_sell_eval,
                                                   start_rise_eval,
                                                   after_rise_eval):

        sell_then_buy_data, pre_sell, start_sell, max_sell, start_rise = self.data_bank.get_rise_after_over_sold()

        # not started
        self._set_data_and_check_eval(sell_then_buy_data[0:pre_sell], pre_sell_eval, False)

        # starts selling
        self._set_data_and_check_eval(sell_then_buy_data[0:start_sell], started_sell_eval, True)

        # max selling
        self._set_data_and_check_eval(sell_then_buy_data[0:max_sell], max_sell_eval, True)

        # start buying
        self._set_data_and_check_eval(sell_then_buy_data[0:start_rise], start_rise_eval, True)

        # bought
        self._set_data_and_check_eval(sell_then_buy_data, after_rise_eval, True)

    # test reaction to over-bought
    def run_test_reactions_to_over_bought_then_dip(self, pre_buy_eval,
                                                   started_buy_eval,
                                                   max_buy_eval,
                                                   start_dip_eval,
                                                   max_dip_eval,
                                                   after_dip_eval):

        # not started, buying started, buying maxed, start dipping, max dip, max: back normal:
        buy_then_sell_data, pre_buy, start_buy, max_buy, start_dip, max_dip = \
            self.data_bank.get_dip_after_over_bought()

        # not started
        self._set_data_and_check_eval(buy_then_sell_data[0:pre_buy], pre_buy_eval, False)

        # starts buying
        self._set_data_and_check_eval(buy_then_sell_data[0:start_buy], started_buy_eval, False)

        # max buying
        self._set_data_and_check_eval(buy_then_sell_data[0:max_buy], max_buy_eval, False)

        # start dipping
        self._set_data_and_check_eval(buy_then_sell_data[0:start_dip], start_dip_eval, False)

        # max dip
        self._set_data_and_check_eval(buy_then_sell_data[0:max_dip], max_dip_eval, True)

        # back normal
        self._set_data_and_check_eval(buy_then_sell_data, after_dip_eval, False)

    def _set_data_and_check_eval(self, data, expected_eval_note, check_inferior):
        self.evaluator.set_data(data)
        self.evaluator.eval_impl()
        if check_inferior:
            assert self.evaluator.eval_note == expected_eval_note \
                or self.evaluator.eval_note <= expected_eval_note
        else:
            assert self.evaluator.eval_note == expected_eval_note \
                or self.evaluator.eval_note >= expected_eval_note

    def _assert_init(self):
        assert self.evaluator
        assert self.config
        assert self.data_bank
