#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
from abc import ABCMeta, abstractmethod
from math import isnan
from timeit import default_timer as timer
from mock import patch, AsyncMock

import tests.test_utils.config as test_utils_config
from octobot_commons.constants import START_PENDING_EVAL_NOTE
from octobot_commons.enums import TimeFramesMinutes, TimeFrames
from tests.test_utils.data_bank import DataBank


class AbstractTATest:
    """
    Reference class for technical analysis black box testing. Defines tests to implement in order to assess a TA
    evaluator's behaviour.
    """
    __metaclass__ = ABCMeta
    ENOUGH_DATA_STARTING_POINT = 30

    # no __init__ constructor for pytest to be able to collect this class

    async def initialize(self, data_file=None):
        self.time_frame = None
        self.evaluator = self.TA_evaluator_class(test_utils_config.load_test_tentacles_config())
        patch.object(self.evaluator, 'get_exchange_symbol_data', new=self._mocked_get_exchange_symbol_data)
        self.data_bank = DataBank(data_file)
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
                                                 time_limit_seconds=15,
                                                 skip_long_time_frames=False):
        try:
            await self.initialize()
            start_time = timer()
            with patch.object(self.evaluator, 'get_exchange_symbol_data', new=self._mocked_get_exchange_symbol_data), \
                    patch.object(self.evaluator, 'evaluation_completed', new=AsyncMock()):
                for symbol in self.data_bank.data_importer.symbols:
                    self.data_bank.default_symbol = symbol
                    self.data_bank.standard_mode(self.ENOUGH_DATA_STARTING_POINT)
                    for time_frame, current_time_frame_data in self.data_bank.origin_ohlcv_by_symbol[symbol].items():
                        if TimeFramesMinutes[time_frame] > TimeFramesMinutes[TimeFrames.THREE_DAYS] and \
                                skip_long_time_frames:
                            continue
                        self.time_frame = time_frame
                        # start with 0 data data frame and goes onwards until the end of the data
                        not_neutral_evaluation_count = 0
                        total_candles_count = len(current_time_frame_data)
                        start_point = self.ENOUGH_DATA_STARTING_POINT + 1
                        if total_candles_count > start_point:
                            for _ in range(start_point, total_candles_count):
                                if reset_eval_to_none_before_each_eval:
                                    # force None value if possible to make sure eval_note is set during eval_impl()
                                    self.evaluator.eval_note = None
                                await self._increment_bank_data_and_call_evaluator()

                                assert self.evaluator.eval_note is not None
                                if self.evaluator.eval_note != START_PENDING_EVAL_NOTE:
                                    assert not isnan(self.evaluator.eval_note)
                                if self.evaluator.eval_note != START_PENDING_EVAL_NOTE:
                                    not_neutral_evaluation_count += 1

                            assert not_neutral_evaluation_count / (total_candles_count - start_point) >= \
                                required_not_neutral_evaluation_ratio
            process_time = timer() - start_time
            assert process_time <= time_limit_seconds
        finally:
            await self.data_bank.stop()

    # test reaction to dump
    async def run_test_reactions_to_dump(self, pre_dump_eval,
                                         slight_dump_started_eval,
                                         heavy_dump_started_eval,
                                         end_dump_eval,
                                         after_dump_eval):
        try:
            await self.initialize()

            self.time_frame, pre_dump, start_dump, heavy_dump, end_dump, stopped_dump = \
                self.data_bank.sudden_dump_mode()

            with patch.object(self.evaluator, 'get_exchange_symbol_data', new=self._mocked_get_exchange_symbol_data), \
                    patch.object(self.evaluator, 'evaluation_completed', new=AsyncMock()):
                # not dumped yet
                await self._set_data_and_check_eval(pre_dump, pre_dump_eval, False)

                # starts dumping
                await self._set_data_and_check_eval(start_dump, slight_dump_started_eval, True)

                # real dumping
                await self._set_data_and_check_eval(heavy_dump, heavy_dump_started_eval, True)

                # end dumping
                await self._set_data_and_check_eval(end_dump, end_dump_eval, True)

                # stopped dumping
                await self._set_data_and_check_eval(stopped_dump, after_dump_eval, True)
        finally:
            await self.data_bank.stop()

    # test reaction to pump
    async def run_test_reactions_to_pump(self, pre_pump_eval,
                                         start_pump_started_eval,
                                         heavy_pump_started_eval,
                                         max_pump_eval,
                                         stop_pump_eval,
                                         start_dip_eval,
                                         dipped_eval):
        try:
            await self.initialize()

            # not started, started, heavy pump, max pump, change trend, dipping, max: dipped:
            self.time_frame, pre_pump, start_dump, heavy_pump, max_pump, change_trend, dipping, dipped = \
                self.data_bank.sudden_pump_mode()

            with patch.object(self.evaluator, 'get_exchange_symbol_data', new=self._mocked_get_exchange_symbol_data), \
                    patch.object(self.evaluator, 'evaluation_completed', new=AsyncMock()):
                # not pumped yet
                await self._set_data_and_check_eval(pre_pump, pre_pump_eval, False)

                # starts pumping
                await self._set_data_and_check_eval(start_dump, start_pump_started_eval, False)

                # real pumping
                await self._set_data_and_check_eval(heavy_pump, heavy_pump_started_eval, False)

                # max pumping
                await self._set_data_and_check_eval(max_pump, max_pump_eval, False)

                # trend reversing
                await self._set_data_and_check_eval(change_trend, stop_pump_eval, True)

                # starts dipping
                await self._set_data_and_check_eval(dipping, start_dip_eval, True)

                # dipped
                await self._set_data_and_check_eval(dipped, dipped_eval, True)
        finally:
            await self.data_bank.stop()

    # test reaction to over-sold
    async def run_test_reactions_to_rise_after_over_sold(self, pre_sell_eval,
                                                         started_sell_eval,
                                                         max_sell_eval,
                                                         start_rise_eval,
                                                         after_rise_eval):
        try:
            await self.initialize()

            self.time_frame, pre_sell, start_sell, max_sell, start_rise, bought = \
                self.data_bank.rise_after_over_sold_mode()

            with patch.object(self.evaluator, 'get_exchange_symbol_data', new=self._mocked_get_exchange_symbol_data), \
                    patch.object(self.evaluator, 'evaluation_completed', new=AsyncMock()):
                # not started
                await self._set_data_and_check_eval(pre_sell, pre_sell_eval, False)

                # starts selling
                await self._set_data_and_check_eval(start_sell, started_sell_eval, True)

                # max selling
                await self._set_data_and_check_eval(max_sell, max_sell_eval, True)

                # start buying
                await self._set_data_and_check_eval(start_rise, start_rise_eval, True)

                # bought
                await self._set_data_and_check_eval(bought, after_rise_eval, True)
        finally:
            await self.data_bank.stop()

    # test reaction to over-bought
    async def run_test_reactions_to_over_bought_then_dip(self, pre_buy_eval,
                                                         started_buy_eval,
                                                         max_buy_eval,
                                                         start_dip_eval,
                                                         max_dip_eval,
                                                         after_dip_eval):
        try:
            await self.initialize()

            with patch.object(self.evaluator, 'get_exchange_symbol_data', new=self._mocked_get_exchange_symbol_data), \
                    patch.object(self.evaluator, 'evaluation_completed', new=AsyncMock()):
                # not started, buying started, buying maxed, start dipping, max dip, max: back normal:
                self.time_frame, pre_buy, start_buy, max_buy, start_dip, max_dip, normal = \
                    self.data_bank.dip_after_over_bought_mode()

                # not started
                await self._set_data_and_check_eval(pre_buy, pre_buy_eval, False)

                # starts buying
                await self._set_data_and_check_eval(start_buy, started_buy_eval, False)

                # max buying
                await self._set_data_and_check_eval(max_buy, max_buy_eval, False)

                # start dipping
                await self._set_data_and_check_eval(start_dip, start_dip_eval, False)

                # max dip
                await self._set_data_and_check_eval(max_dip, max_dip_eval, True)

                # back normal
                await self._set_data_and_check_eval(normal, after_dip_eval, False)
        finally:
            await self.data_bank.stop()

    # test reaction to flat trend
    async def run_test_reactions_to_flat_trend(self, eval_start_move_ending_up_in_a_rise,
                                               eval_reaches_flat_trend, eval_first_micro_up_p1, eval_first_micro_up_p2,
                                               eval_micro_down1, eval_micro_up1, eval_micro_down2, eval_micro_up2,
                                               eval_micro_down3, eval_back_normal3, eval_micro_down4, eval_back_normal4,
                                               eval_micro_down5, eval_back_up5, eval_micro_up6, eval_back_down6,
                                               eval_back_normal6, eval_micro_down7, eval_back_up7, eval_micro_down8,
                                               eval_back_up8, eval_micro_down9, eval_back_up9):
        try:
            await self.initialize()

            # long data_frame with flat then sudden big rise and then mostly flat for 120 values
            # start move ending up in a rise, reaches flat trend, first micro up p1, first mirco up p2, micro down,
            # micro up, micro down, micro up, micro down, back normal, micro down, back normal, micro down, back up,
            # micro up, back down, back normal, micro down, back up, micro down, back up, micro down, back up
            self.time_frame, start_move_ending_up_in_a_rise, reaches_flat_trend, first_micro_up_p1, \
                first_micro_up_p2, micro_down1, micro_up1, micro_down2, micro_up2, micro_down3, back_normal3, \
                micro_down4, back_normal4, micro_down5, back_up5, micro_up6, back_down6, back_normal6, micro_down7, \
                back_up7, micro_down8, back_up8, micro_down9, back_up9 = self.data_bank.overall_flat_trend_mode()

            with patch.object(self.evaluator, 'get_exchange_symbol_data', new=self._mocked_get_exchange_symbol_data), \
                    patch.object(self.evaluator, 'evaluation_completed', new=AsyncMock()):
                # start_move_ending_up_in_a_rise
                await self._set_data_and_check_eval(start_move_ending_up_in_a_rise, eval_start_move_ending_up_in_a_rise,
                                                    False)
                #  reaches_flat_trend
                await self._move_and_set_data_and_check_eval(reaches_flat_trend, eval_reaches_flat_trend, False)
                #  first_micro_up_p1
                await self._move_and_set_data_and_check_eval(first_micro_up_p1, eval_first_micro_up_p1, False)
                #  first_micro_up_p2
                await self._move_and_set_data_and_check_eval(first_micro_up_p2, eval_first_micro_up_p2, False)
                #  micro_down1
                await self._move_and_set_data_and_check_eval(micro_down1, eval_micro_down1, True)
                #  micro_up1
                await self._move_and_set_data_and_check_eval(micro_up1, eval_micro_up1, False)
                #  micro_down2
                await self._move_and_set_data_and_check_eval(micro_down2, eval_micro_down2, True)
                #  micro_up2
                await self._move_and_set_data_and_check_eval(micro_up2, eval_micro_up2, False)
                #  micro_down3
                await self._move_and_set_data_and_check_eval(micro_down3, eval_micro_down3, True)
                #  back_normal3
                await self._move_and_set_data_and_check_eval(back_normal3, eval_back_normal3, False)
                #  micro_down4
                await self._move_and_set_data_and_check_eval(micro_down4, eval_micro_down4, True)
                #  back_normal4
                await self._move_and_set_data_and_check_eval(back_normal4, eval_back_normal4, False)
                #  micro_down5
                await self._move_and_set_data_and_check_eval(micro_down5, eval_micro_down5, True)
                #  back_up5
                await self._move_and_set_data_and_check_eval(back_up5, eval_back_up5, False)
                #  micro_up6
                await self._move_and_set_data_and_check_eval(micro_up6, eval_micro_up6, False)
                #  back_down6
                await self._move_and_set_data_and_check_eval(back_down6, eval_back_down6, True)
                #  back_normal6
                await self._move_and_set_data_and_check_eval(back_normal6, eval_back_normal6, False)
                #  micro_down7
                await self._move_and_set_data_and_check_eval(micro_down7, eval_micro_down7, True)
                #  back_up7
                await self._move_and_set_data_and_check_eval(back_up7, eval_back_up7, False)
                #  micro_down8
                await self._move_and_set_data_and_check_eval(micro_down8, eval_micro_down8, True)
                #  back_up8
                await self._move_and_set_data_and_check_eval(back_up8, eval_back_up8, False)
                #  micro_down9
                await self._move_and_set_data_and_check_eval(micro_down9, eval_micro_down9, True)
                #  back_up9
                await self._move_and_set_data_and_check_eval(back_up9, eval_back_up9, False)
        finally:
            await self.data_bank.stop()

    def _mocked_get_exchange_symbol_data(self, exchange, exchange_id, symbol):
        return self.data_bank.symbol_data

    async def _call_evaluator(self):
        last_candle = self.data_bank.get_last_candle_for_default_symbol(self.time_frame)
        await self.evaluator.evaluator_ohlcv_callback(self.data_bank.exchange_name,
                                                      "0a",
                                                      "Bitcoin",
                                                      self.data_bank.default_symbol,
                                                      self.time_frame.value,
                                                      last_candle)

    async def _set_bank_data_and_call_evaluator(self, end_index):
        self.data_bank.set_data_for_default_symbol(self.time_frame, end_index)
        await self._call_evaluator()

    async def _increment_bank_data_and_call_evaluator(self):
        self.data_bank.increment_data_for_default_symbol(self.time_frame)
        await self._call_evaluator()

    async def _move_and_set_data_and_check_eval(self, eval_index, expected_eval_note, check_inferior):
        if self.previous_move_stop is None:
            self.previous_move_stop = 0

        if eval_index > 0:
            # move up to next evaluation
            for i in range(30, eval_index - self.previous_move_stop - 1):
                await self._set_bank_data_and_call_evaluator(self.previous_move_stop + i)

        await self._set_data_and_check_eval(eval_index, expected_eval_note, check_inferior)
        self.previous_move_stop = eval_index

    async def _set_data_and_check_eval(self, end_index, expected_eval_note, check_inferior):
        await self._set_bank_data_and_call_evaluator(end_index)
        if expected_eval_note != -2:
            if check_inferior:
                assert self.evaluator.eval_note == expected_eval_note or self.evaluator.eval_note <= expected_eval_note
            else:
                assert self.evaluator.eval_note == expected_eval_note or self.evaluator.eval_note >= expected_eval_note

    def _assert_init(self):
        assert self.evaluator
        assert self.data_bank
