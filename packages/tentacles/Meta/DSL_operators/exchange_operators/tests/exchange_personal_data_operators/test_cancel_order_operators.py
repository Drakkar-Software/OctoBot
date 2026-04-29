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
import pytest_asyncio

import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.enums
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.dsl

import tentacles.Meta.DSL_operators.exchange_operators.exchange_personal_data_operators.cancel_order_operators as cancel_order_operators

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    backtesting_config,
    fake_backtesting,
    backtesting_exchange_manager,
    backtesting_trader,
)

SYMBOL = "BTC/USDT"
EXCHANGE_ORDER_ID = "order-123"


def _create_mock_order(exchange_order_id: str, side: str = "buy", symbol: str = SYMBOL):
    order = mock.Mock()
    order.exchange_order_id = exchange_order_id
    order.symbol = symbol
    order.side = octobot_trading.enums.TradeOrderSide(side)
    order.is_cancelled = mock.Mock(return_value=False)
    order.is_closed = mock.Mock(return_value=False)
    return order


@pytest_asyncio.fixture
async def cancel_order_operators_list(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    return cancel_order_operators.create_cancel_order_operators(exchange_manager)


@pytest_asyncio.fixture
async def cancel_order_operators_with_trading_mode(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    mock_trading_mode = mock.Mock()
    mock_trading_mode.cancel_order = mock.AsyncMock(return_value=(True, None))
    mock_dependencies = mock.Mock()
    operators_list = cancel_order_operators.create_cancel_order_operators(
        exchange_manager,
        trading_mode=mock_trading_mode,
        dependencies=mock_dependencies,
    )
    return operators_list, mock_trading_mode, mock_dependencies


@pytest_asyncio.fixture
async def interpreter(cancel_order_operators_list):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + cancel_order_operators_list
    )


@pytest_asyncio.fixture
async def no_exchange_manager_cancel_order_operators_list():
    return cancel_order_operators.create_cancel_order_operators(None)


@pytest_asyncio.fixture
async def no_exchange_manager_interpreter(no_exchange_manager_cancel_order_operators_list):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + no_exchange_manager_cancel_order_operators_list
    )


@pytest_asyncio.fixture
async def maybe_exchange_manager_interpreter(request, interpreter, no_exchange_manager_interpreter):
    """Parametrized fixture that yields either interpreter or no_exchange_manager_interpreter."""
    selected_value = request.param
    if selected_value == "interpreter":
        return interpreter
    elif selected_value == "no_exchange_manager_interpreter":
        return no_exchange_manager_interpreter
    raise ValueError(f"Invalid selected_value: {selected_value}")


class TestCancelOrderOperator:
    @pytest.mark.asyncio
    async def test_pre_compute_cancels_matching_orders(self, cancel_order_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        cancel_order_op_class, = cancel_order_operators_list

        order1 = _create_mock_order("order-1")
        order2 = _create_mock_order("order-2")
        mock_orders = [order1, order2]

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=mock_orders,
        ), mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(side_effect=[True, True]),
        ) as cancel_order_mock:
            operator = cancel_order_op_class(
                SYMBOL,
                exchange_order_ids=["order-1", "order-2"],
            )
            await operator.pre_compute()

            assert operator.value == {"cancelled_orders": ["order-1", "order-2"]}
            assert cancel_order_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_pre_compute_no_orders_to_cancel(self, cancel_order_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        cancel_order_op_class, = cancel_order_operators_list

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=[],
        ), mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(),
        ) as cancel_order_mock:
            operator = cancel_order_op_class(
                SYMBOL,
                exchange_order_ids=["order-1"],
            )
            with pytest.raises(
                trading_errors.OrderDescriptionNotFoundError,
                match="No .* order found matching",
            ):
                await operator.pre_compute()

            cancel_order_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pre_compute_filters_by_exchange_order_ids(self, cancel_order_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        cancel_order_op_class, = cancel_order_operators_list

        order1 = _create_mock_order("order-1")
        order2 = _create_mock_order("order-2")
        order3 = _create_mock_order("order-3")
        mock_orders = [order1, order2, order3]

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=mock_orders,
        ), mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(side_effect=[True, True]),
        ) as cancel_order_mock:
            operator = cancel_order_op_class(
                SYMBOL,
                exchange_order_ids=["order-1", "order-3"],
            )
            await operator.pre_compute()

            assert operator.value == {"cancelled_orders": ["order-1", "order-3"]}
            assert cancel_order_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_pre_compute_filters_by_side(self, cancel_order_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        cancel_order_op_class, = cancel_order_operators_list

        buy_order = _create_mock_order("order-1", side="buy")
        sell_order = _create_mock_order("order-2", side="sell")
        mock_orders = [buy_order, sell_order]

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=mock_orders,
        ), mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(return_value=True),
        ) as cancel_order_mock:
            operator = cancel_order_op_class(
                SYMBOL,
                side="buy",
                exchange_order_ids=["order-1", "order-2"],
            )
            await operator.pre_compute()

            assert operator.value == {"cancelled_orders": ["order-1"]}
            cancel_order_mock.assert_awaited_once_with(buy_order, wait_for_cancelling=True)

    @pytest.mark.asyncio
    async def test_pre_compute_skips_cancelled_orders(self, cancel_order_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        cancel_order_op_class, = cancel_order_operators_list

        order1 = _create_mock_order("order-1")
        order1.is_cancelled = mock.Mock(return_value=True)
        order2 = _create_mock_order("order-2")
        mock_orders = [order1, order2]

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=mock_orders,
        ), mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(return_value=True),
        ) as cancel_order_mock:
            operator = cancel_order_op_class(
                SYMBOL,
                exchange_order_ids=["order-1", "order-2"],
            )
            await operator.pre_compute()

            assert operator.value == {"cancelled_orders": ["order-2"]}
            cancel_order_mock.assert_awaited_once_with(order2, wait_for_cancelling=True)

    @pytest.mark.asyncio
    async def test_pre_compute_skips_closed_orders(self, cancel_order_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        cancel_order_op_class, = cancel_order_operators_list

        order1 = _create_mock_order("order-1")
        order1.is_closed = mock.Mock(return_value=True)
        order2 = _create_mock_order("order-2")
        mock_orders = [order1, order2]

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=mock_orders,
        ), mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(return_value=True),
        ) as cancel_order_mock:
            operator = cancel_order_op_class(
                SYMBOL,
                exchange_order_ids=["order-1", "order-2"],
            )
            await operator.pre_compute()

            assert operator.value == {"cancelled_orders": ["order-2"]}
            cancel_order_mock.assert_awaited_once_with(order2, wait_for_cancelling=True)

    @pytest.mark.asyncio
    async def test_pre_compute_does_not_append_when_cancel_fails(self, cancel_order_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        cancel_order_op_class, = cancel_order_operators_list

        order1 = _create_mock_order("order-1")
        order2 = _create_mock_order("order-2")
        mock_orders = [order1, order2]

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=mock_orders,
        ), mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(side_effect=[False, True]),
        ) as cancel_order_mock:
            operator = cancel_order_op_class(
                SYMBOL,
                exchange_order_ids=["order-1", "order-2"],
            )
            await operator.pre_compute()

            assert operator.value == {"cancelled_orders": ["order-2"]}
            assert cancel_order_mock.await_count == 2

    def test_compute_without_pre_compute(self, cancel_order_operators_list):
        cancel_order_op_class, = cancel_order_operators_list
        operator = cancel_order_op_class(
            SYMBOL,
            exchange_order_ids=["order-1"],
        )
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="has not been pre_computed",
        ):
            operator.compute()

    @pytest.mark.asyncio
    async def test_pre_compute_uses_trading_mode_when_provided(
        self, cancel_order_operators_with_trading_mode, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        operators_list, mock_trading_mode, mock_dependencies = cancel_order_operators_with_trading_mode
        cancel_order_op_class, = operators_list

        order1 = _create_mock_order("order-1")
        mock_orders = [order1]

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=mock_orders,
        ):
            operator = cancel_order_op_class(
                SYMBOL,
                exchange_order_ids=["order-1"],
            )
            await operator.pre_compute()

            assert operator.value == {"cancelled_orders": ["order-1"]}
            mock_trading_mode.cancel_order.assert_awaited_once()
            call_args = mock_trading_mode.cancel_order.call_args
            assert call_args[0][0] == order1
            assert call_args[1]["wait_for_cancelling"] is True
            assert call_args[1]["dependencies"] is mock_dependencies

    @pytest.mark.asyncio
    async def test_cancel_order_call_as_dsl(self, interpreter, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader

        if SYMBOL not in exchange_manager.client_symbols:
            exchange_manager.client_symbols.append(SYMBOL)
        if SYMBOL not in exchange_manager.exchange_config.traded_symbol_pairs:
            exchange_manager.exchange_config.traded_symbol_pairs.append(SYMBOL)

        limit_buy = trading_personal_data.BuyLimitOrder(exchange_manager.trader)
        limit_buy.update(
            order_type=octobot_trading.enums.TraderOrderType.BUY_LIMIT,
            symbol=SYMBOL,
            exchange_order_id=EXCHANGE_ORDER_ID,
            current_price=decimal.Decimal("50000"),
            quantity=decimal.Decimal("0.01"),
            price=decimal.Decimal("50000"),
        )
        await exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(limit_buy)

        open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol=SYMBOL)
        assert len(open_orders) == 1
        assert open_orders[0].exchange_order_id == EXCHANGE_ORDER_ID

        result = await interpreter.interprete(
            f"cancel_order('{SYMBOL}', exchange_order_ids=['{EXCHANGE_ORDER_ID}'])"
        )
        assert result == {"cancelled_orders": [EXCHANGE_ORDER_ID]}

        open_orders_after = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol=SYMBOL)
        assert len(open_orders_after) == 0
        assert limit_buy.is_cancelled()

    @pytest.mark.asyncio
    async def test_cancel_order_call_as_dsl_with_side(self, interpreter, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader

        buy_order = _create_mock_order("order-buy", side="buy")
        mock_orders = [buy_order]

        with mock.patch.object(
            exchange_manager.exchange_personal_data.orders_manager,
            "get_open_orders",
            return_value=mock_orders,
        ), mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(return_value=True),
        ):
            result = await interpreter.interprete(
                f"cancel_order('{SYMBOL}', side='buy', exchange_order_ids=['order-buy'])"
            )
            assert result == {"cancelled_orders": ["order-buy"]}


class TestGetDependencies:
    """Tests for get_dependencies using DSL syntax and the interpreter."""

    @pytest.mark.parametrize(
        "maybe_exchange_manager_interpreter",
        ["interpreter", "no_exchange_manager_interpreter"],
        indirect=True,
    )
    def test_cancel_order_get_dependencies_from_interpreter(
        self, maybe_exchange_manager_interpreter
    ):
        maybe_exchange_manager_interpreter.prepare(
            f"cancel_order('{SYMBOL}', exchange_order_ids=['{EXCHANGE_ORDER_ID}'])"
        )
        assert maybe_exchange_manager_interpreter.get_dependencies() == [
            octobot_trading.dsl.SymbolDependency(symbol=SYMBOL),
        ]
        symbol = "ETH/USDT"
        maybe_exchange_manager_interpreter.prepare(
            f"cancel_order('{symbol}', tag='my_tag')"
        )
        assert maybe_exchange_manager_interpreter.get_dependencies() == [
            octobot_trading.dsl.SymbolDependency(symbol=symbol),
        ]
