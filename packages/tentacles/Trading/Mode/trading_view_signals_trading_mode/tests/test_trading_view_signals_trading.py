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
import pytest_asyncio

import async_channel.util as channel_util
import octobot_backtesting.api as backtesting_api
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.constants as commons_constants
import octobot_commons.symbols as commons_symbols
import octobot_commons.tests.test_config as test_config
import octobot_trading.constants as trading_constants
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.errors as errors
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.signals as trading_signals
import octobot_trading.modes.script_keywords as script_keywords
import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.blockchain_wallets.simulator.blockchain_wallet_simulator as blockchain_wallet_simulator
import octobot_tentacles_manager.api as tentacles_manager_api

import tentacles.Trading.Mode as Mode
import tentacles.Trading.Mode.trading_view_signals_trading_mode.trading_view_signals_trading as trading_view_signals_trading
import tentacles.Trading.Mode.trading_view_signals_trading_mode.actions_params as actions_params
import tentacles.Trading.Mode.trading_view_signals_trading_mode.errors as trading_view_signals_trading_mode_errors

import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def tools():
    tentacles_manager_api.reload_tentacle_info()
    exchange_manager = None
    try:
        symbol = "BTC/USDT"
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
            data_files=[
                os.path.join(test_config.TEST_CONFIG_FOLDER, "AbstractExchangeHistoryCollector_1586017993.616272.data")
            ])
        exchange_manager.exchange = exchanges.ExchangeSimulator(exchange_manager.config,
                                                                exchange_manager,
                                                                backtesting)
        await exchange_manager.exchange.initialize()
        for exchange_channel_class_type in [exchanges_channel.ExchangeChannel, exchanges_channel.TimeFrameExchangeChannel]:
            await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                             exchange_manager=exchange_manager)

        trader = exchanges.TraderSimulator(config, exchange_manager)
        await trader.initialize()

        mode = Mode.TradingViewSignalsTradingMode(config, exchange_manager)
        mode.symbol = symbol
        await mode.initialize()
        # add mode to exchange manager so that it can be stopped and freed from memory
        exchange_manager.trading_modes.append(mode)
        producer = mode.producers[0]
        consumer = mode.get_trading_mode_consumers()[0]

        # set BTC/USDT price at 7009.194999999998 USDT
        last_btc_price = 7009.194999999998
        trading_api.force_set_mark_price(exchange_manager, symbol, last_btc_price)
        exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value = \
            decimal.Decimal(str(last_btc_price * 10))

        yield exchange_manager, symbol, mode, producer, consumer
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


BLOCKCHAIN_WALLET_ASSET = "ETH"

@pytest.fixture
def blockchain_wallet_details():
    blockchain_descriptor = blockchain_wallets.BlockchainDescriptor(
        wallet_type=blockchain_wallets.BlockchainWalletSimulator.__name__,
        network=trading_constants.SIMULATED_BLOCKCHAIN_NETWORK,
        native_coin_symbol="ETH"
    )
    wallet_descriptor = blockchain_wallets.WalletDescriptor(
        address="0x1234567890123456789012345678901234567890",
        private_key="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        specific_config={
            # Test with sufficient balance
            blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
                {
                    blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: BLOCKCHAIN_WALLET_ASSET,
                    blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.0
                }
            ]
        }
    )
    wallet_details = blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor,
        wallet_descriptor=wallet_descriptor
    )
    yield wallet_details


async def test_parse_signal_data():
    errors = []
    exchange_name = "binance"
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        """
        
        
        KEY=value
        EXCHANGE=1
        
        
        
        PLOp=true
        """,
        exchange_name,
        errors
    ) == {
        "KEY": "value",
        "EXCHANGE": "1",
        "PLOp": True,
    }
    assert errors == []

    errors = []
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "KEY=value\nEXCHANGE=1\n\n\n\nPLOp=false\n",
        exchange_name,
        errors
    ) == {
        "KEY": "value",
        "EXCHANGE": "1",
        "PLOp": False,
    }
    assert errors == []

    errors = []
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "KEY=value\\nEXCHANGE=1\\nPLOp=ABC",
        exchange_name,
        errors
    ) == {
        "KEY": "value",
        "EXCHANGE": "1",
        "PLOp": "ABC",
    }
    assert errors == []

    errors = []
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "KEY=value\\nEXCHANGE\\nPLOp=ABC",
        exchange_name,
        errors
    ) == {
        "KEY": "value",
        "PLOp": "ABC",
    }
    assert len(errors) == 1
    assert "EXCHANGE" in str(errors[0])
    assert "nPLOp" not in str(errors[0])
    assert "KEY" not in str(errors[0])

    errors = []
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "KEY=value;EXCHANGE;;;;;PLOp=ABC;TAKE_PROFIT_PRICE=1;;TAKE_PROFIT_PRICE_2=3",
        exchange_name,
        errors
    ) == {
        "KEY": "value",
        "PLOp": "ABC",
        "TAKE_PROFIT_PRICE": "1",
        "TAKE_PROFIT_PRICE_2": "3",
    }
    assert len(errors) == 1
    assert "EXCHANGE" in str(errors[0])
    assert "nPLOp" not in str(errors[0])
    assert "KEY" not in str(errors[0])

    errors = []
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        ";KEY=value;EXCHANGE\nPLOp=ABC\\nGG=HIHI;LEVERAGE=3",
        exchange_name,
        errors
    ) == {
        "KEY": "value",
        "PLOp": "ABC",
        "GG": "HIHI",
        "LEVERAGE": "3",
    }
    assert len(errors) == 1
    assert "EXCHANGE" in str(errors[0])
    assert "nPLOp" not in str(errors[0])
    assert "KEY" not in str(errors[0])
    assert "LEVERAGE" not in str(errors[0])


async def test_parse_signal_data_with_generic_usd_stablecoin_symbol():
    errors = []
    exchange_name = "binance"
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "SYMBOL=USD*", None, errors
    ) == {
        "SYMBOL": "USD*", # no exchange, leave as is
    }
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "NO_SYMBOL=USD*", "", errors
    ) == {
        "NO_SYMBOL": "USD*", # no exchange, leave as is
    }
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "SYMBOL=USD*", exchange_name, errors
    ) == {
        "SYMBOL": "USDC", # default reference market for binance, as defined in 
        # tentacles.Meta.Keywords.scripting_library.configuration.exchanges_configuration
        # (case insensitive)
    }
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "NO_SYMBOL=USD*", exchange_name, errors
    ) == {
        "NO_SYMBOL": "USD*", # no symbol, leave as is
    }
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "SYMBOL=USD*;EXCHANGE=BiNance", exchange_name, errors
    ) == {
        "SYMBOL": "USDC", # default reference market for binance, as defined in 
        # tentacles.Meta.Keywords.scripting_library.configuration.exchanges_configuration
        # (case insensitive)
        "EXCHANGE": "BiNance",
    }
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "SYMBOL=USD*", "mexc", errors
    ) == {
        "SYMBOL": commons_constants.DEFAULT_REFERENCE_MARKET, # no default reference market for mexc, use default
    }
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "SYMBOL=USD*;EXCHANGE=????", "????", errors
    ) == {
        "SYMBOL": commons_constants.DEFAULT_REFERENCE_MARKET, # unknown exchange, use default
        "EXCHANGE": "????",
    }
    assert Mode.TradingViewSignalsTradingMode.parse_signal_data(
        "SYMBOL=USD*", None, errors
    ) == {
        "SYMBOL": "USD*", # no exchange, leave as is
    }
    assert errors == []


async def test_trading_view_signal_callback(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    context = script_keywords.get_base_context(producer.trading_mode)
    with mock.patch.object(script_keywords, "get_base_context", mock.Mock(return_value=context)) \
         as get_base_context_mock:
        for exception in (errors.MissingFunds, errors.InvalidArgumentError):
            # ensure exception is caught
            with mock.patch.object(
                producer, "signal_callback", mock.AsyncMock(side_effect=exception)
            ) as signal_callback_mock:
                signal = f"""
                    EXCHANGE={exchange_manager.exchange_name}
                    SYMBOL={symbol}
                    SIGNAL=BUY
                """
                await mode._trading_view_signal_callback({"metadata": signal})
                signal_callback_mock.assert_awaited_once()
                get_base_context_mock.assert_called_once()
                get_base_context_mock.reset_mock()

        with mock.patch.object(producer, "signal_callback", mock.AsyncMock()) as signal_callback_mock:
            # invalid data
            data = ""
            await mode._trading_view_signal_callback({"metadata": data})
            signal_callback_mock.assert_not_awaited()
            signal_callback_mock.reset_mock()
            get_base_context_mock.assert_not_called()

            # invalid symbol
            data = f"""
            EXCHANGE={exchange_manager.exchange_name}
            SYMBOL={symbol}PLOP
            SIGNAL=BUY
            """
            await mode._trading_view_signal_callback({"metadata": data})
            signal_callback_mock.assert_not_awaited()
            signal_callback_mock.reset_mock()
            get_base_context_mock.assert_not_called()

            # minimal signal
            data = f"""
            EXCHANGE={exchange_manager.exchange_name}
            SYMBOL={symbol}
            SIGNAL=BUY
            """
            await mode._trading_view_signal_callback({"metadata": data})
            signal_callback_mock.assert_awaited_once_with({
                mode.EXCHANGE_KEY: exchange_manager.exchange_name,
                mode.SYMBOL_KEY: symbol,
                mode.SIGNAL_KEY: "BUY",
            }, context)
            signal_callback_mock.reset_mock()
            get_base_context_mock.assert_called_once()
            get_base_context_mock.reset_mock()

            # minimal signal
            signal = f"""
                EXCHANGE={exchange_manager.exchange_name}
                SYMBOL={symbol}
                SIGNAL=BUY
            """
            await mode._trading_view_signal_callback({"metadata": signal})
            signal_callback_mock.assert_awaited_once_with({
                mode.EXCHANGE_KEY: exchange_manager.exchange_name,
                mode.SYMBOL_KEY: symbol,
                mode.SIGNAL_KEY: "BUY",
            }, context)
            signal_callback_mock.reset_mock()
            get_base_context_mock.assert_called_once()
            get_base_context_mock.reset_mock()

            # other signals
            signal = f"""
                EXCHANGE={exchange_manager.exchange_name}
                SYMBOL={commons_symbols.parse_symbol(symbol).merged_str_base_and_quote_only_symbol(
                market_separator=""
            )}
                SIGNAL=BUY
                HEELLO=True
                PLOP=faLse
            """
            await mode._trading_view_signal_callback({"metadata": signal})
            signal_callback_mock.assert_awaited_once_with({
                mode.EXCHANGE_KEY: exchange_manager.exchange_name,
                mode.SYMBOL_KEY: commons_symbols.parse_symbol(symbol).merged_str_base_and_quote_only_symbol(
                    market_separator=""
                ),
                mode.SIGNAL_KEY: "BUY",
                "HEELLO": True,
                "PLOP": False,
            }, context)
            signal_callback_mock.reset_mock()
            get_base_context_mock.assert_called_once()
            get_base_context_mock.reset_mock()

            # Test non-order signal with missing EXCHANGE_KEY - should call _process_or_ignore_non_order_signal
            # and process it if first trading mode
            with mock.patch.object(mode, "is_first_trading_mode_on_this_matrix", mock.Mock(return_value=True)) \
                as is_first_mock, \
                mock.patch.object(mode.logger, "info") as logger_info_mock:
                signal = f"""
                    SYMBOL={symbol}
                    SIGNAL={mode.ENSURE_EXCHANGE_BALANCE_SIGNAL}
                """
                await mode._trading_view_signal_callback({"metadata": signal})
                is_first_mock.assert_called_once()
                # Should process the signal since it's a non-order signal and first trading mode
                signal_callback_mock.assert_called_once()
                logger_info_mock.assert_called()
                assert "Non order signal" in str(logger_info_mock.call_args_list)
                assert "processing" in str(logger_info_mock.call_args_list)
                signal_callback_mock.reset_mock()
                logger_info_mock.reset_mock()

            # Test non-order signal with missing EXCHANGE_KEY but not first trading mode - should ignore
            with mock.patch.object(mode, "is_first_trading_mode_on_this_matrix", mock.Mock(return_value=False)) \
                as is_first_mock, \
                mock.patch.object(mode.logger, "info") as logger_info_mock:
                signal = f"""
                    SYMBOL={symbol}
                    SIGNAL={mode.ENSURE_EXCHANGE_BALANCE_SIGNAL}
                """
                await mode._trading_view_signal_callback({"metadata": signal})
                is_first_mock.assert_called_once()
                # Should not process the signal since it's not the first trading mode
                signal_callback_mock.assert_not_awaited()
                logger_info_mock.assert_called()
                assert "Non order signal" in str(logger_info_mock.call_args_list)
                assert "ignored" in str(logger_info_mock.call_args_list)
                signal_callback_mock.reset_mock()
                logger_info_mock.reset_mock()

            # Test regular order signal with missing EXCHANGE_KEY - should call _process_or_ignore_non_order_signal but return False
            with mock.patch.object(mode.logger, "error") as logger_error_mock:
                signal = f"""
                    SYMBOL={symbol}
                    SIGNAL=BUY
                """
                await mode._trading_view_signal_callback({"metadata": signal})
                # Should not process the signal and should log error
                signal_callback_mock.assert_not_awaited()
                logger_error_mock.assert_called_once()
                assert "missing" in str(logger_error_mock.call_args).lower() or "required" in str(logger_error_mock.call_args).lower()
                signal_callback_mock.reset_mock()
                logger_error_mock.reset_mock()

            # Test non-order signal with missing SYMBOL_KEY - should call _process_or_ignore_non_order_signal
            # and process it if first trading mode
            with mock.patch.object(mode, "is_first_trading_mode_on_this_matrix", mock.Mock(return_value=True)) \
                as is_first_mock, \
                mock.patch.object(mode.logger, "info") as logger_info_mock:
                signal = f"""
                    EXCHANGE={exchange_manager.exchange_name}
                    SIGNAL={mode.WITHDRAW_FUNDS_SIGNAL}
                """
                await mode._trading_view_signal_callback({"metadata": signal})
                is_first_mock.assert_called_once()
                # Should process the signal since it's a non-order signal and first trading mode
                signal_callback_mock.assert_awaited_once()
                logger_info_mock.assert_called()
                assert "Non order signal" in str(logger_info_mock.call_args_list)
                assert "processing" in str(logger_info_mock.call_args_list)
                signal_callback_mock.reset_mock()
                logger_info_mock.reset_mock()


async def test_signal_callback(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    context = script_keywords.get_base_context(producer.trading_mode)
    with mock.patch.object(producer, "_set_state", mock.AsyncMock()) as _set_state_mock, \
        mock.patch.object(mode, "set_leverage", mock.AsyncMock()) as set_leverage_mock:
        await producer.signal_callback({
            mode.EXCHANGE_KEY: exchange_manager.exchange_name,
            mode.SYMBOL_KEY: "unused",
            mode.SIGNAL_KEY: "BUY",
        }, context)
        _set_state_mock.assert_awaited_once()
        set_leverage_mock.assert_not_called()
        assert _set_state_mock.await_args[0][1] == symbol
        assert _set_state_mock.await_args[0][2] == trading_view_signals_trading.SignalActions.CREATE_ORDERS
        assert _set_state_mock.await_args[0][3] == trading_enums.EvaluatorStates.VERY_LONG
        assert compare_dict_with_nan(_set_state_mock.await_args[0][4], {
            consumer.PRICE_KEY: trading_constants.ZERO,
            consumer.VOLUME_KEY: trading_constants.ZERO,
            consumer.STOP_PRICE_KEY: decimal.Decimal(math.nan),
            consumer.STOP_ONLY: False,
            consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal(math.nan),
            consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [],
            consumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: [],
            consumer.REDUCE_ONLY_KEY: False,
            consumer.TAG_KEY: None,
            consumer.TRAILING_PROFILE: None,
            consumer.EXCHANGE_ORDER_IDS: None,
            consumer.LEVERAGE: None,
            consumer.ORDER_EXCHANGE_CREATION_PARAMS: {},
            consumer.CANCEL_POLICY: None,
            consumer.CANCEL_POLICY_PARAMS: None,
        })
        assert compare_dict_with_nan(_set_state_mock.await_args[0][5], {
            mode.EXCHANGE_KEY: exchange_manager.exchange_name,
            mode.SYMBOL_KEY: "unused",
            mode.SIGNAL_KEY: "BUY",
        })
        _set_state_mock.reset_mock()

        await producer.signal_callback({
            mode.EXCHANGE_KEY: exchange_manager.exchange_name,
            mode.SYMBOL_KEY: "unused",
            mode.SIGNAL_KEY: "SELL",
            mode.ORDER_TYPE_SIGNAL: "stop",
            mode.STOP_PRICE_KEY: 25000,
            mode.VOLUME_KEY: "12%",
            mode.TAG_KEY: "stop_1_tag",
            mode.CANCEL_POLICY: trading_personal_data.ExpirationTimeOrderCancelPolicy.__name__,
            mode.CANCEL_POLICY_PARAMS: {
                "expiration_time": 1000.0,
            },
            consumer.EXCHANGE_ORDER_IDS: None,

        }, context)
        set_leverage_mock.assert_not_called()
        _set_state_mock.assert_awaited_once()
        assert _set_state_mock.await_args[0][1] == symbol
        assert _set_state_mock.await_args[0][2] == trading_view_signals_trading.SignalActions.CREATE_ORDERS
        assert _set_state_mock.await_args[0][3] == trading_enums.EvaluatorStates.SHORT
        assert compare_dict_with_nan(_set_state_mock.await_args[0][4], {
            consumer.PRICE_KEY: trading_constants.ZERO,
            consumer.VOLUME_KEY: decimal.Decimal("1.2"),
            consumer.STOP_PRICE_KEY: decimal.Decimal("25000"),
            consumer.STOP_ONLY: True,
            consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal(math.nan),
            consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [],
            consumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: [],
            consumer.REDUCE_ONLY_KEY: False,
            consumer.TAG_KEY: "stop_1_tag",
            consumer.EXCHANGE_ORDER_IDS: None,
            consumer.TRAILING_PROFILE: None,
            consumer.LEVERAGE: None,
            consumer.ORDER_EXCHANGE_CREATION_PARAMS: {},
            consumer.CANCEL_POLICY: trading_personal_data.ExpirationTimeOrderCancelPolicy.__name__,
            consumer.CANCEL_POLICY_PARAMS: {'expiration_time': 1000.0},
        })
        _set_state_mock.reset_mock()

        await producer.signal_callback({
            mode.EXCHANGE_KEY: exchange_manager.exchange_name,
            mode.SYMBOL_KEY: "unused",
            mode.SIGNAL_KEY: "SelL",
            mode.PRICE_KEY: "123",
            mode.VOLUME_KEY: "12%",
            mode.REDUCE_ONLY_KEY: True,
            mode.ORDER_TYPE_SIGNAL: "LiMiT",
            mode.STOP_PRICE_KEY: "12",
            mode.TAKE_PROFIT_PRICE_KEY: "22222",
            mode.EXCHANGE_ORDER_IDS: ["ab1", "aaaaa"],
            mode.CANCEL_POLICY: "chainedorderfillingpriceordercancelpolicy",
            consumer.LEVERAGE: 22,
            "PARAM_TAG_1": "ttt",
            "PARAM_Plop": False,
        }, context)
        set_leverage_mock.assert_called_once()
        assert set_leverage_mock.mock_calls[0].args[2] == decimal.Decimal(22)
        set_leverage_mock.reset_mock()
        _set_state_mock.assert_awaited_once()
        assert _set_state_mock.await_args[0][1] == symbol
        assert _set_state_mock.await_args[0][2] == trading_view_signals_trading.SignalActions.CREATE_ORDERS
        assert _set_state_mock.await_args[0][3] == trading_enums.EvaluatorStates.SHORT
        assert compare_dict_with_nan(_set_state_mock.await_args[0][4], {
            consumer.PRICE_KEY: decimal.Decimal("123"),
            consumer.VOLUME_KEY: decimal.Decimal("1.2"),
            consumer.STOP_PRICE_KEY: decimal.Decimal("12"),
            consumer.STOP_ONLY: False,
            consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal("22222"),
            consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [],
            consumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: [],
            consumer.REDUCE_ONLY_KEY: True,
            consumer.TAG_KEY: None,
            mode.EXCHANGE_ORDER_IDS: ["ab1", "aaaaa"],
            consumer.TRAILING_PROFILE: None,
            consumer.LEVERAGE: 22,
            consumer.ORDER_EXCHANGE_CREATION_PARAMS: {
                "TAG_1": "ttt",
                "Plop": False,
            },
            consumer.CANCEL_POLICY: trading_personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__,
            consumer.CANCEL_POLICY_PARAMS: None,
        })
        _set_state_mock.reset_mock()

        # with trailing profile and TP volume
        await producer.signal_callback({
            mode.EXCHANGE_KEY: exchange_manager.exchange_name,
            mode.SYMBOL_KEY: "unused",
            mode.SIGNAL_KEY: "SelL",
            mode.PRICE_KEY: "123",
            mode.VOLUME_KEY: "12%",
            mode.REDUCE_ONLY_KEY: True,
            mode.ORDER_TYPE_SIGNAL: "LiMiT",
            mode.STOP_PRICE_KEY: "12",
            mode.TAKE_PROFIT_PRICE_KEY: "22222",
            mode.TAKE_PROFIT_VOLUME_RATIO_KEY: "1",
            mode.EXCHANGE_ORDER_IDS: ["ab1", "aaaaa"],
            mode.TRAILING_PROFILE: "fiLLED_take_profit",
            mode.CANCEL_POLICY: "expirationtimeordercancelpolicy",
            mode.CANCEL_POLICY_PARAMS: "{'expiration_time': 1000.0}",
            consumer.LEVERAGE: 22,
            "PARAM_TAG_1": "ttt",
            "PARAM_Plop": False,
        }, context)
        set_leverage_mock.assert_called_once()
        assert set_leverage_mock.mock_calls[0].args[2] == decimal.Decimal(22)
        set_leverage_mock.reset_mock()
        _set_state_mock.assert_awaited_once()
        assert _set_state_mock.await_args[0][1] == symbol
        assert _set_state_mock.await_args[0][2] == trading_view_signals_trading.SignalActions.CREATE_ORDERS
        assert _set_state_mock.await_args[0][3] == trading_enums.EvaluatorStates.SHORT
        assert compare_dict_with_nan(_set_state_mock.await_args[0][4], {
            consumer.PRICE_KEY: decimal.Decimal("123"),
            consumer.VOLUME_KEY: decimal.Decimal("1.2"),
            consumer.STOP_PRICE_KEY: decimal.Decimal("12"),
            consumer.STOP_ONLY: False,
            consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal("22222"),
            consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [],
            consumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: [decimal.Decimal(1)],
            consumer.REDUCE_ONLY_KEY: True,
            consumer.TAG_KEY: None,
            mode.EXCHANGE_ORDER_IDS: ["ab1", "aaaaa"],
            consumer.LEVERAGE: 22,
            consumer.TRAILING_PROFILE: "filled_take_profit",
            consumer.ORDER_EXCHANGE_CREATION_PARAMS: {
                "TAG_1": "ttt",
                "Plop": False,
            },
            consumer.CANCEL_POLICY: trading_personal_data.ExpirationTimeOrderCancelPolicy.__name__,
            consumer.CANCEL_POLICY_PARAMS: {'expiration_time': 1000.0},
        })
        _set_state_mock.reset_mock()

        # future exchange: call set_leverage
        exchange_manager.is_future = True
        symbol_contract = trading_api.create_default_future_contract(
            "BTC/USDT", decimal.Decimal(4), trading_enums.FutureContractType.LINEAR_PERPETUAL,
            trading_constants.DEFAULT_SYMBOL_POSITION_MODE
        )
        # We have to hardcode the symbol contract as it's not a futures symbol so we can't use load_pair_contract
        exchange_manager.exchange.pair_contracts[symbol] = symbol_contract
        await producer.signal_callback({
            mode.EXCHANGE_KEY: exchange_manager.exchange_name,
            mode.SYMBOL_KEY: "unused",
            mode.SIGNAL_KEY: "SelL",
            mode.PRICE_KEY: "123@",  # price = 123
            mode.VOLUME_KEY: "100q",  # base amount
            mode.REDUCE_ONLY_KEY: False,
            mode.ORDER_TYPE_SIGNAL: "LiMiT",
            mode.STOP_PRICE_KEY: "-10%",  # price - 10%
            f"{mode.TAKE_PROFIT_PRICE_KEY}_0": "120.333333333333333d",   # price  + 120.333333333333333
            f"{mode.TAKE_PROFIT_PRICE_KEY}_1": "122.333333333333333d",   # price  + 122.333333333333333
            f"{mode.TAKE_PROFIT_PRICE_KEY}_2": "4444d",   # price  + 4444
            f"{mode.TAKE_PROFIT_VOLUME_RATIO_KEY}_0": "1",
            f"{mode.TAKE_PROFIT_VOLUME_RATIO_KEY}_1": "1.122",
            f"{mode.TAKE_PROFIT_VOLUME_RATIO_KEY}_2": "0.2222",
            mode.EXCHANGE_ORDER_IDS: ["ab1", "aaaaa"],
            consumer.LEVERAGE: 22,
            "PARAM_TAG_1": "ttt",
            "PARAM_Plop": False,
        }, context)
        set_leverage_mock.assert_called_once()
        assert set_leverage_mock.mock_calls[0].args[2] == decimal.Decimal("22")
        _set_state_mock.assert_awaited_once()
        assert _set_state_mock.await_args[0][1] == symbol
        assert _set_state_mock.await_args[0][2] == trading_view_signals_trading.SignalActions.CREATE_ORDERS
        assert _set_state_mock.await_args[0][3] == trading_enums.EvaluatorStates.SHORT
        assert compare_dict_with_nan(_set_state_mock.await_args[0][4], {
            consumer.PRICE_KEY: decimal.Decimal("123"),
            consumer.VOLUME_KEY: decimal.Decimal("0.8130081300813008130081300813"),
            consumer.STOP_PRICE_KEY: decimal.Decimal("6308.27549999"),
            consumer.STOP_ONLY: False,
            consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal("nan"), # only additional TP orders are provided
            consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [
                decimal.Decimal("7129.52833333"), decimal.Decimal("7131.52833333"), decimal.Decimal('11453.19499999')
            ],
            consumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: [
                decimal.Decimal("1"), decimal.Decimal("1.122"), decimal.Decimal("0.2222"),
            ],
            consumer.REDUCE_ONLY_KEY: False,
            consumer.TAG_KEY: None,
            mode.EXCHANGE_ORDER_IDS: ["ab1", "aaaaa"],
            consumer.TRAILING_PROFILE: None,
            consumer.LEVERAGE: 22,
            consumer.ORDER_EXCHANGE_CREATION_PARAMS: {
                "TAG_1": "ttt",
                "Plop": False,
            },
            consumer.CANCEL_POLICY: None,
            consumer.CANCEL_POLICY_PARAMS: None,
        })
        _set_state_mock.reset_mock()
        set_leverage_mock.reset_mock()

        with pytest.raises(errors.MissingFunds):
            await producer.signal_callback({
                mode.EXCHANGE_KEY: exchange_manager.exchange_name,
                mode.SYMBOL_KEY: "unused",
                mode.SIGNAL_KEY: "SelL",
                mode.PRICE_KEY: "123000q",  # price = 123
                mode.VOLUME_KEY: "11111b",  # base amount: not enough funds
                mode.REDUCE_ONLY_KEY: True,
                mode.ORDER_TYPE_SIGNAL: "LiMiT",
                mode.STOP_PRICE_KEY: "-10%",  # price - 10%
                mode.TAKE_PROFIT_PRICE_KEY: "120.333333333333333d",   # price  + 120.333333333333333
                mode.EXCHANGE_ORDER_IDS: ["ab1", "aaaaa"],
                mode.LEVERAGE: None,
                "PARAM_TAG_1": "ttt",
                "PARAM_Plop": False,
            }, context)
        set_leverage_mock.assert_not_called()
        _set_state_mock.assert_not_called()

        with pytest.raises(errors.InvalidArgumentError):
            await producer.signal_callback({
                mode.EXCHANGE_KEY: exchange_manager.exchange_name,
                mode.SYMBOL_KEY: "unused",
                mode.SIGNAL_KEY: "DSDSDDSS",
                mode.PRICE_KEY: "123000q",  # price = 123
                mode.VOLUME_KEY: "11111b",  # base amount: not enough funds
                mode.REDUCE_ONLY_KEY: True,
                mode.ORDER_TYPE_SIGNAL: "LiMiT",
                mode.STOP_PRICE_KEY: "-10%",  # price - 10%
                mode.TAKE_PROFIT_PRICE_KEY: "120.333333333333333d",   # price  + 120.333333333333333
                mode.EXCHANGE_ORDER_IDS: ["ab1", "aaaaa"],
                mode.LEVERAGE: None,
                "PARAM_TAG_1": "ttt",
                "PARAM_Plop": False,
            }, context)
        set_leverage_mock.assert_not_called()
        _set_state_mock.assert_not_called()

        with pytest.raises(errors.InvalidCancelPolicyError):
            await producer.signal_callback({
                mode.EXCHANGE_KEY: exchange_manager.exchange_name,
                mode.SYMBOL_KEY: "unused",
                mode.SIGNAL_KEY: "SelL",
                mode.CANCEL_POLICY: "unknown_cancel_policy",
            }, context)
        set_leverage_mock.assert_not_called()
        _set_state_mock.assert_not_called()

        # Test meta action only signal - should return early without calling _parse_order_details or _set_state
        _set_state_mock.reset_mock()
        prev_value = set(mode.META_ACTION_ONLY_SIGNALS)
        try:
            mode.META_ACTION_ONLY_SIGNALS.add("buy")
            with mock.patch.object(producer, "_parse_order_details", mock.AsyncMock()) as _parse_order_details_mock, \
                mock.patch.object(producer, "apply_cancel_policies", mock.AsyncMock(return_value=(True, None))) as apply_cancel_policies_mock, \
                mock.patch.object(producer, "_process_pre_state_update_actions", mock.AsyncMock()) as _process_pre_state_update_actions_mock, \
                mock.patch.object(producer, "_process_meta_actions", mock.AsyncMock()) as _process_meta_actions_mock:
                await producer.signal_callback({
                    mode.EXCHANGE_KEY: exchange_manager.exchange_name,
                    mode.SYMBOL_KEY: "unused",
                    mode.SIGNAL_KEY: "BUY",
                }, context)
                # Should call apply_cancel_policies, _process_pre_state_update_actions, and _process_meta_actions
                apply_cancel_policies_mock.assert_awaited_once()
                _process_pre_state_update_actions_mock.assert_awaited_once()
                _process_meta_actions_mock.assert_awaited_once()
                # Should NOT call _parse_order_details or _set_state (early return)
                _parse_order_details_mock.assert_not_awaited()
                _set_state_mock.assert_not_awaited()
        finally:
            mode.__class__.META_ACTION_ONLY_SIGNALS = prev_value


async def test_signal_callback_with_meta_actions(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    mode.CANCEL_PREVIOUS_ORDERS = True
    context = script_keywords.get_base_context(producer.trading_mode)
    with mock.patch.object(producer, "_set_state", mock.AsyncMock()) as _set_state_mock, \
        mock.patch.object(mode, "set_leverage", mock.AsyncMock()) as set_leverage_mock, \
        mock.patch.object(producer, "cancel_symbol_open_orders", mock.AsyncMock()) as cancel_symbol_open_orders_mock:
        await producer.signal_callback({
            mode.SIGNAL_KEY: mode.ENSURE_EXCHANGE_BALANCE_SIGNAL,
        }, context)
        _set_state_mock.assert_awaited_once()
        set_leverage_mock.assert_not_called()
        cancel_symbol_open_orders_mock.assert_not_called() # not called for meta actions even when CANCEL_PREVIOUS_ORDERS is True
        assert _set_state_mock.await_args[0][1] == symbol
        assert _set_state_mock.await_args[0][2] == trading_view_signals_trading.SignalActions.ENSURE_EXCHANGE_BALANCE
        assert _set_state_mock.await_args[0][3] == trading_enums.EvaluatorStates.NEUTRAL
        assert compare_dict_with_nan(_set_state_mock.await_args[0][4], {
            consumer.PRICE_KEY: trading_constants.ZERO,
            consumer.VOLUME_KEY: trading_constants.ZERO,
            consumer.STOP_PRICE_KEY: decimal.Decimal(math.nan),
            consumer.STOP_ONLY: False,
            consumer.TAKE_PROFIT_PRICE_KEY: decimal.Decimal(math.nan),
            consumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: [],
            consumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: [],
            consumer.REDUCE_ONLY_KEY: False,
            consumer.TAG_KEY: None,
            consumer.TRAILING_PROFILE: None,
            consumer.EXCHANGE_ORDER_IDS: None,
            consumer.LEVERAGE: None,
            consumer.ORDER_EXCHANGE_CREATION_PARAMS: {},
            consumer.CANCEL_POLICY: None,
            consumer.CANCEL_POLICY_PARAMS: None,
        })
        assert compare_dict_with_nan(_set_state_mock.await_args[0][5], {
            mode.SIGNAL_KEY: mode.ENSURE_EXCHANGE_BALANCE_SIGNAL,
        })
        _set_state_mock.reset_mock()


async def test_signal_callback_with_cancel_policies(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    context = script_keywords.get_base_context(producer.trading_mode)
    mode.CANCEL_PREVIOUS_ORDERS = True
    print(f"{mode.META_ACTION_ONLY_SIGNALS=}")

    async def _apply_cancel_policies(*args, **kwargs):
        return True, trading_signals.get_orders_dependencies([mock.Mock(order_id="123"), mock.Mock(order_id="456-cancel_policy")])
    async def _cancel_symbol_open_orders(*args, **kwargs):
        return True, trading_signals.get_orders_dependencies([mock.Mock(order_id="456-cancel_symbol_open_orders")])

    with mock.patch.object(producer, "_set_state", mock.AsyncMock()) as _set_state_mock, \
        mock.patch.object(producer, "_process_pre_state_update_actions", mock.AsyncMock()) as _process_pre_state_update_actions_mock, \
        mock.patch.object(producer, "_parse_order_details", mock.AsyncMock(return_value=(
            trading_view_signals_trading.SignalActions.CREATE_ORDERS,
            trading_enums.EvaluatorStates.LONG,
            {}
        ))) as _parse_order_details_mock, \
        mock.patch.object(producer, "apply_cancel_policies", mock.AsyncMock(side_effect=_apply_cancel_policies)) as apply_cancel_policies_mock, \
        mock.patch.object(producer, "cancel_symbol_open_orders", mock.AsyncMock(side_effect=_cancel_symbol_open_orders)) as cancel_symbol_open_orders_mock:
        await producer.signal_callback({
            mode.EXCHANGE_KEY: exchange_manager.exchange_name,
            mode.SYMBOL_KEY: "unused",
            mode.SIGNAL_KEY: "BUY",
        }, context)
        _process_pre_state_update_actions_mock.assert_awaited_once()
        _parse_order_details_mock.assert_awaited_once()
        apply_cancel_policies_mock.assert_awaited_once()
        cancel_symbol_open_orders_mock.assert_awaited_once()
        _set_state_mock.assert_awaited_once()
        assert _set_state_mock.mock_calls[0].kwargs["dependencies"] == trading_signals.get_orders_dependencies([
            mock.Mock(order_id="123"), 
            mock.Mock(order_id="456-cancel_policy"), 
            mock.Mock(order_id="456-cancel_symbol_open_orders")
        ])
    mode.CANCEL_PREVIOUS_ORDERS = False
    with mock.patch.object(producer, "_set_state", mock.AsyncMock()) as _set_state_mock, \
        mock.patch.object(producer, "_process_pre_state_update_actions", mock.AsyncMock()) as _process_pre_state_update_actions_mock, \
        mock.patch.object(producer, "_parse_order_details", mock.AsyncMock(return_value=(trading_view_signals_trading.SignalActions.CREATE_ORDERS, trading_enums.EvaluatorStates.LONG, {}))) as _parse_order_details_mock, \
        mock.patch.object(producer, "apply_cancel_policies", mock.AsyncMock(side_effect=_apply_cancel_policies)) as apply_cancel_policies_mock, \
        mock.patch.object(producer, "cancel_symbol_open_orders", mock.AsyncMock(side_effect=_cancel_symbol_open_orders)) as cancel_symbol_open_orders_mock:
        await producer.signal_callback({
            mode.EXCHANGE_KEY: exchange_manager.exchange_name,
            mode.SYMBOL_KEY: "unused",
            mode.SIGNAL_KEY: "BUY",
        }, context)
        _process_pre_state_update_actions_mock.assert_awaited_once()
        _parse_order_details_mock.assert_awaited_once()
        apply_cancel_policies_mock.assert_awaited_once()
        cancel_symbol_open_orders_mock.assert_not_called() # CANCEL_PREVIOUS_ORDERS is False
        _set_state_mock.assert_awaited_once()
        assert _set_state_mock.mock_calls[0].kwargs["dependencies"] == trading_signals.get_orders_dependencies([
            mock.Mock(order_id="123"), 
            mock.Mock(order_id="456-cancel_policy"),
        ])


async def test_set_state(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    cryptocurrency = mode.cryptocurrency
    order_data = {
        consumer.PRICE_KEY: decimal.Decimal("100"),
        consumer.VOLUME_KEY: decimal.Decimal("1.0"),
    }
    parsed_data = {
        mode.EXCHANGE_KEY: exchange_manager.exchange_name,
        mode.SYMBOL_KEY: symbol,
        mode.SIGNAL_KEY: "BUY",
    }
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="test_order")])

    # Test CREATE_ORDERS action - should call submit_trading_evaluation
    exchange_manager.is_backtesting = False
    with mock.patch.object(producer, "submit_trading_evaluation", mock.AsyncMock()) as submit_mock, \
        mock.patch.object(producer, "_send_alert_notification", mock.AsyncMock()) as send_notification_mock, \
        mock.patch.object(producer.logger, "info") as logger_info_mock:
        producer.state = trading_enums.EvaluatorStates.NEUTRAL
        producer.final_eval = -0.5
        
        await producer._set_state(
            cryptocurrency,
            symbol,
            trading_view_signals_trading.SignalActions.CREATE_ORDERS,
            trading_enums.EvaluatorStates.LONG,
            order_data,
            parsed_data,
            dependencies=dependencies
        )
        
        # State should be updated
        assert producer.state == trading_enums.EvaluatorStates.LONG
        logger_info_mock.assert_called()
        assert "new state" in str(logger_info_mock.call_args_list).lower()
        
        # Should call submit_trading_evaluation
        submit_mock.assert_awaited_once()
        call_args = submit_mock.await_args
        assert call_args.kwargs["cryptocurrency"] == cryptocurrency
        assert call_args.kwargs["symbol"] == symbol
        assert call_args.kwargs["time_frame"] is None
        assert call_args.kwargs["final_note"] == producer.final_eval
        assert call_args.kwargs["state"] == trading_enums.EvaluatorStates.LONG
        assert call_args.kwargs["data"] == order_data
        assert call_args.kwargs["dependencies"] == dependencies
        
        send_notification_mock.assert_awaited_once_with(symbol, trading_enums.EvaluatorStates.LONG)
        exchange_manager.is_backtesting = True
        submit_mock.reset_mock()
        logger_info_mock.reset_mock()

    # Test ENSURE_EXCHANGE_BALANCE action - should call process_non_creating_orders_actions
    with mock.patch.object(producer, "process_non_creating_orders_actions", mock.AsyncMock()) as process_actions_mock, \
        mock.patch.object(producer, "submit_trading_evaluation", mock.AsyncMock()) as submit_mock:
        producer.state = trading_enums.EvaluatorStates.NEUTRAL
        
        await producer._set_state(
            cryptocurrency,
            symbol,
            trading_view_signals_trading.SignalActions.ENSURE_EXCHANGE_BALANCE,
            trading_enums.EvaluatorStates.NEUTRAL,
            order_data,
            parsed_data,
            dependencies=dependencies
        )
        
        # Should call process_non_creating_orders_actions
        process_actions_mock.assert_awaited_once_with(
            trading_view_signals_trading.SignalActions.ENSURE_EXCHANGE_BALANCE,
            symbol,
            order_data,
            parsed_data
        )
        # Should not call submit_trading_evaluation
        submit_mock.assert_not_awaited()
        process_actions_mock.reset_mock()

    # Test CANCEL_ORDERS action - should call process_non_creating_orders_actions
    with mock.patch.object(producer, "process_non_creating_orders_actions", mock.AsyncMock()) as process_actions_mock, \
        mock.patch.object(producer, "submit_trading_evaluation", mock.AsyncMock()) as submit_mock:
        await producer._set_state(
            cryptocurrency,
            symbol,
            trading_view_signals_trading.SignalActions.CANCEL_ORDERS,
            trading_enums.EvaluatorStates.NEUTRAL,
            order_data,
            parsed_data,
            dependencies=dependencies
        )
        
        process_actions_mock.assert_awaited_once_with(
            trading_view_signals_trading.SignalActions.CANCEL_ORDERS,
            symbol,
            order_data,
            parsed_data
        )
        submit_mock.assert_not_awaited()
        process_actions_mock.reset_mock()

    # Test with None dependencies
    with mock.patch.object(producer, "submit_trading_evaluation", mock.AsyncMock()) as submit_mock:
        await producer._set_state(
            cryptocurrency,
            symbol,
            trading_view_signals_trading.SignalActions.CREATE_ORDERS,
            trading_enums.EvaluatorStates.LONG,
            order_data,
            parsed_data,
            dependencies=None
        )
        
        submit_mock.assert_awaited_once()
        assert submit_mock.await_args.kwargs["dependencies"] is None


async def test_process_non_creating_orders_actions(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    order_data = {
        consumer.EXCHANGE_ORDER_IDS: ["order_1", "order_2"],
        consumer.TAG_KEY: "test_tag",
    }
    parsed_data = {
        mode.EXCHANGE_KEY: exchange_manager.exchange_name,
        mode.SYMBOL_KEY: symbol,
    }

    # Test CANCEL_ORDERS action
    with mock.patch.object(producer, "cancel_orders_from_order_data", mock.AsyncMock(return_value=(True, None))) \
        as cancel_orders_mock:
        await producer.process_non_creating_orders_actions(
            trading_view_signals_trading.SignalActions.CANCEL_ORDERS,
            symbol,
            order_data,
            parsed_data
        )
        cancel_orders_mock.assert_awaited_once_with(symbol, order_data, parsed_data)
        cancel_orders_mock.reset_mock()

    # Test ENSURE_EXCHANGE_BALANCE action
    with mock.patch.object(producer, "ensure_exchange_balance", mock.AsyncMock()) as ensure_exchange_mock:
        await producer.process_non_creating_orders_actions(
            trading_view_signals_trading.SignalActions.ENSURE_EXCHANGE_BALANCE,
            symbol,
            order_data,
            parsed_data
        )
        ensure_exchange_mock.assert_awaited_once_with(parsed_data)
        ensure_exchange_mock.reset_mock()

    # Test ENSURE_BLOCKCHAIN_WALLET_BALANCE action
    with mock.patch.object(producer, "ensure_blockchain_wallet_balance", mock.AsyncMock()) \
        as ensure_blockchain_mock:
        await producer.process_non_creating_orders_actions(
            trading_view_signals_trading.SignalActions.ENSURE_BLOCKCHAIN_WALLET_BALANCE,
            symbol,
            order_data,
            parsed_data
        )
        ensure_blockchain_mock.assert_awaited_once_with(parsed_data)
        ensure_blockchain_mock.reset_mock()

    # Test WITHDRAW_FUNDS action
    with mock.patch.object(producer, "withdraw_funds", mock.AsyncMock()) as withdraw_funds_mock:
        await producer.process_non_creating_orders_actions(
            trading_view_signals_trading.SignalActions.WITHDRAW_FUNDS,
            symbol,
            order_data,
            parsed_data
        )
        withdraw_funds_mock.assert_awaited_once_with(parsed_data)
        withdraw_funds_mock.reset_mock()

    # Test TRANSFER_FUNDS action
    with mock.patch.object(producer, "transfer_funds", mock.AsyncMock()) as transfer_funds_mock:
        await producer.process_non_creating_orders_actions(
            trading_view_signals_trading.SignalActions.TRANSFER_FUNDS,
            symbol,
            order_data,
            parsed_data
        )
        transfer_funds_mock.assert_awaited_once_with(parsed_data)
        transfer_funds_mock.reset_mock()

    # Test unknown action - should raise InvalidArgumentError
    with pytest.raises(errors.InvalidArgumentError, match="Unknown action"):
        await producer.process_non_creating_orders_actions(
            trading_view_signals_trading.SignalActions.NO_ACTION,
            symbol,
            order_data,
            parsed_data
        )

    # Test CREATE_ORDERS action - should raise InvalidArgumentError (not handled by this method)
        with pytest.raises(errors.InvalidArgumentError, match="Unknown action"):
            await producer.process_non_creating_orders_actions(
                trading_view_signals_trading.SignalActions.CREATE_ORDERS,
                symbol,
                order_data,
                parsed_data
            )


async def test_ensure_exchange_balance(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    asset = "USDT"
    portfolio = exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    
    # Test with sufficient holdings
    parsed_data = {
        "asset": asset,
        "holdings": 100.0,
    }
    
    # Set portfolio balance to have enough
    portfolio._update_portfolio_data(asset, total_value=decimal.Decimal("150.0"), available_value=decimal.Decimal("150.0"), replace_value=True)
    
    with mock.patch.object(producer.logger, "info") as logger_info_mock:
        await producer.ensure_exchange_balance(parsed_data)
        
        logger_info_mock.assert_called_once()
        assert "Enough" in str(logger_info_mock.call_args)
        assert asset in str(logger_info_mock.call_args)
    
    # Test with insufficient holdings
    portfolio._update_portfolio_data(asset, total_value=decimal.Decimal("50.0"), available_value=decimal.Decimal("50.0"), replace_value=True)
    
    with pytest.raises(trading_view_signals_trading_mode_errors.MissingFundsError) as exc_info:
        await producer.ensure_exchange_balance(parsed_data)
    assert "Not enough" in str(exc_info.value)
    assert asset in str(exc_info.value)
    assert "available: 50" in str(exc_info.value)
    assert "required: 100" in str(exc_info.value)


async def test_ensure_blockchain_wallet_balance(tools, blockchain_wallet_details):
    exchange_manager, symbol, mode, producer, consumer = tools    
    
    parsed_data = {
        "asset": BLOCKCHAIN_WALLET_ASSET,
        "holdings": 5.0,
        "wallet_details": blockchain_wallet_details,
    }
    async with trading_api.blockchain_wallet_context(blockchain_wallet_details, exchange_manager.trader) as wallet:
    
        with mock.patch.object(producer.logger, "info") as logger_info_mock:
            await producer.ensure_blockchain_wallet_balance(parsed_data)
            
            logger_info_mock.assert_called_once()
            assert "Enough" in str(logger_info_mock.call_args)
            assert BLOCKCHAIN_WALLET_ASSET in str(logger_info_mock.call_args)
    
    # Test with insufficient balance
    blockchain_wallet_details.wallet_descriptor.specific_config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: BLOCKCHAIN_WALLET_ASSET,
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 2.0
            }
        ]}
    async with trading_api.blockchain_wallet_context(blockchain_wallet_details, exchange_manager.trader) as wallet:
    
        with pytest.raises(trading_view_signals_trading_mode_errors.MissingFundsError) as exc_info:
            await producer.ensure_blockchain_wallet_balance(parsed_data)
        assert "Not enough" in str(exc_info.value)
        assert BLOCKCHAIN_WALLET_ASSET in str(exc_info.value)
        assert "available: 2" in str(exc_info.value)
        assert "required: 5" in str(exc_info.value)
    
    # Test when asset not in wallet balance
    blockchain_wallet_details.wallet_descriptor.specific_config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: []
    }
    async with trading_api.blockchain_wallet_context(blockchain_wallet_details, exchange_manager.trader) as wallet:
    
        with pytest.raises(trading_view_signals_trading_mode_errors.MissingFundsError) as exc_info:
            await producer.ensure_blockchain_wallet_balance(parsed_data)
        assert "Not enough" in str(exc_info.value)
        assert "available: 0" in str(exc_info.value)


async def test_withdraw_funds(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    asset = "BTC"
    amount = 0.1
    network = "bitcoin"
    address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    tag = "test_tag"
    params = {"test_param": "test_value"}
    
    parsed_data = {
        "asset": asset,
        "amount": amount,
        "network": network,
        "address": address,
        "tag": tag,
        "params": params,
    }
    
    # Set portfolio balance to have enough for withdrawal
    portfolio = exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    portfolio._update_portfolio_data(asset, total_value=decimal.Decimal("1.0"), available_value=decimal.Decimal("1.0"), replace_value=True)
    
    # Test successful withdrawal
    with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', True), \
        mock.patch.object(producer.logger, "info") as logger_info_mock, \
        mock.patch.object(producer.exchange_manager.trader, "_withdraw_on_exchange", mock.AsyncMock(wraps=producer.exchange_manager.trader._withdraw_on_exchange)) as _withdraw_on_exchange_mock:
        await producer.withdraw_funds(parsed_data)
        _withdraw_on_exchange_mock.assert_awaited_once_with(asset, decimal.Decimal(str(amount)), network, address, tag=tag, params=params)
        logger_info_mock.assert_called_once()
        assert "Withdrawn" in str(logger_info_mock.call_args)
        assert asset in str(logger_info_mock.call_args)
        _withdraw_on_exchange_mock.reset_mock()
        logger_info_mock.reset_mock()
    
        # Test when ALLOW_FUNDS_TRANSFER is False - should raise DisabledFundsTransferError
        with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', False):
            with pytest.raises(errors.DisabledFundsTransferError):
                await producer.withdraw_funds(parsed_data)
        _withdraw_on_exchange_mock.assert_not_awaited()

async def test_transfer_funds(tools, blockchain_wallet_details):
    exchange_manager, symbol, mode, producer, consumer = tools
    amount = 1.0
    address = "0x1234567890123456789012345678901234567890"    
    
    parsed_data = {
        "asset": BLOCKCHAIN_WALLET_ASSET,
        "amount": amount,
        "address": address,
        "wallet_details": blockchain_wallet_details,
    }
    
    # Test successful transfer
    with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', True), \
        mock.patch.object(producer.logger, "info") as logger_info_mock, \
        mock.patch.object(blockchain_wallets.BlockchainWalletSimulator, "withdraw", mock.AsyncMock()) as withdraw_mock:
        await producer.transfer_funds(parsed_data)
        withdraw_mock.assert_awaited_once_with(
            BLOCKCHAIN_WALLET_ASSET, decimal.Decimal(str(amount)), trading_constants.SIMULATED_BLOCKCHAIN_NETWORK, address
        )
        
        logger_info_mock.assert_called_once()
        assert "Transferred" in str(logger_info_mock.call_args)
        assert BLOCKCHAIN_WALLET_ASSET in str(logger_info_mock.call_args)
        withdraw_mock.reset_mock()
        logger_info_mock.reset_mock()


async def test_is_non_order_signal(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    for signal in mode.NON_ORDER_SIGNALS:
        assert mode.is_non_order_signal({
            mode.SIGNAL_KEY: signal,
        }) is True
    for signal in [mode.BUY_SIGNAL, mode.SELL_SIGNAL, mode.MARKET_SIGNAL, mode.LIMIT_SIGNAL, mode.STOP_SIGNAL, mode.CANCEL_SIGNAL, "plop"]:
        assert mode.is_non_order_signal({
            mode.SIGNAL_KEY: signal,
        }) is False


async def test_is_meta_action_only(tools):
    exchange_manager, symbol, mode, producer, consumer = tools
    # Test with missing SIGNAL_KEY - should return False
    assert mode.is_meta_action_only({}) is False
    
    # Test with various signals - all should return False since META_ACTION_ONLY_SIGNALS is currently an empty set
    # and get_signal returns a string, so string == set() will always be False
    for signal in [
        mode.BUY_SIGNAL,
        mode.SELL_SIGNAL,
        mode.MARKET_SIGNAL,
        mode.LIMIT_SIGNAL,
        mode.STOP_SIGNAL,
        mode.CANCEL_SIGNAL,
        mode.ENSURE_EXCHANGE_BALANCE_SIGNAL,
        mode.ENSURE_BLOCKCHAIN_WALLET_BALANCE_SIGNAL,
        mode.WITHDRAW_FUNDS_SIGNAL,
        mode.TRANSFER_FUNDS_SIGNAL,
        "unknown_signal",
        "",
    ]:
        assert mode.is_meta_action_only({
            mode.SIGNAL_KEY: signal,
        }) is False
    
    # Test case-insensitive behavior (get_signal uses casefold)
    assert mode.is_meta_action_only({
        mode.SIGNAL_KEY: "BUY",
    }) is False
    assert mode.is_meta_action_only({
        mode.SIGNAL_KEY: "buy",
    }) is False
    assert mode.is_meta_action_only({
        mode.SIGNAL_KEY: "Buy",
    }) is False
    prev_value = set(mode.META_ACTION_ONLY_SIGNALS)
    try:
        mode.META_ACTION_ONLY_SIGNALS.add("buy")
        assert mode.is_meta_action_only({
            mode.SIGNAL_KEY: "BUY",
        }) is True
    finally:
        mode.__class__.META_ACTION_ONLY_SIGNALS = prev_value


def compare_dict_with_nan(d_1, d_2):
    try:
        for key, val in d_1.items():
            assert (
                d_2[key] == d_1[key]
                or (isinstance(d_2[key], decimal.Decimal) and d_2[key].is_nan() and isinstance(d_1[key], decimal.Decimal) and d_1[key].is_nan())
                or compare_dict_with_nan(d_1[key], d_2[key])
            ), f"Key {key} is not equal: {d_1[key]} != {d_2[key]}"
        return True
    except (KeyError, AttributeError) as err:
        # print(f"Error comparing dicts: {err.__class__.__name__}: {err}")
        return False
