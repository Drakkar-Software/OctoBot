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
import decimal

import mock
import pytest

import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.api
import octobot_trading.constants
import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators

from tentacles.Meta.DSL_operators.exchange_operators.tests.exchange_public_data_operators import (
    SYMBOL,
    SYMBOL2,
    RESOLVED_SYMBOL,
)


PRICES_BY_SYMBOL = {
    SYMBOL: decimal.Decimal("50000"),
    SYMBOL2: decimal.Decimal("3000"),
    RESOLVED_SYMBOL: decimal.Decimal("50000"),
}


def _identity_get_exchange_symbol(symbol, error_on_missing=False):
    return symbol


@pytest.fixture
def exchange_manager_with_prices():
    symbol_data_by_symbol = {}

    def get_exchange_symbol_data(symbol, allow_creation=True):
        if symbol not in PRICES_BY_SYMBOL:
            raise octobot_commons.errors.InvalidParametersError(f"Symbol {symbol} not found")
        if symbol not in symbol_data_by_symbol:
            prices_manager = mock.Mock()
            prices_manager.get_mark_price_no_wait = mock.Mock(
                return_value=PRICES_BY_SYMBOL[symbol]
            )
            symbol_data_by_symbol[symbol] = mock.Mock(prices_manager=prices_manager)
        return symbol_data_by_symbol[symbol]

    return mock.Mock(
        get_exchange_symbol=mock.Mock(side_effect=_identity_get_exchange_symbol),
        exchange_symbols_data=mock.Mock(
            get_exchange_symbol_data=get_exchange_symbol_data
        )
    )


@pytest.fixture
def interpreter(exchange_manager_with_prices):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + exchange_operators.create_price_operators(exchange_manager_with_prices, SYMBOL)
    )


@pytest.fixture
def interpreter_without_exchange_data():
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + exchange_operators.create_price_operators(None, None)
    )


@pytest.mark.asyncio
async def test_price_operator_default_symbol(interpreter):
    assert await interpreter.interprete("price") == float(PRICES_BY_SYMBOL[SYMBOL])


@pytest.mark.asyncio
async def test_price_operator_with_symbol_param(interpreter):
    assert await interpreter.interprete(f"price('{SYMBOL2}')") == float(PRICES_BY_SYMBOL[SYMBOL2])
    assert await interpreter.interprete(f"price('{SYMBOL}')") == float(PRICES_BY_SYMBOL[SYMBOL])


@pytest.mark.asyncio
async def test_price_operator_unknown_symbol(interpreter):
    with pytest.raises(octobot_commons.errors.InvalidParametersError, match="Symbol UNKNOWN/PAIR not found"):
        await interpreter.interprete("price('UNKNOWN/PAIR')")


@pytest.mark.asyncio
async def test_price_operator_no_valid_price(exchange_manager_with_prices):
    symbol_data = exchange_manager_with_prices.exchange_symbols_data.get_exchange_symbol_data(SYMBOL)
    symbol_data.prices_manager.get_mark_price_no_wait = mock.Mock(
        side_effect=ValueError(f"No up to date mark price for {SYMBOL}")
    )
    price_interpreter = dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + exchange_operators.create_price_operators(exchange_manager_with_prices, SYMBOL)
    )
    with pytest.raises(octobot_commons.errors.DSLInterpreterError, match="No up to date mark price"):
        await price_interpreter.interprete("price")


@pytest.mark.asyncio
async def test_price_operator_without_exchange_manager(interpreter_without_exchange_data):
    with pytest.raises(octobot_commons.errors.DSLInterpreterError, match="exchange_manager must be provided"):
        await interpreter_without_exchange_data.interprete(f"price('{SYMBOL}')")


class TestGetDependencies:
    @pytest.mark.asyncio
    async def test_price_dependencies_with_context_symbol(self, interpreter):
        interpreter.prepare("price")
        assert interpreter.get_dependencies() == [
            exchange_operators.ExchangeDataDependency(
                symbol=SYMBOL,
                time_frame=None,
                data_source=octobot_trading.constants.MARK_PRICE_CHANNEL,
            )
        ]

    @pytest.mark.asyncio
    async def test_price_dependencies_with_param_symbol(self, interpreter):
        interpreter.prepare(f"price + price('{SYMBOL2}')")
        assert interpreter.get_dependencies() == [
            exchange_operators.ExchangeDataDependency(
                symbol=SYMBOL,
                time_frame=None,
                data_source=octobot_trading.constants.MARK_PRICE_CHANNEL,
            ),
            exchange_operators.ExchangeDataDependency(
                symbol=SYMBOL2,
                time_frame=None,
                data_source=octobot_trading.constants.MARK_PRICE_CHANNEL,
            ),
        ]

    @pytest.mark.asyncio
    async def test_price_dependencies_without_exchange_manager(self, interpreter_without_exchange_data):
        interpreter_without_exchange_data.prepare("price")
        assert interpreter_without_exchange_data.get_dependencies() == []
        interpreter_without_exchange_data.prepare(f"price + price('{SYMBOL2}')")
        assert interpreter_without_exchange_data.get_dependencies() == [
            exchange_operators.ExchangeDataDependency(
                symbol=SYMBOL2,
                time_frame=None,
                data_source=octobot_trading.constants.MARK_PRICE_CHANNEL,
            ),
        ]


class TestGetExchangeSymbol:
    @pytest.mark.asyncio
    async def test_pre_compute_calls_get_exchange_symbol_with_context_symbol(
        self, exchange_manager_with_prices
    ):
        price_interpreter = dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + exchange_operators.create_price_operators(exchange_manager_with_prices, SYMBOL)
        )
        await price_interpreter.interprete("price")
        exchange_manager_with_prices.get_exchange_symbol.assert_called_once_with(SYMBOL)

    @pytest.mark.asyncio
    async def test_pre_compute_calls_get_exchange_symbol_with_param_symbol(
        self, exchange_manager_with_prices
    ):
        price_interpreter = dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + exchange_operators.create_price_operators(exchange_manager_with_prices, SYMBOL)
        )
        await price_interpreter.interprete(f"price('{SYMBOL2}')")
        exchange_manager_with_prices.get_exchange_symbol.assert_called_once_with(SYMBOL2)

    @pytest.mark.asyncio
    async def test_get_dependencies_calls_get_exchange_symbol(self, exchange_manager_with_prices):
        price_interpreter = dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + exchange_operators.create_price_operators(exchange_manager_with_prices, SYMBOL)
        )
        price_interpreter.prepare("price")
        price_interpreter.get_dependencies()
        exchange_manager_with_prices.get_exchange_symbol.assert_called_once_with(
            SYMBOL, error_on_missing=False
        )

    @pytest.mark.asyncio
    async def test_get_dependencies_does_not_call_get_exchange_symbol_without_exchange_manager(
        self, interpreter_without_exchange_data
    ):
        with mock.patch.object(
            exchange_operators.exchange_public_data_operators.ohlcv_operators.ExchangeDataDependency,
            "resolve_symbol",
            autospec=True,
        ) as resolve_symbol_mock:
            interpreter_without_exchange_data.prepare(f"price('{SYMBOL2}')")
            interpreter_without_exchange_data.get_dependencies()
            resolve_symbol_mock.assert_called()
            assert all(
                call.args[1] is None
                for call in resolve_symbol_mock.call_args_list
            )

    @pytest.mark.asyncio
    async def test_pre_compute_uses_resolved_symbol_downstream(
        self, exchange_manager_with_prices
    ):
        exchange_manager_with_prices.get_exchange_symbol = mock.Mock(return_value=RESOLVED_SYMBOL)
        price_interpreter = dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + exchange_operators.create_price_operators(exchange_manager_with_prices, SYMBOL)
        )
        with mock.patch.object(
            octobot_trading.api, "get_symbol_data", wraps=octobot_trading.api.get_symbol_data
        ) as get_symbol_data_spy:
            await price_interpreter.interprete("price")
            get_symbol_data_spy.assert_called_once_with(
                exchange_manager_with_prices, RESOLVED_SYMBOL, allow_creation=False
            )
