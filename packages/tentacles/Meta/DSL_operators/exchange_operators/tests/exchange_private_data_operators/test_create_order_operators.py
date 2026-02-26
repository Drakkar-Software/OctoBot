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

import octobot_commons.constants as commons_constants
import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.symbols as commons_symbols
import octobot_trading.enums
import octobot_trading.personal_data as personal_data

import tentacles.Meta.DSL_operators.exchange_operators.exchange_private_data_operators.create_order_operators as create_order_operators

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    backtesting_config,
    fake_backtesting,
    backtesting_exchange_manager,
    backtesting_trader,
)

SYMBOL = "BTC/USDT"
AMOUNT = 0.01
PRICE = "50000"
MARK_PRICE = decimal.Decimal("50000")


def _create_mock_order(symbol: str = SYMBOL, side: str = "buy", order_type=None):
    order = mock.Mock()
    order.symbol = symbol
    order.side = octobot_trading.enums.TradeOrderSide(side)
    order.order_type = order_type or octobot_trading.enums.TraderOrderType.BUY_MARKET
    order.to_dict = mock.Mock(return_value={"symbol": symbol, "side": side})
    return order


@pytest_asyncio.fixture
async def create_order_operators_list(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    return create_order_operators.create_create_order_operators(exchange_manager)


@pytest_asyncio.fixture
async def interpreter(create_order_operators_list):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + create_order_operators_list
    )


def _ensure_portfolio_config(backtesting_trader, portfolio_content):
    _config, exchange_manager, _trader = backtesting_trader
    if commons_constants.CONFIG_SIMULATOR not in _config:
        _config[commons_constants.CONFIG_SIMULATOR] = {}
    if commons_constants.CONFIG_STARTING_PORTFOLIO not in _config[commons_constants.CONFIG_SIMULATOR]:
        _config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO] = {}
    _config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO].update(
        portfolio_content
    )
    exchange_manager.exchange_personal_data.portfolio_manager.apply_forced_portfolio(
        _config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]
    )


def _ensure_market_order_trading_context(backtesting_trader):
    """Set up portfolio, symbol config, and mark price for real simulated order creation."""
    _config, exchange_manager, _trader = backtesting_trader
    _ensure_portfolio_config(backtesting_trader, {"BTC": 0, "USDT": 100000})

    if SYMBOL not in exchange_manager.client_symbols:
        exchange_manager.client_symbols.append(SYMBOL)
    if SYMBOL not in exchange_manager.exchange_config.traded_symbol_pairs:
        exchange_manager.exchange_config.traded_symbol_pairs.append(SYMBOL)
        exchange_manager.exchange_config.traded_symbols.append(
            commons_symbols.parse_symbol(SYMBOL)
        )

    symbol_data = exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        SYMBOL, allow_creation=True
    )
    symbol_data.handle_mark_price_update(
        MARK_PRICE, octobot_trading.enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value
    )


def _ensure_sell_order_trading_context(backtesting_trader):
    """Set up portfolio with BTC for sell orders, symbol config, and mark price."""
    _config, exchange_manager, _trader = backtesting_trader
    _ensure_portfolio_config(backtesting_trader, {"BTC": 1.0, "USDT": 0})

    if SYMBOL not in exchange_manager.client_symbols:
        exchange_manager.client_symbols.append(SYMBOL)
    if SYMBOL not in exchange_manager.exchange_config.traded_symbol_pairs:
        exchange_manager.exchange_config.traded_symbol_pairs.append(SYMBOL)
        exchange_manager.exchange_config.traded_symbols.append(
            commons_symbols.parse_symbol(SYMBOL)
        )

    symbol_data = exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        SYMBOL, allow_creation=True
    )
    symbol_data.handle_mark_price_update(
        MARK_PRICE, octobot_trading.enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value
    )


class TestMarketOrderOperator:
    @pytest.mark.asyncio
    async def test_pre_compute_creates_market_order(
        self, create_order_operators_list, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        market_op_class, _limit_op_class, _stop_loss_op_class = create_order_operators_list
        mock_order = _create_mock_order()

        factory = market_op_class("buy", SYMBOL, AMOUNT).get_order_factory()
        with mock.patch.object(
            factory,
            "create_base_order_and_associated_elements",
            mock.AsyncMock(return_value=mock_order),
        ), mock.patch.object(
            factory,
            "create_order_on_exchange",
            mock.AsyncMock(return_value=mock_order),
        ):
            operator = market_op_class("buy", SYMBOL, AMOUNT)
            await operator.pre_compute()

            assert operator.value == {"symbol": SYMBOL, "side": "buy"}
            factory.create_base_order_and_associated_elements.assert_awaited_once()
            call_kwargs = factory.create_base_order_and_associated_elements.call_args[1]
            assert call_kwargs["symbol"] == SYMBOL
            assert call_kwargs["side"] == "buy"
            assert call_kwargs["amount"] == AMOUNT
            assert call_kwargs["order_type"] == octobot_trading.enums.TraderOrderType.BUY_MARKET

    @pytest.mark.asyncio
    async def test_pre_compute_sell_market_order(
        self, create_order_operators_list, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        market_op_class, _limit_op_class, _stop_loss_op_class = create_order_operators_list
        mock_order = _create_mock_order(side="sell")

        factory = market_op_class("sell", SYMBOL, AMOUNT).get_order_factory()
        with mock.patch.object(
            factory,
            "create_base_order_and_associated_elements",
            mock.AsyncMock(return_value=mock_order),
        ), mock.patch.object(
            factory,
            "create_order_on_exchange",
            mock.AsyncMock(return_value=mock_order),
        ):
            operator = market_op_class("sell", SYMBOL, AMOUNT)
            await operator.pre_compute()

            call_kwargs = factory.create_base_order_and_associated_elements.call_args[1]
            assert call_kwargs["order_type"] == octobot_trading.enums.TraderOrderType.SELL_MARKET

    @pytest.mark.asyncio
    async def test_pre_compute_raises_when_create_order_fails(
        self, create_order_operators_list, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        market_op_class, _limit_op_class, _stop_loss_op_class = create_order_operators_list
        mock_order = _create_mock_order()

        factory = market_op_class("buy", SYMBOL, AMOUNT).get_order_factory()
        with mock.patch.object(
            factory,
            "create_base_order_and_associated_elements",
            mock.AsyncMock(return_value=mock_order),
        ), mock.patch.object(
            factory,
            "create_order_on_exchange",
            mock.AsyncMock(return_value=None),
        ):
            operator = market_op_class("buy", SYMBOL, AMOUNT)
            with pytest.raises(
                octobot_commons.errors.DSLInterpreterError,
                match="Failed to create",
            ):
                await operator.pre_compute()

    def test_compute_without_pre_compute(self, create_order_operators_list):
        market_op_class, _limit_op_class, _stop_loss_op_class = create_order_operators_list
        operator = market_op_class("buy", SYMBOL, AMOUNT)
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="has not been pre_computed",
        ):
            operator.compute()


class TestLimitOrderOperator:
    @pytest.mark.asyncio
    async def test_pre_compute_creates_limit_order(
        self, create_order_operators_list, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        _market_op_class, limit_op_class, _stop_loss_op_class = create_order_operators_list
        mock_order = _create_mock_order(order_type=octobot_trading.enums.TraderOrderType.BUY_LIMIT)

        factory = limit_op_class("buy", SYMBOL, AMOUNT, PRICE).get_order_factory()
        with mock.patch.object(
            factory,
            "create_base_order_and_associated_elements",
            mock.AsyncMock(return_value=mock_order),
        ), mock.patch.object(
            factory,
            "create_order_on_exchange",
            mock.AsyncMock(return_value=mock_order),
        ):
            operator = limit_op_class("buy", SYMBOL, AMOUNT, PRICE)
            await operator.pre_compute()

            assert operator.value == {"symbol": SYMBOL, "side": "buy"}
            call_kwargs = factory.create_base_order_and_associated_elements.call_args[1]
            assert call_kwargs["symbol"] == SYMBOL
            assert call_kwargs["side"] == "buy"
            assert call_kwargs["amount"] == AMOUNT
            assert call_kwargs["price"] == PRICE
            assert call_kwargs["order_type"] == octobot_trading.enums.TraderOrderType.BUY_LIMIT


class TestStopLossOrderOperator:
    @pytest.mark.asyncio
    async def test_pre_compute_creates_stop_loss_order(
        self, create_order_operators_list, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        _market_op_class, _limit_op_class, stop_loss_op_class = create_order_operators_list
        mock_order = _create_mock_order(order_type=octobot_trading.enums.TraderOrderType.STOP_LOSS)

        factory = stop_loss_op_class("buy", SYMBOL, AMOUNT, PRICE).get_order_factory()
        with mock.patch.object(
            factory,
            "create_base_order_and_associated_elements",
            mock.AsyncMock(return_value=mock_order),
        ), mock.patch.object(
            factory,
            "create_order_on_exchange",
            mock.AsyncMock(return_value=mock_order),
        ):
            operator = stop_loss_op_class("buy", SYMBOL, AMOUNT, PRICE)
            await operator.pre_compute()

            call_kwargs = factory.create_base_order_and_associated_elements.call_args[1]
            assert call_kwargs["order_type"] == octobot_trading.enums.TraderOrderType.STOP_LOSS


class TestCreateOrderCallAsDsl:
    @pytest.mark.asyncio
    async def test_market_call_as_dsl(self, interpreter, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        _ensure_market_order_trading_context(backtesting_trader)

        result = await interpreter.interprete(
            f"market('buy', '{SYMBOL}', {AMOUNT})"
        )

        assert isinstance(result, dict)
        assert result["symbol"] == SYMBOL
        assert result["side"] == octobot_trading.enums.TradeOrderSide.BUY.value
        assert "id" in result or "exchange_id" in result

        all_orders = exchange_manager.exchange_personal_data.orders_manager.get_all_orders(
            symbol=SYMBOL
        )
        assert all_orders == []
        trades = exchange_manager.exchange_personal_data.trades_manager.get_trades()
        assert len(trades) == 1
        created_trade = trades[0]
        assert created_trade.trade_type == octobot_trading.enums.TraderOrderType.BUY_MARKET
        assert created_trade.side == octobot_trading.enums.TradeOrderSide.BUY
        assert created_trade.executed_price == MARK_PRICE
        assert created_trade.executed_quantity == decimal.Decimal(str(AMOUNT))

    @pytest.mark.asyncio
    async def test_limit_call_as_dsl(
        self, interpreter, backtesting_trader, create_order_operators_list
    ):
        _config, exchange_manager, _trader = backtesting_trader
        _ensure_market_order_trading_context(backtesting_trader)

        order_price = 45000
        result = await interpreter.interprete(
            f"limit('buy', '{SYMBOL}', {AMOUNT}, {order_price}, reduce_only=True)"
        )

        assert isinstance(result, dict)
        assert result["symbol"] == SYMBOL
        assert result["side"] == octobot_trading.enums.TradeOrderSide.BUY.value
        assert "id" in result or "exchange_id" in result

        all_orders = exchange_manager.exchange_personal_data.orders_manager.get_all_orders(
            symbol=SYMBOL
        )
        assert len(all_orders) == 1
        trades = exchange_manager.exchange_personal_data.trades_manager.get_trades()
        assert len(trades) == 0
        created_order = all_orders[0]
        assert isinstance(created_order, personal_data.BuyLimitOrder)
        assert created_order.origin_price == decimal.Decimal(str(order_price))
        assert created_order.origin_quantity == decimal.Decimal(str(AMOUNT))
        assert created_order.reduce_only == True

    @pytest.mark.asyncio
    async def test_limit_sell_with_take_profit_call_as_dsl(
        self, interpreter, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        _ensure_sell_order_trading_context(backtesting_trader)

        limit_price = 55000
        take_profit_price = 52000
        result = await interpreter.interprete(
            f"limit('sell', '{SYMBOL}', {AMOUNT}, price='{limit_price}', "
            f"take_profit_prices=['{take_profit_price}'])"
        )

        assert isinstance(result, dict)
        assert result["symbol"] == SYMBOL
        assert result["side"] == octobot_trading.enums.TradeOrderSide.SELL.value
        assert "id" in result or "exchange_id" in result

        all_orders = exchange_manager.exchange_personal_data.orders_manager.get_all_orders(
            symbol=SYMBOL
        )
        assert len(all_orders) == 1
        base_order = all_orders[0]
        assert isinstance(base_order, personal_data.SellLimitOrder)
        assert base_order.origin_price == decimal.Decimal(str(limit_price))
        assert base_order.origin_quantity == decimal.Decimal(str(AMOUNT))
        assert len(base_order.chained_orders) == 1
        tp_order = base_order.chained_orders[0]
        assert isinstance(tp_order, personal_data.BuyLimitOrder)
        assert tp_order.side == octobot_trading.enums.TradeOrderSide.BUY
        assert tp_order.origin_price == decimal.Decimal(str(take_profit_price))
        assert tp_order.origin_quantity == decimal.Decimal(str(AMOUNT))

    @pytest.mark.asyncio
    async def test_stop_loss_sell_call_as_dsl(self, interpreter, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        _ensure_sell_order_trading_context(backtesting_trader)

        stop_price = 48000
        result = await interpreter.interprete(
            f"stop_loss('sell', '{SYMBOL}', {AMOUNT}, price='{stop_price}')"
        )

        assert isinstance(result, dict)
        assert result["symbol"] == SYMBOL
        assert result["side"] == octobot_trading.enums.TradeOrderSide.SELL.value
        assert "id" in result or "exchange_id" in result

        all_orders = exchange_manager.exchange_personal_data.orders_manager.get_all_orders(
            symbol=SYMBOL
        )
        assert len(all_orders) == 1
        created_order = all_orders[0]
        assert isinstance(created_order, personal_data.StopLossOrder)
        assert created_order.side == octobot_trading.enums.TradeOrderSide.SELL
        assert created_order.origin_price == decimal.Decimal(str(stop_price))
        assert created_order.origin_quantity == decimal.Decimal(str(AMOUNT))

    @pytest.mark.asyncio
    async def test_limit_buy_with_take_profit_and_stop_loss_call_as_dsl(
        self, interpreter, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        _ensure_market_order_trading_context(backtesting_trader)

        limit_price = 50000
        take_profit_price_offset = "10%"
        stop_loss_price = 48000
        tag = "test_tag"
        cancel_policy = personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__
        active_order_swap_strategy = personal_data.TakeProfitFirstActiveOrderSwapStrategy.__name__
        result = await interpreter.interprete(
            f"limit('buy', '{SYMBOL}', {AMOUNT}, price='{limit_price}', "
            f"take_profit_prices=['{take_profit_price_offset}'], stop_loss_price='{stop_loss_price}', tag='{tag}', cancel_policy='{cancel_policy}', active_order_swap_strategy='{active_order_swap_strategy}')"
        )

        assert isinstance(result, dict)
        assert result["symbol"] == SYMBOL
        assert result["side"] == octobot_trading.enums.TradeOrderSide.BUY.value
        assert "id" in result or "exchange_id" in result

        all_orders = exchange_manager.exchange_personal_data.orders_manager.get_all_orders(
            symbol=SYMBOL
        )
        assert len(all_orders) == 1
        base_order = all_orders[0]
        assert isinstance(base_order, personal_data.BuyLimitOrder)
        assert base_order.origin_price == decimal.Decimal(str(limit_price))
        assert base_order.origin_quantity == decimal.Decimal(str(AMOUNT))
        assert base_order.tag == tag
        assert isinstance(base_order.cancel_policy, personal_data.ChainedOrderFillingPriceOrderCancelPolicy)
        assert len(base_order.chained_orders) == 2
        stop_orders = [o for o in base_order.chained_orders if personal_data.is_stop_order(o.order_type)]
        tp_orders = [o for o in base_order.chained_orders if not personal_data.is_stop_order(o.order_type)]
        assert len(stop_orders) == 1
        assert len(tp_orders) == 1
        assert isinstance(stop_orders[0], personal_data.StopLossOrder)
        assert isinstance(tp_orders[0], personal_data.SellLimitOrder)
        assert tp_orders[0].tag == tag
        assert stop_orders[0].tag == tag
        assert stop_orders[0].side == octobot_trading.enums.TradeOrderSide.SELL
        assert stop_orders[0].origin_price == decimal.Decimal(str(stop_loss_price))
        assert stop_orders[0].origin_quantity == decimal.Decimal(str(AMOUNT))
        assert tp_orders[0].side == octobot_trading.enums.TradeOrderSide.SELL
        assert tp_orders[0].origin_price == decimal.Decimal("55000") # 50k + 10%
        assert tp_orders[0].origin_quantity == decimal.Decimal(str(AMOUNT))
        order_group = tp_orders[0].order_group
        assert isinstance(order_group, personal_data.OneCancelsTheOtherOrderGroup)
        assert isinstance(order_group.active_order_swap_strategy, personal_data.TakeProfitFirstActiveOrderSwapStrategy) # non default strategy
        assert tp_orders[0].order_group is stop_orders[0].order_group

    @pytest.mark.asyncio
    async def test_limit_buy_with_many_take_profits_and_a_stop_loss_call_as_dsl(
        self, interpreter, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        _ensure_market_order_trading_context(backtesting_trader)

        limit_price = 50000
        take_profit_price_offset_1 = "10%"
        take_profit_price_offset_2 = "20%"
        take_profit_price_offset_3 = "30%"
        take_profit_volume_percents = [50, 20, 30]
        stop_loss_price = 48000
        trailing_profile = personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT.value
        result = await interpreter.interprete(
            f"limit('buy', '{SYMBOL}', {AMOUNT}, price='{limit_price}', "
            f"take_profit_prices=['{take_profit_price_offset_1}', '{take_profit_price_offset_2}', '{take_profit_price_offset_3}'], take_profit_volume_percents=['{take_profit_volume_percents[0]}', '{take_profit_volume_percents[1]}', '{take_profit_volume_percents[2]}'], stop_loss_price='{stop_loss_price}', trailing_profile='{trailing_profile}')"
        )

        assert isinstance(result, dict)
        assert result["symbol"] == SYMBOL
        assert result["side"] == octobot_trading.enums.TradeOrderSide.BUY.value
        assert "id" in result or "exchange_id" in result

        all_orders = exchange_manager.exchange_personal_data.orders_manager.get_all_orders(
            symbol=SYMBOL
        )
        assert len(all_orders) == 1
        base_order = all_orders[0]
        assert isinstance(base_order, personal_data.BuyLimitOrder)
        assert base_order.origin_price == decimal.Decimal(str(limit_price))
        assert base_order.origin_quantity == decimal.Decimal(str(AMOUNT))
        assert len(base_order.chained_orders) == 4
        stop_orders = [o for o in base_order.chained_orders if personal_data.is_stop_order(o.order_type)]
        tp_orders = [o for o in base_order.chained_orders if not personal_data.is_stop_order(o.order_type)]
        assert len(stop_orders) == 1
        assert len(tp_orders) == 3
        assert isinstance(stop_orders[0], personal_data.StopLossOrder)
        assert isinstance(tp_orders[0], personal_data.SellLimitOrder)
        assert stop_orders[0].side == octobot_trading.enums.TradeOrderSide.SELL
        assert stop_orders[0].origin_price == decimal.Decimal(str(stop_loss_price))
        assert stop_orders[0].origin_quantity == decimal.Decimal(str(AMOUNT))
        for i, tp_order in enumerate(tp_orders):
            assert tp_order.side == octobot_trading.enums.TradeOrderSide.SELL
            assert tp_order.origin_price == decimal.Decimal("50000") * decimal.Decimal(str(1 + (i + 1) * 0.1))
            assert tp_order.origin_quantity == decimal.Decimal(str(AMOUNT)) * decimal.Decimal(str(take_profit_volume_percents[i] / 100))
            order_group = tp_order.order_group
            assert isinstance(order_group, personal_data.TrailingOnFilledTPBalancedOrderGroup)
            assert isinstance(order_group.active_order_swap_strategy, personal_data.StopFirstActiveOrderSwapStrategy) # default strategy
            assert tp_order.order_group is stop_orders[0].order_group