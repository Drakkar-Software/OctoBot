# pylint: disable=missing-class-docstring,missing-function-docstring
#  Drakkar-Software OctoBot-Commons
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
import typing
import dataclasses
import numpy as np

import octobot_commons.constants
import octobot_commons.errors
import octobot_commons.logging
import octobot_commons.enums as commons_enums
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.exchanges
import octobot_trading.exchange_data
import octobot_trading.api
import octobot_trading.constants

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


@dataclasses.dataclass
class ExchangeDataDependency(dsl_interpreter.InterpreterDependency):
    exchange_manager_id: str
    symbol: typing.Optional[str]
    time_frame: typing.Optional[str]
    data_source: str = octobot_trading.constants.OHLCV_CHANNEL

    def __hash__(self) -> int:
        return hash((self.exchange_manager_id, self.symbol, self.time_frame, self.data_source))


class OHLCVOperator(exchange_operator.ExchangeOperator):
    def __init__(self, *parameters: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.value: dsl_interpreter_operator.ComputedOperatorParameterType = exchange_operator.UNINITIALIZED_VALUE # type: ignore

    @staticmethod
    def get_library() -> str:
        # this is a contextual operator, so it should not be included by default in the get_all_operators function return values
        return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="symbol", description="the symbol to get the OHLCV data for", required=False, type=str),
            dsl_interpreter.OperatorParameter(name="time_frame", description="the time frame to get the OHLCV data for", required=False, type=str),
        ]

    def get_symbol_and_time_frame(self) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
        if parameters := self.get_computed_parameters():
            symbol = parameters[0] if len(parameters) > 0 else None
            time_frame = parameters[1] if len(parameters) > 1 else None
            return (
                str(symbol) if symbol is not None else None,
                str(time_frame) if time_frame is not None else None
            )
        return None, None

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        if self.value is exchange_operator.UNINITIALIZED_VALUE:
            raise octobot_commons.errors.DSLInterpreterError("{self.__class__.__name__} has not been initialized")
        return self.value


def create_ohlcv_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
    symbol: typing.Optional[str],
    time_frame: typing.Optional[str],
    candle_manager_by_time_frame_by_symbol: typing.Optional[
        typing.Dict[str, typing.Dict[str, octobot_trading.exchange_data.CandlesManager]]
    ] = None
) -> typing.List[type[OHLCVOperator]]:

    if exchange_manager is None and candle_manager_by_time_frame_by_symbol is None:
        raise octobot_commons.errors.InvalidParametersError("exchange_manager or candle_manager_by_time_frame_by_symbol must be provided")

    def _get_candles_values_with_latest_kline_if_available(
        input_symbol: typing.Optional[str], input_time_frame: typing.Optional[str],
        value_type: commons_enums.PriceIndexes, limit: int = -1
    ) -> np.ndarray:
        _symbol = input_symbol or symbol
        _time_frame = input_time_frame or time_frame
        if exchange_manager is None:
            if candle_manager_by_time_frame_by_symbol is not None:
                candles_manager = candle_manager_by_time_frame_by_symbol[_time_frame][_symbol]
            symbol_data = None
        else:
            symbol_data = octobot_trading.api.get_symbol_data(
                exchange_manager, _symbol, allow_creation=False
            )
            candles_manager = octobot_trading.api.get_symbol_candles_manager(
                symbol_data, _time_frame
            )
        candles_values = _get_candles_values(candles_manager, value_type, limit)
        if symbol_data is not None and (kline := _get_kline(symbol_data, _time_frame)):
            kline_time = kline[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
            last_candle_time = candles_manager.time_candles[candles_manager.time_candles_index - 1]
            if kline_time == last_candle_time:
                # kline is an update of the last candle
                return _adapt_last_candle_value(candles_manager, value_type, candles_values, kline)
            else:
                tf_seconds = commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(_time_frame)] * octobot_commons.constants.MINUTE_TO_SECONDS
                if kline_time == last_candle_time + tf_seconds:
                    # kline is a new candle
                    kline_value = kline[value_type.value]
                    return np.append(candles_values[1:], kline_value)
                else:
                    octobot_commons.logging.get_logger(OHLCVOperator.__name__).error(
                        f"{exchange_manager.exchange_name + '' if exchange_manager is not None else ''}{_symbol} {_time_frame} "
                        f"kline time ({kline_time}) is not equal to last candle time not the last time + {_time_frame} "
                        f"({last_candle_time} + {tf_seconds}) seconds. Kline has been ignored."
                    )
        return candles_values

    def _get_dependencies() -> typing.List[ExchangeDataDependency]:
        return [
            ExchangeDataDependency(
                exchange_manager_id=octobot_trading.api.get_exchange_manager_id(exchange_manager),
                symbol=symbol,
                time_frame=time_frame
            )
        ]

    class _LocalOHLCVOperator(OHLCVOperator):
        PRICE_INDEX: commons_enums.PriceIndexes = None # type: ignore

        def get_dependencies(self) -> typing.List[dsl_interpreter.InterpreterDependency]:
            return super().get_dependencies() + _get_dependencies()

        async def pre_compute(self) -> None:
            await super().pre_compute()
            self.value = _get_candles_values_with_latest_kline_if_available(*self.get_symbol_and_time_frame(), self.PRICE_INDEX, -1)
    
    class _OpenPriceOperator(_LocalOHLCVOperator):
        DESCRIPTION = "Returns the candle's open price as array of floats"
        EXAMPLE = "open('BTC/USDT', '1h')"

        PRICE_INDEX = commons_enums.PriceIndexes.IND_PRICE_OPEN

        @staticmethod
        def get_name() -> str:
            return "open"
    
    class _HighPriceOperator(_LocalOHLCVOperator):
        DESCRIPTION = "Returns the candle's high price as array of floats"
        EXAMPLE = "high('BTC/USDT', '1h')"

        PRICE_INDEX = commons_enums.PriceIndexes.IND_PRICE_HIGH

        @staticmethod
        def get_name() -> str:
            return "high"

    class _LowPriceOperator(_LocalOHLCVOperator):
        DESCRIPTION = "Returns the candle's low price as array of floats"
        EXAMPLE = "low('BTC/USDT', '1h')"

        PRICE_INDEX = commons_enums.PriceIndexes.IND_PRICE_LOW

        @staticmethod
        def get_name() -> str:
            return "low"

    class _ClosePriceOperator(_LocalOHLCVOperator):
        DESCRIPTION = "Returns the candle's close price as array of floats"
        EXAMPLE = "close('BTC/USDT', '1h')"

        PRICE_INDEX = commons_enums.PriceIndexes.IND_PRICE_CLOSE

        @staticmethod
        def get_name() -> str:
            return "close"

    class _VolumePriceOperator(_LocalOHLCVOperator):
        DESCRIPTION = "Returns the candle's volume as array of floats"
        EXAMPLE = "volume('BTC/USDT', '1h')"

        PRICE_INDEX = commons_enums.PriceIndexes.IND_PRICE_VOL

        @staticmethod
        def get_name() -> str:
            return "volume"
    
    class _TimePriceOperator(_LocalOHLCVOperator):
        DESCRIPTION = "Returns the candle's time as array of floats"
        EXAMPLE = "time('BTC/USDT', '1h')"

        PRICE_INDEX = commons_enums.PriceIndexes.IND_PRICE_TIME

        @staticmethod
        def get_name() -> str:
            return "time"

    return [_OpenPriceOperator, _HighPriceOperator, _LowPriceOperator, _ClosePriceOperator, _VolumePriceOperator, _TimePriceOperator]

def _get_kline(
    symbol_data: octobot_trading.exchange_data.ExchangeSymbolData, _time_frame: str
) -> typing.Optional[list]:
    try:
        return octobot_trading.api.get_symbol_klines(symbol_data, _time_frame)
    except KeyError:
        return None


def _get_candles_values(
    candles_manager: octobot_trading.exchange_data.CandlesManager,
    candle_value: commons_enums.PriceIndexes, limit: int = -1
) -> np.ndarray:
    match candle_value:
        case commons_enums.PriceIndexes.IND_PRICE_CLOSE:
            return candles_manager.get_symbol_close_candles(limit)
        case commons_enums.PriceIndexes.IND_PRICE_OPEN:
            return candles_manager.get_symbol_open_candles(limit)
        case commons_enums.PriceIndexes.IND_PRICE_HIGH:
            return candles_manager.get_symbol_high_candles(limit)
        case commons_enums.PriceIndexes.IND_PRICE_LOW:
            return candles_manager.get_symbol_low_candles(limit)
        case commons_enums.PriceIndexes.IND_PRICE_VOL:
            return candles_manager.get_symbol_volume_candles(limit)
        case commons_enums.PriceIndexes.IND_PRICE_TIME:
            return candles_manager.get_symbol_time_candles(limit)
        case _:
            raise octobot_commons.errors.InvalidParametersError(f"Invalid candle value: {candle_value}")

def _adapt_last_candle_value(
    candles_manager: octobot_trading.exchange_data.CandlesManager,
    candle_value: commons_enums.PriceIndexes,
    candles_values: np.ndarray,
    kline: list
) -> np.ndarray:
    match candle_value:
        case commons_enums.PriceIndexes.IND_PRICE_CLOSE:
            candles_values[candles_manager.close_candles_index - 1] = kline[commons_enums.PriceIndexes.IND_PRICE_CLOSE.value]
        case commons_enums.PriceIndexes.IND_PRICE_OPEN:
            candles_values[candles_manager.open_candles_index - 1] = kline[commons_enums.PriceIndexes.IND_PRICE_OPEN.value]
        case commons_enums.PriceIndexes.IND_PRICE_HIGH:
            candles_values[candles_manager.high_candles_index - 1] = kline[commons_enums.PriceIndexes.IND_PRICE_HIGH.value]
        case commons_enums.PriceIndexes.IND_PRICE_LOW:
            candles_values[candles_manager.low_candles_index - 1] = kline[commons_enums.PriceIndexes.IND_PRICE_LOW.value]
        case commons_enums.PriceIndexes.IND_PRICE_VOL:
            candles_values[candles_manager.volume_candles_index - 1] = kline[commons_enums.PriceIndexes.IND_PRICE_VOL.value]
        case commons_enums.PriceIndexes.IND_PRICE_TIME:
            # nothing to do for time (this value is constant)
            pass
        case _:
            raise octobot_commons.errors.InvalidParametersError(f"Invalid candle value: {candle_value}")
    return candles_values
