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
import decimal
import math
import mock
import pytest
import os.path
import copy
import pytest_asyncio

import async_channel.util as channel_util
import octobot_backtesting.api as backtesting_api
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.constants as commons_constants
import octobot_commons.tests.test_config as test_config
import octobot_trading.constants as trading_constants
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchange_data as exchange_data
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges as exchanges
import octobot_trading.modes.script_keywords as script_keywords
import octobot_trading.personal_data as trading_personal_data
import tentacles.Trading.Mode as Mode
import tests.unit_tests.trading_modes_tests.trading_mode_test_toolkit as trading_mode_test_toolkit
import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges
import octobot_tentacles_manager.api as tentacles_manager_api


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def tools():
    tentacles_manager_api.reload_tentacle_info()
    exchange_manager = None
    try:
        symbol = "BTC/USDT"
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO][
            "SUB"] = 0.000000000000000000005
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO][
            "BNB"] = 0.000000000000000000005
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
            data_files=[
                os.path.join(test_config.TEST_CONFIG_FOLDER, "AbstractExchangeHistoryCollector_1586017993.616272.data")])
        exchange_manager.exchange = exchanges.ExchangeSimulator(exchange_manager.config,
                                                                exchange_manager,
                                                                backtesting)
        await exchange_manager.exchange.initialize()
        for exchange_channel_class_type in [exchanges_channel.ExchangeChannel, exchanges_channel.TimeFrameExchangeChannel]:
            await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                             exchange_manager=exchange_manager)

        trader = exchanges.TraderSimulator(config, exchange_manager)
        await trader.initialize()

        mode = Mode.DailyTradingMode(config, exchange_manager)
        await mode.initialize()
        # add mode to exchange manager so that it can be stopped and freed from memory
        exchange_manager.trading_modes.append(mode)
        consumer = mode.get_trading_mode_consumers()[0]
        consumer.MAX_CURRENCY_RATIO = 1

        # set BTC/USDT price at 7009.194999999998 USDT
        last_btc_price = 7009.194999999998
        trading_api.force_set_mark_price(exchange_manager, symbol, last_btc_price)

        yield exchange_manager, trader, symbol, consumer, decimal.Decimal(str(last_btc_price))
    finally:
        if exchange_manager:
            try:
                await _stop(exchange_manager)
            except Exception as err:
                print(f"error when stopping exchange manager: {err}")


@pytest_asyncio.fixture
async def future_tools():
    tentacles_manager_api.reload_tentacle_info()
    exchange_manager = None
    try:
        symbol = "BTC/USDT:USDT"
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO][
            "SUB"] = 0.000000000000000000005
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO][
            "BNB"] = 0.000000000000000000005
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 2000
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        exchange_manager.tentacles_setup_config = test_utils_config.get_tentacles_setup_config()

        # use backtesting not to spam exchanges apis
        exchange_manager.is_spot_only = False
        exchange_manager.is_future = True
        exchange_manager.is_simulated = True
        exchange_manager.is_backtesting = True
        exchange_manager.use_cached_markets = False
        backtesting = await backtesting_api.initialize_backtesting(
            config,
            exchange_ids=[exchange_manager.id],
            matrix_id=None,
            data_files=[
                os.path.join(test_config.TEST_CONFIG_FOLDER, "AbstractExchangeHistoryCollector_1586017993.616272.data")])
        exchange_manager.exchange = exchanges.ExchangeSimulator(exchange_manager.config,
                                                                exchange_manager,
                                                                backtesting)
        await exchange_manager.exchange.initialize()
        for exchange_channel_class_type in [exchanges_channel.ExchangeChannel, exchanges_channel.TimeFrameExchangeChannel]:
            await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                             exchange_manager=exchange_manager)

        contract = exchange_data.FutureContract(
            pair=symbol,
            margin_type=trading_enums.MarginType.ISOLATED,
            contract_type=trading_enums.FutureContractType.LINEAR_PERPETUAL,
            current_leverage=trading_constants.ONE,
            maximum_leverage=trading_constants.ONE_HUNDRED
        )
        exchange_manager.exchange.set_pair_future_contract(symbol, contract)
        trader = exchanges.TraderSimulator(config, exchange_manager)
        await trader.initialize()

        mode = Mode.DailyTradingMode(config, exchange_manager)
        await mode.initialize()
        # add mode to exchange manager so that it can be stopped and freed from memory
        exchange_manager.trading_modes.append(mode)
        consumer = mode.get_trading_mode_consumers()[0]
        consumer.MAX_CURRENCY_RATIO = 1

        # set BTC/USDT:USDT price at 7009.194999999998 USDT
        last_btc_price = 7009.194999999998
        trading_api.force_set_mark_price(exchange_manager, symbol, last_btc_price)

        yield exchange_manager, trader, symbol, consumer, decimal.Decimal(str(last_btc_price))
    finally:
        if exchange_manager:
            try:
                await _stop(exchange_manager)
            except Exception as err:
                print(f"error when stopping exchange manager: {err}")


async def _stop(exchange_manager):
    for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
        await backtesting_api.stop_importer(importer)
    await exchange_manager.exchange.backtesting.stop()
    await exchange_manager.stop()
    # let updaters gracefully shutdown
    await asyncio_tools.wait_asyncio_next_cycle()


async def test_valid_create_new_orders_no_ref_market_as_quote(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # change reference market to USDT
    exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "USDT"
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[
        symbol] = last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(last_btc_price * 10 + 1000))

    market_status = exchange_manager.exchange.get_market_status(symbol, with_fixer=False)

    # portfolio: "BTC": 10 "USD": 1000
    # order from neutral state
    _origin_decimal_adapt_order_quantity_because_fees = trading_personal_data.decimal_adapt_order_quantity_because_fees

    def _decimal_adapt_order_quantity_because_fees(
        exchange_manager, symbol: str, order_type: trading_enums.TraderOrderType, quantity: decimal.Decimal,
        price: decimal.Decimal, side: trading_enums.TradeOrderSide
    ):
        return quantity

    with mock.patch.object(
            trading_personal_data, "decimal_adapt_order_quantity_because_fees",
            mock.Mock(side_effect=_decimal_adapt_order_quantity_because_fees)
    ) as decimal_adapt_order_quantity_because_fees_mock:
        assert await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.NEUTRAL.value) == []
        assert await consumer.create_new_orders(symbol, decimal.Decimal(str(0.5)), trading_enums.EvaluatorStates.NEUTRAL.value) == []
        assert await consumer.create_new_orders(symbol, trading_constants.ZERO, trading_enums.EvaluatorStates.NEUTRAL.value) == []
        assert await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.5)), trading_enums.EvaluatorStates.NEUTRAL.value) == []
        assert await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.NEUTRAL.value) == []
        # neutral state
        decimal_adapt_order_quantity_because_fees_mock.assert_not_called()

        # valid sell limit order (price adapted)
        orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.65)), trading_enums.EvaluatorStates.SHORT.value)
        # short state
        decimal_adapt_order_quantity_because_fees_mock.assert_not_called()
        assert len(orders) == 1
        order = orders[0]
        assert isinstance(order, trading_personal_data.SellLimitOrder)
        assert order.currency == "BTC"
        assert order.symbol == "BTC/USDT"
        assert order.origin_price == decimal.Decimal(str(7062.64011187))
        assert order.created_last_price == last_btc_price
        assert order.order_type == trading_enums.TraderOrderType.SELL_LIMIT
        assert order.side == trading_enums.TradeOrderSide.SELL
        assert order.status == trading_enums.OrderStatus.OPEN
        assert order.exchange_manager == exchange_manager
        assert order.trader == trader
        assert order.fee is None
        assert order.filled_price == trading_constants.ZERO
        assert order.origin_quantity == decimal.Decimal(str(7.6))
        assert order.filled_quantity == trading_constants.ZERO
        assert order.simulated is True
        assert order.chained_orders == []
        assert isinstance(order.order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)

        trading_mode_test_toolkit.check_order_limits(order, market_status)

        trading_mode_test_toolkit.check_oco_order_group(order,
                                                        trading_enums.TraderOrderType.STOP_LOSS, decimal.Decimal(str(6658.73524999)),
                                                        market_status)

        # valid buy limit order with (price and quantity adapted)
        orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.65)), trading_enums.EvaluatorStates.LONG.value)
        assert len(orders) == 1
        order = orders[0]
        # long state
        adapted_args = list(decimal_adapt_order_quantity_because_fees_mock.mock_calls[0].args)
        adapted_args[3] = trading_personal_data.decimal_adapt_quantity(market_status, adapted_args[3])
        adapted_args[4] = trading_personal_data.decimal_adapt_price(market_status, adapted_args[4])
        assert adapted_args == [
            exchange_manager, order.symbol, trading_enums.TraderOrderType.BUY_LIMIT,
            order.origin_quantity,
            order.origin_price,
            trading_enums.TradeOrderSide.BUY,
        ]
        decimal_adapt_order_quantity_because_fees_mock.reset_mock()
        assert isinstance(order, trading_personal_data.BuyLimitOrder)
        assert order.currency == "BTC"
        assert order.symbol == "BTC/USDT"
        assert order.origin_price == decimal.Decimal(str(6955.74988812))
        assert order.created_last_price == last_btc_price
        assert order.order_type == trading_enums.TraderOrderType.BUY_LIMIT
        assert order.side == trading_enums.TradeOrderSide.BUY
        assert order.status == trading_enums.OrderStatus.OPEN
        assert order.exchange_manager == exchange_manager
        assert order.trader == trader
        assert order.fee is None
        assert order.filled_price == trading_constants.ZERO
        assert order.origin_quantity == decimal.Decimal(str(0.12554936))
        assert order.filled_quantity == trading_constants.ZERO
        assert order.simulated is True
        assert order.order_group is None
        assert order.chained_orders == []

        trading_mode_test_toolkit.check_order_limits(order, market_status)

        truncated_last_price = trading_personal_data.decimal_trunc_with_n_decimal_digits(last_btc_price, 8)

        # valid buy market order with (price and quantity adapted) using user_given quantity (which is adapted as well)
        orders = await consumer.create_new_orders(
            symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.VERY_LONG.value,
            data={
                consumer.VOLUME_KEY: decimal.Decimal('0.0123')
            }
        )
        assert len(orders) == 1
        order = orders[0]
        assert order.origin_quantity == decimal.Decimal('0.0123')
        # very long state
        adapted_args = list(decimal_adapt_order_quantity_because_fees_mock.mock_calls[0].args)
        adapted_args[3] = trading_personal_data.decimal_adapt_quantity(market_status, adapted_args[3])
        adapted_args[4] = trading_personal_data.decimal_adapt_price(market_status, adapted_args[4])
        assert adapted_args == [
            exchange_manager, order.symbol, trading_enums.TraderOrderType.BUY_MARKET,
            order.origin_quantity,
            order.origin_price,
            trading_enums.TradeOrderSide.BUY,
        ]
        decimal_adapt_order_quantity_because_fees_mock.reset_mock()
        assert isinstance(order, trading_personal_data.BuyMarketOrder)
        assert order.currency == "BTC"
        assert order.symbol == "BTC/USDT"
        assert order.origin_price == truncated_last_price
        assert order.created_last_price == truncated_last_price
        assert order.order_type == trading_enums.TraderOrderType.BUY_MARKET
        assert order.side == trading_enums.TradeOrderSide.BUY
        assert order.status == trading_enums.OrderStatus.FILLED
        # order has been cleared
        assert order.exchange_manager is None
        assert order.trader is None
        assert order.fee
        assert order.filled_price == decimal.Decimal(str(7009.19499999))
        assert order.origin_quantity == decimal.Decimal('0.0123')
        assert order.filled_quantity == order.origin_quantity
        assert order.simulated is True
        assert order.order_group is None
        assert order.chained_orders == []

        trading_mode_test_toolkit.check_order_limits(order, market_status)

        # valid buy market order with (price and quantity adapted)
        orders = await consumer.create_new_orders(symbol, trading_constants.ONE,
                                                  trading_enums.EvaluatorStates.VERY_SHORT.value)
        # very short state
        decimal_adapt_order_quantity_because_fees_mock.assert_not_called()
        assert len(orders) == 1
        order = orders[0]
        assert isinstance(order, trading_personal_data.SellMarketOrder)
        assert order.currency == "BTC"
        assert order.symbol == "BTC/USDT"
        assert order.origin_price == truncated_last_price
        assert order.created_last_price == truncated_last_price
        assert order.order_type == trading_enums.TraderOrderType.SELL_MARKET
        assert order.side == trading_enums.TradeOrderSide.SELL
        assert order.status == trading_enums.OrderStatus.FILLED
        assert order.exchange_manager is None
        assert order.trader is None
        assert order.fee
        assert order.filled_price == decimal.Decimal(str(7009.19499999))
        assert order.origin_quantity == decimal.Decimal('2.4122877')
        assert order.filled_quantity == order.origin_quantity
        assert order.simulated is True
        assert order.order_group is None
        assert order.chained_orders == []

        trading_mode_test_toolkit.check_order_limits(order, market_status)


async def test_valid_create_new_orders_ref_market_as_quote(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[
        symbol] = last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))

    # portfolio: "BTC": 10 "USD": 1000
    # order from neutral state
    assert await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.NEUTRAL.value) == []
    assert await consumer.create_new_orders(symbol, decimal.Decimal(str(0.5)), trading_enums.EvaluatorStates.NEUTRAL.value) == []
    assert await consumer.create_new_orders(symbol, decimal.Decimal(str(0)), trading_enums.EvaluatorStates.NEUTRAL.value) == []
    assert await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.5)), trading_enums.EvaluatorStates.NEUTRAL.value) == []
    assert await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.NEUTRAL.value) == []

    # valid sell limit order (price adapted)
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.65)), trading_enums.EvaluatorStates.SHORT.value)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, trading_personal_data.SellLimitOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == decimal.Decimal(str(7062.64011187))
    assert order.created_last_price == last_btc_price
    assert order.order_type == trading_enums.TraderOrderType.SELL_LIMIT
    assert order.side == trading_enums.TradeOrderSide.SELL
    assert order.status == trading_enums.OrderStatus.OPEN
    assert order.exchange_manager == exchange_manager
    assert order.trader == trader
    assert order.fee is None
    assert order.filled_price == trading_constants.ZERO
    assert order.origin_quantity == decimal.Decimal(str(4.4))
    assert order.filled_quantity == trading_constants.ZERO
    assert order.simulated is True
    assert isinstance(order.order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)

    market_status = exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
    trading_mode_test_toolkit.check_order_limits(order, market_status)

    trading_mode_test_toolkit.check_oco_order_group(order,
                                                    trading_enums.TraderOrderType.STOP_LOSS, decimal.Decimal(str(6658.73524999)),
                                                    market_status)

    # valid buy limit order with (price and quantity adapted)
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.65)), trading_enums.EvaluatorStates.LONG.value)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, trading_personal_data.BuyLimitOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == decimal.Decimal(str(6955.74988812))
    assert order.created_last_price == last_btc_price
    assert order.order_type == trading_enums.TraderOrderType.BUY_LIMIT
    assert order.side == trading_enums.TradeOrderSide.BUY
    assert order.status == trading_enums.OrderStatus.OPEN
    assert order.exchange_manager == exchange_manager
    assert order.trader == trader
    assert order.fee is None
    assert order.filled_price == trading_constants.ZERO
    assert order.origin_quantity == decimal.Decimal(str(0.21685799))
    assert order.filled_quantity == trading_constants.ZERO
    assert order.simulated is True
    assert order.order_group is None
    assert order.chained_orders == []

    trading_mode_test_toolkit.check_order_limits(order, market_status)

    truncated_last_price = trading_personal_data.decimal_trunc_with_n_decimal_digits(last_btc_price, 8)

    # valid buy market order with (price and quantity adapted)
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.VERY_LONG.value)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, trading_personal_data.BuyMarketOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == truncated_last_price
    assert order.created_last_price == truncated_last_price
    assert order.order_type == trading_enums.TraderOrderType.BUY_MARKET
    assert order.side == trading_enums.TradeOrderSide.BUY
    assert order.status == trading_enums.OrderStatus.FILLED
    assert order.filled_price == decimal.Decimal(str(7009.19499999))
    assert order.origin_quantity == decimal.Decimal(str(0.07013502))
    assert order.filled_quantity == order.origin_quantity
    assert order.simulated is True
    assert order.order_group is None
    assert order.chained_orders == []

    trading_mode_test_toolkit.check_order_limits(order, market_status)

    # valid buy market order with (price and quantity adapted)
    orders = await consumer.create_new_orders(symbol, trading_constants.ONE, trading_enums.EvaluatorStates.VERY_SHORT.value)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, trading_personal_data.SellMarketOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == truncated_last_price
    assert order.created_last_price == truncated_last_price
    assert order.order_type == trading_enums.TraderOrderType.SELL_MARKET
    assert order.side == trading_enums.TradeOrderSide.SELL
    assert order.status == trading_enums.OrderStatus.FILLED
    assert order.fee
    assert order.filled_price == decimal.Decimal(str(7009.19499999))
    assert order.origin_quantity == decimal.Decimal(str(4.08244671))
    assert order.filled_quantity == order.origin_quantity
    assert order.simulated is True
    assert order.order_group is None
    assert order.chained_orders == []

    trading_mode_test_toolkit.check_order_limits(order, market_status)


async def test_invalid_create_new_orders(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # portfolio: "BTC": 10 "USD": 1000
    min_trigger_market = "ADA/BNB"

    # invalid sell order with not trade data
    import octobot_trading.constants
    trading_constants.ORDER_DATA_FETCHING_TIMEOUT = 0.1
    assert await consumer.create_new_orders(min_trigger_market, decimal.Decimal(str(0.6)), trading_enums.EvaluatorStates.SHORT.value,
                                            timeout=1) == []

    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").available = decimal.Decimal(str(0.000000000000000000005))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").total = decimal.Decimal(str(2000))

    # invalid sell order with not enough currency to sell
    with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
        await consumer.create_new_orders(symbol, decimal.Decimal(str(0.6)), trading_enums.EvaluatorStates.SHORT.value)

    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available = decimal.Decimal(str(0.000000000000000000005))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").total = decimal.Decimal(str(2000))

    # invalid buy order with not enough currency to buy
    with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
        orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.6)), trading_enums.EvaluatorStates.LONG.value)


async def test_create_new_orders_with_dusts_included(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").available = decimal.Decimal(str(0.000015))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").total = decimal.Decimal(str(0.000015))

    # trigger order that should not sell everything but does sell everything because remaining amount
    # is not sellable
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.6)), trading_enums.EvaluatorStates.VERY_SHORT.value)
    assert len(orders) == 1

    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").available = trading_constants.ZERO
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").total = trading_constants.ZERO

    test_currency = "NEO"
    test_pair = f"{test_currency}/BTC"
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(test_currency).available = decimal.Decimal(str(0.44))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(test_currency).total = decimal.Decimal(str(0.44))

    trading_api.force_set_mark_price(exchange_manager, test_pair, 0.005318)
    # trigger order that should not sell everything but does sell everything because remaining amount
    # is not sellable
    orders = await consumer.create_new_orders(test_pair, decimal.Decimal(str(0.75445456165478)),
                                              trading_enums.EvaluatorStates.SHORT.value)
    assert len(orders) == 1
    assert exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(test_currency).available == trading_constants.ZERO
    assert exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(test_currency).total == orders[0].origin_quantity


async def test_split_create_new_orders(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # change reference market to get more orders
    exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "USDT"
    exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "USDT"
    market_status = exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").available = decimal.Decimal(str(2000000001))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").total = decimal.Decimal(str(2000000001))

    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[
        symbol] = last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(last_btc_price * 2000000001 + 1000))

    # split orders because order too big and coin price too high
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.6)), trading_enums.EvaluatorStates.SHORT.value)
    assert len(orders) == 11
    adapted_order = orders[0]
    identical_orders = orders[1:]

    assert isinstance(adapted_order, trading_personal_data.SellLimitOrder)
    assert adapted_order.currency == "BTC"
    assert adapted_order.symbol == "BTC/USDT"
    assert adapted_order.origin_price == decimal.Decimal(str(7065.26855999))
    assert adapted_order.created_last_price == last_btc_price
    assert adapted_order.order_type == trading_enums.TraderOrderType.SELL_LIMIT
    assert adapted_order.side == trading_enums.TradeOrderSide.SELL
    assert adapted_order.status == trading_enums.OrderStatus.OPEN
    assert adapted_order.exchange_manager == exchange_manager
    assert adapted_order.trader == trader
    assert adapted_order.fee is None
    assert adapted_order.filled_price == trading_constants.ZERO
    assert adapted_order.origin_quantity == decimal.Decimal(str(64625635.97358073))
    assert adapted_order.filled_quantity == trading_constants.ZERO
    assert adapted_order.simulated is True
    assert isinstance(adapted_order.order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)

    trading_mode_test_toolkit.check_order_limits(adapted_order, market_status)

    trading_mode_test_toolkit.check_oco_order_group(adapted_order,
                                                    trading_enums.TraderOrderType.STOP_LOSS, decimal.Decimal(str(6658.73524999)),
                                                    market_status)

    for order in identical_orders:
        assert isinstance(order, trading_personal_data.SellLimitOrder)
        assert order.currency == adapted_order.currency
        assert order.symbol == adapted_order.symbol
        assert order.origin_price == adapted_order.origin_price
        assert order.created_last_price == adapted_order.created_last_price
        assert order.order_type == adapted_order.order_type
        assert order.side == adapted_order.side
        assert order.status == adapted_order.status
        assert order.exchange_manager == adapted_order.exchange_manager
        assert order.trader == adapted_order.trader
        assert order.fee == adapted_order.fee
        assert order.filled_price == adapted_order.filled_price
        assert order.origin_quantity == decimal.Decimal(str(141537436.47664192))
        assert order.origin_quantity > adapted_order.origin_quantity
        assert order.filled_quantity == trading_constants.ZERO
        assert order.simulated == adapted_order.simulated
        assert isinstance(order.order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)

        trading_mode_test_toolkit.check_order_limits(order, market_status)
        trading_mode_test_toolkit.check_oco_order_group(order,
                                                        trading_enums.TraderOrderType.STOP_LOSS, decimal.Decimal(str(6658.73524999)),
                                                        market_status)

    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available = decimal.Decimal(str(40000000000))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").total = decimal.Decimal(str(40000000000))

    # set btc last price to 6998.55407999 * 0.000001 = 0.00699855408
    trading_api.force_set_mark_price(exchange_manager, symbol, float(last_btc_price * decimal.Decimal(str(0.000001))))
    # split orders because order too big and too many coins
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.6)), trading_enums.EvaluatorStates.LONG.value)
    assert len(orders) == 3
    adapted_order = orders[0]
    identical_orders = orders[1:]

    assert isinstance(adapted_order, trading_personal_data.BuyLimitOrder)
    assert adapted_order.currency == "BTC"
    assert adapted_order.symbol == "BTC/USDT"
    assert adapted_order.origin_price == decimal.Decimal(str(0.00695312))
    assert adapted_order.created_last_price == decimal.Decimal(str(0.007009194999999998))
    assert adapted_order.order_type == trading_enums.TraderOrderType.BUY_LIMIT
    assert adapted_order.side == trading_enums.TradeOrderSide.BUY
    assert adapted_order.status == trading_enums.OrderStatus.OPEN
    assert adapted_order.exchange_manager == exchange_manager
    assert adapted_order.trader == trader
    assert adapted_order.fee is None
    assert adapted_order.filled_price == trading_constants.ZERO
    assert adapted_order.origin_quantity == decimal.Decimal("396851564266.65327383")
    assert adapted_order.filled_quantity == trading_constants.ZERO
    assert adapted_order.simulated is True

    trading_mode_test_toolkit.check_order_limits(adapted_order, market_status)

    for order in identical_orders:
        assert isinstance(order, trading_personal_data.BuyLimitOrder)
        assert order.currency == adapted_order.currency
        assert order.symbol == adapted_order.symbol
        assert order.origin_price == adapted_order.origin_price
        assert order.created_last_price == adapted_order.created_last_price
        assert order.order_type == adapted_order.order_type
        assert order.side == adapted_order.side
        assert order.status == adapted_order.status
        assert order.exchange_manager == adapted_order.exchange_manager
        assert order.trader == adapted_order.trader
        assert order.fee == adapted_order.fee
        assert order.filled_price == adapted_order.filled_price
        assert order.origin_quantity == decimal.Decimal(str(1000000000000.0))
        assert order.origin_quantity > adapted_order.origin_quantity
        assert order.filled_quantity == trading_constants.ZERO
        assert order.simulated == adapted_order.simulated

        trading_mode_test_toolkit.check_order_limits(order, market_status)


async def test_valid_create_new_orders_without_stop_order(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # change reference market to get more orders
    exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "USDT"
    exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "USDT"
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[
        symbol] = last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(last_btc_price * 10 + 1000))
    market_status = exchange_manager.exchange.get_market_status(symbol, with_fixer=False)

    # force no stop orders
    consumer.USE_STOP_ORDERS = False

    # valid sell limit order (price adapted)
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.65)), trading_enums.EvaluatorStates.SHORT.value)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, trading_personal_data.SellLimitOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == decimal.Decimal(str(7062.64011187))
    assert order.created_last_price == last_btc_price
    assert order.order_type == trading_enums.TraderOrderType.SELL_LIMIT
    assert order.side == trading_enums.TradeOrderSide.SELL
    assert order.status == trading_enums.OrderStatus.OPEN
    assert order.exchange_manager == exchange_manager
    assert order.trader == trader
    assert order.fee is None
    assert order.filled_price == trading_constants.ZERO
    assert order.origin_quantity == decimal.Decimal(str(7.6))
    assert order.filled_quantity == trading_constants.ZERO
    assert order.simulated is True
    assert order.order_group is None
    assert order.chained_orders == []

    trading_mode_test_toolkit.check_order_limits(order, market_status)


def _get_evaluations_gradient(step):
    nb_steps = 1 / step
    return [decimal.Decimal(str(i / nb_steps)) for i in range(int(-nb_steps), int(nb_steps + 1), 1)]


def _get_states_gradient_with_invald_states():
    states = [state.value for state in trading_enums.EvaluatorStates]
    states += [None, 1, {'toto': 1}, math.nan]
    return states


def _get_irrationnal_numbers():
    irrationals = [math.pi, math.sqrt(2), math.sqrt(3), math.sqrt(5), math.sqrt(7), math.sqrt(11), math.sqrt(73),
                   10 / 3]
    return [decimal.Decimal(str(1 / i)) for i in irrationals]


def _reset_portfolio(exchange_manager):
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").available = decimal.Decimal(str(10))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("BTC").total = decimal.Decimal(str(10))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").available = decimal.Decimal(str(2000))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio("USDT").total = decimal.Decimal(str(2000))


async def test_create_orders_using_a_lot_of_different_inputs_with_portfolio_reset(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools
    gradient_step = 0.005
    nb_orders = 1
    initial_portfolio = copy.copy(exchange_manager.exchange_personal_data.portfolio_manager.portfolio)
    portfolio_wrapper = exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    market_status = exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
    min_trigger_market = "ADA/BNB"
    trading_api.force_set_mark_price(exchange_manager, min_trigger_market, 0.001)

    for state in _get_states_gradient_with_invald_states():
        for evaluation in _get_evaluations_gradient(gradient_step):
            _reset_portfolio(exchange_manager)
            # orders are possible
            try:
                orders = await consumer.create_new_orders(symbol, evaluation, state)
                trading_mode_test_toolkit.check_orders(orders, evaluation, state, nb_orders, market_status)
                trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders)
            except trading_errors.MissingMinimalExchangeTradeVolume:
                pass
            # orders are impossible
            try:
                orders = []
                orders = await consumer.create_new_orders(min_trigger_market, evaluation, state)
                trading_mode_test_toolkit.check_orders(orders, evaluation, state, 0, market_status)
                trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders)
            except trading_errors.MissingMinimalExchangeTradeVolume:
                pass

        for evaluation in _get_irrationnal_numbers():
            # orders are possible
            _reset_portfolio(exchange_manager)
            try:
                orders = await consumer.create_new_orders(symbol, evaluation, state)
                trading_mode_test_toolkit.check_orders(orders, evaluation, state, nb_orders, market_status)
                trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders)
            except trading_errors.MissingMinimalExchangeTradeVolume:
                pass
            # orders are impossible
            try:
                orders = []
                orders = await consumer.create_new_orders(min_trigger_market, evaluation, state)
                trading_mode_test_toolkit.check_orders(orders, evaluation, state, 0, market_status)
                trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders)
            except trading_errors.MissingMinimalExchangeTradeVolume:
                pass

        _reset_portfolio(exchange_manager)
        # orders are possible
        try:
            orders = await consumer.create_new_orders(symbol, decimal.Decimal("nan"), state)
            trading_mode_test_toolkit.check_orders(orders, decimal.Decimal("nan"), state, nb_orders, market_status)
            trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders)
        except trading_errors.MissingMinimalExchangeTradeVolume:
            pass
        # orders are impossible
        try:
            orders = []
            orders = await consumer.create_new_orders(min_trigger_market, decimal.Decimal("nan"), state)
            trading_mode_test_toolkit.check_orders(orders, decimal.Decimal("nan"), state, 0, market_status)
            trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders)
        except trading_errors.MissingMinimalExchangeTradeVolume:
            pass
        try:
            orders = []
            # float evaluation
            orders = await consumer.create_new_orders(min_trigger_market, math.nan, state)
            trading_mode_test_toolkit.check_orders(orders, math.nan, state, 0, market_status)
            trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders)
        except trading_errors.MissingMinimalExchangeTradeVolume:
            pass


async def test_create_order_using_a_lot_of_different_inputs_without_portfolio_reset(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    gradient_step = 0.001
    nb_orders = "unknown"
    initial_portfolio = copy.copy(exchange_manager.exchange_personal_data.portfolio_manager.portfolio)
    portfolio_wrapper = exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    market_status = exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
    min_trigger_market = "ADA/BNB"
    trading_api.force_set_mark_price(exchange_manager, min_trigger_market, 0.001)

    _reset_portfolio(exchange_manager)
    for state in _get_states_gradient_with_invald_states():
        for evaluation in _get_evaluations_gradient(gradient_step):
            # orders are possible
            try:
                orders = await consumer.create_new_orders(symbol, evaluation, state)
                trading_mode_test_toolkit.check_orders(orders, evaluation, state, nb_orders, market_status)
                trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders, True)
                await trading_mode_test_toolkit.fill_orders(orders, trader)
            except trading_errors.MissingMinimalExchangeTradeVolume:
                pass
            # orders are impossible
            try:
                orders = []
                orders = await consumer.create_new_orders(min_trigger_market, evaluation, state)
                trading_mode_test_toolkit.check_orders(orders, evaluation, state, 0, market_status)
                trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders, True)
                await trading_mode_test_toolkit.fill_orders(orders, trader)
            except trading_errors.MissingMinimalExchangeTradeVolume:
                pass

    _reset_portfolio(exchange_manager)
    for state in _get_states_gradient_with_invald_states():
        for evaluation in _get_irrationnal_numbers():
            # orders are possible
            try:
                orders = await consumer.create_new_orders(symbol, evaluation, state)
                trading_mode_test_toolkit.check_orders(orders, evaluation, state, nb_orders, market_status)
                trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders, True)
                if any(order
                       for order in orders
                       if order.order_type not in (
                trading_enums.TraderOrderType.SELL_MARKET, trading_enums.TraderOrderType.BUY_MARKET)):
                    # no need to fill market orders
                    await trading_mode_test_toolkit.fill_orders(orders, trader)
            except trading_errors.MissingMinimalExchangeTradeVolume:
                pass
            # orders are impossible
            try:
                orders = []
                orders = await consumer.create_new_orders(min_trigger_market, evaluation, state)
                trading_mode_test_toolkit.check_orders(orders, evaluation, state, 0, market_status)
                trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders, True)
                if any(order
                       for order in orders
                       if order.order_type not in (
                trading_enums.TraderOrderType.SELL_MARKET, trading_enums.TraderOrderType.BUY_MARKET)):
                    # no need to fill market orders
                    await trading_mode_test_toolkit.fill_orders(orders, trader)
            except trading_errors.MissingMinimalExchangeTradeVolume:
                pass

    _reset_portfolio(exchange_manager)
    for state in _get_states_gradient_with_invald_states():
        # orders are possible
        try:
            orders = await consumer.create_new_orders(symbol, decimal.Decimal("nan"), state)
            trading_mode_test_toolkit.check_orders(orders, math.nan, state, nb_orders, market_status)
            trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders, True)
            await trading_mode_test_toolkit.fill_orders(orders, trader)
        except trading_errors.MissingMinimalExchangeTradeVolume:
            pass
        # orders are impossible
        try:
            orders = []
            orders = await consumer.create_new_orders(min_trigger_market, decimal.Decimal("nan"), state)
            trading_mode_test_toolkit.check_orders(orders, math.nan, state, 0, market_status)
            trading_mode_test_toolkit.check_portfolio(portfolio_wrapper, initial_portfolio, orders, True)
            await trading_mode_test_toolkit.fill_orders(orders, trader)
        except trading_errors.MissingMinimalExchangeTradeVolume:
            pass


async def test_create_multiple_buy_orders_after_fill(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # with BTC/USDT
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[symbol] = \
        last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))
    # force many traded asset not to create all in orders
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.origin_crypto_currencies_values \
        = {
        "a": trading_constants.ZERO,
        "b": trading_constants.ZERO,
        "c": trading_constants.ZERO,
        "d": trading_constants.ZERO,
        "e": trading_constants.ZERO
    }
    await ensure_smaller_orders(consumer, symbol, trader)

    # with another symbol with 0 quantity when start
    trading_api.force_set_mark_price(exchange_manager, "ADA/BTC", 0.0000001)
    await ensure_smaller_orders(consumer, "ADA/BTC", trader)


async def ensure_smaller_orders(consumer, symbol, trader):
    state = trading_enums.EvaluatorStates.VERY_LONG.value

    # first call: biggest order
    orders1 = (await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), state))
    if any(order
           for order in orders1
           if order.order_type not in (
    trading_enums.TraderOrderType.SELL_MARKET, trading_enums.TraderOrderType.BUY_MARKET)):
        # no need to fill market orders
        await trading_mode_test_toolkit.fill_orders(orders1, trader)

    state = trading_enums.EvaluatorStates.LONG.value
    # second call: smaller order (same with very long as with long)
    orders2 = (await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.6)), state))
    assert orders1[0].origin_quantity > orders2[0].origin_quantity
    if any(order
           for order in orders2
           if order.order_type not in (
    trading_enums.TraderOrderType.SELL_MARKET, trading_enums.TraderOrderType.BUY_MARKET)):
        # no need to fill market orders
        await trading_mode_test_toolkit.fill_orders(orders2, trader)

    # third call: even smaller order
    orders3 = (await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.6)), state))
    assert orders2[0].origin_quantity > orders3[0].origin_quantity
    if any(order
           for order in orders3
           if order.order_type not in (
    trading_enums.TraderOrderType.SELL_MARKET, trading_enums.TraderOrderType.BUY_MARKET)):
        # no need to fill market orders
        await trading_mode_test_toolkit.fill_orders(orders3, trader)

    # third call: even-even smaller order
    orders4 = (await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.6)), state))
    assert orders3[0].origin_quantity > orders4[0].origin_quantity
    if any(order
           for order in orders4
           if order.order_type not in (
    trading_enums.TraderOrderType.SELL_MARKET, trading_enums.TraderOrderType.BUY_MARKET)):
        # no need to fill market orders
        await trading_mode_test_toolkit.fill_orders(orders4, trader)


async def test_create_new_orders_with_cancel_policy(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # with BTC/USDT
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[symbol] = \
        last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))

    # simple buy order
    data = {
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
        consumer.CANCEL_POLICY: trading_personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__,
    }
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.LONG.value, data=data)
    buy_order = orders[0]
    assert isinstance(buy_order, trading_personal_data.BuyLimitOrder)
    assert isinstance(buy_order.cancel_policy, trading_personal_data.ChainedOrderFillingPriceOrderCancelPolicy)
    assert len(buy_order.chained_orders) == 0
    
    # buy order order with stop
    data = {
        consumer.STOP_PRICE_KEY: decimal.Decimal("10"),
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
        consumer.CANCEL_POLICY: trading_personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__,
    }
    orders_with_stop = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.VERY_LONG.value, data=data)
    buy_order = orders_with_stop[0]
    assert isinstance(buy_order, trading_personal_data.BuyMarketOrder)
    assert isinstance(buy_order.cancel_policy, trading_personal_data.ChainedOrderFillingPriceOrderCancelPolicy)
    assert len(buy_order.chained_orders) == 1
    stop_order = buy_order.chained_orders[0]
    assert stop_order.cancel_policy is None # cancel policy is set on the entry order only
    assert stop_order.is_open()

    # simple sell order with invalid policy
    data = {
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
        consumer.CANCEL_POLICY: trading_personal_data.ExpirationTimeOrderCancelPolicy.__name__,
    }
    with pytest.raises(trading_errors.InvalidCancelPolicyError):
        orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(1)), trading_enums.EvaluatorStates.SHORT.value, data=data)
    
    # simple sell order with valid policy
    data = {
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
        consumer.CANCEL_POLICY: trading_personal_data.ExpirationTimeOrderCancelPolicy.__name__,
        consumer.CANCEL_POLICY_PARAMS: {
            "expiration_time": 1000.0,
        },
    }
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(1)), trading_enums.EvaluatorStates.SHORT.value, data=data)
    sell_order = orders[0]
    assert isinstance(sell_order, trading_personal_data.SellLimitOrder)
    assert isinstance(sell_order.cancel_policy, trading_personal_data.ExpirationTimeOrderCancelPolicy)
    assert sell_order.cancel_policy.expiration_time == 1000.0
    assert len(sell_order.chained_orders) == 0

async def test_chained_stop_loss_and_take_profit_orders(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # with BTC/USDT
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[symbol] = \
        last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))

    state = trading_enums.EvaluatorStates.VERY_LONG.value
    # stop loss only
    data = {
        consumer.STOP_PRICE_KEY: decimal.Decimal("10"),
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
        consumer.TAG_KEY: "super"
    }
    orders_with_stop = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), state, data=data)
    buy_order = orders_with_stop[0]
    assert buy_order.cancel_policy is None
    assert len(buy_order.chained_orders) == 1
    assert buy_order.tag == "super"
    stop_order = buy_order.chained_orders[0]
    assert isinstance(stop_order, trading_personal_data.StopLossOrder)
    assert stop_order.origin_quantity == decimal.Decimal("0.01") \
           - trading_personal_data.get_fees_for_currency(buy_order.fee, stop_order.quantity_currency)
    assert stop_order.origin_price == decimal.Decimal("10")
    # stop has been triggered as signal is triggering a buy market order that is instantly filled
    assert stop_order.is_waiting_for_chained_trigger is False
    assert stop_order.associated_entry_ids == [buy_order.order_id]
    assert stop_order.tag == "super"
    assert stop_order.reduce_only is False
    assert stop_order.trailing_profile is None
    assert stop_order.cancel_policy is None
    assert stop_order.is_open()

    state = trading_enums.EvaluatorStates.LONG.value
    # take profit only
    data = {
        consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal("100000"),
        consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [],
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
    }
    orders_with_tp = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), state, data=data)
    buy_order = orders_with_tp[0]
    assert len(buy_order.chained_orders) == 1
    take_profit_order = buy_order.chained_orders[0]
    assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
    assert take_profit_order.origin_quantity == decimal.Decimal("0.01") \
           - trading_personal_data.get_fees_for_currency(buy_order.fee, take_profit_order.quantity_currency)
    assert take_profit_order.origin_price == decimal.Decimal("100000")
    assert take_profit_order.is_waiting_for_chained_trigger
    assert take_profit_order.associated_entry_ids == [buy_order.order_id]
    assert take_profit_order.trailing_profile is None
    assert not take_profit_order.is_open()
    assert not take_profit_order.is_created()
    assert take_profit_order.reduce_only is False
    # take profit only using ADDITIONAL_TAKE_PROFIT_PRICES_KEY
    data = {
        consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [decimal.Decimal("100000")],
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
    }
    orders_with_tp = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), state, data=data)
    buy_order = orders_with_tp[0]
    assert len(buy_order.chained_orders) == 1
    take_profit_order = buy_order.chained_orders[0]
    assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
    assert take_profit_order.origin_quantity == decimal.Decimal("0.01") \
           - trading_personal_data.get_fees_for_currency(buy_order.fee, take_profit_order.quantity_currency)
    assert take_profit_order.origin_price == decimal.Decimal("100000")
    assert take_profit_order.is_waiting_for_chained_trigger
    assert take_profit_order.associated_entry_ids == [buy_order.order_id]
    assert not take_profit_order.is_open()
    assert not take_profit_order.is_created()
    assert take_profit_order.reduce_only is False
    assert take_profit_order.trailing_profile is None

    # stop loss and take profit
    data = {
        consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal("100012"),
        consumer.STOP_PRICE_KEY: decimal.Decimal("123"),
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
    }
    orders_with_tp = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.4)), state, data=data)
    buy_order = orders_with_tp[0]
    assert len(buy_order.chained_orders) == 2
    stop_order = buy_order.chained_orders[0]
    assert isinstance(stop_order, trading_personal_data.StopLossOrder)
    assert stop_order.origin_quantity == decimal.Decimal("0.01") \
           - trading_personal_data.get_fees_for_currency(buy_order.fee, stop_order.quantity_currency)
    assert stop_order.origin_price == decimal.Decimal("123")
    assert stop_order.is_waiting_for_chained_trigger
    assert stop_order.associated_entry_ids == [buy_order.order_id]
    assert stop_order.trailing_profile is None
    assert stop_order.cancel_policy is None
    assert not take_profit_order.is_open()
    assert not take_profit_order.is_created()
    take_profit_order = buy_order.chained_orders[1]
    assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
    assert take_profit_order.origin_quantity == decimal.Decimal("0.01") \
           - trading_personal_data.get_fees_for_currency(buy_order.fee, take_profit_order.quantity_currency)
    assert take_profit_order.origin_price == decimal.Decimal("100012")
    assert take_profit_order.is_waiting_for_chained_trigger
    assert take_profit_order.associated_entry_ids == [buy_order.order_id]
    assert not take_profit_order.is_open()
    assert not take_profit_order.is_created()
    assert take_profit_order.reduce_only is False
    assert isinstance(stop_order.order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)
    assert take_profit_order.order_group is stop_order.order_group
    assert take_profit_order.trailing_profile is None
    assert take_profit_order.cancel_policy is None

    # stop loss and take profit but decreasing position size: create stop loss and no take profit
    # (this initial order is a take profit already)
    state = trading_enums.EvaluatorStates.SHORT.value
    data = {
        consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal("100012"),
        consumer.STOP_PRICE_KEY: decimal.Decimal("123"),
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
    }
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.4)), state, data=data)
    assert len(orders) == 1
    sell_limit = orders[0]
    order_group = sell_limit.order_group
    stop_loss = exchange_manager.exchange_personal_data.orders_manager.get_order_from_group(order_group.name)[1]
    assert isinstance(sell_limit, trading_personal_data.SellLimitOrder)
    assert isinstance(stop_loss, trading_personal_data.StopLossOrder)
    assert sell_limit.chained_orders == []
    assert stop_loss.associated_entry_ids is None
    assert stop_loss.chained_orders == []
    assert stop_loss.reduce_only is True    # True as force stop loss
    assert stop_loss.origin_price == decimal.Decimal("123")
    assert stop_loss.trailing_profile is None
    assert stop_loss.cancel_policy is None
    assert stop_loss.origin_quantity == decimal.Decimal("0.01") \
           - trading_personal_data.get_fees_for_currency(sell_limit.fee, stop_loss.quantity_currency)


async def test_chained_multiple_take_profit_orders(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # with BTC/USDT
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[symbol] = \
        last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))

    state = trading_enums.EvaluatorStates.LONG.value
    # 1 take profit and 2 additional (3 in total)
    data = {
        consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal("100000"),
        consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [decimal.Decimal("110000"), decimal.Decimal("120000")],
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
    }
    orders_with_tps = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), state, data=data)
    buy_order = orders_with_tps[0]
    tp_prices = [decimal.Decimal("100000"), decimal.Decimal("110000"), decimal.Decimal("120000")]
    assert len(buy_order.chained_orders) == len(tp_prices)
    for i, take_profit_order in enumerate(buy_order.chained_orders):
        is_last = i == len(buy_order.chained_orders) - 1
        assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
        assert take_profit_order.origin_quantity == (
            decimal.Decimal("0.01")
           - trading_personal_data.get_fees_for_currency(buy_order.fee, take_profit_order.quantity_currency)
        ) / decimal.Decimal(str(len(tp_prices)))
        assert take_profit_order.order_group is None
        assert take_profit_order.origin_price == tp_prices[i]
        assert take_profit_order.is_waiting_for_chained_trigger
        assert take_profit_order.associated_entry_ids == [buy_order.order_id]
        assert not take_profit_order.is_open()
        assert not take_profit_order.is_created()
        assert take_profit_order.update_with_triggering_order_fees == is_last
        assert take_profit_order.trailing_profile is None
        assert take_profit_order.is_active is True

    # only 2 additional (2 in total)
    data = {
        consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [decimal.Decimal("110000"), decimal.Decimal("120000")],
        consumer.VOLUME_KEY: decimal.Decimal("0.01"), consumer.TRAILING_PROFILE: None
    }
    orders_with_tps = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), state, data=data)
    buy_order = orders_with_tps[0]
    tp_prices = [decimal.Decimal("110000"), decimal.Decimal("120000")]
    assert len(buy_order.chained_orders) == len(tp_prices)
    for i, take_profit_order in enumerate(buy_order.chained_orders):
        is_last = i == len(buy_order.chained_orders) - 1
        assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
        assert take_profit_order.origin_quantity == (
            decimal.Decimal("0.01")
           - trading_personal_data.get_fees_for_currency(buy_order.fee, take_profit_order.quantity_currency)
        ) / decimal.Decimal(str(len(tp_prices)))
        assert take_profit_order.origin_price == tp_prices[i]
        assert take_profit_order.is_waiting_for_chained_trigger
        assert take_profit_order.associated_entry_ids == [buy_order.order_id]
        assert not take_profit_order.is_open()
        assert not take_profit_order.is_created()
        assert take_profit_order.update_with_triggering_order_fees == is_last
        assert take_profit_order.trailing_profile is None
        assert take_profit_order.is_active is True

    # only 2 additional with volume (2 in total)
    volume_ratios = [decimal.Decimal("1"), decimal.Decimal("1.2")]
    data = {
        consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [decimal.Decimal("110000"), decimal.Decimal("120000")],
        consumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: volume_ratios,
        consumer.VOLUME_KEY: decimal.Decimal("0.01"), consumer.TRAILING_PROFILE: None
    }
    orders_with_tps = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), state, data=data)
    buy_order = orders_with_tps[0]
    tp_prices = [decimal.Decimal("110000"), decimal.Decimal("120000")]
    assert len(buy_order.chained_orders) == len(tp_prices)
    for i, take_profit_order in enumerate(buy_order.chained_orders):
        is_last = i == len(buy_order.chained_orders) - 1
        assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
        assert take_profit_order.origin_quantity == (
            decimal.Decimal("0.01")
           - trading_personal_data.get_fees_for_currency(buy_order.fee, take_profit_order.quantity_currency)
        ) * volume_ratios[i] / sum(volume_ratios)
        assert take_profit_order.origin_price == tp_prices[i]
        assert take_profit_order.is_waiting_for_chained_trigger
        assert take_profit_order.associated_entry_ids == [buy_order.order_id]
        assert not take_profit_order.is_open()
        assert not take_profit_order.is_created()
        assert take_profit_order.update_with_triggering_order_fees == is_last
        assert take_profit_order.trailing_profile is None
        assert take_profit_order.is_active is True

    # stop loss and 1 take profit and 5 additional with volume data (6 TP in total)
    exchange_manager.trader.enable_inactive_orders = True
    tp_prices = [
        decimal.Decimal("100012"),
        decimal.Decimal("110000"), decimal.Decimal("120000"), decimal.Decimal("130000"),
        decimal.Decimal("140000"), decimal.Decimal("150000")
    ]
    tp_volumes = [
        decimal.Decimal(str(val))
        for val in (
            1,
            2, 2.5, 2,
            3, 2
        )
    ]
    data = {
        consumer.STOP_PRICE_KEY: decimal.Decimal("123"),
        consumer.TAKE_PROFIT_PRICE_KEY: tp_prices[0],
        consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: tp_prices[1:],
        consumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: tp_volumes,  # inclue volume of 1st TP
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
    }
    orders_with_tp = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.4)), state, data=data)
    buy_order = orders_with_tp[0]
    assert len(buy_order.chained_orders) == 1 + len(tp_prices)
    stop_order = buy_order.chained_orders[0]
    assert isinstance(stop_order, trading_personal_data.StopLossOrder)
    assert stop_order.origin_quantity == decimal.Decimal("0.01") \
           - trading_personal_data.get_fees_for_currency(buy_order.fee, stop_order.quantity_currency)
    assert stop_order.origin_price == decimal.Decimal("123")
    assert stop_order.is_waiting_for_chained_trigger
    assert stop_order.associated_entry_ids == [buy_order.order_id]
    assert stop_order.update_with_triggering_order_fees is True
    assert stop_order.trailing_profile is None
    assert stop_order.is_active is True
    assert len(buy_order.chained_orders[1:]) == len(tp_prices)
    for i, take_profit_order in enumerate(buy_order.chained_orders[1:]):
        is_last = i == len(buy_order.chained_orders[1:]) - 1
        assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
        assert take_profit_order.origin_quantity == (
            decimal.Decimal("0.01")
           - trading_personal_data.get_fees_for_currency(buy_order.fee, take_profit_order.quantity_currency)
        ) * tp_volumes[i] / sum(tp_volumes)
        assert take_profit_order.origin_price == tp_prices[i]
        assert take_profit_order.is_active is False
        assert take_profit_order.is_waiting_for_chained_trigger
        assert take_profit_order.associated_entry_ids == [buy_order.order_id]
        assert not take_profit_order.is_open()
        assert not take_profit_order.is_created()
        assert isinstance(stop_order.order_group, trading_personal_data.BalancedTakeProfitAndStopOrderGroup)
        assert take_profit_order.order_group is stop_order.order_group
        assert take_profit_order.update_with_triggering_order_fees == is_last
        assert take_profit_order.trailing_profile is None


async def test_chained_multiple_take_profit_with_filled_tp_trailing_stop_orders(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # with BTC/USDT
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[symbol] = \
        last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))

    exchange_manager.trader.enable_inactive_orders = True
    state = trading_enums.EvaluatorStates.LONG.value
    # stop loss and 1 take profit and 5 additional (6 TP in total)
    tp_prices = [
        decimal.Decimal("100012"),
        decimal.Decimal("110000"), decimal.Decimal("120000"), decimal.Decimal("130000"),
        decimal.Decimal("140000"), decimal.Decimal("150000")
    ]
    data = {
        consumer.STOP_PRICE_KEY: decimal.Decimal("123"),
        consumer.TAKE_PROFIT_PRICE_KEY: tp_prices[0],
        consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: tp_prices[1:],
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
        consumer.TRAILING_PROFILE: trading_personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT.value,
    }
    orders_with_tp = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.4)), state, data=data)
    buy_order = orders_with_tp[0]
    assert len(buy_order.chained_orders) == 1 + len(tp_prices)
    stop_order = buy_order.chained_orders[0]
    assert isinstance(stop_order, trading_personal_data.StopLossOrder)
    assert stop_order.origin_quantity == decimal.Decimal("0.01") \
           - trading_personal_data.get_fees_for_currency(buy_order.fee, stop_order.quantity_currency)
    assert stop_order.origin_price == decimal.Decimal("123")
    assert stop_order.is_waiting_for_chained_trigger
    assert stop_order.associated_entry_ids == [buy_order.order_id]
    assert stop_order.update_with_triggering_order_fees is True
    assert stop_order.is_active is True
    assert stop_order.trailing_profile == trading_personal_data.FilledTakeProfitTrailingProfile([
        trading_personal_data.TrailingPriceStep(float(trailing_price), float(trigger_price), True)
        for trailing_price, trigger_price in zip([buy_order.origin_price] + tp_prices[:-1], tp_prices)
    ])
    assert len(buy_order.chained_orders[1:]) == len(tp_prices)
    for i, take_profit_order in enumerate(buy_order.chained_orders[1:]):
        is_last = i == len(buy_order.chained_orders[1:]) - 1
        assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
        assert take_profit_order.origin_quantity == (
            decimal.Decimal("0.01")
           - trading_personal_data.get_fees_for_currency(buy_order.fee, take_profit_order.quantity_currency)
        ) / decimal.Decimal(str(len(tp_prices)))
        assert take_profit_order.origin_price == tp_prices[i]
        assert take_profit_order.is_waiting_for_chained_trigger
        assert take_profit_order.associated_entry_ids == [buy_order.order_id]
        assert take_profit_order.is_active is False
        assert not take_profit_order.is_open()
        assert not take_profit_order.is_created()
        assert isinstance(stop_order.order_group, trading_personal_data.TrailingOnFilledTPBalancedOrderGroup)
        assert take_profit_order.order_group is stop_order.order_group
        assert take_profit_order.update_with_triggering_order_fees == is_last
        assert take_profit_order.trailing_profile is None


async def test_create_stop_loss_orders(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools
    exchange_manager.trader.enable_inactive_orders = True

    # with BTC/USDT
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[symbol] = \
        last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))

    state = trading_enums.EvaluatorStates.SHORT.value
    data = {
        consumer.STOP_PRICE_KEY: decimal.Decimal("10"),
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
        consumer.STOP_ONLY: True
    }
    created_orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.6)), state, data=data)
    assert len(created_orders) == 1
    stop_order = created_orders[0]
    assert isinstance(stop_order, trading_personal_data.StopLossOrder)
    assert stop_order.origin_quantity == decimal.Decimal("0.01")
    assert stop_order.origin_price == decimal.Decimal("10")
    assert stop_order.side is trading_enums.TradeOrderSide.SELL
    assert stop_order.is_waiting_for_chained_trigger is False
    assert stop_order.update_with_triggering_order_fees is False    # not chained order
    assert stop_order.tag is None
    assert stop_order.is_active is True
    assert stop_order.is_open()

    state = trading_enums.EvaluatorStates.LONG.value
    data = {
        consumer.STOP_PRICE_KEY: decimal.Decimal("5"),
        consumer.VOLUME_KEY: decimal.Decimal("0.01"),
        consumer.STOP_ONLY: True,
        consumer.TAG_KEY: "plop1"
    }
    created_orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(-0.6)), state, data=data)
    assert len(created_orders) == 1
    stop_order = created_orders[0]
    assert isinstance(stop_order, trading_personal_data.StopLossOrder)
    assert stop_order.origin_quantity == decimal.Decimal("0.01")
    assert stop_order.origin_price == decimal.Decimal("5")
    assert stop_order.side is trading_enums.TradeOrderSide.BUY
    assert stop_order.is_waiting_for_chained_trigger is False
    assert stop_order.tag == "plop1"
    assert stop_order.is_active is True
    assert stop_order.is_open()


async def test_get_limit_quantity_from_risk(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools
    ctx = script_keywords.get_base_context(consumer.trading_mode, symbol)
    last_btc_price = 100
    trading_api.force_set_mark_price(exchange_manager, symbol, last_btc_price)
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[
        symbol] = last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(last_btc_price * 10 + 1000))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.current_crypto_currencies_values["BTC"] = \
        decimal.Decimal(str(last_btc_price))
    # with user amount
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal(1)
    consumer.trading_mode.trading_config[trading_constants.CONFIG_BUY_ORDER_AMOUNT] = 10
    consumer.trading_mode.trading_config[trading_constants.CONFIG_SELL_ORDER_AMOUNT] = 10
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("10")

    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.5")
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("9.9")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("1.9")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, True) == decimal.Decimal("1.9")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    # decreasing position
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, False) == decimal.Decimal("10")
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, False) == decimal.Decimal("10")

    # without user amount
    consumer.trading_mode.trading_config.pop(trading_constants.CONFIG_BUY_ORDER_AMOUNT)
    consumer.trading_mode.trading_config.pop(trading_constants.CONFIG_SELL_ORDER_AMOUNT)

    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.5")
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("8.7")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("1.9")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, True) == decimal.Decimal("1.9")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    # decreasing position
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, False) == decimal.Decimal("15")
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, False) == decimal.Decimal("15")

    # all-in orders
    # 1. sell
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("1.9")
    consumer.SELL_WITH_MAXIMUM_SIZE_ORDERS = True
    # increasing position (would be 1.9 without all-in)
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("15")
    # decreasing position
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, False) == decimal.Decimal("15")

    # 2. buy
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, True) == decimal.Decimal("1.9")
    consumer.BUY_WITH_MAXIMUM_SIZE_ORDERS = True
    # increasing position (would be 1.9 without all-in)
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, True) == decimal.Decimal("15")
    # decreasing position
    assert await consumer._get_limit_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, False) == decimal.Decimal("15")


async def test_get_market_quantity_from_risk(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools
    ctx = script_keywords.get_base_context(consumer.trading_mode, symbol)
    last_btc_price = 80
    trading_api.force_set_mark_price(exchange_manager, symbol, last_btc_price)
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[
        symbol] = last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(last_btc_price * 10 + 1000))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.current_crypto_currencies_values["BTC"] = \
        decimal.Decimal(str(last_btc_price))
    # with user amount
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal(1)
    consumer.trading_mode.trading_config[trading_constants.CONFIG_BUY_ORDER_AMOUNT] = 10
    consumer.trading_mode.trading_config[trading_constants.CONFIG_SELL_ORDER_AMOUNT] = 10
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("10")

    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.5")
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("10")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("2.125")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, True) == decimal.Decimal("2.125")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    # decreasing position
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, False) == decimal.Decimal("10")
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, False) == decimal.Decimal("10")

    # without user amount
    consumer.trading_mode.trading_config.pop(trading_constants.CONFIG_BUY_ORDER_AMOUNT)
    consumer.trading_mode.trading_config.pop(trading_constants.CONFIG_SELL_ORDER_AMOUNT)

    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.5")
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("11.125")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("2.125")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, True) == decimal.Decimal("2.125")
    consumer.MAX_CURRENCY_RATIO = decimal.Decimal("0.1")
    # decreasing position
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, False) == decimal.Decimal("10.8")
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, False) == decimal.Decimal("10.8")

    # all-in orders
    # 1. sell
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("2.125")
    consumer.SELL_WITH_MAXIMUM_SIZE_ORDERS = True
    # increasing position (would be 2.125 without all-in)
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, True) == decimal.Decimal("15")
    # decreasing position
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", True, False) == decimal.Decimal("15")

    # 2. buy
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, True) == decimal.Decimal("2.125")
    consumer.BUY_WITH_MAXIMUM_SIZE_ORDERS = True
    # increasing position (would be 1.9 without all-in)
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, True) == decimal.Decimal("15")
    # decreasing position
    assert await consumer._get_market_quantity_from_risk(ctx, 1, decimal.Decimal(15), "BTC", False, False) == decimal.Decimal("15")


async def test_target_profit_mode(tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = tools

    # with BTC/USDT
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[symbol] = \
        last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))
    consumer.USE_TARGET_PROFIT_MODE = True
    _, _, _, _, symbol_market = await trading_personal_data.get_pre_order_data(
        exchange_manager, symbol=symbol, timeout=1
    )
    state = trading_enums.EvaluatorStates.LONG.value
    # take profit only
    consumer.USE_STOP_ORDERS = False
    orders_with_tp = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), state)
    buy_order = orders_with_tp[0]
    assert len(buy_order.chained_orders) == 1
    take_profit_order = buy_order.chained_orders[0]
    assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
    assert take_profit_order.side is trading_enums.TradeOrderSide.SELL
    assert take_profit_order.origin_quantity == buy_order.origin_quantity
    assert take_profit_order.reduce_only is False
    assert take_profit_order.origin_price == trading_personal_data.decimal_adapt_price(
        symbol_market,
        buy_order.origin_price * (trading_constants.ONE + consumer.TARGET_PROFIT_TAKE_PROFIT)
    )
    assert take_profit_order.is_waiting_for_chained_trigger
    assert take_profit_order.associated_entry_ids == [buy_order.order_id]
    assert not take_profit_order.is_open()
    assert not take_profit_order.is_created()

    exchange_manager.trader.enable_inactive_orders = True
    # stop loss and take profit
    consumer.USE_STOP_ORDERS = True
    orders_with_tp = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.4)), state)
    buy_order = orders_with_tp[0]
    assert len(buy_order.chained_orders) == 2
    stop_order = buy_order.chained_orders[0]
    assert isinstance(stop_order, trading_personal_data.StopLossOrder)
    assert stop_order.side is trading_enums.TradeOrderSide.SELL
    assert stop_order.origin_quantity == buy_order.origin_quantity
    assert stop_order.reduce_only is False
    assert stop_order.is_active is True
    assert stop_order.origin_price == trading_personal_data.decimal_adapt_price(
        symbol_market,
        buy_order.origin_price * (trading_constants.ONE - consumer.TARGET_PROFIT_STOP_LOSS)
    )
    assert stop_order.is_waiting_for_chained_trigger
    assert stop_order.associated_entry_ids == [buy_order.order_id]
    assert not stop_order.is_open()
    assert not stop_order.is_created()
    take_profit_order = buy_order.chained_orders[1]
    assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
    assert take_profit_order.side is trading_enums.TradeOrderSide.SELL
    assert take_profit_order.origin_quantity == buy_order.origin_quantity
    assert take_profit_order.origin_price == trading_personal_data.decimal_adapt_price(
        symbol_market,
        buy_order.origin_price * (trading_constants.ONE + consumer.TARGET_PROFIT_TAKE_PROFIT)
    )
    assert take_profit_order.is_waiting_for_chained_trigger
    assert take_profit_order.associated_entry_ids == [buy_order.order_id]
    assert not take_profit_order.is_open()
    assert not take_profit_order.is_created()
    assert take_profit_order.is_active is False
    assert isinstance(stop_order.order_group, trading_personal_data.OneCancelsTheOtherOrderGroup)
    assert take_profit_order.order_group is stop_order.order_group

    # stop loss and take profit but decreasing position size: do nothing in this mode
    # (this initial order is a take profit already)
    state = trading_enums.EvaluatorStates.SHORT.value
    orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(0.4)), state)
    assert orders == []


async def test_target_profit_mode_futures_trading(future_tools):
    exchange_manager, trader, symbol, consumer, last_btc_price = future_tools

    # with BTC/USDT
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair[symbol] = \
        last_btc_price
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
        decimal.Decimal(str(10 + 1000 / last_btc_price))
    consumer.USE_TARGET_PROFIT_MODE = True
    consumer.TARGET_PROFIT_ENABLE_POSITION_INCREASE = True
    _, _, _, _, symbol_market = await trading_personal_data.get_pre_order_data(
        exchange_manager, symbol=symbol, timeout=1
    )

    exchange_manager.trader.enable_inactive_orders = True
    # take profit and stop loss / long signal
    consumer.TARGET_PROFIT_TAKE_PROFIT = decimal.Decimal(str(10))
    consumer.TARGET_PROFIT_STOP_LOSS = decimal.Decimal(str(2.5))
    consumer.USE_STOP_ORDERS = True
    long_orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(-1)), trading_enums.EvaluatorStates.LONG.value)
    buy_order = long_orders[0]
    assert isinstance(buy_order, trading_personal_data.BuyLimitOrder)
    assert len(buy_order.chained_orders) == 2
    take_profit_order = buy_order.chained_orders[1]
    stop_loss_order = buy_order.chained_orders[0]
    assert isinstance(take_profit_order, trading_personal_data.SellLimitOrder)
    assert isinstance(stop_loss_order, trading_personal_data.StopLossOrder)
    # both are active on futures
    assert stop_loss_order.is_active is True
    assert take_profit_order.is_active is True
    assert take_profit_order.side is trading_enums.TradeOrderSide.SELL
    assert take_profit_order.origin_quantity == buy_order.origin_quantity
    assert take_profit_order.origin_price == trading_personal_data.decimal_adapt_price(
        symbol_market,
        buy_order.origin_price * (trading_constants.ONE + consumer.TARGET_PROFIT_TAKE_PROFIT)
    )
    assert stop_loss_order.side is trading_enums.TradeOrderSide.SELL
    assert stop_loss_order.origin_quantity == buy_order.origin_quantity
    assert stop_loss_order.origin_price == trading_personal_data.decimal_adapt_price(
        symbol_market,
        buy_order.origin_price * (trading_constants.ONE - consumer.TARGET_PROFIT_STOP_LOSS)
    )

    consumer.trading_mode.trading_config[trading_constants.CONFIG_BUY_ORDER_AMOUNT] = "100q"
    # take profit and stop loss / short signal
    short_orders = await consumer.create_new_orders(symbol, decimal.Decimal(str(1)), trading_enums.EvaluatorStates.SHORT.value)
    sell_order = short_orders[0]
    assert sell_order.origin_quantity == decimal.Decimal('0.01426697')  # 0.01739031 without 100q config
    assert isinstance(sell_order, trading_personal_data.SellLimitOrder)
    assert len(sell_order.chained_orders) == 2
    take_profit_order = sell_order.chained_orders[1]
    stop_loss_order = sell_order.chained_orders[0]
    assert isinstance(take_profit_order, trading_personal_data.BuyLimitOrder)
    assert isinstance(stop_loss_order, trading_personal_data.StopLossOrder)
    assert take_profit_order.side is trading_enums.TradeOrderSide.BUY
    assert take_profit_order.origin_quantity == sell_order.origin_quantity
    assert take_profit_order.reduce_only is True
    assert take_profit_order.origin_price == trading_personal_data.decimal_adapt_price(
        symbol_market,
        sell_order.origin_price * (trading_constants.ONE - consumer.TARGET_PROFIT_TAKE_PROFIT)
    )
    assert stop_loss_order.side is trading_enums.TradeOrderSide.BUY
    assert stop_loss_order.origin_quantity == sell_order.origin_quantity
    assert stop_loss_order.reduce_only is True
    assert stop_loss_order.origin_price == trading_personal_data.decimal_adapt_price(
        symbol_market,
        sell_order.origin_price * (trading_constants.ONE + consumer.TARGET_PROFIT_STOP_LOSS)
    )
    current_position = exchange_manager.exchange_personal_data.positions_manager \
        .get_symbol_position(
        symbol,
        trading_enums.PositionSide.BOTH
    )
    assert current_position.is_idle()
    await sell_order.on_fill(force_fill=True)
    assert not current_position.is_idle()
    short_orders_2 = await consumer.create_new_orders(symbol, decimal.Decimal(str(1)), trading_enums.EvaluatorStates.SHORT.value)
    # created order
    assert len(short_orders_2) == 1

    consumer.TARGET_PROFIT_ENABLE_POSITION_INCREASE = False
    short_orders_2 = await consumer.create_new_orders(symbol, decimal.Decimal(str(1)), trading_enums.EvaluatorStates.SHORT.value)
    # did not create order as increasing position is disabled
    assert short_orders_2 == []
