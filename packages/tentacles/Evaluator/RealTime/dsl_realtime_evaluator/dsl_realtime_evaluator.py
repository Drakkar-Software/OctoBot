#  Drakkar-Software OctoBot-Tentacles
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
import asyncio
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.channels_name as channels_name
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.util as evaluators_util
import octobot_trading.exchange_channel as exchange_channels
import octobot_trading.api as trading_api

import tentacles.Meta.DSL_operators as dsl_operators


TRIGGER_CHANNEL_OHLCV = "ohlcv"
TRIGGER_CHANNEL_KLINE = "kline"
TRIGGER_CHANNEL_TICKER = "ticker"
TRIGGER_CHANNEL_ALL_TICKERS = "all_tickers"

ALL_TICKERS_DEFAULT_REFRESH_TIME = 64
ALL_TICKERS_REFRESH_TIME_KEY = "all_tickers_refresh_time"

TRIGGER_CHANNEL_TO_EXCHANGE_CHANNEL = {
    TRIGGER_CHANNEL_OHLCV: channels_name.OctoBotTradingChannelsName.OHLCV_CHANNEL.value,
    TRIGGER_CHANNEL_KLINE: channels_name.OctoBotTradingChannelsName.KLINE_CHANNEL.value,
    TRIGGER_CHANNEL_TICKER: channels_name.OctoBotTradingChannelsName.TICKER_CHANNEL.value,
}


class DSLRealtimeEvaluator(evaluators.RealTimeEvaluator):
    TRIGGER_CHANNEL_KEY = "trigger_channel"
    DSL_SCRIPT_KEY = "dsl_script"

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.trigger_channel: str = TRIGGER_CHANNEL_OHLCV
        self.dsl_script: str = ""
        self.interpreter: typing.Optional[dsl_interpreter.Interpreter] = None
        self.exchange_manager = None
        self.triggered_symbol: str = ""
        self.all_tickers_refresh_time: float = ALL_TICKERS_DEFAULT_REFRESH_TIME
        self._all_tickers_task: typing.Optional[asyncio.Task] = None
        self._current_tickers: dict[str, dict] = {}

    def init_user_inputs(self, inputs: dict) -> None:
        self.time_frame = self.time_frame or self.UI.user_input(
            commons_constants.CONFIG_TIME_FRAME,
            commons_enums.UserInputTypes.OPTIONS,
            commons_enums.TimeFrames.ONE_MINUTE.value,
            inputs,
            options=[tf.value for tf in commons_enums.TimeFrames],
            title="Time frame: The time frame to observe (used for OHLCV and Kline channels).",
        )
        self.trigger_channel = self.UI.user_input(
            self.TRIGGER_CHANNEL_KEY,
            commons_enums.UserInputTypes.OPTIONS,
            TRIGGER_CHANNEL_OHLCV,
            inputs,
            options=[
                TRIGGER_CHANNEL_OHLCV, TRIGGER_CHANNEL_KLINE,
                TRIGGER_CHANNEL_TICKER, TRIGGER_CHANNEL_ALL_TICKERS,
            ],
            title="Trigger channel: The data channel that triggers DSL evaluation. "
                  "'ohlcv' fires on candle close, 'kline' fires on every price tick, "
                  "'ticker' fires on ticker updates (~14-64s), "
                  "'all_tickers' periodically fetches ALL exchange tickers and evaluates each symbol.",
        )
        self.all_tickers_refresh_time = float(self.UI.user_input(
            ALL_TICKERS_REFRESH_TIME_KEY,
            commons_enums.UserInputTypes.INT,
            ALL_TICKERS_DEFAULT_REFRESH_TIME,
            inputs,
            title="All tickers refresh time (seconds): How often to fetch all tickers "
                  "(only used when trigger_channel is 'all_tickers').",
        ))
        self.dsl_script = str(self.UI.user_input(
            self.DSL_SCRIPT_KEY,
            commons_enums.UserInputTypes.TEXT,
            "",
            inputs,
            other_schema_values={"minLength": 0},
            title="DSL condition: The DSL expression to evaluate. "
                  "The script result is used as eval_note when truthy, stays pending otherwise. "
                  "Available operators: close(), market_expiry(), now_ms(), triggered_symbol(), etc.",
        ))

    async def start(self, bot_id: str) -> bool:
        if trading_api is None or exchange_channels is None:
            self.logger.error("Can't connect to trading channels: octobot_trading is not installed")
            return False
        exchange_id = trading_api.get_exchange_id_from_matrix_id(
            self.exchange_name, self.matrix_id
        )
        self.exchange_manager = trading_api.get_exchange_manager_from_exchange_id(
            exchange_id
        )
        self._create_interpreter()
        self._prepare_dsl_script()
        if self.trigger_channel == TRIGGER_CHANNEL_ALL_TICKERS:
            self._all_tickers_task = asyncio.create_task(
                self._all_tickers_update_loop()
            )
            self.logger.info(
                f"Started all_tickers update loop "
                f"(refresh every {self.all_tickers_refresh_time}s)"
            )
            return True
        channel_name = TRIGGER_CHANNEL_TO_EXCHANGE_CHANNEL.get(self.trigger_channel)
        if channel_name is None:
            self.logger.error(f"Unknown trigger channel: {self.trigger_channel}")
            return False
        if self.trigger_channel == TRIGGER_CHANNEL_TICKER:
            await exchange_channels.get_chan(
                channel_name, exchange_id
            ).new_consumer(
                callback=self.ticker_callback,
                symbol=self.symbol,
                priority_level=self.priority_level,
            )
        elif self.trigger_channel == TRIGGER_CHANNEL_KLINE:
            await exchange_channels.get_chan(
                channel_name, exchange_id
            ).new_consumer(
                callback=self.kline_callback,
                symbol=self.symbol,
                time_frame=self.available_time_frame,
                priority_level=self.priority_level,
            )
        elif self.trigger_channel == TRIGGER_CHANNEL_OHLCV:
            await exchange_channels.get_chan(
                channel_name, exchange_id
            ).new_consumer(
                callback=self.ohlcv_callback,
                symbol=self.symbol,
                time_frame=self.available_time_frame,
                priority_level=self.priority_level,
            )
        return True

    async def _all_tickers_update_loop(self):
        while True:
            try:
                tickers = await self.exchange_manager.exchange.get_all_currencies_price_ticker()
                if tickers:
                    self._current_tickers.update(tickers)
                    self.logger.debug(
                        f"Fetched {len(tickers)} tickers, evaluating DSL for each"
                    )
                    for symbol in tickers:
                        await self._evaluate("", symbol, eval_time=0)
                else:
                    self.logger.warning("No tickers returned from exchange")
            except asyncio.CancelledError:
                self.logger.debug("All tickers update loop cancelled")
                return
            except Exception as err:
                self.logger.exception(
                    err, True,
                    f"Error fetching all tickers: {err}",
                )
            await asyncio.sleep(self.all_tickers_refresh_time)

    async def ohlcv_callback(
        self, exchange: str, exchange_id: str,
        cryptocurrency: str, symbol: str, time_frame, candle,
    ):
        await self._evaluate(
            cryptocurrency, symbol,
            evaluators_util.get_eval_time(full_candle=candle, time_frame=time_frame),
        )

    async def kline_callback(
        self, exchange: str, exchange_id: str,
        cryptocurrency: str, symbol: str, time_frame, kline,
    ):
        await self._evaluate(
            cryptocurrency, symbol,
            evaluators_util.get_eval_time(kline=kline),
        )

    async def ticker_callback(
        self, exchange: str, exchange_id: str,
        cryptocurrency: str, symbol: str, ticker,
    ):
        await self._evaluate(cryptocurrency, symbol, eval_time=0)

    async def _evaluate(
        self, cryptocurrency: str, symbol: str, eval_time: int,
    ):
        if self.interpreter is None:
            self.logger.warning("DSL interpreter not initialized, skipping evaluation")
            return
        self.triggered_symbol = symbol
        try:
            result = await self.interpreter.compute_expression()
            if result is None or result is False:
                self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
                return
            self.eval_note = result
        except commons_errors.DSLInterpreterError as err:
            self.logger.debug(
                f"DSL evaluation skipped for {symbol}: {err}"
            )
            self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
            return
        except Exception as err:
            self.logger.exception(
                err, True,
                f"Unexpected DSL evaluation error for {symbol}: {err}",
            )
            self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
            return
        await self.evaluation_completed(
            cryptocurrency, symbol, self.available_time_frame,
            eval_time=eval_time,
        )

    async def stop(self) -> None:
        await super().stop()
        if self._all_tickers_task is not None and not self._all_tickers_task.done():
            self._all_tickers_task.cancel()
            try:
                await self._all_tickers_task
            except asyncio.CancelledError:
                pass
            self._all_tickers_task = None

    def _create_interpreter(self):
        operators = (
            dsl_interpreter.get_all_operators()
            + dsl_operators.create_ohlcv_operators(self.exchange_manager, None, None)
            + dsl_operators.create_symbol_operators(self)
            + dsl_operators.create_ticker_operators(self._current_tickers)
        )
        self.interpreter = dsl_interpreter.Interpreter(operators)

    def _prepare_dsl_script(self):
        if not self.dsl_script:
            self.logger.warning("No DSL script configured")
            return
        try:
            self.interpreter.prepare(self.dsl_script)
            self.logger.info(f"DSL script successfully loaded: '{self.dsl_script}'")
        except commons_errors.DSLInterpreterError as err:
            self.logger.exception(
                err, True,
                f"Error when parsing DSL script '{self.dsl_script}': {err}",
            )
        except Exception as err:
            self.logger.exception(
                err, True,
                f"Unexpected error when parsing DSL script '{self.dsl_script}': {err}",
            )

    def set_default_config(self):
        super().set_default_config()
        self.specific_config[commons_constants.CONFIG_TIME_FRAME] = "1m"

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return True

    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        return True
