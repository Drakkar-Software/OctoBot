#  Drakkar-Software OctoBot-Evaluators
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
import async_channel.constants as channel_constants

import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.channels_name as channels_name
import octobot_commons.tree as commons_tree

import octobot_evaluators.constants as constants
import octobot_evaluators.evaluators as evaluator


class TAEvaluator(evaluator.AbstractEvaluator):
    __metaclass__ = evaluator.AbstractEvaluator
    DEFAULT_LIVE_PRICE_INIT_TIMEOUT = 5 * common_constants.MINUTE_TO_SECONDS

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.time_frame = None

        # True when this evaluator is only triggered on closed candles
        self.is_triggered_after_candle_close = True

        self._price_init_timeout = self.DEFAULT_LIVE_PRICE_INIT_TIMEOUT

    async def start(self, bot_id: str) -> bool:
        """
        Default TA start: to be overwritten
        Subscribe to OHLCV notification from self.symbols and self.time_frames
        :return: success of the evaluator's start
        """
        await super().start(bot_id)
        try:
            import octobot_trading.exchange_channel as exchanges_channel
            import octobot_trading.api as exchange_api
            exchange_id = exchange_api.get_exchange_id_from_matrix_id(self.exchange_name, self.matrix_id)
            time_frame_filter = [tf.value
                                 for tf in exchange_api.get_exchange_available_required_time_frames(
                                    self.exchange_name, exchange_id)]
            if len(time_frame_filter) == 1:
                time_frame_filter = time_frame_filter[0]
            await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.OHLCV_CHANNEL.value, exchange_id).\
                new_consumer(
                    self.evaluator_ohlcv_callback,
                    cryptocurrency=self.cryptocurrency if self.cryptocurrency else channel_constants.CHANNEL_WILDCARD,
                    symbol=self.symbol if self.symbol else channel_constants.CHANNEL_WILDCARD,
                    time_frame=self.time_frame.value if self.time_frame else time_frame_filter,
                    priority_level=self.priority_level,
            )
            if exchange_api.get_is_backtesting(
                    exchange_api.get_exchange_manager_from_exchange_name_and_id(self.exchange_name, exchange_id)
            ):
                self.use_backtesting_init_timeout()
            return True
        except ImportError as e:
            self.logger.error(f"Can't connect to OHLCV trading channel {e}")
        return False

    def use_backtesting_init_timeout(self):
        self._price_init_timeout = 0

    async def reset_evaluation(self, cryptocurrency, symbol, time_frame):
        self.eval_note = common_constants.START_PENDING_EVAL_NOTE
        await self.evaluation_completed(cryptocurrency, symbol, time_frame, eval_time=0, notify=False)

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        # To be used to trigger an evaluation when a new candle in closed or a re-evaluation is required
        pass

    async def evaluator_ohlcv_callback(self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str,
                                       time_frame: str, candle: dict):
        if not self.get_is_symbol_wildcard():
            # do not wait for price in symbol wildcard or it will prevent evaluations for all
            # symbols waiting in this consumer queue
            await commons_tree.EventProvider.instance().wait_for_event(
                self.bot_id,
                commons_tree.get_exchange_path(
                    exchange,
                    common_enums.InitializationEventExchangeTopics.PRICE.value,
                    symbol=symbol,
                ),
                self._price_init_timeout
            )
        await self.ohlcv_callback(exchange, exchange_id, cryptocurrency, symbol, time_frame, candle, False)

    async def evaluators_callback(self,
                                  matrix_id,
                                  evaluator_name,
                                  evaluator_type,
                                  exchange_name,
                                  cryptocurrency,
                                  symbol,
                                  time_frame,
                                  data):
        # Used to communicate between evaluators
        # ignore time frames related to other instances if case of a non time frame wildcard evaluator
        time_frames_to_update = data.get(constants.EVALUATOR_CHANNEL_DATA_TIME_FRAMES, []) \
            if self.get_is_time_frame_wildcard() else \
            [self.time_frame] if self.time_frame in data.get(constants.EVALUATOR_CHANNEL_DATA_TIME_FRAMES, []) else []
        if not self.enable_reevaluation():
            self.logger.debug(f"Ignoring re-evaluation ({data[constants.EVALUATOR_CHANNEL_DATA_ACTION]}) "
                              f"for {symbol}/{time_frame} on {exchange_name}: enable_reevaluation() is False")
            return
        # re-evaluation processes
        if data[constants.EVALUATOR_CHANNEL_DATA_ACTION] == constants.TA_RE_EVALUATION_TRIGGER_UPDATED_DATA:
            try:
                import octobot_trading.api as exchange_api
                exchange_id = data[constants.EVALUATOR_CHANNEL_DATA_EXCHANGE_ID]
                symbol_data = self.get_exchange_symbol_data(exchange_name, exchange_id, symbol)
                for time_frame in time_frames_to_update:
                    candles_data = exchange_api.get_symbol_historical_candles(symbol_data, time_frame, limit=1)
                    # do not trigger ohlcv_callback on empty candles data
                    if all(values for values in candles_data.values()):
                        last_full_candle = exchange_api.get_candle_as_list(candles_data)
                        await self.ohlcv_callback(exchange_name, exchange_id, cryptocurrency,
                                                  symbol, time_frame.value, last_full_candle, True)
            except KeyError:
                self.logger.debug(
                    f"Ignored re-evaluation trigger for {symbol} on {exchange_name}: missing {time_frame} data"
                )
            except ImportError:
                self.logger.error(f"Can't get OHLCV: requires OctoBot-Trading package installed")
        elif data[constants.EVALUATOR_CHANNEL_DATA_ACTION] == constants.RESET_EVALUATION:
            for time_frame in time_frames_to_update:
                await self.reset_evaluation(cryptocurrency, symbol, time_frame.value)
