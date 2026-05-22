# Drakkar-Software OctoBot-Tentacles
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
import dataclasses
import decimal
import typing
import numpy as np
import octobot_commons.enums as commons_enums

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.logging as logging
import octobot_commons.time_frame_manager as time_frame_manager

import octobot_trading.api as trading_api
import octobot_trading.exchange_data as exchange_data
import octobot_trading.constants as trading_constants
import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators


DEFAULT_TIME_FRAME = commons_enums.TimeFrames.ONE_HOUR.value


@dataclasses.dataclass
class AdvancedPriceSource:
    exchange: str
    pair: str
    time_frame: typing.Optional[str]
    weight: decimal.Decimal
    formula: str

    _formula_interpreter: typing.Optional[dsl_interpreter.Interpreter] = None

    async def evaluate_formula(self, price: typing.Optional[decimal.Decimal] = None) -> decimal.Decimal:
        if not self.formula:
            if price is None:
                raise ValueError("price is required when no formula is configured")
            return price
        result = None
        try:
            result = await self._evaluate_formula()
            return decimal.Decimal(str(result))
        except decimal.DecimalException:
            # formula is not a flat number
            raise NotImplementedError(
                f"Configured formula \"{self.formula}\" should return a number, got {type(result).__name__} (value: {self._get_sumarized_formula_error_message(result)})"
            )
        except TypeError as err:
            raise TypeError(
                f"Invalid {self.pair} reference price formula: {err.__class__.__name__}: {err}"
            ) from err

    def get_dependencies(self, exchange_manager) -> typing.List[exchange_operators.ExchangeDataDependency]:
        base_dependencies = [
            exchange_operators.ExchangeDataDependency(
                symbol=self.pair,
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            )
        ]
        if self.formula:
            all_dependencies = (
                base_dependencies
                + self._formula_interpreter.get_dependencies() # type: ignore
            )
            deduplicated_dependencies = []
            for dependency in all_dependencies:
                if dependency not in deduplicated_dependencies:
                    deduplicated_dependencies.append(dependency)
            return deduplicated_dependencies
        return base_dependencies

    async def initialize_if_required(
        self,
        exchange_manager,
        candle_manager_by_time_frame_by_symbol: typing.Optional[
            typing.Dict[str, typing.Dict[str, exchange_data.CandlesManager]]
        ] = None,
        price_by_symbol: typing.Optional[typing.Dict[str, typing.Optional[decimal.Decimal]]] = None
    ) -> None:
        if self.formula and not self._formula_interpreter:
            self._initialize_formula_interpreter(
                exchange_manager, candle_manager_by_time_frame_by_symbol, price_by_symbol
            )
    
    async def validate_interpreted_formula(
        self,
        exchange_manager,
        candle_manager_by_time_frame_by_symbol: typing.Optional[
            typing.Dict[str, typing.Dict[str, exchange_data.CandlesManager]]
        ] = None
    ) -> None:
        self.reset_formula_interpreter()
        await self.initialize_if_required(exchange_manager, candle_manager_by_time_frame_by_symbol)

    def reset_formula_interpreter(self) -> None:
        self._formula_interpreter = None

    def _get_sumarized_formula_error_message(self, result: typing.Any) -> typing.Union[str, list]:
        if isinstance(result, (list, np.ndarray, tuple)) and len(result) > 4:
            return list(result[:2]) + ["..."] + list(result[-2:])
        return str(result)

    async def _evaluate_formula(self) -> typing.Any:
        formula_result = await self._formula_interpreter.compute_expression()
        return formula_result

    def _get_formula_interpreter_operators(
        self, exchange_manager,
        time_frame: commons_enums.TimeFrames,
        candle_manager_by_time_frame_by_symbol: typing.Optional[
            typing.Dict[str, typing.Dict[str, exchange_data.CandlesManager]]
        ] = None,
        price_by_symbol: typing.Optional[typing.Dict[str, typing.Optional[decimal.Decimal]]] = None
    ) -> typing.List[type[dsl_interpreter.Operator]]:
        base_operators = dsl_interpreter.get_all_operators()
        ohlcv_operators = exchange_operators.create_ohlcv_operators(
            exchange_manager, self.pair, time_frame.value, candle_manager_by_time_frame_by_symbol
        )
        price_operators = exchange_operators.create_price_operators(
            exchange_manager, self.pair, price_by_symbol
        )
        return base_operators + ohlcv_operators + price_operators

    def _initialize_formula_interpreter(
        self,
        exchange_manager,
        candle_manager_by_time_frame_by_symbol: typing.Optional[
            typing.Dict[str, typing.Dict[str, exchange_data.CandlesManager]]
        ] = None,
        price_by_symbol: typing.Optional[typing.Dict[str, typing.Optional[decimal.Decimal]]] = None
    ) -> None:

        if exchange_manager:
            time_frames = trading_api.get_watched_timeframes(exchange_manager)
        else:
            time_frames = [
                commons_enums.TimeFrames(time_frame)
                for time_frame in candle_manager_by_time_frame_by_symbol
            ]
        watched_timeframes = time_frame_manager.sort_time_frames(time_frames)
        time_frame = self.time_frame or (
            watched_timeframes[-1] if watched_timeframes else DEFAULT_TIME_FRAME
        )
        if not time_frame:
            raise ValueError("No time frame available")
        time_frame = commons_enums.TimeFrames(time_frame)
        self._formula_interpreter = dsl_interpreter.Interpreter(
            self._get_formula_interpreter_operators(
                exchange_manager, time_frame, candle_manager_by_time_frame_by_symbol, price_by_symbol
            )
        )
        logger = logging.get_logger(self.__class__.__name__)
        try:
            self._formula_interpreter.prepare(self.formula)
            exchange_name = f"[{exchange_manager.exchange_name}] " if exchange_manager else ''
            logger.info(
                f"Formula interpreter successfully prepared for \"{self.formula}\" "
                f"on {exchange_name}pair={self.pair} time_frame={self.time_frame} "
                f"[weight={self.weight}]"
            )
        except Exception as e:
            logger.error(f"Error when parsing formula {self.formula}: {e}")
            raise e

async def compute_reference_price(
    price_by_pair_by_exchange: typing.Dict[str, typing.Dict[str, typing.Optional[decimal.Decimal]]],
    reference_price_specs_by_exchange: typing.Dict[str, typing.Iterable[AdvancedPriceSource]]
) -> decimal.Decimal:
    total_price = trading_constants.ZERO
    total_weight = trading_constants.ZERO
    for exchange, price_by_pair in price_by_pair_by_exchange.items():
        if exchange in reference_price_specs_by_exchange:
            for reference_price_spec in reference_price_specs_by_exchange[exchange]:
                price = price_by_pair.get(reference_price_spec.pair)
                source_price = await reference_price_spec.evaluate_formula(price)
                total_price += source_price * reference_price_spec.weight
                total_weight += reference_price_spec.weight
    if total_weight:
        return total_price / total_weight
    return trading_constants.ZERO
