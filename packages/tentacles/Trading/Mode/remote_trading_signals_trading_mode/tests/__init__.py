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
import os.path
import mock
import pytest
import pytest_asyncio

import octobot_backtesting.api as backtesting_api
import async_channel.util as channel_util
import async_channel.channels as channels
import octobot_commons.channels_name as channels_names
import octobot_commons.tests.test_config as test_config
import octobot_commons.constants as commons_constants
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.signals as signals
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as exchanges
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.enums as trading_enums
import octobot_trading.signals as trading_signals
import tentacles.Trading.Mode as modes
import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges
from tentacles.Trading.Mode.remote_trading_signals_trading_mode.remote_trading_signals_trading import \
    RemoteTradingSignalsTradingMode
import octobot_tentacles_manager.api as tentacles_manager_api


@pytest_asyncio.fixture
async def local_trader(exchange_name="binance", backtesting=None, symbol="BTC/USDT:USDT"):
    tentacles_manager_api.reload_tentacle_info()
    exchange_manager = None
    signal_channel = None
    try:
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 2000
        exchange_manager = test_exchanges.get_test_exchange_manager(config, exchange_name)
        exchange_manager.tentacles_setup_config = test_utils_config.get_tentacles_setup_config()

        # use backtesting not to spam exchanges apis
        exchange_manager.is_simulated = True
        exchange_manager.is_backtesting = True
        exchange_manager.use_cached_markets = False
        backtesting = backtesting or await backtesting_api.initialize_backtesting(
            config,
            exchange_ids=[exchange_manager.id],
            matrix_id=None,
            data_files=[os.path.join(test_config.TEST_CONFIG_FOLDER,
                                     "AbstractExchangeHistoryCollector_1586017993.616272.data")])

        exchange_manager.exchange = exchanges.ExchangeSimulator(exchange_manager.config,
                                                                exchange_manager,
                                                                backtesting)
        await exchange_manager.exchange.initialize()
        for exchange_channel_class_type in [exchanges_channel.ExchangeChannel,
                                            exchanges_channel.TimeFrameExchangeChannel]:
            await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                             exchange_manager=exchange_manager)

        trader = exchanges.TraderSimulator(config, exchange_manager)
        await trader.initialize()

        mode = modes.RemoteTradingSignalsTradingMode(config, exchange_manager)
        mode.symbol = None if mode.get_is_symbol_wildcard() else symbol
        # avoid error when trying to connect to server signals
        with mock.patch.object(RemoteTradingSignalsTradingMode, "_subscribe_to_signal_feed",
                               new=mock.AsyncMock(return_value=[])) \
                as _subscribe_to_signal_feed_mock:
            signal_channel, created = await trading_signals.create_remote_trading_signal_channel_if_missing(
                exchange_manager
            )
            assert created is True
            await mode.initialize()
            # add mode to exchange manager so that it can be stopped and freed from memory
            exchange_manager.trading_modes.append(mode)

            # set BTC/USDT price at 1000 USDT
            trading_api.force_set_mark_price(exchange_manager, symbol, 1000)
            # let trading modes start
            await asyncio_tools.wait_asyncio_next_cycle()
            _subscribe_to_signal_feed_mock.assert_called_once()
        yield mode.producers[0], mode.get_trading_mode_consumers()[0], trader
    finally:
        if exchange_manager is not None:
            for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
                await backtesting_api.stop_importer(importer)
            if exchange_manager.exchange.backtesting.time_updater is not None:
                await exchange_manager.exchange.backtesting.stop()
            await exchange_manager.stop()
        if signal_channel is not None:
            await signal_channel.stop()
            channels.del_chan(channels_names.OctoBotCommunityChannelsName.REMOTE_TRADING_SIGNALS_CHANNEL.value)


SIGNAL_TOPIC = trading_enums.TradingSignalTopics.ORDERS.value


@pytest.fixture
def mocked_sell_limit_signal():
    return signals.Signal(
        SIGNAL_TOPIC,
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.SELL_LIMIT.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.3574085830652285%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 1010.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "46a0b2de-5b8f-4a39-89a0-137504f83dfc",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.BalancedTakeProfitAndStopOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value: trading_personal_data.StopFirstActiveOrderSwapStrategy.__name__,
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value: 3,
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value: trading_enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value,
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_PRICE.value: 21,
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_ABOVE.value: False,
            trading_enums.TradingSignalOrdersAttrs.IS_ACTIVE.value: False,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "managed_order long exit (id: 143968020)",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "5705d395-f970-45d9-9ba8-f63da17f17b2",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: True,
        },
        dependencies=trading_signals.get_orders_dependencies([mock.Mock(order_id="123"), mock.Mock(order_id="456")])
    )


@pytest.fixture
def mocked_sell_limit_signal_with_trailing_group():
    return signals.Signal(
        SIGNAL_TOPIC,
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.SELL_LIMIT.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.3574085830652285%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 1010.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "46a0b2de-5b8f-4a39-89a0-137504f83dfc",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.TrailingOnFilledTPBalancedOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "managed_order long exit (id: 143968020)",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "5705d395-f970-45d9-9ba8-f63da17f17b2",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: True,
        },
        dependencies=trading_signals.get_orders_dependencies([])
    )


@pytest.fixture
def mocked_update_leverage_signal():
    return signals.Signal(
        trading_enums.TradingSignalTopics.POSITIONS.value,
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.EDIT.value,
            trading_enums.TradingSignalPositionsAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalPositionsAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalPositionsAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.FUTURE.value,
            trading_enums.TradingSignalPositionsAttrs.STRATEGY.value: "plop strategy",
            trading_enums.TradingSignalPositionsAttrs.SIDE.value: None,
            trading_enums.TradingSignalPositionsAttrs.LEVERAGE.value: 10,
        }
    )


@pytest.fixture
def mocked_buy_limit_signal():
    return signals.Signal(
        SIGNAL_TOPIC,
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.BUY_LIMIT.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.3574085830652285%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 888.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "managed_order long exit (id: 143968020)",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "5705d395-f970-45d9-9ba8-f63da17f17b2",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
        },
        dependencies=trading_signals.get_orders_dependencies([mock.Mock(order_id="123"), mock.Mock(order_id="456")])
    )


@pytest.fixture
def mocked_bundle_stop_loss_in_sell_limit_signal(mocked_sell_limit_signal):
    mocked_sell_limit_signal.content[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value].append(
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.STOP_LOSS.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.356892%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 9990.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "46a0b2de-5b8f-4a39-89a0-137504f83dfc",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.BalancedTakeProfitAndStopOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "managed_order long exit (id: 143968020)",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "5ad2a999-5ac2-47f0-9b69-c75a36f3858a",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: True,
        }
    )
    return mocked_sell_limit_signal


@pytest.fixture
def mocked_bundle_stop_loss_in_sell_limit_in_market_signal(mocked_sell_limit_signal, mocked_buy_market_signal):
    trailing_profile = trading_personal_data.FilledTakeProfitTrailingProfile([
        trading_personal_data.TrailingPriceStep(price, price, True)
        for price in (10000, 12000, 13000)
    ])
    mocked_sell_limit_signal.content[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value].append(
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.STOP_LOSS.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.356892%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 9990.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "46a0b2de-5b8f-4a39-89a0-137504f83dfc",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.BalancedTakeProfitAndStopOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value: trading_personal_data.StopFirstActiveOrderSwapStrategy.__name__,
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value: 3,
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value: trading_enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value,
            trading_enums.TradingSignalOrdersAttrs.TRAILING_PROFILE_TYPE.value: None,
            trading_enums.TradingSignalOrdersAttrs.TRAILING_PROFILE.value: None,
            trading_enums.TradingSignalOrdersAttrs.CANCEL_POLICY_TYPE.value: trading_personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__,
            trading_enums.TradingSignalOrdersAttrs.CANCEL_POLICY_KWARGS.value: None,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "managed_order long exit (id: 143968020)",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "5ad2a999-5ac2-47f0-9b69-c75a36f3858a",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: False,
        }
    )
    mocked_buy_market_signal.content[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value].append(
        mocked_sell_limit_signal.content
    )
    return mocked_buy_market_signal


@pytest.fixture
def mocked_bundle_trailing_stop_loss_in_sell_limit_in_market_signal(mocked_sell_limit_signal_with_trailing_group, mocked_buy_market_signal):
    trailing_profile = trading_personal_data.FilledTakeProfitTrailingProfile([
        trading_personal_data.TrailingPriceStep(price, price, True)
        for price in (10000, 12000, 13000)
    ])
    mocked_sell_limit_signal_with_trailing_group.content[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value].append(
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.STOP_LOSS.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.356892%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 9990.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "46a0b2de-5b8f-4a39-89a0-137504f83dfc",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.TrailingOnFilledTPBalancedOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.TRAILING_PROFILE_TYPE.value:
                trading_personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT.value,
            trading_enums.TradingSignalOrdersAttrs.TRAILING_PROFILE.value: trailing_profile.to_dict(),
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "managed_order long exit (id: 143968020)",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "5ad2a999-5ac2-47f0-9b69-c75a36f3858a",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: False,
            trading_enums.TradingSignalOrdersAttrs.CANCEL_POLICY_TYPE.value: trading_personal_data.ExpirationTimeOrderCancelPolicy.__name__,
            trading_enums.TradingSignalOrdersAttrs.CANCEL_POLICY_KWARGS.value: {
                "expiration_time": 1000.0,
            },
        }
    )
    mocked_buy_market_signal.content[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value].append(
        mocked_sell_limit_signal_with_trailing_group.content
    )
    return mocked_buy_market_signal


@pytest.fixture
def mocked_bundle_trigger_above_stop_loss_in_sell_limit_in_market_signal(mocked_sell_limit_signal, mocked_buy_market_signal):
    mocked_sell_limit_signal.content[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value].append(
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.STOP_LOSS.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.356892%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: 0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 999999990.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: True,
            trading_enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value: True,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: "46a0b2de-5b8f-4a39-89a0-137504f83dfc",
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value:
                trading_personal_data.BalancedTakeProfitAndStopOrderGroup.__name__,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "managed_order long exit (id: 143968020)",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "5ad2a999-5ac2-47f0-9b69-c75a36f3858a",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: False,
        }
    )
    mocked_buy_market_signal.content[trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value].append(
        mocked_sell_limit_signal.content
    )
    return mocked_buy_market_signal


@pytest.fixture
def mocked_buy_market_signal():
    return signals.Signal(
        SIGNAL_TOPIC,
        {
            trading_enums.TradingSignalCommonsAttrs.ACTION.value: trading_enums.TradingSignalOrdersActions.CREATE.value,
            trading_enums.TradingSignalOrdersAttrs.SYMBOL.value: "BTC/USDT:USDT",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE.value: "bybit",
            trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value: trading_enums.ExchangeTypes.SPOT.value,
            trading_enums.TradingSignalOrdersAttrs.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            trading_enums.TradingSignalOrdersAttrs.TYPE.value: trading_enums.TraderOrderType.BUY_MARKET.value,
            trading_enums.TradingSignalOrdersAttrs.QUANTITY.value: 0.004,
            trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value: "5.356892%",
            trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value: None,
            trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value: 1001.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.CURRENT_PRICE.value: 1000.69,
            trading_enums.TradingSignalOrdersAttrs.UPDATED_CURRENT_PRICE.value: 0.0,
            trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.POST_ONLY.value: False,
            trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value: None,
            trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value: None,
            trading_enums.TradingSignalOrdersAttrs.TAG.value: "managed_order long entry (id: 143968020)",
            trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value: "adc24701-573b-40dd-b6c9-3666cd22f33e",
            trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value: None,
            trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value: None,
            trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value: [],
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value: None,
            trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value: True,
        }
    )
