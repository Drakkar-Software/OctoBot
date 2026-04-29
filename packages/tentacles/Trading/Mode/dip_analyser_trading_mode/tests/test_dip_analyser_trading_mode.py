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
import pytest
import pytest_asyncio
import os.path
import asyncio
import mock
import decimal

import async_channel.util as channel_util
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.enums as commons_enum
import octobot_commons.tests.test_config as test_config
import octobot_backtesting.api as backtesting_api
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as exchanges
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.modes.script_keywords as script_keywords
import octobot_commons.constants as commons_constants
import tentacles.Evaluator.TA as TA
import tentacles.Evaluator.Strategies as Strategies
import tentacles.Trading.Mode as Mode
import tests.test_utils.memory_check_util as memory_check_util
import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def tools():
    trader = None
    try:
        tentacles_manager_api.reload_tentacle_info()
        producer, consumer, trader = await _get_tools()
        yield producer, consumer, trader
    finally:
        if trader:
            await _stop(trader.exchange_manager)


async def test_run_independent_backtestings_with_memory_check():
    """
    Should always be called first here to avoid other tests' related memory check issues
    """
    tentacles_setup_config = tentacles_manager_api.create_tentacles_setup_config_with_tentacles(
        Mode.DipAnalyserTradingMode,
        Strategies.DipAnalyserStrategyEvaluator,
        TA.KlingerOscillatorReversalConfirmationMomentumEvaluator,
        TA.RSIWeightMomentumEvaluator
    )
    config = test_config.load_test_config()
    config[commons_constants.CONFIG_TIME_FRAME] = [commons_enum.TimeFrames.FOUR_HOURS]
    await memory_check_util.run_independent_backtestings_with_memory_check(config, tentacles_setup_config)


async def test_init(tools):
    producer, consumer, trader = tools
    # trading mode
    assert producer.trading_mode is consumer.trading_mode
    assert producer.trading_mode.sell_orders_per_buy == 3

    # producer
    assert producer.last_buy_candle is None
    assert producer.first_trigger

    # consumer
    assert consumer.sell_targets_by_order_id == {}
    assert consumer.PRICE_WEIGH_TO_PRICE_PERCENT == {
        1: decimal.Decimal("1.04"),
        2: decimal.Decimal("1.07"),
        3: decimal.Decimal("1.1"),
    }
    assert consumer.VOLUME_WEIGH_TO_VOLUME_PERCENT == {
        1: decimal.Decimal("0.5"),
        2: decimal.Decimal("0.7"),
        3: decimal.Decimal("1"),
    }


async def test_create_limit_bottom_order(tools):
    producer, consumer, trader = tools

    price = decimal.Decimal("1000")
    market_quantity = decimal.Decimal("2")
    volume_weight = decimal.Decimal("1")
    risk_multiplier = decimal.Decimal("1.1")

    market_status = producer.exchange_manager.exchange.get_market_status(producer.trading_mode.symbol, with_fixer=False)
    _origin_decimal_adapt_order_quantity_because_fees = trading_personal_data.decimal_adapt_order_quantity_because_fees

    def _decimal_adapt_order_quantity_because_fees(
        exchange_manager, symbol: str, order_type: trading_enums.TraderOrderType, quantity: decimal.Decimal,
        price: decimal.Decimal, side: trading_enums.TradeOrderSide,
    ):
        return quantity

    with mock.patch.object(
            trading_personal_data, "decimal_adapt_order_quantity_because_fees",
            mock.Mock(side_effect=_decimal_adapt_order_quantity_because_fees)
    ) as decimal_adapt_order_quantity_because_fees_mock:
        await producer._create_bottom_order(1, volume_weight, 1)
        # create as task to allow creator's queue to get processed
        await asyncio.create_task(_check_open_orders_count(trader, 1))
        await asyncio_tools.wait_asyncio_next_cycle()

        order = trading_api.get_open_orders(trader.exchange_manager)[0]
        adapted_args = list(decimal_adapt_order_quantity_because_fees_mock.mock_calls[0].args)
        adapted_args[3] = trading_personal_data.decimal_adapt_quantity(market_status, adapted_args[3])
        adapted_args[4] = trading_personal_data.decimal_adapt_price(market_status, adapted_args[4])
        assert adapted_args == [
            producer.exchange_manager, producer.trading_mode.symbol, trading_enums.TraderOrderType.BUY_LIMIT,
            order.origin_quantity,
            order.origin_price,
            trading_enums.TradeOrderSide.BUY,
        ]

        assert isinstance(order, trading_personal_data.BuyLimitOrder)
        expected_quantity = market_quantity * risk_multiplier * \
            consumer.VOLUME_WEIGH_TO_VOLUME_PERCENT[volume_weight] * \
            consumer.SOFT_MAX_CURRENCY_RATIO
        assert order.origin_quantity == expected_quantity

        expected_price = price * consumer.LIMIT_PRICE_MULTIPLIER
        assert order.origin_price == expected_price
        portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
        assert portfolio.get_currency_portfolio("USDT").available > trading_constants.ZERO

        assert order.order_id in consumer.sell_targets_by_order_id


async def test_create_market_bottom_order(tools):
    producer, consumer, trader = tools

    price = decimal.Decimal("1000")
    market_quantity = decimal.Decimal("2")
    volume_weight = decimal.Decimal("1")
    risk_multiplier = decimal.Decimal("1.1")
    consumer.USE_BUY_MARKET_ORDERS_VALUE = True
    trades = trading_api.get_trade_history(trader.exchange_manager)
    assert trades == []

    market_status = producer.exchange_manager.exchange.get_market_status(producer.trading_mode.symbol, with_fixer=False)
    _origin_decimal_adapt_order_quantity_because_fees = trading_personal_data.decimal_adapt_order_quantity_because_fees

    def _decimal_adapt_order_quantity_because_fees(
        exchange_manager, symbol: str, order_type: trading_enums.TraderOrderType, quantity: decimal.Decimal,
        price: decimal.Decimal, side: trading_enums.TradeOrderSide,
    ):
        return quantity

    with mock.patch.object(
            trading_personal_data, "decimal_adapt_order_quantity_because_fees",
            mock.Mock(side_effect=_decimal_adapt_order_quantity_because_fees)
    ) as decimal_adapt_order_quantity_because_fees_mock:
        await producer._create_bottom_order(1, volume_weight, 1)
        # create as task to allow creator's queue to get processed (market order is instantly filled)
        await asyncio.create_task(_check_open_orders_count(trader, 0))
        await asyncio_tools.wait_asyncio_next_cycle()

        trade = trading_api.get_trade_history(trader.exchange_manager)[0]
        adapted_args = list(decimal_adapt_order_quantity_because_fees_mock.mock_calls[0].args)
        adapted_args[3] = trading_personal_data.decimal_adapt_quantity(market_status, adapted_args[3])
        adapted_args[4] = trading_personal_data.decimal_adapt_price(market_status, adapted_args[4])
        assert adapted_args == [
            producer.exchange_manager, producer.trading_mode.symbol, trading_enums.TraderOrderType.BUY_MARKET,
            trade.origin_quantity,
            trade.origin_price,
            trading_enums.TradeOrderSide.BUY,
        ]

        assert trade.trade_type == trading_enums.TraderOrderType.BUY_MARKET
        expected_quantity = market_quantity * risk_multiplier * \
            consumer.VOLUME_WEIGH_TO_VOLUME_PERCENT[volume_weight] * \
            consumer.SOFT_MAX_CURRENCY_RATIO
        assert trade.origin_quantity == expected_quantity

        # no price multiplier used as it is a market order (use market price)
        assert trade.origin_price == price
        portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
        assert portfolio.get_currency_portfolio("USDT").available > trading_constants.ZERO

        assert trade.origin_order_id in consumer.sell_targets_by_order_id


async def test_create_bottom_order_with_configured_quantity(tools):
    producer, consumer, trader = tools

    producer.trading_mode.trading_config[trading_constants.CONFIG_BUY_ORDER_AMOUNT] = \
        f"20{script_keywords.QuantityType.PERCENT.value}"
    price = decimal.Decimal("1000")
    market_quantity = decimal.Decimal("2")
    volume_weight = decimal.Decimal("1")
    risk_multiplier = decimal.Decimal("1.1")
    # force portfolio value
    trader.exchange_manager.exchange_personal_data. \
        portfolio_manager.portfolio_value_holder.portfolio_current_value = decimal.Decimal(1)
    await producer._create_bottom_order(1, volume_weight, 1)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))
    await asyncio_tools.wait_asyncio_next_cycle()

    order = trading_api.get_open_orders(trader.exchange_manager)[0]
    default_expected_quantity = market_quantity * risk_multiplier * \
        consumer.VOLUME_WEIGH_TO_VOLUME_PERCENT[volume_weight] * \
        consumer.SOFT_MAX_CURRENCY_RATIO
    expected_quantity = market_quantity * risk_multiplier * \
        consumer.VOLUME_WEIGH_TO_VOLUME_PERCENT[volume_weight] * \
        decimal.Decimal("0.2")
    assert default_expected_quantity != expected_quantity
    assert order.origin_quantity == expected_quantity

    expected_price = price * consumer.LIMIT_PRICE_MULTIPLIER
    assert order.origin_price == expected_price
    portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    assert trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available  > trading_constants.ZERO

    assert order.order_id in consumer.sell_targets_by_order_id


async def test_create_too_large_bottom_order(tools):
    producer, consumer, trader = tools

    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available = decimal.Decimal("200000000000000")
    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").total = decimal.Decimal("200000000000000")
    await producer._create_bottom_order(1, 1, 1)
    # create as task to allow creator's queue to get processed
    for _ in range(37):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, 37))
    assert trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available > trading_constants.ZERO


async def test_create_too_small_bottom_order(tools):
    producer, consumer, trader = tools

    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available = decimal.Decimal("0.01")
    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").total = decimal.Decimal("0.01")
    await producer._create_bottom_order(1, 1, 1)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 0))
    assert trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available == decimal.Decimal("0.01")


async def test_create_bottom_order_replace_current(tools):
    producer, consumer, trader = tools

    price = decimal.Decimal("1000")
    market_quantity = decimal.Decimal("2")
    volume_weight = decimal.Decimal("1")
    risk_multiplier = decimal.Decimal("1.1")
    portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio

    # first order
    await producer._create_bottom_order(1, volume_weight, 1)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))
    await asyncio_tools.wait_asyncio_next_cycle()

    first_order = trading_api.get_open_orders(trader.exchange_manager)[0]
    assert first_order.status == trading_enums.OrderStatus.OPEN
    expected_quantity = market_quantity * risk_multiplier * \
        consumer.VOLUME_WEIGH_TO_VOLUME_PERCENT[volume_weight] * consumer.SOFT_MAX_CURRENCY_RATIO
    assert first_order.origin_quantity == expected_quantity
    expected_price = price * consumer.LIMIT_PRICE_MULTIPLIER
    assert first_order.origin_price == expected_price
    available_after_order = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available
    assert available_after_order > trading_constants.ZERO
    assert first_order.order_id in consumer.sell_targets_by_order_id

    # second order, same weight
    await producer._create_bottom_order(1, volume_weight, 1)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))
    await asyncio_tools.wait_asyncio_next_cycle()

    second_order = trading_api.get_open_orders(trader.exchange_manager)[0]
    assert first_order.status == trading_enums.OrderStatus.CANCELED
    assert second_order.status == trading_enums.OrderStatus.OPEN
    assert second_order is not first_order
    assert second_order.origin_quantity == first_order.origin_quantity
    assert second_order.origin_price == first_order.origin_price
    assert trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available == available_after_order
    # order still in sell_targets_by_order_id: cancelling orders doesn't remove them for this
    assert first_order.order_id in consumer.sell_targets_by_order_id
    assert second_order.order_id in consumer.sell_targets_by_order_id

    # third order, different weight
    volume_weight = 3
    await producer._create_bottom_order(1, volume_weight, 1)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))
    await asyncio_tools.wait_asyncio_next_cycle()

    third_order = trading_api.get_open_orders(trader.exchange_manager)[0]
    assert second_order.status == trading_enums.OrderStatus.CANCELED
    assert third_order.status == trading_enums.OrderStatus.OPEN
    assert third_order is not second_order and third_order is not first_order
    expected_quantity = market_quantity * \
        consumer.VOLUME_WEIGH_TO_VOLUME_PERCENT[volume_weight] * consumer.SOFT_MAX_CURRENCY_RATIO
    assert third_order.origin_quantity != first_order.origin_quantity
    assert third_order.origin_quantity == expected_quantity
    assert third_order.origin_price == first_order.origin_price
    available_after_third_order = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available
    assert available_after_third_order < available_after_order
    assert second_order.order_id in consumer.sell_targets_by_order_id
    assert third_order.order_id in consumer.sell_targets_by_order_id

    # fill third order
    await _fill_order(third_order, trader, trigger_update_callback=False, consumer=consumer)

    # fourth order: can't be placed: an order on this candle got filled
    volume_weight = 3
    await producer._create_bottom_order(1, volume_weight, 1)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 0))

    # fifth order: in the next candle
    volume_weight = 2
    new_market_quantity = decimal.Decimal(f'{trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available}') \
        / price
    await producer._create_bottom_order(2, volume_weight, 1)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))
    await asyncio_tools.wait_asyncio_next_cycle()

    fifth_order = trading_api.get_open_orders(trader.exchange_manager)[0]
    assert third_order.status == trading_enums.OrderStatus.FILLED
    assert fifth_order.status == trading_enums.OrderStatus.OPEN
    assert fifth_order is not third_order and fifth_order is not second_order and fifth_order is not first_order
    expected_quantity = new_market_quantity * risk_multiplier * \
        consumer.VOLUME_WEIGH_TO_VOLUME_PERCENT[volume_weight] * consumer.SOFT_MAX_CURRENCY_RATIO
    assert fifth_order.origin_quantity != first_order.origin_quantity
    assert fifth_order.origin_quantity != third_order.origin_quantity
    assert fifth_order.origin_quantity == trading_personal_data.decimal_trunc_with_n_decimal_digits(expected_quantity, 8)
    assert fifth_order.origin_price == first_order.origin_price
    assert trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available < available_after_third_order
    assert first_order.order_id in consumer.sell_targets_by_order_id
    assert second_order.order_id in consumer.sell_targets_by_order_id

    # third_order still in _get_order_identifier to keep history
    assert third_order.order_id in consumer.sell_targets_by_order_id
    assert fifth_order.order_id in consumer.sell_targets_by_order_id


async def test_create_sell_orders_without_stop_loss(tools):
    producer, consumer, trader = tools

    sell_quantity = decimal.Decimal("5")
    sell_target = 2
    buy_price = decimal.Decimal("100")
    order_id = "a"
    consumer.STOP_LOSS_PRICE_MULTIPLIER = trading_constants.ZERO
    consumer.sell_targets_by_order_id[order_id] = sell_target
    await producer._create_sell_order_if_enabled(order_id, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    for _ in range(consumer.trading_mode.sell_orders_per_buy):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    assert all(o.associated_entry_ids == ["a"] for o in open_orders)
    assert all(isinstance(o, trading_personal_data.SellLimitOrder) for o in open_orders)
    assert not any(isinstance(o, trading_personal_data.StopLossOrder) for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    # rounding because orders to create volumes are X.33333
    assert sell_quantity * decimal.Decimal("0.9999") <= total_sell_quantity <= sell_quantity

    max_price = buy_price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[sell_target]
    increment = (max_price - buy_price) / consumer.trading_mode.sell_orders_per_buy
    assert open_orders[0].origin_price == \
           trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + increment, 8)
    assert open_orders[1].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + 2 * increment, 8)
    assert open_orders[2].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + 3 * increment, 8)

    # now fill a sell order
    await _fill_order(open_orders[0], trader, trigger_update_callback=False, consumer=consumer)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy - 1))
    sell_quantity = decimal.Decimal("3")
    sell_target = 3
    buy_price = decimal.Decimal("2525")
    order_id_2 = "b"
    consumer.sell_targets_by_order_id[order_id_2] = sell_target
    await producer._create_sell_order_if_enabled(order_id_2, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    for _ in range(consumer.trading_mode.sell_orders_per_buy):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy * 2 - 1))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    assert all(o.associated_entry_ids == ["a"] for o in open_orders[:2])
    assert all(o.associated_entry_ids == ["b"] for o in open_orders[2:])
    assert all(isinstance(o, trading_personal_data.SellLimitOrder) for o in open_orders)
    assert not any(isinstance(o, trading_personal_data.StopLossOrder) for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders if o.origin_price > 150)
    assert total_sell_quantity == sell_quantity

    max_price = buy_price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[sell_target]
    increment = (max_price - buy_price) / consumer.trading_mode.sell_orders_per_buy
    assert open_orders[2 + 0].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + increment, 8)
    assert open_orders[2 + 1].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + 2 * increment, 8)
    assert open_orders[2 + 2].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + 3 * increment, 8)

    # now fill a sell order
    await _fill_order(open_orders[-1], trader, trigger_update_callback=False, consumer=consumer)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy * 2 - 2))


async def test_create_sell_orders_with_stop_loss(tools):
    producer, consumer, trader = tools

    trader.enable_inactive_orders = True
    sell_quantity = decimal.Decimal("5")
    sell_target = 2
    buy_price = decimal.Decimal("100")
    order_id = "a"
    consumer.STOP_LOSS_PRICE_MULTIPLIER = decimal.Decimal("0.75")
    stop_price = consumer.STOP_LOSS_PRICE_MULTIPLIER * buy_price
    consumer.sell_targets_by_order_id[order_id] = sell_target
    await producer._create_sell_order_if_enabled(order_id, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    for _ in range(consumer.trading_mode.sell_orders_per_buy):
        await asyncio_tools.wait_asyncio_next_cycle()
    # * 2 to account for the stop order associated to each sell order
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy * 2))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.associated_entry_ids == ["a"] for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    assert any(isinstance(o, (trading_personal_data.SellLimitOrder, trading_personal_data.StopLossOrder))
               for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    # rounding because orders to create volumes are X.33333
    assert sell_quantity * decimal.Decimal("0.9999") * 2 <= total_sell_quantity <= sell_quantity * 2

    # ensure order quantity and groups
    limit_orders = [o for o in open_orders if isinstance(o, trading_personal_data.SellLimitOrder)]
    stop_orders = [o for o in open_orders if isinstance(o, trading_personal_data.StopLossOrder)]
    assert len(limit_orders) == len(stop_orders)
    for limit, stop in zip(limit_orders, stop_orders):
        assert isinstance(limit.order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)
        assert limit.order_group is stop.order_group
        assert limit.origin_quantity == stop.origin_quantity
        assert limit.origin_price > stop.origin_price
        assert stop.origin_price == stop_price
        assert stop.is_active is True
        assert limit.is_active is False
        group_orders = trader.exchange_manager.exchange_personal_data.orders_manager.get_order_from_group(
            limit.order_group.name
        )
        assert group_orders == [limit, stop]

    # now fill a sell order
    await _fill_order(limit_orders[0], trader, trigger_update_callback=False, consumer=consumer, closed_orders_count=2)
    # create as task to allow creator's queue to get processed
    # also check that associated stop loss is cancelled
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy * 2 - 2))
    sell_quantity = decimal.Decimal("3")
    sell_target = 3
    buy_price = decimal.Decimal("2525")
    order_id_2 = "b"
    consumer.sell_targets_by_order_id[order_id_2] = sell_target
    await producer._create_sell_order_if_enabled(order_id_2, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    for _ in range(consumer.trading_mode.sell_orders_per_buy):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy * 2 * 2 - 2))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders if o.origin_price > 150)
    assert total_sell_quantity == sell_quantity * 2

    max_price = buy_price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[sell_target]
    increment = (max_price - buy_price) / consumer.trading_mode.sell_orders_per_buy
    limit_orders = [o for o in open_orders if isinstance(o, trading_personal_data.SellLimitOrder)]
    stop_orders = [o for o in open_orders if isinstance(o, trading_personal_data.StopLossOrder)]
    assert limit_orders[2 + 0].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + increment, 8)
    assert limit_orders[2 + 1].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + 2 * increment, 8)
    assert limit_orders[2 + 2].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + 3 * increment, 8)

    # now fill a stop order
    await _fill_order(stop_orders[-1], trader, trigger_update_callback=False, consumer=consumer, closed_orders_count=2)
    # create as task to allow creator's queue to get processed
    # associated sell order gets cancelled
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy * 2 * 2 - 2 * 2))


async def test_create_too_large_sell_orders(tools):
    producer, consumer, trader = tools

    # case 1: too many orders to create: problem
    sell_quantity = decimal.Decimal("500000000")
    sell_target = 2
    buy_price = decimal.Decimal("10000000")
    portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").available = sell_quantity
    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").total = sell_quantity
    order_id = "a"
    consumer.sell_targets_by_order_id[order_id] = sell_target
    await producer._create_sell_order_if_enabled(order_id, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 0))

    # case 2: create split sell orders
    sell_quantity = decimal.Decimal("5000000")
    buy_price = decimal.Decimal("3000000")
    await producer._create_sell_order_if_enabled(order_id, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    for _ in range(17):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, 17))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    # rounding because orders to create volumes are with truncated decimals
    assert sell_quantity * decimal.Decimal("0.9999") <= total_sell_quantity <= sell_quantity

    max_price = buy_price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[sell_target]
    increment = (max_price - buy_price) / 17
    assert open_orders[0].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(buy_price + increment, 8)
    assert open_orders[-1].origin_price == max_price


async def test_create_too_small_sell_orders(tools):
    producer, consumer, trader = tools

    # case 1: not enough to create any order: problem
    sell_quantity = decimal.Decimal("0.001")
    sell_target = 2
    buy_price = decimal.Decimal("0.001")
    order_id = "a"
    consumer.sell_targets_by_order_id[order_id] = sell_target
    await producer._create_sell_order_if_enabled(order_id, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 0))

    # case 2: create less than 3 orders: 1 order
    sell_quantity = decimal.Decimal("0.1")
    buy_price = decimal.Decimal("0.01")
    await producer._create_sell_order_if_enabled(order_id, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert len(open_orders) == 1
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    assert total_sell_quantity == sell_quantity

    max_price = buy_price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[sell_target]
    assert open_orders[0].origin_price == max_price

    # case 3: create less than 3 orders: 2 orders
    sell_quantity = decimal.Decimal("0.2")
    sell_target = 2
    buy_price = decimal.Decimal("0.01")
    # keep same order id to test no issue with it
    await producer._create_sell_order_if_enabled(order_id, sell_quantity, buy_price)
    # create as task to allow creator's queue to get processed
    for _ in range(3):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, 3))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    second_total_sell_quantity = sum(o.origin_quantity for o in open_orders if o.origin_price >= 0.0107)
    assert decimal.Decimal(f"{second_total_sell_quantity}") == sell_quantity

    max_price = buy_price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[sell_target]
    increment = (max_price - buy_price) / 2
    assert open_orders[1].origin_price == buy_price + increment
    assert open_orders[2].origin_price == max_price


async def test_order_fill_callback_with_limit_entry(tools):
    producer, consumer, trader = tools

    volume_weight = 1
    price_weight = 1
    await producer._create_bottom_order(1, volume_weight, price_weight)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))

    # change weights to ensure no interference
    volume_weight = 3
    price_weight = 3

    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    to_fill_order = open_orders[0]
    await _fill_order(to_fill_order, trader, consumer=consumer)
    # create as task to allow creator's queue to get processed
    for _ in range(consumer.trading_mode.sell_orders_per_buy):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy))

    assert to_fill_order.status == trading_enums.OrderStatus.FILLED
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    assert to_fill_order.origin_quantity * decimal.Decimal("0.95") <= total_sell_quantity <= to_fill_order.origin_quantity

    price = decimal.Decimal(f"{to_fill_order.filled_price}")
    max_price = price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[1]
    increment = (max_price - price) / consumer.trading_mode.sell_orders_per_buy
    assert open_orders[0].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + increment, 8)
    assert open_orders[1].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + 2 * increment, 8)
    assert open_orders[2].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + 3 * increment, 8)

    # now fill a sell order
    await _fill_order(open_orders[0], trader, consumer=consumer)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy - 1))

    # new buy order
    await producer._create_bottom_order(2, volume_weight, price_weight)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy))


async def test_order_fill_callback_with_market_entry(tools):
    producer, consumer, trader = tools

    volume_weight = 1
    price_weight = 1
    consumer.USE_BUY_MARKET_ORDERS_VALUE = True
    await producer._create_bottom_order(1, volume_weight, price_weight)
    # create as task to allow creator's queue to get processed
    # market order is instantly filled
    await asyncio.create_task(_check_open_orders_count(trader, 0))

    entry = trading_api.get_trade_history(trader.exchange_manager)[0]

    # create as task to allow creator's queue to get processed
    for _ in range(consumer.trading_mode.sell_orders_per_buy):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy))

    assert entry.status == trading_enums.OrderStatus.FILLED
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    assert entry.origin_quantity * decimal.Decimal("0.95") <= total_sell_quantity <= entry.origin_quantity

    price = decimal.Decimal(f"{entry.executed_price}")
    max_price = price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[1]
    increment = (max_price - price) / consumer.trading_mode.sell_orders_per_buy
    assert open_orders[0].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + increment, 8)
    assert open_orders[1].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + 2 * increment, 8)
    assert open_orders[2].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + 3 * increment, 8)


async def test_order_fill_callback_without_fees(tools):
    producer, consumer, trader = tools

    producer.ignore_exchange_fees = True

    volume_weight = 1
    price_weight = 1
    await producer._create_bottom_order(1, volume_weight, price_weight)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))

    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    to_fill_order = open_orders[0]
    await _fill_order(to_fill_order, trader, consumer=consumer)
    # create as task to allow creator's queue to get processed
    for _ in range(consumer.trading_mode.sell_orders_per_buy):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy))

    assert to_fill_order.status == trading_enums.OrderStatus.FILLED
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    assert total_sell_quantity == to_fill_order.origin_quantity


async def test_order_fill_callback_without_fees_adapted_rounding(tools):
    producer, consumer, trader = tools

    producer.ignore_exchange_fees = True

    volume_weight = 1
    price_weight = 1
    await producer._create_bottom_order(1, volume_weight, price_weight)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))

    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    to_fill_order = open_orders[0]
    to_fill_order.origin_quantity = decimal.Decimal("0.000167")
    to_fill_order.origin_price = decimal.Decimal("200")

    await _fill_order(to_fill_order, trader, consumer=consumer)
    # create as task to allow creator's queue to get processed
    for _ in range(consumer.trading_mode.sell_orders_per_buy):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, consumer.trading_mode.sell_orders_per_buy))

    assert to_fill_order.status == trading_enums.OrderStatus.FILLED
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    assert total_sell_quantity == to_fill_order.origin_quantity


async def test_order_fill_callback_not_in_db(tools):
    producer, consumer, trader = tools

    await producer._create_bottom_order(2, 1, 1)
    # create as task to allow creator's queue to get processed
    await asyncio.create_task(_check_open_orders_count(trader, 1))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)
    to_fill_order = open_orders[0]
    await _fill_order(to_fill_order, trader, trigger_update_callback=False, consumer=consumer)

    # remove order from db
    consumer.sell_targets_by_order_id = {}
    await consumer.trading_mode._order_notification_callback(None,
                                                             trader.exchange_manager.id,
                                                             None,
                                                             symbol=to_fill_order.symbol,
                                                             order=to_fill_order.to_dict(),
                                                             update_type=trading_enums.OrderUpdateType.STATE_CHANGE.value,
                                                             is_from_bot=True)
    # create as task to allow creator's queue to get processed
    for _ in range(3):
        await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, 3))
    open_orders = trading_api.get_open_orders(trader.exchange_manager)

    assert all(o.status == trading_enums.OrderStatus.OPEN for o in open_orders)
    assert all(o.side == trading_enums.TradeOrderSide.SELL for o in open_orders)
    total_sell_quantity = sum(o.origin_quantity for o in open_orders)
    assert to_fill_order.origin_quantity * decimal.Decimal("0.95") <= total_sell_quantity <= to_fill_order.origin_quantity

    price = decimal.Decimal(to_fill_order.filled_price)
    max_price = price * consumer.PRICE_WEIGH_TO_PRICE_PERCENT[consumer.DEFAULT_SELL_TARGET]
    increment = (max_price - price) / consumer.trading_mode.sell_orders_per_buy
    assert open_orders[0].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + increment, 8)
    assert open_orders[1].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + 2 * increment, 8)
    assert open_orders[2].origin_price == \
        trading_personal_data.decimal_trunc_with_n_decimal_digits(price + 3 * increment, 8)


async def _check_open_orders_count(trader, count):
    assert len(trading_api.get_open_orders(trader.exchange_manager)) == count


async def _get_tools(symbol="BTC/USDT"):
    config = test_config.load_test_config()
    config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 2000
    exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
    exchange_manager.tentacles_setup_config = test_utils_config.get_tentacles_setup_config()

    # use backtesting not to spam exchanges apis
    exchange_manager.is_simulated = True
    exchange_manager.is_backtesting = True
    exchange_manager.use_cached_markets = False
    backtesting = await backtesting_api.initialize_backtesting(
        config,
        exchange_ids=[exchange_manager.id],
        matrix_id=None,
        data_files=[os.path.join(test_config.TEST_CONFIG_FOLDER,
                                 "AbstractExchangeHistoryCollector_1586017993.616272.data")])
    exchange_manager.exchange = exchanges.ExchangeSimulator(
        exchange_manager.config, exchange_manager, backtesting
    )
    await exchange_manager.exchange.initialize()
    for exchange_channel_class_type in [exchanges_channel.ExchangeChannel, exchanges_channel.TimeFrameExchangeChannel]:
        await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                         exchange_manager=exchange_manager)

    trader = exchanges.TraderSimulator(config, exchange_manager)
    await trader.initialize()

    mode = Mode.DipAnalyserTradingMode(config, exchange_manager)
    mode.symbol = None if mode.get_is_symbol_wildcard() else symbol
    await mode.initialize()
    # add mode to exchange manager so that it can be stopped and freed from memory
    exchange_manager.trading_modes.append(mode)

    # set BTC/USDT price at 1000 USDT
    trading_api.force_set_mark_price(exchange_manager, symbol, 1000)

    return mode.producers[0], mode.get_trading_mode_consumers()[0], trader


async def _fill_order(order, trader, trigger_update_callback=True, ignore_open_orders=False, consumer=None,
                      closed_orders_count=1):
    initial_len = len(trading_api.get_open_orders(trader.exchange_manager))
    await order.on_fill(force_fill=True)
    if order.status == trading_enums.OrderStatus.FILLED:
        if not ignore_open_orders:
            assert len(trading_api.get_open_orders(trader.exchange_manager)) == initial_len - closed_orders_count
        if trigger_update_callback:
            await asyncio_tools.wait_asyncio_next_cycle()
        else:
            with mock.patch.object(consumer, "create_new_orders", new=mock.AsyncMock()):
                await asyncio_tools.wait_asyncio_next_cycle()


async def _stop(exchange_manager):
    for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
        await backtesting_api.stop_importer(importer)
    await exchange_manager.exchange.backtesting.stop()
    await exchange_manager.stop()
