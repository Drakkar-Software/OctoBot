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
import asyncio
import copy
import decimal
import contextlib
import mock
import os
import pytest

import async_channel.util as channel_util
import octobot_commons.constants as commons_constants
import octobot_commons.configuration.user_inputs as commons_user_inputs
import octobot_commons.errors as commons_errors
import octobot_commons.enums as commons_enums
import octobot_commons.tree as commons_tree
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.tests.test_config as test_config
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_backtesting.api as backtesting_api
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.modes as trading_modes
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.util as trading_util

import tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_trading as simple_market_making_trading
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_order_book_distribution as advanced_order_book_distribution
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.spot_hedging_engine as spot_hedging_engine_import
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.hedging_engine as hedging_engine_import
import tentacles.Trading.Mode.simple_market_making_trading_mode.scheduled_volume as scheduled_volume
import tentacles.Trading.Mode.market_making_trading_mode.market_making_trading as market_making_trading_mode
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_reference_price as advanced_reference_price_import
import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging as hedging
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.errors as hedging_errors

import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges
import tests.test_utils.trading_modes as test_trading_modes

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

# binance symbol market extract
SYMBOL_MARKET = {
    'id': 'BTCUSDT', 'lowercaseId': 'btcusdt', 'symbol': 'BTC/USDT', 'base': 'BTC', 'quote': 'USDT',
    'settle': None, 'baseId': 'BTC', 'quoteId': 'USDT', 'settleId': None, 'type': 'spot', 'spot': True,
    'margin': True, 'swap': False, 'future': False, 'option': False, 'index': None, 'active': True,
    'contract': False, 'linear': None, 'inverse': None, 'subType': None, 'taker': 0.001, 'maker': 0.001,
    'contractSize': None, 'expiry': None, 'expiryDatetime': None, 'strike': None, 'optionType': None,
    'precision': {'amount': 5, 'price': 2, 'cost': None, 'base': 1e-08, 'quote': 1e-08},
    'limits': {
        'leverage': {'min': None, 'max': None},
        'amount': {'min': 1e-05, 'max': 9000.0},
        'price': {'min': 0.01, 'max': 1000000.0},
        'cost': {'min': 5.0, 'max': 9000000.0},
        'market': {'min': 0.0, 'max': 107.1489592}
    }, 'created': None,
    'percentage': True, 'feeSide': 'get', 'tierBased': False
}

FORMULA_REFERENCE_PRICE = decimal.Decimal("1.2")


def _incomplete_ticker(symbol: str) -> dict:
    return {
        trading_enums.ExchangeConstantsTickersColumns.SYMBOL.value: symbol,
        trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: None,
        trading_enums.ExchangeConstantsTickersColumns.LAST.value: None,
        trading_enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value: 0.0,
        trading_enums.ExchangeConstantsTickersColumns.QUOTE_VOLUME.value: None,
    }


def _get_mm_config(symbol):
    return {
      "pair_settings": [
        {
          "asks_count": 5,
          "auto_adapt_config": True,
          "bids_count": 5,
          "exchange": "binance",
          "funds_distribution": "flat",
          "max_base_budget": 0,
          "max_quote_budget": 0,
          "max_spread": 20,
          "min_base_budget": 100000,
          "min_quote_budget": 1000,
          "min_spread": 5,
          "order_book_depth": {
            "cumulated_volume_percent": 6,
            "percent_daily_trading_volume": 1
          },
          "orders_distribution": "linear",
          "reference_price": [
            {
              "exchange": "binance",
              "formula": "",
              "pair": symbol,
              "weight": 1
            }
          ],
          "refresh_period": 0,
          "tolerated_above_depth_ratio": 1.5,
          "tolerated_bellow_depth_ratio": 0.8,
          "trading_pair": symbol
        }
      ]
    }


async def _init_trading_mode(config, exchange_manager, symbol):
    mode = simple_market_making_trading.SimpleMarketMakingTradingMode(config, exchange_manager)
    mode.symbol = None if mode.get_is_symbol_wildcard() else symbol
    mode.trading_config = _get_mm_config(symbol)
    await mode.initialize(trading_config=mode.trading_config)
    # add mode to exchange manager so that it can be stopped and freed from memory
    exchange_manager.trading_modes.append(mode)
    test_trading_modes.set_ready_to_start(mode.producers[0])
    return mode, mode.producers[0]


@contextlib.asynccontextmanager
async def _get_tools(symbol, additional_portfolio={}):
    tentacles_manager_api.reload_tentacle_info()
    exchange_manager = None
    try:
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 1000
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO][
            "BTC"] = 10
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO].update(additional_portfolio)
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        exchange_manager.tentacles_setup_config = test_utils_config.load_test_tentacles_config()

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

        # set BTC/USDT price at 1000 USDT
        if symbol not in exchange_manager.client_symbols:
            exchange_manager.client_symbols.append(symbol)
        trading_api.force_set_mark_price(exchange_manager, symbol, 1000)

        mode, producer = await _init_trading_mode(config, exchange_manager, symbol)

        yield producer, mode.get_trading_mode_consumers()[0], exchange_manager
    finally:
        if exchange_manager:
            await _stop(exchange_manager)


async def _stop(exchange_manager):
    for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
        await backtesting_api.stop_importer(importer)
    await exchange_manager.exchange.backtesting.stop()
    await exchange_manager.stop()


@contextlib.contextmanager
def _real_spot_hedging_engine_init_session():
    """
    Resets the hedging singleton registry, patches background hedging startup, and delegates
    get_or_create_hedging_engine to the real implementation (spy for assert_called_once_with).
    Clears the registry again after the block.
    """
    hedging._HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID.clear()
    real_get_or_create = hedging.get_or_create_hedging_engine
    try:
        with mock.patch.object(
            hedging_engine_import.HedgingEngine,
            "_async_start_for_hedging_details",
            mock.AsyncMock(),
        ), mock.patch.object(
            hedging,
            "get_or_create_hedging_engine",
            mock.Mock(side_effect=real_get_or_create),
        ) as get_or_create_spy:
            yield get_or_create_spy
    finally:
        hedging._HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID.clear()


class TestGetHedgingEngineConfig:
    def test_fills_canonical_from_legacy_when_canonical_missing(self):
        cls = simple_market_making_trading.SimpleMarketMakingTradingMode
        symbol_cfg = {
            cls.HEDGING_ENGINE: {
                cls.LEGACY_AVERAGE_PRIVE_COUNTED_MINUTES_KEY: 99,
            }
        }
        result = cls.get_hedging_engine_config(symbol_cfg)
        assert result[cls.AVERAGE_PRICE_COUNTED_MINUTES] == 99

    def test_canonical_key_takes_precedence_over_legacy(self):
        cls = simple_market_making_trading.SimpleMarketMakingTradingMode
        symbol_cfg = {
            cls.HEDGING_ENGINE: {
                cls.AVERAGE_PRICE_COUNTED_MINUTES: 10,
                cls.LEGACY_AVERAGE_PRIVE_COUNTED_MINUTES_KEY: 99,
            }
        }
        result = cls.get_hedging_engine_config(symbol_cfg)
        assert result[cls.AVERAGE_PRICE_COUNTED_MINUTES] == 10

    def test_does_not_mutate_original_hedging_dict(self):
        cls = simple_market_making_trading.SimpleMarketMakingTradingMode
        inner = {cls.LEGACY_AVERAGE_PRIVE_COUNTED_MINUTES_KEY: 5}
        symbol_cfg = {cls.HEDGING_ENGINE: inner}
        cls.get_hedging_engine_config(symbol_cfg)
        assert cls.AVERAGE_PRICE_COUNTED_MINUTES not in inner


@pytest.mark.parametrize(
    "hedging_exchange_case",
    (
        "missing_exchange",
        "empty_string",
        "explicit_none",
    ),
)
async def test_init_user_inputs_defaults_valid_hedging_off_without_exchange(hedging_exchange_case):
    symbol = "BTC/USDT"
    cls = simple_market_making_trading.SimpleMarketMakingTradingMode
    real_find_parent = commons_user_inputs._find_parent_config_node

    # Without array_indexes, pair_settings resolves to a list and user_input skips writes;
    # treat the first row as the parent so init_user_inputs merges defaults into it.
    def find_parent_pair_settings_row(tentacle_config, parent_input_name, array_indexes):
        if parent_input_name == cls.CONFIG_PAIR_SETTINGS and not array_indexes:
            pair_settings_value = tentacle_config.get(cls.CONFIG_PAIR_SETTINGS)
            if isinstance(pair_settings_value, list) and pair_settings_value:
                return pair_settings_value[0]
        return real_find_parent(tentacle_config, parent_input_name, array_indexes)

    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        mode = producer.trading_mode
        mode.trading_config = copy.deepcopy(_get_mm_config(symbol))
        with mock.patch.object(
            commons_user_inputs,
            "_find_parent_config_node",
            side_effect=find_parent_pair_settings_row,
        ):
            mode.init_user_inputs({})
        pair_config = mode.trading_config[cls.CONFIG_PAIR_SETTINGS][0]
        hedging_engine_cfg = pair_config[cls.HEDGING_ENGINE]
        assert hedging_engine_cfg[cls.HEDGING_EXCHANGE] == "" # ensure default is set
        hedging_engine_cfg[cls.HEDGING_MAX_LOSS_THRESHOLD] = 10
        hedging_engine_cfg[cls.LEGACY_AVERAGE_PRIVE_COUNTED_MINUTES_KEY] = 60
        if hedging_exchange_case == "missing_exchange":
            hedging_engine_cfg.pop(cls.HEDGING_EXCHANGE, None)
        elif hedging_exchange_case == "empty_string":
            hedging_engine_cfg[cls.HEDGING_EXCHANGE] = ""
        elif hedging_exchange_case == "explicit_none":
            hedging_engine_cfg[cls.HEDGING_EXCHANGE] = None
        assert producer._load_symbol_trading_config() is True
        producer.read_config()
        assert producer.order_book_distribution is not None
        assert producer.reference_prices_by_exchange
        with mock.patch.object(hedging, "get_or_create_hedging_engine", mock.Mock()) as get_or_create_mock:
            await producer._initialize_hedging_engine()
            get_or_create_mock.assert_not_called()
        assert producer._hedging_engine is None


async def _initialize_reference_prices(producer: simple_market_making_trading.SimpleMarketMakingTradingModeProducer):
    for reference_prices in producer.reference_prices_by_exchange.values():
        for reference_price in reference_prices:
            await reference_price.initialize_if_required(producer.exchange_manager)


async def test_handle_market_making_orders_with_formula_and_incomplete_ticker():
    symbol = "BTC/USDT"
    trading_mode_cls = simple_market_making_trading.SimpleMarketMakingTradingMode
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        pair_config = producer.trading_mode.trading_config[trading_mode_cls.CONFIG_PAIR_SETTINGS][0]
        pair_config[trading_mode_cls.REFERENCE_PRICE] = [{
            trading_mode_cls.EXCHANGE: "binance",
            trading_mode_cls.PAIR: symbol,
            trading_mode_cls.WEIGHT: 1,
            trading_mode_cls.FORMULA: str(FORMULA_REFERENCE_PRICE),
        }]
        producer.read_config()
        await producer._validate_reference_prices()
        await _initialize_reference_prices(producer)

        symbol_data = exchange_manager.exchange_symbols_data.get_exchange_symbol_data(symbol)
        symbol_data.handle_ticker_update(_incomplete_ticker(symbol))

        origin_submit_trading_evaluation = producer.submit_trading_evaluation
        with mock.patch.object(
            trading_personal_data,
            "get_potentially_outdated_price",
            mock.Mock(side_effect=KeyError("no mark price")),
        ), mock.patch.object(
            trading_api,
            "get_all_exchange_ids_with_same_matrix_id",
            mock.Mock(return_value=[exchange_manager.id]),
        ), mock.patch.object(
            trading_api,
            "get_exchange_manager_from_exchange_id",
            mock.Mock(return_value=exchange_manager),
        ):
            assert await producer._get_reference_price() == FORMULA_REFERENCE_PRICE

            with mock.patch.object(
                producer,
                "submit_trading_evaluation",
                mock.AsyncMock(side_effect=origin_submit_trading_evaluation),
            ) as submit_trading_evaluation_mock:
                current_price = decimal.Decimal("1000")
                trigger_source = "ref_price"
                symbol_market = copy.deepcopy(SYMBOL_MARKET)
                symbol_market["limits"]["cost"]["min"] = 0.01
                assert await producer._handle_market_making_orders(
                    current_price, symbol_market, trigger_source, False
                ) is True

                submit_trading_evaluation_mock.assert_called_once()
                data = submit_trading_evaluation_mock.mock_calls[0].kwargs["data"]
                assert data[simple_market_making_trading.SimpleMarketMakingTradingModeConsumer.CURRENT_PRICE_KEY] == (
                    current_price
                )
                order_plan: market_making_trading_mode.OrdersUpdatePlan = data[
                    simple_market_making_trading.SimpleMarketMakingTradingModeConsumer.ORDER_ACTIONS_PLAN_KEY
                ]
                assert len(order_plan.order_actions) == 10
                buy_actions = [
                    action for action in order_plan.order_actions
                    if isinstance(action, market_making_trading_mode.CreateOrderAction)
                    and action.order_data.side == trading_enums.TradeOrderSide.BUY
                ]
                sell_actions = [
                    action for action in order_plan.order_actions
                    if isinstance(action, market_making_trading_mode.CreateOrderAction)
                    and action.order_data.side == trading_enums.TradeOrderSide.SELL
                ]
                assert len(buy_actions) == len(sell_actions) == 5
                assert all(action.order_data.price < FORMULA_REFERENCE_PRICE for action in buy_actions)
                assert all(action.order_data.price > FORMULA_REFERENCE_PRICE for action in sell_actions)
                min_spread_ratio = decimal.Decimal("5") / decimal.Decimal("100")
                expected_best_bid = FORMULA_REFERENCE_PRICE * (
                    trading_constants.ONE - min_spread_ratio / decimal.Decimal("2")
                )
                assert buy_actions[0].order_data.price == expected_best_bid

                for _ in range(len(order_plan.order_actions)):
                    await asyncio_tools.wait_asyncio_next_cycle()

                open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
                assert len(open_orders) == 10
                assert all(
                    order.origin_price < FORMULA_REFERENCE_PRICE
                    for order in open_orders
                    if order.side == trading_enums.TradeOrderSide.BUY
                )
                assert all(
                    order.origin_price > FORMULA_REFERENCE_PRICE
                    for order in open_orders
                    if order.side == trading_enums.TradeOrderSide.SELL
                )


async def test_handle_market_making_orders_from_no_orders():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        price = decimal.Decimal(1000)
        origin_submit_trading_evaluation = producer.submit_trading_evaluation
        with mock.patch.object(
            producer, "submit_trading_evaluation", mock.AsyncMock(side_effect=origin_submit_trading_evaluation)
        ) as submit_trading_evaluation_mock, mock.patch.object(
            producer, "_get_reference_price", mock.AsyncMock(return_value=price)
        ) as _get_reference_price_mock:
            trigger_source = "ref_price"
            for reference_prices in producer.reference_prices_by_exchange.values():
                for reference_price in reference_prices:
                    reference_price.initialize_if_required(exchange_manager)
            # 1. full replace as no order exist
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            _get_reference_price_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_called_once()
            assert submit_trading_evaluation_mock.mock_calls[0].kwargs["symbol"] == symbol
            data = submit_trading_evaluation_mock.mock_calls[0].kwargs["data"]
            assert data[simple_market_making_trading.SimpleMarketMakingTradingModeConsumer.CURRENT_PRICE_KEY] == price
            assert data[simple_market_making_trading.SimpleMarketMakingTradingModeConsumer.SYMBOL_MARKET_KEY] == SYMBOL_MARKET
            order_plan: market_making_trading_mode.OrdersUpdatePlan = data[simple_market_making_trading.SimpleMarketMakingTradingModeConsumer.ORDER_ACTIONS_PLAN_KEY]
            assert isinstance(order_plan, market_making_trading_mode.OrdersUpdatePlan)
            assert len(order_plan.order_actions) == 10
            buy_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading_mode.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.BUY
            ]
            sell_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading_mode.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.SELL
            ]
            assert len(buy_actions) == len(sell_actions) == 5
            assert order_plan.cancelled == False
            assert order_plan.cancellable == False # full replace is not cancellable
            assert not order_plan.processed.is_set()
            assert order_plan.trigger_source == trigger_source

            # wait for orders to be created
            for _ in range(len(order_plan.order_actions)):
                await asyncio_tools.wait_asyncio_next_cycle()

            # ensure orders are properly created
            open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
            assert len(open_orders) == 10
            assert sorted([f"{o.origin_price}{o.side.value}" for o in open_orders]) == sorted([
                f"{a.order_data.price}{a.order_data.side.value}" for a in order_plan.order_actions
                if isinstance(a, market_making_trading_mode.CreateOrderAction)
            ])
            _get_reference_price_mock.reset_mock()
            submit_trading_evaluation_mock.reset_mock()

            # 2. receive an update but orders are already in place: nothing to do
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            _get_reference_price_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_not_called()
            _get_reference_price_mock.reset_mock()

            # 3. receive an update, orders are already in place but force_full_refresh is True: refresh orders
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, True) is True
            _get_reference_price_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_called_once()
            assert submit_trading_evaluation_mock.mock_calls[0].kwargs["symbol"] == symbol
            data = submit_trading_evaluation_mock.mock_calls[0].kwargs["data"]
            order_plan: market_making_trading_mode.OrdersUpdatePlan = data[market_making_trading_mode.MarketMakingTradingModeConsumer.ORDER_ACTIONS_PLAN_KEY]
            assert isinstance(order_plan, market_making_trading_mode.OrdersUpdatePlan)
            assert len(order_plan.order_actions) == 20
            cancel_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading_mode.CancelOrderAction)
            ]
            buy_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading_mode.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.BUY
            ]
            sell_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading_mode.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.SELL
            ]
            assert len(cancel_actions) == 10
            assert len(buy_actions) == len(sell_actions) == 5
            assert order_plan.cancelled == False
            assert order_plan.cancellable == False # full replace is not cancellable
            assert not order_plan.processed.is_set()
            assert order_plan.trigger_source == trigger_source

            # wait for orders to be created
            for _ in range(len(order_plan.order_actions)):
                await asyncio_tools.wait_asyncio_next_cycle()

            # ensure orders are properly created
            open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
            assert len(open_orders) == 10
            assert sorted([f"{o.origin_price}{o.side.value}" for o in open_orders]) == sorted([
                f"{a.order_data.price}{a.order_data.side.value}" for a in order_plan.order_actions
                if isinstance(a, market_making_trading_mode.CreateOrderAction)
            ])
            _get_reference_price_mock.reset_mock()
            submit_trading_evaluation_mock.reset_mock()


async def test_start():
    symbol = "BTC/USDT"
    with mock.patch.object(
        market_making_trading_mode.MarketMakingTradingModeProducer, "start", mock.AsyncMock()
    ) as mm_start_mock, mock.patch.object(
        trading_modes.AbstractTradingModeProducer, "start", mock.AsyncMock()
    ) as producer_start_mock, mock.patch.object(
        simple_market_making_trading.SimpleMarketMakingTradingModeProducer, "_ensure_market_making_orders_and_reschedule", mock.AsyncMock()
    ) as _ensure_market_making_orders_and_reschedule_mock, mock.patch.object(
        scheduled_volume.ScheduledVolume, "start", mock.AsyncMock()
    ) as scheduled_volume_start_mock, mock.patch.object(
        advanced_reference_price_import.AdvancedPriceSource, "initialize_if_required", mock.AsyncMock()
    ) as advanced_reference_price_initialize_mock, mock.patch.object(
        exchanges.Trader, "schedule_bot_stop", mock.AsyncMock()
    ) as schedule_bot_stop_mock:
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            # no config: healthy is False
            producer.healthy = False
            pair_config = producer.trading_mode.trading_config[
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
            ][0]
            pair_config.pop(simple_market_making_trading.SimpleMarketMakingTradingMode.SCHEDULED_VOLUME, None)
            assert len(pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE]) == 1
            assert producer.should_stop is False
            await producer.start()
            mm_start_mock.assert_not_called()
            producer_start_mock.assert_called_once()
            # no scheduled or stop watcher config
            scheduled_volume_start_mock.assert_not_called()
             # exited func before these calls
            advanced_reference_price_initialize_mock.assert_not_called()
            _ensure_market_making_orders_and_reschedule_mock.assert_not_called()
            schedule_bot_stop_mock.assert_awaited_once()
            assert producer.should_stop is False
            assert schedule_bot_stop_mock.mock_calls[0].args == (
                commons_enums.StopReason.INVALID_CONFIG,
                "Configuration error (self.healthy=False) on BTC/USDT [binance], scheduling bot stop"
            )
            assert producer._scheduled_volume is None
            mm_start_mock.reset_mock()
            producer_start_mock.reset_mock()
            scheduled_volume_start_mock.reset_mock()
            advanced_reference_price_initialize_mock.reset_mock()
            _ensure_market_making_orders_and_reschedule_mock.reset_mock()
            schedule_bot_stop_mock.reset_mock()
            assert producer.healthy is False
            assert producer.should_stop is False

            # config with invalid reference price formula
            producer.healthy = True
            producer.should_stop = False
            pair_config = producer.trading_mode.trading_config[
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
            ][0]
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE][0][simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = "invalid_formula"
            with mock.patch.object(
                advanced_reference_price_import.AdvancedPriceSource, "initialize_if_required", mock.AsyncMock(side_effect=commons_errors.DSLInterpreterError("Invalid formula"))
            ) as raising_advanced_reference_price_initialize_mock:
                await producer.start()
                raising_advanced_reference_price_initialize_mock.assert_awaited_once() # called once for the reference price
            mm_start_mock.assert_not_called()
            producer_start_mock.assert_called_once()
            # no scheduled or stop watcher config
            scheduled_volume_start_mock.assert_not_called()
            _ensure_market_making_orders_and_reschedule_mock.assert_not_called()
            assert producer.should_stop is False
            schedule_bot_stop_mock.assert_awaited_once()
            assert schedule_bot_stop_mock.mock_calls[0].args == (
                commons_enums.StopReason.INVALID_CONFIG,
                "Error when initializing reference prices: Invalid formula"
            )
            assert producer._scheduled_volume is None
            mm_start_mock.reset_mock()
            producer_start_mock.reset_mock()
            scheduled_volume_start_mock.reset_mock()
            _ensure_market_making_orders_and_reschedule_mock.reset_mock()
            schedule_bot_stop_mock.reset_mock()
            assert producer.healthy is False
            assert producer.should_stop is False
            producer.should_stop = False

            # with valid config
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE][0][simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = "close[-1]"
            producer.healthy = True
            await producer.start()
            mm_start_mock.assert_not_called()
            producer_start_mock.assert_called_once()
            # no scheduled or stop watcher config
            scheduled_volume_start_mock.assert_not_called()
             # exited func before these calls
            advanced_reference_price_initialize_mock.assert_awaited_once()
            _ensure_market_making_orders_and_reschedule_mock.assert_called_once()
            schedule_bot_stop_mock.assert_not_called()
            assert producer._scheduled_volume is None
            mm_start_mock.reset_mock()
            producer_start_mock.reset_mock()
            scheduled_volume_start_mock.reset_mock()
            advanced_reference_price_initialize_mock.reset_mock()
            _ensure_market_making_orders_and_reschedule_mock.reset_mock()
            schedule_bot_stop_mock.reset_mock()
            assert producer.healthy is True
            assert producer.should_stop is False

            producer.healthy = True
            # disabled config
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.SCHEDULED_VOLUME] = {
                simple_market_making_trading.SimpleMarketMakingTradingMode.MIN_INTERVAL_SECONDS: 1,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_INTERVAL_SECONDS: 2,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MIN_AMOUNT: 1,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_AMOUNT: 0,   # 0 == disabled
            }
            # disabled stop watcher
            # add a second reference price on the same exchange and a 3rd on a different exchange
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE].append({
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.TIME_FRAME: commons_enums.TimeFrames.ONE_HOUR.value,
                simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: "2",
                simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA: "50000",
            })
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE].append({
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "kucoin",
                simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.TIME_FRAME: commons_enums.TimeFrames.ONE_HOUR.value,
                simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: "3",
                simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA: "50000",
            })
            producer.read_config()
            await producer.start()
            mm_start_mock.assert_not_called()
            producer_start_mock.assert_called_once()
            # no scheduled volume config
            scheduled_volume_start_mock.assert_not_called()
            # no stop watcher config
            assert advanced_reference_price_initialize_mock.call_count == 3 # called once for each reference price
            _ensure_market_making_orders_and_reschedule_mock.assert_called_once()
            assert producer._scheduled_volume is None
            mm_start_mock.reset_mock()
            producer_start_mock.reset_mock()
            scheduled_volume_start_mock.reset_mock()
            advanced_reference_price_initialize_mock.reset_mock()
            _ensure_market_making_orders_and_reschedule_mock.reset_mock()
            assert producer.healthy is True
            assert producer.should_stop is False

            producer.healthy = True
            # enabled config
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.SCHEDULED_VOLUME] = {
                simple_market_making_trading.SimpleMarketMakingTradingMode.MIN_INTERVAL_SECONDS: 1,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_INTERVAL_SECONDS: 2,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MIN_AMOUNT: 3,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_AMOUNT: 4,
            }
            await producer.start()
            mm_start_mock.assert_not_called()
            producer_start_mock.assert_called_once()
            scheduled_volume_start_mock.assert_called_once()
            _ensure_market_making_orders_and_reschedule_mock.assert_called_once()
            assert isinstance(producer._scheduled_volume, scheduled_volume.ScheduledVolume)
            assert producer._scheduled_volume.min_interval == 1
            assert producer._scheduled_volume.max_interval == 2
            assert producer._scheduled_volume.min_quote_amount == 3
            assert producer._scheduled_volume.max_quote_amount == 4
            assert producer._scheduled_volume.symbol == symbol
            assert producer._scheduled_volume.exchange_manager is exchange_manager
            mm_start_mock.reset_mock()
            producer_start_mock.reset_mock()
            scheduled_volume_start_mock.reset_mock()
            _ensure_market_making_orders_and_reschedule_mock.reset_mock()
            assert producer.healthy is True
            assert producer.should_stop is False

            producer.healthy = True
            # missing required config elements - should skip hedging engine initialization
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: None,  # missing
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
            }
            producer.read_config()
            await producer.start()
            mm_start_mock.assert_not_called()
            producer_start_mock.assert_called_once()
            assert advanced_reference_price_initialize_mock.call_count > 0
            _ensure_market_making_orders_and_reschedule_mock.assert_called_once()
            assert producer._hedging_engine is None
            assert producer.outdated_reference_price_delta_ratio == trading_constants.ZERO
            mm_start_mock.reset_mock()
            producer_start_mock.reset_mock()
            advanced_reference_price_initialize_mock.reset_mock()
            _ensure_market_making_orders_and_reschedule_mock.reset_mock()
            assert producer.healthy is True
            assert producer.should_stop is False

            producer.healthy = True
            # hedging exchange missing or empty — should skip hedging, remain healthy
            for include_hedging_exchange_key, hedging_exchange_value in (
                (False, None),
                (True, ""),
            ):
                hedging_engine_dict = {
                    simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
                    simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
                    simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
                    simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
                    simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
                    simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
                }
                if include_hedging_exchange_key:
                    hedging_engine_dict[
                        simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE
                    ] = hedging_exchange_value
                pair_config[
                    simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE
                ] = hedging_engine_dict
                producer.read_config()
                await producer.start()
                mm_start_mock.assert_not_called()
                producer_start_mock.assert_called_once()
                assert advanced_reference_price_initialize_mock.call_count > 0
                _ensure_market_making_orders_and_reschedule_mock.assert_called_once()
                schedule_bot_stop_mock.assert_not_called()
                assert producer._hedging_engine is None
                assert producer.outdated_reference_price_delta_ratio == trading_constants.ZERO
                assert producer.healthy is True
                assert producer.should_stop is False
                mm_start_mock.reset_mock()
                producer_start_mock.reset_mock()
                advanced_reference_price_initialize_mock.reset_mock()
                _ensure_market_making_orders_and_reschedule_mock.reset_mock()

            producer.healthy = True
            # valid hedging engine config - should initialize successfully
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
            }

            producer.read_config()
            mock_hedging_engine = mock.Mock()
            mock_hedging_engine.register_symbol = mock.Mock()
            with mock.patch.object(
                hedging, "get_or_create_hedging_engine", mock.Mock(return_value=mock_hedging_engine)
            ) as get_or_create_hedging_engine_mock:
                await producer.start()
                mm_start_mock.assert_not_called()
                producer_start_mock.assert_called_once()
                assert advanced_reference_price_initialize_mock.call_count > 0
                _ensure_market_making_orders_and_reschedule_mock.assert_called_once()
                get_or_create_hedging_engine_mock.assert_called_once_with(
                    hedging.HedgingEngineTypes.SPOT,
                    exchange_manager,
                    "binance"
                )
                assert producer._hedging_engine is mock_hedging_engine
                mock_hedging_engine.register_symbol.assert_called_once_with(
                    symbol,
                    decimal.Decimal("1.0"),
                    decimal.Decimal("0.5"),
                    producer.order_book_distribution,
                    5.0,
                    5.0,
                    60,
                )
                assert producer.outdated_reference_price_delta_ratio == decimal.Decimal("0.01")  # 1.0 / 100
                mm_start_mock.reset_mock()
                producer_start_mock.reset_mock()
                advanced_reference_price_initialize_mock.reset_mock()
                _ensure_market_making_orders_and_reschedule_mock.reset_mock()
                assert producer.healthy is True
                assert producer.should_stop is False

            producer.healthy = True
            # hedging exchange not in reference price exchanges - should still initialize
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "nonexistent_exchange",  # not in reference prices
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
            }
            producer.read_config()
            with mock.patch.object(
                hedging, "get_or_create_hedging_engine", mock.Mock(return_value=mock_hedging_engine)
            ) as get_or_create_hedging_engine_mock:
                await producer.start()
            mm_start_mock.assert_not_called()
            producer_start_mock.assert_called_once()
            assert advanced_reference_price_initialize_mock.call_count > 0
            _ensure_market_making_orders_and_reschedule_mock.assert_called_once()
            schedule_bot_stop_mock.assert_not_called()
            assert producer._hedging_engine is mock_hedging_engine
            assert producer.healthy is True
            mm_start_mock.reset_mock()
            producer_start_mock.reset_mock()
            advanced_reference_price_initialize_mock.reset_mock()
            _ensure_market_making_orders_and_reschedule_mock.reset_mock()
            schedule_bot_stop_mock.reset_mock()
            producer.should_stop = False


async def test_initialize_hedging_engine():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        producer.read_config()
        
        # Test 1: No hedging config - should not initialize
        pair_config = producer.trading_mode.trading_config[
            simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
        ][0]
        pair_config.pop(simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE, None)
        producer.read_config()
        
        await producer._initialize_hedging_engine()
        assert producer._hedging_engine is None
        assert producer.outdated_reference_price_delta_ratio == trading_constants.ZERO
        
        # Test 1b: Hedging exchange key missing — should not initialize
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
        }
        producer.read_config()
        await producer._initialize_hedging_engine()
        assert producer._hedging_engine is None
        assert producer.outdated_reference_price_delta_ratio == trading_constants.ZERO

        # Test 1c: Hedging exchange empty — should not initialize
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE][
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE
        ] = ""
        producer.read_config()
        await producer._initialize_hedging_engine()
        assert producer._hedging_engine is None
        assert producer.outdated_reference_price_delta_ratio == trading_constants.ZERO
        
        # Test 2: average_price_counted_minutes 0 is invalid — should return early
        for element in [
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES,
        ]:
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
            }
            pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE][element] = 0
            producer.read_config()
            
            await producer._initialize_hedging_engine()
            assert producer._hedging_engine is None
            assert producer.outdated_reference_price_delta_ratio == trading_constants.ZERO

        # Test 3: Hedging exchange not in reference price exchanges - should still initialize
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "nonexistent_exchange",
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
        }
        producer.read_config()
        await producer._initialize_hedging_engine()
        assert producer._hedging_engine is not None
        assert producer._hedging_engine.hedging_exchange_name == "nonexistent_exchange"
        assert producer.outdated_reference_price_delta_ratio == decimal.Decimal("0.01")
        producer.outdated_reference_price_delta_ratio = trading_constants.ZERO
        
        # Test 3b: Hedging profit threshold 0 is allowed — engine inits, outdated_reference_price_delta_ratio stays 0
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
        }
        producer.read_config()
        with _real_spot_hedging_engine_init_session() as get_or_create_hedging_engine_mock:
            await producer._initialize_hedging_engine()
            get_or_create_hedging_engine_mock.assert_called_once_with(
                hedging.HedgingEngineTypes.SPOT,
                exchange_manager,
                "binance",
            )
        assert isinstance(producer._hedging_engine, spot_hedging_engine_import.SpotHedgingEngine)
        details = producer._hedging_engine.get_symbol_details(symbol)
        assert details.hedging_profit_threshold == trading_constants.ZERO
        assert details.hedging_max_loss_threshold == decimal.Decimal("0.5")
        assert details.order_book_distribution is producer.order_book_distribution
        assert details.volatility_threshold_checker.max_allowed_positive_percentage_change == decimal.Decimal("5")
        assert details.volatility_threshold_checker.max_allowed_negative_percentage_change == decimal.Decimal("5")
        assert details.volatility_threshold_checker.period_in_minutes == 60
        assert producer.outdated_reference_price_delta_ratio == trading_constants.ZERO
        
        # Test 3c: Hedging max loss threshold 0 is allowed — engine inits (limit-only hedging on spot)
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
        }
        producer.read_config()
        with _real_spot_hedging_engine_init_session() as get_or_create_hedging_engine_mock:
            await producer._initialize_hedging_engine()
            get_or_create_hedging_engine_mock.assert_called_once_with(
                hedging.HedgingEngineTypes.SPOT,
                exchange_manager,
                "binance",
            )
        assert isinstance(producer._hedging_engine, spot_hedging_engine_import.SpotHedgingEngine)
        details = producer._hedging_engine.get_symbol_details(symbol)
        assert details.hedging_profit_threshold == decimal.Decimal("1")
        assert details.hedging_max_loss_threshold == trading_constants.ZERO
        assert details.order_book_distribution is producer.order_book_distribution
        assert details.volatility_threshold_checker.max_allowed_positive_percentage_change == decimal.Decimal("5")
        assert details.volatility_threshold_checker.max_allowed_negative_percentage_change == decimal.Decimal("5")
        assert details.volatility_threshold_checker.period_in_minutes == 60
        assert producer.outdated_reference_price_delta_ratio == decimal.Decimal("0.01")
        
        # Test 3d: Max positive / negative percent price change 0 allowed — engine inits
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
        }
        producer.read_config()
        with _real_spot_hedging_engine_init_session() as get_or_create_hedging_engine_mock:
            await producer._initialize_hedging_engine()
            get_or_create_hedging_engine_mock.assert_called_once_with(
                hedging.HedgingEngineTypes.SPOT,
                exchange_manager,
                "binance",
            )
        assert isinstance(producer._hedging_engine, spot_hedging_engine_import.SpotHedgingEngine)
        details = producer._hedging_engine.get_symbol_details(symbol)
        assert details.hedging_profit_threshold == decimal.Decimal("1")
        assert details.hedging_max_loss_threshold == decimal.Decimal("0.5")
        assert details.order_book_distribution is producer.order_book_distribution
        assert details.volatility_threshold_checker.max_allowed_positive_percentage_change == trading_constants.ZERO
        assert details.volatility_threshold_checker.max_allowed_negative_percentage_change == trading_constants.ZERO
        assert details.volatility_threshold_checker.period_in_minutes == 60
        assert producer.outdated_reference_price_delta_ratio == decimal.Decimal("0.01")
        
        # Test 4: Valid hedging engine config - should initialize successfully
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 2,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 1.5,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 10.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 8.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 120,
        }
        producer.read_config()
        with _real_spot_hedging_engine_init_session() as get_or_create_hedging_engine_mock:
            await producer._initialize_hedging_engine()
            get_or_create_hedging_engine_mock.assert_called_once_with(
                hedging.HedgingEngineTypes.SPOT,
                exchange_manager,
                "binance"
            )
        assert isinstance(producer._hedging_engine, spot_hedging_engine_import.SpotHedgingEngine)
        details = producer._hedging_engine.get_symbol_details(symbol)
        assert details.hedging_profit_threshold == decimal.Decimal("2")
        assert details.hedging_max_loss_threshold == decimal.Decimal("1.5")
        assert details.order_book_distribution is producer.order_book_distribution
        assert details.volatility_threshold_checker.max_allowed_positive_percentage_change == decimal.Decimal("10")
        assert details.volatility_threshold_checker.max_allowed_negative_percentage_change == decimal.Decimal("8")
        assert details.volatility_threshold_checker.period_in_minutes == 120
        assert producer.outdated_reference_price_delta_ratio == decimal.Decimal("0.02")  # 2 / 100
        
        # Test 5: PERPETUAL_FUTURES — hedging engine factory not implemented
        engine_before_futures_attempt = producer._hedging_engine
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.PERPETUAL_FUTURES.value,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: 1.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
        }
        producer.read_config()
        hedging._HEDGING_ENGINES_HEDGING_EXCHANGE_NAME_BY_TRADING_EXCHANGE_ID.clear()
        with mock.patch.object(
            hedging_engine_import.HedgingEngine,
            "_async_start_for_hedging_details",
            mock.AsyncMock(),
        ):
            with pytest.raises(NotImplementedError):
                await producer._initialize_hedging_engine()
        assert producer._hedging_engine is engine_before_futures_attempt
        
        # Test 6: Config with None values for required elements - should return early
        producer._hedging_engine = None
        pair_config[simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE] = {
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_ENGINE_TYPE: hedging.HedgingEngineTypes.SPOT.value,
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_EXCHANGE: "binance",
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_PROFIT_THRESHOLD: None,  # None value
            simple_market_making_trading.SimpleMarketMakingTradingMode.HEDGING_MAX_LOSS_THRESHOLD: 0.5,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_POSITIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: 5.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.AVERAGE_PRICE_COUNTED_MINUTES: 60,
        }
        producer.read_config()
        
        await producer._initialize_hedging_engine()
        assert producer._hedging_engine is None


async def test_ensure_market_making_orders():
    symbol = "BTC/USDT"
    with mock.patch.object(
        simple_market_making_trading.SimpleMarketMakingTradingModeProducer, "create_state", mock.AsyncMock()
    ) as create_state_mock, mock.patch.object(
        scheduled_volume.ScheduledVolume, "wait_required_locked_funds_init", mock.AsyncMock()
    ) as wait_required_locked_funds_init_mock, mock.patch.object(
        scheduled_volume.ScheduledVolume, "ensure_locked_funds", mock.Mock(return_value=None)
    ) as ensure_locked_funds_mock:
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            # no scheduled volume
            await producer._ensure_market_making_orders("plop")
            wait_required_locked_funds_init_mock.assert_not_called()
            ensure_locked_funds_mock.assert_not_called()
            create_state_mock.assert_called_once()
            wait_required_locked_funds_init_mock.reset_mock()
            ensure_locked_funds_mock.reset_mock()
            create_state_mock.reset_mock()

            # with scheduled volume
            producer._scheduled_volume = scheduled_volume.ScheduledVolume(
                exchange_manager, symbol, mock.AsyncMock(), 1, 2, 3, 4
            )
            await producer._ensure_market_making_orders("plop")
            wait_required_locked_funds_init_mock.assert_called_once()
            ensure_locked_funds_mock.assert_called_once()
            assert create_state_mock.mock_calls[0].args[3] is False
            create_state_mock.assert_called_once()
            wait_required_locked_funds_init_mock.reset_mock()
            ensure_locked_funds_mock.reset_mock()
            create_state_mock.reset_mock()
            with mock.patch.object(
                scheduled_volume.ScheduledVolume, "ensure_locked_funds", mock.Mock(return_value=scheduled_volume.LockFundsActions.REALLOCATE_SCHEDULED_VOLUME_FUNDS)
            ) as ensure_locked_funds_mock:
                producer._scheduled_volume = scheduled_volume.ScheduledVolume(
                    exchange_manager, symbol, mock.AsyncMock(), 1, 2, 3, 4
                )
                await producer._ensure_market_making_orders("plop")
                wait_required_locked_funds_init_mock.assert_called_once()
                ensure_locked_funds_mock.assert_called_once()
                assert create_state_mock.mock_calls[0].args[3] is True
                create_state_mock.assert_called_once()
                wait_required_locked_funds_init_mock.reset_mock()
                ensure_locked_funds_mock.reset_mock()
                create_state_mock.reset_mock()


async def test_emergency_cancel_all_market_making_orders():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        # Create some market making orders
        price = decimal.Decimal(1000)
        with mock.patch.object(
            producer, "_get_reference_price", mock.AsyncMock(return_value=price)
        ):
            trigger_source = "test"
            # Create orders
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            
            # Wait for orders to be created
            for _ in range(10):
                await asyncio_tools.wait_asyncio_next_cycle()
            
            # Verify orders were created
            open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
            assert len(open_orders) == 10
            initial_order_ids = [order.order_id for order in open_orders]
            
            # Test emergency cancel without errors
            with mock.patch.object(
                producer.trading_mode, "cancel_order", mock.AsyncMock()
            ) as cancel_order_mock:
                await producer._emergency_cancel_all_market_making_orders()
                # Should call cancel_order for each market making order
                assert cancel_order_mock.call_count == 10
                # Verify wait_for_cancelling=False is passed
                for call in cancel_order_mock.mock_calls:
                    assert call.kwargs.get("wait_for_cancelling") is False
            
            # Test emergency cancel with some errors
            cancel_error = Exception("Cancel failed")
            async def cancel_with_error(order, wait_for_cancelling=False):
                if order.order_id == initial_order_ids[0]:
                    raise cancel_error
                    
            with mock.patch.object(
                producer.trading_mode, "cancel_order", mock.AsyncMock(side_effect=cancel_with_error)
            ) as cancel_order_mock:
                # Should not raise even if some cancellations fail
                await producer._emergency_cancel_all_market_making_orders()
                assert cancel_order_mock.call_count == 10


class TestOnNewReferencePrice:
    """Tests for SimpleMarketMakingTradingModeProducer.on_new_reference_price."""

    @classmethod
    def _order_book_distribution(cls):
        return advanced_order_book_distribution.AdvancedOrderBookDistribution(
            bids_count=10,
            asks_count=10,
            min_spread=decimal.Decimal("4"),
            max_spread=decimal.Decimal("40"),
            target_cumulated_volume_percent=decimal.Decimal("2"),
            daily_trading_volume_percent=decimal.Decimal("1"),
            price_distribution=advanced_order_book_distribution.OrdersDistribution.LINEAR,
            funds_distribution=advanced_order_book_distribution.FundsDistribution.VALLEY,
            max_base_budget=decimal.Decimal("1"),
            max_quote_budget=decimal.Decimal("100"),
            min_base_budget=decimal.Decimal("0.01"),
            min_quote_budget=decimal.Decimal("1"),
        )

    @classmethod
    def _create_registered_spot_hedging_engine(cls, exchange_manager, symbol: str):
        """
        Real SpotHedgingEngine on the same exchange as the producer; register_symbol matches spot tests.
        Patch reached_max_tolerated_volatility / on_new_price on the returned instance in each test.
        """
        engine = spot_hedging_engine_import.SpotHedgingEngine(
            trading_exchange_manager=exchange_manager,
            hedging_exchange_name=exchange_manager.exchange_name,
        )
        engine._hedging_exchange_manager = exchange_manager
        with mock.patch.object(engine, "_async_start_for_hedging_details", mock.AsyncMock()):
            engine.register_symbol(
                symbol=symbol,
                hedging_profit_threshold=decimal.Decimal("0.01"),
                hedging_max_loss_threshold=decimal.Decimal("0.01"),
                order_book_distribution=cls._order_book_distribution(),
                max_positive_percent_price_change=40,
                max_negative_percent_price_change=12,
                average_price_counted_minutes=10,
            )
        return engine

    @staticmethod
    def _buy_sell_limit_orders(
        trader,
        symbol: str,
        buy_price: decimal.Decimal,
        sell_price: decimal.Decimal,
    ) -> list:
        qty = decimal.Decimal("0.01")
        buy_order = trading_personal_data.create_order_instance(
            trader=trader,
            order_type=trading_enums.TraderOrderType.BUY_LIMIT,
            symbol=symbol,
            current_price=buy_price,
            quantity=qty,
            price=buy_price,
        )
        sell_order = trading_personal_data.create_order_instance(
            trader=trader,
            order_type=trading_enums.TraderOrderType.SELL_LIMIT,
            symbol=symbol,
            current_price=sell_price,
            quantity=qty,
            price=sell_price,
        )
        return [buy_order, sell_order]

    async def test_without_hedging_no_refresh_when_spread_ok(self):
        symbol = "BTC/USDT"
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            assert producer._hedging_engine is None
            ref = decimal.Decimal("1000")
            orders = self._buy_sell_limit_orders(
                exchange_manager.trader,
                symbol,
                decimal.Decimal("900"),
                decimal.Decimal("1100"),
            )
            with mock.patch.object(
                producer,
                "get_market_making_orders",
                mock.Mock(return_value=orders),
            ):
                assert await producer.on_new_reference_price(ref) is False

    async def test_without_hedging_triggers_when_buy_above_reference(self):
        symbol = "BTC/USDT"
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            assert producer._hedging_engine is None
            ref = decimal.Decimal("800")
            orders = self._buy_sell_limit_orders(
                exchange_manager.trader,
                symbol,
                decimal.Decimal("950"),
                decimal.Decimal("1100"),
            )
            with mock.patch.object(
                producer,
                "get_market_making_orders",
                mock.Mock(return_value=orders),
            ):
                assert await producer.on_new_reference_price(ref) is True

    async def test_without_hedging_triggers_when_sell_below_reference(self):
        symbol = "BTC/USDT"
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            assert producer._hedging_engine is None
            ref = decimal.Decimal("1200")
            orders = self._buy_sell_limit_orders(
                exchange_manager.trader,
                symbol,
                decimal.Decimal("900"),
                decimal.Decimal("1150"),
            )
            with mock.patch.object(
                producer,
                "get_market_making_orders",
                mock.Mock(return_value=orders),
            ):
                assert await producer.on_new_reference_price(ref) is True

    async def test_with_hedging_updates_engine_then_super(self):
        symbol = "BTC/USDT"
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            ref = decimal.Decimal("50100")
            hedging_engine = self._create_registered_spot_hedging_engine(exchange_manager, symbol)
            producer._hedging_engine = hedging_engine
            reached_mock = mock.Mock(return_value=False)
            on_new_mock = mock.AsyncMock()
            with mock.patch.object(hedging_engine, "reached_max_tolerated_volatility", reached_mock), mock.patch.object(
                hedging_engine, "on_new_price", on_new_mock
            ), mock.patch.object(
                producer,
                "_emergency_cancel_all_market_making_orders",
                mock.AsyncMock(),
            ) as emergency_mock, mock.patch.object(
                market_making_trading_mode.MarketMakingTradingModeProducer,
                "on_new_reference_price",
                mock.AsyncMock(return_value=True),
            ) as super_on_new:
                assert await producer.on_new_reference_price(ref) is True
            emergency_mock.assert_not_called()
            reached_mock.assert_called_once_with(symbol)
            on_new_mock.assert_awaited_once_with(symbol, ref)
            super_on_new.assert_awaited_once_with(ref)

    async def test_with_hedging_already_at_max_volatility_cancels_and_skips_super(self):
        symbol = "BTC/USDT"
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            ref = decimal.Decimal("50100")
            hedging_engine = self._create_registered_spot_hedging_engine(exchange_manager, symbol)
            producer._hedging_engine = hedging_engine
            reached_mock = mock.Mock(return_value=True)
            on_new_mock = mock.AsyncMock()
            with mock.patch.object(hedging_engine, "reached_max_tolerated_volatility", reached_mock), mock.patch.object(
                hedging_engine, "on_new_price", on_new_mock
            ), mock.patch.object(
                producer,
                "_emergency_cancel_all_market_making_orders",
                mock.AsyncMock(),
            ) as emergency_mock, mock.patch.object(
                market_making_trading_mode.MarketMakingTradingModeProducer,
                "on_new_reference_price",
                mock.AsyncMock(),
            ) as super_on_new:
                assert await producer.on_new_reference_price(ref) is False
            emergency_mock.assert_awaited_once()
            on_new_mock.assert_not_called()
            super_on_new.assert_not_called()

    async def test_with_hedging_max_vol_exception_cancels_and_skips_super(self):
        symbol = "BTC/USDT"
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            ref = decimal.Decimal("50100")
            hedging_engine = self._create_registered_spot_hedging_engine(exchange_manager, symbol)
            producer._hedging_engine = hedging_engine
            reached_mock = mock.Mock(return_value=False)
            on_new_mock = mock.AsyncMock(
                side_effect=hedging_errors.HedgingEngineReachedMaxToleratedVolatility("cap")
            )
            with mock.patch.object(hedging_engine, "reached_max_tolerated_volatility", reached_mock), mock.patch.object(
                hedging_engine, "on_new_price", on_new_mock
            ), mock.patch.object(
                producer,
                "_emergency_cancel_all_market_making_orders",
                mock.AsyncMock(),
            ) as emergency_mock, mock.patch.object(
                market_making_trading_mode.MarketMakingTradingModeProducer,
                "on_new_reference_price",
                mock.AsyncMock(),
            ) as super_on_new:
                assert await producer.on_new_reference_price(ref) is False
            emergency_mock.assert_awaited_once()
            on_new_mock.assert_awaited_once()
            super_on_new.assert_not_called()

    async def test_with_hedging_engine_error_returns_false(self):
        symbol = "BTC/USDT"
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            ref = decimal.Decimal("50100")
            hedging_engine = self._create_registered_spot_hedging_engine(exchange_manager, symbol)
            producer._hedging_engine = hedging_engine
            reached_mock = mock.Mock(return_value=False)
            on_new_mock = mock.AsyncMock(side_effect=RuntimeError("hedge feed"))
            with mock.patch.object(hedging_engine, "reached_max_tolerated_volatility", reached_mock), mock.patch.object(
                hedging_engine, "on_new_price", on_new_mock
            ), mock.patch.object(
                producer,
                "_emergency_cancel_all_market_making_orders",
                mock.AsyncMock(),
            ) as emergency_mock, mock.patch.object(
                market_making_trading_mode.MarketMakingTradingModeProducer,
                "on_new_reference_price",
                mock.AsyncMock(),
            ) as super_on_new:
                assert await producer.on_new_reference_price(ref) is False
            emergency_mock.assert_not_called()
            on_new_mock.assert_awaited_once()
            super_on_new.assert_not_called()


async def test_force_stop_strategy():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        reason_description = "Holding threshold exceeded"
        
        # Test 1: Simple force stop without ongoing execution
        with mock.patch.object(
            producer, "_emergency_cancel_all_market_making_orders", mock.AsyncMock()
        ) as emergency_cancel_mock:
            producer._scheduled_volume = None
            producer.latest_actions_plan = None
            
            assert producer.should_stop is False
            await producer.force_stop_strategy(reason_description)
            assert producer.should_stop is True
            
            # Should call emergency cancel once
            assert emergency_cancel_mock.call_count == 1

            producer.should_stop = False
        
        # Test 2: Force stop with scheduled volume
        with mock.patch.object(
            producer, "_emergency_cancel_all_market_making_orders", mock.AsyncMock()
        ) as emergency_cancel_mock:
            scheduled_vol = mock.Mock(spec=scheduled_volume.ScheduledVolume)
            scheduled_vol.stop = mock.Mock()
            producer._scheduled_volume = scheduled_vol
            producer.latest_actions_plan = None
            
            await producer.force_stop_strategy(reason_description)
            assert producer.should_stop is True
            # Should stop scheduled volume
            scheduled_vol.stop.assert_called_once()
            # Should call emergency cancel once (no ongoing execution)
            assert emergency_cancel_mock.call_count == 1

            producer.should_stop = False
        # Test 3: Force stop with ongoing execution
        with mock.patch.object(
            producer, "_emergency_cancel_all_market_making_orders", mock.AsyncMock()
        ) as emergency_cancel_mock:
            # Create a fake ongoing execution
            fake_plan = market_making_trading_mode.OrdersUpdatePlan()
            fake_plan.force_cancelled = False
            producer.latest_actions_plan = fake_plan
            producer._scheduled_volume = None
            
            # Simulate the plan being processed after a short delay
            async def set_processed_after_delay():
                await asyncio_tools.wait_asyncio_next_cycle()
                fake_plan.processed.set()
            
            # Start the task to set processed
            asyncio.create_task(set_processed_after_delay())
            
            await producer.force_stop_strategy(reason_description)
            assert producer.should_stop is True
            # Should set force_cancelled to True
            assert fake_plan.force_cancelled is True
            # Should call emergency cancel twice (once before wait, once after)
            assert emergency_cancel_mock.call_count == 2

            producer.should_stop = False
        # Test 4: Force stop with already processed execution
        with mock.patch.object(
            producer, "_emergency_cancel_all_market_making_orders", mock.AsyncMock()
        ) as emergency_cancel_mock:
            fake_plan = market_making_trading_mode.OrdersUpdatePlan()
            fake_plan.processed.set()  # Already processed
            fake_plan.force_cancelled = False
            producer.latest_actions_plan = fake_plan
            producer._scheduled_volume = None
            
            await producer.force_stop_strategy(reason_description)
            assert producer.should_stop is True
            # Don't set force_cancelled to True if the plan is already processed
            assert fake_plan.force_cancelled is False
            # Should only call emergency cancel once (plan already processed)
            assert emergency_cancel_mock.call_count == 1

            producer.should_stop = False


async def test_force_stop_strategy_integration():
    """Integration test for force_stop_strategy with real orders"""
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        # Create real orders first
        price = decimal.Decimal(1000)
        with mock.patch.object(
            producer, "_get_reference_price", mock.AsyncMock(return_value=price)
        ):
            trigger_source = "test"
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            
            # Wait for orders to be created
            for _ in range(10):
                await asyncio_tools.wait_asyncio_next_cycle()
            
            # Verify orders were created
            open_orders_before = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
            assert len(open_orders_before) == 10
        
        # Now force stop
        await producer.force_stop_strategy("Holding threshold exceeded")
        
        # Wait for cancellations to process
        for _ in range(10):
            await asyncio_tools.wait_asyncio_next_cycle()
        
        # Verify all orders were cancelled
        open_orders_after = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
        # Orders should be cancelled (may still be in the list but with cancelled status)
        for order in open_orders_after:
            assert order.is_cancelled() or order.is_closed()


async def test_get_reference_price():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        # Ensure producer is initialized and config is loaded
        producer.read_config()
        
        # Set up reference prices configuration
        # Default config has one reference price source for binance exchange
        assert producer.reference_prices_by_exchange is not None
        assert "binance" in producer.reference_prices_by_exchange
        
        # Initialize reference prices
        await producer._validate_reference_prices()
        
        # Set mark price for the symbol
        test_price = decimal.Decimal("1000")
        trading_api.force_set_mark_price(exchange_manager, symbol, float(test_price))
        
        # Wait for price to be available
        await asyncio_tools.wait_asyncio_next_cycle()

        # no available exchange
        with mock.patch.object(
            trading_api, "get_all_exchange_ids_with_same_matrix_id", mock.Mock(return_value=[])
        ) as get_all_exchange_ids_with_same_matrix_id_mock:
            assert await producer._get_reference_price() == trading_constants.ZERO
            get_all_exchange_ids_with_same_matrix_id_mock.assert_called_once_with(exchange_manager.exchange_name, exchange_manager.id)
        
        # with available exchanges
        with mock.patch.object(
            trading_api, "get_all_exchange_ids_with_same_matrix_id", mock.Mock(return_value=["binance-1", "binance-2"])
        ) as get_all_exchange_ids_with_same_matrix_id_mock, \
        mock.patch.object(
            trading_api, "get_exchange_manager_from_exchange_id", mock.Mock(return_value=exchange_manager)
        ) as get_exchange_manager_from_exchange_id_mock:
            await _initialize_reference_prices(producer)
            # Get reference price
            reference_price = await producer._get_reference_price()
            assert get_all_exchange_ids_with_same_matrix_id_mock.call_count == 2
            assert all(
                call.args == (exchange_manager.exchange_name, exchange_manager.id)
                for call in get_all_exchange_ids_with_same_matrix_id_mock.mock_calls
            )
            assert get_exchange_manager_from_exchange_id_mock.call_count == 4
            
            # Should return the mark price since there's only one source with weight 1
            assert reference_price == test_price
            
            # Test with multiple reference price sources with different weights
            producer.reference_prices_by_exchange["binance"] = [
                advanced_reference_price_import.AdvancedPriceSource(
                    exchange="binance",
                    pair=symbol,
                    time_frame=None,
                    weight=decimal.Decimal("2"),
                    formula=""
                ),
                advanced_reference_price_import.AdvancedPriceSource(
                    exchange="binance",
                    pair=symbol,
                    time_frame=None,
                    weight=decimal.Decimal("2"),
                    formula="1000"
                )
            ]
            
            # Set a different price
            test_price_2 = decimal.Decimal("2000")
            trading_api.force_set_mark_price(exchange_manager, symbol, float(test_price_2))
            await asyncio_tools.wait_asyncio_next_cycle()
            
            await _initialize_reference_prices(producer)
            # Get reference price - should still be the same since both sources use the same price
            reference_price_2 = await producer._get_reference_price()
            assert reference_price_2 == decimal.Decimal("1500") # (1000 * 2 + 2000 * 1) / (2 + 1) = 1500
            
            # Test with formula-based reference price
            producer.reference_prices_by_exchange["binance"] = [
                advanced_reference_price_import.AdvancedPriceSource(
                    exchange="binance",
                    pair=symbol,
                    time_frame=None,
                    weight=decimal.Decimal("1"),
                    formula="1000 + 500"  # Formula that returns 1500
                )
            ]
            await producer._validate_reference_prices()
            
            # Set mark price
            base_price = decimal.Decimal("1000")
            trading_api.force_set_mark_price(exchange_manager, symbol, float(base_price))
            await asyncio_tools.wait_asyncio_next_cycle()
            
            # Get reference price - formula should evaluate to 1500
            await _initialize_reference_prices(producer)
            reference_price_3 = await producer._get_reference_price()
            assert reference_price_3 == decimal.Decimal("1500")
            
            # Test with empty reference prices (should return ZERO)
            producer.reference_prices_by_exchange = {}
            reference_price_empty = await producer._get_reference_price()
            assert reference_price_empty == trading_constants.ZERO
            
            # Test with reference prices but no price data available
            producer.reference_prices_by_exchange = {
                "nonexistent_exchange": [
                    advanced_reference_price_import.AdvancedPriceSource(
                        exchange="nonexistent_exchange",
                        pair=symbol,
                        time_frame=None,
                        weight=decimal.Decimal("1"),
                        formula=""
                    )
                ]
            }
            await producer._validate_reference_prices()
            reference_price_no_data = await producer._get_reference_price()
            assert reference_price_no_data == trading_constants.ZERO


async def test_register_pair_requirement_on_reference_exchange():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        exchange_id = exchange_manager.id
        
        # Test 1: Basic watched symbol (MARK_PRICE_CHANNEL dependency)
        # Reference price with no formula (MARK_PRICE_CHANNEL dependency)
        mock_ref_price_1 = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_1.pair = "ETH/USDT"
        mock_ref_price_1.initialize_if_required = mock.AsyncMock()
        mock_ref_price_1.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="ETH/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            )
        ])
        
        producer._hedging_engine = None
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ) as register_mock:
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, [mock_ref_price_1]
            )
            
            # Should initialize reference price
            mock_ref_price_1.initialize_if_required.assert_awaited_once_with(exchange_manager)
            # Should register as watched symbol only
            assert register_mock.call_count == 1
            register_mock.assert_any_call(
                exchange_manager,
                ["ETH/USDT"],
                watch_only=True
            )
        
        # Test 2: Traded symbol with time frame (OHLCV_CHANNEL dependency)
        # Reference price with formula using OHLCV data
        mock_ref_price_2 = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_2.pair = "BTC/USDT"
        mock_ref_price_2.initialize_if_required = mock.AsyncMock()
        mock_ref_price_2.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="BTC/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            ),
            exchange_operators.ExchangeDataDependency(
                symbol="BTC/USDT",
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                data_source=trading_constants.OHLCV_CHANNEL
            )
        ])
        
        producer._hedging_engine = None
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ) as register_mock:
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, [mock_ref_price_2]
            )
            
            # Should initialize reference price
            mock_ref_price_2.initialize_if_required.assert_awaited_once_with(exchange_manager)
            # Should register as traded symbol with time frames
            assert register_mock.call_count == 2  # One for watched (MARK_PRICE), one for traded (OHLCV)
            assert register_mock.mock_calls[0].args[1] == ["BTC/USDT"]
            assert register_mock.mock_calls[0].kwargs["time_frames"] == [commons_enums.TimeFrames.ONE_HOUR]
            # watched only = False is called first
            assert register_mock.mock_calls[0].kwargs["watch_only"] is False
            assert register_mock.mock_calls[1].args[1] == ["BTC/USDT"]
            assert register_mock.mock_calls[1].kwargs["watch_only"] is True
        
        # Test 3: Multiple reference prices with mixed dependencies
        mock_ref_price_3a = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_3a.pair = "ETH/USDT"
        mock_ref_price_3a.initialize_if_required = mock.AsyncMock()
        mock_ref_price_3a.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="ETH/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            )
        ])
        
        mock_ref_price_3b = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_3b.pair = "BNB/USDT"
        mock_ref_price_3b.initialize_if_required = mock.AsyncMock()
        mock_ref_price_3b.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="BNB/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            ),
            exchange_operators.ExchangeDataDependency(
                symbol="BNB/USDT",
                time_frame=commons_enums.TimeFrames.FOUR_HOURS.value,
                data_source=trading_constants.OHLCV_CHANNEL
            )
        ])
        
        producer._hedging_engine = None
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ) as register_mock:
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, [mock_ref_price_3a, mock_ref_price_3b]
            )
            
            # Should initialize both reference prices
            mock_ref_price_3a.initialize_if_required.assert_awaited_once_with(exchange_manager)
            mock_ref_price_3b.initialize_if_required.assert_awaited_once_with(exchange_manager)
            
            # Should register watched symbols (ETH/USDT, BNB/USDT)
            # Should register traded symbols (BNB/USDT) with time frames
            watched_calls = [call for call in register_mock.call_args_list if call.kwargs.get("watch_only") is True]
            traded_calls = [call for call in register_mock.call_args_list if call.kwargs.get("watch_only") is False]
            
            assert len(watched_calls) == 1
            assert len(traded_calls) == 1
            
            # Check watched symbols
            assert sorted(watched_calls[0].args[1]) == ["BNB/USDT", "ETH/USDT"]
            
            # Check traded symbols
            assert traded_calls[0].args[1] == ["BNB/USDT"]
            assert commons_enums.TimeFrames.FOUR_HOURS in traded_calls[0].kwargs.get("time_frames", [])
        
        # Test 4: Hedging engine on same exchange
        mock_ref_price_4 = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_4.pair = "ETH/USDT"
        mock_ref_price_4.initialize_if_required = mock.AsyncMock()
        mock_ref_price_4.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="ETH/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            )
        ])
        
        mock_hedging_engine = mock.Mock()
        mock_hedging_engine.hedging_exchange_name = exchange_manager.exchange_name
        producer._hedging_engine = mock_hedging_engine
        producer.symbol = symbol
        
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ) as register_mock:
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, [mock_ref_price_4]
            )
            
            # Should register watched symbols
            # Should register traded symbols including the trading symbol from hedging engine
            traded_calls = [call for call in register_mock.call_args_list if call.kwargs.get("watch_only") is False]
            
            assert len(traded_calls) == 1
            traded_symbols = set(traded_calls[0].args[1])
            assert symbol in traded_symbols  # Trading symbol should be added due to hedging engine
        
        # Test 5: Hedging engine on different exchange
        mock_ref_price_5 = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_5.pair = "ETH/USDT"
        mock_ref_price_5.initialize_if_required = mock.AsyncMock()
        mock_ref_price_5.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="ETH/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            )
        ])
        
        mock_hedging_engine_different = mock.Mock()
        mock_hedging_engine_different.hedging_exchange_name = "kucoin"  # Different exchange, should not register traded symbols
        producer._hedging_engine = mock_hedging_engine_different
        producer.symbol = symbol
        
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ) as register_mock:
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, [mock_ref_price_5]
            )
            
            # Should only register watched symbols (no traded symbols from hedging engine)
            traded_calls = [call for call in register_mock.call_args_list if call.kwargs.get("watch_only") is False]
            
            # Should not have traded calls (or if there are, trading symbol should not be in them)
            if traded_calls:
                for call in traded_calls:
                    assert symbol not in call.args[1]  # Trading symbol should NOT be added
        
        # Test 6: Empty reference prices list
        producer._hedging_engine = None
        
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ) as register_mock:
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, []
            )
            
            # Should not register anything (no reference prices, no hedging engine)
            register_mock.assert_not_called()
        
        # Test 6b: Empty reference prices list with hedging engine on same exchange
        mock_hedging_engine_empty = mock.Mock()
        mock_hedging_engine_empty.hedging_exchange_name = exchange_manager.exchange_name
        producer._hedging_engine = mock_hedging_engine_empty
        producer.symbol = symbol
        
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ) as register_mock:
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, []
            )
            
            # Should register trading symbol due to hedging engine
            assert register_mock.call_count == 1
            register_mock.assert_called_once_with(
                exchange_manager,
                [symbol],
                watch_only=False,
                time_frames=[]
            )
        
        # Test 7: Verify reference price initialization calls
        mock_ref_price_7a = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_7a.pair = "ETH/USDT"
        mock_ref_price_7a.initialize_if_required = mock.AsyncMock()
        mock_ref_price_7a.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="ETH/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            )
        ])
        
        mock_ref_price_7b = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_7b.pair = "BNB/USDT"
        mock_ref_price_7b.initialize_if_required = mock.AsyncMock()
        mock_ref_price_7b.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="BNB/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            )
        ])
        
        producer._hedging_engine = None
        
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ):
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, [mock_ref_price_7a, mock_ref_price_7b]
            )
            
            # Should initialize both reference prices
            assert mock_ref_price_7a.initialize_if_required.call_count == 1
            assert mock_ref_price_7b.initialize_if_required.call_count == 1
            mock_ref_price_7a.initialize_if_required.assert_awaited_with(exchange_manager)
            mock_ref_price_7b.initialize_if_required.assert_awaited_with(exchange_manager)
            
            # Should get dependencies after initialization
            assert mock_ref_price_7a.get_dependencies.call_count == 1
            assert mock_ref_price_7b.get_dependencies.call_count == 1
        
        # Test 8: Multiple time frames for same symbol
        mock_ref_price_8 = mock.Mock(spec=advanced_reference_price_import.AdvancedPriceSource)
        mock_ref_price_8.pair = "BTC/USDT"
        mock_ref_price_8.initialize_if_required = mock.AsyncMock()
        mock_ref_price_8.get_dependencies = mock.Mock(return_value=[
            exchange_operators.ExchangeDataDependency(
                symbol="BTC/USDT",
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            ),
            exchange_operators.ExchangeDataDependency(
                symbol="BTC/USDT",
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                data_source=trading_constants.OHLCV_CHANNEL
            ),
            exchange_operators.ExchangeDataDependency(
                symbol="BTC/USDT",
                time_frame=commons_enums.TimeFrames.FOUR_HOURS.value,
                data_source=trading_constants.OHLCV_CHANNEL
            )
        ])
        
        producer._hedging_engine = None
        
        with mock.patch.object(
            trading_api, "register_new_pairs_on_exchange_manager", mock.AsyncMock()
        ) as register_mock:
            await producer._register_pair_requirement_on_reference_exchange(
                exchange_manager, [mock_ref_price_8]
            )
            
            # Should register with both time frames
            traded_calls = [call for call in register_mock.call_args_list if call.kwargs.get("watch_only") is False]
            assert len(traded_calls) == 1
            time_frames = traded_calls[0].kwargs.get("time_frames", [])
            assert commons_enums.TimeFrames.ONE_HOUR in time_frames
            assert commons_enums.TimeFrames.FOUR_HOURS in time_frames
            assert len(time_frames) == 2


async def test_ensure_dependencies():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        exchange_id = exchange_manager.id
        
        # Mock channel objects
        ohlcv_consumers = []
        mock_ohlcv_channel = mock.Mock(get_consumer_from_filters=mock.Mock(return_value=ohlcv_consumers))
        mock_ohlcv_channel.new_consumer = mock.AsyncMock(side_effect=lambda *args, **kwargs: ohlcv_consumers.append(mock.Mock(callback=kwargs["callback"])))
        mark_price_consumers = []
        mock_mark_price_channel = mock.Mock(get_consumer_from_filters=mock.Mock(return_value=mark_price_consumers))
        mock_mark_price_channel.new_consumer = mock.AsyncMock(side_effect=lambda *args, **kwargs: mark_price_consumers.append(mock.Mock(callback=kwargs["callback"])))
        
        # Test 1: OHLCV_CHANNEL dependency - should subscribe to OHLCV and mark price
        ohlcv_dependency = exchange_operators.ExchangeDataDependency(
            symbol=symbol,
            time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
            data_source=trading_constants.OHLCV_CHANNEL
        )
        
        with mock.patch.object(
            exchanges_channel, 'get_chan', side_effect=lambda channel_name, ex_id: 
                mock_ohlcv_channel if channel_name == trading_constants.OHLCV_CHANNEL 
                else mock_mark_price_channel if channel_name == trading_constants.MARK_PRICE_CHANNEL 
                else None
        ):
            await producer._ensure_dependencies(exchange_manager, [ohlcv_dependency])
            
            # Should subscribe to OHLCV channel
            assert mock_ohlcv_channel.new_consumer.call_count == 1
            ohlcv_call = mock_ohlcv_channel.new_consumer.call_args
            assert ohlcv_call.kwargs['symbol'] == symbol
            assert ohlcv_call.kwargs['time_frame'] == commons_enums.TimeFrames.ONE_HOUR.value
            assert ohlcv_call.kwargs['callback'] == producer._ohlcv_callback
            
            # Should also subscribe to mark price channel
            assert mock_mark_price_channel.new_consumer.call_count == 1
            mark_price_call = mock_mark_price_channel.new_consumer.call_args
            assert mark_price_call.kwargs['symbol'] == symbol
            assert mark_price_call.kwargs['callback'] == producer._mark_price_callback
        
        # Reset mocks and clear subscriptions
        mock_ohlcv_channel.new_consumer.reset_mock()
        mock_mark_price_channel.new_consumer.reset_mock()
        ohlcv_consumers.clear()
        mark_price_consumers.clear()
        
        # Test 2: MARK_PRICE_CHANNEL dependency - should subscribe to mark price only
        mark_price_dependency = exchange_operators.ExchangeDataDependency(
            symbol=symbol,
            time_frame=None,
            data_source=trading_constants.MARK_PRICE_CHANNEL
        )
        
        with mock.patch.object(
            exchanges_channel, 'get_chan', side_effect=lambda channel_name, ex_id: 
                mock_ohlcv_channel if channel_name == trading_constants.OHLCV_CHANNEL 
                else mock_mark_price_channel if channel_name == trading_constants.MARK_PRICE_CHANNEL 
                else None
        ):
            await producer._ensure_dependencies(exchange_manager, [mark_price_dependency])
            
            # Should NOT subscribe to OHLCV
            mock_ohlcv_channel.new_consumer.assert_not_called()
            # Should subscribe to mark price
            assert mock_mark_price_channel.new_consumer.call_count == 1
            mark_price_call = mock_mark_price_channel.new_consumer.call_args
            assert mark_price_call.kwargs['symbol'] == symbol
            assert mark_price_call.kwargs['callback'] == producer._mark_price_callback
        
        # Reset mocks and clear subscriptions
        mock_ohlcv_channel.new_consumer.reset_mock()
        mock_mark_price_channel.new_consumer.reset_mock()
        ohlcv_consumers.clear()
        mark_price_consumers.clear()
        
        # Test 3: Multiple dependencies - should handle all of them
        dependencies = [
            exchange_operators.ExchangeDataDependency(
                symbol=symbol,
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                data_source=trading_constants.OHLCV_CHANNEL
            ),
            exchange_operators.ExchangeDataDependency(
                symbol=symbol,
                time_frame=None,
                data_source=trading_constants.MARK_PRICE_CHANNEL
            )
        ]
        
        # Test 4: avoid re-sub
        with mock.patch.object(
            exchanges_channel, 'get_chan', side_effect=lambda channel_name, ex_id: 
                mock_ohlcv_channel if channel_name == trading_constants.OHLCV_CHANNEL 
                else mock_mark_price_channel if channel_name == trading_constants.MARK_PRICE_CHANNEL 
                else None
        ):
            # call 3 times to ensure the dependencies are not subscribed again
            await producer._ensure_dependencies(exchange_manager, dependencies)
            await producer._ensure_dependencies(exchange_manager, dependencies)
            await producer._ensure_dependencies(exchange_manager, dependencies)
            
            # Should subscribe to OHLCV 1 times
            assert mock_ohlcv_channel.new_consumer.call_count == 1
            # Should subscribe to mark price only 1 times
            assert mock_mark_price_channel.new_consumer.call_count == 1
        
        # Reset mocks and DO NOT clear subscriptions
        mock_ohlcv_channel.new_consumer.reset_mock()
        mock_mark_price_channel.new_consumer.reset_mock()
        
        with mock.patch.object(
            exchanges_channel, 'get_chan', side_effect=lambda channel_name, ex_id: 
                mock_ohlcv_channel if channel_name == trading_constants.OHLCV_CHANNEL 
                else mock_mark_price_channel if channel_name == trading_constants.MARK_PRICE_CHANNEL 
                else None
        ):
            await producer._ensure_dependencies(exchange_manager, dependencies)
            
            # already subscribed to these OHLCV and mark price specs => don't subscribe again
            # (the are in producer.subscribed_channel_specs_by_exchange_id)
            mock_ohlcv_channel.new_consumer.assert_not_called()
            mock_mark_price_channel.new_consumer.assert_not_called()
        
        # Reset mocks and clear subscriptions
        mock_ohlcv_channel.new_consumer.reset_mock()
        mock_mark_price_channel.new_consumer.reset_mock()
        ohlcv_consumers.clear()
        mark_price_consumers.clear()
        
        # Test 5: Unknown dependency data source - should log an error
        unknown_dependency = exchange_operators.ExchangeDataDependency(
            symbol=symbol,
            time_frame=None,
            data_source="unknown_channel"
        )
        
        with mock.patch.object(
            producer.logger, 'error', mock.Mock()
        ) as mock_logger_error, mock.patch.object(
            exchanges_channel, 'get_chan', side_effect=lambda channel_name, ex_id: 
                mock_ohlcv_channel if channel_name == trading_constants.OHLCV_CHANNEL 
                else mock_mark_price_channel if channel_name == trading_constants.MARK_PRICE_CHANNEL 
                else None
        ):
            await producer._ensure_dependencies(exchange_manager, [unknown_dependency])
            
            # Should log an error
            mock_logger_error.assert_called_once()
            assert "Unknown dependency data source" in str(mock_logger_error.call_args)
            # Should NOT subscribe to anything
            mock_ohlcv_channel.new_consumer.assert_not_called()
            mock_mark_price_channel.new_consumer.assert_not_called()
        
        # Reset mocks and clear subscriptions
        mock_ohlcv_channel.new_consumer.reset_mock()
        mock_mark_price_channel.new_consumer.reset_mock()
        ohlcv_consumers.clear()
        mark_price_consumers.clear()
        
        # Test 6: Empty dependencies list - should do nothing
        with mock.patch.object(
            exchanges_channel, 'get_chan', side_effect=lambda channel_name, ex_id: 
                mock_ohlcv_channel if channel_name == trading_constants.OHLCV_CHANNEL 
                else mock_mark_price_channel if channel_name == trading_constants.MARK_PRICE_CHANNEL 
                else None
        ):
            await producer._ensure_dependencies(exchange_manager, [])
            
            # Should not subscribe to anything
            mock_ohlcv_channel.new_consumer.assert_not_called()
            mock_mark_price_channel.new_consumer.assert_not_called()


async def test_reschedule_if_necessary():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        # Test 1: can_create_orders=True with refresh_period set - should schedule health check
        producer.refresh_period = 60.0
        producer.scheduled_health_check = None
        mock_event_loop = mock.Mock()
        mock_call_later_result = mock.Mock()
        mock_event_loop.call_later = mock.Mock(return_value=mock_call_later_result)
        with mock.patch(
            "asyncio.get_event_loop", return_value=mock_event_loop
        ):
            await producer._reschedule_if_necessary(can_create_orders=True)
            
            # Should schedule health check with refresh_period
            mock_event_loop.call_later.assert_called_once_with(60.0, producer._schedule_order_refresh)
            assert producer.scheduled_health_check == mock_call_later_result
        
        # Test 2: can_create_orders=True with refresh_period=0 - should log but not schedule
        producer.refresh_period = 0
        producer.scheduled_health_check = None
        mock_event_loop = mock.Mock()
        mock_event_loop.call_later = mock.Mock()
        with mock.patch(
            "asyncio.get_event_loop", return_value=mock_event_loop
        ):
            await producer._reschedule_if_necessary(can_create_orders=True)
            
            # Should not schedule health check when refresh_period is 0
            mock_event_loop.call_later.assert_not_called()
            assert producer.scheduled_health_check is None
        
        # Test 3: can_create_orders=True with refresh_period=None - should log but not schedule
        producer.refresh_period = None
        producer.scheduled_health_check = None
        mock_event_loop = mock.Mock()
        mock_event_loop.call_later = mock.Mock()
        with mock.patch(
            "asyncio.get_event_loop", return_value=mock_event_loop
        ):
            await producer._reschedule_if_necessary(can_create_orders=True)
            
            # Should not schedule health check when refresh_period is None
            mock_event_loop.call_later.assert_not_called()
            assert producer.scheduled_health_check is None
        
        # Test 4: can_create_orders=False with empty portfolio and initialized - should schedule bot stop
        producer.should_stop = False
        with mock.patch.object(
            trading_util, "wait_for_topic_init", mock.AsyncMock(return_value=True)
        ) as wait_for_topic_init_mock, mock.patch.object(
            trading_api, "get_portfolio", mock.Mock(return_value={})
        ) as get_portfolio_mock, mock.patch.object(
            exchange_manager.trader, "schedule_bot_stop", mock.AsyncMock()
        ) as schedule_bot_stop_mock, mock.patch.object(
            market_making_trading_mode.MarketMakingTradingModeProducer, "_reschedule_if_necessary", mock.AsyncMock()
        ) as super_reschedule_mock:
            await producer._reschedule_if_necessary(can_create_orders=False)
            
            # Should wait for portfolio initialization
            wait_for_topic_init_mock.assert_awaited_once_with(
                exchange_manager, 0, commons_enums.InitializationEventExchangeTopics.BALANCE.value
            )
            # Should check portfolio
            get_portfolio_mock.assert_called_once_with(exchange_manager)
            # Should schedule bot stop with MISSING_MINIMAL_FUNDS
            schedule_bot_stop_mock.assert_awaited_once()
            assert schedule_bot_stop_mock.mock_calls[0].args == (
                commons_enums.StopReason.MISSING_MINIMAL_FUNDS,
                "Empty [binance] portfolio for BTC/USDT market making, scheduling bot stop"
            )
            # Should set should_stop to True
            assert producer.should_stop is False
            # Should NOT call super()._reschedule_if_necessary
            super_reschedule_mock.assert_not_called()
        
        # Test 5: can_create_orders=False with non-empty portfolio - should call super
        producer.should_stop = False
        mock_portfolio = {"BTC": {"available": 1.0, "total": 1.0}}
        with mock.patch.object(
            trading_util, "wait_for_topic_init", mock.AsyncMock(return_value=True)
        ) as wait_for_topic_init_mock, mock.patch.object(
            trading_api, "get_portfolio", mock.Mock(return_value=mock_portfolio)
        ) as get_portfolio_mock, mock.patch.object(
            exchange_manager.trader, "schedule_bot_stop", mock.AsyncMock()
        ) as schedule_bot_stop_mock, mock.patch.object(
            market_making_trading_mode.MarketMakingTradingModeProducer, "_reschedule_if_necessary", mock.AsyncMock()
        ) as super_reschedule_mock:
            await producer._reschedule_if_necessary(can_create_orders=False)
            
            # Should wait for portfolio initialization
            wait_for_topic_init_mock.assert_awaited_once()
            # Should check portfolio
            get_portfolio_mock.assert_called_once_with(exchange_manager)
            # Should NOT schedule bot stop since portfolio is not empty
            schedule_bot_stop_mock.assert_not_called()
            # Should call super()._reschedule_if_necessary
            super_reschedule_mock.assert_awaited_once_with(False)
            # should_stop should remain False
            assert producer.should_stop is False
        
        # Test 6: can_create_orders=False with empty portfolio but not initialized - should call super
        producer.should_stop = False
        with mock.patch.object(
            trading_util, "wait_for_topic_init", mock.AsyncMock(return_value=False)
        ) as wait_for_topic_init_mock, mock.patch.object(
            trading_api, "get_portfolio", mock.Mock(return_value={})
        ) as get_portfolio_mock, mock.patch.object(
            exchange_manager.trader, "schedule_bot_stop", mock.AsyncMock()
        ) as schedule_bot_stop_mock, mock.patch.object(
            market_making_trading_mode.MarketMakingTradingModeProducer, "_reschedule_if_necessary", mock.AsyncMock()
        ) as super_reschedule_mock:
            await producer._reschedule_if_necessary(can_create_orders=False)
            
            # Should wait for portfolio initialization
            wait_for_topic_init_mock.assert_awaited_once()
            # Should check portfolio
            get_portfolio_mock.assert_called_once_with(exchange_manager)
            # Should NOT schedule bot stop since portfolio is not initialized yet
            schedule_bot_stop_mock.assert_not_called()
            # Should call super()._reschedule_if_necessary
            super_reschedule_mock.assert_awaited_once_with(False)
            # should_stop should remain False
            assert producer.should_stop is False


async def test_register_pair_requirement_on_reference_exchanges():
    symbol = "BTC/USDT"
    price_topic = commons_enums.InitializationEventExchangeTopics.PRICE.value
    dependency_symbols_by_topic = {price_topic: {"ETH/USDT"}}

    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        # Setup mock reference price specs
        mock_ref_price_spec_1 = mock.Mock()
        mock_ref_price_spec_1.initialize_if_required = mock.AsyncMock()
        mock_ref_price_spec_1.get_dependencies = mock.Mock(return_value=[])
        mock_ref_price_spec_1.formula = ""

        mock_ref_price_spec_2 = mock.Mock()
        mock_ref_price_spec_2.initialize_if_required = mock.AsyncMock()
        mock_ref_price_spec_2.get_dependencies = mock.Mock(return_value=[])
        mock_ref_price_spec_2.formula = ""

        # Set up reference_prices_by_exchange with the local exchange
        local_exchange_name = exchange_manager.exchange_name
        producer.reference_prices_by_exchange = {
            local_exchange_name: [mock_ref_price_spec_1, mock_ref_price_spec_2]
        }
        producer.subscribed_requirements_exchange_ids = set()

        captured_pending_symbols_by_topic = {}

        async def capture_wait_for_symbols_init(exchange_mgr, symbols_by_pending_topic):
            captured_pending_symbols_by_topic.clear()
            captured_pending_symbols_by_topic.update(symbols_by_pending_topic)
            assert producer.waiting_for_dependencies_init is True

        with mock.patch.object(
            trading_api, "get_all_exchange_ids_with_same_matrix_id", mock.Mock(return_value=[exchange_manager.id])
        ) as get_all_exchange_ids_mock, mock.patch.object(
            trading_api, "get_exchange_manager_from_exchange_id", mock.Mock(return_value=exchange_manager)
        ) as get_exchange_manager_mock, mock.patch.object(
            producer, "_register_pair_requirement_on_reference_exchange", mock.AsyncMock()
        ) as register_pair_mock, mock.patch.object(
            producer, "_ensure_dependencies", mock.AsyncMock(return_value=dependency_symbols_by_topic)
        ) as ensure_dependencies_mock, mock.patch.object(
            producer, "_wait_for_symbols_init", mock.AsyncMock(side_effect=capture_wait_for_symbols_init)
        ) as wait_for_symbols_init_mock:
            # Test 1: First call - should register and subscribe
            await producer._register_pair_requirement_on_reference_exchanges()

            get_all_exchange_ids_mock.assert_called_once_with(local_exchange_name, exchange_manager.id)
            get_exchange_manager_mock.assert_called_once_with(exchange_manager.id)
            register_pair_mock.assert_awaited_once_with(
                exchange_manager, [mock_ref_price_spec_1, mock_ref_price_spec_2]
            )
            assert exchange_manager.id in producer.subscribed_requirements_exchange_ids
            # Each ref price spec should be initialized and have dependencies ensured
            mock_ref_price_spec_1.initialize_if_required.assert_awaited_once_with(exchange_manager)
            mock_ref_price_spec_2.initialize_if_required.assert_awaited_once_with(exchange_manager)
            assert ensure_dependencies_mock.await_count == 2
            wait_for_symbols_init_mock.assert_awaited_once_with(
                exchange_manager, {price_topic: set()}
            )
            assert captured_pending_symbols_by_topic[price_topic] == set()
            assert producer.waiting_for_dependencies_init is False

            # Reset mocks
            register_pair_mock.reset_mock()
            mock_ref_price_spec_1.initialize_if_required.reset_mock()
            mock_ref_price_spec_2.initialize_if_required.reset_mock()
            ensure_dependencies_mock.reset_mock()
            wait_for_symbols_init_mock.reset_mock()

            # Test 2: Second call - already subscribed, should not register again
            await producer._register_pair_requirement_on_reference_exchanges()

            register_pair_mock.assert_not_called()
            mock_ref_price_spec_1.initialize_if_required.assert_not_called()
            mock_ref_price_spec_2.initialize_if_required.assert_not_called()
            ensure_dependencies_mock.assert_not_called()
            wait_for_symbols_init_mock.assert_not_called()

        # Test 3: Other exchange with formula - pending symbols should include dependency symbols
        other_exchange_manager = mock.Mock()
        other_exchange_manager.id = "kraken-1"
        other_exchange_manager.exchange_name = "kraken"
        other_exchange_manager.bot_id = exchange_manager.bot_id

        mock_ref_price_spec_with_formula = mock.Mock()
        mock_ref_price_spec_with_formula.initialize_if_required = mock.AsyncMock()
        mock_ref_price_spec_with_formula.get_dependencies = mock.Mock(return_value=[])
        mock_ref_price_spec_with_formula.formula = "50000"

        producer.reference_prices_by_exchange = {
            other_exchange_manager.exchange_name: [mock_ref_price_spec_with_formula]
        }
        producer.subscribed_requirements_exchange_ids = set()

        with mock.patch.object(
            trading_api, "get_all_exchange_ids_with_same_matrix_id", mock.Mock(return_value=[other_exchange_manager.id])
        ), mock.patch.object(
            trading_api, "get_exchange_manager_from_exchange_id", mock.Mock(return_value=other_exchange_manager)
        ), mock.patch.object(
            producer, "_register_pair_requirement_on_reference_exchange", mock.AsyncMock()
        ), mock.patch.object(
            producer, "_ensure_dependencies", mock.AsyncMock(return_value=dependency_symbols_by_topic)
        ), mock.patch.object(
            producer, "_wait_for_symbols_init", mock.AsyncMock()
        ) as wait_for_symbols_init_mock:
            await producer._register_pair_requirement_on_reference_exchanges()

            wait_for_symbols_init_mock.assert_awaited_once_with(
                other_exchange_manager, {price_topic: {"ETH/USDT"}}
            )

        # Test 4: Other exchange without formula - pending symbols should stay empty
        mock_ref_price_spec_without_formula = mock.Mock()
        mock_ref_price_spec_without_formula.initialize_if_required = mock.AsyncMock()
        mock_ref_price_spec_without_formula.get_dependencies = mock.Mock(return_value=[])
        mock_ref_price_spec_without_formula.formula = ""

        producer.reference_prices_by_exchange = {
            other_exchange_manager.exchange_name: [mock_ref_price_spec_without_formula]
        }
        producer.subscribed_requirements_exchange_ids = set()

        with mock.patch.object(
            trading_api, "get_all_exchange_ids_with_same_matrix_id", mock.Mock(return_value=[other_exchange_manager.id])
        ), mock.patch.object(
            trading_api, "get_exchange_manager_from_exchange_id", mock.Mock(return_value=other_exchange_manager)
        ), mock.patch.object(
            producer, "_register_pair_requirement_on_reference_exchange", mock.AsyncMock()
        ), mock.patch.object(
            producer, "_ensure_dependencies", mock.AsyncMock(return_value=dependency_symbols_by_topic)
        ), mock.patch.object(
            producer, "_wait_for_symbols_init", mock.AsyncMock()
        ) as wait_for_symbols_init_mock:
            await producer._register_pair_requirement_on_reference_exchanges()

            wait_for_symbols_init_mock.assert_awaited_once_with(
                other_exchange_manager, {price_topic: set()}
            )

        # Test 5: Local exchange with formula - pending symbols should stay empty
        mock_ref_price_spec_local_formula = mock.Mock()
        mock_ref_price_spec_local_formula.initialize_if_required = mock.AsyncMock()
        mock_ref_price_spec_local_formula.get_dependencies = mock.Mock(return_value=[])
        mock_ref_price_spec_local_formula.formula = "50000"

        producer.reference_prices_by_exchange = {
            local_exchange_name: [mock_ref_price_spec_local_formula]
        }
        producer.subscribed_requirements_exchange_ids = set()

        with mock.patch.object(
            trading_api, "get_all_exchange_ids_with_same_matrix_id", mock.Mock(return_value=[exchange_manager.id])
        ), mock.patch.object(
            trading_api, "get_exchange_manager_from_exchange_id", mock.Mock(return_value=exchange_manager)
        ), mock.patch.object(
            producer, "_register_pair_requirement_on_reference_exchange", mock.AsyncMock()
        ), mock.patch.object(
            producer, "_ensure_dependencies", mock.AsyncMock(return_value=dependency_symbols_by_topic)
        ), mock.patch.object(
            producer, "_wait_for_symbols_init", mock.AsyncMock()
        ) as wait_for_symbols_init_mock:
            await producer._register_pair_requirement_on_reference_exchanges()

            wait_for_symbols_init_mock.assert_awaited_once_with(
                exchange_manager, {price_topic: set()}
            )


class TestWaitForSymbolsInit:
    async def test_creates_events_and_waits_for_each_symbol(self):
        symbol = "BTC/USDT"
        price_topic = commons_enums.InitializationEventExchangeTopics.PRICE.value
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            mock_event_provider = mock.Mock()
            mock_get_or_create_event = mock.Mock()
            mock_event_provider.get_or_create_event = mock_get_or_create_event

            with mock.patch.object(
                commons_tree.EventProvider, "instance", mock.Mock(return_value=mock_event_provider)
            ), mock.patch.object(
                trading_util, "wait_for_topic_init", mock.AsyncMock()
            ) as wait_for_topic_init_mock:
                await producer._wait_for_symbols_init(
                    exchange_manager, {price_topic: {"BTC/USDT", "ETH/USDT"}}
                )

                assert mock_get_or_create_event.call_count == 2
                for pending_symbol in ["BTC/USDT", "ETH/USDT"]:
                    mock_get_or_create_event.assert_any_call(
                        exchange_manager.bot_id,
                        commons_tree.get_exchange_path(
                            exchange_manager.exchange_name,
                            price_topic,
                            symbol=pending_symbol,
                        ),
                        allow_creation=True,
                    )
                wait_for_topic_init_mock.assert_awaited_once_with(
                    exchange_manager,
                    1 * commons_constants.MINUTE_TO_SECONDS,
                    price_topic,
                    symbols=mock.ANY,
                )
                awaited_symbols = wait_for_topic_init_mock.await_args.kwargs["symbols"]
                assert set(awaited_symbols) == {"BTC/USDT", "ETH/USDT"}

    async def test_timeout_is_swallowed(self):
        symbol = "BTC/USDT"
        price_topic = commons_enums.InitializationEventExchangeTopics.PRICE.value
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            mock_event_provider = mock.Mock()
            mock_event_provider.get_or_create_event = mock.Mock()

            with mock.patch.object(
                commons_tree.EventProvider, "instance", mock.Mock(return_value=mock_event_provider)
            ), mock.patch.object(
                trading_util, "wait_for_topic_init", mock.AsyncMock(side_effect=asyncio.TimeoutError)
            ) as wait_for_topic_init_mock:
                await producer._wait_for_symbols_init(
                    exchange_manager, {price_topic: {"BTC/USDT"}}
                )

                wait_for_topic_init_mock.assert_awaited_once()

    async def test_empty_symbols_still_waits(self):
        symbol = "BTC/USDT"
        price_topic = commons_enums.InitializationEventExchangeTopics.PRICE.value
        async with _get_tools(symbol) as (producer, consumer, exchange_manager):
            mock_event_provider = mock.Mock()
            mock_get_or_create_event = mock.Mock()
            mock_event_provider.get_or_create_event = mock_get_or_create_event

            with mock.patch.object(
                commons_tree.EventProvider, "instance", mock.Mock(return_value=mock_event_provider)
            ), mock.patch.object(
                trading_util, "wait_for_topic_init", mock.AsyncMock()
            ) as wait_for_topic_init_mock:
                await producer._wait_for_symbols_init(
                    exchange_manager, {price_topic: set()}
                )

                mock_get_or_create_event.assert_not_called()
                wait_for_topic_init_mock.assert_awaited_once_with(
                    exchange_manager,
                    1 * commons_constants.MINUTE_TO_SECONDS,
                    price_topic,
                    symbols=[],
                )
