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
import contextlib
import mock
import pytest
import pytest_asyncio

import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.dsl
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data

import tentacles.Meta.DSL_operators.exchange_operators.exchange_personal_data_operators.fetch_order_operators as fetch_order_operators

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    backtesting_config,
    fake_backtesting,
    backtesting_exchange_manager,
    backtesting_trader,
)

SYMBOL = "BTC/USDT"
EXCHANGE_ORDER_ID = "order-123"
RAW_ORDER_SENTINEL = {"exchange_id": EXCHANGE_ORDER_ID, "symbol": SYMBOL}
FORMATTED_ORDER_SENTINEL = {"formatted": True, "exchange_order_id": EXCHANGE_ORDER_ID}


@pytest_asyncio.fixture
async def fetch_order_operators_list(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    return fetch_order_operators.create_fetch_order_operators(exchange_manager)


@pytest_asyncio.fixture
async def interpreter(fetch_order_operators_list):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + fetch_order_operators_list
    )


@pytest_asyncio.fixture
async def no_exchange_manager_fetch_order_operators_list():
    return fetch_order_operators.create_fetch_order_operators(None)


@pytest_asyncio.fixture
async def no_exchange_manager_interpreter(no_exchange_manager_fetch_order_operators_list):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + no_exchange_manager_fetch_order_operators_list
    )


@pytest_asyncio.fixture
async def maybe_exchange_manager_interpreter(request, interpreter, no_exchange_manager_interpreter):
    selected_value = request.param
    if selected_value == "interpreter":
        return interpreter
    if selected_value == "no_exchange_manager_interpreter":
        return no_exchange_manager_interpreter
    raise ValueError(f"Invalid selected_value: {selected_value}")


class TestFetchOrderOperator:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "trader_mode",
        ("simulated", "real_trading"),
    )
    async def test_pre_compute_returns_formatted_order_dict(
        self, fetch_order_operators_list, backtesting_trader, trader_mode
    ):
        _config, exchange_manager, trader = backtesting_trader
        fetch_order_op_class, = fetch_order_operators_list
        mock_order = mock.Mock()
        mock_order.to_dict = mock.Mock(return_value=FORMATTED_ORDER_SENTINEL)

        with contextlib.ExitStack() as stack:
            if trader_mode == "simulated":
                mock_order.symbol = SYMBOL
                orders_get_mock = stack.enter_context(mock.patch.object(
                    exchange_manager.exchange_personal_data.orders_manager,
                    "get_order",
                    mock.Mock(return_value=mock_order),
                ))
            else:
                stack.enter_context(mock.patch.object(
                    exchange_manager, "is_trader_simulated", False,
                ))
                exchange_get_mock = stack.enter_context(mock.patch.object(
                    exchange_manager.exchange,
                    "get_order",
                    mock.AsyncMock(return_value=RAW_ORDER_SENTINEL),
                ))
                create_from_raw_mock = stack.enter_context(mock.patch.object(
                    trading_personal_data,
                    "create_order_instance_from_raw",
                    mock.Mock(return_value=mock_order),
                ))

            operator = fetch_order_op_class(
                SYMBOL,
                exchange_order_id=EXCHANGE_ORDER_ID,
            )
            await operator.pre_compute()

        assert operator.value == FORMATTED_ORDER_SENTINEL
        mock_order.to_dict.assert_called_once_with()
        if trader_mode == "simulated":
            orders_get_mock.assert_called_once_with(None, exchange_order_id=EXCHANGE_ORDER_ID)
        else:
            exchange_get_mock.assert_awaited_once_with(EXCHANGE_ORDER_ID, symbol=SYMBOL)
            create_from_raw_mock.assert_called_once_with(trader, RAW_ORDER_SENTINEL)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "trader_mode",
        ("simulated", "real_trading"),
    )
    async def test_pre_compute_order_not_found(
        self, fetch_order_operators_list, backtesting_trader, trader_mode
    ):
        _config, exchange_manager, _trader = backtesting_trader
        fetch_order_op_class, = fetch_order_operators_list

        with contextlib.ExitStack() as stack:
            if trader_mode == "simulated":
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange_personal_data.orders_manager,
                    "get_order",
                    mock.Mock(side_effect=KeyError(EXCHANGE_ORDER_ID)),
                ))
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange_personal_data.trades_manager,
                    "get_trades",
                    mock.Mock(return_value=[]),
                ))
            else:
                stack.enter_context(mock.patch.object(
                    exchange_manager, "is_trader_simulated", False,
                ))
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange,
                    "get_order",
                    mock.AsyncMock(return_value=None),
                ))
            operator = fetch_order_op_class(
                SYMBOL,
                exchange_order_id=EXCHANGE_ORDER_ID,
            )
            await operator.pre_compute()
            assert operator.value is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "trader_mode",
        ("simulated", "real_trading"),
    )
    async def test_pre_compute_order_not_found_raises_when_raise_if_not_found(
        self, fetch_order_operators_list, backtesting_trader, trader_mode
    ):
        _config, exchange_manager, _trader = backtesting_trader
        fetch_order_op_class, = fetch_order_operators_list
        with contextlib.ExitStack() as stack:
            if trader_mode == "simulated":
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange_personal_data.orders_manager,
                    "get_order",
                    mock.Mock(side_effect=KeyError(EXCHANGE_ORDER_ID)),
                ))
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange_personal_data.trades_manager,
                    "get_trades",
                    mock.Mock(return_value=[]),
                ))
            else:
                stack.enter_context(mock.patch.object(
                    exchange_manager, "is_trader_simulated", False,
                ))
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange,
                    "get_order",
                    mock.AsyncMock(return_value=None),
                ))
            operator = fetch_order_op_class(
                SYMBOL,
                exchange_order_id=EXCHANGE_ORDER_ID,
                raise_if_not_found=True,
            )
            with pytest.raises(
                octobot_commons.errors.InvalidParametersError,
                match="No .* order found for symbol=.*exchange_order_id=",
            ):
                await operator.pre_compute()

    @pytest.mark.asyncio
    async def test_pre_compute_symbol_mismatch_simulated(
        self, fetch_order_operators_list, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        fetch_order_op_class, = fetch_order_operators_list
        mock_order = mock.Mock()
        mock_order.symbol = "ETH/USDT"

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_order",
            mock.Mock(return_value=mock_order),
        ):
            operator = fetch_order_op_class(
                SYMBOL,
                exchange_order_id=EXCHANGE_ORDER_ID,
            )
            with pytest.raises(
                octobot_commons.errors.InvalidParametersError,
                match="is for symbol",
            ):
                await operator.pre_compute()

    @pytest.mark.asyncio
    async def test_pre_compute_simulated_resolves_from_trades_when_order_not_in_manager(
        self, fetch_order_operators_list, backtesting_trader
    ):
        _config, exchange_manager, trader = backtesting_trader
        fetch_order_op_class, = fetch_order_operators_list
        mock_order_instance = mock.Mock()
        mock_order_instance.to_dict = mock.Mock(return_value=FORMATTED_ORDER_SENTINEL)

        mock_trade = mock.Mock()
        mock_trade.symbol = SYMBOL
        mock_trade.to_dict = mock.Mock(return_value={trading_enums.ExchangeConstantsOrderColumns.ID.value: "t1"})
        mock_trade.has_been_executed = mock.Mock(return_value=True)
        mock_trade.executed_quantity = mock.Mock()
        mock_trade.get_time = mock.Mock(return_value=0.0)

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_order",
            mock.Mock(side_effect=KeyError(EXCHANGE_ORDER_ID)),
        ), mock.patch.object(
            exchange_manager.exchange_personal_data.trades_manager,
            "get_trades",
            mock.Mock(return_value=[mock_trade]),
        ) as get_trades_mock, mock.patch.object(
            trading_personal_data,
            "create_order_from_dict",
            mock.Mock(return_value=mock_order_instance),
        ) as create_from_dict_mock:
            operator = fetch_order_op_class(
                SYMBOL,
                exchange_order_id=EXCHANGE_ORDER_ID,
            )
            await operator.pre_compute()

        assert operator.value == FORMATTED_ORDER_SENTINEL
        get_trades_mock.assert_called_once_with(exchange_order_id=EXCHANGE_ORDER_ID)
        create_from_dict_mock.assert_called_once()
        assert trader is create_from_dict_mock.call_args[0][0]
        order_dict_passed = create_from_dict_mock.call_args[0][1]
        assert trading_enums.ExchangeConstantsOrderColumns.FILLED.value in order_dict_passed

    @pytest.mark.asyncio
    async def test_pre_compute_requires_exchange_manager(self, no_exchange_manager_fetch_order_operators_list):
        fetch_order_op_class, = no_exchange_manager_fetch_order_operators_list
        operator = fetch_order_op_class(
            SYMBOL,
            exchange_order_id=EXCHANGE_ORDER_ID,
        )
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="exchange_manager and exchange_manager.trader are required for fetch_order operator",
        ):
            await operator.pre_compute()

    @pytest.mark.asyncio
    async def test_pre_compute_requires_trader(self, fetch_order_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        fetch_order_op_class, = fetch_order_operators_list
        previous_trader = exchange_manager.trader
        exchange_manager.trader = None
        try:
            operator = fetch_order_op_class(
                SYMBOL,
                exchange_order_id=EXCHANGE_ORDER_ID,
            )
            with pytest.raises(
                octobot_commons.errors.DSLInterpreterError,
                match="exchange_manager and exchange_manager.trader are required for fetch_order operator",
            ):
                await operator.pre_compute()
        finally:
            exchange_manager.trader = previous_trader

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "trader_mode",
        ("simulated", "real_trading"),
    )
    async def test_fetch_order_call_as_dsl(
        self, interpreter, backtesting_trader, trader_mode
    ):
        _config, exchange_manager, _trader = backtesting_trader
        mock_order = mock.Mock()
        mock_order.to_dict = mock.Mock(return_value=FORMATTED_ORDER_SENTINEL)

        with contextlib.ExitStack() as stack:
            if trader_mode == "simulated":
                mock_order.symbol = SYMBOL
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange_personal_data.orders_manager,
                    "get_order",
                    mock.Mock(return_value=mock_order),
                ))
            else:
                stack.enter_context(mock.patch.object(
                    exchange_manager, "is_trader_simulated", False,
                ))
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange,
                    "get_order",
                    mock.AsyncMock(return_value=RAW_ORDER_SENTINEL),
                ))
                stack.enter_context(mock.patch.object(
                    trading_personal_data,
                    "create_order_instance_from_raw",
                    mock.Mock(return_value=mock_order),
                ))
            resolved = await interpreter.interprete(
                f"fetch_order('{SYMBOL}', exchange_order_id='{EXCHANGE_ORDER_ID}')"
            )
        assert resolved == FORMATTED_ORDER_SENTINEL

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "trader_mode",
        ("simulated", "real_trading"),
    )
    async def test_fetch_order_call_as_dsl_raise_if_not_found_true(
        self, interpreter, backtesting_trader, trader_mode
    ):
        _config, exchange_manager, _trader = backtesting_trader
        with contextlib.ExitStack() as stack:
            if trader_mode == "simulated":
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange_personal_data.orders_manager,
                    "get_order",
                    mock.Mock(side_effect=KeyError(EXCHANGE_ORDER_ID)),
                ))
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange_personal_data.trades_manager,
                    "get_trades",
                    mock.Mock(return_value=[]),
                ))
            else:
                stack.enter_context(mock.patch.object(
                    exchange_manager, "is_trader_simulated", False,
                ))
                stack.enter_context(mock.patch.object(
                    exchange_manager.exchange,
                    "get_order",
                    mock.AsyncMock(return_value=None),
                ))
            with pytest.raises(
                octobot_commons.errors.InvalidParametersError,
                match="No .* order found for symbol=.*exchange_order_id=",
            ):
                await interpreter.interprete(
                    f"fetch_order('{SYMBOL}', exchange_order_id='{EXCHANGE_ORDER_ID}', "
                    f"raise_if_not_found=True)"
                )


class TestGetDependencies:
    @pytest.mark.parametrize(
        "maybe_exchange_manager_interpreter",
        ["interpreter", "no_exchange_manager_interpreter"],
        indirect=True,
    )
    def test_fetch_order_get_dependencies_from_interpreter(
        self, maybe_exchange_manager_interpreter
    ):
        maybe_exchange_manager_interpreter.prepare(
            f"fetch_order('{SYMBOL}', exchange_order_id='{EXCHANGE_ORDER_ID}')"
        )
        assert maybe_exchange_manager_interpreter.get_dependencies() == [
            octobot_trading.dsl.SymbolDependency(symbol=SYMBOL),
        ]
        other_symbol = "ETH/USDT"
        maybe_exchange_manager_interpreter.prepare(
            f"fetch_order('{other_symbol}', exchange_order_id='{EXCHANGE_ORDER_ID}')"
        )
        assert maybe_exchange_manager_interpreter.get_dependencies() == [
            octobot_trading.dsl.SymbolDependency(symbol=other_symbol),
        ]
