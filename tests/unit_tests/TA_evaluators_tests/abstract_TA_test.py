#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from abc import ABCMeta, abstractmethod
import math
from timeit import default_timer as timer

from config import START_PENDING_EVAL_NOTE
from tests.test_utils.config import load_test_config
from tests.test_utils.data_bank import DataBank

"""
Reference class for technical analysis black box testing. Defines tests to implement to test a TA analyser.
"""


class AbstractTATest:
    __metaclass__ = ABCMeta

    async def initialize(self, TA_evaluator_class, data_file=None, test_symbols=None):
        if test_symbols is None:
            test_symbols = ["BTC/USDT"]
        self.evaluator = TA_evaluator_class()
        self.config = load_test_config()
        self.test_symbols = test_symbols
        self.data_bank = DataBank(self.config, data_file, test_symbols)
        await self.data_bank.initialize()
        self._assert_init()
        self.previous_move_stop = None

    # replays a whole dataframe set and assert no exceptions are raised
    @staticmethod
    @abstractmethod
    def test_stress_test(evaluator_tester):
        raise NotImplementedError("stress_test not implemented")

    # checks evaluations when a dump is happening
    @staticmethod
    @abstractmethod
    def test_reactions_to_dump(evaluator_tester):
        raise NotImplementedError("test_reactions_to_dump not implemented")

    # checks evaluations when a pump is happening
    @staticmethod
    @abstractmethod
    def test_reactions_to_pump(evaluator_tester):
        raise NotImplementedError("test_reactions_to_pump not implemented")

    # checks evaluations when an asset is over-sold
    @staticmethod
    @abstractmethod
    def test_reaction_to_rise_after_over_sold(evaluator_tester):
        raise NotImplementedError("test_reaction_to_oversold not implemented")

    # checks evaluations when an asset is over-bought
    @staticmethod
    @abstractmethod
    def test_reaction_to_over_bought_then_dip(evaluator_tester):
        raise NotImplementedError("test_reaction_to_over_bought_then_dip not implemented")

    # checks evaluations when an asset doing nothing
    @staticmethod
    @abstractmethod
    def test_reaction_to_flat_trend(evaluator_tester):
        raise NotImplementedError("test_reaction_to_flat_trend not implemented")

    # runs stress test and assert that neutral evaluation ratio is under required_not_neutral_evaluation_ratio and
    # resets eval_note between each run if reset_eval_to_none_before_each_eval set to True. Also ensure the execution
    # time is bellow or equal to the given limit
    async def run_stress_test_without_exceptions(self,
                                                 required_not_neutral_evaluation_ratio=0.75,
                                                 reset_eval_to_none_before_each_eval=True,
                                                 time_limit_seconds=2):
        start_time = timer()
        for symbol in self.test_symbols:
            time_framed_data_list = self.data_bank.get_all_data_for_all_available_time_frames_for_symbol(symbol)
            for key, current_time_frame_data in time_framed_data_list.items():
                # start with 0 data dataframe and goes onwards the end of the data
                not_neutral_evaluation_count = 0
                for current_time_in_frame in range(30, len(current_time_frame_data[0])):
                    self.evaluator.set_data(DataBank.reduce_data(current_time_frame_data, 0, current_time_in_frame))
                    # self.evaluator.set_data(current_time_frame_data[0:current_time_in_frame])
                    if reset_eval_to_none_before_each_eval:
                        # force None value if possible to make sure eval_note is set during eval_impl()
                        self.evaluator.eval_note = None
                    await self.evaluator.eval_impl()

                    assert self.evaluator.eval_note is not None
                    if self.evaluator.eval_note != START_PENDING_EVAL_NOTE:
                        assert not math.isnan(self.evaluator.eval_note)
                    if self.evaluator.eval_note != START_PENDING_EVAL_NOTE:
                        not_neutral_evaluation_count += 1

                assert not_neutral_evaluation_count / len(current_time_frame_data) \
                    >= required_not_neutral_evaluation_ratio
        process_time = timer() - start_time

        assert process_time <= time_limit_seconds

    # test reaction to dump
    async def run_test_reactions_to_dump(self, pre_dump_eval,
                                         slight_dump_started_eval,
                                         heavy_dump_started_eval,
                                         end_dump_eval,
                                         after_dump_eval):

        dump_data, pre_dump, start_dump, heavy_dump, end_dump = self.data_bank.get_sudden_dump()

        # not dumped yet
        await self._set_data_and_check_eval(DataBank.reduce_data(dump_data, 0, pre_dump), pre_dump_eval, False)

        # starts dumping
        await self._set_data_and_check_eval(DataBank.reduce_data(dump_data, 0, start_dump), slight_dump_started_eval,
                                            True)

        # real dumping
        await self._set_data_and_check_eval(DataBank.reduce_data(dump_data, 0, heavy_dump), heavy_dump_started_eval,
                                            True)

        # end dumping
        await self._set_data_and_check_eval(DataBank.reduce_data(dump_data, 0, end_dump), end_dump_eval, True)

        # stopped dumping
        await self._set_data_and_check_eval(dump_data, after_dump_eval, True)

    # test reaction to pump
    async def run_test_reactions_to_pump(self, pre_pump_eval,
                                         start_pump_started_eval,
                                         heavy_pump_started_eval,
                                         max_pump_eval,
                                         stop_pump_eval,
                                         start_dip_eval,
                                         dipped_eval):

        # not started, started, heavy pump, max pump, change trend, dipping, max: dipped:
        pump_data, pre_pump, start_dump, heavy_pump, max_pump, change_trend, dipping = self.data_bank.get_sudden_pump()

        # not pumped yet
        await self._set_data_and_check_eval(DataBank.reduce_data(pump_data, 0, pre_pump), pre_pump_eval, False)

        # starts pumping
        await self._set_data_and_check_eval(DataBank.reduce_data(pump_data, 0, start_dump), start_pump_started_eval,
                                            False)

        # real pumping
        await self._set_data_and_check_eval(DataBank.reduce_data(pump_data, 0, heavy_pump), heavy_pump_started_eval,
                                            False)

        # max pumping
        await self._set_data_and_check_eval(DataBank.reduce_data(pump_data, 0, max_pump), max_pump_eval, False)

        # trend reversing
        await self._set_data_and_check_eval(DataBank.reduce_data(pump_data, 0, change_trend), stop_pump_eval, True)

        # starts dipping
        await self._set_data_and_check_eval(DataBank.reduce_data(pump_data, 0, dipping), start_dip_eval, True)

        # dipped
        await self._set_data_and_check_eval(pump_data, dipped_eval, True)

    # test reaction to over-sold
    async def run_test_reactions_to_rise_after_over_sold(self, pre_sell_eval,
                                                         started_sell_eval,
                                                         max_sell_eval,
                                                         start_rise_eval,
                                                         after_rise_eval):

        sell_then_buy_data, pre_sell, start_sell, max_sell, start_rise = self.data_bank.get_rise_after_over_sold()

        # not started
        await self._set_data_and_check_eval(DataBank.reduce_data(sell_then_buy_data, 0, pre_sell), pre_sell_eval, False)

        # starts selling
        await self._set_data_and_check_eval(DataBank.reduce_data(sell_then_buy_data, 0, start_sell), started_sell_eval,
                                            True)

        # max selling
        await self._set_data_and_check_eval(DataBank.reduce_data(sell_then_buy_data, 0, max_sell), max_sell_eval, True)

        # start buying
        await self._set_data_and_check_eval(DataBank.reduce_data(sell_then_buy_data, 0, start_rise), start_rise_eval,
                                            True)

        # bought
        await self._set_data_and_check_eval(sell_then_buy_data, after_rise_eval, True)

    # test reaction to over-bought
    async def run_test_reactions_to_over_bought_then_dip(self, pre_buy_eval,
                                                         started_buy_eval,
                                                         max_buy_eval,
                                                         start_dip_eval,
                                                         max_dip_eval,
                                                         after_dip_eval):

        # not started, buying started, buying maxed, start dipping, max dip, max: back normal:
        buy_then_sell_data, pre_buy, start_buy, max_buy, start_dip, max_dip = \
            self.data_bank.get_dip_after_over_bought()

        # not started
        await self._set_data_and_check_eval(DataBank.reduce_data(buy_then_sell_data, 0, pre_buy), pre_buy_eval, False)

        # starts buying
        await self._set_data_and_check_eval(DataBank.reduce_data(buy_then_sell_data, 0, start_buy), started_buy_eval,
                                            False)

        # max buying
        await self._set_data_and_check_eval(DataBank.reduce_data(buy_then_sell_data, 0, max_buy), max_buy_eval, False)

        # start dipping
        await self._set_data_and_check_eval(DataBank.reduce_data(buy_then_sell_data, 0, start_dip), start_dip_eval,
                                            False)

        # max dip
        await self._set_data_and_check_eval(DataBank.reduce_data(buy_then_sell_data, 0, max_dip), max_dip_eval, True)

        # back normal
        await self._set_data_and_check_eval(buy_then_sell_data, after_dip_eval, False)

    # test reaction to flat trend
    async def run_test_reactions_to_flat_trend(self, eval_start_move_ending_up_in_a_rise,
                                               eval_reaches_flat_trend, eval_first_micro_up_p1, eval_first_micro_up_p2,
                                               eval_micro_down1, eval_micro_up1, eval_micro_down2, eval_micro_up2,
                                               eval_micro_down3, eval_back_normal3, eval_micro_down4, eval_back_normal4,
                                               eval_micro_down5, eval_back_up5, eval_micro_up6, eval_back_down6,
                                               eval_back_normal6, eval_micro_down7, eval_back_up7, eval_micro_down8,
                                               eval_back_up8, eval_micro_down9, eval_back_up9):

        # long data_frame with flat then sudden big rise and then mostly flat for 120 values
        # start move ending up in a rise, reaches flat trend, first micro up p1, first mirco up p2, micro down,
        # micro up, micro down, micro up, micro down, back normal, micro down, back normal, micro down, back up,
        # micro up, back down, back normal, micro down, back up, micro down, back up, micro down, back up
        up_then_flat_data, start_move_ending_up_in_a_rise, reaches_flat_trend, first_micro_up_p1, first_micro_up_p2, \
            micro_down1, micro_up1, micro_down2, micro_up2, micro_down3, back_normal3, micro_down4, back_normal4, \
            micro_down5, back_up5, micro_up6, back_down6, back_normal6, micro_down7, back_up7, micro_down8, back_up8, \
            micro_down9, back_up9 = self.data_bank.get_overall_flat_trend()

        # start_move_ending_up_in_a_rise
        await self._set_data_and_check_eval(
            DataBank.reduce_data(up_then_flat_data, 0, start_move_ending_up_in_a_rise),
            eval_start_move_ending_up_in_a_rise, False)
        #  reaches_flat_trend
        await self._move_and_set_data_and_check_eval(up_then_flat_data, reaches_flat_trend, eval_reaches_flat_trend,
                                                     False)
        #  first_micro_up_p1
        await self._move_and_set_data_and_check_eval(up_then_flat_data, first_micro_up_p1, eval_first_micro_up_p1,
                                                     False)
        #  first_micro_up_p2
        await self._move_and_set_data_and_check_eval(up_then_flat_data, first_micro_up_p2, eval_first_micro_up_p2,
                                                     False)
        #  micro_down1
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_down1, eval_micro_down1, True)
        #  micro_up1
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_up1, eval_micro_up1, False)
        #  micro_down2
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_down2, eval_micro_down2, True)
        #  micro_up2
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_up2, eval_micro_up2, False)
        #  micro_down3
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_down3, eval_micro_down3, True)
        #  back_normal3
        await self._move_and_set_data_and_check_eval(up_then_flat_data, back_normal3, eval_back_normal3, False)
        #  micro_down4
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_down4, eval_micro_down4, True)
        #  back_normal4
        await self._move_and_set_data_and_check_eval(up_then_flat_data, back_normal4, eval_back_normal4, False)
        #  micro_down5
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_down5, eval_micro_down5, True)
        #  back_up5
        await self._move_and_set_data_and_check_eval(up_then_flat_data, back_up5, eval_back_up5, False)
        #  micro_up6
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_up6, eval_micro_up6, False)
        #  back_down6
        await self._move_and_set_data_and_check_eval(up_then_flat_data, back_down6, eval_back_down6, True)
        #  back_normal6
        await self._move_and_set_data_and_check_eval(up_then_flat_data, back_normal6, eval_back_normal6, False)
        #  micro_down7
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_down7, eval_micro_down7, True)
        #  back_up7
        await self._move_and_set_data_and_check_eval(up_then_flat_data, back_up7, eval_back_up7, False)
        #  micro_down8
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_down8, eval_micro_down8, True)
        #  back_up8
        await self._move_and_set_data_and_check_eval(up_then_flat_data, back_up8, eval_back_up8, False)
        #  micro_down9
        await self._move_and_set_data_and_check_eval(up_then_flat_data, micro_down9, eval_micro_down9, True)
        #  back_up9
        await self._move_and_set_data_and_check_eval(up_then_flat_data, back_up9, eval_back_up9, False)

    async def _move_and_set_data_and_check_eval(self, data, eval_index, expected_eval_note, check_inferior):
        if self.previous_move_stop is None:
            self.previous_move_stop = 0

        if eval_index > 0:
            # move up to next evaluation
            for i in range(30, eval_index - self.previous_move_stop - 1):
                self.evaluator.set_data(DataBank.reduce_data(data, 0, self.previous_move_stop + i))
                await self.evaluator.eval_impl()

        await self._set_data_and_check_eval(DataBank.reduce_data(data, 0, eval_index), expected_eval_note,
                                            check_inferior)
        self.previous_move_stop = eval_index

    async def _set_data_and_check_eval(self, data, expected_eval_note, check_inferior):
        self.evaluator.set_data(data)
        await self.evaluator.eval_impl()
        if expected_eval_note != -2:
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
